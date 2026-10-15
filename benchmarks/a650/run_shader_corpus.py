#!/usr/bin/env python3
"""Repeatable host GLSL compilation proxy; not an IR3 or GPU benchmark."""
from __future__ import annotations
import argparse, csv, hashlib, json, platform, shutil, statistics, subprocess, tempfile, time
from pathlib import Path
def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repetitions", type=int, default=5, choices=(1, 3, 5, 7))
    ap.add_argument("--output", type=Path, default=Path("results"))
    args = ap.parse_args()
    compiler = shutil.which("glslangValidator")
    if not compiler:
        raise SystemExit("glslangValidator not found")
    root = Path(__file__).resolve().parent / "shaders"
    shaders = sorted(root.glob("*.vert")) + sorted(root.glob("*.frag")) + sorted(root.glob("*.comp"))
    if not shaders:
        raise SystemExit(f"No shader fixtures found in {root}")
    args.output.mkdir(parents=True, exist_ok=True)
    records = []
    with tempfile.TemporaryDirectory(prefix="a650-shader-corpus-") as temp:
        tempdir = Path(temp)
        for shader in shaders:
            subprocess.run([compiler, "-V", str(shader), "-o", str(tempdir / (shader.name + ".warm.spv"))], check=True, capture_output=True, text=True)
        for rep in range(1, args.repetitions + 1):
            for shader in shaders:
                output = tempdir / f"r{rep}-{shader.name}.spv"
                start = time.perf_counter_ns()
                proc = subprocess.run([compiler, "-V", str(shader), "-o", str(output)], capture_output=True, text=True)
                elapsed = time.perf_counter_ns() - start
                if proc.returncode:
                    raise RuntimeError(f"{shader.name} failed on repetition {rep}: {proc.stderr}")
                records.append({"repetition": rep, "shader": shader.name, "stage": shader.suffix[1:], "elapsedNs": elapsed, "outputSha256": sha256(output), "sourceSha256": sha256(shader)})
    by_shader = {}
    for shader in shaders:
        rows = [r for r in records if r["shader"] == shader.name]
        timings = [r["elapsedNs"] / 1e6 for r in rows]
        hashes = {r["outputSha256"] for r in rows}
        if len(hashes) != 1:
            raise RuntimeError(f"Non-deterministic compiler output for {shader.name}")
        by_shader[shader.name] = {"stage": shader.suffix[1:], "sourceSha256": rows[0]["sourceSha256"], "outputSha256": rows[0]["outputSha256"], "samples": len(timings), "medianMs": statistics.median(timings), "minMs": min(timings), "maxMs": max(timings), "spreadMs": max(timings) - min(timings)}
    all_ms = [r["elapsedNs"] / 1e6 for r in records]
    version = subprocess.run([compiler, "--version"], check=True, capture_output=True, text=True).stdout.strip()
    summary = {"classification": "HOST_GLSLANG_FRONTEND_PROXY_NOT_TURNIP_IR3_OR_GPU_PERFORMANCE", "runnerPlatform": platform.platform(), "pythonVersion": platform.python_version(), "compilerPath": compiler, "compilerVersion": version, "repetitions": args.repetitions, "shaderCount": len(shaders), "successfulCompiles": len(records), "medianCompileMs": statistics.median(all_ms), "minCompileMs": min(all_ms), "maxCompileMs": max(all_ms), "shaders": by_shader, "records": records}
    (args.output / "shader-corpus.json").write_text(json.dumps(summary, indent=2) + "\n")
    with (args.output / "shader-corpus.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["repetition", "shader", "stage", "elapsedNs", "outputSha256", "sourceSha256"])
        writer.writeheader()
        writer.writerows(records)
    markdown = ["# A650 Host Shader-Corpus Proxy", "", "**Not a Turnip IR3 benchmark and not GPU performance.** This measures host GLSL-to-SPIR-V compilation with glslangValidator; the Turnip profile does not affect these timings.", "", f"- Compiler: {version}", f"- Fixtures: {len(shaders)}", f"- Repetitions: {args.repetitions}", f"- Successful measured compiles: {len(records)}", f"- Median per compile: {statistics.median(all_ms):.3f} ms", "", "| Shader | Median (ms) | Spread (ms) | Output deterministic |", "|---|---:|---:|---|"]
    for name, row in by_shader.items():
        markdown.append(f"| {name} | {row['medianMs']:.3f} | {row['spreadMs']:.3f} | yes |")
    (args.output / "shader-corpus.md").write_text("\n".join(markdown) + "\n")
    print("\n".join(markdown))
    return 0
if __name__ == "__main__":
    raise SystemExit(main())
