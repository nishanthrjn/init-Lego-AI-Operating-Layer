# Lego AI Operating Layer — Evaluation Specification

**Evaluation specification version:** 0.1.0  
**Status:** PROPOSED — FOR CANONICAL REVIEW  
**Authority:** [intent.md](../intent.md) 1.0 → [SPEC.md](../SPEC.md) 0.1.0 → [ARCHITECTURE.md](../architecture/ARCHITECTURE.md) 0.1.0 → [CONTRACTS.md](../contracts/CONTRACTS.md) 0.1.0 → [PLUGIN-SPEC.md](../plugin-spec/PLUGIN-SPEC.md) 0.1.0 → [SECURITY.md](../security/SECURITY.md) 0.1.0 → this document.  
**Scope:** Technology-neutral assessment definitions, attempts, methods, cases, datasets, judgments, coverage, uncertainty, comparison, and governed evidence.

## 1. Authority, scope, and boundaries

**EVAL-001.** This specification MUST preserve the accepted authorities' concepts, ownership, lifecycle states, Capability/Port/Plugin semantics, security authority, tenancy, resources, execution, effects, errors, Outcomes and conformance boundaries. SPEC §1 supplies normative language. Applicable upstream requirements are cumulative. A discovered contradiction MUST identify exact upstream sections and their owner; only the affected evaluation behavior remains unfinalized until an upstream correction. Evaluation MUST NOT silently repair or replace higher-level semantics.

No new higher-level contradiction was identified. SPEC §4.11 already defines Evaluation as an assessment attempt. This document's reusable assessment declaration and EvaluationRun vocabulary refine how that attempt is described and observed; neither replaces Evaluation with a new global entity or lifecycle. Architecture §§4.7 and 5.2 and resolved Contracts HLC-01 remain binding: Intelligence does not directly invoke Evaluation. An authorized consumer permitted to depend on both orchestrates Model/Skill assessment; authorized existing evidence may be referenced without a new module dependency.

**EVAL-002.** Evaluation supplies measurement, assessment and evidence. Conformance determines whether a declared implementation satisfies mandatory canonical obligations using its required proof. A good score, evaluator opinion, successful assessment execution or security finding MUST NOT by itself grant Permission, Approval, Plugin admission, release/deployment, Policy change, Task acceptance, Goal achievement or canonical Outcome. Consumers make separate entitled decisions under their own contracts; Evaluation cannot appoint their authorities.

**EVAL-003.** Evaluation MUST be independently consumable. A deterministic function, direct capability, Tool Adapter, Retriever, Artifact transformation or Policy evaluator can be assessed without an Agent, Team, Goal, Workflow, Model, conversation or RAG composition. An evaluation need not have a Plugin as its subject or require a Plugin-management workflow. Where an Evaluator realization is supplied as a Provider/Adapter, its existing owning-Plugin and admission obligations remain applicable, including for built-ins; independent consumption does not exempt realization governance. Only declared relevant dependencies are required.

**EVAL-004.** No evaluation language, vendor, Model judge, framework, test runner, statistical library, tracing system, database, notebook, CI platform, schema, benchmark format or serialization is selected. This document creates no evaluator code, cases/datasets for execution, test suite, judge prompt implementation, red-team tooling, CI configuration, SDK, schema or ADR. Conceptual structures are labeled **illustrative semantic structure — not canonical serialization**. Tables and diagrams define semantic relationships and observable obligations, not implementation APIs.

## 2. Evaluation principles and invariants

The following summarizes normative obligations defined throughout this document. It is not a substitute for their detailed applicability and evidence conditions.

| Invariant | Requirement anchors |
|---|---|
| EvaluationResult never grants authority or automatically creates Outcome | EVAL-002, EVAL-066–068, EVAL-079–080 |
| Successful evaluator execution is not subject success; failed assessment is not automatically subject failure | EVAL-007–010, EVAL-029–034, EVAL-058–061 |
| Subject, Evaluator, material configuration/environment and case/dataset versions are attributable and pinned | EVAL-006, EVAL-011–014, EVAL-020–028 |
| Missing results are never silently pass or zero; partial coverage remains explicit | EVAL-029–034, EVAL-040–046 |
| Material probabilistic uncertainty is disclosed; numerical values have defined meaning | EVAL-015–019, EVAL-029–033 |
| Self-evaluation is labeled; independence names its dimensions | EVAL-035–039 |
| Human evaluation is not HumanApproval; Model judge output is evidence, not truth | EVAL-036–039 |
| Evidence and evaluation work remain tenant/security/resource governed | EVAL-054–065, EVAL-077–080 |
| Evaluation scores do not replace Conformance proof | EVAL-002, EVAL-082–084 |
| Historical results are immutable; changed assessment semantics/material data create new versions | EVAL-025–028 |
| No private chain-of-thought is required | EVAL-014, EVAL-048, EVAL-078 |

## 3. Canonical model and Evaluation-layer vocabulary

**EVAL-005.** Evaluation Management remains the Architecture §4.12 owner of Evaluator definitions, Evaluation attempts, EvaluationResults and assessment evidence. Respective source modules retain subject state, acceptance, authority, resource balances and Artifact relationships. Evaluator realizations sit behind the Evaluation Port and obey permitted Architecture dependencies. Security and resource admission use their existing owners; this specification introduces no privileged evaluation runtime or universal assessment authority.

| Term | Meaning / status in this layer |
|---|---|
| Evaluator | Existing SPEC concept: versioned assessment contract/definition and its realization, with declared method, criteria, outputs and limitations |
| Evaluation | Existing SPEC concept: one governed assessment attempt applying a pinned Evaluator to pinned subjects/criteria and input evidence |
| EvaluationResult | Existing SPEC concept: immutable attributed judgment/measurements from an Evaluation, with evidence, uncertainty and limitations |
| Assessment declaration | Reusable versioned configuration describing intended subjects, criteria, cases, constraints and comparison; an owned definition/value or Artifact, not a second Evaluation lifecycle |
| EvaluationRun | Evaluation-layer execution/provenance record for one performed assessment attempt, linked to its Evaluation and actual Execution; not a global domain entity or separate state machine |
| EvaluationCase / AdversarialCase | Versioned scenario/input and assessment expectations; adversarial specialization adds attacker, threat and defense criteria |
| EvaluationSuite | Versioned grouping of cases/assessments and explicit selection, dependency and completion rules; not a mandatory Workflow |
| EvaluationDataset / corpus | Governed versioned input/reference collection and membership/provenance/sampling description |
| EvaluationCriterion | Versioned property or quality question to assess |
| EvaluationMetric | Versioned method/scale for measuring or judging a criterion, numeric or nonnumeric |
| EvaluationBaseline | Pinned reference subject/result/expected behavior/distribution with applicability conditions |
| EvaluationComparison | Attributed assessment relating exact results/subjects using a declared comparable basis |
| EvaluationCoverage | Evidence of assessed scope relative to a declared denominator/population and its limitations |

Independently referenced vocabulary records inherit SPEC S-01–S-12 for stable identity, accountable owner, scope, version/revision, access, retention and provenance. Embedded records may use owner identity plus a local key. These terms do not add global entities, privileged owners or new canonical lifecycle values. Existing Artifact/definition/record semantics govern their persistence where represented; no particular storage representation is required.

### 3.1 Evaluation binding and run identity

**EVAL-006.** An Evaluation request MUST bind exact subject identities/kinds/scopes and relevant definition/state/Artifact versions, Evaluator and criteria versions, selected case/dataset/suite versions and membership, assessment configuration, material environment assumptions, required evidence, optional exact baseline/comparator, tenant/Principal context, resource/deadline limits and security/privacy conditions. A request may resolve an explicit current/latest selector before binding, but MUST record its exact resolution; later changes cannot rewrite the attempt or result. Unresolvable mandatory identity/meaning prevents the assessment from claiming valid evidence.

**EVAL-007.** Evaluation retains SPEC §4.11's lifecycle: `requested → running → completed, failed, or cancelled`; requested may be cancelled. Execution uses SPEC §5.8 independently. An EvaluationRun record MUST identify the Evaluation and immutable assessment declaration revision, actual root Execution identity and subordinate attempts where applicable, Evaluator/realization, subjects, configuration, selected cases/data, environment/dependencies, start/end observations, actual statuses, inputs/evidence, resource usage, failures, partial result references and provenance. One performed attempt has one run identity; retransmission retains that identity, while a genuine rerun creates a linked new Evaluation/Execution/run, preserving prior facts.

The run record exposes canonical Evaluation status and Execution status separately. It introduces no `partially_passed`, `inconclusive`, `needs_adjudication` or other execution lifecycle state. A suite may coordinate several child Evaluations with explicit parent coverage/completion rules; a run name cannot hide their distinct attempts or retry costs. Rejected execution admission does not invent an Evaluation `rejected` state: the requested Evaluation remains pending with a recorded refusal/obligation, or is cancelled through its permitted path. Assessment errors after work starts use the existing permitted failure semantics.

**EVAL-008.** A run's successful execution means the declared assessment work/postconditions were performed, not that the subject passed. Evaluation completed, operation completed, Execution succeeded, subject judgment and coverage MUST be independently visible. Full-suite completion MUST NOT be asserted when required cases remain unassessed. Completed child assessments may produce valid partial evidence even while their parent remains running or ends failed/cancelled. A predeclared bounded or adaptive stopping rule may complete its specified assessment scope, but it cannot retrospectively shrink the promised denominator to hide missing cases.

### 3.2 Results and evidence boundaries

**EVAL-009.** Each EvaluationResult MUST bind subject identities and exact versions/revisions, Evaluator/realization and method/criteria versions, Evaluation/run/Execution references, case/dataset selection, configuration/environment/dependency assumptions, judgment and metric interpretations, material uncertainty, coverage, applicability/freshness, limitations, timestamp/assessor, evidence and provenance. Where no metric, dataset, baseline or uncertainty estimate applies, the result MUST state non-applicability or the relevant limitation rather than fabricate a value. Multiple result records may describe different cases, criteria, slices or observations from the same attempt.

**EVAL-010.** Recorded results are immutable attributed assessments, not immutable truth claims. Corrections append a linked corrected record with reason, authority and evidence; original interpretations remain inspectable under policy. Subject failure may be reported from valid observations against a criterion even when the overall run later fails, but assessor failure/missing measurement alone MUST NOT be labeled subject failure. Consumers MUST validate subject match, evidence validity, coverage and uncertainty before using a result; they do not inherit the evaluator's permissions or acceptance authority.

```text
Diagram 1 — Subject to EvaluationResult
pinned subject + configuration/environment + governed inputs
    --> admitted Evaluation [Evaluator/criteria/cases/constraints]
    --> assessment Execution/run --> observations --> EvaluationResult
                                                judgment + coverage + uncertainty
source owners keep subject state; consumer decisions remain separate
```

