"""Traceable model smoke and synthetic host timing; never physical acceptance."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import sys
from importlib.metadata import version
from pathlib import Path
from time import perf_counter_ns

import numpy as np

from eyes_project_ai.inspect_model import inspect_model
from eyes_project_ai.model_manifest import load_manifest
from eyes_project_ai.tflite_runner import validate_interpreter_contract


def source_commit(root: Path) -> str:
    def git(*args: str) -> str:
        return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()

    commit = git("rev-parse", "HEAD")
    if len(commit) != 40 or any(c not in "0123456789abcdef" for c in commit):
        raise ValueError("invalid source commit")
    if git("status", "--porcelain"):
        raise ValueError("CI report requires a clean checkout")
    return commit


def build_report(root: Path, model: Path) -> dict:
    from ai_edge_litert.interpreter import Interpreter

    commit = source_commit(root)
    manifest_path = root / "config/model-manifest.v1.json"
    smoke = inspect_model(model, manifest_path)
    manifest = load_manifest(manifest_path)
    interpreter = Interpreter(model_path=str(model), num_threads=4)
    interpreter.allocate_tensors()
    input_index, _ = validate_interpreter_contract(interpreter, manifest)
    interpreter.set_tensor(input_index, np.zeros(manifest.input.shape, dtype=np.uint8))
    for _ in range(3):
        interpreter.invoke()
    durations = []
    for _ in range(20):
        start = perf_counter_ns()
        interpreter.invoke()
        durations.append((perf_counter_ns() - start) / 1_000_000)
    # Check again after invocation: do not label a changed source tree as clean.
    if source_commit(root) != commit:
        raise ValueError("source changed during measurement")
    return {
        "schema_version": 1,
        "source": {"commit": commit, "clean": True},
        "runtime": {
            "python": sys.version.split()[0],
            "litert": version("ai-edge-litert"),
            "platform": platform.platform(),
            "threads": 4,
        },
        "inputs": {
            name: hashlib.sha256((root / name).read_bytes()).hexdigest()
            for name in (
                "config/model-manifest.v1.json",
                "config/experiment.v1.json",
                "config/assistive-evaluation.v1.json",
                "uv.lock",
            )
        },
        "model_smoke": smoke,
        "host_benchmark": {
            "scope": "synthetic_zero_tensor_inference_on_build_host",
            "warmup_invocations": 3,
            "samples": len(durations),
            "unit": "ms",
            "p50": float(np.percentile(durations, 50)),
            "p95": float(np.percentile(durations, 95)),
            "raw_samples": durations,
        },
        "physical_device_executed": False,
        "scientific_acceptance": False,
        "limits": [
            "Black synthetic input; no room corpus or detection accuracy.",
            "Build-host timing; no Android/camera/TTS latency or production gate.",
            "REN-34/35/37/69 remain responsible for experimental evidence.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default="artifacts/models/efficientdet-lite0.tflite")
    parser.add_argument("--output", default="artifacts/ci/model-smoke-host-benchmark.json")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    output = Path(args.output).resolve()
    try:
        if output.exists():
            raise ValueError("report already exists; do not overwrite prior evidence")
        report = build_report(root, Path(args.model))
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("x", encoding="utf-8") as stream:
            json.dump(report, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.write("\n")
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"CI report failed: {error}\n")
    print(f"Model smoke and host-only timing saved for {report['source']['commit']}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
