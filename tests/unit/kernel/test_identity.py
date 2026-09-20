"""SPEC identity distinction; ADR-002 Kernel; Gate-1 F0 input/immutability rules."""

from dataclasses import FrozenInstanceError
from typing import cast

import pytest

from legoai.kernel.identity import PrincipalId, TenantId


@pytest.mark.parametrize("kind", [TenantId, PrincipalId])
@pytest.mark.parametrize("text", ["abc", " A ", " ", "é\tABC", "x" * 256])
def test_exact_value(kind: type[TenantId] | type[PrincipalId], text: str) -> None:
    value = kind(text)
    assert value.value == text
    assert value == kind(text)
    assert hash(value) == hash(kind(text))
    assert {value: "found"}[kind(text)] == "found"


@pytest.mark.parametrize("kind", [TenantId, PrincipalId])
@pytest.mark.parametrize("text", ["", "x" * 257])
def test_length_rejected(kind: type[TenantId] | type[PrincipalId], text: str) -> None:
    with pytest.raises(ValueError, match="1–256"):
        kind(text)


@pytest.mark.parametrize("kind", [TenantId, PrincipalId])
@pytest.mark.parametrize("value", [None, 1, True, b"abc", [], {}])
def test_no_coercion(kind: type[TenantId] | type[PrincipalId], value: object) -> None:
    # Deliberately cross the annotated boundary to test runtime validation.
    with pytest.raises(TypeError, match="must be text"):
        kind(cast(str, value))


def test_subclass_rejected() -> None:
    class Text(str):
        pass

    with pytest.raises(TypeError):
        TenantId(Text("abc"))


@pytest.mark.parametrize("kind", [TenantId, PrincipalId])
def test_immutable(kind: type[TenantId] | type[PrincipalId]) -> None:
    value = kind("abc")
    original_hash = hash(value)
    with pytest.raises(FrozenInstanceError):
        # Exercise runtime rejection without adding a static assignment error.
        setattr(value, "value", "changed")  # noqa: B010
    assert not hasattr(value, "__dict__")
    assert value.value == "abc"
    assert hash(value) == original_hash


def test_nominal_distinction() -> None:
    tenant: object = TenantId("abc")
    principal: object = PrincipalId("abc")
    assert tenant != principal
    assert principal != tenant
    values: set[object] = {TenantId("abc"), PrincipalId("abc"), "abc"}
    assert len(values) == 3
    assert TenantId("abc") != TenantId("ABC")


def test_representation_omits_identity_text() -> None:
    assert repr(TenantId("sensitive-canary")) == "TenantId()"
    assert repr(PrincipalId("sensitive-canary")) == "PrincipalId()"
