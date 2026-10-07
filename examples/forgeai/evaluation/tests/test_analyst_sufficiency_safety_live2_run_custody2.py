"""FORGEAI-ANALYST-SUFFICIENCY-SAFETY-LIVE-2-RUN-CUSTODY-2.

Exact admission of the first live/2 BASELINE and two retained zero-call
PREFLIGHTs. Offline only: Git reads, no provider, no model, no run.
"""

import json
import os
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from analyst_design_live1.identity import git
from analyst_sufficiency_safety_eval2 import data as eval2
from analyst_sufficiency_safety_eval3 import data as eval3
from analyst_sufficiency_safety_live2 import custody, identity

ROOT = Path(__file__).resolve().parents[4]
BASE = "9a56a0d"  # SAFETY-EVAL-3 qualification recorded
BASELINE = "safety2-baseline-3cf8aba9a377"
NESTED = (
    "evaluation/safety2-preflight-20261007-01",
    "evaluation/safety2-preflight-20261007-a",
)
PRIOR = {
    "live1-smoke-d59e9c3f030b": "8cef1bea232463de78afca2a01cb11056ec85913",
    "live1-smoke-227bdd3cec0b": "a19b5c191da4b63c298f22e71ca0ae418ae84df7",
    "live1-smoke-bf448d5a12b3": "54494f60b828102452257c1010f19f4688dfb8f9",
    "live1-preflight-411899d3f557": "89f79532512b954c8ae3b2630a06a9e5eef18b7d",
    "live1-preflight-9bdb9f5867b6": "164fd09c88848877c81bd12e339d94e1cab5f2d4",
    "live1-preflight-a9e59b9f3773": "bf9c71dc7f2b406d9c027cdd2d84688917945a49",
    "safety1-preflight-c80435f8dadc": "be52fc954ed30e980ab85db7ea83692389581899",
    "safety2-preflight-300452037205": "5f5f49375b83b9fca58873ea9f15e3f9b409840b",
}

pytestmark = pytest.mark.skipif(
    os.environ.get("FORGEAI_LIVE1_OFFLINE") != "1",
    reason="requires the FORGEAI_LIVE1_OFFLINE=1 provider fence",
)


def report(directory: str) -> dict[str, Any]:
    value: dict[str, Any] = json.loads(
        git("show", f"HEAD:examples/forgeai/{directory}/report.json")
    )
    return value


def wrap(
    *,
    tree: dict[str, str] | None = None,
    status: dict[str, str] | None = None,
    untracked: str = "",
    ignored: str = "",
) -> Callable[..., str]:
    """The real repository with targeted overrides (no file is touched)."""

    def repository(*args: str) -> str:
        target = args[-1].split("examples/forgeai/", 1)[-1]
        if args[0] == "rev-parse" and tree and target in tree:
            return tree[target]
        if args[0] == "status" and "--ignored" in args:
            return git(*args) + ("\n" + ignored if ignored else "")
        if args[0] == "status" and status and target in status:
            return status[target]
        if (
            args[0] == "ls-files"
            and untracked
            and args[-1] == "examples/forgeai/evaluation/"
        ):
            return git(*args) + "\n" + untracked
        if args[0] == "ls-files" and untracked and args[-1] == "examples/forgeai/":
            return git(*args) + "\n" + untracked
        return git(*args)

    return repository


def git_(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout


# 1-10 baseline


def test_baseline_directory_admitted() -> None:
    result = custody.verify(git)
    assert BASELINE in result["directories"]
    assert result["baseline"]["run_id"] == "69bcc2f3-9c5a-4489-b999-8bc6ee1c4046"


def test_baseline_exact_tree_required() -> None:
    assert custody.ARTIFACTS[BASELINE] == custody.BASELINE2["tree"]
    assert (
        git("rev-parse", f"HEAD:examples/forgeai/{BASELINE}")
        == custody.BASELINE2["tree"]
    )
    with pytest.raises(ValueError, match="RUN_DIRECTORY_CHANGED"):
        custody.verify(wrap(tree={BASELINE: "1" * 40}))


def test_one_byte_baseline_change_rejected() -> None:
    with pytest.raises(ValueError, match="RUN_DIRECTORY_MODIFIED"):
        custody.verify(
            wrap(status={BASELINE: f" M examples/forgeai/{BASELINE}/report.json"})
        )


def test_extra_baseline_file_rejected() -> None:
    with pytest.raises(ValueError, match="RUN_DIRECTORY_MODIFIED"):
        custody.verify(
            wrap(status={BASELINE: f"?? examples/forgeai/{BASELINE}/extra.json"})
        )
    assert (
        len(
            git(
                "ls-tree", "--name-only", "HEAD", f"examples/forgeai/{BASELINE}/"
            ).split()
        )
        == 267
    )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("run_id", "00000000-0000-0000-0000-000000000000"),
        ("mode", "PREFLIGHT"),
        ("decision", {"code": "F", "label": "SAFETY CANDIDATE ACCEPTABLE"}),
        ("run_completeness", "INCOMPLETE"),
        ("calls", 23),
        ("condition", "forgeai-analyst-sufficiency-safety-live/1"),
    ],
)
def test_baseline_report_fields_checked(field: str, value: Any) -> None:
    custody.baseline(report(BASELINE))
    with pytest.raises(ValueError, match="BASELINE2_ARTIFACT_MISMATCH"):
        custody.baseline({**report(BASELINE), field: value})


