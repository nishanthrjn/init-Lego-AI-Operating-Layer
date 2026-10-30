"""ADR-029 local role boundaries, using public hosts and replay models only."""

import asyncio
import json
import os
import shutil
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
from forgeai_support import (
    REVIEW_ACCEPT,
    REVIEW_CHANGES,
    REWORK,
    FakeSandbox,
    LoggedReplay,
    SpyReader,
    approve,
    config,
    git_executable,
    proposal,
    repository,
    snapshot,
    task,
)
from legoai.execution.agent.ports import (
    AgentDefinition,
    AgentRequest,
    AgentResult,
    AgentRuntimePort,
)
from legoai.execution.values import ExecutionContext
from legoai.runtime.api import HostError, HostFailure, ModelPurpose
from legoai.runtime.local import open_local_host
from legoai_engineering.analyst.authorized import (
    REPOSITORY_READ_ACTION,
    AuthorizedRepositoryEvidence,
)
from legoai_engineering.analyst.values import EvidenceAcquisitionError
from legoai_engineering.authorization import (
    EffectAuthorizationError,
    EffectAuthorizationFailure,
)
from legoai_engineering.checks.authorized import (
    ENGINEERING_CHECK_ACTION,
    AuthorizedEngineeringChecks,
)
from legoai_engineering.checks.values import CheckKind, CheckRequest
from legoai_engineering.coding.authorized import AuthorizedCodingEvidence
from legoai_engineering.coding.definition import coding_definition
from legoai_engineering.repository.mutation import (
    FileChange,
    FileChangeKind,
    RepositoryChangeSet,
    digest_text,
)
from legoai_engineering.repository.mutation_authorized import (
    REPOSITORY_MUTATION_ACTION,
    AuthorizedRepositoryMutation,
)
from legoai_engineering.repository.workspace import RepositoryPath
from test_line_endings import fixture
from test_noop_rework import identical_proposal
from test_run_report import projected
from test_test_strength import CountedDocker, rework

from forgeai import cli, composition
from forgeai.composition import ForgeAIConfig, bind_roles, prepare_run, utc_now
from forgeai.domain import OperatorDecision, TaskDisposition, TaskFailure
from forgeai.domain import TestStrength as StrengthOutcome
from forgeai.guard import WorkspaceGuard
from forgeai.report import ModelBindingKind, encode_report, run_report
from forgeai.roles import RoleModel, RoleModels, parse_models


def role_config(
    root: Path,
    coder: cli.ReplayModel,
    reviewer: cli.ReplayModel,
) -> ForgeAIConfig:
    roles = RoleModels(
        "test-r1",
        RoleModel("replay", "replay", replay=("coder.json",)),
        RoleModel("replay", "replay", replay=("reviewer.json",)),
    )
    return bind_roles(
        config(root, coder), roles, cli.replay_binding(reviewer), now=utc_now()
    )


class RuntimeSpy:
    def __init__(self, inner: AgentRuntimePort, owner: HostSpy) -> None:
        self.inner = inner
        self.owner = owner
        self.requests: list[AgentRequest] = []

    async def run(
        self, definition: AgentDefinition, request: AgentRequest
    ) -> AgentResult:
        assert request.context in self.owner.minted
        self.requests.append(request)
        self.owner.order.append(self.owner.number)
        return await self.inner.run(definition, request)


class HostSpy:
    def __init__(self, inner: Any, number: int, order: list[int]) -> None:
        self.inner = inner
        self.number = number
        self.order = order
        self.minted: list[ExecutionContext] = []
        self.runtime = RuntimeSpy(inner.agent_runtime(), self)
        self.runtime_requests = 0

    def __getattr__(self, name: str) -> Any:
        return getattr(self.inner, name)

    def model_execution(self, *args: Any, **kwargs: Any) -> ExecutionContext:
        context: ExecutionContext = self.inner.model_execution(*args, **kwargs)
        self.minted.append(context)
        return context

    def agent_runtime(self) -> AgentRuntimePort:
        self.runtime_requests += 1
        return self.runtime


def observe_hosts(monkeypatch: pytest.MonkeyPatch) -> tuple[list[HostSpy], list[int]]:
    real = open_local_host
    hosts: list[HostSpy] = []
    order: list[int] = []

    def opened(*args: Any, **kwargs: Any) -> HostSpy:
        host = HostSpy(real(*args, **kwargs), len(hosts), order)
        hosts.append(host)
        return host

    monkeypatch.setattr(composition, "open_local_host", opened)
    return hosts, order


