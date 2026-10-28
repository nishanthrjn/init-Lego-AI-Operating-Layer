"""Attended synthetic diagnosis; no admission authority, retry or fallback."""

import argparse
import asyncio
import json
import sys
import tempfile
import time
from dataclasses import replace
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any, NoReturn, cast

from legoai.execution.values import ExecutionId
from legoai.intelligence.model.values import ModelId
from legoai.runtime._composition.provider_discovery import (
    discovery_consumer,
    discovery_purpose,
)
from legoai.runtime._composition.secret import _provision_interactively
from legoai.runtime.api import HostError, HostFailure, RemoteModelRuntime
from legoai.runtime.local import (
    _remote_chat_http_status,
    open_credential_source,
    open_local_host,
)
from scripts import kisski_compatibility_probe as legacy
from scripts import kisski_saia_qualification as saia
from scripts.kisski_coding_eval.frozen import verify
from scripts.kisski_coding_eval.pack import OUTPUT_TOKENS, TASKS, Task
from scripts.kisski_coding_eval.scoring import empty

from .diagnostics import (
    EVALUATION,
    NOTICE,
    configuration,
    diagnose,
    report,
    unevaluated,
)
from .invocation import invoke

ROOT = Path(__file__).resolve().parents[2]
CANDIDATES = Path(__file__).with_name("candidates.json")
RAW_AUTHORIZATION = "RETAIN RAW SYNTHETIC OUTPUTS LOCALLY"
MIN_INTERVAL_SECONDS = 20
INTERVALS = (0, 10, 20, 30, 60)


class RefusalReason(Enum):
    CANDIDATES = "CANDIDATES_NOT_SELECTED"
    AUTHORIZATION = "AUTHORIZATION_DECLINED"
    TERMINAL = "NOT_INTERACTIVE"
    CUSTODY = "CUSTODY_INSIDE_REPOSITORY"
    RAW = "RAW_RETENTION_NOT_CONFIRMED"
    DISCOVERY = "DISCOVERY_FAILED"


class PreCallRefusal(ValueError):
    def __init__(self, reason: RefusalReason) -> None:
        self.reason = reason
        super().__init__(reason.value)


def authorization(phase: str) -> str:
    return f"AUTHORIZE {EVALUATION} PHASE {phase} LIVE SYNTHETIC"


def candidates(*, live: bool) -> tuple[str, ...]:
    if CANDIDATES.is_symlink():
        raise ValueError("CANDIDATES_INVALID")
    with CANDIDATES.open("rb") as handle:
        raw = handle.read(4097)
    if len(raw) > 4096:
        raise ValueError("CANDIDATES_INVALID")
    value = json.loads(raw)
    if (
        not isinstance(value, list)
        or not 1 <= len(value) <= 5
        or any(
            not isinstance(model, str)
            or not 1 <= len(model) <= 256
            or model != model.strip()
            or "," in model
            or model.startswith(("'", '"'))
            or model.endswith(("'", '"'))
            or any(ord(c) < 32 or ord(c) == 127 for c in model)
            for model in value
        )
        or len(set(value)) != len(value)
    ):
        raise ValueError("CANDIDATES_INVALID")
    models = tuple(cast(list[str], value))
    if live and any(
        marker in model.upper()
        for model in models
        for marker in ("REPLACE", "PLACEHOLDER", "EXACT_MODEL_ID", "TODO")
    ):
        raise ValueError("CANDIDATES_PLACEHOLDER")
    return models


def selected(
    answer: str, listed: tuple[str, ...], discovered: set[str]
) -> tuple[str, ...]:
    models = tuple(item.strip() for item in answer.split(","))
    if (
        not 1 <= len(models) <= 5
        or len(set(models)) != len(models)
        or not set(models) <= set(listed) & discovered
    ):
        raise ValueError("MODEL_SELECTION_INVALID")
    return models


def plan(
    phase: str,
    models: tuple[str, ...],
    output_tokens: int,
    min_interval_seconds: int = MIN_INTERVAL_SECONDS,
) -> dict[str, Any]:
    if type(min_interval_seconds) is not int or min_interval_seconds not in INTERVALS:
        raise ValueError("MIN_INTERVAL_INVALID")
    tasks = [t.task_id for t in TASKS if t.phase == phase]
    if phase not in ("A", "B") or len(tasks) != 4:
        raise ValueError("PHASE_INVALID")
    return {
        "evaluation": EVALUATION,
        "notice": NOTICE,
        "admission_effect": "NONE",
        "phase": phase,
        "screening_bypassed": True,
        "configuration": configuration(output_tokens),
        "models": models,
        "tasks": tasks,
        "maximum_chat_calls": len(models) * len(tasks),
        "min_interval_seconds": min_interval_seconds,
        "estimated_minimum_duration_seconds": (
            max(0, len(models) * len(tasks) - 1) * min_interval_seconds
        ),
        "maximum_discovery_calls": 1,
        "output_tokens": output_tokens,
        "timeout_seconds": 60,
        "authorization": authorization(phase),
    }


