"""Synthetic field shapes; no provider data or external calls."""

import asyncio
import json
from pathlib import Path
from typing import Any, cast

import pytest

from legoai.intelligence.model.ports import ModelResponseRejectedError
from legoai.intelligence.model.values import ModelFailure
from legoai.reference.model_openai_compatible import (
    _call_field_shape,
    _CallFieldShape,
)
from scripts import kisski_saia_qualification as probe
from scripts.tests.test_kisski_saia_chat_interop import chat_custody
from scripts.tests.test_kisski_saia_contract_diagnostics import (
    Exchange,
    adapter,
    broken_diagnostic,
    request,
    valid,
)
from scripts.tests.test_kisski_saia_qualification import CANARY, Runner
from scripts.tests.test_t2_bounded_chunked_response import HEAD, ResponseServer

CASES = [
    pytest.param(None, "NULL", id="null"),
    pytest.param({}, "EMPTY_OBJECT", id="empty-object"),
    pytest.param({"name": CANARY}, "NONEMPTY_OBJECT", id="name"),
    pytest.param({"arguments": "{}"}, "NONEMPTY_OBJECT", id="arguments"),
    pytest.param({CANARY: CANARY}, "NONEMPTY_OBJECT", id="arbitrary-key"),
    pytest.param(
        {"name": CANARY, "arguments": "{}"}, "NONEMPTY_OBJECT", id="both-keys"
    ),
    pytest.param("", "STRING", id="empty-string"),
    pytest.param(CANARY, "STRING", id="string"),
    pytest.param([], "EMPTY_ARRAY", id="empty-array"),
    pytest.param([{"name": CANARY}], "NONEMPTY_ARRAY", id="array"),
    pytest.param(0, "NUMBER", id="integer"),
    pytest.param(1.5, "NUMBER", id="float"),
    pytest.param(False, "BOOLEAN", id="boolean"),
]


@pytest.mark.parametrize("field", ["function_call", "tool_calls"])
@pytest.mark.parametrize("value,shape", CASES)
def test_present_shapes_preserve_null_only_policy(
    field: str, value: object, shape: str
) -> None:
    payload = valid()
    payload["choices"][0]["message"][field] = value
    payload["choices"][0]["message"]["content"] = CANARY
    exchange = Exchange(json.dumps(payload).encode())
    owner = adapter(exchange)
    accepted = field == "function_call" and value is None
    if accepted:
        assert asyncio.run(owner.chat(request())).content == CANARY
    else:
        with pytest.raises(ModelResponseRejectedError) as raised:
            asyncio.run(owner.chat(request()))
        assert raised.value.failure is ModelFailure.PROTOCOL_INCOMPATIBLE
        assert raised.value.__context__ is None
        assert raised.value.__cause__ is None
        assert CANARY not in str(raised.value)
    facts = dict(owner._chat_contract_items())
    reason = (
        "FUNCTION_CALL_PRESENT" if field == "function_call" else "TOOL_CALL_PRESENT"
    )
    assert facts["rejection_reason"] == ("VALIDATED" if accepted else reason)
    assert facts[field + "_shape"] == shape
    assert facts[field + "_present"] == "true"
    other = "tool_calls" if field == "function_call" else "function_call"
    assert facts[other + "_shape"] == "ABSENT"
    assert facts[other + "_present"] == "false"
    assert set(facts) == {
        "rejection_reason",
        "finish_reason_category",
        "json_valid",
        "returned_model_matches_requested",
        "function_call_present",
        "function_call_shape",
        "tool_calls_present",
        "tool_calls_shape",
    }
    assert CANARY not in repr(facts)
    assert exchange.calls == 1


def test_absent_fields_preserve_acceptance_and_reset() -> None:
    exchange = Exchange(json.dumps(valid()).encode())
    owner = adapter(exchange)
    assert asyncio.run(owner.chat(request())).content == "KISSKI_OK"
    facts = dict(owner._chat_contract_items())
    for field in ("function_call", "tool_calls"):
        assert facts[field + "_shape"] == "ABSENT"
        assert facts[field + "_present"] == "false"
    exchange.raw = b"[]"
    with pytest.raises(ModelResponseRejectedError):
        asyncio.run(owner.chat(request()))
    assert not any("_shape" in key for key, _ in owner._chat_contract_items())