```text
Diagram 2 — Run status versus judgment
Evaluation requested --> running --> completed / failed / cancelled
                              |
                       actual Execution attempt(s)
                              |
                       case/criterion observations
                              |
                      subject pass/fail/inconclusive or declared scale
Execution succeeded + subject failed is valid.
Execution failed + no adequate assessment means unavailable evidence, not subject fail.
```

## 4. Evaluator definition, realization, dependencies, and oracle

**EVAL-011.** An Evaluator definition MUST declare identity/version, accountable owner, purpose, supported subject kinds/versions, criteria, required inputs/evidence, method and output scales, assumptions, uncertainty/failure semantics, limitations, dependencies, resource needs, security/privacy constraints and supported operations. Required collections may be explicitly empty only when meaningful. Evaluator definition, concrete realization/Provider/Plugin release, assessment configuration and run are independently identified. A Model-based realization does not define the canonical Evaluator abstraction.

**EVAL-012.** Dependencies MUST declare exact bindings or compatible requirements, required stages, mandatory/optional status, trust/tenant/resource constraints, omitted-feature consequences and evidence freshness. A judge's Model, prompts/instructions, Tools, reference corpus, subsidiary evaluators and human-review procedures cannot remain hidden. Resolution follows Contracts closure and Plugin admission rules. Cyclic assessment/adjudication dependencies MUST terminate through explicit bounded rules and an accepted reference/assessment basis; unresolved or unbounded recursion fails rather than silently returning a score.

**EVAL-013.** Evaluators themselves MAY be assessed for calibration, agreement, bias, robustness, false-positive/false-negative behavior, reproducibility, cost and latency. Such meta-evaluation MUST pin evaluator subjects and reference methodology, expose shared assumptions and stop at declared accepted evidence/oracle assumptions. It cannot bootstrap infinite verification or self-certify trust. Accepted reference authority means responsibility for expected assessment meaning, not authorization to execute protected actions.

**EVAL-014.** Every criterion MUST identify how observable evidence supports its judgment and where the oracle is uncertain. Exact reference facts, property checks, external verification, authorized Human review, comparisons, multiple evaluators, simulation and statistical evidence are permissible declared strategies; no universal perfect oracle is assumed. Public action/rationale, results, traces and provenance may support assessment, but private chain-of-thought MUST NOT be required. A plausible judge rationale is not independent evidence that its conclusion is correct.

## 5. Criteria, metrics, thresholds, and interpretation

**EVAL-015.** A criterion MUST identify identity/version, owner, subject/property, scope, assessment question, applicability, required observations and limitations. Criteria may cover functional correctness, relevance, groundedness, robustness, security resistance, recovery, task/product quality, public rationale, cost or latency. These examples are not universal mandatory dimensions. Domain-specific criteria belong to scoped evaluator/blueprint/application definitions, not a mandatory core business ontology.

**EVAL-016.** A metric MUST identify identity/version, criterion, measurement/judgment method, result type, scale/units and valid range/categories, direction/interpretation, population/measurement unit, aggregation, missing-data handling, uncertainty, minimum sample/evidence conditions, optional threshold semantics and limitations. Boolean, categorical, ordinal, numeric, distributional, structured qualitative, Human and comparative judgments are all valid when interpretable. Ordinal labels do not automatically support arithmetic; unrelated units/categories cannot be averaged. A bare number or undefined label is invalid assessment evidence.

**EVAL-017.** Deterministic checks MUST identify exact inputs, state cut and comparison/invariant semantics. A deterministic rule applied to stochastic/noisy observations yields a deterministic computation over those observations, not an exact claim about all future behavior. Probabilistic/statistical methods MUST declare relevant variability, sampling and method assumptions. Exact output matching, representation validation, state-transition and accounting checks may contribute evidence for canonical obligations; passing them does not by itself establish full Conformance.

**EVAL-018.** Thresholds MUST be versioned and attributable to their defining authority, criterion/scale, inclusive/exclusive comparison, aggregation/population, minimum evidence, uncertainty treatment, freshness and applicability. A criterion may define pass/fail for its assessment; a separate Policy/gate decides whether that evidence satisfies release/admission/acceptance requirements. Missing confidence bounds or samples cannot be treated as favorable threshold satisfaction. Thresholds chosen after observing candidate results must be disclosed as exploratory or newly versioned, not silently portrayed as an unchanged predeclared gate.

**EVAL-019.** Open-ended work MUST support separate dimensions and structured qualitative findings without forcing a single score. A software-team composition, for example, can declare requirements fit, architecture consistency, correctness, test quality, security, review quality, maintainability, deployment-readiness evidence and handoff quality through ordinary criteria. Research, media, analysis and other applications may use different dimensions. A quality tradeoff or low aggregate cost MUST NOT override a mandatory security/correctness obligation.

## 6. Cases, suites, datasets, and reference baselines

**EVAL-020.** An EvaluationCase MUST bind identity/version/owner, purpose, inputs/references, subject applicability, preconditions, environment, expected or assessable facts, allowed variability, forbidden behavior, oracle/method/criterion versions, resource bounds, classification, tenant/access/retention and provenance. Expectations may be ranges, invariants or qualitative rubrics instead of one golden answer. Published case content and expected-result semantics are immutable; corrections create a new version with reason. Expected answers MUST NOT be silently edited after observing the subject output.

**EVAL-021.** A suite MUST declare case/evaluator membership or reproducible selection rules, dependencies, required/optional components, per-stage and overall completion semantics, stopping rules, resource budget, parallelism/ordering constraints where meaningful, coverage denominator and result aggregation. It need not be implemented as a Workflow. An adaptive suite MUST retain its selection decisions, realized cases and stopping evidence; it cannot describe an adaptive selected subset as an unbiased complete population without justification.

**EVAL-022.** A dataset/corpus MUST identify immutable content/membership version, accountable owner, source and usage/license constraints where applicable, tenant/privacy classification, provenance and collection method, sampling/population assumptions, known bias/contamination, transformations/labels/reference-answer lineage, retention/access and applicability. Storage location is not identity. References to inaccessible/prohibited data do not authorize access; an immutable identifier does not guarantee retained content availability. If the corpus changes during assessment, bind an identifiable snapshot/version or explicitly declare the time-varying coverage limitation.

**EVAL-023.** Dataset governance MUST record known or suspected training contamination, benchmark memorization, case/prompt/answer leakage and evaluator exposure to hidden expected results. Separate subject inputs from evaluator-only reference material according to the case contract. Where independence/blinding requires withholding labels or answers, enforce it at data-access boundaries, not merely through instructions. Unknown contamination MUST be reported as unknown, not clean. Hidden test material is access-restricted according to policy and is a Secret only when its governing classification makes it one; secrecy is not automatically required for every case.

**EVAL-024.** A baseline MUST identify an exact prior release/result, reference implementation/behavior, Human assessment, expected value or historical distribution; include owner/selection authority, criterion/method, data/configuration/environment, time window, uncertainty, support and applicability. A baseline result remains immutable; designating or superseding the current comparison baseline is a separate revisioned decision. “Previous,” “reference,” or “better” without an exact basis MUST NOT support a historical regression claim.

```text
Diagram 3 — Cases, datasets, suites, and Evaluator
dataset version --> selected case versions --> subject inputs
        |                   |
        |             expectations/oracle evidence --> Evaluator version
        |                                              |
suite revision --> selection/completion rules ----------+
                                                       v
                                             Evaluation/run/results
Hidden reference access is separately governed from subject input access.
```

## 7. Versioning, environment, reproducibility, and validity

**EVAL-025.** Evaluator, criterion, metric, judge instructions/prompts, aggregation, threshold interpretation and case-selection semantic changes MUST create new versions/revisions appropriate to their owning definition. Published semantic content follows SPEC §11 and Contracts CTR-063–065; operational progress changes state revisions, not published meaning. Material dataset membership/content, labels, expected answers or case changes create a new dataset/case version. A metadata-only edit may still change interpretation and must be assessed for compatibility rather than automatically classified as harmless.

**EVAL-026.** Material environment evidence MUST include subject configuration, realization/Plugin/Adapter/provider/Model and dependency versions, available Tools, tenant/policy constraints, resource limits, measurement conditions, time-sensitive inputs and relevant external behavior. Record randomness/seed concepts and selection/order where meaningful, without mandating a random generator or format. An opaque external version MUST be identified as opaque with observation time and limitations; it cannot support a false claim of exact reproducibility.

**EVAL-027.** Reproducibility claims MUST distinguish: exact repeat of declared observable results under exact inputs/conditions; statistical consistency under a stated method/population/tolerance; behavioral preservation of specified properties despite variable output; and external/time-dependent behavior not reproducible from retained evidence. Record what is and is not repeatable, requisite access and preserved evidence, and dependency/measurement limitations. A seed alone does not prove repeatability. No method may promise exact replay beyond the subject's and environment's declared guarantees.

**EVAL-028.** Historical results remain facts about their assessed conditions even when stale or no longer applicable. Applicability MUST bind subject/revisions, configuration, environment, method, data, criteria, threat assumptions and evidence integrity. Freshness/validity requirements identify deciding consumer/policy, time basis and invalidation conditions. Changed Model behavior, retrieval corpus, external API, price/rate, Plugin environment or security assumptions may require new assessment. Re-evaluation creates new records; it does not rewrite the old judgment or silently restore stale evidence validity.

## 8. Uncertainty, confidence, calibration, and missing evidence

**EVAL-029.** Material non-exact assessments MUST expose uncertainty from sample selection/size, measurement, label/oracle error, judge disagreement, environment variability, Model stochasticity, bias/contamination and unknown coverage as applicable. Absence of a numerical uncertainty estimate MUST be an explicit limitation, not zero uncertainty. Distinguish observed facts, inferred population claims, assessor judgments and unsupported unknowns.

**EVAL-030.** A reported confidence/probability/interval MUST identify its meaning, metric/quantity, method/version, sample and target population, assumptions, level where applicable, interval or score interpretation and limitations. A judge's self-reported confidence is not automatically a calibrated probability of correctness or statistical interval. No single statistical method is required. A statement such as “95% confident” without these semantics cannot serve as valid confidence evidence.

**EVAL-031.** Statistical claims MUST state the unit of observation, sampling/repetition design, dependence or clustering assumptions, applicable sample conditions, treatment of repeated runs, uncertainty method and inference limits. Repeated outputs from one case are not automatically independent new cases. Adaptive stopping, multiple comparisons, subgroup search and post-hoc metric selection must be declared with their implications for interpretation. Predeclared decision methods and exploratory findings MUST remain distinguishable; no universal significance level or minimum sample count is imposed.

**EVAL-032.** Calibration evidence MUST identify the predicted quantity, reference outcomes/population, method, sample, version and uncertainty. False-positive and false-negative reports MUST identify positive/negative meaning, reference authority/error, counts or denominator definitions, threshold, population and missing/unlabeled treatment. Precision, recall, accuracy and error rates cannot be interpreted without these meanings. Tradeoffs and operational costs, including uncertain reference labels, MUST remain visible instead of being hidden by a single favorable aggregate.

