"""Synthetic TLS only: ForgeAI uses the qualified public remote invocation path."""

import asyncio
import json
import os
import shutil
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest
from forgeai_support import (
    REVIEW_ACCEPT,
    REVIEW_CHANGES,
    REWORK,
    FakeSandbox,
    approve,
    config,
    proposal,
    replay,
    repository,
    snapshot,
    task,
)
from legoai.governance.disclosure import (
    DisclosureAdmission,
    DisclosureClass,
    RepositoryIdentity,
)
from legoai.governance.secret import SecretRef
from legoai.intelligence.model.values import ProviderId
from legoai.kernel.effects import EffectExtent
from legoai.reference.secret import _ProvisionedSecretSource
from legoai.runtime._composition.secret import _provision_interactively
from legoai.runtime.api import (
    CredentialSource,
    HostError,
    RemoteDisclosureConfig,
    RemoteModelRuntime,
)
from legoai_engineering.repository.workspace import RepositoryPath
from test_disclosure import admission, declaration
from tls_server import TEST_CA, TlsServer

from forgeai.cli import _parse, main, remote_confirmer, summarize
from forgeai.composition import (
    ForgeAIConfig,
    bind_remote,
    prepare_run,
    remote_credentials,
)
from forgeai.domain import (
    CheckProfile,
    OperatorDecision,
    ProposalReview,
    TaskDisposition,
    TaskFailure,
    TaskRequest,
    TaskResult,
)
from forgeai.guard import WorkspaceGuard
from forgeai.remote import (
    BINDING,
    CONSUMER,
    RemoteProfile,
    classes,
    load_profile,
)
from forgeai.repository_context import ContextOutcome, ContextReason

CANARY = "forgeai-synthetic-secret-884291-NO-LEAK"
ROOT = Path(__file__).resolve().parents[3]


def profile(port: int, now: datetime) -> RemoteProfile:
    origin = f"https://localhost:{port}"
    decl = declaration(endpoint_origin=origin)
    admissions = tuple(
        admission(
            classes=classes(derived=True),
            bindings=frozenset({BINDING}),
            admission_id=consumer,
            consumer=consumer,
            endpoint_origin=origin,
            not_before=now - timedelta(seconds=1),
            not_after=now + timedelta(minutes=30),
        )
        for consumer in (CONSUMER,)
    )
    return RemoteProfile(
        origin + "/v1",
        "model-a",
        ProviderId("remote-endpoint"),
        RepositoryIdentity("repo-a"),
        RemoteDisclosureConfig((decl,), admissions),
    )


def body(content: str) -> bytes:
    return json.dumps(
        {
            "model": "model-a",
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": content},
                    "finish_reason": "stop",
                }
            ],
        }
    ).encode()


@contextmanager
def configured(
    tmp_path: Path,
    server: TlsServer,
    *,
    root: Path | None = None,
    request: TaskRequest | None = None,
    policy: RemoteProfile | None = None,
) -> Iterator[tuple[ForgeAIConfig, CredentialSource]]:
    root = root or repository(tmp_path)
    request = request or task()
    base = config(
        root,
        replay(),
        editable=tuple(t.path.value for t in request.targets),
        context=tuple(p.value for p in request.context),
    )
    now = datetime.now(UTC)
    source = remote_credentials(base)
    custody = tmp_path / "custody"
    custody.mkdir()
    runtime = RemoteModelRuntime(source, custody, timedelta(minutes=5), TEST_CA)

    # Only the existing S1 trusted bootstrap seam receives synthetic material.
    def synthetic(
        source: _ProvisionedSecretSource, identity: str, purpose: str, consumer: str
    ) -> SecretRef:
        return _provision_interactively(
            source,
            identity,
            purpose,
            consumer,
            read=lambda _: CANARY,
            interactive=lambda: True,
        )

    try:
        with patch("legoai.runtime.local._provision_interactively", synthetic):
            cfg = bind_remote(
                base, policy or profile(server.port, now), request, runtime, now=now
            )
        yield cfg, source
    finally:
        source.close()


