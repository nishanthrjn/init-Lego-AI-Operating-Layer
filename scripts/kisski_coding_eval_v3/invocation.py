"""V3 binding of v2 invocation.py:1-94 (SCREEN-2A invocation.py:21-105).

Only prompt/score/empty imports differ; same disclosure, one call, diagnostic
vocabulary and completion guard. No global rebinding of the frozen invocation.
"""

import time
from typing import Any

from legoai.execution.values import ExecutionState
from legoai.governance.disclosure import DisclosureClass, DisclosureDeclaration
from legoai.intelligence.model.values import ChatMessage, ChatRequest, ChatRole
from legoai.runtime.api import ExecutionDisclosure, ModelPurpose
from legoai.runtime.local import _remote_chat_contract_diagnostics
from scripts import kisski_compatibility_probe as legacy
from scripts.kisski_coding_eval.pack import Task

from .pack import prompt
from .scoring import empty, score


async def invoke(
    host: Any, config: legacy.ProbeConfig, task: Task
) -> tuple[dict[str, Any], str | None]:
    raw: str | None = None
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
        raw = result.response.content
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
    category = facts.get("finish_reason_category")
    if reason in {"FINISH_REASON_MISSING", "FINISH_REASON_INVALID"} and category in {
        "ABSENT",
        "NULL",
        "STOP",
        "LENGTH",
        "CONTENT_FILTER",
        "TOOL_CALLS",
        "FUNCTION_CALL",
        "OTHER_STRING",
        "NON_STRING",
    }:
        row["finish_reason_category"] = category
    row["duration_ms"] = duration
    row["execution_id"] = context.execution_id.value
    return row, raw
