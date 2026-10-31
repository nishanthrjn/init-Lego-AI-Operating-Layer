"""Attended remote roles: synthetic TLS, public hosts, no live provider."""

import asyncio
import json
import os
import shutil
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from forgeai_support import (
    REVIEW_ACCEPT,
    REVIEW_CHANGES,
    REWORK,
    FakeSandbox,
    approve,
    config,
    git_executable,
    proposal,
    replay,
    repository,
    snapshot,
    task,
)
from legoai.governance.disclosure import RepositoryIdentity
from legoai.governance.secret import SecretRef
from legoai.reference.secret import _ProvisionedSecretSource
from legoai.runtime._composition.secret import _provision_interactively
from legoai.runtime.api import CredentialSource
from legoai_engineering.repository.workspace import RepositoryPath
from test_batch import inputs
from test_line_endings import fixture
from test_noop_rework import identical_proposal
from test_remote_profile import CANARY, body, policy_text, profile
from test_test_strength import rework
from tls_server import TEST_CA, TlsServer

from batch import load_policy, load_tasks
from demo import git
from forgeai import cli, composition
from forgeai.composition import ForgeAIConfig, prepare_run, remote_role_session
from forgeai.domain import TaskDisposition, TaskFailure, TaskRequest
from forgeai.domain import TestStrength as StrengthOutcome
from forgeai.guard import WorkspaceGuard
from forgeai.remote import BINDING, RemoteProfile, role_disclosure_preview
from forgeai.report import ModelBindingKind, encode_report, run_report
from forgeai.roles import RoleModel, RoleModels, parse_models


def role_profile(port: int, name: str, now: datetime) -> RemoteProfile:
    value = profile(port, now)
    return replace(
        value,
        model=name,
        policy=replace(
            value.policy,
            admissions=tuple(
                replace(a, models=frozenset({name})) for a in value.policy.admissions
            ),
        ),
    )


def setup(
    tmp_path: Path,
    server: TlsServer,
    modes: tuple[bool, bool] = (True, True),
    request: TaskRequest | None = None,
    root: Path | None = None,
) -> tuple[ForgeAIConfig, RoleModels, tuple[tuple[str, RemoteProfile], ...]]:
    request = request or task()
    base = config(
        root or repository(tmp_path),
        replay(),
        context=tuple(p.value for p in request.context),
    )
    roles: list[RoleModel] = []
    profiles: list[tuple[str, RemoteProfile]] = []
    for name, remote in zip(("coder", "reviewer"), modes, strict=True):
        if remote:
            value = role_profile(server.port, name, datetime.now(UTC))
            custody = tmp_path / (name + "-custody")
            custody.mkdir()
            roles.append(
                RoleModel(
                    BINDING,
                    name,
                    profile=name + ".toml",
                    custody=str(custody),
                    provider=value.provider.value,
                )
            )
            profiles.append((name, value))
        else:
            roles.append(RoleModel("replay", "replay", replay=(name + ".json",)))
    if modes[0]:
        base = replace(
            base,
            host=replace(base.host, bindings=(profiles[0][1].binding(),)),
            model_selection={
                "revision": base.host.configuration.revision,
                "binding": BINDING,
            },
        )
    return base, RoleModels("roles-r1", roles[0], roles[1]), tuple(profiles)


@contextmanager
def session(
    base: ForgeAIConfig,
    roles: RoleModels,
    profiles: tuple[tuple[str, RemoteProfile], ...],
    events: list[str],
    *,
    request: TaskRequest | None = None,
    fail_reviewer: bool = False,
) -> Iterator[ForgeAIConfig]:
    def provision(
        source: _ProvisionedSecretSource, identity: str, purpose: str, consumer: str
    ) -> SecretRef:
        events.append("provision:" + identity)
        if fail_reviewer and identity == "forgeai-reviewer":
            raise ValueError(CANARY)
        return _provision_interactively(
            source,
            identity,
            purpose,
            consumer,
            read=lambda _: CANARY,
            interactive=lambda: True,
        )

    reviewer = dict(profiles).get("reviewer")
    binding = (
        reviewer.binding()
        if reviewer
        else cli.replay_binding(cli.ReplayModel(REVIEW_ACCEPT))
    )
    with (
        patch("legoai.runtime.local._provision_interactively", provision),
        remote_role_session(
            base,
            roles,
            binding,
            request or task(),
            profiles,
            now=datetime.now(UTC),
            label=lambda name, value: cli.role_credential_label(
                name, value, events.append
            ),
            trust_anchor=TEST_CA,
        ) as configured,
    ):
        yield configured


