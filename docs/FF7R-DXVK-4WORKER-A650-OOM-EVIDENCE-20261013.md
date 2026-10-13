# FF7R Snapdragon 865/Adreno 650: 2026-10-13 four-worker DXVK evidence

User-supplied GameNative logs confirm both DXVK DLLs from SHA `4a65e1b33aae98dc91adf3ef1b8205b5f8623215`, D3D11 FL11_0, four compilation workers, Vulkan wrapper 26.2.99, LSFG resident/off and vkBasalt loaded.

Nine DXVK Vulkan allocation attempts failed in the driver after retry, first/retry `VK_ERROR_OUT_OF_DEVICE_MEMORY (-2)`: 256MiB (4), 128MiB (3), 64MiB (2), all Vulkan memory type 0 on heap 0, `pool_experiment=0`, no dedicated allocations. Last DXVK allocated about 3,652MiB and budget about 3,990MiB: positive reported budget does not guarantee chunk allocation on shared Android RAM.

Frame completion cadence degrades at approximately present ID 7170; final eight window P95 median 62.85ms. Last command queue ENQUEUE mean 19us, QUEUE-SUBMIT 93us (none >10ms); async GPU-WAIT mean 4246us with 5929/45888 >10ms, 726/45888 >33ms. GPU-WAIT is CPU blocking elapsed time, **not measured shader execution, GMEM, GPU utilization, or a direct proof of Turnip regression**.

The user capture continues presenting after the nine failed chunk allocation attempts and ends with X-server disconnection and destroyed-mutex teardown log. Do not interpret each allocation error as terminal OOM; no device-lost error recorded.

Optimization/testing priority: keep all Turnip source variants isolated. First A/B the same DXVK build's gated smaller pooled-device chunk limits (64MiB device/32MiB mapped) vs disabled, verify the exact in-process build stamp before using that artifact. Then compare A77/program-reference/512KiB Turnip candidates under otherwise matched conditions. Only propose actual Turnip allocation or scheduler changes if supported by A650-specific driver evidence or real GPU profiling. Do not force clocks or infer that Vulkan version 1.4 features exist on A650.

This checkpoint is analysis only, no Turnip source edit or device FPS performance claim.