# ForgeAI-4 and M8.4 direction assessment

Status: planning only (2026-09-29). No production source is changed by this
document. It supersedes no ADR, and the historical M8.x and ForgeAI records
remain authoritative for their own slices.

Evidence base:
- the engineering `analyst`, `reviewer`, `coding` and `checks` modules;
- `examples/forgeai` (ForgeAI-1/2/3, all locally qualified);
- ADR-018 and its CR-3 addendum;
- `packages/legoai-engineering/docs/CONSUMING.md`;
- `planning/LEGOAI-CONSUMER-READINESS-PLAN.md`;
- `planning/PYTHON-FIRST-REUSABLE-AI-PLATFORM-PLAN.md` §§H–L;
- `evaluation/EVALUATION.md` (EVAL-036, 047, 048, 071).

## 1. Executive recommendation

| Question | Recommendation |
| --- | --- |
| M8.4 Test/Validation Agent | **DEFER.** Do not implement it as planned. Its three plausible designs are a clone of the reviewer, a clone of the Coding Agent, or test-gap analysis. Only test-gap analysis has a distinct contract, and it has no consumer today. Keep the M8.4 number for this deferred capability; do not reuse it for something else. |
| Largest ForgeAI functional gap | **Target discovery.** The operator must name 1–8 files. It needs a new, separately authorized, paths-only disclosure of repository structure, and a new reusable selection capability. |
| Largest evidence gap | **Live-model behavior is unmeasured.** Every qualification so far uses replay outputs. We do not know whether the real Coding Agent, reviewer and rework can complete even the fixture task. |
| Workflow abstraction | **Not justified.** Every coordination behavior seen so far comes from one application. |
| Team abstraction | **Not justified.** There are two Agent definitions under one principal, and no roles, membership or delegation. |
| CR-4 (Module Catalog, assembly guide) | **Execute now, docs-only, before ForgeAI-4.** Real consumer evidence exists, and the active status text is stale in several places (§13). |
| Live-model qualification | **Start a separate track, ForgeAI-LQ.** Its first slice is measurement only: frozen fixtures, operator-held hidden acceptance tests, reported metrics, and no quality claim. |
| Exact next implementation slice | **ForgeAI-LQ1**, the live-model evaluation harness and baseline (§14). The docs-only CR-4 slice should land first or in parallel; it has no code dependency. |

Rationale in one line: before adding a third Agent or model-driven target
selection, measure whether the two Agents we have actually work with a real
model. A new Agent evaluated only on replay outputs would add abstraction
without evidence of value.

## 2. Current ForgeAI-3 capability boundary

**What ForgeAI does today:**

1. It takes a `TaskRequest`: objective, **operator-named** targets and
   constraints.
2. It requires a clean Git start.
3. The Coding Agent proposes once, reading target content through authorized
   reads.
4. The change is applied through authorized mutation.
5. Ruff, mypy and pytest run in the real sandbox.
6. The Git integrity check runs.
7. The independent reviewer reviews once.
8. If review #1 requires changes, there is **at most one** rework, with the
   review terminal the second time.
9. It returns a closed `TaskResult` with per-attempt evidence.

**Ceilings:** at most 4 model calls, 2 applies, 2 check batches, 2 reviews.

**Outside the boundary:**
- choosing which files to change;
- task decomposition;
- test design separate from coding;
- live-model quality;
- durable state or resume;
- commits;
- more than one rework;
- multi-workspace tasks;
- any other language or repository layout.

The model never discovers files, never sees Git data, and never widens its
own write scope.

## 3. Existing engineering responsibility matrix

Legend: **OWNED** means an existing owner fully covers it. **PARTIAL** means
an owner covers part of it; the gap is noted. **UNOWNED** means nothing covers
it today.

