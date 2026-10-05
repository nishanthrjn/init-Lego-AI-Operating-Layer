"""ANALYST-MODEL-COMPARE-1 qualification. No live model is contacted or pulled.

Replay calls run through the real host, AuthorizedRepositoryEvidence and the
unchanged RepositoryAnalyst 1.0.2; replay outputs exercise the harness only.
"""

import hashlib
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from analyst_model_compare1 import cli, data, report
from analyst_quality1q import cli as cq
from analyst_quality1q import data as q
from analyst_quality1q import metrics
from analyst_quality1q_r2 import data as r2
from analyst_quality1q_r3 import cli as r3cli
from analyst_quality1q_r3 import data as r3
from analyst_quality1q_r3 import report as r3report
from forgeai.cli import ReplayModel, replay_binding
from forgeai_eval.preflight import PreflightError, PreflightFailure

V102 = "5f6635c756df41a855fd1ab8b538765267ba97b31410b16125e905697b82ceef"
PARSER = "016fcc40a0e341c5ec625fe11d130668608cde7d74d5a85a16bb4f9772812672"
CANDIDATE = "qwen2.5-coder:14b"
PIN = "sha256:" + "1" * 64
HARDWARE = "Intel Core i7-8565U (4 cores/8 threads), 16 GB RAM, Windows 11"
SENTINEL = "compare-sentinel-must-not-leak"
MARGINS = {
    "required_recall": 0.15,
    "acceptable_set_success": 0.15,
    "insufficient_correct": 0.25,
    "false_sufficient_ratio": 0.5,
}


def rate(n: int, d: int) -> dict[str, object]:
    return {"numerator": n, "denominator": d, "value": round(n / d, 4) if d else None}


def never(*args: object) -> object:
    raise AssertionError("must be refused before this point")


def pin(monkeypatch: pytest.MonkeyPatch, value: str | None = PIN) -> None:
    pins = {**data.pins(), CANDIDATE: value}
    monkeypatch.setattr(data, "pins", lambda: pins)


def argv(mode: str, output: Path, **overrides: str) -> list[str]:
    flags = {
        "--model": CANDIDATE,
        "--model-digest": PIN,
        "--hardware": HARDWARE,
        "--expect-branch": "b",
        "--expect-commit": "c",
        **{f"--{k.replace('_', '-')}": v for k, v in overrides.items()},
    }
    out = [mode, "--output", str(output)]
    for flag, value in flags.items():
        out += [flag, value]
    return out


# Frozen identities ------------------------------------------------------------


def test_analyst_identity_is_the_r3_1_0_2() -> None:
    analyst = data.read()["analyst"]
    assert analyst == r3.read()["analyst"]
    assert isinstance(analyst, dict)
    assert analyst["version"] == q.analyst_version() == "1.0.2"
    assert analyst["definition_fingerprint"] == q.definition_fingerprint() == V102
    data.require_live_identity()


def test_parser_identity_pin() -> None:
    analyst = data.read()["analyst"]
    assert isinstance(analyst, dict)
    current = r2.parser_identity((q.ROOT / r3.API).read_text(encoding="utf-8"))
    assert analyst["parser_identity"] == current == PARSER


def test_r3_history_is_unchanged() -> None:
    r3.freeze()
    doc = (
        q.ROOT / "planning/FORGEAI-CONTENT-DISCOVERY-ANALYST-QUALITY-R3.md"
    ).read_text(encoding="utf-8")
    assert cli.CONTROL_REPORT_SHA256 in doc
    control = data.read()["control"]
    assert isinstance(control, dict)
    assert control["report_sha256"] == cli.CONTROL_REPORT_SHA256
    assert control["condition_digest"] in doc
    assert control["decision"] == "C"


def test_workload_oracle_threshold_and_plan_reuse() -> None:
    digests = data.freeze()
    assert {k: v for k, v in digests.items() if k != "compare1_preregistration"} == (
        r3.freeze()
    )
    assert data.read()["reused"] == r3.read()["reused"]
    assert q.thresholds()["required_recall_min"] == 0.9
    assert q.thresholds()["false_sufficient_max"] == 0
    assert cq.plan_counts(q.plan())["total_calls"] == 91
    assert data.read()["model_condition"] == r3.read()["model_condition"]


def test_decision_rule_reuse() -> None:
    used = vars(r3report)
    assert used["decide"] is metrics.decide and used["gates"] is metrics.gates
    assert vars(report)["r3"] is r3report  # per-model reports are the R3 builder


