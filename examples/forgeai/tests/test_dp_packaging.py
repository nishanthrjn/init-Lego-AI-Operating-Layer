"""Pure DP gate contracts; no subprocesses, models, builds or Docker."""

import json
from pathlib import Path

import pytest
from validate_forgeai_v0_2_dp_1 import acceptance_report, require_real_results

SUMMARY = "repository guidance: discovered (read-only; confirm below)"
HEADER = "ForgeAI v0.1: supervised local engineering task"


def report(rework: bool = False, /, **updates: object) -> str:
    value: dict[str, object] = {
        "disposition": "SUCCEEDED",
        "model_quality": "NOT_APPLICABLE_REPLAY",
        "rework_used": rework,
    }
    value.update(updates)
    return "forgeai-report: " + json.dumps(value)


@pytest.mark.parametrize("scenario", ["accept", "rework"])
def test_success_requires_final_replay_report(scenario: str) -> None:
    line = report(scenario == "rework")
    prefix = [SUMMARY, HEADER] if scenario == "accept" else [HEADER]
    assert acceptance_report("\n".join([*prefix, line]) + "\n", scenario) == line


@pytest.mark.parametrize(
    "updates",
    [
        {"disposition": "FAILED"},
        {"model_quality": "UNQUALIFIED"},
        {"rework_used": True},
        {"rework_used": 0},
    ],
)
def test_wrong_outcome_never_qualifies(updates: dict[str, object]) -> None:
    with pytest.raises(ValueError, match="required replay outcome"):
        acceptance_report("\n".join([SUMMARY, HEADER, report(**updates)]), "accept")


def test_rework_must_have_used_rework() -> None:
    with pytest.raises(ValueError, match="required replay outcome"):
        acceptance_report(report(), "rework")


@pytest.mark.parametrize(
    "prefix",
    [
        [HEADER],
        [HEADER, SUMMARY],
        [SUMMARY, SUMMARY, HEADER],
        [SUMMARY],
    ],
)
def test_guidance_summary_is_required_once_before_header(prefix: list[str]) -> None:
    with pytest.raises(ValueError, match="one guidance summary before"):
        acceptance_report("\n".join([*prefix, report()]), "accept")


@pytest.mark.parametrize("suffix", ["", "duplicate", "trailing", "invalid", "array"])
def test_missing_duplicate_nonfinal_or_malformed_report_is_rejected(
    suffix: str,
) -> None:
    lines = [SUMMARY, HEADER]
    if suffix == "duplicate":
        lines += [report(), report()]
    elif suffix == "trailing":
        lines += [report(), "unexpected trailing output"]
    elif suffix == "invalid":
        lines += ["forgeai-report: not JSON"]
    elif suffix == "array":
        lines += ["forgeai-report: []"]
    with pytest.raises(ValueError):
        acceptance_report("\n".join(lines), "accept")


def test_real_results_require_executed_passes(tmp_path: Path) -> None:
    path = tmp_path / "results.xml"
    path.write_text(
        '<testsuites><testsuite><testcase name="passed"/></testsuite></testsuites>',
        encoding="utf-8",
    )
    require_real_results(path)


@pytest.mark.parametrize("outcome", ["skipped", "failure", "error", "empty"])
def test_empty_or_nonpassing_real_results_never_qualify(
    tmp_path: Path, outcome: str
) -> None:
    path = tmp_path / "results.xml"
    case = "" if outcome == "empty" else f"<testcase><{outcome}/></testcase>"
    path.write_text(
        f"<testsuites><testsuite>{case}</testsuite></testsuites>", encoding="utf-8"
    )
    with pytest.raises(ValueError, match="executed, passing tests with no skips"):
        require_real_results(path)