def execute(
    cfg: ForgeAIConfig,
    *,
    confirm: bool = True,
    request: TaskRequest | None = None,
    after_approval: Callable[[], None] = lambda: None,
) -> tuple[TaskResult, list[str], FakeSandbox]:
    log: list[str] = []
    checks = FakeSandbox()

    def confirmation(text: str) -> bool:
        log.append("disclosure")
        assert "src/inventory/stock.py" in text
        assert "read-only context" in text and "Reviewer" in text
        assert CANARY not in text
        return confirm

    def approval(review: ProposalReview) -> OperatorDecision:
        log.append("mutation")
        after_approval()
        return approve(review)

    prepared = prepare_run(
        cfg,
        WorkspaceGuard(),
        confirm_context=lambda inventory: True,
        approve=approval,
        sandbox=checks,
        confirm_disclosure=confirmation,
    )
    result = asyncio.run(prepared.worker.run(request or task(), prepared.context))
    return result, log, checks


@pytest.mark.parametrize("rework", [False, True])
def test_remote_coding_review_and_rework_tls(
    tmp_path: Path, rework: bool, caplog: pytest.LogCaptureFixture
) -> None:
    outputs = (
        [proposal(), REVIEW_CHANGES, REWORK, REVIEW_ACCEPT]
        if rework
        else [proposal(), REVIEW_ACCEPT]
    )
    with TlsServer(expected=CANARY) as server:

        def respond() -> None:
            server.responses["/v1/chat/completions"] = body(
                outputs[server.requests - 1]
            )

        server.on_request = respond
        with configured(tmp_path, server) as (cfg, _):
            result, log, checks = execute(cfg)
            assert result.disposition is TaskDisposition.SUCCEEDED
            assert server.requests == len(outputs) == len(server.authorized)
            assert all(server.authorized)
            assert log == ["disclosure"] + ["mutation"] * (2 if rework else 1)
            assert checks.calls == (6 if rework else 3)
            assert CANARY not in repr(result) + summarize(result)
            assert all(CANARY.encode() not in b for b in server.bodies)
            assert CANARY not in caplog.text
            assert (cfg.remote_runtime.custody / "remote-attempts.db").is_file()  # type: ignore[union-attr]


def test_decline_has_no_provider_mutation_checks_or_rework(tmp_path: Path) -> None:
    with TlsServer(expected=CANARY) as server, configured(tmp_path, server) as (cfg, _):
        before = snapshot(cfg.repository)
        result, log, checks = execute(cfg, confirm=False)
        assert result.failure is TaskFailure.MODEL_DISCLOSURE_REFUSED
        assert server.requests == server.connections == checks.calls == 0
        assert log == ["disclosure"] and snapshot(cfg.repository) == before
        assert not result.evidence.attempts


def test_project_preparation_refusal_precedes_remote_confirmation(
    tmp_path: Path,
) -> None:
    with TlsServer(expected=CANARY) as server, configured(tmp_path, server) as (cfg, _):
        uv = shutil.which("uv")
        assert uv is not None
        cfg = replace(cfg, check_profile=CheckProfile.PROJECT, uv_executable=Path(uv))
        result, log, checks = execute(cfg)
        assert result.failure is TaskFailure.CHECK_ENVIRONMENT_UNAVAILABLE
        assert server.connections == checks.calls == 0 and not log


@pytest.mark.parametrize("change", ["task", "target", "context"])
def test_changed_task_scope_never_reuses_approval(tmp_path: Path, change: str) -> None:
    request = task()
    if change == "task":
        request = replace(request, objective="different task")
    elif change == "target":
        request = replace(request, targets=request.targets[:1])
    else:
        request = replace(request, context=(RepositoryPath("pyproject.toml"),))
    with TlsServer() as server, configured(tmp_path, server) as (cfg, _):
        before = snapshot(cfg.repository)
        result, log, checks = execute(cfg, request=request)
        inventory = result.evidence.context_preflight
        assert inventory is not None
        if change == "context":
            # Undeclared context now fails at the earlier read-authorization gate.
            assert result.failure is TaskFailure.EVIDENCE_DENIED
            assert inventory.outcome is ContextOutcome.CONTEXT_INCOMPLETE
            assert inventory.reason is ContextReason.DENIED
            assert not result.evidence.context_confirmed
        else:
            assert result.failure is TaskFailure.MODEL_DISCLOSURE_REFUSED
            assert inventory.outcome is ContextOutcome.READY_FOR_CONTEXT_CONFIRMATION
            assert inventory.reason is None
            assert result.evidence.context_confirmed
        assert result.disposition is TaskDisposition.REJECTED
        assert not result.evidence.attempts
        assert not log and server.requests == server.connections == checks.calls == 0
        assert snapshot(cfg.repository) == before