def test_control_metrics_pin() -> None:
    control = data.read()["control"]
    assert isinstance(control, dict)
    held = control["heldout"]
    assert held == {
        "validity": {"numerator": 67, "denominator": 72},
        "precision": {"numerator": 49, "denominator": 56},
        "required_recall": {"numerator": 34, "denominator": 67},
        "acceptable_set_success": {"numerator": 21, "denominator": 55},
        "insufficient_correct": {"numerator": 3, "denominator": 12},
        "false_sufficient": 10,
        "catastrophic": 0,
        "answerable_success": {"numerator": 28, "denominator": 60},
    }
    assert control["digest"] == data.read()["model_condition"]["digest"]  # type: ignore[index]


# Candidates and pins -------------------------------------------------------------


def test_candidate_registry_and_pins(monkeypatch: pytest.MonkeyPatch) -> None:
    registry = data.candidates()
    assert set(registry) == set(data.pins()) == {CANDIDATE, "phi4:14b"}
    assert registry[CANDIDATE]["required"] is True
    assert "qwen2.5-coder:7b" not in registry  # the control is recorded R3
    assert all(v is None for v in data.pins().values())  # nothing acquired yet
    with pytest.raises(data.CandidateError, match="not a registered"):
        data.require_candidate("qwen2.5-coder:3b", PIN)
    with pytest.raises(data.CandidateError, match="acquisition pending"):
        data.require_candidate(CANDIDATE, PIN)
    pin(monkeypatch)
    with pytest.raises(data.CandidateError, match="differs"):
        data.require_candidate(CANDIDATE, "sha256:" + "2" * 64)
    assert data.require_candidate(CANDIDATE, PIN)["id"] == "qwen2.5-coder-14b"


def test_pin_file_format(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / data.PINS).write_text(json.dumps({CANDIDATE: "latest"}), "utf-8")
    monkeypatch.setattr(data, "HERE", tmp_path)
    with pytest.raises(ValueError):
        data.pins()


# Smoke and full-run semantics ----------------------------------------------------


def smoke_records(output: str | None = None) -> list[dict[str, object]]:
    def binding(case: q.Case, repetition: int) -> object:
        return replay_binding(ReplayModel(output or cq.replay_output(case)))

    return r3cli.execute(data.smoke_plan(), binding)  # type: ignore[arg-type]


def test_smoke_is_not_quality_evidence() -> None:
    assert [case.id for case, _ in data.smoke_plan()] == ["q04", "q10", "q19"]
    records = smoke_records()
    built = report.smoke({"mode": "smoke", "model": {"name": CANDIDATE}}, records)
    assert built["schema"] == report.SMOKE_SCHEMA
    assert built["quality_evidence"] is False
    assert "not quality evidence" in str(built["label"])
    assert not {"gates", "decision", "aggregate", "answerable"} & set(built)
    assert built["calls"] == 3 and built["fits_host"] is True
    slow = [{**r, "seconds": 601.0} for r in records]
    assert report.smoke({"mode": "smoke"}, slow)["fits_host"] is False
    failed = [{**r, "stage": "model_failure"} for r in records]
    assert report.smoke({"mode": "smoke"}, failed)["fits_host"] is False
    assert report.smoke({"mode": "smoke"}, [])["fits_host"] is False


def test_full_run_has_no_early_stop() -> None:
    def binding(case: q.Case, repetition: int) -> object:
        return replay_binding(ReplayModel("not json at all"))

    records = r3cli.execute(q.plan(), binding)  # type: ignore[arg-type]
    assert len(records) == 91
    assert {r["stage"] for r in records} == {"response_not_json"}


def test_per_model_report_isolation(tmp_path: Path) -> None:
    output = tmp_path / "replay"
    assert cli.main(["replay", "--output", str(output)]) == 0
    written = json.loads((output / "report.json").read_text("utf-8"))
    condition = json.loads((output / "condition.json").read_text("utf-8"))
    assert written["schema"] == report.REPORT_SCHEMA
    assert condition["schema"] == report.CONDITION_SCHEMA
    assert condition["analyst"]["definition_fingerprint"] == V102
    assert condition["fixtures"] == data.freeze()
    assert len(written["records"]) == 91
    assert written["decision"]["label"] == "REPLAY ONLY - not quality evidence"
    assert set(written["timing"]) == {
        "calls",
        "mean",
        "median",
        "p90",
        "max",
        "total_hours",
    }
    historical = data.read()["historical"]
    assert isinstance(historical, dict)
    rebuilt = report.build(
        written["condition"], written["records"], q.thresholds(), historical
    )
    assert all(rebuilt[k] == written[k] for k in rebuilt if k != "records")
    assert (output / "report.md").read_text("utf-8") == report.render_model(written)
    assert not (output / "smoke.json").exists()


