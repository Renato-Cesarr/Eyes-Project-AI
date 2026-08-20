"""Reference inference runner for the approved EfficientDet-Lite0 contract."""

from __future__ import annotations

import argparse
import json
import math
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Protocol

import numpy as np
from PIL import Image, ImageOps

from eyes_project_ai.model_manifest import (
    ManifestValidationError,
    ModelManifest,
    TensorContract,
    load_manifest,
    verify_artifact,
)


class InterpreterProtocol(Protocol):
    """Narrow boundary around LiteRT, allowing contract-focused unit tests."""

    def allocate_tensors(self) -> None: ...

    def get_input_details(self) -> Sequence[Mapping[str, Any]]: ...

    def get_output_details(self) -> Sequence[Mapping[str, Any]]: ...

    def set_tensor(self, tensor_index: int, value: np.ndarray) -> None: ...

    def invoke(self) -> None: ...

    def get_tensor(self, tensor_index: int) -> np.ndarray: ...


InterpreterFactory = Callable[[str, int], InterpreterProtocol]


class InferenceContractError(RuntimeError):
    """Raised when LiteRT exposes tensors different from the approved manifest."""


@dataclass(frozen=True)
class BoundingBox:
    """Normalized coordinates in the model's y/x order."""

    ymin: float
    xmin: float
    ymax: float
    xmax: float


@dataclass(frozen=True)
class Detection:
    """One enabled-domain detection returned by the reference runner."""

    domain_id: str
    display_name_pt_br: str
    source_label: str
    model_label_index: int
    score: float
    bounding_box: BoundingBox


@dataclass(frozen=True)
class InferenceResult:
    """Detections and host-only latency for one invocation."""

    detections: tuple[Detection, ...]
    inference_latency_ms: float


def _default_interpreter_factory(model_path: str, num_threads: int) -> InterpreterProtocol:
    from ai_edge_litert.interpreter import Interpreter

    return Interpreter(model_path=model_path, num_threads=num_threads)


def prepare_image(image: Image.Image, contract: TensorContract) -> np.ndarray:
    """Apply the documented RGB/bilinear preprocessing and create a uint8 batch."""

    _, height, width, channels = contract.shape
    if channels != 3 or contract.dtype != "uint8":
        raise InferenceContractError("only the approved uint8 RGB input is supported")
    normalized = ImageOps.exif_transpose(image).convert("RGB")
    resized = normalized.resize((width, height), resample=Image.Resampling.BILINEAR)
    array = np.asarray(resized, dtype=np.uint8)
    return np.expand_dims(array, axis=0)


def _dtype_name(value: Any) -> str:
    try:
        return np.dtype(value).name
    except TypeError as error:
        raise InferenceContractError("tensor dtype is missing or invalid") from error


def _validate_tensor(actual: Mapping[str, Any], expected: TensorContract, semantic: str) -> int:
    actual_name = actual.get("name")
    actual_shape = tuple(int(value) for value in actual.get("shape", ()))
    actual_dtype = _dtype_name(actual.get("dtype"))
    if actual_name != expected.name:
        raise InferenceContractError(
            f"{semantic} tensor name mismatch: expected {expected.name!r}, got {actual_name!r}"
        )
    if actual_shape != expected.shape:
        raise InferenceContractError(
            f"{semantic} tensor shape mismatch: expected {expected.shape}, got {actual_shape}"
        )
    if actual_dtype != expected.dtype:
        raise InferenceContractError(
            f"{semantic} tensor dtype mismatch: expected {expected.dtype}, got {actual_dtype}"
        )
    tensor_index = actual.get("index")
    if not isinstance(tensor_index, int):
        raise InferenceContractError(f"{semantic} tensor index is missing")
    return tensor_index


def validate_interpreter_contract(
    interpreter: InterpreterProtocol, manifest: ModelManifest
) -> tuple[int, Mapping[str, int]]:
    """Match tensors by stable names and validate shape/dtype before inference."""

    input_details = interpreter.get_input_details()
    if len(input_details) != 1:
        raise InferenceContractError(f"expected one input tensor, got {len(input_details)}")
    input_index = _validate_tensor(input_details[0], manifest.input, "input")

    output_details = {
        str(detail.get("name")): detail for detail in interpreter.get_output_details()
    }
    output_indices: dict[str, int] = {}
    for semantic, contract in manifest.outputs.items():
        actual = output_details.get(contract.name)
        if actual is None:
            raise InferenceContractError(
                f"{semantic} tensor {contract.name!r} is missing from the model"
            )
        output_indices[semantic] = _validate_tensor(actual, contract, semantic)
    return input_index, output_indices


