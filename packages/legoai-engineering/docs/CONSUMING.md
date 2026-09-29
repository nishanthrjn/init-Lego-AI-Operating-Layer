# Consuming LegoAI Engineering

This guide is for developers building an application on `legoai-engineering`,
for example a governed coding assistant or a validation service. It describes
the supported public surface only. Anything not listed in §4 is internal and
may change without notice.

## 1. Purpose

LegoAI Engineering provides bounded, governed engineering capabilities behind
stable Ports:

- reading a repository workspace;
- proposing code changes with a model;
- applying changes;
- running known checks, either on the host or in a sandbox;
- observing Git state.

Each effect sits behind a Port. The application depends on the Port, and the
composition root chooses the adapter. Effects that change state or execute
repository code (writes and checks) can be wrapped so that current
authorization is checked immediately before each one.

## 2. Real-world use cases

- A coding assistant that proposes a change, applies it after authorization
  and runs checks on the result.
- A validation service that runs pytest, Ruff or mypy on agent-written or
  third-party code, isolated in a sandbox.
- A repository analyst that answers questions about selected files without
  being able to write.
- An operator console that shows Git status alongside a proposed change.

## 3. Non-use cases

- Running arbitrary commands, shells or installers. There is no argv surface.
- Multi-file transactions or rollback. M4 reports partial effects honestly
  instead.
- Proving that code is correct. A sandboxed `PASSED` is a contained
  observation, not integrity evidence.
- Multi-tenant or remote hosting, durable audit, IAM or approval workflows.
- Git writes (commit, push or checkout). Git access is read-only.

## 4. Supported public imports

The table lists the whole supported surface. Modules or names beginning with
`_` are internal. So is everything in `legoai.reference.*` and
`legoai.runtime._composition.*`.

| Module | Supported names | Extra |
| --- | --- | --- |
| `legoai_engineering.repository.workspace` | `RepositoryPath`, `WorkspacePolicy`, `WorkspaceEntry`, `WorkspaceEntryKind` | base |
| `legoai_engineering.repository.ports` | `RepositoryWorkspacePort` | base |
| `legoai_engineering.repository.local` | `LocalWorkspaceRoot`, `LocalRepositoryWorkspace` | base |
| `legoai_engineering.repository.errors` | `WorkspaceError`, `WorkspaceFailure` | base |
| `legoai_engineering.repository.mutation` | `RepositoryChangeSet`, `FileChange`, `FileChangeKind`, `RepositoryMutationResult`, `digest_text` | base |
| `legoai_engineering.repository.mutation_ports` | `RepositoryMutationPort` | base |
| `legoai_engineering.repository.mutation_local` | `LocalRepositoryMutation` | base |
| `legoai_engineering.repository.mutation_errors` | `MutationConflict`, `MutationConflictReason`, `MutationApplyError` | base |
| `legoai_engineering.repository.mutation_authorized` | `AuthorizedRepositoryMutation`, `REPOSITORY_MUTATION_ACTION` | `analyst` |
| `legoai_engineering.checks.values` | `CheckKind`, `CheckRequest`, `CheckResult`, `CheckOutcome`, `CheckPolicy` | base |
| `legoai_engineering.checks.ports` | `EngineeringCheckPort` | base |
| `legoai_engineering.checks.errors` | `CheckError`, `CheckFailure` | base |
| `legoai_engineering.checks.local` | `LocalEngineeringChecks`, `LocalCheckTools` | base |
| `legoai_engineering.checks.sandboxed` | `SandboxedEngineeringChecks`, `CheckInputPolicy` | base |
| `legoai_engineering.checks.authorized` | `AuthorizedEngineeringChecks`, `ENGINEERING_CHECK_ACTION` | `analyst` |
| `legoai_engineering.sandbox.ports` / `.values` / `.errors` / `.docker` | `SandboxExecutionPort`, `CancellationSignal`, `SandboxPolicy`, `SandboxRequest`, `SandboxResult`, `SandboxError`, `SandboxFailure`, `DockerSandbox`, `DockerSandboxConfig`, `SandboxImage` | base |
| `legoai_engineering.git.ports` / `.local` / `.values` / `.errors` | `GitRepositoryPort`, `LocalGitRepository`, `LocalGitExecutable`, `GitReadPolicy`, Git values, `GitError`, `GitFailure` | base |
| `legoai_engineering.analyst.authorized` | `AuthorizedRepositoryEvidence`, `REPOSITORY_READ_ACTION` | `analyst` |
| `legoai_engineering.analyst.api` / `.values` | `RepositoryAnalyst`, `RepositoryEvidencePort`, analysis values | `analyst` |
| `legoai_engineering.coding.authorized` | `AuthorizedCodingEvidence` | `analyst` |
| `legoai_engineering.coding.api` / `.values` | `CodingAgent`, `CodingRequest`, `CodingTarget`, `CodingResult`, `CodingProposal` | `analyst` |
| `legoai_engineering.reviewer.api` / `.values` | Independent Reviewer | `analyst` |
| `legoai_engineering.authorization` | `EffectAuthorizationError`, `EffectAuthorizationFailure` | base |

