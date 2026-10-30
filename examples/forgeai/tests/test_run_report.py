"""Run-report contracts with replay models and FakeSandbox; no live execution."""

import asyncio
import json
import shutil
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from forgeai_support import (
    REVIEW_ACCEPT,
    REVIEW_CHANGES,
    REWORK,
    FakeSandbox,
    approve,
    config,
    git_executable,
    logged_run,
    proposal,
    replay,
    repository,
    task,
)
from legoai_engineering.repository.workspace import RepositoryPath
from legoai_engineering.sandbox.errors import SandboxFailure

import demo
from forgeai import cli, report
from forgeai.composition import prepare_run
from forgeai.domain import (
    LIMITATIONS,
    AttemptEvidence,
    OperatorDecision,
    TaskDisposition,
    TaskEvidence,
    TaskFailure,
    TaskResult,
)
from forgeai.guard import WorkspaceGuard
from forgeai.report import (
    MAX_REPORT_BYTES,
    REPORT_SCHEMA,
    ModelBindingKind,
    ModelQuality,
    encode_report,
    model_quality,
    run_report,
)
from scripts.forgeai_kisski_bounded_live_pilot import projection


def shared_fields(actual: Any, pilot: Any) -> None:
    """Compare shared leaves recursively: attempt schemas intentionally differ."""
    if isinstance(actual, dict) and isinstance(pilot, dict):
        for key in actual.keys() & pilot.keys() - {"status", "no_change"}:
            shared_fields(actual[key], pilot[key])
    elif isinstance(actual, list) and isinstance(pilot, list):
        assert len(actual) == len(pilot)
        for left, right in zip(actual, pilot, strict=True):
            shared_fields(left, right)
    else:
        assert actual == pilot


def projected(result: TaskResult) -> dict[str, Any]:
    value = run_report(result, ModelBindingKind.REPLAY)
    shared_fields(value, projection(result))
    assert value["disposition"] == projection(result)["task_disposition"]
    assert value["failure"] == projection(result)["task_failure"]
    encoded = encode_report(value)
    assert encoded == encode_report(run_report(result, ModelBindingKind.REPLAY))
    assert len(encoded.encode("utf-8")) <= MAX_REPORT_BYTES
    assert "\n" not in encoded
    decoded: dict[str, Any] = json.loads(encoded)
    return decoded


def test_success_complete_schema(tmp_path: Path) -> None:
    result, _, _, _, _ = logged_run(repository(tmp_path), proposal(), REVIEW_ACCEPT)
    assert result.disposition is TaskDisposition.SUCCEEDED
    start = result.evidence.start
    assert start is not None and start.head.commit is not None
    assert projected(result) == {
        "schema": REPORT_SCHEMA,
        "run_id": result.evidence.run_id,
        "disposition": "SUCCEEDED",
        "failure": None,
        "model_binding": "REPLAY",
        "model_quality": "NOT_APPLICABLE_REPLAY",
        "start_head": start.head.commit.value,
        "context_confirmed": True,
        "rework_used": False,
        "rework_trigger": None,
        "changes_retained": True,
        "repository_effect": "KNOWN",
        "rollback_performed": False,
        "limitations": list(LIMITATIONS),
        "attempts": [
            {
                "number": 1,
                "coding_status": "SUCCEEDED",
                "model_attempt": "SUCCEEDED",
                "model_effect": "COMPLETED",
                "proposal_valid": True,
                "no_change": False,
                "mutation_approval": True,
                "changed_paths": [
                    {"path": "src/inventory/stock.py", "kind": "UPDATE"},
                    {"path": "tests/test_stock.py", "kind": "UPDATE"},
                ],
                "mutation_uncertain": False,
                "mutation_denied": False,
                "mutation_conflict": False,
                "checks": [
                    {"kind": kind, "outcome": "PASSED", "no_result": False}
                    for kind in ("RUFF_CHECK", "MYPY", "PYTEST")
                ],
                "review_status": "COMPLETED",
                "review_decision": "ACCEPT",
                "blocking_findings": 0,
            }
        ],
    }