| Responsibility | Status | Owner / evidence |
| --- | --- | --- |
| Repository understanding (of named files) | OWNED | `RepositoryAnalyst`: authorized reads of ≤8 **supplied** paths, then a closed analysis with cited findings |
| Repository understanding (which files matter) | **UNOWNED** | No capability discloses structure. The Analyst's `relevant_files` must be a subset of the supplied targets |
| Code proposal | OWNED | `CodingAgent`: a validated M4 `RepositoryChangeSet` over authorized current content |
| Deterministic execution | OWNED | `EngineeringCheckPort` with the closed `CheckKind`s |
| Isolated test execution | OWNED | `SandboxedEngineeringChecks` on `PYTHON_CHECKS` |
| Test-result observation | OWNED | `CheckResult` (outcome, exit code, bounded output); ForgeAI `CheckRecord` |
| Test adequacy reasoning | PARTIAL | `IndependentReviewer` has the `testing` finding category and blocking findings with required actions. It gives a verdict, not a structured enumeration of missing tests |
| Correctness reasoning | OWNED (opinion) | `IndependentReviewer`, explicitly as an unverified opinion |
| Review findings | OWNED | `ReviewFinding` (category, severity, cited material, required action) |
| Mutation | OWNED | `AuthorizedRepositoryMutation` over `LocalRepositoryMutation` |
| Authorization | OWNED | The public host, `AuthorizationPort` and the CR-3 wrappers (per-effect, current) |
| Rework guidance | OWNED (application) | ForgeAI-3 renders blocking findings into labeled constraint text; the Coding Agent consumes them |
| Target discovery | **UNOWNED** | Operator-supplied only |
| Task planning / decomposition | **UNOWNED** | No capability, and no consumer yet requires multi-step plans |
| Independent correctness oracle | **UNOWNED** (by design) | Only deterministic checks and model opinion exist. No hidden-test oracle is part of any runtime path, and none should be; it belongs to evaluation (§12) |

## 4. M8.4 overlap analysis

**Test 1: IndependentReviewer with a different prompt?** A "validation
assessment" Agent that reads check outcomes and code and returns
accept/reject, findings, risks and unknowns has the **same semantic contract**
as `IndependentReviewer`: an opinion over supplied material with a closed
decision. Its prompt, and perhaps its criteria, differ, and ForgeAI already
supplies operator-configured criteria (`test adequacy` is one of them). This
design is **rejected**.

**Test 2: EngineeringCheckPort again?** Any M8.4 that runs pytest, wraps
`CheckResult`, owns a sandbox or selects commands duplicates M5/M6/CR-2b. That
is **rejected**. M8.4 could only add reasoning *above* tool execution.

**Test 3: CodingAgent restricted to test files?** A "test change proposal"
Agent would produce an M4 change set limited to test paths. ForgeAI can
already restrict any Coding request to test targets, since targets are
operator-chosen. The output contract is identical (`CodingProposal`), so a
separate Agent would be a renamed definition. That is **rejected** as a
reusable capability.

**What remains:** only **test-gap analysis**, a structured enumeration of
missing validation that is not a verdict and not a change set, has a
different output contract.

## 5. M8.4 ownership test

Would test-gap analysis still belong in `legoai-engineering` if ForgeAI
disappeared? **Plausibly yes.** Two non-ForgeAI contexts could use it:

1. a pull-request assistant that lists missing test scenarios for a supplied
   diff, without judging the change;
2. a test-authoring tool, where a human or a separate generation step writes
   tests from a structured scenario list.

However, **neither consumer exists in this repository**. ForgeAI-3 already
closes the loop it would serve: reviewer `testing` findings drive the single
rework, and the fixture demonstrates exactly that. There is also no evidence
yet that the reviewer misses test gaps a specialist would catch; only
live-model measurement (§12) could show that. Building it now would put the
Rule of Two on hypothetical consumers.

## 6. Candidate M8.4 contracts

| Candidate | Distinct semantics | Existing owner | Reusable beyond ForgeAI | Inputs | Output | Effects / authority | Likely consumer | Verdict |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A. Test-gap analysis | **Yes**: enumerates missing scenarios; no verdict, no change set | None (the reviewer gives a partial verdict only) | Plausible (PR assistant, test authoring) | Objective; supplied changed-file text; supplied existing-test text; check outcomes; all acquired by a trusted authorized boundary | Closed `ValidationPlan`: `TestScenario`s (behavior, input class, expected observable, suggested location as a supplied path), `CoverageGap`s citing supplied material, `ValidationRisk`s, `Unknown`s; no decision, score or command | None; one governed call | None today | **Defer** (the only viable redefinition) |
| B. Test change proposal | No: same as `CodingProposal` | `CodingAgent` with test targets | — | — | — | Mutation-capable proposal | — | Reject |
| C. Validation assessment | No: same as `Review` | `IndependentReviewer` | — | — | — | — | — | Reject |
| D. Test-to-requirement traceability (map each objective clause to supplied tests) | Weakly distinct | Partially the reviewer | Unproven | Same as A | Clause-to-test links | None | None | Reject for now; fold into A if A proceeds |