**EVAL-033.** Missingness descriptors such as not evaluated, unsupported, not applicable, insufficient evidence, measurement unavailable, indeterminate and invalid case/dataset MUST state reason, affected scope and coverage impact. They are assessment vocabulary, not canonical error categories or execution states. Not applicable requires a justified applicability decision; it is not a convenient exclusion of a failing case. No missing/invalid observation may silently become zero, pass or a favorable denominator adjustment.

**EVAL-034.** Assessor execution failure MUST be reported through canonical errors and attempt state independently of subject judgment. A criterion may legitimately judge an independently observed subject timeout, refusal or failed external action; it MUST distinguish that observation from the evaluator failing to observe it. When correctness cannot be established, report insufficient evidence/inconclusive with limitations. A consumer gate may fail closed for insufficient evidence without asserting that the evaluated subject violated the criterion.

## 9. Independence, Human review, and Model judges

**EVAL-035.** Independence claims MUST identify what is independent from what, dimension, evidence, relevant correlations and limitations. Dimensions may include different code path, Model/family, Plugin, publisher, reviewer/organization, data source or method. Different names/instances do not establish independence. Required independence is selected by entitled policy/consumer criteria; complete organizational separation is not universal. Shared training data, providers, reference labels or instructions may correlate errors and must be disclosed where material.

**EVAL-036.** Self-evaluation MAY be evidence but MUST be labeled with overlapping subject/evaluator identities, dependencies and potential conflicts: an Agent critiquing its plan, Model judging its response, Plugin running bundled checks or Team reviewing its work. It MUST NOT satisfy a requirement for independent verification solely because it emits a result record. Self-test execution uses an already admitted governed path; assessing an unadmitted candidate does not authorize running its code to admit itself.

**EVAL-037.** Human assessment MUST bind reviewer identity and scoped Principal/Role eligibility where relevant, instructions/rubric revision, exact subject/cases, criteria/scale, material presentation, time, independence/blinding conditions and inter-rater evidence when claimed. Protect review-channel context and access. Disagreement, fatigue/ordering effects or missing qualifications are assessment limitations where material. Human evaluation is evidence and MUST NOT be represented as HumanApproval unless a separate applicable Approval operation captures an entitled explicit decision.

**EVAL-038.** A Model-based or LLM-as-judge Evaluator MUST pin Model/provider/version or disclose opacity, judge instructions/configuration, reference/context inputs, output interpretation and relevant sampling conditions. Its evidence MUST disclose material risks such as position, verbosity, style and self-preference bias, family correlation, prompt sensitivity, non-determinism and fabricated rationale. Counterbalancing, calibration, independent checks or other mitigations may be required by its criteria/policy, but no one technique or provider is mandated. Untrusted subject content cannot alter judge instructions, reference access or authority through prompt injection.

**EVAL-039.** Reviewer/judge eligibility, method applicability, conflicts and required independence MUST be assessed before claiming the corresponding evidence quality. A human, Model or bundled evaluator cannot claim truth merely by authority label. Adjudication requires a declared method and qualified assessor; its new judgment retains original disagreement rather than overwriting it. Evaluation of evaluators obeys the finite dependency and resource bounds in EVAL-012–013.

## 10. Multi-evaluator composition and aggregation

**EVAL-040.** Composition MAY require all assessments, quorum, weights, hierarchical criteria, fallback or adjudication, but MUST declare required versus optional components, meaning of abstention/missingness, applicability, independence assumptions, disagreement handling, resources and stopping/completion conditions. Fallback is explicit and compatible with required guarantees; an unavailable independent evaluator cannot be silently replaced by self-assessment where independence is mandatory.

**EVAL-041.** Aggregation MUST specify the population/denominator, grouping, units/scales, weights and their authority, missing/invalid/timeout behavior, outlier rules, uncertainty propagation, thresholds and coverage. Micro-style pooling of observations and macro-style combination of group results must be distinguished where used, including group sizes and weights. Compatible arithmetic does not make incompatible criteria comparable. Raw constituent results and required critical findings MUST remain available through governed references; an overall score cannot conceal an applicable mandatory safety violation.

**EVAL-042.** Agreement, disagreement, inconclusive and needs-adjudication are judgment/coordination descriptors, not new Evaluation lifecycle states. Do not average incompatible labels or force consensus merely to yield a pass/fail. Report how divergent methods or reference assumptions affect interpretation. An adjudication judgment MUST identify its scope and method and preserve earlier results and confidence limitations.

**EVAL-043.** Multi-stage assessment may sequence deterministic validation, functional checks, quality assessment, security assessment and Human review. Stage completion does not imply release. Skipped downstream stages MUST report the stopping rule and resulting coverage; a failing prerequisite cannot make unevaluated stages pass. Each effectful stage has governed Execution attribution, explicit dependency/authority/resource requirements and separate result/effect facts.

```text
Diagram 8 — Mixed evaluator composition
same pinned subject/cases --> deterministic checks --+
                          --> Human assessment -----+--> declared aggregation
                          --> Model judge ----------+    + disagreement/limits
                                                         |
                                                   EvaluationResult
required independent evidence missing --> explicit gap/adjudication, not silent fallback
```

## 11. Coverage, slicing, partial evaluation, and fairness

**EVAL-044.** Coverage MUST state what was intended and actually assessed, denominator/population definition, selection method, case identity/version set, observed exclusions and untested dimensions. Dimensions may include operations, capabilities, inputs/edges, failure paths, threats, languages, tenant profiles, classifications, Tools, providers, workflow branches, Roles, resources or lifecycle stages. “100%” without a declared denominator and meaning is invalid; exhausting a finite dataset does not prove complete behavior-space or security coverage.

**EVAL-045.** Partial evaluation MUST expose planned/selected/completed/missing/invalid/skipped case sets, reasons, produced results, remaining obligations, coverage and uncertainty impact. For example, 80 assessed of 100 required cases cannot be reported as a complete 100-case assessment; results may accurately describe the 80 assessed cases and 20 unavailable cases. Correctly recording that partial report is distinct from completing the parent assessment. Cancellation, dependency failure or resource exhaustion preserves completed evidence and incurred/unknown usage. New attempts may cover missing cases through explicitly linked assessments without rewriting original coverage.

**EVAL-046.** Slices MUST identify authorized grouping semantics, population, sample/selection, overlap, denominators and uncertainty; aggregate and slice conclusions may differ and both must remain attributable. Fairness/bias assessment uses domain-specific criteria, methods, populations, legal/policy applicability and limitations; no universal fairness metric is imposed. Sensitive attributes may be used only when legitimately available and authorized, never inferred merely for convenience. Small-group scores, counts and comments may leak protected information and require governed reporting/redaction that preserves honest coverage limitations.

```text
Diagram 12 — Partial evaluation and coverage
planned required set: 100 exact cases
    --> 80 assessed --> per-case judgments + measured aggregate for those 80
    --> 20 unavailable --> reasons + obligations + uncertainty/selection impact
combined report: partial 80/100; no invented values for missing 20
new authorized attempt for missing cases --> linked results, original report unchanged
```

## 12. Functional, Model, Agent, Workflow, and Team evaluation

**EVAL-047.** Functional assessment MUST distinguish exact behavior, semantic correctness and subjective quality. Expected output, permitted state transition, correct target, produced Artifact, completion rule and acceptance evidence each require their own observable basis. A subject's success response alone does not establish all properties. Model assessment may examine task success, output validity, instruction adherence, groundedness, hallucination, safety, robustness, context behavior, latency and cost under declared conditions; no universal Model leaderboard or Agent dependency is required.

**EVAL-048.** Agent assessment MUST identify behavior/state versions, dependencies and allowed work/authority scope, and evaluate observable proposal/planning quality, Tool selection/arguments, completion evidence, boundary compliance, resource use, recovery/escalation and public rationale as relevant. A denied unsafe proposal differs from an actual unauthorized effect: score proposal quality and enforcement behavior separately. Environment/task feasibility and unavailable permissions must be visible. Private reasoning is neither a required input nor an oracle for intent or correctness.

**EVAL-049.** Workflow assessment MUST pin definition/state/Execution and recovery boundaries, then inspect transitions, branches, joins, duplicate signals, bounded loops, waits/resume, checkpoint compatibility, deadlines, cancellation, failure recovery and effect/accounting preservation. A workflow reaching a terminal position does not prove business acceptance. Deterministic/human-only workflows are valid subjects without Agents or Models. Engine-specific state is evidence only through its declared canonical mapping and limitations.

**EVAL-050.** Team assessment MUST support Human, Service and Agent compositions, including child Teams, and pin composition, Roles/assignments, work/delegation and acceptance criteria where relevant. Assess role fulfillment, coordination, handoffs, products, task evidence, goal progress, escalation and resource use without treating the Team as an Actor or granting members pooled authority. Team assessment does not transfer Outcome ownership or replace Work Coordination's acceptance decisions; compare coordination and constituent performance separately when evidence permits.

```text
Diagram 5 — Agent evaluation
Agent behavior/version + task/environment + admitted bounds
    --> observed proposals / mediated Tool attempts / products / usage
    --> planning quality | argument correctness | enforcement behavior
        recovery/escalation | task evidence | public rationale
    --> multidimensional result with uncertainty and coverage
unsafe proposal blocked is not the same observation as unsafe effect executed
```

```text
Diagram 6 — Workflow evaluation
pinned Workflow + starting state + declared cases/failure conditions
    --> transitions / branches / joins / wait-resume / cancellation
    --> checkpoint + prior-effect + accounting observations
    --> invariants and completion-rule judgments
    --> result [tested paths + untested paths + recovery limits]
No engine selection and no automatic Task/Goal acceptance.
```

## 13. Tool, information, direct capability, and composition evaluation

**EVAL-051.** Tool assessment MUST cover applicable targeting/input validation, action/effect identity, result evidence, timeout/unknown effects, safe retry/reconciliation, authority/tenant controls and usage. A confirmed local response differs from confirmed external truth. Simulated or suppressed effects remain labeled. Direct capability and Adapter assessment may evaluate these boundaries independently of Team/Goal/Agent and compare replaceable realizations without adopting their private implementation semantics.

**EVAL-052.** Retrieval assessment MUST distinguish relevance/precision, recall only where the reference universe supports it, ranking, source correctness/freshness, tenant filtering, metadata leakage, provenance and poisoning resistance. Missing relevant-item ground truth limits recall claims. Memory assessment is kind-specific: working/session behavior, semantic recall, episodic fidelity, procedural retrieval, forgetting/retention, isolation and non-restoration of stale authority; vector similarity alone is insufficient. Knowledge assessment retains source accuracy/freshness/confidence, access, supersession and poisoning criteria, without treating stored assertions as automatically true.

