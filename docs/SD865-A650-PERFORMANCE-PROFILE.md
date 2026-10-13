# Snapdragon 865 / Adreno 650 Turnip performance profile

This is an opt-in build profile for measuring Turnip host-side compiler tuning on the Snapdragon 865. It keeps Mesa `main`, the same Turnip source patches, generic AArch64 ISA selection, and the existing O3 + ThinLTO flags. The only change is Clang's `-mtune=cortex-a77` scheduling preference; it does not use `-mcpu` or enable a new instruction set.

The standard Turnip build and generic performance build remain unchanged. The `sd865-cortex-a77` profile is built only when selected in the manual **Build Turnip (Perf 6xx/7xx)** workflow.

## FFVII Remake A/B acceptance

- Use the same Mesa commit, DXVK build, GameNative settings, device state, and scene for both profiles.
- Keep resolution, DRS state, shader cache state, refresh rate, and LSFG setting fixed.
- Run at least three matched trials per profile; record median and p95/p99 real-frame times, FPS, temperature, and any visual or stability issues.
- Keep the profile only if it improves repeatable frame pacing without visual regressions, increased OOM/crash incidence, or earlier thermal throttling.

No S20+ device measurement has been made yet, so this profile is an experiment and has no claimed speedup.

## Isolated program-state candidate (2026-10-13)

`sd865-program-reference` adds the reviewed ARMSX2 host-side optimization to
`sd865-cortex-a77`: graphics binds borrow program state instead of copying the
large structure. No shaders, GMEM decisions, barriers or clocks change.
At command-buffer begin the pointer refers to zero state; a graphics bind
replaces it with the pipeline's state. Vulkan's pipeline lifetime rules apply.
Source attribution is in `patches/sd865/SOURCE`; fork review is recorded in
`SD865-FORK-SURVEY-20261013.md`.

The artifact workflow builds both profiles from exact Mesa commit
`76b9372c4e5d186f57d22d3a4f95dd1c5e04ece2`, with identical compiler flags and
Android API 29 target (compatible with the S20+ Android 13 environment).
The former script compiled at API 34 but labeled minimum API 28 and used a
duplicate platform SDK override; the SD865 pair now declares the actual
minimum API 29. A650 metadata says Vulkan 1.3; actual capability reporting
remains the unmodified upstream runtime query.

Each ZIP has the normal two AdrenoTools files. A sidecar `.manifest.json`
records full Mesa commit, profile, patch SHA256, driver SHA256, NDK and API.
Compare the two new artifacts against each other to isolate the program-state
change. An old A77 artifact built from floating main is not a matched control.

Keep LSFG and vkBasalt enabled in-container and LSFG FG disabled in-game;
keep textures Low, warm caches equally, and record real-frame p95/p99 plus
rendering/stability results in three matched trials. This candidate remains
experimental until those device gates pass.

## Isolated A650 pipeline backing candidate

`sd865-pipeline-512k` uses exactly `sd865-program-reference` plus a change to
A650's pipeline_suballoc default backing size, from 128 to 512 KiB. Other GPUs
and KGSL profiling buffers remain at 128 KiB. Both explicit GPU ID and chip-ID
fallback are tested. Patch attribution is in `patches/sd865/SOURCE`.

A native fake-BO test executes the actual pinned Mesa allocator: a 64 x 16 KiB
pipeline burst requires 8 backing BO allocations with the control and 2 with
the candidate (both allocate exactly 1 MiB). Alignment, non-overlapping content,
oversize allocations, map/BO failures and teardown are checked. This is host
allocation evidence only; kernel latency and FF7R frametimes remain unmeasured.
Larger backing BOs can retain up to 384 KiB extra tail in each current/cached BO.

Compare program-reference versus pipeline-512k with the same DXVK build;
compare A77 versus program-reference separately. The workflow compiles all
three from Mesa 76b9372, with identical NDK/API29/compiler settings and ABI
checks. Manifests additionally identify the A650 allocation size, whether
its patch was applied, and its patch hash. No new environment variables are
required. Leave LSFG/vkBasalt and all game settings fixed.
