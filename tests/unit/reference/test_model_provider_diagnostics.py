"""Failure facts remain separate from effect phases and never carry raw errors."""

import asyncio
import urllib.error
from unittest.mock import patch

import pytest

from legoai.intelligence.model.ports import (
    ModelPreflightError,
    ModelResponseUncertainError,
)
from legoai.intelligence.model.values import ModelFailure
from tests.support.openai_http import Script, server
from tests.unit.reference.test_openai_compatible import CHAT, adapter


@pytest.mark.parametrize("reason", [ConnectionRefusedError(), TimeoutError()])
def test_connection_or_timeout_fact(reason: OSError) -> None:
    with patch(
        "urllib.request.OpenerDirector.open", side_effect=urllib.error.URLError(reason)
    ):
        with pytest.raises(
            (ModelPreflightError, ModelResponseUncertainError)
        ) as caught:
            asyncio.run(adapter("http://127.0.0.1:1/v1").chat(CHAT))
    assert caught.value.failure is (
        ModelFailure.TIMEOUT
        if isinstance(reason, TimeoutError)
        else ModelFailure.ENDPOINT_UNAVAILABLE
    )


def test_timeout_preserves_uncertain_effect_phase() -> None:
    script = Script({}, mode="timeout")
    with server(script) as url:
        with pytest.raises(ModelResponseUncertainError) as caught:
            asyncio.run(adapter(url, timeout=0.05).chat(CHAT))
    assert caught.value.failure is ModelFailure.TIMEOUT
    assert len(script.requests) == 1


def test_oversized_reply_stops_without_retry() -> None:
    script = Script(b"x" * 1_048_577)
    with server(script) as url:
        with pytest.raises(ModelResponseUncertainError) as caught:
            asyncio.run(adapter(url).chat(CHAT))
    assert caught.value.failure is ModelFailure.PROTOCOL_INCOMPATIBLE
    assert len(script.requests) == 1
