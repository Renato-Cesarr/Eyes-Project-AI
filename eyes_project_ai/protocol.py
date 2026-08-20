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
GIT_COMMIT_PATTERN = re.compile(r"^[0-9a-f]{7,40}$")


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

    enabled_coco_indices: set[int] = set()
    enabled_model_indices: set[int] = set()
    for class_id, definition in parsed.items():
        path = f"$.classes[{class_id}]"
        _non_empty_string(
            _required(definition, "display_name_pt_br", path), f"{path}.display_name_pt_br"
        )
        baseline = _mapping(_required(definition, "baseline", path), f"{path}.baseline")
        enabled = _required(baseline, "enabled", f"{path}.baseline")
        if not isinstance(enabled, bool):
            _fail(f"{path}.baseline.enabled", "must be boolean")

        coco_index = baseline.get("coco_contiguous_index")
        coco_category_id = baseline.get("coco_category_id")
        model_label_index = baseline.get("model_label_index")
        source_label = baseline.get("source_label")
        if enabled:
            if not isinstance(coco_index, int) or coco_index < 0:
                _fail(
                    f"{path}.baseline.coco_contiguous_index",
                    "enabled classes require a non-negative contiguous COCO index",
                )
            if not isinstance(coco_category_id, int) or coco_category_id <= 0:
                _fail(
                    f"{path}.baseline.coco_category_id",
                    "enabled classes require a positive official COCO category id",
                )
            if not isinstance(model_label_index, int) or model_label_index < 0:
                _fail(
                    f"{path}.baseline.model_label_index",
                    "enabled classes require a non-negative model label index",
                )
            _non_empty_string(source_label, f"{path}.baseline.source_label")
            if coco_index in enabled_coco_indices:
                _fail(
                    f"{path}.baseline.coco_contiguous_index",
                    f"duplicate COCO contiguous index {coco_index}",
                )
            if model_label_index in enabled_model_indices:
                _fail(
                    f"{path}.baseline.model_label_index",
                    f"duplicate model label index {model_label_index}",
                )
            enabled_coco_indices.add(coco_index)
            enabled_model_indices.add(model_label_index)
        elif any(
            value is not None
            for value in (coco_index, coco_category_id, model_label_index, source_label)
        ):
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


def _validate_status_and_execution_gates(protocol: Mapping[str, Any]) -> None:
    status = protocol.get("status")
    if status not in {"proposed", "approved"}:
        _fail("$.status", "must be 'proposed' or 'approved'")

    baseline = _mapping(_required(protocol, "baseline", "$"), "$.baseline")
    artifact = _mapping(_required(baseline, "artifact", "$.baseline"), "$.baseline.artifact")
    device = _mapping(_required(protocol, "reference_device", "$"), "$.reference_device")
    runtime = _mapping(
        _required(device, "runtime_inventory", "$.reference_device"),
        "$.reference_device.runtime_inventory",
    )
    readiness = _mapping(_required(protocol, "execution_readiness", "$"), "$.execution_readiness")
    approval = _mapping(_required(protocol, "approval", "$"), "$.approval")

    artifact_digest = artifact.get("sha256")
    if not isinstance(artifact_digest, str) or not SHA256_PATTERN.fullmatch(artifact_digest):
        _fail(
            "$.baseline.artifact.sha256",
            "the approved baseline requires a lowercase SHA-256 digest",
        )
    artifact_size = artifact.get("size_bytes")
    if not isinstance(artifact_size, int) or isinstance(artifact_size, bool) or artifact_size <= 0:
        _fail("$.baseline.artifact.size_bytes", "must be a positive integer")
    _non_empty_string(artifact.get("manifest"), "$.baseline.artifact.manifest")
    _non_empty_string(artifact.get("license"), "$.baseline.artifact.license")
    if artifact.get("license_review_status") != "approved":
        _fail(
            "$.baseline.artifact.license_review_status",
            "must be approved before using the baseline",
        )

    if status == "approved":
        if device.get("selection_status") != "selected":
            _fail("$.reference_device.selection_status", "must be 'selected'")
        for field in ("manufacturer", "model"):
            _non_empty_string(device.get(field), f"$.reference_device.{field}")
        if approval.get("team_approved") is not True:
            _fail("$.approval.team_approved", "must be true")
        _non_empty_string(approval.get("approved_by"), "$.approval.approved_by")
        _non_empty_string(approval.get("approved_at"), "$.approval.approved_at")

    readiness_status = readiness.get("status")
    if readiness_status not in {"blocked", "ready"}:
        _fail("$.execution_readiness.status", "must be 'blocked' or 'ready'")
    blocking_items = _sequence(
        _required(readiness, "blocking_items", "$.execution_readiness"),
        "$.execution_readiness.blocking_items",
    )

    if readiness_status == "blocked":
        if not blocking_items:
            _fail(
                "$.execution_readiness.blocking_items",
                "blocked execution requires at least one blocking item",
            )
        return

    if blocking_items:
        _fail(
            "$.execution_readiness.blocking_items",
            "ready execution cannot have blocking items",
        )

    if readiness_status == "ready":
        if runtime.get("status") != "captured":
            _fail("$.reference_device.runtime_inventory.status", "must be 'captured'")
        _non_empty_string(
            runtime.get("android_version"),
            "$.reference_device.runtime_inventory.android_version",
        )
        ram_gb = runtime.get("ram_gb")
        if not isinstance(ram_gb, int | float) or isinstance(ram_gb, bool) or ram_gb <= 0:
            _fail(
                "$.reference_device.runtime_inventory.ram_gb",
                "must be a positive number",
            )
        fingerprint_digest = runtime.get("build_fingerprint_sha256")
        if not isinstance(fingerprint_digest, str) or not SHA256_PATTERN.fullmatch(
            fingerprint_digest
        ):
            _fail(
                "$.reference_device.runtime_inventory.build_fingerprint_sha256",
                "must be a lowercase SHA-256 digest",
            )
        _non_empty_string(
            runtime.get("app_version"),
            "$.reference_device.runtime_inventory.app_version",
        )
        git_commit = runtime.get("git_commit")
        if not isinstance(git_commit, str) or not GIT_COMMIT_PATTERN.fullmatch(git_commit):
            _fail(
                "$.reference_device.runtime_inventory.git_commit",
                "must be a 7 to 40 character lowercase Git commit hash",
            )
        battery_percent = runtime.get("battery_percent_start")
        if (
            not isinstance(battery_percent, int | float)
            or isinstance(battery_percent, bool)
            or not 0 <= battery_percent <= 100
        ):
            _fail(
                "$.reference_device.runtime_inventory.battery_percent_start",
                "must be a number between 0 and 100",
            )
        _non_empty_string(
            runtime.get("thermal_state_start"),
            "$.reference_device.runtime_inventory.thermal_state_start",
        )
        _non_empty_string(
            runtime.get("captured_at"),
            "$.reference_device.runtime_inventory.captured_at",
        )


def validate_protocol(protocol: Mapping[str, Any]) -> None:
    """Validate protocol structure and cross-field scientific invariants."""

    if protocol.get("schema_version") != 1:
        _fail("$.schema_version", "only schema version 1 is supported")
    _non_empty_string(protocol.get("protocol_id"), "$.protocol_id")
    _validate_classes(protocol)
    _validate_split(protocol)
    _validate_metrics(protocol)
    _validate_privacy(protocol)
    _validate_status_and_execution_gates(protocol)


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
