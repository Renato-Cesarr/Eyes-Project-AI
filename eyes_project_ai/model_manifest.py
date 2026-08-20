"""Strict contract and integrity checks for the approved TFLite artifact."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import zipfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, NoReturn

SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
EXPECTED_OUTPUTS = {"boxes", "classes", "scores", "count"}
EXPECTED_OUTPUT_CONTRACTS = {
    "boxes": ((1, 25, 4), "float32"),
    "classes": ((1, 25), "float32"),
    "scores": ((1, 25), "float32"),
    "count": ((1,), "float32"),
}


class ManifestValidationError(ValueError):
    """Raised when the model manifest or artifact violates its contract."""


def _fail(path: str, message: str) -> NoReturn:
    raise ManifestValidationError(f"{path}: {message}")


def _mapping(value: Any, path: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        _fail(path, "must be an object")
    return value


def _sequence(value: Any, path: str) -> Sequence[Any]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        _fail(path, "must be an array")
    return value


def _string(value: Any, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        _fail(path, "must be a non-empty string")
    return value


def _positive_int(value: Any, path: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        _fail(path, "must be a positive integer")
    return value


def _digest(value: Any, path: str) -> str:
    if not isinstance(value, str) or not SHA256_PATTERN.fullmatch(value):
        _fail(path, "must be a lowercase SHA-256 digest")
    return value


def _shape(value: Any, path: str) -> tuple[int, ...]:
    dimensions = _sequence(value, path)
    if not dimensions or any(
        not isinstance(item, int) or isinstance(item, bool) or item <= 0 for item in dimensions
    ):
        _fail(path, "must contain positive integer dimensions")
    return tuple(dimensions)


@dataclass(frozen=True)
class TensorContract:
    """Expected name, shape and dtype for one TFLite tensor."""

    name: str
    shape: tuple[int, ...]
    dtype: str


@dataclass(frozen=True)
class EnabledClass:
    """Stable mapping from a raw model label to an Eyes domain class."""

    domain_id: str
    display_name_pt_br: str
    source_label: str
    model_label_index: int
    coco_category_id: int


@dataclass(frozen=True)
class ModelManifest:
    """Validated, immutable model contract used by tooling and Mobile."""

    model_id: str
    model_version: str
    filename: str
    download_url: str
    artifact_sha256: str
    artifact_size_bytes: int
    license_spdx_id: str
    input: TensorContract
    outputs: Mapping[str, TensorContract]
    label_file: str
    label_count: int
    label_sha256: str
    enabled_classes: tuple[EnabledClass, ...]
    maximum_detections: int

    @property
    def classes_by_index(self) -> Mapping[int, EnabledClass]:
        return {item.model_label_index: item for item in self.enabled_classes}


def parse_manifest(raw: Mapping[str, Any]) -> ModelManifest:
    """Validate a decoded manifest and return its typed representation."""

    if raw.get("schema_version") != 1:
        _fail("$.schema_version", "only schema version 1 is supported")
    model_id = _string(raw.get("model_id"), "$.model_id")
    model_version = _string(raw.get("model_version"), "$.model_version")

    artifact = _mapping(raw.get("artifact"), "$.artifact")
    filename = _string(artifact.get("filename"), "$.artifact.filename")
    download_url = _string(artifact.get("download_url"), "$.artifact.download_url")
    if not download_url.startswith("https://"):
        _fail("$.artifact.download_url", "must use HTTPS")
    artifact_sha256 = _digest(artifact.get("sha256"), "$.artifact.sha256")
    artifact_size = _positive_int(artifact.get("size_bytes"), "$.artifact.size_bytes")
    license_data = _mapping(artifact.get("license"), "$.artifact.license")
    license_spdx_id = _string(license_data.get("spdx_id"), "$.artifact.license.spdx_id")
    if license_data.get("review_status") != "approved":
        _fail("$.artifact.license.review_status", "must be 'approved'")
    _string(license_data.get("source_url"), "$.artifact.license.source_url")

    runtime = _mapping(raw.get("runtime"), "$.runtime")
    input_raw = _mapping(runtime.get("input"), "$.runtime.input")
    input_contract = TensorContract(
        name=_string(input_raw.get("name"), "$.runtime.input.name"),
        shape=_shape(input_raw.get("shape"), "$.runtime.input.shape"),
        dtype=_string(input_raw.get("dtype"), "$.runtime.input.dtype"),
    )
    if input_contract.shape != (1, 320, 320, 3) or input_contract.dtype != "uint8":
        _fail("$.runtime.input", "EfficientDet-Lite0 requires uint8 [1, 320, 320, 3]")
    if input_raw.get("color_space") != "RGB" or input_raw.get("resize_method") != "bilinear":
        _fail("$.runtime.input", "preprocessing must be RGB with bilinear resize")

    outputs_raw = _mapping(runtime.get("outputs"), "$.runtime.outputs")
    if set(outputs_raw) != EXPECTED_OUTPUTS:
        _fail("$.runtime.outputs", f"must contain exactly {sorted(EXPECTED_OUTPUTS)}")
    outputs: dict[str, TensorContract] = {}
    for semantic, value in outputs_raw.items():
        path = f"$.runtime.outputs.{semantic}"
        tensor = _mapping(value, path)
        outputs[semantic] = TensorContract(
            name=_string(tensor.get("name"), f"{path}.name"),
            shape=_shape(tensor.get("shape"), f"{path}.shape"),
            dtype=_string(tensor.get("dtype"), f"{path}.dtype"),
        )
        expected_shape, expected_dtype = EXPECTED_OUTPUT_CONTRACTS[semantic]
        if outputs[semantic].shape != expected_shape or outputs[semantic].dtype != expected_dtype:
            _fail(
                path,
                f"must be {expected_dtype} with shape {expected_shape}",
            )
    if len({tensor.name for tensor in outputs.values()}) != len(outputs):
        _fail("$.runtime.outputs", "tensor names must be unique")

    postprocessing = _mapping(runtime.get("postprocessing"), "$.runtime.postprocessing")
    if postprocessing.get("embedded_in_model") is not True:
        _fail("$.runtime.postprocessing.embedded_in_model", "must be true")
    if postprocessing.get("additional_nms_required") is not False:
        _fail("$.runtime.postprocessing.additional_nms_required", "must be false")
    maximum_detections = _positive_int(
        postprocessing.get("maximum_detections"),
        "$.runtime.postprocessing.maximum_detections",
    )
    if maximum_detections != outputs["classes"].shape[1]:
        _fail(
            "$.runtime.postprocessing.maximum_detections",
            "must equal the detection dimension of the output tensors",
        )

    labels = _mapping(raw.get("labels"), "$.labels")
    label_file = _string(labels.get("associated_file"), "$.labels.associated_file")
    label_count = _positive_int(labels.get("count"), "$.labels.count")
    label_sha256 = _digest(labels.get("sha256"), "$.labels.sha256")

    enabled_raw = _sequence(raw.get("enabled_classes"), "$.enabled_classes")
    enabled_classes: list[EnabledClass] = []
    domain_ids: set[str] = set()
    model_indices: set[int] = set()
    for index, value in enumerate(enabled_raw):
        path = f"$.enabled_classes[{index}]"
        item = _mapping(value, path)
        model_index = item.get("model_label_index")
        coco_id = item.get("coco_category_id")
        if not isinstance(model_index, int) or isinstance(model_index, bool) or model_index < 0:
            _fail(f"{path}.model_label_index", "must be a non-negative integer")
        if not isinstance(coco_id, int) or isinstance(coco_id, bool) or coco_id <= 0:
            _fail(f"{path}.coco_category_id", "must be a positive integer")
        parsed = EnabledClass(
            domain_id=_string(item.get("domain_id"), f"{path}.domain_id"),
            display_name_pt_br=_string(
                item.get("display_name_pt_br"), f"{path}.display_name_pt_br"
            ),
            source_label=_string(item.get("source_label"), f"{path}.source_label"),
            model_label_index=model_index,
            coco_category_id=coco_id,
        )
        if parsed.domain_id in domain_ids or parsed.model_label_index in model_indices:
            _fail(path, "domain ids and model label indexes must be unique")
        if parsed.model_label_index >= label_count:
            _fail(f"{path}.model_label_index", "must be smaller than the label count")
        domain_ids.add(parsed.domain_id)
        model_indices.add(parsed.model_label_index)
        enabled_classes.append(parsed)

    if domain_ids != {"person", "chair", "table_desk", "backpack"}:
        _fail("$.enabled_classes", "must define the four approved MVP classes")

    return ModelManifest(
        model_id=model_id,
        model_version=model_version,
        filename=filename,
        download_url=download_url,
        artifact_sha256=artifact_sha256,
        artifact_size_bytes=artifact_size,
        license_spdx_id=license_spdx_id,
        input=input_contract,
        outputs=outputs,
        label_file=label_file,
        label_count=label_count,
        label_sha256=label_sha256,
        enabled_classes=tuple(enabled_classes),
        maximum_detections=maximum_detections,
    )


def load_manifest(path: str | Path = "config/model-manifest.v1.json") -> ModelManifest:
    """Load and validate the versioned model manifest."""

    with Path(path).open(encoding="utf-8") as source:
        raw = json.load(source)
    return parse_manifest(_mapping(raw, "$"))


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    """Calculate a file digest without loading the model into memory."""

    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def verify_artifact(path: str | Path, manifest: ModelManifest) -> tuple[str, ...]:
    """Verify bytes, embedded label metadata and all enabled label mappings."""

    artifact_path = Path(path)
    if not artifact_path.is_file():
        raise ManifestValidationError(f"artifact not found: {artifact_path}")
    actual_size = artifact_path.stat().st_size
    if actual_size != manifest.artifact_size_bytes:
        raise ManifestValidationError(
            f"artifact size mismatch: expected {manifest.artifact_size_bytes}, got {actual_size}"
        )
    actual_digest = sha256_file(artifact_path)
    if actual_digest != manifest.artifact_sha256:
        raise ManifestValidationError(
            f"artifact SHA-256 mismatch: expected {manifest.artifact_sha256}, got {actual_digest}"
        )

    try:
        with zipfile.ZipFile(artifact_path) as archive:
            label_bytes = archive.read(manifest.label_file)
    except (zipfile.BadZipFile, KeyError) as error:
        raise ManifestValidationError(
            f"artifact does not contain associated file {manifest.label_file!r}"
        ) from error

    actual_label_digest = hashlib.sha256(label_bytes).hexdigest()
    if actual_label_digest != manifest.label_sha256:
        raise ManifestValidationError(
            f"label SHA-256 mismatch: expected {manifest.label_sha256}, got {actual_label_digest}"
        )
    labels = tuple(label_bytes.decode("utf-8").splitlines())
    if len(labels) != manifest.label_count:
        raise ManifestValidationError(
            f"label count mismatch: expected {manifest.label_count}, got {len(labels)}"
        )
    for enabled in manifest.enabled_classes:
        actual_label = labels[enabled.model_label_index]
        if actual_label != enabled.source_label:
            raise ManifestValidationError(
                f"label {enabled.model_label_index} mismatch: "
                f"expected {enabled.source_label!r}, got {actual_label!r}"
            )
    return labels


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify the approved EfficientDet-Lite0 artifact")
    parser.add_argument("artifact", help="path to the downloaded .tflite artifact")
    parser.add_argument("--manifest", default="config/model-manifest.v1.json")
    args = parser.parse_args()
    try:
        manifest = load_manifest(args.manifest)
        labels = verify_artifact(args.artifact, manifest)
    except (OSError, json.JSONDecodeError, ManifestValidationError) as error:
        parser.exit(1, f"model verification failed: {error}\n")
    print(
        f"verified {manifest.model_id}@{manifest.model_version}: "
        f"{manifest.artifact_sha256} ({len(labels)} labels, {manifest.license_spdx_id})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
