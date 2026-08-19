"""Validation for the versioned MVP experiment protocol.

The protocol is deliberately dependency-free so it can be validated before any
training or inference framework is installed. This keeps scientific decisions
separate from a particular ML implementation.
"""

from __future__ import annotations

import argparse
import json
import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, NoReturn

EXPECTED_CLASS_IDS = {"person", "chair", "table_desk", "backpack", "door"}
REQUIRED_METRIC_IDS = {
    "precision",
    "recall",
    "map_50",
    "map_50_95",
    "inference_latency_p50_ms",
    "inference_latency_p95_ms",
    "end_to_end_latency_p50_ms",
    "end_to_end_latency_p95_ms",
    "false_alerts_per_minute",
    "missed_alert_rate",
}
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class ProtocolValidationError(ValueError):
    """Raised when the experiment protocol violates an invariant."""


def _fail(path: str, message: str) -> NoReturn:
    raise ProtocolValidationError(f"{path}: {message}")


def _mapping(value: Any, path: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        _fail(path, "must be an object")
    return value


def _sequence(value: Any, path: str) -> Sequence[Any]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        _fail(path, "must be an array")
    return value


def _required(mapping: Mapping[str, Any], key: str, path: str) -> Any:
    if key not in mapping:
        _fail(path, f"missing required field '{key}'")
    return mapping[key]


def _non_empty_string(value: Any, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        _fail(path, "must be a non-empty string")
    return value


def _validate_classes(protocol: Mapping[str, Any]) -> None:
    classes = _sequence(_required(protocol, "classes", "$"), "$.classes")
    parsed: dict[str, Mapping[str, Any]] = {}

    for index, raw_class in enumerate(classes):
        path = f"$.classes[{index}]"
        class_definition = _mapping(raw_class, path)
        class_id = _non_empty_string(_required(class_definition, "id", path), f"{path}.id")
        if class_id in parsed:
            _fail(f"{path}.id", f"duplicate class id '{class_id}'")
        parsed[class_id] = class_definition

    actual_ids = set(parsed)
    if actual_ids != EXPECTED_CLASS_IDS:
        missing = sorted(EXPECTED_CLASS_IDS - actual_ids)
        unexpected = sorted(actual_ids - EXPECTED_CLASS_IDS)
        _fail("$.classes", f"class taxonomy mismatch; missing={missing}, unexpected={unexpected}")

    enabled_coco_ids: set[int] = set()
    for class_id, definition in parsed.items():
        path = f"$.classes[{class_id}]"
        _non_empty_string(
            _required(definition, "display_name_pt_br", path), f"{path}.display_name_pt_br"
        )
        baseline = _mapping(_required(definition, "baseline", path), f"{path}.baseline")
        enabled = _required(baseline, "enabled", f"{path}.baseline")
        if not isinstance(enabled, bool):
            _fail(f"{path}.baseline.enabled", "must be boolean")

        coco_id = baseline.get("coco_id")
        source_label = baseline.get("source_label")
        if enabled:
            if not isinstance(coco_id, int) or coco_id < 0:
                _fail(f"{path}.baseline.coco_id", "enabled classes require a non-negative COCO id")
            _non_empty_string(source_label, f"{path}.baseline.source_label")
            if coco_id in enabled_coco_ids:
                _fail(f"{path}.baseline.coco_id", f"duplicate COCO id {coco_id}")
            enabled_coco_ids.add(coco_id)
        elif coco_id is not None or source_label is not None:
            _fail(path, "disabled baseline classes must not claim a COCO mapping")

    if parsed["door"]["baseline"]["enabled"]:
        _fail("$.classes[door]", "door cannot be enabled in the COCO pretrained baseline")


def _validate_split(protocol: Mapping[str, Any]) -> None:
    dataset = _mapping(_required(protocol, "dataset", "$"), "$.dataset")
    split = _mapping(_required(dataset, "split", "$.dataset"), "$.dataset.split")
    percentages = _mapping(
        _required(split, "percentages", "$.dataset.split"), "$.dataset.split.percentages"
    )
    expected_keys = {"train", "validation", "test"}
    if set(percentages) != expected_keys:
        _fail("$.dataset.split.percentages", f"must contain exactly {sorted(expected_keys)}")
    if any(not isinstance(value, int | float) or value <= 0 for value in percentages.values()):
        _fail("$.dataset.split.percentages", "all percentages must be positive numbers")
    if abs(sum(percentages.values()) - 100) > 1e-9:
        _fail("$.dataset.split.percentages", "percentages must sum to 100")
    if split.get("assignment_unit") != "capture_session":
        _fail(
            "$.dataset.split.assignment_unit", "must be 'capture_session' to prevent frame leakage"
        )
    _non_empty_string(split.get("group_key"), "$.dataset.split.group_key")
    if not isinstance(split.get("seed"), int):
        _fail("$.dataset.split.seed", "must be an integer")


def _validate_metrics(protocol: Mapping[str, Any]) -> None:
    metrics = _sequence(_required(protocol, "metrics", "$"), "$.metrics")
    metric_ids: set[str] = set()
    for index, raw_metric in enumerate(metrics):
        path = f"$.metrics[{index}]"
        metric = _mapping(raw_metric, path)
        metric_id = _non_empty_string(_required(metric, "id", path), f"{path}.id")
        if metric_id in metric_ids:
            _fail(f"{path}.id", f"duplicate metric id '{metric_id}'")
        metric_ids.add(metric_id)
        if metric.get("status") != "hypothesis":
            _fail(
                f"{path}.status",
                "must remain 'hypothesis' until an experiment result is recorded elsewhere",
            )
        if metric.get("measured_value") is not None:
            _fail(f"{path}.measured_value", "must be null in the pre-experiment protocol")
        _non_empty_string(metric.get("measurement"), f"{path}.measurement")

    missing = REQUIRED_METRIC_IDS - metric_ids
    if missing:
        _fail("$.metrics", f"missing required metrics: {sorted(missing)}")


def _validate_privacy(protocol: Mapping[str, Any]) -> None:
    privacy = _mapping(_required(protocol, "privacy", "$"), "$.privacy")
    required_false = {
        "persist_images_in_app",
        "upload_images_from_app",
        "facial_recognition",
        "identity_inference",
        "include_minors_in_initial_dataset",
    }
    for field in required_false:
        if privacy.get(field) is not False:
            _fail(f"$.privacy.{field}", "must be false for the initial MVP protocol")
    if privacy.get("explicit_consent_required_for_recorded_collection") is not True:
        _fail("$.privacy.explicit_consent_required_for_recorded_collection", "must be true")
    if privacy.get("delete_raw_data_after_days") != 30:
        _fail("$.privacy.delete_raw_data_after_days", "initial retention must be 30 days")


def _validate_approval_gates(protocol: Mapping[str, Any]) -> None:
    status = protocol.get("status")
    if status not in {"proposed", "approved"}:
        _fail("$.status", "must be 'proposed' or 'approved'")

    baseline = _mapping(_required(protocol, "baseline", "$"), "$.baseline")
    artifact = _mapping(_required(baseline, "artifact", "$.baseline"), "$.baseline.artifact")
    device = _mapping(_required(protocol, "reference_device", "$"), "$.reference_device")
    approval = _mapping(_required(protocol, "approval", "$"), "$.approval")

    if status == "approved":
        digest = artifact.get("sha256")
        if not isinstance(digest, str) or not SHA256_PATTERN.fullmatch(digest):
            _fail(
                "$.baseline.artifact.sha256",
                "approved protocols require a lowercase SHA-256 digest",
            )
        if artifact.get("license_review_status") != "approved":
            _fail(
                "$.baseline.artifact.license_review_status",
                "must be approved before protocol approval",
            )
        for field in ("manufacturer", "model", "android_version", "ram_gb"):
            if device.get(field) in {None, ""}:
                _fail(f"$.reference_device.{field}", "must identify the physical reference device")
        if approval.get("team_approved") is not True:
            _fail("$.approval.team_approved", "must be true")
        _non_empty_string(approval.get("approved_by"), "$.approval.approved_by")
        _non_empty_string(approval.get("approved_at"), "$.approval.approved_at")


def validate_protocol(protocol: Mapping[str, Any]) -> None:
    """Validate protocol structure and cross-field scientific invariants."""

    if protocol.get("schema_version") != 1:
        _fail("$.schema_version", "only schema version 1 is supported")
    _non_empty_string(protocol.get("protocol_id"), "$.protocol_id")
    _validate_classes(protocol)
    _validate_split(protocol)
    _validate_metrics(protocol)
    _validate_privacy(protocol)
    _validate_approval_gates(protocol)


def load_and_validate_protocol(path: str | Path) -> dict[str, Any]:
    """Load a UTF-8 JSON protocol, validate it, and return the parsed data."""

    protocol_path = Path(path)
    with protocol_path.open(encoding="utf-8") as source:
        data = json.load(source)
    protocol = dict(_mapping(data, "$"))
    validate_protocol(protocol)
    return protocol


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the Eyes MVP experiment protocol")
    parser.add_argument(
        "path",
        nargs="?",
        default="config/experiment.v1.json",
        help="path to the protocol JSON",
    )
    args = parser.parse_args()
    try:
        protocol = load_and_validate_protocol(args.path)
    except (OSError, json.JSONDecodeError, ProtocolValidationError) as error:
        parser.exit(1, f"protocol validation failed: {error}\n")
    print(f"protocol {protocol['protocol_id']} is valid ({protocol['status']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
