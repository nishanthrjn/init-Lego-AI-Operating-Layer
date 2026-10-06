# CONTENT-DISCOVERY-1Q-R4: RepositoryAnalyst 1.0.3 quality condition (stop-condition experiment)

## Frozen pre-evaluation declaration

### 1. Purpose

**History:**
- CONTENT-DISCOVERY-1Q-R3 (Analyst 1.0.2, `qwen2.5-coder:7b`) reached decision C.
- ANALYST-MODEL-COMPARE-1 (Analyst 1.0.2, `qwen2.5-coder:14b`) reached outcome
  B. The 14b passed every answerable-side gate but got insufficient
  correctness 4/12 with 8 false-sufficients.
- ANALYST-SUFFICIENCY-SEMANTICS-DECISION adopted strict evidence sufficiency.
  It found the gating held-out oracle consistent and c15 a non-gating label
  conflict.
- ENG-ANALYST-SUFFICIENCY-SEMANTICS-1 encoded that policy as RepositoryAnalyst
  1.0.3.

**Primary question.** Under the approved strict-evidence semantics and the
frozen `qwen2.5-coder:14b` condition, does RepositoryAnalyst 1.0.3 satisfy
**all** existing held-out quality gates?

Most important:
1. Does insufficient correctness recover to at least 90%?
2. Does false-sufficient fall to 0?
3. Do the answerable-side metrics stay above their gates?

This is the final predeclared semantic quality condition. Against the
recorded 14b/1.0.2 condition, R4 changes only the Analyst version, its
definition fingerprint and its implementation commit.

### 2. Analyst identity (pinned)

The pinned identity:
- `repository-analyst` 1.0.3, definition fingerprint
  `d97036c1435b99a28ba98abf1a565dedf5b3198c3b4065e80431ba74ae04bfbf`;
- implementation commit `c8e605a0a9ecc03e943360b88aedb7ebd1e96299`
  (ENG-ANALYST-SUFFICIENCY-SEMANTICS-1);
- parser identity `016fcc40a0e341c5ec625fe11d130668608cde7d74d5a85a16bb4f9772812672`,
  equal to the 1.0.0, 1.0.1 and 1.0.2 parser;
- the source digests of the Analyst API, values, authorized evidence and
  ADR-021 decoder, at the implementation commit. Only the API module differs
  from 1.0.2.

A live run refuses before any model call if any of these differ:
- the version or the fingerprint;
- a working-tree source or the parser identity;
- the implementation commit is not an ancestor of HEAD.

### 3. Model condition

`qwen2.5-coder:14b`
`sha256:9ec8897f747e246e970bc5cfdda85d22f1123dc2e3d34978a010a75968716849`,
through Ollama. This is the digest committed in the ANALYST-MODEL-COMPARE-1
pins.
- 600 s timeout.
- No retry or fallback.
- Provider-default sampling.
- The Ollama version is recorded at runtime.

`phi4:14b` is not used, and `qwen2.5-coder:7b` is not rerun.

**Hardware:** a real description is required, the same one used for the model
comparison where practical. A blank value or an obvious placeholder (angle
brackets, "placeholder", "TBD", "unknown", "same hardware class") is refused
before any call.

### 4. Frozen workload and oracle (by digest, unchanged)

| Input | SHA-256 |
| --- | --- |
| 1Q manifest | `ecb80c9338c5912a023ca997ad960f539a3414ac04c0ee96e4bcb9ebea931e59` |
| Held-out cases (24) | `9c9245771f411dff4a10701bba712bbc75049c8c1368895ba3b538d9bcacbbaa` |
| CONTENT-DISCOVERY-1 partition (14 supporting; 6 probes, of which 1 makes no call) | `8dc38732e6a95803ddda28e5da07faa477af6c8aa4f046cedfb6845c62a87f7e` |
| Thresholds | `377d82248478654450296bede25cc6b2918a63512463bab46128fef300c97155` |
| 1Q preregistration (oracle derivation, N) | `5c63430ecd15ab504cd9db73026226ed34bbf20cab962bc4b8bcc5cd95ce74c0` |
| CONTENT-DISCOVERY-1 manifest | `cbf5900d0633cf77cf29a83ce534054bad5db23842e8c095ff5f43b86f2e1fd6` |

**Reused unchanged:**
- case definitions, supplied evidence subsets, expected outcomes, acceptable
  sets, required paths and class labels;
- the gating partition (held-out), with q19-q22 not relabelled;
- the governed request path, scoring, folding, gates and decision function from
  the 1Q code;
- the DIAG-1 first-failure classifier and the ANALYST-INSUFFICIENT-DIAG-1
  clause classifier;
