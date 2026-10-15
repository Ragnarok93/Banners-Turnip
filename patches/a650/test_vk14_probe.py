#!/usr/bin/env python3
"""Fail-closed source test for the experimental A650 Vulkan 1.4 API probe.

This checks patch scope only. It cannot establish device capability or CTS
conformance; those require the built driver running on actual Adreno 650 HW.
"""
from pathlib import Path
import argparse
import subprocess

p = argparse.ArgumentParser()
p.add_argument("--source", type=Path, required=True)
a = p.parse_args()
s = a.source.read_text()

expected = """   props->apiVersion =
      tu_has_multiview(pdevice) ?
         TU_API_VERSION
         : VK_MAKE_VERSION(1, 0, VK_HEADER_VERSION);"""
if s.count(expected) != 1:
    raise SystemExit("FAIL: expected the exact Vulkan 1.4 probe apiVersion expression once")
if "pdevice->info->chip >= 7" in s[s.find("tu_get_properties"):s.find("tu_get_properties") + 5000]:
    raise SystemExit("FAIL: generation gate remains in tu_get_properties")
if "TU_API_VERSION VK_MAKE_VERSION(1, 4" not in s:
    raise SystemExit("FAIL: source TU_API_VERSION is not Vulkan 1.4")
print("PASS: only the apiVersion generation gate is absent; this is not a feature/CTS result")
