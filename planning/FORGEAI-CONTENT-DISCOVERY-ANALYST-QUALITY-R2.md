# CONTENT-DISCOVERY-1Q-R2: RepositoryAnalyst 1.0.1 prompt-contract re-measurement

## Frozen pre-evaluation declaration

### Why a new condition

CONTENT-DISCOVERY-1Q measured RepositoryAnalyst 1.0.0: 0/91 replies were
structurally valid, giving decision B. ANALYST-CONTRACT-DIAG-1 found the cause:
every reply failed the field set, with `risks` and `unknowns` missing together.

ENG-ANALYST-PROMPT-1 then changed only the Analyst SYSTEM guidance, producing
1.0.1 at commit `009378bb720a9b287690d61549bb62ff419f23ed`. A changed prompt is
a different condition. The 1Q and DIAG-1 conditions stay pinned to 1.0.0 and
refuse to sample 1.0.1, so this re-measurement gets its own identity.

**Question.** Under an otherwise frozen 1Q condition, did the 1.0.1
clarification remove the structural validity blocker? Relevance quality is
interpreted only if structural validity reaches the existing gate.

### Analyst identity (pinned)

- `repository-analyst`, behavior version 1.0.1, definition fingerprint
  `f99564e6a483eb91f8d9221f0206ea358251c74295608115c1253103125c2cc0`.
- The Analyst API, values, authorized evidence and ADR-021 decoder are pinned
  by source digest at the implementation commit.
- A parser identity is pinned too: the Analyst API module with the definition
  function removed. It must equal the 1.0.0 parser at the 1Q foundation, so
  only the definition differs.
- A live run refuses if any of these differ:
  - the version, the fingerprint or a working-tree source digest;
  - the implementation commit is not an ancestor of HEAD.

### Reused frozen inputs (by digest, unchanged)

| Input | SHA-256 |
| --- | --- |
| 1Q manifest | `ecb80c9338c5912a023ca997ad960f539a3414ac04c0ee96e4bcb9ebea931e59` |
| Held-out cases (24) | `9c9245771f411dff4a10701bba712bbc75049c8c1368895ba3b538d9bcacbbaa` |
| CONTENT-DISCOVERY-1 partition (14 supporting, 6 probes, 1 probe without a call) | `8dc38732e6a95803ddda28e5da07faa477af6c8aa4f046cedfb6845c62a87f7e` |
| Thresholds | `377d82248478654450296bede25cc6b2918a63512463bab46128fef300c97155` |
| 1Q preregistration (oracle derivation, N, model) | `5c63430ecd15ab504cd9db73026226ed34bbf20cab962bc4b8bcc5cd95ce74c0` |
| CONTENT-DISCOVERY-1 manifest | `cbf5900d0633cf77cf29a83ce534054bad5db23842e8c095ff5f43b86f2e1fd6` |

**Reused unchanged:**
- the 1Q code: case loading, the relevance oracle, the call plan, the governed
  request path, scoring, folding, gates and the decision rule;
- the DIAG-1 first-failure classifier.

No case is added or removed. The oracle, the thresholds and the gating
partition (held-out only) are not changed.

### Repetitions and model condition (unchanged)

**Calls:**
- held-out: 24 cases × N = 3 = 72 calls;
- supporting: 14 × 1 = 14 calls;
- probes: 5 × 1 = 5 calls;
- total: 91 calls.

**Model:** `qwen2.5-coder:7b`, digest
`sha256:dae161e27b0e90dd1856c8bb3209201fd6736d8eb66298e75ed87571486f4364`.
- 600 s timeout.
- One binding: no fallback, no retry.
- Provider-default sampling (unobserved).
- The Ollama version is recorded at runtime.

A different model name or digest is refused before any call.

### Gates (unchanged 1Q thresholds; held-out partition, safety over all calls)

| Gate | Threshold |
| --- | --- |
| Safety counts | 0 |
| Classifier disagreements | 0 |
| Model failures | at most 10% |
| Structural validity | at least 90% |
| Precision | at least 85% |
| Required recall | at least 90% |
| Acceptable-set success | at least 80% |
| Insufficient correctness | at least 90% |
| False-sufficient | 0 |
| Catastrophic miss | 0 |

### Decision rule (the frozen 1Q rule, applied mechanically)

1. Safety, classifier-disagreement or model-failure gate fails →
   **D. EVIDENCE INSUFFICIENT**.
2. Otherwise, validity below 90% → **B. ANALYST OUTPUT CONTRACT IS THE PRIMARY
   BLOCKER** (the output contract remains the primary blocker). Relevance
   metrics are reported but are not decision evidence. The remaining blocker is
   classified with the DIAG-1 pattern rule.
3. Otherwise, every quality gate passes → **A. ANALYST QUALITY SUPPORTS BOUNDED
   CONTENT DISCOVERY**.
4. Otherwise → **C. ANALYST REASONING QUALITY IS INSUFFICIENT**.

B and C are never combined, and there is no fifth outcome. The labels are the
frozen 1Q labels. A does not authorize ForgeAI integration.

### Structural diagnostics