def respond(server: TlsServer, outputs: list[str]) -> None:
    def reply() -> None:
        model = json.loads(server.bodies[-1])["model"]
        result = json.loads(body(outputs[server.requests - 1]))
        result["model"] = model
        server.responses["/v1/chat/completions"] = json.dumps(result).encode()

    server.on_request = reply


@pytest.mark.parametrize("modes", [(True, True), (True, False), (False, True)])
def test_remote_and_mixed_roles_route_and_disclose(
    tmp_path: Path, modes: tuple[bool, bool]
) -> None:
    with TlsServer(expected=CANARY) as server:
        outputs = [
            value
            for value, remote in zip((proposal(), REVIEW_ACCEPT), modes, strict=True)
            if remote
        ]
        respond(server, outputs)
        base, roles, profiles = setup(tmp_path, server, modes)
        events: list[str] = []
        previews: list[str] = []
        with session(base, roles, profiles, events) as cfg:

            def confirm(text: str) -> bool:
                assert server.requests == 0
                previews.append(text)
                return True

            prepared = prepare_run(
                cfg,
                WorkspaceGuard(),
                approve=approve,
                sandbox=FakeSandbox(),
                confirm_context=lambda _: True,
                confirm_disclosure=confirm,
            )
            result = asyncio.run(prepared.worker.run(task(), prepared.context))
            assert result.disposition is TaskDisposition.SUCCEEDED
            expected = [
                name
                for name, remote in zip(("coder", "reviewer"), modes, strict=True)
                if remote
            ]
            assert [json.loads(b)["model"] for b in server.bodies] == expected
            assert all(server.authorized) and len(previews) == sum(modes)
            assert cfg.host.max_executions == 2
            assert cfg.reviewer_host is not None
            assert cfg.reviewer_host.max_executions == 2
            if len(cfg.remote_roles) == 2:
                assert cfg.remote_roles[0].source is not cfg.remote_roles[1].source
            assert events == [
                value
                for name in expected
                for value in (
                    f"Credential for {name} (provider remote-endpoint, model {name})",
                    "provision:forgeai-" + name,
                )
            ]
            encoded = encode_report(
                run_report(result, ModelBindingKind.REPLAY, cfg.roles)
            )
            assert CANARY not in encoded + repr(result) + "\n".join(events)
            assert str(tmp_path) not in encoded and "https://" not in encoded
            for name in expected:
                recorded = json.loads(encoded)["roles"][name]
                assert recorded["provider"] == "remote-endpoint"
                assert recorded["model_quality"] == "UNQUALIFIED"


@pytest.mark.parametrize("decline", [0, 1])
@pytest.mark.parametrize("answer", ["no", "", "EOF", "interrupt"])
def test_disclosure_refusal_prevents_every_call_and_effect(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, decline: int, answer: str
) -> None:
    with TlsServer(expected=CANARY) as server:
        base, roles, profiles = setup(tmp_path, server)
        before = snapshot(base.repository)
        events: list[str] = []
        calls = 0
        probe = composition.remote_credentials(base)
        source_type = type(probe)
        original_close = source_type.close
        probe.close()
        closed: list[CredentialSource] = []

        def close(self: CredentialSource) -> None:
            closed.append(self)
            original_close(self)

        monkeypatch.setattr(source_type, "close", close)

        def ask(_: str) -> str:
            nonlocal calls
            current = calls
            calls += 1
            if current != decline:
                return "yes"
            if answer == "EOF":
                raise EOFError
            if answer == "interrupt":
                raise KeyboardInterrupt
            return answer

        with session(base, roles, profiles, events) as cfg:
            checks = FakeSandbox()
            prepared = prepare_run(
                cfg,
                WorkspaceGuard(),
                approve=approve,
                sandbox=checks,
                confirm_context=lambda _: True,
                confirm_disclosure=cli.remote_confirmer(ask, events.append),
            )
            result = asyncio.run(prepared.worker.run(task(), prepared.context))
            assert result.failure is TaskFailure.MODEL_DISCLOSURE_REFUSED
            assert server.connections == server.requests == checks.calls == 0
            assert snapshot(base.repository) == before
            assert not result.evidence.attempts
            assert calls == decline + 1
        assert len(closed) == 2 and closed[0] is not closed[1]


