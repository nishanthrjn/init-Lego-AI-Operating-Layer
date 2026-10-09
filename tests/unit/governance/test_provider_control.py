"""ADR-024 §22 provider-control authority: values and the pure evaluator."""

from dataclasses import FrozenInstanceError, replace
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from legoai.governance.provider_control import (
    DiscoveryRefusal,
    ProviderDiscoveryAdmission,
    ProviderOperation,
    evaluate_discovery,
)
from legoai.governance.secret import SecretRevisionRef
from legoai.kernel.identity import TenantId
from legoai.kernel.references import ReferenceScope

AT = datetime(2026, 10, 9, 12, tzinfo=UTC)
HOUR = timedelta(hours=1)
SECRET = SecretRevisionRef(
    ReferenceScope("operator", TenantId("t")), "key", "s1-r", "s1-m"
)


def admission(**changes: Any) -> ProviderDiscoveryAdmission:
    value = ProviderDiscoveryAdmission(
        "discovery",
        "d1",
        "remote-endpoint",
        "https://models.example.org",
        "/v1",
        ProviderOperation.MODEL_DISCOVERY,
        "compat-probe",
        SECRET,
        AT - HOUR,
        AT + HOUR,
    )
    return replace(value, **changes)


def decide(value: object, **changes: Any) -> DiscoveryRefusal | None:
    facts: dict[str, Any] = {
        "provider_id": "remote-endpoint",
        "endpoint_origin": "https://models.example.org",
        "api_root": "/v1",
        "operation": ProviderOperation.MODEL_DISCOVERY,
        "consumer": "compat-probe",
        "credential": SECRET,
        "at": AT,
    }
    return evaluate_discovery(value, **(facts | changes))  # type: ignore[arg-type]


def test_operation_vocabulary_is_closed() -> None:
    assert [o.value for o in ProviderOperation] == ["model-discovery"]


def test_admitted_exactly() -> None:
    assert decide(admission()) is None


@pytest.mark.parametrize(
    ("changes", "refusal"),
    [
        ({"at": AT - 2 * HOUR}, DiscoveryRefusal.NOT_YET_VALID),
        ({"at": AT + HOUR}, DiscoveryRefusal.EXPIRED),
        ({"provider_id": "other"}, DiscoveryRefusal.PROVIDER_MISMATCH),
        (
            {"endpoint_origin": "https://models.example.org:8443"},
            DiscoveryRefusal.ENDPOINT_MISMATCH,
        ),
        ({"api_root": "/v2"}, DiscoveryRefusal.API_ROOT_MISMATCH),
        ({"consumer": "other"}, DiscoveryRefusal.CONSUMER_MISMATCH),
        (
            {"credential": replace(SECRET, revision="s1-other")},
            DiscoveryRefusal.CREDENTIAL_MISMATCH,
        ),
    ],
)
def test_every_mismatch_refuses(
    changes: dict[str, Any], refusal: DiscoveryRefusal
) -> None:
    assert decide(admission(), **changes) is refusal


@pytest.mark.parametrize("value", [None, object(), "discovery"])
def test_anything_but_the_exact_type_is_no_admission(value: object) -> None:
    assert decide(value) is DiscoveryRefusal.NO_ADMISSION


@pytest.mark.parametrize(
    "changes",
    [
        {"provider_id": "*"},
        {"provider_id": " padded"},
        {"consumer": "probe?"},
        {"endpoint_origin": "http://models.example.org"},
        {"endpoint_origin": "https://Models.example.org"},
        {"api_root": "/v1/"},
        {"not_after": AT - HOUR},
        {"not_before": datetime(2026, 1, 1)},
    ],
    ids=[
        "wildcard-provider",
        "padded-provider",
        "wildcard-consumer",
        "plaintext-origin",
        "unnormalized-origin",
        "unnormalized-root",
        "inverted-window",
        "naive-time",
    ],
)
def test_no_wildcards_or_unnormalized_endpoints(changes: dict[str, Any]) -> None:
    with pytest.raises(ValueError):
        admission(**changes)


@pytest.mark.parametrize(
    "changes",
    [{"operation": "model-discovery"}, {"credential": "key"}],
)
def test_operation_and_credential_are_typed(changes: dict[str, Any]) -> None:
    with pytest.raises(TypeError):
        admission(**changes)


def test_immutable_and_reveals_no_identities_in_repr() -> None:
    value = admission()
    with pytest.raises(FrozenInstanceError):
        value.provider_id = "other"  # type: ignore[misc]
    text = repr(value)
    assert "models.example.org" not in text and "compat-probe" not in text
    assert "s1-r" not in text
