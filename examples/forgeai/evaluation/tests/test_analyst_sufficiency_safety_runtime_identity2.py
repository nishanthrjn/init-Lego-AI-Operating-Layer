"""FORGEAI-ANALYST-SUFFICIENCY-SAFETY-RUNTIME-IDENTITY-2: Ollama 0.40.0 pin.

Offline only. Runtime identity revision tests; scripted Replay runs here are
never quality evidence and make no provider call (FORGEAI_LIVE1_OFFLINE=1).
"""

import asyncio
import json
import os
import subprocess
from collections.abc import Callable
from functools import cache
from pathlib import Path
from typing import Any

import pytest
from analyst_design_live1 import runtime
from analyst_design_live1.identity import git
from analyst_sufficiency_safety_eval2 import data, runner
from analyst_sufficiency_safety_live1 import harness as live1_harness
from analyst_sufficiency_safety_live1 import identity as live1
from analyst_sufficiency_safety_live1 import storage as live1_storage
from analyst_sufficiency_safety_live1.inputs import prepare
from analyst_sufficiency_safety_live2 import custody, harness, identity, storage
from analyst_sufficiency_safety_live2.storage import Store
from legoai_engineering.analyst.sufficiency import (
    EvidenceManifest,
    EvidenceSufficiencyResult,
)

from forgeai_eval.preflight import ServingIdentity

ROOT = Path(__file__).resolve().parents[4]
BASE = "ecbdf24526405fdc8edb00848294a0e9718cf995"  # refusal artifact committed
LIVE1_PACKAGE = "examples/forgeai/evaluation/analyst_sufficiency_safety_live1"
EVAL2_PACKAGE = "examples/forgeai/evaluation/analyst_sufficiency_safety_eval2"
MEMBERS = [f"s{i:02}" for i in range(1, 23)]

pytestmark = pytest.mark.skipif(
    os.environ.get("FORGEAI_LIVE1_OFFLINE") != "1",
    reason="requires the FORGEAI_LIVE1_OFFLINE=1 provider fence",
)


@cache
def b1() -> dict[str, Any]:
    return live1.binding()


@cache
def b2() -> dict[str, Any]:
    return identity.binding()


