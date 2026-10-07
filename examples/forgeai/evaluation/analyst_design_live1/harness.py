"""Sequential evaluation controller; no automatic mode transitions."""

import asyncio
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from analyst_design_eval2.data import Fixture, load
from analyst_design_eval2.runner import Row
from legoai_engineering.analyst.sufficiency import (
    EvidenceManifest,
    EvidenceSufficiencyResult,
)

from analyst_design_live1.identity import (
    PROFILE,
    REPORT,
    SMOKE,
    preflight,
    verify_before_call,
)
from analyst_design_live1.lifecycle import partition
from analyst_design_live1.measurement import interpret
from analyst_design_live1.runtime import CallStopped, projection, supervised
from analyst_design_live1.sequence import run_row
from analyst_design_live1.storage import Store, parsed, verify_smoke


async def execute(
    mode: str,
    store: Store,
    provenance: dict[str, Any],
    approval: str,
    *,
    call: Callable[..., tuple[EvidenceSufficiencyResult, str | None]] = supervised,
    clock: Callable[[], float] = time.monotonic,
    started: float | None = None,
    before_call: Callable[[], None] | None = None,
) -> dict[str, Any]:
    if mode not in {"SMOKE", "FULL"} or not approval.strip():
        raise ValueError("explicit mode and operator approval required")
    if call is supervised and before_call is None:
        raise ValueError("live calls require preflight revalidation")
    start = clock() if started is None else started
    ceiling = 1800 if mode == "SMOKE" else 21600
    budget = 6 if mode == "SMOKE" else 68
    calls = 0
    rows: dict[tuple[str, str], Row] = {}
    times: list[dict[str, Any]] = []
    reasons: list[str] = []
    stop: str | None = None
    complete = False
    inflight = "NONE"
    fixtures = load()
    plan = [(f, o, v) for f, o in fixtures for v in f.variants]
    if mode == "SMOKE":
        plan = [
            next((f, o, "initial") for f, o in fixtures if f.id == case)
            for case in SMOKE
        ]

    def checkpoint(row: Row) -> None:
        store.checkpoint(row)
        rows[(row.case, row.variant)] = row

    async def assess(
        m: EvidenceManifest, f: Fixture, variant: str, phase: str
    ) -> EvidenceSufficiencyResult:
        nonlocal calls, inflight
        remaining = ceiling - (clock() - start) - 2  # reserve bounded client cleanup
        if remaining <= 0:
            raise CallStopped("deadline", "NOT_STARTED")
        if calls >= budget:
            raise CallStopped("call_ceiling", "NOT_STARTED")
        if before_call is not None:
            before_call()
        expected = projection(m, f, variant, phase)
        calls += 1
        begun = clock()
        inflight = "CLIENT_ACTIVE_SERVER_EFFECT_UNKNOWN"
        store.write(
            f"call-{calls:03}-started.json",
            {
                "case": f.id,
                "variant": variant,
                "phase": phase,
                "timeout": min(600.0, remaining),
            },
        )
        diagnostics: dict[str, Any] | None = None
        diagnostic_serial = 0

        def observe(value: dict[str, Any]) -> None:
            nonlocal diagnostics, diagnostic_serial
            diagnostics = value
            diagnostic_serial += 1
            store.write(
                f"call-{calls:03}-diagnostic-{diagnostic_serial:02}.json",
                {"case": f.id, "variant": variant, "phase": phase, **value},
            )

        try:
            if call is supervised:
                result, payload_digest = call(
                    m, expected, min(600.0, remaining), observe=observe
                )
            else:
                result, payload_digest = call(m, expected, min(600.0, remaining))
        except BaseException as error:
            timing = {
                "case": f.id,
                "variant": variant,
                "phase": phase,
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
            store.write(f"call-{calls:03}-finished.json", timing)
            raise
        inflight = "CLIENT_COMPLETED"
        timing = {
            "case": f.id,
            "variant": variant,
            "phase": phase,
            "seconds": clock() - begun,
            "user_payload_digest": payload_digest,
            "failure": result.failure.value if result.failure else None,
        }
        if diagnostics is not None:
            timing["child_diagnostics"] = diagnostics
        times.append(timing)
        store.write(f"call-{calls:03}-finished.json", timing)
        return result

    try:
        for f, o, variant in plan:
            if clock() - start >= ceiling - 2:
                raise CallStopped("deadline", "NOT_STARTED")
            row = await run_row(
                f, o, variant, assess, smoke=mode == "SMOKE", checkpoint=checkpoint
            )
            status = interpret(
                tuple(rows.values()), complete=False, smoke=mode == "SMOKE"
            )
            outcome = status["sufficiency_profile_outcome"]
            if outcome.endswith("UNSAFE"):
                stop = "safety_failure"
                break
            if any(a.failure == "model_failure" for a in row.attempts):
                reasons.append("model_failure")
                stop = "model_failure"
                break
            if mode == "SMOKE" and any(not a.valid for a in row.attempts):
                stop = "invalid_output"
                break
        else:
            complete = True
    except CallStopped as error:
        stop, inflight = error.reason, error.disposition
        if stop not in {"deadline", "interrupted"}:
            reasons.append(stop)
    except KeyboardInterrupt:
        stop, inflight = "interrupted", "SERVER_EFFECT_UNKNOWN"
    except Exception as error:
        stop = "harness_or_leakage_failure"
        reasons.append(type(error).__name__)
    if clock() - start >= ceiling:
        complete = False
        stop = stop or "deadline"
    observed = tuple(rows.values())
    result = interpret(
        observed,
        complete=complete,
        runtime_failures=tuple(reasons),
        smoke=mode == "SMOKE",
    )
    smoke_status = None
    if mode == "SMOKE":
        outcome = result["sufficiency_profile_outcome"]
        if outcome.endswith("UNSAFE"):
            smoke_status = "SMOKE_SAFETY_FAILURE"
        elif outcome.endswith("CONTRACT_FAILED"):
            smoke_status = "SMOKE_CONTRACT_FAILURE"
        elif reasons or not complete:
            smoke_status = "SMOKE_RUNTIME_FAILURE"
        elif len({r.attempts[0].disposition for r in observed}) == 1:
            smoke_status = "SMOKE_CONDITION_INVALID"
            stop = "uniform_disposition"
        else:
            smoke_status = "SMOKE_PASS — FULL RUN STILL REQUIRES EXPLICIT APPROVAL"
    from analyst_design_eval2.metrics import phases

    slots = []
    for f, _o, variant in plan:
        recorded = rows.get((f.id, variant))
        completed_phases = {a.phase for a in recorded.attempts} if recorded else set()
        for phase in ("initial",) if mode == "SMOKE" else phases(f, variant):
            slots.append(
                {
                    "case": f.id,
                    "variant": variant,
                    "phase": phase,
                    "status": "RECORDED"
                    if phase in completed_phases
                    else "NOT_RECORDED",
                    "reason": None
                    if phase in completed_phases
                    else stop or "bounded_sequence_terminal",
                }
            )
    # d27/d28 are semantic controls, not model-call opportunities.
    controls = {
        f.id
        for f, _o, _v in plan
        if f.failure in {"stale_assessment", "budget_exhausted"}
    }
    lifecycle = partition(store.path, [s for s in slots if s["case"] not in controls])
    if calls != lifecycle["attempted"]:
        raise ValueError("call counter differs from durable lifecycle")
    report = {
        "report_identity": REPORT,
        "sufficiency_profile_identity": PROFILE,
        "revision_2_condition_identity": "forgeai-analyst-design-eval/2",
        "run_id": store.path.name,
        "mode": mode,
        "approval_reference": approval,
        "provenance": provenance,
        "calls": lifecycle["attempted"],
        "execution_lifecycle": lifecycle,
        "call_ceiling": budget,
        "elapsed_seconds": clock() - start,
        "timings": times,
        "in_flight_disposition": inflight,
        "stop_reason": stop,
        "records": [parsed(r) for r in observed],
        "smoke_status": smoke_status,
        "planned_slots": slots,
        "not_run": [
            f"{f.id}/{v}"
            for f, o, v in plan
            if f.id not in controls
            and not any(
                s["identity"].startswith(f"{f.id}/{v}/")
                and s["attempt_state"] != "NEVER_ATTEMPTED"
                for s in lifecycle["slots"]
            )
        ],
        **result,
    }
    store.finish(report)
    return report


def run(
    mode: str, directory: Path, approval: str, *, smoke_report: Path | None = None
) -> dict[str, Any]:
    import json

    if mode not in {"PREFLIGHT", "SMOKE", "FULL"}:
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
        result = {
            "report_identity": REPORT,
            "run_id": directory.name,
            "mode": mode,
            "provenance": {"preflight_verified": False},
            "calls": 0,
            "stop_reason": str(error)
            if isinstance(error, ValueError)
            else type(error).__name__,
            "smoke_status": "SMOKE_CONDITION_INVALID" if mode == "SMOKE" else None,
            **interpret((), complete=False, runtime_failures=("preflight_refused",)),
        }
        store.finish(result)
        return result
    if mode == "FULL":
        if smoke_report is None:
            raise ValueError("passing smoke report required")
        smoke = json.loads(smoke_report.read_text(encoding="utf-8"))
        verify_smoke(smoke, provenance)
        provenance = {**provenance, "smoke_run_id": smoke["run_id"]}
    store = Store(directory)
    if mode == "PREFLIGHT":
        report = {
            "report_identity": REPORT,
            "run_id": directory.name,
            "mode": mode,
            "provenance": provenance,
            "calls": 0,
            **interpret((), complete=False),
        }
        store.finish(report)
        return report
    return asyncio.run(
        execute(
            mode,
            store,
            provenance,
            approval,
            started=started,
            before_call=lambda: verify_before_call(provenance),
        )
    )
