"""Offline synthetic controls; provider, credential and host seams are spies."""

import ast
import asyncio
import json
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from legoai.execution.values import ExecutionState
from legoai.runtime.api import HostError, HostFailure
from scripts import kisski_compatibility_probe as legacy
from scripts import kisski_saia_qualification as saia
from scripts.kisski_coding_eval import frozen, pack, scoring
from scripts.kisski_coding_eval import runner as original
from scripts.kisski_dev_screen import diagnostics, invocation, runner


def coding_value(task: pack.Task) -> dict[str, Any]:
    return {
        "summary": "Synthetic correction",
        "changes": [
            {
                "path": file.path,
                "operation": "update",
                "content": file.reference,
                "reason": "Correct the condition",
            }
            for file in task.files
        ],
        "risks": [],
        "unknowns": [],
    }


def finding(refs: list[str], category: str = "correctness") -> dict[str, Any]:
    return {
        "category": category,
        "severity": "blocking",
        "message": "Synthetic defect",
        "required_action": "Correct the condition",
        "evidence_refs": refs,
    }


def review_value(task: pack.Task) -> dict[str, Any]:
    return {
        "decision": (
            "changes_required" if task.task_id == "review" else "insufficient_evidence"
        ),
        "summary": "Synthetic review",
        "findings": (
            [finding(["r1"]), finding(["r2"]), finding(["r3"], "security")]
            if task.task_id == "review"
            else []
        ),
        "risks": [],
        "unknowns": [] if task.task_id == "review" else ["Missing policy"],
    }


def positive(task: pack.Task) -> str:
    return json.dumps(
        coding_value(task) if task.role == "coding" else review_value(task)
    )


def variants(task: pack.Task) -> list[str]:
    raw = positive(task)
    outputs = [raw, "```json\n" + raw + "\n```", "invalid JSON"]
    if task.role == "coding":
        for mode in (
            "signature",
            "else",
            "scope",
            "empty_reason",
            "missing",
            "unsafe",
        ):
            value = coding_value(task)
            change = value["changes"][0]
            if mode == "signature":
                name = (
                    "lo"
                    if task.task_id in ("bug", "multi")
                    else "authorized"
                    if task.task_id == "security"
                    else "value"
                )
                change["content"] = change["content"].replace(name, "renamed")
            elif mode == "else":
                change["content"] = task.files[0].before
            elif mode == "scope":
                change["path"] = "UNTRUSTED_PATH"
            elif mode == "empty_reason":
                change["reason"] = " "
            elif mode == "missing":
                value["changes"] = value["changes"][:1]
            else:
                change["content"] = "import os\n"
            body = json.dumps(value)
            outputs.extend((body, "```json\n" + body + "\n```"))
    else:
        value = review_value(task)
        value.update(decision="accept", findings=[], unknowns=[])
        outputs.append(json.dumps(value))
        value.update(decision="changes_required", findings=[finding(["r4"])])
        outputs.append(json.dumps(value))
    return outputs


@pytest.mark.parametrize("task", pack.TASKS, ids=lambda task: task.task_id)
def test_all_v1_fields_equal_imported_scorer(task: pack.Task) -> None:
    for raw in variants(task):
        expected = scoring.score(task, raw)
        row = diagnostics.task_row(task, raw)
        assert {key: row[key] for key in expected} == expected


@pytest.mark.parametrize(
    "task",
    [task for task in pack.TASKS if task.role == "coding"],
    ids=lambda task: task.task_id,
)
def test_coding_adherence_invariant_including_early_returns(task: pack.Task) -> None:
    for raw in variants(task):
        row = diagnostics.task_row(task, raw)
        facts = row["diagnostics"]
        if facts["rejected_category"] is None:
            assert facts["adherence_evaluated"] is True
            assert (facts["adherence_reasons"] == []) is row["instruction_adherence"]
        else:
            assert facts["adherence_evaluated"] is False
            assert facts["adherence_reasons"] == facts["observations"] == []


