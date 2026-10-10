"""PROVIDER-MODEL-DISCOVERY-1: the governed credentialed model-catalog query.

ProviderDiscoveryAdmission -> INTENDED ProviderControlAttempt -> a new exact
Secret use (purpose provider-model-discovery) -> T2 `POST /v1/models` with an
empty body to a process-local synthetic TLS server -> settlement -> bounded
parser. Synthetic canaries only; no external network, provider or KISSKI.
"""

import json
import logging
import sqlite3
import traceback
from dataclasses import replace
from datetime import timedelta
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from legoai.governance.disclosure import DisclosureAdmission
from legoai.governance.provider_control import (
    DiscoveryRefusal,
    ProviderDiscoveryAdmission,
)
from legoai.governance.secret import SecretRevisionRef, UseRecoveryCategory
from legoai.intelligence.model.values import ModelId
from legoai.reference._custody_sqlite import _StorageGap
from legoai.reference._remote_attempts import AttemptState, _RemoteAttemptStore
from legoai.reference._secret_ledger import _inspect_source
from legoai.reference.secret import _ProvisionedSecretSource
from legoai.runtime._composition.provider_discovery import (
    DiscoveryEndpoint,
    DiscoveryOutcome,
)
from legoai.runtime._composition.remote_model import credential_purpose
from legoai.runtime.api import RemoteDisclosureConfig
from tests.support.provider_discovery import AT, HOUR, Discovery, discovery
from tests.support.tls_server import TlsServer
from tests.unit.governance.test_disclosure import admission as disclosure_admission
from tests.unit.governance.test_disclosure import declaration

CANARY = "discovery-key-CANARY-DO-NOT-LEAK-30416"
TASK = "TASK-CANARY-8812"
REPO = "REPOSITORY-CANARY-2290"
RAW = "RAW-MODEL-LIST-MARKER-55"
PATH = "/v1/models"


def listing(*ids: str, extra: dict[str, Any] | None = None) -> bytes:
    data = [{"id": i, "object": "model", "owned_by": RAW, **(extra or {})} for i in ids]
    return json.dumps({"object": "list", "data": data}).encode()


def server(mode: str = "ok", body: bytes | None = None) -> TlsServer:
    response = listing("model-a", "model-b") if body is None else body
    return TlsServer(mode, expected=CANARY, responses={PATH: response})


def attempts(x: Discovery) -> list[dict[str, Any]]:
    path = x.directory / "remote-attempts.db"
    conn = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
    try:
        rows = conn.execute(
            "SELECT attempt_id,state,observations,record FROM attempts ORDER BY rowid"
        ).fetchall()
    finally:
        conn.close()
    return [
        {
            "id": key,
            "state": state,
            "observations": set(json.loads(observed)),
            "record": json.loads(record),
        }
        for key, state, observed, record in rows
    ]


def uses(x: Discovery) -> list[Any]:
    statuses = _inspect_source(x.ledger, x.access())
    assert isinstance(statuses, tuple)
    return list(statuses)


def nothing(x: Discovery, tls: TlsServer) -> None:
    assert attempts(x) == [] and uses(x) == []
    assert tls.connections == 0


def leak_free(directory: Path, *values: object, log: str = "") -> None:
    for file in directory.rglob("*"):
        if file.is_file():
            data = file.read_bytes()
            for canary in (CANARY, TASK, REPO, RAW):
                assert canary.encode() not in data, (file, canary)
    for value in values:
        text = (
            "".join(traceback.format_exception(value))
            if isinstance(value, BaseException)
            else repr(value) + str(value)
        )
        for canary in (CANARY, RAW, "Bearer"):
            assert canary not in text, text
    assert CANARY not in log and RAW not in log


# --- Outcomes -----------------------------------------------------------------