@pytest.mark.parametrize("trigger", ["none", "review", "checks", "strength"])
def test_role_runtimes_contexts_and_aggregate_budget(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, trigger: str
) -> None:
    root = fixture(tmp_path, "\r\n") if trigger == "none" else repository(tmp_path)
    coder = LoggedReplay(
        [], proposal(), rework(proposal()) if trigger == "strength" else REWORK
    )
    reviewer = LoggedReplay(
        [], REVIEW_CHANGES if trigger == "review" else REVIEW_ACCEPT, REVIEW_ACCEPT
    )
    cfg = replace(
        role_config(root, coder, reviewer), test_strength=trigger == "strength"
    )
    exits = (
        (1, 0, 0, 0, 0, 0)
        if trigger == "checks"
        else (0, 0, 0, 0, 0, 0, 0, 1)
        if trigger == "strength"
        else (0, 0, 0)
    )
    sandbox = FakeSandbox(exits)
    hosts, order = observe_hosts(monkeypatch)
    prepared = prepare_run(
        cfg,
        WorkspaceGuard(),
        approve=approve,
        confirm_context=lambda _: True,
        sandbox=sandbox,
    )
    reader = SpyReader(prepared.worker.reader)
    worker = replace(prepared.worker, reader=reader)
    result = asyncio.run(worker.run(task(), prepared.context))
    assert result.disposition is TaskDisposition.SUCCEEDED
    if trigger == "none":
        assert all(
            b"\r\n" in (root / path.value).read_bytes()
            for path in result.evidence.changed_paths
        )
    assert len(hosts) == 2
    assert [host.runtime_requests for host in hosts] == [1, 1]
    expected = (
        [0, 1]
        if trigger == "none"
        else [0, 1, 0, 1]
        if trigger == "review"
        else [0, 0, 1]
    )
    assert order == expected
    assert coder.calls + reviewer.calls == len(order) <= 4
    assert len(reader.requests) == reviewer.calls
    assert all(
        set(paths) <= set(result.evidence.changed_paths) for paths in reader.requests
    )
    assert sandbox.calls == (
        3 if trigger == "none" else 8 if trigger == "strength" else 6
    )
    if trigger == "strength":
        assert [item.test_strength for item in result.evidence.attempts] == [
            StrengthOutcome.NOT_DISCRIMINATING,
            StrengthOutcome.DISCRIMINATING,
        ]
    for host in hosts:
        for request in host.runtime.requests:
            assert request.context.correlation_id == prepared.context.correlation_id
        while len(host.minted) < 2:
            host.model_execution(ModelPurpose.CHAT)
        with pytest.raises(HostError) as error:
            host.model_execution(ModelPurpose.CHAT)
        assert error.value.failure is HostFailure.CAPACITY_EXHAUSTED
    assert len(hosts) == 2  # exhaustion never opens a replacement