@pytest.mark.parametrize("trigger", ["checks", "review"])
def test_rework_and_pilot_equivalence(tmp_path: Path, trigger: str) -> None:
    outputs = (
        (proposal(), REWORK, REVIEW_ACCEPT)
        if trigger == "checks"
        else (proposal(), REVIEW_CHANGES, REWORK, REVIEW_ACCEPT)
    )
    result, _, _, _, _ = logged_run(
        repository(tmp_path),
        *outputs,
        exits=(1, 0, 0, 0, 0, 0) if trigger == "checks" else (0, 0, 0),
    )
    value = projected(result)
    assert value["disposition"] == "SUCCEEDED"
    assert value["rework_used"] is True
    assert value["rework_trigger"] == (
        "CHECK_FINDINGS" if trigger == "checks" else "REVIEW_CHANGES_REQUIRED"
    )
    first, second = value["attempts"]
    assert [first["number"], second["number"]] == [1, 2]
    assert first["blocking_findings"] == (None if trigger == "checks" else 1)
    assert second["review_decision"] == "ACCEPT"


def test_declined_proposal_has_no_repository_effect(tmp_path: Path) -> None:
    prepared = prepare_run(
        config(repository(tmp_path), replay()),
        WorkspaceGuard(),
        confirm_context=lambda _: True,
        approve=OperatorDecision.decline,
        sandbox=FakeSandbox(),
    )
    result = asyncio.run(prepared.worker.run(task(), prepared.context))
    value = projected(result)
    assert value["failure"] == "PROPOSAL_DECLINED"
    assert value["changes_retained"] is False
    assert value["repository_effect"] == "NONE"
    attempt = value["attempts"][0]
    assert attempt["mutation_approval"] is False
    assert attempt["changed_paths"] == []
    assert attempt["checks"] == []
    assert attempt["blocking_findings"] is None


def test_invalid_coding_output(tmp_path: Path) -> None:
    result, _, _, _, _ = logged_run(repository(tmp_path), "invalid-output-canary")
    value = projected(result)
    assert value["failure"] == TaskFailure.PROPOSAL_INVALID.name
    assert value["attempts"][0]["proposal_valid"] is False
    assert "invalid-output-canary" not in encode_report(value)


def test_unknown_repository_effect_is_not_lost() -> None:
    result = TaskResult(
        task(),
        TaskDisposition.FAILED,
        TaskFailure.MUTATION_PARTIAL,
        TaskEvidence(
            "uncertain-run",
            attempts=(AttemptEvidence(1, uncertain=RepositoryPath("src/a.py")),),
        ),
    )
    value = projected(result)
    assert value["repository_effect"] == "UNKNOWN"
    assert value["changes_retained"] is False
    assert value["start_head"] is None
    assert value["attempts"][0]["mutation_uncertain"] is True


def test_canary_content_is_never_reported(tmp_path: Path) -> None:
    canary = "PRIVATE_REPORT_CANARY_8b7c31"
    root = repository(tmp_path)
    target = root / demo.TARGETS[0]
    target.write_text(target.read_text("utf-8") + f"\n# {canary}\n", "utf-8")
    demo.git(root, git_executable(), "add", "--all")
    demo.git(
        root,
        git_executable(),
        "-c",
        "user.name=ForgeAI fixture",
        "-c",
        "user.email=fixture@forgeai.invalid",
        "commit",
        "--no-gpg-sign",
        "-m",
        "canary fixture",
    )
    coding = json.loads(proposal(summary=canary, risks=[canary], unknowns=[canary]))
    for change in coding["changes"]:
        change["reason"] = canary
        change["content"] += f"\n# {canary}\n"
    rework_coding = json.loads(json.dumps(coding))  # Deep copy of the JSON fixture.
    rework_coding["changes"][0]["content"] += f"\n# {canary} rework\n"
    review = json.loads(REVIEW_CHANGES)
    review["summary"] = canary
    review["findings"][0]["message"] = canary
    review["findings"][0]["required_action"] = canary
    request = replace(task(), objective=canary, constraints=(canary,))
    model = cli.ReplayModel(
        json.dumps(coding),
        json.dumps(review),
        json.dumps(rework_coding),
        json.dumps(review),
    )
    prepared = prepare_run(
        config(root, model),
        WorkspaceGuard(),
        confirm_context=lambda _: True,
        approve=approve,
        sandbox=FakeSandbox(),
    )
    result = asyncio.run(prepared.worker.run(request, prepared.context))
    assert result.failure is TaskFailure.REVIEW_CHANGES_REQUIRED
    assert model.calls == 4
    assert result.evidence.review is not None
    assert result.evidence.review.review is not None
    assert result.evidence.review.review.findings[0].message == canary
    value = projected(result)
    encoded = encode_report(value)
    assert value["attempts"][0]["blocking_findings"] == 1
    assert all(attempt["no_change"] is False for attempt in value["attempts"])
    assert canary not in encoded
    assert str(tmp_path) not in encoded
    assert json.dumps(str(tmp_path))[1:-1] not in encoded
    assert tmp_path.as_posix() not in encoded


