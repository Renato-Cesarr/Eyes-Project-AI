from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

from eyes_project_ai.protocol import (
    ProtocolValidationError,
    load_and_validate_protocol,
    validate_protocol,
)

PROTOCOL_PATH = Path(__file__).parents[1] / "config" / "experiment.v1.json"


@pytest.fixture
def protocol() -> dict:
    return load_and_validate_protocol(PROTOCOL_PATH)


def test_versioned_protocol_is_valid(protocol: dict) -> None:
    assert protocol["protocol_id"] == "eyes-mvp-object-detection-v1"
    assert protocol["status"] == "proposed"


def test_baseline_enables_only_supported_coco_classes(protocol: dict) -> None:
    enabled = {
        item["id"]: item["baseline"]["coco_id"]
        for item in protocol["classes"]
        if item["baseline"]["enabled"]
    }

    assert enabled == {
        "person": 0,
        "chair": 56,
        "table_desk": 60,
        "backpack": 24,
    }


def test_duplicate_class_is_rejected(protocol: dict) -> None:
    invalid = deepcopy(protocol)
    invalid["classes"][1]["id"] = "person"

    with pytest.raises(ProtocolValidationError, match="duplicate class id"):
        validate_protocol(invalid)


def test_frame_level_split_is_rejected(protocol: dict) -> None:
    invalid = deepcopy(protocol)
    invalid["dataset"]["split"]["assignment_unit"] = "frame"

    with pytest.raises(ProtocolValidationError, match="prevent frame leakage"):
        validate_protocol(invalid)


def test_pre_experiment_protocol_rejects_claimed_result(protocol: dict) -> None:
    invalid = deepcopy(protocol)
    invalid["metrics"][0]["measured_value"] = 0.99

    with pytest.raises(ProtocolValidationError, match="must be null"):
        validate_protocol(invalid)


def test_initial_protocol_rejects_image_persistence(protocol: dict) -> None:
    invalid = deepcopy(protocol)
    invalid["privacy"]["persist_images_in_app"] = True

    with pytest.raises(ProtocolValidationError, match="must be false"):
        validate_protocol(invalid)


def test_approval_requires_artifact_device_and_team(protocol: dict) -> None:
    invalid = deepcopy(protocol)
    invalid["status"] = "approved"

    with pytest.raises(ProtocolValidationError, match="SHA-256"):
        validate_protocol(invalid)
