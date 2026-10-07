# ForgeAI Analyst design reassessment after CONTENT-DISCOVERY-1Q-R4

Date: 2026-10-07. Status: **recommendation ready; no implementation authorized**.
Inspected HEAD: `836596f`. The tracked tree was clean before this change.

Primary direction: **SEPARATE SUFFICIENCY + BOUNDED EVIDENCE ACQUISITION RECOMMENDED**.

The supported diagnosis is a combination of task/contract coupling, unverified
sufficiency classification and a missing operator-visible acquisition or
clarification step. R4 does not establish the model's internal cause, prove that
two calls will solve it, or justify another prompt experiment. No Analyst 1.0.4,
model change, live run, Workflow or Team is proposed. Secret/transport work stays
deferred; credentialed providers, REMOTE and KISSKI remain unauthorized.

## 1. Evidence and history

Inspected the current [Analyst API/definition/parser](../packages/legoai-engineering/src/legoai_engineering/analyst/api.py),
[values](../packages/legoai-engineering/src/legoai_engineering/analyst/values.py),
[authorized evidence reader](../packages/legoai-engineering/src/legoai_engineering/analyst/authorized.py),
[ADR-018](../adrs/ADR-018.md), [M8.1 record](M8.1-REPOSITORY-ANALYST-PLAN.md),
[structure interfaces](../packages/legoai-engineering/src/legoai_engineering/repository/structure.py),
[Agent contracts](../src/legoai/execution/agent/ports.py),
[one-step runtime](../src/legoai/reference/agent.py),
[ForgeAI worker](../examples/forgeai/src/forgeai/worker.py), and
[master roadmap](LEGOAI-FORGEAI-MASTER-ROADMAP-2026.md).

Evaluation evidence includes the committed records below, frozen
[held-out cases](../examples/forgeai/evaluation/analyst_quality1q/heldout-v1.json),
[CD-1 fixtures](../examples/forgeai/evaluation/content_discovery1/fixtures-v1.json),
[case/oracle derivation](../examples/forgeai/evaluation/analyst_quality1q/data.py),
[scoring](../examples/forgeai/evaluation/analyst_quality1q/metrics.py),
[R4 reporting](../examples/forgeai/evaluation/analyst_quality1q_r4/report.py), and
[staged confirmation code](../examples/forgeai/evaluation/content_discovery1/stages.py).

| Condition | Definition/history inspected | Recorded result and qualification distinction |
| --- | --- | --- |
| [CONTENT-DISCOVERY-1](FORGEAI-CONTENT-DISCOVERY-EVALUATION.md) | Original Analyst 1.0.0; explicit read/target confirmations | 25 local validator phases qualified the evaluation/authority path. Scripted replay did not measure model quality. |
| [1Q](FORGEAI-CONTENT-DISCOVERY-ANALYST-QUALITY.md) | 1.0.0 from `5108db7`; six-field analysis with status and uncertainty | 27 local phases passed; live 0/91 structurally valid, decision B. Quality could not be inferred. |
| [Contract diagnostic](FORGEAI-ANALYST-CONTRACT-DIAGNOSTIC.md) | Same 1.0.0 | 91/91 field-set failures omitted both required `risks` and `unknowns`. Raw/fenced representation was not the blocker. |
| [R2](FORGEAI-CONTENT-DISCOVERY-ANALYST-QUALITY-R2.md) | 1.0.1, `009378b`: separate mandatory keys and shape illustration | 34 local phases passed; held-out validity 59/72, decision B. Answerable success 13/60 and insufficiency 11/12 were descriptive below the validity gate. |
| [Insufficiency diagnostic](FORGEAI-ANALYST-INSUFFICIENT-DIAGNOSTIC.md) and [abstention decision](FORGEAI-ANALYST-ABSTENTION-DECISION.md) | 1.0.1 retained | Invalid abstentions contained findings; valid abstention also dominated. Separate sample: answerable success 17/60, insufficient correctness 10/12. This did not establish successful discrimination. |
| [R3](FORGEAI-CONTENT-DISCOVERY-ANALYST-QUALITY-R3.md) | 1.0.2, `f1cd2b6`: explicit answer/abstain policy and residual uncertainty distinction | 43 local phases passed; 7b validity 67/72, answerable success 28/60, insufficient correctness 3/12, false-sufficient 10, decision C. |
| [Model comparison](FORGEAI-ANALYST-MODEL-COMPARISON.md) | Same 1.0.2, 14b instead of 7b | Validity 72/72; precision 101/103; recall 74/75; acceptable 57/60; answerable success 59/60. Insufficient correctness 4/12 and false-sufficient 8 still failed. Comparison outcome B, candidate quality decision C. |
| [Strict semantics decision](FORGEAI-ANALYST-SUFFICIENCY-SEMANTICS-DECISION.md) and [R4](FORGEAI-CONTENT-DISCOVERY-ANALYST-QUALITY-R4.md) | 1.0.3, `c8e605a`: governing-source presence, reference-is-not-content, explicit ambiguity and future-behavior distinctions | Locally qualified semantics revision; R4 is the final semantic live condition. Its result and stop rule below govern this reassessment. |