@pytest.mark.parametrize(
    "fault", ["shared", "nested", "inside", "missing", "identity", "expired"]
)
def test_all_profiles_validated_before_provision(tmp_path: Path, fault: str) -> None:
    with TlsServer() as server:
        base, roles, profiles = setup(tmp_path, server)
        if fault in {"shared", "nested", "inside", "missing"}:
            custody = Path(roles.coder.custody)
            if fault == "nested":
                custody = custody / "nested"
                custody.mkdir()
            elif fault == "inside":
                custody = base.repository
            elif fault == "missing":
                custody = tmp_path / "absent"
            roles = replace(
                roles, reviewer=replace(roles.reviewer, custody=str(custody))
            )
        else:
            reviewer = profiles[1][1]
            if fault == "identity":
                reviewer = replace(reviewer, repository=RepositoryIdentity("other"))
            else:
                reviewer = replace(
                    reviewer,
                    policy=replace(
                        reviewer.policy,
                        admissions=tuple(
                            replace(
                                a,
                                not_before=a.not_before - timedelta(hours=2),
                                not_after=a.not_after - timedelta(hours=2),
                            )
                            for a in reviewer.policy.admissions
                        ),
                    ),
                )
            profiles = (profiles[0], ("reviewer", reviewer))
        events: list[str] = []
        with pytest.raises(ValueError), session(base, roles, profiles, events):
            pytest.fail("invalid configuration entered")
        assert events == [] and server.connections == 0