**EVAL-053.** Retrieval-augmented generation is a composition. Assessment SHOULD distinguish retrieval, context assembly, generation, grounding/citation and end-to-end output quality when those stages are relevant; one aggregate cannot establish the cause of every failure. Application assessment may combine operational, product, coordination, policy, cost and reliability evidence under its declared intent/criteria. Domain-specific creative/software/research quality stays in scoped evaluators, not mandatory core definitions. Composition failures and dependency interactions require evidence beyond passing isolated components.

## 14. Plugin, security, and adversarial evaluation

**EVAL-054.** Plugin assessment MUST pin release/contributions/Providers/Adapters/Ports, configuration, dependencies, activation and evidence environment. Assess declared capability behavior, closure/optional omissions, configuration, health/freshness, canonical lifecycle, bootstrap, upgrades/coexistence/migration, partial completion, tenant/resource/permission/isolation behavior and replacement compatibility where supported. Metadata claims are subjects to assess, not evidence of their own truth. Plugin self-tests are labeled self-evaluation; no result self-admits a Plugin or turns an inactive contribution into ordinary eligible execution.

**EVAL-055.** Security assessment MUST bind SECURITY's relevant threat/asset, attacker capabilities, boundary, assumptions, expected control behavior, observer access, method, evidence/failure domain and residual limitations. Assess prompt injection, tenant/Secret leakage, escape, deputies, Approval replay, authority/revocation races, resource abuse, spoofing/shadowing, audit suppression, evidence integrity, stale health, bootstrap, migration and downgrade as applicable. A demonstrated violation can be reported precisely; absence of observed exploitation is bounded evidence, not proof of universal safety. Security/Policy decides sufficiency; Conformance defines mandatory proof.

**EVAL-056.** An AdversarialCase/red-team case MUST include identity/version, threat, target asset/subject, attacker capabilities and preconditions, proposed attack-method semantics, authorized scope/environment/effect constraints, expected defense, observable judgment criteria, collection requirements, stop conditions, resource bounds and residual assumptions. Exploit details, leakage probes, privileged scenarios and Secret-like test material require governed access and retention. An attack label or quality-assurance purpose confers no authority to test a real target. Evaluation transparency does not require publishing restricted findings or exploit payloads.

**EVAL-057.** The following consumes SECURITY §28 without replacing its conformance obligations. Approaches are assessment designs only; no attacks or tests are executed in this phase. Every approach distinguishes actual, simulated, observed and unavailable evidence.

| Security area | Evaluation approach / observable evidence | Limits and decision boundary |
|---|---|---|
| Injection resistance and malicious Tool/Artifact/Knowledge content | Authorized varied instruction/data-confusion cases; observe proposals, grants, target actions and disclosures independently | Detection rate and attack corpus do not prove universal resistance; no private reasoning required |
| Cross-tenant leakage | Scoped content/existence/cache/error/lineage probes under declared access scenarios | Report authorized visibility and hidden coverage; privacy may restrict details |
| Plugin isolation/shared-host escape and collusion | Threat-scoped attempts/evidence review for host, peer, credential and state access | Actual environment/threat assumptions pin applicability; logical modules alone prove nothing |
| Secret handling and confused deputy | Purpose/consumer/target mismatch scenarios; observe authorization and public disclosure surfaces | Real material use must be authorized; hidden values not included in reports |
| Approval UI deception/replay | Compare presented material action with exact approved/consumed scope; concurrent/changed-target cases | Human evaluation differs from Approval; channel and eligibility assumptions explicit |
| Resource exhaustion | Bounded stress/amplification cases with authoritative claim/usage evidence | Assessment itself obeys budgets; limited pressure does not establish unlimited availability |
| Namespace/provider spoofing, shadowing and capability claims | Identity/alias/priority/offer-evidence mutation scenarios and exact binding observations | Unknown authority verification cannot be treated as conformant acceptance |
| Stale authority, revocation, health and partitions | Declared schedules of expiry/restriction/hand-off; observe effective order and claims | Sampling races supplies evidence within timing/failure assumptions, not a universal ordering proof |
| Audit denial-of-service/suppression | Missing/late pre-evidence versus post-effect custody-loss scenarios; observe handoffs and obligations | No repeated external effect to recreate evidence; bounded failure domain |
| Evidence tampering/forgery | Altered/stale/incorrect-subject evidence scenarios with custody/verifier observations | Claims limited to declared adversary and integrity guarantee |
| Bootstrap/identity authority compromise | Bounded root/self-trust/cycle/replacement scenarios and authority-chain review | Accepted initial assumptions remain explicit; no evaluator becomes the root |
| Migration and security downgrade | Exact old/new state/profile/configuration cases, revoked-grant restoration attempts | Preserve partial effects and history; no unauthorized real migration |
| Break-glass abuse | Expiry/scope/non-waivable-constraint/review-obligation cases | Evaluate evidence against declared Governance rules, never appoint an exception authority |
| Side-channel leakage | Approved observation of relevant timing/shared-resource channels under pinned threat assumptions | No blanket absence claim outside measured channels or sensitivity |

```text
Diagram 7 — Plugin and security assessment
exact Plugin/config/dependencies/isolation environment + declared threats
    --> authorized assessment scope + bounded adversarial cases
    --> observed lifecycle/authority/effects/tenant/resource/evidence behavior
    --> EvaluationResult [claims, findings, coverage, uncertainty, residual assumptions]
    --> separate Security/Lifecycle decision if entitled
No self-admission, unrestricted red-team authority or universal safety claim.
```

## 15. Robustness, failure modes, execution errors, and retries

**EVAL-058.** Robustness assessment MUST declare variations such as phrasing/order/noise, missing/ambiguous fields, hostile input, provider delay/failure, dependency outage, stale evidence or resource pressure, and the expected invariant or acceptable change. Distinguish graceful refusal/safe waiting from successful task performance. Results must identify which variation/failure schedule was actually applied and whether the observer could verify the relevant behavior.

| Failure condition | Assessment evidence and expected distinction |
|---|---|
| Timeout / lost acknowledgment | Named action's known/unknown effect and retained liability; no inferred none |
| Duplicate request | Same equivalence identity and owner outcome, no new independent effect within guarantee |
| Unknown effect | Reconciliation/safe retry/intervention behavior; uncertainty retained |
| Partial completion | Actual per-owner committed facts and outstanding obligations; no global atomicity assumption |
| Dependency failure | Causal failure and affected scope; no undeclared weaker fallback |
| Network partition | Joint-current authority/claim validity or fail-closed behavior under declared guarantee |
| Stale health | Hard eligibility predicate cannot be satisfied by stale projection |
| Expired Grant / revoked Approval | No later protected dispatch when restriction wins order; prior effects retained |
| Resource exhaustion | Controlled refusal/wait/stop with no accounting reset or copied balance |
| Invalid checkpoint | Compatibility/current authority checked; revoked Secrets/spent resources not restored |

**EVAL-059.** Evaluator operations MUST use the existing canonical error categories: ValidationError, CapabilityUnavailable, CapabilityResolutionError, AuthorizationDenied, PolicyViolation, BudgetExceeded, DeadlineExceeded, DependencyFailure, ExecutionFailure, ToolFailure, ModelFailure, HumanRejected, Conflict, VersionMismatch, TenantViolation and PluginFailure as applicable. Preserve the most specific safe cause, effect status and recoverability. Model judge failure is not a new JudgeError; unsupported mandatory method/versions use existing validation/capability/version categories. Explicit Human rejection of a required Approval differs from a Human reviewer's negative quality judgment.

**EVAL-060.** Retransmission MUST preserve operation/run identity and exact equivalence, expected revisions and intended effect identity under Contracts §5. A genuine execution retry creates a new linked attempt/run/Evaluation, pins the same subjects/data/method/configuration when claiming comparable retry, preserves partial results and cumulative accounting, and retains the intended effect identity where relying on deduplication. A changed case set or Evaluator is new assessment meaning, not an equivalent retry. Late observations are linked corrections/results, not overwritten history.

**EVAL-061.** Assessment may itself cause disclosure, Model charges, Tool mutations, human work or external effects. Timeouts and partial failures MUST retain actual/unknown effects, claim liabilities, produced Artifacts and obligations. Repairing result publication/audit cannot repeat the already performed assessment/subject effect merely to reconstruct records. EvaluationResult recording completion is separate from parent suite completion. No universal exactly-once behavior, atomic cross-owner commit or safe repeated production experiment is assumed.

## 16. Cost, latency, efficiency, and reliability

**EVAL-062.** Cost/resource measurements MUST name dimensions/units, authoritative accounting versus telemetry/estimate source, scope, measurement interval, quantities and uncertainty, applicable rate/conversion versions where used, and exclusions. Token, money, compute, storage, Tool/API calls, time and Human-review capacity are distinct dimensions; no universal currency/tariff is selected. Separate subject cost from evaluator/judge/collection cost, retries, setup/migration and unresolved external charges. Unknown usage is not zero and cancellation does not refund incurred measurement cost.

**EVAL-063.** Latency MUST name both boundaries and their acknowledgment meanings, time basis/uncertainty, units, population, completed/timeout/cancelled inclusion, sampling and aggregation. Request→accepted, admitted→started, started→first-result, started→completed and dispatch→effect-confirmed measure different things. Record censoring or unavailable endpoints explicitly; do not silently omit slow timeouts from favorable summaries. Report quantile/distribution estimates with method and sample limitations where used; a single number without interval semantics is insufficient.

**EVAL-064.** Efficiency metrics MUST define denominator and success/acceptance source: cost per successful Execution, accepted Task result or published/accepted Artifact are different. Required acceptance evidence comes from the entitled owner, not the evaluator inventing acceptance. Include retry/waste and missing-success treatment explicitly; zero successful cases makes per-success cost undefined or otherwise explicitly defined, not automatically zero. Tradeoffs cannot silently prioritize cheap behavior over mandatory correctness/security. Measurement is not authorization to exceed a resource limit.

**EVAL-065.** Reliability/availability/recovery rates MUST identify eligible trials/time windows, declared failure model, success criterion, observation completeness, dependencies, reconciliation/deadline behavior and uncertainty. Safe refusal during unprovable authority may satisfy safety while reducing availability; report both. Recovery assessment must preserve earlier effects and resource accounting. Evaluation admission itself obeys Budget/Quota/Limit, concurrency, deadlines, Model/Tool/Human capacity and bounded graph/loop/comparison work. Dependency expansion, pairwise growth, full-corpus reruns and recursive judge/adjudication work require explicit bounds and controlled exhaustion behavior.

## 17. Operational results, Artifacts, Outcomes, and decisions

