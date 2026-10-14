"""Synthetic post-HTTP contract evidence; no provider data or external calls."""

import asyncio
import json
from pathlib import Path
from typing import Any, NoReturn, cast
from unittest.mock import patch

import pytest

from legoai.intelligence.model.ports import ModelResponseRejectedError
from legoai.intelligence.model.values import (
    ChatMessage,
    ChatRequest,
    ChatRole,
    ModelFailure,
    ProviderId,
)
from legoai.reference.model_openai_compatible import (
    OpenAICompatibleModelAdapter,
    OpenAICompatibleModelConfig,
    _ChatContractReason,
    _json_body,
)
from scripts import kisski_saia_qualification as probe
from scripts.tests.test_kisski_saia_chat_interop import chat_custody
from scripts.tests.test_kisski_saia_qualification import CANARY, Runner
from scripts.tests.test_t2_bounded_chunked_response import HEAD, ResponseServer


def valid() -> dict[str, Any]:
    return {
        "model": "selected-model",
        "choices": [
            {
                "finish_reason": "stop",
                "message": {"role": "assistant", "content": "KISSKI_OK"},
            }
        ],
    }


def rejected_body(reason: str) -> bytes:
    payload = valid()
    choice = payload["choices"][0]
    message = choice["message"]
    if reason == "JSON_INVALID":
        return b"not-json-" + CANARY.encode()
    if reason == "ROOT_NOT_OBJECT":
        return b"[]"
    if reason == "MODEL_FIELD_MISSING":
        del payload["model"]
    elif reason == "MODEL_FIELD_NOT_STRING":
        payload["model"] = None
    elif reason == "MODEL_ID_MISMATCH":
        payload["model"] = CANARY
    elif reason == "CHOICES_MISSING":
        del payload["choices"]
    elif reason == "CHOICES_NOT_LIST":
        payload["choices"] = {}
    elif reason == "CHOICE_COUNT_INVALID":
        payload["choices"] = []
    elif reason == "CHOICE_NOT_OBJECT":
        payload["choices"] = [None]
    elif reason == "FINISH_REASON_MISSING":
        del choice["finish_reason"]
    elif reason == "FINISH_REASON_INVALID":
        choice["finish_reason"] = CANARY
    elif reason == "MESSAGE_MISSING":
        del choice["message"]
    elif reason == "MESSAGE_NOT_OBJECT":
        choice["message"] = None
    elif reason == "ROLE_INVALID":
        message["role"] = CANARY
    elif reason == "CONTENT_MISSING":
        del message["content"]
    elif reason == "CONTENT_NULL":
        message["content"] = None
    elif reason == "CONTENT_NOT_STRING":
        message["content"] = [{"text": CANARY}]
    elif reason == "TOOL_CALL_PRESENT":
        message["tool_calls"] = [{"arguments": CANARY}]
    elif reason == "FUNCTION_CALL_PRESENT":
        message["function_call"] = {"arguments": CANARY}
    else:
        raise AssertionError("unknown synthetic fixture")
    payload["ignored_canary"] = CANARY
    return json.dumps(payload).encode()


REASONS = (
    "JSON_INVALID",
    "ROOT_NOT_OBJECT",
    "MODEL_FIELD_MISSING",
    "MODEL_FIELD_NOT_STRING",
    "MODEL_ID_MISMATCH",
    "CHOICES_MISSING",
    "CHOICES_NOT_LIST",
    "CHOICE_COUNT_INVALID",
    "CHOICE_NOT_OBJECT",
    "FINISH_REASON_MISSING",
    "FINISH_REASON_INVALID",
    "MESSAGE_MISSING",
    "MESSAGE_NOT_OBJECT",
    "ROLE_INVALID",
    "CONTENT_MISSING",
    "CONTENT_NULL",
    "CONTENT_NOT_STRING",
    "TOOL_CALL_PRESENT",
    "FUNCTION_CALL_PRESENT",
)


def test_closed_reason_vocabulary_has_fixture_coverage() -> None:
    assert {reason.value for reason in _ChatContractReason} == set(REASONS) | {
        "VALIDATED",
        "RESULT_CONSTRUCTION_FAILED",
    }