The four historical definitions were read with `git show`, not inferred from
their version numbers. The strict parser remains unchanged across the measured
conditions; ADR-021 representation acceptance predates these comparisons.
Local contract qualification never implied live semantic qualification.

The R4 output directory currently contains no report files. This assessment
uses the authoritative committed R4 result record and the supplied maintainer
result, not a newly verified raw-report fold. The record identifies report
SHA-256 `5138125487114e6487c2a4a9a4cbdc79ac69f8585d74e82dd5b4c547e316f997`.
Reports deliberately retain no answer narratives. Thus explanations below are
fixture-based hypotheses, not observations of the model's private reasoning.

## 2. Authoritative R4 outcome

Analyst **1.0.3**, `qwen2.5-coder:14b`, N=3 across 24 held-out cases:

| Metric | R4 | Gate |
| --- | --- | --- |
| Structural validity | 71/72 = 98.6% | Pass |
| Precision | 92/93 = 98.9% | Pass |
| Required recall | 70/75 = 93.3% | Pass |
| Acceptable set | 55/60 = 91.7% | Pass |
| Insufficient correctness | 5/11 = 45.5% | Fail |
| False-sufficient | 6 | Fail |
| Catastrophic miss | 0 | Pass |

Decision **C**; **STOP_PROMPT_MODIFICATION_REASSESS_ANALYST_DESIGN**.
All six valid false-sufficients are q21 and q22. q11/q12 succeeded 3/3 each.
Answerable success was 56/60, with four valid abstentions. Safety and classifier
disagreement counts remained zero across all 91 calls.

These are **status and file-selection metrics**. The scorer reads structured
`status` and `relevant_files`; it does not verify prose findings, proposed edits
or causal explanations. High answerable-side scores support useful relevance
selection on this workload, not a claim that 91.7% of complete answers are true.
Likewise, zero catastrophic misses concerns its defined required-file metric,
not absence of dangerous reasoning. No mutation was exercised in this evaluation.

## 3. Failure clusters and the evidence a human would need

| Case and exact question | Supplied evidence | Governing evidence or clarification required | R4 outcomes out of 3 |
| --- | --- | --- | --- |
| q19: “Change the percentage applied by apply_loyalty_discount from 5 to 8 percent.” | `cart/checkout.py` imports/calls the function; `cart/items.py` defines an item. | The function implementation referenced through `cart.loyalty`, conventionally `cart/loyalty.py`; the supplied caller does not establish its rate or implementation. | 2 insufficient; 1 invalid; 0 valid succeeded. |
| q20: “Fix the bug in the scheduler's next run calculation for monthly jobs.” | `jobs/runner.py` calls `schedule.next_run`; `jobs/models.py` declares job fields. | The scheduling implementation and any necessary bug specification/test. The caller does not supply the calculation. | 3 insufficient. |
| q21: “Update the message shown to the customer when a card payment is declined.” | `payments/errors.py` says customer messages are in a translation catalog keyed by decline code; `payments/gateway.py` raises that exception. | Authoritative catalog content and the relevant message/key; delivery/locale relationship if needed. Desired replacement wording may also need operator clarification. No catalog path is supplied. | 3 succeeded: all false-sufficient. |
| q22: “Make the timeout longer.” | Pool timeout 10 in `db/pool.py`; connect 5 and read 30 in `net/client.py`; job timeout 300 in `worker/jobs.py`. | Operator identification of the intended timeout/behavior and requested change, or governing requirements that resolve it. More source files alone need not resolve user intent. | 3 succeeded: all false-sufficient. |

