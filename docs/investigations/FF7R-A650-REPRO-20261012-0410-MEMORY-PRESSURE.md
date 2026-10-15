# FFVII Remake S20+ — 04:10 UTC repeat crash, native KGSL OOM with rising swap

**Source scope:** user-uploaded Wine `wine_debug.log.txt` (1,263 lines), DXVK module log (155 lines), GameNative app log (1,111 lines), 4-line DXGI log, separate historic October 6 crash file. Capture timestamp visible in app log **October 11, 23:08 local**; supplied at ~2026-10-12 04:10 UTC. No raw phone logs committed. **This report owns only native driver/KGSL behavior and Android memory pressure.** Other subsystems have their own reports.

## Confirmed native path

This run **does load the already built A650 native diagnostic**; Wine log includes 128 `FF7R-A650-KGSL-ALLOC` (independent 128-event cap), 128 `FF7R-A650-TU-ALLOC` (independent cap), and four `FF7R-A650-KGSL-PRESSURE` snapshots. All 128 native KGSL events are `stage=gpumem_alloc_id errno=12` = Linux **ENOMEM** at `IOCTL_KGSL_GPUMEM_ALLOC_ID`; all 128 Turnip events have `stage=tu_allocate_failure vkresult=-2` = Vulkan `VK_ERROR_OUT_OF_DEVICE_MEMORY`.

- `request_bytes` on logged *failed* native ioctl calls: 8 MiB ×8, 16 MiB ×12, 32 MiB ×27, 64 MiB ×32, 128 MiB ×28, 256 MiB ×21; total 128 recorded.
- `request_flags=2348810240` (0x8c000000) on 110 calls, `201326592` (0x0c000000) on 18; `bo_flags=0`, `force_32bit=0`, `replayable=0` in all 128. These flags require the source driver's KGSL header to decode fully. Do **not** infer an explicit 32-bit GPU address allocation path from the DXVK `VK_MEMORY_ALLOCATE_DEVICE_ADDRESS_BIT`.
- Turnip failed native `memory_type` distribution 0:92 / 1:18 / 2:18, sharing heap 0. `heap_size_bytes=8337227776` (7,951 MiB advertised) and observed `heap_used_bytes` reaches 4,213,997,568 (~4,019 MiB), substantially below advertised total. This does **not** establish a hard 4-GiB device limit.

### Actual Android memory pressure at errno failures

Four `FF7R-A650-KGSL-PRESSURE` events were observed (Wine lines 590, 701, 783, 871). They contain extended post-V11 fields, proving the updated pressure diagnostic itself was active, although exact installed ZIP SHA is not included in trace.

| Wine line | MemAvailable KiB | MemTotal KiB | SwapFree KiB | VmRSS KiB | VmSwap KiB | CmaFree KiB | RLIMIT_AS |
|---:|---:|---:|---:|---:|---:|---:|---|
| 590 | 310544 | 10856072 | 6178576 | 2301852 | 25512 | 364 | -1 |
| 701 | 365148 | 10856072 | 5791760 | 1909996 | 416400 | 0 | -1 |
| 783 | 423588 | 10856072 | 5706000 | 1837000 | 489396 | 8 | -1 |
| 871 | 415808 | 10856072 | 5671696 | 1809224 | 509588 | 0 | -1 |

**Interpretation:** `MemAvailable` remains approximately **303–414 MiB** during the native KGSL failures, while calling-process swap climbs **~25 MiB → ~498 MiB** and calling-process RSS drops **~2.20 → ~1.73 GiB**. This is stronger evidence for substantial Android shared-memory pressure and reclaim/swapping than prior captures. Physical memory availability is very low relative to the device's total reported 10.35 GiB. `CmaFree≈0` does **not automatically prove** these KGSL BO requests require contiguous CMA (that kernel allocation implementation remains to be proven). `SwapFree` describes global free swap and is not directly available GPU BO memory. `VmSize` near 109 GiB represents virtual mappings and `RLIMIT_AS=-1` means unlimited/unknown, not a reason for hard Vulkan exhaustion. RSS, Turnip heap-used and DXVK tracked memory must not be added as separate physical consumptions.

**One useful detail:** The first observed DXVK driver call fails but DXVK's retry succeeds (a 256-MiB BO); this means the system can briefly reclaim/reuse memory to satisfy an allocation. Later native driver calls fail and the game terminates. We cannot prove the same KGSL ioctl *retry* succeeded from failure-only native markers (they do not log successful calls).

## Causal confidence

**Confirmed** native KGSL ioctl returned ENOMEM; Turnip propagated Vulkan -2; correct raw 7951-MiB heap report with no 2048 spoof; driver request did not carry `FORCE_32BIT`; Android MemAvailable very low with fast swap growth; no additional native kernel backtrace or exact allocator branch. **Leading explanation**: GPU BO pressure under Android-wide reclaim / KGSL kernel page, mapping, or accounting constraints. **Still open:** specific kernel ENOMEM branch, memcg quota, shared physical RAM vs IOVA fragmentation vs cgroup pressure; pure 4-GiB GPU aperture; exact source identity of Mr Purple T30 (this diagnostic is a separate pinned Mesa driver, not the stock T30 binary).

## Proposed discriminating experiment / next driver-only work

1. With **same pinned diagnostic AdrenoTools ZIP**, DXVK, FEX, game save/settings, restart the phone and close nonessential apps before launching. No ADB. Keep GameNative graphics Max Device Memory=0 and `TU_A650_KGSL_ALLOC_TRACE=1`, and log initial native ENOMEM / MemAvailable / VmRSS / VmSwap. Compare the failure point against this 303–414-MiB MemAvailable baseline. No assertion that rebooting fixes anything.
2. If Android MemAvailable is materially higher but ioctl still returns ENOMEM at the same ~4 GiB tracked GPU BO usage, investigate pinned Samsung KGSL kernel `GPUMEM_ALLOC_ID` failure branches and per-process GPU VA accounting. Avoid spoofing heaps or suppressing Vulkan BDA flags.
3. If failure threshold shifts with increased MemAvailable or live UE4 texture memory decreases, prioritize actual workload/UE4 texture-streaming reductions instead of "VRAM cap" settings.
4. If extending the driver trace, log successful **bounded** KGSL allocation after preceding failure and approximate kernel allocation-state totals if available without root. Preserve errno and opt-in, capped failure-only logs.

Cross-links: [DXVK allocation experiment](https://github.com/Ragnarok93/dxvk-SD865/blob/feature/ff7r-sd865-architecture-20261011/docs/FF7R-SD865-POOL-EXPERIMENT-DEVICE-RESULT-20261012.md); [GameNative settings report](https://github.com/Ragnarok93/GameNative/blob/research/ff7r-vram-config-20261012/docs/investigations/FF7R-SD865-VRAM-CONFIG-PROPAGATION-20261012.md); [FEX boundary](https://github.com/Ragnarok93/FEX/blob/research/ff7r-memory-triage-20261012/docs/investigations/FF7R-SD865-FEX2610-NONCAUSAL-TRIAGE-20261012.md).
