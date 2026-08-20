from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from eyes_project_ai.model_manifest import load_manifest
from eyes_project_ai.tflite_runner import TFLiteDetector

ROOT = Path(__file__).parents[1]
MODEL_PATH = ROOT / "artifacts" / "models" / "efficientdet-lite0.tflite"


def test_official_model_opens_and_runs_black_frame_smoke() -> None:
    if not MODEL_PATH.is_file():
        pytest.skip("run eyes_project_ai.acquire_model to enable the real-model smoke test")
    manifest = load_manifest(ROOT / "config" / "model-manifest.v1.json")
    detector = TFLiteDetector(MODEL_PATH, manifest, num_threads=4)

    result = detector.infer(Image.new("RGB", (640, 480)), score_threshold=0.4)

    assert result.inference_latency_ms > 0
    assert result.detections == ()
