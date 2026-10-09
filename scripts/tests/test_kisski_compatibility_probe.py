"""KISSKI-COMPATIBILITY-1 harness: offline, against the synthetic TLS server.

The live provider is never contacted: tests replace only the origin, the
trust anchor (test CA) and the hidden-input reader (synthetic canary
material). Every call goes through the qualified governed paths.
"""

import ast
import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from legoai.governance.disclosure import (
    DisclosureClass,
    FactBasis,
    RetentionKind,
    TrainingUse,
)
from legoai.governance.provider_control import DiscoveryRefusal, ProviderOperation
from legoai.intelligence.model.values import ModelId
from legoai.runtime._composition.provider_discovery import (
    DiscoveryOutcome,
    discovery_consumer,
    discovery_purpose,
)
from legoai.runtime._composition.remote_model import (
    credential_consumer,
    credential_purpose,
)
from legoai.runtime._composition.secret import _provision_interactively
from legoai.runtime.local import open_credential_source
from scripts import kisski_compatibility_probe as probe
from scripts.kisski_compatibility_probe import Classification, ProbeConfig
from tests.support.tls_server import TEST_CA, TlsServer

CANARY = "kisski-key-CANARY-DO-NOT-LEAK-71203"
RAW = "RAW-LISTING-MARKER-4410"
MODELS = "/v1/models"
CHAT = "/v1/chat/completions"
SCRIPT = Path(probe.__file__)


def listing(*ids: str) -> bytes:
    data = [{"id": i, "object": "model", "owned_by": RAW} for i in ids]
    return json.dumps({"object": "list", "data": data}).encode()


def chat_body(model: str = "model-a", content: str = "READY") -> bytes:
    return json.dumps(
        {
            "model": model,
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": content},
                    "finish_reason": "stop",
                }
            ],
        }
    ).encode()


def server(mode: str = "ok", **responses: bytes) -> TlsServer:
    bodies = {MODELS: listing("model-a", "model-b"), CHAT: chat_body()}
    bodies.update({MODELS if k == "models" else CHAT: v for k, v in responses.items()})
    return TlsServer(mode, expected=CANARY, responses=bodies)


class Run:
    def __init__(self, tmp_path: Path, port: int, answer: str = "1") -> None:
        live = ProbeConfig.live(tmp_path)
        self.config = replace(
            live, origin=f"https://localhost:{port}", trust_anchor=TEST_CA
        )
        self.answer = answer
        self.lines: list[str] = []
        self.reads = 0
        self.asked: list[str] = []

    def read(self, prompt: str) -> str:
        self.reads += 1
        return CANARY

    def ask(self, prompt: str) -> str:
        self.asked.append(prompt)
        return self.answer

    def __call__(self) -> Classification:
        return probe.run_probe(
            self.config,
            write=self.lines.append,
            ask=self.ask,
            read=self.read,
            interactive=lambda: True,
        )

    @property
    def output(self) -> str:
        return "\n".join(self.lines)


def leak_free(run: Run, directory: Path) -> None:
    for text in (run.output, *run.asked):
        assert CANARY not in text and RAW not in text and "Bearer" not in text
    for file in directory.rglob("*"):
        if file.is_file():
            data = file.read_bytes()
            assert CANARY.encode() not in data and RAW.encode() not in data, file


# --- Configuration -------------------------------------------------------------


def test_live_provider_facts_are_exact() -> None:
    live = ProbeConfig.live(Path("unused"))
    assert (live.provider_id, live.origin, live.api_root) == (
        "gwdg-saia",
        "https://chat-ai.academiccloud.de",
        "/v1",
    )
    assert live.base_url == "https://chat-ai.academiccloud.de/v1"
    assert live.trust_anchor is None  # system trust store only
    assert probe.PROMPT == "Return exactly the word READY."


def test_declaration_states_only_documented_facts() -> None:
    value = probe.declaration(ProbeConfig.live(Path("unused")))
    assert value.processor.basis is FactBasis.PROVIDER_DECLARED
    assert value.training.value is TrainingUse.NO
    assert value.training.basis is FactBasis.PROVIDER_DECLARED
    # The no-storage statements concern Chat AI conversations, not API logs.
    assert value.retention.kind is RetentionKind.UNKNOWN
    for fact in (value.location, value.retention, value.human_access):
        assert fact.basis is FactBasis.UNKNOWN
    assert value.subprocessors.basis is FactBasis.UNKNOWN


def test_chat_admission_is_synthetic_only_and_exact() -> None:
    now = datetime(2026, 10, 9, 12, tzinfo=UTC)
    value = probe.chat_admission(
        ProbeConfig.live(Path("unused")), ModelId("model-a"), now
    )
    assert value.classes == frozenset({DisclosureClass.SYNTHETIC})
    assert value.repositories == frozenset() and value.conditions == ()
    assert value.models == frozenset({"model-a"})
    assert value.purposes == frozenset({"chat"})
    assert value.bindings == frozenset({probe.BINDING})
    assert value.consumer == probe.PROBE_CONSUMER
    assert value.not_after - value.not_before <= timedelta(minutes=31)


