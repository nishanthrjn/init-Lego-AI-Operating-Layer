# ANALYST-ABSTENTION-DECISION-1: smallest justified next RepositoryAnalyst experiment

Status: decision record (2026-10-05). No production code, prompt, parser, model,
threshold, oracle or evidence change. No live run.

## 1. Evidence summary

Both runs used the same frozen condition:
- RepositoryAnalyst 1.0.1, fingerprint `f99564e6…2cc0`;
- `qwen2.5-coder:7b` `sha256:dae161e2…f4364`;
- the 1Q workload: 91 calls, 72 held-out, N = 3.

| Measurement | CONTENT-DISCOVERY-1Q-R2 (`2e8f1ab`) | ANALYST-INSUFFICIENT-DIAG-1 (`fa4aa8f`) |
| --- | --- | --- |
| Structurally valid, held-out | 59/72 | 60/72 |
| Field-set failures | 0 | 0 |
| `insufficient_inconsistent` | 13 (12 held-out) | 12 (all held-out) |
| Refined clause | not recorded | `insufficient_findings_present` 12/12 |
| Non-JSON | 1 | 0 |
| Answerable held-out → succeeded (valid) | 13/60 | 17/60 |
| Answerable held-out → valid abstention | 34/60 | 31/60 |
| Answerable held-out → invalid abstention | 12/60 | 12/60 |
| Expected-insufficient held-out → insufficient | 11/12 | 10/12 |
| Integrity (model failures, disagreements, inconsistencies) | 0 | 0 |
| Decision | B (validity < 90%) | B (abstention requires a quality decision) |

**Verification:**
- The DIAG-1 counts were re-derived from its 91 records: per class (section 4)
  they sum to 17 / 31 / 12.
- The r2 per-class counts below were re-derived from the r2 records.
- Neither raw report is still present locally, so both were verified from the
  report contents supplied by the operator and the recorded digests:
  r2 `e5a0efd3…`; DIAG-1 `09c096a7…`.

**Answerable-success rate** (expected `succeeded`, actual `succeeded`,
structurally valid; descriptive, not a gate):
- r2: 13/60 (21.7%);
- DIAG-1: 17/60 (28.3%).

## 2. Two separate problems

**Problem A: structural.** Some `insufficient_evidence` replies still carry
findings. That is 12 of 60 answerable held-out calls in each run, always one or
two findings, and `unknowns` was never empty. This failure costs validity only.

**Problem B: behavioral.** The model chooses `insufficient_evidence` on
answerable cases: 46/60 (r2) and 43/60 (DIAG-1), counting valid and invalid
abstentions together. Most of these, 34 and 31, satisfy the contract
completely.

These are separate:
- Fixing A at best turns 12 invalid abstentions into valid abstentions or
  answers. That raises validity but not the answer rate.
- B exists even among perfectly valid replies.

No single change is claimed to solve both.

## 3. Intended semantics of `insufficient_evidence`, and the current guidance

**What the sources say:**
- **Schema rule** (`values.py`, `api.py`, Engineering README): an
  insufficient-evidence result requires at least one unknown and no findings.
  The same status is also used, without a model call, for acquisition failure
  (DENIED, UNAVAILABLE, BOUNDARY or BUDGET).
- **M8.1 plan, item 12:** "Uncertainty: explicit unknowns and insufficient-evidence
  outcome". It names the outcome but does not define when to choose it.
- **1Q predeclaration:** the measured question is whether the Analyst can
  "identify which supplied files are relevant to understanding or implementing
  the requested change". Relevance is not editability.

Taken together, the intended **decision policy** is that `insufficient_evidence`
means the supplied files are not enough for a defensible analysis. It does not
mean residual uncertainty, an unimplemented requested change, or an incomplete
view of the wider repository. That reading is consistent with every source.
**No source states it.**

**What the RepositoryAnalyst 1.0.1 SYSTEM guidance says:**

