"""V3 binding of v2 runner.py:1-437; SCREEN-2A safeguards, v1 screening.

Orchestration differs for v3 manifest identity, Phase A provenance and repeats.
Identical status, custody, pacing and refusal helpers are imported, not forked.
"""

import asyncio
import json
import sys
import tempfile
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

from legoai.intelligence.model.values import ModelId
from legoai.runtime._composition.provider_discovery import (
    discovery_consumer,
    discovery_purpose,
)
from legoai.runtime._composition.secret import _provision_interactively
from legoai.runtime.api import HostError, HostFailure, RemoteModelRuntime
from legoai.runtime.local import open_credential_source, open_local_host
from scripts import kisski_compatibility_probe as legacy
from scripts import kisski_saia_qualification as saia
from scripts.kisski_coding_eval.pack import Task
from scripts.kisski_coding_eval.runner import (
    SelectionError,
    reliability,
    screening,
    selected,
)
from scripts.kisski_dev_screen.runner import (
    INTERVALS,
    MIN_INTERVAL_SECONDS,
    RAW_AUTHORIZATION,
    PreCallRefusal,
    RefusalReason,
    SafeParser,
    closed_http_status,
    http_status,
    outside_repository,
    pace,
    save,
)

from .frozen import ManifestNotFrozen, verify
from .invocation import invoke
from .pack import OBSERVED, OUTPUT_TOKENS, TASKS, VERSION, digest
from .scoring import empty, summarize

NOTICE = "Frozen synthetic eligibility only; separate admission review required."


def authorization(phase: str) -> str:
    return f"AUTHORIZE {VERSION} PHASE {phase} LIVE SYNTHETIC"


def schedule(phase: str) -> tuple[tuple[Task, int], ...]:
    if phase not in ("A", "B"):
        raise ValueError("PHASE_INVALID")
    return tuple(
        (task, repeat)
        for task in TASKS
        if task.phase == phase
        for repeat in range(1, (1 if phase == "A" else 2) + 1)
    )


def plan(phase: str, interval: int = MIN_INTERVAL_SECONDS) -> dict[str, Any]:
    if type(interval) is not int or interval not in INTERVALS:
        raise ValueError("MIN_INTERVAL_INVALID")
    maximum = 5 if phase == "A" else 2
    calls = len(schedule(phase)) * maximum
    return {
        "evaluation": VERSION,
        "phase": phase,
        "notice": NOTICE,
        "admission_effect": "NONE",
        "pack_digest": digest(),
        "observed_candidates": OBSERVED,
        "tasks": [task.task_id for task in TASKS if task.phase == phase],
        "repetitions": 1 if phase == "A" else 2,
        "maximum_models": maximum,
        "maximum_discovery_calls": 1,
        "maximum_chat_calls": calls,
        "output_tokens": OUTPUT_TOKENS,
        "timeout_seconds": 60,
        "min_interval_seconds": interval,
        "estimated_minimum_duration_seconds": (calls - 1) * interval,
        "authorization": authorization(phase),
    }


def prior_report(path: Path, manifest: str) -> list[dict[str, Any]]:
    """V1 runner.py:138-231 boundary adapted to v3 identity and safe score fields.

    Reports are operator custody, not authenticated authority. Import only the
    closed Phase A score projection needed for screening and final qualification.
    """
    if path.is_symlink() or path.stat().st_size > 262144:
        raise ValueError("PRIOR_REPORT_INVALID")
    value = json.loads(path.read_bytes())
    if (
        type(value) is not dict
        or value.get("evaluation") != VERSION
        or value.get("pack_digest") != digest()
        or value.get("manifest_digest") != manifest
        or value.get("phase") != "A"
        or value.get("admission_effect") != "NONE"
    ):
        raise ValueError("PRIOR_REPORT_INVALID")
    rows = value.get("records")
    if type(rows) is not list or not 1 <= len(rows) <= 20:
        raise ValueError("PRIOR_REPORT_INVALID")
    tasks = {task.task_id: task for task in TASKS if task.phase == "A"}
    seen: set[tuple[str, str]] = set()
    accepted: list[dict[str, Any]] = []
    for row in rows:
        if type(row) is not dict:
            raise ValueError("PRIOR_REPORT_INVALID")
        task_id = row.get("task_id")
        if not isinstance(task_id, str):
            raise ValueError("PRIOR_REPORT_INVALID")
        task = tasks.get(task_id)
        model = row.get("model_id")
        if task is None or model not in OBSERVED:
            raise ValueError("PRIOR_REPORT_INVALID")
        if (model, task.task_id) in seen:
            raise ValueError("PRIOR_REPORT_INVALID")
        seen.add((model, task.task_id))
        if (
            row.get("phase") != "A"
            or row.get("role") != "coding"
            or type(row.get("repeat")) is not int
            or row["repeat"] != 1
            or row.get("invocation_outcome") != "completed"
        ):
            raise ValueError("PRIOR_REPORT_INVALID")
        clean = empty(task)
        for name, default in clean.items():
            if type(default) is bool:
                if type(row.get(name)) is not bool:
                    raise ValueError("PRIOR_REPORT_INVALID")
                clean[name] = row[name]
        for name in ("patch_applies", "targeted_tests_pass", "regression_tests_pass"):
            item = row.get(name)
            if item is not None and type(item) is not bool:
                raise ValueError("PRIOR_REPORT_INVALID")
            clean[name] = item
        clean.update(model_id=model, repeat=1, invocation_outcome="completed")
        accepted.append(clean)
    if len({row["model_id"] for row in accepted}) > 5:
        raise ValueError("PRIOR_REPORT_INVALID")
    return accepted