**EVAL-066.** Operational result quality and correctness MAY be assessed without Goal, Team, Organization or canonical Outcome. A Tool may complete its action while the produced work fails a quality criterion; a safe refusal may meet a security criterion but not complete the user's task. SPEC DEC-01 remains authoritative. When evaluating an existing canonical Outcome, pin its assessment/evidence and accountable Team; the evaluator does not become that Team, create ownership, or declare Organization-owned Goal achievement by scoring a result.

**EVAL-067.** Artifact assessments MUST pin exact ArtifactVersion and relevant content interpretation, lineage/access/evidence. Current aliases may be resolved before binding but cannot substitute later content. Important evaluation reports/results SHOULD be preserved as Artifacts according to SPEC E-07, with ownership, tenant, retention and provenance; an immutable EvaluationResult is not automatically identical to its rendered report or Artifact. Content unavailability is explicit, and a report cannot falsely claim inspected content that was inaccessible.

**EVAL-068.** Quality/release gates MUST bind exact subject, required result references, criteria/threshold versions, applicability/freshness, minimum coverage/independence/uncertainty, governing Policy and accountable decision owner. Evidence sufficiency and the actual authorized decision remain separate from EvaluationResult. Gate outcomes may refuse/wait for insufficient evidence without claiming subject failure. No assessment directly activates a Plugin, approves deployment, modifies Policy, accepts a Task, or creates an Outcome. Multi-stage release evidence does not prescribe a deployment pipeline.

```text
Diagram 9 — Evaluation evidence to governed decision
EvaluationResult + exact applicability/coverage/uncertainty + required other evidence
    --> authorized consumer checks current evidence requirements
    --> Policy/Governance/Security or acceptance owner decision
    --> separate admitted action only with current authority/claims
High score cannot substitute for grant, Approval or mandatory evidence.
```

## 18. Comparison, regression, and evidence freshness

**EVAL-069.** Comparison MUST identify exact subjects/results, baseline, Evaluator/method versions, same/different cases and sampling, configuration/environment, normalization and its justification, uncertainty/aggregation, coverage, missingness and limitations. Changes to multiple dimensions must remain visible; improvement cannot be attributed to one changed component without supporting design/evidence. Incompatible methods/scales/populations yield an explicit limited, non-comparable or inconclusive assessment rather than forced ranking.

**EVAL-070.** Regression means deterioration under a declared criterion, exact baseline, comparison rule and meaningful-change threshold or significance/decision semantics. Not every numerical difference is regression. Separate observed magnitude, practical threshold, statistical uncertainty and known coverage/confounding; a method may use deterministic invariants or statistical criteria without universal significance defaults. Post-hoc exploration cannot masquerade as a predeclared regression gate.

**EVAL-071.** Release comparisons MAY assess Models, prompts, Skills, Agents, Workflows, Tool Adapters, Plugins, Retrievers, Memory, Policy evaluators and Application revisions. Prompt/judge instruction changes are behaviorally material where they affect outputs; replacing a Model is a dependency change requiring evidence applicability review. Preserve changed and held-fixed variables, independent repeat conditions, baseline limitations and per-slice findings. Candidate selection using benchmark results must disclose subsequent reuse/overfitting risks rather than treating the same evidence as independent confirmation.

**EVAL-072.** Pairwise comparisons MUST define order/presentation, tie/abstain meaning, assessor/method, sample pairing, normalization, uncertainty and aggregation. A pairwise preference under one context does not establish a universal total ranking or transitive superiority. Where a baseline or candidate is unavailable/stale, report that limitation. Replacing a baseline or changing threshold requires a new governed revision and explicit impact on subsequent decisions; historical comparisons remain pinned.

```text
Diagram 4 — Regression comparison
baseline subject/result + exact conditions ----+
candidate subject/result + exact conditions ---+--> comparability assessment
                                                  |
                            declared criterion/change rule + uncertainty + coverage
                                                  |
                          regression / no detected regression / inconclusive
                          with magnitude, assumptions and limitations
No detected regression is not proof of all required behavior.
```

## 19. Offline, simulation, shadow, production, and drift evaluation

**EVAL-073.** Evaluation mode MUST be explicit: offline retained evidence, staging/simulation, shadow, or online/production work. These describe evidence/interaction conditions, not required deployments. Simulation must identify modeled versus actual behavior, fidelity/assumptions and unmodeled effects; it cannot be represented as observation of a real external system. Offline data remains access/tenant/retention governed. Production assessments require current authority for every real disclosure/effect and declared safety/stop/resource bounds.

**EVAL-074.** Shadow/replay evaluation MUST preserve originating tenant, data classification, source versions, Secret restrictions and effect-equivalence history. Declare which effects are suppressed, simulated or actually authorized, and verify the claimed boundary; calling a run “shadow” does not prevent Tool/Model charges or external writes. Fresh execution of a historical request is not automatic authority to repeat its business effects. Simulated successes remain distinct from real effect confirmation.

**EVAL-075.** Continuous/drift assessment may be triggered pre-merge, pre-release/admission, post-release, periodically, on incident or on changes to Model/prompt/Skill/Tool/Plugin/dependency/Policy/dataset/security assumptions. A trigger schedules a request, not access or budget permission. Bind an exact observation window, baseline, change criteria, selection method, sensitivity/uncertainty, false-alarm/missed-change limitations and applicable environment. Drift produces evidence; configuration changes, rollback or trust revocation are separate entitled decisions, not silent evaluation side effects.

**EVAL-076.** Monitoring detects/records conditions; Evaluation interprets observations against criteria. A telemetry alert is not automatically an EvaluationResult. Trace, telemetry, audit, provenance, accounting and Evaluation remain distinct owners/meanings; source completeness, sampling, privacy filters and timing limitations accompany measurements. Production-observation data may differ from planned cases; report selection/exposure bias, missing failures, changing workloads and limited causal attribution. Continuous evaluation does not justify unbounded retention or perpetual access.

```text
Diagram 11 — Continuous and drift assessment
release / incident / schedule / provider or corpus change
    --> governed Evaluation request --> exact subject/window/baseline binding
    --> authorized observation/assessment --> drift evidence + uncertainty
    --> separate consumer decision / further evaluation request
monitoring alert is input; no automatic configuration or authority mutation
```

## 20. Governance, provenance, privacy, and evidence consumption

**EVAL-077.** Evaluator, criterion/metric, threshold, dataset/case/suite and baseline publication/change MUST have an accountable owner, entitled publishing Principal, scope, immutable versions and expected-revision semantics. Evaluation Management owns assessment meaning; Artifact/source owners retain their state; no new universal governance authority is appointed. Cases, prompts, outputs, scores, comments, findings and adversarial details have access/classification/retention rules. Evaluation purpose alone grants no privileged subject or cross-tenant access.

**EVAL-078.** Results MUST answer what exact subject/configuration was assessed, by which evaluator/realization and criteria, using which cases/data/selection, under which environment/dependencies, when, with which observed evidence, uncertainty/coverage and limitations. Preserve assessor, tenant, Principal/Execution/effect, source authority and causal provenance through safe references. Reviewer comments and rationale are governed public/authorized evidence, not private reasoning requirements. Sanitized reports retain truthful scope/limitations and do not falsely imply full evidence disclosure.

**EVAL-079.** A consuming Security, Governance, Plugin admission, release gate, Application or Conformance decision MUST verify subject/configuration/environment match, evidence integrity/custody, freshness, supported scope, Evaluator method/authority/required independence, dataset relevance/contamination, coverage, uncertainty and limitations. Freshly recorded old observations are not automatically fresh behavior evidence. An unavailable restricted underlying finding may be represented by adequate authorized attestations only where governing requirements permit; it cannot be replaced with a favorable unverified assertion.

**EVAL-080.** Evidence retention MUST account for reproducibility, security/incident obligations, privacy, tenant deletion, usage/license constraints and permitted minimal history through Security/Governance. No legal precedence or indefinite retention right is invented here. Missing content after permitted disposition or record loss must be explicit; old identifiers do not prove retrievability. Required pre-evidence failures block protected assessment effects; post-effect result/evidence custody failures create Contracts obligations and never justify repeating the original external effect. Resource/retention changes and evaluator dependency recursion remain bounded governed work.

## 21. Evaluation matrices

**EVAL-081.** The following matrices are normative scope guides through their enclosing requirements, not universal mandatory feature bundles. Support must be explicitly declared. Every row inherits exact binding, governed execution, canonical errors, privacy, resource and evidence rules. Uncertainty is required whenever material, including limits of finite deterministic-case coverage. All judgments remain evidence with the row's authority limits.

### 21.1 Subject evaluation matrix

| Subject type | Possible criteria | Required identity/version pins | Possible evidence | Uncertainty required? | Security/tenant considerations | Typical regression basis | Result authority limits |
|---|---|---|---|---|---|---|---|
| Model | Task quality, output validity, grounding, robustness, latency/cost | Model/provider, prompt, inputs, config, Evaluator/cases | Outputs, reference labels, usage, authorized observations | Stochasticity, sampling, oracle and opaque version limits | Disclosure/training/retention/residency and output trust | Prior exact Model/prompt under comparable cases | No truth, permission or leaderboard-wide superiority implied |
| Agent | Planning/proposals, Tools, completion, recovery, bounds | Behavior/state, work, Tools/Models/Skills, grants/criteria | Public proposals/actions, effects, products, usage | Task/environment variation and assessor limits | No private reasoning; proposals distinct from effects | Prior behavior/configuration with same feasible scope | No authority from rationale or automatic Task acceptance |
| Workflow | Transitions/joins/waits/recovery/effect preservation | Definition, state/checkpoint, Execution and dependencies | Transition/effect/accounting records | Coverage and failure/timing assumptions | Current resume authority and scoped checkpoints | Prior definition/driver over matched paths | Terminal run not Goal achievement |
| Team | Roles, delegation, handoff, products, coordination | Composition/assignments, work/criteria and exact products | Attributed Actor work and acceptance evidence | Human/composition/task variability | Team not Actor or pooled authority; reviewers scoped | Prior composition under comparable work | Team retains Outcome ownership; evaluator cannot accept globally |
| Tool | Target/input/effect/retry/authority/usage | Tool/Adapter/Port/provider, action/target/effect versions | Dispatch/result/reconciliation and external evidence | Unknown external effects and observer coverage | Real effects require permission/approval and Secret bounds | Prior realization under same declared effect contract | Success response not absolute external truth |
| Retrieval | Relevance/ranking/recall/freshness/filtering | Retriever, corpus/query/config, source snapshots | Authorized relevance labels/results/access evidence | Incomplete relevance universe and sampling | Filter before disclosure; existence leakage | Prior retrieval/corpus with differences exposed | No generation/Agent required or retrieved truth assumed |
| Memory | Kind-specific recall/update/forgetting/fidelity | Kind/contract/implementation, entries/session/state | Governed reads/updates/disposition evidence | Recall reference and retention observation limits | Scope preserved; stale authority not restored | Prior kind-specific behavior/state compatibility | Not vector similarity alone or driver state ownership |
| Knowledge | Sources, freshness/confidence, supersession | Collection/records/source revisions and criteria | Curation/reference/source lineage | Unknown truth/source reliability | Access/classification and poisoning | Prior curation/source versions | Claims do not become verified truth/Policy |
| Plugin | Lifecycle, closure, health, migration, isolation | Release/contributions/activation/config/deps/environment | Admission refs, effects, lifecycle/security observations | Failure-domain and threat coverage | No self-admission or unadmitted execution | Compatible prior release/realization | Evidence only; no admission/certification |
| Artifact | Requirements fit, integrity, quality, lineage | Exact ArtifactVersion, content interpretation and rubric | Authorized content/reference/production evidence | Creative/oracle and access limits | Exact approved version; content remains untrusted | Prior exact version/rubric | Publication/quality is not safety or acceptance authority |
| Security control | Boundary behavior, detection/error tradeoffs | Control/Policy/profile, threat/environment/evidence versions | Authorized adversarial and normal-case observations | False positives/negatives, untested threats | No testing bypass, restricted findings | Prior exact control/threat conditions | No perfect safety, grant or final Conformance proof |
| Direct capability | Declared inputs/outputs/errors/governance | Capability/Port/Provider/Adapter and binding versions | Governed call/result/effects | Method and finite coverage limits | Normal context/resource checks without fabricated Team | Prior contract-compatible realization | Operational result need not be Outcome |
| Application | Intent fit, end-to-end products/coordination/reliability | App/composition/configuration/criteria/dependencies | Authorized cross-module products and evidence | Workload/selection/confounding | All policy/tenant boundaries; evaluation access scoped | Prior exact Application revision under comparable scope | No deployment/Goal/Outcome decision by score |