def test_foreign_contexts_and_reviewer_authority(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = repository(tmp_path)
    coder = LoggedReplay([], proposal())
    reviewer = LoggedReplay([], REVIEW_ACCEPT)
    cfg = replace(
        role_config(root, coder, reviewer),
        context_paths=(RepositoryPath("pyproject.toml"),),
    )
    hosts, _ = observe_hosts(monkeypatch)
    sandbox = FakeSandbox()
    prepared = prepare_run(cfg, WorkspaceGuard(), approve=approve, sandbox=sandbox)
    review_context = prepared.worker.review_context(prepared.context)
    assert review_context.causation == prepared.context.operation
    assert isinstance(prepared.worker.reader, AuthorizedRepositoryEvidence)
    assert prepared.worker.reader.authorization is hosts[1].authorization
    coding_reads = prepared.worker.agent.evidence_reader
    assert isinstance(coding_reads, AuthorizedCodingEvidence)
    assert coding_reads.reads.authorization is hosts[0].authorization
    assert coding_reads.references is not None
    assert coding_reads.references.authorization is hosts[0].authorization
    assert RepositoryPath("pyproject.toml") not in prepared.worker.reader.allowed_paths

    async def exercise() -> None:
        for destination, foreign in (
            (hosts[1], prepared.context),
            (hosts[0], review_context),
        ):
            with pytest.raises(HostError) as error:
                await destination.inner.agent_runtime().run(
                    coding_definition(), AgentRequest(foreign, "synthetic")
                )
            assert error.value.failure is HostFailure.FOREIGN_CONTEXT
        with pytest.raises(EvidenceAcquisitionError):
            await prepared.worker.reader.acquire(
                (RepositoryPath("pyproject.toml"),), review_context.tenant_context
            )

    asyncio.run(exercise())
    assert coder.calls == reviewer.calls == 0
    assert cfg.reviewer_host is not None
    assert {g.action for g in cfg.host.grants} == {
        "invoke-capability",
        REPOSITORY_READ_ACTION,
        REPOSITORY_MUTATION_ACTION,
        ENGINEERING_CHECK_ACTION,
    }
    assert {g.action for g in cfg.reviewer_host.grants} == {
        "invoke-capability",
        REPOSITORY_READ_ACTION,
    }
    reference = replace(
        cfg.reviewer_host.configuration.configuration, instance="workspace"
    )
    for action in (REPOSITORY_MUTATION_ACTION, ENGINEERING_CHECK_ACTION):
        with pytest.raises(HostError) as error:
            hosts[1].security_context(reference, action, "workspace")
        assert error.value.failure is HostFailure.GRANT_NOT_CONFIGURED
    # Evaluate attempted effect actions using only the reviewer's read grant.
    # Transferring a coder SecurityContext would transfer its effect grant too;
    # evaluator identity is not an ownership boundary for supplied grants.
    assert isinstance(prepared.worker.mutation, AuthorizedRepositoryMutation)
    assert isinstance(prepared.worker.checks, AuthorizedEngineeringChecks)
    read_authority = hosts[1].security_context(
        reference, REPOSITORY_READ_ACTION, "workspace"
    )
    mutation = replace(
        prepared.worker.mutation,
        security_context=replace(read_authority, action=REPOSITORY_MUTATION_ACTION),
        authorization=hosts[1].authorization,
    )
    checks = replace(
        prepared.worker.checks,
        security_context=replace(read_authority, action=ENGINEERING_CHECK_ACTION),
        authorization=hosts[1].authorization,
    )
    target = task().targets[0].path
    before = snapshot(root)
    changes = RepositoryChangeSet(
        (
            FileChange(
                target,
                FileChangeKind.UPDATE,
                digest_text((root / target.value).read_bytes().decode("utf-8")),
                "changed\n",
            ),
        )
    )
    with pytest.raises(EffectAuthorizationError) as denied_mutation:
        mutation.apply(changes)
    assert denied_mutation.value.reason is EffectAuthorizationFailure.DENIED
    with pytest.raises(EffectAuthorizationError) as denied_check:
        checks.check(cfg.check_plan[0])
    assert denied_check.value.reason is EffectAuthorizationFailure.DENIED
    assert sandbox.calls == 0
    assert snapshot(root) == before


@pytest.mark.parametrize("ending", ["\n", "\r\n"])
def test_role_noop_and_crlf_stop_before_approval(tmp_path: Path, ending: str) -> None:
    root = fixture(tmp_path, ending)
    before = snapshot(root)
    coder = LoggedReplay([], identical_proposal(root, lf=True))
    reviewer = LoggedReplay([], REVIEW_ACCEPT)
    sandbox = FakeSandbox()

    def forbidden(_: Any) -> Any:
        pytest.fail("a no-op must not request approval")

    prepared = prepare_run(
        role_config(root, coder, reviewer),
        WorkspaceGuard(),
        approve=forbidden,
        confirm_context=lambda _: True,
        sandbox=sandbox,
    )
    result = asyncio.run(prepared.worker.run(task(), prepared.context))
    assert result.failure is TaskFailure.PROPOSAL_NO_CHANGE
    assert snapshot(root) == before
    assert coder.calls == 1 and reviewer.calls == sandbox.calls == 0


def test_role_approval_identity_and_retained_changes(tmp_path: Path) -> None:
    root = repository(tmp_path)
    coder = LoggedReplay([], proposal(), REWORK)
    reviewer = LoggedReplay([], REVIEW_CHANGES, REVIEW_ACCEPT)
    approvals: list[Any] = []

    def stale(value: Any) -> OperatorDecision:
        approvals.append(value)
        return OperatorDecision.approve(approvals[0])

    sandbox = FakeSandbox()
    prepared = prepare_run(
        role_config(root, coder, reviewer),
        WorkspaceGuard(),
        approve=stale,
        confirm_context=lambda _: True,
        sandbox=sandbox,
    )
    result = asyncio.run(prepared.worker.run(task(), prepared.context))
    assert result.failure is TaskFailure.PROPOSAL_DECLINED
    assert len(approvals) == 2 and sandbox.calls == 3
    assert coder.calls == 2 and reviewer.calls == 1
    for change in approvals[0].proposal.changeset.changes:
        assert (root / change.path.value).read_bytes() == change.text.encode("utf-8")
    assert "WARNING: changes remain" in cli.summarize(result)


def models_file(tmp_path: Path) -> Path:
    (tmp_path / "coder.json").write_text(proposal(), encoding="utf-8")
    (tmp_path / "reviewer.json").write_text(REVIEW_ACCEPT, encoding="utf-8")
    path = tmp_path / "models.toml"
    path.write_text(
        'schema = "forgeai-models/1"\nrevision = "r1"\n'
        '[roles.coder]\nbinding = "replay"\nreplay = ["coder.json"]\n'
        '[roles.reviewer]\nbinding = "replay"\nreplay = ["reviewer.json"]\n',
        encoding="utf-8",
    )
    return path


@pytest.mark.parametrize(
    "invalid",
    [
        "missing",
        "unknown",
        "unknown-role",
        "remote",
        "no-files",
        "oversize",
        "duplicate",
        "duplicate-file",
        "empty",
        "url",
    ],
)
def test_bad_config_precedes_host_creation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, invalid: str
) -> None:
    path = models_file(tmp_path)
    text = path.read_text(encoding="utf-8")
    if invalid == "missing":
        text = text.split("[roles.reviewer]")[0]
    elif invalid == "unknown":
        text += 'unknown = "x"\n'
    elif invalid == "unknown-role":
        text = text.replace("roles.reviewer", "roles.other")
    elif invalid == "remote":
        text = text.replace('binding = "replay"', 'binding = "remote"')
    elif invalid == "no-files":
        text = text.replace('["coder.json"]', "[]")
    elif invalid == "oversize":
        text += "#" * 16_385
    elif invalid == "duplicate":
        text += 'binding = "replay"\n'
    elif invalid == "duplicate-file":
        text = text.replace('["coder.json"]', '["coder.json", "coder.json"]')
    elif invalid == "empty":
        text = text.replace('revision = "r1"', 'revision = ""')
    else:
        text = text.replace(
            'binding = "replay"\nreplay = ["coder.json"]',
            'binding = "ollama"\nollama_model = "model"\nollama_url = "https://remote.invalid"',
        )
    path.write_text(text, encoding="utf-8")

    def forbidden(*args: Any, **kwargs: Any) -> Any:
        pytest.fail("invalid config must fail before any host opens")

    monkeypatch.setattr(composition, "open_local_host", forbidden)
    with pytest.raises(SystemExit) as error:
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
            ]
        )
    assert error.value.code == 2