@pytest.mark.parametrize("fenced", [False, True])
def test_missing_multi_target_does_not_override_frozen_adherence(fenced: bool) -> None:
    task = next(t for t in pack.TASKS if t.task_id == "multi")
    value = coding_value(task)
    value["changes"] = value["changes"][:1]
    raw = json.dumps(value)
    if fenced:
        raw = "```json\n" + raw + "\n```"
    row = diagnostics.task_row(task, raw)
    assert row["instruction_adherence"] is (not fenced)
    assert row["patch_applies"] is False
    assert row["diagnostics"]["adherence_reasons"] == (
        ["FENCED_JSON"] if fenced else []
    )
    assert row["diagnostics"]["observations"] == ["TARGET_SET_MISMATCH"]


def test_signature_else_fence_combination_and_multi_path_isolation() -> None:
    task = next(t for t in pack.TASKS if t.task_id == "refactor")
    value = coding_value(task)
    value["changes"][0]["content"] = task.files[0].before.replace("value", "renamed")
    raw = "```json\n" + json.dumps(value) + "\n```"
    assert diagnostics.diagnose(task, raw)["adherence_reasons"] == [
        "ELSE_RETAINED",
        "FENCED_JSON",
        "SIGNATURE_CHANGED:subject.py",
    ]
    task = next(t for t in pack.TASKS if t.task_id == "multi")
    value = coding_value(task)
    value["changes"][1]["content"] = value["changes"][1]["content"].replace(
        "value", "renamed"
    )
    assert diagnostics.diagnose(task, json.dumps(value))["adherence_reasons"] == [
        "SIGNATURE_CHANGED:right.py"
    ]


@pytest.mark.parametrize("task", pack.TASKS, ids=lambda task: task.task_id)
def test_passing_outputs_have_no_adherence_reasons(task: pack.Task) -> None:
    assert diagnostics.diagnose(task, positive(task))["adherence_reasons"] == []


def test_security_fenced_correct_has_only_framing_reason() -> None:
    task = next(t for t in pack.TASKS if t.task_id == "security")
    facts = diagnostics.diagnose(task, "```json\n" + positive(task) + "\n```")
    assert facts["adherence_reasons"] == ["FENCED_JSON"]


def test_empty_reason_is_rejected_before_observations() -> None:
    task = pack.TASKS[0]
    value = coding_value(task)
    value["changes"][0]["reason"] = " "
    facts = diagnostics.diagnose(task, json.dumps(value))
    assert facts["rejected_category"] == "SCHEMA_INVALID"
    assert facts["observations"] == facts["adherence_reasons"] == []
    assert facts["adherence_evaluated"] is False


@pytest.mark.parametrize(
    ("kind", "expected", "rejected"),
    [
        ("wrong", "WRONG_CATEGORY", False),
        ("warning", "NOT_BLOCKING", False),
        ("action", "NO_REQUIRED_ACTION", True),
        ("multiple", "MULTIPLE_REFS", False),
        ("duplicate", "DUPLICATE_REF", False),
        ("clean", "CLEAN_REF", False),
        ("supplied_nondefect", "UNSUPPLIED_REF", False),
        ("unsupplied", "UNSUPPLIED_REF", True),
    ],
)
def test_each_reviewer_cause_and_contract_rejection(
    kind: str, expected: str, rejected: bool
) -> None:
    task = pack.TASKS[-1]
    value = review_value(task)
    extra = finding(["r1"])
    if kind == "wrong":
        extra["category"] = "security"
    elif kind == "warning":
        extra.update(severity="warning", required_action=None)
    elif kind == "action":
        extra["required_action"] = None
    elif kind == "multiple":
        extra["evidence_refs"] = ["r1", "r2"]
    elif kind == "clean":
        extra["evidence_refs"] = ["r4"]
    elif kind in ("supplied_nondefect", "unsupplied"):
        extra["evidence_refs"] = [
            "proposal" if kind == "supplied_nondefect" else "CANARY"
        ]
    value["findings"].append(extra)
    raw = json.dumps(value)
    facts = diagnostics.diagnose(task, raw)
    field = "reviewer_rejection_causes" if rejected else "false_positive_causes"
    assert facts[field] == {expected: 1}
    assert facts["reviewer_evaluated"] is (not rejected)
    if not rejected:
        assert (
            sum(facts[field].values())
            == scoring.score(task, raw)["reviewer_false_positives"]
        )
    else:
        assert facts["false_positive_causes"] == facts["reviewer_references"] == {}


