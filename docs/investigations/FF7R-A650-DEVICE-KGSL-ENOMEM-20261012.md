# Adreno 650 / FFVII Remake: driver-native KGSL ENOMEM captured on device

**Evidence date:** 2026-10-12. **Owner:** `Ragnarok93/Banners-Turnip`. Four new user files: `ff7remake__d3d11.log` (153 lines), `ff7remake__dxgi.log` (4 lines), `wine_debug.log (3).txt` (1,063 lines), and an **old unrelated** Oct 6 GameNative JNI crash report. Private source logs were not checked into this repository.

## This materially advances the previous Vulkan -2-only diagnosis

For the first time the user's Android Wine export contains **both** opt-in native `FF7R-A650-KGSL-ALLOC` and `FF7R-A650-TU-ALLOC` tags. The exact marker strings match the diagnostic instrumentation built in our [pinned Mesa A650 ZIP workflow](../../.github/workflows/turnip_a650_ff7r_oom_diagnostic.yml). **The logs do not contain a full selected driver identity/SHA, so confirm the installed package separately before claiming exact binary provenance or an equivalence with Mr Purple T30.**

- 128 `FF7R-A650-KGSL-ALLOC` events were captured, and every one has **`stage=gpumem_alloc_id errno=12`**, meaning the kernel's **`IOCTL_KGSL_GPUMEM_ALLOC_ID`** returned **`ENOMEM`**. This is the specific native point of failure, beyond Vulkan reporting -2.
- 128 `FF7R-A650-TU-ALLOC` records all say **`stage=tu_allocate_failure vkresult=-2`**. All have `allocate_flags=2` (ordinary `VK_MEMORY_ALLOCATE_DEVICE_ADDRESS_BIT`). This agrees with 117 DXVK `stage=driver_retry` events in the parallel logs; **do not infer 128 logical resource requests** because each DXVK first+retry pair can generate two native failures, and native markers have independent caps of 128 per process.
- **Native KGSL bo_flags=0, force_32bit=0, replayable=0 in all 128 sampled failures**. This rules out the explicit `KGSL_MEMFLAGS_FORCE_32BIT` / replayable code paths for the *captured* failures. It does **not** prove an unlimited underlying GPU virtual address range or exclude KGSL-internal GPU VM fragmentation.
- **Request sizes:** 8 MiB ×8, 16 MiB ×12, 32 MiB ×28, 64 MiB ×32, 128 MiB ×28, 256 MiB ×20. Every observed ioctl request returns ENOMEM. Both `memory_type=0/1/2` appear at the Turnip layer: 92/18/18, all on the same Vulkan heap 0.
- Native `request_flags=2348810240` (`0x8c000000`) on 110 failures and `201326592` (`0x0c000000`) on 18. These are KGSL request flags, not DXVK's Vulkan memory flags. Exact individual bit meaning must be established from the pinned driver/kernel headers before attributing a cause. Both classes fail, so it is **not limited to one memory type or request flag pattern**.
- Native Turnip `heap_used_bytes` ranges **4,109,139,968** (~3,918.78 MiB) to **4,213,997,568** (~4,018.78 MiB) at the recorded failures. `heap_size_bytes=8,337,227,776` (~7,951 MiB) in all 128 native traces. Thus Turnip's own heap accounting is **well below** its reported heap size; the native KGSL syscall fails nonetheless. Because heap usage can change between calls, do not mistake a repeated rounded level for proof of a literal 4-GiB integer limit.
- DXVK has 117 `driver_retry` events (`first_vkresult=-2 retry_vkresult=-2 recovered=0`), eight `pool_exhausted` reports and four final resource allocation errors. DXVK `pool_experiment=0` for this run. DXVK's final tracked allocation is around **4,008 MiB**. The reported Vulkan driver `VK_EXT_memory_budget` exceeds the used amount at failure, which is **not a guarantee that a new KGSL BO can be allocated**.
- DXGI log reports only EDID/color metadata fallbacks. The accompanying `pluvia_crash_2026-10-06_06-51-57` is historical and documents an Android `UnsatisfiedLinkError` in `GPUImage`; it is not this driver's root cause.

## Confidence table

| Statement | Confidence |
|---|---|
| Underlying `GPUMEM_ALLOC_ID` ioctl failed with Linux `ENOMEM` | **Directly confirmed** by tagged native driver |
| Turnip maps it to Vulkan `VK_ERROR_OUT_OF_DEVICE_MEMORY` | **Directly confirmed** |
| DXVK correctly sees real failed `vkAllocateMemory` first and retry | **Directly confirmed** |
| Turnip's own advertised heap was exhausted (7,951 MiB) | **Contradicted by native heap-used readouts** |
| Explicit FORCE_32BIT or capture/replayable allocation was applied | **Contradicted in the failed native requests** |
| Absolute 4 GiB Qualcomm KGSL process, GPU VM, cgroup or physical limit | **Hypothesis, not proven** |
| Existing DXGI/Graphics video-memory settings physically capped KGSL | **No: these controls only affect reports** |
| The installed binary was identical to Mr Purple T30 | **Not established from the uploaded logs** |

## Next measured discriminant

Capture **non-sensitive, failure-only Android shared-memory pressure** in the *Turnip diagnostic build* via `/proc/meminfo MemAvailable`, `/proc/self/status VmRSS/VmSwap`, and (where available) `RLIMIT_AS` at the *first* KGSL ENOMEM. This uses the same driver stderr tags already **proven visible in the user's GameNative Wine export without ADB**, and avoids continuously polling. Do not increase Vulkan heap limits, disable device addresses, force 32-bit GPU memory placement or change allocator behavior. A second run should compare native MemAvailable and VmRSS with this run's ~4-GiB failure threshold. If Android still has substantial MemAvailable, investigate the kernel's KGSL per-process accounting, GPU VA map and buffer allocation implementation; if system memory is depleted, prioritize lowering live UE4 texture/streaming load and other process memory usage.

### Ownership / related modules
- DXVK data: [source allocation tracer and A/B results](https://github.com/Ragnarok93/dxvk-SD865/blob/feature/ff7r-sd865-architecture-20261011/docs/FF7R-SD865-POOL-EXPERIMENT-DEVICE-RESULT-20261012.md).
- GameNative settings and DXVK_CONFIG serializer: [GameNative investigation](https://github.com/Ragnarok93/GameNative/blob/research/ff7r-vram-config-20261012/docs/investigations/FF7R-SD865-VRAM-CONFIG-PROPAGATION-20261012.md).
- FEX 2610: no FEX-specific crash shown; [FEX boundary report](https://github.com/Ragnarok93/FEX/blob/research/ff7r-memory-triage-20261012/docs/investigations/FF7R-SD865-FEX2610-NONCAUSAL-TRIAGE-20261012.md).