| Topic | Current guidance | Gap |
| --- | --- | --- |
| When to use `succeeded` | Only "status is succeeded or insufficient_evidence" | No criterion |
| When to use `insufficient_evidence` | Only its shape: "at least one unknown and no findings" | No criterion |
| Partial evidence | Not addressed | Unclear whether any gap forces abstention |
| Uncertainty with `succeeded` | Not stated (the parser allows unknowns and risks with `succeeded`) | The model is not told that uncertainty can coexist with an answer |
| Risks, unknowns | Defined as fields: risks "supported by the supplied evidence", unknowns "relevant unresolved or missing evidence" | No link to the status choice |
| Findings | "Every finding must cite supplied paths" | No link to status |
| relevant_files | "at most 8 distinct supplied paths" | It is not said that identifying them is the answer |
| Framing | "Identify uncertainty; do not claim contents of files not supplied"; "Narrative is a hypothesis" | Pushes toward caution with no counterweight |
| Change-request questions | Not addressed | It is not said that a requested change missing from the code is not missing evidence |

**Conclusion:** the guidance defines the shape of each status but gives no
policy for choosing between them. The ambiguity is material. Problem A is itself
a symptom of this: in 12/12 invalid replies the model produced findings, which
by the intended semantics means it had an answer, yet it declared insufficiency.

## 4. Per-class abstention (answerable held-out cases, content-free metadata)

DIAG-1 (`fa4aa8f`), each class 6 calls unless noted:

| Class | Calls | Succeeded | Valid abstention | Invalid abstention |
| --- | --- | --- | --- | --- |
| opaque_names | 9 | 2 | 7 | 0 |
| renamed_replacement | 6 | 3 | 3 | 0 |
| interface_impl | 6 | 0 | 4 | 2 |
| source_test | 6 | 3 | 2 | 1 |
| multi_file | 9 | 2 | 6 | 1 |
| misleading_names | 6 | 2 | 3 | 1 |
| context_only | 6 | 3 | 0 | 3 |
| irrelevant_plausible | 6 | 2 | 2 | 2 |
| prompt_injection | 6 | 0 | 4 | 2 |
| **Total** | **60** | **17** | **31** | **12** |

The r2 run gave the same totals (13 / 34 / 12, plus 1 non-JSON reply):
- opaque_names 3 / 5 / 1;
- renamed_replacement 2 / 3 / 1;
- interface_impl 1 / 4 / 1;
- source_test 1 / 3 / 2;
- multi_file 2 / 6 / 0;
- misleading_names 1 / 5 / 0;
- context_only 1 / 1 / 4;
- irrelevant_plausible 2 / 2 / 2;
- prompt_injection 0 / 5 / 1.

**Pattern:**
- Abstention is **broad**: every one of the 9 answerable classes abstains in
  at least half of its calls in both runs.
- It is **case-stable**:
  - 8 of the 20 answerable cases abstained in all 6 samples across both runs:
    q04, q07, q11, q12, q14, q16, q23, q24.
  - `q16` was an invalid abstention 6/6.
  - Trivially answerable `q01`, a one-constant edit in a 3-file, 290-byte
    subset, was answered in only 1 of 6 calls.

That is not the signature of a specific reasoning class (for example misleading
names) or of evidence scarcity.

**Contrast:** expected-insufficient cases abstain correctly 21/24 across the two
runs, so the policy the model applies errs toward abstaining.

## 5. Evidence-sufficiency audit (committed `heldout-v1.json`)

**Construction:** `data.validate` enforces that the required files, every
acceptable set and every context file are contained in the supplied subset. The
oracle classes partition the supplied files exactly. The subsets were confirmed
as complete for every answerable case.

**Size:** 226–1,037 bytes per answerable case (106–1,037 across all 24 cases),
far below the 24,576-byte aggregate bound. 2 to 4 files each. No truncation.

**Per case:** each required file visibly contains the code the question
concerns:
- q01 `LATE_FEE_PER_DAY = 0.25`;
- q11 `Invoice` and its `render`;
- q12 the `authenticate` failure branch, with `audit.warn` supplied;
- q14 the `EMAIL` regex in `forms/fields.py`;
- q16 `report_days` filtering weekends;
- the same holds for the others.

No answerable case needs an unsupplied file or a recursive read.

**Contradictions and decoys** are deliberate and resolvable from the supplied
text:
- q04 `rates_old.py` says it was replaced by `tariffs.py`;
- q05 `naming.py` says it is no longer imported;
- q13, q14 and q17 use misleading names;
- q23 and q24 contain injected instructions.