**Smallest contract, if A is later justified.** A pure M7 one-step Agent on
the `engineering-reasoning` profile, with:

- an immutable bounded request: objective ≤2 KiB, ≤8 supplied materials, the
  M8.2-style byte limits, and an `ExecutionContext`;
- one `AgentRuntimePort` invocation;
- a closed JSON schema parsed into `ValidationPlan`, with `TestScenario` /
  `CoverageGap` citing only supplied material IDs;
- no Ports other than the runtime: no filesystem, mutation, checks, Git,
  sandbox, shell, tools, retries or memory.

It must not reuse the `Review` / `ReviewFinding` / `ReviewDecision` shapes; it
has no decision field.

## 7. Recommended M8.4 decision

**DEFER.** The Test/Validation Agent stays planned and unstarted. The M8.4
number keeps its historical meaning.

**Reconsider when:**
- ForgeAI-LQ shows that the reviewer systematically misses test gaps that
  hidden acceptance tests expose, and a structured scenario list would feed a
  measurable improvement; **or**
- a second, non-ForgeAI consumer of structured test scenarios appears.

When reconsidered, candidate A (§6) is the only contract to evaluate.

## 8. ForgeAI functional gaps, ranked by dependency

Ordering is by what each gap depends on, not by subjective value.

| # | Gap | Depends on | Why this position |
| --- | --- | --- | --- |
| 1 | Live-model behavior unmeasured | Nothing (existing `ollama` binding, fixtures, sandbox) | Every later model-driven capability, target selection included, needs a measurement harness and a baseline to show it helps |
| 2 | Stale active documentation and missing Module Catalog (CR-4) | Nothing | Consumers and later slices otherwise build on false status |
| 3 | Target discovery (objective to candidate targets) | A decision on disclosing structure (an ADR or ADR-018 addendum); a new selection capability; gap 1 to evaluate it | Biggest user-facing limitation, but it cannot be evaluated honestly without gap 1 and needs an authority decision first |
| 4 | Operator confirmation of model-proposed targets | 3 | The editable allowlist must stay operator-authorized; a model must never widen its own write scope |
| 5 | Test-gap specialist (M8.4 candidate A) | 1 (evidence of reviewer misses), a second consumer | Deferred (§7) |
| 6 | Durable run record / resume | A real long-running or remote consumer | Not needed by single-shot local runs |
| 7 | More than one rework, or task decomposition | Evidence from 1 that one rework is the binding limit; a Workflow need | Speculative today |

## 9. Target-discovery analysis

**Why it is the largest functional limitation.** Real tasks rarely arrive
with the right files named. Today the operator must already know the files
and all eight paths, which makes ForgeAI a guided editor rather than an
engineering assistant.

**The pipeline it would need:**

```
objective
  → bounded, authorized repository map (paths only, no contents)
  → candidate target selection (one governed model call)
  → operator confirmation (the confirmed paths become the editable allowlist and targets)
  → existing ForgeAI-3 flow (authorized content reads happen here, as today)
```

**Disclosure authority, the critical point.**
- M2 `RepositoryWorkspacePort.list_entries` can enumerate directories, within
  `WorkspacePolicy` depth and entry limits.
- No existing authorization covers **disclosing path names to a model**:
  - ADR-018's `read-for-model-analysis` covers the *contents* of allowlisted
    paths;
  - `AuthorizedCodingEvidence` explicitly states that "listings are not
    disclosed".
- Path names can be sensitive (customer names, security files, internal
  structure). So a repository map needs a **new fixed action**, for example
  `read-structure-for-model-analysis`, evaluated per acquisition with the
  same ADR-018 rules:
  - current authority;
  - fixed scope;
  - approvals refused;
  - bound to the workspace reference.
- That is an architecture decision: an **ADR-018 addendum** (or a new ADR)
  must precede implementation.

**Bounds and exclusions the map must enforce:**
- operator-configured roots (for example `src`, `tests`);
- the existing M2 exclusions, plus hidden and dot paths;
- an entry ceiling (for example ≤512 files) and a serialized byte ceiling;
- no sizes or digests unless justified;
- no Git status. Git stays operator-only, and untracked or ignored state is
  not disclosed.

