# CONTENT-DISCOVERY-1Q-R3: RepositoryAnalyst 1.0.2 quality condition

## Frozen pre-evaluation declaration

### 1. Why R3 exists

**History (Analyst 1.0.1):**
- CONTENT-DISCOVERY-1Q-R2 removed the 1.0.0 field-set blocker but stayed at
  decision B: held-out validity was 59/72.
- ANALYST-INSUFFICIENT-DIAG-1 showed the dominant behavior was abstention on
  answerable cases. All 12 invalid abstentions had findings present.
- ANALYST-ABSTENTION-DECISION-1 found that the 1.0.1 guidance defined status
  shapes but no status decision policy.

**What changed:** ENG-ANALYST-SUFFICIENCY-PROMPT-1 added that policy as
RepositoryAnalyst 1.0.2, at commit
`f1cd2b69ca6c7cdcf0c9cd19ba8f349253f0379b`. A changed prompt is a new
condition. The r2 and DIAG-1 conditions stay pinned to 1.0.1 and refuse 1.0.2.

**Primary question.** Under the otherwise frozen 1Q condition, does
RepositoryAnalyst 1.0.2 satisfy the existing structural and relevance quality
gates?

**Secondary, descriptive only.** Does answerable-case abstention decrease
compared with the recorded 1.0.1 conditions? There is no gate for this.

### 2. Analyst identity (pinned)

The pinned identity:
- `repository-analyst` 1.0.2, definition fingerprint
  `5f6635c756df41a855fd1ab8b538765267ba97b31410b16125e905697b82ceef`;
- parser identity `016fcc40a0e341c5ec625fe11d130668608cde7d74d5a85a16bb4f9772812672`.
  That is the Analyst API module without its definition function, equal to the
  1.0.0 and 1.0.1 parser, so only the guidance and version changed;
- the source digests of the Analyst API, values, authorized evidence and
  ADR-021 decoder, at the implementation commit.

A live run refuses before any model call if any of these differ:
- the version or the fingerprint;
- a working-tree source or the parser identity;
- the implementation commit is not an ancestor of HEAD.

### 3. Reused frozen workload (by digest, unchanged)

| Input | SHA-256 |
| --- | --- |
| 1Q manifest | `ecb80c9338c5912a023ca997ad960f539a3414ac04c0ee96e4bcb9ebea931e59` |
| Held-out cases (24) | `9c9245771f411dff4a10701bba712bbc75049c8c1368895ba3b538d9bcacbbaa` |
| CONTENT-DISCOVERY-1 partition (14 supporting; 6 probes, of which 1 makes no call) | `8dc38732e6a95803ddda28e5da07faa477af6c8aa4f046cedfb6845c62a87f7e` |
| Thresholds | `377d82248478654450296bede25cc6b2918a63512463bab46128fef300c97155` |
| 1Q preregistration (oracle derivation, N, model) | `5c63430ecd15ab504cd9db73026226ed34bbf20cab962bc4b8bcc5cd95ce74c0` |
| CONTENT-DISCOVERY-1 manifest | `cbf5900d0633cf77cf29a83ce534054bad5db23842e8c095ff5f43b86f2e1fd6` |

**Reused unchanged:**
- the cases, oracle, partition, expected outcomes and gating partition
  (held-out);
- the governed request path, scoring, folding, gates and decision function from
  the 1Q code;
- the DIAG-1 first-failure classifier and the ANALYST-INSUFFICIENT-DIAG-1
  clause classifier.

### 4. Call plan and model condition (unchanged)

**Calls:**
- held-out: 24 × N = 3 = 72;
- supporting: 14 × 1 = 14;
- calling probes: 5 × 1 = 5 (probe `c18` makes no call);
- total: **91 model calls**.

N is fixed, and nothing stops early.

**Model:** `qwen2.5-coder:7b`
`sha256:dae161e27b0e90dd1856c8bb3209201fd6736d8eb66298e75ed87571486f4364`,
through Ollama.
- 600 s timeout.
- No retry or fallback.
- Provider-default sampling.
- The Ollama version is recorded at runtime.

