#!/usr/bin/env python3
"""Fail-closed source test for the experimental A650 Vulkan 1.4 API probe.

This checks patch scope only. It cannot establish device capability or CTS
conformance; those require the built driver running on actual Adreno 650 HW.
"""
from pathlib import Path
import argparse

p = argparse.ArgumentParser()
p.add_argument("--source", type=Path, required=True)
a = p.parse_args()
s = a.source.read_text()

expected = "props->apiVersion = TU_API_VERSION;"
if s.count(expected) != 1:
    raise SystemExit("FAIL: expected the patched Vulkan apiVersion expression once")
if "((pdevice->info->chip >= 7) ? TU_API_VERSION" in s:
    raise SystemExit("FAIL: A7xx generation gate remains in apiVersion")
if "TU_API_VERSION VK_MAKE_VERSION(1, 4" not in s:
    raise SystemExit("FAIL: source TU_API_VERSION is not Vulkan 1.4")
print("PASS: apiVersion gate removed; this is not a feature/limit/CTS result")
