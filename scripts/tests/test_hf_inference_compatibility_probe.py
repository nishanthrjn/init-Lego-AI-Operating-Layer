"""Offline tests for the blocked HF preflight, not live HF qualification."""

import ast
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest

from legoai.governance.provider_control import ProviderOperation
from legoai.governance.secret import SecretRef, SecretRevisionRef
from legoai.intelligence.model.ports import ModelResponseRejectedError
from legoai.intelligence.model.values import ModelId
from legoai.kernel.identity import TenantId
from legoai.kernel.references import ReferenceScope
from legoai.reference.model_openai_compatible import parse_model_list
from legoai.runtime._composition.provider_discovery import discovery_purpose
from legoai.runtime._composition.remote_model import credential_purpose
from scripts import hf_inference_compatibility_probe as probe

ROOT = Path(__file__).resolve().parents[2]
CANARY = "hf-SYNTHETIC-CANARY-DO-NOT-LEAK-71426"


@pytest.mark.parametrize("args,code", [(["--plan"], 0), ([], 2), (["--live"], 2)])
def test_every_mode_has_zero_io(
    args: list[str],
    code: int,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("HF_TOKEN", CANARY)
    with (
        patch("socket.getaddrinfo", side_effect=AssertionError("DNS forbidden")),
        patch("socket.socket", side_effect=AssertionError("network forbidden")),
        patch("getpass.getpass", side_effect=AssertionError("Secret read forbidden")),
        patch("builtins.input", side_effect=AssertionError("input forbidden")),
        patch("builtins.open", side_effect=AssertionError("file read forbidden")),
    ):
        assert probe.main(args) == code
    captured = capsys.readouterr()
    assert CANARY not in captured.out + captured.err
    assert "PREFLIGHT BLOCKED" in captured.out
    assert "executable calls now: 0" in captured.out
    assert "PROVIDER_IDENTITY_INDETERMINATE" in captured.out


@pytest.mark.parametrize(
    "option", ["--token", "--api-key", "--model", "--repository", "--prompt", "--config"]
)
def test_untrusted_arguments_never_echo(
    option: str, capsys: pytest.CaptureFixture[str]
) -> None:
    with pytest.raises(SystemExit) as error:
        probe.main([option, CANARY])
    assert error.value.code == 2
    captured = capsys.readouterr()
    assert CANARY not in captured.out + captured.err


def test_exact_discovery_admission_and_short_window() -> None:
    exact = SecretRevisionRef(
        ReferenceScope("operator", TenantId("hf-probe-test")), "key", "r1", "m1"
    )
    credential = SecretRef(exact, "api-key", discovery_purpose())
    now = datetime(2026, 10, 10, tzinfo=UTC)
    admission = probe.discovery_admission(credential, now)
    assert admission.provider_id == "huggingface-inference-router"
    assert admission.endpoint_origin == "https://router.huggingface.co"
    assert admission.api_root == "/v1"
    assert admission.operation is ProviderOperation.MODEL_DISCOVERY
    assert admission.consumer == "hf-inference-compatibility-probe"
    assert admission.credential == exact
    assert admission.not_before == now
    assert admission.not_after == now + timedelta(minutes=15)
    assert probe.DISCOVERY_PURPOSE == discovery_purpose()
    assert probe.CHAT_PURPOSE == credential_purpose()
    with pytest.raises(ValueError, match="separate Secret purpose"):
        probe.discovery_admission(SecretRef(exact, "api-key", credential_purpose()), now)


def test_hf_documented_shape_is_accepted_but_backend_metadata_is_lost() -> None:
    # Synthetic shape from HF Hub API docs, NOT observed provider data.
    item: dict[str, object] = {
        "id": "example/coder",
        "object": "model",
        "architecture": {"input_modalities": ["text"], "output_modalities": ["text"]},
        "providers": [{"provider": "example", "status": "live", "pricing": {}}],
    }
    assert parse_model_list(json.dumps({"data": [item]}).encode()) == (
        ModelId("example/coder"),
    )
    # IDs alone cannot prove any backend is live, text-capable or affordable.
    item["providers"] = [{"provider": "other", "status": "error"}]
    assert parse_model_list(json.dumps({"data": [item]}).encode()) == (
        ModelId("example/coder"),
    )


@pytest.mark.parametrize(
    "data", [[{"id": "x"}, {"id": "x"}], [{"id": ""}], [{"id": 1}]]
)
def test_existing_parser_still_requires_valid_unique_ids(data: object) -> None:
    with pytest.raises(ModelResponseRejectedError):
        parse_model_list(json.dumps({"data": data}).encode())


def test_plan_never_claims_live_authority_or_compatibility() -> None:
    text = "\n".join(probe.plan_lines())
    assert "GET https://router.huggingface.co/v1/models" in text
    assert "POST https://router.huggingface.co/v1/chat/completions" in text
    assert "SYNTHETIC only" in text
    assert "no retry; no fallback" in text
    assert "1 discovery + 1 chat" in text
    assert "HF_COMPATIBILITY_PASS" not in text
    assert probe.PROMPT == "Return exactly the word READY."


def test_preflight_has_no_execution_or_material_access_dependency() -> None:
    tree = ast.parse(Path(probe.__file__).read_text(encoding="utf-8"))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
    assert imports == {
        "argparse",
        "datetime",
        "enum",
        "typing",
        "legoai.governance.provider_control",
        "legoai.governance.secret",
    }


def test_no_hf_identity_in_core() -> None:
    for path in (ROOT / "src/legoai").rglob("*.py"):
        source = path.read_text(encoding="utf-8").lower()
        assert "huggingface" not in source, path
        assert "hf-inference" not in source, path
