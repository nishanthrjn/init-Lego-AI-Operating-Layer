"""Attended, quota-bounded SAIA evaluation. Default invocation is inert."""

import argparse
import asyncio
import json
import sys
import tempfile
import time
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, NoReturn, cast

from legoai.execution.values import ExecutionState
from legoai.governance.disclosure import DisclosureClass, DisclosureDeclaration
from legoai.intelligence.model.values import ChatMessage, ChatRequest, ChatRole, ModelId
from legoai.runtime._composition.provider_discovery import (
    discovery_consumer,
    discovery_purpose,
)
from legoai.runtime._composition.secret import _provision_interactively
from legoai.runtime.api import ExecutionDisclosure, ModelPurpose, RemoteModelRuntime
from legoai.runtime.local import (
    _remote_chat_contract_diagnostics,
    open_credential_source,
    open_local_host,
)
from scripts import kisski_compatibility_probe as legacy
from scripts import kisski_saia_qualification as saia

from .frozen import verify
from .pack import OBSERVED, OUTPUT_TOKENS, TASKS, VERSION, Task, digest, prompt
from .scoring import classify, empty, score


def authorization(phase: str) -> str:
    return f"AUTHORIZE {VERSION} PHASE {phase} LIVE SYNTHETIC"


def plan(phase: str) -> dict[str, Any]:
    maximum = 5 if phase == "A" else 2
    tasks = [t.task_id for t in TASKS if t.phase == phase]
    return {
        "evaluation": VERSION,
        "phase": phase,
        "pack_digest": digest(),
        "observed_candidates": OBSERVED,
        "tasks": tasks,
        "maximum_models": maximum,
        "maximum_discovery_calls": 1,
        "maximum_chat_calls": maximum * len(tasks),
        "output_tokens": OUTPUT_TOKENS,
        "timeout_seconds": 60,
        "live_calls_now": 0,
        "authorization": authorization(phase),
    }


def selected(
    answer: str, discovered: set[str], phase: str, eligible: set[str]
) -> tuple[str, ...]:
    models = tuple(item.strip() for item in answer.split(","))
    maximum = 5 if phase == "A" else 2
    if not 1 <= len(models) <= maximum or len(set(models)) != len(models):
        raise ValueError("invalid model selection")
    if not set(models) <= set(OBSERVED) & discovered & eligible:
        raise ValueError("model not observed, discovered or eligible")
    return models


def screening(records: list[dict[str, Any]], model: str) -> bool:
    rows = [r for r in records if r.get("model_id") == model and r.get("phase") == "A"]
    return (
        len(rows) == 4
        and {r.get("task_id") for r in rows}
        == {t.task_id for t in TASKS if t.phase == "A"}
        and all(
            r.get("invocation_outcome") == "completed"
            and r.get("schema_valid") is True
            and r.get("scope_discipline") is True
            and r.get("instruction_adherence") is True
            and r.get("critical_safety_violation") is False
            for r in rows
        )
        and sum(r.get("acceptance_criteria_met") is True for r in rows) >= 3
    )


def prior_report(path: Path) -> list[dict[str, Any]]:
    if path.is_symlink() or path.stat().st_size > 262144:
        raise ValueError("invalid prior report")
    with path.open("rb") as handle:
        raw = handle.read(262145)
    if len(raw) > 262144:
        raise ValueError("prior report too large")
    value = json.loads(raw)
    if (
        type(value) is not dict
        or value.get("evaluation") != VERSION
        or value.get("pack_digest") != digest()
        or value.get("phase") != "A"
    ):
        raise ValueError("prior phase mismatch")
    rows = value.get("records")
    if (
        type(rows) is not list
        or len(rows) > 20
        or not all(type(row) is dict for row in rows)
    ):
        raise ValueError("invalid prior records")
    allowed_tasks = {t.task_id: t for t in TASKS if t.phase == "A"}
    seen: set[tuple[str, str]] = set()
    for row in rows:
        task = allowed_tasks.get(row.get("task_id"))
        if task is None or row.get("model_id") not in OBSERVED:
            raise ValueError("invalid prior attribution")
        key = (row["model_id"], task.task_id)
        if key in seen:
            raise ValueError("duplicate prior result")
        seen.add(key)
        template = empty(task)
        extras = {
            "model_id",
            "invocation_outcome",
            "output_tokens",
            "contract_reason",
            "duration_ms",
            "execution_id",
        }
        if set(row) != set(template) | extras:
            raise ValueError("unrecognized prior evidence")
        for name, default in template.items():
            if type(default) is bool and type(row[name]) is not bool:
                raise ValueError("invalid prior score")
            if type(default) is str and row[name] != default:
                raise ValueError("invalid prior role or scope")
            if default is None and row[name] is not None:
                if name == "failure_category":
                    if row[name] not in {
                        "SCHEMA_INVALID",
                        "SCOPE_VIOLATION",
                        "REFERENCE_INVALID",
                        "PYTHON_SUBSET_REJECTED",
                        "SYNTAX_INVALID",
                        "DUPLICATE_JSON_KEY",
                        "OUTPUT_INVALID",
                        "CHECK_FAILED",
                    }:
                        raise ValueError("unrecognized prior failure")
                elif (
                    name
                    in {
                        "patch_applies",
                        "targeted_tests_pass",
                        "regression_tests_pass",
                    }
                    and type(row[name]) is bool
                ):
                    pass
                else:
                    raise ValueError("invalid nullable score")
        if row["invocation_outcome"] != "completed" or row["contract_reason"] not in {
            "VALIDATED",
            "OTHER_OR_UNAVAILABLE",
        }:
            raise ValueError("prior phase contains incomplete invocation")
        for name in ("duration_ms", "output_tokens"):
            if row[name] is not None and (
                type(row[name]) is not int or not 0 <= row[name] <= 3600000
            ):
                raise ValueError("invalid prior metric")
        execution = row["execution_id"]
        if (
            type(execution) is not str
            or not execution.startswith("exec-")
            or len(execution) > 80
            or not all(c.isalnum() or c == "-" for c in execution)
        ):
            raise ValueError("invalid prior execution")
    return cast(list[dict[str, Any]], rows)


