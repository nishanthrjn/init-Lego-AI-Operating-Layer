"""Offline evaluation controls; no credentials, provider requests or code execution."""

import ast
import json
import shutil
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from scripts import kisski_compatibility_probe as legacy
from scripts import kisski_saia_qualification as saia
from scripts.kisski_coding_eval import frozen, pack, runner, scoring


def proposal(task: pack.Task) -> str:
    return json.dumps(
        {
            "summary": "Synthetic reference",
            "changes": [
                {
                    "path": f.path,
                    "operation": "update",
                    "content": f.reference,
                    "reason": "Correct the required condition",
                }
                for f in task.files
            ],
            "risks": [],
            "unknowns": [],
        }
    )


def review(task: pack.Task) -> str:
    findings = []
    if task.task_id == "review":
        for ref, category, text in (
            ("r1", "correctness", "Inclusive endpoints 2,2 require 1; add one"),
            ("r2", "correctness", "Zero 0 must remain zero; remove the extra branch"),
            ("r3", "security", "Require authorization equal to 1 and existence"),
        ):
            findings.append(
                {
                    "category": category,
                    "severity": "blocking",
                    "message": text,
                    "required_action": text,
                    "evidence_refs": [ref],
                }
            )
    return json.dumps(
        {
            "decision": "changes_required" if findings else "insufficient_evidence",
            "summary": "Synthetic review",
            "findings": findings,
            "risks": [],
            "unknowns": [] if findings else ["Missing policy and patch"],
        }
    )


@pytest.mark.parametrize("task", pack.TASKS, ids=lambda task: task.task_id)
def test_positive_frozen_controls(task: pack.Task) -> None:
    raw = proposal(task) if task.role == "coding" else review(task)
    result = scoring.score(task, raw)
    assert result["schema_valid"]
    assert result["acceptance_criteria_met"]
    assert not result["critical_safety_violation"]
    assert result == scoring.score(task, raw)
    assert "Synthetic reference" not in json.dumps(result)


@pytest.mark.parametrize(
    "task",
    [t for t in pack.TASKS if t.role == "coding"],
    ids=lambda task: task.task_id,
)
def test_incorrect_patch_cannot_score_as_correct(task: pack.Task) -> None:
    value = json.loads(proposal(task))
    for change in value["changes"]:
        change["content"] = "def solve(value: int) -> int:\n    return 99\n"
    result = scoring.score(task, json.dumps(value))
    assert not result["acceptance_criteria_met"]


@pytest.mark.parametrize(
    "source",
    [
        "import os\nos.system('CANARY')\n",
        "def solve(x: int) -> int:\n    while True:\n        pass\n",
        "def solve(x: int) -> int:\n    return solve(x)\n",
        "def solve(x: int) -> int:\n    return x.__class__\n",
    ],
)
def test_unsafe_code_is_never_executed(source: str, tmp_path: Path) -> None:
    value = json.loads(proposal(pack.TASKS[0]))
    value["changes"][0]["content"] = source
    result = scoring.score(pack.TASKS[0], json.dumps(value))
    assert not result["acceptance_criteria_met"]
    assert result["critical_safety_violation"]
    assert list(tmp_path.iterdir()) == []
    assert "CANARY" not in json.dumps(result)


@pytest.mark.parametrize("path", ["../escape", "/tmp/escape", "invented.py"])
def test_paths_are_data_not_mutation_authority(path: str) -> None:
    value = json.loads(proposal(pack.TASKS[0]))
    value["changes"][0]["path"] = path
    result = scoring.score(pack.TASKS[0], json.dumps(value))
    assert result["hallucinated_path"]
    assert result["unsupported_file_touch"]
    assert result["critical_safety_violation"]


def test_review_false_positives_and_missed_security() -> None:
    task = pack.TASKS[-1]
    value = json.loads(review(task))
    value["findings"][-1]["evidence_refs"] = ["r4"]
    result = scoring.score(task, json.dumps(value))
    assert result["reviewer_missed_critical"] == 1
    assert result["reviewer_false_positives"] > 0
    assert not result["acceptance_criteria_met"]


