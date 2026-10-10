"""Discovery v2 request shapes, custody compatibility and bounded observations."""

import json
from dataclasses import replace
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from legoai.governance.provider_control import DiscoveryRefusal, ProviderDiscoveryMethod
from legoai.intelligence.model.ports import ModelResponseRejectedError
from legoai.reference._credential_https import (
    HttpsTarget,
    TransportError,
    _CredentialFlight,
    tls_context,
)
from legoai.reference._remote_attempts import ProviderControlAttempt, _decode, _encode
from legoai.reference.model_openai_compatible import (
    parse_model_catalog,
    parse_model_list,
)
from legoai.runtime._composition import credential_https
from legoai.runtime._composition.provider_discovery import DiscoveryOutcome
from tests.support.provider_discovery import discovery
from tests.support.tls_server import TEST_CA, TlsServer

CANARY = "synthetic-discovery-v2-CANARY-791"
GET = ProviderDiscoveryMethod.GET
POST = ProviderDiscoveryMethod.POST_EMPTY
PATH = "/v1/models"


def item(**changes: Any) -> dict[str, Any]:
    return {
        "id": "example/coder",
        "architecture": {"input_modalities": ["text"], "output_modalities": ["text"]},
        "providers": [
            {
                "provider": "backend",
                "status": "live",
                "pricing": {"input": 1, "output": 2},
            }
        ],
    } | changes


def listing(*items: dict[str, Any]) -> bytes:
    return json.dumps({"data": items}).encode()


@pytest.mark.parametrize("method,verb,headers", [(GET, "GET", 4), (POST, "POST", 6)])
def test_method_wire_custody_and_containment(
    tmp_path: Path, method: ProviderDiscoveryMethod, verb: str, headers: int
) -> None:
    with TlsServer(
        expected=CANARY, responses={PATH: listing(item())}, methods={PATH: verb}
    ) as tls:
        with discovery(
            tmp_path, tls.port, CANARY, method=method, selection_metadata=True
        ) as x:
            result = x.run()
            assert result.outcome is DiscoveryOutcome.LISTED
            assert result.catalog[0].providers[0].input_price == 1
            assert result.attempt_id is not None
            status = x.attempts.inspect(result.attempt_id)
            assert status is not None and isinstance(
                status.attempt, ProviderControlAttempt
            )
            assert status.attempt.method is method
            encoded = _encode(status.attempt)
            assert _decode(encoded) == status.attempt
            if method is POST:
                legacy = json.loads(encoded)
                legacy["kind"] = "provider-control"
                del legacy["method"]
                assert _decode(json.dumps(legacy)) == status.attempt
                legacy["method"] = "get"
                with pytest.raises(ValueError):
                    _decode(json.dumps(legacy))
            else:
                damaged = json.loads(encoded)
                del damaged["method"]
                with pytest.raises(ValueError):
                    _decode(json.dumps(damaged))
            assert tls.paths == [f"{verb} {PATH}"]
            assert tls.bodies == [b""] and tls.authorized == [True]
            assert tls.header_lines == [headers]
            assert set(tls.header_names[0]) == (
                {"host", "accept", "authorization", "connection"}
                | ({"content-length", "content-type"} if method is POST else set())
            )
            assert CANARY not in repr(result)
    for path in tmp_path.rglob("*"):
        if path.is_file():
            assert CANARY.encode() not in path.read_bytes()


@pytest.mark.parametrize("method,other", [(GET, POST), (POST, GET)])
def test_admission_mismatch_before_connection(
    tmp_path: Path, method: ProviderDiscoveryMethod, other: ProviderDiscoveryMethod
) -> None:
    with TlsServer(expected=CANARY) as tls:
        with discovery(tmp_path, tls.port, CANARY, method=method) as x:
            result = x.run(endpoint=replace(x.endpoint, method=other))
            assert result.refusal is DiscoveryRefusal.METHOD_MISMATCH
            assert result.attempt_id is None
            assert tls.connections == 0


@pytest.mark.parametrize("method,other", [(GET, POST), (POST, GET)])
def test_custody_mismatch_before_handoff(
    tmp_path: Path, method: ProviderDiscoveryMethod, other: ProviderDiscoveryMethod
) -> None:
    original = credential_https.exchange

    def substituted(*args: Any, **kwargs: Any) -> Any:
        changed = list(args)
        changed[4] = replace(changed[4], discovery_method=other)
        return original(*changed, **kwargs)

    with TlsServer(expected=CANARY) as tls:
        with discovery(tmp_path, tls.port, CANARY, method=method) as x:
            with patch(
                "legoai.runtime._composition.provider_discovery.exchange", substituted
            ):
                with pytest.raises(RuntimeError, match="not sent"):
                    x.run()
            assert tls.connections == 0


