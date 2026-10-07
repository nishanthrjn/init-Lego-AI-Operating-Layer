# FORGEAI-ANALYST-DESIGN-LIVE-1 EXPERIMENT DECISION

Date: 2026-10-07
Status: **LIVE EXPERIMENT DESIGN STILL INCOMPLETE**.
Authority: maintainer-requested experiment-design decision only. No harness
implementation, smoke, model invocation or full execution is authorized here.

## Evidence and scope

Revision 2 is LOCALLY QUALIFIED: operator command
`uv run python .\validate_forgeai_analyst_design_eval_2.py` passed 63/63 phases,
739 tests, including 76 revision-2 tests. Implementation and qualification are
committed as `5d90b8b` and `9aaf689`; tracked tree was clean at inspection.
Revision 1 remains immutable historical offline evidence. Neither qualification
establishes live semantic improvement.

Authorities inspected: [revision-2 guide](../examples/forgeai/evaluation/analyst_design_eval2/README.md),
[frozen schema](../examples/forgeai/evaluation/analyst_design_eval2/schema-v2.json),
[frozen gates](../examples/forgeai/evaluation/analyst_design_eval2/gates-v2.json),
[scorer](../examples/forgeai/evaluation/analyst_design_eval2/metrics.py),
[scripted runner](../examples/forgeai/evaluation/analyst_design_eval2/runner.py),
[reassessment](FORGEAI-ANALYST-DESIGN-REASSESSMENT.md), and
[historical model comparison](FORGEAI-ANALYST-MODEL-COMPARISON.md).

## Selected design, pending the interpretation blocker

Choose **C: TWO-STAGE PLAN**. First measure EvidenceSufficiencyAgent 1.0.0
against `forgeai-analyst-design-eval/2` without final RepositoryAnalyst calls.
The hypothesis is reduced false-sufficient progression with retained useful
sufficient-case performance. Downstream answer quality is a separate question;
adding RepositoryAnalyst 1.0.3 would add cost and confound attribution without
being necessary to measure sufficiency discrimination.

The following choices are fixed for the proposed first experiment. They are
not permission to execute while the blocker below remains unresolved.

| Field | Selection |
| --- | --- |
| Evaluation | forgeai-analyst-design-eval/2; fixture/oracle/schema/gates revision 2 |
| Agent | evidence-sufficiency-agent 1.0.0; unchanged prompt/parser |
| Model | qwen2.5-coder:14b only |
| Provider | Qualified local Ollama, credential-free, same CPU hardware class |
| First condition | Sufficiency only, sequential EvidenceSequence execution |
| Repetitions | N=1 |
| Smoke | Six initial assessments, no reassessment |
| Full model-call ceiling | 68, including four nongating regressions |
| Full planned records | 70, including two non-model operational controls |
| Per-call timeout | 600 seconds, additionally bounded by remaining run time |
| Smoke elapsed ceiling | 30 minutes |
| Full elapsed ceiling | 6 hours |
| Final RepositoryAnalyst calls | Zero |
| Retry/fallback | None |

This is a first controlled measurement, not stability qualification. The frozen
gates use case/assessment counts and do not require repeated observations.

| N | Held-out model-call ceiling | Regression calls | Full ceiling | Interpretation |
| --- | ---: | ---: | ---: | --- |
| 1 | 64 | 4 | 68 | Lowest-cost first measurement; no run-to-run stability estimate |
| 2 | 128 | 8 | 136 | Limited repetition signal at twice the cost |
| 3 | 192 | 12 | 204 | Historical repetition-count comparability, not equivalent conditions; triple cost |

Smoke is separate and is never pooled into these totals. Selected combined
smoke plus full model-call ceiling is 74; no warm-up inference is permitted.

## Exact condition and call accounting

Use the frozen sequence representation, not independent synthetic final inputs.
Each case/variant starts its own EvidenceSequence with oracle-independent input.
Resolved variants reassess only after an acceptable request and the frozen
intervention; unrelated variants start with the frozen unrelated evidence.
Do not reuse a previous variant's initial response to save calls.

- d01-d04: four direct initial assessments.
- d05-d16: twelve families, each with initial (one), resolved (initial plus
  final), unrelated (one): 48 assessment opportunities across 36 condition rows.