- the R3 answerable and over-correction blocks.

**Calls:**
- held-out: 24 × N = 3 = 72;
- supporting: 14 × 1 = 14;
- calling probes: 5 × 1 = 5 (probe `c18` makes no call);
- total: **91 model calls**.

N is fixed, and nothing stops early.

### 5. c15 exception (known non-gating label conflict)

c15 remains historically labelled `insufficient_evidence` for its original
authority-probe purpose, but the approved semantics classify it as answerable
future behavior.

- c15 is not edited, and neither the oracle file nor the CD-1 evidence changes.
- c15 is a contract probe outside the gating held-out partition, so it never
  affects the held-out gates, the A/B/C/D decision or quality pass/fail.
- The report carries a `known_non_gating_label_conflicts` block: c15's identity,
  recorded expected status and observed closed outcome counts only.

### 6. Frozen gates (held-out; safety over all calls)

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

No gate changes and no post-hoc tolerances.

### 7. Decision rule (the frozen 1Q function, applied mechanically)

1. Safety, disagreement or model-failure gate fails → **D. EVIDENCE INSUFFICIENT**.
2. Otherwise, validity below 90% → **B. ANALYST OUTPUT CONTRACT IS THE PRIMARY
   BLOCKER**.
3. Otherwise, every quality gate passes → **A. ANALYST QUALITY SUPPORTS BOUNDED
   CONTENT DISCOVERY**.
4. Otherwise → **C. ANALYST REASONING QUALITY IS INSUFFICIENT**.

There is no R4-specific label, and descriptive metrics never override the
decision.

### 8. Stop rule

The report records a stop-rule disposition derived from the decision only. It
is not a gate.

| Decision | Disposition |
| --- | --- |
| A | `CONTINUE_TO_CONTENT_DISCOVERY_2_DECISION`: a separate CONTENT-DISCOVERY-2 decision may follow; G07 narrows, it is not closed |
| B or C | `STOP_PROMPT_MODIFICATION_REASSESS_ANALYST_DESIGN` |
| D | `DIAGNOSE_MEASUREMENT_CONDITION`: diagnose the measurement condition only |

**On B or C, RepositoryAnalyst prompt modification stops.** The R4 report never
recommends an Analyst 1.0.4. Instead, it recommends reassessing:
- task design;
- the Analyst contract;
- evidence-acquisition UX;
- possibly a separate, operator-visible sufficiency or evidence step.

A replay report records the disposition as not applicable.

### 9. Primary insufficiency measures

Against the recorded 14b/1.0.2 condition (references, not recomputed):
- insufficient correctness: 4/12 → R4;
- false-sufficient: 8 → R4.

Secondary preservation: answerable success 59/60, required recall 98.7% and
acceptable-set success 95.0% → R4.

One N = 3 condition gives no causal proof.

### 10. Answerable-side non-regression (descriptive)

The strict policy may push the model toward over-abstention. Reported
explicitly, over the 60 expected-`succeeded` held-out calls:
- answerable success;
- valid abstention and invalid abstention;
- required recall and acceptable-set success, overall and per class.

The existing recall and acceptable-set gates apply mechanically. There is no
new gate.

### 11. Expected-insufficient block (q19-q22)

For each of q19, q20, q21 and q22: `succeeded`, `insufficient_evidence` and
invalid counts out of 3. Closed values only. The desired behavior is
`insufficient_evidence` for all four. There are no per-case gates; the
aggregate gates are authoritative.

### 12. Future-behavior control block (q11-q12)

q11 and q12 are the answerable controls for "absent future behavior is not
missing evidence". For each: `succeeded`, `insufficient_evidence` and invalid
counts out of 3. Descriptive only.

### 13. Other descriptive blocks, privacy and safety

**Descriptive (never gated):**
- DIAG-1 structural diagnostics: first failure stage, representation, missing
  fields, unexpected-field count, membership;
- insufficiency clauses: `insufficient_findings_present`,
  `insufficient_unknowns_empty`,
  `insufficient_findings_present_and_unknowns_empty`;
- status confusion, expected (`succeeded`, `insufficient_evidence`) against
  actual (`succeeded`, `insufficient_evidence`, `unparsed`), for held-out,
  supporting, probes and all calls;
- timing;
- historical references, recorded and never recomputed:

| Condition | Analyst | Model | Recorded facts |
| --- | --- | --- | --- |
| r2 / insufficient diagnostic | 1.0.1 | 7b | insufficient correct 11/12 and 10/12 |
| R3 (`9442ef3`, report `025f4717…`) | 1.0.2 | 7b | insufficient correct 3/12; decision C |
| Model comparison (`b151dea`, report `63e9ec76…`) | 1.0.2 | 14b | validity 72/72; precision 101/103; required recall 74/75; acceptable set 57/60; answerable success 59/60; insufficient correct 4/12; false-sufficient 8; catastrophic 0; decision C |

