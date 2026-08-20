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
    assert protocol["status"] == "approved"
    assert protocol["reference_device"]["model"] == "POCO X5 Pro 5G"
    assert protocol["execution_readiness"]["status"] == "blocked"


def test_baseline_enables_only_supported_coco_classes(protocol: dict) -> None:
    enabled = {
        item["id"]: (
            item["baseline"]["coco_contiguous_index"],
            item["baseline"]["coco_category_id"],
            item["baseline"]["model_label_index"],
        )
        for item in protocol["classes"]
        if item["baseline"]["enabled"]
    }

    assert enabled == {
        "person": (0, 1, 0),
        "chair": (56, 62, 61),
        "table_desk": (60, 67, 66),
        "backpack": (24, 27, 26),
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


def test_approval_requires_selected_device(protocol: dict) -> None:
    invalid = deepcopy(protocol)
    invalid["reference_device"]["selection_status"] = "pending"

    with pytest.raises(ProtocolValidationError, match="must be 'selected'"):
        validate_protocol(invalid)


def test_approval_requires_team_approval(protocol: dict) -> None:
    invalid = deepcopy(protocol)
    invalid["approval"]["team_approved"] = False

    with pytest.raises(ProtocolValidationError, match="must be true"):
        validate_protocol(invalid)


def test_blocked_execution_requires_blocking_items(protocol: dict) -> None:
    invalid = deepcopy(protocol)
    invalid["execution_readiness"]["blocking_items"] = []

    with pytest.raises(ProtocolValidationError, match="at least one blocking item"):
        validate_protocol(invalid)


def test_ready_execution_requires_verified_artifact(protocol: dict) -> None:
    invalid = deepcopy(protocol)
    invalid["execution_readiness"] = {"status": "ready", "blocking_items": []}
    invalid["baseline"]["artifact"]["sha256"] = None

    with pytest.raises(ProtocolValidationError, match="SHA-256"):
        validate_protocol(invalid)


def test_ready_execution_accepts_verified_artifact_and_runtime_inventory(
    protocol: dict,
) -> None:
    ready = deepcopy(protocol)
    ready["execution_readiness"] = {"status": "ready", "blocking_items": []}
    ready["baseline"]["artifact"]["sha256"] = "a" * 64
    ready["reference_device"]["runtime_inventory"] = {
        "status": "captured",
        "android_version": "captured-on-device",
        "ram_gb": 8,
        "build_fingerprint_sha256": "b" * 64,
        "app_version": "1.0.0-dev+1",
        "git_commit": "c" * 40,
        "battery_percent_start": 90,
        "thermal_state_start": "nominal",
        "captured_at": "2026-08-19T10:00:00-03:00",
    }

    validate_protocol(ready)