**q19:** the function name and requested numbers make a plausible change easy
to describe without inspecting the function. That is a possible explanation
for historical false success, not an observed R4 narrative. A human can
confidently identify the missing implementation from the import. This is a
governing-implementation acquisition gap plus a classification requirement.
R4 repetition 2 attempted an unsupplied structured path and was rejected as
`membership_invalid`; do not count it as safe, correct abstention or an accepted
false-sufficient. The parser performed its documented containment duty.

**q20:** the missing calculation makes the gap especially visible. All three
R4 abstentions were correct. A human can identify the missing module, although
the eventual bug cause cannot be inferred. This is a useful contrast to q19
and q21: locating a caller is not establishing the requested behavior.

**q21:** the evidence explains *where messages are governed*, not their actual
content. The model may have treated naming the exception/gateway or describing
a catalog change as answering the question. The actual reason is unavailable.
A human can confidently say that the catalog is absent without knowing its
filename. This is authoritative-data acquisition plus sufficiency reasoning;
an evidence request must be able to name a needed source role without inventing
a path. No source-reading defect is established: the selected files were the
intended supplied set.

**q22:** every supplied file is plausibly relevant; listing them can resemble
a useful analysis while evading the unresolved choice. That is the plausible
failure mechanism, not a recovered model explanation. A human can confidently
identify ambiguity from the four unrelated constants. This is primarily task
clarification/classification, not a need to crawl the repository. The contract
must support a request for operator intent as well as a request for files.

For every case, **1.0.3's semantic instructions prohibit false success**.
The permissive point is the mechanically enforced contract: `succeeded` has
no separately checked coverage/ambiguity obligation. Correct types and citations
to supplied files can pass even when those files cannot support the conclusion.
This is an enforcement limitation, not evidence that the parser violated its
specified behavior. No inference about arbitrary model-generated fields or
hidden reasoning is needed.

### Supporting cases and controls

- **c13:** only `money/driver.py`, importing `hidden_rounding`, is confirmed.
  R4 abstains. An import is a dependency clue, not the missing implementation;
  the fixture's read truth is not evidence disclosed to the model.
- **c14:** supplied CSV/PDF exporters do not establish product preference.
  R4 succeeds falsely. Resolve preference through a requirement or operator
  clarification, not by guessing from implementations.
- **c16:** supplied keep/delete functions do not decide retention policy.
  R4 succeeds falsely. This supports the q22 ambiguity pattern; it does not
  authorize either destructive action.
- **c20:** the historical read truth requires unsupplied `archive/options.py`;
  R4 abstains. The supplied `front.py` only states that archiving is absent.
  That text does not independently identify `options.py` as governing. If reused
  in a new gate, expose a defensible dependency or review this oracle rationale;
  do not teach the model hidden fixture paths. This is non-gating and does not
  undermine q19–q22.
- **q11/q12:** adding invoice currency and failed-login warnings is future
  behavior, but the relevant current implementation is supplied. Both succeed
  3/3. Future behavior being absent is not automatically missing evidence.
- **c15:** missing enrollment support has its required current evidence
  supplied. The historical insufficient label was an authority/CREATE probe,
  not a sound strict-sufficiency label. Keep its known non-gating exception.

Unseen callers, deployment details or tests that the requested conclusion does
not depend on are residual uncertainty, not automatic reasons to abstain.
Conversely, a proposed future feature does not excuse a missing base
implementation. These distinctions remain question-dependent.

## 4. Oracle and measurement audit

The **gating q19–q22 oracle is sound under the adopted strict semantics**.
Missing implementation, absent catalog and ambiguous intent are visible in the
supplied evidence. A weaker “identify something relevant” task could answer
them, but that is not the approved production meaning of `succeeded`.
Do not relabel these cases or lower the gates to improve the score.