Every call also gets the DIAG-1 first-failure diagnosis of the same reply. That
is the same model call, never a second one. Each record keeps:
- the representation and the first-failure stage;
- expected and actual field counts;
- missing required fields in canonical order;
- the unexpected-field count (never the names);
- required-field JSON types;
- the closed status value;
- consistency with the 1Q category.

The structural aggregates and the DIAG-1 pattern rule are folded from the
records.

### Historical comparison (reference only, never recomputed)

| Condition | Analyst | Recorded fact |
| --- | --- | --- |
| 1Q (`2edc3f7`, report `f03d213f…b93d`) | 1.0.0 | valid 0/91; `schema_invalid` 91/91; decision B |
| DIAG-1 (`6f5a80f`, report `7bbc3ab0…3fa8`) | 1.0.0 | `field_set_invalid` 91/91; `risks`+`unknowns` missing together 91/91; one unexpected field 90/91 |

The first comparison is structural validity: 1.0.0 = 0/91, and 1.0.1 = r2 valid
calls / 91.

The prior blocker is a call whose first failure is `field_set_invalid` with both
`risks` and `unknowns` missing. The report states one descriptive observation,
with no causal claim:
- **CONSISTENT WITH THE PRIOR BLOCKER BEING ADDRESSED**: no call shows the prior
  blocker and at least one call is valid;
- **PRIOR BLOCKER PERSISTS**: at least half of all calls show it;
- **PRIOR BLOCKER REDUCED, NOT ELIMINATED**: otherwise.

Rejected content from 1Q is never compared, and historical reports are not
recalculated with 1.0.1 code.

### Authority, safety and privacy (unchanged from 1Q)

**Authority:**
- the exact confirmed evidence subset;
- named-file read for model analysis, plus governed Chat;
- no write or check grant, no mutation, no target creation and no ForgeAI
  worker call.

The output is advisory, and relevant files never become targets.

**Reports may hold:**
- condition identity, case and repetition IDs;
- structured synthetic relative predicted paths;
- counts, categories, rates, timings, gates and the decision.

**Reports never hold:**
- file contents, questions or prompts;
- replies, narrative, risks or unknowns text;
- unexpected key names, absolute paths or credentials.

<!-- END 1Q-R2 PREDECLARATION -->

## Frozen identity (recorded after the declaration, before any live call)

The preregistration `evaluation/analyst_quality1q_r2/preregistration-r2.json`
binds:
- this predeclaration (through the marker);
- the reused 1Q, partition, threshold and CONTENT-DISCOVERY-1 digests;
- the Analyst 1.0.1 identity and parser identity;
- the model condition;
- the historical references.

Its own digest is pinned in `analyst_quality1q_r2/data.py`. The harness refuses
to run if any of them changes. The 1Q freeze, which verifies its 1.0.0 sources
at the 1Q foundation, runs first.

## Harness

- `analyst_quality1q_r2/runner.py`: one governed call through the unchanged
  1Q request path. It applies the 1Q reconciliation and scoring and the DIAG-1
  diagnosis to the same in-memory result, then drops the reply.
- `report.py`: schemas `forgeai-analyst-quality-condition/2` and
  `forgeai-analyst-quality-report/2`. It folds the 1Q aggregates, gates and
  decision from the records, adds structural aggregates, the DIAG-1 pattern and
  the historical comparison, and renders Markdown from the written JSON.
- `cli.py` and `evaluation/run_analyst_quality_1q_r2.py`: the operator command.

## Live procedure (operator; not run in this slice)

Run it only after `validate_forgeai_content_discovery_1q_r2.py` passes, this
slice is committed, and the tracked tree is clean. From `examples/forgeai`:

```powershell
uv run python evaluation/run_analyst_quality_1q_r2.py live `
  --model qwen2.5-coder:7b `
  --model-digest sha256:dae161e27b0e90dd1856c8bb3209201fd6736d8eb66298e75ed87571486f4364 `
  --hardware "<same hardware class as 1Q>" `
  --expect-branch (git branch --show-current) `
  --expect-commit (git rev-parse HEAD) `
  --output aq1q-r2-qwen2.5-coder-7b
```

**Refusals:** the command refuses with exit 3, before any model call and
without writing, on:
- a different Analyst version, fingerprint or source;
- the implementation commit not being an ancestor of HEAD;
- a dirty tracked tree, or a branch or commit mismatch;
- a model name or digest different from the preregistration;
- Ollama being unreachable or the model being absent.

An existing output directory is refused with exit 2, and nothing is deleted.

`condition.json` is written before the first call, and `report.json` and
`report.md` after all 91 calls.

**No live result exists yet, and no quality claim is made.**

## Local qualification

All 34 phases of `validate_forgeai_content_discovery_1q_r2.py` passed on
2026-10-05 (38 including sub-phases), with no live model or Docker. That
includes regressions for:
- Analyst (90 tests) and authorized evidence (25);
- DISCOVERY-1 (185);
- DISCOVERY-2A/2A.1, CONTENT-DISCOVERY-1, 1Q and DIAG-1 (310);
- ForgeAI architecture (41) and ENG-ANALYST-PROMPT-1 (27).