def test_listed_models_through_the_governed_path(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.DEBUG)
    with server() as tls, discovery(tmp_path, tls.port, CANARY) as x:
        result = x.run()
        assert result.outcome is DiscoveryOutcome.LISTED
        assert result.models == (ModelId("model-a"), ModelId("model-b"))
        assert all(type(m) is ModelId for m in result.models)  # ids only
        assert result.status == 200 and result.state is AttemptState.COMPLETED
        # One fixed request: POST /v1/models, empty body, the exact credential.
        assert tls.paths == [f"POST {PATH}"]
        assert tls.bodies == [b""]
        assert tls.header_lines == [6]
        assert tls.authorized == [True]
        assert tls.connections == 1
        (attempt,) = attempts(x)
        assert result.attempt_id is not None
        assert attempt["id"] == result.attempt_id.value
        assert attempt["state"] == "completed"
        record = attempt["record"]
        assert record["kind"] == "provider-control-v2"
        assert record["method"] == "post_empty"
        assert record["control"] == "model-discovery"
        assert (record["admission_id"], record["admission_revision"]) == (
            "discovery",
            "d1",
        )
        # No fabricated disclosure, binding or model identities.
        for absent in ("declaration_id", "binding_id", "model", "capability"):
            assert absent not in record
        (use,) = uses(x)
        assert use.use_id.value == attempt["id"]
        assert use.category is UseRecoveryCategory.ACCEPTED_ATTRIBUTED
        assert use.accepted_fact.plan.purpose == "provider-model-discovery"
        leak_free(tmp_path, result, x.endpoint, x.admission, log=caplog.text)


def test_empty_listing_is_listed_with_no_models(tmp_path: Path) -> None:
    with server(body=listing()) as tls, discovery(tmp_path, tls.port, CANARY) as x:
        result = x.run()
    assert result.outcome is DiscoveryOutcome.LISTED and result.models == ()


@pytest.mark.parametrize(
    "body",
    [
        b"not json",
        b'{"object":"list"}',
        b'{"data":{"id":"model-a"}}',
        b'{"data":["model-a"]}',
        b'{"data":[{"object":"model"}]}',
        b'{"data":[{"id":7}]}',
        json.dumps({"data": [{"id": "x" * 257}]}).encode(),
        json.dumps({"data": [{"id": "bad" + chr(10) + "id"}]}).encode(),
        listing("model-a", "model-a"),
        listing(*(f"m-{i}" for i in range(1025))),
    ],
    ids=[
        "malformed-json",
        "missing-data",
        "data-not-list",
        "entry-not-object",
        "missing-id",
        "non-string-id",
        "oversized-id",
        "control-character-id",
        "duplicate-id",
        "excessive-count",
    ],
)
def test_malformed_listing_keeps_completed_transport_truth(
    tmp_path: Path, body: bytes
) -> None:
    with server(body=body) as tls, discovery(tmp_path, tls.port, CANARY) as x:
        result = x.run()
        assert result.outcome is DiscoveryOutcome.MALFORMED
        assert result.models == ()
        assert [a["state"] for a in attempts(x)] == ["completed"]
        assert tls.connections == 1


@pytest.mark.parametrize("mode", ["401", "403", "404", "405", "429", "500", "503"])
def test_complete_rejections_are_never_retried(tmp_path: Path, mode: str) -> None:
    echo = json.dumps({"error": f"bad key {CANARY}"}).encode()
    with server(mode, echo) as tls, discovery(tmp_path, tls.port, CANARY) as x:
        result = x.run()
        assert result.outcome is DiscoveryOutcome.PROVIDER_REJECTED
        assert result.status == int(mode)
        (attempt,) = attempts(x)
        assert attempt["state"] == "provider_rejected"
        assert tls.connections == 1 and tls.requests == 1
        (use,) = uses(x)
        assert use.category is UseRecoveryCategory.ACCEPTED_ATTRIBUTED
        leak_free(tmp_path, result)


@pytest.mark.parametrize("mode", ["truncated", "chunked", "malformed", "timeout"])
def test_incomplete_responses_are_unknown(tmp_path: Path, mode: str) -> None:
    with server(mode) as tls, discovery(tmp_path, tls.port, CANARY) as x:
        result = x.run(timeout=1.0)
        assert result.outcome is DiscoveryOutcome.UNKNOWN
        (attempt,) = attempts(x)
        assert attempt["state"] == "unknown"
        assert attempt["observations"] == {"sent_all", "response_incomplete"}
        assert tls.connections == 1


