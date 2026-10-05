# ANALYST-INSUFFICIENT-DIAG-1: content-free diagnosis of `insufficient_inconsistent`

## Pre-run declaration

### Starting point (CONTENT-DISCOVERY-1Q-R2, immutable)

| Item | Value |
| --- | --- |
| Condition commit | `2e8f1ab8f401c01ec13c75b01041882ff6eea0a2` |
| RepositoryAnalyst | 1.0.1, fingerprint `f99564e6a483eb91f8d9221f0206ea358251c74295608115c1253103125c2cc0` |
| Model | `qwen2.5-coder:7b` `sha256:dae161e27b0e90dd1856c8bb3209201fd6736d8eb66298e75ed87571486f4364` |
| `report.json` SHA-256 | `e5a0efd31ff391ccafcc70d6f57bdca6ca8f69c994c28f3e99ab2671c199e49c` |
| `condition.json` SHA-256 | `5b716ad7509992e4835932fab225423dfdca7590c2e01da8939f059097856c43` |
| Condition digest | `5cd301942dd91cf6186f768ef6b86ad42a0bc8e131b41c855317a53eba4cfec3` |
| Decision | B (held-out validity 59/72 = 81.9% < 90%) |

The coarse blocker: 13 of the 14 invalid calls failed at
`insufficient_inconsistent`; the 14th was `response_not_json`. The unchanged
Analyst rule is that `status = insufficient_evidence` requires a non-empty
`unknowns` and an empty `findings`.

### Why the recorded r2 records are not sufficient

The r2 records hold the first-failure stage, field types and status value,
but not the `findings` or `unknowns` counts. The raw replies were never
retained. So the clause that failed cannot be recovered from the recorded
evidence, and it is not guessed.

**What the recorded records can show, folded mechanically in `recorded` mode:**
- actual status against the expected outcome;
- structurally valid versus invalid abstention.

**What they cannot show:** the clause split. That needs a fresh
same-condition live diagnostic. It is prepared here and is run only by the
operator, after local qualification and approval.

### Refined taxonomy (only `insufficient_inconsistent` is refined)

The diagnosis mirrors the frozen parser order:
1. ADR-021 decode;
2. JSON parse and duplicate keys;
3. exact field set;
4. status;
5. findings shape;
6. summary, relevant_files, risks and unknowns shape;
7. constructor bounds;
8. **then** the insufficient-evidence rule;
9. then membership.

A reply is refined only when the DIAG-1 first failure is
`insufficient_inconsistent`. Earlier stages, including `response_not_json`,
keep their DIAG-1 stage. The refined categories:

| Refined category | `findings_count` | `unknowns_count` |
| --- | --- | --- |
| `insufficient_findings_present` | > 0 | > 0 |
| `insufficient_unknowns_empty` | 0 | 0 |
| `insufficient_findings_present_and_unknowns_empty` | > 0 | 0 |

A reply with status `insufficient_evidence`, `findings_count` 0 and
`unknowns_count` > 0 passes the rule, so the stage is never
`insufficient_inconsistent`. A refined category that disagrees with the stage
is counted as an integrity failure.

### Abstention classes (closed)

- `valid_abstention`: stage `valid`, status `insufficient_evidence`.
- `invalid_abstention`: stage `insufficient_inconsistent`.
- `valid_success`: stage `valid`, status `succeeded`.
- `other_invalid`: every other stage, including unparsed replies, which have
  no status.

Each class is cross-tabulated against the expected outcome from the frozen 1Q
oracle (`succeeded` or `insufficient_evidence`). The oracle is evaluation-side
only and never enters a model-visible input. The status confusion matrix is
expected outcome × actual status, where the actual status is `succeeded`,
`insufficient_evidence` or `unparsed`.

### Privacy

**Records hold only:**
- case ID, partition, class and repetition;
- runtime status, first-failure stage and representation;
- actual status (a closed value) and expected outcome;
- `findings_count` and `unknowns_count` (insufficient-evidence replies only);
- the refined category, abstention class, consistency flags and timing.

**Records never hold:** finding, unknown, risk or summary text; questions,
prompts, source contents, raw replies, unexpected key names, predicted paths,
absolute paths or secrets.

### Next-decision rule (applied mechanically to the held-out partition of a live diagnostic run)

The terms:
- **P**: parsed held-out replies on cases whose expected outcome is `succeeded`.
- **VA**: valid abstentions within P.
- **I**: held-out invalid calls (every stage except `valid` and model failure).
- **IA**: invalid abstentions within I.

