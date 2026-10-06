# ANALYST-MODEL-COMPARE-1: does a stronger model resolve RepositoryAnalyst 1.0.2 quality?

## Pre-run declaration

### 1. Starting point: R3 decision C

CONTENT-DISCOVERY-1Q-R3 measured RepositoryAnalyst 1.0.2 on `qwen2.5-coder:7b`.
- Commit `9442ef3`; report `025f4717b2479812823068196f00cdf587ba3fcb40b083ea7ebd23e69dd0d367`.
- Decision: **C. ANALYST REASONING QUALITY IS INSUFFICIENT**.

Held-out results:
- **Passed:** validity 67/72, precision 49/56, catastrophic 0, safety 0.
- **Failed:** required recall 34/67, acceptable set 21/55, insufficient
  correctness 3/12, false-sufficient 10.

Descriptive results: answerable success 28/60, and 9 of 12 expected-insufficient
calls answered succeeded.

### 2. Why prompt tuning has stopped

The R3 predeclaration fixed the follow-up for C: prompt tuning stops, and model
comparison is the next candidate.

- 1.0.1 fixed the field contract.
- 1.0.2 tested an explicit status decision policy. It moved answers in both
  directions, without better discrimination.

RepositoryAnalyst 1.0.2 is therefore held byte-for-byte unchanged:
- no 1.0.3, no examples and no re-worded status guidance;
- no parser change, retry, repair or JSON mode.

**Question:** are the 1.0.2 quality failures materially specific to
`qwen2.5-coder:7b`, or do they persist under a stronger model condition? The
model is the only changed variable. This is an evaluation experiment, not a
leaderboard, router, fallback or provider abstraction.

### 3. Installed local inventory (Ollama 0.35.1, read from `/api/tags`, 2026-10-05)

| Model | Digest | Family | Parameters | Quant | Disk | Repository evidence |
| --- | --- | --- | --- | --- | --- | --- |
| `qwen2.5-coder:7b` | `sha256:dae161e27b0e90dd1856c8bb3209201fd6736d8eb66298e75ed87571486f4364` | qwen2 | 7.6B | Q4_K_M | 4.68 GB | LQ1, 1Q, DIAG-1, r2, insufficient diagnostic, R3 (control) |
| `qwen2.5-coder:3b` | `sha256:f72c60cabf6237b07f6e632b2c48d533cef25eda2efbd34bed21c5e9c01e6225` | qwen2 | 3.1B | Q4_K_M | 1.93 GB | LQ1 baseline only |
| `qwen2.5-coder:1.5b` | `sha256:d7372fd828518a4d38b1eb196c673c31a85f2ed302b3d1e406c4c2d1b64a0668` | qwen2 | 1.5B | Q4_K_M | 0.99 GB | none |
| `llama3.2:latest` | `sha256:a80c4f17acd55265feec403c7aef86be0c25983ab279d83f3bcd3abbcb5b8b72` | llama | 3.2B | Q4_K_M | 2.02 GB | LQ1 baseline only |
| `nomic-embed-text:latest` | `sha256:0a109f422b47e3a30ba2b10eca18548e944e8a23073ee3f3e947efcf3c45e59f` | nomic-bert | 137M | F16 | 0.27 GB | embedding model; not a chat candidate |

No installed chat model is stronger than the control; every other installed
model is smaller. Comparing weaker variants cannot answer the question, so none
is selected. **A stronger candidate must be acquired.** It is not pulled in this
slice.

### 4. Host feasibility

The measured host:
- Intel Core i7-8565U, 4 cores / 8 threads;
- 16 GB RAM (about 5 GB free at inspection, with other applications open);
- NVIDIA GeForce MX130 with 2 GB VRAM, plus Intel UHD 620;
- Windows 11, with 222 GB free disk.

With 2 GB of VRAM, inference is effectively CPU-bound.

**Control timing (R3, 91 calls):** mean 47.5 s, median 43.1 s, p90 66.2 s,
max 101.9 s, total 1.2 h.

