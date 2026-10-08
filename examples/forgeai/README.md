# ForgeAI: reviewed repository task worker with one bounded rework

ForgeAI is an application built on LegoAI. It runs **one bounded coding task**
against **one clean local Git repository**:

1. a model proposal;
2. authorized application of that proposal;
3. contained deterministic verification;
4. **an independent review** of the verified candidate;
5. **at most one rework** if that review requires changes;
6. an evidence-backed result.

It is assembled almost entirely from public LegoAI components. ForgeAI adds
only the task vocabulary, the fixed run sequence, deterministic review and
rework material, and the operator profile. **This is not a self-healing or
autonomous team.** It has no planner, no open-ended loop, no retry and no
memory.

**Status:**
- **ForgeAI-3** (bounded one-cycle rework): locally qualified on 2026-09-29
  for the Windows + Docker Desktop scope with replay models; see
  "ForgeAI-3 qualification evidence".
- **ForgeAI-2** (independent review gate): locally qualified on 2026-09-29.
  Its "CHANGES_REQUIRED stops the run" behavior is superseded by ForgeAI-3's
  single rework.
- **ForgeAI-1** (single task worker without review): locally qualified on
  2026-09-29.
- **ForgeAI v0.1** (supervised local engineering assistant): `forgeai run`
  plus an explicit operator approval before any repository change; see
  "ForgeAI v0.1" below. Locally qualified on 2026-10-08 (`validate_forgeai_v01.py`,
  18/18 phases) with replay models and real sandboxed checks; live-model use is
  unqualified.

## ForgeAI v0.1: supervised local engineering assistant

**Scope.** v0.1 is deliberately small. You get:
- one local Git repository and one task per run;
- targets that you choose, and that the model can never add to;
- the existing reviewed flow with at most one rework.

It does **not** include target discovery, the Repository Analyst or
sufficiency agents, secrets, Git commit/push/PR, durable resume, or hosted
use.

**Supported repositories.** The built-in profile checks a Python repository
laid out as `src/` + `tests/` + `pyproject.toml`. It runs Ruff (`src`,
`tests`), mypy (`src`) and pytest (`tests`) in the qualified Docker checks
image. Other layouts are not supported yet.

**Prerequisites** (Windows + Docker Desktop is the qualified scope):
- Git;
- Docker Desktop (Linux engine) with the CR-2a `PYTHON_CHECKS` image built
  locally;
- `uv`;
- for live use, Ollama with a coding model.

**Setup:**

```powershell
cd examples/forgeai
uv sync --locked
ollama pull qwen2.5-coder:7b   # or any installed model; see --ollama-model
ollama serve                   # if not already running
```

**Run a task.** Start from a committed, clean working tree. Run from
`examples/forgeai`. From the repository root, add `--project
examples/forgeai` (`uv run --project examples/forgeai forgeai run ...`): the
root project does not install the `forgeai` command.

```powershell
uv run forgeai run `
    --repo C:\path\to\repo `
    --task "Reject negative quantities in reserve() and test it" `
    --target src/inventory/stock.py `
    --target tests/test_stock.py
```

- Give 1-8 `--target` paths, relative to the repository. A target is
  updated by default; write `PATH:create` for a new file.
- Add `--constraint TEXT` (up to 8) for extra instructions.
- Model options: `--ollama-model`, `--ollama-url` (default
  `http://127.0.0.1:11434`) and `--ollama-timeout`.
- `--binding replay --replay FILE ...` uses recorded outputs instead of a
  live model.
- The older form `forgeai <repo> --objective ... --target ...` still works
  and also asks for approval.

**What you see:**
1. **Before any model call:** the repository, task, editable targets,
   constraints, checks and model.
2. **Startup failures** stop here with a clear message: missing repository,
   not a Git repository, invalid target, Ollama unreachable or model not
   installed, or no Git/Docker executable. A repository with no commit or
   with uncommitted changes is rejected before the model is called.
3. **Docker readiness**, checked before the scope is shown and before any
   model call. It uses the Engineering sandbox's metadata-only preflight:
   `docker info`, then `docker image inspect` of the pinned checks image. A
   not-ready sandbox refuses the run with `startup refused: ...` and one next
   action, exit code `2`. Nothing is called, written, checked or reviewed.
   - Docker CLI missing, or the Docker Desktop Linux engine unreachable: start
     Docker Desktop (Linux containers).
   - Qualified checks image absent: build it from
     `sandbox-images/python-checks` (CR-2a).
   - Required sandbox controls missing: use the Desktop Linux engine.

   ForgeAI never starts Docker and never pulls or builds images. Ready means
   only "ready right now". Checks can still fail later and are reported
   normally.
