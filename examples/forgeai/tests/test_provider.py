"""Provider interoperability: loopback HTTP and synthetic TLS only."""

import asyncio
import json
import sys
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

import pytest
from legoai.governance.disclosure import DisclosureClass, RepositoryIdentity
from legoai.intelligence.model.values import ModelFailure, ProviderId
from legoai.reference.secret import _ProvisionedSecretSource
from legoai.runtime._composition.secret import _provision_interactively
from legoai.runtime.api import ModelDeployment, RemoteDisclosureConfig
from legoai_engineering.repository.workspace import RepositoryPath
from test_disclosure import admission, declaration
from tls_server import TEST_CA, TlsServer

from forgeai.composition import provider_session, summarize_provider_file
from forgeai.provider import ProviderProfile, ReadOnlyApproval, synthetic_valid
from forgeai.provider_cli import main
from forgeai.remote import BINDING, classes


def body(text: str, model: str = "model-a") -> bytes:
    return json.dumps(
        {
            "model": model,
            "choices": [
                {
                    "message": {"role": "assistant", "content": text},
                    "finish_reason": "stop",
                }
            ],
        }
    ).encode()


@contextmanager
def endpoint(
    replies: tuple[tuple[int, bytes], ...],
) -> Iterator[tuple[str, list[dict[str, object]]]]:
    seen: list[dict[str, object]] = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: object) -> None:
            pass

        def do_POST(self) -> None:
            seen.append(
                json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            )
            assert self.path == "/v1/chat/completions"
            assert self.headers.get("Authorization") is None
            status, response = replies[min(len(seen) - 1, len(replies) - 1)]
            self.send_response(status)
            self.send_header("Content-Length", str(len(response)))
            self.end_headers()
            self.wfile.write(response)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/v1", seen
    finally:
        server.shutdown()
        server.server_close()
        thread.join(5)


def profile(url: str = "http://127.0.0.1:8000/v1") -> ProviderProfile:
    return ProviderProfile(
        "openai_compatible",
        url,
        "model-a",
        ModelDeployment.LOCAL,
        ProviderId("operator-endpoint"),
    )


def replies() -> tuple[tuple[int, bytes], ...]:
    return tuple(
        (200, body(text))
        for text in (
            "READY",
            '{"status":"READY"}',
            "def add(a, b):\n    return a + b\n",
            "A small function.",
        )
    )


@pytest.mark.parametrize(
    "url",
    [
        "http://example.com/v1",
        "http://localhost/v1",
        "http://0.0.0.0/v1",
        "http://127.0.0.1:0/v1",
        "http://user:pass@127.0.0.1/v1",
        "http://127.0.0.1/v1?token=x",
        "http://127.0.0.1/v1#x",
        "http://127.0.0.1/../v1",
        "http://127.0.0.1/%2e/v1",
        "http://127.0.0.1/" + "x" * 512,
    ],
)
def test_local_endpoint_boundary(url: str) -> None:
    with pytest.raises(ValueError):
        profile(url)


@pytest.mark.parametrize("timeout", [0, -1, 301, float("inf"), float("nan"), True])
def test_timeout_bound(timeout: float) -> None:
    with pytest.raises(ValueError):
        replace(profile(), timeout=timeout)


@pytest.mark.parametrize("model", ["", "*", " model", "x\n", "x" * 257])
def test_exact_model(model: str) -> None:
    with pytest.raises(ValueError):
        replace(profile(), model=model)


def test_neutral_configuration_and_no_auth() -> None:
    assert (
        replace(profile(), model="Qwen/Qwen2.5-Coder-14B-Instruct-AWQ").auth_mode
        == "none"
    )
    with pytest.raises(ValueError):
        replace(profile(), auth_mode="bearer")
    with pytest.raises(ValueError):
        replace(profile(), provider_type="notebook")
    with pytest.raises(ValueError):
        replace(profile(), mode=ModelDeployment.REMOTE)


