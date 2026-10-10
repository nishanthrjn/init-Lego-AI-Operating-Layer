"""FORGEAI-ANALYST-SUFFICIENCY-SAFETY-LIVE-2-PREFLIGHT-CUSTODY-1.

Exact admission of the committed live/2 PREFLIGHT directory. Offline only:
Git reads, no provider, no model, no run.
"""

import json
import os
from collections.abc import Callable
from typing import Any

import pytest
from analyst_design_live1.identity import git
from analyst_sufficiency_safety_live2 import custody

DIRECTORY = "safety2-preflight-300452037205"
TREE = "5f5f49375b83b9fca58873ea9f15e3f9b409840b"
RUN = "8b147424-5231-4758-9e0f-05730f6174bc"
PRIOR = {
    "live1-smoke-d59e9c3f030b": "8cef1bea232463de78afca2a01cb11056ec85913",
    "live1-smoke-227bdd3cec0b": "a19b5c191da4b63c298f22e71ca0ae418ae84df7",
    "live1-smoke-bf448d5a12b3": "54494f60b828102452257c1010f19f4688dfb8f9",
    "live1-preflight-411899d3f557": "89f79532512b954c8ae3b2630a06a9e5eef18b7d",
    "live1-preflight-9bdb9f5867b6": "164fd09c88848877c81bd12e339d94e1cab5f2d4",
    "live1-preflight-a9e59b9f3773": "bf9c71dc7f2b406d9c027cdd2d84688917945a49",
    "safety1-preflight-c80435f8dadc": "be52fc954ed30e980ab85db7ea83692389581899",
}

pytestmark = pytest.mark.skipif(
    os.environ.get("FORGEAI_LIVE1_OFFLINE") != "1",
    reason="requires the FORGEAI_LIVE1_OFFLINE=1 provider fence",
)


def report() -> dict[str, Any]:
    value: dict[str, Any] = json.loads(
        git("show", f"HEAD:examples/forgeai/{DIRECTORY}/report.json")
    )
    return value


def wrap(
    rev_parse: dict[str, str] | None = None,
    status: dict[str, str] | None = None,
    untracked: str = "",
    show: Callable[[str], str] | None = None,
) -> Callable[..., str]:
    def repository(*args: str) -> str:
        name = args[-1].rsplit("/", 1)[-1]
        if args[0] == "rev-parse" and rev_parse and name in rev_parse:
            return rev_parse[name]
        if args[0] == "status" and status and name in status:
            return status[name]
        if args[0] == "ls-files" and untracked:
            return git(*args) + "\n" + untracked
        if args[0] == "show" and show is not None:
            return show(args[1])
        return git(*args)

    return repository


def test_new_live2_preflight_directory_is_accepted() -> None:
    result = custody.verify(git)
    assert DIRECTORY in result["directories"]
    assert result["preflight"]["run_id"] == RUN


def test_exact_tree_id_required() -> None:
    assert custody.ARTIFACTS[DIRECTORY] == TREE == custody.PREFLIGHT2["tree"]
    assert git("rev-parse", f"HEAD:examples/forgeai/{DIRECTORY}") == TREE
    with pytest.raises(ValueError, match="RUN_DIRECTORY_CHANGED"):
        custody.verify(wrap(rev_parse={DIRECTORY: "1" * 40}))


def test_one_byte_modification_rejected() -> None:
    # A committed one-byte change yields another tree id; an uncommitted one
    # shows in the working tree. Both refuse.
    with pytest.raises(ValueError, match="RUN_DIRECTORY_CHANGED"):
        custody.verify(wrap(rev_parse={DIRECTORY: TREE[:-1] + "0"}))
    with pytest.raises(ValueError, match="RUN_DIRECTORY_MODIFIED"):
        custody.verify(
            wrap(status={DIRECTORY: f" M examples/forgeai/{DIRECTORY}/run.json"})
        )


def test_another_safety2_preflight_directory_rejected() -> None:
    with pytest.raises(ValueError, match="UNRECOGNIZED_OR_MISSING"):
        custody.verify(
            wrap(untracked="examples/forgeai/safety2-preflight-0123456789ab/")
        )
    assert not any(k.endswith("*") or "?" in k for k in custody.ARTIFACTS)


def test_arbitrary_untracked_run_directory_rejected() -> None:
    for extra in ("live1-smoke-0123456789ab", "other-preflight-abcdefabcdef"):
        with pytest.raises(ValueError, match="UNRECOGNIZED_OR_MISSING"):
            custody.verify(wrap(untracked=f"examples/forgeai/{extra}/"))


