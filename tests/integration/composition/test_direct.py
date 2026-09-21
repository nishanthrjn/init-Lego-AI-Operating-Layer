"""F8b: private direct composition integration tests (Gate-1 plan SS13's
"internal walking skeleton", composition-experiment half).

These prove F2 + F7 + F8a + the one F8b deterministic fixture compose
coherently through ``compose_direct`` without any Gate-2 concept
(Execution, CapabilityResolver, admission, authorization) appearing.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from legoai.application.values import (
    CapturedCandidate,
    NormalizationMode,
    NormalizationPatch,
    SourceLayer,
    SourceProvenance,
)
from legoai.capabilities.values import (
    CapabilityId,
    CapabilityOffer,
    CapabilityRequirement,
    CapabilityVersionRange,
)
from legoai.kernel.identity import ApplicationId, TenantId
from legoai.kernel.references import ApplicationRef, ConfigurationRef, ReferenceScope
from legoai.kernel.versions import Version
from legoai.plugins.values import PluginDeclaration, PluginId
from legoai.reference.deterministic import (
    text_normalization_capability_id,
    text_normalization_declaration,
    text_normalization_release,
)
from legoai.runtime._composition.direct import (
    CompositionResult,
    CompositionStatus,
    compose_direct,
)
from tests.support.observation import CapturingObservationSink, FailingObservationSink

VERSION = Version(0, 1, 0)


def _target(instance: str = "inst1") -> ConfigurationRef:
    scope = ReferenceScope("owner1", TenantId("t1"))
    return ConfigurationRef(ApplicationRef(scope, ApplicationId("app1")), instance)


def _normalization_requirement() -> CapabilityRequirement:
    return CapabilityRequirement(
        text_normalization_capability_id(),
        CapabilityVersionRange(text_normalization_release()),
    )


def _compose(**overrides: object) -> CompositionResult:
    target = overrides.pop("target", _target())
    defaults: dict[str, object] = {
        "target": target,
        "candidates": (),
        "contract_version": VERSION,
        "interpretation_version": VERSION,
        "text": "  hello   world  ",
        "requirement": _normalization_requirement(),
        "declarations": (text_normalization_declaration(),),
    }
    defaults.update(overrides)
    return compose_direct(**defaults)  # type: ignore[arg-type]


class TestSuccessfulComposition:
    def test_unique_match_composes(self) -> None:
        result = _compose()
        assert result.status is CompositionStatus.COMPOSED
        assert result.normalized_text == "hello world"
        assert result.compatibility.status.value == "unique_match"

    def test_configuration_is_present_and_matches_target(self) -> None:
        target = _target()
        result = _compose(target=target)
        assert result.configuration.target == target


class TestRepeatability:
    def test_identical_inputs_produce_identical_output(self) -> None:
        first = _compose()
        second = _compose()
        assert first.normalized_text == second.normalized_text
        assert first.status == second.status
        assert first.configuration == second.configuration

    def test_repeated_composition_many_times(self) -> None:
        outputs = {_compose().normalized_text for _ in range(20)}
        assert outputs == {"hello world"}


class TestConfigurationImmutability:
    def test_captured_candidates_not_mutated(self) -> None:
        candidate = CapturedCandidate(
            target=_target(),
            provenance=SourceProvenance("owner", "source", "rev1", VERSION, VERSION),
            layer=SourceLayer.BASE,
            values=NormalizationPatch(None, NormalizationMode.TRIM, None),
        )
        candidates = (candidate,)
        _compose(candidates=candidates)
        # The exact same tuple/candidate objects remain unchanged -- a pure
        # composition function does not mutate caller-owned input.
        assert candidates == (candidate,)
        assert candidates[0].layer is SourceLayer.BASE


class TestNoMatch:
    def test_incompatible_requirement_yields_no_compatible_declaration(self) -> None:
        unrelated = CapabilityRequirement(
            CapabilityId("unrelated.capability"),
            CapabilityVersionRange(Version(1, 0, 0)),
        )
        result = _compose(requirement=unrelated)
        assert result.status is CompositionStatus.NO_COMPATIBLE_DECLARATION
        assert result.normalized_text is None

    def test_no_match_never_calls_deterministic_function(self) -> None:
        calls: list[str] = []

        def spy(text: str, effective: object) -> str:
            calls.append(text)
            return "SHOULD-NEVER-RUN"

        unrelated = CapabilityRequirement(
            CapabilityId("unrelated.capability"),
            CapabilityVersionRange(Version(1, 0, 0)),
        )
        result = _compose(requirement=unrelated, normalization_function=spy)
        assert result.status is CompositionStatus.NO_COMPATIBLE_DECLARATION
        assert calls == []


class TestAmbiguity:
    def test_two_compatible_declarations_yield_ambiguous(self) -> None:
        duplicate = PluginDeclaration(
            PluginId("other.org", "dup-normalizer"),
            text_normalization_release(),
            (
                CapabilityOffer(
                    text_normalization_capability_id(), text_normalization_release()
                ),
            ),
        )
        result = _compose(declarations=(text_normalization_declaration(), duplicate))
        assert result.status is CompositionStatus.AMBIGUOUS_DECLARATION
        assert result.normalized_text is None

    def test_ambiguous_never_calls_deterministic_function(self) -> None:
        calls: list[str] = []

        def spy(text: str, effective: object) -> str:
            calls.append(text)
            return "SHOULD-NEVER-RUN"

        duplicate = PluginDeclaration(
            PluginId("other.org", "dup-normalizer"),
            text_normalization_release(),
            (
                CapabilityOffer(
                    text_normalization_capability_id(), text_normalization_release()
                ),
            ),
        )
        result = _compose(
            declarations=(text_normalization_declaration(), duplicate),
            normalization_function=spy,
        )
        assert result.status is CompositionStatus.AMBIGUOUS_DECLARATION
        assert calls == []

    def test_ambiguous_does_not_arbitrarily_pick_first_or_latest(self) -> None:
        # Order of declarations must not affect the outcome.
        duplicate = PluginDeclaration(
            PluginId("aaa.org", "dup-normalizer"),
            text_normalization_release(),
            (
                CapabilityOffer(
                    text_normalization_capability_id(), text_normalization_release()
                ),
            ),
        )
        forward = _compose(declarations=(text_normalization_declaration(), duplicate))
        backward = _compose(declarations=(duplicate, text_normalization_declaration()))
        assert (
            forward.status is backward.status is CompositionStatus.AMBIGUOUS_DECLARATION
        )


class TestFixtureMismatch:
    def test_unique_match_against_unknown_declaration_is_mismatch(self) -> None:
        unrelated_capability = CapabilityId("unrelated.capability")
        unrelated_declaration = PluginDeclaration(
            PluginId("other.org", "other-plugin"),
            Version(1, 0, 0),
            (CapabilityOffer(unrelated_capability, Version(1, 0, 0)),),
        )
        requirement = CapabilityRequirement(
            unrelated_capability, CapabilityVersionRange(Version(1, 0, 0))
        )
        result = _compose(
            declarations=(unrelated_declaration,), requirement=requirement
        )
        assert result.status is CompositionStatus.FIXTURE_MISMATCH
        assert result.normalized_text is None

    def test_fixture_mismatch_never_calls_deterministic_function(self) -> None:
        calls: list[str] = []

        def spy(text: str, effective: object) -> str:
            calls.append(text)
            return "SHOULD-NEVER-RUN"

        unrelated_capability = CapabilityId("unrelated.capability")
        unrelated_declaration = PluginDeclaration(
            PluginId("other.org", "other-plugin"),
            Version(1, 0, 0),
            (CapabilityOffer(unrelated_capability, Version(1, 0, 0)),),
        )
        requirement = CapabilityRequirement(
            unrelated_capability, CapabilityVersionRange(Version(1, 0, 0))
        )
        result = _compose(
            declarations=(unrelated_declaration,),
            requirement=requirement,
            normalization_function=spy,
        )
        assert result.status is CompositionStatus.FIXTURE_MISMATCH
        assert calls == []


class TestSubstitutability:
    def test_alternative_pure_function_is_used_when_supplied(self) -> None:
        def shout(text: str, effective: object) -> str:
            return text.strip().upper()

        result = _compose(normalization_function=shout)
        assert result.status is CompositionStatus.COMPOSED
        assert result.normalized_text == "HELLO   WORLD"

    def test_default_function_used_when_none_supplied(self) -> None:
        result = _compose()
        assert result.normalized_text == "hello world"


class TestSafeObservation:
    def test_capturing_sink_records_expected_bounded_events(self) -> None:
        sink = CapturingObservationSink()
        result = _compose(sink=sink)
        assert result.status is CompositionStatus.COMPOSED
        assert len(sink.observations) == 2
        assert sink.observations[0].event_code.value == "composition.started"
        assert sink.observations[1].event_code.value == "composition.composed"

    def test_no_sink_supplied_still_composes(self) -> None:
        result = _compose()
        assert result.status is CompositionStatus.COMPOSED

    def test_tenant_id_threaded_into_observations_only(self) -> None:
        sink = CapturingObservationSink()
        tenant_id = TenantId("t1")
        _compose(sink=sink, tenant_id=tenant_id)
        assert all(obs.tenant_id == tenant_id for obs in sink.observations)


class TestFailingSinkContainment:
    def test_failing_sink_does_not_change_semantic_result(self) -> None:
        capturing_result = _compose(sink=CapturingObservationSink())
        failing_result = _compose(sink=FailingObservationSink())
        assert capturing_result == failing_result

    def test_failing_sink_does_not_raise_out_of_compose_direct(self) -> None:
        result = _compose(sink=FailingObservationSink())
        assert result.status is CompositionStatus.COMPOSED
        assert result.normalized_text == "hello world"

    def test_failing_sink_on_no_match_path_still_reports_no_match(self) -> None:
        unrelated = CapabilityRequirement(
            CapabilityId("unrelated.capability"),
            CapabilityVersionRange(Version(1, 0, 0)),
        )
        result = _compose(requirement=unrelated, sink=FailingObservationSink())
        assert result.status is CompositionStatus.NO_COMPATIBLE_DECLARATION


class TestNoExecutableDeclarationBinding:
    def test_declaration_not_mutated_or_extended_by_composition(self) -> None:
        declaration = text_normalization_declaration()
        original = text_normalization_declaration()
        _compose(declarations=(declaration,))
        assert declaration == original
        for forbidden in ("callable", "implementation", "factory", "provider_instance"):
            assert not hasattr(declaration, forbidden)

    def test_offer_not_mutated_or_extended_by_composition(self) -> None:
        declaration = text_normalization_declaration()
        offer = declaration.offers[0]
        for forbidden in ("callable", "implementation", "factory"):
            assert not hasattr(offer, forbidden)

    def test_no_binding_type_exists_in_composition_module(self) -> None:
        import legoai.runtime._composition.direct as module

        assert not hasattr(module, "Binding")
        assert not hasattr(module, "Resolver")
        assert not hasattr(module, "CapabilityResolver")


class TestCompositionResultValidation:
    def test_wrong_type_status_rejected(self) -> None:
        result = _compose()
        with pytest.raises(TypeError):
            CompositionResult(
                "composed",  # type: ignore[arg-type]
                result.configuration,
                result.compatibility,
                "x",
            )

    def test_wrong_type_configuration_rejected(self) -> None:
        result = _compose()
        with pytest.raises(TypeError):
            CompositionResult(
                result.status,
                "not-a-configuration",  # type: ignore[arg-type]
                result.compatibility,
                result.normalized_text,
            )

    def test_wrong_type_compatibility_rejected(self) -> None:
        result = _compose()
        with pytest.raises(TypeError):
            CompositionResult(
                result.status,
                result.configuration,
                "not-a-compatibility-analysis",  # type: ignore[arg-type]
                result.normalized_text,
            )

    def test_composed_result_rejects_wrong_type_normalized_text(self) -> None:
        result = _compose()
        with pytest.raises(ValueError):
            CompositionResult(
                result.status,
                result.configuration,
                result.compatibility,
                123,  # type: ignore[arg-type]
            )

    def test_no_match_result_cannot_carry_normalized_text(self) -> None:
        unrelated = CapabilityRequirement(
            CapabilityId("unrelated.capability"),
            CapabilityVersionRange(Version(1, 0, 0)),
        )
        no_match = _compose(requirement=unrelated)
        with pytest.raises(ValueError):
            CompositionResult(
                no_match.status,
                no_match.configuration,
                no_match.compatibility,
                "should-not-be-allowed",
            )


class TestNoGate2Symbols:
    def test_no_forbidden_symbols_defined_in_f8b_modules(self) -> None:
        forbidden_names = {
            "Execution",
            "ExecutionContext",
            "ExecutionId",
            "ExecutionState",
            "ExecutionResult",
            "CapabilityResolver",
            "PluginAdmission",
        }
        import legoai.reference.deterministic as deterministic_module
        import legoai.runtime._composition.direct as composition_module

        for module in (deterministic_module, composition_module):
            defined = {name for name in dir(module) if not name.startswith("_")}
            assert not (defined & forbidden_names)

    def test_no_forbidden_calls_in_composition_source(self) -> None:
        import legoai.runtime._composition.direct as module

        assert module.__file__ is not None
        tree = ast.parse(Path(module.__file__).read_text(encoding="utf-8"))
        forbidden_calls = {"activate", "dispatch", "authorize", "admit_plugin"}
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                assert node.func.id not in forbidden_calls
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                assert node.func.attr not in forbidden_calls
