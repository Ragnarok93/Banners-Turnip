#!/usr/bin/env python3
"""Aggregate per-profile build/package measurements; not GPU performance."""
import csv
import json
from pathlib import Path
import statistics
import sys

root = Path(sys.argv[1] if len(sys.argv) > 1 else "downloaded")
output = Path(sys.argv[2] if len(sys.argv) > 2 else "summary")
output.mkdir(parents=True, exist_ok=True)
files = sorted(root.rglob("candidate-results/*.json"))
rows = []
for path in files:
    try:
        row = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        print(f"Skipping unreadable result {path}: {exc}", file=sys.stderr)
        continue
    if row.get("classification") != "BUILD_AND_PACKAGE_METRICS_NOT_GPU_PERFORMANCE":
        continue
    rows.append(row)
if not rows:
    raise SystemExit(f"No candidate metric JSON files found under {root}")
rows.sort(key=lambda r: r["profile"])
fields = ["profile", "mesaCommit", "buildElapsedSeconds", "archiveBytes", "archiveSha256",
          "driverSha256", "pipelineSuballocA650KiB", "pipelineSuballoc256kPatchApplied",
          "programReference", "renderModeA650", "appliedPatches", "classification"]
with (output / "candidate-comparison.csv").open("w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        row["appliedPatches"] = ";".join(row.get("appliedPatches") or [])
        writer.writerow(row)
baseline = next((r for r in rows if r["profile"] == "generic"), None)
pipeline = next((r for r in rows if r["profile"] == "sd865-pipeline-512k"), None)
lines = [
    "# A650 Pre-Device Candidate Build Comparison", "",
    "**These are build/package measurements, not driver runtime or GPU performance.**",
    "",
    f"- Candidate profiles with results: {len(rows)}",
    f"- Mesa revisions represented: {len({r.get('mesaCommit') for r in rows})}",
]
if len({r.get("mesaCommit") for r in rows}) != 1:
    lines += ["- WARNING: results do not share a single Mesa SHA; do not compare them as a controlled matrix."]
lines += ["", "| Profile | Build time (s) | Archive (bytes) | Pipeline suballoc (KiB) | Program reference | Render mode |", "|---|---:|---:|---:|---|---|"]
for row in rows:
    lines.append(f"| {row['profile']} | {row.get('buildElapsedSeconds', '')} | {row.get('archiveBytes', '')} | {row.get('pipelineSuballocA650KiB', '')} | {row.get('programReference', '')} | {row.get('renderModeA650', '')} |")
if baseline and pipeline:
    lines += ["", "## Controls", "",
              f"- Generic baseline build duration: {baseline.get('buildElapsedSeconds')} s.",
              f"- 512 KiB candidate build duration: {pipeline.get('buildElapsedSeconds')} s.",
              "- Differences in build duration can reflect runner noise and compile/cache behavior; they are not evidence of in-game FPS differences."]
(output / "candidate-comparison.md").write_text("\n".join(lines) + "\n")
print("\n".join(lines))