### 21.2 Method matrix

| Method | Deterministic/probabilistic | Typical subjects | Required evidence | Strengths | Limitations | Reproducibility | Independence considerations |
|---|---|---|---|---|---|---|---|
| Exact assertion | Deterministic predicate over pinned observations | Functions, outputs, field/state checks | Exact input/expected/actual and equality semantics | Precise narrow claim | Wrong oracle or untested inputs | Exact where inputs/environment preserved | Same code generating expected/actual may share defect |
| Property/invariant check | Deterministic rule; selection may vary | Lifecycle, accounting, boundaries | Property/version, observed state/effect cut and cases | Checks relational guarantees | Observation/coverage incomplete | Behavioral, or exact for fixed observations | Observer/source trust and shared implementation matter |
| Reference/golden comparison | Exact or interpreted judgment | Outputs, transformations, labels | Attributable reference version and tolerance | Clear expected behavior when known | Reference error/contamination; no unique golden creative answer | Depends on reference/subject variation | Reference authority/conflicts explicit |
| Statistical evaluation | Probabilistic inference | Rates, distributions, quality | Sampling/design/counts/method/assumptions | Quantifies measured variability | Bias, dependence and limited population reach | Statistical under declared conditions | Shared samples/labels/dependencies affect correlation |
| Human review | Judgment with variability | Open-ended products, plans, findings | Reviewer eligibility/rubric/presentation and judgments | Context-sensitive assessment | Bias, inconsistency, cost and missing expertise | Behavioral/agreement bounds, not automatic exactness | HumanEvaluation not Approval; blinding/independence scoped |
| Model-based judge | Probabilistic evidence even if one output is repeatable | Quality, relevance, comparative work | Judge Model/prompt/config/output/reference and calibration | Scalable structured assessment | Bias, injection, family correlation, fabricated rationale | Declared stochastic/opaque-provider limits | Self/family/dependency overlap labeled |
| Pairwise comparison | Human/Model/statistical or exact rule | Candidate outputs/realizations | Paired subjects, order, ties, scale and method | Relative assessment under matched context | Context dependence, nontransitivity and bias | Depends on method/order/environment | Same judge/reference does not prove independent confirmation |
| Adversarial/red-team | Deterministic cases or adaptive exploration | Security, robustness, recovery | Threat/attacker/scope/cases/defense observations | Finds concrete failure modes | No-exploit does not prove absence | Exact case replay or bounded exploratory repeatability | Attacker/assessor/control dependencies and privileges declared |
| Simulation | Model-based; may be deterministic/stochastic | External effects, failure schedules | Simulation/version/assumptions and modeled observations | Safe bounded exploration when contained | Fidelity gap; not real external behavior | Within simulator/seed/input limits | Simulator may encode the same mistaken assumptions |
| Production observation | Observational, often statistical | Quality, cost, latency, drift | Authorized window/workload/source completeness | Real usage evidence | Selection bias, confounding and hidden failures | Time-limited statistical/behavioral claims | Observer and subject coupling disclosed; no new effect authority |

### 21.3 Result dimension matrix

| Dimension | Required meaning | Must not be collapsed into |
|---|---|---|
| Evaluation status | Canonical requested/running/completed/failed/cancelled | Subject pass/fail |
| Execution/run status | Actual Execution lifecycle and linked run identity; begun/effect facts preserved | Evaluation judgment or new invented lifecycle |
| Operation disposition | Contracts pending/completed/failed/refused for named interaction | Completion of the entire suite |
| Judgment | Declared boolean/category/ordinal/qualitative/comparative scale | Grant, Approval, admission or authoritative Outcome |
| Metric | Versioned method, scale/units, denominator and interpretation | An unexplained numeric score |
| Coverage | Intended versus assessed scope and omissions | Universal completeness or favorable denominator rewrite |
| Uncertainty | Material sampling, measurement, judge/oracle/environment limits | Zero error or confidence from an unsupported percentage |
| Freshness | Observation time, validity rule and material changes | Updated record timestamp or erased historical result |
| Applicability | Exact subject/config/environment/method/data/threat match | General endorsement of all versions/uses |
| Limitations | Known unknowns, reference, independence and reproducibility bounds | Optional prose that hides mandatory unmet evidence |
| Effects/resources | Named none/partial/completed/unknown effects and actual/unknown usage | Subject judgment, refunded cost or harmless timeout |
| Provenance/evidence | Assessor/source, pinned inputs, authority and custody/access references | Private chain-of-thought or new security authority |

## 22. Inputs provided to CONFORMANCE.md

**EVAL-082.** Conformance MAY reuse evaluation evidence but MUST define which mandatory canonical obligations and supported profiles it proves, including required scenarios, assurance, failure domains and completeness. An evaluator saying “looks compliant” or producing a favorable average does not establish conformance. Evaluation evidence may be a component of that proof; it cannot relax canonical requirements through sample averages or subjective weighting.

| Input provided | Meaning preserved for Conformance |
|---|---|
| Evaluation identities/version semantics | Canonical attempt and immutable bindings; run records do not create a competing lifecycle |
| EvaluationResult semantics | Separate judgment, status, metrics, effects and authoritative consumer decisions |
| Coverage semantics | Explicit denominator, tested/untested cases, slices, partial completion and selection limits |
| Uncertainty semantics | Methods, population/sample assumptions, missing evidence, confidence and calibration limits |
| Evaluator evidence | Exact method/realization versions, required independence, self-evaluation and assessor applicability |
| Security/adversarial evidence | Threat/asset/attacker/control/failure-domain observations, authorized scope and residual assumptions |
| Regression evidence | Pinned baseline/comparator, compatible methods/data/environment, meaningful-change rule |
| Dataset/case provenance | Immutable membership/expectations, ownership, sampling, labels, contamination and usage restrictions |
| Reproducibility limits | Exact/statistical/behavioral/non-reproducible distinctions and preserved-input guarantees |
| Subject/environment pinning | Capability/Port/Plugin/Model/configuration/dependency/threat conditions needed to interpret evidence |
| Evidence access and retention | Source integrity/custody, redacted findings, availability/tombstones and permitted use |

**EVAL-083.** This phase MUST NOT finalize mandatory conformance profiles, official certification, implementation test suites, release certification authorities, wire schemas or testing frameworks. It does not select mandatory business quality thresholds. Those owners may consume this model and define independently testable supported obligations without redefining Evaluation, security or Plugin semantics.

**EVAL-084.** Future conformance work SHOULD verify observable evaluation behavior: invalid/changed version binding rejected; missing cases not silently passed; canonical statuses preserved; probabilistic claims disclose methods/uncertainty; self-evaluation cannot satisfy required independence; Model/Human judges cannot issue authority; retries preserve effects/costs; hidden reference access is controlled; incompatible comparisons are explicit; partial results remain interpretable; and evidence consumers check applicability. These are handoff obligations, not tests built or run here.

```text
Diagram 10 — Evaluation and Conformance
Evaluation --> scoped measurements/judgments/evidence + uncertainty/coverage
                         |
                         v
Conformance owner --> mandatory canonical obligations + required proof criteria
                         |
                    assess evidence sufficiency and supported scope
                         |
                    conformance finding under declared authority
Good quality score cannot replace mandatory behavioral proof.
```

## 23. Inherited questions and risks

**EVAL-085.** Every inherited item below remains tied to its next owner and exit criterion. Partial advancement means improved assessment/evidence semantics, not final implementation or Conformance proof. Unchanged items remain governed upstream; no omission creates permission to weaken them.

### 23.1 SPEC questions

| ID | Disposition here | Next owner | Exit criterion |
|---|---|---|---|
| Q-02 | Unchanged/carried: evaluation uses one operational tenant, explicit crossing | GOVERNANCE / SPEC | Accepted upstream amendment before co-ownership; scoped assessment remains default |
| Q-03 | Partially advanced: assessor/reference authority and certification-claim provenance explicit | GOVERNANCE / CONFORMANCE | Actual namespace/assessor/certifier entitlement and scheme rules appointed |
| Q-04 | Materially advanced: exact evidence, uncertainty, coverage and independence inputs supplied (§22) | CONFORMANCE / GOVERNANCE | Named mandatory supported sets and sufficient-proof requirements approved |
| Q-05 | Unchanged precedence; evaluation thresholds/retention/gates require entitled authority | GOVERNANCE / domain authorities | Applicable conflict/exception/retention resolvers and precedence approved |
| Q-06 | Partially advanced: cost/latency sources, units, unknowns and measurement boundaries (§16) | Resource CONTRACT profiles / GOVERNANCE | Approved precision, time, conversion, uncertainty and settlement parameters |
| Q-07 | Materially advanced: failure-domain, recovery, evidence availability and reproducibility assessment (§§7, 15–16) | CONFORMANCE / capability profiles / ADRs | Required guarantees tested with sufficient evidence for stated profiles |
| Q-08 | Unchanged core vocabularies; narrow assessment vocabulary declared (§3) | CONTRACT vocabulary governance / GOVERNANCE | Needed representation/domain vocabulary accepted without new global entities |

### 23.2 Architecture risks

