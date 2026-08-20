"""Open the real model with LiteRT and verify its executable tensor contract."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from eyes_project_ai.model_manifest import load_manifest, verify_artifact
from eyes_project_ai.tflite_runner import validate_interpreter_contract


def inspect_model(model_path: str | Path, manifest_path: str | Path) -> dict[str, object]:
    """Validate integrity, allocate tensors and run a deterministic smoke invocation."""

    from ai_edge_litert.interpreter import Interpreter

    manifest = load_manifest(manifest_path)
    labels = verify_artifact(model_path, manifest)
    interpreter = Interpreter(model_path=str(model_path), num_threads=4)
    interpreter.allocate_tensors()
    input_index, output_indices = validate_interpreter_contract(interpreter, manifest)
    interpreter.set_tensor(input_index, np.zeros(manifest.input.shape, dtype=np.uint8))
    interpreter.invoke()
    observed_shapes = {
        semantic: list(interpreter.get_tensor(index).shape)
        for semantic, index in output_indices.items()
    }
    return {
        "model_id": manifest.model_id,
        "model_version": manifest.model_version,
        "sha256": manifest.artifact_sha256,
        "license": manifest.license_spdx_id,
        "labels": len(labels),
        "enabled_classes": [item.domain_id for item in manifest.enabled_classes],
        "observed_output_shapes": observed_shapes,
        "smoke_inference": "passed",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect the approved TFLite model contract")
    parser.add_argument("--model", default="artifacts/models/efficientdet-lite0.tflite")
    parser.add_argument("--manifest", default="config/model-manifest.v1.json")
    args = parser.parse_args()
    try:
        result = inspect_model(args.model, args.manifest)
    except (OSError, ValueError, RuntimeError) as error:
        parser.exit(1, f"model inspection failed: {error}\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