def outside_repository(path: Path) -> Path:
    resolved = path.resolve()
    if resolved.is_relative_to(ROOT.resolve()):
        raise PreCallRefusal(RefusalReason.CUSTODY)
    if path.is_symlink():
        raise ValueError("CUSTODY_LINK")
    return resolved


def http_status(host: Any, row: dict[str, Any]) -> int | str | None:
    """Same execution-scoped observation as saia.chat_once; no HTTP body access."""
    identity = row.get("execution_id")
    if not isinstance(identity, str):
        return None
    try:
        # invoke returns context.execution_id.value; reconstruct the same value.
        status = _remote_chat_http_status(host, ExecutionId(identity))
    except Exception:
        return None
    return closed_http_status(status)


def closed_http_status(status: object) -> int | str | None:
    if status is None:
        return None
    if type(status) is int and status in (
        200,
        400,
        401,
        403,
        404,
        408,
        409,
        413,
        422,
        429,
        500,
        502,
        503,
        504,
    ):
        return status
    return "OTHER"


async def pace(previous_start: float | None, interval: int) -> float:
    if previous_start is not None and interval:
        while (remaining := previous_start + interval - time.monotonic()) > 0:
            await asyncio.sleep(remaining)
    return time.monotonic()


def retain(custody: Path, index: int, task: Task, raw: str) -> None:
    custody = outside_repository(custody)
    if not 0 <= index < 5 or task not in TASKS:
        raise ValueError("RAW_IDENTITY_INVALID")
    directory = custody / "raw"
    if directory.is_symlink():
        raise ValueError("RAW_DIRECTORY_LINK")
    directory.mkdir(exist_ok=True)
    if directory.resolve().parent != custody:
        raise ValueError("RAW_DIRECTORY_ESCAPE")
    with (directory / f"{index}-{task.task_id}.txt").open(
        "x", encoding="utf-8", newline=""
    ) as handle:
        handle.write(raw)


def save(custody: Path, value: dict[str, Any]) -> None:
    custody = outside_repository(custody)
    temporary = custody / "evaluation.tmp"
    with temporary.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(value, sort_keys=True, indent=2) + "\n")
    temporary.replace(custody / "evaluation.json")


