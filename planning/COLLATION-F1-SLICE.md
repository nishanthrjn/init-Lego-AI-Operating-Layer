# Collation F1 — Source-Linked Readings and Precedence Collation

Status: IMPLEMENTED — PACK VALIDATION PASSED (assistant-run; see "Validation record").

Authority: [ADR-016](../adrs/ADR-016.md) additive pack strategy, following the
`legoai-engineering` M1 precedent: a pure pack with no runtime or Core
dependency and a small example consumer. No Core module, canonical document or
ADR is changed; see "ADR decision". The contract is in the
[pack README](../packages/legoai-collation/README.md).

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

## ADR decision: none required for F1

**Policy basis**
- CLAUDE.md requires an ADR for *significant* architecture decisions.
- The ADR index (§2) calls for one ADR per meaningful architectural choice.
  Implementation work under an accepted decision does not automatically need
  its own.
- [ADR-016](../adrs/ADR-016.md) already decides the mechanism F1 uses:
  reusable Python capabilities as separate distributions with distinct import
  roots, additive and optional.
- Recording an ADR-016 increment in the forward plan follows existing practice.
  `legoai-engineering` and `legoai-document` were added this way, with no
  package-specific ADR.

**Why F1 needs no new decision.** F1 changes no Core module, canonical
contract, dependency direction, security or tenancy boundary, persistence or
wire format. It adds no runtime dependency and makes no registered-capability
claim. It is reversible by deleting one package directory. This matches
ADR-016's "preparatory implementation, not a new semantic Kernel type" case,
with an example as its first consumer, as for M1.

**Record:** this file, plus the forward-plan package row. No ADR number is
allocated.

**When an ADR becomes required.** Write one, as ADR-021, the next free
number, before any of these:
- placing this behaviour in Core, including `legoai.information.knowledge`;
- subject or entity resolution;
- a public serialization or wire contract;
- admitting it as a governed capability;
- adding a runtime dependency.

ADR-016's condition "extract for a first real consumer and harden with a
second" is still open. F1 makes no supported-capability claim until a real
consumer, such as document field consensus, adopts it.

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

## Protection limits

These are local protection bounds. Their purpose is to keep every call's
memory and time bounded and every error explicit. They have **not** been
validated against any workload, and raising one is an ordinary reviewed
change.

| Limit | Value | Rationale |
|---|---|---|
| Identifier text | 1–256 chars | Same bound as Core's opaque identities (`legoai.kernel.identity`) |
| Raw text | 4096 chars | Field values, not documents; bounds text-rule and alias work per reading |
| Raw integer | < 600 digits | Keeps `str(int)` below CPython's smallest configurable conversion limit (640), so no interpreter setting can make it fail |
| Raw `Decimal` coefficient | 4096 digits | Same order as raw text; bounds the tuple scan before canonicalization |
| Canonical integer / fraction digits | 64 / 64 | Exceeds common exact-numeric widths (e.g. 38-digit SQL decimals); bounds expansion, output (≤ 130 chars) and scaled-integer comparison |
| Readings per collation | 1024 | Bounds sorting and the O(n × sources) rank lookups of one call |
| Policy sources | 256 | Rank lookup is a linear scan; a policy is a curated list |
| Aliases per choice rule | 256 | Alias lookup is a linear scan per reading |
| Vocabulary tokens | 256 | A closed, reviewable token set |
| Qualifiers | 16 | A comparison context needs few pinned dimensions |
| Whitespace characters per text rule | 64 | An explicit character set, not a Unicode category |

Limit violations raise `LimitExceededError` (or `ValueError` for identifier
length) before any collation work. Canonical-bound violations make the
reading INVALID instead, because they are data validity, not call size.

## Validation record

Assistant-run on 2026-09-28 in the pack's own `uv sync` environment. This is
not independent assurance.

**Environment and lockfile**
- `uv sync` created `.venv` and `uv.lock` (lock format v1, revision 3,
  `requires-python ==3.14.*`).
- The lock has 17 third-party packages, all from PyPI, at the same versions as
  the reviewed `legoai-engineering` lock.
- The only editable project is `legoai-collation`, and there are no runtime
  dependencies.
- `uv sync --locked` later confirmed the lock matches `pyproject.toml`.

**Pack checks**

| Command | Result |
|---|---|
| `uv run pytest -q` | 118 tests passed |
| `uv run mypy src tests examples` | No issues in 15 files |
| `uv run ruff check src tests examples` | Passed |
| `uv run ruff format --check src tests examples` | Passed |
| `uv run python examples/station_reading.py` | The five documented lines |

`uv run pytest -q` exits 1 on this machine even though every test passes.
Pytest's session teardown cannot remove a stale, unreadable `pytest-current`
reparse point in the user temp directory (`PermissionError`). With
`--basetemp` in a private directory it exits 0. This is a machine issue, not a
package defect.

**Isolation and packaging**
- Tests from an extracted sdist, with `legoai_collation` not installed: 118
  tests passed.
- The wheel and sdist inventories are exact, and `test_package_install.py`
  enforces them.
- The sdist ships the pack's own `.gitignore`: hatchling always includes the
  nearest one, which was previously the repository root's.

**Repository level**
- `tests/architecture` passed 287 and failed 1, which predates F1 (below).
- `git diff --check` is clean.

**Pre-existing failure, unrelated to F1**
- `tests/architecture/test_package_install.py::test_build_and_fresh_wheel`
  fails because the Core wheel contains
  `legoai/runtime/_composition/model_selection.py`.
- That module was added in `a451abe`, after the test's expected inventory was
  last updated.
- F1 changes no Core source and not that test.

The full root suite was not run: F1 changes no Core behaviour, and its one
root change (an added architecture test) passes.
