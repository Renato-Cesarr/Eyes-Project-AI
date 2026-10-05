from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path

import pytest

from eyes_project_ai.evaluation_protocol import (
    EvaluationProtocolError,
    load_evaluation_protocol,
    validate_evaluation_protocol,
)
from eyes_project_ai.protocol import ProtocolValidationError, load_and_validate_protocol

ROOT = Path(__file__).parents[1]


@pytest.fixture
def contract() -> dict:
    return json.loads((ROOT / "config/assistive-evaluation.v1.json").read_text())


@pytest.mark.parametrize(
    "section,key,value",
    [
        ("latency", "gates_ms", {"camera_to_tts_p95": 500}),
        ("latency", "minimum_samples_per_configuration", 4),
        ("latency", "warmup_frames", 0),
        ("latency", "measured_values", {"inference": 64.16}),
        ("detection", "minimum_independent_sessions", 1),
        ("detection", "gates", {"precision": 0.4}),
        ("detection", "split", {"group_key": "frame"}),
        ("assistive_segments", "evaluation", 0),
        ("sustained", "duration_minutes", 15),
        ("sustained", "battery_consumption_requires_unplugged", False),
        ("readiness", "status", "ready"),
    ],
)
def test_rejects_weakened_or_unmeasured_contract(contract, section, key, value):
    invalid = deepcopy(contract)
    invalid[section][key] = value
    with pytest.raises(EvaluationProtocolError):
        validate_evaluation_protocol(invalid)


def test_contract_hash_is_cross_platform_and_file_changes_are_rejected(tmp_path):
    source = (ROOT / "config/assistive-evaluation.v1.json").read_text()
    digest = hashlib.sha256(source.encode()).hexdigest()
    candidate = tmp_path / "contract.json"
    candidate.write_bytes(source.replace("\n", "\r\n").encode())
    assert (
        load_evaluation_protocol(candidate, digest)["protocol_id"] == "eyes-assistive-evaluation-v1"
    )
    candidate.write_text(source + " ")
    with pytest.raises(EvaluationProtocolError, match="SHA-256"):
        load_evaluation_protocol(candidate, digest)


def test_experiment_requires_shared_contract_hash(tmp_path):
    experiment = json.loads((ROOT / "config/experiment.v1.json").read_text())
    experiment["evaluation_protocol"]["sha256_lf"] = "0" * 64
    path = tmp_path / "experiment.v1.json"
    path.write_text(json.dumps(experiment))
    (tmp_path / "assistive-evaluation.v1.json").write_bytes(
        (ROOT / "config/assistive-evaluation.v1.json").read_bytes()
    )
    with pytest.raises(ProtocolValidationError, match="SHA-256"):
        load_and_validate_protocol(path)


def test_historical_pilot_has_explicit_origin_and_small_tts_sample():
    receipt = json.loads((ROOT / "docs/evidence/REN-68-legacy-pilot.json").read_text())
    assert receipt["analysisSoftware"]["sourceDirty"] is False
    assert receipt["provenance"]["claim"] == "descriptive_only"
    assert receipt["provenance"]["measurementWindowVerified"] is False
    assert receipt["analysis"]["frameCount"] == 550
    assert receipt["analysis"]["matchedSpeechCount"] == 4
    stats = receipt["analysis"]["latencyStatistics"]
    assert stats["cameraToSpeechStart"]["n"] == 4
    assert stats["firstOperationalAlert"]["n"] == 1
    assert stats["firstOperationalAlert"]["p50Ms"] != stats["sessionToFirstAlert"]["p50Ms"]


def test_pilot_protocol_digest_matches_current_contract():
    receipt = json.loads((ROOT / "docs/evidence/REN-68-legacy-pilot.json").read_text())
    experiment = load_and_validate_protocol(ROOT / "config/experiment.v1.json")
    assert receipt["protocolSha256"] == experiment["evaluation_protocol"]["sha256_lf"]
