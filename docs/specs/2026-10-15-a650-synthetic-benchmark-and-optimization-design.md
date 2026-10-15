# A650 Synthetic Benchmark Suite and Next Optimization Pass

Date: 2026-10-15
Target branch: `feature/a650-unified-vulkan14-20261015`
Target: Mesa Turnip / Adreno 650 / Snapdragon 865 / Android KGSL
Execution environment: GitHub-hosted Actions runners only

## Goals

1. Add a separate GitHub Actions workflow that builds or consumes the same pinned Mesa/profile matrix and runs reproducible host-side synthetic tests before device installation.
2. Use the warm-cache observation from FFVII Remake to prioritize shader compiler and cache-related investigation without claiming host metrics predict Adreno FPS.
3. Select the next driver changes only after auditing upstream Mesa history and source behavior at the pinned Mesa SHA.
4. Preserve a known-good generic profile and the user's current leading `sd865-pipeline-512k` profile as comparison controls.

## Benchmark architecture

- Keep `.github/workflows/a650-reproducible-matrix.yml` unchanged in purpose: compile and package each candidate against one resolved Mesa SHA.
- Add a separate synthetic benchmark workflow with manual dispatch and relevant path triggers.
- Resolve Mesa SHA once per run and pass it to all jobs; record branch SHA, Mesa SHA, patch hashes, NDK/compiler versions, runner image, workload revision, and benchmark parameters.
- Use only tests that actually execute on the hosted runner. Initial workloads should include a deterministic fixed shader corpus compiled with the available Mesa/IR3 compiler tooling, reporting successful shader count, elapsed time, throughput, per-shader latency distribution, output hashes, and failures.
- Where practical and supported by the source/build, add CPU-side microbenchmarks for shader IR transformations or pipeline-state setup. Do not call these GPU execution benchmarks.
- Do not report GPU utilization, Adreno frame time, KGSL behavior, Vulkan device conformance, or FFVII Remake FPS from hosted runners.
- Run multiple repetitions, report median and spread (and p95 only where sample size supports it), and avoid pass/fail thresholds based on tiny noisy differences. Correctness/build failures are hard failures; performance regressions are reported with explicit uncertainty.

## Driver optimization investigation

- Review the pinned Mesa revision and relevant upstream changes after/before it for shader compilation, pipeline-cache behavior, IR3 optimization, command-state setup, and allocation hot paths.
- Prefer minimal upstream-backed backports with clear generation guards and source-level tests.
- Treat pipeline-cache warm-up as a diagnostic hypothesis, not proof. Separate cache-cold and cache-warm workloads where the harness can reliably control cache state.
- Do not add a speculative driver behavior change solely because it improves a host-side proxy score.
- Keep the borrowed graphics-program-state patch experimental until command-buffer and pipeline lifetime paths are audited.
- Keep forced SYSMEM as a diagnostic control. Keep 512 KiB pipeline suballocation as the current comparison candidate; do not silently combine it with other changes.
- Preserve Vulkan metadata honesty: API-version reporting, successful compilation, and synthetic tests do not establish Vulkan conformance.

## Outputs

- Per-profile JSON results and a combined CSV.
- Markdown summary comparing profiles to `generic` and `sd865-pipeline-512k`.
- Workload sources, checksums, exact commands, and logs as downloadable Actions artifacts.
- Clear labels distinguishing compile-time/host-side proxy measurements from device-only performance measurements.
- A driver-change report identifying each candidate patch, upstream provenance, rationale, correctness checks, and remaining device-validation requirements.

## Validation and acceptance

- Validate workflow YAML and shell/Python syntax.
- Run deterministic benchmark self-tests using a small fixture corpus.
- Run the Actions workflow on the target branch and inspect artifacts and logs.
- Require repeatable correctness results and no shader-output mismatch before comparing timing.
- Accept a source optimization for device testing only when it is semantically justified and survives relevant source/build checks. A host benchmark improvement alone is insufficient to claim an Adreno performance win.
- After the next optimization batch builds successfully, provide the artifacts and exact A/B device-test plan. Do not claim runtime GPU performance without an actual device run.

## Explicit non-goals

- No self-hosted runner requirement.
- No simulated Adreno GPU benchmark or fabricated device telemetry.
- No automatic publication of release drivers.
- No Vulkan 1.4 conformance claim from metadata or synthetic results.
- No changes to the known-good baseline unless evidence justifies them.
