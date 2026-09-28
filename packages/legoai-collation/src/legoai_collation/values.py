"""Immutable source-linked inputs, normalization rules and precedence policy.

Construction performs no I/O and keeps no caller-owned mutable object:
collections must be supplied as tuples or frozensets, and are validated and
stored in a canonical order. Built-in types are checked exactly, so ``str``
or ``Decimal`` subclasses are rejected and ``bool`` is never an integer.
"""

from __future__ import annotations

import dataclasses
from decimal import Decimal
from enum import Enum
from typing import ClassVar

from legoai_collation import _decimal
from legoai_collation.errors import LimitExceededError

MAX_IDENTIFIER_LENGTH = 256
MAX_TEXT_LENGTH = 4096
MAX_RAW_DECIMAL_DIGITS = 4096
# Below CPython's smallest configurable int/str conversion limit (640), so
# converting a retained integer never depends on interpreter settings.
MAX_RAW_INTEGER_DIGITS = 600
MAX_QUALIFIERS = 16
MAX_WHITESPACE_CHARACTERS = 64
MAX_ALIASES = 256
MAX_VOCABULARY_TOKENS = 256
MAX_POLICY_SOURCES = 256
MAX_READINGS = 1024
MAX_INTEGER_DIGITS = _decimal.MAX_INTEGER_DIGITS
MAX_FRACTION_DIGITS = _decimal.MAX_FRACTION_DIGITS

ASCII_WHITESPACE = frozenset(" \t\n\r\f\v")

_INTEGER_CEILING = 10**MAX_RAW_INTEGER_DIGITS


def _identifier(value: object, what: str) -> str:
    if type(value) is not str:
        raise TypeError(f"{what} must be text")
    if not 1 <= len(value) <= MAX_IDENTIFIER_LENGTH:
        raise ValueError(f"{what} must contain 1-{MAX_IDENTIFIER_LENGTH} characters")
    return value


def _pairs(value: object, what: str, limit: int) -> tuple[tuple[object, object], ...]:
    if type(value) is not tuple:
        raise TypeError(f"{what} must be a tuple of pairs")
    if len(value) > limit:
        raise LimitExceededError(f"{what} exceed {limit} entries")
    for pair in value:
        if type(pair) is not tuple or len(pair) != 2:
            raise TypeError(f"{what} must be a tuple of pairs")
    return value


@dataclasses.dataclass(frozen=True, slots=True)
class SourceId:
    """Opaque source identity, compared exactly with no case or Unicode folding.

    Naming a source neither authenticates nor authorizes it.
    """

    value: str = dataclasses.field(repr=False)

    def __post_init__(self) -> None:
        _identifier(self.value, "source id")


@dataclasses.dataclass(frozen=True, slots=True)
class SourceRef:
    """Where one reading came from; ``(source, locator)`` is its identity.

    ``locator`` is an opaque position or reading identifier inside the source
    (a row, page or message id). ``content_digest`` is caller-supplied
    metadata carried unchanged: this package neither computes nor verifies
    it, and it is evidence of neither file integrity nor publisher identity.
    It is not part of the reading's identity.
    """

    source: SourceId
    locator: str | None = dataclasses.field(default=None, repr=False)
    content_digest: str | None = dataclasses.field(default=None, repr=False)

    def __post_init__(self) -> None:
        if type(self.source) is not SourceId:
            raise TypeError("source reference requires SourceId")
        if self.locator is not None:
            _identifier(self.locator, "locator")
        if self.content_digest is not None:
            _identifier(self.content_digest, "content digest")


@dataclasses.dataclass(frozen=True, slots=True)
class ComparisonContext:
    """The one subject, field and qualifier set a collation compares.

    The caller has already resolved the subject; this package performs no
    entity resolution and only checks exact equality. Qualifiers pin anything
    that must match for values to be comparable, such as a unit or a time.
    They are stored sorted by key; duplicate keys are rejected.
    """

    subject: str = dataclasses.field(repr=False)
    field: str
    qualifiers: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        _identifier(self.subject, "subject")
        _identifier(self.field, "field")
        pairs = _pairs(self.qualifiers, "qualifiers", MAX_QUALIFIERS)
        checked = [
            (_identifier(key, "qualifier key"), _identifier(value, "qualifier value"))
            for key, value in pairs
        ]
        if len({key for key, _ in checked}) != len(checked):
            raise ValueError("qualifier keys must be unique")
        object.__setattr__(self, "qualifiers", tuple(sorted(checked)))


class RawKind(Enum):
    ABSENT = "absent"
    NULL = "null"
    TEXT = "text"
    INTEGER = "integer"
    DECIMAL = "decimal"
    BOOLEAN = "boolean"