def live(
    phase: str,
    custody: Path,
    listed: tuple[str, ...],
    output_tokens: int,
    retain_raw: bool,
    manifest_digest: str,
    min_interval_seconds: int = MIN_INTERVAL_SECONDS,
) -> bool:
    """CLI has already checked both typed gates, TTY, candidates and integrity."""
    custody = outside_repository(custody)
    plan(phase, listed, output_tokens, min_interval_seconds)
    tasks = tuple(t for t in TASKS if t.phase == phase)
    config = replace(saia.live_config(custody), max_output_tokens=output_tokens)
    rows: list[dict[str, Any]] = []
    models: tuple[str, ...] = ()
    completed = False
    stopped_reason: str | None = None
    previous_start: float | None = None
    chats_started = 0
    discovery_classification: str | None = None
    discovery_outcome: str | None = None
    discovery_http_status: int | None = None

    def persist() -> None:
        value = report(
            phase,
            rows,
            manifest_digest,
            output_tokens,
            models,
            completed=completed,
        )
        value.update(
            min_interval_seconds=min_interval_seconds,
            stopped_reason=stopped_reason,
            chats_not_attempted=len(models) * len(tasks) - chats_started,
            discovery_classification=discovery_classification,
            discovery_outcome=discovery_outcome,
            discovery_http_status=discovery_http_status,
        )
        save(custody, value)

    persist()
    source = open_credential_source(legacy._scope())
    try:
        owned = cast(Any, source)._source
        ref = _provision_interactively(
            owned, "dev-screen-discovery", discovery_purpose(), discovery_consumer()
        )

        def now() -> datetime:
            return datetime.now(UTC)

        discovered = legacy._discover(config, owned, ref, now(), now)
        classification = legacy.classify_discovery(discovered)
        discovery_classification = classification.value if classification else None
        discovery_outcome = discovered.outcome.value
        status = closed_http_status(discovered.status)
        discovery_http_status = status if isinstance(status, int) else None
        if classification is not None:
            raise PreCallRefusal(RefusalReason.DISCOVERY)
        available = {m.value for m in discovered.models} & set(listed)
        print("Listed and discovered IDs: " + json.dumps(sorted(available)))
        models = selected(
            input("Comma-separated exact model IDs (no quotes): "), listed, available
        )
        print(
            json.dumps(
                plan(phase, models, output_tokens, min_interval_seconds), indent=2
            )
        )
        if input("Approve this bounded SYNTHETIC phase? [y/N] ") != "y":
            return False
        credential = source.provision("dev-screen-chat")

        async def run_model(index: int, model: str) -> bool:
            nonlocal previous_start, chats_started, stopped_reason
            model_custody = custody / f"model-{index}"
            model_custody.mkdir()
            host = open_local_host(
                replace(
                    saia.host_config(config, credential, ModelId(model), now()),
                    max_executions=len(tasks),
                ),
                {"revision": "r1", "binding": legacy.BINDING},
                clock=now,
                remote=RemoteModelRuntime(
                    source, model_custody, config.margin, config.trust_anchor
                ),
            )
            for task in tasks:
                raw: str | None = None
                previous_start = await pace(previous_start, min_interval_seconds)
                chats_started += 1
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
                        output_tokens=None,
                        failure_effect=(
                            "NONE"
                            if isinstance(error, HostError)
                            and error.failure is HostFailure.WRONG_EVENT_LOOP
                            else "UNKNOWN"
                        ),
                    )
                row["http_status"] = http_status(host, row)
                if row["http_status"] == 429:
                    stopped_reason = "RATE_LIMITED"
                elif row["http_status"] == 503:
                    stopped_reason = "SERVICE_UNAVAILABLE"
                row.update(
                    model_id=model,
                    configuration=configuration(output_tokens),
                    comparable_with_frozen=output_tokens == OUTPUT_TOKENS,
                    diagnostics=(
                        diagnose(task, raw) if raw is not None else unevaluated()
                    ),
                )
                rows.append(row)
                persist()
                if retain_raw and raw is not None:
                    retain(custody, index, task, raw)
                print(
                    json.dumps(
                        {
                            "model": model,
                            "task": task.task_id,
                            "outcome": row["invocation_outcome"],
                        }
                    )
                )
                if stopped_reason or row["invocation_outcome"] != "completed":
                    return False
            return True

        all_completed = True
        for index, model in enumerate(models):
            # Account-level stops prevent even construction of the next host.
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
            print(
                json.dumps(
                    {
                        "stopped_reason": stopped_reason,
                        "chats_not_attempted": len(models) * len(tasks) - chats_started,
                        "discovery_classification": discovery_classification,
                        "discovery_outcome": discovery_outcome,
                        "discovery_http_status": discovery_http_status,
                    }
                )
            )
            persist()
            print("Derived evidence: " + str(custody / "evaluation.json"))


class SafeParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        self.exit(2, "Invalid options; no provider calls.\n")


def main(options: list[str] | None = None) -> int:
    parser = SafeParser(allow_abbrev=False)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--plan", action="store_true")
    group.add_argument("--live", action="store_true")
    parser.add_argument("--phase", choices=("A", "B"), default="A")
    parser.add_argument(
        "--output-tokens",
        type=int,
        choices=(1024, 2048, 4096),
        default=OUTPUT_TOKENS,
    )
    parser.add_argument("--retain-raw", action="store_true")
    parser.add_argument(
        "--min-interval-seconds",
        type=int,
        choices=INTERVALS,
        default=MIN_INTERVAL_SECONDS,
    )
    args = parser.parse_args(options)
    try:
        try:
            listed = candidates(live=args.live)
        except OSError, ValueError:
            raise PreCallRefusal(RefusalReason.CANDIDATES) from None
        print(
            json.dumps(
                plan(args.phase, listed, args.output_tokens, args.min_interval_seconds),
                indent=2,
            )
        )
        if not args.live:
            return 0
        if not sys.stdin.isatty() or not sys.stdout.isatty():
            raise PreCallRefusal(RefusalReason.TERMINAL)
        if input("Type exact authorization: ") != authorization(args.phase):
            raise PreCallRefusal(RefusalReason.AUTHORIZATION)
        if (
            args.retain_raw
            and input("Type raw retention confirmation: ") != RAW_AUTHORIZATION
        ):
            raise PreCallRefusal(RefusalReason.RAW)
        manifest_digest = verify()
        outside_repository(Path(tempfile.gettempdir()))
        custody = outside_repository(
            Path(tempfile.mkdtemp(prefix="kisski-dev-screen-"))
        )
        print("Local custody directory: " + str(custody))
        return (
            0
            if live(
                args.phase,
                custody,
                listed,
                args.output_tokens,
                args.retain_raw,
                manifest_digest,
                args.min_interval_seconds,
            )
            else 2
        )
    except PreCallRefusal as error:
        print(error.reason.value)
        return 2
    except Exception, KeyboardInterrupt:
        print("DEV_SCREEN_INCONCLUSIVE; no retry; raw error suppressed; retain custody")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
