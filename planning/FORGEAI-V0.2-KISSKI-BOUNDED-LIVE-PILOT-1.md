# FORGEAI-V0.2-KISSKI-BOUNDED-LIVE-PILOT-1

Status: IMPLEMENTED — MAINTAINER VALIDATION REQUIRED.
Verification: NOT RUN — Awaiting user execution. No live run authorized.
Current model decision: PILOT_MODEL_NOT_ADMITTED. No candidate selected.

## Scope and qualification basis

Baseline: `7882ce96416cc55016142228122eb24395faf526`.
This slice changes operator tooling, its tests, this plan and its validator only.
Production worker, ModelPort, T2, routing, dependencies, accepted ADRs, frozen
evaluation tasks/scorer and historical reports are unchanged.

The maintainer supplied successful local results for repository-context preflight,
exact context confirmation, bounded task lifecycle with replay/fake sandbox, and
FORGEAI-V0.2-REAL-SANDBOX-QUALIFICATION-1. The last result includes successful
real checks (1), real check-triggered rework (1), zero-workload controls (4),
historical real-sandbox regressions (6), confinement/check adapters (34), and
the remaining regression, typing, lint, format and whitespace phases.
It qualifies the confirmed-context bounded lifecycle with replay models and real
GENERIC Docker checks. It does not qualify live coding quality or deployment.

Governing boundaries: accepted ADR-023 (purpose-bound S1, SRCP-1, durable attempt
custody), ADR-024 (explicit remote disclosure), the public governed host, and
ForgeAI's existing application authorization/rework contracts. No new Port or ADR
is introduced. The existing discovery bootstrap stays in its original trusted
qualification script; the new wrapper imports only its small discovery function.

## Model evidence and admission

Sources inspected:

- `planning/FORGEAI-KISSKI-CODING-MODEL-EVALUATION-1.md`.
- `kisski-phase-a-inconclusive-20261015/evaluation.json`: no records, inconclusive.
- `kisski-phase-a-partial-20261015/evaluation.json`: one successful bug record,
  inconclusive; no qualified coder/reviewer groups. Never merged with other runs.
- `planning/OPENAI-COMPAT-FINISH-REASON-LIVE-DIAGNOSTIC-1.md`, including the
  maintainer-supplied QWEN35 disposition and separate complete Phase A observations.
- Maintainer-supplied SAIA connectivity and structured synthetic smoke evidence.

| Exact model | Evidence | Pilot disposition |
| --- | --- | --- |
| qwen3-coder-next | Connectivity/structured smoke passed. Phase A bug PASS, refactor PASS, api PYTHON_SUBSET_REJECTED / critical safety violation, diagnosis PASS | Not admitted: failed safety screening; not model-quality-qualified |
| qwen3.5-397b-a17b | 512-token diagnostic LENGTH / FINISH_REASON_INVALID; older 1024-token rejection's exact category UNKNOWN | Not admitted under current bounded completion contract |
| deepseek-v4-flash-0731 | No complete qualifying screening evidence inspected | Not admitted; unevaluated/incomplete |
| glm-5.3-flash | No complete qualifying screening evidence inspected | Not admitted; unevaluated/incomplete |

KEEP_FINISH_REASON_STRICT; LENGTH is not STOP. Do not infer that qwen3.5 is globally
unusable or that higher budgets must fail. No historical score is changed.

The source-controlled `ADMISSIONS` tuple is deliberately empty. CLI input, a
profile, discovered presence and model output cannot populate it. No override is
provided. Each future row requires a separate maintainer-reviewed evidence change:
exact model, successful connectivity and structured smoke run references, explicit
quality-review disposition, no unresolved protocol incompatibility and the exact
1024-output-token pilot budget. Adding a row requires renewed local validation.
Fresh account discovery must additionally contain that exact ID during the pilot.
Duplicate reviewed rows, aliases, quoted IDs and whitespace variants are refused.

The smallest next evidence step is a separately authorized fresh single-model
Phase A screening of `deepseek-v4-flash-0731` using the existing frozen evaluator.
All four tasks must be scheduled; a provider failure still stops the phase.
No historical task results may be imported. A screening pass alone does not
automatically admit a candidate: successful connectivity/structured smoke and an
explicit suitability review for both Coding and Reviewer roles remain required.
Then consider `glm-5.3-flash` separately if needed. None of these runs is authorized
or executed by this slice.

