# A650 Synthetic Benchmark Implementation Status

Branch: `feature/a650-unified-vulkan14-20261015`
Date: 2026-10-15

## Implemented in this pass

- Added `.github/workflows/a650-synthetic-benchmark.yml`, separate from the existing reproducible build matrix. It pins one Mesa SHA for the run, runs profile-isolation and patch-applicability checks, compiles a fixed GLSL corpus repeatedly, and builds/packages all candidate profiles.
- Added `benchmarks/a650/run_shader_corpus.py` and four fixed shader fixtures. Outputs JSON, CSV, and Markdown with timing samples, source/output hashes, deterministic-output checks, and environment metadata.
- Added `benchmarks/a650/check_profiles.py` to guard that isolated candidate profiles don't accidentally enable each other's changes.
- Improved `build_turnip_perf.sh` manifests to include the exact list of applied patches, rather than relying on hashes for patches that may not have been applied.
- Added `sd865-pipeline-256k`, an isolated 256 KiB A650 pipeline suballocation candidate alongside the existing 512 KiB profile, and exposed it in both build matrices.

## Interpretation

The host shader corpus is intentionally a glslang frontend/toolchain proxy. It does **not** execute Turnip's IR3 compiler, does not depend on which Turnip profile is built, and cannot predict Adreno 650 FPS. Build duration and artifact size are likewise build/package metrics, not runtime performance.

The 256 KiB profile is a controlled source candidate intended for later A/B device testing against 128 KiB baseline and the user's current 512 KiB leader. No default profile was changed. No speculative change was made to shader semantics or Vulkan synchronization.

## Verification status

The files are committed to the target branch and their contents were fetched back for inspection. The new workflow is configured to run on relevant branch changes, including these additions. Until its resulting Actions run is inspected, do not claim that Mesa patch application, all eight candidate builds, or shader-corpus tests passed. No on-device test or Vulkan CTS run has been performed in this pass.