def broken_diagnostic(*args: object) -> NoReturn:
    raise ValueError(CANARY)


class Exchange:
    def __init__(self, raw: bytes, status: int = 200) -> None:
        self.raw, self.status = raw, status
        self.calls = 0

    def __call__(self, path: str, raw: bytes) -> tuple[int, bytes]:
        self.calls += 1
        assert path == "/chat/completions"
        assert json.loads(raw)["stream"] is False
        return self.status, self.raw


def adapter(exchange: Exchange) -> OpenAICompatibleModelAdapter:
    return OpenAICompatibleModelAdapter(
        OpenAICompatibleModelConfig(
            "https://synthetic.invalid/v1", "selected-model", None, 1, 512
        ),
        ProviderId("synthetic"),
        exchange=exchange,
    )


def request() -> ChatRequest:
    return ChatRequest((ChatMessage(ChatRole.USER, probe.TINY_PROMPT),))


@pytest.mark.parametrize("reason", REASONS)
def test_exact_rejection_reason_without_raw_content(reason: str) -> None:
    exchange = Exchange(rejected_body(reason))
    owner = adapter(exchange)
    with pytest.raises(ModelResponseRejectedError) as raised:
        asyncio.run(owner.chat(request()))
    assert raised.value.failure is ModelFailure.PROTOCOL_INCOMPATIBLE
    assert raised.value.__context__ is None and raised.value.__cause__ is None
    facts = dict(owner._chat_contract_items())
    assert facts["rejection_reason"] == reason
    assert facts["json_valid"] == ("false" if reason == "JSON_INVALID" else "true")
    assert CANARY not in repr(facts) + str(raised.value) + repr(owner)
    assert exchange.calls == 1
    if reason == "MODEL_ID_MISMATCH":
        assert facts["returned_model_matches_requested"] == "false"
    if reason in REASONS[:4]:
        assert "returned_model_matches_requested" not in facts


@pytest.mark.parametrize(
    "raw",
    [
        b'{"model":"a","model":"b"}',
        b'{"x":NaN}',
        b"\xff",
    ],
)
def test_strict_json_failure_is_distinct_from_root_shape(raw: bytes) -> None:
    owner = adapter(Exchange(raw))
    with pytest.raises(ModelResponseRejectedError) as raised:
        asyncio.run(owner.chat(request()))
    assert dict(owner._chat_contract_items())["rejection_reason"] == "JSON_INVALID"
    assert raised.value.__context__ is None


def test_json_decoder_recursion_failure_is_safely_rejected() -> None:
    # A fixed nesting depth need not exceed every runtime's decoder limit.
    owner = adapter(Exchange(b"[]"))
    with patch(
        "legoai.reference.model_openai_compatible.json.loads",
        side_effect=RecursionError(CANARY),
    ):
        with pytest.raises(ModelResponseRejectedError) as raised:
            _json_body(b"[]", _observer=owner._record_contract)
    assert dict(owner._chat_contract_items()) == {
        "rejection_reason": "JSON_INVALID",
        "json_valid": "false",
    }
    assert raised.value.failure is ModelFailure.PROTOCOL_INCOMPATIBLE
    assert raised.value.__context__ is None and raised.value.__cause__ is None
    assert CANARY not in str(raised.value) + repr(owner._chat_contract_items())


@pytest.mark.parametrize("raw", [b"null", b"1", b'"synthetic"', b"true", b"[]"])
def test_non_object_json_is_valid_json_but_invalid_contract(raw: bytes) -> None:
    owner = adapter(Exchange(raw))
    with pytest.raises(ModelResponseRejectedError):
        asyncio.run(owner.chat(request()))
    assert dict(owner._chat_contract_items()) == {
        "rejection_reason": "ROOT_NOT_OBJECT",
        "json_valid": "true",
    }


