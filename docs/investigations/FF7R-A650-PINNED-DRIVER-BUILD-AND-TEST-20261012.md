# Snapdragon 865 / Adreno 650 — FFVII Remake pinned Turnip diagnostic build

**Status:** Experimental build, not a demonstrated OOM fix. This is a separate **AdrenoTools Turnip ZIP**, **not a DXVK/FEX `.wcp`**. Driver source is pinned Banners Mesa `745709a000482a4a24c91faef5c5a40bd653a863`, not claimed equivalent to Mr Purple T30. All claims of native KGSL behavior require running this pinned driver on the S20+.

## Build provenance

- Repo branch: `research/ff7r-a650-kgsl-oom-20261012`.
- CI: [`turnip_a650_ff7r_oom_diagnostic.yml`](../../.github/workflows/turnip_a650_ff7r_oom_diagnostic.yml), produces one uniquely named ZIP (library `libvulkan_freedreno.so`, `meta.json`) and its SHA-256 file.
- Based on Banners A6xx standard driver (no A8xx patches); optional compile flag `TURNIP_A650_FF7R=1` yields `-O3 -flto=thin -mtune=cortex-a77`, retains base Armv8 ISA for all Snapdragon 865 Kryo 585 cores. This improves compiler targeting *on paper*; real FF7R performance gain is unmeasured.
- Build with `EXTRA_SCRIPT=patches/a650/instrument_kgsl_oom.py`, fail-closed on Mesa source structure changes. No Vulkan feature spoofing, memory-heap size override, buffer-device-address suppression, forced 32-bit IOVA, or modified Vulkan allocation policy.
- Diagnostics are **off by default** and use stderr only after a failure, limited to 128 lines per process. They don't dump GPU virtual addresses, client pointers, FD values, memory contents or Android private data.

## What the driver diagnostic attempts to distinguish

At failed KGSL `IOCTL_KGSL_GPUMEM_ALLOC_ID`: `FF7R-A650-KGSL-ALLOC stage=gpumem_alloc_id errno=... request_bytes=... align_bytes=... bo_flags=... request_flags=... force_32bit=... replayable=...`.

At failed `tu_AllocateMemory` after BO allocation: `FF7R-A650-TU-ALLOC stage=tu_allocate_failure vkresult=... requested_bytes=... memory_type=... heap_used_bytes=... heap_size_bytes=... allocate_flags=...`.

These fields distinguish a native errno-generating ioctl rejection from Turnip heap accounting, and let us check whether BOs rejected for FF7R actually carry the `FORCE_32BIT` low-address constraint (which **must not be inferred** from `VK_MEMORY_ALLOCATE_DEVICE_ADDRESS_BIT` alone).

**Output capture warning:** The Vulkan ICD runs natively under Android. Whether its `stderr` is included in GameNative's Wine debug log export is **not verified**. First look for these markers in the exported `wine_debug` / `d3d11.log`; their absence does not prove the driver code isn't active. A later GameNative-native logging integration may be needed to forward safe driver diagnostic markers without ADB.

## Phone-only A/B

1. Preserve Mr Purple T30 installed as a stable rollback. Import the pinned **AdrenoTools ZIP** in GameNative graphics driver settings/Contents Manager and select it for FF7R, not as a DXVK WCP.
2. Keep original known DXVK 2.7.1, FEX2610, UE4 settings, 540p/low textures, same save. GameNative **Graphics Max Device Memory = 0** (do not spoof the Vulkan heap). Disable LSFG/framegen and vkBasalt.
3. Add `TU_A650_KGSL_ALLOC_TRACE=1`, `DXVK_SD865_ALLOC_TRACE=1`, `DXVK_LOG_LEVEL=error`. Export GameNative Wine debug logs and DXVK D3D11 log after one reproduced failure.
4. Inspect `FF7R-A650-KGSL-ALLOC` / `FF7R-A650-TU-ALLOC` for stage and errno; correlate with `DXVK-SD865-ALLOC stage=driver_retry`. Do not enable giant Wine `+vulkan` trace.
5. Run a second matched test using original Mr Purple T30 with the same DXVK/FEX/UE4 configuration, preserving T30 artifact/hash. Compare native OOM threshold, texturing correctness, driver identity, crash status and performance. This isolates *driver difference* from reporting-only DXGI VRAM settings.

## If errno is missing

Treat `VkResult=-2` as verified but native kernel cause unknown. Do not assume it means GPU's 4-GiB virtual address cap. Instrument driver-to-GameNative-native log forwarding next. Never require ADB for this user workflow.

Related repos: [DXVK memory analysis](https://github.com/Ragnarok93/dxvk-SD865/blob/feature/ff7r-sd865-architecture-20261011/docs/FF7R-SD865-DXGI-REPORTED-VRAM-VS-VULKAN-OOM-20261012.md), [GameNative settings implementation](https://github.com/Ragnarok93/GameNative/blob/research/ff7r-vram-config-20261012/docs/investigations/FF7R-SD865-VRAM-CONFIG-PROPAGATION-20261012.md), [FEX diagnosis boundaries](https://github.com/Ragnarok93/FEX/blob/research/ff7r-memory-triage-20261012/docs/investigations/FF7R-SD865-FEX2610-NONCAUSAL-TRIAGE-20261012.md).

## 2026-10-12 CI verification completed

Pinned A650 build succeeded in [GitHub Actions run 38190843264](https://github.com/Ragnarok93/Banners-Turnip/actions/runs/38190843264) from commit `a2e797087b3dc1c53692c786b4e0808009d393a6`. The workflow checked the exact Mesa pin and both ELF markers. Independently downloaded the Actions ZIP and verified:

- Installable AdrenoTools ZIP: `mesa-turnip-main-A650-FF7R-KGSL-Diag-a2e797087b3d-V6.zip`
- SHA-256: `087bd81ee3d696fbb114ec56d5d35950f22e8e4b2b2d4f23df967de3378b5699`
- `meta.json` driver identity: `Banners Turnip A650 FF7R KGSL OOM Diagnostic a2e797087b3d`, reported Vulkan `1.4.363`.
- `libvulkan_freedreno.so`: ELF 64-bit AArch64, Android 34, NDK r29, BuildID `fa2dcb88067db4ee9e98f4bf8718fecedec4fa39`.
- Verified embedded text symbols `FF7R-A650-KGSL-ALLOC`, `FF7R-A650-TU-ALLOC`, `TU_A650_KGSL_ALLOC_TRACE`.

**No runtime A650 device validation yet.** Benchmarking against Mr Purple T30, loading with PurpleVK, and verifying stderr forwarding remain open. The package is source/compile/structure validated but not a proven performance improvement or root-cause fix.
