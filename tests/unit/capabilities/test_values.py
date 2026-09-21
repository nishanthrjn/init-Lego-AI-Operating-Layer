"""F7: Capability value construction/validation tests (PLUGIN-SPEC
PLG-006, PLG-008, PLG-015, PLG-040).
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from legoai.capabilities.values import (
    CapabilityId,
    CapabilityOffer,
    CapabilityRequirement,
    CapabilityVersionRange,
)
from legoai.kernel.versions import Version


class TestCapabilityId:
    def test_valid_construction(self) -> None:
        assert CapabilityId("text.normalize").value == "text.normalize"

    def test_empty_rejected(self) -> None:
        with pytest.raises(ValueError):
            CapabilityId("")

    def test_wrong_type_rejected(self) -> None:
        with pytest.raises(TypeError):
            CapabilityId(123)  # type: ignore[arg-type]

    def test_frozen(self) -> None:
        cid = CapabilityId("x")
        with pytest.raises(FrozenInstanceError):
            cid.value = "y"  # type: ignore[misc]

    def test_equality_is_structural(self) -> None:
        assert CapabilityId("x") == CapabilityId("x")
        assert CapabilityId("x") != CapabilityId("y")

    def test_hostile_text_remains_inert_data(self) -> None:
        hostile = CapabilityId("os.system('rm -rf /')")
        assert hostile.value == "os.system('rm -rf /')"


class TestCapabilityVersionRange:
    def test_minimum_only_is_unbounded_above(self) -> None:
        r = CapabilityVersionRange(Version(1, 0, 0))
        assert r.contains(Version(1, 0, 0))
        assert r.contains(Version(99, 0, 0))
        assert not r.contains(Version(0, 9, 0))

    def test_exclusive_minimum(self) -> None:
        r = CapabilityVersionRange(Version(1, 0, 0), minimum_inclusive=False)
        assert not r.contains(Version(1, 0, 0))
        assert r.contains(Version(1, 0, 1))

    def test_inclusive_maximum(self) -> None:
        r = CapabilityVersionRange(Version(1, 0, 0), maximum=Version(2, 0, 0))
        assert r.contains(Version(2, 0, 0))
        assert not r.contains(Version(2, 0, 1))

    def test_exclusive_maximum(self) -> None:
        r = CapabilityVersionRange(
            Version(1, 0, 0), maximum=Version(2, 0, 0), maximum_inclusive=False
        )
        assert not r.contains(Version(2, 0, 0))
        assert r.contains(Version(1, 9, 9))

    def test_exact_version_range(self) -> None:
        v = Version(1, 2, 3)
        r = CapabilityVersionRange(v, True, v, True)
        assert r.contains(v)
        assert not r.contains(Version(1, 2, 4))

    def test_minimum_exceeds_maximum_rejected(self) -> None:
        with pytest.raises(ValueError):
            CapabilityVersionRange(Version(2, 0, 0), maximum=Version(1, 0, 0))

    def test_empty_exclusive_range_rejected(self) -> None:
        v = Version(1, 0, 0)
        with pytest.raises(ValueError):
            CapabilityVersionRange(v, False, v, True)
        with pytest.raises(ValueError):
            CapabilityVersionRange(v, True, v, False)

    def test_wrong_type_minimum_rejected(self) -> None:
        with pytest.raises(TypeError):
            CapabilityVersionRange("1.0.0")  # type: ignore[arg-type]

    def test_wrong_type_maximum_rejected(self) -> None:
        with pytest.raises(TypeError):
            CapabilityVersionRange(Version(1, 0, 0), maximum="2.0.0")  # type: ignore[arg-type]

    def test_wrong_type_minimum_inclusive_rejected(self) -> None:
        with pytest.raises(TypeError):
            CapabilityVersionRange(Version(1, 0, 0), minimum_inclusive="yes")  # type: ignore[arg-type]

    def test_wrong_type_maximum_inclusive_rejected(self) -> None:
        with pytest.raises(TypeError):
            CapabilityVersionRange(
                Version(1, 0, 0),
                maximum=Version(2, 0, 0),
                maximum_inclusive="yes",  # type: ignore[arg-type]
            )

    def test_contains_wrong_type_rejected(self) -> None:
        r = CapabilityVersionRange(Version(1, 0, 0))
        with pytest.raises(TypeError):
            r.contains("1.5.0")  # type: ignore[arg-type]

    def test_no_implicit_zero_x_compatibility(self) -> None:
        # 0.x releases are never implicitly compatible with each other
        # (PLG-008) -- an explicit range is always required and honored
        # literally, with no special-cased 0.x leniency.
        r = CapabilityVersionRange(Version(0, 1, 0), maximum=Version(0, 1, 0))
        assert not r.contains(Version(0, 2, 0))


class TestCapabilityRequirement:
    def test_valid_construction(self) -> None:
        req = CapabilityRequirement(
            CapabilityId("x"), CapabilityVersionRange(Version(1, 0, 0))
        )
        assert req.capability == CapabilityId("x")

    def test_wrong_type_capability_rejected(self) -> None:
        with pytest.raises(TypeError):
            CapabilityRequirement("x", CapabilityVersionRange(Version(1, 0, 0)))  # type: ignore[arg-type]

    def test_wrong_type_range_rejected(self) -> None:
        with pytest.raises(TypeError):
            CapabilityRequirement(CapabilityId("x"), "1.0.0")  # type: ignore[arg-type]

    def test_frozen(self) -> None:
        req = CapabilityRequirement(
            CapabilityId("x"), CapabilityVersionRange(Version(1, 0, 0))
        )
        with pytest.raises(FrozenInstanceError):
            req.capability = CapabilityId("y")  # type: ignore[misc]


class TestCapabilityOffer:
    def test_valid_construction(self) -> None:
        offer = CapabilityOffer(CapabilityId("x"), Version(1, 0, 0))
        assert offer.version == Version(1, 0, 0)

    def test_wrong_type_capability_rejected(self) -> None:
        with pytest.raises(TypeError):
            CapabilityOffer("x", Version(1, 0, 0))  # type: ignore[arg-type]

    def test_wrong_type_version_rejected(self) -> None:
        with pytest.raises(TypeError):
            CapabilityOffer(CapabilityId("x"), "1.0.0")  # type: ignore[arg-type]

    def test_no_executable_field_exists(self) -> None:
        canary_invoked = False

        def canary() -> None:
            nonlocal canary_invoked
            canary_invoked = True

        with pytest.raises(TypeError):
            CapabilityOffer(canary, Version(1, 0, 0))  # type: ignore[arg-type]
        assert canary_invoked is False

    def test_equality_is_structural(self) -> None:
        a = CapabilityOffer(CapabilityId("x"), Version(1, 0, 0))
        b = CapabilityOffer(CapabilityId("x"), Version(1, 0, 0))
        assert a == b
        assert a is not b
