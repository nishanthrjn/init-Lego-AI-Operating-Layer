"""Text and choice normalization, and missing-value handling for every rule."""

from decimal import Decimal

import pytest

from legoai_collation import (
    ASCII_WHITESPACE,
    ChoiceRule,
    ChoiceVocabulary,
    DecimalRule,
    ObservationState,
    RawInput,
    TextMode,
    TextRule,
    ValueKind,
    normalize,
    normalize_choice,
    normalize_text,
)

TRIM = TextRule(TextMode.TRIM, ASCII_WHITESPACE)
COLLAPSE = TextRule(TextMode.COLLAPSE, ASCII_WHITESPACE)
LEVELS = ChoiceVocabulary("level/1", frozenset({"low", "high"}))
CHOICE = ChoiceRule(
    LEVELS,
    COLLAPSE,
    (
        (RawInput.of("Lo"), "low"),
        (RawInput.of("very high"), "high"),
        (RawInput.of(1), "high"),
        (RawInput.of(False), "low"),
    ),
)
RULES = [
    pytest.param(TRIM, ValueKind.TEXT, id="text"),
    pytest.param(DecimalRule(), ValueKind.DECIMAL, id="decimal"),
    pytest.param(CHOICE, ValueKind.CHOICE, id="choice"),
]


@pytest.mark.parametrize(("rule", "kind"), RULES)
def test_absent_and_null_precede_type_validation(
    rule: TextRule | DecimalRule | ChoiceRule, kind: ValueKind
) -> None:
    absent = normalize(RawInput.absent(), rule)
    null = normalize(RawInput.null(), rule)
    assert (absent.state, absent.kind, absent.value) == (
        ObservationState.ABSENT,
        kind,
        None,
    )
    assert (null.state, null.kind, null.value) == (ObservationState.NULL, kind, None)


@pytest.mark.parametrize(("rule", "kind"), RULES)
def test_empty_text_is_blank_for_every_rule(
    rule: TextRule | DecimalRule | ChoiceRule, kind: ValueKind
) -> None:
    result = normalize(RawInput.of(""), rule)
    assert (result.state, result.kind) == (ObservationState.BLANK, kind)


def test_trim_and_collapse() -> None:
    raw = RawInput.of("\t a  \n b ")
    assert normalize_text(raw, TRIM).value == "a  \n b"
    assert normalize_text(raw, COLLAPSE).value == "a b"
    assert (
        normalize_text(RawInput.of(" \n\t"), COLLAPSE).state is ObservationState.BLANK
    )


def test_unlisted_characters_are_never_altered() -> None:
    no_break = "\u00a0x\u00a0"
    assert normalize_text(RawInput.of(no_break), COLLAPSE).value == no_break
    assert normalize_text(RawInput.of("Ab"), TRIM).value == "Ab"
    empty_set = TextRule(TextMode.COLLAPSE, frozenset())
    assert normalize_text(RawInput.of("  a  "), empty_set).value == "  a  "


@pytest.mark.parametrize(
    "raw", [RawInput.of(5), RawInput.of(True), RawInput.of(Decimal("5"))]
)
def test_text_rule_does_not_convert_other_kinds(raw: RawInput) -> None:
    assert normalize_text(raw, TRIM).state is ObservationState.INVALID


def test_choice_uses_declared_aliases_after_text_rule() -> None:
    assert normalize_choice(RawInput.of("  very   high "), CHOICE).value == "high"
    assert normalize_choice(RawInput.of("Lo"), CHOICE).value == "low"
    assert normalize_choice(RawInput.of("lo"), CHOICE).state is ObservationState.INVALID
    # A token spelling is not an implicit alias.
    assert (
        normalize_choice(RawInput.of("low"), CHOICE).state is ObservationState.INVALID
    )
    assert normalize_choice(RawInput.of(" \t"), CHOICE).state is ObservationState.BLANK


def test_choice_keys_match_only_the_same_raw_kind() -> None:
    assert normalize_choice(RawInput.of(1), CHOICE).value == "high"
    assert normalize_choice(RawInput.of(True), CHOICE).state is ObservationState.INVALID
    assert normalize_choice(RawInput.of("1"), CHOICE).state is ObservationState.INVALID
    assert normalize_choice(RawInput.of(False), CHOICE).value == "low"
    assert normalize_choice(RawInput.of(0), CHOICE).state is ObservationState.INVALID
    assert (
        normalize_choice(RawInput.of(Decimal("1")), CHOICE).state
        is ObservationState.INVALID
    )


def test_normalizers_reject_wrong_argument_types() -> None:
    with pytest.raises(TypeError):
        normalize_text("x", TRIM)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        normalize_text(RawInput.of("x"), COLLAPSE.mode)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        normalize(RawInput.of("x"), object())  # type: ignore[arg-type]
