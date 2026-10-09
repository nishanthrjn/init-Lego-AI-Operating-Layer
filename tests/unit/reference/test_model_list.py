"""PROVIDER-MODEL-DISCOVERY-1: the bounded model-list parser and `/models` target."""

import json

import pytest

from legoai.intelligence.model.ports import ModelResponseRejectedError
from legoai.intelligence.model.values import ModelId
from legoai.reference._credential_https import (
    HttpsTarget,
    TransportError,
    TransportFailure,
)
from legoai.reference.model_openai_compatible import parse_model_list


def test_ids_only_in_advertised_order() -> None:
    raw = json.dumps(
        {
            "object": "list",
            "data": [
                {"id": "b", "owned_by": "x", "created": 1},
                {"id": "a", "object": "model"},
            ],
        }
    ).encode()
    assert parse_model_list(raw) == (ModelId("b"), ModelId("a"))


def test_empty_listing() -> None:
    assert parse_model_list(b'{"data":[]}') == ()


@pytest.mark.parametrize(
    "raw",
    [
        b"",
        b"[]",
        b'{"data":null}',
        b'{"data":[1]}',
        b'{"data":[{"id":""}]}',
        b'{"data":[{"id":"   "}]}',
        b'{"data":[{"id":"a"},{"id":"a"}]}',
        b'{"data":[],"data":[]}',
        b'{"data":[{"id":NaN}]}',
        json.dumps({"data": [{"id": "m"} for _ in range(2)]}).encode(),
        json.dumps({"data": [{"id": f"m{i}"} for i in range(1025)]}).encode(),
    ],
)
def test_fail_closed_without_retaining_the_body(raw: bytes) -> None:
    with pytest.raises(ModelResponseRejectedError) as raised:
        parse_model_list(raw)
    assert raised.value.__cause__ is None and raised.value.__context__ is None


def test_bound_is_inclusive_at_1024() -> None:
    raw = json.dumps({"data": [{"id": f"m{i}"} for i in range(1024)]}).encode()
    assert len(parse_model_list(raw)) == 1024


def test_models_is_the_only_new_t2_path() -> None:
    target = HttpsTarget.for_endpoint("https://models.example.org", "/v1", "/models")
    assert target.request_path == "/v1/models"
    for path in ("/models/x", "/documents", "/completions", "/v1/models", "models"):
        with pytest.raises(TransportError) as raised:
            HttpsTarget.for_endpoint("https://models.example.org", "/v1", path)
        assert raised.value.failure is TransportFailure.ORIGIN