type RawValue = str | int | Decimal | bool | None

_KIND_ORDER = {kind: index for index, kind in enumerate(RawKind)}


@dataclasses.dataclass(frozen=True, slots=True, eq=False)
class RawInput:
    """One value exactly as the source supplied it, before normalization.

    ABSENT means the source had no such field; NULL means it supplied an
    explicit null. Equality is representation-exact: ``Decimal("4.2")`` and
    ``Decimal("4.20")`` are different raw inputs, while a NaN equals itself.
    Floats are rejected because binary floating point cannot carry an exact
    decimal representation.
    """

    kind: RawKind
    value: RawValue = dataclasses.field(default=None, repr=False)

    def __post_init__(self) -> None:
        if type(self.kind) is not RawKind:
            raise TypeError("raw input requires RawKind")
        value = self.value
        match self.kind:
            case RawKind.ABSENT | RawKind.NULL:
                if value is not None:
                    raise ValueError("absent or null raw input carries no value")
            case RawKind.TEXT:
                if type(value) is not str:
                    raise TypeError("text raw input requires str")
                if len(value) > MAX_TEXT_LENGTH:
                    raise LimitExceededError(
                        f"raw text exceeds {MAX_TEXT_LENGTH} characters"
                    )
            case RawKind.INTEGER:
                if type(value) is not int:
                    raise TypeError("integer raw input requires int")
                if not -_INTEGER_CEILING < value < _INTEGER_CEILING:
                    raise LimitExceededError(
                        f"raw integer exceeds {MAX_RAW_INTEGER_DIGITS} digits"
                    )
            case RawKind.DECIMAL:
                if type(value) is not Decimal:
                    raise TypeError("decimal raw input requires Decimal")
                if len(value.as_tuple().digits) > MAX_RAW_DECIMAL_DIGITS:
                    raise LimitExceededError(
                        f"raw decimal exceeds {MAX_RAW_DECIMAL_DIGITS} coefficient digits"
                    )
            case RawKind.BOOLEAN:
                if type(value) is not bool:
                    raise TypeError("boolean raw input requires bool")

    @classmethod
    def absent(cls) -> RawInput:
        return cls(RawKind.ABSENT)

    @classmethod
    def null(cls) -> RawInput:
        return cls(RawKind.NULL)

    @classmethod
    def of(cls, value: str | int | Decimal | bool) -> RawInput:
        if type(value) is bool:
            return cls(RawKind.BOOLEAN, value)
        if type(value) is int:
            return cls(RawKind.INTEGER, value)
        if type(value) is str:
            return cls(RawKind.TEXT, value)
        if type(value) is Decimal:
            return cls(RawKind.DECIMAL, value)
        if isinstance(value, float):
            raise TypeError(
                "float raw input is rejected: supply text or Decimal to keep "
                "the exact decimal representation"
            )
        raise TypeError("raw value must be str, int, Decimal or bool")

    def _key(self) -> tuple[RawKind, object]:
        if type(self.value) is Decimal:
            return (self.kind, self.value.as_tuple())
        return (self.kind, self.value)

    def _order_key(self) -> tuple[int, str | int]:
        value = self.value
        if type(value) is str or type(value) is int or type(value) is bool:
            return (_KIND_ORDER[self.kind], value)
        raise ValueError("only text, integer and boolean raw inputs are ordered")

    def __eq__(self, other: object) -> bool:
        if type(other) is not RawInput:
            return NotImplemented
        return self._key() == other._key()

    def __hash__(self) -> int:
        return hash(self._key())


class ObservationState(Enum):
    """What a reading supplied, independent of any collation outcome."""

    PRESENT = "present"
    ABSENT = "absent"
    NULL = "null"
    BLANK = "blank"
    INVALID = "invalid"


class ValueKind(Enum):
    """The canonical type and meaning a rule produces."""

    TEXT = "text"
    DECIMAL = "decimal"
    CHOICE = "choice"


class TextMode(Enum):
    TRIM = "trim"
    COLLAPSE = "collapse"


@dataclasses.dataclass(frozen=True, slots=True)
class TextRule:
    """Whitespace handling for text.

    TRIM removes leading and trailing characters found in ``whitespace``;
    COLLAPSE also replaces each interior run of them with one ASCII space.
    Other characters, including all non-listed Unicode, are never altered.
    There is no default whitespace set; ``ASCII_WHITESPACE`` is provided.
    """

    RULE: ClassVar[str] = "legoai.collation.text/1"

    mode: TextMode
    whitespace: frozenset[str]

    def __post_init__(self) -> None:
        if type(self.mode) is not TextMode:
            raise TypeError("text rule requires TextMode")
        if type(self.whitespace) is not frozenset:
            raise TypeError("whitespace must be a frozenset")
        if len(self.whitespace) > MAX_WHITESPACE_CHARACTERS:
            raise LimitExceededError(
                f"whitespace exceeds {MAX_WHITESPACE_CHARACTERS} characters"
            )
        for character in self.whitespace:
            if type(character) is not str or len(character) != 1:
                raise ValueError("whitespace entries must be single characters")