**Flags.** Not unanswerability, but noted:
- q11 and q12 request **new behavior** (a currency code; an audit warning). The
  relevant files exist, but the requested behavior does not. A model reading
  insufficiency as "the evidence lacks the requested behavior" will abstain;
  both abstained 6/6.
- q03, q06 and q10 need modest cross-file reasoning, with acceptable sets
  covering the defensible alternatives.

No fixture is judged unanswerable under its supplied subset, and the oracle is
not changed.

**Conclusion:** the evidence subsets are adequate. Abstention does not
correlate with missing or context-poor evidence.

## 6. Candidate experiments

| Candidate | Addresses B (dominant)? | Addresses A? | Isolates causality | Scope and cost | Evidence supports it now? |
| --- | --- | --- | --- | --- | --- |
| A. Narrow contract clarification only | No: at most 12/60 | Yes | Yes | Smallest | The rule is already stated verbatim in 1.0.1 and still violated; rewording alone is weakly motivated |
| B. Sufficiency-policy prompt clarification | Yes: targets the missing decision policy | Partly: replies with findings should become `succeeded` | Yes, if only the guidance changes | Small: version bump; reuse r2/DIAG harness; 91 calls (~1.2 h local) | **Yes**: material ambiguity (section 3), broad case-stable abstention (section 4), adequate evidence (section 5) |
| C. Model comparison | Possibly | Possibly | Only if the policy is clear; today it would conflate calibration with ambiguity | No stronger model installed (only qwen2.5-coder 1.5b/3b/7b and llama3.2); a 14b+ pull adds unmeasured hardware/time cost | **No**: the section-10 threshold (policy already clear) is not met |
| D. Evidence-design experiment | Unlikely | No | Yes | Needs a new frozen evidence condition | **No**: subsets are complete and tiny; no correlation with missing context |

Rejected here, and kept out of every candidate:
- allowing findings under `insufficient_evidence`;
- making `unknowns` optional;
- lowering any gate;
- retries or repair;
- changing the oracle;
- combining a prompt change with a model or evidence change.

## 7. Selected next experiment

**ANALYST SUFFICIENCY-POLICY PROMPT EXPERIMENT JUSTIFIED.** All three conditions
of the prompt-change threshold hold:
1. the current guidance is materially ambiguous about when to abstain;
2. the observed abstention is broad and consistent with that ambiguity;
3. the evidence subsets on expected-succeeded cases are adequate.

Caveat: the link between the ambiguity and the behavior is an inference from
content-free counts; narratives were never read. The experiment tests it. If
abstention persists under a clear policy, the next candidate becomes the model
comparison (C), now with its threshold met.

## 8. Structural-fix disposition

**INCLUDE WITH NEXT PROMPT REVISION.**
- The `insufficient_evidence` ⇒ `findings = []`, `unknowns` non-empty rule is
  part of the same status policy. Stating it next to the sufficiency criterion
  completes that policy: if findings answer the question, choose `succeeded`.
- It changes no semantics.
- It stays separately measurable through the DIAG-1 refined clause counts.

Rule A alone (narrow fix only) is not justified as the primary experiment:
1.0.1 already states it.

## 9. Risks

**Over-correction toward false sufficiency.** Expected-insufficient cases are
already answered 3/24 times across the two runs. The frozen gates guard this:
insufficient correctness ≥ 90% and false-sufficient = 0.

**Run-to-run variance at N = 3.** Answerable success was 13 vs 17 under the
same condition. Single-run differences of a few calls are not evidence.

**Fixture overfitting.** The guidance must be generic Analyst policy:
- no ForgeAI, fixture or class wording;
- no examples drawn from the held-out cases;
- held-out cases are synthetic and from the same author.

**Other risks:**
- **Prompt budget:** the system prompt plus 32,768 must stay ≤ 49,152 bytes;
  this is tested.
- **Injection resistance** must not regress; the q23/q24 safety counts must stay 0.
- **A clear policy may still not move a 7b model.** That outcome is
  informative: it would justify C.

## 10. Exact next-slice recommendation