def test_changed_configured_context_refused_before_worker(tmp_path: Path) -> None:
    with TlsServer() as server, configured(tmp_path, server) as (cfg, _):
        before = snapshot(cfg.repository)
        changed = replace(cfg, context_paths=(RepositoryPath("pyproject.toml"),))
        checks = FakeSandbox()
        # Configured read paths cannot widen the already-bound remote task.
        # Composition refuses this mismatch before returning a runnable worker.
        with pytest.raises(
            ValueError, match="^remote task scope differs from configured scope$"
        ):
            prepare_run(
                changed,
                WorkspaceGuard(),
                approve=lambda _: pytest.fail("mutation approval reached"),
                confirm_context=lambda _: pytest.fail("context confirmation reached"),
                confirm_disclosure=lambda _: pytest.fail("disclosure reached"),
                sandbox=checks,
            )
        assert server.requests == server.connections == checks.calls == 0
        assert snapshot(cfg.repository) == before


@pytest.mark.parametrize(
    "fault",
    [
        "missing",
        "expired",
        "future",
        "provider",
        "model",
        "origin",
        "root",
        "repository_class",
        "revision",
        "reviewer",
        "purpose",
    ],
)
def test_bad_disclosure_refuses_before_provider(tmp_path: Path, fault: str) -> None:
    now = datetime.now(UTC)
    with TlsServer() as server:
        value = profile(server.port, now)
        (a,) = value.policy.admissions
        admissions: tuple[DisclosureAdmission, ...]
        if fault == "missing":
            admissions = ()
        else:
            if fault == "expired":
                a = replace(
                    a,
                    not_before=now - timedelta(minutes=30),
                    not_after=now - timedelta(seconds=1),
                )
            elif fault == "future":
                a = replace(a, not_before=now + timedelta(minutes=1))
            elif fault == "provider":
                a = replace(a, provider_id="another-provider")
            elif fault == "model":
                a = replace(a, models=frozenset({"another-model"}))
            elif fault == "origin":
                a = replace(a, endpoint_origin="https://other.invalid")
            elif fault == "root":
                a = replace(a, api_root="/other")
            elif fault == "revision":
                a = replace(a, declaration_revision="stale")
            elif fault == "reviewer":
                a = replace(a, consumer="wrong-consumer")
            elif fault == "purpose":
                a = replace(a, purposes=frozenset({"embedding"}))
            elif fault == "repository_class":
                kept = frozenset(
                    {DisclosureClass.TASK_TEXT, DisclosureClass.PLATFORM_INSTRUCTION}
                )
                a = replace(
                    a,
                    classes=kept,
                    conditions=tuple(
                        c for c in a.conditions if c.disclosure_class in kept
                    ),
                    repositories=frozenset(),
                )
            admissions = (a,)
        with pytest.raises((ValueError, HostError)):
            value = replace(value, policy=replace(value.policy, admissions=admissions))
            with configured(tmp_path, server, policy=value):
                pass
        assert server.connections == 0


@pytest.mark.parametrize("mode", ["expired", "retired"])
def test_currentness_between_coding_and_review(tmp_path: Path, mode: str) -> None:
    with TlsServer(
        expected=CANARY, responses={"/v1/chat/completions": body(proposal())}
    ) as server:
        with configured(tmp_path, server) as (cfg, source):
            now = datetime.now(UTC)

            def invalidate(review: ProposalReview) -> OperatorDecision:
                nonlocal now
                if mode == "expired":
                    now += timedelta(hours=2)
                else:
                    provider = cfg.host.bindings[0].provider
                    source.retire(provider.bearer_credential)  # type: ignore[union-attr,arg-type]
                return approve(review)

            prepared = prepare_run(
                cfg,
                WorkspaceGuard(),
                confirm_context=lambda inventory: True,
                approve=invalidate,
                sandbox=FakeSandbox(),
                clock=lambda: now,
                confirm_disclosure=lambda _: True,
            )
            result = asyncio.run(prepared.worker.run(task(), prepared.context))
            assert result.disposition is TaskDisposition.FAILED
            assert server.requests == 1
            assert CANARY not in repr(result) + summarize(result)


