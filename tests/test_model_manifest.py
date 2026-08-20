from __future__ import annotations

import hashlib
import io
import json
import zipfile
from copy import deepcopy
from pathlib import Path

import pytest

from eyes_project_ai.acquire_model import ModelAcquisitionError, acquire_model
from eyes_project_ai.model_manifest import (
    ManifestValidationError,
    load_manifest,
    parse_manifest,
    verify_artifact,
)

ROOT = Path(__file__).parents[1]
MANIFEST_PATH = ROOT / "config" / "model-manifest.v1.json"


def _raw_manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def _artifact_fixture(tmp_path: Path) -> tuple[bytes, dict]:
    raw = _raw_manifest()
    labels = ["???"] * 90
    for item in raw["enabled_classes"]:
        labels[item["model_label_index"]] = item["source_label"]
    label_bytes = ("\n".join(labels) + "\n").encode()
    artifact = tmp_path / "fixture.tflite"
    with zipfile.ZipFile(artifact, "w") as archive:
        archive.writestr("labelmap.txt", label_bytes)
    artifact_bytes = artifact.read_bytes()
    raw["artifact"]["filename"] = artifact.name
    raw["artifact"]["sha256"] = hashlib.sha256(artifact_bytes).hexdigest()
    raw["artifact"]["size_bytes"] = len(artifact_bytes)
    raw["labels"]["sha256"] = hashlib.sha256(label_bytes).hexdigest()
    return artifact_bytes, raw


def test_versioned_manifest_has_pinned_approved_artifact() -> None:
    manifest = load_manifest(MANIFEST_PATH)

    assert manifest.model_id == "efficientdet-lite0-coco2017-int8"
    assert manifest.artifact_size_bytes == 4_563_519
    assert manifest.license_spdx_id == "Apache-2.0"
    assert manifest.input.shape == (1, 320, 320, 3)
    assert manifest.classes_by_index[66].domain_id == "table_desk"


def test_artifact_and_embedded_labels_are_verified(tmp_path: Path) -> None:
    artifact_bytes, raw = _artifact_fixture(tmp_path)
    artifact_path = tmp_path / "downloaded.tflite"
    artifact_path.write_bytes(artifact_bytes)

    labels = verify_artifact(artifact_path, parse_manifest(raw))

    assert len(labels) == 90
    assert labels[61] == "chair"


def test_artifact_digest_mismatch_is_rejected(tmp_path: Path) -> None:
    artifact_bytes, raw = _artifact_fixture(tmp_path)
    artifact_path = tmp_path / "tampered.tflite"
    artifact_path.write_bytes(artifact_bytes[:-1] + b"x")

    with pytest.raises(ManifestValidationError, match="SHA-256 mismatch"):
        verify_artifact(artifact_path, parse_manifest(raw))


def test_incorrect_enabled_label_mapping_is_rejected(tmp_path: Path) -> None:
    artifact_bytes, raw = _artifact_fixture(tmp_path)
    raw["enabled_classes"][0]["source_label"] = "not-person"
    artifact_path = tmp_path / "labels.tflite"
    artifact_path.write_bytes(artifact_bytes)

    with pytest.raises(ManifestValidationError, match="label 0 mismatch"):
        verify_artifact(artifact_path, parse_manifest(raw))


def test_acquisition_is_atomic_and_idempotent(tmp_path: Path) -> None:
    artifact_bytes, raw = _artifact_fixture(tmp_path)
    manifest = parse_manifest(raw)
    destination = tmp_path / "models" / "model.tflite"
    calls = 0

    def opener(_request, _timeout):
        nonlocal calls
        calls += 1
        return io.BytesIO(artifact_bytes)

    assert acquire_model(manifest, destination, opener=opener) is True
    assert acquire_model(manifest, destination, opener=opener) is False
    assert calls == 1
    assert not list(destination.parent.glob("*.download"))


def test_acquisition_does_not_publish_unverified_bytes(tmp_path: Path) -> None:
    artifact_bytes, raw = _artifact_fixture(tmp_path)
    manifest = parse_manifest(raw)
    destination = tmp_path / "models" / "model.tflite"

    def opener(_request, _timeout):
        return io.BytesIO(artifact_bytes[:-1])

    with pytest.raises(ModelAcquisitionError, match="artifact size mismatch"):
        acquire_model(manifest, destination, opener=opener)

    assert not destination.exists()


def test_unapproved_license_is_rejected() -> None:
    raw = deepcopy(_raw_manifest())
    raw["artifact"]["license"]["review_status"] = "pending"

    with pytest.raises(ManifestValidationError, match="must be 'approved'"):
        parse_manifest(raw)
