# Snapdragon 865 / Adreno 650 Turnip performance profile

This is an opt-in build profile for measuring Turnip host-side compiler tuning on the Snapdragon 865. It keeps Mesa `main`, the same Turnip source patches, generic AArch64 ISA selection, and the existing O3 + ThinLTO flags. The only change is Clang's `-mtune=cortex-a77` scheduling preference; it does not use `-mcpu` or enable a new instruction set.

The standard Turnip build and generic performance build remain unchanged. The `sd865-cortex-a77` profile is built only when selected in the manual **Build Turnip (Perf 6xx/7xx)** workflow.

## FFVII Remake A/B acceptance

- Use the same Mesa commit, DXVK build, GameNative settings, device state, and scene for both profiles.
- Keep resolution, DRS state, shader cache state, refresh rate, and LSFG setting fixed.
- Run at least three matched trials per profile; record median and p95/p99 real-frame times, FPS, temperature, and any visual or stability issues.
- Keep the profile only if it improves repeatable frame pacing without visual regressions, increased OOM/crash incidence, or earlier thermal throttling.

No S20+ device measurement has been made yet, so this profile is an experiment and has no claimed speedup.
