# FFVII Remake — Adreno 650 KGSL ENOMEM and Android memory-pressure snapshots (2026-10-12)

**Subsystem owner:** `Ragnarok93/Banners-Turnip`; date of user's uploaded observation 2026-10-12 01:57 UTC. Files supplied in chat: `ff7remake__d3d11.log` (153 lines), `ff7remake__dxgi.log` (4 lines), `wine_debug.log.txt` (1,212 lines), and a separate **historical** `pluvia_crash_2026-10-06_06-51-57.txt`. The source logs are intentionally not committed. This report supersedes the previous open question of whether the new pressure probe reached the user device. **It did.**

## End-to-end native path, confirmed by user logs

```text
FF7R-A650-KGSL-ALLOC stage=gpumem_alloc_id errno=12 ...
FF7R-A650-TU-ALLOC stage=tu_allocate_failure vkresult=-2 ...
err: DXVK-SD865-ALLOC stage=driver_retry first_vkresult=-2 retry_vkresult=-2 recovered=0 ...
```

**128** native `FF7R-A650-KGSL-ALLOC` records: *all* `errno=12` (`ENOMEM`) from failed `KGSL_GPUMEM_ALLOC_ID` ioctl calls. **128** `FF7R-A650-TU-ALLOC` records: *all* `vkresult=-2`. **117** corresponding DXVK `stage=driver_retry` records with two failing `vkAllocateMemory` calls per record. This means **the kernel-facing KGSL allocation rejects the request**, not DXVK's internal heap-budget guard. Independent 128-entry caps apply to native stages; event totals do not equal game resource-request totals.

- Failed native request sizes: 4 MiB: **12**; 8 MiB: **26**; 16 MiB: **28**; 32 MiB: **20**; 64 MiB: **14**; 128 MiB: **14**; 256 MiB: **14**.
- Request `bo_flags=0`, `force_32bit=0`, `replayable=0` on every recorded failed ioctl. Thus the driver did **not explicitly request 32-bit constrained GPU VA** on the observed BO allocations; this does not rule out other KGSL/IOMMU mapping constraints. `request_flags=2348810240` (0x8c000000): 106 events, `201326592` (0x0c000000): 22. Compare pinned Mesa KGSL defines for cache/coherency bits; never equate these flags with Vulkan's `allocate_flags=2`.
- DXVK failed allocation types 0: 69 records, 1: 24, 2: 24. DXVK `flags=2` on every failed request means `VK_MEMORY_ALLOCATE_DEVICE_ADDRESS_BIT`, but native `force_32bit=0`. All memory types map to the same heap.
- DXVK logged `DXVK-SD865-POOL state=init enabled=0` twice: ordinary 256/64-MiB pools in this particular run; it is a valid intentional control setting from an earlier user clarification, not a GameNative env propagation bug.
- Vulkan's reported physical heap size remains **8,337,227,776 bytes = 7,951 MiB**. The terminal DXVK allocated total reaches **4,206,886,912 bytes = 4,012.0 MiB**, while driver's budget on its final retry remains above that figure. The kernel is entitled to reject allocations irrespective of `VK_EXT_memory_budget` estimates.

## New Android shared-memory pressure evidence

Eight bounded `FF7R-A650-KGSL-PRESSURE stage=alloc_enomem` records, at Wine log lines **540, 779, 861, 949, 1030, 1055, 1083, 1106**, each taken while handling a native `KGSL_GPUMEM_ALLOC_ID` ENOMEM:

| Wine line | MemAvailable (KiB) | Calling process VmRSS (KiB) | VmSwap (KiB) | VmSize (KiB) | RLIMIT_AS |
|---:|---:|---:|---:|---:|---|
| 540 | 400708 | 2400024 | 0 | 113304136 | -1 |
| 779 | 483060 | 2266332 | 0 | 113169768 | -1 |
| 861 | 483552 | 2266332 | 0 | 113169768 | -1 |
| 949 | 480852 | 2280364 | 5668 | 113200376 | -1 |
| 1030 | 482868 | 2278260 | 8332 | 113205752 | -1 |
| 1055 | 494924 | 2275404 | 12552 | 113216840 | -1 |
| 1083 | 501592 | 2275060 | 16884 | 113246296 | -1 |
| 1106 | 477864 | 2274012 | 22940 | 113249976 | -1 |

**MemAvailable ranges 391–490 MiB** and calling-process VmRSS ranges **2.17–2.29 GiB**. VmSwap rises from zero to ~22.4 MiB during terminal failure. `RLIMIT_AS=-1` indicates unavailable/unlimited limit, **not** negative real memory; VmSize near 108 GiB reflects virtual mappings, **not physically committed memory**. Calling-process RSS excludes substantial other Android processes and some kernel GPU BO charges; DXVK tracked bytes and RSS must **never be added as though separate physical resident allocations** because mappings/charges can overlap.

