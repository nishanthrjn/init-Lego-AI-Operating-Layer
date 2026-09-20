"""F1 / CTR-004, 009, 012, 013, 064: values cannot confer authority."""

from collections.abc import Callable
from dataclasses import FrozenInstanceError, fields, replace
from itertools import combinations
from typing import cast

import pytest

from legoai.kernel.context import TenantContext
from legoai.kernel.effects import EffectExtent
from legoai.kernel.errors import ErrorCategory, ErrorCause, ErrorDetail, Recoverability
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
    ApplicationRevisionRef,
    ConfigurationRef,
    ConfigurationRevisionRef,
    OperationRef,
    OwnerRevision,
    PrincipalRef,
    ReferenceScope,
)
from legoai.kernel.versions import Version

type Identity = ApplicationId | OperationId | RequestId | CorrelationId | TraceId


@pytest.mark.parametrize(
    "kind", [ApplicationId, OperationId, RequestId, CorrelationId, TraceId]
)
def test_added_id(kind: type[Identity]) -> None:
    for text in ("abc", " A ", " ", "é\t", "x" * 256):
        identity = kind(text)
        assert identity.value == text
        assert identity == kind(text)
        assert hash(identity) == hash(kind(text))
        with pytest.raises(FrozenInstanceError):
            setattr(identity, "value", "new")  # noqa: B010
        assert not hasattr(identity, "__dict__")
    for text in ("", "x" * 257):
        with pytest.raises(ValueError):
            kind(text)
    invalid_inputs: tuple[object, ...] = (None, True, 1, b"x", [], {})
    for value in invalid_inputs:
        with pytest.raises(TypeError):
            kind(cast(str, value))
    assert "canary" not in repr(kind("canary"))


def test_all_identity_kinds_distinct() -> None:
    identities: tuple[object, ...] = tuple(
        kind("same")
        for kind in (
            TenantId,
            PrincipalId,
            ApplicationId,
            OperationId,
            RequestId,
            CorrelationId,
            TraceId,
        )
    )
    for left, right in combinations(identities, 2):
        assert left != right and right != left
    assert len(set(identities)) == 7


def scope(tenant: str = "tenant", owner: str = "composition") -> ReferenceScope:
    return ReferenceScope(owner, TenantId(tenant))


def test_scoped_references_and_pins() -> None:
    app = ApplicationRef(scope(), ApplicationId("same"))
    config = ConfigurationRef(app, "same")
    operation = OperationRef(config, OperationId("same"), "configuration")
    assert operation != replace(operation, subject=replace(config, instance="other"))
    assert operation != replace(operation, subject=app)
    assert operation != replace(operation, contract_identity="other")
    assert len({app, config, operation}) == 3
    assert config != replace(config, application=replace(app, scope=scope("other")))
    assert config != replace(
        config, application=replace(app, scope=scope(owner="other"))
    )
    other_app = replace(app, application_id=ApplicationId("other"))
    other_config = replace(config, application=other_app)
    assert config != other_config
    assert operation != replace(operation, subject=other_config)
    pinned = ConfigurationRevisionRef(config, "1", Version(0, 1, 0))
    assert len({config, pinned, replace(pinned, revision="2")}) == 3
    assert pinned != replace(pinned, contract_version=Version(0, 2, 0))
    head = OwnerRevision(config, 1)
    assert len({head, pinned, Version(0, 1, 0)}) == 3
    assert head != replace(head, subject=other_config)
    assert head != replace(head, subject=replace(config, instance="other"))
    assert head != replace(
        head, subject=replace(config, application=replace(app, scope=scope("other")))
    )
    assert head != replace(
        head,
        subject=replace(config, application=replace(app, scope=scope(owner="other"))),
    )
    assert head == replace(head)
    assert {head: "found"}[replace(head)] == "found"
    app_revision = ApplicationRevisionRef(app, "1", Version(0, 1, 0))
    assert len({app, app_revision, pinned}) == 3
    principal = PrincipalRef("issuer", PrincipalId("same"))
    assert principal != replace(principal, issuer="another-issuer")
    for reference in (app, config, operation, pinned, head, app_revision, principal):
        assert not any(
            hasattr(reference, name)
            for name in (
                "resolve",
                "latest",
                "permissions",
                "authorized",
                "lookup",
                "next_revision",
            )
        )


@pytest.mark.parametrize("value", [-1, 0, True, False, "1", 1.0, None])
def test_owner_revision_rejects(value: object) -> None:
    with pytest.raises((TypeError, ValueError)):
        OwnerRevision(
            ConfigurationRef(ApplicationRef(scope(), ApplicationId("app")), "record"),
            cast(int, value),
        )


