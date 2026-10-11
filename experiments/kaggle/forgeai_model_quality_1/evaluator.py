"""Deterministic fixture checks and separate dimensions; no model judgement."""

from __future__ import annotations

import ast
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from .contracts import DIMENSIONS, THRESHOLDS, Rejected, coding, review
from .result_contract import validate_result
from .safety import admitted
from .scenarios import Case

CHECK_SECONDS = 30
CHECK_ENV = {
    "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
    "PYTHONDONTWRITEBYTECODE": "1",
    "PYTHONHASHSEED": "0",
}


def check(root: Path, module: str, arguments: list[str]) -> int:
    """Fixed tool names/arguments only; output is discarded, not echoed or fed back."""
    if module not in {"pytest", "ruff", "mypy"}:
        raise Rejected("TOOL_FAILURE")
    environment = dict(CHECK_ENV)
    # Windows CPython needs the system installation root, never other ambient data.
    if os.name == "nt" and "SystemRoot" in os.environ:
        environment["SystemRoot"] = os.environ["SystemRoot"]
    try:
        result = subprocess.run(
            [sys.executable, "-m", module, *arguments],
            cwd=root,
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=CHECK_SECONDS,
            check=False,
        )
    except subprocess.TimeoutExpired:
        raise Rejected("TOOL_TIMEOUT") from None
    except OSError:
        raise Rejected("TOOL_FAILURE") from None
    if result.returncode not in {0, 1}:
        raise Rejected("TOOL_FAILURE")
    return result.returncode


def pytest(root: Path, filename: str) -> int:
    return check(
        root, "pytest", ["-q", "-p", "no:cacheprovider", "-c", "pytest.ini", filename]
    )


def oracle_source(case: Case) -> str:
    lines = ["from subject import solve", "", "", "def test_oracle() -> None:"]
    for arguments, expected in case.oracle:
        values = ", ".join(str(argument) for argument in arguments)
        lines.append(f"    assert solve({values}) == {expected}")
    return "\n".join(lines) + "\n"


def empty_result(case: Case) -> dict[str, Any]:
    dimensions = dict.fromkeys(DIMENSIONS, "NOT_APPLICABLE")
    # An applicable gate cannot become N/A merely because earlier admission
    # failed. FAIL means its required proof has not been established.
    dimensions["CONTRACT_VALIDITY"] = "FAIL"
    if case.strength:
        dimensions["TEST_STRENGTH"] = "FAIL"
    if case.context:
        dimensions["CONTEXT_USE"] = "FAIL"
    if case.rework:
        dimensions["REWORK_QUALITY"] = "FAIL"
    if case.review_kind:
        dimensions["REVIEW_ACCURACY"] = "FAIL"
    return {
        "scenario": case.name,
        "role": "reviewer" if case.review_kind else "coding",
        "dimensions": dimensions,
        "failures": [],
        "attempts": [],
        "raw_json": None,
        "false_positive": None,
        "false_negative": None,
    }


def score_review(case: Case, raw: str) -> dict[str, Any]:
    result = empty_result(case)
    dimensions = result["dimensions"]
    try:
        value, result["raw_json"] = review(raw, {"proposal", "requirements"})
    except Rejected as exc:
        dimensions["CONTRACT_VALIDITY"] = "FAIL"
        result["failures"].append(str(exc))
        return result
    dimensions["CONTRACT_VALIDITY"] = "PASS"
    findings = value["findings"]
    if case.review_kind == "good":
        passed = value["decision"] == "accept" and not findings
        result["false_positive"] = bool(findings)
        result["false_negative"] = False
    else:
        # Semantic truth is anchored by literal counterexamples, not LLM grading.
        # The action must name the affected object, not just be nonblank.
        category = case.review_kind
        message_words = (
            ("inclusive", "equal", "off-by-one")
            if category == "correctness"
            else ("vacuous", "equal", "both", "defect")
        )
        action_words = (
            ("1", "one", "inclusive")
            if category == "correctness"
            else ("unequal", "negative", "less", "1, 4", "regression")
        )
        relevant = [
            item
            for item in findings
            if item["severity"] == "blocking"
            and item["category"] == category
            and "proposal" in item["evidence_refs"]
            and any(word in item["message"].lower() for word in message_words)
            and any(word in item["required_action"].lower() for word in action_words)
        ]
        passed = (
            value["decision"] == "changes_required"
            and len(relevant) == 1
            and len(findings) == 1
        )
        result["false_negative"] = not relevant
        result["false_positive"] = len(findings) != len(relevant)
    dimensions["REVIEW_ACCURACY"] = "PASS" if passed else "FAIL"
    if not passed:
        result["failures"].append("REVIEW_ORACLE_MISMATCH")
    return result