@pytest.mark.parametrize(
    "flag,value",
    [
        ("--binding", "replay"),
        ("--replay", "x"),
        ("--remote-profile", "x"),
        ("--remote-custody", "x"),
        ("--ollama-url", "x"),
        ("--ollama-model", "x"),
        ("--ollama-timeout", "1"),
        ("--bind", "replay"),
    ],
)
def test_models_exclusive_before_loading(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, flag: str, value: str
) -> None:
    def forbidden(*args: Any, **kwargs: Any) -> Any:
        pytest.fail("exclusive options must fail before loading or host creation")

    monkeypatch.setattr(cli, "load_models", forbidden)
    monkeypatch.setattr(composition, "open_local_host", forbidden)
    with pytest.raises(SystemExit) as error:
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
                "unused",
                flag,
                value,
            ]
        )
    assert error.value.code == 2


def test_role_report_redacts_recordings_and_model_content(tmp_path: Path) -> None:
    root = repository(tmp_path)
    canary = "PRIVATE_ROLE_CANARY"
    coding = json.loads(proposal(summary=canary, risks=[canary], unknowns=[canary]))
    for change in coding["changes"]:
        change["reason"] = canary
        change["content"] += "\n# " + canary + "\n"
    review = json.loads(REVIEW_ACCEPT)
    review["summary"] = canary
    coder = LoggedReplay([], json.dumps(coding))
    reviewer = LoggedReplay([], json.dumps(review))
    cfg = role_config(root, coder, reviewer)
    prepared = prepare_run(
        cfg,
        WorkspaceGuard(),
        approve=approve,
        sandbox=FakeSandbox(),
        confirm_context=lambda _: True,
    )
    result = asyncio.run(prepared.worker.run(task(), prepared.context))
    assert result.disposition is TaskDisposition.SUCCEEDED
    baseline = run_report(result, ModelBindingKind.REPLAY)
    report = run_report(result, ModelBindingKind.REPLAY, cfg.roles)
    assert report.pop("roles") == {
        role: {
            "binding": "replay",
            "model": "replay",
            "model_quality": "NOT_APPLICABLE_REPLAY",
        }
        for role in ("coder", "reviewer")
    }
    limitations = report.pop("limitations")
    previous_limitations = baseline.pop("limitations")
    assert isinstance(limitations, list) and isinstance(previous_limitations, list)
    assert limitations[:-1] == previous_limitations[:-1]
    assert "separately configured role host" in limitations[-1]
    assert report == baseline
    encoded = encode_report(run_report(result, ModelBindingKind.REPLAY, cfg.roles))
    assert canary not in encoded and "coder.json" not in encoded
    assert str(tmp_path) not in encoded and tmp_path.as_posix() not in encoded
    header = cli.header(cfg, task(), "unused")
    assert "model coder: replay replay" in header
    assert "model reviewer: replay replay" in header
    assert cfg.roles is not None
    mixed = replace(cfg.roles, reviewer=RoleModel("ollama", "local:7b"))
    mixed_report = json.loads(
        encode_report(run_report(result, ModelBindingKind.REPLAY, mixed))
    )
    assert mixed_report["roles"]["reviewer"]["model_quality"] == "UNQUALIFIED"