def test_version_ordering_and_no_compatibility_policy() -> None:
    assert Version(0, 1, 0) < Version(0, 2, 0) < Version(1, 0, 0)
    assert Version(1, 2, 9) < Version(1, 3, 0) < Version(2, 0, 0)
    assert Version(0, 0, 0) == Version(0, 0, 0)
    assert len({Version(0, 1, 0), Version(0, 2, 0), "0.1.0.dev0"}) == 3
    assert not hasattr(Version, "is_compatible_with")
    assert not hasattr(Version, "parse")
    for text in ("1.0.0", "1.0.0-alpha", ">=1.0", "v1", "0.1.0.dev0"):
        with pytest.raises(TypeError):
            Version(cast(int, text), 0, 0)
    with pytest.raises(TypeError):
        cast(Callable[..., object], replace)(Version(1, 0, 0), prerelease="alpha")


@pytest.mark.parametrize("field", ["major", "minor", "patch"])
@pytest.mark.parametrize("value", [-1, True, False, "1", 1.0, None])
def test_version_rejects(field: str, value: object) -> None:
    with pytest.raises((TypeError, ValueError)):
        cast(Callable[..., object], replace)(Version(0, 0, 0), **{field: value})


def test_effect_error_recovery_independence() -> None:
    assert {extent.value for extent in EffectExtent} == {
        "none",
        "partial",
        "completed",
        "unknown",
    }
    assert {recovery.value for recovery in Recoverability} == {
        "terminal",
        "potentially retryable",
        "requires intervention",
        "unknown",
    }
    assert {category.value for category in ErrorCategory} == {
        "ValidationError",
        "VersionMismatch",
        "TenantViolation",
        "Conflict",
        "DependencyFailure",
    }
    for category in ErrorCategory:
        for recovery in Recoverability:
            error = ErrorDetail(category, recovery, ())
            for effect in EffectExtent:
                assert error.category is category
                assert error.recoverability is recovery
                assert len({category, recovery, effect}) == 3
                assert not isinstance(error, Exception)
                assert not hasattr(error, "execution_state")
                assert not hasattr(error, "retry")
    for kind in (EffectExtent, ErrorCategory, Recoverability):
        with pytest.raises(ValueError):
            kind("unsupported")
    cause = ErrorCause(
        ErrorCategory.TENANT_VIOLATION,
        OperationRef(
            ApplicationRef(scope(), ApplicationId("app")),
            OperationId("op"),
            "application",
        ),
        "record",
    )
    other = replace(cause, category=ErrorCategory.CONFLICT, record_key="second")
    error = ErrorDetail(
        ErrorCategory.DEPENDENCY_FAILURE, Recoverability.UNKNOWN, (cause, other)
    )
    assert error.causes == (cause, other)
    assert "record" not in repr(error)
    with pytest.raises(TypeError):
        replace(error, causes=cast(tuple[ErrorCause, ...], [cause]))
    with pytest.raises(TypeError):
        replace(error, causes=cast(tuple[ErrorCause, ...], ("unsafe raw exception",)))


def test_nested_value_validation_and_immutability() -> None:
    app = ApplicationRef(scope(), ApplicationId("app"))
    config = ConfigurationRef(app, "config")
    op = OperationRef(config, OperationId("operation"), "configuration")
    cause = ErrorCause(ErrorCategory.CONFLICT, op, "record")
    values = (
        scope(),
        PrincipalRef("issuer", PrincipalId("principal")),
        app,
        ApplicationRevisionRef(app, "revision", Version(0, 1, 0)),
        config,
        ConfigurationRevisionRef(config, "revision", Version(0, 1, 0)),
        OwnerRevision(config, 1),
        op,
        TenantContext(TenantId("tenant")),
        Version(0, 1, 0),
        cause,
        ErrorDetail(ErrorCategory.CONFLICT, Recoverability.UNKNOWN, (cause,)),
    )
    for value in values:
        original_hash = hash(value)
        assert value == replace(value)
        assert not hasattr(value, "__dict__")
        for attribute in fields(value):
            with pytest.raises(FrozenInstanceError):
                setattr(value, attribute.name, None)
            invalid_inputs: tuple[object, ...] = (None, True, [], {}, "")
            for invalid in invalid_inputs:
                with pytest.raises((TypeError, ValueError)):
                    cast(Callable[..., object], replace)(
                        value, **{attribute.name: invalid}
                    )
            if type(getattr(value, attribute.name)) is str:
                with pytest.raises(ValueError):
                    cast(Callable[..., object], replace)(
                        value, **{attribute.name: "x" * 257}
                    )
        assert hash(value) == original_hash