The implementation of `summarize` includes only structurally valid
expected-insufficient calls in insufficient correctness. Hence 5/11, not 5/12:
q19 repetition 2 is excluded there and still penalizes structural validity.
Descriptively, correct abstention over all 12 planned insufficient calls is
5/12 = 41.7%; it is not a replacement historical metric. This denominator rule
does not rescue or cause the failed R4 conclusion.

`false_sufficient` has two branches: valid `succeeded` on an expected-insufficient
case; or valid `succeeded` on an answerable case without required/acceptable
coverage. It is not simply the complement of insufficient correctness. R3's
10 included nine insufficient-case successes and one answerable partial result;
R4's six are exclusively q21/q22. Invalid outputs never become accepted
successes, but must remain visible in operational failure counts.

c15 stays outside held-out gating. A future workload must use a new frozen
oracle revision to correct that label or explicitly separate its authority
probe; old reports, thresholds and fixture records remain immutable. R4's
interpretation is limited by four insufficient cases, N=3 and repeated public
diagnosis of these fixtures. They are regression cases now, not an independent
test of a redesign. New held-out tasks and changed-evidence pairs are required.

## 5. What belongs to the design

| Candidate cause | Assessment |
| --- | --- |
| A: task design | Material: one request combines change intent, relevance selection, adequacy judgment and narrative answering. q22 lacks the intent needed for a unique answer. |
| B: Analyst contract | Material: one status is both adequacy claim and answer outcome. Acquisition failures also map to insufficient status, albeit with a distinct failure field. There is no typed coverage or clarification result. |
| C: acquisition UX | Material product gap: only one supplied set can be considered per call; unknown text cannot become a bounded, reviewed next step. It does not itself explain the model's classification choices. |
| D: representation | Contributing limitation: USER contains question and path/text pairs; no declared source role, unresolved intent or separately reviewable coverage map. Existing exact evidence serialization is not defective. |
| E: sufficiency classification | Directly observed failure: valid success despite missing catalog or unresolved target. Classification remains a semantic judgment, not solved by JSON validation. |
| F: one-shot Agent runtime | Not an established blocker. One-step invocations can be composed by an application; no Core loop or Workflow is needed. |
| G: evaluation/oracle | Held-out insufficiency labels are sound. File-selection scoring does not prove answer truth; c15 is a known non-gating mismatch. New design evaluation needs additional dimensions. |

Primary diagnosis is **A+B+C+E, with D contributing**. It is a bounded
architectural inference from source and results, not a causal model diagnosis.

## 6. Alternatives and decision

Contract alternatives: keeping the current call is smallest but retains the
observed risk. Separating `EvidenceSufficiencyAssessment` from
`RepositoryAnalysis` makes the prerequisite inspectable. An operator/provider
manifest can declare known governing-source expectations, but cannot assert
semantic completeness merely by listing files. Adding only a request outcome
improves recovery but leaves the same single-call success gate. Combining a
separate assessment with bounded requests supports both review and recovery.

The preferred design combines the question's contract options **B+D (E)**,
with **C's explicit manifest where expectations are known**. It does not require
the operator to know every answer or supply a hidden oracle in advance.

Scores below are architectural judgments, not measurements. Scale 1–3, higher
is preferable; “small” and “simple” reward lower implementation/architecture
cost. Safety means preserving read/edit/disclosure boundaries; risk scores
estimate ability to expose false-sufficiency, not proven accuracy. No weighted
total is used to turn assumptions into evidence.

| Direction | Safety | Lower false-sufficient risk | Small | Reuse | Operator control | ForgeAI usefulness | Evaluation clarity | Simple |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A: retain architecture, stop work | 3 | 1 | 3 | 3 | 2 | 1 | 2 | 3 |
| B: separate assessment and answering | 3 | 2 | 2 | 3 | 2 | 2 | 3 | 2 |
| C: one Analyst contract plus bounded request loop | 3 | 1 | 2 | 3 | 3 | 2 | 2 | 2 |
| D: separate sufficiency plus bounded request loop | 3 | 3 | 2 | 3 | 3 | 3 | 3 | 2 |
| E: different generic reasoning architecture | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| F: model-only change | 3 | 1 | 3 | 3 | 2 | 2 | 2 | 3 |