@pytest.mark.parametrize("method,required", [(GET, "POST"), (POST, "GET")])
def test_405_never_switches_method(
    tmp_path: Path, method: ProviderDiscoveryMethod, required: str
) -> None:
    with TlsServer(expected=CANARY, methods={PATH: required}) as tls:
        with discovery(tmp_path, tls.port, CANARY, method=method) as x:
            result = x.run()
            assert result.status == 405
            assert result.outcome is DiscoveryOutcome.PROVIDER_REJECTED
            assert tls.requests == 1 and tls.connections == 1


@pytest.mark.parametrize("method", [GET, POST])
def test_discovery_body_refused(method: ProviderDiscoveryMethod) -> None:
    target = HttpsTarget.for_endpoint(
        "https://example.org", "/v1", "/models", discovery_method=method
    )
    with pytest.raises(TransportError):
        _CredentialFlight(target, tls_context(TEST_CA), b"payload", timeout=1)


@pytest.mark.parametrize("bad", ["GET", "POST", "DELETE", None, 1])
def test_arbitrary_methods_refused(tmp_path: Path, bad: Any) -> None:
    assert {m.value for m in ProviderDiscoveryMethod} == {"get", "post_empty"}
    with TlsServer() as tls:
        with discovery(tmp_path, tls.port, CANARY) as x:
            with pytest.raises(TypeError):
                replace(x.admission, method=bad)
            with pytest.raises(TypeError):
                replace(x.endpoint, method=bad)
            assert tls.connections == 0


def test_get_cannot_be_used_for_model_chat() -> None:
    with pytest.raises(TransportError):
        HttpsTarget.for_endpoint(
            "https://example.org", "/v1", "/chat/completions", discovery_method=GET
        )


@pytest.mark.parametrize("option", ["method", "headers", "body", "url", "path"])
def test_discovery_has_no_arbitrary_request_surface(
    tmp_path: Path, option: str
) -> None:
    with TlsServer() as tls:
        with discovery(tmp_path, tls.port, CANARY, method=GET) as x:
            with pytest.raises(TypeError):
                x.run(**{option: "untrusted-input"})
            assert tls.connections == 0


def test_rich_and_id_only_profiles_remain_distinct() -> None:
    raw = listing(item(providers="ignored by v1"))
    assert len(parse_model_list(raw)) == 1
    with pytest.raises(ModelResponseRejectedError):
        parse_model_catalog(raw)
    assert parse_model_catalog(listing({"id": "only-id"}))[0].providers == ()
    models = parse_model_catalog(
        listing(item(), item(id="example/second", providers=[]))
    )
    assert len(models) == 2
    assert models[1].providers == ()


@pytest.mark.parametrize(
    "changes",
    [
        {"id": "m" * 257},
        {"providers": None},
        {"providers": [{"provider": "p"}, {"provider": "p"}]},
        {"providers": [{"provider": f"p{i}"} for i in range(33)]},
        {"providers": [{"provider": "p" * 129}]},
        {"providers": [{"provider": "p\n"}]},
        {"providers": [{"status": "live"}]},
        {"providers": [{"provider": "p", "status": "x" * 33}]},
        {"architecture": None},
        {"architecture": {"input_modalities": ["text"] * 9}},
        {"architecture": {"input_modalities": ["text", "text"]}},
        {"architecture": {"output_modalities": ["x" * 33]}},
    ],
)
def test_metadata_bounds(changes: dict[str, Any]) -> None:
    with pytest.raises(ModelResponseRejectedError):
        parse_model_catalog(listing(item(**changes)))


@pytest.mark.parametrize(
    "price", [-1, True, "1", float("inf"), float("nan"), 1_000_001]
)
def test_invalid_prices(price: Any) -> None:
    with pytest.raises(ModelResponseRejectedError):
        parse_model_catalog(
            listing(item(providers=[{"provider": "p", "pricing": {"input": price}}]))
        )


@pytest.mark.parametrize(
    "raw", [b"no-json", b'{"data":[],"data":[]}', b"[]", b" " * 4_194_305]
)
def test_invalid_response(raw: bytes) -> None:
    with pytest.raises(ModelResponseRejectedError):
        parse_model_catalog(raw)


def test_model_count_bound() -> None:
    with pytest.raises(ModelResponseRejectedError):
        parse_model_catalog(listing(*({"id": f"m{i}"} for i in range(1025))))
