# FORGEAI-KISSKI-CODING-MODEL-EVALUATION-1

Status: HARNESS AND DIAGNOSTICS LOCALLY QUALIFIED; HOST-LIFECYCLE VALIDATION PENDING.
Host-lifecycle verification: NOT RUN — Awaiting user execution.
No live evaluation is authorized by this implementation or local validation.

## Goal and ownership

Compare bounded coding/proposal and independent-review performance on eight frozen,
synthetic task families. This is operator evaluation tooling in
`scripts/kisski_coding_eval`, not a new generic evaluation framework or production
agent. There are no new Ports, providers, dependencies, routing policies or ADRs.
No production worker, CodingAgent, IndependentReviewer, T2, Secret, disclosure,
mutation, public API or accepted ADR changes are needed.

The first slice deliberately measures scalar miniature fixtures. It cannot establish
general repository engineering competence, deployment readiness, production tool
use, test-writing ability or behavior on a private repository. No model wins by
name, size, reputation or latency. Equally qualified candidates remain tied.

## Current qualification basis

Maintainer-provided evidence shows the exact `kisski-saia` / `qwen3-coder-next`
path at `https://chat-ai.academiccloud.de/v1` completed discovery, the exact
`KISSKI_OK` response and a fixed structured synthetic proposal smoke. The reported
chat executions were `exec-db303efaec154db888521a43ea63dbef` and
`exec-3d2d2c7c69dd49b3b6ac3b539f5cdd4d`. The tiny response used complete bounded
ordinary HTTP/1.1 chunked framing, exact model identity, `function_call: null` and
absent `tool_calls`. This is supplied evidence, not a run performed by this agent.

That run qualifies its connectivity/smoke path only. It does not qualify coding
quality, every listed model, SSE, HTTP/2, arbitrary tool calls or repository access.

## Reused assets and contract authority

- Existing Kaggle ForgeAI quality `contracts.py`: frozen CodingProposal and
  IndependentReviewer document parsers and instructions. No second proposal format.
- Its `safety.py`: bounded scalar language admission, not an arbitrary Python sandbox.
- Its `contract-baseline.json`: pins canonical coding/reviewer values, API,
  definitions, JSON framing, ForgeAI review policy and ADR-021. Drift blocks the
  local validator and live entry until explicitly reviewed.
- Existing KiSSKI qualification composition, discovery, public governed chat,
  hidden S1 provision and safe contract diagnostics. Trusted script-private
  bootstrap remains outside consumer/domain code; no new public discovery API.
- Existing Kaggle evaluation regression tests and REMOTE/architecture controls.
  Existing EVAL-3 sufficiency/analyst work informs evidence separation only;
  unreliable Analyst sufficiency behavior is not a qualification gate here.

Production CodingAgent/IndependentReviewer orchestration and sandbox/check profiles
remain independent. Their filesystem mutation/check semantics are not simulated
or claimed by these in-memory checks. Production schemas constrain the mirror;
production modules are not imported to obtain private parsers.

## Candidate selection

The account-observed inventory is frozen as:

`qwen3-coder-next`, `qwen3.5-397b-a17b`, `qwen3.8-27b`, `qwen3.6-35b-a3b`,
`deepseek-v4-flash-0731`, `glm-5.3-flash`, `gemma-4-31b-it`,
`qwen3-30b-a3b-instruct-2507`, `meta-llama-3.1-8b-instruct`,
`qwen3-omni-30b-a3b-instruct`.

An operator enters comma-separated **exact model IDs**, never menu numbers.
Selection must be unique, in this inventory and in that phase's fresh discovery.
Phase B also requires screening eligibility. Removed models are refused; newly
discovered models outside the frozen inventory require a separate pack revision.
No automatic reselection is performed.

The request's suggested initial comparison is `qwen3-coder-next`,
`qwen3.5-397b-a17b`, `qwen3.8-27b`, `deepseek-v4-flash-0731`, and `glm-5.3-flash`.
This is an operator shortlist for coding/review comparison, not evidence of relative
capability. The runner accepts any 1–5 eligible IDs, with 3–5 intended for comparison;
one model is supported for a deliberately smaller authorized run.

## Frozen tasks and equal conditions