def test_baseline_run_uuid_checked() -> None:
    assert report(BASELINE)["run_id"] == custody.BASELINE2["run_id"]


def test_baseline_mode_checked() -> None:
    assert report(BASELINE)["mode"] == "BASELINE"


def test_baseline_decision_g_checked() -> None:
    assert report(BASELINE)["decision"] == {
        "code": "G",
        "label": "AUTHORITY SAFETY FAILURE",
    }


def test_baseline_completeness_checked() -> None:
    r = report(BASELINE)
    assert r["run_completeness"] == "COMPLETE"
    assert (r["planned"], r["attempted"], r["completed"]) == (22, 22, 22)


def _metric(name: str, value: Any) -> dict[str, Any]:
    r = report(BASELINE)
    return {**r, "metrics": {**r["metrics"], name: value}}


def test_baseline_authority_count_checked() -> None:
    assert report(BASELINE)["metrics"]["authority_violations"] == 1
    with pytest.raises(ValueError, match="BASELINE2"):
        custody.baseline(_metric("authority_violations", 0))


def test_baseline_critical_progression_count_checked() -> None:
    assert report(BASELINE)["metrics"]["critical_false_sufficient_progression"] == 4
    with pytest.raises(ValueError, match="BASELINE2"):
        custody.baseline(_metric("critical_false_sufficient_progression", 0))


def test_baseline_no_retry_recorded() -> None:
    r = report(BASELINE)
    cases = [x["case"] for x in r["records"]]
    assert cases == [f"s{i:02}" for i in range(1, 23)]
    assert [t["case"] for t in r["timings"]] == cases
    with pytest.raises(ValueError, match="BASELINE2"):
        custody.baseline({**r, "timings": [*r["timings"], r["timings"][0]]})


# 11-17 nested preflights and admission boundaries


def test_first_retained_preflight_admitted() -> None:
    expected = custody.RETAINED[0]
    assert expected["directory"] == NESTED[0]
    assert expected["run_id"] == "bdbcfa91-0499-42f1-91f1-fdc72d6c3ab1"
    custody.preflight(report(NESTED[0]), expected, "RETAINED_PREFLIGHT")
    assert NESTED[0] in custody.verify(git)["directories"]


def test_second_retained_preflight_admitted() -> None:
    expected = custody.RETAINED[1]
    assert expected["directory"] == NESTED[1]
    assert expected["run_id"] == "002b8ba7-6569-48cc-99ce-4387a1bf20e9"
    custody.preflight(report(NESTED[1]), expected, "RETAINED_PREFLIGHT")
    assert NESTED[1] in custody.verify(git)["directories"]


def test_each_nested_preflight_has_own_tree() -> None:
    trees = [custody.ARTIFACTS[n] for n in NESTED]
    assert len(set(trees)) == 2
    for name in NESTED:
        assert (
            git("rev-parse", f"HEAD:examples/forgeai/{name}") == custody.ARTIFACTS[name]
        )
    # The two are not interchangeable: each report is checked against its own pin.
    with pytest.raises(ValueError, match="RETAINED_PREFLIGHT"):
        custody.preflight(report(NESTED[0]), custody.RETAINED[1], "RETAINED_PREFLIGHT")


def test_mutated_nested_preflight_rejected() -> None:
    with pytest.raises(ValueError, match="RUN_DIRECTORY_CHANGED"):
        custody.verify(wrap(tree={NESTED[1]: "2" * 40}))
    with pytest.raises(ValueError, match="RETAINED_PREFLIGHT"):
        custody.preflight(
            {**report(NESTED[0]), "calls": 1}, custody.RETAINED[0], "RETAINED_PREFLIGHT"
        )


@pytest.mark.parametrize(
    "extra",
    [
        "examples/forgeai/evaluation/safety2-preflight-20261009-02/",
        "examples/forgeai/evaluation/safety2-baseline-0123456789ab/",
        "examples/forgeai/evaluation/live1-smoke-xyz/",
    ],
)
def test_arbitrary_nested_run_directory_rejected(extra: str) -> None:
    with pytest.raises(ValueError, match="UNRECOGNIZED_OR_MISSING"):
        custody.verify(wrap(untracked=extra))


@pytest.mark.parametrize(
    "extra",
    [
        "examples/forgeai/safety2-baseline-0123456789ab/",
        "examples/forgeai/safety2-baseline-second-run/",
    ],
)
def test_arbitrary_top_level_baseline_rejected(extra: str) -> None:
    with pytest.raises(ValueError, match="UNRECOGNIZED_OR_MISSING"):
        custody.verify(wrap(untracked=extra))