@pytest.mark.parametrize(
    "finish", ["length", "tool_calls", "content_filter", None, CANARY]
)
def test_finish_reason_policy_is_not_broadened(finish: object) -> None:
    payload = valid()
    payload["choices"][0]["finish_reason"] = finish
    # Later missing message must not hide the first failure.
    del payload["choices"][0]["message"]
    owner = adapter(Exchange(json.dumps(payload).encode()))
    with pytest.raises(ModelResponseRejectedError):
        asyncio.run(owner.chat(request()))
    facts = dict(owner._chat_contract_items())
    assert facts["rejection_reason"] == "FINISH_REASON_INVALID"


def test_multiple_choices_remain_refused() -> None:
    payload = valid()
    payload["choices"] *= 2
    owner = adapter(Exchange(json.dumps(payload).encode()))
    with pytest.raises(ModelResponseRejectedError):
        asyncio.run(owner.chat(request()))
    assert (
        dict(owner._chat_contract_items())["rejection_reason"] == "CHOICE_COUNT_INVALID"
    )


@pytest.mark.parametrize("content", ["KISSKI_OK", "wrong-token", "", CANARY])
@pytest.mark.parametrize(
    "usage",
    [
        None,
        "bad-shape",
        {},
        {"prompt_tokens": -1, "completion_tokens": True},
        {"prompt_tokens": 3, "completion_tokens": 2},
    ],
)
def test_valid_protocol_unknown_fields_and_permissive_usage(
    content: str, usage: object
) -> None:
    payload = valid()
    payload["usage"] = usage
    payload["unknown"] = CANARY
    message = payload["choices"][0]["message"]
    message["content"] = content
    message["reasoning_content"] = CANARY
    owner = adapter(Exchange(json.dumps(payload).encode()))
    result = asyncio.run(owner.chat(request()))
    assert result.content == content
    assert dict(owner._chat_contract_items())["rejection_reason"] == "VALIDATED"
    assert CANARY not in repr(owner._chat_contract_items())
    if isinstance(usage, dict):
        assert result.usage is not None
        expected = (3, 2) if usage.get("prompt_tokens") == 3 else (None, None)
        assert (result.usage.prompt_tokens, result.usage.completion_tokens) == expected
    else:
        assert result.usage is None


def test_usage_absent_and_reasoning_only_is_not_content() -> None:
    owner = adapter(Exchange(json.dumps(valid()).encode()))
    assert asyncio.run(owner.chat(request())).usage is None
    payload = valid()
    message = payload["choices"][0]["message"]
    del message["content"]
    message["reasoning_content"] = CANARY
    owner = adapter(Exchange(json.dumps(payload).encode()))
    with pytest.raises(ModelResponseRejectedError):
        asyncio.run(owner.chat(request()))
    assert dict(owner._chat_contract_items())["rejection_reason"] == "CONTENT_MISSING"


@pytest.mark.parametrize("key", ["tool_calls", "function_call"])
@pytest.mark.parametrize("value", [None, [], {}])
def test_tool_fields_refused_even_when_empty(key: str, value: object) -> None:
    payload = valid()
    payload["choices"][0]["message"][key] = value
    owner = adapter(Exchange(json.dumps(payload).encode()))
    with pytest.raises(ModelResponseRejectedError):
        asyncio.run(owner.chat(request()))


def test_result_construction_failure_keeps_original_exception() -> None:
    owner = adapter(Exchange(json.dumps(valid()).encode()))
    sentinel = ValueError("synthetic construction failure")
    with patch(
        "legoai.reference.model_openai_compatible.ChatResult", side_effect=sentinel
    ):
        with pytest.raises(ValueError) as raised:
            asyncio.run(owner.chat(request()))
    assert raised.value is sentinel
    facts = dict(owner._chat_contract_items())
    assert facts["rejection_reason"] == "RESULT_CONSTRUCTION_FAILED"