| ID | Phase / role | Frozen requirement |
| --- | --- | --- |
| bug | A / coding | Correct inclusive endpoint counting. |
| refactor | A / coding | Remove else after return without changing clamping. |
| api | A / coding | Add required `limit` argument while preserving exact argument names. |
| diagnosis | A / coding | Repair zero-boundary failing test without editing tests. |
| multi | B / coding | Supply both independent full-file replacements in exact scope. |
| security | B / coding | Preserve authorization AND existence; reject truthy bypass values. |
| abstention | B / reviewer | Missing policy and patch require insufficient evidence. |
| review | B / reviewer | Identify defect, regression and security issue; spare harmless/correct changes. |

Every model gets the same task/role system instruction, user text, source fixture,
allowed files, response schema, constraints and budget. Reference replacements and
targeted/regression vectors are evaluator-only, never prompt hints. There is no
per-model tuning, rework, retry, fallback, command execution or model-generated test.
The same task remains the same across models; roles use their existing distinct
schema instructions. All inputs are fictional/public-safe; no repository files are
sent to the provider. Source reads for local hash integrity are never prompt inputs.

`manifest.json` pins normalized source bytes for the pack, scorer, runner, integrity
module and reused contract/language files. The plan/report additionally identifies
the task/prompt/budget digest. Change of tasks, scoring, instructions or reused
contracts requires explicit review and a new evaluation version; never silently
refresh pins to mix old Phase A evidence with changed Phase B criteria.

## Patch application and deterministic checks

Proposals are parsed as existing complete-file create/update documents, restricted
here to exact **update** targets. All required targets must be supplied. Paths are
data keys; they are never opened as filesystem destinations. Full-file replacement
is confined to a disposable in-memory map. `patch_application = in_memory_only`
is recorded; `patch_applies` does not claim a disk patch or governed mutation.

The shared language gate bounds each candidate to 8 KiB and 512 AST nodes, one
`solve` function, scalar assignments, branches, comparisons and addition/subtraction.
A small deterministic AST interpreter evaluates frozen vectors, with bounded
integer arithmetic. It never calls `exec`, `eval`, subprocesses or generated Python.
There are no imports, recursion, loops, attributes, subscripts, calls or arbitrary
fixture commands. This replaces the execution stage only for this restricted pack;
general filesystem changes require the existing governed mutation/check mechanism
in a separately scoped evaluation.

Targeted and regression results, exact argument-name adherence, schema validity,
scope and safety are separate. Checks sample finite vectors; passing them is not
a proof for all possible inputs. Test names in the JSON refer to these scalar
oracle checks, not pytest execution of generated source.

## Rubric and minimum gates

Coder dimensions: correctness (targeted AND regression), instruction adherence,
schema validity, scope discipline and absence of critical safety violations.
Per-task evidence also records patch applicability, unsupported file touches,
invented paths, acceptance, abstention, review detection and rationale proxy.

Coder weights are **45/20/15/10/10** for correctness/adherence/schema/scope/safety.
Correctness plus safety dominate; style and speed receive zero weight. Reviewer
results are deliberately not blended into the coder total.

Final coder eligibility requires all six coding tasks correct, 100% coder schema,
adherence and scope, no critical coder safety violation, and correct plain-JSON
abstention on the missing-context task. Any hard gate failure overrides total score.
Final reviewer eligibility independently requires both review tasks schema-valid,
plain JSON, correct abstention and all three expected blocking defect categories,
no false findings, no missed critical issue. A weak coder may qualify for review
only; a weak reviewer does not erase an otherwise qualifying coder result.

Both phases and all eight unique records are required for final classification.
Missing/duplicate records or provider/protocol failure make the result inconclusive.
Phase A alone never qualifies a model. All final eligible coders score 100 under
these conservative gates; eligible reviewers separately score 100. The report lists
qualified rank groups as ties, with lexical display order carrying no preference.
The pack therefore may establish eligibility without choosing a unique winner.

Supported results:

- `MODEL_QUALIFIED_FOR_FORGEAI_CODING`
- `MODEL_QUALIFIED_FOR_REVIEW_ONLY`
- `MODEL_NOT_QUALIFIED`
- `NO_MODEL_QUALIFIED`
- `RESULT_INCONCLUSIVE`

These are **frozen-pack results only**, not authorization to deploy or a general
claim about ForgeAI v0.2. Automatic role configuration/routing is not added.

## Abstention, security and reviewer limits

The production coding schema requires at least one change, so it cannot represent
a zero-change abstention. The existing reviewer `insufficient_evidence` schema is
used, with nonempty unknowns and no findings. This measures explicit abstention in
that role, not a new production CodingAgent `CONTEXT_INCOMPLETE` behavior. Invented
acceptance fails the abstention gate; invented evidence IDs fail schema validation.

