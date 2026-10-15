"""Closed finish categories; synthetic exchanges only, no provider calls."""

import asyncio
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import pytest

from legoai.execution.values import ExecutionState
from legoai.intelligence.model.ports import ModelResponseRejectedError
from legoai.intelligence.model.values import ModelFailure
from scripts import kisski_saia_qualification as saia
from scripts.kisski_coding_eval import pack, runner
from scripts.tests.test_kisski_saia_chat_interop import chat_custody
from scripts.tests.test_kisski_saia_contract_diagnostics import (
    Exchange,
    adapter,
    broken_diagnostic,
    request,
    valid,
)
from scripts.tests.test_kisski_saia_qualification import Runner
from scripts.tests.test_t2_bounded_chunked_response import HEAD, ResponseServer

CANARY = "PRIVATE_PROVIDER_VALUE_DO_NOT_RETAIN"
CASES: list[tuple[object, str]] = [
    (None, "ABSENT"),
    (None, "NULL"),
    ("stop", "STOP"),
    ("length", "LENGTH"),
    ("content_filter", "CONTENT_FILTER"),
    ("tool_calls", "TOOL_CALLS"),
    ("function_call", "FUNCTION_CALL"),
    (CANARY, "OTHER_STRING"),
    (1, "NON_STRING"),
    (True, "NON_STRING"),
    ({"secret": CANARY}, "NON_STRING"),
    ([CANARY], "NON_STRING"),
]


@pytest.mark.parametrize("value,category", CASES)
def test_category_never_changes_acceptance(value: object, category: str) -> None:
    payload = valid()
    choice = payload["choices"][0]
    if category == "ABSENT":
        del choice["finish_reason"]
    else:
        choice["finish_reason"] = value
    choice["message"]["function_call"] = None
    owner = adapter(Exchange(json.dumps(payload).encode()))
    if category == "STOP":
        assert asyncio.run(owner.chat(request())).content == "KISSKI_OK"
    else:
        with pytest.raises(ModelResponseRejectedError) as raised:
            asyncio.run(owner.chat(request()))
        assert raised.value.failure is ModelFailure.PROTOCOL_INCOMPATIBLE
        assert raised.value.__context__ is None
        assert CANARY not in str(raised.value)
    facts = dict(owner._chat_contract_items())
    assert facts["finish_reason_category"] == category
    expected = (
        "FINISH_REASON_MISSING" if category == "ABSENT" else "FINISH_REASON_INVALID"
    )
    assert facts["rejection_reason"] == (
        "VALIDATED" if category == "STOP" else expected
    )
    assert CANARY not in repr(facts)


@pytest.mark.parametrize("model_ok", [False, True])
def test_ordering_before_message_and_after_model(model_ok: bool) -> None:
    payload = valid()
    payload["choices"][0].update(finish_reason="length", message=None)
    if not model_ok:
        payload["model"] = CANARY
    owner = adapter(Exchange(json.dumps(payload).encode()))
    with pytest.raises(ModelResponseRejectedError):
        asyncio.run(owner.chat(request()))
    facts = dict(owner._chat_contract_items())
    if model_ok:
        assert facts["rejection_reason"] == "FINISH_REASON_INVALID"
        assert facts["finish_reason_category"] == "LENGTH"
    else:
        assert facts["rejection_reason"] == "MODEL_ID_MISMATCH"
        assert "finish_reason_category" not in facts
    assert "function_call_shape" not in facts


def test_category_reset_and_corrupted_state() -> None:
    exchange = Exchange(json.dumps(valid()).encode())
    owner = adapter(exchange)
    asyncio.run(owner.chat(request()))
    owner._finish_category = cast(Any, CANARY)
    assert "finish_reason_category" not in dict(owner._chat_contract_items())
    exchange.raw = b"[]"
    with pytest.raises(ModelResponseRejectedError):
        asyncio.run(owner.chat(request()))
    assert "finish_reason_category" not in dict(owner._chat_contract_items())