def test_reviewer_match_order_and_duplicate_before_clean() -> None:
    task = pack.TASKS[-1]
    value = review_value(task)
    value["findings"][0]["evidence_refs"] = ["r1", "r3"]
    value["findings"].append(finding(["r1", "r4"]))
    facts = diagnostics.diagnose(task, json.dumps(value))
    assert facts["false_positive_causes"] == {"DUPLICATE_REF": 1}
    assert facts["reviewer_references"]["r1"] == "found"
    assert facts["reviewer_references"]["r4"] == "flagged_clean"
    value["findings"] = value["findings"][:2]
    facts = diagnostics.diagnose(task, json.dumps(value))
    assert facts["reviewer_references"]["r3"] == "missed"
    assert facts["false_positive_causes"] == {}


@pytest.mark.parametrize("with_findings", [False, True])
def test_abstention_reasons(with_findings: bool) -> None:
    task = pack.TASKS[-2]
    value = review_value(task)
    value.update(decision="accept", unknowns=[])
    expected = ["DECISION_NOT_INSUFFICIENT", "UNKNOWNS_EMPTY"]
    if with_findings:
        value.update(decision="changes_required", findings=[finding(["proposal"])])
        expected.append("FINDINGS_PRESENT")
    facts = diagnostics.diagnose(task, json.dumps(value))
    assert facts["abstention_reasons"] == expected


@pytest.mark.parametrize("task", pack.TASKS, ids=lambda task: task.task_id)
def test_canary_never_enters_diagnostics_or_report(task: pack.Task) -> None:
    canary = "SECRET_CANARY_8e71"
    value = coding_value(task) if task.role == "coding" else review_value(task)
    value.update(summary=canary, unknowns=[canary], risks=[canary])
    if task.role == "coding":
        for change in value["changes"]:
            change["reason"] = canary
            change["content"] = '"' + canary + '"\n' + change["content"]
    else:
        for item in value["findings"]:
            item.update(message=canary, required_action=canary)
    row = diagnostics.task_row(task, json.dumps(value))
    row.update(model_id="synthetic-model", invocation_outcome="completed")
    document = diagnostics.report(
        task.phase, [row], "manifest", 1024, ("synthetic-model",), completed=True
    )
    assert canary not in json.dumps(document)
    assert document["admission_effect"] == "NONE"


def test_summaries_use_frozen_classifier_and_require_complete_evidence() -> None:
    rows = []
    for task in pack.TASKS:
        row = diagnostics.task_row(task, positive(task))
        row.update(model_id="model", invocation_outcome="completed")
        rows.append(row)
    document = diagnostics.report(
        "B", rows, "manifest", 1024, ("model",), completed=True
    )
    assert document["summaries"]["model"]["frozen_rule_would_pass"] is True
    assert document["notice"] == diagnostics.NOTICE
    document = diagnostics.report(
        "A", rows[:4], "manifest", 1024, ("model",), completed=True
    )
    assert document["summaries"]["model"]["frozen_rule_would_pass"] is None
    rows[0]["instruction_adherence"] = False
    document = diagnostics.report(
        "B", rows, "manifest", 1024, ("model",), completed=True
    )
    assert document["summaries"]["model"]["frozen_rule_would_pass"] is False


@pytest.mark.parametrize("budget", [1024, 2048, 4096])
def test_output_budget_variant_is_explicit(budget: int) -> None:
    task = pack.TASKS[0]
    row = diagnostics.task_row(task, positive(task), budget)
    assert row["comparable_with_frozen"] is (budget == 1024)
    assert row["configuration"] == (
        "FROZEN_OUTPUT_TOKENS" if budget == 1024 else "DEV_VARIANT_OUTPUT_TOKENS"
    )


def forbidden(*args: Any, **kwargs: Any) -> Any:
    raise AssertionError("unauthorized effect")