Security vectors reject both missing authorization and truthy values other than
the specified integer 1. Unsafe language constructs and out-of-scope targets are
critical failures. They are never executed or written into a workspace.

Reviewer evidence has five independent patches: r1 correctness bug, r2 zero
regression, r3 authorization bypass, r4 harmless refactor, r5 correct identity.
True positives require an unambiguous expected evidence ID/category, blocking
severity and required action. Extra/duplicate/mismatched findings are false findings;
missing r3 is a missed critical issue. The false-positive rate is the fraction of
the two clean patches flagged. References and categories are deterministic proxies:
the scorer does not prove the natural-language explanation or correction is sound.
No hidden keyword/spelling requirements are used to award defect credit.

`reasoning_sufficiency_proxy` means required rationale exists (coding) or review
fixture gates pass (reviewing); it is not semantic reasoning qualification.
`unsupported_assumption_rate` is null because free-text assertions cannot be
soundly counted without another adjudication contract. Invented paths and unknown
review references are detected separately. Full reasoning quality remains outside
this narrow automatic qualification; it is not silently assigned a perfect score.

## Structured-output reliability and operations

Derived evidence separates completed provider responses from evaluation failures.
Per model: valid schema count, malformed document count, provider/protocol failures,
typed protocol rejection count, forbidden call-field rejections, wrong-model
rejections and finish-reason failures. Optional safe diagnostics may be unavailable;
their absence never changes the governed outcome. Truncation is explicitly
`NOT_SEPARATELY_OBSERVABLE`; finish failures do not prove token exhaustion.

Each record includes exact selected model/task/role/phase, safe execution ID,
invocation outcome, closed contract/failure categories, bounded elapsed duration,
and reported output tokens if available. Latency is secondary. Cost is
`NOT_AVAILABLE`; repeatability is `NOT_MEASURED` (one sample, no provider determinism
claim or guaranteed seed). Identical prompts/budgets are reproducible methodology,
not a promise of identical generations.

## Quota and phase gates

| Phase | Models | Tasks per model | Maximum chats | Discovery |
| --- | --- | --- | --- | --- |
| A screening | 1–5 (normally 3–5) | 4 | 20 | 1 |
| B finalists | 1–2 | 4 | 8 | 1 |

One authorized run of each phase: **28 chats + 2 discovery calls = 30 calls**.
Each chat requests at most 1024 output tokens and a 60-second client timeout.
Combined completion-token request ceiling is 28,672; actual accounting is not
claimed. System plus user input is bounded to 16 KiB per task. T2/SRCP-1 retain
their existing framing, body and deadline bounds. No automatic quota expansion.

Phase A screening requires four complete unique tasks, schema/adherence/scope
success and no critical safety failure, with at least 3/4 correct. An imperfect
screen can proceed for review evaluation but cannot meet final 6/6 coding gates.
The operator selects at most two eligible finalists in a separately authorized
Phase B run. Phase B imports a bounded, closed-record Phase A report with matching
pack identity; it does not rerun Phase A. It performs one new discovery.

A protocol/provider failure halts the entire current phase and retains partial
evidence as inconclusive. No automatic replay of uncertain effects. A completed
but incorrect/schema-invalid answer is recorded once; subsequent preapproved
tasks may continue without correcting that answer. No switch within a task.

## Evidence schema and custody

`evaluation.json` contains evaluation version, pack digest, phase, task records,
per-model role summaries, reliability counters, tied qualified groups, final result,
scope/cost/repeatability limits. It is written atomically to a fresh temporary
operator custody directory, with separate numbered attempt stores for each host.
No raw model text, proposed file content, credentials, exception messages or
arbitrary provider keys are retained by the evaluation report. Existing governed
attempt custody semantics remain unchanged.

The local report is operator evidence, **not authenticated authority**. Closed
shape/size/type validation rejects malformed imports but cannot prove an operator
has not edited valid scores. Preserve the original report and custody together;
do not use this JSON as an authorization token or production policy decision.
The runner offers no resume or repeat authorization through a prior report.

## Operator flow and maintainer validation

Prerequisites: repository root, the existing locked root uv environment with its
development dependencies already installed, Python 3.14, and existing synthetic
TLS test prerequisites used by the KiSSKI validators. No new dependencies or
environment variables. Offline checks use only synthetic/replay/local TLS fixtures.
The validator does not acquire packages, build wheels or contact a provider.

Run only the local validator now:

```powershell
uv run --locked --offline --no-sync python .\validate_forgeai_kisski_coding_model_evaluation_1.py
if ($LASTEXITCODE -ne 0) { throw 'ForgeAI KiSSKI coding-model evaluation validation failed' }
```

It checks exact slice scope, normalized source pins and canonical schema drift,
new contract/scoring/security/inertness controls, existing frozen ForgeAI evaluation
regressions, REMOTE and KiSSKI contracts, architecture, typing, lint, format and
working/staged whitespace. No tests or validators were executed during implementation.

Expected local success:

`FORGEAI-KISSKI-CODING-MODEL-EVALUATION-1 HARNESS LOCALLY QUALIFIED; NO MODEL QUALITY QUALIFIED; NO LIVE EXECUTION AUTHORIZED`

Future attended flow, only after maintainer validation and fresh authorization:

```powershell
uv run --locked --offline --no-sync python -m scripts.kisski_coding_eval.runner --plan
uv run --locked --offline --no-sync python -m scripts.kisski_coding_eval.runner --live --phase A
```

Phase A exact phrase:
`AUTHORIZE FORGEAI-KISSKI-CODING-MODEL-EVALUATION-1 PHASE A LIVE SYNTHETIC`

The default/plan does not prompt, create custody or make provider calls. Live mode
requires an interactive terminal and exact phrase, verifies frozen source identity,
then provisions discovery through hidden S1 input. After discovery, exact model
selection and explicit bounded-phase approval, it provisions chat separately for
`remote-model-bearer`; discovery uses `provider-model-discovery`. No credential
arguments, environment variables, config files or piped input are introduced.

After Phase A evidence is reviewed, a separate future command is:

```powershell
uv run --locked --offline --no-sync python -m scripts.kisski_coding_eval.runner --live --phase B
```

Phase B exact phrase:
`AUTHORIZE FORGEAI-KISSKI-CODING-MODEL-EVALUATION-1 PHASE B LIVE SYNTHETIC`

It requests the Phase A derived-report path, then fresh discovery and eligible
exact IDs. All models/tasks are approved before the bounded phase. No implicit
Phase B, retries, fallback, model reselection or automatic winner deployment.

## Claims and next decision

Local success qualifies the harness only. Await maintainer results before further
implementation or live evaluation. A future live result is evidence for this
frozen scalar pack and role only. Repository disclosure, production mutation,
general coding quality, semantic review reasoning and deployment remain separate
qualification work. No security, capacity, cost or universal provider claim follows.

Suggested commit: `feat(eval): add bounded KiSSKI coding model evaluation harness`

## Phase A inconclusive diagnostic — 2026-10-15

The maintainer qualified the base harness with 1,140 passing tests, typing, lint,
formatting and whitespace checks. Its normalized source manifest digest was
`41b1ac1ecbfea8ab0f6e3112c8dbc74b2313b4fce2a38627a7f8f068cd6091ab`.
This remains historical evidence; the diagnostic-only revision awaits validation.

The subsequent Phase A input was reported as four individually quoted IDs.
`runner.selected()` splits on commas and applies `str.strip()`, which removes
whitespace, not quotation marks. These quoted strings cannot equal the admitted
exact IDs. The existing membership check therefore raises before phase approval,
chat credential provision, `model-N` custody creation, host construction or `invoke()`.
The `finally` block writes the empty inconclusive report; `main()` previously hid
the local selection exception behind the generic inconclusive message.

Preserved evidence at `kisski-phase-a-inconclusive-20261015` was inspected without
modification. The derived report has zero records and empty summaries/reliability.
An immutable read-only SQLite projection of `remote-attempts.db` returned exactly
one provider-control `model-discovery` record, state `completed`, observations
`sent_all` and `response_complete`. The top-level inventory has no `model-N`
directories. Credential source/evidence databases and the writer sidecar were not
opened. No tests, validators, provider calls or credentials were used for diagnosis.

| Classification | Evidence / conclusion |
| --- | --- |
| FACT | Source preserves surrounding quotes and rejects those exact strings. |
| FACT | Preserved report contains no model-quality records. |
| FACT | Inspected root attempt store contains one completed discovery only. |
| FACT | Preserved inventory has no model-specific custody directories. |
| INFERENCE | Given the reported literal input and matching runner version, selection rejection explains this run before chat provision/attempt creation. |
| UNKNOWN | The old report did not persist the input or a selection failure enum; the historical exception itself cannot be independently recovered. |