def test_discovery_admission_is_exact(tmp_path: Path) -> None:
    run = Run(tmp_path, 9)
    source: Any = open_credential_source(probe._scope())
    reference = _provision_interactively(
        source._source,
        "k",
        discovery_purpose(),
        discovery_consumer(),
        read=run.read,
        interactive=lambda: True,
    )
    now = datetime(2026, 10, 9, 12, tzinfo=UTC)
    value = probe.discovery_admission(run.config, reference, now)
    assert value.operation is ProviderOperation.MODEL_DISCOVERY
    assert value.consumer == discovery_consumer()
    assert value.credential == reference.exact
    assert (value.provider_id, value.api_root) == ("gwdg-saia", "/v1")
    assert value.not_after - value.not_before <= timedelta(minutes=16)


# --- Synthetic end to end --------------------------------------------------------


def test_synthetic_end_to_end_discovery_then_one_chat(tmp_path: Path) -> None:
    with server() as tls:
        run = Run(tmp_path, tls.port)
        assert run() is Classification.PASS
    assert tls.paths == [f"POST {MODELS}", f"POST {CHAT}"]
    assert tls.connections == 2 and tls.authorized == [True, True]
    assert tls.bodies[0] == b""
    assert json.loads(tls.bodies[1]) == {
        "model": "model-a",
        "messages": [{"role": "user", "content": probe.PROMPT}],
        "stream": False,
        "max_tokens": 16,
    }
    assert run.reads == 2  # the key is typed twice, hidden
    assert "selected model id: model-a" in run.output
    assert "synthetic instruction followed: yes" in run.output
    assert "FINAL CLASSIFICATION: KISSKI COMPATIBILITY PASS" in run.output
    assert "disclosure classes: SYNTHETIC" in run.output
    leak_free(run, tmp_path)


def test_two_separate_revisions_with_distinct_purposes(tmp_path: Path) -> None:
    calls: list[tuple[str, str]] = []
    original = _provision_interactively

    def spy(source: Any, identity: str, purpose: str, consumer: str, **kw: Any) -> Any:
        calls.append((purpose, consumer))
        return original(source, identity, purpose, consumer, **kw)

    with server() as tls, patch.object(probe, "_provision_interactively", spy):
        Run(tmp_path, tls.port)()
    assert calls == [
        (discovery_purpose(), discovery_consumer()),
        (credential_purpose(), credential_consumer()),
    ]


def test_operator_choice_is_honored_never_automatic(tmp_path: Path) -> None:
    with server(chat=chat_body("model-b")) as tls:
        run = Run(tmp_path, tls.port, answer="2")
        assert run() is Classification.PASS
    assert json.loads(tls.bodies[1])["model"] == "model-b"
    assert "1. model-a" in run.output and "2. model-b" in run.output


@pytest.mark.parametrize("answer", ["", "0", "3", "x", "1.0", "-1", "model-a"])
def test_invalid_selection_makes_no_chat_call(tmp_path: Path, answer: str) -> None:
    with server() as tls:
        run = Run(tmp_path, tls.port, answer=answer)
        assert run() is Classification.LOCAL_PREFLIGHT_FAILURE
    assert tls.paths == [f"POST {MODELS}"]


@pytest.mark.parametrize(
    ("mode", "responses", "verdict"),
    [
        ("401", {}, Classification.AUTHENTICATION_FAILURE),
        ("403", {}, Classification.AUTHENTICATION_FAILURE),
        ("404", {}, Classification.MODEL_DISCOVERY_CONTRACT_INCOMPATIBLE),
        ("503", {}, Classification.PROVIDER_AVAILABILITY_FAILURE),
        ("429", {}, Classification.PROVIDER_AVAILABILITY_FAILURE),
        (
            "ok",
            {"models": b"not json"},
            Classification.MODEL_DISCOVERY_CONTRACT_INCOMPATIBLE,
        ),
        ("ok", {"models": listing()}, Classification.RESULT_INCONCLUSIVE),
        ("chunked", {}, Classification.RESULT_INCONCLUSIVE),
        ("truncated", {}, Classification.RESULT_INCONCLUSIVE),
    ],
    ids=[
        "401",
        "403",
        "404",
        "503",
        "429",
        "malformed",
        "empty",
        "chunked",
        "truncated",
    ],
)
def test_discovery_failure_prevents_chat(
    tmp_path: Path, mode: str, responses: dict[str, bytes], verdict: Classification
) -> None:
    with server(mode, **responses) as tls:
        run = Run(tmp_path, tls.port)
        assert run() is verdict
    assert tls.paths == [f"POST {MODELS}"] and tls.connections == 1
    assert "no chat call is made" in run.output
    assert run.asked == []  # no selection prompt without a listing
    leak_free(run, tmp_path)


