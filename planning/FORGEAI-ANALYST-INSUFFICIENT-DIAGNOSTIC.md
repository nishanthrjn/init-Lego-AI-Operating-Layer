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
