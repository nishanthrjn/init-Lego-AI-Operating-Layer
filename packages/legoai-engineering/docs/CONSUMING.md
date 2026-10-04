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
| `legoai_engineering.repository.structure` | `RepositoryStructurePolicy`, `RepositoryStructure`, `StructureError`, `StructureFailure` | base |
| `legoai_engineering.repository.structure_authorized` | `AuthorizedRepositoryStructure`, `REPOSITORY_STRUCTURE_ACTION` | `analyst` |
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

## DISCOVERY-1 — bounded authorized structure acquisition

Implemented; **operator local qualification pending**. This is deterministic
acquisition, not target discovery/selection. No Agent, model, ForgeAI, content-read,
Git, mutation or sandbox dependency is introduced. Base structure values require
no Core; the authorized facade uses the existing `analyst` extra for governance.

Use RepositoryStructurePolicy as trusted operator configuration. Roots are 1–8
explicit relative directories, unique, non-overlapping, without case aliases;
no None/whole-repository default or file roots. Hard ceilings (lower values allowed):

| Bound | Ceiling / meaning |
| --- | --- |
| Depth | 6 components from workspace root; FILE at limit allowed; admitted DIRECTORY at limit fails, including empty directories. Roots must be shallower. |
| Entries | 512 including roots; no truncation or partial release. |
| Listing calls | 64/pass, exactly two successful equal passes; at most 128/acquisition. |
| Serialized map | 16,384 strict UTF-8 bytes including fixed version/coverage envelope. |
| Paths | RepositoryPath ≤240 code points; ≤960 UTF-8 bytes; components ≤128 code points; no normalization. Controls/format characters and invalid Unicode refused. |
| Extra exclusions | ≤32 component names and ≤32 relative subtrees, case-insensitive; additive only. |

Every dot-prefixed component is excluded, plus case-insensitive `secrets`,
`credentials`, `private`, `node_modules`, `build`, `dist`, `generated`, `vendor`,
`__pycache__`. Excluded directories are not traversed. `.gitignore` is not read;
this does not guarantee all Git-ignored files are excluded. Benign-looking names
such as `customer-acme-contract.py` may remain visible: this is not a secret
classifier. Future operator preview and destination-specific authorization remain
necessary before model disclosure.

The composition root supplies a bound RepositoryWorkspacePort and workspace
ConfigurationRef. Configure LocalRepositoryWorkspace with WorkspacePolicy.max_entries
≤512, depth sufficient for the structure policy, and exclusions that are a subset
of the structure policy. An empty adapter exclusion tuple is supported; structure
filtering then happens after adapter safety validation. Never bind an adapter with
undeclared extra exclusions and call the map complete under a different policy.
The Port cannot inspect these settings: this is an explicit trusted-composition
obligation. Raw scan work is at most 128 x 512 entries under that adapter profile;
excluded entries count in its per-directory bound. The facade independently refuses
returned tuples over 512 and validates every direct child before filtering/traversal.

Public composition sketch (host, workspace, reference and clock are trusted
operator-owned dependencies; the host already has an explicit OperatorGrant):

```python
from legoai_engineering.repository.structure import RepositoryStructurePolicy
from legoai_engineering.repository.structure_authorized import (
    AuthorizedRepositoryStructure, REPOSITORY_STRUCTURE_ACTION,
)
from legoai_engineering.repository.workspace import RepositoryPath

policy = RepositoryStructurePolicy((RepositoryPath("src"), RepositoryPath("tests")))
context = host.security_context(workspace_reference, REPOSITORY_STRUCTURE_ACTION,
                                workspace_reference.instance)
reader = AuthorizedRepositoryStructure(workspace_reference, workspace, context,
                                      host.authorization, policy, clock)
structure = reader.acquire(context.tenant_context)
```

The fixed action is `read-structure-for-model-analysis`, not named-file content
authority. Synchronous acquire checks current authority with fresh time before
each listing and final release. Wrong tenant/scope/action and approval-bearing
contexts fail closed. Unavailable authority never becomes ALLOWED. No cached allow,
partial release or retry; earlier authorized local I/O cannot be undone.

RepositoryStructure reuses immutable WorkspaceEntry values. Traversal is bounded
and deterministic; final entries are globally sorted. Two complete filtered maps
must match or STRUCTURE_CHANGED is raised. No atomic snapshot, TOCTOU elimination,
hostile namespace defense or hard synchronous I/O deadline is claimed. Existing
LocalRepositoryWorkspace link/reparse/hardlink/containment/device/change checks stay
unchanged; safety failure takes precedence over convenient filtering.

`model_bytes()` explicitly serializes approved relative paths/kinds and fixed
version/coverage text; it neither calls a model nor authorizes later disclosure.
`identity_bytes()` additionally encodes sorted roots, filter profile/configuration
and limits. `digest()` is SHA-256 of these versioned canonical bytes: not authority,
anonymity, file-content integrity or snapshot identity. Digest is absent from the
model envelope. Paths/filter/entry fields and bound dependencies are repr-excluded.
Do not log explicit serialization without separate permission.

StructureError.reason distinguishes CONFIGURATION_INVALID, AUTHORIZATION_DENIED,
AUTHORITY_UNAVAILABLE, WORKSPACE_UNAVAILABLE, BOUNDARY_VIOLATION,
STRUCTURE_LIMIT_EXCEEDED, UNSUPPORTED_ENTRY and STRUCTURE_CHANGED. The facade
translates WorkspaceError and retains its cause for trusted diagnostics. Top-level
messages/reprs contain no paths; raw traceback causes may contain confidential
paths. Invalid dependency contracts can still raise programming errors, as with
existing authorization wrappers; they never produce an allowed result.

Run from repository root:

```powershell
uv run python .\validate_engineering_discovery_1.py
```

The validator checks scope, structure/security/failure tests, repository and Agent
regressions, replay ForgeAI/LQ1 tests, isolated wheel public consumption, mypy and
Ruff. No live model or Docker is required. Docker tests are excluded because no
execution/check/sandbox/runtime dependency changed; this does not requalify those
unchanged adapters. Full operator qualification is pending. Target selection and
operator confirmation remain unimplemented.
