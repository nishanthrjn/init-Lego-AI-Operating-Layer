"""F7: pure Capability compatibility analysis tests (PLUGIN-SPEC PLG-017-
020, PLG-038; this batch's own SS19/SS39-45).

No network/database is used; all declarations are synthetic fixtures.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from legoai.capabilities.values import (
    CapabilityId,
    CapabilityOffer,
    CapabilityRequirement,
    CapabilityVersionRange,
)
from legoai.kernel.versions import Version
from legoai.plugins.values import PluginDeclaration, PluginId
from legoai.reference.resolution import (
    CandidateOffer,
    CompatibilityAnalysis,
    CompatibilityStatus,
    analyze_compatibility,
    analyze_requirements,
)

TEXT_NORMALIZE = CapabilityId("text.normalize")
IMAGE_RESIZE = CapabilityId("image.resize")


def _requirement(
    capability: CapabilityId = TEXT_NORMALIZE, minimum: Version | None = None
) -> CapabilityRequirement:
    return CapabilityRequirement(
        capability, CapabilityVersionRange(minimum or Version(1, 0, 0))
    )


def _declaration(
    namespace: str,
    local_id: str,
    release: Version,
    capability: CapabilityId,
    version: Version,
) -> PluginDeclaration:
    return PluginDeclaration(
        PluginId(namespace, local_id), release, (CapabilityOffer(capability, version),)
    )


class TestUniqueMatch:
    def test_one_requirement_one_compatible_offer(self) -> None:
        declaration = _declaration(
            "org.a", "norm", Version(1, 0, 0), TEXT_NORMALIZE, Version(1, 0, 0)
        )
        result = analyze_compatibility(_requirement(), (declaration,))
        assert result.status is CompatibilityStatus.UNIQUE_MATCH
        assert len(result.candidates) == 1
        assert result.candidates[0].plugin_id == declaration.plugin_id


class TestNoMatch:
    def test_one_requirement_no_offers(self) -> None:
        result = analyze_compatibility(_requirement(), ())
        assert result.status is CompatibilityStatus.NO_MATCH
        assert result.candidates == ()

    def test_wrong_capability_identity_never_matches(self) -> None:
        # Offers for a different capability identity must never cross-match
        # even with an otherwise-satisfying version.
        declaration = _declaration(
            "org.a", "resize", Version(1, 0, 0), IMAGE_RESIZE, Version(1, 0, 0)
        )
        result = analyze_compatibility(_requirement(TEXT_NORMALIZE), (declaration,))
        assert result.status is CompatibilityStatus.NO_MATCH

    def test_incompatible_version_never_matches(self) -> None:
        declaration = _declaration(
            "org.a", "norm", Version(1, 0, 0), TEXT_NORMALIZE, Version(0, 9, 0)
        )
        result = analyze_compatibility(
            _requirement(minimum=Version(1, 0, 0)), (declaration,)
        )
        assert result.status is CompatibilityStatus.NO_MATCH


class TestAmbiguity:
    def test_two_plugins_offering_same_capability_are_ambiguous(self) -> None:
        declaration_a = _declaration(
            "org.a", "norm", Version(1, 0, 0), TEXT_NORMALIZE, Version(1, 0, 0)
        )
        declaration_b = _declaration(
            "org.b", "norm", Version(1, 0, 0), TEXT_NORMALIZE, Version(1, 5, 0)
        )
        result = analyze_compatibility(_requirement(), (declaration_a, declaration_b))
        assert result.status is CompatibilityStatus.AMBIGUOUS
        assert len(result.candidates) == 2

    def test_ambiguous_does_not_prefer_highest_version(self) -> None:
        declaration_a = _declaration(
            "org.a", "norm", Version(1, 0, 0), TEXT_NORMALIZE, Version(9, 0, 0)
        )
        declaration_b = _declaration(
            "org.b", "norm", Version(1, 0, 0), TEXT_NORMALIZE, Version(1, 0, 0)
        )
        result = analyze_compatibility(_requirement(), (declaration_a, declaration_b))
        assert result.status is CompatibilityStatus.AMBIGUOUS
        # Both candidates remain present -- neither is dropped/selected.
        versions = {c.capability_version for c in result.candidates}
        assert versions == {Version(9, 0, 0), Version(1, 0, 0)}

    def test_ambiguous_does_not_prefer_alphabetical_plugin(self) -> None:
        declaration_a = _declaration(
            "zzz.org", "norm", Version(1, 0, 0), TEXT_NORMALIZE, Version(1, 0, 0)
        )
        declaration_b = _declaration(
            "aaa.org", "norm", Version(1, 0, 0), TEXT_NORMALIZE, Version(1, 0, 0)
        )
        result = analyze_compatibility(_requirement(), (declaration_a, declaration_b))
        assert result.status is CompatibilityStatus.AMBIGUOUS
        namespaces = {c.plugin_id.namespace for c in result.candidates}
        assert namespaces == {"zzz.org", "aaa.org"}

    def test_no_candidate_is_selected_in_ambiguous_result(self) -> None:
        declaration_a = _declaration(
            "org.a", "norm", Version(1, 0, 0), TEXT_NORMALIZE, Version(1, 0, 0)
        )
        declaration_b = _declaration(
            "org.b", "norm", Version(1, 0, 0), TEXT_NORMALIZE, Version(1, 0, 0)
        )
        result = analyze_compatibility(_requirement(), (declaration_a, declaration_b))
        # There is no "selected"/"winner" field anywhere on the result.
        assert not hasattr(result, "selected")
        assert not hasattr(result, "winner")
        assert not hasattr(result, "chosen")


class TestPluginIdentityIsolation:
    def test_offers_from_different_plugins_remain_individually_attributed(self) -> None:
        declaration_a = _declaration(
            "org.a", "norm", Version(1, 0, 0), TEXT_NORMALIZE, Version(1, 0, 0)
        )
        declaration_b = _declaration(
            "org.b", "norm", Version(1, 0, 0), TEXT_NORMALIZE, Version(1, 0, 0)
        )
        result = analyze_compatibility(_requirement(), (declaration_a, declaration_b))
        plugin_ids = {c.plugin_id for c in result.candidates}
        assert plugin_ids == {declaration_a.plugin_id, declaration_b.plugin_id}


class TestMultiRequirementAnalysis:
    def test_one_resolved_one_unresolved_preserved_independently(self) -> None:
        declaration = _declaration(
            "org.a", "norm", Version(1, 0, 0), TEXT_NORMALIZE, Version(1, 0, 0)
        )
        results = analyze_requirements(
            (_requirement(TEXT_NORMALIZE), _requirement(IMAGE_RESIZE)), (declaration,)
        )
        assert results[0].status is CompatibilityStatus.UNIQUE_MATCH
        assert results[1].status is CompatibilityStatus.NO_MATCH

    def test_no_flattened_global_success_field(self) -> None:
        results = analyze_requirements((_requirement(),), ())
        assert isinstance(results, tuple)
        assert not hasattr(results, "overall_status")
        assert not hasattr(results, "success")


class TestDeterminism:
    def test_repeated_analysis_yields_identical_result(self) -> None:
        declaration_a = _declaration(
            "org.a", "norm", Version(1, 0, 0), TEXT_NORMALIZE, Version(1, 0, 0)
        )
        declaration_b = _declaration(
            "org.b", "norm", Version(1, 0, 0), TEXT_NORMALIZE, Version(1, 0, 0)
        )
        first = analyze_compatibility(_requirement(), (declaration_a, declaration_b))
        second = analyze_compatibility(_requirement(), (declaration_b, declaration_a))
        assert first == second


class TestCandidateOfferValidation:
    def test_wrong_type_plugin_id_rejected(self) -> None:
        with pytest.raises(TypeError):
            CandidateOffer("not-a-plugin-id", Version(1, 0, 0), Version(1, 0, 0))  # type: ignore[arg-type]

    def test_wrong_type_release_rejected(self) -> None:
        with pytest.raises(TypeError):
            CandidateOffer(PluginId("org", "p"), "1.0.0", Version(1, 0, 0))  # type: ignore[arg-type]

    def test_wrong_type_capability_version_rejected(self) -> None:
        with pytest.raises(TypeError):
            CandidateOffer(PluginId("org", "p"), Version(1, 0, 0), "1.0.0")  # type: ignore[arg-type]


class TestAnalyzeFunctionInputValidation:
    def test_analyze_compatibility_rejects_wrong_requirement_type(self) -> None:
        with pytest.raises(TypeError):
            analyze_compatibility("not-a-requirement", ())  # type: ignore[arg-type]

    def test_analyze_compatibility_rejects_wrong_declarations_type(self) -> None:
        with pytest.raises(TypeError):
            analyze_compatibility(_requirement(), [])  # type: ignore[arg-type]

    def test_analyze_compatibility_rejects_non_declaration_element(self) -> None:
        with pytest.raises(TypeError):
            analyze_compatibility(_requirement(), ("not-a-declaration",))  # type: ignore[arg-type]

    def test_analyze_requirements_rejects_wrong_requirements_type(self) -> None:
        with pytest.raises(TypeError):
            analyze_requirements([_requirement()], ())  # type: ignore[arg-type]

    def test_analyze_requirements_rejects_non_requirement_element(self) -> None:
        with pytest.raises(TypeError):
            analyze_requirements(("not-a-requirement",), ())  # type: ignore[arg-type]


class TestCompatibilityAnalysisValidation:
    def test_wrong_type_requirement_rejected(self) -> None:
        candidate = CandidateOffer(
            PluginId("org", "p"), Version(1, 0, 0), Version(1, 0, 0)
        )
        with pytest.raises(TypeError):
            CompatibilityAnalysis(
                "not-a-requirement",  # type: ignore[arg-type]
                CompatibilityStatus.UNIQUE_MATCH,
                (candidate,),
            )

    def test_wrong_type_status_rejected(self) -> None:
        with pytest.raises(TypeError):
            CompatibilityAnalysis(_requirement(), "unique_match", ())  # type: ignore[arg-type]

    def test_wrong_type_candidates_rejected(self) -> None:
        with pytest.raises(TypeError):
            CompatibilityAnalysis(
                _requirement(),
                CompatibilityStatus.NO_MATCH,
                ["not-a-tuple"],  # type: ignore[arg-type]
            )

    def test_candidates_element_wrong_type_rejected(self) -> None:
        with pytest.raises(TypeError):
            CompatibilityAnalysis(
                _requirement(),
                CompatibilityStatus.UNIQUE_MATCH,
                ("not-a-candidate",),  # type: ignore[arg-type]
            )

    def test_unique_match_requires_exactly_one_candidate(self) -> None:
        with pytest.raises(ValueError):
            CompatibilityAnalysis(_requirement(), CompatibilityStatus.UNIQUE_MATCH, ())

    def test_no_match_requires_zero_candidates(self) -> None:
        candidate = CandidateOffer(
            PluginId("org", "p"), Version(1, 0, 0), Version(1, 0, 0)
        )
        with pytest.raises(ValueError):
            CompatibilityAnalysis(
                _requirement(), CompatibilityStatus.NO_MATCH, (candidate,)
            )

    def test_ambiguous_requires_at_least_two_candidates(self) -> None:
        candidate = CandidateOffer(
            PluginId("org", "p"), Version(1, 0, 0), Version(1, 0, 0)
        )
        with pytest.raises(ValueError):
            CompatibilityAnalysis(
                _requirement(), CompatibilityStatus.AMBIGUOUS, (candidate,)
            )


class TestNoExecutableBinding:
    def test_analyze_compatibility_returns_no_callable(self) -> None:
        declaration = _declaration(
            "org.a", "norm", Version(1, 0, 0), TEXT_NORMALIZE, Version(1, 0, 0)
        )
        result = analyze_compatibility(_requirement(), (declaration,))
        for candidate in result.candidates:
            assert not callable(candidate)
            # The candidate's only public fields are plugin_id/release/
            # capability_version -- none is or can become a Provider/
            # Adapter callable.
            assert not callable(candidate.plugin_id)
            assert not callable(candidate.release)
            assert not callable(candidate.capability_version)

    def test_module_source_contains_no_dynamic_execution(self) -> None:
        import legoai.reference.resolution as module

        assert module.__file__ is not None
        tree = ast.parse(Path(module.__file__).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                assert node.func.id not in {
                    "eval",
                    "exec",
                    "compile",
                    "__import__",
                }
            if isinstance(node, ast.Import):
                assert not {alias.name for alias in node.names} & {
                    "importlib",
                    "subprocess",
                }