@pytest.mark.parametrize("mode", ["500", "truncated", "malformed"])
def test_provider_failure_has_no_retry_or_fallback(tmp_path: Path, mode: str) -> None:
    with (
        TlsServer(mode, expected=CANARY) as server,
        configured(tmp_path, server) as (cfg, _),
    ):
        result, log, checks = execute(cfg)
        assert result.disposition is TaskDisposition.FAILED
        assert server.requests == 1 and checks.calls == 0 and log == ["disclosure"]
        assert CANARY not in repr(result)
        if mode in {"truncated", "malformed"}:
            assert result.evidence.model_effect is EffectExtent.UNKNOWN


@pytest.mark.parametrize(
    "answer,expected",
    [("", False), ("no", False), ("Y", True), ("yes", True), ("sure", False)],
)
def test_confirmation_is_explicit_and_separate(answer: str, expected: bool) -> None:
    output: list[str] = []
    assert remote_confirmer(lambda _: answer, output.append)("preview") is expected
    assert output == ["preview"]
    assert not remote_confirmer(None, output.append)("preview")


def test_cli_flow_previews_disclosure_then_patch(tmp_path: Path) -> None:
    from forgeai.cli import _execute

    with TlsServer(expected=CANARY) as server, configured(tmp_path, server) as (cfg, _):

        def respond() -> None:
            server.responses["/v1/chat/completions"] = body(
                proposal() if server.requests == 1 else REVIEW_ACCEPT
            )

        server.on_request = respond
        output: list[str] = []
        prompts: list[str] = []

        def answer(prompt: str) -> str:
            prompts.append(prompt)
            if len(prompts) == 1:
                assert "Confirm" in prompt and server.requests == 0
            elif len(prompts) == 2:
                assert "Send" in prompt and server.requests == 0
                assert "task digest:" in output[-1]
            else:
                assert "Apply" in prompt and server.requests == 1
                assert "--- proposed patch" in "\n".join(output)
            return "yes"

        checks = FakeSandbox()

        def prepare(*args, **kwargs):  # type: ignore[no-untyped-def]
            return prepare_run(*args, **kwargs, sandbox=checks)

        with patch("forgeai.cli.prepare_run", prepare):
            code = _execute(
                cfg,
                task(),
                "synthetic remote",
                ask=answer,
                out=output.append,
                ready=lambda _: None,
            )
        assert code == 0 and len(prompts) == 3 and server.requests == 2
        assert checks.calls == 3 and CANARY not in "\n".join(output)


@pytest.mark.parametrize("fault", ["review_consumer", "rework_diagnostics"])
def test_invocation_gate_refuses_later_unadmitted_material(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fault: str,
) -> None:
    from legoai.runtime.api import ExecutionDisclosure

    with TlsServer(
        expected=CANARY, responses={"/v1/chat/completions": body(proposal())}
    ) as server:
        with configured(tmp_path, server) as (cfg, _):
            if fault == "review_consumer":
                original = RemoteProfile.disclosure

                def changed(
                    self: RemoteProfile, *, derived: bool
                ) -> ExecutionDisclosure:
                    result = original(self, derived=derived)
                    return (
                        replace(result, consumer="wrong-reviewer")
                        if derived
                        else result
                    )

                monkeypatch.setattr(RemoteProfile, "disclosure", changed)
            else:
                assert cfg.remote_profile is not None
                profile_value = cfg.remote_profile
                (a,) = profile_value.policy.admissions
                kept = a.classes - {DisclosureClass.DERIVED_DIAGNOSTIC}
                a = replace(
                    a,
                    classes=kept,
                    conditions=tuple(
                        c for c in a.conditions if c.disclosure_class in kept
                    ),
                )
                policy = replace(profile_value.policy, admissions=(a,))
                cfg = replace(
                    cfg,
                    remote_profile=replace(profile_value, policy=policy),
                    host=replace(cfg.host, disclosure=policy),
                )
            # Deliberately bypass startup policy validation to isolate the
            # independent invocation-time gate. Production fails even earlier.
            monkeypatch.setattr(RemoteProfile, "validate", lambda self, now: None)
            prepared = prepare_run(
                cfg,
                WorkspaceGuard(),
                confirm_context=lambda inventory: True,
                approve=approve,
                sandbox=FakeSandbox(
                    (0, 0, 1) if fault == "rework_diagnostics" else (0, 0, 0)
                ),
                confirm_disclosure=lambda _: True,
            )
            result = asyncio.run(prepared.worker.run(task(), prepared.context))
            assert result.disposition is TaskDisposition.FAILED
            assert server.requests == 1