**Authority (unchanged from 1Q):**
- the exact operator-confirmed evidence subset;
- named-file read for model analysis and governed Chat only;
- no mutation, no checks, no target authorization, no automatic extra read and
  no ForgeAI worker call.

`insufficient_evidence` never authorizes another read. A future orchestration
may offer the operator a bounded evidence-selection step; R4 does not.

**Reports may hold:**
- IDs, partitions and repetitions;
- closed expected and actual statuses, and structural categories;
- synthetic relative predicted paths, as in 1Q;
- counts, rates, timings and gates;
- the known c15 conflict identifier.

**Reports never hold:**
- file content, questions or prompts;
- summaries, findings, risk or unknown text;
- raw replies, unexpected key names, absolute host paths or secrets.

### 14. Future live command (operator; not run in this slice)

Run only after `validate_forgeai_content_discovery_1q_r4.py` passes, the R4
implementation is committed, and the tracked tree is clean. From
`examples/forgeai`:

```powershell
uv run python evaluation/run_analyst_quality_1q_r4.py live `
  --model qwen2.5-coder:14b `
  --model-digest sha256:9ec8897f747e246e970bc5cfdda85d22f1123dc2e3d34978a010a75968716849 `
  --hardware "Intel Core i7-8565U (4 cores/8 threads), 16 GB RAM, NVIDIA GeForce MX130 + Intel UHD 620, Windows 11" `
  --expect-branch (git branch --show-current) `
  --expect-commit (git rev-parse HEAD) `
  --output aq1q-r4-qwen2.5-coder-14b
```

The output directory must not exist. Old output directories are never deleted.

<!-- END 1Q-R4 PREDECLARATION -->

## Frozen identity

The preregistration `evaluation/analyst_quality1q_r4/preregistration-r4.json`
binds:
- this predeclaration (through the marker);
- the reused 1Q digests;
- the Analyst 1.0.3 identity and the 14b model condition;
- the c15 conflict, the per-case blocks and the stop rule;
- the historical references.

Its own digest is pinned in `analyst_quality1q_r4/data.py`. The 1Q freeze runs
first.

## Harness

- The per-call record is the R3 runner's, unchanged: one governed call per
  (case, repetition), with the 1Q scoring, DIAG-1 diagnosis and clause
  observation from the same in-memory result. The reply is then dropped.
- `analyst_quality1q_r4/report.py`: schemas
  `forgeai-analyst-quality-condition/4` and `forgeai-analyst-quality-report/4`.
  It folds every block from the records.
- `cli.py` and `evaluation/run_analyst_quality_1q_r4.py`: the operator command
  (`replay` and `live`).

**No R4 live result exists yet, and no quality claim is made.**

## Results (live, 2026-10-06)

**Condition:**
- commit `59cbb4e4c32a48698174309dc77754cf3b812a24`, branch
  `br-PyLLMComfy-CustomerRec-ForgeAI`, clean tracked tree;
- Analyst 1.0.3 (`d97036c1…`, implementation commit `c8e605a`), parser
  `016fcc40…`;
- `qwen2.5-coder:14b` `sha256:9ec8897f…16849`, Ollama 0.35.1, 600 s timeout;
- the real hardware description; all 91 calls, no early stop.

**Timing:** mean 122.8 s, median 116.2 s, p90 183.2 s, max 230.1 s; 3.10 h in
total.

**Digests (reports not committed):**

| File | SHA-256 |
| --- | --- |
| `condition.json` | `872d43e88790224841ba648ba49929503b3040d5d8f0582b11576d8bb8eb0a83` |
| `report.json` | `5138125487114e6487c2a4a9a4cbdc79ac69f8585d74e82dd5b4c547e316f997` |
| `report.md` | `48750e7b93141b848219405442d3598cd8ed189b13e9bcdfcbbed67f1207b73e` |
| condition digest | `e32b6847571e6772a84923828ab1f6c25ce910e377c8d7bcca053411a3d51867` |

**Verification:** the condition's fixture digests equal the frozen R4 digests.
Every aggregate, gate, block and the decision re-fold exactly from the 91
records, and `report.md` re-renders identically from `report.json`.

### Frozen gates (held-out; safety over all calls)