def test_partial_provision_failure_closes_both_sources(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    with TlsServer() as server:
        base, roles, profiles = setup(tmp_path, server)
        probe = composition.remote_credentials(base)
        source_type = type(probe)
        original_close = source_type.close
        probe.close()
        closed: list[CredentialSource] = []

        def close(self: CredentialSource) -> None:
            closed.append(self)
            original_close(self)

        monkeypatch.setattr(source_type, "close", close)
        events: list[str] = []
        with (
            pytest.raises(ValueError),
            session(base, roles, profiles, events, fail_reviewer=True),
        ):
            pytest.fail("failed provisioning cannot yield a configuration")
        assert len(closed) == 2 and closed[0] is not closed[1]
        assert events[-1] == "provision:forgeai-reviewer"
        assert server.connections == 0


@pytest.mark.parametrize("fault", ["associations", "runtime", "custody", "policy"])
def test_cross_wiring_refused(tmp_path: Path, fault: str) -> None:
    with TlsServer() as server:
        base, roles, profiles = setup(tmp_path, server)
        with session(base, roles, profiles, []) as cfg:
            left, right = cfg.remote_roles
            with pytest.raises(ValueError):
                if fault == "associations":
                    replace(cfg, remote_roles=(right, left))
                elif fault == "runtime":
                    replace(left, runtime=right.runtime)
                elif fault == "custody":
                    changed = replace(
                        left,
                        runtime=replace(left.runtime, custody=right.runtime.custody),
                    )
                    replace(cfg, remote_roles=(changed, right))
                else:
                    replace(
                        cfg, host=replace(cfg.host, disclosure=right.profile.policy)
                    )
            assert server.connections == 0


def test_reviewer_preview_excludes_coder_context(tmp_path: Path) -> None:
    request = replace(task(), context=(RepositoryPath("docs/private.md"),))
    value = role_profile(8443, "coder", datetime.now(UTC))
    assert "docs/private.md" in role_disclosure_preview("coder", value, request)
    assert "docs/private.md" not in role_disclosure_preview("reviewer", value, request)


@pytest.mark.parametrize("trigger", ["check", "review"])
def test_remote_rework_uses_own_hosts_with_bounded_calls(
    tmp_path: Path, trigger: str
) -> None:
    with TlsServer(expected=CANARY) as server:
        outputs = (
            [proposal(), REWORK, REVIEW_ACCEPT]
            if trigger == "check"
            else [proposal(), REVIEW_CHANGES, REWORK, REVIEW_ACCEPT]
        )
        respond(server, outputs)
        base, roles, profiles = setup(tmp_path, server)
        with session(base, roles, profiles, []) as cfg:
            checks = FakeSandbox(
                (1, 0, 0, 0, 0, 0) if trigger == "check" else (0, 0, 0, 0, 0, 0)
            )
            prepared = prepare_run(
                cfg,
                WorkspaceGuard(),
                approve=approve,
                sandbox=checks,
                confirm_context=lambda _: True,
                confirm_disclosure=lambda _: True,
            )
            result = asyncio.run(prepared.worker.run(task(), prepared.context))
            assert result.disposition is TaskDisposition.SUCCEEDED
            assert checks.calls == 6 and server.requests == len(outputs) <= 4
            assert [json.loads(b)["model"] for b in server.bodies] == (
                ["coder", "coder", "reviewer"]
                if trigger == "check"
                else ["coder", "reviewer", "coder", "reviewer"]
            )


def test_remote_role_schema_closed() -> None:
    for entry in (
        {"binding": BINDING, "profile": "p"},
        {"binding": BINDING, "profile": "p", "custody": "c", "credential": CANARY},
    ):
        with pytest.raises(ValueError):
            parse_models(
                {
                    "schema": "forgeai-models/1",
                    "revision": "r1",
                    "roles": {"coder": entry, "reviewer": entry},
                }
            )


def test_cli_label_escapes_bidi_and_never_prints_location() -> None:
    value = profile(8443, datetime.now(UTC))
    # Defensive rendering even if a caller circumvents profile validation.
    object.__setattr__(value, "model", "model\u202eunsafe")
    output: list[str] = []
    cli.role_credential_label("coder", value, output.append)
    assert output == [
        "Credential for coder (provider remote-endpoint, model model\\u202eunsafe)"
    ]


@pytest.mark.parametrize("ending", ["\n", "\r\n"])
def test_remote_noop_after_line_matching(tmp_path: Path, ending: str) -> None:
    root = fixture(tmp_path, ending)
    with TlsServer(expected=CANARY) as server:
        respond(server, [identical_proposal(root, lf=True)])
        base, roles, profiles = setup(tmp_path, server, root=root)
        before = snapshot(root)
        with session(base, roles, profiles, []) as cfg:
            checks = FakeSandbox()

            def forbidden(_: Any) -> Any:
                pytest.fail("no-op must not request mutation approval")

            prepared = prepare_run(
                cfg,
                WorkspaceGuard(),
                approve=forbidden,
                sandbox=checks,
                confirm_context=lambda _: True,
                confirm_disclosure=lambda _: True,
            )
            result = asyncio.run(prepared.worker.run(task(), prepared.context))
            assert result.failure is TaskFailure.PROPOSAL_NO_CHANGE
            assert server.requests == 1 and checks.calls == 0
            assert snapshot(root) == before


def test_remote_strength_overlay_preserves_budgets(tmp_path: Path) -> None:
    with TlsServer(expected=CANARY) as server:
        respond(server, [proposal(), rework(proposal()), REVIEW_ACCEPT])
        base, roles, profiles = setup(tmp_path, server)
        base = replace(base, test_strength=True)
        with session(base, roles, profiles, []) as cfg:
            checks = FakeSandbox((0, 0, 0, 0, 0, 0, 0, 1))
            prepared = prepare_run(
                cfg,
                WorkspaceGuard(),
                approve=approve,
                sandbox=checks,
                confirm_context=lambda _: True,
                confirm_disclosure=lambda _: True,
            )
            result = asyncio.run(prepared.worker.run(task(), prepared.context))
            assert result.disposition is TaskDisposition.SUCCEEDED
            assert checks.calls == 8 and server.requests == 3
            assert [item.test_strength for item in result.evidence.attempts] == [
                StrengthOutcome.NOT_DISCRIMINATING,
                StrengthOutcome.DISCRIMINATING,
            ]


def test_expired_reviewer_keeps_coder_changes(tmp_path: Path) -> None:
    with TlsServer(expected=CANARY) as server:
        respond(server, [proposal()])
        base, roles, profiles = setup(tmp_path, server)
        with session(base, roles, profiles, []) as cfg:
            now = datetime.now(UTC)
            checks = FakeSandbox()

            def expire(review: Any) -> Any:
                nonlocal now
                now += timedelta(minutes=31)
                return approve(review)

            prepared = prepare_run(
                cfg,
                WorkspaceGuard(),
                approve=expire,
                sandbox=checks,
                confirm_context=lambda _: True,
                confirm_disclosure=lambda _: True,
                clock=lambda: now,
            )
            result = asyncio.run(prepared.worker.run(task(), prepared.context))
            assert result.disposition is TaskDisposition.FAILED
            assert result.failure is TaskFailure.REVIEW_FAILED
            assert server.requests == 1 and checks.calls == 3
            assert result.evidence.attempts[0].applied is not None
            assert "remain" in cli.summarize(result).lower()


def test_changed_task_invalidates_disclosure_binding(tmp_path: Path) -> None:
    with TlsServer() as server:
        base, roles, profiles = setup(tmp_path, server)
        events: list[str] = []
        with session(base, roles, profiles, events) as cfg:
            prepared = prepare_run(
                cfg,
                WorkspaceGuard(),
                approve=approve,
                sandbox=FakeSandbox(),
                confirm_context=lambda _: True,
                confirm_disclosure=lambda _: pytest.fail(
                    "changed task cannot be approved"
                ),
            )
            result = asyncio.run(
                prepared.worker.run(
                    replace(task(), objective="a different task"), prepared.context
                )
            )
            assert result.failure is TaskFailure.MODEL_DISCLOSURE_REFUSED
            assert server.connections == 0


@pytest.mark.parametrize("failure", [False, True])
def test_cli_label_order_cleanup_and_suppressed_provision_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: bool
) -> None:
    with TlsServer() as server:
        base, roles, profiles = setup(tmp_path, server)
        values = dict(profiles)
        events: list[str] = []
        sources: list[CredentialSource] = []
        closed: list[CredentialSource] = []
        original_source = composition.remote_credentials
        probe = original_source(base)
        source_type = type(probe)
        original_close = source_type.close
        probe.close()

        def source(cfg: ForgeAIConfig) -> CredentialSource:
            result = original_source(cfg)
            sources.append(result)
            return result

        def close(self: CredentialSource) -> None:
            closed.append(self)
            original_close(self)

        def provision(
            source: _ProvisionedSecretSource, identity: str, purpose: str, consumer: str
        ) -> SecretRef:
            events.append("provision:" + identity)
            if failure and identity == "forgeai-reviewer":
                raise RuntimeError(CANARY)
            return _provision_interactively(
                source,
                identity,
                purpose,
                consumer,
                read=lambda _: CANARY,
                interactive=lambda: True,
            )

        monkeypatch.setattr(
            cli,
            "load_models",
            lambda _: (roles, values["coder"].binding(), values["reviewer"].binding()),
        )
        monkeypatch.setattr(cli, "load_profile", lambda path: values[path.stem])
        monkeypatch.setattr(composition, "remote_credentials", source)
        monkeypatch.setattr(source_type, "close", close)
        monkeypatch.setattr(cli, "_execute", lambda *args, **kwargs: 0)
        with patch("legoai.runtime.local._provision_interactively", provision):
            result = cli.main(
                [
                    "run",
                    "--repo",
                    str(base.repository),
                    "--task",
                    "test",
                    "--target",
                    "src/inventory/stock.py",
                    "--models",
                    "models.toml",
                    "--git",
                    str(base.git_executable),
                    "--docker",
                    str(base.docker_executable),
                ],
                out=events.append,
            )
        assert result == (2 if failure else 0)
        assert events[:4] == [
            "Credential for coder (provider remote-endpoint, model coder)",
            "provision:forgeai-coder",
            "Credential for reviewer (provider remote-endpoint, model reviewer)",
            "provision:forgeai-reviewer",
        ]
        assert closed == list(reversed(sources)) and len(sources) == 2
        assert CANARY not in "\n".join(events)
        assert server.connections == 0


