"""Synthetic HF discovery/chat and disabled live gate; no external provider."""

import ast
import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest

from legoai.governance.disclosure import DisclosureClass, FactBasis
from legoai.governance.provider_control import (
    ProviderDiscoveryMethod,
    ProviderOperation,
)
from legoai.governance.secret import SecretRef, SecretRevisionRef
from legoai.intelligence.model.ports import ModelResponseRejectedError
from legoai.intelligence.model.values import ModelId
from legoai.kernel.identity import TenantId
from legoai.kernel.references import ReferenceScope
from legoai.reference.model_openai_compatible import (
    parse_model_catalog,
    parse_model_list,
)
from legoai.runtime._composition.provider_discovery import (
    DiscoveryOutcome,
    ModelDiscovery,
    discovery_purpose,
)
from legoai.runtime._composition.remote_model import credential_purpose
from legoai.runtime._composition.secret import _provision_interactively
from scripts import hf_inference_compatibility_probe as probe
from tests.support.tls_server import TEST_CA, TlsServer

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
    if args == ["--plan"]:
        assert "LOCAL VALIDATION PENDING" in captured.out
        assert "executable live calls now: 0" in captured.out
    else:
        assert "Live execution refused" in captured.out


@pytest.mark.parametrize(
    "option",
    [
        "--token",
        "--api-key",
        "--model",
        "--repository",
        "--prompt",
        "--config",
        "--method",
    ],
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
    assert admission.method is ProviderDiscoveryMethod.GET
    assert admission.consumer == "hf-inference-compatibility-probe"
    assert admission.credential == exact
    assert admission.not_before == now
    assert admission.not_after == now + timedelta(minutes=15)
    assert probe.DISCOVERY_PURPOSE == discovery_purpose()
    assert probe.CHAT_PURPOSE == credential_purpose()
    with pytest.raises(ValueError, match="separate Secret purpose"):
        probe.discovery_admission(
            SecretRef(exact, "api-key", credential_purpose()), now
        )


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


def test_harness_reuses_governed_runtime_without_network_client() -> None:
    tree = ast.parse(Path(probe.__file__).read_text(encoding="utf-8"))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
    assert not {name.split(".")[0] for name in imports} & {
        "requests",
        "urllib",
        "http",
        "httpx",
        "huggingface_hub",
        "openai",
        "socket",
        "os",
    }
    assert "legoai.runtime.local" in imports


def test_no_hf_identity_in_core() -> None:
    for path in (ROOT / "src/legoai").rglob("*.py"):
        source = path.read_text(encoding="utf-8").lower()
        assert "huggingface" not in source, path
        assert "hf-inference" not in source, path


def catalog_item(**changes: object) -> dict[str, object]:
    return {
        "id": probe.CODING_MODELS[0],
        "architecture": {"input_modalities": ["text"], "output_modalities": ["text"]},
        "providers": [
            {
                "provider": "novita",
                "status": "live",
                "pricing": {"input": 1, "output": 2},
            }
        ],
    } | changes


def observed(*items: dict[str, object]) -> ModelDiscovery:
    catalog = parse_model_catalog(json.dumps({"data": items}).encode())
    return ModelDiscovery(
        DiscoveryOutcome.LISTED, models=tuple(m.model for m in catalog), catalog=catalog
    )


@pytest.mark.parametrize(
    "changes",
    [
        {"id": "unknown/coder"},
        {"id": probe.CODING_MODELS[0] + ":novita"},
        {"providers": []},
        {
            "providers": [
                {
                    "provider": "novita",
                    "status": "error",
                    "pricing": {"input": 1, "output": 1},
                }
            ]
        },
        {"providers": [{"provider": "novita", "status": "live"}]},
        {"architecture": {}},
        {
            "architecture": {
                "input_modalities": ["image"],
                "output_modalities": ["text"],
            }
        },
    ],
)
def test_ineligible_observations(changes: dict[str, object]) -> None:
    assert probe.shortlist(observed(catalog_item(**changes))) == ()


@pytest.mark.parametrize(
    "backend", ["unknown", "auto", "fastest", "cheapest", "preferred", "novita:other"]
)
def test_unpinned_backend_refused(backend: str) -> None:
    result = observed(
        catalog_item(
            providers=[
                {
                    "provider": backend,
                    "status": "live",
                    "pricing": {"input": 1, "output": 1},
                }
            ]
        )
    )
    assert probe.shortlist(result) == ()


def test_shortlist_bound_and_membership() -> None:
    providers = [
        {"provider": key, "status": "live", "pricing": {"input": 1, "output": 1}}
        for key, _, _ in probe.BACKENDS
    ]
    result = observed(
        *(catalog_item(id=model, providers=providers) for model in probe.CODING_MODELS)
    )
    choices = probe.shortlist(result)
    assert len(choices) == 3
    for choice in choices:
        assert any(
            choice.model == m.model and choice.backend in m.providers
            for m in result.catalog
        )
    assert probe.select_pair(result, lambda _: "2", lambda _: None) == choices[1]
    for answer in ("", "0", "4", probe.CODING_MODELS[0], choices[0].request_model):
        assert probe.select_pair(result, lambda _: answer, lambda _: None) is None
    assert probe.shortlist(replace(result, models=())) == ()


def test_selected_pair_freezes_synthetic_admission(tmp_path: Path) -> None:
    config = probe.ProbeConfig.live(tmp_path)
    first = probe.shortlist(observed(catalog_item()))[0]
    second = probe.shortlist(observed(catalog_item(id=probe.CODING_MODELS[1])))[0]
    now = datetime.now(UTC)
    admission = probe.chat_admission(config, first, now)
    assert admission.classes == frozenset({DisclosureClass.SYNTHETIC})
    assert first.request_model in admission.models
    assert second.request_model not in admission.models
    assert probe.chat_admission(config, second, now) != admission
    processor = probe.declaration(config, first)
    assert processor.location.basis is FactBasis.UNKNOWN


@pytest.mark.parametrize(
    "answer,expected_calls", [("1", 2), ("arbitrary/model:novita", 1), ("", 1)]
)
def test_synthetic_get_then_selected_chat(
    tmp_path: Path, answer: str, expected_calls: int
) -> None:
    listing = json.dumps({"data": [catalog_item()]}).encode()
    chat = json.dumps(
        {
            "model": probe.CODING_MODELS[0] + ":novita",
            "choices": [
                {
                    "finish_reason": "stop",
                    "message": {"role": "assistant", "content": "READY"},
                }
            ],
        }
    ).encode()
    lines: list[str] = []
    prompts: list[str] = []

    def read(prompt: str) -> str:
        prompts.append(prompt)
        return CANARY

    with TlsServer(
        expected=CANARY,
        responses={"/v1/models": listing, "/v1/chat/completions": chat},
        methods={"/v1/models": "GET", "/v1/chat/completions": "POST"},
    ) as tls:
        config = replace(
            probe.ProbeConfig.live(tmp_path),
            origin=f"https://localhost:{tls.port}",
            trust_anchor=TEST_CA,
        )
        answers = iter([answer, "y"])
        verdict = probe.run_probe(
            config,
            write=lines.append,
            ask=lambda _: next(answers),
            read=read,
            interactive=lambda: True,
        )
        assert tls.requests == expected_calls
        assert len(prompts) == expected_calls
        assert tls.paths[0] == "GET /v1/models"
        assert tls.bodies[0] == b""
        if expected_calls == 2:
            assert verdict is probe.Classification.HF_COMPATIBILITY_PASS
            body = json.loads(tls.bodies[1])
            assert body["model"] == probe.CODING_MODELS[0] + ":novita"
            assert body["messages"] == [{"role": "user", "content": probe.PROMPT}]
            assert body["stream"] is False
        else:
            assert verdict is probe.Classification.PROVIDER_IDENTITY_INDETERMINATE
    assert CANARY not in "\n".join(lines)
    for file in tmp_path.rglob("*"):
        if file.is_file():
            assert CANARY.encode() not in file.read_bytes()


def test_direct_live_orchestration_gate(tmp_path: Path) -> None:
    with (
        patch("getpass.getpass", side_effect=AssertionError("must not provision")),
        patch("socket.getaddrinfo", side_effect=AssertionError("must not resolve")),
    ):
        assert (
            probe.run_probe(
                probe.ProbeConfig.live(tmp_path),
                write=lambda _: None,
                ask=lambda _: "1",
            )
            is probe.Classification.RESULT_INCONCLUSIVE
        )
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize(
    "mode,model,finish,reply,expected",
    [
        (
            "ok",
            "wrong-model",
            "stop",
            "READY",
            probe.Classification.CHAT_CONTRACT_INCOMPATIBLE,
        ),
        (
            "ok",
            None,
            "length",
            "READY",
            probe.Classification.CHAT_CONTRACT_INCOMPATIBLE,
        ),
        ("ok", None, "stop", CANARY, probe.Classification.RESULT_INCONCLUSIVE),
        ("chunked", None, "stop", "READY", probe.Classification.RESULT_INCONCLUSIVE),
        ("truncated", None, "stop", "READY", probe.Classification.RESULT_INCONCLUSIVE),
        ("401", None, "stop", "READY", probe.Classification.AUTHENTICATION_FAILURE),
        ("403", None, "stop", "READY", probe.Classification.AUTHORIZATION_FAILURE),
        ("429", None, "stop", "READY", probe.Classification.RESULT_INCONCLUSIVE),
        (
            "503",
            None,
            "stop",
            "READY",
            probe.Classification.PROVIDER_AVAILABILITY_FAILURE,
        ),
    ],
)
def test_safe_coarse_failures(
    tmp_path: Path,
    mode: str,
    model: str | None,
    finish: str,
    reply: str,
    expected: probe.Classification,
) -> None:
    response = json.dumps(
        {
            "model": model or probe.CODING_MODELS[0] + ":novita",
            "choices": [
                {
                    "finish_reason": finish,
                    "message": {"role": "assistant", "content": reply},
                }
            ],
        }
    ).encode()
    lines: list[str] = []
    with TlsServer(
        mode,
        expected=CANARY,
        responses={
            "/v1/models": json.dumps({"data": [catalog_item()]}).encode(),
            "/v1/chat/completions": response,
        },
    ) as tls:
        config = replace(
            probe.ProbeConfig.live(tmp_path),
            origin=f"https://localhost:{tls.port}",
            trust_anchor=TEST_CA,
        )
        answers = iter(["1", "y"])
        verdict = probe.run_probe(
            config,
            write=lines.append,
            ask=lambda _: next(answers),
            read=lambda _: CANARY,
            interactive=lambda: True,
        )
        assert verdict is expected
        assert tls.requests == (2 if mode == "ok" else 1)
    assert CANARY not in "\n".join(lines)


@pytest.mark.parametrize("approve", [False, True])
def test_provisioning_purposes_are_separate_and_chat_is_optional(
    tmp_path: Path, approve: bool
) -> None:
    with TlsServer(
        expected=CANARY,
        responses={"/v1/models": json.dumps({"data": [catalog_item()]}).encode()},
    ) as tls:
        config = replace(
            probe.ProbeConfig.live(tmp_path),
            origin=f"https://localhost:{tls.port}",
            trust_anchor=TEST_CA,
        )
        answers = iter(["1", "y" if approve else "n"])
        with patch.object(
            probe, "_provision_interactively", wraps=_provision_interactively
        ) as provision:
            probe.run_probe(
                config,
                write=lambda _: None,
                ask=lambda _: next(answers),
                read=lambda _: CANARY,
                interactive=lambda: True,
            )
            purposes = [call.args[2] for call in provision.call_args_list]
            assert purposes == ["provider-model-discovery"] + (
                ["remote-model-bearer"] if approve else []
            )
        assert tls.requests == (2 if approve else 1)