| Candidate class | Approx. Q4 size | Host fit |
| --- | --- | --- |
| 14B (Q4_K_M) | about 9 GB | Runnable on CPU if roughly 10 GB of RAM is free (close other applications). Expected about 2-2.5× control latency: about 100-120 s mean, about 2.5-3 h per 91 calls, well under the 600 s timeout. The smoke stage measures this before any full run. |
| 32B and larger (Q4) | 19 GB or more | **Not runnable on this host** (exceeds RAM). Acquisition candidate only, for different hardware. |

### 5. Candidate selection

**Control: `qwen2.5-coder:7b`**
`sha256:dae161e27b0e90dd1856c8bb3209201fd6736d8eb66298e75ed87571486f4364`.
The recorded R3 condition is the control and is **not re-run**:
- every non-model identity is pinned and verified;
- r2 and the insufficient diagnostic already document run-to-run variation at
  N = 3;
- a duplicate 91-call run (about 1.2 h) would add little to the comparison's
  fairness. A control re-run would need its own justification and approval.

**Primary candidate (required): `qwen2.5-coder:14b`**, Q4_K_M, about 9 GB,
Apache-2.0.
- It is the same family, tokenizer conventions and instruction format as the
  control, at about twice the parameters. Scale is close to the only changed
  variable.
- It is stronger on code and repository reasoning than the 7b, and it is the
  largest coding model that is practical on this host.
- It works with the existing Ollama chat adapter without changes. It is a
  non-thinking model, so its output is plain text the unchanged ADR-021 decoder
  already handles.

**Optional candidate (different family): `phi4:14b`**, about 9.1 GB, MIT licence.
- It is a strong general-reasoning model of the same size class.
- It tests whether the result is specific to the qwen family.
- It is run only if the primary candidate's smoke succeeds and the operator
  approves the extra 2.5-3 h.

**Not selected:**
- **Smaller installed models** cannot show whether a stronger model helps.
- **Thinking or reasoning-trace models** emit reasoning blocks that the
  unchanged request and decoder path was not designed for. That would confound
  the model variable with output-format handling.
- **Cloud providers** are excluded from this slice.

**Acquisition is required before any candidate run** (operator, separately
approved). The commands:

```powershell
ollama pull qwen2.5-coder:14b
# optional, second family, only after the primary smoke succeeds:
ollama pull phi4:14b
```

After pulling, the operator:
1. reads the exact digest (`ollama list`, or `/api/tags`);
2. records it in `evaluation/analyst_model_compare1/model-pins.json`;
3. commits that record before any smoke or full run.

Live commands refuse a candidate whose digest is unpinned or different.

### 6. Frozen identity (everything except the model)

Every candidate condition reuses, unchanged and verified before the first call:
- **Analyst:** RepositoryAnalyst 1.0.2, fingerprint
  `5f6635c756df41a855fd1ab8b538765267ba97b31410b16125e905697b82ceef`, parser
  identity `016fcc40a0e341c5ec625fe11d130668608cde7d74d5a85a16bb4f9772812672`,
  implementation commit `f1cd2b69ca6c7cdcf0c9cd19ba8f349253f0379b`, with source
  digests checked by the R3 freeze;
- **workload:** the 1Q manifest, the 24 held-out cases, the partition, the
  thresholds, the 1Q preregistration and the CD-1 manifest, all verified through
  the R3 and 1Q freezes;
- **measurement:** the oracle, expected outcomes, N = 3/1 and the 91-call plan;
- **request path:** the evidence subsets, read and Chat grants only, and the R3
  per-call record (1Q scoring, DIAG-1 diagnosis, clause observation);
- **decision:** the frozen 1Q gates and decision function.

**What changes per candidate:**
- the model name and exact digest, which must equal the committed pin and the
  Ollama-reported digest;
- the recorded Ollama version, timeout (600 s), the hardware description (a real
  one; placeholders are refused) and the commit.

### 7. Gates (applied independently to each candidate; unchanged)

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

Each candidate report carries its own frozen A/B/C/D decision under the 1Q
rule.

### 8. Secondary metrics (descriptive, never gated)

For each model:
- answerable success, valid, invalid and total abstention;
- expected-insufficient → succeeded;
- over-selection and under-selection;
- per-class required recall and acceptable-set success;
- call time (mean, median, p90, max);
- model failures and structural failure stages;
- refined `insufficient_evidence` clauses.