@pytest.mark.skipif(
    os.environ.get("LEGOAI_QUALIFY_REMOTE_ROLES") != "1",
    reason="explicit real-Docker synthetic TLS qualification only",
)
def test_real_docker_remote_roles(tmp_path: Path) -> None:
    docker = shutil.which("docker")
    assert docker, "qualified Docker checks image and Linux engine required"
    with TlsServer(expected=CANARY) as server:
        respond(server, [proposal(), REVIEW_ACCEPT])
        base, roles, profiles = setup(tmp_path, server)
        base = replace(base, docker_executable=Path(docker))
        with session(base, roles, profiles, []) as cfg:
            prepared = prepare_run(
                cfg,
                WorkspaceGuard(),
                approve=approve,
                confirm_context=lambda _: True,
                confirm_disclosure=lambda _: True,
            )
            result = asyncio.run(prepared.worker.run(task(), prepared.context))
            assert result.disposition is TaskDisposition.SUCCEEDED
            assert server.requests == 2 and all(server.authorized)


def test_remote_model_file_resolves_paths_and_refuses_guidance(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "coder.json").write_text(proposal(), encoding="utf-8")
    (tmp_path / "remote.toml").write_text(policy_text(443), encoding="utf-8")
    path = tmp_path / "models.toml"
    path.write_text(
        'schema = "forgeai-models/1"\nrevision = "r1"\n'
        '[roles.coder]\nbinding = "replay"\nreplay = ["coder.json"]\n'
        '[roles.reviewer]\nbinding = "openai-compatible-remote"\n'
        'profile = "remote.toml"\ncustody = "custody"\n',
        encoding="utf-8",
    )
    roles, _, reviewer = cli.load_models(path)
    assert roles.reviewer.profile == str((tmp_path / "remote.toml").resolve())
    assert roles.reviewer.custody == str((tmp_path / "custody").resolve())
    assert reviewer.binding_id == BINDING

    def forbidden(*args: Any, **kwargs: Any) -> Any:
        pytest.fail("guidance refusal must precede sources and hosts")

    monkeypatch.setattr(composition, "remote_credentials", forbidden)
    monkeypatch.setattr(composition, "open_local_host", forbidden)
    output: list[str] = []
    with pytest.raises(SystemExit):
        cli.main(
            [
                "run",
                "--repo",
                str(tmp_path),
                "--task",
                "x",
                "--target",
                "src/a.py",
                "--models",
                str(path),
                "--discover-guidance",
            ],
            out=output.append,
        )
    assert output == []


