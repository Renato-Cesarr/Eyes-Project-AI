"""Reproducibly acquire the approved model without committing binary weights."""

from __future__ import annotations

import argparse
import os
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import BinaryIO
from urllib.request import Request, urlopen

from eyes_project_ai.model_manifest import (
    ManifestValidationError,
    ModelManifest,
    load_manifest,
    verify_artifact,
)

OpenUrl = Callable[[Request, float], BinaryIO]


class ModelAcquisitionError(RuntimeError):
    """Raised when a model cannot be downloaded and verified safely."""


def _open_url(request: Request, timeout: float) -> BinaryIO:
    return urlopen(request, timeout=timeout)  # noqa: S310 - URL is pinned by the manifest


def acquire_model(
    manifest: ModelManifest,
    destination: str | Path,
    *,
    timeout_seconds: float = 60,
    opener: OpenUrl = _open_url,
) -> bool:
    """Download atomically, verify all bytes and return whether a download occurred."""

    target = Path(destination)
    if target.is_file():
        try:
            verify_artifact(target, manifest)
            return False
        except ManifestValidationError:
            pass

    target.parent.mkdir(parents=True, exist_ok=True)
    request = Request(
        manifest.download_url,
        headers={"User-Agent": "Eyes-Project-AI/1.0 (REN-36 model acquisition)"},
    )
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            prefix=f".{target.name}.",
            suffix=".download",
            dir=target.parent,
            delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)
            with opener(request, timeout_seconds) as response:
                while chunk := response.read(1024 * 1024):
                    temporary.write(chunk)
                    if temporary.tell() > manifest.artifact_size_bytes:
                        raise ModelAcquisitionError("download exceeded the expected artifact size")
            temporary.flush()
            os.fsync(temporary.fileno())
        verify_artifact(temporary_path, manifest)
        os.replace(temporary_path, target)
        temporary_path = None
        return True
    except (OSError, ManifestValidationError) as error:
        raise ModelAcquisitionError(f"model acquisition failed: {error}") from error
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Acquire the pinned EfficientDet-Lite0 model")
    parser.add_argument("--destination", default="artifacts/models/efficientdet-lite0.tflite")
    parser.add_argument("--manifest", default="config/model-manifest.v1.json")
    parser.add_argument("--timeout", type=float, default=60)
    args = parser.parse_args()
    try:
        manifest = load_manifest(args.manifest)
        downloaded = acquire_model(manifest, args.destination, timeout_seconds=args.timeout)
    except (OSError, ModelAcquisitionError, ManifestValidationError) as error:
        parser.exit(1, f"{error}\n")
    action = "downloaded and verified" if downloaded else "already verified"
    print(f"{action}: {args.destination} ({manifest.artifact_sha256})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