def test_wildcard_admission_absent() -> None:
    assert not any(set("*?[") & set(k) for k in custody.ARTIFACTS)
    assert all(len(v) == 40 for v in custody.ARTIFACTS.values())
    assert custody.LOCATIONS == ("", "evaluation")
    # Evaluator packages and fixtures are never mistaken for runs.
    for name in (
        "analyst_sufficiency_safety_eval3",
        "analyst_design_live1",
        "tests",
        "lq1-baseline",
        "lq1-baseline-llama3.2",
        "amc1-smoke-qwen2.5-coder-14b",
    ):
        assert not custody.is_run_directory(name)
    assert (
        custody._relative("examples/forgeai/evaluation/tests/safety2-preflight-x/")
        is None
    )


# 18-22 historical pins and failure modes


def test_existing_historical_pins_unchanged() -> None:
    assert {k: custody.ARTIFACTS[k] for k in PRIOR} == PRIOR
    assert len(custody.ARTIFACTS) == len(PRIOR) + 3
    for name, tree in PRIOR.items():
        assert git("rev-parse", f"HEAD:examples/forgeai/{name}") == tree


def test_successful_original_live2_preflight_still_accepted() -> None:
    custody.preflight(report("safety2-preflight-300452037205"))
    assert "safety2-preflight-300452037205" in custody.verify(git)["directories"]


def test_live1_refusal_still_accepted() -> None:
    r = report("safety1-preflight-c80435f8dadc")
    assert r["stop_reason"] == "RUNTIME_IDENTITY_REVIEW_REQUIRED" and r["calls"] == 0
    assert "safety1-preflight-c80435f8dadc" in custody.verify(git)["directories"]


def test_ignored_live_evidence_rejected() -> None:
    assert not custody.ignored_run_directories(git)
    for line in (
        f"!! examples/forgeai/{BASELINE}/",
        "!! examples/forgeai/evaluation/safety2-preflight-20261007-a/",
        "!! examples/forgeai/safety2-preflight-unpinned-run/",
    ):
        with pytest.raises(ValueError, match="IGNORED_RUN_DIRECTORY"):
            custody.verify(wrap(ignored=line))
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert "safety2-baseline" not in gitignore and "safety2-preflight" not in gitignore


def test_committed_working_tree_mismatch_rejected() -> None:
    for name in (BASELINE, *NESTED):
        assert (
            git_("diff", "--name-only", "HEAD", "--", f"examples/forgeai/{name}") == ""
        )
        with pytest.raises(ValueError, match="RUN_DIRECTORY_MODIFIED"):
            custody.verify(wrap(status={name: f" M examples/forgeai/{name}/run.json"}))


# 23-28 seals and offline guarantees


def test_safety_eval3_unchanged() -> None:
    eval3.freeze()
    path = "examples/forgeai/evaluation/analyst_sufficiency_safety_eval3"
    assert git_("diff", "--name-only", BASE, "--", path) == ""
    assert git_("status", "--porcelain", "--", path) == ""


def test_safety_eval2_unchanged() -> None:
    eval2.freeze()
    path = "examples/forgeai/evaluation/analyst_sufficiency_safety_eval2"
    assert git_("diff", "--name-only", BASE, "--", path) == ""
    assert git_("status", "--porcelain", "--", path) == ""


def test_live2_semantic_identity_unchanged() -> None:
    recorded = report("safety2-preflight-300452037205")["provenance"]
    current = identity.binding()
    assert [k for k in current if current[k] != recorded.get(k)] == ["harness_sources"]
    changed = [
        n
        for n, v in current["harness_sources"].items()
        if recorded["harness_sources"].get(n) != v
    ]
    assert changed == ["custody.py"]
    assert current["ollama_version"] == "0.40.0"
    assert current["model_digest"] == custody.MODEL_DIGEST


def test_zero_provider_model_calls() -> None:
    assert os.environ["FORGEAI_LIVE1_OFFLINE"] == "1"
    source = Path(str(custody.__file__)).read_text(encoding="utf-8")
    imports = [x for x in source.splitlines() if x.startswith(("import ", "from "))]
    assert imports == [
        "import json",
        "import re",
        "from collections.abc import Callable",
        "from typing import Any",
    ]  # Git reads through the caller's repository function only


def test_no_baseline_rerun() -> None:
    runs = custody.run_directories(git)
    assert sorted(d for d in runs if "-baseline-" in d) == [BASELINE]
    assert (
        git_("log", "--format=%h", "-1", "--", f"examples/forgeai/{BASELINE}").strip()
        == "ade5d97"
    )


def test_no_evaluator_run() -> None:
    runs = custody.run_directories(git)
    assert not [d for d in runs if "safety3" in d or "eval3" in d]
    assert set(runs) == set(custody.ARTIFACTS)