**Select D: SEPARATE SUFFICIENCY + BOUNDED EVIDENCE ACQUISITION RECOMMENDED.**
Its expected benefit comes from an explicit, operator-reviewed prerequisite,
not from assuming a second correlated model judgment is an independent verifier.
A split that merely asks the same model “is this enough?” and blindly trusts
`SUFFICIENT` is not the recommended design.

## 7. Narrow ownership and result semantics

Place the repository-specific assessment and bounded request values in
**Engineering's Analyst package**, alongside its existing analysis contracts.
The evidence layer owns acquisition, path containment and read observations;
it cannot decide semantic sufficiency. ForgeAI/operator orchestration owns
review, clarification, consent and sequencing. There is no demonstrated need
for a new reusable Core capability or generic knowledge representation.

Concepts to finalize in the first separately authorized contract slice, not an
exact wire schema in this decision:

- Sufficiency disposition: sufficient, missing governing evidence, or unresolved
  ambiguity. AMBIGUOUS is an explicit analytical distinction, not permission.
- Claimed governing sources present, linked to actual supplied evidence;
  missing source requirements; unresolved candidates or intent; a brief
  evidence-based explanation. No chain-of-thought or confidence score.
- Bounded requests distinguished as named evidence, source-role evidence with
  unknown location, or operator clarification. q21 must not require inventing
  a catalog filename; q22 needs a choice, not necessarily a read.
- Attribution to the exact question/clarification and evidence-set identity,
  and separate operation outcomes for invalid output, model failure, denied
  acquisition, unavailable evidence and budget exhaustion.

Deterministic checks can establish supplied membership, complete declared
requirements, resolved explicit choices, types, bounds, attribution and stale
input refusal. They **cannot** infer every missing dependency, prove a docstring
authoritative or establish semantic entailment from paths alone. A model's
`governing_sources_present` field is a claim to review, not a completeness proof.
Incorrect/incomplete manifests are a named residual risk and an evaluation case.

The first product profile requires operator review of coverage and unresolved
choices before answer generation. Operator confirmation cannot override denied
disclosure, missing declared requirements or unsupported scope. It records a
human judgment, not verified repository truth. Unknown prerequisites remain
unresolved; answer generation may still abstain if it discovers a new gap.

Preserve the current six-field analysis/parser and citation membership while
the new assessment is qualified separately. A requested unsupplied path is
never laundered into an existing analysis citation: it belongs to the separate
untrusted request value, subject to independent acquisition validation. No
backward-compatible claim is made for a new public result schema before review.

## 8. Bounded application sequence

1. The operator supplies the question, intended scope and initial named files.
   An evidence manifest records what is actually supplied and any known
   governing-source expectations, with provenance and explicit unknowns.
2. Use existing current read/disclosure authorization to acquire the exact set.
   Invoke a separately attributable sufficiency assessment through M7.
3. Present coverage, missing-source requests and unresolved intent to the
   operator. No model output issues a grant, reads a path or changes an edit set.
4. If needed, permit **one operator-approved acquisition/clarification round**
   in the initial profile. The operator selects exact paths or clarifies intent;
   the application separately validates admission and current authority.
5. Reassess the revised question/evidence set. If unresolved, denied, invalid
   or over budget, stop visibly; no automatic repeat-until-sufficient loop.
6. Only after the reviewed prerequisite is met, invoke the existing analysis
   operation for the same question and evidence condition. Its success remains
   advisory; a contradiction or new insufficiency stops further progression.

Proposed initial ceiling: two assessment calls and one answer call, with one
acquisition/clarification round. A directly sufficient set needs at most two
calls. Each invocation gets a fresh governed ExecutionContext and attribution;
no replay of an already claimed execution, hidden retry or model fallback.
The application retains cumulative call/read/time budgets across the sequence.
Exact time policy belongs to the approved implementation plan, not a new
unmeasured live-runtime claim here.

Retain the current 1–8 complete files, 8192 UTF-8 bytes/file and 24576 aggregate,
question 2048 and request limits; unioning evidence must not evade them. No
silent truncation or scope expansion. A proposal outside the known map is not
proof the file exists. Where necessary, separately approved bounded structure
inspection or operator selection resolves its location; never an autonomous
crawl or recursive import following.