def decode_detections(
    manifest: ModelManifest,
    *,
    boxes: np.ndarray,
    classes: np.ndarray,
    scores: np.ndarray,
    count: np.ndarray,
    score_threshold: float,
) -> tuple[Detection, ...]:
    """Filter postprocessed model outputs to the four approved domain classes."""

    if not 0 <= score_threshold <= 1:
        raise ValueError("score_threshold must be between 0 and 1")
    raw_count = float(count.reshape(-1)[0])
    if not math.isfinite(raw_count):
        raise InferenceContractError("model returned a non-finite detection count")
    detection_count = min(max(int(round(raw_count)), 0), manifest.maximum_detections)
    raw_boxes = boxes.reshape(-1, 4)
    raw_classes = classes.reshape(-1)
    raw_scores = scores.reshape(-1)
    available_count = min(detection_count, len(raw_boxes), len(raw_classes), len(raw_scores))
    classes_by_index = manifest.classes_by_index
    detections: list[Detection] = []

    for index in range(available_count):
        score = float(raw_scores[index])
        if not math.isfinite(score) or score < score_threshold:
            continue
        raw_class = float(raw_classes[index])
        if not math.isfinite(raw_class):
            continue
        model_label_index = int(round(raw_class))
        enabled = classes_by_index.get(model_label_index)
        if enabled is None:
            continue
        raw_coordinates = raw_boxes[index].astype(float)
        if not np.all(np.isfinite(raw_coordinates)):
            continue
        coordinates = np.clip(raw_coordinates, 0.0, 1.0)
        ymin, xmin, ymax, xmax = (float(value) for value in coordinates)
        if ymax <= ymin or xmax <= xmin:
            continue
        detections.append(
            Detection(
                domain_id=enabled.domain_id,
                display_name_pt_br=enabled.display_name_pt_br,
                source_label=enabled.source_label,
                model_label_index=model_label_index,
                score=score,
                bounding_box=BoundingBox(ymin=ymin, xmin=xmin, ymax=ymax, xmax=xmax),
            )
        )
    return tuple(detections)


class TFLiteDetector:
    """Verified reference detector; the Mobile implementation must match this contract."""

    def __init__(
        self,
        model_path: str | Path,
        manifest: ModelManifest,
        *,
        num_threads: int = 4,
        interpreter_factory: InterpreterFactory = _default_interpreter_factory,
    ) -> None:
        if num_threads <= 0:
            raise ValueError("num_threads must be positive")
        self._model_path = Path(model_path)
        self._manifest = manifest
        verify_artifact(self._model_path, manifest)
        self._interpreter = interpreter_factory(str(self._model_path), num_threads)
        self._interpreter.allocate_tensors()
        self._input_index, self._output_indices = validate_interpreter_contract(
            self._interpreter, manifest
        )

    def infer(self, image: Image.Image, *, score_threshold: float = 0.4) -> InferenceResult:
        """Run one inference. Latency excludes image decode and preprocessing."""

        input_tensor = prepare_image(image, self._manifest.input)
        self._interpreter.set_tensor(self._input_index, input_tensor)
        started = time.perf_counter_ns()
        self._interpreter.invoke()
        elapsed_ms = (time.perf_counter_ns() - started) / 1_000_000
        outputs = {
            semantic: self._interpreter.get_tensor(index)
            for semantic, index in self._output_indices.items()
        }
        return InferenceResult(
            detections=decode_detections(
                self._manifest,
                boxes=outputs["boxes"],
                classes=outputs["classes"],
                scores=outputs["scores"],
                count=outputs["count"],
                score_threshold=score_threshold,
            ),
            inference_latency_ms=elapsed_ms,
        )


def _percentile(values: Sequence[float], percentile: float) -> float:
    return float(np.percentile(np.asarray(values, dtype=float), percentile))


def main() -> int:
    parser = argparse.ArgumentParser(description="Run verified EfficientDet-Lite0 inference")
    parser.add_argument("image", help="path to an input image")
    parser.add_argument("--model", default="artifacts/models/efficientdet-lite0.tflite")
    parser.add_argument("--manifest", default="config/model-manifest.v1.json")
    parser.add_argument("--threshold", type=float, default=0.4)
    parser.add_argument("--threads", type=int, default=4)
    parser.add_argument("--warmup", type=int, default=3)
    parser.add_argument("--iterations", type=int, default=1)
    args = parser.parse_args()
    if args.warmup < 0 or args.iterations <= 0:
        parser.error("warmup must be non-negative and iterations must be positive")

    try:
        manifest = load_manifest(args.manifest)
        detector = TFLiteDetector(args.model, manifest, num_threads=args.threads)
        with Image.open(args.image) as source:
            image = source.copy()
        for _ in range(args.warmup):
            detector.infer(image, score_threshold=args.threshold)
        results = [
            detector.infer(image, score_threshold=args.threshold) for _ in range(args.iterations)
        ]
    except (OSError, ValueError, ManifestValidationError, InferenceContractError) as error:
        parser.exit(1, f"inference failed: {error}\n")

    latencies = [item.inference_latency_ms for item in results]
    payload = {
        "model_id": manifest.model_id,
        "model_sha256": manifest.artifact_sha256,
        "score_threshold": args.threshold,
        "host_measurement_only": True,
        "iterations": args.iterations,
        "inference_latency_ms": {
            "p50": _percentile(latencies, 50),
            "p95": _percentile(latencies, 95),
        },
        "detections": [asdict(item) for item in results[-1].detections],
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