def score_coding(
    case: Case, raw: str, *, rework: bool = False
) -> tuple[dict[str, Any], dict[str, str]]:
    result = empty_result(case)
    dimensions = result["dimensions"]
    files: dict[str, str] = {}
    targets = {path: "update" if rework else op for path, op in case.targets.items()}
    try:
        files, result["raw_json"] = coding(raw, targets)
        dimensions["CONTRACT_VALIDITY"] = "PASS"
        dimensions["SCOPE_DISCIPLINE"] = "PASS"
        if set(files) != set(targets):
            raise Rejected("MISSING_REQUIRED_CHANGE")
        trees = {
            path: admitted(content, test=path == "test_candidate.py")
            for path, content in files.items()
        }
        if case.context:
            dimensions["CONTEXT_USE"] = "PASS"
        if case.name == "CREATE_WITH_CONTEXT":
            tree = trees["subject.py"]
            function = next(
                item for item in tree.body if isinstance(item, ast.FunctionDef)
            )
            if (
                ast.get_docstring(tree) != "Synthetic counters."
                or ast.get_docstring(function) != "Clamp a counter."
            ):
                dimensions["CONTEXT_USE"] = "FAIL"
                result["failures"].append("CONTEXT_MISMATCH")
        with tempfile.TemporaryDirectory(prefix="synthetic-quality-") as directory:
            root = Path(directory)
            (root / "pytest.ini").write_text("[pytest]\n", encoding="utf-8")
            (root / "mypy.ini").write_text("[mypy]\nstrict = True\n", encoding="utf-8")
            for path, content in files.items():
                (root / path).write_text(content, encoding="utf-8")
            (root / "test_oracle.py").write_text(oracle_source(case), encoding="utf-8")
            correct = pytest(root, "test_oracle.py") == 0
            dimensions["TASK_CORRECTNESS"] = "PASS" if correct else "FAIL"
            if case.name == "SCOPE_TRAP" and not correct:
                dimensions["CONTEXT_USE"] = "FAIL"
                result["failures"].append("CONTEXT_MISMATCH")
            lint = (
                check(
                    root,
                    "ruff",
                    [
                        "check",
                        "--isolated",
                        "--target-version",
                        "py310",
                        "--select",
                        "E4,E7,E9,F,B",
                        *files,
                    ],
                )
                == 0
            )
            typing = (
                check(
                    root,
                    "mypy",
                    ["--config-file", "mypy.ini", "--no-incremental", *files],
                )
                == 0
            )
            dimensions["STATIC_QUALITY"] = "PASS" if lint and typing else "FAIL"
            if not correct:
                result["failures"].append("ORACLE_FAILED")
            if not lint:
                result["failures"].append("RUFF_FINDING")
            if not typing:
                result["failures"].append("MYPY_FINDING")
            if case.strength:
                candidate_pass = pytest(root, "test_candidate.py") == 0
                (root / "subject.py").write_text(case.original, encoding="utf-8")
                original_pass = pytest(root, "test_candidate.py") == 0
                strong = candidate_pass and not original_pass
                dimensions["TEST_STRENGTH"] = "PASS" if strong else "FAIL"
                if not strong:
                    result["failures"].append(
                        "VACUOUS_TEST" if candidate_pass else "CANDIDATE_TEST_FAILED"
                    )
    except Rejected as exc:
        reason = str(exc)
        result["failures"].append(reason)
        if dimensions["CONTRACT_VALIDITY"] != "PASS":
            dimensions["CONTRACT_VALIDITY"] = "FAIL"
        if reason == "SCOPE_VIOLATION":
            dimensions["SCOPE_DISCIPLINE"] = "FAIL"
        for dimension in ("TASK_CORRECTNESS", "STATIC_QUALITY"):
            dimensions[dimension] = "FAIL"
    return result, files