The rule:
1. Any classifier disagreement, any stage/category or refinement
   inconsistency, or model failures above 10% of held-out calls →
   **D. MIXED BLOCKER — FURTHER EVIDENCE REQUIRED**.
2. Otherwise, VA / P ≥ 0.5 → **B. ANALYST ABSTENTION BEHAVIOR REQUIRES QUALITY
   DECISION**. Structurally valid abstention dominates answerable cases, so
   fixing the contract alone would not yield answers.
3. Otherwise, IA / I ≥ 0.5 and one refined category covers ≥ 80% of IA →
   **A. ANALYST INSUFFICIENT-EVIDENCE PROMPT CLARIFICATION JUSTIFIED**.
4. Otherwise → **D. MIXED BLOCKER — FURTHER EVIDENCE REQUIRED**.

**C. ANALYST CONTRACT SEMANTICS REQUIRE REVIEW** is never selected
mechanically. Content-free counts cannot show that the rule conflicts with its
intended semantics, so C can only follow a separate maintainer review.

**Modes:**
- Recorded and replay modes report the rule's inputs as a preview, never as
  a decision.
- No fix is implemented in this slice.
- No threshold, oracle, parser, prompt or r2 decision changes.

<!-- END INSUFFICIENT-DIAG-1 PREDECLARATION -->

## Harness

`examples/forgeai/evaluation/analyst_insufficient_diag1/`:
- `clauses.py`: the refinement and abstention classes, plus the count
  extraction. It is applied only after DIAG-1 reaches the insufficient rule.
- `runner.py`: one governed call on the unchanged 1Q/r2 request path. It
  produces the 1Q category, the DIAG-1 stage and the refinement from the same
  in-memory result, then drops the reply.
- `report.py`: schemas `forgeai-analyst-insufficient-diagnostic-condition/1`
  and `forgeai-analyst-insufficient-diagnostic-report/1`. It folds from the
  records and links to the r2 identity.
- `cli.py` and `evaluation/run_analyst_insufficient_diag_1.py`, with three
  modes:
  - `recorded`: reads the local r2 `report.json` only if its SHA-256 equals the
    pinned digest;
  - `replay`;
  - `live`: the r2 preflight, with the exact Analyst 1.0.1 identity, the
    preregistered model and digest, a clean checkout and a new output
    directory.

## Operator commands (not run in this slice)

From `examples/forgeai`. The recorded fold makes no model call:

```powershell
uv run python evaluation/run_analyst_insufficient_diag_1.py recorded `
  --r2-report aq1q-r2-qwen2.5-coder-7b/report.json --output aid1-recorded
```

The same-condition live diagnostic (91 calls) runs only after the validator
passes, this slice is committed, the tree is clean and the run is approved:

```powershell
uv run python evaluation/run_analyst_insufficient_diag_1.py live `
  --model qwen2.5-coder:7b `
  --model-digest sha256:dae161e27b0e90dd1856c8bb3209201fd6736d8eb66298e75ed87571486f4364 `
  --hardware "<actual hardware description>" `
  --expect-branch (git branch --show-current) `
  --expect-commit (git rev-parse HEAD) `
  --output aid1-qwen2.5-coder-7b