| ID | Disposition here | Next owner | Exit criterion |
|---|---|---|---|
| R-01 | Unchanged/preserved: Evaluation uses existing owners and allowed dependencies | ARCHITECTURE / CONFORMANCE | No hidden core-to-adapter or Intelligence-to-Evaluation dependency |
| R-02 | Partially advanced: bootstrap/security assessment evidence, not self-trust | GOVERNANCE / bootstrap ADR / CONFORMANCE | Independent admitted root and finite graph proven under chosen realization |
| R-04 | Partially advanced: race/failure schedules and observer limits recorded (§14–15) | Dispatch/claim ADRs / CONFORMANCE | Required joint-valid dispatch/revocation guarantee proven, not inferred from sampled success |
| R-05 | Unchanged/preserved: assessment statuses never add Plugin states | CONFORMANCE / SPEC if expansion requested | Only upstream permitted transitions in implementation |
| R-06 | Materially advanced: threat/environment-pinned isolation and residual-channel evidence (§14) | Isolation ADRs / CONFORMANCE | Sufficient actual containment proof against admitted threats, beyond favorable score |
| R-07 | Materially advanced: partial-progress/effect/accounting observations and failure cases (§15) | CONFORMANCE / ADRs | Lost/partial operations preserve owner facts and never replay original effects for evidence repair |
| R-08 | Partially advanced: evaluator recursion bounded; evidence roots remain upstream (§§4, 20) | GOVERNANCE / evidence ADRs / CONFORMANCE | Finite admitted custody/enforcement basis and privacy/failure guarantees demonstrated |

### 23.3 Contract risks

| ID | Disposition here | Next owner | Exit criterion |
|---|---|---|---|
| CR-01 | Unchanged security choice; assessment distinguishes safety/availability under uncertainty | ADRs / CONFORMANCE | No stale dispatch under declared failure assumptions; availability limits evidenced |
| CR-02 | Partially advanced: run retransmission/retry/horizon semantics (§15) | CONTRACT profiles / CONFORMANCE | Retention and retry windows align; outside-horizon uncertainty not replayed unsafely |
| CR-03 | Unchanged: evaluator cannot refund consumed Approval or grant replacement entitlement | GOVERNANCE / CONFORMANCE | Entitled linked reissue process preserves prior effects and use counts |
| CR-04 | Materially advanced: scoped/redacted findings with honest evidence/coverage limits (§20) | GOVERNANCE / evidence profiles / CONFORMANCE | Reports support authorized review without leaking tenants, cases or exploit details |
| CR-05 | Materially advanced: evidence availability and reproducibility limitations distinguish identity from content (§§7, 20) | Artifact/evidence profiles / CONFORMANCE | Historical retrieval/loss/disposition claims match actual retention guarantees |
| CR-06 | Unchanged/preserved: favorable result/publication cannot activate Plugin | CONFORMANCE | Negative cases reject implicit activation and ineligible execution |
| CR-07 | Partially advanced: finite evaluator/meta-evaluator graph consumes established roots | GOVERNANCE / bootstrap ADRs / CONFORMANCE | No recursive self-approval/evidence or unbounded meta-evaluation |

### 23.4 All Plugin-specific risks (PLUGIN-SPEC §23)

| Risk | Disposition here | Next owner | Exit criterion |
|---|---|---|---|
| Dependency explosion | Partially advanced: bounded graph assessment/cost and failure observations | Resolution profiles / CONFORMANCE | Adversarial graph completion/refusal within bounds without dropping mandatory edges |
| Provider shadowing | Partially advanced: namespace/alias/priority/stale-projection cases | GOVERNANCE / Catalog ADR / CONFORMANCE | Pinned binding remains protected under sufficient adversarial evidence |
| Namespace impersonation | Unchanged authority rules; assessment records issuer/transfer assumptions | GOVERNANCE / identity ADR / CONFORMANCE | Actual accepted authority verification resists impersonation |
| Capability spoofing | Materially advanced: claim-versus-observed behavior, scoped oracle and evidence | EVALUATION implementations / CONFORMANCE | Required behavior evidence independently adequate; claims alone cannot pass gates |
| Stale health evidence | Materially advanced: timed applicability/drift and partition observations | Health profiles / CONFORMANCE | Stale evidence cannot satisfy mandatory use predicate under declared guarantee |
| Hidden implementation coupling | Partially advanced: comparative replacement under matched contracts | ARCHITECTURE / CONFORMANCE | Different realizations preserve consumer meaning without hidden dependency |
| State migration incompatibility | Partially advanced: version-pinned partial migration and failure cases | State profiles / CONFORMANCE | Target rejects incompatible state and preserves original effects/scope |
| Configuration drift | Partially advanced: environment applicability and drift results | Lifecycle profiles / CONFORMANCE | Changed configuration invalidates relevant stale evidence before unsafe use |
| Partial activation | Partially advanced: owner-local status/effects/results distinguished | CONFORMANCE / ADRs | Partial publication/audit does not create false activation completion or duplicate setup |
| Contribution publication races | Partially advanced: exact activation/offer revision and late-message cases | Catalog profiles / CONFORMANCE | Late publication cannot restore stopped/revoked eligibility |
| Shared-host escape | Materially advanced: threat-scoped actual versus simulated evidence and residual risks | Isolation ADRs / CONFORMANCE | Required containment supported by adequate proof, not no-observed-escape alone |
| Trust bootstrap circularity | Unchanged trust basis; finite assessment assumptions explicit | GOVERNANCE / bootstrap ADR / CONFORMANCE | Independent roots established and unresolved cycles rejected |
| Extensions becoming de facto core | Partially advanced: baseline contract versus extension-dependent comparison | GOVERNANCE / ARCHITECTURE / CONFORMANCE | Independent base contract behavior demonstrable without hidden extension |
| Version coexistence conflicts | Partially advanced: concurrent-version state/effect/resource scenarios | State profiles / CONFORMANCE | Coexistence preserves deduplication, scope, state interpretation and conservation |
| Silent guarantee weakening | Materially advanced: multidimensional regression cannot mask mandatory failure | Contract authorities / CONFORMANCE | Replacement proves all required guarantees, not favorable average only |

### 23.5 All Security-specific risks (SECURITY §30)

| Risk | Disposition here | Next owner | Exit criterion |
|---|---|---|---|
| Identity-provider compromise | Materially advanced: scoped compromised-issuer/recovery assessment evidence | GOVERNANCE / identity ADR / CONFORMANCE | Independent recovery and bounded acceptance proven within threat model |
| Overbroad delegation | Partially advanced: multi-hop/deputy observable authority cases | GOVERNANCE / CONFORMANCE | No amplification of granted scope/resources/deadlines |
| Policy conflict ambiguity | Unchanged authority question; incomplete applicability cannot score as allow | GOVERNANCE / domain authorities | Entitled conflict resolution/precedence established and tested |
| Break-glass abuse | Materially advanced: expiry/scope/non-waivable/review cases and evidence | GOVERNANCE / CONFORMANCE | Bounded emergency authority and post-review demonstrated; no evaluator exception |
| Trust-root compromise | Partially advanced: explicit root assumptions and recovery observation limits | GOVERNANCE / bootstrap ADR / CONFORMANCE | Independently authorized recovery exists outside compromised basis |
| Approval UI deception | Materially advanced: presented-versus-approved action and Human-review evidence | Approval-channel ADR / CONFORMANCE | Material deception/misbinding does not produce valid Approval use |
| Secret confused-deputy attack | Partially advanced: purpose/consumer/target mismatch cases | Secret/Tool ADRs / CONFORMANCE | Privileged Secret cannot serve unauthorized request scope |
| Cross-tenant metadata leakage | Partially advanced: classified existence/cache/lineage/error probes | Isolation/evidence profiles / CONFORMANCE | Metadata confidentiality holds under claimed access assumptions |
| Side-channel leakage | Materially advanced: channel/sensitivity/environment-specific measurements | Isolation ADR / CONFORMANCE | Relevant channels addressed with honest residual bounds, no universal absence inference |
| Privileged Plugin collusion | Partially advanced: multi-contribution threat cases and dependency attribution | GOVERNANCE / isolation ADR / CONFORMANCE | Claimed containment withstands admitted colluding capabilities |
| Audit denial-of-service | Materially advanced: pressure/availability/precondition/post-repair evidence | Evidence/resource profiles / CONFORMANCE | Bounded failure retains no-dispatch safety and honest evidence gaps |
| Evidence forgery | Partially advanced: stale/altered/wrong-subject evidence cases | Evidence ADR / CONFORMANCE | Required verifier/custody guarantees demonstrated against stated adversary |
| Security-control downgrade | Partially advanced: old profile/config/rollback comparative cases | GOVERNANCE / CONFORMANCE | Current mandatory controls cannot be silently weakened |
| Stale security profile | Partially advanced: result applicability invalidation under environment/threat changes | Profile governance / CONFORMANCE | Changed conditions trigger reassessment before stale assurance is relied on |
| Revocation propagation failure | Partially advanced: effective-order schedules and missing-observation limits | Dispatch/identity ADRs / CONFORMANCE | Revoked later dispatch impossible within claimed guarantee, not merely rare in sample |

No inherited risk is closed as implemented or certified. HLC-01 stays resolved upstream; no new upstream correction is required for this specification's semantics.

## 24. Evaluation-specific risks

**EVAL-086.** The following risk labels are local assessment concerns, not new canonical entities or errors. Supported evaluator/profile declarations MUST address relevant risks and expose residual limitations rather than claim unqualified quality or security assurance.