## Results (live, 2026-10-05)

**Condition:**
- commit `2e8f1ab8f401c01ec13c75b01041882ff6eea0a2`, clean tracked tree;
- RepositoryAnalyst 1.0.1, fingerprint `f99564e6…2cc0`, parser identity
  `016fcc40…2672`;
- `qwen2.5-coder:7b` `sha256:dae161e2…f4364`, Ollama 0.35.1, 600 s timeout,
  provider-default sampling, no retry or fallback;
- all 91 planned calls completed.

The report was not committed. Its digests:
- `report.json`: SHA-256 `e5a0efd31ff391ccafcc70d6f57bdca6ca8f69c994c28f3e99ab2671c199e49c`;
- `report.md`: `9418b02411cd6d492ad54f3319eac25a2d4572852b466f43b0cd33d03df2ab0e`;
- `condition.json`: `5b716ad7509992e4835932fab225423dfdca7590c2e01da8939f059097856c43`;
- condition digest: `5cd301942dd91cf6186f768ef6b86ad42a0bc8e131b41c855317a53eba4cfec3`.

Re-building from the 91 records reproduces the aggregates, structural block,
gates, decision and comparison exactly, and `report.md` re-renders identically.

**Recording defect:** `hardware_class` holds the literal placeholder
`<same hardware class as 1Q>`, because the documented command was run without
substituting it. The platform is recorded as Windows 11 (AMD64). The condition
is immutable and stays as written; hardware equivalence with 1Q is asserted
by the operator, not recorded.

### Structural result (the primary question)

| Analyst | Structurally valid (all calls) | Held-out (gating) |
| --- | --- | --- |
| 1.0.0 (1Q, recorded) | 0/91 | 0/72 |
| 1.0.1 (r2) | 77/91 (84.6%) | 59/72 (81.9%) |

**The prior blocker is gone:**
- `field_set_invalid`: 0/91, compared with 91/91 in DIAG-1.
- Missing `risks`/`unknowns`: 0, and unexpected fields: 0.
- All 90 parsed objects carry the six fields with the correct JSON types.
- The pre-declared observation is **CONSISTENT WITH THE PRIOR BLOCKER BEING
  ADDRESSED**. This is not a causal proof: it is one condition, with fresh
  samples.

**The 14 invalid calls:**
- 13 are `insufficient_inconsistent`: 12 held-out and 1 CD-1 supporting
  (`c19`). Every one has status `insufficient_evidence` on a case whose
  expected answer is `succeeded`. They violate the unchanged rule that
  `insufficient_evidence` requires at least one unknown and no findings. The
  first-failure record does not say which clause failed.
- 1 is `response_not_json` (`q10` repetition 2).

The DIAG-1 pattern rule returns **F, MIXED STRUCTURAL PATTERN**. That is a
mechanical artifact: `insufficient_inconsistent` belongs to none of the
rule's parse, field-set or shape groups, even though 13 of the 14 failures are
that one stage.

**Other gates:** safety counts 0, classifier disagreements 0, model failures 0
and coarse inconsistencies 0. Representations were 46 fenced and 45 raw; ADR-021
decoding was again not a blocker.

### Decision (mechanical, frozen 1Q rule)

| Gate (held-out) | Passed |
| --- | --- |
| safety | true |
| classifier_disagreement | true |
| model_failure_rate | true |
| validity (≥ 90%) | **false** (81.9%) |

**B. ANALYST OUTPUT CONTRACT IS THE PRIMARY BLOCKER**: the output contract
remains the primary blocker, and `quality_is_decision_evidence` = false. The
blocker has moved, from field-set omission (1.0.0) to status/narrative
consistency under `insufficient_evidence` (1.0.1).

### Relevance metrics: descriptive only, NOT decision evidence

Below the validity gate, these are reported for orientation only. No
reasoning-quality conclusion (C) is drawn.

Held-out, valid calls only:
- precision 27/33;
- required recall 18/57;
- acceptable-set success 8/47;
- insufficient correctness 11/12;
- false-sufficient 1 (`q22` repetition 2);
- catastrophic 0.

The dominant valid-reply behavior is abstention:
- 34 of the 47 valid answerable held-out replies are `insufficient_evidence`.
- Across all calls, the status is `insufficient_evidence` in 67 of the 90 parsed
  objects.
- Together with the 13 inconsistent abstentions, the model abstains on most
  answerable cases while still listing relevant files.

This is an observation, not an evaluated gate.

### Next step (recommendation only; not implemented)

**A content-free diagnostic of the new blocker, before any further Analyst
change:**
- Refine `insufficient_inconsistent` into its clauses: findings present,
  unknowns empty, or both.
- Record status against the expected outcome per class.

This should reuse the r2 condition identity and request path, with no prompt,
parser or threshold change. Whether a later Analyst revision should address the
`insufficient_evidence` consistency or the abstention tendency is a separate
decision, made on that evidence. Quality remains unmeasured as decision
evidence. CONTENT-DISCOVERY-2 and ForgeAI integration stay out of scope.
G07 remains open.
