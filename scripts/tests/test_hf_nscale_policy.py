"""Nscale identity policy is SYNTHETIC only, never availability or disclosure."""

from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from legoai.governance.disclosure import DisclosureClass, FactBasis
from scripts import hf_inference_compatibility_probe as probe
from scripts.tests.test_hf_discovery_eligibility import backend, model_item, observed


def test_policy_is_only_an_appended_harness_identity() -> None:
    assert probe.BACKENDS == (
        ("fireworks-ai", "Fireworks AI", "fireworks-ai"),
        ("novita", "Novita", "novita"),
        ("together", "Together AI", "together"),
        ("nscale", "Nscale", "nscale"),
    )
    assert probe.CODING_MODELS == (
        "Qwen/Qwen2.5-Coder-32B-Instruct",
        "Qwen/Qwen3-Coder-480B-A35B-Instruct",
    )
    root = Path(__file__).resolve().parents[2]
    for path in (root / "src/legoai").rglob("*.py"):
        assert "nscale" not in path.read_text(encoding="utf-8").lower()


@pytest.mark.parametrize("provider", ["fireworks-ai", "novita", "together", "nscale"])
def test_all_reviewed_backends_use_the_same_eligibility_policy(provider: str) -> None:
    result = observed(
        model_item(
            providers=[
                backend(provider=provider, pricing={"input": 0.06, "output": 0.20})
            ]
        )
    )
    model = result.catalog[0]
    evaluation = probe.evaluate_candidate(model, model.providers[0])
    assert evaluation.eligible and evaluation.reasons == ()
    assert (
        probe.shortlist(result)[0].request_model
        == probe.CODING_MODELS[0] + ":" + provider
    )


@pytest.mark.parametrize(
    "changes,reason",
    [
        ({"status": "error"}, probe.RejectionReason.BACKEND_STATUS_NOT_LIVE),
        ({"pricing": {"output": 0.20}}, probe.RejectionReason.INPUT_PRICE_MISSING),
        ({"pricing": {"input": 0.06}}, probe.RejectionReason.OUTPUT_PRICE_MISSING),
        (
            {"pricing": {"input": 5.01, "output": 0.20}},
            probe.RejectionReason.INPUT_PRICE_ABOVE_LIMIT,
        ),
        (
            {"pricing": {"input": 0.06, "output": 5.01}},
            probe.RejectionReason.OUTPUT_PRICE_ABOVE_LIMIT,
        ),
    ],
)
def test_nscale_still_requires_current_facts(
    changes: dict[str, Any], reason: probe.RejectionReason
) -> None:
    entry = (
        backend(provider="nscale", pricing={"input": 0.06, "output": 0.20}) | changes
    )
    result = observed(model_item(providers=[entry]))
    model = result.catalog[0]
    assert reason in probe.evaluate_candidate(model, model.providers[0]).reasons
    assert probe.shortlist(result) == ()


def test_nscale_wrong_modality_and_featherless_missing_prices_remain_rejected() -> None:
    result = observed(
        model_item(
            architecture={"input_modalities": ["image"], "output_modalities": ["text"]},
            providers=[backend(provider="nscale")],
        )
    )
    model = result.catalog[0]
    assert (
        probe.RejectionReason.MODALITY_SHAPE_UNSUPPORTED
        in probe.evaluate_candidate(model, model.providers[0]).reasons
    )
    assert probe.shortlist(result) == ()
    featherless = observed(
        model_item(providers=[backend(provider="featherless-ai", pricing={})])
    )
    model = featherless.catalog[0]
    assert probe.evaluate_candidate(model, model.providers[0]).reasons == (
        probe.RejectionReason.BACKEND_NOT_ALLOWED,
        probe.RejectionReason.INPUT_PRICE_MISSING,
        probe.RejectionReason.OUTPUT_PRICE_MISSING,
    )
    assert probe.shortlist(featherless) == ()


def test_numbered_selection_and_synthetic_identity_do_not_admit_repository(
    tmp_path: Path,
) -> None:
    result = observed(model_item(providers=[backend(provider="nscale")]))
    with (
        patch.object(
            probe, "declaration", side_effect=AssertionError("no automatic identity")
        ),
        patch.object(
            probe,
            "chat_admission",
            side_effect=AssertionError("no automatic admission"),
        ),
        patch.object(probe, "_chat", side_effect=AssertionError("no chat")),
        patch("socket.socket", side_effect=AssertionError("network forbidden")),
    ):
        assert probe.shortlist(observed()) == ()
        assert probe.select_pair(result, lambda _: "", lambda _: None) is None
        assert probe.select_pair(result, lambda _: "nscale", lambda _: None) is None
        selected = probe.select_pair(result, lambda _: "1", lambda _: None)
    assert selected is not None
    config = probe.ProbeConfig.live(tmp_path)
    declaration = probe.declaration(config, selected)
    assert (
        declaration.processor.name == "Hugging Face router; inference processor Nscale"
    )
    assert declaration.processor.basis is FactBasis.PROVIDER_DECLARED
    assert declaration.processor.source is not None
    assert (
        declaration.processor.source.retrieved_on
        == datetime(2026, 10, 10, tzinfo=UTC).date()
    )
    assert probe.DOCS + "providers/nscale" in declaration.processor.source.reference
    assert all(
        fact.basis is FactBasis.UNKNOWN
        for fact in (
            declaration.location,
            declaration.retention,
            declaration.training,
            declaration.human_access,
            declaration.subprocessors,
        )
    )
    admission = probe.chat_admission(config, selected, datetime.now(UTC))
    assert admission.classes == frozenset({DisclosureClass.SYNTHETIC})
    assert admission.models == frozenset({probe.CODING_MODELS[0] + ":nscale"})
    assert probe.PROMPT == "Return exactly the word READY."
