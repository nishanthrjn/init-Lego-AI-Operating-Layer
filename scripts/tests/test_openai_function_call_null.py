"""Null-only legacy compatibility; independent synthetic response fixtures."""

import asyncio
import json
from typing import Any

import pytest

from legoai.intelligence.model.ports import ModelResponseRejectedError
from legoai.intelligence.model.values import ModelFailure
from scripts.tests.test_kisski_saia_contract_diagnostics import (
    Exchange,
    adapter,
    broken_diagnostic,
    request,
)


def response() -> dict[str, Any]:
    # Structural analogue only; no provider response body is copied.
    return {
        "model": "selected-model",
        "choices": [
            {
                "finish_reason": "stop",
                "message": {
                    "role": "assistant",
                    "content": "synthetic-null-result",
                    "function_call": None,
                },
            }
        ],
    }


@pytest.mark.parametrize("present", [False, True])
def test_absent_and_null_accept_with_truthful_diagnostics(present: bool) -> None:
    payload = response()
    if not present:
        del payload["choices"][0]["message"]["function_call"]
    exchange = Exchange(json.dumps(payload).encode())
    owner = adapter(exchange)
    result = asyncio.run(owner.chat(request()))
    assert result.content == "synthetic-null-result"
    assert result.model_identity.value == "selected-model"
    assert result.usage is None
    assert exchange.calls == 1
    facts = dict(owner._chat_contract_items())
    assert facts["rejection_reason"] == "VALIDATED"
    assert facts["function_call_present"] == str(present).lower()
    assert facts["function_call_shape"] == ("NULL" if present else "ABSENT")
    assert facts["tool_calls_shape"] == "ABSENT"


@pytest.mark.parametrize(
    "value",
    [
        pytest.param({}, id="empty-object"),
        pytest.param({"name": "synthetic", "arguments": "{}"}, id="object"),
        pytest.param([], id="empty-array"),
        pytest.param([{}], id="array"),
        pytest.param("", id="empty-string"),
        pytest.param("synthetic", id="string"),
        pytest.param(0, id="zero"),
        pytest.param(1, id="integer"),
        pytest.param(0.0, id="float-zero"),
        pytest.param(1.5, id="float"),
        pytest.param(False, id="false"),
        pytest.param(True, id="true"),
    ],
)
@pytest.mark.parametrize("fault", [False, True])
def test_every_non_null_value_rejects_even_if_observation_fails(
    value: object, fault: bool, monkeypatch: pytest.MonkeyPatch
) -> None:
    payload = response()
    payload["choices"][0]["message"]["function_call"] = value
    exchange = Exchange(json.dumps(payload).encode())
    owner = adapter(exchange)
    if fault:
        monkeypatch.setattr(owner, "_record_call_shapes", broken_diagnostic)
    with pytest.raises(ModelResponseRejectedError) as raised:
        asyncio.run(owner.chat(request()))
    assert raised.value.failure is ModelFailure.PROTOCOL_INCOMPATIBLE
    facts = dict(owner._chat_contract_items())
    assert facts["rejection_reason"] == "FUNCTION_CALL_PRESENT"
    assert exchange.calls == 1


@pytest.mark.parametrize("value", [None, {}, [], "", 0, False, [{"name": "x"}]])
def test_tool_presence_wins_over_null_legacy_field(value: object) -> None:
    payload = response()
    payload["choices"][0]["message"]["tool_calls"] = value
    owner = adapter(Exchange(json.dumps(payload).encode()))
    with pytest.raises(ModelResponseRejectedError):
        asyncio.run(owner.chat(request()))
    facts = dict(owner._chat_contract_items())
    assert facts["rejection_reason"] == "TOOL_CALL_PRESENT"
    assert facts["function_call_shape"] == "NULL"


@pytest.mark.parametrize(
    "case,reason",
    [
        ("model", "MODEL_ID_MISMATCH"),
        ("choices", "CHOICE_COUNT_INVALID"),
        ("choice", "CHOICE_NOT_OBJECT"),
        ("finish", "FINISH_REASON_INVALID"),
        ("message", "MESSAGE_NOT_OBJECT"),
        ("role", "ROLE_INVALID"),
        ("content-null", "CONTENT_NULL"),
        ("content-list", "CONTENT_NOT_STRING"),
    ],
)
def test_null_does_not_bypass_earlier_gates(case: str, reason: str) -> None:
    payload = response()
    choice = payload["choices"][0]
    if case == "model":
        payload["model"] = "wrong-model"
    elif case == "choices":
        payload["choices"] *= 2
    elif case == "choice":
        payload["choices"] = [None]
    elif case == "finish":
        choice["finish_reason"] = "length"
    elif case == "message":
        choice["message"] = None
    elif case == "role":
        choice["message"]["role"] = "tool"
    elif case == "content-null":
        choice["message"]["content"] = None
    else:
        choice["message"]["content"] = []
    owner = adapter(Exchange(json.dumps(payload).encode()))
    with pytest.raises(ModelResponseRejectedError):
        asyncio.run(owner.chat(request()))
    facts = dict(owner._chat_contract_items())
    assert facts["rejection_reason"] == reason
    assert "function_call_shape" not in facts


@pytest.mark.parametrize(
    "raw",
    [
        b'{"function_call":null,',
        b'{"function_call":null,"function_call":null}',
        b'{"function_call":null,"x":NaN}',
    ],
)
def test_null_does_not_bypass_strict_json(raw: bytes) -> None:
    owner = adapter(Exchange(raw))
    with pytest.raises(ModelResponseRejectedError):
        asyncio.run(owner.chat(request()))
    assert dict(owner._chat_contract_items())["rejection_reason"] == "JSON_INVALID"


@pytest.mark.parametrize("usage", [None, "invalid", {}, {"prompt_tokens": False}])
def test_null_preserves_optional_usage_policy(usage: object) -> None:
    payload = response()
    payload["usage"] = usage
    owner = adapter(Exchange(json.dumps(payload).encode()))
    result = asyncio.run(owner.chat(request()))
    if isinstance(usage, dict):
        assert result.usage is not None
        assert result.usage.prompt_tokens is None
        assert result.usage.completion_tokens is None
    else:
        assert result.usage is None