def retain(custody: Path, index: int, task_id: str, repeat: int, raw: str) -> None:
    """SCREEN-2A runner.py:201-214, with repeat in the exclusive filename."""
    custody = outside_repository(custody)
    directory = custody / "raw"
    if directory.is_symlink():
        raise ValueError("RAW_DIRECTORY_LINK")
    directory.mkdir(exist_ok=True)
    if directory.resolve().parent != custody:
        raise ValueError("RAW_DIRECTORY_ESCAPE")
    if (
        not 0 <= index < 5
        or task_id not in {task.task_id for task in TASKS}
        or repeat not in (1, 2)
    ):
        raise ValueError("RAW_IDENTITY_INVALID")
    with (directory / f"{index}-{task_id}-{repeat}.txt").open(
        "x", encoding="utf-8", newline=""
    ) as handle:
        handle.write(raw)


def live(
    phase: str,
    custody: Path,
    interval: int = MIN_INTERVAL_SECONDS,
    retain_raw: bool = False,
    previous_path: Path | None = None,
) -> bool:
    manifest = verify()
    plan(phase, interval)
    custody = outside_repository(custody)
    jobs = schedule(phase)
    previous: list[dict[str, Any]] = []
    if phase == "B":
        path = previous_path or Path(input("V3 Phase A report path: "))
        previous = prior_report(path, manifest)
    eligible = (
        set(OBSERVED)
        if phase == "A"
        else {model for model in OBSERVED if screening(previous, model)}
    )
    if not eligible:
        raise PreCallRefusal(RefusalReason.CANDIDATES)
    config = replace(saia.live_config(custody), max_output_tokens=OUTPUT_TOKENS)
    models: tuple[str, ...] = ()
    records: list[dict[str, Any]] = []
    completed = False
    stopped_reason: str | None = None
    discovery: dict[str, Any] = {
        "discovery_classification": None,
        "discovery_outcome": None,
        "discovery_http_status": None,
    }
    starts = 0
    previous_start: float | None = None

    def persist() -> None:
        save(
            custody,
            {
                "evaluation": VERSION,
                "pack_digest": digest(),
                "manifest_digest": manifest,
                "phase": phase,
                "admission_effect": "NONE",
                "notice": NOTICE,
                "completed": completed,
                "records": records,
                "summaries": {
                    model: summarize([r for r in records if r["model_id"] == model])
                    for model in models
                },
                "reliability": {
                    model: reliability([r for r in records if r["model_id"] == model])
                    for model in models
                },
                "min_interval_seconds": interval,
                "stopped_reason": stopped_reason,
                "chats_not_attempted": len(models) * len(jobs) - starts,
                **discovery,
            },
        )

    persist()
    source = open_credential_source(legacy._scope())
    try:
        owned = cast(Any, source)._source
        ref = _provision_interactively(
            owned, "eval-v3-discovery", discovery_purpose(), discovery_consumer()
        )

        def now() -> datetime:
            return datetime.now(UTC)

        discovered = legacy._discover(config, owned, ref, now(), now)
        classification = legacy.classify_discovery(discovered)
        status = closed_http_status(discovered.status)
        discovery.update(
            discovery_classification=classification.value if classification else None,
            discovery_outcome=discovered.outcome.value,
            discovery_http_status=status if isinstance(status, int) else None,
        )
        if classification is not None:
            raise PreCallRefusal(RefusalReason.DISCOVERY)
        available = {m.value for m in discovered.models} & eligible & set(OBSERVED)
        print("Eligible exact IDs: " + json.dumps(sorted(available)))
        try:
            models = selected(
                input("Comma-separated exact model IDs (no quotes): "),
                available,
                phase,
                eligible,
            )
        except SelectionError:
            raise PreCallRefusal(RefusalReason.CANDIDATES) from None
        print(f"Frozen bound: {len(models) * len(jobs)} chats; no retries or expansion")
        if input("Approve this bounded SYNTHETIC phase? [y/N] ") != "y":
            raise PreCallRefusal(RefusalReason.AUTHORIZATION)
        records.extend(row for row in previous if row["model_id"] in models)
        credential = source.provision("eval-v3-chat")

        async def run_model(index: int, model: str) -> bool:
            nonlocal starts, previous_start, stopped_reason
            model_custody = custody / f"model-{index}"
            model_custody.mkdir()
            host = open_local_host(
                replace(
                    saia.host_config(config, credential, ModelId(model), now()),
                    max_executions=len(jobs),
                ),
                {"revision": "r1", "binding": legacy.BINDING},
                clock=now,
                remote=RemoteModelRuntime(
                    source, model_custody, config.margin, config.trust_anchor
                ),
            )
            for task, repeat in jobs:
                raw: str | None = None
                previous_start = await pace(previous_start, interval)
                starts += 1
                try:
                    row, raw = await invoke(host, config, task)
                except Exception as error:
                    row = empty(task)
                    row.update(
                        invocation_outcome="invocation_error",
                        failure_category=(
                            error.failure.value
                            if isinstance(error, HostError)
                            else "OTHER"
                        ),
                        failure_effect=(
                            "NONE"
                            if isinstance(error, HostError)
                            and error.failure is HostFailure.WRONG_EVENT_LOOP
                            else "UNKNOWN"
                        ),
                        output_tokens=None,
                    )
                row["http_status"] = http_status(host, row)
                if row["http_status"] == 429:
                    stopped_reason = "RATE_LIMITED"
                elif row["http_status"] == 503:
                    stopped_reason = "SERVICE_UNAVAILABLE"
                row.update(model_id=model, repeat=repeat)
                records.append(row)
                persist()
                if retain_raw and raw is not None:
                    retain(custody, index, task.task_id, repeat, raw)
                print(
                    json.dumps(
                        {
                            "model": model,
                            "task": task.task_id,
                            "repeat": repeat,
                            "outcome": row["invocation_outcome"],
                        }
                    )
                )
                if stopped_reason or row["invocation_outcome"] != "completed":
                    return False
            return True

        all_completed = True
        for index, model in enumerate(models):
            model_completed = asyncio.run(run_model(index, model))
            all_completed = all_completed and model_completed
            if stopped_reason:
                break
        completed = all_completed
        return completed
    finally:
        try:
            source.close()
        finally:
            persist()
            print(
                json.dumps(
                    {
                        "stopped_reason": stopped_reason,
                        "chats_not_attempted": len(models) * len(jobs) - starts,
                        **discovery,
                    }
                )
            )
            print("Derived evidence: " + str(custody / "evaluation.json"))


