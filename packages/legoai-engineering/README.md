# LegoAI engineering foundation

M1: bounded deterministic inspection of caller-supplied repository text.
M1 implementation and local validation complete: 44 tests, typing, lint,
formatting and the example passed. M1 does not publish a governed `repo.inspect`
capability or acquire live repository data.

M2 adds a bounded local workspace adapter below. Its implementation and local
validation are complete for the documented supported scope. M1 remains closed
and its code is unchanged. M3 remains unstarted.

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
isolated Python. No network, Ollama or system Git is needed by the tests.

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
