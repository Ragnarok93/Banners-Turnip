# FF7R SD865 budget-aware Turnip experiment

## Goal

Test whether an earlier Vulkan memory-budget warning reduces FFVII Remake allocation pressure on Snapdragon 865 / Adreno 650 without changing the rendering path or shader compiler behavior.

This is a separate, opt-in profile: `sd865-ff7r-budget75-512k`. The existing `generic`, `sd865-pipeline-256k`, `sd865-pipeline-512k`, and `sd865-memory-audit` profiles remain unchanged.

## Evidence and rationale

The October 16 GameNative capture did not reproduce OOM and contained no `TU_KGSL_MEM` events, so it cannot demonstrate that the BO cleanup or telemetry patch fixes FF7R's earlier OOMs. The previous capture showed 128 MiB / 256 MiB requests failing around 3.4–3.7 GiB reported DXVK allocation totals, while DXVK's empty-pool reclaim pass recovered zero bytes. This does not prove a fixed 4 GiB hardware limit or a specific KGSL failure stage.

Upstream Turnip currently calculates the reported budget as the lesser of the heap size and `heap_used + 90% of available system memory`, additionally bounded by the GPU VA size when known. Upstream's system heap sizing separately limits the advertised heap to half of RAM at 4 GiB or less, otherwise three quarters of RAM, then clamps to GPU VA size. See `tu_get_system_heap_size()` and `tu_get_budget_memory()` in `src/freedreno/vulkan/tu_device.cc`.

The candidate changes only the runtime available-memory multiplier from 90% to 75% for this profile. The intent is to notify budget-aware clients earlier, potentially prompting earlier resource trimming. This is a hypothesis, not a guaranteed allocator fix: it does not free memory, change real allocation limits, or force DXVK to reclaim anything. If DXVK does not respond to the reported budget, or if it already has no reclaimable resources, this may be neutral or harmful. It therefore stays experimental.

## Profile contents

- Mesa source is pinned to `dc671cbf0f76194c72b621205b6cc84e1c914fad` for reproducibility.
- Uses the same 512 KiB Adreno 650 pipeline suballocator size as `sd865-pipeline-512k`, through a profile-specific minimal-context patch because the existing `0002` patch does not apply to the pinned Mesa snapshot.
- Applies `patches/sd865/0008-tu-ff7r-pipeline-suballoc-512k.patch` and `patches/sd865/0007-tu-ff7r-conservative-memory-budget.patch`.
- Does not enable borrowed program state, forced SYSMEM, BO lifecycle warning logs, new allocation retries, or changes to DXVK.
- Existing KGSL cleanup and audit profiles are not modified.

## External source/fork review

- Mesa's upstream Turnip implementation is the baseline; its UMA heap and budget policy is documented in `tu_device.cc`. The upstream Freedreno documentation describes Adreno as UMA and distinguishes GMEM tile storage from system-memory rendering: https://docs.mesa3d.org/drivers/freedreno.html
- Upstream commit [`1e1d8931c7de6316b2c7b4c2c20e370079c23402`](https://github.com/mirror/mesa/commit/1e1d8931c7de6316b2c7b4c2c20e370079c23402) reduces memory advertised by the Gallium Freedreno screen to match the closed driver and avoid over-allocation in OpenCL CTS. That change is in the Gallium path, not Turnip's Vulkan budget path, so it is not copied directly; it supports the general principle of avoiding overly optimistic memory reporting, not a claim that the same patch fixes Vulkan OOM.
- [Turnip SD865 Z](https://github.com/AlexSanz0902/turnip-sd865-z) claims 15–35% gains for Switch emulation on one Adreno 650 device, but its README explicitly says it was not designed or verified for Windows translation layers such as GameNative/Winlator. Its game-specific filtering/render-target modifications are therefore excluded from this FF7R build rather than blindly ported.

## Validation plan

1. CI must apply the patch cleanly to the pinned Mesa source and build the Android KGSL driver.
2. Install this profile alongside the unchanged 512 KiB control.
3. Repeat the same FF7R scene/replay, resolution, GameNative version, thermal state, LSFG state, and shader-cache state for A/B/A/B runs.
4. Capture DXVK allocation totals, budget, requested sizes, reclaim results, and frame-time p50/p95/p99 in GameNative. Redact command-line secrets before sharing.
5. Keep the candidate only if it reduces OOMs or peak allocations without worse p95/p99 frame times, visual regressions, hangs, or device loss. Otherwise discard the budget patch.

## Expected interpretation

A lower reported budget with unchanged real allocation totals but earlier successful trimming supports the hypothesis. A lower budget followed by earlier allocation failure, unchanged reclaim counters, or worse frame pacing rejects it. No OOM in a short run is not sufficient proof; compare identical workloads and capture durations.
