# Snapdragon 865 / Adreno 650 memory-pressure optimization

Target branch: `feature/sd865-memory-pressure-20261016`
Base: `feature/a650-unified-vulkan14-20261015`
Control: `sd865-pipeline-512k`; comparison: `generic`
Device system RAM: 12 GiB (shared UMA; not a 12 GiB GPU allocation budget).

## Scope and safety

This work targets Turnip/Freedreno and KGSL memory behavior. Keep DXVK/game changes out of this branch. Keep the existing pipeline slab profile unchanged so memory changes can be compared independently. Do not force GMEM, invent lazy allocation for ordinary Vulkan images, move live allocations, or enable render-target aliasing in the first pass.

## Findings that must be measured, not assumed

- A 12 GiB physical RAM total is not the GPU's available budget. Android and other processes share the same DRAM.
- An OOM near 3.7 GiB is evidence of a limit/pressure point, not proof of a universal 4 GiB A650 limit or physical-contiguity failure.
- GMEM is on-chip tile storage. Selecting GMEM does not generally eliminate the backing allocations required by Vulkan images.
- Vulkan drivers cannot transparently split an arbitrary VkDeviceMemory allocation without changing binding/resource semantics.
- Lazy allocation is not a generic driver-side switch: it requires supported memory types and valid transient-attachment usage/lifetimes.

## Implementation sequence

### 1. Establish a reproducible baseline

Use the same game build, driver, resolution, scene/replay, shader-cache state, and capture window. Record:
- driver/Mesa commit and Turnip profile;
- process RSS/PSS and system available memory before and during the run;
- Vulkan allocation request size, result, and allocation type/path where available;
- KGSL/BO allocation/free events and current/peak bytes where they can be tracked accurately;
- DXVK allocation logs and exact failure timestamp;
- frame-time p50/p95/p99, crash/hang, and visual result.

Do not call allocator-requested bytes "physical VRAM used": UMA, imported dma-bufs, kernel accounting, and other processes can make these values differ.

### 2. Audit allocation lifetime and accounting

Inspect the exact Mesa commit resolved by the build. Trace all KGSL BO allocation paths (DMA-heap, ION, imported dma-buf), BO destruction, fd ownership, and every error unwind. Check for leaked dma-buf fds/BO references before adding heuristics. Counters must not double-count imports or count memory as freed before its last owner releases it.

### 3. Bounded, safe cache reclamation

Only after the audit identifies reclaimable caches, add an OOM-triggered, bounded reclaim-and-retry path where it is safe:
- reclaim only entries known to be unused and not referenced by in-flight submissions;
- preserve normal behavior if no reclaimable bytes exist;
- retry at most once per failed allocation to avoid retry loops;
- report original failure, reclaimed bytes, retry result, and cache class;
- never free live pipeline state, descriptors, or BOs merely because an allocation failed.

Pipeline slab cap/eviction is not approved until the actual slab owner/lifetime and memory domain are confirmed. The 512 KiB performance control remains unchanged.

### 4. Budget reporting

Audit current `VK_EXT_memory_budget` support and heap reporting. If implemented, verify that the budget is conservative and reflects the driver's observable constraints; do not report all 12 GiB as device-local free memory. Keep any new logging behind an opt-in debug flag and avoid per-frame log spam.

### 5. Separate experiments

Transient/lazy attachments, descriptor pool tuning, GMEM heuristics, texture transcoding, and aliasing are separate experiments. Each needs its own patch and correctness/performance evidence. Do not bundle them with allocator telemetry or cache reclamation.

## Acceptance criteria

- Android/Turnip build succeeds against the pinned Mesa commit with no fuzzed or silently skipped patches.
- Identical replay baseline shows lower peak driver-owned allocation or a successful recovery from a previously failing allocation.
- No regression in p95/p99 frame time beyond run-to-run noise.
- No validation errors, rendering corruption, GPU hangs, or use-after-free.
- OOM telemetry differentiates the original allocation failure from a successful or failed retry.
- Publish a build only after CI passes; device performance and visual correctness remain unverified until tested on the Snapdragon 865.

## Current status

Planning/branch setup only. No driver source patch or performance claim is included until the source-level lifetime audit and build verification are complete.