### 9. Comparison rule (applied mechanically; exactly one outcome)

**Inputs:** the control is the recorded R3 report, verified by SHA-256. Each
candidate's full 91-call report must pass identity verification:
- schema and live mode;
- the Analyst fingerprint and parser identity;
- workload digests equal to the freeze;
- the 91-call plan;
- the model digest equal to the committed pin;
- records that re-fold exactly.

The control's held-out values: required recall 0.5075, acceptable set 0.3818,
insufficient correctness 0.25, false-sufficient 10.

**A candidate is materially better** when its frozen decision is A (every gate
passes), or when all of these hold:
- structural validity ≥ 90% and safety counts 0;
- required recall ≥ control + 0.15 (at least 0.6575);
- acceptable-set success ≥ control + 0.15 (at least 0.5318);
- insufficient correctness ≥ control + 0.25 (at least 0.50);
- false-sufficient ≤ half the control (at most 5);
- required recall improves in a strict majority of the answerable held-out
  classes that are defined in both reports.

These margins exceed single-call N = 3 movement. For example, a
required-recall change of 0.15 is at least 10 of the 67 required files. That
avoids declaring wins from 1-3 calls.

**Outcomes:**
1. Any candidate report that fails identity verification, has its own frozen
   decision D, or has a classifier disagreement → **D. EVIDENCE INSUFFICIENT**.
2. Otherwise, at least one candidate is materially better and has safety counts
   0 → **A. STRONGER MODEL CONDITION JUSTIFIED**.
3. Otherwise, at least one full candidate report exists → **B. MODEL CHANGE DOES
   NOT RESOLVE ANALYST QUALITY**.
4. If no candidate can complete its smoke stage on this host (every smoke call
   is a model failure, or a smoke call exceeds 600 s) and no full report exists →
   **C. CURRENT HARDWARE CANNOT TEST A CREDIBLE STRONGER MODEL**.

**Constraints on the outcome:**
- A safety failure blocks A for that candidate.
- A higher answer rate never compensates for false-sufficient: it is a required
  condition of material improvement.
- Lower structural validity is recorded as a tradeoff and is never repaired or
  normalized.
- A does not authorize routing, fallback or integration; it only justifies a
  stronger model condition for later configuration.

### 10. Staged execution (per candidate)

**Stage 1, smoke (non-gating):**
- one call each for 3 frozen cases: `q04` (answerable), `q10` (multi-file
  answerable) and `q19` (expected insufficient);
- the same preflight as the full run;
- it proves model compatibility, output shape and latency, and projects the
  91-call duration;
- schema `forgeai-analyst-model-compare-smoke/1`, labelled "not quality
  evidence", with no gates or decision.

**Stage 2, full condition:**
- all 91 calls in the frozen order, with no early stop;
- schema `forgeai-analyst-model-compare-report/1`, per model and in its own
  output directory.

**Comparison:**
- schema `forgeai-analyst-model-compare-comparison/1`;
- it references the control and each candidate report by SHA-256, re-verifies
  each identity and applies section 9.

Model outputs are never merged. There is no model routing, no automatic fallback
and no change to ModelPort, the Ollama adapter or the routing configuration.

### 11. Historical references (recorded, never recomputed)

| Condition | Analyst | Model | Held-out facts |
| --- | --- | --- | --- |
| 1Q (`2edc3f7`) | 1.0.0 | qwen2.5-coder:7b | valid 0/91 (all calls); B |
| r2 (`2e8f1ab`) | 1.0.1 | qwen2.5-coder:7b | valid 59/72; answerable success 13/60; B |
| insufficient diagnostic (`fa4aa8f`) | 1.0.1 | qwen2.5-coder:7b | valid 60/72; answerable success 17/60; B (abstention) |
| R3 (`9442ef3`) | 1.0.2 | qwen2.5-coder:7b | valid 67/72, precision 49/56, required recall 34/67, acceptable set 21/55, insufficient correct 3/12, false-sufficient 10, catastrophic 0, answerable success 28/60; C |