def test_operator_cli_qualifies_before_separate_file_approval(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    (tmp_path / "source.py").write_text("def add(a,b):\n return a+b")
    with endpoint(replies()) as (url, seen):
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "provider",
                "--mode",
                "local",
                "--base-url",
                url,
                "--model",
                "model-a",
                "--provider",
                "local-fixture",
                "--repository",
                str(tmp_path),
                "--repository-id",
                "repo-a",
                "--target",
                "source.py",
            ],
        )

        def approve_file(prompt: str) -> str:
            assert len(seen) == 3
            return "y"

        monkeypatch.setattr("builtins.input", approve_file)
        assert main() == 0
        assert len(seen) == 4
        assert "READ-ONLY RESPONSE" in capsys.readouterr().out


def test_three_synthetic_then_one_explicit_read_no_mutation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "source.py"
    target.write_text("def add(a, b):\n    return a + b\n")
    (tmp_path / "hidden.py").write_text("NEVER-DISCLOSE-CANARY")
    before = {p.name: p.read_bytes() for p in tmp_path.iterdir()}
    monkeypatch.setenv("HTTP_PROXY", "http://127.0.0.1:1")
    with endpoint(replies()) as (url, seen), provider_session(profile(url)) as session:

        async def run() -> None:
            qualified = await session.qualify()
            assert qualified.failure is None and qualified.checks == (
                "ready",
                "json",
                "add",
            )
            approval = ReadOnlyApproval(
                RepositoryIdentity("repo-a"),
                RepositoryPath("source.py"),
                "model-a",
                url,
            )
            result = await summarize_provider_file(
                session, tmp_path, approval, approve=lambda _: True
            )
            assert result.failure is None and result.checks == ("read_only",)
            assert result.summary == "A small function."
            assert result.response_digest is not None
            with pytest.raises(ValueError):
                await session.qualify()
            with pytest.raises(ValueError):
                await summarize_provider_file(
                    session, tmp_path, approval, approve=lambda _: True
                )

        asyncio.run(run())
        assert len(seen) == 4
        assert all(
            x["model"] == "model-a" and x["temperature"] == 0 and x["max_tokens"] == 512
            for x in seen
        )
        assert "NEVER-DISCLOSE-CANARY" not in json.dumps(seen)
        assert "source.py" not in json.dumps(seen[:3])
    assert before == {p.name: p.read_bytes() for p in tmp_path.iterdir()}


def test_approval_decline_and_prequalification_read_block(tmp_path: Path) -> None:
    with endpoint(replies()) as (url, seen), provider_session(profile(url)) as session:
        approval = ReadOnlyApproval(
            RepositoryIdentity("repo-a"), RepositoryPath("missing.py"), "model-a", url
        )

        async def run() -> None:
            with pytest.raises(ValueError):
                await summarize_provider_file(
                    session, tmp_path, approval, approve=lambda _: True
                )
            assert (await session.qualify()).failure is None
            result = await summarize_provider_file(
                session, tmp_path, approval, approve=lambda _: False
            )
            assert result.failure is ModelFailure.DISCLOSURE_NOT_APPROVED

        asyncio.run(run())
        assert len(seen) == 3


@pytest.mark.parametrize(
    ("status", "response", "failure"),
    [
        (402, b'{"error":"SECRET-CANARY"}', ModelFailure.REQUEST_REJECTED),
        (
            404,
            b'{"error":{"code":"model_not_found","message":"SECRET-CANARY"}}',
            ModelFailure.MODEL_UNAVAILABLE,
        ),
        (404, b"{}", ModelFailure.REQUEST_REJECTED),
        (429, b"{}", ModelFailure.REQUEST_REJECTED),
        (503, b"{}", ModelFailure.REQUEST_REJECTED),
        (200, b"{}", ModelFailure.PROTOCOL_INCOMPATIBLE),
        (200, body("READY", "other-model"), ModelFailure.PROTOCOL_INCOMPATIBLE),
        (200, body("wrong"), ModelFailure.RESPONSE_INVALID),
        (200, body("x" * 4097), ModelFailure.RESPONSE_INVALID),
    ],
)
def test_failure_no_retry_fallback_or_leak(
    status: int, response: bytes, failure: ModelFailure
) -> None:
    with (
        endpoint(((status, response),)) as (url, seen),
        provider_session(profile(url)) as session,
    ):
        result = asyncio.run(session.qualify())
        assert result.failure is failure
        assert "SECRET-CANARY" not in repr(result)
        assert len(seen) == 1