**ENG-ANALYST-SUFFICIENCY-PROMPT-1** (production definition only; separately
approved). The wording is not written here.
- RepositoryAnalyst 1.0.1 → 1.0.2. AgentId, public API, parser, `values.py`,
  bounds, membership, the ADR-021 decoder, provider and runtime are unchanged.
- The generic SYSTEM guidance gains a status decision policy:
  - `succeeded` when the supplied evidence supports a defensible analysis of
    the question, including identifying the relevant supplied files, even
    though uncertainties remain;
  - uncertainties go in `risks` and `unknowns`, not the status;
  - `insufficient_evidence` only when missing evidence prevents that analysis;
  - a requested change or behavior that does not yet exist in the code is not
    missing evidence;
  - restating the existing rule: with `insufficient_evidence`, `findings` is `[]`
    and `unknowns` is non-empty.
- Tests: request-level SYSTEM/USER checks, the parser regressions, and the
  existing six-field and shape tests.
- Frozen-history pins follow the same pattern as ENG-ANALYST-PROMPT-1: r2 and
  DIAG-1 refuse to sample 1.0.2.

**Then, after local qualification and commit: CONTENT-DISCOVERY-1Q-R3.** A new
condition that pins 1.0.2 and reuses unchanged:
- the frozen cases, oracle, partition, thresholds, N = 91, model and digest,
  and the decision rule;
- the r2 harness pattern;
- the DIAG-1 refined clause counts.

It also reports:
- answerable-success rate, descriptively and with no new gate;
- the status-against-expected confusion;
- valid and invalid abstention.

The comparison with 1.0.1 uses the recorded r2 and DIAG-1 references only.

**Authority is unchanged:**
- exact confirmed evidence;
- read and governed Chat only;
- no mutation or checks authority;
- no target authorization;
- no ForgeAI worker integration.

## 11. Roadmap and G07

- **G07** (evaluated understanding/discovery quality) **remains open**. No
  quality gate has been met; validity is still below 90% and relevance quality
  is unmeasured as decision evidence.
- This decision narrows the blocker from output formatting to the Analyst's
  status decision policy.
- **CONTENT-DISCOVERY-2 and ForgeAI integration remain deferred.**

## 12. Implementation status: ENG-ANALYST-SUFFICIENCY-PROMPT-1 (2026-10-05)

The decision was approved and implemented: RepositoryAnalyst 1.0.1 → 1.0.2,
changing only the instruction text and version in `analyst/api.py`. Local
validation is pending.

**Added generic status decision policy:**
- **succeeded:** sufficient evidence for a defensible analysis; this is not
  certainty, and uncertainty goes in `risks` and `unknowns`.
- **insufficient_evidence:** only when missing evidence prevents a defensible
  analysis. It is not chosen for limited repository visibility, residual
  uncertainty or risk, possible unseen related files, or a not-yet-implemented
  requested change.
- **Existing rule, restated:** `findings = []` and a non-empty `unknowns` under
  `insufficient_evidence`; findings that answer the question mean `succeeded`.
  This is the section 8 disposition: INCLUDE WITH NEXT PROMPT REVISION.

**Unchanged:**
- the parser, values, schema, bounds, membership and the ADR-021 decoder;
- the model, provider and sampling;
- the evidence and the runtime.

**Pinned history:** the r2 and DIAG-1 live commands refuse 1.0.2; their tests
assert the pinned 1.0.1 identity.

**No live benefit is claimed.** CONTENT-DISCOVERY-1Q-R3 is required next and is
not implemented here. It reuses unchanged the frozen gates:
- safety 0 and classifier disagreements 0;
- model failures ≤ 10%;
- validity ≥ 90%;
- precision ≥ 85%;
- required recall ≥ 90%;
- acceptable set ≥ 80%;
- insufficient correctness ≥ 90%;
- false-sufficient 0 and catastrophic 0.

It reports descriptively, with no new gate:
- answerable-success rate;
- valid and invalid abstention;
- the expected-vs-actual status confusion;
- the insufficient-evidence clause counts.

Over-correction toward false success on expected-insufficient cases is the main
risk, and the insufficient-correctness and false-sufficient gates guard it.
