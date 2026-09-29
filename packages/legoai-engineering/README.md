# LegoAI engineering foundation

M1: bounded deterministic inspection of caller-supplied repository text.
M1 implementation and local validation complete: 44 tests, typing, lint,
formatting and the example passed. M1 does not publish a governed `repo.inspect`
capability or acquire live repository data.

M2 adds a bounded local workspace adapter below. Its implementation and local
validation are complete for the documented supported scope. M1 remains closed
and its code is unchanged. M3 is complete based on the maintainer's local evidence.
M4 implementation and local validation are complete for the documented supported
scope. M5 implementation and local validation are complete for the documented
trusted-local scope. M6 is locally qualified for the bounded Windows Docker Desktop
Linux workload scope documented below. M6.5 and M7 are locally qualified in Core.
M8.1 and M8.2 are locally qualified for their documented scopes;
M8.3 is locally qualified for its documented scope (2026-09-29); M8.4 is unstarted.
Earlier milestone handoff notes below retain their chronology.

The [repository intake example](examples/repository_intake.py) is its first
consumer. It searches explicitly supplied project metadata and produces match
coordinates. Future repository analysis can compose this function behind a
governed acquisition/invocation boundary. No Agent, Model or framework is needed.

## M1 supported contract

Import `inspect_text` from `legoai_engineering.repository.api` and its immutable
values from `legoai_engineering.repository.values`. Initializers are inert;
no Core dependency or runtime dependency is necessary for this pure subset.

| Value / behavior | Contract |
|---|---|
| `RepositoryText(path, text)` | Supplied label and content, never a filesystem reference or a verified Snapshot |
| Path label | 1–240 Unicode code points, slash-delimited relative nonempty components; reject `.`/`..`, backslash, colon, ASCII controls and DEL; labels are case-sensitive and never normalized |
| Text | Exact built-in str, at most 65,536 code points; empty text is valid |
| `InspectionRequest(files, query, max_matches)` | Exact immutable tuple of at most 128 exact RepositoryText values, unique labels, total at most 1,048,576 code points |
| Query | Exact str of 1–256 code points without CR/LF; literal and case-sensitive; no regex/glob interpretation |
| Result cap | Exact int 1–1,000; bool and coercion are rejected |
| Line semantics | Split on LF only; CR in CRLF is retained, other Unicode separators remain content; line/column are one-based Unicode code-point positions |
| Match semantics | Return first occurrence on each matching line, sorted by path label (Unicode lexical order) then line; no repeated matches for the same line |
| `InspectionResult` | Immutable bounded unique ordered coordinates; `truncated=True` only if at least one additional matching line exists, not merely when the cap is reached |
| Empty / no match | Empty tuple and `truncated=False` |
| Validation | TypeError for incorrect runtime types; ValueError for unsupported values/combinations; errors do not echo supplied content |

All inputs are required. Constructors validate before inspection. Frozen/slotted
values and tuples prevent ordinary post-construction mutation; Python process
memory is not a security boundary. The function is synchronous and bounded by
the input/result limits. It performs no I/O, has no retries, and creates no
worker, timeout or cancellation abstraction for pure bounded computation.

Path checks provide a consistent input label grammar only. They do not validate
Windows/POSIX filenames, prevent symlink/race attacks, establish repository root
confinement, verify source revision or freshness, or authorize disclosure.
`A.py` and `a.py` are distinct labels. Text and labels remain untrusted data.
Results refer only to supplied content: they are not a complete repository
inventory, semantic code review, canonical Artifact/Evidence or security verdict.
Repr suppresses paths/content as a convenience, not a data-access control.

M1 includes no host file access, Git, shell, sandbox, test runner, patching, persistence,
provider invocation, Plugin registration or public runtime facade.
Later live operations must pass the governed runtime's current authorization,
resource, evidence and dispatch boundaries. Installing or calling a pure helper
does not itself establish an admitted operational capability.

## Local validation

From this directory:

```powershell
uv sync
uv run pytest -q
uv run mypy src tests examples
uv run ruff check src tests examples
uv run ruff format --check src tests examples
uv run python examples/repository_intake.py
```

Expected example output: `pyproject.toml:2:1`. Tests derive from the contract:
matching/order/truncation, bounds/type errors/immutability, no implicit I/O,
dependency direction and consumer integration. The package test builds wheel
and sdist, checks the wheel inventory/typing marker/dependencies, installs the
wheel offline into a new venv, and exercises the API outside the checkout with
isolated Python. M1/M2 need no network, Ollama or system Git. M3's expanded
suite requires installed Git; see its qualification section below.

Build tools are pinned to the repository's existing versions. The first local
`uv sync` generated this pack's lockfile; dependency inventory review found five
direct development/build dependencies, twelve transitive dependencies, and no
runtime dependencies. No internal install execution was performed. See the
[forward plan](../../planning/PYTHON-FIRST-REUSABLE-AI-PLATFORM-PLAN.md)
for milestone gates and stop conditions.

## M2 — bounded repository workspace

`repository.ports.RepositoryWorkspacePort` defines two synchronous methods:
`list_entries(directory: RepositoryPath | None)` and
`read_text(path: RepositoryPath)`. Explicit `None` lists the configured root;
there is no ambient working-directory fallback. The interface returns immutable
`WorkspaceEntry` tuples and M1 `RepositoryText`, respectively. A consumer can
substitute a fixture or another bounded acquisition implementation without
importing the local adapter. Remote async/deadline semantics are not promised
by this synchronous Port.

`repository.workspace` owns `RepositoryPath`, `WorkspacePolicy`,
`WorkspaceEntry` and `WorkspaceEntryKind` (FILE/DIRECTORY).
`repository.local` owns immutable `LocalWorkspaceRoot(Path)` host configuration
and `LocalRepositoryWorkspace(root, policy)`. The root is a native absolute
Path validated and canonicalized at construction, then bound to its filesystem
identity. It is not a new canonical Repository identity, tenant binding or Grant.
Results never include host absolute paths; the adapter exposes no raw Path API.

### Read and traversal contract

| Concern | M2 behavior |
|---|---|
| Domain path | Reuses M1's 1–240 character relative slash-delimited grammar; no normalization or backslash conversion; case/text preserved |
| Additional access restrictions | Reject Windows reserved device names (including numbered aliases), colon/ADS, wildcard characters, trailing dot/space components, absolute/drive/UNC/device paths and traversal before I/O |
| Local root | Absolute native local path; no parent traversal, link/reparse ancestor or UNC/device namespace; stable local filesystem required |
| Listing | One directory only, never recursive; Unicode lexical ordering of full relative paths; FILE/DIRECTORY entries |
| Scan bound | Required `max_entries`, 1–4096; counts every encountered entry including excluded names; one extra entry may be observed to detect overflow; fail without returning a partial list |
| Depth bound | Required `max_depth`, 1–32 relative components, also enforced on returned entries; listing a directory whose children exceed depth fails |
| Read bytes | Required `max_read_bytes`, 1–262144; precheck file size and bounded read of at most limit + 1 bytes to detect growth/overflow |
| Text characters | Required `max_text_chars`, 1–65536 Unicode code points, compatible with M1's ceiling |
| Encoding | Strict UTF-8; CRLF/newlines and UTF-8 BOM preserved; no replacement decoding or normalization |
| Binary rule | NUL byte is rejected; invalid UTF-8 is rejected separately. This is a narrow text policy, not MIME detection |
| Exclusions | Explicit immutable tuple of up to 32 single-component names; case-insensitive exact match at any path depth, applied to list and read; no Git-ignore/globs |
| Hidden files | Allowed unless explicitly excluded; the example excludes only `.git`, `.venv`, `__pycache__`, `build`, `dist` |
| Links and special files | Reject symlinks, observed Windows reparse points (including junctions), files with multiple hardlinks, cross-device targets and nonregular file reads |
| Missing/type/I/O failure | Explicit error; no silent skip, substitution or partial successful listing |
| Lifetime | Streams/scans close on success and failure. No retries, background workers, global discovery or import-time I/O |

Listing does not imply text readability: oversized, invalid UTF-8 or NUL-bearing
regular files may be listed but cannot be returned as text. Exclusions are a
caller-configured selection policy, not a secret detector or authorization rule.
An empty tuple excludes nothing. Hidden `.env` content is not automatically safe
to disclose; the caller must enforce its disclosure policy.

### Supported security boundary and limitations

Within an explicitly configured **trusted local workspace with a stable directory
and mount namespace during each call**, targets remain under the canonical root.
Each operation checks root identity, examines every ancestor using non-following
stat, rejects links/reparse points, and checks resolved containment with pathlib
path semantics rather than string prefixes. Reads compare opened-file identity
before reading and recheck identity/size/modification observations afterwards.
Listings recheck directory identity/modification observations. Detected changes
fail with CHANGED; there is no atomic repository snapshot guarantee.

