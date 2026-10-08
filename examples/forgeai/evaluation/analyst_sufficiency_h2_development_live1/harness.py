"""Sequential H2 development controller: s01..s22, one initial 1.1.0 call each.

Two result layers per case, never merged:
- raw: the Agent 1.1.0 result under the frozen SAFETY-EVAL-2 progression
  (a valid SUFFICIENT is accepted, anything else declined), scored by the
  unchanged evaluator;
- guarded: the same result through the unchanged H1 PolicyGatedSequence on a
  separately prepared sequence, under the same frozen progression rule.

Semantic failures (false sufficient, invalid output, fabricated or forbidden
requests, wrong kinds, ambiguity misses, over-abstention) remain measurement
rows. Leakage, identity or payload mismatch, an actual unauthorized effect,
the call or time ceiling, a runtime/IPC integrity failure, an H3 violation and
a non-structural model failure stop the run. No retry, reassessment,
acquisition, clarification answer, repair, fallback, resume or replay.
"""

import asyncio
import hashlib
import time
from collections import Counter
from collections.abc import Callable, Mapping
from dataclasses import asdict
from pathlib import Path
from typing import Any, cast

from analyst_design_live1.lifecycle import partition
from analyst_evidence_loop.policy_gate import PolicyGatedSequence
from analyst_evidence_loop.sequence import EvidenceSequence, OperatorReview, Stage
from analyst_sufficiency_safety_eval1.report import record
from analyst_sufficiency_safety_eval2.data import declared_paths, input_facts, load
from analyst_sufficiency_safety_eval2.metrics import STRUCTURAL, evaluate, leaks
from analyst_sufficiency_safety_eval2.runner import Row
from analyst_sufficiency_safety_eval2.scoring import score
from analyst_sufficiency_safety_live1.inputs import prepare as base_prepare
from legoai_engineering.analyst.sufficiency import (
    EvidenceSufficiencyResult,
    SufficiencyDisposition,
)

from analyst_sufficiency_h2_development_live1 import comparison, identity
from analyst_sufficiency_h2_development_live1.identity import (
    CALL_CEILING,
    CALL_SECONDS,
    CLEANUP_RESERVE,
    CONDITION,
    EVALUATION,
    REPORT,
    TOTAL_SECONDS,
    policy,
    preflight,
    verify_before_call,
)
from analyst_sufficiency_h2_development_live1.inputs import (
    Prepared,
    facts,
    guard,
    prepare,
)
from analyst_sufficiency_h2_development_live1.runtime import (
    H3_ABSENT,
    CallStopped,
    supervised,
)
from analyst_sufficiency_h2_development_live1.storage import INTERPRETATION, Store
from legoai.execution.values import ExecutionId

Call = Callable[..., tuple[EvidenceSufficiencyResult, str | None, str]]
VARIANT = PHASE = "initial"


class Stopped(Exception):
    """A stop condition that invalidates subsequent measurement."""

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(reason)


def planned() -> list[dict[str, str]]:
    return [{"case": c.id, "variant": VARIANT, "phase": PHASE} for c, _ in load()]


def _progress(sequence: EvidenceSequence | PolicyGatedSequence) -> bool:
    """The frozen progression rule: accept a valid SUFFICIENT, decline the rest."""
    obs = sequence.observe()
    if obs.stage is Stage.REVIEW:
        assert obs.assessment is not None
        accept = obs.assessment.disposition is SufficiencyDisposition.SUFFICIENT
        sequence.progress(
            OperatorReview(obs.manifest.identity(), obs.assessment_ids[-1], accept),
            obs.manifest,
        )
    return sequence.observe().stage is Stage.ELIGIBLE_FOR_ANALYSIS