### 12. Authority, safety and privacy (unchanged)

**Authority:** read and governed Chat only, on the exact confirmed evidence, for
every model. There is no mutation or check grant, no target authorization and no
ForgeAI worker call.

**Privacy:** reports hold only closed values, counts, synthetic relative
predicted paths, timings and digests. They never hold contents, questions,
prompts, replies, narrative or absolute paths.

<!-- END MODEL-COMPARE-1 PREDECLARATION -->

## Harness

`examples/forgeai/evaluation/analyst_model_compare1/`:
- `preregistration-compare1.json`: frozen; its digest is pinned in `data.py`.
- `model-pins.json`: operator-recorded candidate digests, committed before any
  run.
- `data.py`: freeze and identity checks; the candidate registry and pin
  enforcement.
- `report.py`: the per-model report (the R3 blocks plus timing), the smoke
  report, and the comparison under the section 9 rule.
- `cli.py`, with the modes `replay`, `smoke`, `live` and `compare`; and
  `evaluation/run_analyst_model_compare_1.py`.

Each call reuses the R3 runner unchanged.

## Live procedure (operator; not run in this slice)

The prerequisites:
- the validator passes and this slice is committed;
- the candidate is pulled;
- its digest is recorded in `model-pins.json` and committed;
- the tracked tree is clean.

From `examples/forgeai`:

```powershell
# Stage 1: smoke (non-gating)
uv run python evaluation/run_analyst_model_compare_1.py smoke `
  --model qwen2.5-coder:14b --model-digest <pinned sha256:...> `
  --hardware "Intel Core i7-8565U (4 cores/8 threads), 16 GB RAM, NVIDIA GeForce MX130 + Intel UHD 620, Windows 11" `
  --expect-branch (git branch --show-current) --expect-commit (git rev-parse HEAD) `
  --output amc1-smoke-qwen2.5-coder-14b

# Stage 2: the full frozen condition (about 2.5-3 h on this host)
uv run python evaluation/run_analyst_model_compare_1.py live `
  --model qwen2.5-coder:14b --model-digest <pinned sha256:...> `
  --hardware "Intel Core i7-8565U (4 cores/8 threads), 16 GB RAM, NVIDIA GeForce MX130 + Intel UHD 620, Windows 11" `
  --expect-branch (git branch --show-current) --expect-commit (git rev-parse HEAD) `
  --output amc1-qwen2.5-coder-14b

# Comparison (no model call)
uv run python evaluation/run_analyst_model_compare_1.py compare `
  --control aq1q-r3-qwen2.5-coder-7b/report.json `
  --candidate amc1-qwen2.5-coder-14b/report.json `
  --smoke amc1-smoke-qwen2.5-coder-14b/smoke.json `
  --output amc1-comparison
```

**No candidate is installed, and no comparison result exists yet.**

## Acquisition and pins (2026-10-06)

The operator pulled both candidates. Their digests, as Ollama reports them, are
recorded in `model-pins.json` (commit `e9024c9`):

| Model | Digest | Family / size |
| --- | --- | --- |
| `qwen2.5-coder:14b` | `sha256:9ec8897f747e246e970bc5cfdda85d22f1123dc2e3d34978a010a75968716849` | qwen2, 14.8B Q4_K_M, 9.0 GB, context 32768 |
| `phi4:14b` | `sha256:ac896e5b8b34a1f4efa7b14d7520725140d5512484457fab45d2a4ea14c69dba` | phi3, 14.7B Q4_K_M, 9.1 GB, context 16384 |

## Stage 1 smoke: `qwen2.5-coder:14b` (2026-10-05T22:49Z; not quality evidence)

- **Condition:** commit `e9024c9`, clean tracked tree; Analyst 1.0.2
  (`5f6635c7…`); Ollama 0.35.1; the real hardware description.
- **Files:** `smoke.json` SHA-256
  `2b03221b27dfb16f7e5c40ab740aaa79ac388987e7164ac664bbb825f7ae6d18`;
  `condition.json`
  `d8584d45908fbe5ffc79e42eaa27de37d81412eef439b94331b95fe932eb7800`;
  condition digest
  `90ad01e5b481bff3b3ad50c2f6dbed38866fa52a6318b8aa7482deff85c27e02`.