On Windows, `lstat` supports name-surrogate reparse points including symlinks
and junctions; this adapter rejects the observed reparse attribute rather than
allowing selected tags. Other reparse behavior is OS-dependent. The supported
deployment excludes cloud placeholder/filter-driver redirection and unqualified
filesystems. See Python's [stat and reparse-point behavior](https://docs.python.org/3.14/library/os.html#os.stat)
and [Windows stat attributes](https://docs.python.org/3.14/library/os.html#os.stat_result.st_file_attributes).

These portable checks are **not race-proof against a hostile process replacing
directories, roots, links or mounts concurrently**. Hardlink-count and device
checks are defensive; they do not prove where content originated or detect all
same-device bind mounts. The trusted host must provision and control the workspace
and its ancestors. Do not expose this adapter to an adversarial mutable checkout
under a stronger isolation claim. OS sandboxing, permissions virtualization,
malware protection, container isolation and hostile Plugin containment remain
outside M2. No supported boundary is claimed for UNC/network filesystems or
filesystems without meaningful file identities.

The adapter performs no writes/mutations or subprocess/Git/network/Model calls.
OS-managed access-time updates can still occur on reads. Individual synchronous
OS calls may block; finite byte/entry limits are not wall-clock deadlines, and no
hard cancellation guarantee exists. Only local regular-file storage with acceptable
host I/O behavior belongs in this scope. Runtime supervision/resource/deadline
integration remains a separate qualification.

### Governance and failures

This is a reference acquisition adapter, **not an admitted governed capability
or supported Agent-facing runtime facade**. ADR-005/007 controls still belong at
the trusted runtime boundary before acquisition/disclosure; possession of a Port
or root object grants no authority. Do not hand a future Agent direct construction
authority. The application must bind an approved workspace, Principal/tenant,
current authorization, resource/evidence obligations and governed invocation.
M2 does not create fake context or self-approved callback tokens to claim those
guarantees. ADR-014/public authoring and the broader Phase C governed integration
remain open. No canonical document or ADR is amended for this adapter.

`repository.errors.WorkspaceError.reason` is a closed `WorkspaceFailure` enum:
MISSING, NOT_DIRECTORY, NOT_FILE, EXCLUDED, LIMIT, DECODE, BINARY, CHANGED, IO or
BOUNDARY. `WorkspaceBoundaryError` distinctly identifies invalid target syntax,
forbidden links and containment violations. Incorrect Python types raise TypeError;
invalid policy bounds raise ValueError. Top-level messages omit target content
and absolute paths. Chained OS/decoding causes preserve useful diagnosis but may
contain sensitive paths/bytes: raw tracebacks belong only in trusted diagnostics.
No read is retried and errors do not assert canonical execution/effect status.

### Example and local validation

The new `examples/workspace_intake.py` accepts an explicit absolute root,
lists it, selects `pyproject.toml`, reads through RepositoryWorkspacePort,
and passes the resulting RepositoryText to unchanged M1 inspection. Example
construction is an explicit local operator demonstration, not an authorization
implementation. Existing M1 tests and example remain regression coverage.

From the repository root:

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

Expected example output for this package's current metadata: `pyproject.toml:9:1`.
Pytest includes updated wheel/sdist inventories and fresh offline wheel installation
with real M2 list/read use outside the checkout. Architecture tests keep filesystem
imports confined to the adapter, reject process/write calls, retain pure M1 import
restrictions, and include all new modules in the inert-import probe. New runtime
dependencies: **zero**; package/tool versions and lockfile are unchanged.

The Windows junction test must pass on Windows; the POSIX FIFO test is explicitly
skipped there. The symlink test may skip only for missing Windows symlink privilege;
if it does, symlink qualification remains pending until a permitted local run
supplies evidence (for example with Developer Mode enabled). Skips do not prove
security behavior. Return all test output, including skip reasons. M2 is not
complete until applicable local evidence has been reviewed; M3 remains unstarted.

### M2 local validation closure

User-supplied Windows results: initial suite **86 passed, 2 skipped**, including
Windows junction, architecture and wheel/sdist/clean-install checks; example
`pyproject.toml:9:1`; no whitespace issues from `git diff --check`. After
behavior-preserving test/example corrections, mypy passed over 14 source files,
Ruff lint passed and Ruff reported 14 files already formatted. The previously
privilege-blocked symlink escape test subsequently **passed in 0.05s** in a
separate Windows session. The remaining initial skip is the POSIX-only FIFO
case, inapplicable to this Windows qualification. These are separate local runs,
not a claimed combined full-suite rerun. No internal validation was executed.

`ENGINEERING_M2_COMPLETE = YES` for the scope documented above. Broader runtime
governance, hostile concurrent mutation containment and non-Windows qualification
are not established by these results. M3 remains unstarted.

## M3 — deterministic Git read capability

**Implementation complete — local validation pending.** No M3 test, build,
typecheck, lint, formatter or integration command has been run internally.
M1 and M2 remain complete; M4 is unstarted. `ENGINEERING_M3_COMPLETE = NO`
until the maintainer's local evidence qualifies this scope.

`git.ports.GitRepositoryPort.inspect()` returns one immutable
`git.values.GitRepositoryState(head, entries)`. This narrow Port lets consumers
request a semantic observation without knowing subprocess arguments or importing
the local implementation. It does not mirror the Git command catalogue.

| Value | Meaning |
|---|---|
| `GitHeadKind` | ATTACHED, DETACHED or UNBORN |
| `GitHead(kind, branch, commit)` | Branch is absent only when detached; commit is absent only when unborn. Branch is bounded textual data, never an instruction |
| `GitCommitId(value)` | Opaque nonzero lowercase hexadecimal string of 1–128 characters; no SHA-1-only length assumption or promise to identify the hashing algorithm |
| `GitChange` | UNCHANGED, MODIFIED, ADDED, DELETED, TYPE_CHANGED |
| `GitStatusEntry(path, index, worktree, untracked)` | Reuses M2 RepositoryPath; index and worktree changes remain separate. Untracked entries have unchanged columns and `untracked=True` |
| `GitRepositoryState` | Exact GitHead plus unique Unicode-lexically sorted tuple of at most 4096 status entries; empty tuple means no reported changes under this Git configuration |

Public values are frozen/slotted with exact runtime type checks. A successful
result is complete for the supported operation; bounds never silently truncate.
Unchanged tracked files are absent from status. Ignored files are not untracked
results. Rename detection is disabled, so a staged rename appears as deletion
and addition. Diffs, a public tracked-file inventory, commit metadata/history,
conflict modelling and all mutation operations are deferred.

### Local composition and execution

`git.local.LocalGitRepository(root, executable, policy)` takes M2
`LocalWorkspaceRoot`, immutable `LocalGitExecutable(absolute_native_path)`, and
immutable `GitReadPolicy(timeout_seconds, max_output_bytes, max_status_entries,
max_scan_entries)`. Imports and construction perform no repository I/O, executable
discovery or process launch. Each explicit inspect call binds an M2 workspace.
The application selects a trusted installed native Git executable; Windows
batch/command scripts are rejected. The example discovers Git at composition
time using `shutil.which`, never within capability semantics.

Use a maintained Git installation supporting `--no-lazy-fetch`, porcelain v2
and SHA-256 repositories. Unsupported executable/options produce COMMAND failure;
there is no unsafe fallback. Python remains CPython 3.14 as specified by the pack.

After admission, only these fixed read commands run:

1. `ls-files --stage -z`, privately validating index paths/modes/stages.
2. `status --porcelain=v2 --branch --no-ahead-behind --untracked-files=all
   --ignore-submodules=all --no-renames -z`.

The index check rejects indexed symlinks, gitlinks and unmerged stages before
status. Submodule inspection is also disabled defensively. Both invocations bind
explicit `--git-dir`, `--work-tree` and cwd; they never search a parent repository.
The helper is private, accepts a closed command enum, and uses a sequence of
arguments with `shell=False` and stdin disconnected. Filenames and branch names
never become command arguments. No generic process/shell Port is introduced.

Semantically this is **read-only repository observation**; its implementation
performs local OS/process effects and is not pure. Optional Git locks/index
refresh writes, lazy fetching, replacement objects, auto maintenance, helpers,
pagers, prompts and network protocols are disabled or excluded by admission.
There are no mutation commands or retries. Observational OS access-time changes
are possible. Tests compare file inventories, bytes and modification times
before and after HEAD/status inspection; their results remain pending.

### Admission, configuration and security boundary

The supported repository is an ordinary non-bare root with a local `.git`
directory, standard refs/index, and regular files in a **trusted, stable local
filesystem namespace**. M2 is used unchanged to check all entries, including
ignored worktree entries and Git metadata. This admission walk does not infer
Git status or parse ignore rules. Its purpose is to reject links/reparse points,
multiple hardlinks, cross-device targets, special files and unsupported names
before Git can access them. Git supplies the status semantics.

Consequently large workspaces, ignored environments containing links, or any
entry outside M2's portable path grammar can fail admission. There is no silent
skip. Index paths are checked too, including currently deleted files. UTF-8
decoding is strict; unsupported control-character paths fail with M2's boundary
error rather than a replacement pathname. Spaces, Unicode, leading dashes and
portable shell-looking filenames are data and are covered by tests.

Gitfiles/linked worktrees are recognized and rejected without following their
external metadata. Bare layouts and nested repositories are rejected. There is
no recursive Git discovery. Alternates, shallow/partial repositories, linked
worktree metadata and submodules are unsupported. Conflicts fail explicitly
without returning a partial successful status. A branch literally named
`(detached)` is rejected because of porcelain's sentinel spelling.

Local configuration is read through M2 and admitted by a deliberately narrow
grammar before invoking Git: simple section/key/value lines, comments on their
own lines, common core filesystem booleans, repository format 0/1, autocrlf,
SHA-1/SHA-256 object format, user name/email and inert remote URL/fetch and branch
remote/merge values. Unknown settings, includes/includeIf, escapes/continuations,
quoted values, inline comments, filter commands, fsmonitor, worktree overrides,
sparse/reftable and other extensions are rejected. This is an admission subset,
not a general replacement for Git's config parser; do not change a real repository's
config just to bypass a rejection. Global/system configuration and attributes/
excludes files are disabled. Repository `.gitignore` and `.git/info/exclude`
still determine ignored paths. Inherited Git, tracing, credentials, HOME, PATH and
loader settings are not forwarded; only Windows SystemRoot is retained where needed.

This is not an OS sandbox, hostile concurrent-mutation boundary, integrity check
of an arbitrary Git binary or descendant-process supervisor. Trust the installed
Git program and host loader, workspace/metadata and stable namespace. No atomic
snapshot is promised between the two commands. Do not deploy this adapter under
stronger adversarial isolation claims. Future governed invocation/disclosure must
enforce ADR-005/007 and runtime resource/evidence obligations before acquisition;
the Port and root objects themselves confer no authorization. ADR-014 remains
unresolved for a supported authoring facade. No canonical document/ADR changes
are needed for this additive ADR-016 reference adapter.

### Bounds and failures

Each policy limit is a required exact int, rejecting bool/coercion. Timeout is
1–60 seconds **per Git invocation**. Stdout and stderr are each bounded to
1–1,048,576 bytes, with one extra byte to detect overflow. Status count is 1–4096;
whole admission/index entry count is 1–65,536. M2 additionally bounds each directory
to 4096 entries and depth to 32; an admission listing may observe that bounded
batch before detecting the aggregate limit. Config/HEAD reads use M2's 262144-byte
and 65536-character ceilings. All byte/count errors fail without partial results.

Private capture polls nonblocking pipes, retains bounded buffers, and closes both
pipes on success/failure. Timeout/overflow kills the direct child and reaps it,
with a separate five-second cleanup wait. There are no reader threads or output
temporary files. Synchronous M2 checks, process creation and OS kill calls do not
have a hard wall-clock interruption guarantee; the timeout is not an end-to-end
inspect deadline or process-tree sandbox. No external cancellation API is claimed.

`git.errors.GitError.reason` uses `GitFailure`: UNAVAILABLE, NOT_REPOSITORY,
INVALID_REPOSITORY, UNSUPPORTED, COMMAND, TIMEOUT, OUTPUT_LIMIT, ENTRY_LIMIT,
DECODE, FORMAT or IO. Missing executable is checked distinctly from a non-Git root.
Missing/wrong required metadata gives INVALID_REPOSITORY; other Git-reported
corruption/nonzero exits give COMMAND, never a false NOT_REPOSITORY. Unexpected
stderr also fails COMMAND, so warnings cannot silently qualify an observation.
COMMAND errors retain a typed `returncode` (including zero for diagnostic output).
M2 WorkspaceError/WorkspaceBoundaryError remain distinct and propagate unchanged.
Top-level messages exclude stderr, environment and paths; chained OS/decoding
causes are trusted diagnostics and may contain paths/bytes. No raw stderr is
attached to an exception. Invalid caller types/bounds raise TypeError/ValueError.

Protocol references: Git's [porcelain v2 contract](https://git-scm.com/docs/git-status#_porcelain_format_version_2),
[execution/environment controls](https://git-scm.com/docs/git), and Python's
[nonblocking pipe support](https://docs.python.org/3.14/library/os.html#os.set_blocking).

### M3 local qualification

Run from the repository root:

```powershell
Push-Location packages/legoai-engineering
uv sync --locked
git --version
uv run pytest -q
uv run mypy src tests examples
uv run ruff check src tests examples
uv run ruff format --check src tests examples
uv run python examples/git_intake.py "$((Get-Location).Path)"
Pop-Location
git diff --check
```

The last example intentionally supplies the package directory, which is not a
Git root. Expected stable output: `repository: absent at supplied root`. It must
not discover the enclosing checkout. For HEAD/status display, pass the absolute
path of an existing repository satisfying the admission contract; output lists
head kind, branch/commit (or `-`), change count and sorted status entries. The
example never creates or deletes a repository. Pytest also exercises it against
an unborn temporary repository with exact expected semantic output.

Git is required for qualification; missing Git fails the integration fixture,
not a successful skip. Tests initialize/commit only temporary repositories with
isolated configuration and local identities. They cover initial/attached/detached
HEAD, SHA-256, staged/unstaged/deleted/untracked/ignored state, rename-as-delete/add,
hostile portable names, roots with spaces, unsupported layouts/configs, corruption,
environment isolation, byte/count limits, real-child timeout/cleanup, inert imports,
closed commands/dependencies and M1/M2 regressions. The existing packaging test
builds wheel and sdist, checks all M3 modules/examples, installs the wheel offline
into a fresh environment and exercises an actual temporary Git observation there.

Expected: pytest passes (review M2's documented platform skips), clean mypy/Ruff/
format checks, expected example output, and no output from `git diff --check`.
Wheel/sdist/install success is not claimed until local results return. New runtime
dependencies: **zero**. Package metadata, pinned tools and lockfile are unchanged.
Return the full output, including warnings/skips. M4 remains unstarted.

### M3 local qualification closure

The maintainer's M4 instruction reports **129 passed, 1 expected Windows skip**,
clean mypy/Ruff, 24 files formatted, successful wheel/sdist/fresh-install checks,
passing example and clean `git diff --check`. This is user-reported qualification,
not internal execution or broader platform assurance. M1–M3 are complete within
their documented scope. `ENGINEERING_M3_COMPLETE = YES`.

## M4 — bounded repository text mutation

**Implementation and local validation complete.** M1–M3 production code is
unchanged; M5 is unstarted. The separate `repository.mutation_ports.RepositoryMutationPort`
exposes only `apply(RepositoryChangeSet) -> RepositoryMutationResult`. The existing
RepositoryWorkspacePort remains read-only. No Git, subprocess, shell, Agent,
Model, framework, Core dependency or public raw host-path write API is introduced.

### Changes and preconditions

Import values from `repository.mutation`:

| Value | Contract |
|---|---|
| `ContentDigest(value)` | Exact lowercase 64-character SHA-256 hex; integrity/version precondition, not signature, trust or authorization |
| `digest_text(text)` | Pure hash of bounded, strictly encoded UTF-8 bytes; same bytes as M2 read then UTF-8 re-encode, with no newline normalization |
| `FileChangeKind` | CREATE, UPDATE, DELETE |
| `FileChange(path, kind, expected, text)` | Exact M2 RepositoryPath; CREATE has no digest and requires text; UPDATE requires digest and text; DELETE requires digest and no payload |
| `RepositoryChangeSet(changes)` | Exact tuple of 1–128 FileChange values, preserving declared order; aggregate encoded payload at most 1,048,576 bytes |
| `FileChangeResult(path, kind, before, after)` | Confirmed operation with absent before digest for CREATE and absent after digest for DELETE |
| `RepositoryMutationResult(applied)` | Immutable tuple in request order; full tuple on success, confirmed prefix inside a failure |

All public values are frozen/slotted and validate without I/O. Duplicate targets,
case-fold aliases and ancestor/descendant target pairs are rejected rather than
reordered. Case-fold rejection is deliberately conservative even on case-sensitive
filesystems. No global changeset ID, arbitrary metadata, approval boolean or
dry-run mode is introduced. Construction validates data; it does not establish
filesystem preconditions or authorization.

CREATE requires the target to be absent. UPDATE and DELETE require an existing
regular text file whose exact-byte digest matches the proposal. Missing targets,
existing create targets and stale digests are semantic conflicts. Parent directories
must already exist. Directories, links/reparse points, multiply linked files,
special files and files without the owner-write mode bit are rejected. There is
no rename, public mkdir/chmod, recursive delete, binary editing or unified-diff
parser. Changesets may update a file to identical bytes; that is still an applied
replacement, not an idempotency guarantee.

### Local implementation and bounds

`repository.mutation_local.LocalRepositoryMutation(LocalWorkspaceRoot, WorkspacePolicy)`
is inert at construction. On apply, it binds M2 LocalRepositoryWorkspace and
reuses the repository owner's existing private path/identity checks and public
bounded `read_text`; M2's path grammar, device/link restrictions and errors are
unchanged. Private reuse is confined to the same repository owner. Future adapters
implement the semantic mutation Port without receiving these filesystem helpers.

The existing policy's `max_read_bytes` and `max_text_chars` bound both old and new
content; there is no second conflicting per-file limit. Its depth and exclusion
rules apply to all targets. Fixed value ceilings remain 65536 code points per
payload and 1 MiB across payloads. Strict UTF-8 encodability and NUL rejection
are checked before preparation, including isolated-surrogate failures. LF/CRLF
are preserved exactly. No BOM is added; an explicitly supplied U+FEFF is preserved
as caller content. Read-back digesting therefore handles existing BOMs exactly.

There is no recursive workspace scan. Administrative checks use seven fixed
names per ancestor, with at most 128 native path components; policy `max_entries`
remains a read-listing budget and is not a changeset count. Memory and temporary
payload bytes are bounded by the changeset. Synchronous filesystem calls can block;
there is no hard deadline or cancellation API and no automatic retries.

### Protected paths and host scope

Any case-insensitive `.git` component is rejected during pure validation, including
the `.git` file itself. Apply also rejects roots/ancestors inside `.git`, gitfile
layouts without following their pointers, and administrative directories identified
by HEAD plus objects/refs/config/commondir/gitdir markers. This protects ordinary
Git directories, recognizable bare/custom administrative roots and their descendants.
Fixed-name ancestor lstat probes may inspect metadata outside the root; they do not
enumerate those directories, read their contents or modify them. Git never runs.

The trusted host must provision a normal workspace and must not bind concealed,
malformed or arbitrarily repurposed Git administration as editable source. This
is not a complete Git-layout discovery API. Worktree/gitfile layouts are unsupported
and fail closed. Conservative marker checks may reject a nongit directory with
the same reserved marker combination. `.venv` and other environment paths are
protected when named in the supplied WorkspacePolicy; the example excludes `.git`
and `.venv`. Other explicitly requested hidden files are allowed.

Qualification remains **trusted, stable local filesystem namespace**, including
file contents and parent metadata during apply. Preconditions catch stale proposals
and some observed changes; they do not eliminate the digest-check-to-write race.
There is no hostile concurrent-mutation isolation, cross-process lock, OS sandbox,
network-filesystem support or atomic snapshot. Root identity is bound per apply
and rechecked through M2. Concurrent use against the same workspace is unsupported.

### Application phases and failure semantics

1. Validate all targets, content limits, existing parents and digest/absence
   preconditions. Failure here changes no target and creates no temporary file.
2. Recheck each write target, then prepare its bounded content in an exclusive
   same-directory temporary file. Flush and close all prepared streams.
3. Recheck every precondition again. Apply in declared order, rechecking each
   target immediately before its final syscall.
4. Clean up remaining temporary files, checking root/parent and file identity.

UPDATE uses `os.replace` of a completed same-directory temporary file, preserving
ordinary mode bits. CREATE publishes a prepared file with `os.link`, which fails
if its destination already exists, then removes the temporary name. Thus CREATE
requires local hardlink support; unsupported filesystems fail without fallback to
blind overwrite. This temporary internal link is not permission to mutate existing
multiply linked user files. DELETE unlinks only a preconditioned regular file.
Temporary names are internally generated `.legoai-*.tmp`; no caller chooses them.
Temporary-name path headroom is checked before preparation.

Successful per-file publication does **not** provide an atomic multi-file commit.
There is no rollback, journal, fsync durability or power-loss guarantee. Failure
during final I/O may leave a completed prefix. CREATE begins with restrictive
temporary-file permissions; UPDATE preserves ordinary mode bits but replacement
does not promise preservation of ACLs, ownership, extended attributes, alternate
streams, timestamps or file identity. Workspaces requiring that metadata preservation
are outside this subset. Explicit chmod/move capability is not exposed.

Python documents [exclusive temporary creation](https://docs.python.org/3.14/library/tempfile.html#tempfile.mkstemp)
and [replacement behavior](https://docs.python.org/3.14/library/os.html#os.replace);
filesystem and OS qualification still govern actual guarantees.

`repository.mutation_errors.MutationConflict` carries a relative path and
MutationConflictReason (EXISTS, MISSING, STALE). M2 WorkspaceError and
WorkspaceBoundaryError propagate for preflight safety/content failures; invalid
request types/combinations raise TypeError/ValueError. After preparation begins,
ordinary failures raise `MutationApplyError` containing:

- `completed`: confirmed applied prefix, possibly empty or the entire changeset;
- `uncertain`: the target of an attempted final syscall without confirmed return,
  or None when no such syscall is in question;
- `temporary_paths`: bounded relative paths whose cleanup was not confirmed.

Original failure and cleanup errors remain chained (ExceptionGroup if needed).
Top-level messages/reprs do not include content or absolute paths. Raw causes
may contain sensitive diagnostics and belong only in trusted operator channels.
Cleanup failure is never silently discarded. A completed create may retain a
second temporary hardlink if cleanup fails; reconcile that state before further
mutation. No automated retry/compensation occurs. Process termination, asynchronous
interrupts or host crashes can prevent a result and leave uncertain effects or
temporary files; no recovery proof is claimed by this in-memory report.

### Governance and validation handoff

**M4 capability ≠ authorization.** This is a reference mutation mechanism, not an
admitted autonomous-Agent facade. Future runtime composition must bind current
Principal/tenant authority, resource/evidence obligations and governed dispatch
before effects under ADR-005/007/008. A digest or constructed changeset grants
no permission. No canonical state/error vocabulary, durable retry scheme or ADR
is created. This is additive ADR-016 capability work; M5 remains unstarted.

The [M4 example](examples/mutation_intake.py) creates a disposable workspace,
creates initial text through the mutation Port, reads it through M2, applies a
digest-preconditioned update and cleans up the temporary directory. It never edits
the checkout or user files and requires no Git commands.

From the repository root:

```powershell
Push-Location packages/legoai-engineering
uv sync --locked
git --version
uv run pytest -q
uv run mypy src tests examples
uv run ruff check src tests examples
uv run ruff format --check src tests examples
uv run python examples/mutation_intake.py
Pop-Location
git diff --check
```

Expected example output:

```text
update: greeting.txt
hello LegoAI
```

Pytest includes M1–M3 regressions, real temporary Git integration for unstaged
create/update/delete without index mutation, preflight conflicts, exact bytes,
path/metadata/link protection, bounds, partial I/O, late conflicts and cleanup
failures. Architecture/import-inertness and wheel/sdist/fresh offline installation
tests include M4. All applicable tests must pass, mypy/Ruff/format must be clean,
and `git diff --check` must produce no whitespace errors. Explain all skips/warnings.
If the new symlink test skips for Windows privilege, rerun in a permitted session:

```powershell
Push-Location packages/legoai-engineering
uv run pytest -q tests/test_mutation.py::test_symlink_target_parent_and_root_escape
Pop-Location
```

Windows junction protection has a separate test and must pass on Windows. Its
non-Windows skip and M2's Windows-inapplicable FIFO skip are intentional. No M4
test/build/install/typecheck/lint/format command was run internally. Zero runtime
dependencies added; package metadata and lockfile unchanged.
`ENGINEERING_M4_COMPLETE = YES` for the documented supported scope. M5 unstarted.

Maintainer validation: 174 tests passed; the sole skip was the POSIX special-file
boundary on Windows. Mypy passed for 30 source files, Ruff lint passed, and the
mutation example produced the expected output. Ruff's format check identified
one formatting defect in `tests/test_architecture.py`; its exact suggested
change was applied. The maintainer's format recheck passed: 30 files already
formatted. `git diff --check` reported only LF-to-CRLF conversion warnings and
no whitespace errors. Packaging validation is included in the passing pytest
suite. M1–M3 regressions passed; the sole skip was unrelated to M4, so Windows
symlink and junction checks passed. M4 is complete within its documented trusted,
stable local namespace qualification; M5 is unstarted.

## M5 — known engineering checks

**IMPLEMENTATION AND LOCAL VALIDATION COMPLETE.** Earlier handoff and
closure entries are historical. M1–M4 remain complete; their production code is
unchanged. `ENGINEERING_M5_COMPLETE = YES` for the documented scope. M6 is unstarted.

**M5 bounds command selection. It does NOT isolate repository code. M5 is not
safe execution of untrusted repository code.** Pytest executes repository Python,
including conftest and explicitly configured plugins; mypy plugins can execute
Python too. Such code can read/write host files, open network connections, spawn
children and access process credentials. Only trusted workspaces, configuration,
installed tools and a trusted, stable local namespace are supported. Directory
targets and tool configuration/import resolution are not a filesystem sandbox.

### Ownership and public contract

Design A from the M5 instruction is selected: an independent semantic Port and
local adapter, with governed composition later. ADR-002/016 retain engineering
semantics outside Core. Existing Core `ExecutionCoordinator` and private
`runtime._composition.governed`/`model_governed` bind particular admitted
capabilities; they are not a public engineering invocation facade. M5 neither
imports these internals nor duplicates admission, authority, dispatch, execution
state, resource accounting or evidence semantics. ADR-014 remains the supported
authoring gate; ADR-012 remains the hostile-code isolation gate. No new canonical
decision or ADR is needed for this scoped reference mechanism.

The public `checks.ports.EngineeringCheckPort.check(CheckRequest) -> CheckResult`
is realized by `checks.local.LocalEngineeringChecks`. The immutable values in
`checks.values` are `CheckRequest`, `CheckPolicy`, and `CheckResult`, with enums
`CheckKind` and `CheckOutcome`. Construction/imports are inert. Requests contain
only a kind and 1–32 unique `RepositoryPath` targets, preserving declared order.
No raw executable, shell string, extra arguments, caller environment, arbitrary
config path, cwd override, node selector or auto-fix mode is exposed. Targets
reuse M2's 240-character portable path syntax and must be UTF-8 encodable.

`LocalCheckTools(pytest, ruff, mypy)` is **trusted host configuration**, separate
from requests. Each is an explicit absolute native path to the corresponding
named executable (`pytest.exe`, `ruff.exe`, `mypy.exe` on Windows; extensionless
names on POSIX). Windows batch/script launchers are rejected. The host must
provision authentic tools: the filename is not executable attestation. There is
no PATH search, version probe, tool import, package-manager invocation, download
or auto-installation. Missing configuration paths can be constructed inertly;
invoking the absent tool raises `CheckError(UNAVAILABLE)`.

### Commands, paths and outcomes

| Kind | Fixed command options before `--` and absolute target paths |
|---|---|
| `PYTEST` | `pytest -q -o addopts= -p no:cacheprovider` |
| `RUFF_CHECK` | `ruff check --no-fix --no-fix-only --no-cache` |
| `RUFF_FORMAT_CHECK` | `ruff format --check --no-cache` |
| `MYPY` | `mypy --no-incremental --cache-dir <os.devnull>` |

Every target is validated before dispatch using M2's public
`LocalRepositoryWorkspace.list_entries(parent)`. This checks root identity,
ancestor/target symlinks and reparse points, regular file/directory type and
hard links; it retains M2's conservative sibling checks. Each parent listing is
bounded at 4096 entries, with depth 32 and `.git`/`.venv` exclusions. A forbidden
sibling or oversized parent directory can reject a check even when its target
alone is ordinary. All supplied targets must exist. The subprocess cwd is the
explicit `LocalWorkspaceRoot`; option-like and `@argfile` names become absolute
path arguments after `--`. No shell or ambient cwd is used.

Tools recursively discover files and dependencies themselves. M2 admission does
not inspect every descendant, imported module, discovered configuration or
external path referred to by trusted configuration. It does not prevent races
after validation. The host must review that namespace and configuration; do not
interpret these entry-path checks as confinement of the running tool.

| Completed exit | Semantic outcome |
|---|---|
| Any supported tool: 0 | `PASSED` |
| Any supported tool: 1 | `FAILED` (check findings, not launch failure) |
| Pytest: 2 | `INTERRUPTED`, also used by pytest for collection/import errors |
| Pytest: 5 | `NO_TESTS` |
| Other exits, including pytest 3/4 and Ruff/mypy 2 | `ERROR` |

Exact exit codes and bounded raw `stdout`/`stderr` bytes are retained in
`CheckResult`; `outcome` is derived rather than independently supplied. Diagnostic
bytes are intentionally not parsed into findings, normalized or silently decoded.
Trusted consumers may decode with an explicit policy. Output may contain source,
host paths or secrets; it is excluded from repr and never automatically logged.
No timestamps, execution IDs, versions or nondeterministic duration fields are
added. Tool/configuration/environment versions still affect observable output.

See the primary [pytest exit-code contract](https://docs.pytest.org/en/stable/reference/exit-codes.html),
[Ruff CLI](https://docs.astral.sh/ruff/configuration/),
[Ruff format-check exits](https://docs.astral.sh/ruff/formatter/), and
[mypy cache controls](https://mypy.readthedocs.io/en/stable/command_line.html#incremental-mode).

### Process limits and failure behavior

`CheckPolicy` defaults to 60 seconds and 262144 bytes **per stream**. Configurable
limits are integers in 1–3600 seconds and 1–1048576 bytes; booleans are rejected.
Private `_process._capture` uses `subprocess.Popen(shell=False)`, argv sequences,
`DEVNULL` stdin and two nonblocking pipes on CPython 3.14. Incremental dual-pipe
draining avoids unbounded `communicate()`, reader threads and output spool files.
An additional byte detects overflow; `OUTPUT_LIMIT` aborts the run rather than
returning a silently truncated result. A monotonic deadline includes launch and
pipe draining; pipes retained by descendants cannot cause indefinite draining.

`CheckError` distinguishes `UNAVAILABLE`, `IO`, `TIMEOUT`, `OUTPUT_LIMIT` and
`CLEANUP`. On failure/interruption the direct child is killed if still running,
waited for up to five additional seconds, and pipes are closed. Failure to confirm
cleanup is reported, preserving exception causality. OS process creation and
filesystem admission cannot be preempted by this synchronous deadline. No strict
wall-clock bound on an unresponsive operating system is promised.

There is no process-tree kill guarantee, host shutdown supervisor, cooperative
cancellation token or retry. `KeyboardInterrupt` propagates after cleanup unless
cleanup itself fails; original context is retained in that case. Descendants can
survive. A timeout, interruption or nonzero exit cannot prove that repository
code had no effects; inspect state before deciding on another run. Resource/tenant
admission, governed cancellation and uncertain-effect accounting remain external.

The child environment retains only `SystemRoot`, `WINDIR`, `PATH`, `TEMP`, `TMP`,
`TMPDIR`, `HOME`, `USERPROFILE`, `APPDATA`, and `LOCALAPPDATA` when present. It sets
UTF-8 Python output, disables Python bytecode writes and pytest entry-point plugin
autoload, and requests no color. Inherited `PYTHONPATH`, `PYTEST_ADDOPTS`, mypy/Ruff
flags and loader settings are omitted; the global environment is unchanged.
Retained home/PATH settings and project configuration are trusted inputs, not
isolated resources. No environment values are included in results or logged.

Ruff fix flags explicitly override project fix settings. Pytest cacheprovider
and mypy/Ruff caches are disabled, but this does not make project execution
read-only: tests, conftest, plugins and configuration-enabled reports may write.
M5 adds no Git staging/commit, M4 bypass helper, shell, framework or Agent/Model
dependency. Tool availability is a host/dev concern; runtime dependencies remain
empty. M6 must address stronger isolation before untrusted-code use.

### Local qualification handoff

**Local validation completed by the maintainer; commands retained below.**
No test/build/install/lint/format/typecheck or M5
tool execution was run internally. Tests include real pytest pass/fail/no-tests
and collection errors; real Ruff lint/format-check and mypy success/findings;
no-fix byte preservation; M4 coexistence; M3 status preservation; missing tools;
stdin EOF; timeout/direct-child reaping; both output bounds and dual-pipe pressure;
path, symlink/junction and argv boundaries; architecture and inert imports.
Wheel/sdist/fresh offline installation tests include M5 and verify import/use
without pytest, Ruff or mypy libraries installed in the fresh environment.

```powershell
Push-Location packages/legoai-engineering
uv sync --locked
git --version
uv run pytest --version
uv run ruff --version
uv run mypy --version
uv run pytest -q
uv run mypy src tests examples
uv run ruff check src tests examples
uv run ruff format --check src tests examples
uv run python examples/check_intake.py
Pop-Location
git diff --check
```

Expected: all applicable M1–M5 tests pass, mypy and Ruff are clean, and the example
prints `ruff_check: passed`. The example provisions only a temporary tiny project,
uses the environment's Ruff executable, installs nothing and cleans up afterward.
The POSIX FIFO test skips on Windows; junction tests skip on non-Windows. POSIX
qualification is not claimed without local evidence. If symlink privilege causes
skips on Windows, rerun those checks in a permitted PowerShell session:

```powershell
Push-Location packages/legoai-engineering
uv run pytest -q tests/test_workspace.py::test_symlink_file_directory_and_root_escape tests/test_mutation.py::test_symlink_target_parent_and_root_escape tests/test_checks.py::test_symlink_target_parent_and_root_rejected
Pop-Location
```

For future validation, retain complete output including warnings/skips and
classify failures before correction. `ENGINEERING_M5_COMPLETE = YES` for the
documented trusted-local scope, based on the maintainer evidence below.
M6, Agent, Workflow, Team and ForgeAI work remain unstarted.

Maintainer validation on 2026-09-23: pytest 9.1.1 reported **215 passed,
1 expected Windows skip** (the POSIX special-file boundary). Mypy 2.3.1 passed
for 38 source files; Ruff 0.16.8 lint passed; the example printed
`ruff_check: passed`. Packaging and real-tool integration checks are included
in the passing suite. Git 2.54.0.windows.1 reported only LF-to-CRLF conversion
warnings during the diff check. The remaining failures were formatting defects
in `checks/local.py` and `tests/test_checks.py`; Ruff's exact suggested changes
were applied without behavioral changes. The maintainer's final format recheck
passed: **38 files already formatted**. The diff check reported only LF-to-CRLF
conversion warnings and no whitespace errors. The sole pytest skip was unrelated
to M5; Windows symlink and junction checks passed. This evidence qualifies the
documented trusted-local Windows scope, not POSIX or untrusted-code isolation.
`ENGINEERING_M5_COMPLETE = YES`; M6 remains unstarted.

## M6 engineering workload isolation

**IMPLEMENTATION AND SCOPED LOCAL VALIDATION COMPLETE**

The statements above record earlier milestone history. M6 now adds
`sandbox.values` (`SandboxRequest`, `SandboxPolicy`, `SandboxArtifact`,
`SandboxResult`), `sandbox.ports.SandboxExecutionPort` and `CancellationSignal`,
`sandbox.errors.SandboxError`/`SandboxFailure`, and the separate
`sandbox.docker.DockerSandbox`/`DockerSandboxConfig` adapter. Runtime dependencies
remain empty. Imports and constructors are inert.

Engineering workload isolation **≠ Plugin isolation**. M6 covers bounded
repository-controlled/generated Python workloads using normal OS APIs, spawning
descendants, modifying sandbox files, emitting malformed output and attempting
filesystem/network escape. Protected assets are the source checkout, other host
files, host environment secrets and Docker control endpoint. The trusted
enforcement base is the host adapter/interpreter, operator-selected pinned image,
Docker daemon/Desktop backend, container runtime and Linux kernel. Those trusted
components are outside M6 protection.

Explicit exclusions: **kernel/runtime exploits; compromised Docker daemon;
compromised host administrator; compromised reference image; hostile co-located
Plugins; cross-tenant isolation; side-channel resistance; production multi-tenant
sandbox service guarantees**. No hostile/untrusted Plugin admission or general
hostile-code execution across LegoAI is qualified. ADR-012 remains **Proposed**.

### Inputs, execution and artifacts

The request contains one Python script (1–65,536 UTF-8 bytes), at most 64 explicit
M1 `RepositoryText` inputs (262,144 bytes each; 1 MiB total), and at most 16 explicit
M2 `RepositoryPath` artifact selections. Paths have at most 32 components
(255 UTF-8 bytes per component). Reuse `RepositoryWorkspacePort.read_text`
for controlled acquisition; no recursive copy or atomic cross-file snapshot is
provided. M2's stable namespace limitations remain. Exclusions reject `.git`,
`.venv`, common credential/cache directories and the reserved internal script
name. Path exclusions cannot detect secrets embedded in ordinary text: selection
and disclosure authorization remain the caller's responsibility.

No source checkout, home, cache, credential directory, Docker socket or arbitrary
host file is mounted. Bounded bytes are sent over stdin into a private Docker
tmpfs volume. The script becomes workload PID 1. A separate, trusted collector
container holds a read-only mount to retain that volume after workload exit.
After Docker confirms workload termination, the collector opens only selected
paths, rejecting ancestor/leaf symlinks, hardlinks, directories and special files.
It does not import workspace code. Content returns as bounded bytes, never host
archive extraction. All results are untrusted data, not canonical Artifacts or
Evidence. Applying a future change still requires M4 preconditions and external
governance; M5 pytest/Ruff/mypy semantics are unchanged and not yet composed here.

The synchronous Port fits this blocking, bounded first consumer without adding
an async runtime. `execute(request, cancellation)` accepts a caller-owned
`threading.Event`-compatible signal. Polling detects cancellation and performs
container-wide cleanup. `KeyboardInterrupt` also unwinds through cleanup, then
propagates if cleanup succeeds. Async task cancellation does not automatically
cancel a call running in another thread; callers must set the signal and await
completion. Forced interpreter termination, host crash and unrecoverable daemon
loss cannot guarantee cleanup. No automatic retries occur.

### Fixed reference profile and local qualification

The maintainer's local run passed the real-backend tests for the controls below.
Cleanup/control-loss exceptions also have fault-injection coverage; no real
daemon-failure drill is claimed. Qualification is limited to this reference
environment and declared threat scope, not universal protection.

| Boundary | Implemented control / qualification test |
| --- | --- |
| Host/source filesystem | No host mounts; explicit inputs; real host canary and source-write attempts, source byte preservation |
| Secrets | Host CLI retains only `SystemRoot`/`WINDIR` plus private `TEMP`/`TMP`; empty Docker config; workload environment fixed to `PATH`, `LANG`, `HOME=/nonexistent`, `TMPDIR=/tmp`; synthetic secret test |
| Network/control endpoint | `network=none`, no published ports/socket, private PID/cgroup/IPC namespaces; loopback-only interfaces and unreachable non-loopback connection test |
| Privilege | UID/GID 65534, all capabilities dropped, no-new-privileges, default seccomp required; effective capability/UID checks |
| Writes | Read-only image root; private `/work` tmpfs volume 32 MiB/4,096 inodes, `/tmp` 8 MiB/1,024 inodes, `/dev/shm` 8 MiB; Docker's private device files remain available; root write rejection and workspace ENOSPC tests |
| CPU | One CPU quota per container; cgroup quota/period checked locally, no performance or scheduling fairness claim |
| Memory | 128 MiB per container, swap disabled; cgroup settings plus real workload OOM test; two-container overhead is explicit |
| Processes | 32 PIDs per container; real bounded process creation reaches EAGAIN; workload namespace exit and forced removal contain descendants |
| Lifetime | Default 60 seconds, configurable 1–300 seconds across preparation/execution/collection; cleanup has a separate 60-second budget; native process creation cannot be preempted by polling |
| Output | Default 256 KiB each stdout/stderr, up to 1 MiB; overflow fails and removes sandbox; transport adds 16 bytes for the trusted preparation prefix |
| Artifacts | Default 256 KiB each/1 MiB total, ceilings 1 MiB each/4 MiB total; count/path/byte validation, link/special-file rejection, stopped writers, bounded protocol parsing |
| Cleanup | Generated names, remove workload then collector then volume; verify absence, no broad prune; success/nonzero/error/timeout/cancel fixtures and fault-injected control loss |

The collector has its own fixed resource profile; this is per-execution
confinement, not aggregate host resource admission. Docker/runtime overhead and
concurrent calls are not globally budgeted. No production host starvation or
multi-tenant guarantee follows. Input preparation errors are distinguished using
a fixed prefix emitted before untrusted script execution. Completed nonzero
exits remain `SandboxResult`; a Docker-observed OOM becomes `RESOURCE_LIMIT`.
Other nonzero exits are not guessed to be resource failures. PID/storage denial
can be caught by the workload and need not produce a special exit classification.

Unavailable runtime/image, unsupported controls, preparation/control failure,
timeout, cancellation, output overflow, unsafe artifacts and cleanup uncertainty
have distinct typed reasons. Diagnostic exception chains are for trusted operators
and may contain host paths; do not serialize them to Agents. A cleanup failure
carries generated `recovery_ids` for operator inspection. Lost creation
acknowledgement remains uncertain even after an empty listing, because delayed
daemon creation cannot be ruled out. No error claims rollback or no effects.

### Local validation required

Reference: Windows CPython 3.14 and Docker Desktop **Linux**, context
`desktop-linux`, platform `linux/amd64`, cgroup v2 and seccomp. The adapter fixes
the local named pipe `npipe:////./pipe/dockerDesktopLinuxEngine` instead of loading
ambient context/proxy/credential configuration. Verify that context endpoint
below; another endpoint is unsupported by this first adapter. The operator binds
an absolute `docker.exe` path. The request cannot select executables, image,
mounts, environment dictionaries, shell strings or runtime flags.

The already prepared immutable environment is:

```text
python@sha256:82bc3c539b8813ada9d68c63b40158fa002f7f33de9bf3312a3dfdc0620dff56
```

No image pull or installation is performed by sandbox execution. Run from the
repository root; each failing native command stops this handoff:

```powershell
Push-Location packages/legoai-engineering
try {
    uv sync --locked
    if ($LASTEXITCODE -ne 0) { throw 'uv sync failed' }
    docker --context desktop-linux version
    if ($LASTEXITCODE -ne 0) { throw 'Docker unavailable' }
    docker context inspect desktop-linux --format '{{.Endpoints.docker.Host}}'
    if ($LASTEXITCODE -ne 0) { throw 'Docker context unavailable' }
    docker --context desktop-linux image inspect 'python@sha256:82bc3c539b8813ada9d68c63b40158fa002f7f33de9bf3312a3dfdc0620dff56' --format '{{.Os}}/{{.Architecture}}'
    if ($LASTEXITCODE -ne 0) { throw 'Pinned image unavailable' }
    uv run pytest -q
    if ($LASTEXITCODE -ne 0) { throw 'pytest failed' }
    uv run mypy src tests examples
    if ($LASTEXITCODE -ne 0) { throw 'mypy failed' }
    uv run ruff check src tests examples
    if ($LASTEXITCODE -ne 0) { throw 'Ruff lint failed' }
    uv run ruff format --check src tests examples
    if ($LASTEXITCODE -ne 0) { throw 'Ruff formatting failed' }
    uv run python examples/sandbox_intake.py
    if ($LASTEXITCODE -ne 0) { throw 'Sandbox example failed' }
} finally {
    Pop-Location
}
git diff --check
if ($LASTEXITCODE -ne 0) { throw 'Whitespace check failed' }
```

Expected: real Docker sandbox tests and M1–M5 regressions pass; package/wheel and
inert-import checks pass; mypy/Ruff clean. Example prints `hello isolated LegoAI`
then `source unchanged; synthetic host secret absent`. No M6 test may skip on
the reference Windows host; missing Docker/image fails explicitly. Existing
POSIX-only special-file tests may skip on Windows; existing symlink tests require
the previously established Windows privilege. Non-Windows M6 skips do not
qualify another backend. Retain complete output, including skips and warnings.

No test/build/install/Docker qualification/lint/formatter/typechecker was run by
the implementing assistant. The maintainer reported **265 passed, 1 expected
POSIX-only skip**, mypy clean for **48 source files**, and a successful sandbox
example. Final Ruff rechecks reported **All checks passed!** and **48 files already
formatted**. The diff check showed only LF-to-CRLF conversion warnings, with no
whitespace errors. Only import-order/formatting edits followed the passing tests.
**ENGINEERING_M6_COMPLETE = YES** for the declared reference scope. M1–M5 retain
their prior scope; M6.5 and M7 are unstarted. See the
[completion report](../../planning/ENGINEERING-M6-IMPLEMENTATION.md#completion-report).

## M8.1 — Repository Analyst

**COMPLETE for the documented local scope.**

`analyst.api.RepositoryAnalyst` composes a trusted `RepositoryEvidencePort` with
the existing M7 `AgentRuntimePort`. `repository_analyst_definition()` returns an
immutable version 1.0.0 definition using the M6.5 `engineering-reasoning` profile.
The [offline example](examples/repository_analyst.py) supplies real routing,
governed Chat and an in-memory fake ModelPort; it requires no provider service.
Install the `analyst` extra to add the existing Core distribution. Base M1–M6
modules retain zero runtime dependencies. Core, Model adapters and M7 are unchanged.
See [ADR-018](../../adrs/ADR-018.md) for placement and authorization decisions.

The request contains a bounded question, explicit RepositoryPath targets and an
ExecutionContext. Trusted composition supplies the workspace and model configuration;
neither the request nor instructions grant permission. `analyst.authorized.AuthorizedRepositoryEvidence`
binds an explicit M2 Port to a workspace ConfigurationRef, an exact path allowlist,
SecurityContext, AuthorizationPort and clock. It requires the external
`read-for-model-analysis` action covering reads **and disclosure to the configured
model**. The operator must associate that authorization with the destination used
by the injected M7 runtime. There is no destination discovery or permission issuer.
Current grant/policy is evaluated before each read and before releasing evidence;
approval-bearing contexts fail closed. This trusted local association is not a
new published capability or protection from malicious in-process adapters.

| Boundary | Limit and behavior |
|---|---|
| Selection | 1–8 explicit distinct paths; no search, listing or Git; lexical path order |
| Question | Nonblank, at most 2,048 UTF-8 bytes |
| Evidence | Complete file text, at most 8,192 UTF-8 bytes/file and 24,576 total |
| Serialized input | Question and file JSON at most 32,768 UTF-8 bytes, including escaping |
| M7 prompt | At most 49,152 UTF-8 bytes including versioned instructions |
| Accepted Model output | At most 16,384 UTF-8 bytes, enforced by existing M7 |
| Analysis | Summary at most 2,048 bytes; at most eight relevant files, findings, risks and unknowns each |
| Finding | Nonblank text at most 1,024 bytes and 1–8 distinct evidence-member paths |
| Risk/unknown | Nonblank text at most 1,024 UTF-8 bytes per entry |

No silent truncation or arbitrary partial selection occurs. Acquisition failure
returns INSUFFICIENT_EVIDENCE with DENIED, UNAVAILABLE, BOUNDARY or BUDGET and no
Agent invocation. Missing files are not submitted to the model for guessing.
No-match/ambiguous routing returns MODEL_FAILURE without invoking the Model.
Model failures preserve the original AgentResult and downstream effects, including
UNKNOWN. Successful model transport with malformed JSON, duplicate/extra fields,
invalid sizes or fabricated structured paths returns OUTPUT_INVALID, preserving
the completed model effect. No retry or fallback occurs.

Successful structured analysis requires exact schema validation. Every finding
cites supplied files. Relevant files and finding paths must match supplied labels
exactly; unknown references fail closed. **Only citation membership is validated**:
all narrative (including filenames mentioned in prose) remains unverified model
claims, not independently confirmed repository facts. INSUFFICIENT_EVIDENCE from
the model requires at least one unknown and no findings. Results retain bounded
evidence and Agent attribution for trusted consumers; do not log those payloads.
Source content and model narrative are excluded from repr and validation messages.

M2 enforces existing root, exclusion, symlink/reparse and file-size semantics.
The workspace must satisfy M2's trusted stable-filesystem assumptions; these reads
are not an atomic snapshot. Synchronous M2 reads add no hard I/O deadline or new
cancellation mechanism. Unexpected composition errors and cancellation propagate
without fabricated settlement. File content cannot request further effects: the
Analyst receives no mutation, Git, check, shell or sandbox capability. This slice
has no tools, memory, Workflow, Team or executable patch result.

Agent accepted-output size is bounded. Provider generation, tokens, HTTP response
allocation, transport memory and provider cost are not bounded by this policy.
Token limits, bounded transport, provider-specific max-token translation and
generation/resource budgeting remain future Model/runtime work.

### Local validation required

No tests, formatting, typechecking, builds, installs or examples were run internally.
The new optional dependency requires **local lock regeneration** before locked
commands; review and include `packages/legoai-engineering/uv.lock` in the change.
Use PowerShell from the repository root. The wrapper stops on native-command errors.

```powershell
function Invoke-AnalystCheck([scriptblock] $Action) {
    & $Action
    if ($LASTEXITCODE -ne 0) { throw 'Local M8.1 validation failed; classify before continuing' }
}

# Direct Core dependencies: M7, M6.5 and governed Model integration.
Invoke-AnalystCheck { uv run --locked --no-sync python -m pytest -p no:cacheprovider -q tests/unit/execution/test_agent.py tests/architecture/test_agent.py tests/integration/composition/test_agent.py tests/unit/reference/test_model_routing.py tests/architecture/test_model_routing.py tests/unit/reference/test_model.py tests/unit/intelligence/test_model_values.py tests/integration/composition/test_model_governed.py }

Push-Location packages/legoai-engineering
try {
    Invoke-AnalystCheck { uv lock }
    Invoke-AnalystCheck { uv sync --locked --extra analyst }
    # Import ordering and formatting are intentionally handed off locally.
    Invoke-AnalystCheck { uv run --locked --no-sync ruff check --fix src tests examples }
    Invoke-AnalystCheck { uv run --locked --no-sync ruff format src tests examples }
    Invoke-AnalystCheck { uv run --locked --no-sync ruff check src tests examples }
    Invoke-AnalystCheck { uv run --locked --no-sync ruff format --check src tests examples }
    Invoke-AnalystCheck { uv run --locked --no-sync mypy src tests examples }
    $analystTemp = Join-Path ([IO.Path]::GetTempPath()) ('legoai-m81-' + [guid]::NewGuid().ToString('N'))
    # Includes Analyst units/governed integration, architecture/inertness,
    # M1/M2 regressions, other non-Docker Engineering tests and wheel/fresh install.
    Invoke-AnalystCheck { uv run --locked --no-sync python -m pytest -p no:cacheprovider --basetemp $analystTemp -q tests --ignore=tests/test_sandbox_docker.py }
    Invoke-AnalystCheck { uv run --locked --no-sync python examples/repository_analyst.py }
} finally {
    Pop-Location
}
Invoke-AnalystCheck { git diff --check }
```

The packaging test builds wheel/sdist, checks optional dependency metadata, uses
a fresh environment without Core for the original pack, then installs the Core
wheel offline and runs the Analyst example outside the checkout. Example output:
`succeeded`, `a.py, b.py`, `The supplied files define and import greet.`
Full affected Engineering coverage includes the new tests; it does not rerun real
Docker because sandbox code is unchanged. Core dependency regressions cover the
integration boundary; unchanged Document/DocuMind packages need no new run.
Existing POSIX-only skips on Windows are expected. Symlink coverage requires the
previously established Windows privilege; a skipped Analyst escape test leaves
that local qualification pending. Retain complete output and classify failures
as CODE, TEST, ENVIRONMENT, CONFIGURATION or TOOLCHAIN/DEPENDENCY DEFECT.

Maintainer evidence: 153 Core regressions and 284 Engineering tests passed;
mypy passed for 55 files; Ruff lint/format, wheel/sdist/fresh install and offline
example passed. Initial Analyst/M2 symlink skips were closed by **2 passed in
0.16s** in the targeted rerun. Diff check had only line-ending notices. The
environment mismatch and copy fallback warnings did not prevent installation.
See the [completion report](../../planning/M8.1-REPOSITORY-ANALYST-PLAN.md#completion-report).
`REPOSITORY_ANALYST_M8_1_COMPLETE = YES`. M1–M7 retain their qualified scopes.

## M8.2 — Independent Reviewer

**COMPLETE for the documented local supplied-text review scope.**

`reviewer.api.IndependentReviewer` evaluates an explicitly supplied textual
proposal using existing M7 `AgentRuntimePort`. It has no filesystem, mutation,
Git, test, lint or sandbox Port. The immutable v1.0.0 definition uses AgentId
`independent-reviewer` and the existing `engineering-reasoning` profile. No new
provider, framework, runtime dependency or Core contract is introduced. The
existing `analyst` extra supplies Core for both Engineering specializations.

`ReviewRequest` carries the producer AgentId, objective, criteria, proposal,
supporting ReviewMaterial tuple and ExecutionContext. The producer identity must
differ from the fixed Reviewer identity. A match yields INVALID_SUBMISSION /
SELF_REVIEW before any Model call. Trusted callers must attest producer identity
and authorize disclosure of all supplied material to the configured Model.
Changing the supplied ID is not proof of a different author. This invariant
establishes definition separation, not separate model weights, principals or
unbiased reasoning. The existing governed Chat path still controls invocation.
Request text and Model instructions confer no authority.

| Input/output | Bound |
|---|---|
| Objective | Nonblank, 2048 UTF-8 bytes |
| Criteria | 1–8 nonblank strings, 1024 bytes each; caller order retained |
| Proposal | Nonblank, 8192 bytes; reserved material ID `proposal` |
| Supporting material | 0–8 unique items, 4096 bytes each; sorted by ID in prompt |
| Total material | Proposal plus supporting text <=24576 bytes |
| Material IDs | 1–64 lowercase ASCII letters/digits/hyphens/underscores; not paths |
| Serialized input | <=32768 bytes including JSON escaping and criteria |
| M7 prompt | <=49152 bytes including instructions |
| Accepted output | <=16384 UTF-8 bytes through M7 |
| Review summary | Nonblank, <=2048 bytes |
| Findings, risks, unknowns | Each at most 8 entries; narrative <=1024 bytes per entry |
| Finding references | 1–8 unique supplied material IDs |

Malformed typed input raises safe TypeError/ValueError before invocation; excessive
serialized context returns INVALID_SUBMISSION / CONTEXT_BUDGET. Nothing is
truncated or compressed. One existing M7 call follows deterministic input assembly.
No-match/ambiguous routing and failed governed invocation produce MODEL_FAILURE.
Malformed output produces OUTPUT_INVALID, preserving the AgentResult and completed
or unknown downstream effects. Unexpected composition errors/cancellation propagate;
the specialization adds no retries, fallback or new I/O timeout mechanism.

`ReviewResult` separates execution status from a `Review` opinion. COMPLETED means
the bounded schema and references were validated. Opinions are ACCEPT,
CHANGES_REQUIRED, INSUFFICIENT_EVIDENCE. Each finding carries a closed category
(correctness, architecture, security, maintainability, testing, performance,
documentation), severity (info, warning, blocking), message, evidence_refs and
required_action. A blocking finding requires a nonblank action; nonblocking findings
carry null. CHANGES_REQUIRED requires a blocker; ACCEPT forbids blockers.
INSUFFICIENT_EVIDENCE requires unknowns and no blockers. If a known blocker exists,
report CHANGES_REQUIRED and retain unknowns alongside it. Required actions are
textual requests, never executable patches or changesets. There is no numeric score.

The JSON schema rejects missing/extra/duplicate fields, invalid enum values,
contradictory opinions and fabricated structured references. Only membership in
supplied material is validated. Narrative and any prose filename mentions remain
unverified Model claims. IDs are not verified repository paths or canonical Evidence.
Review is not an approval token, mutation authorization or Workflow transition.
Consumers must apply their own deterministic checks and governance before action.

Payloads are excluded from repr and validation errors; consumers must not log
request material or retained Model text. Accepted-output bounds do not bound
provider generation, token count, transport allocation or cost. Those optimizations
remain deferred. No tools, memory, Workflow, Team, self-correction or voting loop.

### M8.2 local validation

Static source review only was performed internally, as requested. Use the script
from the repository root:

```powershell
.\INDEPENDENT_REVIEWER_M8_2_test.ps1
```

The script contains exact commands for focused M7/M6.5/Model regressions,
Engineering's full non-Docker suite (including M8.1 and Reviewer governed
integration), typing, Ruff, both offline examples and diff checking. Packaging
tests build wheel/sdist, install the pack and Core wheels in a fresh environment,
then run copied examples and their shared demo helper outside the checkout.
`examples/governed_demo.py` is example-only wiring; production Core and M8.1
contracts remain unchanged. Metadata is unchanged; no new lock resolution is needed.
Use a symlink-capable Windows session to retain existing boundary coverage.
Only POSIX-only skips are expected on the reference Windows host. No Docker run
is required. A full Core rerun is unnecessary because Core production did not change.

Reviewer example prints `changes_required`, `correctness`, then
`The proposal needs a missing-input policy.` Maintainer validation reports
**153 Core regressions passed** and **333 Engineering tests passed, 5 skipped**.
Mypy passed for 62 source files; Ruff lint and formatting passed after three files
were formatted locally. Wheel/sdist/fresh-install coverage passed within the full
Engineering suite. Both offline examples printed the expected output. The final
diff check reported only LF-to-CRLF notices.

Four existing symlink tests skipped because the session lacked Windows privilege;
the fifth skip is the POSIX special-file boundary. These are environment/platform
limitations, not Reviewer failures. Analyst/M2 symlink checks already passed in
the earlier elevated rerun (2 passed in 0.16s). M8.2 changes no filesystem boundary
or Analyst production semantics; unchanged M4/M5 retain prior qualification.
No repeated elevated run is needed to qualify this supplied-text Reviewer scope.
The uv environment warning confirms selection of the intended Engineering venv.
No code, configuration or dependency defect remains in this output.

See the [completion report](../../planning/M8.2-INDEPENDENT-REVIEWER-PLAN.md#completion-report).
M8.3 Coding and M8.4 Test/Validation Agents remain unstarted.
`INDEPENDENT_REVIEWER_M8_2_COMPLETE = YES`.

## M8.3 — Bounded Coding Agent

**COMPLETE for the documented local scope** (qualified 2026-09-29; see closure below).

`coding.api.CodingAgent.propose` receives an immutable `CodingRequest`: objective,
1–8 `CodingTarget` values (RepositoryPath plus existing M4 CREATE/UPDATE kind),
up to eight constraints and ExecutionContext. `coding_definition()` returns
`coding-agent` v1.0.0, distinct from Analyst and Reviewer, using the existing
`engineering-reasoning` profile. The Agent acquires deterministic bounded evidence,
invokes M7 once, validates JSON, and returns actual M4 RepositoryChangeSet data.
It has no mutation, Git, check, sandbox, Reviewer, memory or Workflow Port.

Trusted `coding.authorized.AuthorizedCodingEvidence` wraps the existing M8.1
AuthorizedRepositoryEvidence. This reuses its explicit M2 workspace, operator
allowlist, grant/policy evaluator, clock and `read-for-model-analysis` action.
The operator binds the workspace and configured Model destination and authorizes
all disclosure. Request targets cannot widen that allowlist. UPDATE uses the
existing authorized read path. CREATE additionally requires operator-authorized
bounded metadata inspection of the target's parent under the same workspace scope.
The private M8.1 authorization check is reused before each CREATE observation and
before releasing the final bundle; no new authorization framework/action is added.
Approval-bearing contexts remain unsupported and fail closed.

CREATE requires an existing parent with a successful bounded M2 listing and no
case-insensitive target match, followed by a target read returning MISSING.
That read also enforces target-specific M2 exclusions/depth, so excluded names
are not mistaken for absence. Other read failures do not mean CREATE is allowed.
Parent entry metadata is never sent to the Model. Listing can conservatively fail
because of parent size, excluded/unsafe namespace or another unsupported entry;
there is no discovery fallback. New directories are not proposed or created.
All dot-prefixed components, including .git/.venv/.env, are outside this first slice.
M2's path, alias, symlink/reparse, hardlink and stable-filesystem rules are retained.

Each `CodingFile` holds its selected target and exact current RepositoryText for
UPDATE, with an init-disabled ContentDigest computed by M4 `digest_text`. CREATE
holds no current text or digest. `CodingEvidence` is sorted by exact path. Digests
are not requested from or disclosed to the Model, and a digest field in output
is rejected. UPDATE proposals receive the corresponding trusted digest; CREATE
uses M4's absence precondition (`expected=None`). Neither observation is guaranteed
current at later application: separately authorized M4 application must recheck it.

| Boundary | Limit |
|---|---|
| Targets | 1–8 distinct portable paths; no case aliases or ancestor overlaps |
| Objective | Nonblank, <=2048 UTF-8 bytes |
| Constraints | 0–8 nonblank strings, <=1024 bytes each |
| Existing file | <=8192 UTF-8 bytes; exact BOM/newlines retained |
| Total acquired content | <=24576 bytes |
| Serialized input | <=32768 bytes, including JSON escaping |
| Total M7 prompt | <=49152 bytes, including static instructions |
| Accepted output | <=32768 UTF-8 bytes |
| Generated file/total | <=8192 bytes per file, <=24576 bytes total |
| Summary/reasons | Summary <=2048; one nonblank reason <=1024 per change |
| Risks/unknowns | 0–8 nonblank strings each, <=1024 bytes per string |

Closed JSON fields: `summary`, `changes`, `risks`, `unknowns`. Each of 1–8 changes
has exactly `path`, `operation`, `content`, `reason`. Every returned path and kind
must match a selected target. A subset of selected targets may be proposed, but
no invalid change is silently dropped. Duplicate keys/paths, extra fields,
fabricated targets, DELETE, invalid UTF-8, NUL and oversized payloads fail the
entire proposal. Empty replacement content is valid. No truncation or compression.
Constructing actual M4 FileChange/RepositoryChangeSet values retains M4's own
precondition, path and payload validation. Reasons remain ordered with those changes.

`CodingResult` separates SUCCEEDED, INVALID_REQUEST, MODEL_FAILURE and OUTPUT_INVALID.
Malformed request values raise safe constructor errors. Acquisition/absence/scope
failure returns INVALID_REQUEST with existing AcquisitionFailure classification;
serialized context overflow uses BUDGET. No-match/ambiguous routing and governed
invocation failure return MODEL_FAILURE. Invalid output carries no partial
CodingProposal. The exact AgentResult and completed/unknown Model effects are
preserved. Source and narrative are excluded from repr/error messages; consumers
must not log retained source or raw Model output. Unexpected Port errors and
cancellation propagate; M2 synchronous I/O has no new timeout/cancellation guarantee.

**Proposal is not authorization or mutation.** Only separately authorized external
code may later call M4 apply. This Agent and its offline example never do so.
Generated code is not tested, executed, self-reviewed or independently reviewed.
Model narrative remains unverified, and syntactically valid proposals can be wrong.
No retries, fallback, auto-repair or Coding→Reviewer orchestration. Provider token
generation, transport allocation and cost limits remain deferred; M7 only bounds
accepted output. DELETE is deferred because the initial fixture needs CREATE/UPDATE.

### M8.3 local validation required

No tests, typechecker, Ruff, builds, installs or examples ran internally. From the
repository root, in a symlink-capable Windows PowerShell session, run:

```powershell
.\CODING_AGENT_M8_3_test.ps1
```

The script runs focused M7/M6.5/Model regressions, the full non-Docker Engineering
suite (M8.3, Reviewer, Analyst, M4, architecture/inertness and packaging), mypy,
Ruff lint/format, all three offline examples and diff check. Existing metadata
and the `analyst` extra are reused; no dependency or lock change is needed.
Packaging checks wheel/sdist inventory and runs all copied examples against a
fresh installed wheel plus existing Core. The Coding example creates only its
temporary fixture and prints `succeeded`, `1 proposed change`, `example.py update`.
No generated proposal is applied. A separate test driver deliberately exercises
M4's rejection of stale/now-existing targets to prove handoff compatibility;
this adds no production apply path.

New Coding symlink tests for UPDATE targets and CREATE parents must pass to close
M8.3; a privilege skip leaves those boundaries pending. Existing POSIX-only skips
on Windows are expected. Do not rerun Docker or unrelated application suites.
Classify failures as CODE, TEST, ENVIRONMENT, CONFIGURATION or TOOLCHAIN/DEPENDENCY
DEFECT and request only the smallest necessary rerun.
`CODING_AGENT_M8_3_COMPLETE = NO` until local evidence is green. M8.4 is unstarted.

### M8.3 local qualification closure

Maintainer evidence (2026-09-29, symlink-capable Windows session):
- Core focused regressions: 153 passed.
- Ruff lint and format and mypy: clean, 70 files.
- Engineering suite, excluding Docker: **408 passed, 1 skipped**. The skip is the
  POSIX special-file test, which doesn't apply on Windows.
- All six symlink boundary tests passed:
  - Coding CREATE/UPDATE target or parent;
  - Analyst;
  - M2 workspace;
  - M4 mutation;
  - M5 checks.
- All three examples printed exactly their expected output.

Qualification includes the CR-1b public-host composition of the examples. It also
includes one corrected test expectation: CPython 3.13+ raises `TypeError` for
`replace` on the init-disabled digest. See the
[completion report](../../planning/M8.3-BOUNDED-CODING-PLAN.md#completion-report).
`CODING_AGENT_M8_3_COMPLETE = YES`. M8.4 is unstarted.

## ADR-014 public governed host (CR-1b; locally qualified 2026-09-28)

The offline examples now compose through Core's public local host only
(`legoai.runtime.api`, `legoai.runtime.local`). `examples/governed_demo.py` opens
one host per demo, with operator grants for Chat and `read-for-model-analysis`.
`repository_analyst.py` takes its read `SecurityContext` and `AuthorizationPort`
from `host.security_context(...)`/`host.authorization`. No example imports
`legoai.reference.*` or `legoai.runtime._composition.*`, or constructs a `Grant`.
Denied authority is modelled as a configured but expired grant; the M8.3
governance-separation test now uses an expired model grant with authorized
reads (`model_allowed=False`), because a hand-forged context is refused earlier
as `FOREIGN_CONTEXT` (covered in Core). The host pins one
binding, so the engineering tests exercise NO_MATCH routing only; ambiguous
routing stays covered by Core M7 tests. Specialization contracts and the
read-composition modules were unchanged here; CR-3 later made them public as
`analyst/authorized` and `coding/authorized`.
See [ADR-014](../../adrs/ADR-014.md).

## CR-2a — Python engineering-check sandbox image (locally qualified 2026-09-29)

**COMPLETE — LOCALLY DOCKER-QUALIFIED** for the reference environment (see
"CR-2a qualification evidence" below). This extends M6's closed image set;
it does not add a second sandbox or change any runtime control. The
`EngineeringCheckPort` adapter that uses this image belongs to CR-2b.

**Closed image set.** `DockerSandboxConfig(executable, profile=SandboxImage.…)`
replaces the former free-form `image` string, and callers can no longer supply an
image reference.
- `SandboxImage.PYTHON_STDLIB` is the unchanged M6 image (`python@sha256:82bc…`),
  and it remains the default.
- `SandboxImage.PYTHON_CHECKS` is bound to the exact qualified local image ID
  `sha256:4c64580306983d70e059f5f133f6bb3f82657c9c61fa96f562f42594f20269df`,
  recorded in `sandbox.docker._approved_image`. An unqualified identity fails
  closed before any Docker call. The image is never pulled: on a machine without
  that exact local image, execution fails with `ENVIRONMENT_UNAVAILABLE`.
- Only immutable references are accepted: `python@sha256:<64 hex>` or a local
  image ID `sha256:<64 hex>`. Mutable tags are rejected.

Both images run under the identical fixed M6 profile:
- `network=none`, `--pull=never`, UID/GID 65534, all capabilities dropped,
  no-new-privileges, read-only root;
- 1 CPU, 128 MiB memory with swap disabled, 32 PIDs;
- 32 MiB `noexec` `/work`, 8 MiB `/tmp`;
- 1–300 s lifetime and bounded output.

No image selects or alters any of these.

**Image contents.** `sandbox-images/python-checks/Dockerfile` builds from the
pinned M6 base (`python:3.14.7-slim-bookworm`, amd64, by digest). It installs,
with `--require-hashes --no-deps --only-binary=:all:`, only the dependencies
exported from this package's `uv.lock` into `requirements.txt`:
- pytest 9.1.1, Ruff 0.16.8, mypy 2.3.1;
- pluggy 1.6.0, iniconfig 2.3.0, packaging 26.3, pygments 2.21.0,
  mypy-extensions 1.1.0, typing-extensions 4.16.0, pathspec 1.1.1, librt 0.15.0,
  ast-serialize 0.11.2.

The image contains no application source, secrets, credentials, Git or provider
SDKs. The build needs network (an operator step); sandbox runtime never
downloads or installs anything.

**Digest qualification model.**
1. Build.
2. Capture the local image ID.
3. Qualify that ID.
4. Review and record it.
5. The profile is enabled.

During qualification the candidate ID reaches the tests only through
`LEGOAI_SANDBOX_CHECKS_IMAGE`, bound inside the test process. Production
configuration accepts only the recorded ID. A rebuild yields a new ID and needs
requalification; bit-for-bit reproducibility is not claimed.

**Memory measurement.** A trusted qualification harness runs each tool as a
child process with M5's exact options, then reads `memory.peak`, `memory.max` and
`memory.events` (`oom_kill`) from the container's own cgroup v2. The peak is
whole-container: harness, tool, and tmpfs input pages. That is exactly what the
128 MiB limit applies to. The fixture is a small typed package (7 modules and
3 test files, about 7.9 KB) within the unchanged input ceilings of 64 files,
256 KiB each and 1 MiB total. Results are recorded here once qualified.

**Containment is not result integrity.** Sandboxed pytest runs
repository-controlled and model-written code in the pytest process. That code can
manipulate its own outcome, for example with `os._exit(0)`. A passing result
means "the contained process produced this observed result", not "the code is
correct or trustworthy". CR-2b must preserve this statement. Hostile Plugin
isolation remains ADR-012.

**Qualification (operator, from the repository root, Windows + Docker Desktop Linux):**

```powershell
uv run python .\validate_consumer_readiness_cr2a.py
```

Part A is deterministic (typing, Ruff, profile tests, architecture/packaging).
Part B builds the image and qualifies it with real Docker:
- versions and contents;
- confinement;
- pytest pass, fail, collection error and no-tests;
- Ruff clean and finding;
- format clean and finding;
- mypy clean and finding, with memory rows;
- timeout, output limit, PID limit, OOM and cleanup;
- the existing stdlib M6 regression.

### CR-2a qualification evidence

Maintainer run of `validate_consumer_readiness_cr2a.py` on 2026-09-29 (Windows,
CPython 3.14.5, uv 0.11.19, Docker Desktop Linux engine, cgroup v2): **all 20
phases passed**.

**Part A (deterministic):**
- Engineering mypy clean on 71 files; Ruff lint and format clean.
- Profile tests: 41 passed.
- Architecture and packaging: 74 passed.

**Part B (real Docker):**
- Pinned base `python:3.14.7-slim-bookworm` present; image built in 21 s.
- Qualified image ID
  `sha256:4c64580306983d70e059f5f133f6bb3f82657c9c61fa96f562f42594f20269df`.
- Contents: Python 3.14.7, exactly the 12 locked distributions plus the base's
  pip 26.2.1, no Git, tools at `/usr/local/bin/{pytest,ruff,mypy}`.
- M6 confinement held under the new image: network, host secrets, host files,
  privilege, read-only root and cgroup limits.
- Timeout → `TIMEOUT`; output overflow → `OUTPUT_LIMIT`; the PID limit was
  reached inside pytest; memory exhaustion → Docker-reported `RESOURCE_LIMIT`
  (not a silent success).
- Containers and volumes were cleaned up after every run.
- Existing stdlib M6 regression: 20 passed.

**Measured whole-container peak memory under the unchanged 128 MiB limit**
(`memory.max` 134217728; `oom_kill` 0 in every row):

| Tool | Fixture | Exit | Peak | Share of limit | Elapsed |
|---|---|---|---|---|---|
| pytest | baseline (11 passing tests) | 0 | 41.8 MB | 31% | 1.38 s |
| pytest | failing test | 1 | 39.9 MB | 30% | 1.05 s |
| pytest | collection error | 2 | 46.5 MB | 35% | 1.05 s |
| pytest | no tests (`src`) | 5 | 39.7 MB | 30% | 0.93 s |
| pytest | 31-process fork test | 0 | 65.8 MB | 49% | 1.00 s |
| Ruff check | clean / finding | 0 / 1 | 9.4 / 10.0 MB | 7% | 0.01 s |
| Ruff format check | clean / unformatted | 0 / 1 | 9.4 / 9.6 MB | 7% | 0.01 s |
| mypy (strict) | clean / type error | 0 / 1 | 69.0 / 67.5 MB | 51% / 50% | 1.7 s |

These measurements cover the qualified small fixture: 7 typed modules and
3 test files, about 7.9 KB. mypy was the largest consumer, at about half the
limit; most of its cost is loading the standard-library stubs, not project size.
The remaining headroom is measured for this scope only. Larger projects, heavier
imports or third-party stubs can raise the peak. **No general capacity is
claimed, and the resource profile was not changed.** CR-2b must treat
`RESOURCE_LIMIT` as a truthful failure, never a pass.

**Re-qualification.** Re-running the validator rebuilds the image and qualifies
the new build's ID. That ID may differ from the recorded one; the run prints
`CR2A-CANDIDATE` when it does. Replace the recorded ID only after a new passing
run. To re-check the recorded image without rebuilding (no candidate variable
set):

```powershell
Push-Location packages/legoai-engineering
$basetemp = Join-Path ([IO.Path]::GetTempPath()) ('legoai-cr2a-' + [guid]::NewGuid().ToString('N'))
uv run --locked --no-sync python -m pytest -p no:cacheprovider --basetemp $basetemp -q -rs -s tests/test_sandbox_checks_docker.py
Pop-Location
```

A fresh `--basetemp` avoids pytest's shared Windows temp-root cleanup failure
(`PermissionError` on `pytest-of-<user>\pytest-current` after the tests finish).

**Post-enable confirmation (2026-09-29):** the maintainer re-ran all 16 Docker
tests against the recorded ID, with no candidate variable set. All tests passed
with matching evidence: mypy about 67 MB, pytest 40–66 MB, Ruff about 10 MB,
`oom_kill` 0, and memory exhaustion reported as `RESOURCE_LIMIT`. pytest's
default temp-root cleanup then raised the Windows `PermissionError` described
above, after the tests had finished. That is an environment issue, not a test
result.

## CR-2b — sandboxed engineering checks (locally qualified 2026-09-29)

`legoai_engineering.checks.sandboxed.SandboxedEngineeringChecks` is a second
adapter for the existing `EngineeringCheckPort`, which is unchanged. It runs
the four M5 check kinds (`PYTEST`, `RUFF_CHECK`, `RUFF_FORMAT_CHECK`, `MYPY`)
inside the M6 sandbox on the CR-2a `PYTHON_CHECKS` image. It depends only on
`RepositoryWorkspacePort` and `SandboxExecutionPort`, never on Docker. The
slice is locally qualified for the reference scope only; see "CR-2b
qualification evidence".

### When to use which adapter

| Adapter | Target code runs | Use when |
| --- | --- | --- |
| `LocalEngineeringChecks` (M5) | On the host, as the host user | The repository is trusted, for example the maintainer's own tree |
| `SandboxedEngineeringChecks` (CR-2b) | In one confined M6 container per check | The code under test is not trusted, for example agent-written or third-party changes |

There is **no host fallback**. If the sandbox or the qualified toolchain is
unavailable, the check fails with `UNAVAILABLE`; it never falls back to
running on the host. Callers choose the adapter at the composition root.

### Composition

```python
from legoai_engineering.checks.sandboxed import CheckInputPolicy, SandboxedEngineeringChecks
from legoai_engineering.checks.values import CheckPolicy
from legoai_engineering.repository.workspace import RepositoryPath
from legoai_engineering.sandbox.docker import DockerSandbox, DockerSandboxConfig, SandboxImage
from legoai_engineering.sandbox.values import SandboxPolicy

checks = SandboxedEngineeringChecks(
    workspace,  # any RepositoryWorkspacePort, e.g. LocalRepositoryWorkspace
    DockerSandbox(
        DockerSandboxConfig(docker_executable, SandboxImage.PYTHON_CHECKS),
        SandboxPolicy(timeout_seconds=180, max_output_bytes=1_048_576),
    ),
    CheckInputPolicy(
        roots=(RepositoryPath("src"), RepositoryPath("tests")),
        files=(RepositoryPath("pyproject.toml"),),
    ),
    CheckPolicy(timeout_seconds=120),
    cancellation,  # optional CancellationSignal bound to this instance
)
```

The composition root must bind `SandboxImage.PYTHON_CHECKS`. The adapter does
not name an image. Instead, its fixed runner checks the exact tool versions
inside the container (pytest 9.1.1, Ruff 0.16.8, mypy 2.3.1), so any other
image yields `UNAVAILABLE`.

### Commands and runner

Host and sandbox use one private command table, `checks/_commands.py`, so the
options are the same:

| Kind | Command |
| --- | --- |
| `PYTEST` | `pytest -q -o addopts= -p no:cacheprovider -- <targets>` |
| `RUFF_CHECK` | `ruff check --no-fix --no-fix-only --no-cache -- <targets>` |
| `RUFF_FORMAT_CHECK` | `ruff format --check --no-cache -- <targets>` |
| `MYPY` | `mypy --no-incremental --cache-dir /dev/null -- <targets>` |

Callers cannot supply a command, executable, argument or environment. Each check
is exactly one sandbox execution of one constant runner script. The runner reads
a data-only spec, runs the tool with `shell=False` and a fixed environment, and
returns a fixed JSON envelope. The outcome derives from the tool's exit code,
as in M5.

### Input policy and limits

`CheckInputPolicy` selects which repository files are copied into the
sandbox:

- `roots`: 1–16 directories, scanned deterministically.
- `files`: 0–16 explicit files.
- `max_scan_entries`: 1–65 536 directory entries.

Only `.py`, `.pyi`, `.toml`, `.cfg`, `.ini` and `py.typed` files are selected.
Hidden components, `__pycache__` and the reserved spec name are excluded.
Every check target must lie within the selection; otherwise the check is refused
with `WorkspaceError(EXCLUDED)`.

The sandbox request allows at most 63 project files, one slot being reserved
for the spec. Each file may be up to 256 KiB, and the total up to about 1 MiB.
Exceeding any of these limits, a workspace read limit, or the scan limit raises
`CheckError(INPUT_LIMIT)`. **Input is never truncated.** Missing or binary
inputs fail closed with the workspace error.

### Failure mapping

The adapter adds four `CheckFailure` members: `CANCELLED`, `RESOURCE_LIMIT`,
`INPUT_LIMIT` and `CONFINEMENT`. They are raised only by the sandboxed adapter;
`LocalEngineeringChecks` never raises them.

| Source | `CheckFailure` |
| --- | --- |
| `SandboxFailure.TIMEOUT`, or the tool exceeds `CheckPolicy.timeout_seconds` | `TIMEOUT` |
| `SandboxFailure.CANCELLED` | `CANCELLED` |
| `SandboxFailure.RESOURCE_LIMIT`, or a cgroup `oom_kill` during the tool run | `RESOURCE_LIMIT` |
| `SandboxFailure.OUTPUT_LIMIT`, or tool output over `CheckPolicy.max_output_bytes` | `OUTPUT_LIMIT` |
| `SandboxFailure.CLEANUP` | `CLEANUP` |
| `SandboxFailure.UNSUPPORTED` | `CONFINEMENT` |
| `SandboxFailure.RUNTIME_UNAVAILABLE` / `ENVIRONMENT_UNAVAILABLE`, or wrong toolchain | `UNAVAILABLE` |
| `SandboxFailure.PREPARATION` / `CONTROL` / `ARTIFACT`, a non-zero runner exit, or a malformed envelope | `IO` |
| Input over the bounds above | `INPUT_LIMIT` |

Test failures, lint findings, format differences and type errors are
`CheckResult` outcomes, not errors. The original `SandboxError` is kept as
`__cause__`.

### Cancellation

A `CancellationSignal` is bound to each instance, because the port is
unchanged. The signal is checked in three places:

- before input acquisition;
- after input acquisition, before dispatch;
- during execution, through the M6 sandbox, which stops and removes the
  container.

Cancellation always surfaces as `CheckError(CANCELLED)` and never as a result.

### Policy pairing

The runner returns tool output base64-encoded in its envelope, so the two
policies must be sized together:

- **Output:** `SandboxPolicy.max_output_bytes` must be at least
  8/3 × `CheckPolicy.max_output_bytes` plus a few KiB.
- **Time:** `SandboxPolicy.timeout_seconds` must exceed
  `CheckPolicy.timeout_seconds` by a margin for container start and teardown.

If these are undersized, the sandbox limit trips first. It is still reported
truthfully (`OUTPUT_LIMIT` or `TIMEOUT`), but less precisely.

### Containment is not result integrity

The sandbox *contains* the code under test: no network, no host filesystem,
fixed resources, and source bytes on the host are never modified. It does not
make the result *trustworthy*. Code under test runs in the same container as
the tool and can influence it, for example by skipping tests, patching
pytest, or exiting early with status 0. A sandboxed `PASSED` means only that
this outcome was observed under containment. It is not evidence that the change
is correct. Where a result must be trusted, it needs independent review
(M8.2) or verification out of band.

### Scope and known limitations

- **Qualified platform:** Windows with the Docker Desktop Linux engine only,
  the same platform as M6 and CR-2a. Other platforms are not qualified.
- **No toolchain choice:** the tools are fixed to the CR-2a image. Project
  plugins, third-party stubs and non-stdlib runtime dependencies are not
  installed. Checks that need them report their real outcome, typically
  `FAILED` or `INTERRUPTED`.
- **Resource profile:** the fixed 128 MiB profile is qualified only for small
  projects; see the CR-2a evidence. `RESOURCE_LIMIT` is a truthful failure.
- **No input identity in results:** `CheckResult` does not yet record which
  inputs were checked (for example a path and digest manifest). This is
  deferred to CR-3 or ForgeAI-1, where results are bound to a reviewed change.

### Local validation required

```powershell
uv run python .\validate_consumer_readiness_cr2b.py
```

This validator uses the recorded CR-2a image ID and never builds or pulls an
image. Each pytest phase uses a fresh `--basetemp`. It runs these phases:

1. The environment and the qualified image are present.
2. Typing, Ruff lint and Ruff format checks pass.
3. Deterministic adapter tests pass: failure contract, input bounds, command
   parity, cancellation and result mapping.
4. Real Docker tests pass: every pytest, Ruff and mypy outcome; timeout,
   output, resource, cancellation and unavailable-toolchain cases; network
   isolation, cleanup and adapter substitution.
5. Regressions pass: M5, M6, CR-2a, architecture, and the wheel with a clean
   install.
6. `git diff --check` passes.

### CR-2b qualification evidence

On 2026-09-29 the maintainer ran `validate_consumer_readiness_cr2b.py` on
Windows with Docker Desktop (context `desktop-linux`, linux/amd64), against the
recorded image `sha256:4c64580306983d70e059f5f133f6bb3f82657c9c61fa96f562f42594f20269df`.
**All 20 phases passed.**

| Area | Result |
| --- | --- |
| Static checks | mypy clean on 76 files plus the validator; Ruff lint and format clean |
| Deterministic adapter tests | 59 passed |
| Real Docker outcomes | 10 passed: pytest pass, fail, collection error and no tests; Ruff check and format, clean and finding; mypy clean and finding |
| Timeout, output, resource, cancellation, unavailable toolchain | 5 passed |
| Network isolation, adapter substitution, M6 confinement | 3 passed |
| M5 regressions (`tests/test_checks.py`) | 40 passed |
| M6 and CR-2a regressions | 58 passed |
| Architecture | 84 passed |
| Wheel and clean install | 1 passed |
| `git diff --check` | clean |

No sandbox containers or volumes remained after any real Docker test.

The CR-2a re-check against the recorded ID, run with a fresh `--basetemp`, also
passed all 16 tests, with no OOM kills. In one run mypy peaked at about 95 MB
on the baseline fixture, against about 67 MB in the other runs. That is still
within the 128 MiB limit, but headroom varies between runs, which reinforces
the resource-profile limitation above.

A separate re-check run without `--basetemp` hit the known Windows temp-root
`PermissionError` after its tests had finished. That is an environment issue,
not a test result.

## CR-3 — authorized engineering effects (locally qualified 2026-09-29)

Two decorators add current authorization in front of the existing effect
Ports, which are unchanged:

- `repository.mutation_authorized.AuthorizedRepositoryMutation` implements
  `RepositoryMutationPort` with action `apply-repository-changes`.
- `checks.authorized.AuthorizedEngineeringChecks` implements
  `EngineeringCheckPort` with action `run-engineering-check`. It works over
  `LocalEngineeringChecks` or `SandboxedEngineeringChecks`.

**Per-call behavior.** Before every call, each wrapper evaluates the operator's
host-issued `SecurityContext` against the `AuthorizationPort` with a fresh
timestamp. It never caches an allow. On denial it raises
`authorization.EffectAuthorizationError` (`DENIED` or `UNAVAILABLE`), and the
inner adapter is never called. Allowed calls reach the inner adapter exactly
once, and its results and errors pass through unchanged, with no retry.

**Composition checks.** Approval-bearing contexts are refused when the wrapper
is constructed, as are contexts for another workspace, action or scope.

**Shared helper.** The ADR-018 check is one private helper,
`legoai_engineering._authority`. It is shared by the read composition and both
wrappers.

**Public read wiring.** The read composition is now public:
- `analyst/_composition` became `analyst/authorized`;
- `coding/_composition` became `coding/authorized`.

The examples, including the new end-to-end `examples/governed_engineering.py`,
import no private modules.

See [docs/CONSUMING.md](docs/CONSUMING.md) for the application guide and the
[ADR-018](../../adrs/ADR-018.md) addendum for the decision. The wrappers need
the `analyst` extra (Core). Check results still do not record which inputs
were checked, and no authorized Git or evidence wrapper exists.

### CR-3 validation

```powershell
uv run python .\validate_consumer_readiness_cr3.py
```

### CR-3 qualification evidence

On 2026-09-29 the maintainer ran `validate_consumer_readiness_cr3.py` on
Windows with Docker Desktop, using the recorded CR-2a image.
**All 20 phases passed.**

| Area | Result |
| --- | --- |
| Static checks | mypy clean on 83 files plus the validator; Ruff lint and format clean |
| Shared helper, mutation and check wrappers | 12 passed |
| Denial-before-effect ordering | 4 passed |
| Expiry, revocation, policy supersession | 3 passed |
| Tenant and workspace scope | 2 passed |
| Approvals fail closed | 1 passed |
| Local and fake-sandbox substitution | 1 passed |
| Real Docker authorized sandboxed check | 2 passed: allowed ran once; denied made zero sandbox calls |
| M4 regressions | 48 passed |
| M5 and CR-2b regressions | 99 passed |
| M8.1–M8.3 regressions | 113 passed |
| Public-import architecture | 106 passed |
| Clean-install consumer proof | 1 passed |
| ForgeAI structural readiness proof | 2 passed |
| `git diff --check` | clean |

This qualifies the authorization wrappers and public wiring for the reference
scope only. It does not change the containment-versus-integrity or
checked-input-identity limitations.