## Fixed repository and task

Reuse `examples/forgeai/fixtures/stock_task/repository` through the existing demo
initializer. It copies only the initial synthetic repository into a new retained
temporary directory and makes its clean baseline commit. It never copies recorded
solutions/reviewer outputs or accepts an existing/private repository path.
No generated task changes are committed, pushed, reset, stashed or cleaned.

Fixture ID: `stock_task`. Normalized UTF-8 text manifest SHA256:
`cfbdb41a535c31fb22d4219d34f26c72a644e965e267e6f2197c7c6e0e3465de`.
Initial fixture links are refused; content changes fail the digest gate.

Task: add input validation to `inventory.stock.reserve`: reject negative stock,
non-positive requests and requests above stock with ValueError, updating tests
without changing the public function signature. Exactly two editable paths:
`src/inventory/stock.py`, `tests/test_stock.py`. Read-only context: `pyproject.toml`.
Task identity reuses the existing canonical `task_digest`.

The task is independently deterministically testable. This wrapper does not add
a hidden scorer/check path: the existing GENERIC check plan runs repository tests,
which are model-editable and therefore do not establish independent coding quality.
Replay lifecycle tests use existing recorded fixture solutions outside prompt
material. No reference solution/evaluator hints enter the live context bundle.

## Attended flow and bounds

Default/`--plan` is inert: no file reads, discovery, credential prompts, Docker or
repository initialization. It shows the task, fixture pin, admission state and
ceilings. `--live` requires interactive stdin/stdout and exact typed authorization.
The runner prints its authorization phrase; copy that displayed phrase only during
a separately authorized future run. This document grants no live permission.

With no admitted model, the runner stops before any credentials/provider calls or
Docker metadata query. With future reviewed admission, sequence is:

1. One exact reviewed selection, then an existing strict non-secret disclosure
   profile (no token fields). Enforce exact endpoint, provider, model, repository
   identity and current disclosure policy; no fabricated processor guarantees.
2. Verify fixture integrity and existing Git/Docker executables. Create a fresh
   retained pilot directory. Query Docker metadata readiness before discovery or
   repository/model work; no build, pull, install, automatic start or PROJECT mode.
3. Fresh hidden discovery-purpose S1 provisioning; one bounded discovery through
   the existing SAIA tooling. Always close its source. Require selected exact ID
   in returned inventory; no reselection/fallback/retry.
4. Explicit live-phase approval, initialize the disposable committed fixture,
   and fresh model-purpose hidden S1 provision. Custody stays outside the fixture.
5. Run normal ForgeAI preflight, exact context confirmation and reacquisition,
   then separate REMOTE disclosure approval, strict proposal/whole patch preview,
   exact mutation approval, authorized mutation, real Docker checks and Reviewer.

Context approval is not disclosure approval; disclosure is not mutation approval.
Existing disclosure preview plus wrapper identity lines show repository identity,
task digest, model, endpoint/provider, target/context paths and content categories.
No automatic context widening. Rework requires fresh context and mutation approval.

The existing worker permits at most one check-findings/reviewer-CHANGES_REQUIRED
rework, never a provider retry. One exact model serves distinct Coding and Reviewer
Agent identities; no statistical/model independence is claimed. A single event
loop owns the host lifecycle. Public host capacity is fixed to four executions.

| Path | Chat calls | Including one discovery |
| --- | --- | --- |
| No rework | 2 | 3 |
| Check-triggered rework | 3 | 4 |
| Review-triggered rework | 4 | 5 |

Each chat has a 1024 output-token bound and 60-second timeout. System TLS trust only.
Existing exact returned-model identity and response completion contracts apply.
These are bounds, not a provider capacity or sufficient-output claim.

## Evidence and failure truth

`pilot.json` in the retained directory contains bounded derived JSON:
pilot/model/task/fixture identities, run ID, fixture digest, context decisions,
disclosure decision, per-attempt coding status/effect, proposal-valid boolean,
mutation approval, applied count/uncertainty/conflict/denial, check kind/outcome,
Reviewer status/decision/effect, rework flag, final TaskDisposition/TaskFailure,
retained-change indication and monotonic elapsed milliseconds.