def test_invalid_json_keeps_existing_failure_contract(tmp_path: Path) -> None:
    with TlsServer(
        expected=CANARY, responses={"/v1/chat/completions": body("not JSON")}
    ) as server:
        with configured(tmp_path, server) as (cfg, _):
            result, log, checks = execute(cfg)
            assert result.failure is TaskFailure.PROPOSAL_INVALID
            assert server.requests == 1 and checks.calls == 0 and log == ["disclosure"]


def test_cli_no_secret_flags_or_platform_bindings() -> None:
    _, args = _parse(
        [
            "run",
            "--repo",
            ".",
            "--task",
            "x",
            "--target",
            "src/a.py",
            "--binding",
            BINDING,
            "--remote-profile",
            "policy.toml",
            "--remote-custody",
            "custody",
        ]
    )
    assert args.check_profile == "generic" and args.binding == BINDING
    with pytest.raises(SystemExit):
        _parse(
            [
                "run",
                "--repo",
                ".",
                "--task",
                "x",
                "--target",
                "src/a.py",
                "--api-key",
                CANARY,
            ]
        )


@pytest.mark.parametrize("binding", ["ollama", BINDING])
@pytest.mark.parametrize("checks", ["generic", "project"])
def test_model_and_check_options_are_independent(binding: str, checks: str) -> None:
    _, args = _parse(
        [
            "run",
            "--repo",
            ".",
            "--task",
            "x",
            "--target",
            "src/a.py",
            "--binding",
            binding,
            "--check-profile",
            checks,
        ]
    )
    assert args.binding == binding and args.check_profile == checks


def policy_text(port: int) -> str:
    now = datetime.now(UTC)
    return f"""provider = "remote-endpoint"
base_url = "https://localhost:{port}/v1"
model = "model-a"
repository = "repo-a"
revision = "r1"
basis = "operator_attested"
processor = "Synthetic local TLS fixture"
locations = ["DE"]
retention_days = 0
training = "no"
human_access = "none"
subprocessors = ["Synthetic fixture only"]
not_before = {(now - timedelta(seconds=1)).isoformat()}
not_after = {(now + timedelta(minutes=30)).isoformat()}
"""


@pytest.mark.parametrize("fault", ["secret", "http", "oversize", "unknown_facts"])
def test_profile_rejects_unsafe_inputs(tmp_path: Path, fault: str) -> None:
    text = policy_text(443)
    if fault == "secret":
        text += f'api_key = "{CANARY}"\n'
    elif fault == "http":
        text = text.replace("https:", "http:")
    elif fault == "oversize":
        text += "#" * 16_385
    else:
        text = text.replace('training = "no"', 'training = "unknown"')
    path = tmp_path / "policy.toml"
    path.write_text(text, encoding="utf-8")
    with pytest.raises(ValueError) as error:
        load_profile(path)
    assert CANARY not in str(error.value)