# Comparison rule -------------------------------------------------------------------


def summ(
    *,
    decision: str = "C",
    validity: bool = True,
    recall: tuple[int, int] = (34, 67),
    acceptable: tuple[int, int] = (21, 55),
    insufficient: tuple[int, int] = (3, 12),
    false_sufficient: int = 10,
    safety: int = 0,
    disagreements: int = 0,
    classes: dict[str, tuple[int, int]] | None = None,
) -> dict[str, object]:
    per_class = classes or {"a": (1, 2), "b": (1, 2), "c": (1, 2)}
    return {
        "model": "m",
        "decision": decision,
        "gates": {"validity": validity},
        "validity": rate(67, 72),
        "precision": rate(49, 56),
        "required_recall": rate(*recall),
        "acceptable_set_success": rate(*acceptable),
        "insufficient_correct": rate(*insufficient),
        "false_sufficient": false_sufficient,
        "classifier_disagreements": disagreements,
        "safety": {"unknown_path_accepted": safety, "authority_expansion": 0},
        "per_class": {
            k: {"required_recall": rate(*v), "acceptable_set_success": rate(0, 1)}
            for k, v in per_class.items()
        },
    }


CONTROL = summ()
BETTER = {"a": (2, 2), "b": (2, 2), "c": (1, 2)}


@pytest.mark.parametrize(
    ("candidate", "code"),
    [
        (summ(decision="A"), "A"),
        (
            summ(
                recall=(48, 67),
                acceptable=(31, 55),
                insufficient=(6, 12),
                false_sufficient=5,
                classes=BETTER,
            ),
            "A",
        ),
        (
            summ(
                recall=(38, 67),
                acceptable=(24, 55),
                insufficient=(5, 12),
                false_sufficient=8,
                classes=BETTER,
            ),
            "B",
        ),
        (
            summ(
                recall=(60, 67),
                acceptable=(40, 55),
                insufficient=(6, 12),
                false_sufficient=8,
                classes=BETTER,
            ),
            "B",
        ),
        (
            summ(
                recall=(40, 67),
                acceptable=(40, 55),
                insufficient=(10, 12),
                false_sufficient=1,
                classes=BETTER,
            ),
            "B",
        ),
        (
            summ(
                validity=False,
                recall=(60, 67),
                acceptable=(40, 55),
                insufficient=(10, 12),
                false_sufficient=1,
                classes=BETTER,
            ),
            "B",
        ),
        (summ(decision="A", safety=1), "B"),
        (
            summ(
                recall=(60, 67),
                acceptable=(40, 55),
                insufficient=(10, 12),
                false_sufficient=1,
                classes={"a": (1, 2), "b": (0, 2), "c": (2, 2)},
            ),
            "B",
        ),
    ],  # fmt: skip
    ids=[
        "all_gates",
        "material",
        "within_noise",
        "false_sufficient_priority",
        "recall_priority",
        "validity_tradeoff",
        "safety_blocks",
        "class_inconsistency",
    ],
)
def test_comparison_rule(candidate: dict[str, object], code: str) -> None:
    assert report.compare(CONTROL, [candidate], [], [], MARGINS)["code"] == code


def test_comparison_d_and_c_outcomes() -> None:
    good = summ(decision="A")
    assert report.compare(CONTROL, [good], [], ["x: bad"], MARGINS)["code"] == "D"
    assert report.compare(CONTROL, [summ(decision="D")], [], [], MARGINS)["code"] == "D"
    assert (
        report.compare(CONTROL, [summ(disagreements=1)], [], [], MARGINS)["code"] == "D"
    )
    failed: dict[str, object] = {"fits_host": False}
    assert report.compare(CONTROL, [], [failed, failed], [], MARGINS)["code"] == "C"
    with pytest.raises(ValueError):
        report.compare(CONTROL, [], [{"fits_host": True}], [], MARGINS)
    with pytest.raises(ValueError):
        report.compare(CONTROL, [], [], [], MARGINS)


