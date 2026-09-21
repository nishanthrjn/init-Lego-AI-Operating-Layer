"""F7: Plugin declaration value construction/validation tests (PLUGIN-SPEC
PLG-004-014).
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
from legoai.plugins.values import PluginDeclaration, PluginId


class TestPluginId:
    def test_valid_construction(self) -> None:
        pid = PluginId("example.org", "text-normalizer")
        assert pid.namespace == "example.org"
        assert pid.local_id == "text-normalizer"

    def test_empty_namespace_rejected(self) -> None:
        with pytest.raises(ValueError):
            PluginId("", "x")

    def test_empty_local_id_rejected(self) -> None:
        with pytest.raises(ValueError):
            PluginId("x", "")

    def test_wrong_type_rejected(self) -> None:
        with pytest.raises(TypeError):
            PluginId(123, "x")  # type: ignore[arg-type]

    def test_frozen(self) -> None:
        pid = PluginId("a", "b")
        with pytest.raises(FrozenInstanceError):
            pid.namespace = "c"  # type: ignore[misc]

    def test_two_plugins_with_different_identity_remain_distinct(self) -> None:
        # PLG identity isolation: namespace collision alone does not equate
        # two different local IDs, and vice versa.
        assert PluginId("org", "a") != PluginId("org", "b")
        assert PluginId("org-a", "x") != PluginId("org-b", "x")

    def test_hostile_text_remains_inert_data(self) -> None:
        pid = PluginId("../../etc", "import os; os.system('x')")
        assert pid.namespace == "../../etc"
        assert pid.local_id == "import os; os.system('x')"


def _offer(cap: str = "x", version: Version | None = None) -> CapabilityOffer:
    return CapabilityOffer(CapabilityId(cap), version or Version(1, 0, 0))


def _requirement(
    cap: str = "x", minimum: Version | None = None
) -> CapabilityRequirement:
    return CapabilityRequirement(
        CapabilityId(cap), CapabilityVersionRange(minimum or Version(1, 0, 0))
    )


class TestPluginDeclaration:
    def test_valid_minimal_construction(self) -> None:
        decl = PluginDeclaration(PluginId("org", "p"), Version(1, 0, 0))
        assert decl.offers == ()
        assert decl.requirements == ()

    def test_valid_full_construction(self) -> None:
        decl = PluginDeclaration(
            PluginId("org", "p"),
            Version(1, 0, 0),
            (_offer(),),
            (_requirement(),),
        )
        assert len(decl.offers) == 1
        assert len(decl.requirements) == 1

    def test_frozen(self) -> None:
        decl = PluginDeclaration(PluginId("org", "p"), Version(1, 0, 0))
        with pytest.raises(FrozenInstanceError):
            decl.release = Version(2, 0, 0)  # type: ignore[misc]

    def test_wrong_type_plugin_id_rejected(self) -> None:
        with pytest.raises(TypeError):
            PluginDeclaration("not-a-plugin-id", Version(1, 0, 0))  # type: ignore[arg-type]

    def test_wrong_type_release_rejected(self) -> None:
        with pytest.raises(TypeError):
            PluginDeclaration(PluginId("org", "p"), "1.0.0")  # type: ignore[arg-type]

    def test_offers_wrong_type_rejected(self) -> None:
        with pytest.raises(TypeError):
            PluginDeclaration(PluginId("org", "p"), Version(1, 0, 0), [_offer()])  # type: ignore[arg-type]

    def test_offers_element_wrong_type_rejected(self) -> None:
        with pytest.raises(TypeError):
            PluginDeclaration(
                PluginId("org", "p"),
                Version(1, 0, 0),
                ("not-an-offer",),  # type: ignore[arg-type]
            )

    def test_requirements_wrong_type_rejected(self) -> None:
        with pytest.raises(TypeError):
            PluginDeclaration(
                PluginId("org", "p"),
                Version(1, 0, 0),
                (),
                [_requirement()],  # type: ignore[arg-type]
            )

    def test_duplicate_offer_same_capability_and_version_rejected(self) -> None:
        offer = _offer()
        with pytest.raises(ValueError):
            PluginDeclaration(PluginId("org", "p"), Version(1, 0, 0), (offer, offer))

    def test_two_versions_of_same_capability_allowed(self) -> None:
        # PLUGIN-SPEC does not prohibit a release offering the same
        # capability at two different exact versions -- this batch does
        # not invent that restriction.
        decl = PluginDeclaration(
            PluginId("org", "p"),
            Version(1, 0, 0),
            (_offer(version=Version(1, 0, 0)), _offer(version=Version(2, 0, 0))),
        )
        assert len(decl.offers) == 2

    def test_no_implementation_locator_field_exists(self) -> None:
        decl = PluginDeclaration(PluginId("org", "p"), Version(1, 0, 0))
        for forbidden in (
            "module",
            "class_name",
            "entry_point",
            "factory",
            "command",
            "url",
            "executable",
        ):
            assert not hasattr(decl, forbidden)

    def test_cannot_pass_callable_as_unsupported_field(self) -> None:
        canary_invoked = False

        def canary() -> None:
            nonlocal canary_invoked
            canary_invoked = True

        with pytest.raises(TypeError):
            PluginDeclaration(  # type: ignore[call-arg]
                PluginId("org", "p"), Version(1, 0, 0), factory=canary
            )
        assert canary_invoked is False
