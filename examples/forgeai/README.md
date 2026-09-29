# ForgeAI: reviewed single repository task worker

ForgeAI is an application built on LegoAI. It runs **one bounded coding task**
against **one clean local Git repository**:

1. one model proposal;
2. authorized application of that proposal;
3. contained deterministic verification;
4. **one independent review** of the verified candidate;
5. an evidence-backed result.

It is assembled almost entirely from public LegoAI components. ForgeAI adds
only the task vocabulary, the run sequence, deterministic review material and
the operator profile. This is a single fixed sequence, not an autonomous
engineering team: there is no planner, rework loop, retry or memory.

**Status:**
- **ForgeAI-2** (independent review gate): locally qualified on 2026-09-29
  for the Windows + Docker Desktop scope with replay models; see
  "ForgeAI-2 qualification evidence".
- **ForgeAI-1** (single task worker without review): locally qualified on
  2026-09-29; see "ForgeAI-1 qualification evidence".

## Workflow

`RepositoryTaskWorker.run(task, context)` performs these steps, in this order,
once per run. Nothing is hidden, and nothing is retried.

1. **Claim the workspace.** The in-process `WorkspaceGuard` refuses a second
   concurrent run on the same repository.
2. **Observe Git** through `GitRepositoryPort`. The repository must have a
   commit and no changes, not even untracked files. Otherwise the run is
   rejected. ForgeAI never stashes, resets, cleans or commits.
3. **Propose** (model call 1). `CodingAgent.propose` is called **exactly
   once**. It performs the authorized, bounded reads of the target files, then
   one governed model call, and returns a validated M4 change set. The model
   proposes; it never applies.
4. **Apply** through `AuthorizedRepositoryMutation`, which wraps
   `LocalRepositoryMutation`. Authority is checked immediately before the
   write, and the digest preconditions are enforced.
5. **Check.** The configured checks run in order (Ruff check, mypy, pytest)
   through `AuthorizedEngineeringChecks` over `SandboxedEngineeringChecks` on
   `SandboxImage.PYTHON_CHECKS`. There is no host check adapter and no
   fallback.
6. **Observe Git again.** HEAD must be unchanged, and the working-tree changes
   must be exactly the applied paths.
7. **Review** (model call 2). This step runs **only if steps 3–6 all passed**:
   1. The final content of the applied files is read through the same
      `AuthorizedRepositoryEvidence` (the `read-for-model-analysis` grant), and
      each file is verified against its applied digest.
   2. ForgeAI renders deterministic review material and mints a **fresh**
      Chat `ExecutionContext` from the host.
   3. The unchanged `IndependentReviewer` is called **exactly once**.
8. **Return a `TaskResult`** built from this run's evidence.

A successful run makes **exactly two model calls**: the Coding Agent, then the
reviewer. There is never a third call, and there is no fallback.

## Deterministic checks versus review

| | Deterministic checks | Independent review |
| --- | --- | --- |
| What it is | Tool observations (pytest, Ruff, mypy) in the sandbox | A bounded model opinion from a distinct Agent definition |
| When it runs | After apply | Only after every deterministic gate passed |
| Can it fail the task? | Yes | Yes |
| Can it make the task succeed on its own? | No: review `ACCEPT` is also required | No: an `ACCEPT` can never override a failed check, a Git integrity failure, a denial or an infrastructure error |
| Authority | None | None: it is not authorization, and it never edits, applies or reruns anything |

## Review decisions

| Reviewer outcome | ForgeAI result |
| --- | --- |
| `ACCEPT` | `SUCCEEDED`, provided every deterministic gate passed |
| `CHANGES_REQUIRED` | `FAILED` / `REVIEW_CHANGES_REQUIRED`. The blocking findings and their required actions are recorded as text only |
| `INSUFFICIENT_EVIDENCE` | `FAILED` / `REVIEW_INSUFFICIENT_EVIDENCE`. The reviewer's unknowns are recorded |

**No rework.** On `CHANGES_REQUIRED` the run **stops**. It does not call the
Coding Agent again, patch files from `required_action`, rerun checks or rerun
the review.

**No rollback.** The review happens after the changes were applied, so they
**remain in the working tree**. The result records:

- the applied paths and digests;
- the check results;
- the final Git state;
- the full review.

The operator decides what to do next.

## Review input

ForgeAI builds the existing M8.2 `ReviewRequest`, whose limits are unchanged:

- **Producer:** the Coding Agent's actual `AgentId` (`coding-agent`), taken
  from its `AgentResult`. The reviewer is `independent-reviewer`.
- **Objective:** the task objective.
- **Criteria:** a fixed operator set in `ForgeAIConfig.review_criteria`:
  correctness, requested behavior, test adequacy, maintainability and
  unintended changes. Task and model output cannot change them. There are no
  scores or rankings.