Exceeding a bound fails explicitly, and nothing is truncated. As with the
reviewer, a partial map must never look complete.

**Selection output.** A closed schema of ≤8 candidates. Each is an existing
map path (`update`), or a new path whose parent directory is in the map
(`create`), with a rationale and unknowns. Candidates outside the map are
rejected. There is no score.

**Operator confirmation is mandatory.** Model-proposed targets become the
editable allowlist only after operator confirmation, for example a
`forgeai plan` command that prints candidates and a `forgeai run --target …`
that the operator issues. Automatically accepting candidates would let model
output set its own write authority. That is excluded unless a future ADR
defines an approval mechanism.

**Reusable or ForgeAI-owned?**
- **The map acquisition and the selection Agent are reusable engineering
  capabilities.** The Repository Analyst currently requires named files, and
  a "question → which files" front end would serve it directly (consumer 1).
  ForgeAI is consumer 2. IDE-style code search is a plausible third.
- **The operator-confirmation UX is ForgeAI-owned.**

## 10. RepositoryAnalyst reuse analysis

| Question | Answer (from the M8.1 contract) |
| --- | --- |
| What evidence can it receive? | Full text of ≤8 explicitly requested paths from the operator allowlist, through `AuthorizedRepositoryEvidence` |
| Can it discover paths? | **No.** `relevant_files` and finding paths must be a subset of the supplied paths |
| Does existing authorization support bounded discovery? | **No.** Only `read-for-model-analysis` of allowlisted contents; listings are not disclosed |
| Could it do target selection? | Only as a **second stage**: after a map-based selection proposes ≤8 candidates, the Analyst could read and confirm relevance. It cannot replace the map stage |
| Is a new reusable capability needed? | **Yes**, for the map-disclosure boundary and candidate selection. Stretching the Analyst (for example by feeding a synthetic "map file") would violate its contract that cited paths are real supplied files |

Recommended reuse: keep the Analyst unchanged. The future discovery pipeline
may run **map → selection → (optional) Analyst confirmation → operator
confirmation**. The optional Analyst step only earns its model call if
ForgeAI-LQ shows it improves selection precision.

## 11. Workflow / Team promotion test

| Coordination semantics seen in ForgeAI-1/2/3 | Reusable platform semantics or ForgeAI semantics? | Evidence |
| --- | --- | --- |
| Ordered stages (gate → propose → apply → check → Git → review) | ForgeAI | One application. DocuMind's ingest/answer pipeline has different stages and no gates |
| Gating (a later stage only if earlier deterministic gates pass) | ForgeAI | One application; the gate definitions are engineering-specific |
| Bounded attempts (exactly one rework) | ForgeAI | One application, one bound; no second loop anywhere |
| Effect authorization | **Already platform** | The CR-3 wrappers and host; nothing new to promote |
| Result propagation (typed values between stages) | ForgeAI | Plain values; no shared state model is needed |
| Terminal states (closed dispositions and failures) | ForgeAI | Vocabulary is task-specific |
| Evidence accumulation (per-attempt records) | ForgeAI | EVAL-/SPEC-level Evidence exists separately; ForgeAI's is application evidence |

**Rule of Two / Three: not met for any row.** Generative media has
completion policies, and DocuMind has fixed pipelines, but neither shows
gating, bounded rework or multi-Agent stage coordination.

**Workflow:** not justified. **Team:** not justified. ForgeAI has two Agent
definitions under **one** principal, with no roles, membership, delegation
or accountable organization (§I of the platform plan).

**What would justify revisiting Workflow:**
- a second, materially different workflow with the same needs (bounded
  loops, gating and resumable state), for example a bug-triage flow or a
  DocuMind review cycle; **or**
- ForgeAI needing durable wait or resume, such as human approval across
  process restarts.

## 12. Live-model qualification track (ForgeAI-LQ)

This is separate from architecture qualification, which stays replay-based
and deterministic. Live evaluation **measures**; it does not re-qualify the
architecture. It is governed by EVAL-047/048 (functional and Agent
assessment), EVAL-036 (reviewer ACCEPT is a model judge and must be labeled
as such) and EVAL-071 (record variables when comparing models).

