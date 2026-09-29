# Python-first reusable AI platform — forward implementation plan

Date: 2026-09-22. Authority: intent 1.0 + IA-001; canonical SPEC, Architecture,
Contracts, Security, Evaluation, Conformance, Plugin Spec; accepted ADRs
including ADR-016. This replaces forward sequencing, not v0.1 history.
M1 implementation and local validation are complete. The first local run passed
tests, typing, lint and the example; the returned formatter recheck passed after
the two formatting-only corrections recorded below. The milestone is closed.
M2's bounded local acquisition subset is now implemented under the maintainer's
separate M2 instruction; local validation is complete for its documented trusted
local Windows scope (see M2 closure below). M3 is complete based on the maintainer's
reported local evidence. M4 implementation and local validation are complete
for the documented trusted local scope. M5 implementation and local validation
are complete for the documented trusted-local Windows scope. M6 engineering
workload isolation implementation and local qualification are complete for the
documented Windows Docker Desktop Linux scope. See
[M6 implementation and scope](ENGINEERING-M6-IMPLEMENTATION.md) and the
[qualification handoff](../packages/legoai-engineering/README.md#m6-engineering-workload-isolation).
M6.5 is complete for its documented scope: user-supplied evidence reports 1,425
Core tests, two DocuMind tests, clean mypy/lint/format, build/fresh install and
the routing example. M7 implementation and local qualification are complete;
see the [M7 plan](M7-AGENT-PLAN.md) and [handoff](../docs/agent.md).
M8 specialized engineering Agents remain unstarted.
See the [M6.5 design](M6.5-MODEL-ROUTING-PLAN.md) and
[validation handoff](../docs/model-routing.md#local-validation-required).
Other remaining Phase C and later work remains planned and unstarted.

## A. Corrected product direction

LegoAI is a Python-first platform for composing reusable governed AI building
blocks. Production-grade is the destination, qualified per supported scope.
Components are implemented once in Python; external ecosystems integrate
through optional adapters. No application needs every composition layer.

## B. Preserved v0.1 architecture

Retain capability-first independent use; Ports & Adapters; explicit tenant,
Principal, governance, resources, effects and evidence; Agent ≠ Role;
Team ≠ Actor; Model ≠ Agent; Memory ≠ vector DB; Retrieval ≠ RAG;
Evaluation ≠ Conformance; Evidence ≠ Observation. Preserve the qualified
local runtime, ModelPort/Ollama, Document Pack and DocuMind.
The [v0.1 record](V0.1-RELEASE-READINESS.md) remains historical qualification.

## C. Amendments

See [impact analysis](PYTHON-FIRST-IMPACT-ASSESSMENT.md),
[IA-001](../intent-amendments/IA-001.md), and [ADR-016](../adrs/ADR-016.md).
No canonical entity or operational behavior is redefined. Intent 1.0 text is
preserved, with a visible current amendment pointer. ADR-001/002 stay valid.

## D. Package strategy

| Location | Responsibility / dependency rule |
|---|---|
| `src/legoai` / `legoai-reference` | Existing owner values/Ports → reference realizations → private composition; enforce ADR-002 |
| `packages/legoai-document` | Existing document capabilities; public Core contracts only |
| `packages/legoai-engineering` | M1 pure repository text inspection; no Core dependency needed for this preparatory data transformation |
| `packages/legoai-collation` | Slice F1 pure source-linked reading normalization and single-field precedence collation; no Core dependency; see [F1 record](COLLATION-F1-SLICE.md) |
| Future Agent, Workflow, Team modules | Use ADR-002's logical owner map once actual consumers require executable subsets; no empty packages now |
| Future provider/framework/protocol distributions | Distinct import roots, public contracts only, optional third-party dependencies |
| `examples/documind` | Existing application composition, unchanged |
| Engineering pack intake example | First small deterministic consumer of M1; synthetic supplied content, no live repository authority |
| Future ForgeAI application | Consumes supported LegoAI application boundary and reusable engineering components |

Do not rename Core, move Ollama, create a mega `utils` package, change namespace
ownership, or split every owner into a distribution. New runtime dependencies
need capability, stdlib-alternative, maintenance/security and replacement analysis.

## E. Capability strategy

Start with typed bounded engineering inputs/results. M1's supplied text
inspection is pure preparation, not published `repo.inspect` support.
Later `repo.inspect/search`, Git, tests, lint, typecheck and patch operations
must declare versions, targets, authorization, failures and resource/effect
semantics before admission. Keep existing `document.parsing`, `.chunking`,
`.embedding` names; the requested future catalog is illustrative.

Live filesystem read must define path/root binding, symlink/reparse behavior,
concurrent mutation, decoding, size limits, deadline/cancellation and tenant
disclosure. Path lexical checks alone are not containment. Git must avoid
untrusted hooks/config/executables and command injection. Patch application
requires expected source revision and explicit conflict/partial-write behavior.

## F. Agent strategy

Implement the smallest subset of SPEC §4.2 Agent after engineering primitives.
Bound role, instructions, capability requirements, model policy, output contract,
steps, resource/deadline and escalation behavior. Reuse identity, context and
error contracts. ModelPort is a dependency, not an Agent implementation.
Start with repository analysis and independent review, then coding once
safe write/execution capabilities exist. A test engineer interprets deterministic
results; it does not replace pytest. No God Agent or agent class hierarchy.

## G. Skill strategy

SPEC §4.5 already defines versioned expertise assets. Retain its content,
usage, dependency and evaluation semantics. Defer Python Skill types/loading
until two uses demonstrate reusable expertise beyond capability/workflow
composition; never let scripts/instructions grant authority or install dependencies.

## H. Workflow strategy

Use explicit DAG/state-machine behavior consistent with SPEC §4.6. Workflow
owns state, ordering, bounded branching/loops/retries, timeouts, waits, approval,
quality gates, cancellation and recovery. Bind definition revisions and retain
effect knowledge. ADR-015 supervises concurrency; it is not a workflow engine.
Parallel analysis is allowed only for independent work with explicit joins,
bounded capacity and owner-supervised lifetime. No uncontrolled group chat.

## I. Team strategy

Teams compose Actors and Roles under accountable Organization/Outcome semantics.
Keep authority and membership separate. Independent reviewer and deterministic
quality gates remain distinct from coding self-review. Typed work products pass
through workflow state and canonical Artifact references where persisted; avoid
giant conversation histories and duplicate Artifact models.

## J. Interoperability and adapters

First preserve Python contracts and independently replaceable implementations.
MCP server maps admitted capabilities to external tools with authenticated tenant,
Principal, cancellation, limits, errors and disclosure boundaries. MCP client
wraps external tools as governed contributions; remote descriptions/results cannot
grant local authority. Decide mappings against the then-current primary protocol
specification when a consumer exists; no protocol schema is selected here.
A2A, HTTP/OpenAPI and events likewise require actual interoperability demand.

Additional OpenAI, Anthropic, Azure or compatible providers implement ModelPort
behind optional adapters; provider fields stay out of generic contracts unless
generalized semantics require them. Framework adapters (including Semantic Kernel,
MAF, LangGraph and OpenAI Agents SDK) map to LegoAI meanings, never the reverse.
No external SDK dependency or provider claim is added now.

## K. Dependency-ordered roadmap and stop boundaries

Every row is a separate milestone with a local validation handoff and stop.
Completion requires applicable tests plus review of actual supplied local output.
No release/version bump follows automatically from completing a row.

| Phase | Scope | Non-scope | Completion criteria / tests | Architecture check | Next dependency |
|---|---|---|---|---|---|
| A | Impact, IA-001, ADR-016, forward pointers | Rewriting v0.1 | Clause alignment and preserved historical records | No lower-level override of intent | M1 |
| B / M1 | Bounded supplied repository text values, literal inspection, intake example | Host read/write, Git, shell, registration, Agent | Contract/limit/order/failure tests, strict typing, inert imports, wheel/sdist + clean install | Pack has no application/Core-private dependency; no I/O | Local output review, then C |
| C | Governed read-only repository/filesystem/Git inspection | Writes, execution, agents | Denial prevents I/O; path escape/reparse/concurrent mutation tests; bounded output and cancellation; application integration | ADR-005–009/015; resolve ADR-014 before supported facade | D |
| D | Bounded sandbox/test/lint/typecheck and guarded patch capabilities | Unrestricted host shell/deploy | Injection, escape, timeout, cancellation, orphan/resource, partial-write, revision/conflict and structured tool-result tests | Engineering workload isolation requires an explicit threat model and locally qualified boundary before repository-controlled/generated code is treated as isolated. ADR-012 remains separately required for hostile/untrusted Plugin admission or expanded Plugin threat scope; process ≠ sandbox; no implicit retries | E |
| E | Minimal Agent foundation for identified analysis/review tasks | Universal memory/agent framework | Typed outputs, step/budget/deadline limits, denied tools, malformed model output and cancellation cases | Canonical Agent ≠ Model/Role; external enforcement | F |
| F | Repository analyst, coding and independent reviewer compositions | Full team autonomy | Representative task fixtures; deterministic validators; separate quality evaluation by authorized consumer | No framework/provider classes in definitions | G |
| G | Workflow foundation for those bounded tasks | Distributed scheduler | Branch/join/loop exhaustion, failure, approval wait/revocation, recovery/effect tests | State owned by Workflow, lifetime by accepted Execution mechanisms | H |
| H | One feature/bug-fix engineering workflow | Every workflow in target catalog | Intake → plan → patch → tests → review → bounded rework → gate; failure cannot reach success | Artifacts/state explicit, independent review preserved | I |
| I | Reusable Software Engineering Team | ForgeAI product UI | Bounded task delivered with deterministic tests/lint/typecheck/review and residual failures surfaced | Team ≠ Actor; no union of permissions | J |
| J | ForgeAI bootstrap over supported authoring boundary | Generic engineering implementation inside product | Clean-installed integration and approvals/artifact/delivery cases | ADR-014 accepted; LegoAI never imports ForgeAI | Consumer-driven K |
| K | One demanded MCP/provider/framework adapter at a time | Ecosystem checklist implementation | Mapping/compatibility, denial, interruption, error and uncertain-effect tests; then-current protocol qualification | Adapter-only SDK/protocol dependencies | New consumer assessment |

K may precede later rows when an actual consumer makes it a prerequisite;
it never bypasses security or authoring gates. G may supply a minimal
deterministic harness before F only if F's evaluation consumer requires it;
record a narrowed milestone rather than creating a second orchestration model.

## L. ForgeAI dependency path

ForgeAI → reusable Software Engineering Team → engineering Workflows →
bounded Agents → optional Skills → engineering Capabilities → governed runtime
→ provider/framework/protocol adapters. Arrows describe consumption, subject
to the canonical owner matrix. Applications may omit intermediate layers.
Generic code/repo/test/review capabilities belong in reusable packages.

## M. M1 requirements, validation and release gates

M1's contract is [engineering README](../packages/legoai-engineering/README.md).
The input is an explicitly supplied immutable tuple, never a live repository
Snapshot claim. Literal, case-sensitive search returns one first-match coordinate
per matching LF-delimited line, sorted by portable label then line; cap results
and report truncation only when another matching line exists. No regex, path
resolution, logging, model call, process or network is performed.

Hard input bounds precede inspection. Reject wrong types (including bool for
integers), duplicate path labels, malformed labels and unsupported sizes rather
than silently coercing/skipping. Output constructors preserve bounds and ordering.
No acquisition consistency, repository completeness, freshness or authorization
is inferred from the result. This deliberately small pure contract can be wrapped
by a later governed contribution without changing Core now.

Run locally from the repository root:

```powershell
Push-Location packages/legoai-engineering
uv sync
uv run pytest -q
uv run mypy src tests examples
uv run ruff check src tests examples
uv run ruff format --check src tests examples
uv run python examples/repository_intake.py
Pop-Location
git diff --check
```

The test suite includes wheel/sdist building and fresh offline wheel installation,
using the locally synced build tools. Expected: all tests pass without skips,
mypy reports no issues, Ruff checks succeed, and the example reports
`pyproject.toml:2:1`. The pack's first local `uv sync` generated its lockfile;
its dependency inventory has now been reviewed (see local validation record).
Existing baseline locks stay unchanged.
No validation has been run by the assistant. Commands and output are a release
gate, not a prediction of success. Stop on failure, classify code/test/environment/
toolchain/configuration before changing production code, and retain complete output.

Later increments additionally rerun affected baseline package suites and
clean-installed compositions. v0.1 historical results cannot qualify new runtime
or adapter behavior. Independent-use, replacement, boundary and negative-path
evidence are required for any new supported operational scope under ADR-011.

## N. Deferred items

Full engineering catalog; formal Skill implementation; persistent Agent memory;
universal agents; distributed/queue/multi-worker infrastructure; public runtime
facade before ADR-014; hostile-code claims before ADR-012; production observation
claims before ADR-013; all-provider/framework support; A2A without demand;
ForgeAI UI/delivery; deploy/email/network mutation. Local supplied-text helpers
are not an escape hatch for any of these boundaries.

## M1 static review record

Same-assistant source review on 2026-09-22 checked bounds before iteration,
exact nested immutable values, case-sensitive deterministic ordering, Unicode
coordinate meaning, cap-versus-truncation distinction, and safe exception text.
The bounded function performs no I/O and cannot interpret input as commands.
The example consumes the package without private runtime wiring. New tests
cover failure boundaries and fresh-install use; no test execution is claimed.

Review corrections: made the Core reverse-import check fail if its expected
source tree is absent instead of passing vacuously; simplified the inert-import
probe's context-manager syntax; retained the exact-cap/nontruncation regression.
The packaging test installs only the built wheel, offline, outside the source
tree. All existing runtime/document/application source and lockfiles remain
unchanged. This review is not independent assurance. At the time of this initial
static review, local validation and first lockfile review were pending; their
subsequent results are recorded below.

## M1 local validation record — first returned run

User-supplied PowerShell output on CPython 3.14.5 records:

- `uv sync`: successful, 18 packages including the local engineering project.
- `pytest -q`: 44 passed in 2.89s, including the build/clean-install test.
- `mypy src tests examples`: no issues in 8 source files.
- `ruff check src tests examples`: all checks passed.
- Intake example: `pyproject.toml:2:1`, as specified.
- `git diff --check`: no whitespace errors reported; Git emitted LF/CRLF notices.
- `ruff format --check`: failed on two formatting differences, six files already
  formatted. Classification: source/test formatting defect, not runtime behavior,
  test logic, dependency/toolchain or environment failure.

Applied exactly the two formatter-provided changes to `repository/values.py`
and `tests/test_architecture.py`. No behavior or dependency changes. The assistant
did not execute validation commands; a local formatter recheck was then required.
No next-milestone work begins on the basis of this partial validation record.

Reviewed `packages/legoai-engineering/uv.lock`: five pinned direct development/
build packages (hatchling, editables, pytest, mypy, ruff), twelve transitive
packages, all external package sources listed as PyPI; the only editable project
is this pack. There are no runtime dependencies. This is a dependency inventory
review, not a vulnerability audit. The lockfile is preserved as generated locally.

Environment messages are non-blocking: uv ignored the active root environment
and used the pack's own `.venv`; hardlink failure fell back to a successful copy
installation; Git's notices describe line-ending conversion. No production-code
change or repository-wide environment/line-ending policy change is needed.

## M1 closure — returned formatter recheck

The user ran the engineering pack's `.venv/Scripts/ruff.exe format --check
src tests examples` and supplied the result: **8 files already formatted**.
Together with the first returned run and lockfile review, this closes M1's
applicable local validation gates. Only formatting changed after that first run;
no redundant functional test/build rerun was requested or performed.

M1 is complete for bounded supplied-text inspection and its intake example.
This does not establish governed live repository access, sandbox isolation,
Agent/Workflow/Team support or general production conformance. Phase C/M2
remains unstarted; the milestone stop boundary is preserved.

## M2 implementation record — bounded repository workspace

**M1 complete. M2 implementation and local validation complete for its declared
scope. M3 not started. ENGINEERING_M2_COMPLETE = YES.**

The maintainer's M2 request narrows the next Phase C increment to read-only
local workspace acquisition, explicitly excluding Git and Agent implementation.
This record supersedes the historical M1 closure's M2-unstarted pointer only.
It does not mark all Phase C governance/Git/public-authoring work complete.

### Contract and dependency review

Reviewed intent/IA-001, SPEC identity/security/independent-use rules, logical
Architecture and Contracts, Security, ADR-002/005/007/008/016, ADR index,
the impact assessment and prior forward/batch pointers, plus M1 source/tests.
Existing M1 `RepositoryText` is the read result and `InspectionRequest`/
`inspect_text` remain the analyzer. No duplicate Snapshot, Artifact, Agent,
Skill or canonical identity was introduced.

The replaceable `RepositoryWorkspacePort` has only `list_entries` and `read_text`.
`RepositoryPath`, `WorkspacePolicy`, `WorkspaceEntry` and `WorkspaceEntryKind`
are immutable acquisition-domain values. `LocalWorkspaceRoot` is host-local
configuration and `LocalRepositoryWorkspace` its synchronous reference adapter.
`WorkspaceError` has a closed failure enum; boundary violations have a distinct
subclass. This is a concrete I/O substitution boundary for the intake consumer,
not a speculative collection of future workspace providers.

Dependency direction: workspace values reuse M1 labels; Port references values;
local adapter implements that shape; example chooses and composes the adapter.
Only the local module imports filesystem machinery. Core, providers, frameworks,
applications, Git and shell are absent from pack runtime dependencies. Existing
M1 implementation and tests remain; architecture/package tests were extended for
the actual new modules. No runtime dependency, tool version, lockfile, Core code,
canonical document or ADR changed. ADR-016's additive pack strategy is preserved.

### Supported scope and stop boundaries

Explicit absolute local root, portable relative result paths, nonrecursive
bounded directory listing, strict bounded UTF-8 reads and explicit failures.
No write, mutation, execution, network access or automatic retry. Exclusions
are a small explicit name tuple rather than a Git-ignore engine. Listing fails
on scan/depth overflow rather than returning an arbitrary partial directory.
The [engineering README](../packages/legoai-engineering/README.md) defines exact
limits, errors, example and boundary assumptions.

Reject traversal, rooted/drive/UNC/device/ADS syntax, Windows filename aliases,
symlinks and observed reparse points (including junctions), multiply-linked files,
cross-device targets and special files. Recheck root identity; compare open-file
identity before reading and recheck ordinary mutations. A stable trusted local
directory/mount namespace is a supported-scope precondition, not something
these portable checks can enforce against an attacker. Hostile concurrent path
replacement, same-device bind mounts, unqualified filesystem/filter drivers,
network filesystems and sandbox isolation are not claimed. Finite reads/scans
do not imply hard OS-call timeout/cancellation guarantees.

The Port is an acquisition adapter, not an admitted governed invocation facade.
ADR-005/007 enforcement before disclosure, tenant binding, resource/evidence
admission and ADR-014-supported authoring remain requirements for future runtime
integration. The local operator example does not substitute path possession for
that authority. No new approval-token or authorization framework is invented.

### Static review and validation handoff

Same-assistant static review inspected imports, mutable state, public types,
path validation before I/O, root revalidation, bounded stream/scan lifetime,
UTF-8/M1 compatibility, safe error messages and cause retention. Corrected a
missing test return annotation, a needless type-ignore and a Windows-only
typing hazard in the POSIX FIFO test. Added a root-replacement regression and
explicit read-only-open/static process checks. This review is not independent
assurance or runtime security proof; no tests, builds, typechecks or linters
were executed internally.

Tests now cover explicit/missing/file roots, UTF-8/CRLF/BOM/empty text, nested
paths, missing/directory targets, traversal and Windows aliases, byte/character
ceilings, decode/NUL failure, order/hidden-file/exclusion behavior, bounded scans
and depth, file/root replacement, error causality, symlink and hardlink escape,
Windows junction escape, and POSIX special files. Architecture tests include
inert imports and negative filesystem/process dependency fixtures. Packaging
tests build wheel/sdist, assert new module inventories, install offline into a
fresh environment and exercise both M1 and real M2 outside the checkout.

Run locally from repository root:

```powershell
Push-Location packages/legoai-engineering
uv sync --locked
uv run pytest -q
uv run mypy src tests examples
uv run ruff check src tests examples
uv run ruff format --check src tests examples
uv run python examples/workspace_intake.py "$((Get-Location).Path)"
Pop-Location
git diff --check
```

Expected: applicable tests pass, mypy no issues, Ruff lint/format clean,
example prints `pyproject.toml:9:1`. Build/install checks are included in pytest.
Windows skips the POSIX FIFO case; other platforms skip Windows junctions.
Missing Windows symlink privilege may produce an explicit skip, which leaves
symlink qualification pending until a permitted local run succeeds. Review the
complete output and every skip before claiming M2 complete. Do not start M3.

### M2 first returned local validation

User-supplied Windows output records successful locked sync, **86 passed and
2 skipped in 2.25s**, including successful Windows junction and package/build/
clean-install cases. The example printed `pyproject.toml:9:1`; `git diff --check`
reported no issues. No internal validation was executed.

Failure classification and corrections:

- **TEST DEFECT:** mypy correctly rejected the deliberately invalid list passed
  to `dataclasses.replace` in the tuple-validation negative test. Added a scoped
  `# type: ignore[arg-type]`, preserving the runtime rejection assertion. The
  earlier static-review removal of that ignore was incorrect for this toolchain.
- **TEST/EXAMPLE STYLE DEFECT:** applied the two reported Ruff UP012 corrections
  (literal UTF-8 encode defaults) and two exact formatting changes. No production
  adapter or domain behavior changed.
- **ENVIRONMENT LIMITATION:** Windows lacked symlink-creation privilege; the
  symlink escape test skipped. This remains a release-blocking evidence gap
  pending a local run with symlink permission, not grounds to weaken the test.
- **EXPECTED PLATFORM SKIP:** POSIX FIFO test is inapplicable on Windows.
- **NON-BLOCKING ENVIRONMENT WARNING:** uv ignored the active root environment
  and used the package environment as intended. No configuration change required.

Remaining validation: mypy, Ruff lint/format, and the single symlink escape test
in a permitted local session. The functional suite/build/example need not be
repeated for these behavior-preserving test/style corrections. M2 remains pending;
M3 remains unstarted and `ENGINEERING_M2_COMPLETE = NO`.

### M2 second returned local validation

The user reports mypy clean over 14 source files, Ruff lint clean, and
14 files already formatted. Those corrected checks are closed. The targeted
symlink escape test again skipped in 0.08s because Windows symlink-creation
privilege was unavailable. Classification remains ENVIRONMENT LIMITATION;
no production or test change is warranted. The boundary assertion did not run.

Only that targeted test remains: run in a Windows session permitted to create
symlinks (Developer Mode, the assigned privilege, or an administrator process,
per Python's os.symlink documentation). Require a passing result, not a skip.
No full-suite, package, example, typing or lint rerun is needed at this point.
M2 remains validation-pending; M3 remains unstarted.

### M2 closure — returned symlink escape result

The user supplied a subsequent targeted Windows run:
`test_symlink_file_directory_and_root_escape`: **1 passed in 0.05s**.
This closes the symlink-creation privilege evidence gap without weakening the
test or modifying production behavior. Earlier skipped attempts remain historical
environment findings; they are not security passes.

Combined evidence consists of the initial **86 passed, 2 skipped** full suite
(including Windows junction, architecture and wheel/sdist/clean installation),
the corrected mypy result (14 files, no issues), Ruff lint and format results
(14 files formatted), correct example output `pyproject.toml:9:1`, the initial
clean whitespace check, and this separately passing symlink case. There was no
combined full-suite rerun. POSIX FIFO remains an expected platform exclusion;
no non-Windows qualification is claimed. M1 regression cases were included in
the initial passing suite. No internal test execution occurred.

Files created by M2: `repository/errors.py`, `repository/workspace.py`,
`repository/ports.py`, `repository/local.py` under the engineering source tree;
`examples/workspace_intake.py`; `tests/test_workspace.py`.
Files modified: root and engineering READMEs, this forward plan, engineering
`tests/test_architecture.py` and `tests/test_package_install.py`. Subsequent fixes
affected only the new test/example and validation records. Existing M1 production
source, Core, canonical documents, ADRs, package metadata and lockfile are unchanged.

M2 is complete for synchronous, bounded, read-only acquisition in a trusted,
stable local filesystem namespace. Root-relative containment is not a hostile
mutation sandbox, and the adapter is not a governed invocation facade. All README
limits and residual risks remain. New runtime dependencies: zero. ADR-016's
capability-first additive package strategy is preserved.

`ENGINEERING_M2_COMPLETE = YES`. Next work is a separately scoped M3 decision
within the remaining Phase C work (governed integration/Git inspection, respecting
ADR-014 before supported authoring); none is authorized or implemented by this
closure. Stop here.

## M3 implementation handoff — local validation pending

The maintainer separately authorized deterministic read-only Git observation.
Current status: **M1 complete; M2 complete; M3 implementation complete — local
validation pending; M4 unstarted. ENGINEERING_M3_COMPLETE = NO.** Earlier M1/M2
records above retain the scope and evidence at their respective closure dates.

Added an independent `legoai_engineering.git` semantic layer: immutable HEAD,
commit identity, index/worktree status values and a one-method GitRepositoryPort.
LocalGitRepository binds an explicit M2 root plus trusted Git executable and
finite policy. It admits a deliberately narrow ordinary local repository/config
subset, checks the index with fixed `ls-files`, then reads porcelain-v2 status.
Shell execution, arbitrary command arguments, Git mutation, network, diffs,
rename detection and conflict modelling are absent. Unsupported states fail
explicitly. The unchanged M2 checks enforce the trusted stable namespace scope;
this is not hostile-mutation isolation or an admitted governed runtime facade.

Implementation files added: `git/__init__.py`, `git/values.py`, `git/ports.py`,
`git/errors.py`, `git/local.py`, `git/_config.py`, `git/_parse.py`,
`git/_process.py`; `examples/git_intake.py`; `tests/test_git.py` in the engineering
pack. Updated its architecture/inert-import and wheel/sdist/offline-install tests,
both READMEs and this forward plan. M1/M2 production modules, Core, Document Pack,
DocuMind, canonical specifications/ADRs, package metadata and lockfile are unchanged.
No new runtime dependency or foundational architectural decision was introduced.

Static review covers strict immutable contracts, dependency direction, fixed
read commands, noninteractive environment isolation, config/helper admission,
path/layout restrictions, dual bounded nonblocking pipe capture, child cleanup,
timeout/error behavior, package inventory and local test coverage. Applicable
verification is deferred to the maintainer as explicitly required. No test,
build, install, lint, formatter or typecheck was executed internally.

Use the complete PowerShell command sequence and expected results in the
[M3 qualification instructions](../packages/legoai-engineering/README.md#m3-local-qualification).
Pytest includes actual temporary Git repositories and artifact build/fresh offline
installation. Review every failure, warning and skip before qualification; classify
code, test, environment, toolchain/dependency or configuration defects first.
No packaging/typing/test success is claimed now. Stop for local evidence; do not
start mutation, process-execution, sandbox or Agent work. M4 remains unstarted.

## M3 closure and M4 implementation handoff

The maintainer's separate M4 instruction supplies M3 local qualification:
129 passed, one expected Windows skip, clean mypy/Ruff, 24 files formatted,
wheel/sdist/fresh-install validation passed, example passed, and clean
`git diff --check`. This is user-reported evidence for the documented scope;
`ENGINEERING_M3_COMPLETE = YES`. Earlier handoff entries remain historical.

Current state: **M1 complete; M2 complete; M3 complete; M4 complete for its
documented scope; M5 unstarted. ENGINEERING_M4_COMPLETE = YES.**

M4 adds immutable CREATE/UPDATE/DELETE changesets, exact UTF-8 SHA-256 content
preconditions, a separate mutation Port and one inertly constructed local adapter.
The adapter reuses M2 containment/read mechanisms and WorkspacePolicy. All
preconditions are checked before temporary preparation and again before apply.
Changes preserve request order. Single-file publication uses same-directory
prepared files; partial final-I/O failure reports confirmed changes, an uncertain
target and unconfirmed cleanup paths. No multi-file/crash transaction, automatic
retry, Git command, generic write helper or authorization grant is claimed.

Design boundaries follow ADR-016's additive capability direction and preserve
ADR-005/007/008 future governance/effect obligations. Git administration, gitfile
layouts and recognizable bare/custom metadata ancestors fail closed. Trusted
stable local namespace remains the qualification; hostile mutation, sandboxing,
metadata/ACL preservation and concealed malformed Git layouts are unsupported.
Ordinary file mode preservation is private replacement behavior, not a chmod API.

Created under the engineering pack: `repository/mutation.py`,
`repository/mutation_ports.py`, `repository/mutation_errors.py`,
`repository/mutation_local.py`, `tests/test_mutation.py`,
`examples/mutation_intake.py`. Updated architecture/inert-import and package-install
tests, pack/root READMEs and this plan. M1–M3 production, Core, Document Pack,
DocuMind, canonical documents/ADRs, package metadata and lockfile remain unchanged.
Runtime dependencies added: zero. No new foundational decision or ADR was needed.

Static review addressed typed request/result invariants, protected paths,
precondition ordering, private M2 reuse, cleanup failures, exact encoding,
partial/uncertain effects, package inventory and test coverage. Tests cover
temporary-workspace CRUD, stale/no-write cases, UTF-8/limits, path/link protection,
partial application and cleanup, and unstaged M3 integration against temporary
Git fixtures. Pytest retains wheel/sdist/fresh offline installation coverage.

No test/build/install/lint/format/typecheck was run internally, as required by
the maintainer. Use the exact commands and targeted Windows symlink rerun in
the [M4 documentation](../packages/legoai-engineering/README.md#m4--bounded-repository-text-mutation).
Expected example: `update: greeting.txt` followed by `hello LegoAI`. Review every
warning/skip and classify failures before corrections. Stop for local evidence;
M5, Git mutation, execution/sandbox and Agent work remain unstarted.

M4 maintainer validation returned 174 passed and one expected Windows skip for
the POSIX special-file boundary. Mypy (30 source files), Ruff lint, and the
mutation example passed. The sole formatter defect in `test_architecture.py`
was corrected using Ruff's suggested layout. The maintainer's recheck passed:
30 files already formatted; `git diff --check` reported conversion warnings only,
with no whitespace errors. Packaging and M1–M3 regression checks are included in
the passing suite. Windows symlink and junction checks passed; the sole skip
was the POSIX special-file boundary. No validation commands were run internally.
`ENGINEERING_M4_COMPLETE = YES` for the documented trusted, stable local namespace
scope; M5 remains unstarted.

## M5 implementation handoff — known engineering checks

Current state: **M1–M5 complete for their documented scopes;
M6 unstarted. ENGINEERING_M5_COMPLETE = YES.** Earlier entries retain
their historical milestone states.

The maintainer's M5 instruction explicitly permits design A: separate reusable
engineering semantics and a bounded local adapter, with governed runtime
composition later. Selected under ADR-002/016, preserving Core's ownership of
admission, authority, dispatch, supervision, effects and evidence. Core's current
capability-specific private invocation wiring is not a supported authoring API;
ADR-014 remains open. No Core imports, duplicate runtime or new ADR is introduced.

New `checks` modules: inert initializer, `values`, `errors`, `ports`, `local`,
private `_process`. Public `EngineeringCheckPort.check` accepts only an immutable
`CheckRequest` for pytest, Ruff check, Ruff format-check or mypy and 1–32 explicit
repository targets. `LocalCheckTools` provides trusted host executable paths;
`CheckPolicy` supplies finite time/output limits. `CheckResult` preserves exact
exit and byte diagnostics with semantic outcomes. Missing tools and operational
faults are distinct from completed checks with findings. No dependency added,
no package/lockfile change, no public arbitrary command/argv/environment API.

M2's public parent-listing API validates targets before any process launch;
M1–M4 production code stays unchanged. Limits: 60s/256KiB per stream by default,
at most 3600s/1MiB per stream. Private dual-pipe nonblocking capture, DEVNULL stdin,
shell=False, finite direct-child cleanup and explicit overflow failures. No
reader threads, output spool files, retry, installation or network setup. Tool
flags disable fixes/common caches; filtered environment avoids inherited tool
overrides and Python search paths. Trusted project configuration still applies.

**This is not safe execution of untrusted repository code.** Pytest/conftest and
mypy plugins can execute Python and access the host. Target admission is not
recursive filesystem confinement; configuration/dependency discovery can leave
the workspace. Descendants may survive timeout, OS launch/I/O can delay deadline
handling, and failures do not imply no effects. M6/ADR-012 remains the isolation
boundary. Governed Agent use requires future higher-layer composition.

Added real-tool, output/timeout, path/argv, Windows link, M4/M3 coexistence tests,
extended architecture/inertness and package-install checks, plus a temporary
project example. Static review addressed exact exit mapping, no-fix overrides,
Windows byte preservation, bounded capture and cleanup. This is same-assistant
review, not independent review or executed verification.

The [M5 local qualification commands](../packages/legoai-engineering/README.md#m5--known-engineering-checks)
are retained for reproduction. Pytest includes real installed tools and wheel/sdist plus
fresh offline installation without tool libraries. Expected example output:
`ruff_check: passed`. No locally runnable validation was performed internally.
Local evidence is recorded below; M6 and later milestones remain unstarted.

M5 local evidence returned on 2026-09-23: **215 passed, 1 expected Windows skip**
for the POSIX special-file boundary; mypy clean across 38 files; Ruff lint clean;
example output correct. The passing pytest suite includes packaging, real-tool
integration and M1–M4 regressions. Tools: pytest 9.1.1, Ruff 0.16.8, mypy 2.3.1,
Git 2.54.0.windows.1. The format check identified a source formatting defect in
`checks/local.py` and test formatting defects in `tests/test_checks.py`.
Applied the reported formatting changes only. The maintainer's final recheck
passed: **38 files already formatted**. Git's LF-to-CRLF notices are conversion
warnings, with no whitespace errors reported. The sole pytest skip was unrelated
to M5; Windows symlink and junction checks passed. Qualification is limited to
the documented trusted-local Windows scope; no POSIX or sandbox claim follows.
`ENGINEERING_M5_COMPLETE = YES`; M6 remains unstarted.

## M6.5 implementation handoff

M1–M6 retain their documented qualification. M6.5 implements exact Chat profile
selection through ModelRequirement, ModelBinding, ModelRouteStatus,
ModelRouteDecision, ModelRouterPort and DeterministicModelRouter. Configuration
revision and selected binding remain pinned; private composition checks their
correspondence and reuses the existing governed Chat claim/effect path.

No new dependency, distribution, provider, configuration store or canonical/ADR
change. Ollama, DocuMind, Document Pack and engineering source are unchanged.
Shared Chat composition changes require the documented DocuMind regression.
ADR-012 remains Proposed and M6 qualification is unchanged.

Focused routing, architecture, governance/replay/effect, installed-wheel and
offline-example tests are authored. Same-assistant static review is the only
internal verification; no tests, mypy, Ruff, builds, installs or examples ran.
Follow the [local commands](../docs/model-routing.md#local-validation-required).
**IMPLEMENTATION COMPLETE — LOCAL VALIDATION PENDING.**
`MODEL_ROUTING_M6_5_COMPLETE = YES` based on the returned local evidence above.

## M7 implementation handoff

The one-step execution-owner Agent consumes M6.5 and existing governed Chat.
It bounds inputs and accepted UTF-8 output, retaining downstream effects even
when Agent output validation fails. Shared Model code and M6 production code
are unchanged; the M6 PID test workload was corrected without weakening limits.
No tools, memory, Workflow, Team, retry, fallback or framework dependency.
Provider generation/token limits, bounded transport, provider max-token translation
and cost/resource budgeting remain future Model/runtime optimization work.

Same-assistant static review only; no local validation executed internally.
Maintainer evidence: 53 focused M7 tests, 100 routing/Model regressions and
1,478 Core tests passed; mypy, lint, formatting, build/install, example and
whitespace checks passed. The corrected targeted M6 test passed (3.33s), closing
the separate environment/test-defect observation. See docs/agent.md for details.
`AGENT_M7_COMPLETE = YES`. M8 remains unstarted; stop at this qualification gate.

## M8.1 implementation handoff

M1–M7 remain complete for their qualified scopes. M8.1 Repository Analyst is
**IMPLEMENTATION COMPLETE — LOCAL VALIDATION PENDING**. The specialization is
in the existing Engineering package with an optional Core dependency, preserving
Core ownership and unchanged Model/M7 contracts. See
[ADR-018](../adrs/ADR-018.md), the [scoped plan](M8.1-REPOSITORY-ANALYST-PLAN.md)
and [contract/local commands](../packages/legoai-engineering/README.md#m81--repository-analyst).

Explicit authorized M2 reads produce sorted bounded M1 RepositoryText evidence.
One existing M7 invocation uses M6.5 routing and governed Chat. A small closed
JSON validator bounds analysis and validates structured citation membership;
narrative remains unverified. No tools, mutation, execution, Git, memory, retry,
fallback, Workflow or Team. No new third-party runtime dependency.

Only source review was performed internally. Engineering lock regeneration,
tests, typing, lint/format, package installation and the offline example await
local execution. `REPOSITORY_ANALYST_M8_1_COMPLETE = NO` pending that evidence.
M8.2 Reviewer Agent, M8.3 Coding Agent and M8.4 Test/Validation Agent are unstarted.

## M8.1 closure and M8.2 handoff

M8.1 is locally qualified: 153 Core dependency regressions, 284 Engineering tests,
mypy (55 files), Ruff, wheel/sdist/fresh install, example and diff check passed.
The remaining Analyst/M2 symlink gap closed with **2 passed in 0.16s**.
`REPOSITORY_ANALYST_M8_1_COMPLETE = YES`; see the
[completion report](M8.1-REPOSITORY-ANALYST-PLAN.md#completion-report).
Earlier handoff sections preserve chronology, not current status.

M8.2 Independent Reviewer is **IMPLEMENTATION COMPLETE — LOCAL VALIDATION PENDING**.
It consumes bounded supplied proposals and material through M7/M6.5/governed Chat,
enforces producer/reviewer definition separation, and validates structured review
opinions and evidence-member references. Review does not grant authorization.
No repository acquisition, mutation, checks, sandbox, memory, retry, fallback,
Workflow or Team. ADR-018 reviewed as a reusable ownership/disclosure decision;
its Proposed canonical status is unchanged. No new dependency or Core production
change. M8.1 production contracts remain unchanged; examples share demo wiring.

See the [M8.2 plan](M8.2-INDEPENDENT-REVIEWER-PLAN.md),
[contract](../packages/legoai-engineering/README.md#m82--independent-reviewer), and
[local script](../INDEPENDENT_REVIEWER_M8_2_test.ps1). Same-assistant static review
only, no runnable validation internally. `INDEPENDENT_REVIEWER_M8_2_COMPLETE = NO`.
M8.3 Coding Agent and M8.4 Test/Validation Agent remain unstarted.

## M8.2 local qualification closure

Maintainer output: 153 Core regressions passed; 333 non-Docker Engineering tests
passed with five existing filesystem skips; mypy passed for 62 files; Ruff lint
and formatting passed; packaging/fresh install and both offline examples passed.
Final diff check showed only line-ending notices. The Analyst/M2 symlink boundary
was already proven by the earlier two-test elevated run; M8.2 does not change it
or introduce filesystem access. No new elevated run or Docker qualification is needed.
See the [full completion report](M8.2-INDEPENDENT-REVIEWER-PLAN.md#completion-report)
for skip classifications, exact scope and limitations.

`INDEPENDENT_REVIEWER_M8_2_COMPLETE = YES`. M1–M8.2 retain their documented
qualified scopes. M8.3 Coding Agent and M8.4 Test/Validation Agent remain unstarted.

## M8.3 implementation handoff

M1–M8.2 remain qualified. M8.3 is **IMPLEMENTATION COMPLETE — LOCAL VALIDATION
PENDING**. `legoai_engineering.coding` proposes bounded CREATE/UPDATE M4 changesets
after authorized M2 evidence and one governed M7 invocation. Digests are computed
from acquired exact text; Model-provided digests, paths outside scope and DELETE
are rejected. No apply, tests, sandbox, Git, Reviewer orchestration, retry, fallback,
memory, Workflow or Team. M8.4 remains unstarted.

ADR-018's existing ownership/disclosure decision applies; no new ADR, canonical
change, runtime dependency or Core modification. Tests cover denied acquisition,
CREATE absence/parent checks, UPDATE digests, limits/invalid output, no writes,
M4 stale-precondition handoff and dependency boundaries. Static review only internally.
See [plan](M8.3-BOUNDED-CODING-PLAN.md),
[contract](../packages/legoai-engineering/README.md#m83--bounded-coding-agent), and
[local script](../CODING_AGENT_M8_3_test.ps1).
`CODING_AGENT_M8_3_COMPLETE = NO` pending local qualification.

**Closure (2026-09-29):** the maintainer's symlink-capable run of the M8.3 script
passed. The Engineering suite had 408 passed and 1 POSIX-only skip. All six
Windows symlink boundary tests ran and passed. Typing and Ruff were clean, and
the three examples printed their expected output. Core regressions had 153
passed. See the [completion report](M8.3-BOUNDED-CODING-PLAN.md#completion-report).
`CODING_AGENT_M8_3_COMPLETE = YES`. M8.4 remains unstarted.