4. **Progress lines:** `[1/7] Repository verified`, `[2/7] Proposal
   generated`, `[3/7] Waiting for approval`, `[4/7] Changes applied`,
   `[5/7] Checks completed`, `[6/7] Review completed` and `[7/7] Final
   result`. A rework is announced with `[rework]`.
5. **The proposal**, before anything is written: a short proposal id, each
   changed path with create/update and its size, the per-file reason, the
   summary, risks and unknowns, and then **the exact patch**.
   - The patch is a unified diff of the proposed content against the
     current text the proposal was based on, bounded by
     `--- proposed patch ---` and `--- end of patch ---`. It is rendered in
     memory: no file read, no Git command, no write.
   - Its "before" side is verified against the same content digest the
     mutation precondition enforces, and approval is bound to the shown
     proposal id. What you see is exactly what will be written.
   - Control and bidirectional-text characters in proposed code are shown
     as `\uXXXX` escapes. They can't move the cursor, recolor or reorder
     the screen.
   - Only the whole patch is ever shown. If it exceeds 800 diff lines or
     96 KiB, ForgeAI prints `PREVIEW EXCEEDS DISPLAY BOUND`, does not ask,
     and declines. A change you can't fully see is never applied.

   Read the patch before answering. The checks and the reviewer can both
   miss weak code. In the first live pilot, tests that could never fail
   passed every check and were accepted by the 7B reviewer.

**Approval.** Then comes `Apply this proposal? [y/N]`:
- Only `y` or `yes` applies the proposal. Anything else, an empty answer,
  EOF (closed or empty stdin) or Ctrl+C declines.
- A declined proposal writes **nothing** and runs no checks and no review.
- There is no automatic approval, and no `--yes` flag.
- Approval is bound to the exact change set shown. Approving one proposal
  can never apply a different one, and the existing content preconditions
  still refuse a file that changed in the meantime.
- A rework proposal needs its own approval: `Rework proposal (attempt 2,
  id …)`, the reason, the exact feedback the Coding Agent received, the full
  patch, then `Apply this rework proposal? [y/N]`.

**One bounded rework.** A run has at most two proposals. It gets one rework,
triggered by exactly one of these:
- **The attempt-1 checks reported code findings.** Every configured check
  completed, and each one that didn't pass is `failed` (the tool ran and
  found problems). The Coding Agent gets a bounded excerpt of those checks'
  own output as data: location-bearing lines such as `file.py:14` plus the
  message line before each, at most about 1 KB per check, with a note of any
  lines left out. It gets the same task and the same targets, and it reads
  the *current* candidate files, so the preconditions bind to candidate 1.
  Its new proposal is shown and approved like any other, applied through the
  same authorized mutation, and all checks run again. Candidate 1 is never
  reviewed. If the checks pass, the reviewer reviews candidate 2 once. If
  the reviewer then requires changes, the run stops: the budget is spent.
- **Review #1 required changes**, after all attempt-1 checks passed. This
  is unchanged from ForgeAI-3.

There is never a third proposal. ForgeAI never runs `ruff --fix` or any
other auto-fix, and changes code only through approved proposals.

A check that **could not complete** is never "repaired" by the model:
Docker or sandbox failure, timeout, a tool error, interrupted pytest
collection, or no tests collected. The run stops. A check finding can't
widen the scope either: a rework proposal touching a file outside your
targets is rejected.

**Final result.** The final block lists:
- the disposition and reason;
- run id, starting HEAD and attempt count;
- changed files and each check result;
- the review decision, findings and blocking-finding count;
- risks and unknowns;
- whether HEAD is unchanged;
- a `git -C <repo> diff -- <files>` command for inspecting the change.

No model is used to summarize.

**Invalid model output.** If the Coding Agent or the reviewer returns output
that fails its contract, the result names why. For example:

```
review output invalid:
  reason: REQUIRED_FIELD_MISSING (a required field is missing)
  field: findings[0].required_action
  no retry or repair was attempted; raw output is not shown
```