def test_cli_decline_and_secret_canary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    root = repository(tmp_path)
    custody = tmp_path / "custody"
    custody.mkdir()
    with TlsServer(expected=CANARY) as server:
        path = tmp_path / "remote.toml"
        path.write_text(policy_text(server.port))

        # Provisioning remains the public S1 source; only its input seam is patched.
        def synthetic(
            source: _ProvisionedSecretSource, identity: str, purpose: str, consumer: str
        ) -> SecretRef:
            return _provision_interactively(
                source,
                identity,
                purpose,
                consumer,
                read=lambda _: CANARY,
                interactive=lambda: True,
            )

        monkeypatch.setattr("legoai.runtime.local._provision_interactively", synthetic)
        # Real host uses system trust at open; no TLS occurs after decline.
        outputs: list[str] = []
        prompts: list[str] = []

        def decline(prompt: str) -> str:
            if prompt.startswith("Confirm"):
                return "yes"
            prompts.append(prompt)
            return "no"

        code = main(
            [
                "run",
                "--repo",
                str(root),
                "--task",
                task().objective,
                "--target",
                "src/inventory/stock.py",
                "--binding",
                BINDING,
                "--remote-profile",
                str(path),
                "--remote-custody",
                str(custody),
            ],
            ask=decline,
            out=outputs.append,
            ready=lambda _: None,
        )
        assert code == 2 and len(prompts) == 1 and "Send" in prompts[0]
        assert server.connections == 0
        assert CANARY not in repr(outputs) + capsys.readouterr().out


@pytest.mark.skipif(
    os.environ.get("LEGOAI_QUALIFY_FORGEAI_REMOTE") != "1",
    reason="explicit real Docker qualification",
)
@pytest.mark.parametrize("project", [False, True])
def test_real_docker_remote_profile_independence(tmp_path: Path, project: bool) -> None:
    from forgeai_support import git_executable
    from legoai_engineering.coding.values import CodingTarget
    from legoai_engineering.repository.mutation import FileChangeKind

    from demo import git

    docker, uv = shutil.which("docker"), shutil.which("uv")
    assert docker and uv
    root = repository(tmp_path)
    request = task()
    output = proposal()
    if project:
        fixture = ROOT / "examples/forgeai/fixtures/project_checks"
        shutil.copytree(fixture, root, dirs_exist_ok=True)
        git(root, git_executable(), "add", ".")
        git(
            root,
            git_executable(),
            "-c",
            "user.name=Fixture",
            "-c",
            "user.email=fixture@example.invalid",
            "commit",
            "-m",
            "locked dependency fixture",
        )
        path = "src/domain_name.py"
        request = TaskRequest(
            "Add a docstring to ascii_hostname without changing behavior.",
            (CodingTarget(RepositoryPath(path), FileChangeKind.UPDATE),),
        )
        output = proposal(
            changes=[
                {
                    "path": path,
                    "operation": "update",
                    "content": (root / path)
                    .read_text()
                    .replace(
                        "    return idna",
                        '    """Return the IDNA ASCII representation."""\n    return idna',
                    ),
                    "reason": "Document the public function.",
                }
            ]
        )
    with TlsServer(expected=CANARY) as server:

        def respond() -> None:
            review = json.loads(REVIEW_ACCEPT)
            if project:
                review["summary"] = (
                    "The hostname function is documented and checks passed."
                )
                review["findings"] = []
            server.responses["/v1/chat/completions"] = body(
                output if server.requests == 1 else json.dumps(review)
            )

        server.on_request = respond
        with configured(tmp_path, server, root=root, request=request) as (cfg, _):
            cfg = replace(
                cfg,
                docker_executable=Path(docker),
                uv_executable=Path(uv),
                check_profile=CheckProfile.PROJECT if project else CheckProfile.GENERIC,
            )
            events: list[str] = []

            def confirm(text: str) -> bool:
                events.append("disclosure")
                assert server.requests == 0
                return True

            prepared = prepare_run(
                cfg,
                WorkspaceGuard(),
                confirm_context=lambda inventory: True,
                approve=approve,
                confirm_disclosure=confirm,
                preflight=events.append,
            )
            result = asyncio.run(prepared.worker.run(request, prepared.context))
            assert result.disposition is TaskDisposition.SUCCEEDED, result
            assert server.requests == 2
            if project:
                assert events.index(
                    "checks: Ruff, mypy, pytest; check network: disabled"
                ) < events.index("disclosure")
