"""ADR-005 / F1: explicit attribution is not verification or permission."""

from collections.abc import Callable
from dataclasses import MISSING, FrozenInstanceError, fields, replace
from typing import cast

import pytest

from legoai.governance.values import OperationContext, Principal
from legoai.kernel.context import TenantContext
from legoai.kernel.identity import (
    ApplicationId,
    CorrelationId,
    OperationId,
    PrincipalId,
    RequestId,
    TenantId,
    TraceId,
)
from legoai.kernel.references import (
    ApplicationRef,
    ConfigurationRef,
    OperationRef,
    PrincipalRef,
    ReferenceScope,
)


def context(tenant: str) -> OperationContext:
    principal = Principal(PrincipalRef("identity-owner", PrincipalId("admin")))
    return OperationContext(
        OperationRef(
            ConfigurationRef(
                ApplicationRef(
                    ReferenceScope("composition", TenantId(tenant)),
                    ApplicationId("app"),
                ),
                "config",
            ),
            OperationId("operation"),
            "configuration",
        ),
        RequestId("request"),
        CorrelationId("correlation"),
        TraceId("trace"),
        TenantContext(TenantId(tenant)),
        principal,
        principal,
        None,
    )


def test_explicit_context_not_authority() -> None:
    first, second = context("first"), context("second")
    assert first.acting_principal == second.acting_principal
    assert first.tenant_context != second.tenant_context
    assert first != second
    assert first == replace(first)
    assert first.causation is None
    assert replace(first, trace_id=None).trace_id is None
    for value in (first, first.acting_principal, first.tenant_context):
        assert not any(
            hasattr(value, attr)
            for attr in (
                "authorized",
                "is_authenticated",
                "is_admin",
                "trusted",
                "permissions",
                "roles",
            )
        )
    assert not hasattr(first.acting_principal, "tenant_id")
    assert "admin" not in repr(first)
    # Missing arguments remain errors; no ambient/default tenant or principal.
    assert all(
        field.default is MISSING and field.default_factory is MISSING
        for field in fields(OperationContext)
    )
    with pytest.raises(TypeError):
        Principal(cast(PrincipalRef, PrincipalId("admin")))


def test_scope_and_causation_rejection() -> None:
    value = context("tenant")
    with pytest.raises(ValueError, match="tenant mismatch"):
        replace(value, tenant_context=TenantContext(TenantId("other")))
    with pytest.raises(ValueError, match="tenant mismatch"):
        replace(value, causation=context("other").operation)
    with pytest.raises(ValueError, match="itself"):
        replace(value, causation=value.operation)
    parent = replace(value.operation, operation_id=OperationId("parent"))
    assert replace(value, causation=parent).causation == parent
    with pytest.raises(ValueError, match="delegated"):
        replace(
            value,
            originating_requester=Principal(
                PrincipalRef("issuer", PrincipalId("other"))
            ),
        )


def test_context_boundary_and_immutability() -> None:
    value = context("tenant")
    for item in (value, value.acting_principal, value.tenant_context):
        original_hash = hash(item)
        assert not hasattr(item, "__dict__")
        for field in fields(item):
            with pytest.raises(FrozenInstanceError):
                setattr(item, field.name, None)
            invalid_inputs: tuple[object, ...] = (
                "raw",
                True,
                [],
                PrincipalId("wrong-kind"),
            )
            for invalid in invalid_inputs:
                with pytest.raises(TypeError):
                    cast(Callable[..., object], replace)(item, **{field.name: invalid})
            if field.name not in {"trace_id", "causation"}:
                with pytest.raises(TypeError):
                    cast(Callable[..., object], replace)(item, **{field.name: None})
        assert hash(item) == original_hash