**What can truthfully be measured, per fixture and model, over N ≥ 3 runs:**
- **Completion:** `SUCCEEDED` rate, and the success rate on the **operator's
  hidden acceptance tests**. These are run by the harness, in the sandbox,
  after the ForgeAI run, and are never seen by ForgeAI or the models. They
  are the only independent correctness oracle.
- **Structured-output validity:** the Coding `OUTPUT_INVALID` rate and the
  review `OUTPUT_INVALID` rate.
- **Deterministic checks:** pass rate per attempt, and failure distribution
  by check kind.
- **Review decisions:** the distribution of review #1 and #2 decisions.
- **Reviewer against hidden tests:** the ACCEPT-but-hidden-fail rate (false
  accept) and the CHANGES_REQUIRED-but-hidden-pass rate. This labeled
  model-judge agreement is the evidence M8.4 would need (§7).
- **Rework:** how often rework is invoked, and how often it recovers
  (CHANGES_REQUIRED, then ACCEPT and hidden-pass).
- **Cost and failures:** model calls per run (at most 4), per-call and total
  latency, the histogram of `TaskFailure` categories, and `UNKNOWN`
  model-effect counts.

**What it must not claim:**
- production quality;
- generalization beyond the frozen fixtures;
- anything from fewer runs than reported;
- anything about models, prompts or hardware not recorded.

**Every report records:**
- the model name and the operator-supplied model digest;
- Ollama, fixture and hidden-test revisions;
- the ForgeAI commit;
- the hardware class;
- N;
- the date.

## 13. CR-4 timing recommendation

**Execute CR-4 now, docs-only, before ForgeAI-4 functionality.** The draft
catalog in the readiness plan (§8) is now wrong in several rows:

- the Core governed runtime row says "no host entry yet (B1)", but CR-1b
  qualified the public host;
- the engineering Agents row says "8.3 implemented; wiring private", but 8.3
  is qualified and the wiring is public since CR-3;
- the checks row omits CR-2b's sandboxed checks and the CR-3 wrappers.

**Active status statements that are now false:**

| Location | Stale active statement | Correct current state |
| --- | --- | --- |
| `README.md` (intro paragraph) | "Workflows, Teams and ForgeAI remain planned." | ForgeAI-1/2/3 exist as a locally qualified example application (replay-only); Workflows and Teams remain planned |
| `README.md` (model-composition paragraph) | "a public application-authoring facade remain[s] future work" | The ADR-014 public local host (`legoai.runtime.api/local`) is locally qualified (CR-1b) |
| `README.md`, lines "M8.4 remains unstarted" (×2) | True but incomplete | M8.4 is **deferred** by this assessment |
| `planning/LEGOAI-CONSUMER-READINESS-PLAN.md` §17 | "nothing on the Core governed path is consumer-ready today" | The engineering governed path is consumer-ready by §17's standard (CONSUMING.md, public imports, clean-install proof); the Core runtime has the public host |
| `planning/LEGOAI-CONSUMER-READINESS-PLAN.md` §8 draft rows | See above | Replace with the CR-4 catalog |
| `planning/PYTHON-FIRST-REUSABLE-AI-PLATFORM-PLAN.md` §K ordering | Workflow (G) before the engineering workflow (H) and ForgeAI (J) | ForgeAI reached the J/H territory without G. Record this deviation as **evidence** that a fixed application sequence sufficed, not as a completed Workflow phase |
| `README.md` browser hand-landmark line | "implemented with local validation pending" | **Verify** against that slice's records; not assessed here |

**Historical text that must remain:**
- M8.x closure records ("M8.4 is unstarted" at the time);
- `FORGEAI-REUSE-GAP-ASSESSMENT.md` ("FORGEAI-1 BLOCKED" at the time);
- CR slice records.

Add forward pointers; do not rewrite.

**CR-4 scope:**
- `docs/modules/MODULE-CATALOG.md`: human-facing only, one row per real
  module, the §8 maturity labels, and an evidence link per row;
- `docs/ASSEMBLING-APPLICATIONS.md`: the §10 outline, with DocuMind,
  engineering consumers and ForgeAI as the three worked examples;
- the per-module guide standard: reference `CONSUMING.md` as the exemplar;
- the stale-status corrections above.

It creates **no** machine-readable registry and changes no code.