def test_prior_seven_entries_remain_accepted() -> None:
    # RUN-CUSTODY-2 adds three explicitly pinned artifacts, preserving all prior pins.
    assert {k: custody.ARTIFACTS[k] for k in PRIOR} == PRIOR
    assert custody.ARTIFACTS == {
        **PRIOR,
        DIRECTORY: TREE,
        "safety2-baseline-3cf8aba9a377": "6c0529d9444885a276c1e8f445989ed4579ded13",
        "evaluation/safety2-preflight-20261007-01": "24e26616ba5f575810e3c15180b6be0851afb3b7",
        "evaluation/safety2-preflight-20261007-a": "bed52e1f1ed70236a70208c60a2a6eb07f6c1ee6",
    }
    assert set(PRIOR) <= set(custody.verify(git)["directories"])


def test_prior_changed_artifact_remains_rejected() -> None:
    with pytest.raises(ValueError, match="RUN_DIRECTORY_CHANGED"):
        custody.verify(wrap(rev_parse={"safety1-preflight-c80435f8dadc": "2" * 40}))


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("run_id", "00000000-0000-0000-0000-000000000000"),
        ("condition", "forgeai-analyst-sufficiency-safety-live/1"),
        ("report_identity", "forgeai-analyst-sufficiency-safety-live-report/1"),
        ("mode", "BASELINE"),
        ("calls", 1),
        ("records", [{"case": "s01"}]),
    ],
)
def test_report_identity_fields_required(field: str, value: Any) -> None:
    custody.preflight(report())
    with pytest.raises(ValueError, match="PREFLIGHT2_ARTIFACT_MISMATCH"):
        custody.preflight({**report(), field: value})


def test_run_uuid_matches() -> None:
    assert report()["run_id"] == RUN == custody.PREFLIGHT2["run_id"]


def test_condition_and_report_identities_match() -> None:
    r = report()
    assert r["condition"] == "forgeai-analyst-sufficiency-safety-live/2"
    assert r["report_identity"] == "forgeai-analyst-sufficiency-safety-live-report/2"


def test_mode_is_preflight() -> None:
    assert report()["mode"] == "PREFLIGHT"
    assert report()["decision"]["label"] == "PREFLIGHT - NO MEASUREMENT"


def test_calls_zero() -> None:
    r = report()
    assert (r["calls"], r["attempted"], r["completed"]) == (0, 0, 0)


def test_records_empty() -> None:
    assert report()["records"] == [] and report()["timings"] == []


def test_model_digest_matches() -> None:
    p = report()["provenance"]
    assert p["model_digest"] == p["observed"]["digest"] == custody.MODEL_DIGEST
    broken = {**p, "model_digest": "sha256:" + "0" * 64}
    with pytest.raises(ValueError, match="PREFLIGHT2_ARTIFACT_MISMATCH"):
        custody.preflight({**report(), "provenance": broken})


def test_ollama_version_is_0_40_0() -> None:
    p = report()["provenance"]
    assert p["ollama_version"] == p["observed"]["ollama"] == "0.40.0"
    observed = {**p["observed"], "ollama": "0.35.1"}
    with pytest.raises(ValueError, match="PREFLIGHT2_ARTIFACT_MISMATCH"):
        custody.preflight({**report(), "provenance": {**p, "observed": observed}})


def test_leakage_status_passed() -> None:
    p = report()["provenance"]
    assert p["payload_leakage_preflight"] == "PASSED"
    with pytest.raises(ValueError, match="PREFLIGHT2_ARTIFACT_MISMATCH"):
        custody.preflight(
            {**report(), "provenance": {**p, "payload_leakage_preflight": "FAILED"}}
        )


def test_no_baseline_artifact_admitted() -> None:
    assert {k for k in custody.ARTIFACTS if "-baseline-" in k} == {
        "safety2-baseline-3cf8aba9a377"
    }
    assert {d for d in custody.run_directories(git) if "-baseline-" in d} == {
        "safety2-baseline-3cf8aba9a377"
    }
    with pytest.raises(ValueError, match="UNRECOGNIZED_OR_MISSING"):
        custody.verify(
            wrap(untracked="examples/forgeai/safety2-baseline-300452037205/")
        )


def test_admission_changes_only_the_custody_source_digest() -> None:
    from analyst_sufficiency_safety_live2 import identity

    recorded = report()["provenance"]
    current = identity.binding()
    assert [k for k in current if current[k] != recorded.get(k)] == ["harness_sources"]
    changed = [
        name
        for name, value in current["harness_sources"].items()
        if recorded["harness_sources"].get(name) != value
    ]
    assert changed == ["custody.py"]