def main(options: list[str] | None = None) -> int:
    parser = SafeParser(allow_abbrev=False)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--plan", action="store_true")
    group.add_argument("--live", action="store_true")
    parser.add_argument("--phase", choices=("A", "B"), default="A")
    parser.add_argument("--phase-a-report", type=Path)
    parser.add_argument("--retain-raw", action="store_true")
    parser.add_argument(
        "--min-interval-seconds",
        type=int,
        choices=INTERVALS,
        default=MIN_INTERVAL_SECONDS,
    )
    args = parser.parse_args(options)
    try:
        print(json.dumps(plan(args.phase, args.min_interval_seconds), indent=2))
        if not args.live:
            return 0
        verify()
        if not sys.stdin.isatty() or not sys.stdout.isatty():
            raise PreCallRefusal(RefusalReason.TERMINAL)
        if input("Type exact authorization: ") != authorization(args.phase):
            raise PreCallRefusal(RefusalReason.AUTHORIZATION)
        if (
            args.retain_raw
            and input("Type raw retention confirmation: ") != RAW_AUTHORIZATION
        ):
            raise PreCallRefusal(RefusalReason.RAW)
        outside_repository(Path(tempfile.gettempdir()))
        custody = outside_repository(Path(tempfile.mkdtemp(prefix="kisski-eval-v3-")))
        print("Local custody directory: " + str(custody))
        return (
            0
            if live(
                args.phase,
                custody,
                args.min_interval_seconds,
                args.retain_raw,
                args.phase_a_report,
            )
            else 2
        )
    except ManifestNotFrozen:
        print("MANIFEST_NOT_FROZEN")
        return 2
    except PreCallRefusal as error:
        print(error.reason.value)
        return 2
    except Exception, KeyboardInterrupt:
        print("RESULT_INCONCLUSIVE; no retry; raw error suppressed; retain custody")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