async def invoke(host: Any, config: legacy.ProbeConfig, task: Task) -> dict[str, Any]:
    system, user = prompt(task)
    context = host.model_execution(
        ModelPurpose.CHAT,
        disclosure=ExecutionDisclosure(
            legacy.PROBE_CONSUMER,
            DisclosureDeclaration(frozenset({DisclosureClass.SYNTHETIC})),
        ),
    )
    started = time.monotonic()
    result = await host.governed_chat(
        context,
        ChatRequest(
            (ChatMessage(ChatRole.SYSTEM, system), ChatMessage(ChatRole.USER, user))
        ),
    )
    duration = min(3600000, max(0, round((time.monotonic() - started) * 1000)))
    if (
        result.response is not None
        and result.execution.final_state is ExecutionState.SUCCEEDED
    ):
        row = score(task, result.response.content)
        usage = result.response.usage
        row["output_tokens"] = usage.completion_tokens if usage else None
        row["invocation_outcome"] = "completed"
    else:
        row = empty(task)
        row["invocation_outcome"] = "provider_or_protocol_failure"
        row["failure_category"] = (
            result.failure.value if result.failure else "unclassified"
        )
        row["output_tokens"] = None
    try:
        facts = dict(_remote_chat_contract_diagnostics(host, context.execution_id))
    except Exception:
        facts = {}
    # Closed diagnostic vocabulary only; never persist content, raw IDs from output,
    # arbitrary provider keys, or exception strings.
    reason = facts.get("rejection_reason")
    known = {
        "VALIDATED",
        "MODEL_ID_MISMATCH",
        "FINISH_REASON_INVALID",
        "FINISH_REASON_MISSING",
        "TOOL_CALL_PRESENT",
        "FUNCTION_CALL_PRESENT",
        "JSON_INVALID",
    }
    row["contract_reason"] = reason if reason in known else "OTHER_OR_UNAVAILABLE"
    row["duration_ms"] = duration
    row["execution_id"] = context.execution_id.value
    return row