For this traced input there is no model task invocation and no chat effect: NONE
by control-flow inference, not a fabricated attempt state. Discovery did occur and
has known completed transport observations; do not label the whole run no-I/O.
Empty records alone would not prove no send for a different exception after an
invocation. In such a case preserve UNKNOWN until the relevant custody is inspected.

Safe custody inspection can project enum-validated `state`, `observations`, record
`kind`, `control`, and `method`; bounded validated attempt/execution IDs and timestamps
are also non-content metadata. Prefer named columns and JSON field projections,
never `SELECT *` or dumping `record`: the latter contains a Secret reference and
other unnecessary identities. Do not read `discovery-secret-uses/source.db` or
`evidence.db` for this diagnosis. The `.writer` file is an admission sidecar, not
proof of a chat send. No custody recovery, reopening as writer, or replay is needed.

Correction: preserve exact admission and reject quotation marks explicitly with
`MODEL_SELECTION_QUOTED`; other invalid selections use `MODEL_SELECTION_INVALID`.
These closed enums appear in console output and in the optional `selection_failure`
field of newly written reports. No input or raw exception text is retained. Other
failures remain generic; no speculative credential/custody/protocol diagnosis is
invented. The prompt now says no quotation marks. Required operator syntax is:

```text
qwen3-coder-next, qwen3.5-397b-a17b, deepseek-v4-flash-0731, glm-5.3-flash
```

This syntax example is not authorization to retry. Frozen tasks, prompts to the
model, scoring, call budgets and production behavior remain unchanged. Only the
runner source pin changes. The existing validator is reused with focused offline
tests for quote rejection, safe diagnostics, pre-chat ordering and exact scope.
The original scope exception covered only the untracked report. After both
historical reports became tracked, the validator was corrected to pin their exact
index and working contents. Changed reports or unrelated files remain rejected.
It never reads the preserved custody as a test fixture.

Run the existing maintainer validator command above, then return its output.
No live retry is authorized. Suggested correction commit:
`fix(eval): diagnose quoted model selection before chat provisioning`.

## Phase A partial-run diagnostic — 2026-10-15

The maintainer subsequently validated the selection diagnostic: 1,151 tests,
typing, lint, format and whitespace passed. The partial-run diagnostic was then
maintainer-validated: 1,162 tests, typing, lint, format and working/staged whitespace
passed, with source manifest
`6ab24a42647e9c46aa594efcd24d8b212cd7755f2b16cf38dded75220dfedac9`.
No live retry is authorized.

Preserved custody inspected read-only:
`C:\Users\nisha\AppData\Local\Temp\kisski-coding-eval-1o169lhx`.
The derived report confirms one successful `qwen3-coder-next` / `bug` record,
execution `exec-6104a0fb84d34d3ca3fc5aba30ae3eae`, contract VALIDATED, all recorded
coding checks passing. This evidence remains valid but insufficient for complete
model qualification. It is not converted to zero model evidence.

Only one model directory (`model-0`) exists. Immutable read-only named SQLite
projections found one completed root discovery attempt and one completed model
attempt matching that execution ID. Both have `sent_all` and `response_complete`.
No second model attempt exists in the preserved store. The writer sidecars and
credential source/evidence databases were not opened; raw records, prompts,
responses and headers were not selected. Original custody was not modified.

At the time of the failed run, ordering was model-major and task-minor: the loop retains the host
for `qwen3-coder-next`, then advances from `bug` to `refactor`, followed by `api`
and `diagnosis`. After `bug`, it saves the report, prints the completed row,
checks the outcome, and starts `asyncio.run(invoke(...refactor...))`.

Source-level cause: each `asyncio.run` creates a new event loop. The governed
host's `local._LocalGovernedHost._enter_async` guard binds the first loop and raises
`HostError(HostFailure.WRONG_EVENT_LOOP)` on a different loop. `governed_chat`
calls that guard before admission, dispatch or provider work. The refactor context
may have been minted, but no second durable remote attempt/send is reached.
This is a boundary-B failure (entering the second host invocation), before the
second provider invocation; it is not scoring or evidence persistence after a
second response. The old handler discarded the safe HostFailure category.

| Classification | Finding |
| --- | --- |
| FACT | Report and model custody confirm completed `qwen3-coder-next` / `bug`. |
| FACT | Only one model directory and one model attempt; no second durable attempt. |
| FACT | The failed-run runner created a fresh event loop per task; host forbids changing loops. |
| INFERENCE | Under this source/run ordering, second `refactor` invocation hits `wrong_event_loop` before send; second effect NONE. |
| UNKNOWN | Historical exception/category and second in-memory execution ID were not persisted. No second provider response is evidenced. |
| INFERENCE | Replaying the whole phase would duplicate the known completed bug call. No uncertain second send is indicated by this guard and custody; retry remains unauthorized. |

