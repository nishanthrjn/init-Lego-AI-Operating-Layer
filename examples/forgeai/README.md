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
- **Exactly one rework.** A second `CHANGES_REQUIRED` stops the run.
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
uv run python demo.py            # review #1 accepts: 2 model calls
uv run python demo.py rework     # review #1 requires changes, one rework: 4 model calls
uv run forgeai <repo> --objective "..." --target src/pkg/mod.py --target tests/test_mod.py --replay coding-1.json --replay review-1.json [--replay coding-2.json --replay review-2.json]
```

`demo.py` is a test harness. It commits the fixture into a temporary
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
uv run python .\validate_forgeai_3.py
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
