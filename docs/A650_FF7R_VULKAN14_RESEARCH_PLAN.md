# A650 FF7R / Vulkan 1.4 Research Plan

Status: research only; no production behavior changed.
Target branch: feature/a650-unified-vulkan14-20261015
Target: Adreno 650 / Snapdragon 865, Android KGSL.

## Repository model
This repository downloads upstream Mesa and applies selected patches. It is a build-and-patch harness, not a full Turnip source fork. Userspace changes belong in narrowly scoped Mesa patches or upstream; GMEM_BASE and speed-bin fixes are kernel-side and require checking the target kernel.

## Audit findings
- The Vulkan 1.4 API-version probe changes the reported version only. It does not implement mandatory functionality or prove conformance. Keep it diagnostic-only.
- The current test for the probe validates source text, not device capabilities or Vulkan CTS.
- Existing experimental candidates include borrowed graphics program state, 512 KiB A650 pipeline suballocation, and forced SYSMEM. None should become default without correctness and device benchmarks.
- Borrowed program state requires a pipeline/command-buffer lifetime audit.
- Forced SYSMEM is a diagnostic control, not an assumed optimization.
- The common build script already asserts upstream KGSL zero-timeout polling and timestamp/sync-file merge fixes. Preserve those guards.
- Mesa's current device-property model associates shading-rate support with Gen4 rather than Gen3. Defer VRS on A650 unless authoritative evidence establishes a valid hardware path.

## Workstream A: upstream and kernel
1. Pin one full Mesa SHA for each A/B build.
2. Compare every local patch with that exact Mesa revision and record conflicts, upstream equivalents, generation guards, and test evidence.
3. Verify the target kernel's A650 MSM_PARAM_GMEM_BASE and speed-bin behavior.
4. Treat SQE firmware changes as a separate compatibility investigation; never replace firmware blindly.

## Workstream B: Vulkan 1.4
Build a matrix of applicable Vulkan 1.4 core features, properties, limits, and promoted extensions. For each, record current Mesa implementation, A650 hardware/kernel dependencies, missing work, and CTS coverage. Capture baseline device enumeration and run applicable CTS before changing advertised capabilities. Do not equate successful compilation or a changed apiVersion with conformance.

## Workstream C: FF7 Remake performance
Benchmark candidates with an immutable baseline and reproducible Mesa SHA:
1. Correctness and stability first: no corruption, hangs, device loss, invalid descriptors, or new crashes.
2. Audit borrowed program-state pointer lifetime, then measure command recording and pipeline-bind costs.
3. Compare 128 KiB vs 512 KiB pipeline suballocation; measure allocation count, CPU cost, fragmentation, peak memory, and frame-time variance.
4. Compare default render-mode autotuning against forced SYSMEM as a control.
5. Evaluate IR3 and shader-cache changes only with evidence of compile stalls or hot shader costs. ACO/LLVM are not drop-in IR3 optimizations.
6. Compare generic builds against O3 + ThinLTO + Cortex-A77 tuning while retaining generic AArch64 ISA.

## Telemetry and acceptance
Record Mesa SHA, patch hashes, builder commit, compiler/NDK, device/kernel/firmware, settings, thermal state, frame-time percentiles, CPU/GPU metrics where available, memory, shader stutter, visual correctness, and CTS results. Use paired A/B/A/B trials. Accept a win only if it exceeds run-to-run noise and introduces no correctness or stability regression.

## Initial disposition
| Candidate | Decision |
|---|---|
| GMEM_BASE / speed bins | Verify target kernel first |
| SQE firmware | Hold pending compatibility evidence |
| API-version probe | Diagnostic-only |
| Borrowed program state | Lifetime audit, then benchmark |
| 512 KiB suballocation | Optional A650 experiment |
| Forced SYSMEM | Diagnostic control only |
| Dynamic rendering / descriptors / sync2 | Audit existing support and CTS gaps first |
| VRS | Defer for A650 pending hardware evidence |
| IR3/cache improvements | Prioritize evidence-backed upstream changes |

## References
- Mesa Freedreno: https://docs.mesa3d.org/drivers/freedreno.html
- Vulkan 1.4 requirements: https://docs.vulkan.org/features/latest/features/proposals/VK_VERSION_1_4.html
- Vulkan core revisions: https://docs.vulkan.org/spec/latest/appendices/versions.html
- A650 GMEM_BASE discussion: https://lists.openwall.net/linux-kernel/2026/03/16/1325
- Mesa device properties: https://android.googlesource.com/platform/external/mesa3d/+/293f137d4debd4eadac97a7d4f60191f50bb2ca6/src/freedreno/common/freedreno_devices.py
