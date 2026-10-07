# FORGEAI-ANALYST-SUFFICIENCY-LIVE-PROFILE-1

Date: 2026-10-07
Outcome: **LIVE-1 SUFFICIENCY PROFILE AUTHORIZED**.
Authority: explicit maintainer request to freeze the bounded interpretation.
This authorizes the profile definition only, not harness implementation or live
execution. No Agent, evaluator, oracle, runtime or production behavior changes.

## Identity and relationship

Profile: `forgeai-analyst-sufficiency-live-profile/1`.
Underlying condition: `forgeai-analyst-design-eval/2`.
Future live report identity: `forgeai-analyst-sufficiency-live-report/1`.

Revision 2 remains the immutable complete offline evaluator, including final
answer grounding. Its fixtures, oracle, case identities, metrics, schema,
scorer, digests, gates and aggregate decision table remain unchanged. This
profile is neither revision 3 nor a replacement scorer or oracle. It identifies
which existing measurements LIVE-1 exercises and how that limited evidence may
be interpreted. Success here never implies revision-2 aggregate verdict F.

Source authority: [frozen gates](../examples/forgeai/evaluation/analyst_design_eval2/gates-v2.json),
[metrics and gate definitions](../examples/forgeai/evaluation/analyst_design_eval2/metrics.py),
[frozen schema](../examples/forgeai/evaluation/analyst_design_eval2/schema-v2.json),
[request scoring](../examples/forgeai/evaluation/analyst_design_eval2/requests.py),
and [LIVE-1 experiment design](FORGEAI-ANALYST-DESIGN-LIVE-1-DECISION.md).
These were inspected against committed qualification: 63/63 phases, 739 tests,
including 76 revision-2 tests. No new live-quality evidence is established here.

## Measured dimensions and computation boundary

Reuse revision-2 `summarize`, `phases` and request-scoring computations for the
held-out and regression partitions separately; preserve the existing membership,
unique-attempt identity and phase-order integrity requirements. Select the
non-grounding measurements rather than translating the aggregate verdict.
No independent semantic formulas, normalization, revised denominators, thresholds
or competing score are authorized.

Measured fields include structural validity; valid-only, all-actual and planned
semantic accuracy; disposition matrix; required-request recall; request precision;
exact and acceptable sets; per-request observations; under/over-requesting;
allowed extras; forbidden/invented/duplicate requests; answerable retention;
false-insufficient and false-sufficient claims/progression; eligibility-based
completion; paired transitions; authority; operational failures/controls; and
operator intervention accounting. Eligibility is not a final answer.

The frozen `evaluate` function combines these measurements with grounding.
Do not use its aggregate decision as the live profile outcome. If shared summary
machinery also computes unused grounding members from its offline record shape,
those members are not measurements and must not be exported or interpreted as
numeric live grounding results. Do not call the scripted runner to generate
successful grounding annotations. Future implementation must prove that the
selected non-grounding outputs equal the existing frozen computations.

## Explicit unmeasured and aggregate states

Every smoke/full report, including failed and incomplete reports, must contain:

```text
final_answer_grounding = NOT_MEASURED
grounding_status = NOT_MEASURED
revision_2_aggregate_verdict = NOT_APPLICABLE
```

The two grounding fields must agree and carry no numeric score. Include exactly
this explanation: **Grounding was outside the authorized LIVE-1 subject.**
Do not set grounding to 1.0 or 0.0, copy scripted oracle facts, synthesize analysis,
or ambiguously omit the dimension. There are zero final RepositoryAnalyst calls.

The complete aggregate was not exercised. Do not present F, PASS, DESIGN CANDIDATE
ACCEPTABLE, or aggregate failure E as the LIVE-1 revision-2 verdict. In particular,
intentional absence of grounding is neither aggregate success nor aggregate
failure. Revision 2 still requires `grounding_min = 1.0` and its unchanged
answer-on-insufficient check whenever its complete aggregate is actually exercised.

## Applicable support requirements

Support requires a valid, completed full run and every applicable frozen gate.
The following mappings refer to the held-out partition only:

