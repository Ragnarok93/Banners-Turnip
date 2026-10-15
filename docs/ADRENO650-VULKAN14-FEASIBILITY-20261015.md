# Adreno 650 Vulkan 1.4 feasibility (2026-10-15)

## Verdict

**Technically plausible, not yet proven conformant.** Vulkan 1.4 is a software API contract, not a hardware generation number. The Adreno 650 may expose Vulkan 1.4 only if Turnip can correctly implement every mandatory Vulkan 1.4 feature and limit on this GPU, including features that were optional in 1.3. Merely changing the reported apiVersion or removing a GPU-generation gate is not sufficient evidence.

Upstream Turnip has historically gated its Vulkan 1.4 apiVersion path to A7xx and newer. A community fork reports enabling 1.4 on A6xx by removing that gate. That establishes that the gate can be bypassed in source; it does not establish full correctness or CTS conformance on Adreno 650.

## Vulkan 1.4 requirements to audit

Use the current Khronos Vulkan 1.4 specification and feature proposal as the source of truth:
- https://registry.khronos.org/vulkan/specs/latest/html/vkspec.html
- https://docs.vulkan.org/features/latest/features/proposals/VK_VERSION_1_4.html

At minimum, audit the mandatory Vulkan 1.4 features/limits, including:
- Required Roadmap 2024 feature set: shaderImageGatherExtended, shaderInt16, storageBuffer16BitAccess, shaderInt8, storageBuffer8BitAccess.
- Required additional functionality such as largePoints, variablePointers, variablePointersStorageBuffer, and bresenhamLines.
- Promoted functionality and feature bits, including pushDescriptor, dynamic rendering local reads, scalar block layout, subgroup rotate/clustered rotate, line rasterization and maintenance functionality.
- Required limits such as maxBoundDescriptorSets >= 7, maxColorAttachments >= 8, timestampComputeAndGraphics, maxImageDimension3D >= 512, maxPushConstantsSize >= 256, and viewport bounds/dimensions.
- Vulkan 1.4 queue requirements, including graphics/compute queues also advertising transfer support.

The list above is a screening checklist, not a replacement for the complete spec's feature and limit requirements.

## Required validation before advertising Vulkan 1.4

1. Build a dedicated A650 candidate from a pinned Mesa commit with only the apiVersion gate changed initially. Keep the existing Vulkan 1.3 build as control.
2. Query and save VkPhysicalDeviceProperties, VkPhysicalDeviceFeatures2 plus the Vulkan 1.4 feature struct, queue-family properties, limits, and extension enumeration on real Adreno 650 hardware.
3. Compare every mandatory feature and limit with the Vulkan 1.4 specification. Do not report a mandatory feature as supported unless Turnip's implementation and hardware path actually satisfy it; do not fake support by forcing feature bits true.
4. Run the relevant Vulkan 1.4 CTS on the exact driver binary and device, then investigate all failures. CTS success for Vulkan 1.3 or a successful build is not Vulkan 1.4 conformance.
5. Run emulator/game smoke tests only after the feature/limit audit; these complement but do not replace CTS.

## Interpretation

- If all mandatory requirements are genuinely supported and CTS passes, expose Vulkan 1.4 on A650 behind a dedicated, reversible build profile and publish the tested Mesa SHA and CTS result.
- If one or more mandatory requirements cannot be implemented correctly, keep Vulkan 1.3 advertised. A private experimental branch may still test individual extensions, but must not claim Vulkan 1.4 conformance.
- Vulkan 1.5+ is not a meaningful target unless Khronos has ratified that API version and the driver implements its complete requirements.

## Related repository work

The unified A650 branch carries the opt-in SYSMEM/program-state/pipeline-allocation candidates and the KGSL OOM diagnostics. Those changes are independent of Vulkan API-version support and must not be used as evidence for or against Vulkan 1.4 capability.


## External fork survey (2026-10-15)

### NightHammer1000/TurnipMagisk

Repository: https://github.com/NightHammer1000/TurnipMagisk  
Release: https://github.com/NightHammer1000/TurnipMagisk/releases

This fork builds Mesa main and removes the `chip >= 7` API-version gate, describing Vulkan 1.4 as enabled for A6xx. Its archived README does not document an A650 Vulkan 1.4 CTS pass, a complete mandatory-feature audit, or an A650-specific benchmark. The repository was archived on 2026-08-19. Treat it as proof that a community build can expose the version, not proof of conformance or benefit.

### MrPurple666/purple-turnip

Releases: https://github.com/MrPurple666/purple-turnip/releases

The unified T29 release reports Vulkan 1.4.354 and explicitly describes its A6xx Vulkan 1.4 support as non-conformant. T30 later reports improved A6xx/A7xx stability and fewer graphical issues, while also noting limited tester coverage for some target devices. This is the strongest caution in the fork survey: users may run workloads with a 1.4-reported driver, but that is not the same as a conformant implementation. The release notes do not provide a verified Adreno 650 CTS result or a controlled performance comparison isolating Vulkan 1.4.

### Anmol6002/AdrenoToolsDrivers and mesa-unified

Releases: https://github.com/Anmol6002/AdrenoToolsDrivers/releases

The A6xx Vulkan 1.4-specialized release notes explicitly say the configuration was tested on A613, not broadly validated on all A6xx GPUs, and warn that other devices should be tested independently. This is not direct evidence for Adreno 650, whose feature reporting and driver path still need their own validation.

### Official Mesa / Khronos baseline

Collabora's September 2026 engineering report says upstream Turnip is fully Vulkan 1.3-supported on A6xx and Vulkan 1.4-conformant on A7xx. The Khronos conformant-products list has Turnip entries for Adreno 610, 618 and 660 at Vulkan 1.3, and no Adreno 650 Vulkan 1.4 entry was found in the list reviewed on 2026-10-15. These are stronger evidence for the supported baseline than fork version strings.

References:
- https://www.collabora.com/news-and-blog/news-and-events/mesa-on-android-how-we-brought-turnip,-skiavk,-and-cuttlefish-to-ci.html
- https://www.khronos.org/conformance/adopters/conformant-products/vulkan

## Capability vs. benefit

**Capability:** Plausible enough to test. A6xx forks repeatedly remove the same generation gate, suggesting the API version is not intrinsically tied to a hardware generation. But these forks mostly change the advertised API level and provide limited or no public CTS evidence. No public evidence reviewed here establishes Vulkan 1.4 conformance specifically on Adreno 650.

**Performance:** Do not expect an automatic FPS uplift from changing Vulkan 1.3 to 1.4. Vulkan 1.4 primarily consolidates promoted functionality and makes a set of features/limits mandatory. It can improve compatibility when software needs Vulkan 1.4 or relies on newly core functionality, but an API-version string alone adds no hardware throughput. Any game performance change would need to be measured against the same Mesa revision, settings, caches and workload.

**Recommendation:** Keep the version-gate probe as an isolated diagnostic experiment, but do not make it the first candidate for a production Vulkan 1.4 build. First collect an unmodified A650 capability report and compare every Vulkan 1.4 requirement against Turnip's actual feature/limit initialization. Then implement only real gaps that are supportable on A650. Run Vulkan 1.4 CTS before promoting. Do not target a hypothetical Vulkan 1.5+ API unless Khronos has ratified that version and published its requirements.