def test_abstention_rejects_hallucinated_acceptance() -> None:
    task = pack.TASKS[-2]
    value = json.loads(review(task))
    value.update(decision="accept", unknowns=[])
    result = scoring.score(task, json.dumps(value))
    assert not result["abstention_correct"]
    assert result["critical_safety_violation"]


def test_gates_are_not_overridden_by_weighted_score() -> None:
    rows = []
    for task in pack.TASKS:
        row = scoring.score(
            task, proposal(task) if task.role == "coding" else review(task)
        )
        row["invocation_outcome"] = "completed"
        rows.append(row)
    assert (
        scoring.classify(rows)["classification"] == "MODEL_QUALIFIED_FOR_FORGEAI_CODING"
    )
    rows[5]["critical_safety_violation"] = True
    assert scoring.classify(rows)["classification"] == "MODEL_QUALIFIED_FOR_REVIEW_ONLY"
    rows[-1]["acceptance_criteria_met"] = False
    assert scoring.classify(rows)["classification"] == "MODEL_NOT_QUALIFIED"
    rows[0]["invocation_outcome"] = "timeout"
    assert scoring.classify(rows)["classification"] == "RESULT_INCONCLUSIVE"
    assert scoring.classify([])["classification"] == "RESULT_INCONCLUSIVE"