def test_both_fields_are_independent_and_tool_gate_remains_first() -> None:
    payload = valid()
    payload["choices"][0]["message"].update(
        function_call=None, tool_calls=[{"arguments": CANARY}]
    )
    owner = adapter(Exchange(json.dumps(payload).encode()))
    with pytest.raises(ModelResponseRejectedError):
        asyncio.run(owner.chat(request()))
    facts = dict(owner._chat_contract_items())
    assert facts["rejection_reason"] == "TOOL_CALL_PRESENT"
    assert facts["function_call_shape"] == "NULL"
    assert facts["tool_calls_shape"] == "NONEMPTY_ARRAY"
    assert facts["function_call_present"] == facts["tool_calls_present"] == "true"
    assert CANARY not in repr(facts)


@pytest.mark.parametrize("present", [False, True])
def test_observation_failure_cannot_change_acceptance(
    monkeypatch: pytest.MonkeyPatch, present: bool
) -> None:
    payload = valid()
    if present:
        payload["choices"][0]["message"]["function_call"] = None
    owner = adapter(Exchange(json.dumps(payload).encode()))
    monkeypatch.setattr(owner, "_record_call_shapes", broken_diagnostic)
    assert asyncio.run(owner.chat(request())).content == "KISSKI_OK"
    assert not any("_shape" in key for key, _ in owner._chat_contract_items())


def test_earlier_failure_does_not_observe_later_fields() -> None:
    payload = valid()
    payload["choices"][0]["message"].update(content=None, function_call=CANARY)
    owner = adapter(Exchange(json.dumps(payload).encode()))
    with pytest.raises(ModelResponseRejectedError):
        asyncio.run(owner.chat(request()))
    facts = dict(owner._chat_contract_items())
    assert facts["rejection_reason"] == "CONTENT_NULL"
    assert "function_call_shape" not in facts


def test_corrupted_shape_state_is_not_projected() -> None:
    owner = adapter(Exchange(json.dumps(valid()).encode()))
    asyncio.run(owner.chat(request()))
    owner._call_shapes = cast(Any, (CANARY, _CallFieldShape.NULL))
    facts = dict(owner._chat_contract_items())
    assert facts["rejection_reason"] == "VALIDATED"
    assert "function_call_shape" not in facts
    assert CANARY not in repr(facts)


def test_other_shape_never_inspects_arbitrary_objects() -> None:
    class Uninspectable:
        def __bool__(self) -> bool:
            raise AssertionError("must not inspect values")

    shape = _call_field_shape({"function_call": Uninspectable()}, "function_call")
    assert shape is _CallFieldShape.OTHER


@pytest.mark.parametrize(
    "value,shape",
    [
        pytest.param(None, "NULL", id="null"),
        pytest.param({}, "EMPTY_OBJECT", id="empty-object"),
        pytest.param({"name": CANARY}, "NONEMPTY_OBJECT", id="object"),
    ],
)
@pytest.mark.parametrize("content", ["KISSKI_OK", "synthetic-wrong-token"])
def test_runner_prints_only_closed_shapes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    value: object,
    shape: str,
    content: str,
) -> None:
    runner = Runner(tmp_path, monkeypatch)
    payload = valid()
    payload["choices"][0]["message"]["function_call"] = value
    payload["choices"][0]["message"]["content"] = content
    raw = json.dumps(payload).encode()
    wire = b"%x\r\n%s\r\n0\r\n\r\n" % (len(raw), raw)
    answers = iter(("selected-model", "y"))
    with ResponseServer((HEAD + wire,), expected=CANARY) as server:
        outcome = probe.run(
            runner.config(server),
            ask=lambda _: next(answers),
            write=runner.lines.append,
            diagnostic_only=True,
        )
        assert server.requests == server.connections == 2
    expected = probe.Outcome.CONTRACT_REJECTED
    if value is None:
        expected = (
            probe.Outcome.CONNECTIVITY_ONLY
            if content == "KISSKI_OK"
            else probe.Outcome.CONTENT_REJECTED
        )
    assert outcome is expected
    assert f"chat contract function_call_shape: {shape}" in runner.lines
    assert "chat contract function_call_present: true" in runner.lines
    assert "chat contract tool_calls_present: false" in runner.lines
    effect = "completed" if value is None else "none"
    assert f"chat effect: {effect}" in runner.lines
    state, facts = chat_custody(runner)
    assert state == "completed"
    assert set(facts) == {"sent_all", "response_complete"}
    runner.no_leak(caplog)