- **Compatibility:** 3/3 replies structurally valid; 0 model failures.
  `fits_host` is true.
- **Latency:** mean 187.4 s and max 239.5 s per call. That is about 4x the
  control (mean 47.5 s), not the 2-2.5x estimated, but every call is under the
  600 s timeout. The projected full run is about 4.7 h.
- **Not evidence:** the smoke carries no gates and no decision. Its status
  outcomes are not compared with anything.
- **Recording note:** the smoke `plan` block reuses the 1Q `plan_counts`
  helper. It shows `heldout_repetitions: 3` as a constant, while the smoke
  actually makes one call per case (`total_calls: 3`).

The R3 control `report.json` was restored from `9a92430` to its local path for
the later comparison step. Its SHA-256 matches the pinned
`025f4717…d0d367` exactly.

**Next:** the full 91-call `qwen2.5-coder:14b` condition, then the comparison.
`phi4:14b` remains optional and needs separate approval.

## Stage 2 full condition and comparison (live, 2026-10-06)

**Condition:**
- `qwen2.5-coder:14b`
  `sha256:9ec8897f747e246e970bc5cfdda85d22f1123dc2e3d34978a010a75968716849`;
- commit `46ef93f8b7fc186d42448fadaf94cac2b1727d4e`, clean tracked tree;
- Analyst 1.0.2 (`5f6635c7…`), parser `016fcc40…`; Ollama 0.35.1, 600 s timeout;
- the real hardware description;
- all 91 calls, no early stop.

**Timing:** mean 130.1 s, median 121.8 s, p90 188.7 s, max 238.5 s; 3.29 h in
total, under the smoke projection of 4.7 h.

**Digests (reports not committed):**

| File | SHA-256 |
| --- | --- |
| candidate `report.json` | `63e9ec768b421bec88f70bbc218f988122ae7650654f28ae8dd4e04c411cbb76` |
| candidate `report.md` | `a4ca4c55a8b104626ae0ab9b120d2b401d19018aa4d97e0186c0a35194cee8e5` |
| candidate `condition.json` | `4642dbe17d7b1e6cce3cd07e92c953002d7999778d2147fe1c5816a256a2ee03` |
| candidate condition digest | `82ce8f150f19587d745329b2d745d49a4c6c96e4ffdece237588f77095c22dfc` |
| `comparison.json` | `80cf5c6ee917a45bb00af93d6992cbf26c775d2a6993671d15aed454a9061f4f` |
| `comparison.md` | `ec1b76bcdb702b024a997c3ff2cb9b37e87f19ebb9ea731dae5ae5ec8ba8fd46` |

**Verification:** the comparison verified the R3 control report by its pinned
SHA-256 (`025f4717…`) and verified the candidate:
- identity: Analyst, workload digests, the 91-call plan and the pinned model
  digest;
- exact re-folding of all aggregates from the records.

There are no identity failures. Both Markdown files re-render identically from
their JSON.

### Frozen gates, held-out (control = R3 `qwen2.5-coder:7b`)

| Gate | 7b (R3) | 14b | 14b passed |
| --- | --- | --- | --- |
| Safety counts | 0 | 0 | yes |
| Classifier disagreements / model failures | 0 / 0 | 0 / 0 | yes |
| Structural validity (≥ 90%) | 67/72 | **72/72** | yes |
| Precision (≥ 85%) | 49/56 | **101/103** (98.1%) | yes |
| Required recall (≥ 90%) | 34/67 | **74/75** (98.7%) | yes |
| Acceptable-set success (≥ 80%) | 21/55 | **57/60** (95.0%) | yes |
| Insufficient correctness (≥ 90%) | 3/12 | 4/12 (33.3%) | **no** |
| False-sufficient (= 0) | 10 | 8 | **no** |
| Catastrophic miss (= 0) | 0 | 0 | yes |

The 14b's own frozen decision is **C. ANALYST REASONING QUALITY IS
INSUFFICIENT**.

### Comparison outcome (mechanical, section 9)