def test_margins_are_preregistered() -> None:
    assert data.read()["margins"] == MARGINS
    assert data.read()["smoke_cases"] == ["q04", "q10", "q19"]


# Verified comparison end to end ----------------------------------------------------


def live_report(tmp_path: Path) -> dict[str, object]:
    """A replay report re-labelled as a pinned live candidate (identity test only)."""
    output = tmp_path / "source"
    assert cli.main(["replay", "--output", str(output)]) == 0
    source = json.loads((output / "report.json").read_text("utf-8"))
    condition = {
        **source["condition"],
        "mode": "live",
        "model": {"provider": "ollama", "name": CANDIDATE, "digest": PIN},
    }
    historical = data.read()["historical"]
    return report.build(condition, source["records"], q.thresholds(), historical)  # type: ignore[arg-type]


def test_candidate_identity_verification(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pin(monkeypatch)
    value = live_report(tmp_path)
    digests = data.freeze()
    cli.verify_candidate(value, digests)
    tampered = json.loads(json.dumps(value))
    tampered["records"][0]["valid"] = not tampered["records"][0]["valid"]
    with pytest.raises(cli.IdentityError, match="re-fold"):
        cli.verify_candidate(tampered, digests)
    mutations: list[tuple[Callable[[Any], object], str]] = [
        (lambda v: v["condition"]["model"].update(digest="sha256:" + "3" * 64), "pin"),
        (
            lambda v: v["condition"]["analyst"].update(definition_fingerprint="0"),
            "1.0.2",
        ),
        (lambda v: v["condition"]["fixtures"].update(heldout="0"), "workload"),
        (lambda v: v["condition"]["plan"].update(total_calls=3), "91"),
        (lambda v: v.update(schema="forgeai-analyst-quality-report/3"), "schema"),
    ]
    for mutate, match in mutations:
        broken = json.loads(json.dumps(value))
        mutate(broken)
        with pytest.raises(cli.IdentityError, match=match):
            cli.verify_candidate(broken, digests)


def test_compare_command_end_to_end(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pin(monkeypatch)
    candidate_dir = tmp_path / "candidate"
    candidate_dir.mkdir()
    (candidate_dir / "report.json").write_text(
        json.dumps(live_report(tmp_path)), "utf-8"
    )
    r3_out = tmp_path / "r3"
    assert r3cli.main(["replay", "--output", str(r3_out)]) == 0
    control = json.loads((r3_out / "report.json").read_text("utf-8"))
    control_dir = tmp_path / "control"
    control_dir.mkdir()
    control_path = control_dir / "report.json"
    control_path.write_text(json.dumps({**control, "mode": "live"}), "utf-8")
    with pytest.raises(SystemExit):  # not the recorded R3 report
        cli.main(
            ["compare", "--output", str(tmp_path / "x"), "--control", str(control_path)]
        )
    monkeypatch.setattr(
        cli,
        "CONTROL_REPORT_SHA256",
        hashlib.sha256(control_path.read_bytes()).hexdigest(),
    )
    out = tmp_path / "comparison"
    assert cli.main([
        "compare", "--output", str(out), "--control", str(control_path),
        "--candidate", str(candidate_dir / "report.json"),
    ]) == 0  # fmt: skip
    written = json.loads((out / "comparison.json").read_text("utf-8"))
    assert written["schema"] == report.COMPARISON_SCHEMA
    assert written["outcome"]["code"] == "A"  # oracle-shaped replay passes every gate
    assert len(written["models"]) == 2
    assert written["inputs"]["control"] == cli.CONTROL_REPORT_SHA256
    assert (out / "comparison.md").read_text("utf-8") == report.render_comparison(
        written
    )


# Privacy ------------------------------------------------------------------------------


def test_report_privacy(tmp_path: Path) -> None:
    leaky = json.dumps(
        {
            "status": "insufficient_evidence",
            "summary": SENTINEL,
            "relevant_files": [],
            "findings": [{"text": SENTINEL, "paths": ["x.py"]}],
            "risks": [SENTINEL],
            "unknowns": [SENTINEL],
            SENTINEL: 1,
        }
    )
    records = smoke_records(leaky)
    condition = cli.condition(
        "smoke", data.freeze(), data.smoke_plan(), {"head": "h"}, {"name": "m"},
        {"id": "x", "role": "y"}, HARDWARE,
    )  # fmt: skip
    report.write(
        tmp_path, "smoke", report.smoke(condition, records), report.render_smoke
    )
    full = report.build(condition, records, q.thresholds(), data.read()["historical"])  # type: ignore[arg-type]
    report.write(tmp_path, "report", full, report.render_model)
    cases = {case.id: case for case, _ in data.smoke_plan()}
    for name in ("smoke.json", "smoke.md", "report.json", "report.md"):
        text = (tmp_path / name).read_text("utf-8")
        assert SENTINEL not in text
        assert str(q.ROOT) not in text and str(tmp_path) not in text
        for case in cases.values():
            assert case.question not in text
            for f in case.files:
                assert f.text not in text


# Live refusals -------------------------------------------------------------------------


@pytest.mark.parametrize("mode", ["smoke", "live"])
def test_refuses_wrong_analyst(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mode: str
) -> None:
    pin(monkeypatch)
    monkeypatch.setattr(q, "definition_fingerprint", lambda: "0" * 64)
    monkeypatch.setattr(cq, "git_state", never)
    monkeypatch.setattr(cli, "verify_ollama", never)
    output = tmp_path / mode
    assert cli.main(argv(mode, output)) == cq.PREFLIGHT_FAILED
    assert not output.exists()


@pytest.mark.parametrize(
    ("model", "digest", "pinned"),
    [
        ("qwen2.5-coder:7b", PIN, PIN),
        ("qwen2.5-coder:3b", PIN, PIN),
        (CANDIDATE, PIN, None),
        (CANDIDATE, "sha256:" + "2" * 64, PIN),
    ],
    ids=["control", "unregistered", "unpinned", "digest"],
)
def test_refuses_wrong_model_or_digest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    model: str,
    digest: str,
    pinned: str | None,
) -> None:
    pin(monkeypatch, pinned)
    monkeypatch.setattr(cq, "git_state", never)
    monkeypatch.setattr(cli, "verify_ollama", never)
    output = tmp_path / "live"
    assert cli.main(argv("live", output, model=model, model_digest=digest)) == (
        cq.PREFLIGHT_FAILED
    )
    assert not output.exists()


@pytest.mark.parametrize(
    "state",
    [{"status": " M x"}, {"branch": "other"}, {"rev-parse": "zzz"}],
    ids=["dirty", "branch", "commit"],
)
def test_refuses_checkout_mismatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, state: dict[str, str]
) -> None:
    pin(monkeypatch)
    good = {"rev-parse": "c", "branch": "b", "status": ""}
    monkeypatch.setattr(cq, "git", lambda args: {**good, **state}[args[0]])
    monkeypatch.setattr(cli, "verify_ollama", never)
    output = tmp_path / "live"
    assert cli.main(argv("live", output)) == cq.PREFLIGHT_FAILED
    assert not output.exists()