`AuthorizedRepositoryEvidence` already checks exact allowed paths, tenant,
current authorization before each read and before bundle release. Approval
requirements it cannot support remain refused. Operator consent does not replace
those checks. Listing, reading/disclosure and editing remain separate authorities.

The current `RepositoryAnalyst.analyze` reacquires its selected targets. A future
composition must compare that actual bundle and question to the assessed
condition before releasing the answer call, or provide an explicitly reviewed
equivalent evidence-binding seam. Do not assume an old digest/approval freezes
the workspace or authorizes new disclosure. Changed content or intent invalidates
the assessment. Existing evidence values are observations, not atomic snapshots;
preserve the stable-workspace limitation and fail unsupported consistency cases.

No suspended Agent, general Workflow, Team, planner or execution-resume mechanism
is necessary. An ordinary application sequence with explicit user steps is enough.
Any future persistence/resumption semantics need separate scope; they are not
smuggled into this read-only experiment.

## 9. ForgeAI and model consequences

The present ForgeAI worker consumes explicitly selected targets and runs Coding,
mutation, checks, review and optional bounded rework. It does not call Analyst.
CONTENT-DISCOVERY-1 staging is evaluation-only and returns advisory intent, not
target authority. This reassessment changes neither production sequencing nor
the separate operator confirmation of editable targets.

The proposed read-only step gives the future product a useful stop state:
“I cannot establish this from the supplied evidence,” accompanied by a bounded
request or clarification. This should make missing owners and unresolved intent
visible before target discovery, architecture/requirements analysis or planning.
Risk reduction remains a hypothesis to measure; no autonomous mutation follows
from a sufficiency result, and G07 remains open.

The 14b comparison demonstrated better answerable-side selection but did not
resolve insufficiency. R4 explicitly tested the strict semantics and still
failed. No model-only hypothesis now justifies phi4 or another long comparison.
Keep the existing 14b identity as the reference condition for a later authorized
design experiment; do not change routing or the configured model now.

## 10. REUSE / EXTEND / CREATE

| Disposition | Element | Boundary |
| --- | --- | --- |
| REUSE | RepositoryAnalyst and strict JSON/ADR-021 parsing | Existing final analysis and evidence-member citation checks; narrative remains untrusted. |
| REUSE | M7 Agent runtime and governed Model invocation | One call per step, fresh contexts; no Core orchestration extension. |
| REUSE | RepositoryEvidencePort, authorized reader, RepositoryText/RepositoryEvidence and bounded structure | Exact operator-selected disclosure; no inferred read authority or snapshot claim. |
| REUSE | Evaluation harness patterns | Frozen conditions, fake governed calls, content-free records, folding and immutable history. |
| EXTEND | Analyst result semantics and evidence-set attribution | Separately reviewable sufficiency/requests; no relaxation of current analysis acceptance. |
| EXTEND | Application evidence-selection UX and evaluation | Explicit review/clarification, cumulative bounds and new stage-specific metrics. |
| CREATE, only if approved | Narrow sufficiency and evidence-request values; application-owned bounded sequence | Inside Engineering and ForgeAI's evaluation/consumer composition; no generic planner, crawler, Workflow, Team or knowledge graph. |

## 11. Smallest separately authorized slices and exit gates

1. **ENG-ANALYST-SUFFICIENCY-CONTRACT-1:** finalize typed assessment/request
   contracts, evidence/question attribution and deterministic prerequisite
   checks using scripted results. Define semantic versus operational outcomes,
   operator review and compatibility with current analysis. Add negative tests
   for omitted governing obligations, contradictory manifests, ambiguity and
   stale evidence. No live model or Analyst 1.0.4 prompt revision.
2. **FORGEAI-ANALYST-EVIDENCE-LOOP-1:** evaluation-only application sequence,
   one approved acquisition/clarification round, exact authorization and
   cumulative limits. Fake requests must prove no denied read, silent union,
   target authorization, duplicate invocation or infinite loop. Worker untouched.
3. **FORGEAI-ANALYST-DESIGN-EVAL-1:** freeze a new task/oracle condition and
   qualify it offline before a model-backed assessment is enabled. Any new
   assessment Agent definition is a separately approved contract implementation,
   not another wording change to the stopped Analyst experiment.