| Risk | Containment here | Next owner | Exit criterion |
|---|---|---|---|
| Benchmark overfitting | Pin selection history, held-fixed evidence and validation limits | Evaluator/dataset governance / EVALUATION implementation | Candidate selection and confirmation evidence are distinguished; generalization claims justified |
| Dataset leakage | Govern hidden inputs/labels/reference access and report exposure | SECURITY / dataset governance / CONFORMANCE | Subjects cannot obtain withheld references through evaluator channels under claimed design |
| Judge bias | Method/calibration, order/style/family sensitivity and uncertainty | Evaluator owner / EVALUATION implementation | Measured relevant bias and declared mitigation/limits for applicable population |
| Self-evaluation bias | Explicit overlap and required independence checks | GOVERNANCE / CONFORMANCE | Self-assessment never silently satisfies independent verification |
| Metric gaming | Multi-dimensional criteria and retained critical findings | Application/evaluator owners | Demonstrated criteria track intended properties with known proxy failure limits |
| Goodhart's law | Optimization target distinguished from broader criterion; changed selection disclosed | Evaluator/application governance | Evidence shows proxy limits and follow-up checks after optimization-driven drift |
| Dataset contamination | Source/training/exposure provenance and unknown status | Dataset/evaluator owners | Adequate known-contamination reporting and defensible applicability limits |
| Non-representative cases | Target population, selection, slices and coverage denominator | Dataset governance / EVALUATION implementation | Representativeness claims supported or bounded; omitted populations explicit |
| Test flakiness | Repetitions, environment/randomness and failure observations retained | Evaluator owner / subject ADR | Variation quantified without deleting inconvenient runs or favorable rerun selection |
| Environment drift | Exact assumptions, time windows and re-evaluation triggers | Subject/evaluator owners | Changed dependencies/configuration invalidate or qualify evidence use |
| Evaluation cost explosion | Bounded loops/graphs/pairwise/corpus work with authoritative resources | Resource profiles / CONFORMANCE | Worst-case or approved uncertainty consumption stays within admitted bounds |
| Hidden evaluator dependency | Complete method/Model/Tool/reference graph | Evaluator/Plugin owners / CONFORMANCE | Inputs/dependencies affecting results and independence are inspectable |
| Score aggregation masking failures | Per-criterion/slice/critical findings and missingness preserved | Gate/evaluator owners / CONFORMANCE | Mandatory unmet evidence cannot be outweighed by favorable aggregate |
| False confidence | Explicit inference/calibration/sample assumptions | Evaluator owner / EVALUATION methodology review | Reported confidence interpretation valid for declared population and method |
| Human reviewer inconsistency | Versioned rubric, eligibility, inter-rater/adjudication evidence | Human-assessment governance | Disagreement/variance and relevant review conditions visible; no fabricated consensus |
| Adversarial evaluator manipulation | Subject content remains data; governed reference/control separation | SECURITY / evaluator owner / CONFORMANCE | Injected input cannot alter authority, hidden references or undeclared scoring rules |
| Security finding disclosure | Scoped findings, redaction, retention and reviewer access | SECURITY / GOVERNANCE / evidence profiles | Authorized review remains possible without unauthorized exploit/tenant disclosure |

## 25. Traceability

**EVAL-087.** Every major assessment requirement maps to governing semantics below. Later representations, evaluators, release gates, ADRs and Conformance cases MUST cite their applicable EVAL requirements and preserve these authorities. A narrow supported feature or dataset result cannot waive cross-cutting security, scope, resource or effect obligations.

| EVAL requirements / topic | intent.md | SPEC.md | ARCHITECTURE.md | CONTRACTS.md | PLUGIN-SPEC.md | SECURITY.md |
|---|---|---|---|---|---|---|
| 001–005: authority/modularity/model ownership | §§11, 33–34, 39, 47, 54–55 | §§1, 3, 4.11; DEC-01 | §§4.12, 5.2; AR-06/07 | CTR-001–003, 049, 062 | PLG-001–005 | SEC-001–003, 087 |
| 006–010: attempts/runs/results | §§26, 31–34 | S-01–08, §4.11, §5.8, E-01–11 | §§4.4/12/13, 6 | CTR-004–016, 027, 049 | PLG-052–054, 059–061 | SEC-029–030, 073–077 |
| 011–014: Evaluator/method/dependencies/oracle | §§7, 11, 33–34 | Evaluator §4.11, C-03–06 | AR-12/21; §§4.12, 13 | §§24, 27, 32 | PLG-012–020, 061–062 | SEC-026, 054–056, 087 |
| 015–019: criteria/metrics/thresholds | §§33–34, 51 | §4.11, V-09, I-20 | §4.12, AR-10 | CTR-049, 066–069 | PLG-061–062 | SEC-044, 087 |
| 020–024: cases/datasets/suites/baselines | §§27–29, 31, 33–35 | S-01–12, A-01–05, §4.11 | §§4.8/9/12, 10 | CTR-043–047, 049 | PLG-055–056, 059–061 | SEC-060–077 |
| 025–028: versions/environment/reproducibility | §§24, 26, 31, 34 | S-08, V-01–09, §4.11 | AR-09/14/23 | CTR-013–016, 063–069 | PLG-006–010, 019–020, 061 | SEC-048, 073, 086–087 |
| 029–034: uncertainty/confidence/missing evidence | §§31, 33–34 | EvaluationResult §4.11, §10, I-20 | §§4.12, 12–13 | CTR-007–012, 049 | PLG-051, 060–062 | SEC-073–077, 084–087 |
| 035–039: independence/Human/Model judges | §§19, 33–36 | Evaluator §4.11, HumanApproval §4.9 | §§4.10/12, 8.2 | CTR-036, 041, 049 | PLG-028, 061–062 | SEC-031–034, 038–042, 078, 087 |
| 040–046: composition/aggregation/coverage | §§7–11, 29–34 | §1.2, §4.11, S-10–12 | §§4.12, 13 | CTR-049, 062, 066–069 | PLG-014, 055–062 | SEC-060–077, 086–089 |
| 047–050: function/Model/Agent/Workflow/Team | §§11–18, 26, 33 | §§3, 4.2–6, 4.11, 5–6; DEC-01 | §§4.4–7/12, 8, 13 | §§10–13, 16–17, 24 | PLG-004–005, 012–014 | SEC-035–045 |
| 051–053: Tool/information/composition | §§20, 27–28, 33–34 | §§4.5–8, E-06–11 | §§4.6–9/12, 13 | §§14, 19–22, 24 | PLG-005, 013, 051–054 | SEC-043–045, 066–072 |
| 054–057: Plugin/security/adversarial | §§19–22, 33–35 | S-09–12, §4.12, §5.12, I-11/12 | AR-19/21/23; §§10–13 | CTR-051–055, 068–069 | §§9–18, 23, 25 | §§4–5, 14–16, 28–30 |
| 058–061: robustness/errors/retries/partial work | §§26, 30–34 | L-01–04, E-06–11, §10 | AR-15–18/22; §§8.3, 12 | CTR-011–022, 049, 056–061 | PLG-051–054 | SEC-027–030, 074–085 |
| 062–065: cost/latency/reliability/resources | §§30, 32–34 | B-01–04, §4.10–11 | AR-18; §§9, 13 | CTR-037–038, 049, 067 | PLG-057–058 | SEC-063–065, 081–083 |
| 066–068: operational/Artifact/Outcome/gates | §§28, 31, 33, 54 | §3, §4.11, A-01–05, DEC-01 | AR-07/10; §§4.5/9/12 | CTR-009, 031, 047, 049 | PLG-005, 059–062 | SEC-070, 073–077, 087 |
| 069–076: comparison/regression/continuous/modes | §§24, 31–34, 46 | §4.11, E-06–11, V-01–09 | §§4.12–13, 11.4 | CTR-049–050, 063–069 | PLG-019–020, 047–050, 061 | SEC-048–050, 073, 086–087 |
| 077–084: governance/evidence/conformance handoff | §§29–35, 46–51 | S-01–12, A-03, V-09, §12 | AR-23; §§4.12–13, 13 | CTR-049–050, 059–069 | PLG-059–070 | SEC-073–089 |
| 085–090: dispositions/risks/traceability/review/phase boundary | §§46–48, 51, 55 | §13 | §§14–16 | §§35–36 | §§22–27 | §§29–33 |

## 26. Final self-review

**EVAL-088.** This review verifies specification coverage, not measured subject quality or implementation conformance. Revisions MUST repeat affected review, update traceability and preserve unresolved risk ownership. All required examples, matrices and diagrams describe semantics only.

| # | Check | Result / anchor |
|---|---|---|
| 1 | No evaluation technology selected | Pass — §1 |
| 2 | No concrete schema created | Pass — §§1, 3 |
| 3 | Evaluation distinct from Conformance | Pass — §§1, 22 |
| 4 | Evaluation distinct from Approval | Pass — §§9, 17 |
| 5 | Evaluation distinct from authorization | Pass — §§1, 17, 20 |
| 6 | Evaluation distinct from Outcome | Pass — §17 |
| 7 | Run success distinct from subject pass | Pass — §3 |
| 8 | Result subject/version pinned | Pass — §3 |
| 9 | Evaluator version pinned | Pass — §§3–4 |
| 10 | Dataset/case versions pinned | Pass — §§3, 6 |
| 11 | Material environment/configuration assumptions recorded | Pass — §7 |
| 12 | Missing data explicit | Pass — §8 |
| 13 | Partial evaluation explicit | Pass — §11 |
| 14 | Material uncertainty represented | Pass — §8 |
| 15 | Qualitative results supported | Pass — §5 |
| 16 | Quantitative results have semantics | Pass — §§5, 8, 16 |
| 17 | Human evaluation not HumanApproval | Pass — §9 |
| 18 | LLM judge is probabilistic evidence | Pass — §9 |
| 19 | Self-evaluation labeled | Pass — §9 |
| 20 | Independence claim scoped | Pass — §9 |
| 21 | Deterministic systems evaluable without AI | Pass — §§1, 12 |
| 22 | Retrieval evaluable without generation | Pass — §§1, 13 |
| 23 | Model evaluable without Agent | Pass — §§1, 12 |
| 24 | Team evaluation does not redefine Outcome | Pass — §§12, 17 |
| 25 | Tool evaluation preserves effect uncertainty | Pass — §§13, 15 |
| 26 | Plugin evaluation cannot self-admit | Pass — §14 |
| 27 | Security evaluation grants no security authority | Pass — §14 |
| 28 | Red-team result cannot automatically change Policy | Pass — §§14, 17 |
| 29 | Tenant/security boundaries preserved | Pass — §§14, 19–20 |
| 30 | Evaluation resources governed | Pass — §§15–16 |
| 31 | Regression has declared baseline/comparison | Pass — §18 |
| 32 | Historical results immutable | Pass — §§3, 7 |
| 33 | Changed evaluator semantics versioned | Pass — §7 |
| 34 | Changed material dataset/case versioned | Pass — §§6–7 |
| 35 | Observation types consumed without collapsed ownership | Pass — §§19–20 |
| 36 | No private chain-of-thought required | Pass — §§4, 12, 20 |
| 37 | All Q/R/CR/Plugin/Security risks tracked | Pass — §23 |
| 38 | Explicit Conformance handoff | Pass — §22 |
| 39 | No official certification invented | Pass — §§1, 22 |
| 40 | Next phase remains specification | Pass — §27 |

**EVAL-089.** Later supported-scope declarations MUST report relevant untested cases, method/oracle and independence limits, security/effect assumptions, resource bounds and evidence availability. A document review, passing score or finite adversarial sample MUST NOT be presented as proof of all behaviors or universal security. This document's 40 checks establish semantic coverage only; no evaluator, benchmark, red-team scenario or implementation test was executed as part of this phase.

## 27. Next document and phase boundary

**EVAL-090.** The next recommended artifact is `conformance/CONFORMANCE.md`. It should define versioned supported obligations and proof requirements, consume §22's evidence semantics and §23–24's tracked risks, specify independent Port/composition/security/lifecycle/recovery conformance surfaces, and distinguish claims from adequate proof. It must preserve all accepted authorities and cannot turn a quality average into a waiver of mandatory behavior.

This Evaluation specification phase ends here. Conformance, schemas, datasets, evaluator/test implementations, CI/deployment, vendor integration and technology ADRs require separate instruction.