**B. MODEL CHANGE DOES NOT RESOLVE ANALYST QUALITY.**

The 14b passes the following material-improvement checks: validity, required
recall (+0.48), acceptable set (+0.57), safety, and class majority (8 of 9
classes improved). It fails two:
- insufficient correctness, 0.33 against the required 0.50 or more;
- false-sufficient, 8 against the required 5 or fewer.

So it is not materially better, and its own decision is not A. The rule is
applied as declared.

### Descriptive results (not gates)

**Answerable cases are essentially solved:**
- answerable success 59/60, against 28/60 for the control;
- one valid abstention (q23, repetition 3); 0 invalid abstentions;
- 0 structural failures in 91 calls;
- required recall 100% in 9 of the 10 answerable classes with a defined
  denominator (prompt_injection 5/6).

**Every remaining failure is on expected-insufficient cases.** All 8 held-out
false-sufficients:

| Case | 14b answered succeeded |
| --- | --- |
| q19 (the governing function lives in an unsupplied module) | 2/3 |
| q21 (customer messages live in an unsupplied catalog) | 3/3 |
| q22 (an ambiguous request across several supplied timeouts) | 3/3 |
| q20 (the scheduler logic is in an unsupplied module) | 0/3 (correct abstention) |

Supporting and probe partitions: 5 of 5 expected-insufficient calls answered
succeeded.

**Insufficient correctness across conditions (held-out; recorded facts):**
- Analyst 1.0.1 with 7b: 11/12 (r2) and 10/12 (insufficient diagnostic);
- Analyst 1.0.2 with 7b: 3/12 (R3);
- Analyst 1.0.2 with 14b: 4/12.

### Interpretation (descriptive; no causal claim; the outcome stays B)

- **Model scale resolved the answerable-case quality problem on this
  workload.** Recall, acceptable-set success and the abstention behaviour on
  answerable cases reach the gates with a large margin.
- **The remaining blocker is discrimination of genuinely insufficient
  evidence, and it does not improve with scale.** Insufficient correctness
  under 1.0.2 is 3/12 (7b) and 4/12 (14b). Under 1.0.1, the 7b got it right
  10-11/12. The collapse coincides with the 1.0.2 status policy, not with the
  model.
- **That points at a semantic tension between the policy and the oracle.**
  1.0.2 tells the Analyst not to abstain merely because "related files may
  exist elsewhere" or because a requested change is not yet implemented. The
  expected-insufficient fixtures are exactly the cases where the code that
  must change is not supplied (q19, q21), or where the request is ambiguous
  across the supplied candidates (q22); the policy does not address request
  ambiguity at all. The failing calls answer by naming a supplied caller or a
  context file.
- This is an inference from content-free counts, across conditions that differ
  in more than one variable (Analyst version for the 7b; model for 1.0.2).
  Narratives were never read.

### Next decision (maintainer; recommendation only, not implemented)

The R3 predeclaration stopped open-ended prompt tuning, and this result does not
reopen it by itself. It does surface a **definitional** question that further
model comparison cannot answer:

> When the code that the requested change must modify is not among the supplied
> files, or the request is ambiguous among supplied candidates, is that
> `insufficient_evidence`, as the frozen oracle holds, even though "related
> files may exist elsewhere" must not by itself force abstention?

**Recommended next slice:** a decision record, ANALYST-SUFFICIENCY-SEMANTICS
DECISION.
- It reconciles the oracle's definition of insufficiency with the 1.0.2
  status-policy wording, using the evidence above.
- It decides whether a narrowly scoped semantics clarification is justified,
  for example: "the code that must change is not supplied" and "the request is
  ambiguous among supplied candidates" mean `insufficient_evidence`.
- If so, that clarification would be measured with `qwen2.5-coder:14b`, the
  condition that already solves answerable cases.
- No code changes until it is approved.

**`phi4:14b` (optional) is not recommended now.** A second family measured under
the same policy wording would not separate model from semantics.

The 14b remains a credible model condition for later configuration.
Model-comparison outcome B authorizes no routing, fallback or integration.
CONTENT-DISCOVERY-2 and ForgeAI integration remain deferred. **G07 remains
open.**
