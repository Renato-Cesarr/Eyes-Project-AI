from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from eyes_project_ai.model_manifest import load_manifest
from eyes_project_ai.tflite_runner import (
    InferenceContractError,
    decode_detections,
    prepare_image,
    validate_interpreter_contract,
)

MANIFEST = load_manifest(Path(__file__).parents[1] / "config" / "model-manifest.v1.json")


class FakeInterpreter:
    def __init__(self, *, invalid_input_shape: bool = False) -> None:
        shape = [1, 321, 320, 3] if invalid_input_shape else list(MANIFEST.input.shape)
        self._inputs = [
            {
                "name": MANIFEST.input.name,
                "shape": np.asarray(shape),
                "dtype": np.uint8,
                "index": 7,
            }
        ]
        self._outputs = [
            {
                "name": contract.name,
                "shape": np.asarray(contract.shape),
                "dtype": np.dtype(contract.dtype).type,
                "index": index,
            }
            for index, contract in enumerate(MANIFEST.outputs.values(), start=20)
        ]

    def get_input_details(self):
        return self._inputs

    def get_output_details(self):
        return self._outputs


def test_preprocessing_produces_approved_uint8_rgb_tensor() -> None:
    image = Image.new("RGBA", (640, 480), color=(10, 20, 30, 128))

    tensor = prepare_image(image, MANIFEST.input)

    assert tensor.shape == (1, 320, 320, 3)
    assert tensor.dtype == np.uint8
    assert tensor[0, 0, 0].tolist() == [10, 20, 30]


def test_interpreter_contract_matches_tensors_by_name() -> None:
    input_index, output_indices = validate_interpreter_contract(FakeInterpreter(), MANIFEST)

    assert input_index == 7
    assert set(output_indices) == {"boxes", "classes", "scores", "count"}


def test_interpreter_contract_rejects_shape_drift() -> None:
    with pytest.raises(InferenceContractError, match="input tensor shape mismatch"):
        validate_interpreter_contract(FakeInterpreter(invalid_input_shape=True), MANIFEST)


def test_decoder_filters_threshold_and_unapproved_classes() -> None:
    boxes = np.asarray(
        [[[0.1, 0.2, 0.8, 0.9], [0.0, 0.0, 0.5, 0.5], [0.2, 0.2, 0.3, 0.3]]],
        dtype=np.float32,
    )
    classes = np.asarray([[61.0, 2.0, 26.0]], dtype=np.float32)
    scores = np.asarray([[0.9, 0.99, 0.2]], dtype=np.float32)
    count = np.asarray([3.0], dtype=np.float32)

    detections = decode_detections(
        MANIFEST,
        boxes=boxes,
        classes=classes,
        scores=scores,
        count=count,
        score_threshold=0.4,
    )

    assert len(detections) == 1
    assert detections[0].domain_id == "chair"
    assert detections[0].display_name_pt_br == "cadeira"
    assert detections[0].bounding_box.xmax == pytest.approx(0.9)


def test_decoder_clips_boxes_and_rejects_invalid_threshold() -> None:
    boxes = np.asarray([[[-0.1, -0.2, 1.2, 1.1]]], dtype=np.float32)
    classes = np.asarray([[0.0]], dtype=np.float32)
    scores = np.asarray([[0.8]], dtype=np.float32)
    count = np.asarray([1.0], dtype=np.float32)

    detections = decode_detections(
        MANIFEST,
        boxes=boxes,
        classes=classes,
        scores=scores,
        count=count,
        score_threshold=0.4,
    )
    assert detections[0].bounding_box.ymin == 0.0
    assert detections[0].bounding_box.xmax == 1.0

    with pytest.raises(ValueError, match="between 0 and 1"):
        decode_detections(
            MANIFEST,
            boxes=boxes,
            classes=classes,
            scores=scores,
            count=count,
            score_threshold=1.1,
        )