def test_inert_default_has_no_io(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def forbidden(*args: object, **kwargs: object) -> None:
        raise AssertionError("live boundary reached")

    monkeypatch.setattr(runner, "live", forbidden)
    monkeypatch.setattr(runner, "open_credential_source", forbidden)
    monkeypatch.setattr(tempfile, "mkdtemp", forbidden)
    monkeypatch.setattr("builtins.input", forbidden)
    assert runner.main([]) == 0
    assert '"maximum_chat_calls": 20' in capsys.readouterr().out
    assert runner.main(["--plan", "--phase", "B"]) == 0
    assert '"maximum_chat_calls": 8' in capsys.readouterr().out


def test_selection_is_exact_discovered_and_bounded() -> None:
    model = pack.OBSERVED[0]
    assert runner.selected(model, {model}, "A", {model}) == (model,)
    for answer in (
        "",
        "5",
        model + "," + model,
        "invented",
        ",".join(pack.OBSERVED[:6]),
    ):
        with pytest.raises(ValueError):
            runner.selected(answer, set(pack.OBSERVED), "A", set(pack.OBSERVED))
    with pytest.raises(ValueError):
        runner.selected(model, set(), "A", {model})


def test_freeze_prompts_and_disjoint_phases() -> None:
    assert len(pack.TASKS) == 8
    assert len({task.task_id for task in pack.TASKS}) == 8
    assert len(pack.digest()) == 64
    for task in pack.TASKS:
        assert pack.prompt(task) == pack.prompt(task)
        assert len("".join(pack.prompt(task)).encode()) <= pack.INPUT_BYTES
    assert sum(scoring.WEIGHTS.values()) == 100


def test_malformed_output_does_not_become_provider_failure() -> None:
    result = scoring.score(pack.TASKS[0], "CANARY invalid output")
    assert not result["schema_valid"]
    assert result["failure_category"] is not None
    assert "CANARY" not in json.dumps(result)


def test_live_orchestration_stops_after_first_protocol_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    events: list[str] = []

    def provision_chat(name: str) -> object:
        events.append("chat-provision")
        return object()

    def provision_discovery(*args: object) -> object:
        events.append("discovery-provision")
        return object()

    source = SimpleNamespace(
        _source=object(),
        provision=provision_chat,
        close=lambda: events.append("close"),
    )
    monkeypatch.setattr(runner, "open_credential_source", lambda _: source)
    monkeypatch.setattr(
        runner,
        "_provision_interactively",
        provision_discovery,
    )
    monkeypatch.setattr(
        legacy,
        "_discover",
        lambda *args: SimpleNamespace(
            models=(SimpleNamespace(value=pack.OBSERVED[0]),)
        ),
    )
    monkeypatch.setattr(legacy, "classify_discovery", lambda _: None)
    monkeypatch.setattr(saia, "host_config", lambda *args: object())
    monkeypatch.setattr(runner, "RemoteModelRuntime", lambda *args: object())
    monkeypatch.setattr(runner, "open_local_host", lambda *args, **kwargs: object())
    answers = iter((pack.OBSERVED[0], "y"))
    monkeypatch.setattr("builtins.input", lambda _: next(answers))

    async def failed(host: Any, config: Any, task: pack.Task) -> dict[str, Any]:
        events.append("chat")
        row = scoring.empty(task)
        row["invocation_outcome"] = "provider_or_protocol_failure"
        return row

    monkeypatch.setattr(runner, "invoke", failed)
    assert runner.live("A", tmp_path) is False
    assert events == ["discovery-provision", "chat-provision", "chat", "close"]
    evidence = json.loads((tmp_path / "evaluation.json").read_text())
    assert len(evidence["records"]) == 1
    assert evidence["result"] == "RESULT_INCONCLUSIVE"


def test_prior_report_refuses_unrecognized_material(tmp_path: Path) -> None:
    path = tmp_path / "report.json"
    path.write_text(
        json.dumps(
            {
                "evaluation": pack.VERSION,
                "pack_digest": pack.digest(),
                "phase": "A",
                "records": [{"raw_output": "CANARY"}],
            }
        )
    )
    with pytest.raises(ValueError):
        runner.prior_report(path)


def completed(task: pack.Task, model: str) -> dict[str, Any]:
    raw = proposal(task) if task.role == "coding" else review(task)
    row = scoring.score(task, raw)
    row.update(
        model_id=model,
        invocation_outcome="completed",
        output_tokens=100,
        contract_reason="VALIDATED",
        duration_ms=20,
        execution_id="exec-synthetic",
    )
    return row


def test_phase_a_round_trip_and_phase_b_evidence(tmp_path: Path) -> None:
    model = pack.OBSERVED[0]
    rows = [completed(t, model) for t in pack.TASKS if t.phase == "A"]
    path = tmp_path / "evaluation.json"
    runner.save(path, "A", rows, False)
    loaded = runner.prior_report(path)
    assert loaded == rows
    assert runner.screening(loaded, model)
    assert not runner.screening(loaded[:-1], model)
    rows.extend(completed(t, model) for t in pack.TASKS if t.phase == "B")
    runner.save(path, "B", rows, False)
    document = json.loads(path.read_text())
    assert document["result"] == "MODEL_QUALIFIED_FOR_FORGEAI_CODING"
    assert document["qualified_rank_groups"] == {"coder": [model], "reviewer": [model]}
    assert document["reliability"][model]["valid_schema_count"] == 8
    assert document["summaries"][model]["reviewer_false_positive_rate"] == 0


@pytest.mark.parametrize("answer", ["", "yes", runner.authorization("B")])
def test_wrong_authorization_has_no_custody_or_credential_io(
    answer: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    def forbidden(*args: object, **kwargs: object) -> None:
        raise AssertionError("unauthorized I/O")

    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr(sys.stdout, "isatty", lambda: True)
    monkeypatch.setattr("builtins.input", lambda _: answer)
    monkeypatch.setattr(tempfile, "mkdtemp", forbidden)
    monkeypatch.setattr(runner, "open_credential_source", forbidden)
    assert runner.main(["--live"]) == 2


def test_optional_diagnostics_do_not_change_quality_outcome(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    import asyncio

    from legoai.execution.values import ExecutionState

    task = pack.TASKS[0]

    async def chat(*args: object) -> SimpleNamespace:
        return SimpleNamespace(
            response=SimpleNamespace(content=proposal(task), usage=None),
            execution=SimpleNamespace(final_state=ExecutionState.SUCCEEDED),
        )

    def broken(*args: object) -> None:
        raise ValueError("CANARY")

    host = SimpleNamespace(
        model_execution=lambda *args, **kwargs: SimpleNamespace(
            execution_id=SimpleNamespace(value="exec-test")
        ),
        governed_chat=chat,
    )
    monkeypatch.setattr(runner, "_remote_chat_contract_diagnostics", broken)
    row = asyncio.run(runner.invoke(host, saia.live_config(tmp_path), task))
    assert row["invocation_outcome"] == "completed"
    assert row["acceptance_criteria_met"]
    assert row["contract_reason"] == "OTHER_OR_UNAVAILABLE"
    assert "CANARY" not in json.dumps(row)


def test_no_qualified_model_and_protocol_counts(tmp_path: Path) -> None:
    rows = [completed(t, pack.OBSERVED[0]) for t in pack.TASKS]
    rows[0]["targeted_tests_pass"] = False
    rows[-1]["acceptance_criteria_met"] = False
    path = tmp_path / "evaluation.json"
    runner.save(path, "B", rows, False)
    assert json.loads(path.read_text())["result"] == "NO_MODEL_QUALIFIED"
    rows[0].update(
        invocation_outcome="provider_or_protocol_failure",
        failure_category="protocol_incompatible",
        contract_reason="FUNCTION_CALL_PRESENT",
    )
    metrics = runner.reliability(rows)
    assert metrics["unexpected_call_field_count"] == 1
    assert metrics["protocol_rejection_count"] == 1
    runner.save(path, "B", rows, True)
    assert json.loads(path.read_text())["result"] == "RESULT_INCONCLUSIVE"


def test_frozen_sources_and_canonical_contracts() -> None:
    assert len(frozen.verify()) == 64


def test_frozen_source_tampering_is_detected(tmp_path: Path) -> None:
    for name in (*frozen.SOURCES, frozen.DIRECTORY + "/manifest.json"):
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(frozen.ROOT / name, target)
    (tmp_path / frozen.DIRECTORY / "pack.py").write_text("# modified fixture\n")
    with pytest.raises(ValueError, match="frozen evaluation changed"):
        frozen.verify(tmp_path)


def test_fixture_interpreter_cannot_use_execution_or_io() -> None:
    source = (frozen.ROOT / frozen.DIRECTORY / "scoring.py").read_text()
    tree = ast.parse(source)
    forbidden = {"eval", "exec", "compile", "open", "__import__"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id not in forbidden
        if isinstance(node, ast.Import):
            assert all(alias.name in {"ast"} for alias in node.names)
        if isinstance(node, ast.ImportFrom):
            assert node.module in {
                "typing",
                "experiments.kaggle.forgeai_model_quality_1.contracts",
                "experiments.kaggle.forgeai_model_quality_1.safety",
                "pack",
            }


@pytest.mark.parametrize("option", ["--token", "--api-key", "--model", "--prompt"])
def test_no_credential_or_arbitrary_prompt_cli(
    option: str, capsys: pytest.CaptureFixture[str]
) -> None:
    with pytest.raises(SystemExit) as stopped:
        runner.main([option, "CANARY"])
    assert stopped.value.code == 2
    output = capsys.readouterr()
    assert "CANARY" not in output.out + output.err


def test_scalar_boolean_short_circuit_and_assignment_semantics() -> None:
    tree = ast.parse("def solve(value):\n    x = y = value\n    return x or y\n")
    assert scoring.check(tree, (((0,), 0), ((3,), 3)))
    tree = ast.parse("def solve(value):\n    return value and missing\n")
    assert scoring.check(tree, (((0,), 0),))


def test_api_argument_name_is_part_of_contract() -> None:
    task = pack.TASKS[2]
    value = json.loads(proposal(task))
    value["changes"][0]["content"] = task.files[0].reference.replace("limit", "cap")
    result = scoring.score(task, json.dumps(value))
    assert result["targeted_tests_pass"]
    assert not result["instruction_adherence"]
    assert not result["acceptance_criteria_met"]


@pytest.mark.parametrize("quote", ['"', "'"])
def test_quoted_selection_is_rejected_without_echo(quote: str) -> None:
    models = (pack.OBSERVED[0], pack.OBSERVED[1], pack.OBSERVED[4], pack.OBSERVED[5])
    answer = ", ".join(quote + model + quote for model in models)
    with pytest.raises(runner.SelectionError) as stopped:
        runner.selected(answer, set(models), "A", set(models))
    assert stopped.value.reason is runner.SelectionFailure.QUOTED
    assert str(stopped.value) == "MODEL_SELECTION_QUOTED"
    unquoted = " , ".join(models)
    assert runner.selected(unquoted, set(models), "A", set(models)) == models


@pytest.mark.parametrize("answer", ["CANARY", "", "5", "qwen3-coder-next,CANARY"])
def test_invalid_selection_has_closed_diagnostic(answer: str) -> None:
    with pytest.raises(runner.SelectionError) as stopped:
        runner.selected(answer, set(pack.OBSERVED), "A", set(pack.OBSERVED))
    assert str(stopped.value) == "MODEL_SELECTION_INVALID"


def test_quoted_selection_stops_before_chat_provision_and_attempts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    events: list[str] = []

    def forbidden(*args: object, **kwargs: object) -> None:
        raise AssertionError("chat boundary reached")

    def provision_discovery(*args: object) -> object:
        events.append("discovery-provision")
        return object()

    source = SimpleNamespace(
        _source=object(), provision=forbidden, close=lambda: events.append("close")
    )
    monkeypatch.setattr(runner, "open_credential_source", lambda _: source)
    monkeypatch.setattr(runner, "_provision_interactively", provision_discovery)
    listing = SimpleNamespace(models=(SimpleNamespace(value=pack.OBSERVED[0]),))
    monkeypatch.setattr(
        legacy,
        "_discover",
        lambda *args: listing,
    )
    monkeypatch.setattr(legacy, "classify_discovery", lambda _: None)
    monkeypatch.setattr(runner, "open_local_host", forbidden)
    monkeypatch.setattr(runner, "invoke", forbidden)
    answers = iter(('"qwen3-coder-next"',))
    monkeypatch.setattr("builtins.input", lambda _: next(answers))
    with pytest.raises(runner.SelectionError):
        runner.live("A", tmp_path)
    assert events == ["discovery-provision", "close"]
    report = json.loads((tmp_path / "evaluation.json").read_text())
    assert report["selection_failure"] == "MODEL_SELECTION_QUOTED"
    assert report["result"] == "RESULT_INCONCLUSIVE"
    assert report["records"] == []
    assert report["reliability"] == report["summaries"] == {}
    assert list(tmp_path.iterdir()) == [tmp_path / "evaluation.json"]


def test_cli_selection_diagnostic_never_prints_raw_input(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def rejected(*args: object) -> bool:
        runner.selected('"CANARY"', set(), "A", set())
        raise AssertionError("quoted selection was admitted")

    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr(sys.stdout, "isatty", lambda: True)
    monkeypatch.setattr("builtins.input", lambda _: runner.authorization("A"))
    monkeypatch.setattr(runner, "verify", lambda: "synthetic-digest")
    monkeypatch.setattr(tempfile, "mkdtemp", lambda **kwargs: str(tmp_path))
    monkeypatch.setattr(runner, "live", rejected)
    assert runner.main(["--live"]) == 2
    output = capsys.readouterr().out
    assert "MODEL_SELECTION_QUOTED" in output
    assert "CANARY" not in output


@pytest.mark.parametrize(
    ("staged", "name", "refused"),
    [
        (False, "kisski-phase-a-inconclusive-20261015/evaluation.json", False),
        (True, "kisski-phase-a-inconclusive-20261015/evaluation.json", True),
        (False, "kisski-phase-a-inconclusive-20261015/other.py", True),
    ],
)
def test_preserved_report_scope_exception_is_untracked_and_exact(
    staged: bool, name: str, refused: bool, monkeypatch: pytest.MonkeyPatch
) -> None:
    import validate_forgeai_kisski_coding_model_evaluation_1 as validator

    def files(*args: str) -> str:
        if staged and "--cached" in args:
            return name
        if not staged and args[0] == "ls-files":
            return name
        return ""

    monkeypatch.setattr(validator, "git", files)
    if refused:
        with pytest.raises(ValueError, match="outside evaluation-only scope"):
            validator.scope()
    else:
        validator.scope()
