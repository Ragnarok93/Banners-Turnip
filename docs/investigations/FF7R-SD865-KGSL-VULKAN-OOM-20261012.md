# FFVII Remake / Adreno 650 — Turnip/KGSL Vulkan allocation investigation

**Date:** 2026-10-12 UTC. **Owner:** Turnip driver subsystem (`Ragnarok93/Banners-Turnip`). **Status:** Evidence audit + reproducible diagnostic proposal; **no driver binary patch or hardware validation is claimed**.

This is intentionally separate from GameNative UI/env plumbing (`Ragnarok93/GameNative`), DXVK allocator behavior (`Ragnarok93/dxvk-SD865`), and FEX JIT/cache (`Ragnarok93/FEX`). The user's exact driver for the failing captures is the **Mr Purple T30 / PurpleVK-public chain**, *not* proven to be a Banners-Turnip-built binary. This repository is the designated Turnip investigation home and has a reproducible Mesa build recipe. Conclusions from a generic Mesa source implementation are **conditional** on how it matches the user's installed T30 build.

## Primary field observations from FF7R diagnostic captures

User's S20+ SM-G986U1 / Adreno 650, running GameNative + FEX2610 + DXVK-SD865 2.7.1-derived WCP + Turnip T30 behind the PurpleVK wrapper:

- Repeated DXVK `vkAllocateMemory` failure-only probes show **`first_vkresult=-2` and `retry_vkresult=-2`**, **`recovered=0`**, in the failing buffer-pool path. Vulkan `-2` means **`VK_ERROR_OUT_OF_DEVICE_MEMORY`**. It is **not a DXVK budget-guard-only denial**.
- The last standard-pool run shows about **4008 MiB** allocated by DXVK when Turnip rejects fresh allocations **as small as 4 MiB**; the experimental DXVK 64/32-MiB pool path reclaimed **47 fully empty chunks / 1452 MiB cumulatively** but still failed near **4002 MiB** allocated. Original Vulkan reported heap after removing a user-chosen 2-GiB wrapper override was **7951 MiB**. `VK_EXT_memory_budget` typically advertised **~4.5–4.8 GiB**, exceeding DXVK-tracked allocations at failure. That is *reported budget*, not a guarantee that any BO size will be allocated.
- Failed allocation reports: `dedicated=0`, `flags=2` (`VK_MEMORY_ALLOCATE_DEVICE_ADDRESS_BIT`), `buffer_usage=137727`, heap 0 and memory types 0/1/2. These identify the failing **buffer-pool** path. The flags do **not** prove the device-address feature itself causes the native failure. The driver accepts other BDA allocations prior to the breakdown.
- The **2-GiB reported-heap case was explicitly user-configured** through GameNative Graphics → Max Device Memory = 2048, propagated as `WRAPPER_VMEM_MAX_SIZE` and not the original driver limit. Graphics max = 0 restored heap 7951 MiB without fixing actual driver OOM. Wine video-memory size 2048 and DXVK `dxgi.maxDeviceMemory=3072` are app-visible descriptions, not KGSL/Turnip allocation quotas.
- The captured Wine log lacks a kernel ioctl errno, kernel memory-map snapshot, or a native `tu_bo_init` stack. We **cannot** yet distinguish global Android memory pressure, GPU IOVA exhaustion, allocation-size/alignment rejection, kernel per-process memory policy, or Mesa internal errors. A repeatable ~4 GiB DXVK high-water mark is **suggestive but not proof** of a 32-bit GPU address-space cap.

