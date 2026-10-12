#!/usr/bin/env python3
"""Failure-only Adreno 650 / FF7R Turnip KGSL allocation diagnostic.

Run against a clean, pinned Mesa source checkout. Strict source anchors ensure a
changed upstream implementation fails closed instead of making a silent no-op.
Enable runtime stderr markers with TU_A650_KGSL_ALLOC_TRACE=1. This does NOT
modify Vulkan caps, allocation flags, result values or kernel ioctl behavior.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import re

MARKER = "FF7R-A650-KGSL-ALLOC"


def add_includes(source: str) -> str:
    match = re.search(r"^#include [<\"][^>\"]+[>\"]\s*$", source, re.MULTILINE)
    if match is None:
        raise ValueError("No C++ include directive found")
    return (source[:match.start()] +
            "#include <atomic>\n#include <cerrno>\n#include <cstdio>\n#include <cstdlib>\n" +
            source[match.start():])


def instrument_kgsl(source: str) -> str:
    if MARKER in source:
        raise ValueError("KGSL code already instrumented")
    pattern = re.compile(
        r"(ret\s*=\s*safe_ioctl\s*\(\s*dev->physical_device->local_fd\s*,"
        r"\s*IOCTL_KGSL_GPUMEM_ALLOC_ID\s*,\s*&req\s*\)\s*;\s*"
        r"if\s*\(\s*ret\s*\)\s*\{)",
        flags=re.MULTILINE)
    matches = list(pattern.finditer(source))
    if len(matches) != 1:
        raise ValueError(f"Expected exactly one GPUMEM_ALLOC_ID failure branch, got {len(matches)}")
    # Do not modify the existing error/return branch: only add stderr telemetry.
    add = r'''
      // Opt-in, failure-only diagnostic; no live BO addresses or client data.
      const int ff7r_saved_errno = errno;
      static std::atomic<unsigned> ff7r_log_count { 0u };
      if (const char* trace = std::getenv("TU_A650_KGSL_ALLOC_TRACE");
          trace && trace[0] == '1' && trace[1] == '\0'
          && ff7r_log_count.fetch_add(1u, std::memory_order_relaxed) < 128u) {
         std::fprintf(stderr,
            "FF7R-A650-KGSL-ALLOC stage=gpumem_alloc_id errno=%d"
            " request_bytes=%llu align_bytes=%llu bo_flags=%llu"
            " request_flags=%llu force_32bit=%d replayable=%d\n",
            ff7r_saved_errno,
            static_cast<unsigned long long>(size),
            static_cast<unsigned long long>(align),
            static_cast<unsigned long long>(flags),
            static_cast<unsigned long long>(req.flags),
            (req.flags & KGSL_MEMFLAGS_FORCE_32BIT) ? 1 : 0,
            (flags & TU_BO_ALLOC_REPLAYABLE) ? 1 : 0);
      }
      errno = ff7r_saved_errno;
'''
    pos = matches[0].end()
    return add_includes(source[:pos] + add + source[pos:])


def instrument_tu_device(source: str) -> str:
    if "FF7R-A650-TU-ALLOC" in source:
        raise ValueError("Turnip code already instrumented")
    start = source.find("tu_AllocateMemory(")
    if start < 0:
        raise ValueError("No tu_AllocateMemory function found")
    end = source.find("\ntu_allocate_lazy_memory(", start)
    if end < 0:
        raise ValueError("No next function boundary")
    body = source[start:end]
    target = "if (result != VK_SUCCESS) {"
    if body.count(target) != 1:
        raise ValueError("Expected one allocation failure branch")
    add = r'''
      // Opt-in failure-only root-cause stage, no memory behavior changes.
      static std::atomic<unsigned> ff7r_tu_log_count { 0u };
      if (const char* trace = std::getenv("TU_A650_KGSL_ALLOC_TRACE");
          trace && trace[0] == '1' && trace[1] == '\0'
          && ff7r_tu_log_count.fetch_add(1u, std::memory_order_relaxed) < 128u) {
         std::fprintf(stderr,
            "FF7R-A650-TU-ALLOC stage=tu_allocate_failure vkresult=%d"
            " requested_bytes=%llu memory_type=%u heap_used_bytes=%llu"
            " heap_size_bytes=%llu allocate_flags=%u\n",
            static_cast<int>(result),
            static_cast<unsigned long long>(pAllocateInfo->allocationSize),
            pAllocateInfo->memoryTypeIndex,
            static_cast<unsigned long long>(p_atomic_read(&mem_heap->used)),
            static_cast<unsigned long long>(mem_heap->size),
            flags_info ? static_cast<unsigned>(flags_info->flags) : 0u);
      }
'''
    body = body.replace(target, target + add)
    return add_includes(source[:start] + body + source[end:])


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("mesa", type=Path, nargs="?", default=Path("."))
    args = p.parse_args()
    kgsl = args.mesa / "src/freedreno/vulkan/tu_knl_kgsl.cc"
    device = args.mesa / "src/freedreno/vulkan/tu_device.cc"
    # Fail closed; make no edits until both input structures are validated.
    updated_kgsl = instrument_kgsl(kgsl.read_text())
    updated_device = instrument_tu_device(device.read_text())
    kgsl.write_text(updated_kgsl)
    device.write_text(updated_device)
    print("FF7R-A650: inserted bounded failure-only KGSL errno and tu_AllocateMemory result diagnostics")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
