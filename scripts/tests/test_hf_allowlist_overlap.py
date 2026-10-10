"""Observed overlap does not confer backend identity, policy or chat authority."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from legoai.intelligence.model.ports import ModelResponseRejectedError
from scripts import hf_inference_compatibility_probe as probe
from scripts.tests.test_hf_discovery_eligibility import backend, model_item, observed

PREFIX = "overlap observation (not authority): "


def test_unknown_backend_observation_is_not_authority(tmp_path: Path) -> None:
    result = observed(model_item(providers=[backend(provider="unreviewed-backend")]))
    policy = probe.BACKENDS
    with (
        patch.object(probe, "declaration", side_effect=AssertionError("identity")),
        patch.object(probe, "chat_admission", side_effect=AssertionError("admission")),
        patch.object(
            probe, "ModelBindingConfig", side_effect=AssertionError("binding")
        ),
        patch.object(probe, "_chat", side_effect=AssertionError("chat")),
        patch.object(
            probe, "open_credential_source", side_effect=AssertionError("Secret")
        ),
        patch("socket.socket", side_effect=AssertionError("network")),
        patch("builtins.open", side_effect=AssertionError("persistence")),
    ):
        lines = probe.eligibility_lines(result)
        samples = [
            json.loads(line.removeprefix(PREFIX))
            for line in lines
            if line.startswith(PREFIX)
        ]
        assert samples == [
            {
                "model": probe.CODING_MODELS[0],
                "backend": "unreviewed-backend",
                "status": "live",
                "input_modalities": ["text"],
                "output_modalities": ["text"],
                "input_price": 5.0,
                "output_price": 0.0,
                "reasons": ["BACKEND_NOT_ALLOWED"],
            }
        ]
        assert probe.shortlist(result) == ()
        assert (
            probe.select_pair(
                result, lambda _: pytest.fail("no selection"), lambda _: None
            )
            is None
        )
    assert probe.BACKENDS == policy
    assert list(tmp_path.iterdir()) == []
    assert "  BACKEND_NOT_ALLOWED: 1" in lines
    assert "eligible pairs: 0" in lines


def test_overlap_bound_asymmetry_aggregates_and_selection() -> None:
    result = observed(
        model_item(
            providers=[backend(provider=f"unknown-{n}") for n in range(6)] + [backend()]
        ),
        model_item(
            id="not/allowed", providers=[backend(), backend(provider="unknown")]
        ),
    )
    before = probe.shortlist(result)
    lines = probe.eligibility_lines(result)
    samples = [
        json.loads(line.removeprefix(PREFIX))
        for line in lines
        if line.startswith(PREFIX)
    ]
    assert len(samples) == 4
    assert all(sample["model"] == probe.CODING_MODELS[0] for sample in samples)
    assert [sample["backend"] for sample in samples] == [
        "novita",
        "unknown-0",
        "unknown-1",
        "unknown-2",
    ]
    assert lines[:5] == (
        "discovered models: 2",
        "allowlisted models observed: 1",
        "models without backend observations: 0",
        "observed model/backend pairs: 9",
        "eligible pairs: 1",
    )
    assert "  MODEL_NOT_ALLOWED: 2" in lines
    assert "  BACKEND_NOT_ALLOWED: 7" in lines
    assert len(lines) == 20
    assert probe.shortlist(result) == before
    assert probe.select_pair(result, lambda _: "1", lambda _: None) == before[0]


@pytest.mark.parametrize("identifier", ["x" * 129, "bad id", "bad\n", "bad*", "é"])
def test_parser_refuses_unsafe_backend_ids(identifier: str) -> None:
    with pytest.raises(ModelResponseRejectedError):
        observed(model_item(providers=[backend(provider=identifier)]))


@pytest.mark.parametrize(
    "identifier", ["https://example.invalid/metadata", "hf_SYNTHETIC_CANARY"]
)
def test_display_refuses_urls_and_token_shapes(identifier: str) -> None:
    result = observed(model_item(providers=[backend(provider=identifier)]))
    lines = probe.eligibility_lines(result)
    assert not any(line.startswith(PREFIX) for line in lines)
    assert identifier not in "\n".join(lines)
    assert "  BACKEND_NOT_ALLOWED: 1" in lines


def test_normalized_fields_and_raw_metadata_exclusion() -> None:
    canary = "SYNTHETIC-CREDENTIAL-CANARY"
    result = observed(
        model_item(
            description=canary,
            url="https://example.invalid/" + canary,
            architecture={
                "input_modalities": ["text", "image"],
                "output_modalities": [],
            },
            providers=[
                backend(
                    provider="x" * 128,
                    status="error",
                    pricing={"input": 1_000_000},
                    description=canary,
                )
            ],
        )
    )
    lines = probe.eligibility_lines(result)
    assert canary not in "\n".join(lines)
    sample = json.loads(
        next(line.removeprefix(PREFIX) for line in lines if line.startswith(PREFIX))
    )
    assert sample["backend"] == "x" * 128
    assert sample["status"] == "error"
    assert sample["input_modalities"] == ["text", "image"]
    assert sample["output_modalities"] == []
    assert sample["input_price"] == 1_000_000.0
    assert sample["output_price"] is None
    assert sample["reasons"] == [
        "BACKEND_NOT_ALLOWED",
        "BACKEND_STATUS_NOT_LIVE",
        "OUTPUT_MODALITY_MISSING",
        "MODALITY_SHAPE_UNSUPPORTED",
        "OUTPUT_PRICE_MISSING",
        "INPUT_PRICE_ABOVE_LIMIT",
    ]
