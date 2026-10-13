# Turnip A650 continuation survey and candidate selection

Starting head: de02c45, branch feature/sd865-a650-perf-20261012.
Target: FF7R D3D11 / GameNative / Snapdragon 865 / Adreno 650 / Vulkan 1.3.
Prior survey: SD865-FORK-SURVEY-20261013.md. Do not repeat accepted/rejected work.

## Refreshed sources before implementation

| Source | Head / evidence | Decision |
| --- | --- | --- |
| Mesa main | existing pinned 76b9372 | Preserve exact tested source, feature gates, KGSL fixes and Android API29. |
| bmdhacks/armsx2-turnip | c7b815e7 | Existing borrowed program state retained; feedback-loop relaxation excluded. |
| Ghael-V/Turnip-Lemon-Ade | 99c98b93 | Inspect 83323558 (larger suballocators), 7dd6ac9a (GCM), 2690ee8d (bounded NIR optimization). Select only pipeline backing size, isolated from profiling and shader changes. Their A830/TOTK measurements are not A650/FF7R evidence. |
| WinNative-Emu/Drivers | c71f600a | No new applicable A650 patch; do not import A8xx retired-IB cache or clock policy. |
| StevenMXZ/Adreno-Tools-Drivers | b3b32ad3 | Packaging/patch lineage also carried by Banners; preserve existing common fixes, not gen8 capabilities. |
| MrPurple666/freedreno-CI | ce36aac7 | Historic packaging, no current T30 source provenance. |
| Tranquility6789/Turnip-A650-Patched-Drivers | 7269dd98 | Binary-only / explicitly excludes Winlator. |
| AlexSanz0902/turnip-sd865-z | ed308405 | SD865/Eden-specific compression/filter/direct-render changes; README explicitly excludes Windows layers. No import. |
| RetroidPocketFive/RP5_Turnip_Eden | bbc8e729 | Experimental 24.3 baseline, no implementation patch in published patch directories. |
| mercurious/etk-turnip-gtk | c4f6da99 | Linux MSM/PS3 gears, barrier alternatives, forged query results and kernel coupling excluded. Forced-double-wave RA cap patch 0009 is a separate correctness candidate; no evidence current DXVK FF7R requests that wave mode, so defer. |
| SuperBrowserProject/mesa_turnip_a618_optimized | c05fd0ea | Build flags target A618, not an A650-specific performance implementation. |
| Florkaa282810/mesa-turnip-optimized | 74185dcb | Early Winlator build packaging; no isolated measured change to transplant. |
| ff7161987-cmd/mesa-turnip-optimized | 42db22ae | Build-time sed edits for A660/GMEM use silent fallback and lack FF7R evidence; excluded. |
| Shinigami-MV/Turnip-MV-F6 | README | A735 O3 packaging; no A650 source fix. |
| Grima04/mesa-turnip-kgsl | 50ed40fb | Historic KGSL lineage; current Mesa already implements KGSL backend. |
| Heasterian/mesa-turnip-kgsl | 13d4d5a8 | Historic device/pipeline port; not a current A650 performance candidate. |
| lfdevs/mesa-for-android-container | 401198fb | Linux/container integration, not Android GameNative driver replacement. |
| Droid-VM/turnip | 486c9735 | Timestamp polling replaces blocking waits; do not transplant without scheduling/timeout evidence. |
| fish4terrisa-MSDSM/mesa-kgsl-25.2.5 | 9ca14a37 | Deferred-submit merge and timestamp modifications change synchronization; excluded from this isolated allocation trial. |
| rtiangha/Mesa-Turnip-Builder | 0a5d4026 | Stable Mesa/NDK packaging; no independent A650 FF7R optimization identified. |
| Thepffffff/blue-turnip | 2d3cce37 | Packaging alternative, no demonstrated A650 implementation benefit. |
| leegao/mesa-wrapper-CI | 05bca959 | Separate wrapper integration; preserve current wrapper/layer stack for attribution. |
| K11MCH1, Weab-chan, NightHammer1000 | refreshed histories; prior source audit | No source-backed A650 storage8 implementation; do not spoof Vulkan1.4. |

Discovery: public repository searches for Turnip A650, optimized Mesa, KGSL,
Adreno6xx and StevenMXZ, plus source/commit inspections and prior ledger.
Coverage is the relevant identified public forks; private/unindexed forks remain unknown.

## Selected isolated candidate

PERF_PROFILE=sd865-pipeline-512k: same program-reference patch, same pinned Mesa,
A77/O3/ThinLTO/API29 and common KGSL changes. Only pipeline_suballoc default size
changes 128KiB to 512KiB. Keep kgsl_profiling_suballoc at 128KiB to avoid confounding.
No shader changes, synchronization changes, clock controls or Vulkan feature changes.

Hypothesis: pipeline bursts require fewer backing BO allocations and kernel calls.
Validate using the actual Mesa suballocator with a fake BO backend: identical aligned
placements, content, oversize allocations and failure behavior; count backing BO calls
and allocation sizes on identical bursts. This proves an allocation effect only.
Potential cost: larger partial backing BOs and memory retention (up to 384KiB extra
unused tail per current/cached BO); hardware timing and memory-pressure acceptance
remain pending. This is distinct from DXVK's prior 64MiB memory chunk experiment.

## Progress

- [x] Recover previous source/build/device checkpoints.
- [x] Refresh fork survey before changing code.
- [ ] Wait for DXVK PE/WCP validation, then implement Turnip candidate.
- [ ] Apply patch without fuzz and execute suballocator regression.
- [ ] Compile matched control/candidate driver ZIPs and validate ABI/provenance.
- [ ] S20+ FF7R median/p95/p99 and memory-pressure acceptance.