- **Proposal:** a deterministic textual rendering of the validated
  `CodingProposal`: summary, each change with its reason, risks and unknowns.
- **Materials:** at most eight:
  - `checks`: the deterministic check outcomes only, with no tool output;
  - `file-1`, `file-2`, …: the final content of each applied file, in apply
    order. The mapping from material ID to path is kept in `TaskEvidence`.
    Material IDs are labels, not paths or canonical Evidence.

**Not disclosed to the reviewer:** Git data (branch, commit, status),
unrelated files, hidden files and environment data.

**Nothing is ever truncated, summarized by a model or compressed.** Review
input that does not fit fails with `REVIEW_INPUT_FAILED` and a
`ReviewInputFailure`:
- `READ_DENIED` or `READ_UNAVAILABLE`: the authorized re-read failed;
- `MATERIAL_BOUNDS`: an M8.2 value bound was exceeded, for example a changed
  file larger than 4 KiB or more than seven changed files;
- `CONTEXT_BUDGET`: the serialized request exceeds the reviewer's input budget.

## Reused LegoAI components

| Concern | Component |
| --- | --- |
| Host, authorization and model routing | `legoai.runtime.local.open_local_host`, `legoai.runtime.api` (`LocalHostConfig`, `OperatorGrant`, `ModelBindingConfig`, `OllamaSettings`, `TrustedModelContribution`, `HostError`), `GovernedHost.agent_runtime`, `model_execution` |
| Authorized reads, proposal and review | `AuthorizedRepositoryEvidence`, `AuthorizedCodingEvidence`, `CodingAgent`, and `IndependentReviewer` with its `ReviewRequest` / `ReviewMaterial` / `ReviewResult` / `Review` / `ReviewDecision` values, all unchanged |
| Workspace and mutation | `LocalRepositoryWorkspace`, `LocalRepositoryMutation`, `AuthorizedRepositoryMutation` |
| Checks and sandbox | `AuthorizedEngineeringChecks`, `SandboxedEngineeringChecks`, `CheckInputPolicy`, `DockerSandbox`, `SandboxImage.PYTHON_CHECKS` |
| Git observation | `LocalGitRepository` / `GitRepositoryPort` (read-only, operator-only) |

No LegoAI code was changed or copied for ForgeAI-1 or ForgeAI-2.

**Both Agents use the host's one configured `engineering-reasoning` binding.**
The public host pins one binding, so there is no per-Agent provider routing.
Identity separation proves distinct Agent **definitions**. It does not prove
distinct model weights, providers or principals, or guaranteed independence.

## ForgeAI-owned code (`src/forgeai`)

| Module | Layer | Contents |
| --- | --- | --- |
| `domain.py` | Domain | `TaskRequest`, `TaskDisposition`, `TaskFailure`, `ReviewInputFailure`, `CheckRecord`, `TaskEvidence`, `TaskResult` |
| `review.py` | Application | Pure, deterministic review-material rendering |
| `worker.py` | Application | `RepositoryTaskWorker`, which depends on Ports, the two Agents and values only |
| `guard.py` | Application | `WorkspaceGuard`, an in-process same-workspace refusal |
| `composition.py` | Composition root | `ForgeAIConfig`, `local_profile`, `prepare_run`, `run_task`; the only module that opens the host or names adapters |
| `cli.py` | Presentation | the `forgeai` command, the bounded `summarize`, and the `replay` and `ollama` bindings |

## Configuration boundary

`TaskRequest` holds **intent only**:
- `objective`;
- 1–8 `CodingTarget`s (path plus create or update);
- up to 8 constraints.

It never carries a repository root, model, provider, URL, key, grant,
executable, image, command or review policy.

Operator configuration is `ForgeAIConfig`. It covers:

- the repository root and `WorkspacePolicy`, and the editable-path allowlist;
- the Git executable and `GitReadPolicy`;
- host principal, tenant, policy and grants for exactly four actions:
  - `invoke-capability` for Chat, covering both model calls;
  - `read-for-model-analysis`, covering the Coding reads and the review re-reads;
  - `apply-repository-changes`;
  - `run-engineering-check`;
- model bindings and the selection;
- the Docker executable, the `SandboxPolicy` and the closed `SandboxImage`;
- `CheckInputPolicy`, `CheckPolicy` and the ordered check plan;
- the review criteria.

**Switching providers is configuration-only.** Changing the selected binding
changes no ForgeAI code. A provider LegoAI does not support still needs a new
adapter, written in code.

## Supported scope