Full run-by-run accounting belongs in DXVK:
[pool-on device result](https://github.com/Ragnarok93/dxvk-SD865/blob/feature/ff7r-sd865-architecture-20261011/docs/FF7R-SD865-POOL-EXPERIMENT-DEVICE-RESULT-20261012.md),
[pool-off control](https://github.com/Ragnarok93/dxvk-SD865/blob/feature/ff7r-sd865-architecture-20261011/docs/FF7R-SD865-UI-CONFIG-AND-POOL-OFF-CONTROL-20261012.md).

## What Banners-Turnip actually builds

[`README.md`](../../README.md) says the **Standard A6xx/A7xx** target uses Mesa `main`, without the A8xx-specific feature patches. Its [`build_turnip.sh`](../../build_turnip.sh) clones Mesa from `https://gitlab.freedesktop.org/mesa/mesa` and can pin `MESA_COMMIT`. [`mesa_hash.txt`](../../mesa_hash.txt) on branch A8xx currently records **`745709a000482a4a24c91faef5c5a40bd653a863`**, Mesa 26.3.0 as of 2026-10-11. The repo **does not check in the full Mesa source tree**; a driver-code finding below comes from a publicly accessible *comparable Mesa fork*, not a verified file at the exact pinned Mesa SHA.

The `patches/a8xx-winnative/0005` file and `TU_BO_ALLOC_NO_32B_ROLLOVER` workaround are **A8xx-specific / command-buffer issues**; the A650 standard build does not receive the A8xx patches. The two existing upstreamed KGSL fixes recorded here (zero-timeout poll and mixed sync merge, Mesa MR 44838) address **synchronization**, not demonstrated allocation-limit fixes. Do not misattribute FF7R allocation OOM to them. The private installed Mr Purple T30 build is **not automatically equivalent** to a freshly built Banners Standard driver merely because both are Turnip.

Mr Purple T30 public distribution is a packaged driver release, not a source checkout or source commit trace in this repo. The release notes say Mesa 26.3.0-devel / Vulkan 1.4.359, while Banners current README advertises Mesa 26.3.0 / Vulkan 1.4.363. Even if both support A650, **source/config/patch equivalence is unverified**. Native driver provenance must be recorded before attributing a root cause or testing a driver patch against the observed binary.

## Comparable Mesa Turnip source chain (not verified T30 provenance)

An accessible modern Mesa source mirror ([`DsoTsin/mesa-manet` `src/freedreno/vulkan/tu_device.cc`](https://github.com/DsoTsin/mesa-manet/blob/master/src/freedreno/vulkan/tu_device.cc), and [`tu_knl_kgsl.cc`](https://github.com/DsoTsin/mesa-manet/blob/master/src/freedreno/vulkan/tu_knl_kgsl.cc)) shows these relevant pathways. Verify against the exact pinned Mesa source before modifying Banners Standard builds:

1. `tu_GetPhysicalDeviceMemoryProperties2` exposes one Turnip heap with `heap.size`, native Vulkan memory types and `VK_EXT_memory_budget` fields. `tu_get_budget_memory` asks Mesa's system-memory budget helper for **90%** of shared-system-memory availability; `tu_get_system_heap_size` uses available system memory and caps against `physical_device->va_size`. Thus reported Vulkan budget is **not** the same thing as what a particular KGSL allocation can successfully map.
2. `tu_AllocateMemory` first checks `mem_heap_used > mem_heap->size`, returning `VK_ERROR_OUT_OF_DEVICE_MEMORY` if exceeded. The user's normal *reported* heap was ~7951 MiB while DXVK had ~4000 MiB allocated, so **this specific early heap-used guard is not demonstrated** as the limiter (and `mem_heap_used` != DXVK's tracked memory). The code then makes a `tu_bo_init` allocation via `_tu_init_memory` and handles failures.
3. For ordinary KGSL buffers, `kgsl_bo_init` calls `IOCTL_KGSL_GPUMEM_ALLOC_ID`. If the ioctl fails, the comparable source calls `vk_errorf(..., VK_ERROR_OUT_OF_DEVICE_MEMORY, "GPUMEM_ALLOC_ID failed (%s)", strerror(errno))`. **This collapses different kernel `errno` values into the same Vulkan -2 observed by DXVK**, so DXVK's exact `VkResult` still cannot say whether the kernel returned `ENOMEM`, `ENOSPC`, `EINVAL`, or another error.
4. Crucial BDA qualification: `tu_AllocateMemory` in this comparable version checks the **capture-replay** bit `VK_MEMORY_ALLOCATE_DEVICE_ADDRESS_CAPTURE_REPLAY_BIT` to set a special replayable BO flag. The ordinary bit `VK_MEMORY_ALLOCATE_DEVICE_ADDRESS_BIT` (DXVK `flags=2`) is **not that capture-replay bit**. Separately, `KGSL_MEMFLAGS_FORCE_32BIT` is assigned in `kgsl_bo_init` when `TU_BO_ALLOC_NO_32B_ROLLOVER` is present (command-stream/IB workaround). There is **no demonstrated direct relation** between the user's plain `flags=2` BDA Vulkan allocation and this 32-bit placement flag. Hypothesis that *all BDA allocations are forced into 32-bit GPU IOVA space* is **unsupported and should not guide a workaround** without exact-driver instrumentation.
5. Allocation may fail in `_tu_init_memory`, in external/DMABUF paths, or bookkeeping and still yield a generic driver result. Do not prematurely claim all observed `-2` statuses were from the one ioctl without tracing the path.

### Root cause hypotheses to discriminate

| Hypothesis | What would confirm it |
|---|---|
| KGSL ioctl rejects allocations due to physical/system pressure | Exact `IOCTL_KGSL_GPUMEM_ALLOC_ID` errno and before/after actual native used/available RAM; compare at matched FF7R scene |
| GPU VA / IOVA fragmentation or low-address aperture | Inspect native KGSL allocation/map failures, reported GPU address width and VMA or kernel logs; compare ordinary vs replayable BO flags |
| Wrapper corrupts memory reporting or allocation forwarding | Same raw physical device `VkPhysicalDeviceMemoryProperties2` vs wrapper at startup, per-call forwarded `VkMemoryAllocateInfo`, and exact native `VkResult` |
| Real aggregate Android memory pressure / process cap | Driver-side KGSL memory footprint and Android process/native memory readings before first OOM; compare with background apps reduced |
| Turnip internal heap accounting or size-limits | Log `mem_heap_used`, `heap.size`, requested allocation size and failure stage directly in `tu_AllocateMemory` |
| DXVK still retains live partially occupied pools | Already investigated in DXVK repo; requires live per-resource stats and is not itself a Turnip defect |

## Correct next driver-only experiment (not performed)

**Do not change driver default behavior yet.** Build from a **pinned Mesa SHA** (prefer the known Banners `745709a...` revision) and add an opt-in **failure-only** diagnostic with strict throttling to the Turnip KGSL code:
- At `tu_AllocateMemory` failure, report stage (`heap_used_guard` vs `bo_init` vs `tu_add_to_heap`), `VkResult`, request bytes, memory type and Vulkan flags, current `mem_heap_used`, heap size, and queryable budget.
- At KGSL `GPUMEM_ALLOC_ID` ioctl failure, report `errno` **numeric and symbolic**, original size/alignment, BO allocation flag mask (especially `NO_32B_ROLLOVER`, `REPLAYABLE`), whether client IOVA was requested, and GPU aperture if safely available. Log only failed calls, rate-limit to avoid the million-line captures. Do not dump kernel pointers, addresses of private allocations or potentially identifying process data.
- Ensure the output is visible through existing GameNative/Wine log export **without ADB or root** (driver stderr routing must be verified on Android). Optionally use a small wrapper layer to forward driver failure-only diagnostics to the app log if necessary; require positive capture evidence before promising this path.
- Bundle baseline and diagnostic standard A6xx `AdrenoTools` WCP/ZIP with unique profile identity and SHA256, then compare the **same game, same save, same DXVK** with/without extra Turnip diagnostics. The driver repo publishes standard AdrenoTools ZIPs, **not DXVK WCPs**; never substitute a DXVK package type for a Turnip driver.
- If the driver reports `KGSL_MEMFLAGS_FORCE_32BIT` only on internal IBs, preserve it; do not globally remove the workaround, spoof memory budget, or disable ordinary `VK_MEMORY_ALLOCATE_DEVICE_ADDRESS_BIT` requested by DXVK.

**Open provenance gate:** supply or recover the selected installed Mr Purple T30 driver's `meta.json`, binary SHA256 and/or Mesa commit/patch sources. Without that, an opt-in Banners driver build can provide an **A/B comparison**, but cannot be described as a patch directly applied to T30.

## Cross-repository notes

- [GameNative VRAM config propagation/quoting](https://github.com/Ragnarok93/GameNative/blob/research/ff7r-vram-config-20261012/docs/investigations/FF7R-SD865-VRAM-CONFIG-PROPAGATION-20261012.md)
- [DXVK real Vulkan OOM vs reported VRAM](https://github.com/Ragnarok93/dxvk-SD865/blob/feature/ff7r-sd865-architecture-20261011/docs/FF7R-SD865-DXGI-REPORTED-VRAM-VS-VULKAN-OOM-20261012.md)
- [FEX 2610 observation boundaries](https://github.com/Ragnarok93/FEX/blob/research/ff7r-memory-triage-20261012/docs/investigations/FF7R-SD865-FEX2610-NONCAUSAL-TRIAGE-20261012.md)
