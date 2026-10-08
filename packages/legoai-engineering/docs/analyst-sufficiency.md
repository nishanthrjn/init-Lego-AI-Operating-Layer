# Analyst evidence sufficiency contracts

ENG-ANALYST-SUFFICIENCY-CONTRACT-1: **LOCALLY QUALIFIED**.

Import the additive public values from `legoai_engineering.analyst.sufficiency`.
There is no assessment Agent, prompt, model call, filesystem access, acquisition
loop or ForgeAI integration. RepositoryAnalyst 1.0.3, its six-field final analysis,
parser and previous M8.1 qualification remain unchanged.

## Values and ownership

`EvidenceSufficiencyAssessment` represents a separately reviewable judgment:

- `SUFFICIENT`: advisory judgment with at least one supplied governing citation,
  no outstanding requests, and no unmet declared prerequisites.
- `MISSING_GOVERNING_EVIDENCE`: at least one named/source-role evidence request.
- `UNRESOLVED_AMBIGUITY`: at least one operator clarification request.

Missing evidence and ambiguity can coexist: requests may describe both, while
the author supplies the primary disposition. Software does not infer it from
source text. Explanations describe evidence limitations, not hidden reasoning
or confidence scores. All semantic results remain untrusted judgments.

`EvidenceRequest` is inert data with three closed kinds:

| Kind | Shape and meaning |
| --- | --- |
| `NAMED_EVIDENCE` | Required `RepositoryPath`, no choices. The proposed path may be unsupplied or unauthorized; it is not a citation or permission. |
| `SOURCE_ROLE` | Description only, no path or choices. For example, the catalog governing a message. Text is never interpreted as a filename. |
| `OPERATOR_CLARIFICATION` | Description, optionally 2–8 distinct choices; no path. A free-text answer is allowed when choices are absent. Clarification is not acquisition. |

`GoverningSourceExpectation` declares a named or role requirement. A named
requirement is present only when its exact path is supplied. A source role is
unresolved until explicitly bound to supplied paths; the binding is a declared
judgment, not proof those files really govern the answer. Named requirements
cannot substitute other paths. `EvidenceClarification` records a question and
optional operator answer; closed-choice answers must match exactly.

`EvidenceManifest` binds the exact question, `RepositoryEvidence`, a bounded
provenance label, expectations, clarifications and explicit unknown prerequisites.
The label is caller-provided observation/workspace identity, not authenticated
provenance. Unknowns in this manifest mean unresolved prerequisites and block a
sufficient claim; residual risks belong in the existing final analysis instead.
No manifest claims complete knowledge merely because all declared entries exist.

## Deterministic checks and attribution

Construction checks types, bounds, duplicates, supplied citation membership,
role-binding membership and disposition/request consistency. Constructing a
`SUFFICIENT` assessment also rejects missing declared sources, unanswered
clarifications and unknown prerequisites with `PREREQUISITES_UNMET`.

`manifest.evidence_identity` hashes canonical path/content observations;
`manifest.identity()` additionally binds the exact question, provenance and all
expectation/clarification/unknown state. Both use domain-tagged canonical UTF-8
JSON and SHA-256, not Python object identity or randomized `hash()`. Declaration
order is canonicalized; file and choice spelling/content remain exact. All
values are immutable and support ordinary equality/hash semantics.

Before reusing an assessment, call `assessment.validate_for(current_manifest)`.
It returns `None` on matching attribution and applicable declared prerequisites,
or raises `EvidenceSufficiencyError` with a closed reason. A changed question,
path, file content, provenance, expectation, answer or unknown invalidates reuse
as `STALE_ASSESSMENT`, even if the new evidence looks better. The application
must build current observations; this method does not reread the filesystem.
Evidence remains read observations, not an atomic snapshot.

The checks do not prove entailment, dependency completeness, catalog authority,
the correctness of a human answer or final analysis truth. A mislabeled role
binding or an omitted prerequisite can still produce a structurally acceptable
advisory result. Such claims need operator review and future semantic evaluation.
An unrelated new file cannot resolve an explicitly unanswered clarification.
Absent future behavior alone does not mechanically force insufficiency.

## Operational failures

`EvidenceSufficiencyResult` contains exactly one assessment or `SufficiencyFailure`.
Operational reasons are `INVALID_OUTPUT`, `MODEL_FAILURE`, `ACQUISITION_DENIED`,
`EVIDENCE_UNAVAILABLE`, `AUTHORIZATION_FAILURE`, `BUDGET_EXHAUSTED`,
`STALE_ASSESSMENT` and `PREREQUISITES_UNMET`. The last denotes a contradictory
sufficient claim failing deterministic validation, not semantic insufficiency.
Malformed value construction raises safe `TypeError`/`ValueError` messages.

