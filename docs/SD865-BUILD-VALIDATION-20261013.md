# SD865 Turnip matched-build validation — 2026-10-13

Source checkpoint: `f39c5f7cb9a3beec1c20d2049480baaa263d05bb`.
Mesa: `76b9372c4e5d186f57d22d3a4f95dd1c5e04ece2`.
CI: https://github.com/Ragnarok93/Banners-Turnip/actions/runs/38348570456

Both sd865-cortex-a77 control and sd865-program-reference candidate:
- compile successfully with NDK r29, Android API 29 and O3/A77/ThinLTO;
- pass profile/Mesa/API/patch/driver hash checks;
- pass all 12 existing Android ZIP ABI checks (AArch64, bionic dependencies, HMI export, SONAME, metadata and exact two-file layout);
- retain A650 Vulkan 1.3 feature gates, shader paths, barriers, GMEM choices and clocks.

Artifacts: turnip-sd865-cortex-a77-3 (11789163943), turnip-sd865-program-reference-3 (11789084208).

ZIP SHA256:
- control: 60e49d6f7153097dae4dbcfe46c961c289fad0ce79ab9c45814cac4fd3990173
- candidate: 1651e53c2dc3df3f3f4c20c849dee14f69ef53202856140aabe654a96eb44e18

Program-state patch SHA256: 504dfc79cbece8d984c511f4115b1a0c88d2c57c5720417b7264595823dcf79c.
The three-file patch applies exactly to the pinned upstream and reverses byte-for-byte. Full-source inspection found all program-state consumers updated. The pointer uses static zero state before first graphics bind and borrows state from a pipeline whose lifetime is already governed by Vulkan recording/submission rules.

DXVK counterpart: selective upstream backports at Ragnarok93/dxvk-SD865 340eb6a, successful x32/x64 WCP build and 49 tests.

Device validation pending: FF7R startup, combat/cutscenes, image correctness, OOM/crash rate and warm-cache real-frame p95/p99. No FF7R gain claimed. Keep LSFG/vkBasalt on in-container, LSFG FG off in-game and textures Low. Use both new profiles on the same DXVK and Mesa; historical floating-main A77 drivers are not a matched control. Fork coherency relaxations and forced clock/governor changes remain excluded.