def git_(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout


def probe(
    version: str = "0.40.0",
    model: str = identity.MODEL,
    digest: str = identity.MODEL_DIGEST,
) -> Callable[[str, str, str], ServingIdentity]:
    return lambda url, m, d: ServingIdentity(version, model, digest)


def repository(*args: str) -> str:
    if args[0] == "status":
        return ""
    return "0" * 40 if args[0] == "rev-parse" else ""


def inprocess(
    m: EvidenceManifest,
    expected: dict[str, Any],
    timeout: float,
    *,
    output: str,
    observe: Callable[[dict[str, Any]], None],
) -> tuple[EvidenceSufficiencyResult, str | None]:
    result, digest, _ = asyncio.run(runtime.governed(m, expected, timeout, output))
    return result, digest


def test_live1_remains_pinned_to_0_35_1() -> None:
    assert live1.VERSION == "0.35.1"
    assert b1()["ollama_version"] == "0.35.1"
    assert b1()["condition"] == "forgeai-analyst-sufficiency-safety-live/1"


def test_live1_remains_immutable() -> None:
    assert git_("diff", "--name-only", BASE, "--", LIVE1_PACKAGE) == ""
    assert git_("status", "--porcelain", "--", LIVE1_PACKAGE) == ""
    assert b2()["live1_harness_sources"] == b1()["harness_sources"]


def test_live2_identity_is_distinct() -> None:
    assert b2()["condition"] == "forgeai-analyst-sufficiency-safety-live/2"
    assert b2()["report"] == "forgeai-analyst-sufficiency-safety-live-report/2"
    assert (b2()["condition"], b2()["report"]) != (b1()["condition"], b1()["report"])
    assert b2()["runtime_revision"]["supersedes"] == live1.CONDITION
    assert b2()["harness_sources"] != b1()["harness_sources"]


def test_live2_pins_exactly_0_40_0() -> None:
    assert identity.VERSION == "0.40.0" and b2()["ollama_version"] == "0.40.0"
    record = identity.compatibility()
    assert record["to"]["ollama"] == "0.40.0" and record["from"]["ollama"] == "0.35.1"
    assert record["decision"] == "COMPATIBLE"
    assert {s["class"] for s in record["surfaces"]} <= {
        "UNCHANGED",
        "COMPATIBLE CHANGE",
    }


def test_0_40_0_accepted_by_live2(tmp_path: Path) -> None:
    result = identity.preflight(tmp_path / "x", probe=probe(), repository=repository)
    assert result["observed"] == {
        "model": identity.MODEL,
        "digest": identity.MODEL_DIGEST,
        "ollama": "0.40.0",
    }
    assert result["payload_leakage_preflight"] == "PASSED"
    assert not (tmp_path / "x").exists()


def test_0_35_1_rejected_by_live2(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="RUNTIME_IDENTITY_REVIEW_REQUIRED"):
        identity.preflight(tmp_path / "x", probe=probe("0.35.1"), repository=repository)


@pytest.mark.parametrize(
    "version", ["0.40.1", "0.41.0", "1.0.0", "0.40", "0.40.0-rc6", "latest", ""]
)
def test_arbitrary_newer_version_rejected(tmp_path: Path, version: str) -> None:
    with pytest.raises(ValueError, match="RUNTIME_IDENTITY_REVIEW_REQUIRED"):
        identity.preflight(tmp_path / "x", probe=probe(version), repository=repository)


def test_model_tag_unchanged(tmp_path: Path) -> None:
    assert b2()["model"] == b1()["model"] == "qwen2.5-coder:14b"
    with pytest.raises(ValueError, match="MODEL_IDENTITY_MISMATCH"):
        identity.preflight(
            tmp_path / "x", probe=probe(model="qwen2.5-coder:7b"), repository=repository
        )


def test_model_digest_unchanged(tmp_path: Path) -> None:
    expected = "sha256:9ec8897f747e246e970bc5cfdda85d22f1123dc2e3d34978a010a75968716849"
    assert b2()["model_digest"] == b1()["model_digest"] == expected
    # The same tag with any other digest is refused.
    with pytest.raises(ValueError, match="MODEL_IDENTITY_MISMATCH"):
        identity.preflight(
            tmp_path / "x",
            probe=probe(digest="sha256:" + "1" * 64),
            repository=repository,
        )


def test_safety_eval2_unchanged() -> None:
    assert b2()["evaluation"] == "forgeai-analyst-sufficiency-safety-eval/2"
    assert b2()["frozen_digests"] == data.freeze() == b1()["frozen_digests"]
    assert git_("diff", "--name-only", BASE, "--", EVAL2_PACKAGE) == ""


def test_agent_prompt_parser_unchanged() -> None:
    for key in ("agent", "agent_version", "agent_fingerprint", "prompt_digest"):
        assert b2()[key] == b1()[key]
    assert b2()["parser_identity"] == b1()["parser_identity"]
    assert git_("diff", "--name-only", BASE, "731f69c", "--", "packages", "src") == ""


def test_membership_unchanged() -> None:
    assert b2()["membership"] == b1()["membership"] == MEMBERS


def test_gates_unchanged() -> None:
    assert data.gates()["decision_order"] == ["A", "G", "C", "B", "D", "E", "F"]
    assert (
        b2()["frozen_digests"]["gates-s2.json"]
        == b1()["frozen_digests"]["gates-s2.json"]
    )


def test_budgets_unchanged() -> None:
    for key in (
        "call_ceiling",
        "call_seconds",
        "total_seconds",
        "N",
        "retry",
        "fallback",
        "acquisition",
        "reassessment",
    ):
        assert b2()[key] == b1()[key]
    assert (b2()["call_ceiling"], b2()["call_seconds"], b2()["total_seconds"]) == (
        22,
        600,
        3600,
    )


def test_report_semantics_unchanged(tmp_path: Path) -> None:
    outputs = {
        c.id: runner.scripted(c, o, runner.Fault.CORRECT) for c, o in data.load()
    }
    provenance = {**b2(), "commit": "offline", "clean_tracked_tree": True}
    report = harness.execute(
        Store(tmp_path / "run"),
        provenance,
        "offline-test",
        mode="OFFLINE_REPLAY",
        call=inprocess,
        outputs=outputs,
    )
    assert report["report_identity"] == identity.REPORT
    assert report["condition"] == identity.CONDITION
    assert report["decision"]["code"] == "F"  # scripted, not quality evidence
    assert report["calls"] == 22 and report["blended_score"] == "NOT_PRODUCED"
    on_disk = json.loads((tmp_path / "run" / "report.json").read_text())
    storage.validate(on_disk)
    schema = json.loads((live1.HERE / "report-schema.json").read_text())
    assert set(schema["required"]) <= set(on_disk)
    run = json.loads((tmp_path / "run" / "run.json").read_text())
    assert run["condition"] == identity.CONDITION
    with pytest.raises(ValueError, match="report identity"):
        live1_storage.validate(on_disk)  # never mistaken for a live/1 report
    with pytest.raises(ValueError, match="identity"):
        storage.validate({**on_disk, "report_identity": live1.REPORT})


def test_failed_preflight_artifact_remains_immutable() -> None:
    path = "examples/forgeai/" + custody.REFUSAL["directory"]
    assert git_("rev-parse", "HEAD:" + path).strip() == custody.REFUSAL["tree"]
    assert git_("diff", "--name-only", BASE, "--", path) == ""
    assert git_("status", "--porcelain", "--", path) == ""
    report = json.loads((ROOT / path / "report.json").read_text(encoding="utf-8"))
    assert report["run_id"] == "6c557182-67a9-4851-9260-058c36e896be"
    assert report["stop_reason"] == "RUNTIME_IDENTITY_REVIEW_REQUIRED"
    assert report["calls"] == 0 and report["records"] == []


def test_refusal_artifact_recognized_narrowly() -> None:
    result = custody.verify(git)
    assert custody.REFUSAL["directory"] in result["directories"]

    def tampered(*args: str) -> str:
        if args[0] == "rev-parse" and args[1].endswith(custody.REFUSAL["directory"]):
            return "0" * 40
        return git(*args)

    with pytest.raises(ValueError, match="RUN_DIRECTORY_CHANGED"):
        custody.verify(tampered)


@pytest.mark.parametrize(
    "extra", ["safety2-preflight-0123456789ab", "safety1-baseline-0123456789ab"]
)
def test_no_arbitrary_live_artifact_directory_accepted(extra: str) -> None:
    def untracked(*args: str) -> str:
        if args[0] == "ls-files":
            return git(*args) + f"\nexamples/forgeai/{extra}/"
        return git(*args)

    with pytest.raises(ValueError, match="UNRECOGNIZED_OR_MISSING"):
        custody.verify(untracked)


def test_no_semantic_safety_cases_executed_by_validator() -> None:
    assert os.environ["FORGEAI_LIVE1_OFFLINE"] == "1"
    case, o = data.load()[0]
    p = asyncio.run(prepare(case, o))
    with pytest.raises(ValueError, match="OFFLINE_PROVIDER_FORBIDDEN"):
        asyncio.run(runtime.governed(p.manifest, p.expected, 600.0))


def test_zero_baseline_calls(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    result = identity.preflight(tmp_path / "x", probe=probe(), repository=repository)
    monkeypatch.setattr(harness, "preflight", lambda directory: result)

    def forbidden(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("baseline execution in this slice")

    monkeypatch.setattr(harness, "execute", forbidden)
    report = harness.run("PREFLIGHT", tmp_path / "p", "offline-test")
    assert report["calls"] == 0 and report["decision"]["code"] is None
    assert report["report_identity"] == identity.REPORT
    assert not list((tmp_path / "p").glob("call-*"))
    assert harness.execute is forbidden and live1_harness.execute is not forbidden
    # RUN-CUSTODY-2 admitted a pinned past baseline; PREFLIGHT still makes zero calls.
    assert custody.verify(git)["directories"]
    assert not [d for d in custody.run_directories(git) if d not in custody.ARTIFACTS]
