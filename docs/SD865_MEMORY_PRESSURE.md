# Snapdragon 865 / Adreno 650 memory-pressure optimization

Target branch: `feature/sd865-memory-pressure-20261016`
Base: `feature/a650-unified-vulkan14-20261015`
Performance control: `sd865-pipeline-512k`; comparison: `sd865-pipeline-256k`
Memory-fix profile: `sd865-memory-audit`
Pinned Mesa source for the memory-fix profile: `dc671cbf0f76194c72b621205b6cc84e1c914fad` (upstream Mesa mirror snapshot, 2026-10-08).
Device system RAM: 12 GiB shared UMA; this is not a 12 GiB GPU allocation budget.

## Exact source found

The build script normally clones Mesa `main` at build time, so builds made on different days could silently use different driver code. For the memory-fix profile, the build now checks out the exact source commit above before applying patches. The commit is an upstream Mesa snapshot whose history includes the KGSL syncobj/wait fixes required by `patches/common/apply_common.sh` and the earlier dma-buf allocation-fd leak fix.

Source references:
- [Pinned upstream Mesa commit](https://chromium.googlesource.com/external/gitlab.freedesktop.org/mesa/mesa/+/dc671cbf0f76194c72b621205b6cc84e1c914fad)
- [KGSL backend at that commit](https://chromium.googlesource.com/external/gitlab.freedesktop.org/mesa/mesa/+/dc671cbf0f76194c72b621205b6cc84e1c914fad/src/freedreno/vulkan/tu_knl_kgsl.cc)
- [Upstream fix for internally allocated dma-buf FD leaks](https://chromium.googlesource.com/external/gitlab.freedesktop.org/mesa/mesa/+/9f955af118d0cdabae776d08e36f99f7aa92317b)

The dma-buf FD leak is already fixed upstream in the pinned tree. That leak affects internally allocated *shareable/exportable* BOs, not ordinary offscreen textures, so it should not be presented as the proven cause of the reported DXVK texture-memory failure.

## Implemented source change

`patches/sd865/0005-tu-kgsl-sparse-bind-oom-cleanup.patch` is applied only by the new `sd865-memory-audit` profile. It makes two narrow changes:

1. **Corrects heap-budget initialization order.** The KGSL path previously calculated `device->heap.size` before querying `KGSL_PROP_GPU_VA64_SIZE`. But `tu_get_system_heap_size()` clamps the heap to `physical_device->va_size` when that value is known. Querying it first lets Vulkan see the effective GPU VA-size cap when the kernel reports one. This is a budget-reporting correction, not proof that the SD865 has a 4 GB VA limit; the device property must be measured.
2. Adds the requested byte count to KGSL backing BO allocation, dma-heap allocation, and sparse-bind failure messages. This helps identify which stage failed and how much memory was requested.
3. Fixes a cleanup gap in `kgsl_bo_init()`: after the kernel BO is allocated, a failed `IOCTL_KGSL_GPUMEM_BIND_RANGES` previously returned an error without freeing that BO. The patch frees it on this failure path and moves the BO-allocation RMV event before mapping so failure cleanup has a matching destroy event. The replayable mapping path remains delegated to `kgsl_bo_user_map()`, which already cleans up its own failures.

This combines accurate heap-budget reporting, a failure-path leak fix, and event-driven error diagnostics; it is not a general cache-reclamation mechanism. If KGSL reports a small VA size, the heap cap may explain why applications attempt allocations beyond the addressable range. If it reports a much larger range, the heap-order fix will not explain the 3.4–3.7 GiB failures. The captured failure stage and queried VA size will decide which path matters.

## Scope and safety

- Keep DXVK/game changes out of this branch.
- Keep the 512 KiB pipeline profile unchanged as the control.
- Do not force GMEM, invent lazy allocation for ordinary Vulkan images, move live allocations, or enable render-target aliasing in this pass.
- Do not retry failed allocations or reclaim live pipeline state based only on an OOM.
- The new profile is pinned independently of the existing pipeline comparison profiles.

## What the error evidence means

- 12 GiB of physical RAM is shared by Android, the game, the driver, and other processes; it is not a GPU-only budget.
- An OOM near 3.7 GiB is evidence of a pressure point, not proof of a universal 4 GiB A650 limit or physical-contiguity failure.
- KGSL failures from `GPUMEM_ALLOC_ID`, dma-heap allocation, mapping, and sparse VA binding are different failure stages and should not be treated as interchangeable.
- GMEM is on-chip tile storage; selecting GMEM does not generally eliminate backing allocations for Vulkan images.
- Vulkan cannot transparently split arbitrary `VkDeviceMemory` allocations without changing resource/binding semantics.

## Next measurement step

Build `sd865-memory-audit` from the perf workflow, install it as a separate test build, and repeat the same game/replay, resolution, shader-cache state, and capture window as the control. Capture the new failure-stage/byte-count messages alongside DXVK allocation logs, process RSS/PSS, Android available memory, and frame-time p50/p95/p99. Compare against `sd865-pipeline-512k` and `sd865-pipeline-256k` separately.

If the failed stage is consistently `GPUMEM_ALLOC_ID` for ordinary BO allocations, the sparse-bind cleanup is not the relevant fix; the next step is to investigate heap accounting, the kernel's KGSL allocation limit, and live BO lifetimes. Only add cache reclamation after identifying a specific cache with a safe lifetime contract.

## Acceptance criteria

- Patch applies cleanly to the pinned Mesa SHA; no fuzzy or silently skipped patches.
- Android/Turnip build succeeds against that exact SHA.
- The error log includes allocation stage and requested size.
- Identical replay demonstrates either lower peak driver-owned allocation or recovery from a previously failing allocation.
- No validation errors, rendering corruption, GPU hangs, use-after-free, or p95/p99 regression beyond run-to-run noise.

## Current status

- Branch and source-audit plan committed.
- Exact upstream Mesa source SHA identified and pinned for the new memory-fix profile.
- KGSL failure-size diagnostics and sparse-bind BO cleanup patch added.
- Build and patch-application checks have **not yet run** in this environment. No performance or device-correctness claim is made until CI and Snapdragon 865 testing complete.