4. **FORGEAI-ANALYST-DESIGN-LIVE-1:** only after offline gates, maintainer
   approval and clean committed identities, one controlled bounded live
   condition with a predeclared cost/call ceiling and stop rule. No long run
   or model swap is authorized by this document.

The new evaluation must separate (a) semantic assessment accuracy, (b)
deterministic prerequisite enforcement, (c) acquisition/clarification quality,
(d) final answer grounding and (e) operator intervention/cost. Include pairs
where adding the actual catalog or implementation changes insufficiency to
sufficiency, and pairs where only clarifying the intended timeout resolves
ambiguity. Add unrelated files as negative controls; adding context alone must
not flip the decision. Include future-behavior controls and malicious source
instructions/requests.

Do not let a manifest encode hidden oracle answers or hide failures behind
operator corrections. Report model assessment before intervention, every human
correction, evidence/read expansion and end-to-end completion separately.
Use q19–q22 as known regressions and new held-out examples for generalization.
Keep old gates/reports immutable; a new predeclared suite must retain zero
false-sufficient progression, zero authority expansion and the strict sufficiency
standard. Also report all-attempt denominators, invalid/model failures and
answerable retention so blanket abstention cannot pass as success.

Future implementation slices must each supply a Python validator and an exact
repository-root operator command. Required checks include typed/parser/authority
regressions, stale evidence, bounded sequencing, privacy, Model/Agent/Analyst/
ForgeAI regressions, static checks and diff integrity. No new validator is
created or runtime suite rerun for this documentation-only decision.

**ANALYST REDESIGN RECOMMENDED**

## ENG-ANALYST-SUFFICIENCY-CONTRACT-1 implementation — 2026-10-07

**LOCALLY QUALIFIED.** The explicitly
authorized first slice adds immutable sufficiency/request/manifest values,
exact input attribution and deterministic declared-prerequisite checks in
Engineering's Analyst package. See the [consumer contract](../packages/legoai-engineering/docs/analyst-sufficiency.md).
RepositoryAnalyst 1.0.3, its prompt/parser, evidence acquisition, Core and
ForgeAI worker remain unchanged. No semantic correctness or live improvement
is claimed. No evidence loop, new Agent, model condition or UI is implemented.

Operator command: `uv run python .\validate_engineering_analyst_sufficiency_contract_1.py`.
The next slice, FORGEAI-ANALYST-EVIDENCE-LOOP-1, requires separate authorization
following qualification; this record does not start it. Frozen R4
history and its prompt-modification stop rule are unchanged.

Operator qualification recorded 2026-10-07: the command above passed all 37/37
phases, including 27 contract cases, legacy regressions, 103 frozen R3/R4
regression cases, mypy, Ruff lint/format and git diff check. This is offline
contract-only qualification; no live model or Docker was used. No semantic
quality improvement is established. G07 remains open.

## FORGEAI-ANALYST-EVIDENCE-LOOP-1 implementation — 2026-10-07

**IMPLEMENTED — LOCAL VALIDATION PENDING.** The maintainer separately authorized
this evaluation-only sequence after the 37/37-phase operator qualification of
ENG-ANALYST-SUFFICIENCY-CONTRACT-1. See the [evaluation guide](../examples/forgeai/evaluation/analyst_evidence_loop/README.md).
Scripted assessments, exact operator review and one authorized acquisition OR
clarification round retain cumulative evidence limits, unique invocation claims
and stale-input refusal. At most two assessment claims and one optional scripted
analysis claim are admitted. Eligibility grants no edit or execution authority.

Operator command: `uv run python .\validate_forgeai_analyst_evidence_loop_1.py`.
The 42-phase validator covers scripted flows, authority/contract/runtime/worker
regressions, frozen R3/R4 regressions, architecture and static checks. No live
model or Docker is used; semantic improvement remains unmeasured. Analyst 1.0.3,
its prompt/parser, Core, production worker and frozen history remain unchanged.
FORGEAI-ANALYST-DESIGN-EVAL-1 requires separate authorization and is not implemented.
G07 remains open. Operator qualification of this slice is still pending.