## 14. Exact next implementation slice: ForgeAI-LQ1

**ForgeAI-LQ1: live-model evaluation harness and baseline.**
- **Where:** a ForgeAI-owned evaluation harness under
  `examples/forgeai/evaluation/`, not part of the installed `forgeai`
  package.
- **Architecture:** no change to ForgeAI runtime behavior, and none to LegoAI.

**Contents:**
1. **A frozen fixture set** of 3–5 small repositories and tasks, including
   the existing stock task. Each has a pinned objective, targets and
   constraints, plus **hidden acceptance tests** stored outside the fixture
   repository.
2. **A harness** that, per fixture and run:
   - provisions a fresh committed copy;
   - runs `run_task` with the operator-selected binding (`ollama`, or
     `replay` for self-test);
   - then copies the hidden tests into the sandbox inputs and runs them
     through the same `SandboxedEngineeringChecks` path, never on the host;
   - records the §12 metrics from `TaskResult` and the hidden-test
     `CheckResult`.
3. **A report writer** producing JSON plus a Markdown table. It records the
   variables listed in §12 and labels reviewer judgments as model-judge
   evidence (EVAL-036).
4. **Replay-mode self-tests** proving the harness itself: metric
   computation, hidden-test isolation (the hidden tests are never visible to
   the ForgeAI run or models), and report completeness. These run offline
   and deterministically.
5. **A documented baseline run** against one locally admitted Ollama model,
   produced by the maintainer and recorded as measurement. It has no
   pass/fail threshold unless the maintainer sets one.

## 15. Acceptance criteria for ForgeAI-LQ1

1. `git diff HEAD -- src/legoai packages examples/forgeai/src` is empty. The
   harness adds no runtime behavior.
2. Hidden acceptance tests are never readable by the ForgeAI run.
   - The editable allowlist, targets and sandbox inputs during the run
     exclude them; a test asserts this.
   - They execute only in the sandbox, after the run.
3. In replay mode, the harness produces a complete report for every fixture,
   and deterministic tests verify every metric field.
4. Every run records the §12 variables, and the report refuses to render if
   any is missing.
5. Metrics are computed only from typed `TaskResult` / `CheckResult` values;
   nothing is parsed from human-readable text.
6. A live run with an unreachable provider yields recorded `MODEL_FAILED`
   runs. The harness does not crash and does not retry.
7. The architecture tests still pass. The harness imports only public
   LegoAI and ForgeAI APIs plus test-harness facilities.
8. The documentation states plainly that results are measurements over
   frozen fixtures, not production-quality claims.
9. The existing ForgeAI-3 validator still passes unchanged.

## 16. Non-goals

For this assessment and the next slices, do not:

- implement M8.4, or any Test/Validation, Planner or Target-selection Agent;
- implement ForgeAI-4 functionality before LQ1 and the disclosure decision;
- create a Workflow or Team abstraction, generic orchestration or a retry
  framework;
- create a machine-readable module registry;
- give models autonomous write-scope expansion, Git disclosure or
  whole-repository disclosure;
- run hidden acceptance tests on the host, or expose them to models;
- make claims of production quality or model leaderboards;
- add durable run state, resume, commits, PRs or remote workers.

## 17. Sequence for the next 2–4 slices

1. **CR-4** (docs-only; may run in parallel with 2): the Module Catalog,
   the assembly guide and the stale-status corrections from §13.
2. **ForgeAI-LQ1**: the live-model evaluation harness and baseline (§14–15).
3. **Target-discovery decision** (ADR-018 addendum or a new ADR; decision
   only). It defines:
   - the paths-only `read-structure-for-model-analysis` disclosure action;
   - map bounds and exclusions;
   - the fail-closed rules;
   - the mandatory operator confirmation of model-proposed targets.

   Informed by LQ1 data on whether real models can use supplied context well.
4. **M8.5 Repository Target Discovery plus ForgeAI-4.** M8.5 adds, in
   engineering, the authorized map acquisition and the pure selection Agent.
   ForgeAI-4 adds a `plan` step with operator confirmation that feeds the
   unchanged ForgeAI-3 flow. It is measured with the LQ harness: selection
   precision and recall against fixture ground truth, plus end-to-end
   completion.

M8.4 (candidate A, test-gap analysis) re-enters the sequence only when the §7
triggers are met.