def test_legacy_one_host_and_unchanged_projection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = repository(tmp_path)
    model = LoggedReplay([], proposal(), REVIEW_ACCEPT)
    cfg = config(root, model)
    hosts, order = observe_hosts(monkeypatch)
    prepared = prepare_run(
        cfg,
        WorkspaceGuard(),
        approve=approve,
        sandbox=FakeSandbox(),
        confirm_context=lambda _: True,
    )
    result = asyncio.run(prepared.worker.run(task(), prepared.context))
    assert result.disposition is TaskDisposition.SUCCEEDED
    assert len(hosts) == 1 and order == [0, 0]
    assert hosts[0].runtime_requests == 1
    assert "roles" not in run_report(result, ModelBindingKind.REPLAY)
    # Existing independent pilot projection remains the baseline oracle.
    assert run_report(result, ModelBindingKind.REPLAY) == projected(result)
    assert "model: baseline\nNothing is written" in cli.header(cfg, task(), "baseline")


def test_ollama_defaults_and_closed_roles() -> None:
    roles = parse_models(
        {
            "schema": "forgeai-models/1",
            "revision": "r1",
            "roles": {
                role: {"binding": "ollama", "ollama_model": "local:7b"}
                for role in ("coder", "reviewer")
            },
        }
    )
    assert roles.coder.timeout == 300.0
    assert roles.reviewer.url == "http://127.0.0.1:11434"


def test_cli_role_file_uses_separate_recordings(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = repository(tmp_path)
    path = models_file(tmp_path)
    hosts, order = observe_hosts(monkeypatch)
    original = prepare_run

    def prepared(*args: Any, **kwargs: Any) -> composition.PreparedRun:
        return original(*args, **kwargs, sandbox=FakeSandbox())

    monkeypatch.setattr(cli, "prepare_run", prepared)
    output: list[str] = []
    code = cli.main(
        [
            "run",
            "--repo",
            str(root),
            "--task",
            task().objective,
            "--target",
            task().targets[0].path.value,
            "--target",
            task().targets[1].path.value,
            "--git",
            str(git_executable()),
            "--docker",
            str(git_executable()),
            "--models",
            str(path),
            "--json-report",
        ],
        ask=lambda _: "y",
        out=output.append,
        ready=lambda _: None,
    )
    assert code == 0 and len(hosts) == 2 and order == [0, 1]
    encoded = next(
        line.removeprefix("forgeai-report: ")
        for line in output
        if line.startswith("forgeai-report: ")
    )
    report = json.loads(encoded)
    assert set(report["roles"]) == {"coder", "reviewer"}
    assert str(path) not in encoded


@pytest.mark.skipif(
    os.environ.get("LEGOAI_QUALIFY_ROLE_HOSTS") != "1",
    reason="explicit real-Docker replay qualification only",
)
def test_real_docker_role_hosts(tmp_path: Path) -> None:
    root = repository(tmp_path)
    coder = LoggedReplay([], proposal())
    reviewer = LoggedReplay([], REVIEW_ACCEPT)
    executable = shutil.which("docker")
    assert executable is not None, "Docker and qualified checks image are required"
    cfg = replace(
        role_config(root, coder, reviewer),
        docker_executable=Path(executable),
        check_plan=(CheckRequest(CheckKind.PYTEST, (RepositoryPath("tests"),)),),
        test_strength=True,
    )
    sandbox = CountedDocker(cfg)
    prepared = prepare_run(
        cfg,
        WorkspaceGuard(),
        approve=approve,
        sandbox=sandbox,
        confirm_context=lambda _: True,
    )
    result = asyncio.run(prepared.worker.run(task(), prepared.context))
    assert result.disposition is TaskDisposition.SUCCEEDED
    assert coder.calls == reviewer.calls == 1 and sandbox.calls == 2
