"""Bounded HF policy diagnostics from synthetic normalized observations only."""

import inspect
import json
from dataclasses import replace
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from legoai.reference.model_openai_compatible import parse_model_catalog
from legoai.runtime._composition.provider_discovery import (
    DiscoveryOutcome,
    ModelDiscovery,
)
from scripts import hf_inference_compatibility_probe as probe
from tests.support.tls_server import TEST_CA, TlsServer

R = probe.RejectionReason
CANARY = "SYNTHETIC-SECRET-CANARY-ELIGIBILITY-981"


def model_item(**changes: Any) -> dict[str, Any]:
    return {
        "id": probe.CODING_MODELS[0],
        "architecture": {"input_modalities": ["text"], "output_modalities": ["text"]},
        "providers": [backend()],
    } | changes


def backend(**changes: Any) -> dict[str, Any]:
    return {
        "provider": "novita",
        "status": "live",
        "pricing": {"input": 5, "output": 0},
    } | changes


def observed(*items: dict[str, Any]) -> ModelDiscovery:
    catalog = parse_model_catalog(json.dumps({"data": items}).encode())
    return ModelDiscovery(
        DiscoveryOutcome.LISTED, models=tuple(m.model for m in catalog), catalog=catalog
    )


@pytest.mark.parametrize(
    "changes,reasons",
    [
        ({}, ()),
        ({"id": "other/model"}, (R.MODEL_NOT_ALLOWED,)),
        ({"providers": [backend(provider="other")]}, (R.BACKEND_NOT_ALLOWED,)),
        ({"providers": [backend(status="error")]}, (R.BACKEND_STATUS_NOT_LIVE,)),
        ({"providers": [backend(status=None)]}, (R.BACKEND_STATUS_NOT_LIVE,)),
        ({"providers": [backend(pricing={"output": 1})]}, (R.INPUT_PRICE_MISSING,)),
        ({"providers": [backend(pricing={"input": 1})]}, (R.OUTPUT_PRICE_MISSING,)),
        (
            {"providers": [backend(pricing={"input": 6, "output": 1})]},
            (R.INPUT_PRICE_ABOVE_LIMIT,),
        ),
        (
            {"providers": [backend(pricing={"input": 1, "output": 6})]},
            (R.OUTPUT_PRICE_ABOVE_LIMIT,),
        ),
    ],
)
def test_pair_reasons(
    changes: dict[str, Any], reasons: tuple[probe.RejectionReason, ...]
) -> None:
    # Missing status is absent, not a malformed JSON null.
    if "providers" in changes and changes["providers"][0].get("status") is None:
        changes = {"providers": [dict(changes["providers"][0])]}
        del changes["providers"][0]["status"]
    result = observed(model_item(**changes))
    model = result.catalog[0]
    evaluation = probe.evaluate_candidate(model, model.providers[0])
    assert evaluation.model == model.model
    assert evaluation.provider == model.providers[0].provider
    assert evaluation.reasons == reasons
    assert evaluation.eligible is (not reasons)
    assert bool(probe.shortlist(result)) is evaluation.eligible


@pytest.mark.parametrize("direction", ["input", "output"])
@pytest.mark.parametrize("modalities", [[], ["image"], ["text", "image"]])
def test_exact_modality_policy(direction: str, modalities: list[str]) -> None:
    architecture = {"input_modalities": ["text"], "output_modalities": ["text"]}
    architecture[direction + "_modalities"] = modalities
    model = observed(model_item(architecture=architecture)).catalog[0]
    reason = (
        R.MODALITY_SHAPE_UNSUPPORTED
        if modalities
        else R.INPUT_MODALITY_MISSING
        if direction == "input"
        else R.OUTPUT_MODALITY_MISSING
    )
    assert probe.evaluate_candidate(model, model.providers[0]).reasons == (reason,)


def test_complete_reasons_and_aggregate_counts() -> None:
    result = observed(
        model_item(
            id="other/model",
            architecture={},
            providers=[backend(provider="other", status="error", pricing={})],
        ),
        model_item(providers=[]),
    )
    model = result.catalog[0]
    expected = (
        R.MODEL_NOT_ALLOWED,
        R.BACKEND_NOT_ALLOWED,
        R.BACKEND_STATUS_NOT_LIVE,
        R.INPUT_MODALITY_MISSING,
        R.OUTPUT_MODALITY_MISSING,
        R.INPUT_PRICE_MISSING,
        R.OUTPUT_PRICE_MISSING,
    )
    assert probe.evaluate_candidate(model, model.providers[0]).reasons == expected
    lines = probe.eligibility_lines(result)
    assert lines[:5] == (
        "discovered models: 2",
        "allowlisted models observed: 1",
        "models without backend observations: 1",
        "observed model/backend pairs: 1",
        "eligible pairs: 0",
    )
    for reason in R:
        assert f"  {reason.value}: {int(reason in expected)}" in lines
    assert not any(line.startswith("overlap observation") for line in lines)