def guarded_view(
    case_id: str, p: Prepared, result: EvidenceSufficiencyResult, raw: bool
) -> dict[str, Any]:
    """H1 on a separately prepared sequence; the raw result is never replaced."""
    g = asyncio.run(base_prepare(p.base.case, p.base.oracle))
    if g.manifest.identity() != p.base.manifest.identity():
        raise Stopped("runtime_integrity:guarded_manifest")
    reads = list(g.workspace.reads)
    gated = PolicyGatedSequence(g.sequence, policy())
    gated.assess(ExecutionId(f"{case_id}-{VARIANT}-{PHASE}-guarded"), result)
    decision = gated.decisions[-1].audit() if gated.decisions else None
    eligible = gated.rejected is None and _progress(gated)
    if g.workspace.reads != reads:  # no request is ever executed
        raise Stopped("authority_effect_violation")
    return {
        "decision": decision,
        "blocked_by_h1": decision is not None and not decision["accepted"],
        "raw_progressed": raw,
        "guarded_progressed": eligible,
    }


def execute(
    store: Store,
    provenance: dict[str, Any],
    approval: str,
    *,
    mode: str = "DEVELOPMENT",
    call: Call = supervised,
    outputs: Mapping[str, str] | None = None,
    clock: Callable[[], float] = time.monotonic,
    started: float | None = None,
    before_call: Callable[[], None] | None = None,
) -> dict[str, Any]:
    if mode not in {"DEVELOPMENT", "OFFLINE_REPLAY"} or not approval.strip():
        raise ValueError("explicit mode and operator approval required")
    if mode == "DEVELOPMENT" and (outputs is not None or before_call is None):
        raise ValueError("live calls require preflight revalidation and no replay")
    if mode == "OFFLINE_REPLAY" and outputs is None:
        raise ValueError("offline replay requires scripted outputs")
    start = clock() if started is None else started
    calls = 0
    rows: list[Row] = []
    guarded: dict[str, dict[str, Any]] = {}
    times: list[dict[str, Any]] = []
    invalid: list[dict[str, Any]] = []
    stop: str | None = None
    inflight = "NONE"
    leaked = False
    h3 = "NOT_OBSERVED"
    complete = False
    plan = load()  # frozen SAFETY-EVAL-2 order, verified against the freeze

    def dispatch(p: Prepared) -> EvidenceSufficiencyResult:
        nonlocal calls, inflight, h3
        remaining = TOTAL_SECONDS - (clock() - start) - CLEANUP_RESERVE
        if remaining <= 0:
            raise CallStopped("deadline", "NOT_STARTED")
        if calls >= CALL_CEILING:
            raise CallStopped("call_ceiling", "NOT_STARTED")
        if before_call is not None:
            try:
                before_call()
            except ValueError as error:
                raise Stopped("harness_identity_failure") from error
        timeout = min(float(CALL_SECONDS), remaining)
        calls += 1
        begun = clock()
        inflight = "CLIENT_ACTIVE_SERVER_EFFECT_UNKNOWN"
        name = f"call-{calls:03}"
        base = {"case": p.base.case.id, "variant": VARIANT, "phase": PHASE}
        store.write(f"{name}-started.json", {**base, "timeout": timeout})
        diagnostics: dict[str, Any] | None = None
        serial = 0

        def observe(value: dict[str, Any]) -> None:
            nonlocal diagnostics, serial
            diagnostics = value
            serial += 1
            store.write(f"{name}-diagnostic-{serial:02}.json", {**base, **value})

        options: dict[str, Any] = {"observe": observe}
        if outputs is not None:
            options["output"] = outputs[p.base.case.id]
        try:
            result, digest, marker = call(
                p.base.manifest, p.expected, timeout, **options
            )
        except BaseException as error:
            timing: dict[str, Any] = {
                **base,
                "seconds": clock() - begun,
                "user_payload_digest": None,
                "failure": error.reason
                if isinstance(error, CallStopped)
                else type(error).__name__,
            }
            if isinstance(error, CallStopped):
                timing["child_diagnostics"] = error.diagnostics.record()
            elif diagnostics is not None:
                timing["child_diagnostics"] = diagnostics
            times.append(timing)
            store.write(f"{name}-finished.json", timing)
            raise
        inflight = "CLIENT_COMPLETED"
        timing = {
            **base,
            "seconds": clock() - begun,
            "user_payload_digest": digest,
            "failure": result.failure.value if result.failure else None,
            "h3": marker,
        }
        if diagnostics is not None:
            timing["child_diagnostics"] = diagnostics
        times.append(timing)
        store.write(f"{name}-finished.json", timing)
        if marker != H3_ABSENT:
            h3 = "VIOLATED"
            raise Stopped("h3_structured_output_present")
        h3 = "ABSENT"
        if digest != hashlib.sha256(p.payload.encode()).hexdigest():
            raise Stopped("runtime_integrity:payload_digest")
        if result.failure is not None:
            entry: dict[str, Any] = {**base, "failure": result.failure.value}
            if result.failure.value in STRUCTURAL:
                entry["diagnostics"] = {
                    k: (diagnostics or {}).get(k)
                    for k in (
                        "invalid_output_rejection_code",
                        "output_length_class",
                        "invalid_output_branch",
                        "diagnostic_disagreement",
                    )
                }
            invalid.append(entry)
        return result

    try:
        for case, o in plan:
            if clock() - start >= TOTAL_SECONDS - CLEANUP_RESERVE:
                raise CallStopped("deadline", "NOT_STARTED")
            p = asyncio.run(prepare(case, o))
            reads = list(p.base.workspace.reads)
            try:
                guard(p)
            except ValueError as error:
                leaked = True
                raise Stopped("payload_leakage") from error
            result = dispatch(p)
            sequence = p.base.sequence
            sequence.assess(ExecutionId(f"{case.id}-{VARIANT}-{PHASE}"), result)
            raw = _progress(sequence)
            a = result.assessment
            row = Row(
                case.id,
                a.disposition.value if a else None,
                a.requests if a else (),
                tuple(x.value for x in a.governing_sources) if a else (),
                result.failure is None,
                result.failure.value if result.failure else None,
                raw,
                sum(x not in p.base.allowed for x in p.base.workspace.reads),
                1,
                p.payload,  # in memory only; the record keeps its SHA-256
            )
            guarded[case.id] = guarded_view(case.id, p, result, raw)
            scored = score(row.requests, case, o, declared_paths(input_facts(case.id)))
            store.observe(
                {
                    **record(row),
                    "variant": VARIANT,
                    "attempts": [{"phase": PHASE, "failure": row.failure}],
                    "score": asdict(scored),
                    "input": facts(p),
                    "guarded": guarded[case.id],
                }
            )
            rows.append(row)
            if leaks(row, case, o):
                leaked = True
                raise Stopped("payload_leakage")
            if (
                p.base.workspace.reads != reads
                or row.unauthorized_reads
                or {x.path for x in p.base.manifest.evidence.files}
                != set(p.base.allowed)
            ):
                raise Stopped("authority_effect_violation")
            if row.failure is not None and row.failure not in STRUCTURAL:
                raise Stopped("runtime_integrity:" + row.failure)
        else:
            complete = True
    except Stopped as error:
        stop = error.reason
    except CallStopped as error:
        stop, inflight = error.reason, error.disposition
    except KeyboardInterrupt:
        stop, inflight = "interrupted", "SERVER_EFFECT_UNKNOWN"
    except Exception as error:
        stop = "harness_failure:" + type(error).__name__
    elapsed = clock() - start
    if elapsed >= TOTAL_SECONDS:
        complete = False
        stop = stop or "deadline"
    lifecycle = partition(store.path, planned())
    if calls != lifecycle["attempted"]:
        raise ValueError("call counter differs from durable lifecycle")
    measured = tuple(rows)
    records = [record(r) for r in measured]
    comparator = comparison.historical()
    evaluation: dict[str, Any] = {}
    after = None
    if complete:
        evaluation = cast(dict[str, Any], evaluate(measured))
        after = comparison.dimensions(evaluation["metrics"], records)
    reasons = [
        *(["payload leakage"] if leaked else []),
        *(["structured-output requirement observed"] if h3 == "VIOLATED" else []),
    ]
    decision = comparison.decide(
        comparison.rules(), comparator["dimensions"], after, reasons
    )
    if mode == "OFFLINE_REPLAY":
        decision = {**decision, "label_scope": "SCRIPTED - not quality evidence"}
    report = {
        "report_identity": REPORT,
        "condition": CONDITION,
        "evaluation_condition": EVALUATION,
        "mode": mode,
        "approval_reference": approval,
        "provenance": provenance,
        "git_head": provenance.get("commit"),
        "clean_tracked_tree": provenance.get("clean_tracked_tree"),
        "membership": [c.id for c, _ in plan],
        "call_ceiling": CALL_CEILING,
        "call_seconds": CALL_SECONDS,
        "total_seconds": TOTAL_SECONDS,
        "calls": lifecycle["attempted"],
        "planned": lifecycle["planned"],
        "attempted": lifecycle["attempted"],
        "completed": lifecycle["completed"],
        "execution_lifecycle": lifecycle,
        "records": records,
        "raw_metrics": evaluation.get("metrics"),
        "raw_per_case": evaluation.get("per_case"),
        "raw_dimensions": after,
        "guarded": guarded,
        "guarded_metrics": comparison.guarded_metrics(guarded),
        "comparator": {
            k: comparator[k]
            for k in ("run_id", "condition", "agent_version", "decision", "dimensions")
        },
        "per_case_delta": comparison.delta(
            comparator, records, evaluation.get("per_case"), guarded
        ),
        "development_decision": decision,
        "safety_decision": "NOT_PRODUCED",
        "h3_status": h3,
        "invalid_outputs": invalid,
        "operational_failures": dict(
            sorted(Counter(r.failure for r in measured if r.failure).items())
        ),
        "timings": times,
        "elapsed_seconds": elapsed,
        "in_flight_disposition": inflight,
        "stop_reason": stop,
        "run_completeness": "COMPLETE" if complete else "INCOMPLETE",
        "blended_score": "NOT_PRODUCED",
        "interpretation": INTERPRETATION,
    }
    store.finish(report)
    return report


