# Adreno 650 FF7R memory diagnostics: DXVK pool control A

2026-10-13 new DXVK pool WCP run **did not enable the 64MiB/32MiB experiment**. Both loaded DLLs matched commit `749729333e9b7cfddc427c8fc57cb24b7cb5f3ce`; `DXVK-SD865-POOL state=init enabled=0` confirmed device cap 256MiB, mapped cap 64MiB, default empty-chunk retention. Four compiler workers active, 1280x720, Vulkan driver wrapper 26.2.99, LSFG resident/off and vkBasalt loaded.

13 driver `VK_ERROR_OUT_OF_DEVICE_MEMORY (-2)` retry sequences: 256MiB x5; 128MiB x4; 64MiB x3; 32MiB x1, all on heap0/type0. Compared with the previous 4-worker run's nine 256/128/64MiB failures, this capture ran longer and had **357MiB more initial driver-reported budget**. It cannot be used to claim allocator improvement or regression.

The new capture had 61 x 256-present windows. Distinct ~33ms, ~7.7ms, then 35–45ms pacing regimes occur in different present-ID ranges from the previous capture, invalidating scene-agnostic p95 comparisons. Queue-submit mean 101us, GPU-completion *CPU wait* mean 4315us, 10403/64192 waits above 10ms (16.21%); these are not GPU shader duration. More than one 32MiB allocation fails under pressure, so reducing maximum chunk size alone cannot be assumed to cure driver memory allocation.

**Next:** DXVK A/B pool=0 vs pool=1 with same binary, video driver, workload and scene; verify enabled=1 marker. Do not change Turnip GMEM, device heap budget, CPU clocks or Vulkan feature exposure from this ambiguous control evidence. No actual Turnip code changes in this checkpoint.

Do not include unredacted Wine logs in repo documentation (Epic auth fields).
