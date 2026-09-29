# ForgeAI-1: single repository task worker

ForgeAI is an application built on LegoAI. ForgeAI-1 runs **one bounded coding
task** against **one clean local Git repository**:

1. one model proposal;
2. authorized application of that proposal;
3. contained verification;
4. an evidence-backed result.

It is assembled almost entirely from public LegoAI components. ForgeAI adds
only the task vocabulary, the run sequence and the operator profile.

**Status:** locally qualified on 2026-09-29 for the Windows + Docker Desktop
scope with the offline replay model; see "Qualification evidence".

## Workflow

`RepositoryTaskWorker.run(task, context)` performs these steps, in this order,
once per run. Nothing is hidden, and nothing is retried.

1. **Claim the workspace.** The in-process `WorkspaceGuard` refuses a second
   concurrent run on the same repository.
2. **Observe Git** through `GitRepositoryPort`. The repository must have a
   commit and no changes, not even untracked files. Otherwise the run is
   rejected. ForgeAI never stashes, resets, cleans or commits.
3. **Propose.** `CodingAgent.propose` is called **exactly once**. It performs
   the authorized, bounded reads of the target files, then one governed model
   call, and returns a validated M4 change set. The model proposes; it never
   applies.
4. **Apply** through `AuthorizedRepositoryMutation`, which wraps
   `LocalRepositoryMutation`. Authority is checked immediately before the
   write, and the digest preconditions are enforced.
5. **Check.** The configured checks run in order (Ruff check, mypy, pytest)
   through `AuthorizedEngineeringChecks` over `SandboxedEngineeringChecks` on
   `SandboxImage.PYTHON_CHECKS`. There is no host check adapter and no
   fallback.
6. **Observe Git again.** HEAD must be unchanged, and the working-tree changes
   must be exactly the applied paths.
7. **Return a `TaskResult`** built from this run's evidence.

## Reused LegoAI components

| Concern | Component |
| --- | --- |
| Host, authorization and model routing | `legoai.runtime.local.open_local_host`, `legoai.runtime.api` (`LocalHostConfig`, `OperatorGrant`, `ModelBindingConfig`, `OllamaSettings`, `TrustedModelContribution`), `GovernedHost.agent_runtime`, `model_execution` |
| Authorized reads and proposal | `AuthorizedRepositoryEvidence`, `AuthorizedCodingEvidence`, `CodingAgent` (unchanged) |
| Workspace and mutation | `LocalRepositoryWorkspace`, `LocalRepositoryMutation`, `AuthorizedRepositoryMutation` |
| Checks and sandbox | `AuthorizedEngineeringChecks`, `SandboxedEngineeringChecks`, `CheckInputPolicy`, `DockerSandbox`, `SandboxImage.PYTHON_CHECKS` |
| Git observation | `LocalGitRepository` / `GitRepositoryPort` (read-only) |
| Values and errors | `CheckRequest`, `CheckResult`, `CodingTarget`, `RepositoryMutationResult`, `MutationConflict`, `MutationApplyError`, `CheckError`, `EffectAuthorizationError`, `GitRepositoryState` |

No LegoAI code was changed or copied for ForgeAI-1.

## ForgeAI-owned code (`src/forgeai`)

| Module | Layer | Contents |
| --- | --- | --- |
| `domain.py` | Domain | `TaskRequest`, `TaskDisposition`, `TaskFailure`, `CheckRecord`, `TaskEvidence`, `TaskResult` |
| `worker.py` | Application | `RepositoryTaskWorker`, which depends on Ports and the Coding Agent only |
| `guard.py` | Application | `WorkspaceGuard`, an in-process same-workspace refusal |
| `composition.py` | Composition root | `ForgeAIConfig`, `local_profile`, `prepare_run`, `run_task`; the only module that opens the host or names adapters |
| `cli.py` | Presentation | the `forgeai` command, the bounded `summarize`, and the `replay` and `ollama` bindings |

## Configuration boundary

`TaskRequest` holds **intent only**:
- `objective`;
- 1–8 `CodingTarget`s (path plus create or update);
- up to 8 constraints.

It never carries a repository root, model, provider, URL, key, grant,
executable, image or command.

Operator configuration is `ForgeAIConfig`, built by `local_profile` or by your
own composition root. It covers:

- the repository root and `WorkspacePolicy`, and the editable-path allowlist;
- the Git executable and `GitReadPolicy`;
- host principal, tenant, policy and grants for exactly four actions:
  - `invoke-capability` for Chat;
  - `read-for-model-analysis`;
  - `apply-repository-changes`;
  - `run-engineering-check`;
- model bindings and the selection `{"revision", "binding"}`;
- the Docker executable, the `SandboxPolicy` and the closed `SandboxImage`;
- `CheckInputPolicy`, `CheckPolicy` and the ordered check plan.

**Switching providers is configuration-only.** Changing the selected binding
(for example `replay` to `ollama`) changes no ForgeAI code. The tests prove
this. A provider LegoAI does not support still needs a new adapter, written in
code.

## Supported scope

- **Tasks:** update or create 1–8 files of at most 8 KiB each (24 KiB in
  total), solvable by one proposal. Deleting files is not supported.
