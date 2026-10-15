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