- **Reasons** are a closed set from the Engineering parsers:
  - `OUTPUT_CONTRACT`, `JSON_DOCUMENT_INVALID`;
  - `DUPLICATE_FIELD`, `REQUIRED_FIELD_MISSING`, `UNKNOWN_FIELD`,
    `FIELD_TYPE_INVALID`, `ARRAY_BOUNDS_EXCEEDED`, `ENUM_INVALID`;
  - `PATH_INVALID`, `PATH_OUT_OF_SCOPE`, `VALUE_INVALID`,
    `FINDING_REFERENCE_INVALID`.
- **The field** is a schema locator, such as `changes[1].reason`. It is
  never model text.
- **Raw model output and prompts are never printed or kept.** The failure is
  unchanged: invalid coding output stops the run with nothing written, and
  invalid review output stops it without retry or rework. Changes already
  applied remain, as the warning says.

**Failures.** There is no retry, no fallback and no rollback. If a run fails
after changes were applied (checks, review, or a declined rework), the result
says so with `WARNING: changes remain in the working tree` and lists the
files. ForgeAI never commits, resets, stashes or cleans. Exit codes: `0`
succeeded, `2` rejected before any model call, `1` everything else.

**Live pilot evidence** (same customers repository, task and targets):
- `qwen2.5-coder:7b`, ×2: correct guard but **vacuous** tests, which pass
  even without the guard. One review ACCEPTed them; one review output was
  invalid.
- `qwen2.5-coder:14b`, ×2: correct guard and **meaningful** tests (they
  fail without the guard), but written with `assert False`, which the
  repository's Ruff rules reject (B011). Without a rework the run stopped at
  checks. That's the case the check-feedback rework now handles: one
  supervised correction, still approved by you. On this machine Ollama ran
  CPU-only, so 14B needed `--ollama-timeout 1200`.

Neither model is qualified by these observations. 14B being better than 7B
is not a qualification.

**Known v0.1 limits.**
- Live-model quality is **unqualified**; only replay runs are qualified.
- The rework gets a bounded excerpt of check output. A finding that needs
  more context, or a file outside the targets, may not be fixable within one
  rework.
- Docker readiness is a point-in-time check. If Docker stops after
  startup, the check step fails after the approved changes were written,
  and the warning lists them.
- Startup checks the Ollama model list only, not the model's quality.

## Workflow

`RepositoryTaskWorker.run(task, context)` claims the workspace, checks the
initial Git state, and then runs **attempt 1**. Only when attempt 1's review
*completed* with `CHANGES_REQUIRED` does it run **attempt 2**, the single
rework. There is never an attempt 3.

1. **Claim the workspace.** The in-process `WorkspaceGuard` refuses a second
   concurrent run on the same repository. The guard stays held for the whole
   run, including any rework.
2. **Observe Git.** The repository must have a commit and no changes, not even
   untracked files. Otherwise the run is rejected. ForgeAI never stashes,
   resets, cleans, checks out or commits.
3. **Attempt**, run once, or twice when a rework happens:
   1. **Propose.** Call `CodingAgent.propose` once. It authorizes and reads the
      **current** content of the targets, then makes one governed model call.
   2. **Apply** through `AuthorizedRepositoryMutation`. Current authority and
      digest preconditions are checked immediately before the write.
   3. **Check.** Run the full configured plan in order (Ruff check, mypy,
      pytest) through `AuthorizedEngineeringChecks` over
      `SandboxedEngineeringChecks`. There is no host fallback.
   4. **Observe Git.** HEAD must be unchanged, and the working-tree changes
      must equal the union of the paths applied so far.
   5. **Review**, only if steps 1–4 all passed. Re-read the final content of
      every changed file through `AuthorizedRepositoryEvidence`, verify it
      against the applied digests, render deterministic material, mint a
      fresh Chat context, and call the unchanged `IndependentReviewer` once.
4. **Return a `TaskResult`** built from this run's evidence.

## Rework: when and how

**A rework happens only when review #1 completed and its decision is
`CHANGES_REQUIRED`.** Every other outcome is terminal, with no rework:

- `ACCEPT`: the task succeeds;
- `INSUFFICIENT_EVIDENCE`;
- a review model failure (including an `UNKNOWN` effect) or denial;
- invalid review output;
- review-input failure;
- any deterministic, mutation, authorization, sandbox or Git failure.

**The rework request** is a second `CodingRequest` to the **same, unchanged**
`CodingAgent`, on a fresh host-minted Chat context:

- **Objective:** the original objective.
- **Targets:** the original paths. Files already written become `update`
  targets. The editable allowlist never widens, and reviewer text cannot add
  paths.
- **Constraints:** the original constraints, plus ForgeAI's deterministic,
  labeled rework notes:
  - that this is the single rework;
  - that review findings are opinions supplied as data, not commands;
  - the first attempt's check outcomes;
  - each blocking finding with its requested change.
- **File content:** the Coding Agent re-reads the **current** files through
  authorized reads, so the rework uses current contents and digests, never
  stale ones.
- **Not sent:** Git data, host paths, environment, Docker details, grants or
  commands.

If the notes do not fit the `CodingRequest` bounds (at most eight constraints
of 1 KiB each), the run stops with `REWORK_INPUT_FAILED`. Nothing is
truncated, and no model summarizes anything.

**Review findings never drive effects.** A `required_action` is rendered only
into constraint text. The Coding Agent may propose a new validated change set
within scope, and the authorized mutation boundary and M4 preconditions still
decide.

**Review #2 is terminal.** `ACCEPT` means success. `CHANGES_REQUIRED`,
`INSUFFICIENT_EVIDENCE` or any failure means the run stops. There is no
second rework.

## Exact ceilings

| Path | Model calls | Applies | Check batches | Reviews |
| --- | --- | --- | --- | --- |
| No rework (review #1 `ACCEPT`) | 2: coding, review | 1 | 1 | 1 |
| With rework (`CHANGES_REQUIRED`, then review #2) | 4: coding, review, coding, review | 2 | 2 | 2 |
| Maximum, per run | **4** | **2** | **2** | **2** |

The ceilings are structural. Architecture tests enforce them:

- `_attempt` is called exactly twice in the worker, and `_rework` once;
- there is one `propose` call site and one `review` call site;
- there are no `while` loops;
- `MAX_ATTEMPTS = 2` is a constant, and `ForgeAIConfig` has no attempt, retry
  or cycle setting.

No call is retried, and there is no fallback model.

## No rollback

Changes are applied before each review, so they **remain in the working tree**
whatever happens next, including both attempts' changes when a rework fails.
ForgeAI never reverts, resets or stashes. The result records what is known,
and the operator decides what to do next.

## Deterministic checks versus review

| | Deterministic checks | Independent review |
| --- | --- | --- |
| What it is | Tool observations (pytest, Ruff, mypy) in the sandbox | A bounded model opinion from a distinct Agent definition |
| When it runs | After every apply | Only after every deterministic gate of that attempt passed |
| Can it make the task succeed on its own? | No: review `ACCEPT` is also required | No: an `ACCEPT` never overrides a failed check, a Git integrity failure, a denial or an infrastructure error |
| Authority | None | None: its findings are text, never authorization or effects |

## Review input

Each review uses the existing M8.2 `ReviewRequest`, with unchanged limits:

- **Producer:** the Coding Agent's actual `AgentId` (`coding-agent`). The
  reviewer is `independent-reviewer`.
- **Criteria:** the fixed operator criteria in
  `ForgeAIConfig.review_criteria`.
- **Proposal:** a deterministic rendering of that attempt's proposal. Review
  #2's rendering is labeled as the rework.
- **Materials:**
  - `checks`: that attempt's check outcomes;
  - `file-1…n`: the final content of **every** file changed in the run, so
    review #2 always sees the final candidate, never first-attempt contents.

Git data is never disclosed. Input that does not fit fails with
`REVIEW_INPUT_FAILED` (`READ_DENIED`, `READ_UNAVAILABLE`, `MATERIAL_BOUNDS` or
`CONTEXT_BUDGET`), never truncated.

## Authorization

Every effect is evaluated against current authority at call time, including
the rework's reads, write and checks. Nothing is cached from attempt 1. A
grant that expires between the attempts fails closed:

- an expired read grant gives `EVIDENCE_DENIED`;
- an expired write grant gives `MUTATION_DENIED`.

Tests cover both. All four model calls use the one Chat grant and the host's
one configured binding; there is no per-attempt or per-Agent routing.

## Reused LegoAI components

| Concern | Component |
| --- | --- |
| Host, authorization and model routing | `open_local_host`, `legoai.runtime.api` (`LocalHostConfig`, `OperatorGrant`, `ModelBindingConfig`, `OllamaSettings`, `TrustedModelContribution`, `HostError`), `agent_runtime`, `model_execution` |
| Reads, proposal and review | `AuthorizedRepositoryEvidence`, `AuthorizedCodingEvidence`, `CodingAgent`, `IndependentReviewer` and its values, all unchanged |
| Workspace and mutation | `LocalRepositoryWorkspace`, `LocalRepositoryMutation`, `AuthorizedRepositoryMutation` |
| Checks and sandbox | `AuthorizedEngineeringChecks`, `SandboxedEngineeringChecks`, `CheckInputPolicy`, `DockerSandbox`, `SandboxImage.PYTHON_CHECKS` |
| Git observation | `LocalGitRepository` / `GitRepositoryPort` (read-only, operator-only) |

**No LegoAI code was changed for ForgeAI-1, ForgeAI-2 or ForgeAI-3.** One
application with one bounded rework is not evidence for a general Workflow
abstraction, so none was added.

## ForgeAI-owned code (`src/forgeai`)

| Module | Layer | Contents |
| --- | --- | --- |
| `domain.py` | Domain | `TaskRequest`, `TaskDisposition`, `TaskFailure`, `ReviewInputFailure`, `CheckRecord`, `AttemptEvidence`, `TaskEvidence`, `TaskResult`, `MAX_ATTEMPTS` |
| `review.py` | Application | Pure rendering: review material, rework targets and rework constraints |
| `worker.py` | Application | `RepositoryTaskWorker`: the fixed sequence of attempt 1 plus at most one rework |
| `guard.py` | Application | `WorkspaceGuard` |
| `composition.py` | Composition root | `ForgeAIConfig`, `local_profile`, `prepare_run`, `run_task` |
| `cli.py` | Presentation | `forgeai`, `summarize`, and the `replay` and `ollama` bindings |

## Configuration boundary

`TaskRequest` holds intent only: the objective, 1–8 `CodingTarget`s and up to
8 constraints.

`ForgeAIConfig` holds all operator configuration:

- the repository root and workspace policy;
- the editable allowlist;
- Git;
- grants for four actions: Chat, read, write, check;
- model bindings and the selection;
- the sandbox;
- the check policies and ordered check plan;
- the review criteria.

There is no attempt, retry or rework-count setting. Switching providers is
configuration-only.

## Dispositions and failures

| Disposition | Meaning | `TaskFailure` reasons |
| --- | --- | --- |
| `SUCCEEDED` | The latest attempt passed every deterministic gate **and** its review completed with `ACCEPT` | — |
| `REJECTED` | Refused before any model call or repository effect | `WORKSPACE_BUSY`, `REPOSITORY_UNAVAILABLE`, `UNSUPPORTED_REPOSITORY`, `DIRTY_START`, `EVIDENCE_DENIED`, `EVIDENCE_UNAVAILABLE` (attempt 1 only) |
| `FAILED`: deterministic step | Work started; a gate failed, so there is no review for that attempt | `MODEL_FAILED`, `PROPOSAL_INVALID`, `MUTATION_DENIED`, `MUTATION_CONFLICT`, `MUTATION_PARTIAL`, `CHECK_DENIED`, `CHECK_ERROR`, `CHECKS_FAILED`, `FINAL_STATE_UNAVAILABLE`, `HEAD_CHANGED`, `UNEXPECTED_CHANGES`, and for the rework's own reads `EVIDENCE_DENIED` / `EVIDENCE_UNAVAILABLE` |
| `FAILED`: review could not complete | Execution failure, not an opinion | `REVIEW_INPUT_FAILED`, `REVIEW_FAILED`, `REVIEW_OUTPUT_INVALID` |
| `FAILED`: review withheld acceptance | Opinion; after attempt 2, or `INSUFFICIENT_EVIDENCE` after attempt 1 | `REVIEW_CHANGES_REQUIRED`, `REVIEW_INSUFFICIENT_EVIDENCE` |
| `FAILED`: rework not started | Review #1 findings did not fit a bounded rework request | `REWORK_INPUT_FAILED` |

**Which attempt failed.** The failure applies to the **latest attempt**. The
result shows where the run stopped through `evidence.attempts` (1 or 2) and
`evidence.reworked`, so the failure vocabulary does not need rework-specific
copies.

## Evidence

`TaskEvidence` holds:

- one run id;
- the start Git state;
- the planned checks;
- `attempts`, a tuple of one or two `AttemptEvidence` values;
- the fixed limitations.

Each `AttemptEvidence` records that attempt's number and:

- its Coding, Agent and model-effect status;
- its proposal and applied mutation result, or its denial, conflict, or
  uncertain and temporary paths;
- its check records;
- its final Git state;
- its review material mapping;
- its review-input failure or its full typed `ReviewResult`.

Single-value views such as `evidence.review` and `evidence.checks` report the
latest attempt. `evidence.changed_paths` is the union of paths across
attempts. The evidence holds no exceptions, environment, host paths or
runtime objects.

## Known limitations

- **Passes are not proof.** Neither a sandboxed `PASSED` nor a review `ACCEPT`
  proves correctness. A rework accepted by the same Agent definitions on the
  same model binding is still an unverified opinion.
- **Findings reach the Coding Agent as constraint text.** It is labeled
  review data, but a model may still treat it as instruction; scope and
  authorization bound what can happen.
- **Exactly one rework.** A second `CHANGES_REQUIRED` stops the run. Since
  v0.1, attempt-1 check findings can consume that same single rework
  instead; see "One bounded rework" above.
- **No rollback.** Failed runs leave both attempts' changes in place.
- **Union-based Git check.** If a rework restores a file to its committed
  content, that file no longer appears changed, and the run reports
  `UNEXPECTED_CHANGES`.
- **No checked-input identity.** The evidence does not record which files
  were copied into the sandbox.
- **Operator-only Git.** Git data is never disclosed to either model.
- **Bounded review input.** The M8.2 review bounds apply to the final
  candidate.
- **In-process guard.** Same-workspace refusal is in-process only.
- **Blocking steps.** Synchronous steps block their thread.
- **Volatile runs.** No durable run store, resume or commits.
- **Replay-only qualification.** `ollama` is configurable but unqualified,
  and live-model proposal, review and rework quality is unqualified.

## Running

```powershell
cd examples/forgeai
uv sync --locked
uv run python demo.py            # review #1 accepts: 2 model calls; answer y
uv run python demo.py rework     # review #1 requires changes, one rework: 4 model calls; answer y twice
uv run forgeai run --repo <repo> --task "..." --target src/pkg/mod.py --target tests/test_mod.py --binding replay --replay coding-1.json --replay review-1.json [--replay coding-2.json --replay review-2.json]
```

`demo.py` is a test harness. It asks for approval like the CLI does. It commits the fixture into a temporary
repository and replays recorded outputs **strictly in call order**. A call
beyond the recorded outputs fails loudly.

Fixtures in `fixtures/stock_task/`:

| File | Role |
| --- | --- |
| `proposal.json` | Coding proposal #1 |
| `review_changes_required.json` | Review `CHANGES_REQUIRED` (review #1, or a terminal review #2) |
| `proposal_rework.json` | Rework proposal |
| `review_accept.json` | Review `ACCEPT` (review #1 or #2) |
| `review_insufficient.json` | Review `INSUFFICIENT_EVIDENCE` |

## Validation

From the repository root, on Windows with Docker Desktop and the CR-2a image
present:

```powershell
uv run python .\validate_forgeai_v01.py   # v0.1 (pipes an explicit "y" to the demos)
uv run python .\validate_forgeai_3.py     # historical; its demo phases now prompt for approval
```

## ForgeAI-3 qualification evidence

On 2026-09-29 the maintainer ran `validate_forgeai_3.py` on Windows with
Docker Desktop, using the recorded CR-2a image. **All phases passed.**

| Area | Result |
| --- | --- |
| No LegoAI source change in this slice | `git diff --exit-code HEAD -- src/legoai packages` clean |
| Static checks | mypy clean on 17 files plus the validator; Ruff lint and format clean |
| Domain and evidence invariants | 19 passed |
| Rework context: rendering, bounds, scope | 3 passed |
| Review #1 gating (no rework unless `CHANGES_REQUIRED`) | 9 passed |
| No-rework `ACCEPT` path | 2 passed |
| `CHANGES_REQUIRED` → rework path | 2 passed |
| Terminal second-review paths | 5 passed |
| Rework proposal failures | 2 passed |
| Second mutation failure | 1 passed |
| Second check and Git integrity failures | 2 passed |
| Authorization re-evaluated for the rework | 2 passed |
| Call and attempt ceilings, guard | 5 passed |
| Architecture and import boundaries | 24 passed |
| Real-Docker rework `ACCEPT`, and second-pass failure | 2 passed |
| Clean-install execution (accept and rework scenarios) | 1 passed |
| ForgeAI-1/2 regressions | 50 passed |
| M8.2 and M8.3 engineering regressions | 84 passed |
| Demos | `accept`: succeeded, 1 attempt. `rework`: succeeded, 2 attempts (attempt 1 review `changes_required`, final review `accept`) |
| `git diff --check` | clean |

This qualifies the bounded one-cycle rework **with deterministic replay outputs
for all four model calls**:

- the rework trigger;
- current-content rework input;
- the unchanged scope;
- the structural ceilings (4 model calls, 2 applies, 2 check batches, 2
  reviews);
- the terminal second review;
- authorization re-evaluated per effect;
- the guard held for the whole run;
- no rollback;
- per-attempt evidence.

It makes no claim about live-model proposal, review or rework quality, or
about reviewer independence beyond a distinct Agent definition. All the
limitations listed above still apply.

## ForgeAI-2 qualification evidence

On 2026-09-29 the maintainer ran `validate_forgeai_2.py` on Windows with
Docker Desktop, using the recorded CR-2a image. **All phases passed.**

| Area | Result |
| --- | --- |
| Static checks | mypy clean on 16 files plus the validator; Ruff lint and format clean |
| Domain-contract extensions | 19 passed |
| Review input: construction, bounds, disclosure | 6 passed |
| Reviewer gating and order | 5 passed |
| ACCEPT path | 2 passed |
| CHANGES_REQUIRED path | 1 passed |
| INSUFFICIENT_EVIDENCE path | 1 passed |
| Reviewer execution failures | 4 passed |
| No rework and no retry | 3 passed |
| Evidence and result invariants | 4 passed |
| Architecture and import boundaries | 21 passed |
| Replay + real-Docker ACCEPT end-to-end | 1 passed |
| Real-Docker pre-review failure paths | 2 passed |
| Clean-install execution | 1 passed |
| M8.2 reviewer regressions | 33 passed |
| ForgeAI-1 regressions | 30 passed |
| README demo | `succeeded`; Ruff, mypy and pytest passed; HEAD unchanged; `review: accept` |
| `git diff --check` | clean |

This qualifies the reviewed application flow **with deterministic replay
outputs for both model calls**:

- review gating after the deterministic gates;
- exactly two model calls;
- the decision mapping;
- the separation of execution failures from opinions;
- no rework or rollback;
- the disclosure boundary;
- the evidence.

It makes no claim about live-model proposal or review quality, and it does
not show that the reviewer is independent beyond having a distinct Agent
definition. All the limitations listed above still apply.

That qualification predates ForgeAI-3. Its "`CHANGES_REQUIRED` stops the run"
behavior is superseded by the single rework. The ForgeAI-2 tests remain in the
suite, updated for that rework.

## ForgeAI-1 qualification evidence

On 2026-09-29, **before the review stage existed**, the maintainer ran
`validate_forgeai_1.py` on Windows with Docker Desktop, using the recorded
CR-2a image. **All 20 phases passed.**

| Area | Result |
| --- | --- |
| Static checks | mypy clean on 14 files plus the validator; Ruff lint and format clean |
| Domain contracts | 17 passed |
| Clean-start gate | 3 passed |
| Fake model and Coding Agent | 5 passed |
| Authorized mutation | 3 passed |
| Check orchestration | 2 passed |
| Check infrastructure failures | 5 passed |
| Final Git state | 3 passed |
| Run isolation and same-workspace policy | 3 passed |
| Architecture and import boundaries | 15 passed |
| Real-sandbox end-to-end fixture task | 1 passed |
| Real-Docker finding and missing-Docker paths | 2 passed |
| Provider/config substitution and CLI | 6 passed |
| Clean-install package | 1 passed |
| LegoAI engineering regressions | 133 passed |
| README demo | `succeeded`; Ruff, mypy and pytest passed; HEAD unchanged; 2 files changed |
| `git diff --check` | clean |

That run qualified the ForgeAI-1 composition, governance, mutation, sandboxed
check and evidence flow with a deterministic replay model. The ForgeAI-1
tests remain part of the suite; with ForgeAI-2, their success paths also
require the review `ACCEPT`.
