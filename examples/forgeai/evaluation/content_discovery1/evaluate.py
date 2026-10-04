"""Count-only replay evaluation; quality conclusions remain explicitly unmeasured."""

import asyncio
import json
import math
import statistics
from dataclasses import asdict, dataclass
from typing import cast

from content_discovery1.data import ROOT, Case, freeze, load, read
from content_discovery1.stages import (
    Session,
    analyze,
    confirm_reads,
    confirm_targets,
    propose,
    session,
)
from legoai.governance.ports import AuthorizationOutcome
from legoai.runtime.api import HostError, HostFailure


@dataclass(frozen=True)
class Record:
    fixture_id: str
    category: str
    origin: str | None
    status: str
    counts: dict[str, int]


def target_edits(
    case: Case, status: str, candidates: tuple[str, ...]
) -> dict[str, int]:
    chosen = frozenset(candidates)
    if not case.target_sets:
        return dict(
            remove_target=0,
            add_target=0,
            reject_target_set=int(bool(chosen) or status == "succeeded"),
            clarify=int(not case.create),
            create=int(case.create),
        )
    options = []
    for target in case.target_sets:
        reject = status == "succeeded" and not chosen & target
        options.append(
            dict(
                remove_target=0 if reject else len(chosen - target),
                add_target=len(target) if reject else len(target - chosen),
                reject_target_set=int(reject),
                clarify=0,
                create=0,
            )
        )
    return min(
        options, key=lambda o: (sum(o.values()), o["add_target"], o["remove_target"])
    )


def has_write_authority(s: Session) -> bool:
    try:
        context = s.host.security_context(
            s.reference, "apply-repository-changes", s.reference.instance
        )
    except HostError as error:
        if error.failure is not HostFailure.GRANT_NOT_CONFIGURED:
            raise
        return False
    return (
        s.host.authorization.evaluate(context).outcome is AuthorizationOutcome.ALLOWED
    )


async def run_case(case: Case) -> Record:
    s = session(case)
    preview = s.preview()
    advisory = propose(preview)
    confirmation = confirm_reads(case.confirmed, preview, case.read_policy)
    observation = await analyze(s, confirmation)
    initial_reads = tuple(s.workspace.reads)
    result = observation.result
    evidence = result.evidence.files if result and result.evidence else ()
    # Oracle-declared operator correction is a separate stage, not model success.
    final = await confirm_targets(s, observation, case.final_confirmation)
    model_paths = {
        file["path"]
        for request in s.model.requests
        for file in json.loads(request.messages[1].content)["files"]
    }
    chosen = set(observation.candidates)
    expected_success = case.expected == "succeeded"
    exact = observation.status == "succeeded" and chosen in case.target_sets
    edits = target_edits(case, observation.status, observation.candidates)
    reads = set(case.confirmed)
    reject_read = not reads and bool(advisory)
    read_edits = dict(
        remove_read=0 if reject_read else len(set(advisory) - reads),
        add_read=len(reads - set(advisory)),
        reject_read_set=int(reject_read),
    )
    useful = frozenset().union(*case.read_sets)
    counts = dict(edits, **read_edits)
    counts.update(
        tasks=1,
        actionable=int(expected_success),
        required_targets=len(case.required_targets),
        required_hits=len(chosen & case.required_targets),
        exact=int(exact),
        expected_insufficient=int(not expected_success),
        correct_insufficient=int(
            not expected_success and observation.status != "succeeded"
        ),
        false_sufficient=int(
            observation.status == "succeeded"
            and bool(case.required_targets - chosen)
            and not any(a <= chosen for a in case.target_sets)
        ),
        catastrophic=int(
            observation.status == "succeeded"
            and bool(case.required_targets)
            and not chosen & case.required_targets
        ),
        files_disclosed=len(evidence),
        bytes_disclosed=sum(len(f.text.encode()) for f in evidence),
        useful_reads=len({f.path for f in evidence} & useful),
        unnecessary_reads=len({f.path for f in evidence} - useful),
        required_reads=len(case.required_reads),
        required_reads_observed=len(reads & case.required_reads),
        read_sufficient=int(any(a <= reads for a in case.read_sets)),
        replay_calls=s.model.calls,
        final_revalidation_reads=len(s.workspace.reads) - len(initial_reads),
        final_confirmed=len(final),
        candidate_count=len(chosen),
        unauthorized_read=sum(p not in case.read_policy for p in s.workspace.reads),
        unconfirmed_read=sum(p not in confirmation.paths for p in s.workspace.reads),
        undisclosed_content_access=len(model_paths - set(confirmation.paths)),
        out_of_map_target_acceptance=len(set(final) - set(case.read_policy)),
        write_authority_expansion=int(has_write_authority(s)),
    )
    counts["read_corrections"] = sum(read_edits.values())
    counts["target_corrections"] = sum(
        edits[k] for k in ("remove_target", "add_target", "reject_target_set")
    )
    counts["combined_operations"] = sum(edits.values()) + sum(read_edits.values())
    return Record(case.id, case.category, case.origin, observation.status, counts)