def save(path: Path, phase: str, records: list[dict[str, Any]], stopped: bool) -> None:
    models = sorted({r["model_id"] for r in records})
    summaries = {
        model: classify([r for r in records if r["model_id"] == model])
        for model in models
    }
    classes = {s["classification"] for s in summaries.values()}
    if stopped or phase == "A" or not classes or "RESULT_INCONCLUSIVE" in classes:
        final = "RESULT_INCONCLUSIVE"
    elif "MODEL_QUALIFIED_FOR_FORGEAI_CODING" in classes:
        final = "MODEL_QUALIFIED_FOR_FORGEAI_CODING"
    elif "MODEL_QUALIFIED_FOR_REVIEW_ONLY" in classes:
        final = "MODEL_QUALIFIED_FOR_REVIEW_ONLY"
    else:
        final = "NO_MODEL_QUALIFIED"
    value = {
        "evaluation": VERSION,
        "pack_digest": digest(),
        "phase": phase,
        "records": records,
        "summaries": summaries,
        "reliability": {
            model: reliability([r for r in records if r["model_id"] == model])
            for model in models
        },
        "qualified_rank_groups": {
            role: [
                model
                for model in models
                if summaries[model].get(role + "_score") == 100
                and (
                    summaries[model]["classification"]
                    == "MODEL_QUALIFIED_FOR_FORGEAI_CODING"
                    if role == "coder"
                    else summaries[model].get("reviewer_qualified") is True
                )
            ]
            for role in ("coder", "reviewer")
        },
        "ranking_note": "Qualified scores tie at 100; lexical display order is not rank",
        "result": final,
        "scope": "frozen scalar synthetic pack only; no production deployment recommendation",
        "cost": "NOT_AVAILABLE",
        "repeatability": "NOT_MEASURED",
    }
    temporary = path.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(value, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    temporary.replace(path)


def reliability(rows: list[dict[str, Any]]) -> dict[str, Any]:
    reasons = [r.get("contract_reason") for r in rows]
    return {
        "attempts": len(rows),
        "valid_schema_count": sum(r["schema_valid"] is True for r in rows),
        "malformed_output_count": sum(
            r.get("invocation_outcome") == "completed" and not r["schema_valid"]
            for r in rows
        ),
        "provider_or_protocol_failure_count": sum(
            r.get("invocation_outcome") != "completed" for r in rows
        ),
        "protocol_rejection_count": sum(
            r.get("failure_category") == "protocol_incompatible" for r in rows
        ),
        "unexpected_call_field_count": sum(
            reason in {"TOOL_CALL_PRESENT", "FUNCTION_CALL_PRESENT"}
            for reason in reasons
        ),
        "wrong_model_identity_count": reasons.count("MODEL_ID_MISMATCH"),
        "finish_reason_failure_count": sum(
            reason in {"FINISH_REASON_INVALID", "FINISH_REASON_MISSING"}
            for reason in reasons
        ),
        "truncation": "NOT_SEPARATELY_OBSERVABLE; finish failures are not assumed truncation",
    }


def live(phase: str, custody: Path) -> bool:
    previous: list[dict[str, Any]] = []
    if phase == "B":
        previous = prior_report(Path(input("Phase A derived report path: ")))
    eligible = (
        set(OBSERVED)
        if phase == "A"
        else {m for m in OBSERVED if screening(previous, m)}
    )
    if not eligible:
        raise ValueError("no screened finalists")
    config = replace(saia.live_config(custody), max_output_tokens=OUTPUT_TOKENS)
    source = open_credential_source(legacy._scope())
    records: list[dict[str, Any]] = []
    stopped = True
    report = custody / "evaluation.json"
    try:
        owned = cast(Any, source)._source
        ref = _provision_interactively(
            owned, "eval-discovery", discovery_purpose(), discovery_consumer()
        )

        def now() -> datetime:
            return datetime.now(UTC)

        discovered = legacy._discover(config, owned, ref, now(), now)
        if legacy.classify_discovery(discovered) is not None:
            raise ValueError("discovery failed")
        available = {m.value for m in discovered.models} & set(OBSERVED) & eligible
        print("Eligible exact IDs: " + json.dumps(sorted(available)))
        models = selected(
            input("Comma-separated exact model IDs: "), available, phase, eligible
        )
        tasks = tuple(t for t in TASKS if t.phase == phase)
        print(
            f"Frozen bound: {len(models) * len(tasks)} chats; no retries or expansion"
        )
        if input("Approve this bounded SYNTHETIC phase? [y/N] ").strip() != "y":
            return False
        records = [r for r in previous if r.get("model_id") in models]
        credential = source.provision("eval-chat")
        save(report, phase, records, True)
        for index, model in enumerate(models):
            # Each host owns a distinct attempt store; never reopen an active writer.
            model_custody = custody / f"model-{index}"
            model_custody.mkdir()
            host = open_local_host(
                saia.host_config(config, credential, ModelId(model), now()),
                {"revision": "r1", "binding": legacy.BINDING},
                clock=now,
                remote=RemoteModelRuntime(
                    source, model_custody, config.margin, config.trust_anchor
                ),
            )
            for task in tasks:
                row = asyncio.run(invoke(host, config, task))
                row["model_id"] = model
                records.append(row)
                save(report, phase, records, True)
                print(
                    json.dumps(
                        {
                            "model": model,
                            "task": task.task_id,
                            "outcome": row["invocation_outcome"],
                        }
                    )
                )
                if row["invocation_outcome"] != "completed":
                    return False
        stopped = False
        return True
    finally:
        source.close()
        save(report, phase, records, stopped)
        print("Derived evidence: " + str(report))


class SafeParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        self.exit(2, "Invalid options; use --plan or --live and --phase A/B.\n")


def main(options: list[str] | None = None) -> int:
    parser = SafeParser(allow_abbrev=False)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--plan", action="store_true")
    group.add_argument("--live", action="store_true")
    parser.add_argument("--phase", choices=("A", "B"), default="A")
    args = parser.parse_args(options)
    print(json.dumps(plan(args.phase), indent=2))
    if not args.live:
        return 0
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        print("Interactive terminal required; no provider calls")
        return 2
    if input("Type exact authorization: ").strip() != authorization(args.phase):
        print("Declined; no provider calls")
        return 2
    try:
        print("Frozen evaluation digest: " + verify())
        custody = Path(tempfile.mkdtemp(prefix="kisski-coding-eval-"))
        print("Local custody directory: " + str(custody))
        completed = live(args.phase, custody)
    except Exception, KeyboardInterrupt:
        print("RESULT_INCONCLUSIVE; inspect custody; no retry; raw error suppressed")
        return 2
    return 0 if completed else 2


if __name__ == "__main__":
    raise SystemExit(main())