- **Tasks:** update or create 1–8 files of at most 8 KiB each, solvable by one
  proposal. Deleting files is not supported. To be **reviewable**, each
  changed file must fit a 4 KiB review material, and at most seven files may
  change.
- **Repositories:** a local, non-bare Git repository with a commit, in the
  `src/` + `tests/` + `pyproject.toml` layout, small enough for the qualified
  sandbox.
- **Platform:** Windows with the Docker Desktop Linux engine.

## Dispositions and failures

| Disposition | Meaning | `TaskFailure` reasons |
| --- | --- | --- |
| `SUCCEEDED` | Every deterministic gate passed **and** the review completed with `ACCEPT` | — |
| `REJECTED` | Refused before any model call or repository effect | `WORKSPACE_BUSY`, `REPOSITORY_UNAVAILABLE`, `UNSUPPORTED_REPOSITORY`, `DIRTY_START`, `EVIDENCE_DENIED`, `EVIDENCE_UNAVAILABLE` |
| `FAILED` (before review) | Work started; a deterministic gate failed, so no review was run | `MODEL_FAILED`, `PROPOSAL_INVALID`, `MUTATION_DENIED`, `MUTATION_CONFLICT`, `MUTATION_PARTIAL`, `CHECK_DENIED`, `CHECK_ERROR`, `CHECKS_FAILED`, `FINAL_STATE_UNAVAILABLE`, `HEAD_CHANGED`, `UNEXPECTED_CHANGES` |
| `FAILED` (review could not complete) | Execution failure, not an opinion | `REVIEW_INPUT_FAILED`, `REVIEW_FAILED` (the review model call was denied or failed; the effect extent is kept, including `UNKNOWN`), `REVIEW_OUTPUT_INVALID` (malformed output, or findings that cite unsupplied material) |
| `FAILED` (review withheld acceptance) | The review completed with an opinion | `REVIEW_CHANGES_REQUIRED`, `REVIEW_INSUFFICIENT_EVIDENCE` |

**Tool findings versus infrastructure failures.** Tool findings are
`CheckResult`s, so the run reports `CHECKS_FAILED`, and every configured check
still runs. Infrastructure failures are reported as `CHECK_ERROR`, and the
remaining checks do not run.

**After a failure.** Applied changes stay applied. There is no rollback,
reset, retry or recovery. After any failure that follows a write, the final
Git state is still observed (read-only) and recorded.

## Evidence

`TaskEvidence` is bounded and composed only from existing LegoAI values:

- the run id;
- the starting and final Git state, or the Git failure;
- the Coding status, Agent status and model effect;
- the proposal and the applied mutation result;
- for a failed write: the denial, conflict, or uncertain and temporary paths;
- the planned checks and each check's record;
- the review material mapping;
- the review-input failure, or the complete typed `ReviewResult`: request,
  reviewer attribution and model execution, decision, findings, risks and
  unknowns;
- the fixed limitation statements.

It holds no exceptions, environment, host paths or runtime objects.

## Known limitations

- **A pass is not proof of correctness.** Neither a sandboxed `PASSED` nor a
  review `ACCEPT` proves the change is correct. The review is an unverified
  model opinion over the supplied text.
- **The reviewer shares the Coding Agent's model binding and principal.**
  Independence is by Agent definition only.
- **No rework, retry or rollback.** `CHANGES_REQUIRED` leaves the applied
  changes in place for the operator.
- **No checked-input identity.** The evidence records the configured check
  requests, not the exact files copied into the sandbox.
- **Git state is operator-only** and is never disclosed to either model.
- **Review bounds are the M8.2 bounds.** Larger changes cannot be reviewed and
  are reported, never truncated.
- **One run per workspace.** Same-workspace concurrency is refused in-process
  only.
- **The CLI's editable allowlist is the task targets**, because the local CLI
  user is also the operator.
- **Synchronous steps block** their thread.
- **Volatile, single-shot runs.** No durable run store, no resume and no
  commits.
- **Qualification uses replay models only.** `ollama` is configurable but
  unqualified, and live-model proposal and review quality is unqualified.

## Running

```powershell
cd examples/forgeai
uv sync --locked
uv run python demo.py            # fixture task, replay models, real Docker checks
uv run forgeai <repo> --objective "..." --target src/pkg/mod.py --target tests/test_mod.py --replay coding.json --replay review.json
```

`demo.py` is a test harness. It copies `fixtures/stock_task/repository` into a
temporary directory, commits it, and replays two recorded outputs in call
order: `proposal.json` (the Coding Agent) and `review_accept.json` (the
reviewer). The fixture also includes `review_changes_required.json` and
`review_insufficient.json`.

## Validation

From the repository root, on Windows with Docker Desktop and the CR-2a image
present:

```powershell
uv run python .\validate_forgeai_2.py
```

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
