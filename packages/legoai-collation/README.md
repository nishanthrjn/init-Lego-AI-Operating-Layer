# legoai-collation

Pure collation of source-attributed readings of one field. Several sources
report a value for the same subject, field and qualifiers; each reading is
normalized by its source's rule, and a versioned precedence policy decides the
outcome while every reading, disagreement and exclusion stays visible.

No I/O, no runtime dependencies and no Core dependency. It performs no entity
resolution, authorization, file reading or integrity verification. Design
decisions are recorded in the [F1 slice record](../../planning/COLLATION-F1-SLICE.md).

## Contract

| Value | Meaning |
|---|---|
| `SourceId` | Opaque source identity, compared exactly. Naming a source does not authorize it. |
| `SourceRef(source, locator=None, content_digest=None)` | Where a reading came from. `(source, locator)` is the reading's identity. `content_digest` is caller-supplied metadata: never computed or verified here, and evidence of neither integrity nor publisher identity. |
| `ComparisonContext(subject, field, qualifiers=())` | The single thing being compared. The caller resolves the subject; qualifiers pin anything that must match, such as a unit or time. |
| `RawInput` | The value exactly as supplied: `absent()`, `null()` or `of(str \| int \| Decimal \| bool)`. Floats are rejected. Equality is representation-exact. |
| `TextRule`, `DecimalRule`, `ChoiceRule` | Normalization rules (below). Each source may use its own. |
| `Reading(ref, context, raw, rule)` | A source-linked reading. `state`, `kind` and `value` are computed from `raw` and `rule`. |
| `PrecedencePolicy(version, ranks)` | Source ranks; lower is higher precedence; equal ranks are equal precedence. Ranks order values, they never authorize. |
| `collate_field(context, readings, policy) -> Collation` | The single-field decision. |

Collections are passed as tuples (pairs for mappings) or frozensets and are
stored in canonical order; all values are frozen.

### Normalization

Every rule handles `RawInput.absent()` and `RawInput.null()` first, giving the
ABSENT or NULL state. After that:

- **Text:** text input only. TRIM or COLLAPSE over an explicit whitespace set
  (`ASCII_WHITESPACE` is provided); other characters are never altered, and
  there is no case folding or Unicode normalization. Empty after the rule is
  BLANK. Other kinds are INVALID.
- **Decimal:** text, integer and finite `Decimal` input. Text must be
  `[-]digits[.digits]` in ASCII, with no `+`, exponent, whitespace or
  separators; `""` is BLANK. Lexical options (`allow_negative_sign`,
  `allow_fraction`, `max_fraction_digits`) apply to text only; numeric options
  (`minimum`, `maximum`, `integral`) apply to every kind. Values are
  canonicalized exactly and must fit `MAX_INTEGER_DIGITS` integer and
  `MAX_FRACTION_DIGITS` fraction digits (64 each). Results do not depend on the
  ambient `decimal` context. `canonical_decimal_text` renders fixed-point text.
- **Choice:** declared aliases from text, integer or boolean keys to tokens of
  one named `ChoiceVocabulary`. Keys match only the same raw kind (`True` is not
  `1`); text is matched after the rule's `TextRule`. Blank text is BLANK;
  anything unmapped is INVALID.

### Collation

`collate_field` raises before any work for wrong types, more than
`MAX_READINGS` readings, a reading with a different context
(`MixedContextError`), incompatible rules (`IncompatibleRulesError`: a
different value kind, or choice rules with different vocabularies), or a
duplicate identity (`DuplicateReadingError`: a repeated `(source, locator)`,
or a source with several readings where one lacks a locator). Duplicates are
never merged or dropped.

Every reading becomes a `Candidate`, ordered by rank, source id and locator,
with unranked sources last. Admission: an unranked source is
`UNRANKED_SOURCE` (retained, never decisive); otherwise INVALID readings are
`INVALID`, ABSENT/NULL/BLANK are `NOT_PRESENT`, and PRESENT readings are
`ADMISSIBLE`.

| Admissible readings | Status | `selected` | `has_disagreement` |
|---|---|---|---|
| All equal | AGREED | the value | false |
| Differ; one distinct value at the best rank | PRECEDENCE_SELECTED | best-rank value | true |
| Differ at the best rank | CONFLICT | None | true |
| None, some ranked reading INVALID | INVALID | None | false |
| None otherwise, including no readings | MISSING | None | false |

`distinct_values` lists every distinct admissible value, and `reasons` gives
structured `ReasonCode`s with the `SourceRef`s they concern. AGREED means the
admissible sources agree, not that the value is verified.

```python
from decimal import Decimal
from legoai_collation import (
    ComparisonContext, DecimalRule, PrecedencePolicy, RawInput, Reading,
    SourceId, SourceRef, collate_field,
)

context = ComparisonContext("demo-station-01", "air_temperature", (("unit", "degC"),))
policy = PrecedencePolicy("demo/1", ((SourceId("feed-a"), 0), (SourceId("feed-b"), 1)))
rule = DecimalRule(allow_negative_sign=True)
readings = (
    Reading(SourceRef(SourceId("feed-a")), context, RawInput.of("4.20"), rule),
    Reading(SourceRef(SourceId("feed-b")), context, RawInput.of(Decimal("4.6")), rule),
)
result = collate_field(context, readings, policy)
assert result.status.value == "precedence_selected"
assert result.selected == Decimal("4.2") and result.has_disagreement
```

## Local validation

From the repository root (the first `uv sync` creates this pack's `uv.lock`):

```powershell
Push-Location packages/legoai-collation
uv sync
uv run pytest -q
uv run mypy src tests examples
uv run ruff check src tests examples
uv run ruff format --check src tests examples
uv run python examples/station_reading.py
Pop-Location
uv run pytest -q tests/architecture/test_import_boundaries.py -k collation
git diff --check
```

The package tests need only this directory: `pythonpath` includes `src`, so
they also run from an extracted source distribution. The repository-level
test checks that Core never imports this pack. `test_package_install.py`
builds the wheel and sdist and installs the wheel offline into a fresh
environment; it needs `uv` on `PATH`.
