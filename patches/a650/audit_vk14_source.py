#!/usr/bin/env python3
"""Collect a source-level Vulkan 1.4 requirements screening report.

This intentionally does not call the driver compliant: conditional capability
expressions must be checked on-device, and only Vulkan CTS can establish
conformance. It fails if core assignments disappear so source drift is visible.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import re

p = argparse.ArgumentParser()
p.add_argument("--source", type=Path, required=True,
               help="C/C++ source file or directory to scan recursively")
p.add_argument("--output", type=Path, required=True)
a = p.parse_args()
if a.source.is_dir():
    source_files = sorted(
        path for path in a.source.rglob("*")
        if path.is_file() and path.suffix in {".c", ".cc", ".cpp", ".h", ".hh", ".hpp"}
    )
else:
    source_files = [a.source]
if not source_files:
    raise SystemExit(f"No C/C++ source files found under {a.source}")

requirements = {
    "features": [
        "largePoints", "shaderImageGatherExtended", "shaderInt16",
        "storageBuffer16BitAccess", "shaderInt8", "storageBuffer8BitAccess",
        "variablePointers", "variablePointersStorageBuffer", "bresenhamLines",
        "pushDescriptor", "dynamicRenderingLocalRead", "scalarBlockLayout",
        "shaderSubgroupRotate", "maintenance5", "maintenance6",
    ],
    "limits": [
        "maxBoundDescriptorSets", "maxColorAttachments",
        "timestampComputeAndGraphics", "maxImageDimension3D",
        "maxPushConstantsSize", "maxViewportDimensions", "viewportBoundsRange",
    ],
}
report = {
    "scope": "static source screening only; not device capability or CTS",
    "source": str(a.source),
    "source_files_scanned": len(source_files),
    "features": {},
    "limits": {},
    "missing": [],
}
for category, fields in requirements.items():
    for field in fields:
        hits = []
        # Mesa uses both feature-struct assignments and nested VkPhysicalDeviceLimits
        # assignments such as props->limits.maxViewportDimensions.
        pattern = re.compile(
            r"\b(?:features|props)->(?:limits\.)?" + re.escape(field) + r"(?:\s*\[[^\]]+\])*\s*="
        )
        for source_file in source_files:
            lines = source_file.read_text(errors="replace").splitlines()
            for i, line in enumerate(lines):
                if pattern.search(line):
                    expr = line.strip()
                    # Keep the first continuation line for conditional assignments.
                    if expr.rstrip().endswith("=") and i + 1 < len(lines):
                        expr += " " + lines[i + 1].strip()
                    hits.append({
                        "file": str(source_file),
                        "line": i + 1,
                        "assignment": expr,
                    })
        report[category][field] = hits
        if not hits:
            report["missing"].append(f"{category}.{field}")
report["review_required"] = [
    "Evaluate conditional storageBuffer16BitAccess/storageBuffer8BitAccess values on real Adreno 650.",
    "Query all Vulkan 1.4 mandatory features, limits, extensions and queue-family flags from the built driver.",
    "Compare runtime output against the exact ratified Vulkan 1.4 specification.",
    "Run Vulkan 1.4 CTS on the exact driver binary/device; do not infer compliance from source or API version.",
]
a.output.write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps({"missing": report["missing"], "report": str(a.output),
                  "classification": report["scope"]}))
if report["missing"]:
    raise SystemExit("Missing expected Vulkan 1.4 source assignments; review source drift")