@pytest.mark.parametrize("cert", ["untrusted.pem", "wrong-host.pem"])
def test_tls_failure_is_not_sent_without_realization(tmp_path: Path, cert: str) -> None:
    with (
        TlsServer(cert=cert, expected=CANARY) as tls,
        discovery(tmp_path, tls.port, CANARY) as x,
        patch.object(_ProvisionedSecretSource, "_realize") as realize,
    ):
        result = x.run()
        realize.assert_not_called()
        assert result.outcome is DiscoveryOutcome.NOT_SENT
        (attempt,) = attempts(x)
        assert attempt["observations"] == {"sent_none"}
        assert tls.requests == 0


# --- Authority and security ------------------------------------------------------


def test_no_admission_reaches_nothing(tmp_path: Path) -> None:
    with server() as tls, discovery(tmp_path, tls.port, CANARY) as x:
        result = x.run(admission=None)
        assert result.outcome is DiscoveryOutcome.REFUSED
        assert result.refusal is DiscoveryRefusal.NO_ADMISSION
        nothing(x, tls)


def test_a_disclosure_admission_never_authorizes_discovery(tmp_path: Path) -> None:
    with server() as tls, discovery(tmp_path, tls.port, CANARY) as x:
        chat_authority = disclosure_admission(endpoint_origin=x.origin)
        result = x.run(admission=chat_authority)
        assert result.refusal is DiscoveryRefusal.NO_ADMISSION
        nothing(x, tls)


def test_a_discovery_admission_never_authorizes_disclosure(tmp_path: Path) -> None:
    with discovery(tmp_path, 9, CANARY) as x:
        with pytest.raises(TypeError):
            RemoteDisclosureConfig((declaration(),), (x.admission,))  # type: ignore[arg-type]
    assert not issubclass(ProviderDiscoveryAdmission, DisclosureAdmission)
    assert not issubclass(DisclosureAdmission, ProviderDiscoveryAdmission)
    assert ProviderDiscoveryAdmission.__mro__[1] is object


@pytest.mark.parametrize(
    ("changes", "refusal"),
    [
        (
            {"not_before": AT - 3 * HOUR, "not_after": AT - 2 * HOUR},
            DiscoveryRefusal.EXPIRED,
        ),
        (
            {"not_before": AT + HOUR, "not_after": AT + 2 * HOUR},
            DiscoveryRefusal.NOT_YET_VALID,
        ),
        ({"provider_id": "other-provider"}, DiscoveryRefusal.PROVIDER_MISMATCH),
        (
            {"endpoint_origin": "https://other.example.org"},
            DiscoveryRefusal.ENDPOINT_MISMATCH,
        ),
        ({"api_root": "/v2"}, DiscoveryRefusal.API_ROOT_MISMATCH),
        ({"consumer": "another-consumer"}, DiscoveryRefusal.CONSUMER_MISMATCH),
    ],
    ids=["expired", "not-yet-valid", "provider", "origin", "api-root", "consumer"],
)
def test_admission_mismatch_reaches_nothing(
    tmp_path: Path, changes: dict[str, Any], refusal: DiscoveryRefusal
) -> None:
    with server() as tls, discovery(tmp_path, tls.port, CANARY) as x:
        result = x.run(admission=replace(x.admission, **changes))
        assert result.outcome is DiscoveryOutcome.REFUSED
        assert result.refusal is refusal
        nothing(x, tls)


def test_other_credential_revision_reaches_nothing(tmp_path: Path) -> None:
    with server() as tls, discovery(tmp_path, tls.port, CANARY) as x:
        other = SecretRevisionRef(
            x.credential.exact.scope, "provider-key", "s1-other", "s1-map-other"
        )
        result = x.run(admission=replace(x.admission, credential=other))
        assert result.refusal is DiscoveryRefusal.CREDENTIAL_MISMATCH
        nothing(x, tls)


def test_operation_is_typed_and_fixed() -> None:
    with pytest.raises(TypeError):
        ProviderDiscoveryAdmission(
            "discovery",
            "d1",
            "remote-endpoint",
            "https://models.example.org",
            "/v1",
            "model-discovery",  # type: ignore[arg-type]
            "compat-probe",
            SecretRevisionRef(
                x_scope(), "provider-key", "s1-revision", "s1-map-revision"
            ),
            AT,
            AT + HOUR,
        )


def x_scope() -> Any:
    from tests.support.provider_discovery import SCOPE

    return SCOPE


