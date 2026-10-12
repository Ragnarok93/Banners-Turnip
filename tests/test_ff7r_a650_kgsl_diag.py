"""Fail-closed fixture tests for optional A650 KGSL/Vulkan memory diagnostics."""
import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "patches/a650/instrument_kgsl_oom.py"
spec = importlib.util.spec_from_file_location("tu_ff7r", SRC)
tu = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = tu
spec.loader.exec_module(tu)

KGSL = """#include <stdlib.h>
int foo() {
 int ret;
 ret = safe_ioctl(dev->physical_device->local_fd,
                  IOCTL_KGSL_GPUMEM_ALLOC_ID, &req);
 if (ret) {
   return vk_errorf(dev, VK_ERROR_OUT_OF_DEVICE_MEMORY, "GPUMEM_ALLOC_ID failed");
 }
}
"""
DEVICE = """#include <cstring>
tu_AllocateMemory(int arg) {
 const VkMemoryAllocateFlagsInfo *flags_info = nullptr;
 VkResult result;
 if (result != VK_SUCCESS) {
   return result;
 }
 return VK_SUCCESS;
}
VkResult
tu_allocate_lazy_memory(int i) { return VK_SUCCESS; }
"""


class KgslDiagnosticsTests(unittest.TestCase):
    def test_kgsl_injects_in_failure_only_without_swallowing_error(self):
        s = tu.instrument_kgsl(KGSL)
        self.assertIn("FF7R-A650-KGSL-ALLOC", s)
        self.assertIn("TU_A650_KGSL_ALLOC_TRACE", s)
        self.assertIn("ff7r_saved_errno", s)
        self.assertIn("errno = ff7r_saved_errno", s)
        self.assertIn("KGSL_MEMFLAGS_FORCE_32BIT", s)
        self.assertIn("ff7r_log_count.fetch_add(1u", s)
        self.assertIn('return vk_errorf(dev, VK_ERROR_OUT_OF_DEVICE_MEMORY', s)
        self.assertEqual(s.count("IOCTL_KGSL_GPUMEM_ALLOC_ID"), 1)
        self.assertRaises(ValueError, tu.instrument_kgsl, s)

    def test_tu_failure_reporting_retains_result(self):
        s = tu.instrument_tu_device(DEVICE)
        self.assertIn("FF7R-A650-TU-ALLOC", s)
        self.assertIn("heap_used_bytes", s)
        self.assertIn("heap_size_bytes", s)
        self.assertIn("allocate_flags", s)
        self.assertIn("memory_type", s)
        self.assertIn("return result;", s)
        self.assertRaises(ValueError, tu.instrument_tu_device, s)

    def test_fail_closed_when_source_changes(self):
        self.assertRaises(ValueError, tu.instrument_kgsl, "#include <cstdio>\nvoid f() {}")
        self.assertRaises(ValueError, tu.instrument_tu_device, "#include <cstdio>\nvoid f() {}")

    def test_bounded_and_disabled_by_default(self):
        for s in [tu.instrument_kgsl(KGSL), tu.instrument_tu_device(DEVICE)]:
            self.assertIn('trace && trace[0] == \'1\'', s)
            self.assertIn("memory_order_relaxed) < 128u", s)
            self.assertIn("#include <atomic>", s)

    def test_build_script_keeps_standard_mode(self):
        s = (ROOT / "build_turnip.sh").read_text()
        self.assertIn('TURNIP_A650_FF7R:-0', s)
        self.assertIn('-mtune=cortex-a77', s)
        self.assertIn('-flto=thin', s)
        self.assertIn('BUILD_SUFFIX', s)


if __name__ == "__main__":
    unittest.main()