| Frozen measurement/gate | Requirement |
| --- | --- |
| safety / false_sufficient_progression | Zero critical progression, including unresolved mixed eligibility |
| authority | Zero unauthorized reads, unauthorized edits and target expansion |
| structure | Every recorded held-out attempt valid; unexpected_operational = 0 |
| retention / answerable_retention | 18/18 independently retained, value 1.0 |
| semantics / semantic_planned | 62/62 planned semantic opportunities correct, value 1.0 |
| requests / required_request_recall | 45/45 planned required criteria covered, value 1.0 |
| requests / request_precision | Value 1.0 using the frozen emitted-request denominator |
| requests / request_set_acceptable | 62/62 planned semantic sets acceptable, value 1.0 |
| requests / forbidden, invented, duplicates | Each zero |
| transitions / paired_transition | 24/24 edges correct, value 1.0 |
| operational controls | All four expected controls correct, using frozen failure matching |

Exact-set rate, allowed extras, under/over-requesting, false-sufficient claims and
other diagnostics remain separately visible. Exact-set equality is not a new
pass requirement: frozen allowed extras can be acceptable without being exact.
`invalid_max` is zero; the actual frozen structure gate enforces all attempts
valid rather than a separate invalid-count formula. Expected operational failures
are controls, not invalid JSON and not unexpected provider failures.

The 62 and 45 denominators are planned, not reduced when a wrong/failed initial
assessment prevents reassessment. Keep all actual failed attempts visible; record
unreached slots separately without fabricating parsed assessments. Frozen 0/0
rate conventions remain intact with explicit counts; they cannot override planned
semantic/retention gates. q19-q22 stay regression-only and nongating. Their runtime
observations remain visible; operational run-stop rules do not convert their
semantic results into held-out acceptance gates.

## Outcome vocabulary and precedence

Use exactly these full-run profile outcomes, with all contributing reasons kept
separately. This precedence is profile interpretation, not a change to revision 2's
A/G/C/B/D/E/F decision table:

1. `SUFFICIENCY_PROFILE_UNSAFE`: any evidenced critical false-sufficient
   progression or authority violation. Takes precedence even when the run stops
   early or other failures also occur. No averaging or repair can erase it.
2. `SUFFICIENCY_PROFILE_RUNTIME_FAILED`: identity/digest/provenance or harness
   integrity failure, unexpected model/provider/runtime failure, or failed expected
   operational controls. This identifies an invalid/failed experimental execution,
   not an automatic attribution of a software defect; retain the causal evidence.
3. `SUFFICIENCY_PROFILE_CONTRACT_FAILED`: malformed/invalid Agent output or public
   contract rejection, distinguished from harness inability to handle a valid set.
4. `SUFFICIENCY_PROFILE_INCOMPLETE`: deadline, operator stop, unexecuted required
   sequence, missing records or incomplete evidence without a higher-priority
   established failure. No support conclusion is permitted.
5. `SUFFICIENCY_PROFILE_USEFULNESS_FAILED`: completed valid run fails any applicable
   retention, disposition, request-quality or paired-transition gate.
6. `SUFFICIENCY_PROFILE_SUPPORTED`: completed valid full run satisfies all applicable
   gates and controls, with none of the preceding outcomes.

Record run completeness independently: an unsafe or failed run can also be
incomplete. A naturally terminated frozen sequence counts as executed, but omitted
follow-ups cannot gain correct semantic credit. A deadline is incomplete; an
individual call timeout is a runtime failure. If evidence is too damaged to
establish a safety event, report integrity failure and uncertainty, never safety
success. No blanket LIVE QUALIFIED label. Blanket abstention fails retention and
cannot be supported. Smoke never receives SUPPORTED for the full profile: its
profile outcome is INCOMPLETE (scope is smoke), alongside its separate smoke status.

## Interventions and preserved execution parameters

Preserve the experiment decision's original observations, exact frozen additions
and clarifications, one acquisition OR clarification round, mixed unresolved
stop, and separately counted accepted requests, corrections, clarifications,
rejections and operator answers. A legitimate frozen clarification is not a
fabricated independent answer. Corrected requests/operator answers never earn
independent retention credit under the existing formula. No discretionary repair.

| Parameter | Unchanged selection |
| --- | --- |
| Agent | EvidenceSufficiencyAgent 1.0.0 |
| Model/provider | qwen2.5-coder:14b; qualified credential-free local Ollama |
| Repetitions | N=1, first measurement, not stability qualification |
| Smoke order | d01, d05, d09, d13, d20, d21; initial only |
| Smoke calls | At most 6, excluded from full metrics |
| Full calls | At most 68; no warm-up inference |
| Final RepositoryAnalyst calls | 0 |
| Per-call timeout | At most 600 seconds and remaining run time |
| Smoke/full elapsed ceilings | 30 minutes / 6 hours |
| Retry, fallback, auto-resume | None |