- **Repositories:** a local, non-bare Git repository with a commit, in the
  `src/` + `tests/` + `pyproject.toml` Python layout that the default profile
  checks. It must be small enough for the qualified sandbox: at most 63 input
  files and about 1 MiB, with the fixed 128 MiB / 1 CPU profile.
- **Platform:** Windows with the Docker Desktop Linux engine (the CR-2b
  qualified scope).

## Security and authorization

- **Separate grants per effect.** Reading, invoking the model, writing and
  running checks each need their own operator grant. Each is evaluated
  immediately before its effect.
- **Denial stops before the effect.** A denied read or model call stops
  before the model provider is called. A denied write stops before any write,
  and a denied check before any sandbox call.
- **The model only proposes.** Its output is data. Model-written code runs
  only in the sandbox, which has no network and no host filesystem access.
- **Git is operator-only.** Git state is used for gating and evidence only and
  is **never disclosed to the model**; there is no authorized Git boundary for
  that.
- **Contexts come from the host.** ForgeAI never constructs a `Grant`,
  `SecurityContext` or `Approval`.

## Dispositions and failures

| Disposition | Meaning | `TaskFailure` reasons |
| --- | --- | --- |
| `SUCCEEDED` | Changes applied, every configured check `PASSED`, HEAD unchanged, working-tree changes exactly equal the applied paths | — |
| `REJECTED` | Refused before any model call or repository effect | `WORKSPACE_BUSY`, `REPOSITORY_UNAVAILABLE`, `UNSUPPORTED_REPOSITORY`, `DIRTY_START`, `EVIDENCE_DENIED`, `EVIDENCE_UNAVAILABLE` |
| `FAILED` | Work started but did not succeed | `MODEL_FAILED`, `PROPOSAL_INVALID`, `MUTATION_DENIED`, `MUTATION_CONFLICT`, `MUTATION_PARTIAL`, `CHECK_DENIED`, `CHECK_ERROR`, `CHECKS_FAILED`, `FINAL_STATE_UNAVAILABLE`, `HEAD_CHANGED`, `UNEXPECTED_CHANGES` |

**Tool findings versus infrastructure failures.** Tool findings (a pytest
failure, a Ruff finding, a mypy error) are `CheckResult`s, so the run reports
`CHECKS_FAILED`, and every configured check still runs. Infrastructure
failures are reported as `CHECK_ERROR` with the `CheckFailure` reason, and
the remaining checks do not run. Those failures are: timeout, cancellation,
resource or input limit, sandbox unavailable, and confinement.

**After a failure.** Applied changes stay applied. There is no rollback,
reset, retry or recovery. After any failure that follows a write, the final
Git state is still observed (read-only) and recorded.

## Evidence

`TaskEvidence` is bounded and composed only from existing LegoAI values:

- the run id (`ExecutionId`);
- the starting and final `GitRepositoryState`, or the `GitFailure` if one
  could not be observed;
- the Coding status, acquisition failure, Agent status and model effect
  extent;
- the `CodingProposal`;
- the applied `RepositoryMutationResult`;
- for a failed write: the denial, the conflict reason and path, or the
  uncertain and temporary paths;
- the planned `CheckRequest`s and, per check, its `CheckResult` or failure
  reason;
- the fixed limitation statements.

It holds no exceptions, environment, host paths or runtime objects. Check
output is bounded by `CheckPolicy`.

## Known limitations

- **A pass is not proof of correctness.** A sandboxed `PASSED` is an observed
  contained outcome, and code under test can influence its own tool run.
- **No checked-input identity.** The evidence records the configured check
  requests, not the exact files copied into the sandbox, because `CheckResult`
  does not expose them.
- **One run, one workspace.** Same-workspace concurrency is refused in-process
  only; two processes must never share a repository. Different workspaces may
  run concurrently, each with its own host and adapters.
- **The CLI's editable allowlist is the task targets**, because the local CLI
  user is also the operator. A service would configure the allowlist
  separately.
- **Synchronous steps block.** Git, mutation and check steps block their
  event loop thread; run concurrent tasks on separate threads or processes.
- **Volatile, single-shot runs.** No durable run store, no resume, no
  rework or review loop, no commits, and no live-model qualification.
  `ollama` is configurable but unqualified.

## Running

```powershell
cd examples/forgeai
uv sync --locked
uv run python demo.py            # fixture task, replay model, real Docker checks
uv run forgeai <repo> --objective "..." --target src/pkg/mod.py --target tests/test_mod.py --replay output.json
```

`demo.py` is a test harness. It copies `fixtures/stock_task/repository` into a
temporary directory, commits it, and runs the recorded proposal in
`fixtures/stock_task/proposal.json`: add input validation to
`inventory.stock.reserve` and extend its tests.

## Validation

From the repository root, on Windows with Docker Desktop and the CR-2a image
present:

```powershell
uv run python .\validate_forgeai_1.py
```

## Qualification evidence

On 2026-09-29 the maintainer ran `validate_forgeai_1.py` on Windows with
Docker Desktop, using the recorded CR-2a image. **All 20 phases passed.**

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

This qualifies the application composition, governance, mutation, sandboxed
check and evidence flow **with a deterministic replay model**. It makes no
claim about live-model proposal quality; the Ollama binding is configurable
but unqualified. All the limitations listed above still apply.
