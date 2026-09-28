# Collation F1 — Source-Linked Readings and Precedence Collation

Status: IMPLEMENTED — LOCAL VALIDATION PENDING (see "Validation record").

Authority: [ADR-016](../adrs/ADR-016.md) additive pack strategy, following the
`legoai-engineering` M1 precedent: a pure pack with no runtime or Core
dependency and a small example consumer. No Core, canonical document or ADR is
changed. The contract is in the [pack README](../packages/legoai-collation/README.md).

## Scope

Implemented: source-linked reading and result values; pure text, decimal and
choice normalization; pure single-field precedence collation; synthetic tests;
one example.

Deferred: configuration or schema parsing, JSON codecs, file readers and
adapters, subject/entity resolution, conversion graphs, predicate evaluation,
assertion-set identifiers, and document-pack integration.

## Destination

- **Not Core.** `legoai.information.knowledge` (ADR-002 §7.3) is reserved for
  stored, curated Knowledge; this slice stores nothing.
- **Not an existing pack.** The behaviour is not document-, engineering- or
  media-specific.
- **Name.** `legoai-collation` avoids collisions with existing LegoAI terms:
  effect reconciliation, capability resolution, Observation (telemetry),
  Evidence (custody), resource claims and Knowledge.

## Contract decisions

1. **Decimal safety.**
   - *Raw input limits*, enforced at `RawInput` construction:
     - text of at most 4096 characters;
     - integers under 600 digits, which keeps `str(int)` below CPython's
       smallest configurable conversion limit (640);
     - `Decimal` coefficients of at most 4096 digits.
   - *Canonicalization* works only on the `(sign, digits, exponent)` tuple with
     Python integers:
     1. strip leading and trailing zeros;
     2. check the canonical bounds, 64 integer digits and 64 fraction digits;
     3. only then expand a positive exponent, by at most 64 digits.
   - A huge exponent is therefore rejected without being materialized.
   - Bound comparisons use exact scaled integers, and no `Decimal` arithmetic
     runs anywhere. Results do not depend on the ambient precision, rounding
     or traps.
   - The canonical fixed-point text is at most 130 characters.
2. **Examples use text or `Decimal("4.2")`.** Floats are rejected at
   `RawInput.of`.
3. **Source-specific rules.** Each reading keeps its own rule. Rules are
   compatible when they produce the same `ValueKind`, and for choices the same
   named `ChoiceVocabulary`. Alias maps and decimal or text options may differ.
   A different kind or vocabulary raises `IncompatibleRulesError`.
4. **ABSENT and NULL come first** for every rule, before any type check.
   BLANK means empty after the rule's own text handling; a decimal rule has
   none, so only `""` counts as BLANK there.
5. **Observation identity.**
   - A reading's identity is `(source, locator)`.
   - A source that supplies several readings must give every one of them a
     locator.
   - Repeated identities raise `DuplicateReadingError`, even when the content
     is identical. Readings are never merged or dropped.
   - `content_digest` is not part of identity.
6. **Standalone tests.**
   - Package tests use only the pack directory (`pythonpath = ["src",
     "examples"]`), so they run from an extracted sdist.
   - The check that Core never imports the pack is repository-level, in
     `tests/architecture/test_import_boundaries.py`.
7. **Explicit disagreement.**
   - `Collation.has_disagreement` is true exactly when there is more than one
     distinct admissible value. `Collation` enforces this at construction.
   - PRECEDENCE_SELECTED retains the alternatives, both in `distinct_values`
     and in a `DISAGREEING_ALTERNATIVE` reason.
8. **`content_digest` is caller metadata**, never computed or verified.

**Routine choices**
- NULL stays distinct from BLANK.
- Unranked readings are retained with `UNRANKED_SOURCE` admission.
- A token spelling is not an implicit alias.
- Text equality is exact code-point equality.
- Candidates are ordered by (unranked last, rank, source id, locator).
- Choice text keys are stored normalized.
- The local bounds are 1024 readings, 256 policy sources, 256 aliases,
  256 vocabulary tokens, 16 qualifiers and 64 whitespace characters. These are
  protection limits, not workload-derived capacities.

## Validation record

Pending maintainer-run validation using the commands in the pack README.
Automated review by the assistant is recorded in the change summary, not here.
