"""F4: narrow Evidence value tests."""

from __future__ import annotations

import pytest

from legoai.evidence.values import EvidenceRequirement
from legoai.kernel.identity import ApplicationId, TenantId
from legoai.kernel.references import (
    ApplicationRef,
    ConfigurationRef,
    ConfigurationRevisionRef,
    ReferenceScope,
)
from legoai.kernel.versions import Version

VERSION = Version(0, 1, 0)


def _subject() -> ConfigurationRevisionRef:
    scope = ReferenceScope("owner1", TenantId("t1"))
    target = ConfigurationRef(ApplicationRef(scope, ApplicationId("app1")), "inst1")
    return ConfigurationRevisionRef(target, "r1", VERSION)


def test_valid_construction() -> None:
    requirement = EvidenceRequirement(_subject(), "source submission evidence required")
    assert requirement.description == "source submission evidence required"


def test_wrong_subject_type_rejected() -> None:
    with pytest.raises(TypeError):
        EvidenceRequirement("not-a-revision-ref", "evidence needed")  # type: ignore[arg-type]


def test_empty_description_rejected() -> None:
    with pytest.raises(ValueError):
        EvidenceRequirement(_subject(), "")


def test_wrong_description_type_rejected() -> None:
    with pytest.raises(TypeError):
        EvidenceRequirement(_subject(), 12345)  # type: ignore[arg-type]


def test_frozen() -> None:
    requirement = EvidenceRequirement(_subject(), "evidence needed")
    with pytest.raises(AttributeError):
        requirement.description = "mutated"  # type: ignore[misc]  # noqa: B010


def test_equality_is_structural() -> None:
    subject = _subject()
    assert EvidenceRequirement(subject, "evidence needed") == EvidenceRequirement(
        subject, "evidence needed"
    )