This additive vocabulary does not alter existing Agent, acquisition or Analyst
outcomes. Future application code must map actual operational observations
explicitly; no adapter or automatic mapping is introduced here.

## Limits and confidentiality

| Value | Bound |
| --- | --- |
| Question | 2048 Unicode characters and 2048 UTF-8 bytes, nonblank |
| Complete evidence | Existing 1–8 sorted distinct files, 8192 bytes/file, 24576 bytes total |
| Expectations, clarification entries, explicit unknowns, assessment requests, governing citations | At most 8 per collection; immutable tuples |
| Declaration identifier | 1–64 ASCII alphanumeric, hyphen or underscore; unique across declarations |
| Provenance label | 256 characters/UTF-8 bytes |
| Request/role description, clarification answer, unknown prerequisite | 1024 characters/UTF-8 bytes |
| Clarification choices | Zero or 2–8 distinct nonblank entries, 256 characters/UTF-8 bytes each |
| Assessment explanation | 2048 characters/UTF-8 bytes |

No truncation, coercion, repair or retry. Duplicate expectation identifiers and
identical named targets/source-role descriptions are rejected. Semantic synonyms
are not detected. Sensitive paths, question, text and explanation are excluded
from repr. Identity serialization is private and used only for hashing; this
slice defines no public JSON parser, dump format or persistence API. Digests are
not encryption, authority or permission to publish sensitive identifiers.
Explicit generic serialization such as `dataclasses.asdict` can expose fields;
consumers must not log it. Existing source disclosure restrictions still apply.

## Operator and next consumer boundary

Neither a request nor `SUFFICIENT` reads a file, issues a grant, chooses editable
targets, starts ForgeAI, bypasses review or certifies correctness. The application
and operator own progression. `RepositoryEvidencePort` remains the acquisition
seam, with current read/model-disclosure checks; no new authority is created.

The next separately authorized slice is FORGEAI-ANALYST-EVIDENCE-LOOP-1.
No orchestration, operator UI, new prompt/version, Workflow, Team, Planner,
discovery, held-out live suite or model configuration is implemented here.

## Operator qualification

From repository root:

```powershell
uv run python .\validate_engineering_analyst_sufficiency_contract_1.py
```

The validator has 37 phases: full scripted contract tests with named coverage
references, legacy parser/Analyst/evidence/M7/ForgeAI regressions, import and
scope guards, mypy, Ruff, diff integrity and frozen R3/R4 harness regressions.
Phases 4–24 reference phase 3's passing tests rather than repeat the suite.
It uses offline installed dependencies, no live provider and no Docker.
Operator qualification completed on 2026-10-07 using the command above: all
37/37 phases passed, including 27 contract cases and 103 frozen R3/R4 regression
cases. This establishes offline contract/regression evidence only, not live
model quality or semantic completeness. No live model or Docker was used.

## Request policy (H1, deterministic)

`legoai_engineering.analyst.request_policy` gives applications deterministic
authority over what a parsed `EvidenceSufficiencyAssessment` may *request*. It
accepts or rejects. It never rewrites, repairs, drops, replaces or retries the
assessment.

- `EvidenceRequestPolicy` is an immutable, application-provided policy:
  - **requestable roots:** explicit directories, compared component-wise.
    There are no globs and no implicit repository root; empty permits no
    named request.
  - **classifications:** `EvidenceClassification` (`ordinary`, `sensitive`,
    `operator_only`) for exact paths or directories; the most specific wins.
  - **default classification:** `None` by default, meaning unknown, never
    granted (fail closed).
  - **granted classes:** ordinary only by default.
- `evaluate(assessment, manifest, policy)` is pure: no I/O, model or global
  state. It returns a separate `RequestDecision`, with `accepted` and
  `violations` given as request index plus a closed `RequestViolationReason`:
  - `PATH_NOT_ESTABLISHED`: a named path not visible as a supplied file, a
    declared expectation, or a bounded exact occurrence in supplied evidence.
    Imports, module names, layout conventions and guesses never establish a
    path.
  - `OUTSIDE_REQUESTABLE_SCOPE`.
  - `CLASSIFICATION_NOT_GRANTED`: checked only for established, in-scope paths.
  - `PATH_AS_CLARIFICATION_CHOICE`: a clarification choice equal to a supplied
    or declared path identity. This is an exact identity check, not a string
    shape.
- Establishment is identity, not authority. An established path can still be
  refused by scope or classification.
- `RequestDecision.audit()` is bounded: decision, policy digest, request kinds,
  violation indices, reasons and classes. It contains no paths, prose or model
  output. `EvidenceRequestPolicy.digest()` is a SHA-256 over the canonical
  effective policy (`POLICY_SCHEMA`, sorted roots, classifications, default,
  granted).
- Sensitivity is never inferred from path text or words. Classification is
  application input only.

The policy does not judge sufficiency. In particular, it does not detect a
reference or import being treated as the referenced content.