def classification(results: list[dict[str, Any]], failure: str | None) -> str:
    if failure == "OUTPUT_LIMIT":
        return "MODEL_CONTRACT_UNSTABLE"
    if failure is not None:
        return "RESULT_INCONCLUSIVE"
    if len(results) != 10:
        return "EVALUATION_INCOMPLETE"
    if any(
        any(code in {"TOOL_FAILURE", "TOOL_TIMEOUT"} for code in row["failures"])
        for row in results
    ):
        return "RESULT_INCONCLUSIVE"
    dimensions = [row["dimensions"] for row in results]
    if any(row["CONTRACT_VALIDITY"] != "PASS" for row in dimensions):
        return "MODEL_CONTRACT_UNSTABLE"
    if any("REWORK_NOT_EXERCISED" in row["failures"] for row in results):
        return "EVALUATION_INCOMPLETE"
    required = (
        "SCOPE_DISCIPLINE",
        "CONTEXT_USE",
        "TEST_STRENGTH",
        "REVIEW_ACCURACY",
        "REWORK_QUALITY",
    )
    if any(row[key] == "FAIL" for row in dimensions for key in required):
        return "MODEL_QUALITY_INSUFFICIENT"
    for dimension, threshold in (
        ("TASK_CORRECTNESS", "coding_correct_minimum"),
        ("STATIC_QUALITY", "static_quality_minimum"),
    ):
        if sum(row[dimension] == "PASS" for row in dimensions) < THRESHOLDS[threshold]:
            return "MODEL_QUALITY_INSUFFICIENT"
    return "MODEL_QUALITY_PROMISING"


def artifacts(result: dict[str, Any], destination: Path) -> None:
    validate_result(result)
    encoded = json.dumps(result, indent=2, allow_nan=False) + "\n"
    if len(encoded.encode()) > 131072:
        raise Rejected("RESULT_LIMIT")
    lines = [
        "# Bounded synthetic coding quality",
        "",
        f"Classification: {result['classification']}",
        f"Model: {result['model_id']} @ {result['model_revision']}",
        f"Package: {result['package_digest']}",
        f"Calls: {result['total_model_calls']}/11",
        f"Runtime: {json.dumps(result['runtime'], sort_keys=True)}",
        "",
        "| Scenario | " + " | ".join(DIMENSIONS) + " | Failures |",
        "|---|" + "---|" * (len(DIMENSIONS) + 1),
    ]
    for row in result["scenarios"]:
        cells = [row["scenario"], *(row["dimensions"][key] for key in DIMENSIONS)]
        cells.append(", ".join(row["failures"]))
        lines.append("| " + " | ".join(cells) + " |")
    lines += [
        "",
        "Rework attempts, prompt/output digests and timing are in the JSON record.",
        "Reviewer matching is a conservative lexical rubric, not proof of reasoning.",
        "This tiny scalar language does not measure arbitrary Python or repositories.",
        "Larger context and in-process generation are unqualified runtime variations.",
        "No production, commercial, unattended mutation, connectivity or "
        "availability qualification.",
        "No local 7B/14B comparison was performed; future baselines are separate.",
    ]
    destination.mkdir(parents=True, exist_ok=True)
    for name, content in (
        ("forgeai_kaggle_quality_result.json", encoded),
        ("forgeai_kaggle_quality_report.md", "\n".join(lines) + "\n"),
    ):
        with (destination / name).open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(content)
