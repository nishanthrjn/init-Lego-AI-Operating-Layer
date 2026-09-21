"""F8b: pure deterministic text-normalization function tests (Gate-1 plan
SS13's exact fixture contract).
"""

from __future__ import annotations

import pytest

from legoai.application.values import EffectiveConfiguration, NormalizationMode
from legoai.capabilities.values import CapabilityId
from legoai.kernel.versions import Version
from legoai.plugins.values import PluginId
from legoai.reference.deterministic import (
    normalize_text,
    text_normalization_capability_id,
    text_normalization_declaration,
    text_normalization_offer,
    text_normalization_plugin_id,
    text_normalization_release,
)

VERSION = Version(0, 1, 0)


def _effective(
    mode: NormalizationMode,
    whitespace: tuple[str, ...] = (" ", "\t", "\n", "\r", "\v", "\f"),
    max_length: int = 4096,
) -> EffectiveConfiguration:
    return EffectiveConfiguration(VERSION, VERSION, max_length, mode, whitespace)


class TestTrimMode:
    def test_trims_edges_only(self) -> None:
        result = normalize_text("  hello   world  ", _effective(NormalizationMode.TRIM))
        assert result == "hello   world"

    def test_empty_input(self) -> None:
        assert normalize_text("", _effective(NormalizationMode.TRIM)) == ""

    def test_all_whitespace_input(self) -> None:
        assert normalize_text("   \t\n  ", _effective(NormalizationMode.TRIM)) == ""

    def test_no_leading_or_trailing_whitespace(self) -> None:
        assert normalize_text("hello", _effective(NormalizationMode.TRIM)) == "hello"


class TestCollapseMode:
    def test_collapses_internal_runs_to_one_space(self) -> None:
        result = normalize_text(
            "  hello   world  ", _effective(NormalizationMode.COLLAPSE)
        )
        assert result == "hello world"

    def test_multiple_separators_collapsed(self) -> None:
        result = normalize_text("a\t\tb\n\nc", _effective(NormalizationMode.COLLAPSE))
        assert result == "a b c"

    def test_empty_input(self) -> None:
        assert normalize_text("", _effective(NormalizationMode.COLLAPSE)) == ""


class TestNonAsciiPreservation:
    def test_non_ascii_preserved_in_trim_mode(self) -> None:
        text = "  héllo wörld  "
        result = normalize_text(text, _effective(NormalizationMode.TRIM))
        assert result == "héllo wörld"

    def test_non_ascii_preserved_in_collapse_mode(self) -> None:
        text = "  héllo   wörld  "
        result = normalize_text(text, _effective(NormalizationMode.COLLAPSE))
        assert result == "héllo wörld"


class TestEmptyWhitespaceSet:
    def test_no_whitespace_recognized_means_passthrough(self) -> None:
        text = "  spaced  \t out  "
        result = normalize_text(text, _effective(NormalizationMode.TRIM, whitespace=()))
        assert result == text


class TestLimitRejection:
    def test_oversize_input_rejected(self) -> None:
        with pytest.raises(ValueError):
            normalize_text("x" * 10, _effective(NormalizationMode.TRIM, max_length=5))

    def test_exact_limit_accepted(self) -> None:
        text = "x" * 5
        result = normalize_text(text, _effective(NormalizationMode.TRIM, max_length=5))
        assert result == text


class TestTypeValidation:
    def test_wrong_type_text_rejected(self) -> None:
        with pytest.raises(TypeError):
            normalize_text(123, _effective(NormalizationMode.TRIM))  # type: ignore[arg-type]

    def test_wrong_type_effective_rejected(self) -> None:
        with pytest.raises(TypeError):
            normalize_text("x", "not-an-effective-configuration")  # type: ignore[arg-type]


class TestDeterminism:
    def test_repeated_calls_produce_identical_output(self) -> None:
        effective = _effective(NormalizationMode.COLLAPSE)
        first = normalize_text("  a   b  c  ", effective)
        second = normalize_text("  a   b  c  ", effective)
        third = normalize_text("  a   b  c  ", effective)
        assert first == second == third

    def test_no_wall_clock_or_random_leakage(self) -> None:
        # Same input/config called many times never diverges -- there is no
        # hidden time- or randomness-derived component in the output.
        effective = _effective(NormalizationMode.TRIM)
        outputs = {normalize_text("  fixed input  ", effective) for _ in range(50)}
        assert outputs == {"fixed input"}


class TestFixtureIdentity:
    def test_capability_id_is_fixed_and_stable(self) -> None:
        assert text_normalization_capability_id() == CapabilityId(
            "legoai.deterministic.text_normalization"
        )
        assert text_normalization_capability_id() == text_normalization_capability_id()

    def test_plugin_id_is_fixed_and_stable(self) -> None:
        assert text_normalization_plugin_id() == PluginId(
            "legoai.reference", "deterministic-text-normalizer"
        )
        assert text_normalization_plugin_id() == text_normalization_plugin_id()

    def test_release_is_fixed_and_stable(self) -> None:
        assert text_normalization_release() == Version(1, 0, 0)
        assert text_normalization_release() == text_normalization_release()

    def test_no_random_id_generated_across_calls(self) -> None:
        ids = {text_normalization_plugin_id() for _ in range(20)}
        assert len(ids) == 1

    def test_offer_matches_capability_and_release(self) -> None:
        offer = text_normalization_offer()
        assert offer.capability == text_normalization_capability_id()
        assert offer.version == text_normalization_release()

    def test_declaration_contains_exactly_the_one_offer(self) -> None:
        declaration = text_normalization_declaration()
        assert declaration.plugin_id == text_normalization_plugin_id()
        assert declaration.release == text_normalization_release()
        assert declaration.offers == (text_normalization_offer(),)
        assert declaration.requirements == ()
