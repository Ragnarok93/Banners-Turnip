# FF7R A650 measured-optimization gate — 2026-10-13

Target: Galaxy S20+ Snapdragon 865 / Adreno 650 running FFVII Remake D3D11 in GameNative; Vulkan 1.3 stays mandatory. Keep LSFG and vkBasalt enabled in the container with LSFG frame generation OFF in-game, and texture quality Low.

## Fork review and current state

Reviewed prior pinned fork survey [SD865-FORK-SURVEY-CONTINUATION-20261013.md] plus updated Mesa/Turnip ecosystem: The412Banner/Piperella Turnip, WinNative/termux-glibc driver profiles, Ghael-V/Turnip-Lemon-Ade, bmdhacks/armsx2-turnip, Droid-VM legacy KGSL, and historic dedicated A650 forks. No validated *new* A650 FF7R improvement was identified that warrants stacking unmeasured synchronization or shader changes on current candidate builds. In particular, avoid forced KGSL power locks, duplicate upstream KGSL patches, unsafe GMEM mode forcing, or A8xx-only edits.

**Keep three existing, independently compiled candidate profiles untouched:**

| Profile | Relative change | Existing host validation | S20+ frame-time result |
| --- | --- | --- | --- |
| sd865-cortex-a77 | Cortex-A77 / O3 / ThinLTO build control | Builds/ABI checked | Pending |
| sd865-program-reference | Borrow program state rather than copying | Builds and reference tests pass | Pending |
| sd865-pipeline-512k | A650 pipeline backing buffers 128KiB -> 512KiB | 64 x 16KiB allocations: 8 -> 2 backing BOs; allocation bytes same on fake backend | Pending |

Source Mesa SHA: `76b9372c4e5d186f57d22d3a4f95dd1c5e04ece2`. Do not substitute a floating-main or Mr. Purple build when evaluating these isolated patches.

## Companion DXVK instrumentation

DXVK-SD865 branch `feature/ff7r-sd865-architecture-20261011`, checkpoint `a184c65ee0be42c6d9a078aae4152d013f8edc97` implements:

- `DXVK_FF7R_METRICS=1` opt-in D3D11 DXGI Present completion-interval windows (256 intervals; mean, p50/p95/p99/max). **CPU-side Present cadence is not GPU execution / scanout frame time.**
- Background shader-library / optimized-pipeline worker CPU compilation timings and 10/33ms counts.
- ZIP analyzer `python3 tools/ff7r_perf_compare.py baseline.zip candidate.zip` in DXVK repo. At least three windows per trial, then at least three independent matched trials per driver. Script reports medians of per-window percentile summaries, not globally pooled percentiles.
- Vulkan requirements/features, shader compiler, GMEM/tiler routing, clocks and Turnip worker source paths are unaffected by this instrumentation.

Enable `DXVK_LOG_LEVEL=info` and `DXVK_FF7R_METRICS=1` in GameNative, retain all other environment, FEX, LSFG/vkBasalt, resolution, DRS, caches, save point and thermal conditions across trials. Match the DXVK WCP for each Turnip comparison.

## What results would justify optimization work?

1. If the A77 -> program-reference transition improves p95/p99 repeatably with no texture/cutscene issues, retain that optimization. A regression warrants a controlled rollback.
2. If program-reference -> pipeline-512k improves frame pacing **and** does not raise allocation/OOM risk, retain larger A650 backing BOs. If memory pressure worsens, evaluate an intermediate allocation size only after measurement.
3. If DXVK shader-worker compilation aligns with frame stalls, tune the same DXVK binary's existing compiler-thread configuration in matched trials (e.g. four vs eight workers), then instrument synchronous pipeline creation if background worker statistics are insufficient.
4. Collect game-independent frame statistics or actual Vulkan GPU timing before asserting GPU throughput improvement. Compare the existing GPLAsync baseline using a source-independent frame-timing capture because it lacks our opt-in instrumentation.

## Gates and current results

- [x] Turnip prior fork surveys, profile implementations, allocation unit tests and three matched NDK/API29 build profiles (see earlier validation documents).
- [x] Companion DXVK instrumentation and portable host percentile/parser tests checkpointed.
- [ ] Companion DXVK PE cross-build / WCP workflow success for exact `a184c65` source revision.
- [ ] S20+ three-trial matched scene frame pacing, image correctness, temperature and RAM/OOM validation.
- [ ] Any additional shader/barrier/GMEM/clock change: deferred until above data justifies its risk.

This document checkpoints testing decisions, not a new Turnip binary optimization or a measured FPS win.