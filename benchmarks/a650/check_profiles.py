#!/usr/bin/env python3
"""Static checks for A650 profile isolation; no GPU claims are made."""
from pathlib import Path
import re
import sys
root = Path(__file__).resolve().parents[2]
builder = (root / "build_turnip_perf.sh").read_text()
workflow = (root / ".github/workflows/a650-synthetic-benchmark.yml").read_text()
profiles = ["generic", "sd865-cortex-a77", "sd865-program-reference", "sd865-pipeline-512k", "sd865-pipeline-256k", "sd865-sysmem-screen", "sd865-combined-512k", "sd865-combined-sysmem"]
missing = [p for p in profiles if p not in builder or p not in workflow]
if missing:
    print("Missing candidate profile(s): " + ", ".join(missing), file=sys.stderr)
    raise SystemExit(1)
def profile_block(name: str) -> str:
    match = re.search(r"(?ms)^\t" + re.escape(name) + r"\)\n(.*?)(?=^\t[a-z0-9-]+\)|^\t\*\))", builder)
    if not match:
        raise AssertionError(f"Could not isolate {name} profile block")
    return match.group(1)
pipeline = profile_block("sd865-pipeline-512k")
assert "pipeline_512k=1" in pipeline and "program_reference=1" not in pipeline and "sysmem_screen=1" not in pipeline
pipeline256 = profile_block("sd865-pipeline-256k")
assert "pipeline_256k=1" in pipeline256 and "pipeline_512k=1" not in pipeline256
assert "program_reference=1" not in pipeline256 and "sysmem_screen=1" not in pipeline256
sysmem = profile_block("sd865-sysmem-screen")
assert "sysmem_screen=1" in sysmem and "pipeline_512k=1" not in sysmem and "program_reference=1" not in sysmem
patch = (root / "patches/sd865/0002-tu-a650-pipeline-suballoc-512k.patch").read_text()
assert "fd_dev_gpu_id(&physical_device->dev_id) == 650" in patch and "512 : 128" in patch
patch256 = (root / "patches/sd865/0004-tu-a650-pipeline-suballoc-256k.patch").read_text()
assert "fd_dev_gpu_id(&physical_device->dev_id) == 650" in patch256 and "256 : 128" in patch256
reference = (root / "patches/sd865/0001-tu-reference-bound-program-state.patch").read_text()
assert "struct tu_program_state *program" in reference and "cmd->state.program = &pipeline->program" in reference and "tu_null_program_state" in reference
print("PASS: seven profiles present; pipeline-only and SYSMEM-only controls remain isolated.")
print("NOTE: static checks do not establish runtime safety or performance.")