def test_fixed_contracts_never_execute_code() -> None:
    assert not synthetic_valid("add", "import os\ndef add(a,b):\n return a+b")
    assert not synthetic_valid("json", '{"status":"READY","status":"READY"}')
    assert not synthetic_valid("json", '```json\n{"status":"READY"}\n```')


@pytest.mark.parametrize("target", [".env", "oversized.py", "missing.py"])
def test_invalid_target_stops_before_repository_call(
    tmp_path: Path, target: str
) -> None:
    from legoai_engineering.repository.errors import WorkspaceError

    (tmp_path / ".env").write_text("SECRET-CANARY")
    (tmp_path / "oversized.py").write_text("x" * 16_385)
    with endpoint(replies()) as (url, seen), provider_session(profile(url)) as session:

        async def run() -> None:
            assert (await session.qualify()).failure is None
            approval = ReadOnlyApproval(
                RepositoryIdentity("repo-a"), RepositoryPath(target), "model-a", url
            )
            with pytest.raises(WorkspaceError):
                await summarize_provider_file(
                    session, tmp_path, approval, approve=lambda _: True
                )

        asyncio.run(run())
        assert len(seen) == 3


def test_traversal_target_is_not_an_approval() -> None:
    from legoai_engineering.repository.errors import WorkspaceBoundaryError

    with pytest.raises(WorkspaceBoundaryError):
        RepositoryPath("../secret.py")


@pytest.mark.parametrize("repository_admitted", [False, True])
def test_remote_secret_custody_synthetic_only_blocks_repository(
    tmp_path: Path, repository_admitted: bool
) -> None:
    now = datetime.now(UTC)
    token = "SYNTHETIC-SECRET-CANARY"
    contents = iter(
        (
            "READY",
            '{"status":"READY"}',
            "def add(a,b):\n return a+b",
            "A small function.",
        )
    )
    with TlsServer(expected=token) as server:

        def next_body() -> None:
            server.responses["/v1/chat/completions"] = body(next(contents))

        server.on_request = next_body
        origin = f"https://localhost:{server.port}"
        admitted = frozenset({DisclosureClass.SYNTHETIC})
        if repository_admitted:
            admitted |= classes(derived=False)
        adm = admission(
            admitted,
            bindings=frozenset({BINDING}),
            endpoint_origin=origin,
            not_before=now - timedelta(seconds=1),
            not_after=now + timedelta(minutes=20),
        )
        policy = RemoteDisclosureConfig((declaration(endpoint_origin=origin),), (adm,))
        remote = ProviderProfile(
            "openai_compatible",
            origin + "/v1",
            "model-a",
            ModelDeployment.REMOTE,
            ProviderId("remote-endpoint"),
            10,
            "secret_source",
            policy,
            tmp_path,
        )
        with pytest.raises(ValueError, match="one hour"):
            replace(
                remote,
                disclosure_policy=replace(
                    policy,
                    admissions=(replace(adm, not_after=now + timedelta(hours=2)),),
                ),
            )

        def provision(
            source: _ProvisionedSecretSource, identity: str, purpose: str, consumer: str
        ) -> object:
            return _provision_interactively(
                source,
                identity,
                purpose,
                consumer,
                read=lambda _: token,
                interactive=lambda: True,
            )

        with patch("legoai.runtime.local._provision_interactively", provision):
            with provider_session(remote, trust_anchor=TEST_CA) as session:
                root = tmp_path / "repository"
                root.mkdir()
                (root / "source.py").write_text("def add(a,b):\n return a+b")

                async def run() -> None:
                    result = await session.qualify()
                    assert result.failure is None
                    approval = ReadOnlyApproval(
                        RepositoryIdentity("repo-a"),
                        RepositoryPath("source.py"),
                        "model-a",
                        remote.base_url,
                    )
                    result = await summarize_provider_file(
                        session, root, approval, approve=lambda _: True
                    )
                    assert result.failure is (
                        None
                        if repository_admitted
                        else ModelFailure.DISCLOSURE_NOT_APPROVED
                    )
                    assert token not in repr(result) + repr(remote)

                asyncio.run(run())
        assert server.requests == (4 if repository_admitted else 3) and all(
            server.authorized
        )
        assert all(json.loads(b)["temperature"] == 0 for b in server.bodies)
        assert list(tmp_path.iterdir())  # existing custody plane produced records
