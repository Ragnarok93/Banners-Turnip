# Adreno 650 FF7R: comparable Samsung SM8250 KGSL ioctl ENOMEM branches

**Date:** 2026-10-12. **Owner:** Banners-Turnip source/driver research. This is source comparison, **not an assertion that a third-party kernel branch is the stock Samsung SM-G986U1/HXL1 kernel**.

## Problem being tested

The new user capture has first native `FF7R-A650-KGSL-ALLOC stage=gpumem_alloc_id errno=12` during 256 MiB request, four snapshots with MemAvailable only 303–414 MiB, and up to ~498 MiB of process VmSwap. The actual native `KGSL_GPUMEM_ALLOC_ID` kernel failure branch remains unknown.

Many historical Qualcomm kernel trees **unconditionally** add `KGSL_MEMFLAGS_FORCE_32BIT` for the legacy `kgsl_ioctl_gpumem_alloc_id`, even when the userspace Turnip `request_flags` do not include it ([example old kernel](https://android.googlesource.com/kernel/msm/+/0842b275987c3c8e683016d3658bac1a163839d9/drivers/gpu/msm/kgsl.c)). Thus it was worth checking whether the recurring ~4 GiB failure could be a **kernel-injected GPU VA range limit**.

## New comparable SM8250 4.19 code

A publicly available **non-stock** Samsung SM8250 4.19-derived branch is [`notkernel-oss/not_samsung.sm8250-4.19`](https://github.com/notkernel-oss/not_samsung.sm8250-4.19), branch `staging`. It contains `drivers/gpu/msm/kgsl.c`, `kgsl_sharedmem.c`, and `kgsl_mmu.c`. It is useful for source structure but must **not** be passed off as the user's exact firmware kernel.

In [`kgsl.c` near lines 3968–3978](https://github.com/notkernel-oss/not_samsung.sm8250-4.19/blob/staging/drivers/gpu/msm/kgsl.c#L3968-L3978), `kgsl_ioctl_gpumem_alloc_id` sets `KGSL_MEMFLAGS_FORCE_32BIT` **only when `kgsl_is_compat_task()`**, unlike older trees that unconditionally set it. Turnip's current native process is AArch64 and diagnostic request flags show `force_32bit=0`. These points **weaken but do not eliminate** the hypothesis of a kernel-injected legacy 32-bit GPU VA restriction; stock kernel version, compat-task status and effective kernel memory flags would be needed to settle it.

[`kgsl.c` ~3801–3870](https://github.com/notkernel-oss/not_samsung.sm8250-4.19/blob/staging/drivers/gpu/msm/kgsl.c#L3801-L3870) `gpumem_alloc_entry` validates any **single** request `size <= UINT_MAX`. That is **not** a global 4 GiB per-process GPU allocation ceiling. It can return ENOMEM if an entry allocation or a later kernel resource allocation fails. The actual observed native chunk requests in 4–256 MiB range are below that size check.

[`kgsl_sharedmem.c` ~456–473](https://github.com/notkernel-oss/not_samsung.sm8250-4.19/blob/staging/drivers/gpu/msm/kgsl_sharedmem.c#L456-L473) chooses `kgsl_sharedmem_page_alloc_user` for **normal nonsecure IOMMU allocations**, and uses contiguous or secure allocation only in other cases. The normal [`kgsl_sharedmem_page_alloc_user` path](https://github.com/notkernel-oss/not_samsung.sm8250-4.19/blob/staging/drivers/gpu/msm/kgsl_sharedmem.c#L967-L1065) can fail ENOMEM when creating the page-tracking array (`kvcalloc`) or allocating pages/shmem during pressure. `CmaFree=0` in the current user trace is therefore **not itself proof** the particular failing normal KGSL BO needed physically contiguous CMA.

[`kgsl_mmu.c` ~363–375](https://github.com/notkernel-oss/not_samsung.sm8250-4.19/blob/staging/drivers/gpu/msm/kgsl_mmu.c#L363-L375) can also return `-ENOMEM` when GPU VM range assignment cannot be serviced. An errno=12 alone does **not** distinguish physical-page allocation, page-table overhead, or GPU VM address assignment.

## What remains needed to prove true root branch

- Identify/validate the exact SM-G986U1 firmware build's Samsung stock KGSL code, not just another 4.19 source or Mr Purple kernel assumptions. The `Ragnarok93/Root-My-Galaxy-Payloads` investigation may already have that stock kernel image/source; cross-link code there rather than copying it into Turnip if so.
- If the kernel is not instrumentable on the locked bootloader, run **no-ADB controlled pressure A/B** (fresh reboot + fewer background apps + reduced texture streaming) and observe native errno thresholds from our diagnostic ZIP to distinguish pressure-sensitive failure from a repeatable GPU VA/process policy at substantially higher MemAvailable.
- Do not remove BDA, attempt to make a non-compat process mimic 32-bit flags, change kernel memory properties, or force enormous reported heaps to mask the failure.

**Result:** Comparable SM8250 source shows **multiple possible ENOMEM causes**, no evidence of a universal per-process 4 GiB limit in `gpumem_alloc_entry`, and conditional (not unconditional) FORCE_32BIT on modern implementations. Current user data is most consistent with strong memory pressure, but the exact stock kernel return branch remains unproven.