@pytest.mark.parametrize("finish", ["stop", "length"])
def test_observation_fault_does_not_change_result(
    finish: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    payload = valid()
    payload["choices"][0]["finish_reason"] = finish
    owner = adapter(Exchange(json.dumps(payload).encode()))
    monkeypatch.setattr(owner, "_record_finish_category", broken_diagnostic)
    if finish == "stop":
        assert asyncio.run(owner.chat(request())).content == "KISSKI_OK"
    else:
        with pytest.raises(ModelResponseRejectedError):
            asyncio.run(owner.chat(request()))
    assert "finish_reason_category" not in dict(owner._chat_contract_items())


@pytest.mark.parametrize("category", sorted({c for _, c in CASES}) + [CANARY])
def test_evaluation_retains_only_closed_failure_category(
    category: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def chat(*args: Any) -> Any:
        return SimpleNamespace(
            response=None,
            execution=SimpleNamespace(final_state=ExecutionState.FAILED),
            failure=ModelFailure.PROTOCOL_INCOMPATIBLE,
        )

    host = SimpleNamespace(
        model_execution=lambda *args, **kwargs: SimpleNamespace(
            execution_id=SimpleNamespace(value="exec-synthetic")
        ),
        governed_chat=chat,
    )
    monkeypatch.setattr(
        runner,
        "_remote_chat_contract_diagnostics",
        lambda *args: (
            ("rejection_reason", "FINISH_REASON_INVALID"),
            ("finish_reason_category", category),
        ),
    )
    row = asyncio.run(runner.invoke(host, saia.live_config(tmp_path), pack.TASKS[0]))
    assert row["invocation_outcome"] == "provider_or_protocol_failure"
    if category == CANARY:
        assert "finish_reason_category" not in row
    else:
        assert row["finish_reason_category"] == category
    assert CANARY not in json.dumps(row)


def test_acceptance_fitness_control_detects_relaxation() -> None:
    from validate_openai_compat_finish_reason_shape_diagnostic_1 import acceptance

    source = (
        "class OpenAICompatibleModelAdapter:\n"
        "    async def chat(self, request):\n"
        "        if choice.get('finish_reason') != 'stop':\n"
        "            reject()\n"
    )
    observation = (
        "        self._finish_category = None\n"
        "        try:\n"
        "            self._record_finish_category(choice)\n"
        "        except Exception:\n"
        "            self._finish_category = None\n"
    )
    instrumented = source.replace("        if choice", observation + "        if choice")
    assert acceptance(source) == acceptance(instrumented)
    relaxed = source.replace("!= 'stop'", "not in ('stop', 'length')")
    assert acceptance(source) != acceptance(relaxed)


@pytest.mark.parametrize(
    "value,category", [("length", "LENGTH"), (CANARY, "OTHER_STRING")]
)
def test_synthetic_tls_runner_exposes_category_without_changing_custody(
    value: str,
    category: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    from scripts.tests.test_kisski_saia_qualification import CANARY as TOKEN_CANARY

    probe = Runner(tmp_path, monkeypatch)
    payload = valid()
    payload["choices"][0]["finish_reason"] = value
    raw = json.dumps(payload).encode()
    wire = b"%x\r\n%s\r\n0\r\n\r\n" % (len(raw), raw)
    answers = iter(("selected-model", "y"))
    with ResponseServer((HEAD + wire,), expected=TOKEN_CANARY) as server:
        outcome = saia.run(
            probe.config(server),
            ask=lambda _: next(answers),
            write=probe.lines.append,
            diagnostic_only=True,
        )
        assert server.requests == server.connections == 2
    assert outcome is saia.Outcome.CONTRACT_REJECTED
    assert f"chat contract finish_reason_category: {category}" in probe.lines
    assert "chat effect: none" in probe.lines
    state, observations = chat_custody(probe)
    assert state == "completed"
    assert set(observations) == {"sent_all", "response_complete"}
    assert CANARY not in repr(probe.lines) + caplog.text
    probe.no_leak(caplog)