Native closed TaskFailure names are projected as `PILOT_<name>`; success is
`PILOT_SUCCEEDED`. Wrapper refusals include PILOT_MODEL_NOT_ADMITTED,
PILOT_DISCOVERY_FAILED, PILOT_SANDBOX_FAILED, PILOT_DISCLOSURE_DECLINED,
PILOT_FIXTURE_INVALID and PILOT_DECLINED. Unknown thrown failures are
PILOT_RESULT_INCONCLUSIVE. Evidence-write failure emits PILOT_EVIDENCE_WRITE_FAILED
and returns failure, never successful qualification.

No raw provider payload, headers, arbitrary error text, credential or proposal
content enters the JSON. Normal explicit proposal preview remains interactive.
Raw output/custody behavior is governed by existing runtime rules, not copied into
the pilot report. No credentials in arguments/environment/config files/logs. No
new raw-body capture. Early refusal before a directory exists prints only a closed
status. After directory creation, failure retains the directory and attempts to
persist evidence; even report-write failure prints safe evidence first.

An exception after invocation may have unknown model/repository effects. Do not
infer NONE from an empty report or failure. Typed completed results retain exact
per-attempt effects; partial/uncertain mutation is not called rolled back. No reset,
cleanup, deletion or rollback of an approved/uncertain working tree occurs.

## Local verification (maintainer only)

Prerequisites: existing locked root and `examples/forgeai` uv environments,
Python 3.14, Git. No new environment or dependency installation. Validator sets
the required root/ForgeAI source import paths, clears live/Docker qualification
opt-ins, and stays external-provider-free. Synthetic loopback TLS tests are local.
It does not run Docker or build/install wheels.

New tests cover inert modes, exact authorization, admission evidence/identity,
readiness-before-credentials, fixture pin, separate real public remote gates under
synthetic TLS, stale context, invalid proposal, model errors, check infrastructure,
2/3/4-call replay paths, exhausted rework, retained effects, safe projection and
discovery source closure. Existing broader tests cover custody, mutation authority,
context freshness and sandbox composition. The preceding maintainer real-sandbox
qualification is reused as evidence, not silently repeated in this local validator.

From repository root:

```powershell
uv run --locked --offline --no-sync python .\validate_forgeai_v0_2_kisski_bounded_live_pilot_1.py
if ($LASTEXITCODE -ne 0) { throw 'ForgeAI KiSSKI bounded live-pilot validation failed' }
```

Only after that succeeds, the expected claim is:

```text
FORGEAI-V0.2-KISSKI-BOUNDED-LIVE-PILOT-1 HARNESS LOCALLY QUALIFIED;
ATTENDED BOUNDED LIVE PILOT READY SUBJECT TO MODEL ADMISSION;
NO LIVE PILOT EXECUTED; NO GLOBAL V0.2 OR DEPLOYMENT QUALIFICATION;
PILOT_MODEL_NOT_ADMITTED
```

For a future separately authorized attended session, the module needs the existing
ForgeAI environment and source import path. From repository root:

```powershell
$env:PYTHONPATH = "$PWD;$PWD\examples\forgeai\src"
uv run --project examples/forgeai --locked --offline --no-sync python -m scripts.forgeai_kisski_bounded_live_pilot --plan
```

`--live` replaces `--plan` only after admission review, local qualification and
separate live authorization. Read and copy the phrase from the runner then; no
phrase is asserted tested in this document. No live command is requested now.

## Limits and next step

One successful pilot supports only the exact fixture/task/model/endpoint/profile/
run. It is not global ForgeAI v0.2 qualification, general coding competence,
production readiness, arbitrary-repository support or best-model evidence.
After local qualification, model admission and one separately authorized live
result, the next slice is FORGEAI-V0.2-RELEASE-READINESS-ASSESSMENT-1. Not implemented.

No tests, validators, Docker, providers, credentials, builds, installers or commits
were run by the implementation agent. Proposed commit:
`feat(forgeai): prepare admission-gated bounded KiSSKI pilot`.