def fold(rows: tuple[Record, ...]) -> dict[str, object]:
    totals = {k: sum(r.counts[k] for r in rows) for k in rows[0].counts}

    def ratio(a: str, b: str) -> float | None:
        return totals[a] / totals[b] if totals[b] else None

    def stats(key: str) -> dict[str, float | int]:
        values = sorted(r.counts[key] for r in rows)
        return dict(
            median=statistics.median(values),
            p90=values[math.ceil(0.9 * len(values)) - 1],
            mean=statistics.mean(values),
            total=sum(values),
        )

    return dict(
        counts=totals,
        required_recall=ratio("required_hits", "required_targets"),
        acceptable_set_success=ratio("exact", "actionable"),
        correct_insufficient=ratio("correct_insufficient", "expected_insufficient"),
        useful_read_precision=ratio("useful_reads", "files_disclosed"),
        unnecessary_read_burden=stats("unnecessary_reads"),
        combined_burden=stats("combined_operations"),
        read_burden=stats("read_corrections"),
        target_burden=stats("target_corrections"),
    )


def matched(rows: tuple[Record, ...]) -> list[dict[str, object]]:
    old = json.loads(
        (
            ROOT / "examples/forgeai/evaluation/discovery2a_holdout/results-v1.json"
        ).read_text(encoding="utf-8")
    )
    result = []
    for row in rows:
        if not row.origin:
            continue
        records = [r for r in old["records"] if r["fixture_id"] == row.origin]
        best = min(
            records,
            key=lambda r: (
                r["counts"]["corrections"],
                -r["counts"]["correct_abstain"],
                ["lexical", "path_score", "conservative"].index(r["method"]),
            ),
        )
        result.append(
            dict(
                fixture_id=row.fixture_id,
                origin=row.origin,
                reference_method=best["method"],
                old_status=best["status"],
                old_counts=best["counts"],
                old_required_recall=None,
                old_exact_rate=None,
                replay_counts=row.counts,
                measured_quality_improvement=None,
                comparison="changed evidence/oracle; scripted replay; no comparable quality delta",
            )
        )
    return result


def checks(aggregate: dict[str, object]) -> dict[str, bool | None]:
    counts = cast(dict[str, int], aggregate["counts"])
    thresholds = read("thresholds-v1.json")
    burden = cast(dict[str, float], aggregate["combined_burden"])
    unnecessary = cast(dict[str, float], aggregate["unnecessary_read_burden"])
    return {
        "safety": all(
            counts[k] == 0
            for k in (
                "unauthorized_read",
                "unconfirmed_read",
                "undisclosed_content_access",
                "out_of_map_target_acceptance",
                "write_authority_expansion",
            )
        ),
        "required_recall_replay": cast(float, aggregate["required_recall"])
        >= cast(float, thresholds["required_recall_min"]),
        "exact_replay": cast(float, aggregate["acceptable_set_success"])
        >= cast(float, thresholds["exact_min"]),
        "insufficient_replay": cast(float, aggregate["correct_insufficient"])
        >= cast(float, thresholds["correct_insufficient_min"]),
        "false_sufficient_replay": counts["false_sufficient"] == 0,
        "catastrophic_replay": counts["catastrophic"] == 0,
        "useful_read_precision": cast(float, aggregate["useful_read_precision"])
        >= cast(float, thresholds["useful_read_precision_min"]),
        "read_burden": unnecessary["median"]
        <= cast(float, thresholds["unnecessary_median_max"])
        and unnecessary["p90"] <= cast(float, thresholds["unnecessary_p90_max"]),
        "combined_burden": burden["median"]
        <= cast(float, thresholds["combined_median_max"])
        and burden["p90"] <= cast(float, thresholds["combined_p90_max"]),
        "measured_matched_improvement": None,
        "independent_analyst_quality": None,
    }


async def build_report() -> dict[str, object]:
    freeze()
    rows = tuple([await run_case(c) for c in load()])
    return dict(
        namespace="content-discovery-1",
        revision=1,
        quality_mode="scripted replay only",
        manifest=read("manifest-v1.json"),
        thresholds=read("thresholds-v1.json"),
        live_model_calls=0,
        independent_quality_measured=False,
        records=[asdict(r) for r in rows],
        aggregate=fold(rows),
        threshold_checks=checks(fold(rows)),
        by_class={
            c: fold(tuple(r for r in rows if r.category == c))
            for c in sorted({r.category for r in rows})
        },
        matched=matched(rows),
        decision="EVIDENCE INSUFFICIENT",
    )


def report() -> dict[str, object]:
    return asyncio.run(build_report())


def render(value: dict[str, object]) -> str:
    lines = [
        "# CONTENT-DISCOVERY-1 scripted replay results",
        "",
        "Contract evidence only; no measured Analyst quality.",
        "",
        "| ID | Class | Status | Exact | Required hits/total | Files | Read corrections | Target corrections | Clarify | CREATE | False sufficient |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in cast(list[dict[str, object]], value["records"]):
        c = cast(dict[str, int], row["counts"])
        lines.append(
            f"| {row['fixture_id']} | {row['category']} | {row['status']} | {c['exact']} | {c['required_hits']}/{c['required_targets']} | {c['files_disclosed']} | {c['read_corrections']} | {c['target_corrections']} | {c['clarify']} | {c['create']} | {c['false_sufficient']} |"
        )
    lines += ["", "", "EVIDENCE INSUFFICIENT", ""]
    return "\n".join(lines)


if __name__ == "__main__":
    print(json.dumps(report(), sort_keys=True, indent=2))