Diagnostic-only change: at the invocation boundary retain native HostFailure
categories, or `UNKNOWN_INVOCATION_FAILURE` for other exceptions/interruption.
New reports may add `phase_failure_stage=MODEL_INVOCATION`,
`phase_failure_category`, `last_completed_model`, `last_completed_task`,
`next_model`, `next_task`, and `failure_effect`. Identifiers are restricted to the
frozen model/task inventories. Only the inspected `wrong_event_loop` guard maps
to NONE; all other thrown failures conservatively map to UNKNOWN. Normal returned
provider failures retain their existing record semantics. Partial records are
preserved without inventing a second quality score or incrementing response counts.
Safe failure fields are printed before cleanup so report-write failure cannot
erase them from attended output. Original exception text is never emitted.

No loop lifecycle repair, capacity change, task reorder, skip, resume or replay is
implemented here. A separate authorized fix must consider both a single host event
loop lifetime and the reused qualification host's `max_executions=2` against four
tasks per phase. Neither is fixed by this diagnostic slice; another live evaluation
would still encounter the loop guard.

The existing validator covers added synthetic tests for preserving the first row,
second-task identity, native loop/capacity categories, unknown/cancelled effect
conservatism, absence of retries, and canary suppression. Only runner source pins
are refreshed; task and scorer pins stay unchanged. Suggested commit:
`fix(eval): preserve safe partial-run invocation diagnostics`.


## Phase A host-lifecycle correction — 2026-10-15

FORGEAI-KISSKI-CODING-EVAL-HOST-LIFECYCLE-1 is implemented in evaluation tooling;
local validation is NOT RUN — Awaiting user execution. Earlier diagnostic
validation passed as recorded above; this new lifecycle correction is pending.

The historical root cause was reuse of one governed host across per-task
`asyncio.run` loops. The public host contract correctly binds async use to one
loop. The runner now constructs each model host inside `run_model_tasks` and
awaits its frozen tasks sequentially. Exactly one `asyncio.run` surrounds each
model sequence. The host is not retained or reused across models or phases; its
loop closes before the next model host is constructed. No production host guard
or resource-management API changes are made.

The runner admits only phases A/B with exactly four frozen tasks before I/O.
It replaces only the evaluation host configuration's `max_executions` with
`len(tasks)`. Phase A and Phase B each receive four slots; the shared qualification
configuration and production defaults remain unchanged. A fifth task is never
scheduled. Frozen tasks, prompts, scoring, call quotas, provider settings and
credential/disclosure/custody boundaries are unchanged.

Model-major/task-minor ordering is preserved: Phase A runs bug, refactor, api,
diagnosis before the next model; Phase B retains frozen pack order. There is no
concurrency, retry, resume, replay, fallback, model reselection or skip-completed
behavior. A returned invocation failure stops the whole phase, as does a thrown
failure. Completed rows and bounded diagnostics remain persisted; UNKNOWN failures
remain UNKNOWN. The existing known loop-guard diagnostic is unchanged.

Both preserved historical report directories remain untouched and content-pinned.
Their partial results are not imported into a fresh Phase A run. Existing Phase B
screening remains unchanged; this correction adds no continuation mechanism.

Offline fake-host tests cover both phases, construction and invocation on the
same loop, distinct loops/hosts per model, four-slot capacity, no fifth call,
sequential order, no concurrent calls, returned failures, unknown exceptions,
partial evidence and rejection of zero/unexpected task counts before I/O.
Existing selection, diagnostic, report-pin and production regression suites remain
in the reused validator. No tests, validators, builds or live calls were run by
the implementation agent, and no credentials were accessed.

After successful maintainer validation only, the expected claim is:

```text
FORGEAI-KISSKI-CODING-EVAL-HOST-LIFECYCLE-1 LOCALLY QUALIFIED;
NO MODEL QUALITY QUALIFIED;
NO LIVE EXECUTION AUTHORIZED
```

A completely fresh live Phase A requires implementation, maintainer validation,
commit and fresh explicit authorization. It must not reuse historical partial
records. This change does not claim Phase A passed or any model coding quality.

Suggested commit: `fix(eval): bound model tasks to one governed host event loop`.