def test_batch_still_refuses_remote_before_credentials(tmp_path: Path) -> None:
    tasks, policy = inputs(tmp_path)
    tasks.write_text(
        tasks.read_text(encoding="utf-8").replace(
            'binding = "replay"', f'binding = "{BINDING}"'
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="REMOTE excluded"):
        load_tasks(tasks, load_policy(policy))


def test_remote_reviewer_never_receives_coder_context(tmp_path: Path) -> None:
    root = repository(tmp_path)
    context = root / "private-context.txt"
    context.write_text("CODER_ONLY_CONTEXT_92841", encoding="utf-8")
    git(root, git_executable(), "add", "private-context.txt")
    git(
        root,
        git_executable(),
        "-c",
        "user.name=Fixture",
        "-c",
        "user.email=fixture@example.invalid",
        "commit",
        "--no-gpg-sign",
        "-m",
        "read-only context fixture",
    )
    request = replace(task(), context=(RepositoryPath("private-context.txt"),))
    with TlsServer(expected=CANARY) as server:
        respond(server, [proposal(), REVIEW_ACCEPT])
        base, roles, profiles = setup(tmp_path, server, request=request, root=root)
        with session(base, roles, profiles, [], request=request) as cfg:
            prepared = prepare_run(
                cfg,
                WorkspaceGuard(),
                approve=approve,
                sandbox=FakeSandbox(),
                confirm_context=lambda _: True,
                confirm_disclosure=lambda _: True,
            )
            result = asyncio.run(prepared.worker.run(request, prepared.context))
            assert result.disposition is TaskDisposition.SUCCEEDED
            assert b"CODER_ONLY_CONTEXT_92841" in server.bodies[0]
            assert b"CODER_ONLY_CONTEXT_92841" not in server.bodies[1]
            assert b"private-context.txt" not in server.bodies[1]


def test_remote_stale_mutation_approval_is_refused(tmp_path: Path) -> None:
    with TlsServer(expected=CANARY) as server:
        respond(server, [proposal(), REVIEW_CHANGES, REWORK])
        base, roles, profiles = setup(tmp_path, server)
        approvals: list[Any] = []

        def stale(review: Any) -> Any:
            approvals.append(review)
            return approve(approvals[0])

        with session(base, roles, profiles, []) as cfg:
            checks = FakeSandbox()
            prepared = prepare_run(
                cfg,
                WorkspaceGuard(),
                approve=stale,
                sandbox=checks,
                confirm_context=lambda _: True,
                confirm_disclosure=lambda _: True,
            )
            result = asyncio.run(prepared.worker.run(task(), prepared.context))
            assert result.failure is TaskFailure.PROPOSAL_DECLINED
            assert len(approvals) == 2 and checks.calls == 3 and server.requests == 3
            for change in approvals[0].proposal.changeset.changes:
                assert (
                    cfg.repository / change.path.value
                ).read_bytes() == change.text.encode("utf-8")