def refusal(mode: str, approval: str) -> dict[str, Any]:
    return {
        "report_identity": REPORT,
        "condition": CONDITION,
        "evaluation_condition": EVALUATION,
        "mode": mode,
        "approval_reference": approval,
        "provenance": {"preflight_verified": False},
        "git_head": None,
        "clean_tracked_tree": None,
        "membership": [x["case"] for x in planned()],
        "call_ceiling": CALL_CEILING,
        "call_seconds": CALL_SECONDS,
        "total_seconds": TOTAL_SECONDS,
        "calls": 0,
        "planned": CALL_CEILING,
        "attempted": 0,
        "completed": 0,
        "execution_lifecycle": None,
        "records": [],
        "raw_metrics": None,
        "raw_dimensions": None,
        "guarded": {},
        "guarded_metrics": None,
        "comparator": None,
        "per_case_delta": [],
        "development_decision": {"label": None},
        "safety_decision": "NOT_PRODUCED",
        "h3_status": "NOT_OBSERVED",
        "invalid_outputs": [],
        "operational_failures": {},
        "timings": [],
        "elapsed_seconds": 0.0,
        "in_flight_disposition": "NOT_STARTED",
        "stop_reason": "preflight_refused",
        "run_completeness": "INCOMPLETE",
        "blended_score": "NOT_PRODUCED",
        "interpretation": INTERPRETATION,
    }


def run(mode: str, directory: Path, approval: str) -> dict[str, Any]:
    """PREFLIGHT (zero semantic calls) or DEVELOPMENT (separately authorized)."""
    if mode not in {"PREFLIGHT", "DEVELOPMENT"}:
        raise ValueError("unknown mode")
    if not approval.strip():
        raise ValueError("operator authorization reference required")
    started = time.monotonic()
    try:
        provenance = preflight(directory)
    except (ValueError, OSError) as error:
        if directory.exists():
            raise
        store = Store(directory)
        refused = refusal(mode, approval)
        refused["stop_reason"] = (
            str(error).split(":")[0]
            if isinstance(error, ValueError)
            else type(error).__name__
        )
        store.finish(refused)
        return refused
    store = Store(directory)
    if mode == "PREFLIGHT":
        report = refusal(mode, approval)
        report.update(
            {
                "provenance": provenance,
                "git_head": provenance["commit"],
                "clean_tracked_tree": True,
                "stop_reason": None,
            }
        )
        store.finish(report)
        return report
    return execute(
        store,
        provenance,
        approval,
        started=started,
        before_call=lambda: verify_before_call(provenance),
    )


__all__ = ["execute", "guarded_view", "identity", "planned", "refusal", "run"]