The governed host comes from Core: `legoai.runtime.api` supplies the
configuration types and `GovernedHost`, and `legoai.runtime.local` supplies
`open_local_host`, which only the composition root calls. The `analyst` extra
installs Core (`legoai-reference`). The base install has no runtime
dependencies.

## 5. Application-facing contract

Application code depends only on these Ports and their values:

| Port | Call | Result | Errors |
| --- | --- | --- | --- |
| `RepositoryWorkspacePort` | `list_entries(dir)`, `read_text(path)` | entries, `RepositoryText` | `WorkspaceError` |
| `RepositoryMutationPort` | `apply(RepositoryChangeSet)` | `RepositoryMutationResult` | `MutationConflict`, `MutationApplyError`, `EffectAuthorizationError` when wrapped |
| `EngineeringCheckPort` | `check(CheckRequest)` | `CheckResult` | `CheckError`, `WorkspaceError`, `EffectAuthorizationError` when wrapped |
| `GitRepositoryPort` | `inspect()` | Git state | `GitError` |
| `CodingAgent` | `await propose(CodingRequest)` | `CodingResult` | failures are statuses in the result |

Failing tests, lint findings and type errors are `CheckResult` outcomes, not
errors.

## 6. Configuration surface

All of these are typed, validated values supplied by the operator:

| Value | Controls | Bounds |
| --- | --- | --- |
| `WorkspacePolicy` | Read limits, depth and excluded names | Validated on construction |
| `LocalHostConfig` + `OperatorGrant` | Principal, tenant and application scope, policy, grants, model bindings | 1–64 grants, 1–16 bindings |
| `CheckPolicy` | Check timeout and output capture | Timeout and output ceilings |
| `CheckInputPolicy` | Which files are copied into the sandbox | 1–16 roots, 0–16 files, scan ≤ 65,536 entries |
| `SandboxPolicy` + `SandboxImage` | Sandbox timeout and output; image from the closed qualified set | ≤ 300 s, ≤ 1 MiB |
| `GitReadPolicy` | Git read limits | Validated on construction |

## 7. Runtime inputs vs operator configuration

Requests carry only data: paths, check kinds, change sets and questions. They
never carry commands, URLs, keys, images, grants, actions or scopes. The
authority for every effect comes from operator grants in `LocalHostConfig`. A
request cannot widen a workspace, an allowlist, an action or a scope.

**What configuration can choose:**
- workspace root and policy;
- grant declarations;
- the model binding (selection data);
- `CheckPolicy` and `CheckInputPolicy`;
- the sandbox image, from the closed qualified set.

**What still needs code:**
- wiring concrete adapters in the composition root (there is no config
  loader or DI container);
- implementing an unsupported provider or adapter;
- all application workflow and domain behavior.

Not every application can be assembled from configuration alone.

## 8. Supported adapters

| Port | Adapter | Notes |
| --- | --- | --- |
| `RepositoryWorkspacePort` | `LocalRepositoryWorkspace` | Local filesystem, read-only |
| `RepositoryMutationPort` | `LocalRepositoryMutation` | Digest preconditions; wrap with `AuthorizedRepositoryMutation` |
| `EngineeringCheckPort` | `LocalEngineeringChecks` | **Trusted code only**: runs on the host as the host user |
| `EngineeringCheckPort` | `SandboxedEngineeringChecks` | Untrusted or model-written code: one confined container per check, no host fallback |
| `EngineeringCheckPort` | `AuthorizedEngineeringChecks` | Decorator over either check adapter |
| `SandboxExecutionPort` | `DockerSandbox` | Docker Desktop Linux engine; closed image set |
| `GitRepositoryPort` | `LocalGitRepository` | Read-only `status` and `ls-files` |

## 9. Extension path

To support a new technology, implement the existing Port in your own package,
for example a different sandbox backend behind `SandboxExecutionPort`. Keep
its result and error semantics, and test it against the same consumer tests.
Do not subclass or patch internal modules. A new capability that is not
specific to your application belongs in LegoAI; see the readiness plan.

## 10. Adapter replacement path

Replacing an adapter changes only the composition root. Application code that
depends on `EngineeringCheckPort` behaves the same whether it is given
`LocalEngineeringChecks`, `SandboxedEngineeringChecks` or either one wrapped in
`AuthorizedEngineeringChecks`. The tests `test_authorized_effects.py` and
`test_checks_sandboxed_docker.py` prove this.

