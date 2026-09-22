# LegoAI engineering foundation

M1: bounded deterministic inspection of caller-supplied repository text.
M1 implementation and local validation complete: 44 tests, typing, lint,
formatting and the example passed. This package does not yet
publish a governed `repo.inspect` capability or acquire live repository data.

The [repository intake example](examples/repository_intake.py) is its first
consumer. It searches explicitly supplied project metadata and produces match
coordinates. Future repository analysis can compose this function behind a
governed acquisition/invocation boundary. No Agent, Model or framework is needed.

## Supported contract

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

No host file access, Git, shell, sandbox, test runner, patching, persistence,
provider invocation, Plugin registration or public runtime facade is included.
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
