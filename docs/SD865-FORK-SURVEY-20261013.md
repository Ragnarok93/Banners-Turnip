# A650 Turnip fork survey — 2026-10-13

Target: FF7 Remake in GameNative, Vulkan 1.3, Snapdragon 865 / Adreno 650. Driver changes follow completion of the independent DXVK backport slice (DXVK checkpoint 340eb6a; 49 tests pass; cross-build CI running).

Inspected before selecting the Turnip implementation:

| Source | Finding / disposition |
| --- | --- |
| Mesa main 76b9372c4e5d186f57d22d3a4f95dd1c5e04ece2 | Current KGSL polling and mixed-fence fixes already present. A650 retains its existing feature gates. Current graphics binds still copy tu_program_state. |
| bmdhacks/armsx2-turnip c7b815e711a4ef3b5b93981cfefcc7ba1faeea8c | Identified independent host optimization: reference bound program state rather than copy ~10KB on each graphics bind. Selected for isolated opt-in candidate. Exclude its weaker feedback-loop coherency patch: PS2 scene validation does not establish FF7R correctness. |
| WinNative-Emu/Drivers c71f600a2977a141f21a922c9ed2e14fb09b13d3 | Review perf/balanced scripts. Autotuner thresholds and forced KGSL power constraints combine workload/clock changes; do not import without matched FF7R evidence. Its retired A8xx IB cache is outside A650 scope and was dropped by Banners. |
| Ghael-V/Turnip-Lemon-Ade 99c98b930d6ce9835868e9dd6472fd30eea26151 | Inspect source and features; float-atomic lowering and gen8 work do not justify changing A650 shader capabilities for this game. Still copies program state. |
| MrPurple666/freedreno-CI alpha | Public build script is old upstream-main packaging, not current T30 source. purple-turnip repository is release-only. Cannot infer T30 internals from the historic script. |
| Tranquility6789/Turnip-A650-Patched-Drivers | Current README explicitly excludes Winlator/PC emulators; binary extraction, no reviewable implementation. Reject for GameNative. |
| K11MCH1/AdrenoToolsDrivers / Weab-chan builds / NightHammer1000/TurnipMagisk | Prior source/feature survey in dxvk-SD865 docs/FF7R-A650-TURNIP-DXVK311-COMPATIBILITY-SURVEY.md remains relevant: do not force storage8 or Vulkan 1.4 reporting. |

Scope: identified relevant public forks, not all possible private/unindexed forks. No FF7R speedup claimed from their emulator results. Selected candidate must preserve command-stream values, pipeline lifetime rules, zero-program initialization and every program-state reader. Apply only to a separately named SD865 profile, with identical pinned Mesa and A77 flags for both control and candidate. Device acceptance remains pending; keep LSFG/vkBasalt on in-container and LSFG FG off in-game, textures Low.