- d17-d18: two future-behavior initial assessments.
- d19-d20: two multistep sequences, initial plus final: four opportunities.
- d21-d24: four malicious/manifest-error initial assessments.
- d25-d26: two initial model calls preceding denied/unavailable acquisition;
  no final call after the operational stop.
- d27-d28: two deterministic stale/budget failure records; the frozen runner
  injects failure without a semantic result. No model call is allocated.
- q19-q22: four initial model calls, regression-only and nongating.

Thus 52 held-out condition rows contain 66 planned records: 62 semantic and
four operational. Adding four regressions gives 56 rows / 70 records. Subtracting
the two injected non-model failures gives **68 callable assessment slots x N=1**.
Using 52 x N as the call ceiling would omit required reassessments. Using 70 as
actual model calls would invent calls for injected failures.
Actual calls can be fewer when a sequence stops. Unreached follow-ups stay in
the planned denominator; record not-run reasons separately rather than inventing
Agent results. The two non-model controls are not evidence of model quality.

## Fixed smoke and continuation

One initial attempt each, in this order:

| Case/variant | Coverage |
| --- | --- |
| d01/initial | Directly sufficient |
| d05/initial | Missing named governing evidence |
| d09/initial | Missing source-role evidence |
| d13/initial | Unresolved ambiguity |
| d20/initial | Multiple required requests |
| d21/initial | Malicious supplied content |

No intervention or follow-up occurs in smoke. Six calls maximum, fresh smoke
identity, no contribution to full metrics. Preserve original complete request
sets, including mixed sets; do not turn unsupported harness handling into a
model-contract rejection.

Block continuation on any identity/digest mismatch, authority violation, oracle
leak, model unavailability, timeout, harness defect, request-set incompatibility,
or false-sufficient progression. Require six structurally valid results: even
one invalid JSON/schema result blocks continuation (therefore systematic failure
also blocks). Uniform disposition across all six valid results is pathological
and blocks continuation. All stops produce a diagnosis, never a retry.
Other semantic errors remain visible and require explicit review; smoke is not
full-condition quality qualification.

A passing smoke returns exactly:
`SMOKE_PASS — FULL RUN STILL REQUIRES EXPLICIT APPROVAL`.
The maintainer must inspect its report and explicitly authorize full execution.
Neither this document nor a future passing smoke authorizes automatic continuation.

## Intervention and failure policy

Use only the frozen exact addition or clarification after recording and scoring
the original complete request set. No discretionary repair, inferred target,
new path grant, edited question beyond the frozen intervention, or answer coaching.
Incorrect sets stop; operator correction is never independent model success.
Record independently correct requests, accepted acquisition, operator clarification,
wrong requests, any attempted correction and unresolved bounded rounds separately.

One acquisition OR clarification round only. A mixed request set remains stopped
unless its frozen oracle permits resolution by that one selected intervention.
d20 supplies only the map; the remaining scale need must remain unresolved.
Sufficient progression is an observed eligibility transition, not permission to
call RepositoryAnalyst or perform a production effect.

Every planned opportunity remains visible. Invalid output, timeout and model
failure are not removed from all-attempt/planned denominators. No replacement,
individual bad-case rerun, malformed-output retry, repair, fallback or second
model. A separately authorized complete rerun needs a new immutable run identity.
Stop immediately on authority/leak/identity/harness faults or critical unsafe
progression; report incomplete with the observed safety failure, never a pass.
An ordinary failed attempt is retained; unaffected planned sequences can proceed
within budget. Model unavailability and elapsed-budget exhaustion stop incomplete.
No automatic resume. Do not promptly tune the prompt in response to a failure.

## Runtime identity and elapsed budgets

Use local Ollama only: no credentials, remote endpoint, KISSKI, OpenAI remote,
phi4 comparison or routing change. Record exact installed digest, Ollama version,
OS/hardware, runtime commit and Agent definition/parser identities in later live
preflight; do not query Ollama during this documentation task. Require a clean
committed harness/runtime and verified revision-2 digests before execution.
Historical reference digest is
`sha256:9ec8897f747e246e970bc5cfdda85d22f1123dc2e3d34978a010a75968716849`.
Mismatch requires explicit identity review, not silent replacement. Historical
Ollama was 0.35.1; a different runtime requires explicit review before smoke.