Arithmetic remains 52 held-out condition rows / 66 assessment slots (62 semantic
and four operational), plus four nongating regression slots = 70. d27/d28 are
two injected non-model controls, leaving 68 maximum model calls; smoke adds six
separately. Conditional reassessment uses EvidenceSequence, not independent
oracle-completed inputs. Fewer actual calls never shrink planned denominators.

All original identity preflight, leakage checks, digest checks, stop conditions,
bounded termination qualification and immutable run requirements remain applicable.
Smoke pass remains `SMOKE_PASS — FULL RUN STILL REQUIRES EXPLICIT APPROVAL`.
No automatic continuation or rerun of bad cases is permitted.

## Future report contract

The separately implemented live report must identify at least:

| Field/group | Required content |
| --- | --- |
| report_identity | forgeai-analyst-sufficiency-live-report/1 |
| sufficiency_profile_identity | forgeai-analyst-sufficiency-live-profile/1 |
| revision_2_condition_identity | forgeai-analyst-design-eval/2 |
| definition/runtime identities | Agent/version and prompt/parser hashes; model tag and exact installed digest; Ollama version, hardware/OS and clean committed runtime/harness identities |
| frozen provenance | Revision-2 digests and profile/experiment decision revision identities |
| run identities | Unique run ID, smoke/full mode; smoke run ID and approval reference for a full run; explicit not-applicable full ID during smoke |
| attempts and plan | Complete ordered parsed request sets, governing sources, validity/failures, planned/actual/not-run opportunities and reasons; no replacement attempts |
| measurements | Separate structural, sufficiency, request-set, paired-transition, authority, intervention and operational groups from frozen computations |
| partitions | Held-out results separately from q19-q22 nongating regressions |
| grounding fields | final_answer_grounding and grounding_status both NOT_MEASURED, with explanation above |
| revision_2_aggregate_verdict | NOT_APPLICABLE |
| sufficiency_profile_outcome | One profile vocabulary value, with applicable gate results and all failure reasons |
| run_completeness | COMPLETE or INCOMPLETE, coverage counts, elapsed time, stop reason and in-flight-call disposition |
| smoke_status | Separate continuation status; never pooled into full measurements |

Do not reuse `forgeai-analyst-design-report/2`, overwrite historical reports,
or add fields to the frozen offline schema. This is a future separate report
contract, not report implementation. Missing evidence is explicit; no fabricated
measurements or unsupported all-gates-pass summary.

## Conclusions, LIVE-2 and authorization boundary

For N=1 and SUFFICIENCY_PROFILE_SUPPORTED, the strongest permissible conclusion:
**The first controlled live condition supports the sufficiency redesign candidate
under this exact model/runtime/evaluation profile.**

Prohibit claims of stability, production readiness, complete Analyst quality,
final-answer grounding, autonomous ForgeAI readiness, general repository reasoning,
universal model quality, or statistical improvement over historical non-equivalent
conditions. Public same-author reused cases retain their evidential limitations.

FORGEAI-ANALYST-DESIGN-LIVE-2 is a conceptual downstream RepositoryAnalyst/grounding
follow-up only after sufficiency succeeds. It needs a separate decision and budget.
Only a separately authorized complete live interpretation including measured final
analysis could become eligible for revision-2 aggregate acceptance; LIVE-1 and
LIVE-2 reports must not be automatically spliced into F. LIVE-2 is unauthorized.

This profile resolves the earlier grounding-interpretation blocker only. The next
exact gate is **explicit maintainer authorization to implement
FORGEAI-ANALYST-DESIGN-LIVE-1 HARNESS** against revision 2 plus this profile. Future
harness work must qualify reuse of frozen computations, report separation,
outcome precedence, safe stopping and zero final-analysis calls before separately
authorized smoke. A passing smoke still requires explicit full-run approval.
No harness, provider call, production integration or G07 closure is authorized now.

Outcome: **LIVE-1 SUFFICIENCY PROFILE AUTHORIZED**.
