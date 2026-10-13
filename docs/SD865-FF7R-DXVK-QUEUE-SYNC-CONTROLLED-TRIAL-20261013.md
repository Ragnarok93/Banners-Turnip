# S20+ FF7 Remake DXVK/Turnip cross-stack follow-up — 2026-10-13

The user’s instrumented GameNative run with latest FF7R DXVK showed a shift from ~6–8ms CPU-side DXGI present intervals in earlier scenes/menus to mostly ~31–50ms in a later, unidentified demanding region around presentation ID 6400–6650. DXVK's render-thread pipeline miss slowpaths showed no >10ms stalls in 192 samples. Background shader compilation reached 448 worker tasks, including 14 >10ms tasks.

**No direct Turnip GPU execution time was measured**, so this observation must not be attributed to Mesa's A650 shader compiler, GMEM or memory allocator. Keep driver source unchanged pending controlled tests.

Companion DXVK changes under `Ragnarok93/dxvk-SD865` branch `feature/ff7r-sd865-architecture-20261011` instrument the CPU-side submit queue, WSI presentation call, Vulkan timeline completion waits, command-stream sync waits, fence/resource waits, pipeline backlog and timestamped DXGI frame windows. `DXVK_FF7R_METRICS=1` enables them. Their absence does not prove a zero-cost path; some events only log after a threshold of samples.

## Controlled sequence

1. DXVK four-vs-eight shader compiler threads via existing `DXVK_CONFIG` setting (not a driver change); preserve Turnip driver, graphics, caches, resolution, FEX, LSFG/vkBasalt and matching gameplay.
2. Inspect CPU queue, GPU-completion wait, and CS wait aggregates; compare per-window p95/p99. None is a true GPU hardware timestamp.
3. After this identifies the bottleneck, isolate the previously compiled A77 base, program-reference and 512KiB pipeline backing BO variants as three matched A/B/C driver captures. Do not force clocks or merge A8xx-only changes.
4. Backport other fork features only when A650 Vulkan 1.3 feature-gated, correctness-tested and backed by device evidence. Forks reviewed: WinNative-Emu/Drivers, The412Banner/Banners-Turnip, DXVK GPLALL variants. No newly validated A650 FF7R performance win discovered from the surveyed fixes.

No new GPU driver code, binary or FPS improvement is claimed in this checkpoint.