def apply_text_rule(text: str, rule: TextRule) -> str:
    """Apply a text rule; pure and total for any string."""
    whitespace = rule.whitespace
    start, end = 0, len(text)
    while start < end and text[start] in whitespace:
        start += 1
    while end > start and text[end - 1] in whitespace:
        end -= 1
    trimmed = text[start:end]
    if rule.mode is TextMode.TRIM:
        return trimmed
    pieces: list[str] = []
    in_run = False
    for character in trimmed:
        if character in whitespace:
            if not in_run:
                pieces.append(" ")
            in_run = True
        else:
            pieces.append(character)
            in_run = False
    return "".join(pieces)


@dataclasses.dataclass(frozen=True, slots=True)
class DecimalRule:
    """Exact decimal parsing with separate lexical and numeric restrictions.

    Lexical restrictions (``allow_negative_sign``, ``allow_fraction``,
    ``max_fraction_digits``) apply only to text input and constrain how the
    number is written. Numeric restrictions (``minimum``, ``maximum``,
    ``integral``) apply to every accepted input kind and constrain the value.
    For example ``allow_fraction=False`` rejects the text ``"2.0"``, while
    ``integral=True`` accepts it and rejects ``"2.5"``. Bounds are inclusive
    and stored canonically.
    """

    RULE: ClassVar[str] = "legoai.collation.decimal/1"

    allow_negative_sign: bool = False
    allow_fraction: bool = True
    max_fraction_digits: int | None = None
    minimum: Decimal | None = None
    maximum: Decimal | None = None
    integral: bool = False

    def __post_init__(self) -> None:
        for name in ("allow_negative_sign", "allow_fraction", "integral"):
            if type(getattr(self, name)) is not bool:
                raise TypeError(f"{name} must be bool")
        limit = self.max_fraction_digits
        if limit is not None:
            if type(limit) is not int:
                raise TypeError("max_fraction_digits must be int")
            if not 0 <= limit <= MAX_TEXT_LENGTH:
                raise ValueError(f"max_fraction_digits must be 0-{MAX_TEXT_LENGTH}")
            if not self.allow_fraction:
                raise ValueError("max_fraction_digits requires allow_fraction")
        for name in ("minimum", "maximum"):
            bound = getattr(self, name)
            if bound is None:
                continue
            if type(bound) is not Decimal:
                raise TypeError(f"{name} must be Decimal")
            canonical = _decimal.canonical_of(bound)
            if canonical is None:
                raise ValueError(f"{name} must be finite and within canonical bounds")
            object.__setattr__(self, name, canonical)
        if (
            self.minimum is not None
            and self.maximum is not None
            and _decimal.scaled(self.minimum) > _decimal.scaled(self.maximum)
        ):
            raise ValueError("minimum exceeds maximum")


@dataclasses.dataclass(frozen=True, slots=True)
class ChoiceVocabulary:
    """A named closed set of canonical tokens.

    Two choice rules produce comparable values only when they share an equal
    vocabulary; equal token spellings alone do not establish equal meaning.
    """

    name: str
    tokens: frozenset[str]

    def __post_init__(self) -> None:
        _identifier(self.name, "vocabulary name")
        if type(self.tokens) is not frozenset:
            raise TypeError("vocabulary tokens must be a frozenset")
        if not self.tokens:
            raise ValueError("vocabulary requires at least one token")
        if len(self.tokens) > MAX_VOCABULARY_TOKENS:
            raise LimitExceededError(
                f"vocabulary exceeds {MAX_VOCABULARY_TOKENS} tokens"
            )
        for token in self.tokens:
            _identifier(token, "vocabulary token")


