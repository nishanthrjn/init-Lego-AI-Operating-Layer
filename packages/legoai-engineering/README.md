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
trusted-local scope. M6 is unstarted.
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