**Strengthened primary hypothesis:** Actual Android system-memory pressure is plausibly forcing KGSL's allocation failure near 4 GiB of DXVK allocation accounting, despite a larger reported GPU heap/budget. The ~400–500 MiB available readout cannot alone identify the kernel's exact refusal condition (high watermark, DMA/ION page constraints, page table/IOVA fragmentation, memcg limits, context quota). Do **not** claim a proven hard 4 GiB GPU aperture or that BDA causes the issue. The fact the failure persists at 4 MiB substantially weakens theories limited to 256-MiB chunk fragmentation. No direct GPU address-space map, kernel memcg breakdown or exact kernel failure branch has been captured.

## Next Turnip-only engineering work

1. **Preserve native behavior.** The current pinned Mesa Turnip diagnostic AdrenoTools ZIP `f380e6cfd566`, CI run 38192733815, has been verified to emit these tags and consume them through GameNative's no-ADB Wine export. Don't add fake Vulkan heaps, force GPU address bits, or disable actual buffer-device-address requests.
2. **Repair a diagnostic-only gate in `patches/a650/instrument_kgsl_oom.py`:** pressure sampling currently sits after the `TU_A650_KGSL_ALLOC_TRACE` conditional. Move it under the same opt-in gate and bounded diagnostic event counter. Source privacy/default-disabled behavior must be asserted in tests. The runtime pressure data here demonstrates feature usefulness but not correctness of the 'off' mode.
3. For greater discrimination, add opt-in and bounded `MemTotal`, `SwapFree`, `Committed_AS`, `CmaFree` (when available) to pressure snapshots. These are non-sensitive aggregate counters, not process memory maps or GPU virtual addresses. Capture on first / every 32nd error only, retaining errno across logging. The source pinned Mesa build must pass tests, ELF checks and CI before phone tests.
4. Compare the same FF7R save on unchanged DXVK/FEX/graphics driver with freed background RAM vs baseline, using memory snapshots; measure first `KGSL ENOMEM` and success/failure. A real increase in failure threshold with more `MemAvailable` would support Android RAM pressure; unchanged threshold with materially more available memory would point to KGSL BO/IOVA or process accounting. Do not require ADB.

Cross-links: [DXVK tracked allocation analysis](https://github.com/Ragnarok93/dxvk-SD865/blob/feature/ff7r-sd865-architecture-20261011/docs/FF7R-SD865-DXGI-REPORTED-VRAM-VS-VULKAN-OOM-20261012.md), [GameNative DXVK_CONFIG findings](https://github.com/Ragnarok93/GameNative/blob/research/ff7r-vram-config-20261012/docs/investigations/FF7R-SD865-VRAM-CONFIG-PROPAGATION-20261012.md), [FEX bounded evidence](https://github.com/Ragnarok93/FEX/blob/research/ff7r-memory-triage-20261012/docs/investigations/FF7R-SD865-FEX2610-NONCAUSAL-TRIAGE-20261012.md).

**Confidence:** Real native `ENOMEM`, low `MemAvailable` and request sizes are observed. Physical-memory scarcity is the leading hypothesis, not yet a definitive root-cause proof.

## Corrected pressure diagnostic V11: CI and archive validation

The follow-up driver source was adjusted in `patches/a650/instrument_kgsl_oom.py` so that `/proc/meminfo` and `/proc/self/status` sampling is **inside** the same `TU_A650_KGSL_ALLOC_TRACE=1` branch as the native KGSL failure-only log, and is bounded to 128 recorded errors. Before this correction the pressure probe read `/proc` periodically on failures even if trace env was disabled. Now it performs no periodic `/proc` reads if tracing is off or event cap reached. The first and each 32nd logged KGSL failure has fields `mem_available_kib`, `mem_total_kib`, `swap_free_kib`, `committed_as_kib`, `cma_free_kib` (missing values `-1`), `vm_rss_kib`, `vm_swap_kib`, `vm_size_kib`, `rlimit_as_bytes`. The original errno is restored and the driver memory policy unchanged.

**Verified build:** [GitHub Actions run 38194191376](https://github.com/Ragnarok93/Banners-Turnip/actions/runs/38194191376), SHA `5371791f0a43ea7ba8bee84ca5217285e4b2f30e`, all tests and pinned Mesa compilation passed. Downloaded and independently extracted/validated:

- AdrenoTools installable inner ZIP: `mesa-turnip-main-A650-FF7R-KGSL-Diag-5371791f0a43-V11.zip`, **3,217,221 bytes**.
- ZIP SHA-256: `5bb2d16ba1fff2b8a56e7594c32cd346fd133fc585544928e9834edb64580c26` (matches CI-provided .sha256).
- Valid inner ZIP CRC: `meta.json` names `Banners Turnip A650 FF7R KGSL OOM Diagnostic 5371791f0a43`; `libvulkan_freedreno.so` ELF64 AArch64, size 15,829,000 bytes.
- Native ELF contains all expected markers `FF7R-A650-KGSL-ALLOC`, `FF7R-A650-KGSL-PRESSURE`, `FF7R-A650-TU-ALLOC`, `TU_A650_KGSL_ALLOC_TRACE`, `mem_total_kib=`, `swap_free_kib=`, `committed_as_kib=`, `cma_free_kib=`.

The V11 ZIP is an **AdrenoTools graphics driver** and must not be installed in GameNative as DXVK or FEX WCP. Keep original Mr Purple T30 and prior V9 package for rollback. Current CI checks do not replace required A650 runtime validation.