def test_tls_failure_prevents_chat_and_sends_nothing(tmp_path: Path) -> None:
    with TlsServer(cert="untrusted.pem", expected=CANARY) as tls:
        run = Run(tmp_path, tls.port)
        assert run() is Classification.RESULT_INCONCLUSIVE
    assert tls.requests == 0
    assert "discovery disposition: not_sent" in run.output


@pytest.mark.parametrize(
    "chat", [chat_body("other-model"), b"not json"], ids=["model-identity", "shape"]
)
def test_chat_contract_failure_is_reported_once(tmp_path: Path, chat: bytes) -> None:
    with server(chat=chat) as tls:
        run = Run(tmp_path, tls.port)
        assert run() is Classification.CHAT_CONTRACT_INCOMPATIBLE
    assert tls.paths == [f"POST {MODELS}", f"POST {CHAT}"]  # no retry
    assert "chat attempt state: completed" in run.output


def test_non_ready_reply_is_still_protocol_pass(tmp_path: Path) -> None:
    with server(chat=chat_body(content="Sure! READY" + "x" * 200)) as tls:
        run = Run(tmp_path, tls.port)
        assert run() is Classification.PASS
    assert "synthetic instruction followed: no" in run.output
    reply = next(line for line in run.lines if line.startswith("synthetic reply"))
    assert len(reply) < 64 + 40  # bounded to 64 characters


def _now() -> datetime:
    return datetime.now(UTC)


def test_revisions_never_cross_purposes(tmp_path: Path) -> None:
    run = Run(tmp_path, 9)
    source: Any = open_credential_source(probe._scope())
    chat_ref = _provision_interactively(
        source._source,
        probe.CHAT_IDENTITY,
        credential_purpose(),
        credential_consumer(),
        read=run.read,
        interactive=lambda: True,
    )
    discovery_ref = _provision_interactively(
        source._source,
        probe.DISCOVERY_IDENTITY,
        discovery_purpose(),
        discovery_consumer(),
        read=run.read,
        interactive=lambda: True,
    )
    with patch("socket.create_connection") as connect:
        refused = probe._discover(
            run.config,
            source._source,
            chat_ref,
            _now(),
            _now,
        )
        assert refused.outcome is DiscoveryOutcome.REFUSED
        assert refused.refusal is DiscoveryRefusal.CREDENTIAL_MISMATCH
        verdict = probe._chat(
            replace(run.config, custody=tmp_path / "chat"),
            source,
            discovery_ref,
            ModelId("model-a"),
            _now,
            run.lines.append,
        )
        assert verdict is Classification.LOCAL_PREFLIGHT_FAILURE
        connect.assert_not_called()
    assert "host open refused: invalid_configuration" in run.output


def test_ambient_keys_are_never_used(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    for name in ("OPENAI_API_KEY", "KISSKI_API_KEY", "SAIA_API_KEY", "API_KEY"):
        monkeypatch.setenv(name, "ambient-must-never-be-used")
    with server() as tls:
        assert Run(tmp_path, tls.port)() is Classification.PASS
    assert tls.authorized == [True, True]  # only the hidden-input canary


# --- Live entry point guards -------------------------------------------------------


def test_plan_mode_has_no_network_prompt_or_credential(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with (
        patch("socket.create_connection") as connect,
        patch("socket.getaddrinfo") as resolve,
        patch("getpass.getpass") as hidden,
        patch("builtins.input") as typed,
    ):
        assert probe.main(["--plan"]) == 0
        for mock in (connect, resolve, hidden, typed):
            mock.assert_not_called()
    out = capsys.readouterr().out
    assert "POST /v1/models" in out and "POST /v1/chat/completions" in out
    assert "maximum 2" in out and "SYNTHETIC only" in out


def test_live_entry_requires_an_interactive_terminal(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with (
        patch("getpass.getpass") as hidden,
        patch("socket.create_connection") as connect,
        patch("sys.stdin.isatty", return_value=False),
    ):
        assert probe.main([]) == 2
        hidden.assert_not_called()
        connect.assert_not_called()
    assert "LOCAL-PREFLIGHT FAILURE" in capsys.readouterr().out


def test_only_option_is_plan() -> None:
    with pytest.raises(SystemExit):
        probe.main(["--api-key", "x"])


def test_script_reads_no_ambient_or_file_credential_and_no_forgeai() -> None:
    tree = ast.parse(SCRIPT.read_text(encoding="utf-8"))
    imports: set[str] = set()
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
        elif isinstance(node, ast.Attribute):
            names.add(node.attr)
        elif isinstance(node, ast.Name):
            names.add(node.id)
    assert not names & {"environ", "getenv", "dotenv", "argv", "load_dotenv"}
    assert not any(
        t.split(".")[0] in {"os", "requests", "httpx", "urllib", "http", "openai"}
        for t in imports
    )
    assert not any("forgeai" in t or "engineering" in t for t in imports)
    text = SCRIPT.read_text(encoding="utf-8").lower()
    assert "api_key" not in text and "authorization" not in text
