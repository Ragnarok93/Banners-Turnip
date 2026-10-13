# A650 pipeline backing candidate: build validation

Source checkpoint: c873a668a1a23eb9c6ac5f49463332a5ecc2214a.
CI: https://github.com/Ragnarok93/Banners-Turnip/actions/runs/38354147934 (all three profiles pass).
Mesa: 76b9372c4e5d186f57d22d3a4f95dd1c5e04ece2; NDK r29; Android API29; A77/O3/ThinLTO.

| Profile | Pipeline backing on A650 | ZIP SHA256 | ABI checks |
| --- | --- | --- | --- |
| sd865-cortex-a77 | 128 KiB | 5f8c1c272f51d6fd45e25eb90a1808e6da8feba4d76ef81201c5d377de31a1be | 12 pass |
| sd865-program-reference | 128 KiB | 0e7f5546431db40ab4f994b8e37c226fc6194911ed67ee4964dbeee36910a9b7 | 12 pass |
| sd865-pipeline-512k | 512 KiB | cc9edef5712cc84f52ccb636838e9a1b2ed37860229b1815ca6cd5c0d691a201 | 12 pass |

Downloaded outer archive digests and inner driver hashes verified. Driver ELF is AArch64, SONAME/Android imports pass, no desktop GLIBC/Wayland/XCB requirement. Adreno650 exists in the built device table. Source patch applies strictly on pinned Mesa. Common KGSL fixes remain upstream; profiling backing remains128KiB and other GPUs retain128KiB.

The actual Mesa allocator/GPU-ID regression passes on all three CI builds: 8 vs2 BO calls for64 x16KiB, identical1MiB total backing bytes, valid alignment/content/oversize behavior, OOM/map failure propagation and teardown. Explicit and chip-derived A650 identification pass; A618/A640/A660/A7xx/A830 use128KiB.

No on-device Vulkan conformance, FF7R GPU timing or memory-pressure result is claimed. Larger partially filled BOs can retain additional memory. Keep experimental until three matched device trials show real-frame median/p95/p99 improvement without corruption/crashes/increased memory pressure.

Test order: previous accepted DXVK versus dfcab832 on the same driver; then fix DXVK and compare A77 vs program-reference; then program-reference vs pipeline-512k. Keep LSFG/vkBasalt enabled in-container, LSFG FG off in-game, texturesLow and other settings/cache/thermal conditions fixed.

DXVK counterpart passes50 native tests, MSVC and MinGW x32/x64; WCP run38353184245. See Ragnarok93/dxvk-SD865 docs/FF7R-DXVK311-CONTINUATION-20261013.md.