@pytest.mark.parametrize("binding", list(ModelBindingKind))
def test_model_quality_is_closed(binding: ModelBindingKind) -> None:
    assert {member.value for member in ModelQuality} == {
        "NOT_APPLICABLE_REPLAY",
        "UNQUALIFIED",
    }
    expected = (
        ModelQuality.NOT_APPLICABLE_REPLAY
        if binding is ModelBindingKind.REPLAY
        else ModelQuality.UNQUALIFIED
    )
    assert model_quality(binding) is expected
    result = TaskResult(
        task(), TaskDisposition.REJECTED, TaskFailure.DIRTY_START, TaskEvidence("run")
    )
    value = run_report(result, binding)
    assert value["model_binding"] == binding.value
    assert value["model_quality"] == expected.value


@pytest.mark.parametrize("outcome", ["success", "failed", "rejected"])
def test_cli_opt_in_output_and_bound(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, outcome: str
) -> None:
    root = repository(tmp_path)
    if outcome == "rejected":
        (root / "untracked.txt").write_text("dirty", "utf-8")
    result, _, _, _, _ = logged_run(
        root, "invalid" if outcome == "failed" else proposal(), REVIEW_ACCEPT
    )
    cfg = config(root, replay())

    class RecordedWorker:
        async def run(self, request: object, context: object) -> TaskResult:
            return result

    # Reuse exactly the same observed result: UUIDs and repository state cannot
    # obscure byte-level output compatibility between flag-off and flag-on.
    monkeypatch.setattr(cli, "local_profile", lambda *a, **kw: cfg)
    monkeypatch.setattr(
        cli,
        "prepare_run",
        lambda *a, **kw: SimpleNamespace(worker=RecordedWorker(), context=None),
    )
    arguments = [
        str(root),
        "--objective",
        demo.OBJECTIVE,
        "--constraint",
        task().constraints[0],
        "--replay",
        str(demo.FIXTURE / "proposal.json"),
        "--git",
        str(git_executable()),
        "--docker",
        str(git_executable()),
    ]
    for target in demo.TARGETS:
        arguments += ["--target", target]
    baseline = [
        cli.header(cfg, task(), "replay (recorded outputs; not a live model)"),
        "[7/7] Final result",
        cli.summarize(result, root),
    ]
    expected_exit = {"success": 0, "failed": 1, "rejected": 2}[outcome]
    output: list[str] = []
    assert cli.main(arguments, out=output.append, ready=lambda _: None) == expected_exit
    assert "\n".join(output) == "\n".join(baseline)
    output.clear()
    arguments += ["--json-report"]
    assert cli.main(arguments, out=output.append, ready=lambda _: None) == expected_exit
    assert output[:-1] == baseline
    prefix = "forgeai-report: "
    assert output[-1].startswith(prefix)
    assert json.loads(output[-1][len(prefix) :]) == projected(result)
    monkeypatch.setattr(report, "MAX_REPORT_BYTES", 1)
    output.clear()
    assert cli.main(arguments, out=output.append, ready=lambda _: None) == expected_exit
    assert output == baseline + [prefix + "REPORT_UNAVAILABLE (bound exceeded)"]
    output.clear()
    assert (
        cli.main(
            arguments,
            out=output.append,
            ready=lambda _: SandboxFailure.RUNTIME_UNAVAILABLE,
        )
        == 2
    )
    assert not any(line.startswith(prefix) for line in output)


def test_encoding_bound_and_deterministic_ascii() -> None:
    with pytest.raises(ValueError):
        encode_report({"oversized": "x" * MAX_REPORT_BYTES})
    assert encode_report({"z": "é", "a": 1}) == '{"a":1,"z":"\\u00e9"}'
    assert encode_report({"a": 1, "z": "é"}) == encode_report({"z": "é", "a": 1})


@pytest.mark.parametrize("scenario", [[], ["accept"], ["rework"]])
def test_demo_passthrough(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, scenario: list[str]
) -> None:
    captured: list[list[str]] = []
    monkeypatch.setattr(shutil, "which", lambda _: str(git_executable()))
    monkeypatch.setattr(demo, "create_repository", lambda *a: tmp_path)

    def capture(arguments: list[str]) -> int:
        captured.append(arguments)
        return 0

    monkeypatch.setattr(demo, "forgeai", capture)
    assert demo.main(scenario) == 0
    assert demo.main((scenario or ["accept"]) + ["--json-report"]) == 0
    assert captured[1] == captured[0] + ["--json-report"]