def test_sample_bound_order_and_no_ranking() -> None:
    items = [
        model_item(
            id=model,
            providers=[
                backend(provider=key, status="error") for key, _, _ in probe.BACKENDS
            ],
        )
        for model in probe.CODING_MODELS
    ]
    result = observed(*items)
    lines = probe.eligibility_lines(result)
    reversed_result = observed(
        *(
            item | {"providers": list(reversed(item["providers"]))}
            for item in reversed(items)
        )
    )
    assert lines == probe.eligibility_lines(reversed_result)
    samples = [line for line in lines if line.startswith("overlap observation")]
    assert len(samples) == 4
    assert samples == sorted(samples)
    assert "  BACKEND_STATUS_NOT_LIVE: 8" in lines
    assert probe.shortlist(result) == ()


def test_untrusted_metadata_and_identifiers_never_enter_output() -> None:
    result = observed(
        model_item(id=CANARY, description=CANARY),
        model_item(
            providers=[backend(provider="hf_" + CANARY, status="opaque-status")]
        ),
    )
    text = "\n".join(probe.eligibility_lines(result))
    assert CANARY not in text
    for model in result.catalog:
        assert CANARY not in repr(probe.evaluate_candidate(model, model.providers[0]))
    assert len(probe.eligibility_lines(result)) == 16


def test_diagnostics_are_pure_and_selection_stays_numbered() -> None:
    result = observed(model_item())
    before = probe.shortlist(result)
    assert set(inspect.signature(probe.evaluate_candidate).parameters) == {
        "model",
        "provider",
    }
    with (
        patch.object(probe, "chat_admission", side_effect=AssertionError("authority")),
        patch.object(
            probe, "ModelBindingConfig", side_effect=AssertionError("binding")
        ),
        patch.object(
            probe, "open_credential_source", side_effect=AssertionError("secret")
        ),
        patch("socket.getaddrinfo", side_effect=AssertionError("network")),
        patch("builtins.open", side_effect=AssertionError("persistence")),
    ):
        assert "eligible pairs: 1" in probe.eligibility_lines(result)
        assert probe.shortlist(result) == before
        assert probe.select_pair(result, lambda _: "1", lambda _: None) == before[0]
        assert (
            probe.select_pair(result, lambda _: before[0].request_model, lambda _: None)
            is None
        )


def test_no_pairs_and_inconsistent_observations() -> None:
    assert "observed model/backend pairs: 0" in probe.eligibility_lines(observed())
    result = observed(model_item())
    for invalid in (
        replace(result, models=()),
        replace(result, outcome=DiscoveryOutcome.MALFORMED),
    ):
        assert probe.shortlist(invalid) == ()
        assert probe.eligibility_lines(invalid) == (
            "eligibility diagnostics unavailable: no consistent listed observation",
        )


def test_local_tls_no_eligible_pair_stops_without_chat_or_catalog_persistence(
    tmp_path: Path,
) -> None:
    raw = json.dumps(
        {"data": [model_item(description=CANARY, providers=[backend(pricing={})])]}
    ).encode()
    lines: list[str] = []
    with TlsServer(
        expected=CANARY, responses={"/v1/models": raw}, methods={"/v1/models": "GET"}
    ) as tls:
        config = replace(
            probe.ProbeConfig.live(tmp_path),
            origin=f"https://localhost:{tls.port}",
            trust_anchor=TEST_CA,
        )
        with (
            patch.object(probe, "_chat", side_effect=AssertionError("chat forbidden")),
            patch.object(probe, "select_pair", wraps=probe.select_pair) as select,
        ):
            reads: list[str] = []

            def read(prompt: str) -> str:
                reads.append(prompt)
                return CANARY

            verdict = probe.run_probe(
                config,
                write=lines.append,
                ask=lambda _: pytest.fail("selection forbidden"),
                read=read,
                interactive=lambda: True,
            )
            select.assert_called_once()
        assert verdict is probe.Classification.PROVIDER_IDENTITY_INDETERMINATE
        assert tls.paths == ["GET /v1/models"]
        assert tls.requests == 1
        assert len(reads) == 1
    assert "eligible pairs: 0" in lines
    assert CANARY not in "\n".join(lines)
    for path in tmp_path.rglob("*"):
        if path.is_file():
            data = path.read_bytes()
            assert CANARY.encode() not in data
            assert raw not in data