**Hardware:** a real hardware description is required. A blank value or an
obvious placeholder (angle brackets, "placeholder", "TBD", "unknown", "same
hardware class") is refused before any call.

### 5. Frozen gates (held-out; safety over all calls)

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

### 6. Decision rule (the frozen 1Q function, applied mechanically)

1. Safety, disagreement or model-failure gate fails → **D. EVIDENCE INSUFFICIENT**.
2. Otherwise, validity below 90% → **B. ANALYST OUTPUT CONTRACT IS THE PRIMARY
   BLOCKER**.
3. Otherwise, every quality gate passes → **A. ANALYST QUALITY SUPPORTS BOUNDED
   CONTENT DISCOVERY**.
4. Otherwise → **C. ANALYST REASONING QUALITY IS INSUFFICIENT**.

There is no R3-specific label, and descriptive metrics never override the
decision. The pre-declared follow-ups:
- **A:** a separate CONTENT-DISCOVERY-2 decision before any integration. G07 may
  narrow, but it is not closed from one synthetic workload.
- **B:** diagnose the remaining first structural stage. There is no immediate
  Analyst 1.0.3.
- **C:** ANALYST-MODEL-COMPARE-1 becomes the next candidate, unless a new
  evidence or oracle defect appears. Prompt tuning stops here.
- **D:** diagnose that condition only.

### 7. Descriptive metrics (reported, never gated)

**Structural diagnostics** (DIAG-1), for every call:
- first-failure stage and representation;
- missing required fields (canonical order) and unexpected-field count (no
  names);
- field types and the closed status value;
- the DIAG-1 structural pattern.

**Insufficient-evidence clauses** (ANALYST-INSUFFICIENT-DIAG-1). For replies
that reach the rule with status `insufficient_evidence`:
- `findings_count` and `unknowns_count`;
- the refined category: `insufficient_findings_present`,
  `insufficient_unknowns_empty`, or
  `insufficient_findings_present_and_unknowns_empty`.

**Answerable-success rate:** held-out calls with expected outcome `succeeded`,
a structurally valid reply and actual status `succeeded`, divided by all 60
expected-`succeeded` held-out calls.

**Abstention**, over the 60 expected-`succeeded` held-out calls:
- valid success, valid abstention, invalid abstention and other invalid;
- total abstention = valid abstention + invalid abstention.

**Status confusion:** expected (`succeeded`, `insufficient_evidence`) against
actual (`succeeded`, `insufficient_evidence`, `unparsed`). It is reported for
held-out, supporting, probes and all calls.

**Over-correction watch:**
- expected-insufficient → succeeded, per partition;
- insufficient correctness, false-sufficient and catastrophic miss.

These come from the frozen gates. A failure is never rationalized by an
improved answer rate.

### 8. Historical references (recorded, never recomputed)

| Condition | Analyst | Recorded facts |
| --- | --- | --- |
| 1Q (`2edc3f7`, report `f03d213f…`) | 1.0.0 | valid 0/91; decision B |
| r2 (`2e8f1ab`, report `e5a0efd3…`) | 1.0.1 | held-out validity 59/72; answerable success 13/60; valid abstention 34/60; invalid abstention 12/60; other invalid 1/60; decision B |
| DIAG-1 (`fa4aa8f`, report `09c096a7…`) | 1.0.1 | held-out validity 60/72; answerable success 17/60; valid abstention 31/60; invalid abstention 12/60; other invalid 0/60; `insufficient_findings_present` 12/12; decision B (abstention) |

The two 1.0.1 conditions are reported separately and never averaged.

### 9. Authority, safety and privacy (unchanged from 1Q)

**Authority:**
- the exact confirmed evidence subset;
- named-file read for model analysis and governed Chat;
- no mutation, no check grant, no target authorization and no ForgeAI worker
  call.

The output is advisory.

**Reports may hold:**
- IDs, partitions and repetitions;
- closed statuses and categories;
- synthetic relative predicted paths, as in 1Q;
- counts, rates, timings and gates.

**Reports never hold:**
- file content, questions or prompts;
- summaries, findings, risk or unknown text;
- raw replies, unexpected key names, absolute paths or secrets.

<!-- END 1Q-R3 PREDECLARATION -->

## Frozen identity

The preregistration `evaluation/analyst_quality1q_r3/preregistration-r3.json`
binds:
- this predeclaration (through the marker);
- the reused 1Q digests;
- the Analyst 1.0.2 identity and the model condition;
- the historical references.

Its own digest is pinned in `analyst_quality1q_r3/data.py`. The 1Q freeze runs
first.

## Harness

- `analyst_quality1q_r3/runner.py`: one governed call per (case, repetition),
  on the unchanged request path. The 1Q scoring, the DIAG-1 diagnosis and the
  clause observation all come from the same in-memory result; the reply is then
  dropped.
- `report.py`: schemas `forgeai-analyst-quality-condition/3` and
  `forgeai-analyst-quality-report/3`. It folds from the records:
  - the 1Q aggregates, gates and decision;
  - the DIAG-1 structural block;
  - the clause, confusion and abstention block;
  - answerable success, the over-correction watch and the historical comparison.
- `cli.py` and `evaluation/run_analyst_quality_1q_r3.py`: the operator command.

## Live procedure (operator; not run in this slice)

Run it only after `validate_forgeai_content_discovery_1q_r3.py` passes, this
slice is committed, and the tracked tree is clean. From `examples/forgeai`:

```powershell
uv run python evaluation/run_analyst_quality_1q_r3.py live `
  --model qwen2.5-coder:7b `
  --model-digest sha256:dae161e27b0e90dd1856c8bb3209201fd6736d8eb66298e75ed87571486f4364 `
  --hardware "<REAL HARDWARE DESCRIPTION>" `
  --expect-branch (git branch --show-current) `
  --expect-commit (git rev-parse HEAD) `
  --output aq1q-r3-qwen2.5-coder-7b
```

Replace the hardware placeholder with the real machine description, for example
the CPU, GPU and memory. The literal placeholder is refused.

**No R3 live result exists yet, and no quality claim is made.**

## Local qualification

All 43 phases of `validate_forgeai_content_discovery_1q_r3.py` passed on
2026-10-05 (46 including sub-phases), with no live model or Docker. That
includes regressions for:
- Analyst (90 tests) and authorized evidence (25);
- DISCOVERY-1 (185);
- DISCOVERY-2A/2A.1, CONTENT-DISCOVERY-1, 1Q and DIAG-1 (310);
- ForgeAI architecture (41) and the Analyst 1.0.2 prompt (61);
- r2 (34) and DIAG-1 (38) pinned to 1.0.1.

**Preflight:** two live attempts with the literal hardware placeholder were
refused before any call, and nothing was written.

## Results (live, 2026-10-05)

**Condition:**
- commit `9442ef393d22c316a378818952d690566b04eb52`, clean tracked tree;
- RepositoryAnalyst 1.0.2, fingerprint `5f6635c7…ceef`, parser identity
  `016fcc40…2672`;
- `qwen2.5-coder:7b` `sha256:dae161e2…f4364`, Ollama 0.35.1, 600 s timeout,
  provider-default sampling, no retry or fallback;
- hardware: Intel Core i7-8565U (4 cores/8 threads), 16 GB RAM, NVIDIA GeForce
  MX130 + Intel UHD 620, Windows 11;
- all 91 planned calls completed.

The report was not committed. Its digests:
- `report.json`: SHA-256 `025f4717b2479812823068196f00cdf587ba3fcb40b083ea7ebd23e69dd0d367`;
- `report.md`: `ad324ab8ee4bd758fb4a15ce225b9a77c2a6044c699dc16553bf740dc5af4df3`;
- `condition.json`: `b85648aaaa24fb813de5e9f56de4aa629f11578852b89c5c521271f66444bf60`;
- condition digest: `a8d403e0cdddaee8d04178fa858649fe1c436ddbb288652c90ba79295fb5619e`.

Re-building from the 91 records reproduces every aggregate, gate, decision and
descriptive block exactly, and `report.md` re-renders identically.

### Frozen gates (held-out; safety over all calls)

| Gate | Result | Passed |
| --- | --- | --- |
| Safety counts | 0 | yes |
| Classifier disagreements | 0 | yes |
| Model failures | 0/72 | yes |
| Structural validity (≥ 90%) | 67/72 = 93.1% | **yes** (first time) |
| Precision (≥ 85%) | 49/56 = 87.5% | yes |
| Required recall (≥ 90%) | 34/67 = 50.7% | no |
| Acceptable-set success (≥ 80%) | 21/55 = 38.2% | no |
| Insufficient correctness (≥ 90%) | 3/12 = 25.0% | no |
| False-sufficient (= 0) | 10 | no |
| Catastrophic miss (= 0) | 0 | yes |

### Decision (mechanical, frozen 1Q rule)

**C. ANALYST REASONING QUALITY IS INSUFFICIENT.** Structural validity passed,
and four quality gates fail. Relevance metrics are decision evidence for this
condition.

### Descriptive comparison (no causal claim; N = 3)

| Measure (held-out) | r2 / 1.0.1 | DIAG-1 / 1.0.1 | R3 / 1.0.2 |
| --- | --- | --- | --- |
| Structural validity | 59/72 | 60/72 | **67/72** |
| Answerable success | 13/60 | 17/60 | **28/60** |
| Valid abstention (answerable) | 34/60 | 31/60 | 27/60 |
| Invalid abstention (answerable) | 12/60 | 12/60 | 4/60 |
| Other invalid (answerable) | 1/60 | 0/60 | 1/60 |
| Total abstention (answerable) | 46/60 | 43/60 | 31/60 |
| Expected-insufficient → succeeded | 1/12 | 2/12 | **9/12** |

**What changed:**
- **Structural validity passed the gate.** Invalid abstentions fell from 12 to 4
  on answerable cases. All 5 remaining invalid abstentions (4 held-out, 1
  supporting) are still `insufficient_findings_present`, so the defect is
  reduced but persists.
- **Two new `membership_invalid` replies** cite unsupplied paths: `q16`
  repetition 2 and `c13`. Membership rejected both, and the safety counts stay 0.
- **Answerable success rose to 28/60** (46.7%), but abstention on answerable
  cases is still 31/60. Eight answerable cases never succeeded across their
  3 calls: q08, q12, q14, q23 and q24 abstained in every call, and q01, q02 and
  q06 succeeded only once each.

**Over-correction occurred:**
- 9 of 12 expected-insufficient held-out calls answered `succeeded`. Insufficient
  correctness fell to 25%.
- Every call for `q21` was a false success, and q19, q20 and q22 each had two.
- False-sufficient = 10: 9 on expected-insufficient cases and 1 partial answer
  (`q06` repetition 2).

The frozen gate fails, and it is not rationalized by the improved answer rate.

**Calibration rather than formatting:** the policy moved the model's status
choice in both directions at once. It raised answers on answerable cases and on
unanswerable cases alike, while 8 answerable cases kept failing. That is a
discrimination (calibration) failure, not a formatting or contract failure.

### Next step (pre-declared; recommendation only, not implemented)

Under C, the pre-declared follow-up is **ANALYST-MODEL-COMPARE-1**. Prompt tuning
stops here, because the explicit status policy has now been tested. The R3
results expose no new evidence or oracle defect:
- the supplied subsets are unchanged and audited complete;
- the expected-insufficient cases visibly lack the required code.

The comparison would keep Analyst 1.0.2, the evidence, the oracle, N and the
thresholds fixed, under separately pinned model conditions. No stronger model is
installed locally today, so candidate selection, hardware cost and the pinned
digests are part of that slice's decision.

CONTENT-DISCOVERY-2 and ForgeAI integration remain deferred. **G07 remains open.**