## 11. Security and governance boundary

- **Authorization per effect.** Reads (`read-for-model-analysis`), writes
  (`apply-repository-changes`) and checks (`run-engineering-check`) each need
  their own operator grant on the same workspace. The wrapper evaluates
  current authority immediately before every effect and never caches an
  allow. On denial the inner adapter is never called. Approval-bearing
  contexts are refused. See the [ADR-018](../../../adrs/ADR-018.md) addendum.
- **Contexts come from the host.** Obtain a `SecurityContext` from
  `host.security_context(workspace_reference, action, scope)`. Never construct
  a `Grant` or `SecurityContext` in application code.
- **What authorization does not give you.** It is not isolation (choose the
  sandboxed adapter for that), not result integrity, and not protection
  against hostile Python running in the host process.
- **Model output is data.** The Coding Agent proposes changes only. Applying
  them is a separately authorized step.

## 12. Effect and failure semantics

| Situation | Effect | Error |
| --- | --- | --- |
| Authorization denied | None; the inner adapter is not called | `EffectAuthorizationError(DENIED)` |
| Authorization dependency failed | None | `EffectAuthorizationError(UNAVAILABLE)` |
| M4 validation or precondition failure (stale, exists, missing) | None | `MutationConflict` |
| M4 final I/O failure | Partial; confirmed and uncertain paths are reported | `MutationApplyError`; inspect before retrying |
| Check ran and found problems | Code under test ran | Result with `FAILED` or `INTERRUPTED` |
| Check infrastructure fault (timeout, limit, unavailable, cancelled) | Code may have run | `CheckError(reason)` |

No component retries. The sandboxed adapter never falls back to the host.

## 13. Concurrency and resource behavior

- **Calls are synchronous.** Mutation and check calls block; the Coding
  Agent is async.
- **Local host confinement.** The local host is confined to the thread that
  opened it and to the event loop of its first async use.
- **Execution capacity.** Host executions are bounded by `max_executions`.
- **Sandboxed checks:**
  - one container per check, with 1 CPU, 128 MiB of memory and 32 PIDs;
  - cancellation is bound to each adapter instance;
  - memory exhaustion reports `RESOURCE_LIMIT`.
- **Stable workspace assumed.** No workspace locking is provided. The M4
  digest preconditions detect concurrent edits between proposal and apply.

## 14. Examples

This composition uses public imports only. `open_local_host` is called only in
the composition root, and `config` is your operator `LocalHostConfig`.

```python
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

from legoai.runtime.api import ModelPurpose
from legoai.runtime.local import open_local_host

from legoai_engineering.analyst.authorized import (
    REPOSITORY_READ_ACTION,
    AuthorizedRepositoryEvidence,
)
from legoai_engineering.checks.authorized import (
    ENGINEERING_CHECK_ACTION,
    AuthorizedEngineeringChecks,
)
from legoai_engineering.checks.local import LocalCheckTools, LocalEngineeringChecks
from legoai_engineering.checks.sandboxed import (
    CheckInputPolicy,
    SandboxedEngineeringChecks,
)
from legoai_engineering.checks.values import CheckPolicy
from legoai_engineering.coding.api import CodingAgent
from legoai_engineering.coding.authorized import AuthorizedCodingEvidence
from legoai_engineering.repository.local import (
    LocalRepositoryWorkspace,
    LocalWorkspaceRoot,
)
from legoai_engineering.repository.mutation_authorized import (
    REPOSITORY_MUTATION_ACTION,
    AuthorizedRepositoryMutation,
)
from legoai_engineering.repository.mutation_local import LocalRepositoryMutation
from legoai_engineering.repository.workspace import RepositoryPath, WorkspacePolicy
from legoai_engineering.sandbox.docker import (
    DockerSandbox,
    DockerSandboxConfig,
    SandboxImage,
)
from legoai_engineering.sandbox.values import SandboxPolicy


def clock() -> datetime:
    return datetime.now(UTC)


def compose(config, selection, root: Path, tools: Path, docker: Path, trusted: bool):
    host = open_local_host(config, selection)
    # The workspace reference and scope must match the operator's grants.
    workspace_ref = replace(config.configuration.configuration, instance="workspace")
    policy = WorkspacePolicy(262_144, 65_536, 4096, 32, (".git", ".venv"))
    workspace = LocalRepositoryWorkspace(LocalWorkspaceRoot(root), policy)

    def context(action: str):
        return host.security_context(workspace_ref, action, workspace_ref.instance)

    reads = AuthorizedRepositoryEvidence(
        workspace_ref,
        workspace,
        context(REPOSITORY_READ_ACTION),
        host.authorization,
        (RepositoryPath("src/app.py"),),
        clock,
    )
    agent = CodingAgent(AuthorizedCodingEvidence(reads), host.agent_runtime())
    mutation = AuthorizedRepositoryMutation(
        workspace_ref,
        LocalRepositoryMutation(LocalWorkspaceRoot(root), policy),
        context(REPOSITORY_MUTATION_ACTION),
        host.authorization,
        clock,
    )
    if trusted:
        # Trusted local code only: runs on the host as the host user.
        inner = LocalEngineeringChecks(
            LocalWorkspaceRoot(root),
            # Absolute paths to operator-installed executables.
            LocalCheckTools(tools / "pytest.exe", tools / "ruff.exe", tools / "mypy.exe"),
            CheckPolicy(),
        )
    else:
        # Repository or model-written code: contained, never a host fallback.
        inner = SandboxedEngineeringChecks(
            workspace,
            DockerSandbox(
                DockerSandboxConfig(docker, SandboxImage.PYTHON_CHECKS),
                SandboxPolicy(timeout_seconds=180, max_output_bytes=1_048_576),
            ),
            CheckInputPolicy((RepositoryPath("src"), RepositoryPath("tests"))),
            CheckPolicy(timeout_seconds=120),
        )
    checks = AuthorizedEngineeringChecks(
        workspace_ref, inner, context(ENGINEERING_CHECK_ACTION), host.authorization, clock
    )
    return agent, mutation, checks, host.model_execution(ModelPurpose.CHAT)
```

