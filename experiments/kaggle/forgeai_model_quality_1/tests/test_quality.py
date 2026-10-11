"""Maintainer-run offline requirements, safety and scoring checks; no models."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from experiments.kaggle.forgeai_model_quality_1 import (
    contracts,
    evaluator,
    package,
    quality_probe,
)
from experiments.kaggle.forgeai_model_quality_1.result_contract import validate_result
from experiments.kaggle.forgeai_model_quality_1.safety import admitted
from experiments.kaggle.forgeai_model_quality_1.scenarios import CASES, Case, prompt


def proposal(case: Case, *, vacuous: bool = False) -> str:
    files = {"subject.py": case.reference}
    if case.strength:
        files["test_candidate.py"] = (
            "def test_vacuous() -> None:\n    assert True\n"
            if vacuous
            else evaluator.oracle_source(case)
        )
    return json.dumps(
        {
            "summary": "Synthetic correction",
            "risks": [],
            "unknowns": [],
            "changes": [
                {
                    "path": path,
                    "operation": case.targets[path],
                    "content": content,
                    "reason": "Meet the objective",
                }
                for path, content in files.items()
            ],
        }
    )


def test_inventory_and_prompt_bounds() -> None:
    assert len(CASES) == 10
    assert len({case.name for case in CASES}) == 10
    assert sum(2 if case.rework else 1 for case in CASES) == contracts.CALL_LIMIT == 11
    for case in CASES:
        content = prompt(case)
        assert len(content.encode()) <= contracts.INPUT_BYTES
        assert "D:\\" not in content and "C:\\" not in content
        assert "legoai_engineering" not in content
        if case.reference:
            assert json.dumps(case.reference) not in content


@pytest.mark.parametrize(
    "path",
    [
        "../escape.py",
        "/tmp/escape",
        "policy.txt",
        "SUBJECT.py",
        "subject.py/child",
        "conftest.py",
    ],
)
def test_unrequested_target_rejected_before_write(path: str) -> None:
    value = json.loads(proposal(CASES[0]))
    value["changes"][0]["path"] = path
    with pytest.raises(contracts.Rejected, match="SCOPE_VIOLATION"):
        contracts.coding(json.dumps(value), CASES[0].targets)


@pytest.mark.parametrize(
    "raw",
    [
        '{"summary":1,"summary":2}',
        "[]",
        "{} trailing",
        "```python\n{}\n```",
        "NaN",
    ],
)
def test_non_document_output_rejected(raw: str) -> None:
    with pytest.raises(contracts.Rejected):
        contracts.coding(raw, CASES[0].targets)


def test_framing_and_duplicate_change() -> None:
    raw = proposal(CASES[0])
    assert contracts.coding("```json\n" + raw + "\n```", CASES[0].targets)[1] is False
    value = json.loads(raw)
    value["changes"].append(value["changes"][0])
    with pytest.raises(contracts.Rejected):
        contracts.coding(json.dumps(value), CASES[0].targets)


@pytest.mark.parametrize(
    "source",
    [
        "import os\n",
        "def solve(a: int) -> int:\n    return a.__class__\n",
        "def solve(a: int) -> int:\n    return solve(a)\n",
        "def solve(a: int) -> int:\n    while True:\n        pass\n",
        "def solve(a: int) -> int:\n    return eval('1')\n",
        "@print\ndef solve(a: int) -> int:\n    return a\n",
        "def solve(a: int) -> int:\n    return 2 ** 100\n",
        "def solve(a: int) -> int:\n    return a # type: ignore\n",
        "def solve(a: int) -> int:\n    return open('secret')\n",
        "def solve(a: int) -> int:\n    s = 'a'\n    return s + s\n",
    ],
)
def test_active_python_rejected(source: str) -> None:
    with pytest.raises(contracts.Rejected):
        admitted(source, test=False)


@pytest.mark.parametrize(
    "case",
    [case for case in CASES if not case.review_kind],
    ids=[case.name for case in CASES if not case.review_kind],
)
def test_reference_solutions_pass_real_deterministic_tools(case: Case) -> None:
    result, _ = evaluator.score_coding(case, proposal(case))
    assert not result["failures"]
    assert result["dimensions"]["TASK_CORRECTNESS"] == "PASS"
    assert result["dimensions"]["STATIC_QUALITY"] == "PASS"
    if case.strength:
        assert result["dimensions"]["TEST_STRENGTH"] == "PASS"


def test_passing_both_versions_is_vacuous() -> None:
    result, _ = evaluator.score_coding(CASES[0], proposal(CASES[0], vacuous=True))
    assert "VACUOUS_TEST" in result["failures"]
    assert result["dimensions"]["TASK_CORRECTNESS"] == "PASS"
    assert result["dimensions"]["TEST_STRENGTH"] == "FAIL"


def review_value(*, bad: bool = False) -> dict[str, Any]:
    return {
        "decision": "changes_required" if bad else "accept",
        "summary": "Synthetic review",
        "risks": [],
        "unknowns": [],
        "findings": (
            [
                {
                    "category": "correctness",
                    "severity": "blocking",
                    "message": "Inclusive endpoints are off-by-one",
                    "evidence_refs": ["proposal"],
                    "required_action": "Add one to include the final endpoint",
                }
            ]
            if bad
            else []
        ),
    }


def test_review_known_truth_and_false_negative() -> None:
    good, bad = CASES[7:9]
    accepted = evaluator.score_review(good, json.dumps(review_value()))
    rejected = evaluator.score_review(bad, json.dumps(review_value(bad=True)))
    assert accepted["dimensions"]["REVIEW_ACCURACY"] == "PASS"
    assert rejected["dimensions"]["REVIEW_ACCURACY"] == "PASS"
    result = evaluator.score_review(bad, json.dumps(review_value()))
    assert result["false_negative"] is True
    assert result["dimensions"]["REVIEW_ACCURACY"] == "FAIL"


def test_review_actions_references_and_consistency() -> None:
    for key, replacement in (
        ("required_action", None),
        ("evidence_refs", ["invented"]),
    ):
        value = review_value(bad=True)
        value["findings"][0][key] = replacement
        with pytest.raises(contracts.Rejected):
            contracts.review(json.dumps(value), {"proposal"})


def test_thresholds_are_not_one_aggregate() -> None:
    rows = [evaluator.empty_result(case) for case in CASES]
    for row in rows:
        row["dimensions"] = dict.fromkeys(contracts.DIMENSIONS, "PASS")
    assert evaluator.classification(rows, None) == "MODEL_QUALITY_PROMISING"
    rows[5]["dimensions"]["TEST_STRENGTH"] = "FAIL"
    assert evaluator.classification(rows, None) == "MODEL_QUALITY_INSUFFICIENT"
    assert evaluator.classification(rows, "TOOL_FAILURE") == "RESULT_INCONCLUSIVE"
    assert evaluator.classification([], None) == "EVALUATION_INCOMPLETE"


def test_transfer_manifest_and_notebook() -> None:
    assert len(package.identity()) == 64
    notebook = json.loads((package.SOURCE / "kaggle_quality.ipynb").read_text())
    code = "".join(notebook["cells"][1]["source"])
    assert "AUTHORIZED = False" in code
    assert notebook["cells"][1]["outputs"] == []
    assert "timeout=6000" in code


def test_tampered_package_rejected(tmp_path: Path) -> None:
    (tmp_path / "manifest.json").write_text('{"evaluation_version":"wrong","files":{}}')
    with pytest.raises(contracts.Rejected):
        package.identity(tmp_path)


def test_fixed_schema_pins() -> None:
    schema = json.loads((package.SOURCE / "result.schema.json").read_text())
    properties = schema["properties"]
    assert properties["thresholds"]["const"] == contracts.THRESHOLDS
    assert properties["classification"]["enum"] == list(contracts.CLASSIFICATIONS)
    assert properties["model_revision"]["const"] == contracts.REVISION
    assert properties["total_model_calls"]["maximum"] == contracts.CALL_LIMIT


@pytest.mark.parametrize("second_fails", [False, True])
def test_exactly_one_feedback_attempt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, second_fails: bool
) -> None:
    prompts: list[str] = []

    class ReplayWorker:
        def __init__(self) -> None:
            self.calls = 0
            self.runtime: dict[str, Any] = {}

        def start(self) -> None:
            pass

        def generate(self, content: str) -> str:
            prompts.append(content)
            self.calls += 1
            return "synthetic replay"

        def close(self) -> None:
            pass

    def scoring(
        case: Case, raw: str, *, rework: bool = False
    ) -> tuple[dict[str, Any], dict[str, str]]:
        row = evaluator.empty_result(case)
        row["dimensions"] = dict.fromkeys(contracts.DIMENSIONS, "PASS")
        if case.rework and (not rework or second_fails):
            row["failures"] = ["ORACLE_FAILED"]
            row["dimensions"]["TASK_CORRECTNESS"] = "FAIL"
        return row, {"subject.py": case.reference}

    def reviewer(case: Case, raw: str) -> dict[str, Any]:
        return scoring(case, raw)[0]

    monkeypatch.setattr(quality_probe, "Worker", ReplayWorker)
    monkeypatch.setattr(quality_probe, "score_coding", scoring)
    monkeypatch.setattr(quality_probe, "score_review", reviewer)
    result = quality_probe.run(tmp_path / "new-result")
    validate_result(result)
    assert result["total_model_calls"] == 11
    assert len(prompts) == 11
    assert "ORACLE_FAILED" in prompts[7]
    assert "single rework" in prompts[7]
    assert len(result["scenarios"][6]["attempts"]) == 2
    assert result["scenarios"][6]["dimensions"]["REWORK_QUALITY"] == (
        "FAIL" if second_fails else "PASS"
    )
    result["secret"] = "must never enter exported artifacts"
    with pytest.raises(contracts.Rejected, match="RESULT_SCHEMA_INVALID"):
        validate_result(result)


def test_infrastructure_failure_is_not_weak_model(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def broken_start(self: quality_probe.Worker) -> None:
        raise contracts.Rejected("MODEL_LOAD_FAILED")

    monkeypatch.setattr(quality_probe.Worker, "start", broken_start)
    result = quality_probe.run(tmp_path / "failed-result")
    assert result["classification"] == "RESULT_INCONCLUSIVE"
    assert result["total_model_calls"] == 0
    assert len(result["plan"]) == 10
    validate_result(result)


def test_collection_error_never_counts_as_test_strength(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def tool_error(root: Path, filename: str) -> int:
        raise contracts.Rejected("TOOL_FAILURE")

    monkeypatch.setattr(evaluator, "pytest", tool_error)
    result, _ = evaluator.score_coding(CASES[0], proposal(CASES[0]))
    assert "TOOL_FAILURE" in result["failures"]
    assert result["dimensions"]["TEST_STRENGTH"] != "PASS"


def test_call_limit_refuses_before_transport() -> None:
    worker = quality_probe.Worker()
    worker.calls = contracts.CALL_LIMIT
    with pytest.raises(contracts.Rejected, match="CALL_LIMIT"):
        worker.generate("synthetic")
    assert worker.calls == contracts.CALL_LIMIT


def test_environment_never_inherits_credentials(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HF_TOKEN", "synthetic-canary-not-a-credential")
    monkeypatch.delenv("LD_LIBRARY_PATH", raising=False)
    values = quality_probe.environment(tmp_path)
    assert "HF_TOKEN" not in values
    assert "synthetic-canary-not-a-credential" not in values.values()
    assert values["HF_HUB_OFFLINE"] == "1"
    assert values["TRANSFORMERS_OFFLINE"] == "1"


def test_reviewer_vacuity_rubric_has_positive_and_negative_controls() -> None:
    value = review_value(bad=True)
    finding = value["findings"][0]
    finding["category"] = "testing"
    finding["message"] = "Equal inputs make this test pass both implementations"
    finding["required_action"] = "Add an unequal regression case such as 1, 4"
    result = evaluator.score_review(CASES[9], json.dumps(value))
    assert result["dimensions"]["REVIEW_ACCURACY"] == "PASS"
    finding["required_action"] = "Leave everything unchanged"
    result = evaluator.score_review(CASES[9], json.dumps(value))
    assert result["dimensions"]["REVIEW_ACCURACY"] == "FAIL"


def test_packager_exports_only_frozen_files(tmp_path: Path) -> None:
    import zipfile

    destination = tmp_path / "synthetic.zip"
    assert package.build(destination) == package.identity()
    with zipfile.ZipFile(destination) as archive:
        assert set(archive.namelist()) == {
            "forgeai_model_quality_1/" + name
            for name in (*package.FILES, "manifest.json")
        }
        assert all(info.file_size <= 131072 for info in archive.infolist())


@pytest.mark.parametrize("separator", ["\n", "\r\n"])
def test_adr021_line_endings(separator: str) -> None:
    raw = separator.join(("```json", proposal(CASES[0]), "```"))
    assert contracts.coding(raw, CASES[0].targets)[1] is False


def test_rejected_python_cannot_skip_required_test_strength() -> None:
    value = json.loads(proposal(CASES[0]))
    value["changes"][0]["content"] = "import os\n"
    row, _ = evaluator.score_coding(CASES[0], json.dumps(value))
    assert "PYTHON_SUBSET_REJECTED" in row["failures"]
    assert row["dimensions"]["TEST_STRENGTH"] == "FAIL"