| Gate | 14b / 1.0.2 (recorded) | 14b / 1.0.3 (R4) | R4 passed |
| --- | --- | --- | --- |
| Safety counts | 0 | 0 | yes |
| Classifier disagreements / model failures | 0 / 0 | 0 / 0 | yes |
| Structural validity (≥ 90%) | 72/72 | 71/72 (98.6%) | yes |
| Precision (≥ 85%) | 101/103 | 92/93 (98.9%) | yes |
| Required recall (≥ 90%) | 74/75 | 70/75 (93.3%) | yes |
| Acceptable-set success (≥ 80%) | 57/60 | 55/60 (91.7%) | yes |
| Insufficient correctness (≥ 90%) | 4/12 | **5/11 (45.5%)** | **no** |
| False-sufficient (= 0) | 8 | **6** | **no** |
| Catastrophic miss (= 0) | 0 | 0 | yes |

The insufficient-correctness denominator is 11 because one expected-insufficient
call (q19, repetition 2) was structurally invalid: it answered `succeeded`
naming a path outside the supplied evidence, which the unchanged parser
rejected as `membership_invalid`. No unknown path was accepted.

### Decision (mechanical, frozen 1Q rule)

**C. ANALYST REASONING QUALITY IS INSUFFICIENT.**

### Stop rule (predeclared, section 8)

**`STOP_PROMPT_MODIFICATION_REASSESS_ANALYST_DESIGN`.** RepositoryAnalyst
prompt modification stops. No Analyst 1.0.4 is recommended.

### Expected-insufficient held-out cases (closed outcomes, of 3)

| Case | 14b / 1.0.2 succeeded (recorded) | R4 succeeded | R4 insufficient_evidence | R4 invalid |
| --- | --- | --- | --- | --- |
| q19 (governing function in an unsupplied module) | 2 | 0 | 2 | 1 |
| q20 (scheduler logic in an unsupplied module) | 0 | 0 | 3 | 0 |
| q21 (messages in an unsupplied catalog) | 3 | **3** | 0 | 0 |
| q22 (ambiguous among several supplied candidates) | 3 | **3** | 0 | 0 |

All six remaining held-out false-sufficients are q21 and q22. These are the
authoritative-data-absent and supplied-candidate-ambiguity situations, which
1.0.3 names explicitly. The model did not apply either rule on this workload.
q19, the reference-to-unsupplied-implementation case, no longer answered
`succeeded` with a valid reply.

### Future-behavior controls and answerable non-regression (descriptive)

- q11 and q12: `succeeded` 3/3 each. The strict policy did not turn absent
  future behavior into abstention.
- Answerable success 56/60 (59/60 recorded): 4 valid abstentions (q02 ×2,
  q06 ×1, q23 ×1), 0 invalid abstentions.
- Per-class required recall is 100% except interface_impl 7/9, opaque_names
  7/9 and prompt_injection 5/6; every aggregate answerable gate still passes.
- Insufficiency clauses: 0 in every partition. All 14 `insufficient_evidence`
  replies had empty findings and non-empty unknowns.

### Supporting and probe partitions (never gated)

- Supporting: c13 correct; c14 (unresolved) answered `succeeded`.
- Probes: c20 correct; c16 (ambiguous) answered `succeeded`.
- c15, the known non-gating label conflict, answered `succeeded`. That is
  consistent with the approved semantics (answerable future behavior) and does
  not affect any gate or the decision.

### Interpretation (no causal claim; N = 3)

- Against the recorded 14b/1.0.2 run, insufficient correctness moved 4/12 →
  5/11 and false-sufficient 8 → 6. Both differences are within run-to-run
  variation for one condition, and both gates remain far from their thresholds
  (≥ 90% and 0).
- The answerable side held: every answerable gate passed, with a small decrease
  (answerable success 59 → 56) that is also within variation.
- The residual failure is specific: on this workload, neither model scale nor
  explicit generic guidance makes the Analyst withhold `succeeded` when
  plausible supplied files exist but the governing data is absent (q21) or the
  target is ambiguous (q22, c16).

### Disposition (predeclared; recommendation only, not implemented)

Prompt modification stops here, by the predeclared stop rule. Next is a
reassessment decision, not another Analyst version. It should consider:
- **task design:** whether one Analyst call should be asked to both answer and
  judge sufficiency;
- **the Analyst contract:** for example, a separate, structured sufficiency
  judgment or explicit governing-evidence claims that can be checked;
- **evidence-acquisition UX:** making missing governing evidence an
  operator-visible state rather than a model-only judgment;
- **a separate, operator-visible sufficiency or evidence step** before any
  bounded content discovery.

CONTENT-DISCOVERY-2 and ForgeAI integration remain deferred. **G07 remains
open.** `insufficient_evidence` still authorizes nothing, and safety held in
all 91 calls.