def test_refuses_placeholder_hardware_and_unreachable_ollama(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pin(monkeypatch)
    monkeypatch.setattr(cq, "git_state", never)
    output = tmp_path / "live"
    for hardware in ("<REAL HARDWARE DESCRIPTION>", "TBD", " "):
        assert cli.main(argv("smoke", output, hardware=hardware)) in {
            cq.PREFLIGHT_FAILED,
            2,
        }
    monkeypatch.setattr(cq, "git_state", lambda *a: {"head": "h"})

    def refuse(*args: object) -> object:
        raise PreflightError(PreflightFailure.OLLAMA_UNREACHABLE, "no")

    monkeypatch.setattr(cli, "verify_ollama", refuse)
    assert cli.main(argv("smoke", output)) == cq.PREFLIGHT_FAILED
    assert not output.exists()


def test_refuses_output_collision(tmp_path: Path) -> None:
    existing = tmp_path / "existing"
    existing.mkdir()
    (existing / "keep.txt").write_text("previous", "utf-8")
    for mode in ("live", "smoke", "replay", "compare"):
        with pytest.raises(SystemExit):
            cli.main(argv(mode, existing))
    assert (existing / "keep.txt").read_text("utf-8") == "previous"


def test_harness_is_evaluation_only() -> None:
    source = "\n".join(p.read_text("utf-8") for p in data.HERE.glob("*.py"))
    for forbidden in (
        "mutation",
        "AuthorizedEngineeringChecks",
        "CodingAgent",
        "IndependentReviewer",
        "forgeai.worker",
        "ModelRouter",
        "ollama pull",
    ):
        assert forbidden not in source, forbidden