@pytest.mark.parametrize("valid_response", [False, True])
def test_recording_failure_does_not_change_acceptance(valid_response: bool) -> None:
    raw = (
        json.dumps(valid()).encode()
        if valid_response
        else rejected_body("JSON_INVALID")
    )
    owner = adapter(Exchange(raw))
    with patch.object(owner, "_record_contract", side_effect=ValueError(CANARY)):
        if valid_response:
            assert asyncio.run(owner.chat(request())).content == "KISSKI_OK"
        else:
            with pytest.raises(ModelResponseRejectedError) as raised:
                asyncio.run(owner.chat(request()))
            assert raised.value.failure is ModelFailure.PROTOCOL_INCOMPATIBLE
    assert owner._chat_contract_items() == ()


def test_no_stale_reason_on_reused_adapter_or_http_rejection() -> None:
    exchange = Exchange(rejected_body("MODEL_ID_MISMATCH"))
    owner = adapter(exchange)
    with pytest.raises(ModelResponseRejectedError):
        asyncio.run(owner.chat(request()))
    exchange.status = 401
    with pytest.raises(ModelResponseRejectedError):
        asyncio.run(owner.chat(request()))
    assert owner._chat_contract_items() == ()
    owner._contract_reason = cast(Any, CANARY)
    assert owner._chat_contract_items() == ()


@pytest.mark.parametrize(
    "case", ["valid", "wrong-token", "mismatch", "invalid-json", "incomplete"]
)
@pytest.mark.parametrize("fault", ["none", "record", "projection", "accessor"])
def test_governed_runner_content_free_diagnostics_and_effect_truth(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    case: str,
    fault: str,
) -> None:
    runner = Runner(tmp_path, monkeypatch)
    payload = valid()
    if case == "wrong-token":
        payload["choices"][0]["message"]["content"] = CANARY
    raw = json.dumps(payload).encode()
    if case == "mismatch":
        raw = rejected_body("MODEL_ID_MISMATCH")
    if case == "invalid-json":
        raw = rejected_body("JSON_INVALID")
    wire = b"%x\r\n%s\r\n0\r\n\r\n" % (len(raw), raw)
    if case == "incomplete":
        wire = b"3\r\nx"
    if fault == "record":
        monkeypatch.setattr(
            OpenAICompatibleModelAdapter, "_record_contract", broken_diagnostic
        )
    elif fault == "projection":
        monkeypatch.setattr(
            OpenAICompatibleModelAdapter, "_chat_contract_items", broken_diagnostic
        )
    elif fault == "accessor":
        monkeypatch.setattr(
            probe, "_remote_chat_contract_diagnostics", broken_diagnostic
        )
    answers = iter(("selected-model", "y"))
    with ResponseServer((HEAD + wire,), expected=CANARY) as server:
        outcome = probe.run(
            runner.config(server),
            ask=lambda _: next(answers),
            write=runner.lines.append,
            diagnostic_only=True,
        )
        assert server.requests == server.connections == 2
    expected = {
        "valid": probe.Outcome.CONNECTIVITY_ONLY,
        "wrong-token": probe.Outcome.CONTENT_REJECTED,
        "mismatch": probe.Outcome.CONTRACT_REJECTED,
        "invalid-json": probe.Outcome.CONTRACT_REJECTED,
        "incomplete": probe.Outcome.INCONCLUSIVE,
    }
    assert outcome is expected[case]
    state, facts = chat_custody(runner)
    assert state == ("unknown" if case == "incomplete" else "completed")
    completion = "response_incomplete" if case == "incomplete" else "response_complete"
    assert set(facts) == {"sent_all", completion}
    if case in {"mismatch", "invalid-json"}:
        assert "chat effect: none" in runner.lines
    if case == "incomplete":
        assert "chat effect: unknown" in runner.lines
    output = "\n".join(runner.lines)
    if fault == "none" and case != "incomplete":
        reason = {
            "mismatch": "MODEL_ID_MISMATCH",
            "invalid-json": "JSON_INVALID",
        }.get(case, "VALIDATED")
        assert f"chat contract rejection_reason: {reason}" in output
    else:
        assert "chat contract diagnostics: unavailable" in output
    if case in {"valid", "wrong-token"}:
        match = str(case == "valid").lower()
        assert f"chat contract expected_token_match: {match}" in output
    else:
        assert "chat contract expected_token_match:" not in output
    runner.no_leak(caplog)
