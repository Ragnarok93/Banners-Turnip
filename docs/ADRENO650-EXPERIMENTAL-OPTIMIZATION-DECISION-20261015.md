# Adreno 650 optimization disposition — 2026-10-15

This is a source-risk triage, not a performance result. No new unified-branch
build or on-device A/B run has yet validated these candidates.

## Keep in the experimental branch

| Candidate | Decision | Reason / gate |
|---|---|---|
| Failure-only KGSL allocation instrumentation | Keep | Opt-in, capped logging, no allocation behavior/caps changed. Use only in diagnostic builds; check overhead and log privacy before shipping. |
| Program-state reference instead of copying state | Keep as opt-in candidate | Potential CPU work and command-recording reduction. Pointer lifetime / reset / secondary command buffer correctness must pass build, stress tests and Vulkan CTS before promotion. |
| 512 KiB A650 pipeline backing suballocation | Keep as opt-in candidate | Plausible reduction in allocation/suballocator overhead; may increase retained memory and worsen FF7R pressure. Compare allocation count, peak GPU/host memory, OOMs, frame-time distributions. |
| Cortex-A77 tuning, O3 and ThinLTO | Keep as build-only candidate | Appropriate for Kryo 585's A77 cores and safe at the ISA level as currently configured, but does not prove a runtime win; compare against the generic build and retain only with repeated measurements. |

## Do not promote by default

| Candidate | Decision | Reason |
|---|---|---|
| Forced SYSMEM rendering on A650 | Keep only as a separate screening artifact | It disables the normal GMEM/autotune choice and can raise external-memory bandwidth or hurt geometry/fragment throughput. No device capture demonstrates it wins; never merge into the generic path on build success alone. |
| Any allocation-pool policy inferred from OOM logs | Diagnostics only until evidence | 10,403/64,192 long GPU-completion CPU waits and an OOM are evidence of pressure, not proof that a particular pool-size or submission policy is the cause. Do not tune pool policy without matched before/after captures. |
| Upstream KGSL zero-timeout polling fix | Do not duplicate | The upstream fix is already present in the chosen Mesa lineage; duplicate local patch risks drift. Keep the source assertion/check, not a second implementation. |

## A/B protocol

Use one pinned Mesa SHA and identical Android API, NDK, game settings, caches and driver install path. Record driver and APK hashes. Test baseline, then each candidate alone, then only promising combinations. Capture median/p95/p99 frame times, hitch count, CPU time, GPU time, peak memory, KGSL allocation failures and reproducible OOM outcome. Repeat each arm at least three times after warm-up. Reject wins smaller than run-to-run noise or accompanied by worse tail latency, memory pressure, rendering correctness or stability.

The SYSMEM, program-reference and 512 KiB options are independent candidates and should not be conflated. The API-version probe is also separate from performance tuning.
