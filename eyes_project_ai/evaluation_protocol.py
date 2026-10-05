"""Validate the shared pre-experiment contract without a model runtime."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


class EvaluationProtocolError(ValueError):
    """Invalid shared evaluation contract."""


def load_evaluation_protocol(path: Path, expected_sha256: str) -> dict:
    text = path.read_text(encoding="utf-8").replace("\r\n", "\n")
    if hashlib.sha256(text.encode()).hexdigest() != expected_sha256:
        raise EvaluationProtocolError("evaluation protocol SHA-256 mismatch")
    data = json.loads(text)
    try:
        validate_evaluation_protocol(data)
    except (KeyError, TypeError) as error:
        raise EvaluationProtocolError("malformed evaluation contract") from error
    return data


def validate_evaluation_protocol(data: dict) -> None:
    def require(condition: bool, reason: str) -> None:
        if not condition:
            raise EvaluationProtocolError(reason)

    require(data.get("schema_version") == 1, "evaluation schema must be 1")
    require(data.get("protocol_id") == "eyes-assistive-evaluation-v1", "evaluation id mismatch")
    require(data.get("status") == "pre_experiment", "evaluation is pre-experiment")
    require(
        data.get("classes")
        == {"person": "person", "chair": "chair", "table_desk": "table", "backpack": "backpack"},
        "class mapping mismatch",
    )
    require(
        data["proximity"]["bands"] == ["distant", "attention", "veryNear"],
        "proximity must remain categorical",
    )
    latency = data["latency"]
    require(latency["unit"] == "ms", "latency unit must be ms")
    require(
        latency["gates_ms"]
        == {"inference_p95": 250, "camera_to_queue_p95": 500, "camera_to_tts_p95": 300},
        "preserve the three distinct latency gates",
    )
    require(latency["minimum_samples_per_configuration"] >= 300, "require 300 latency samples")
    require(latency["minimum_samples_scope"] == "inference_only", "300 applies to inference")
    require(
        latency["tts_sample_plan"]["target_pairs_per_configuration"] >= 100
        and latency["tts_sample_plan"]["status"] == "proposed_engineering_target",
        "TTS sampling proposal must remain explicit",
    )
    require(
        latency["warmup_frames"] >= 30 and latency["warmup_seconds"] >= 5,
        "preserve warmup requirements",
    )
    detection = data["detection"]
    require(
        detection["minimum_independent_sessions"] >= 30
        and detection["minimum_test_instances_per_class"] >= 30,
        "preserve corpus minimums",
    )
    require(
        detection["gates"]
        == {
            "precision": 0.6,
            "recall": 0.6,
            "map_50": 0.5,
            "false_alerts_per_minute": 1,
            "missed_annotated_event_rate": 0.4,
        },
        "preserve detection gates",
    )
    require(
        detection["split"]
        == {
            "train": 70,
            "validation": 15,
            "test": 15,
            "seed": 33033,
            "group_key": "room_id + capture_session_id",
        },
        "preserve independent session split",
    )
    segments = data["assistive_segments"]
    require(
        segments["calibration"] >= 48
        and segments["evaluation"] >= 24
        and segments["negative_minimum"] >= 6,
        "preserve independent segment minimums",
    )
    require(data["sustained"]["duration_minutes"] >= 20, "sustained window must cover 20 minutes")
    require(
        data["sustained"]["battery_consumption_requires_unplugged"] is True,
        "battery consumption requires unplugged operation",
    )
    for section in ("latency", "detection", "sustained"):
        require(data[section]["measured_values"] is None, "results must remain separate")
    require(
        data["readiness"]["status"] == "blocked" and data["readiness"]["current_results"] is None,
        "do not claim completed collection",
    )
    require(
        data["report_requirements"]["legacy_single_file_purposes"] == ["fixture", "pilot"],
        "legacy captures cannot establish final evaluation",
    )