def configure_candidates(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "candidates.json"
    path.write_text('["model-one", "model-two"]\n', encoding="utf-8")
    monkeypatch.setattr(runner, "CANDIDATES", path)


def gate_spies(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(runner, "open_credential_source", forbidden)
    monkeypatch.setattr(runner, "_provision_interactively", forbidden)
    monkeypatch.setattr(legacy, "_discover", forbidden)
    monkeypatch.setattr(runner, "open_local_host", forbidden)
    monkeypatch.setattr(runner, "invoke", forbidden)
    monkeypatch.setattr(tempfile, "mkdtemp", forbidden)


@pytest.mark.parametrize(
    "answer",
    ["", "yes", runner.authorization("B"), " " + runner.authorization("A")],
)
def test_wrong_authorization_has_zero_effects(
    answer: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    configure_candidates(tmp_path, monkeypatch)
    gate_spies(monkeypatch)
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr(sys.stdout, "isatty", lambda: True)
    monkeypatch.setattr("builtins.input", lambda _: answer)
    assert runner.main(["--live"]) == 2


def test_nontty_and_default_are_inert(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    configure_candidates(tmp_path, monkeypatch)
    gate_spies(monkeypatch)
    monkeypatch.setattr("builtins.input", forbidden)
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
    assert runner.main([]) == 0
    assert runner.main(["--live"]) == 2


def test_placeholder_refused_before_prompt_or_discovery(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "candidates.json"
    path.write_text('["REPLACE_WITH_EXACT_MODEL_ID"]\n', encoding="utf-8")
    monkeypatch.setattr(runner, "CANDIDATES", path)
    gate_spies(monkeypatch)
    monkeypatch.setattr("builtins.input", forbidden)
    assert runner.main(["--live"]) == 2


@pytest.mark.parametrize(
    "answer",
    ["unlisted", "model-one,unlisted", "model-one,model-one", '"model-one"', ""],
)
def test_selection_intersection(answer: str) -> None:
    with pytest.raises(ValueError, match="MODEL_SELECTION_INVALID"):
        runner.selected(answer, ("model-one",), {"model-one", "unlisted"})
    assert runner.selected("model-one", ("model-one",), {"model-one"}) == ("model-one",)


def test_invalid_output_budget_before_any_io(monkeypatch: pytest.MonkeyPatch) -> None:
    gate_spies(monkeypatch)
    monkeypatch.setattr(runner, "candidates", forbidden)
    with pytest.raises(SystemExit) as error:
        runner.main(["--live", "--output-tokens", "999"])
    assert error.value.code == 2


def test_raw_requires_second_exact_phrase(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    configure_candidates(tmp_path, monkeypatch)
    gate_spies(monkeypatch)
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr(sys.stdout, "isatty", lambda: True)
    answers = iter((runner.authorization("A"), "yes"))
    monkeypatch.setattr("builtins.input", lambda _: next(answers))
    assert runner.main(["--live", "--retain-raw"]) == 2
    assert not (tmp_path / "raw").exists()


def test_custody_and_raw_are_exclusive_and_byte_preserving(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="CUSTODY"):
        runner.outside_repository(runner.ROOT / "custody")
    with pytest.raises(ValueError, match="CUSTODY"):
        runner.retain(runner.ROOT, 0, pack.TASKS[0], "CANARY")
    raw = "synthetic\r\ntext\n"
    runner.retain(tmp_path, 0, pack.TASKS[0], raw)
    path = tmp_path / "raw/0-bug.txt"
    assert path.read_bytes() == raw.encode()
    with pytest.raises(FileExistsError):
        runner.retain(tmp_path, 0, pack.TASKS[0], "overwrite")
    assert path.read_bytes() == raw.encode()


def test_exact_chat_bound_for_each_phase_and_candidate_count() -> None:
    for phase in ("A", "B"):
        for count in range(1, 6):
            plan = runner.plan(phase, tuple(f"model-{i}" for i in range(count)), 1024)
            assert plan["maximum_chat_calls"] == count * 4
            assert plan["maximum_discovery_calls"] == 1


@dataclass(frozen=True)
class HostConfig:
    max_executions: int = 2


@pytest.mark.parametrize("phase", ["A", "B"])
@pytest.mark.parametrize("failure", ["none", "returned", "exception", "unknown"])
def test_attended_bounds_stop_only_failed_model_and_keep_loop_ownership(
    phase: str,
    failure: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    calls: list[tuple[str, str]] = []
    events: list[str] = []
    hosts: list[Any] = []
    models = ("model-one", "model-two")
    tasks = [t for t in pack.TASKS if t.phase == phase]
    source = SimpleNamespace(
        _source=object(),
        provision=lambda _: events.append("chat-credential"),
        close=lambda: events.append("closed"),
    )
    monkeypatch.setattr(runner, "open_credential_source", lambda _: source)
    monkeypatch.setattr(
        runner,
        "_provision_interactively",
        lambda *args: events.append("discovery-credential"),
    )

    def discover(*args: Any) -> Any:
        events.append("discovery")
        return SimpleNamespace(
            models=tuple(SimpleNamespace(value=m) for m in (*models, "unlisted"))
        )

    monkeypatch.setattr(legacy, "_discover", discover)
    monkeypatch.setattr(legacy, "classify_discovery", lambda _: None)
    monkeypatch.setattr(saia, "host_config", lambda *args: HostConfig())
    monkeypatch.setattr(runner, "RemoteModelRuntime", lambda *args: object())

    def open_host(config: HostConfig, *args: Any, **kwargs: Any) -> Any:
        assert config.max_executions == 4
        if hosts:
            assert hosts[-1].loop.is_closed()
        host = SimpleNamespace(
            model=models[len(hosts)], loop=asyncio.get_running_loop()
        )
        hosts.append(host)
        return host

    async def invoke(
        host: Any, config: Any, task: pack.Task
    ) -> tuple[dict[str, Any], str | None]:
        assert asyncio.get_running_loop() is host.loop
        assert config.max_output_tokens == 2048
        calls.append((host.model, task.task_id))
        if host.model == models[0] and task == tasks[1] and failure != "none":
            if failure == "exception":
                raise HostError(HostFailure.WRONG_EVENT_LOOP)
            if failure == "unknown":
                raise RuntimeError("PRIVATE_ERROR_CANARY")
            row = scoring.empty(task)
            row.update(
                invocation_outcome="provider_or_protocol_failure", output_tokens=None
            )
            return row, None
        raw = positive(task)
        row = scoring.score(task, raw)
        row.update(invocation_outcome="completed", output_tokens=100)
        return row, raw

    monkeypatch.setattr(runner, "open_local_host", open_host)
    monkeypatch.setattr(runner, "invoke", invoke)
    answers = iter((",".join(models), "y"))
    monkeypatch.setattr("builtins.input", lambda _: next(answers))
    assert runner.live(phase, tmp_path, models, 2048, False, "manifest") is (
        failure == "none"
    )
    expected = [
        (models[0], t.task_id) for t in (tasks if failure == "none" else tasks[:2])
    ]
    expected.extend((models[1], t.task_id) for t in tasks)
    assert calls == expected
    assert len(calls) == len(set(calls))
    assert events == ["discovery-credential", "discovery", "chat-credential", "closed"]
    report_text = (tmp_path / "evaluation.json").read_text()
    document = json.loads(report_text)
    assert document["admission_effect"] == "NONE"
    assert document["screening_bypassed"] is True
    assert all(not r["comparable_with_frozen"] for r in document["records"])
    assert not (tmp_path / "raw").exists()
    output = capsys.readouterr().out
    assert '"maximum_chat_calls": 8' in output
    assert "PRIVATE_ERROR_CANARY" not in output + report_text
    if failure in ("exception", "unknown"):
        assert document["records"][1]["failure_effect"] == (
            "NONE" if failure == "exception" else "UNKNOWN"
        )


@pytest.mark.parametrize("success", [True, False])
def test_mirrored_invocation_changes_only_raw_capture(
    success: bool, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    task = pack.TASKS[0]
    raw = positive(task)

    async def chat(*args: Any) -> Any:
        return SimpleNamespace(
            response=SimpleNamespace(content=raw, usage=None) if success else None,
            execution=SimpleNamespace(final_state=ExecutionState.SUCCEEDED),
            failure=None,
        )

    host = SimpleNamespace(
        model_execution=lambda *args, **kwargs: SimpleNamespace(
            execution_id=SimpleNamespace(value="exec-test")
        ),
        governed_chat=chat,
    )
    facts = {
        "rejection_reason": "FINISH_REASON_INVALID",
        "finish_reason_category": "LENGTH",
    }
    monkeypatch.setattr(
        original, "_remote_chat_contract_diagnostics", lambda *args: facts
    )
    monkeypatch.setattr(
        invocation, "_remote_chat_contract_diagnostics", lambda *args: facts
    )
    config = saia.live_config(tmp_path)
    expected = asyncio.run(original.invoke(host, config, task))
    actual, captured = asyncio.run(invocation.invoke(host, config, task))
    expected.pop("duration_ms")
    actual.pop("duration_ms")
    assert actual == expected
    assert captured == (raw if success else None)


def test_frozen_and_admission_isolation() -> None:
    assert len(frozen.verify()) == 64
    directory = runner.ROOT / "scripts/kisski_dev_screen"
    for path in directory.glob("*.py"):
        assert "ADMISSIONS" not in path.read_text(encoding="utf-8")
    pilot = ast.parse(
        (runner.ROOT / "scripts/forgeai_kisski_bounded_live_pilot.py").read_text(
            encoding="utf-8"
        )
    )
    assignments = [
        node
        for node in pilot.body
        if isinstance(node, ast.AnnAssign)
        and isinstance(node.target, ast.Name)
        and node.target.id == "ADMISSIONS"
    ]
    assert len(assignments) == 1
    assert assignments[0].value is not None
    assert ast.literal_eval(assignments[0].value) == ()


def test_custody_returned_inside_repo_is_refused_before_credentials(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    configure_candidates(tmp_path, monkeypatch)
    gate_spies(monkeypatch)
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr(sys.stdout, "isatty", lambda: True)
    monkeypatch.setattr("builtins.input", lambda _: runner.authorization("A"))
    monkeypatch.setattr(runner, "verify", lambda: "manifest")
    monkeypatch.setattr(
        tempfile, "mkdtemp", lambda **kwargs: str(runner.ROOT / "refused-custody")
    )
    assert runner.main(["--live"]) == 2


def test_raw_opt_in_reaches_only_local_custody_after_both_phrases(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    configure_candidates(tmp_path, monkeypatch)
    gate_spies(monkeypatch)
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr(sys.stdout, "isatty", lambda: True)
    answers = iter((runner.authorization("B"), runner.RAW_AUTHORIZATION))
    monkeypatch.setattr("builtins.input", lambda _: next(answers))
    monkeypatch.setattr(runner, "verify", lambda: "manifest")
    monkeypatch.setattr(tempfile, "mkdtemp", lambda **kwargs: str(tmp_path))

    def local_only(
        phase: str,
        custody: Path,
        listed: tuple[str, ...],
        tokens: int,
        retain_raw: bool,
        manifest: str,
    ) -> bool:
        assert phase == "B"
        assert tokens == 4096
        assert retain_raw is True
        runner.retain(custody, 0, pack.TASKS[0], "LOCAL_RAW_CANARY")
        return True

    monkeypatch.setattr(runner, "live", local_only)
    result = runner.main(
        ["--live", "--phase", "B", "--output-tokens", "4096", "--retain-raw"]
    )
    assert result == 0
    assert (tmp_path / "raw/0-bug.txt").read_text() == "LOCAL_RAW_CANARY"
    assert "LOCAL_RAW_CANARY" not in capsys.readouterr().out


def test_unknown_reviewer_shapes_use_only_other() -> None:
    value = review_value(pack.TASKS[-1])
    value["findings"] = [{"category": ["CANARY"], "evidence_refs": ["r1"]}]
    facts = diagnostics.diagnose(pack.TASKS[-1], json.dumps(value))
    assert facts["reviewer_rejection_causes"] == {"OTHER": 1}
    assert "CANARY" not in json.dumps(facts)


def test_invocation_mirror_has_only_authorized_capture_edits() -> None:
    def function(path: Path) -> ast.AsyncFunctionDef:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        return next(
            node
            for node in tree.body
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "invoke"
        )

    before = function(runner.ROOT / "scripts/kisski_coding_eval/runner.py")
    after = function(runner.ROOT / "scripts/kisski_dev_screen/invocation.py")
    initial = after.body[0]
    assert isinstance(initial, ast.AnnAssign)
    assert isinstance(initial.target, ast.Name)
    assert initial.target.id == "raw"
    after.body.pop(0)
    success = next(node for node in after.body if isinstance(node, ast.If))
    assert isinstance(success.body[0], ast.Assign)
    assert ast.dump(success.body[0]) == ast.dump(
        ast.parse("raw = result.response.content").body[0]
    )
    success.body.pop(0)
    assert isinstance(after.body[-1], ast.Return)
    assert ast.dump(after.body[-1]) == ast.dump(ast.parse("return row, raw").body[0])
    after.body[-1] = before.body[-1]
    after.returns = before.returns
    assert ast.dump(after) == ast.dump(before)