```

No diagnostic result exists yet.

## Local qualification

All 27 phases of `validate_forgeai_analyst_insufficient_diag_1.py` passed on
2026-10-05 (29 including sub-phases), with no live model or Docker. That
includes regressions for:
- Analyst (90 tests) and authorized evidence (25);
- DISCOVERY-1 (185);
- DISCOVERY-2A/2A.1, CONTENT-DISCOVERY-1, 1Q and DIAG-1 (310);
- ForgeAI architecture (41), ENG-ANALYST-PROMPT-1 (27) and 1Q-R2 (33).

The recorded-mode fold was not run: the local r2 output directory no longer
holds the SHA-256-pinned `report.json`.

## Results (live, 2026-10-05)

**Condition:**
- commit `fa4aa8f691ac1e92212f1616e836372d002b9631`, clean tracked tree;
- RepositoryAnalyst 1.0.1, fingerprint `f99564e6…2cc0`, parser identity
  `016fcc40…2672`;
- `qwen2.5-coder:7b` `sha256:dae161e2…f4364`, Ollama 0.35.1, 600 s timeout,
  provider-default sampling, no retry or fallback;
- all 91 planned calls completed.

The report was not committed. Its digests:
- `report.json`: SHA-256 `09c096a760003bc31b6626c063315a3c15359691e76b055630a359b34faa9022`;
- `report.md`: `a5c55a3b133ed2a9a076ff8cc4324ccfa9b36d0b27e5c95e042afbb9deb5342c`;
- `condition.json`: `f6e94c11f611c362770fa60bceb15d83e982721e88b3dcb87c76312167df9f78`;
- condition digest: `6cd0b37569f1277e9c33544e25bc5b0252eaa741d273a33f4b8e74259719762c`.

Re-building from the 91 records reproduces the aggregates, decision, condition
digest and linkage exactly, and `report.md` re-renders identically.

**Recording defect (repeated):** `hardware_class` holds the literal placeholder
`<actual hardware description>`. The condition stays as written.

**Integrity:** classifier disagreements 0, stage/category inconsistencies 0,
refinement inconsistencies 0 and model failures 0. Every reply parsed; there
were no earlier-stage failures and no non-JSON replies in this sample.

### Clause split (the primary question)

| Refined category | All calls | Held-out |
| --- | --- | --- |
| `insufficient_findings_present` | 12 | 12 |
| `insufficient_unknowns_empty` | 0 | 0 |
| `insufficient_findings_present_and_unknowns_empty` | 0 | 0 |

- **Every invalid abstention (12/12) failed one clause only:** findings were
  present (1 or 2 each) while the status was `insufficient_evidence`.
- `unknowns` was never empty. All 64 insufficient-evidence replies had 1–2
  unknowns.
- All 12 invalid abstentions are on cases expected to `succeed`, spread across
  8 of the 20 answerable held-out cases. `q16` failed in all 3 repetitions.
  None of the supporting or probe calls failed.

### Status against expected outcome

| Partition | Expected | → succeeded | → insufficient_evidence |
| --- | --- | --- | --- |
| held-out | succeeded (60) | 17 | 43 (31 valid, 12 invalid) |
| held-out | insufficient (12) | 2 | 10 |
| supporting | succeeded (12) | 8 | 4 |
| supporting | insufficient (2) | 0 | 2 |
| probes | succeeded (2) | 0 | 2 |
| probes | insufficient (3) | 0 | 3 |

**Abstention classes, all calls:**
- valid abstention 52 (37 on expected-succeeded cases, 15 on expected-insufficient);
- invalid abstention 12 (all expected-succeeded);
- valid success 27 (25 expected-succeeded, 2 expected-insufficient);
- other invalid 0.

### Decision (mechanical, predeclared rule)

**Inputs (held-out):**
- valid abstentions / parsed answerable replies = 31/60 (51.7%);
- invalid abstentions / invalid calls = 12/12;
- dominant refined category `insufficient_findings_present`, 12/12;
- model failures 0/72;
- integrity failures 0.

**B. ANALYST ABSTENTION BEHAVIOR REQUIRES QUALITY DECISION.**

**Interpretation, without changing the rule:**
- **The contract failure is narrow and uniform.** On answerable cases the
  model sometimes reports supporting findings and still chooses
  `insufficient_evidence`. Its `unknowns` are always present. The
  preconditions for A (one clause covering ≥ 80% of invalid abstentions, and
  invalid abstention ≥ 50% of invalid calls) also hold, but the predeclared
  order evaluates B first.
- **Abstention dominates even among valid replies.** On answerable held-out
  cases the model abstains in 43 of 60 calls (71.7%), 31 of them validly.
  Clarifying the `insufficient_evidence` clause alone would at best turn invalid
  abstentions into valid abstentions or answers. It would not by itself
  produce answers on most answerable cases.
- **B sits near the threshold.** 51.7% against the predeclared 50%: one fewer
  valid abstention would have given 30/60, which still meets ≥ 50%. The rule is
  applied as declared.
- **No r2 decision is re-computed.** This sample's held-out validity (60/72) is
  descriptive only; r2 remains decision B. No relevance-quality conclusion is
  drawn.

### Next decision (maintainer; not implemented)

B means the next question is the model's abstention behavior, not JSON or schema
formatting. It is a quality decision, and each candidate needs its own approved,
separately measured condition:
- explicit guidance on when the supplied evidence is sufficient to answer;
- the separable `insufficient_evidence` ⇒ `findings = []` clarification. It is
  evidenced here as the sole validity failure, but it is not a fix for
  abstention;
- a different model or provider condition.

**Unchanged:** no threshold, oracle, parser, rule or model changes. Lowering
the validity gate, allowing findings under `insufficient_evidence`, making
`unknowns` optional, retries and repair all stay out of scope. ForgeAI
integration and CONTENT-DISCOVERY-2 remain deferred. G07 remains open.