The application flow then depends only on the Ports:

1. Call `agent.propose(CodingRequest(..., context))`.
2. Pass the proposal's change set to `mutation.apply(...)`.
3. Call `checks.check(CheckRequest(...))`.

A sandboxed `PASSED` means only that the tool reported success under
containment. Code under test can influence its own tool run, so a pass does
not prove the change is correct.

Runnable offline examples:

- `examples/governed_engineering.py`: the full governed path, with a fake
  model and a deterministic check stand-in;
- `examples/bounded_coding.py`: the Coding Agent proposing a change;
- `examples/repository_analyst.py`: repository analysis;
- `examples/governed_demo.py`: host configuration.

## 15. Validation and tests

- **Fakes to copy:** the tests use in-process fakes that implement the
  Ports: spy authorization, fake mutation, fake checks, fake workspace and
  fake sandbox. Copy them for your own tests.
- **Governance negatives to keep:** denied, expired, revoked, unavailable,
  approval-bearing, wrong-workspace and wrong-tenant contexts.
- **Consumer architecture test:** consumers should also keep a test that their
  modules import no `_`-prefixed module or name; see
  `test_governed_consumers_use_no_private_modules_or_names`.
- **Validation commands:** run from the repository root on Windows with Docker
  Desktop.

```powershell
uv run python .\validate_consumer_readiness_cr3.py
uv run python .\validate_consumer_readiness_cr2b.py
```

## 16. Qualification scope

| Capability | Status | Evidence |
| --- | --- | --- |
| M1–M6 (workspace, Git, mutation, checks, sandbox) | Locally qualified | Engineering README |
| M8.1–M8.3 (analyst, reviewer, coding agent) | Locally qualified | Engineering README |
| CR-1b public governed host | Locally qualified | ADR-014 §12a |
| CR-2a/2b sandboxed checks | Docker-qualified: Windows with Docker Desktop | Engineering README, CR-2b |
| CR-3 authorized wrappers and this guide | Locally qualified (2026-09-29) | Engineering README, CR-3 |

"Locally qualified" means it passed on the maintainer's reference machine. It
is not a production or multi-platform claim.

## 17. Known limitations

- **No input identity in check results.** `CheckResult` does not record which
  files were checked. Applications that need that evidence must compose it
  themselves.
- **One workspace per wrapper.** Each wrapper is bound to one workspace, one
  principal and one tenant, because the Ports carry no tenant. Composing a
  context with the right tenant is the operator's job.
- **Wrapper and adapter must match.** The operator must bind the wrapper's
  workspace reference to the same workspace as its inner adapter; the wrapper
  cannot verify that.
- **Approvals are unsupported.** Contexts carrying an approval are refused.
- **Git is operator-only.** Git data is for operator display. There is no
  authorized Git wrapper for disclosing it to a model.
- **Process-lifetime state.** The local host is in-memory, and its grants,
  revocations and capacity last only for the process.
- **Sandbox scope.** The sandbox profile is qualified for small Python
  projects on Windows with Docker Desktop only.
- **Core required for governed wrappers.** The governed wrappers need the
  `analyst` extra, which installs Core.

## 18. Compatibility and version expectations

`legoai-engineering` is at `0.1.0.dev0` and requires Python 3.14. The Ports
and the public names in §4 change only with a documented, additive change
where possible. Internal modules may change at any time. Engineering and Core
releases are pinned together: the `analyst` extra requires the matching
`legoai-reference` version.