def test_model_bearer_credential_purpose_reaches_nothing(tmp_path: Path) -> None:
    with (
        server() as tls,
        discovery(tmp_path, tls.port, CANARY, purpose=credential_purpose()) as x,
    ):
        result = x.run()
        assert result.refusal is DiscoveryRefusal.CREDENTIAL_MISMATCH
        nothing(x, tls)


def test_wrong_secret_consumer_is_refused_before_transport(tmp_path: Path) -> None:
    with (
        server() as tls,
        discovery(tmp_path, tls.port, CANARY, consumer="another-consumer") as x,
    ):
        result = x.run()
        assert result.outcome is DiscoveryOutcome.NOT_SENT
        (attempt,) = attempts(x)
        assert attempt["observations"] == {"refused_at_gate"}
        assert uses(x) == [] and tls.connections == 0


@pytest.mark.parametrize("kind", ["retired", "grant-revoked", "grant-expired"])
def test_stale_secret_authority_is_refused_before_transport(
    tmp_path: Path, kind: str
) -> None:
    with server() as tls, discovery(tmp_path, tls.port, CANARY) as x:
        if kind == "retired":
            x.source.retire(x.credential.exact)
        elif kind == "grant-revoked":
            x.grants.revoke(x.grant.grant_id)
        else:
            x.grant = replace(x.grant, expires_at=AT - timedelta(minutes=1))
        result = x.run()
        assert result.outcome is DiscoveryOutcome.NOT_SENT
        assert tls.connections == 0 and tls.requests == 0
        assert all(u.accepted_fact is None for u in uses(x))


def test_less_than_the_margin_refuses_inside_the_domain(tmp_path: Path) -> None:
    with server() as tls, discovery(tmp_path, tls.port, CANARY) as x:
        x.grant = replace(x.grant, expires_at=AT + timedelta(minutes=1))
        result = x.run()  # margin 5 minutes: refused at the final gate
        assert result.outcome is DiscoveryOutcome.NOT_SENT
        (attempt,) = attempts(x)
        assert attempt["observations"] == {"sent_none"}
        assert tls.requests == 0  # TLS only; no credential-bearing byte
        assert all(u.accepted_fact is None for u in uses(x))


def test_intended_failure_reaches_no_secret_or_network(tmp_path: Path) -> None:
    with (
        server() as tls,
        discovery(tmp_path, tls.port, CANARY) as x,
        patch.object(_RemoteAttemptStore, "intend", side_effect=_StorageGap("x")),
        patch.object(_ProvisionedSecretSource, "_realize") as realize,
    ):
        with pytest.raises(_StorageGap):
            x.run()
        realize.assert_not_called()
        assert uses(x) == [] and tls.connections == 0


def test_result_cannot_widen_authority_or_change_configuration(
    tmp_path: Path,
) -> None:
    with (
        server(body=listing("model-a", "admin-everything")) as tls,
        discovery(tmp_path, tls.port, CANARY) as x,
    ):
        before = (x.admission, x.endpoint)
        result = x.run()
        assert result.models == (ModelId("model-a"), ModelId("admin-everything"))
        # The admission names no models and no path: nothing to widen.
        assert (x.admission, x.endpoint) == before
        assert not hasattr(x.admission, "models")
        with pytest.raises(AttributeError):
            result.models = ()  # type: ignore[misc]


def test_each_call_is_one_attempt_one_use_one_request(tmp_path: Path) -> None:
    with server("503") as tls, discovery(tmp_path, tls.port, CANARY) as x:
        first, second = x.run(), x.run()
        assert first.attempt_id != second.attempt_id
        assert tls.connections == 2  # one per explicit call; never a retry
        assert len({u.use_id for u in uses(x)}) == 2


def test_ambient_keys_and_task_content_never_enter_the_request(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    for name in ("OPENAI_API_KEY", "KISSKI_API_KEY", "HTTPS_PROXY"):
        monkeypatch.setenv(name, f"{TASK}-{REPO}")
    with server() as tls, discovery(tmp_path, tls.port, CANARY) as x:
        result = x.run()
        assert result.outcome is DiscoveryOutcome.LISTED
        assert tls.authorized == [True]
        assert tls.bodies == [b""]
    leak_free(tmp_path, result)


def test_endpoint_requires_a_secret_reference() -> None:
    with pytest.raises(TypeError):
        DiscoveryEndpoint("p", "https://x.example.org", "/v1", "key")  # type: ignore[arg-type]