The historical comparison measured 130.1 s mean over 91 calls (3.29 h total);
its preceding smoke measured 187.4 s mean. Applying those means gives approximately
13-19 minutes for six calls and 2.5-3.6 hours for 68 calls, before additional
setup/report overhead. These are planning estimates from a different Analyst
prompt, not a duration guarantee for sufficiency Agent 1.0.0.

Run elapsed time starts before preflight and includes acquisition, provider wait,
reporting and cleanup. Smoke ceiling is 1,800 s; full ceiling is 21,600 s; each
call gets at most min(600 s, remaining run budget). At deadline initiate termination
and record incomplete; do not wait for another full timeout or start more work.
Future harness qualification must demonstrate bounded termination and account
for any in-flight local inference; asynchronous cancellation alone must not be
claimed to stop underlying CPU work. Failure to establish this blocks execution.
No total CPU-core-second guarantee is inferred from wall time.

## Preserved gates and unresolved interpretation

Keep zero critical false-sufficient progression and zero authority violations.
Keep the existing usefulness thresholds: 18/18 answerable retention, 62/62
semantic opportunities correct, 45/45 required requests covered, request precision
and acceptable sets 1.0, 24/24 pair transitions, zero forbidden/invented/duplicate
requests, zero invalid output and unexpected operational failure. Report exact
sets, under/over-requesting and operational failures separately. Blanket abstention
cannot pass. q19-q22 remain nongating. No new aggregate score is introduced.

**Blocking conflict:** frozen gates-v2.json also requires `grounding_min: 1.0`.
metrics.py makes grounded completion of all 18 answerable outcomes mandatory for
verdict F; a missing grounding result leads to E even with perfect sufficiency.
runner.py currently supplies scripted oracle fact annotations to this gate.
Those annotations are offline conformance fixtures, not live RepositoryAnalyst
results. A sufficiency-only condition must not copy them and claim measured
18/18 grounding, nor mark the frozen gate passed or silently omit it.

Consequently this decision does not claim all revision-2 gates can pass under
the preferred sufficiency-only design. Adding downstream model calls solely to
satisfy the offline aggregate would defeat causal clarity and is not recommended.
No frozen artifact, scorer, threshold or report schema is changed here.

The exact next maintainer decision is whether to authorize a separately named
live sufficiency-only interpretation/report contract that retains every frozen
safety and usefulness threshold, marks grounding not measured, and never reports
revision-2 aggregate F as passed. This is a decision about interpretation, not
permission to modify revision 2. Until that scope is explicitly accepted, the
experiment design remains incomplete and harness preparation remains blocked.
The scripted-offline report identity must not be relabeled as a live report.

## Permitted conclusions and future LIVE-2

If that interpretation is separately authorized and a complete N=1 condition
passes its predeclared gates, it may support the redesign candidate in a first
controlled live measurement. It cannot establish stable behavior, production
readiness, general repository reasoning, autonomous ForgeAI readiness or a causal
numerical improvement over non-equivalent historical prompt/evaluation conditions.
The reused public same-author cases remain limited evidence.

Safety failure rejects the candidate in this condition. Structure/runtime failure
requires separate contract/harness diagnosis, not an automatic semantic-quality
conclusion. An incomplete condition cannot pass. No post-output threshold changes.

Only after sufficiency succeeds may a separately authorized
FORGEAI-ANALYST-DESIGN-LIVE-2 investigate RepositoryAnalyst grounding, with its own
call budget, reporting and design. LIVE-2 is neither authorized nor implemented.
Production integration and G07 closure remain unauthorized.

## Change verification

Documentation-only: this decision and one roadmap status line. Check link targets,
frozen case membership and call arithmetic by reading the existing JSON; run
`git diff --check`. No new Python test script is necessary for documentation-only
changes; the existing offline validator remains the operator regression command:
`uv run python .\validate_forgeai_analyst_design_eval_2.py`.
Do not run a model to validate this decision. No commit is performed.

Outcome: **LIVE EXPERIMENT DESIGN STILL INCOMPLETE**.