@dataclasses.dataclass(frozen=True, slots=True)
class ChoiceRule:
    """Map source-specific raw values to tokens of one vocabulary.

    Keys may be text, integer or boolean raw inputs and match only raw input
    of the same kind, so ``True`` never matches ``1`` or ``"true"`` unless
    declared. Text keys are stored in their ``text``-normalized form and
    raw text is matched after the same normalization. Only declared aliases
    map: a raw value equal to a token spelling is not accepted implicitly.
    """

    RULE: ClassVar[str] = "legoai.collation.choice/1"

    vocabulary: ChoiceVocabulary
    text: TextRule
    aliases: tuple[tuple[RawInput, str], ...]

    def __post_init__(self) -> None:
        if type(self.vocabulary) is not ChoiceVocabulary:
            raise TypeError("choice rule requires ChoiceVocabulary")
        if type(self.text) is not TextRule:
            raise TypeError("choice rule requires TextRule")
        normalized: dict[RawInput, str] = {}
        for key, token in _pairs(self.aliases, "aliases", MAX_ALIASES):
            if type(key) is not RawInput:
                raise TypeError("alias keys must be RawInput")
            token = _identifier(token, "alias token")
            if token not in self.vocabulary.tokens:
                raise ValueError("alias token is not in the vocabulary")
            if type(key.value) is str:
                text = apply_text_rule(key.value, self.text)
                if not text:
                    raise ValueError("text alias key is blank after normalization")
                key = RawInput(RawKind.TEXT, text)
            elif key.kind not in (RawKind.INTEGER, RawKind.BOOLEAN):
                raise ValueError("alias keys must be text, integer or boolean")
            if key in normalized:
                raise ValueError("alias keys collide after normalization")
            normalized[key] = token
        ordered = tuple(
            sorted(normalized.items(), key=lambda item: item[0]._order_key())
        )
        object.__setattr__(self, "aliases", ordered)

    def token_for(self, key: RawInput) -> str | None:
        for alias, token in self.aliases:
            if alias == key:
                return token
        return None


type Rule = TextRule | DecimalRule | ChoiceRule


@dataclasses.dataclass(frozen=True, slots=True)
class Normalized:
    """A rule's result: a value exists exactly when the state is PRESENT.

    TEXT and CHOICE values are non-empty ``str``; DECIMAL values are
    canonical ``Decimal``.
    """

    state: ObservationState
    kind: ValueKind
    value: str | Decimal | None = dataclasses.field(default=None, repr=False)

    def __post_init__(self) -> None:
        if type(self.state) is not ObservationState:
            raise TypeError("normalized result requires ObservationState")
        if type(self.kind) is not ValueKind:
            raise TypeError("normalized result requires ValueKind")
        present = self.state is ObservationState.PRESENT
        if (self.value is not None) != present:
            raise ValueError("a value exists exactly when the state is present")
        if not present:
            return
        if self.kind is ValueKind.DECIMAL:
            if type(self.value) is not Decimal or not _decimal.is_canonical(self.value):
                raise ValueError("decimal value must be a canonical Decimal")
        elif type(self.value) is not str or not self.value:
            raise ValueError("text and choice values must be non-empty str")


@dataclasses.dataclass(frozen=True, slots=True)
class PrecedencePolicy:
    """Versioned source ranks; a lower rank has higher precedence.

    Equal ranks mean equal precedence. A rank only orders values from sources
    the caller has already decided to use: it never authorizes a source.
    Entries are stored sorted by source id.
    """

    version: str
    ranks: tuple[tuple[SourceId, int], ...]

    def __post_init__(self) -> None:
        _identifier(self.version, "policy version")
        checked: dict[SourceId, int] = {}
        for source, rank in _pairs(self.ranks, "ranks", MAX_POLICY_SOURCES):
            if type(source) is not SourceId:
                raise TypeError("ranked sources must be SourceId")
            if type(rank) is not int:
                raise TypeError("rank must be int")
            if rank < 0:
                raise ValueError("rank must be nonnegative")
            if source in checked:
                raise ValueError("each source may be ranked once")
            checked[source] = rank
        ordered = tuple(sorted(checked.items(), key=lambda item: item[0].value))
        object.__setattr__(self, "ranks", ordered)

    def rank_of(self, source: SourceId) -> int | None:
        for ranked, rank in self.ranks:
            if ranked == source:
                return rank
        return None


class Admission(Enum):
    """Whether a retained reading may influence the collation status."""

    ADMISSIBLE = "admissible"
    UNRANKED_SOURCE = "unranked_source"
    NOT_PRESENT = "not_present"
    INVALID = "invalid"


class CollationStatus(Enum):
    AGREED = "agreed"
    PRECEDENCE_SELECTED = "precedence_selected"
    CONFLICT = "conflict"
    INVALID = "invalid"
    MISSING = "missing"


class ReasonCode(Enum):
    """Structured reasons, reported in this declaration order."""

    AGREEMENT = "agreement"
    PRECEDENCE_OVER_DISAGREEMENT = "precedence_over_disagreement"
    EQUAL_RANK_DISAGREEMENT = "equal_rank_disagreement"
    DISAGREEING_ALTERNATIVE = "disagreeing_alternative"
    INVALID_OBSERVATION = "invalid_observation"
    NOT_PRESENT = "not_present"
    UNRANKED_SOURCE_EXCLUDED = "unranked_source_excluded"
    NO_OBSERVATIONS = "no_observations"
