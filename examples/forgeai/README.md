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
- **ForgeAI v0.2 Developer Preview:** locally qualified by
  `validate_forgeai_v0_2_dp_1.py`, with replay models and real sandboxed checks.
  Live model quality is unqualified.
- **ForgeAI-2** (independent review gate): locally qualified on 2026-09-29.
  Its "CHANGES_REQUIRED stops the run" behavior is superseded by ForgeAI-3's
  single rework.
- **ForgeAI-1** (single task worker without review): locally qualified on
  2026-09-29.
- **ForgeAI v0.1** (supervised local engineering assistant): `forgeai run`
  plus an explicit operator approval before any repository change; see
  "ForgeAI v0.1" below. Locally qualified on 2026-10-08 (`validate_forgeai_v01.py`,
  18/18 phases) with replay models and real sandboxed checks; live-model use is
  unqualified.

## Bounded operator batches (FORGEAI-AUTOPILOT-BATCH-1)

**ADR-028 Proposed; validation pending.** The separate `batch.py` operator tool
runs a finite task list in a disposable standalone clone with its own `.git`
directory and objects, no remotes, and a new `forgeai/batch-*` branch. Only
SUCCEEDED tasks are committed, by the operator tool. Human review and merging
remain separate. The attended Developer Preview below is unchanged.

Review applicable repository guidance before opting in, including any separate
check-confirmation requirements. Policy and task files must be operator-authored.
Explicitly passing `--policy` consents to that fixed policy; no cryptographic
signature or authentication service is claimed. Model text grants no authority.

Example `policy.toml`, outside the output directory:

```toml
max_changed_files = 4
max_total_bytes = 16384
allow_create = true
forbidden_names = ["credentials*"] # extends the mandatory defaults
forbidden_prefixes = ["src/security"]
require_review_accept = true       # false is refused
max_tasks = 4
max_batch_minutes = 60
```

Mandatory forbidden names are `pyproject.toml`, `uv.lock`, `poetry.lock`,
`requirements*.txt`, `setup.py`, `setup.cfg`, `Pipfile`, `Pipfile.lock`,
`package.json`, `package-lock.json`, `Dockerfile`, `.env*`, `.github` paths and
`.gitlab-ci*` paths. Matching is case-insensitive at every depth; extended
basenames support `*`. Prefixes match complete path components. Limits are
1–8 files, 1–24576 UTF-8 payload bytes, 1–20 tasks and 1–480 minutes. CREATE
defaults to false and independent ACCEPT review is mandatory.

Example `tasks.toml` (replay paths resolve relative to this file):

```toml
base = "HEAD"
binding = "replay"
check_profile = "generic"

[[task]]
id = "T1"
objective = "Add input validation and tests."
targets = ["src/inventory/stock.py", "tests/test_stock.py"]
context = []
constraints = ["Keep public signatures unchanged."]
discover_guidance = false
replay = ["proposal.json", "review_accept.json"]
```

Repeat `[[task]]` in execution order with unique ids. `:create` declares a new
target. Replay requires 1–4 responses per task in call order, including rework
when needed. For `binding = "ollama"`, omit `replay` and set top-level
`ollama_model = "qwen2.5-coder:14b"`. Only locally operated Ollama at
`http://127.0.0.1:11434` is supported; forwarding to a remote processor is not
admitted. REMOTE is refused. `check_profile = "project"` selects the existing
qualified project profile; repository guidance cannot select arbitrary commands.

Prerequisites: existing locked Python 3.14 environments, Git, Docker and the
qualified checks image. PROJECT additionally requires the existing uv.exe and
its check-environment prerequisites. The operator repository must be clean and
committed. Output must be new, outside the repository, with an existing parent.
From `examples/forgeai`, when you choose to execute a batch:

```powershell
uv run --locked --offline --no-sync python batch.py --repo C:\work\inventory --tasks C:\batch-inputs\tasks.toml --policy C:\batch-inputs\policy.toml --out-dir C:\batch-results\run1 --json-report
```

The tool resolves the base, clones with `--no-hardlinks --template=`, removes
`origin`, creates the new branch, and verifies HEAD and cleanliness. No operator
repository refs, HEAD, index or working files are written. Context confirmation
requires the exact case-sensitive set of targets and context, plus included
guidance when enabled. Proposal approval binds the exact identity. All existing
mutation authorization, digest, checks, review and one-rework gates remain.

`batch-report.jsonl` contains one S1 report per completed worker run, extended
with `batch_task_id` and `policy_evaluations` (attempt, approval, per-rule results).
`--json-report` also prints those lines. Pre-worker refusals have a summary
reason, not a fabricated S1 report. The final summary lists branch, verified
commits, dispositions and stop reason. Non-success stops without committing that
task. No rollback or cleanup occurs. The deadline prevents new tasks but does
not kill an active task. An interrupted or failed commit/report step can leave
partial effects: inspect HEAD and files. There is no automatic retry or resume.

Review commands are printed with actual paths, base SHA and branch:

```powershell
git -C <out-dir>/workspace log --oneline <base_sha>..HEAD
git -C <out-dir>/workspace diff <base_sha>..HEAD
# Optional human action; never executed by batch.py:
git -C <repo> fetch <out-dir>/workspace forgeai/batch-<id>:forgeai/batch-<id>
```

Delete `<out-dir>` yourself when done. The tool never pushes, fetches, merges,
rebases, resets, deletes branches or removes workspaces. No remotes means no
configured push destination; it does not prohibit a human using an explicit URL.
Local replay/FakeSandbox tests do not qualify live model quality, real Docker
batch execution or clean installation.

Maintainer checks from the repository root, using the existing locked environments
and Git (no additional environment variables, Docker or live model required):

```powershell
git status --short
uv run --locked --offline --no-sync python .\validate_forgeai_autopilot_batch_1.py
git diff --check
git status --short
```

API references for this operator composition:

- [demo.py](demo.py): `git_environment`.
- [cli.py](src/forgeai/cli.py): `ReplayModel`, `replay_binding`, `ollama_binding`, `safe`.
- [composition.py](src/forgeai/composition.py): `local_profile`, `discover_guidance`,
  `sandbox_readiness`, `prepare_run`, `PreparedRun`.
- [domain.py](src/forgeai/domain.py): `TaskRequest`, `ProposalReview`,
  `OperatorDecision`, `proposal_identity`, `TaskDisposition`, `TaskResult`, `CheckProfile`.
- [guard.py](src/forgeai/guard.py): `WorkspaceGuard`;
  [worker.py](src/forgeai/worker.py): `RepositoryTaskWorker.run`.
- [guidance.py](src/forgeai/guidance.py): `GuidanceRefusal`, `guidance_candidates`,
  `guidance_summary`, `GuidanceInventory.included_paths`.
- [repository_context.py](src/forgeai/repository_context.py): `ContextPreflight`, `ContextOutcome`.
- [report.py](src/forgeai/report.py): `ModelBindingKind`, `run_report`, `encode_report`.
- [coding/values.py](../../packages/legoai-engineering/src/legoai_engineering/coding/values.py): `CodingTarget`;
  [repository/workspace.py](../../packages/legoai-engineering/src/legoai_engineering/repository/workspace.py): `RepositoryPath`;
  [repository/mutation.py](../../packages/legoai-engineering/src/legoai_engineering/repository/mutation.py): `FileChangeKind`;
  [sandbox/ports.py](../../packages/legoai-engineering/src/legoai_engineering/sandbox/ports.py): `SandboxExecutionPort` (trusted test seam).

`prepare_run` keywords are `approve`, `confirm_context`, `preflight`, `progress`
and the existing `sandbox` test seam. Its returned worker runs through
`worker.run(task, prepared.context)`. The operator tool `batch.py` sits beside
`demo.py`; the pure INNER policy is installed as `forgeai.policy`. Existing
package modules remain unchanged; module inventories add only `policy`.

## ForgeAI v0.2 Developer Preview

### What it is

An attended, supervised, single-repository, single-task coding worker. It is
not an unattended or commercial coding agent, and it is not a hosted service.
This DP packages the existing bounded workflow; it adds no new capability.

### Quickstart (5 minutes, replay model, real Docker checks)

Prerequisites: Windows, Docker Desktop with its Linux engine running and the
already-qualified `PYTHON_CHECKS` image available locally, Git, and uv. Use the
existing locked development environments and cached dependencies; these commands
do not install missing dependencies or build/pull the checks image. The five-minute
estimate assumes those prerequisites are ready.

From the repository root:

```powershell
cd examples/forgeai
uv run --locked --offline --no-sync python demo.py accept --discover-guidance --json-report
```

The demo creates a temporary, committed fixture repository. Guidance discovery
is limited to that repository; it does not read guidance from the ForgeAI checkout.
The stock fixture has no candidate guidance files, so `NOT_PRESENT` is expected.
First, `Confirm this required repository context? [y/N]` asks you to confirm the
listed inventory. This does not approve mutation. Next, `Apply this proposal?
[y/N]` asks you to approve the exact displayed patch; answer `y` only after
reviewing it. Declining either prompt stops the run. Successful output includes
three passed sandbox checks, an accepted review, `disposition: succeeded`, and
a final `forgeai-report:` JSON line with `model_quality: NOT_APPLICABLE_REPLAY`.
CRLF files retain their line endings; the preview labels hidden CRLF terminators
and shows the substantive changes. The temporary demo repository is removed when
the demo exits.

### Using it on your repository

With ForgeAI available in your existing environment, a clean committed Python
repository, and the named model already installed in a running local Ollama:

```powershell
forgeai run --repo C:\work\inventory --task "Reject non-positive reservation requests and add tests" --target src/inventory/stock.py --target tests/test_stock.py --context docs/conventions.md --discover-guidance --json-report --binding ollama --ollama-model qwen2.5-coder:7b
```

Replace the paths, task and model with your own. Explicit context must exist and
fit the documented bounds. The operator selects every target and explicit context
file; discovery adds bounded read-only guidance only when requested. Guidance
discovery stays opt-in. Live model quality is **UNQUALIFIED**; the preview and
identity-bound approval are the controls. Checks and review can both miss defects.

### Feature summary

| Feature | Behavior |
|---|---|
| Context confirmation | Confirm the exact required repository inventory before the model proceeds. |
| Guidance discovery | Opt-in, bounded ancestor guidance as read-only context; local bindings only. |
| Exact patch preview | Digest-bound before text and full bounded diff, with labeled CRLF handling. |
| Identity-bound approval | Only approval of this exact changeset permits mutation. |
| Sandboxed Ruff/mypy/pytest | Configured checks run in the qualified Docker sandbox. |
| Independent review | A distinct reviewer Agent definition evaluates the checked candidate; this is model opinion, not proof. |
| One rework | At most one correction after code findings or a review requesting changes; fresh confirmation and approval required. |
| Machine-readable report | `--json-report` emits the bounded `forgeai-run-report/1` result. |

### Model status

Replay is qualified for demonstration by the prior local slice evidence. Ollama
and remote OpenAI-compatible bindings work mechanically, but their model quality
is **UNQUALIFIED**. No KiSSKI model is currently admitted: the pilot's `ADMISSIONS`
tuple is empty. `--discover-guidance` is refused with the remote binding.
The consolidated gate uses replay or local synthetic responses, never a live model.

### Known limitations / behaviour

- The qualified platform scope is Windows + Docker Desktop, with Python layouts
  using `src/`, `tests/` and `pyproject.toml`.
- There are 1–8 operator-chosen targets; there is no target discovery.
- Guidance discovery reads candidate files before the Docker and Git checks.
  Nothing is disclosed to a model or written by those reads.
- `NOT_PRESENT` also covers unreadable files.
- With --discover-guidance, the run reuses the discovery host and its operator
  grants, so one operator authority (one expiry window) covers both the guidance
  reads and the coding run.
- The guidance summary is printed before the run header.
- There is no commit, push or rollback. Applied changes remain in the working tree
  on failure; the operator inspects them and decides what to retain.
- A run produces at most two proposals.
- Historical evaluation harness tests under `evaluation/tests` have known
  pre-existing failures tracked as `FORGEAI-EVAL-HARNESS-TRIAGE-1`. They are not
  part of DP qualification.

### DP qualification

From the repository root, on Windows with Docker Desktop running and the pinned
image and all build/install dependencies already available locally:

```powershell
uv run --locked --offline --no-sync python .\validate_forgeai_v0_2_dp_1.py
```

The gate first checks scope, preservation, offline product tests, strict typing,
lint, formatting and whitespace. On Windows it then checks Docker metadata,
real integration and offline clean installation, the dedicated real-sandbox
qualification selectors, and the accept/rework demos. Real phases require
executed passing tests; skips do not qualify. Clean-install cache misses stop the
gate; network access is not enabled. Acceptance demos receive two `y` answers
for accept and four for rework, matching context confirmation plus mutation
approval on each attempt. Their final replay reports are checked and printed.

Only a successful Windows run establishes the consolidated DP qualification:

```text
FORGEAI-V0.2-DP LOCALLY QUALIFIED; REPLAY MODELS AND REAL SANDBOXED CHECKS; MODEL QUALITY UNQUALIFIED; NO LIVE MODEL EXECUTION
```

Other operating systems stop after the offline phases and print:

```text
REAL PHASES NOT RUN (requires Windows Docker Desktop)
FORGEAI-V0.2-DP OFFLINE CHECKS PASSED; REAL PHASES NOT RUN; NOT QUALIFIED
```

**Consolidated verification: PASSED — maintainer-supplied Windows results.**
The gate reported 555 offline product tests passed (11 deselected), clean typing,
lint, formatting, scope, preservation and whitespace checks; 6 real end-to-end
and offline clean-install tests passed; 5 real-Docker regressions passed; and
the dedicated real-sandbox selectors passed 1 success, 1 check-triggered rework
and 4 negative controls. Both acceptance demos reported `SUCCEEDED`, with replay
model quality and the expected rework flags. No live model quality is qualified.

## ForgeAI v0.1: supervised local engineering assistant

**Scope.** v0.1 is deliberately small. You get:
- one local Git repository and one task per run;
- targets that you choose, and that the model can never add to;
- the existing reviewed flow with at most one rework.

It does **not** include target discovery, the Repository Analyst or
sufficiency agents, general secret management, Git commit/push/PR, durable resume, or hosted
use.

**Supported repositories.** The built-in profile checks a Python repository
laid out as `src/` + `tests/` + `pyproject.toml`. It runs Ruff (`src`,
`tests`), mypy (`src`) and pytest (`tests`) in the qualified Docker checks
image. Other layouts are not supported yet.

**Prerequisites** (Windows + Docker Desktop is the qualified scope):
- Git;
- Docker Desktop (Linux engine) with the CR-2a `PYTHON_CHECKS` image built
  locally;
- `uv`;
- for local live use, Ollama with a coding model; alternatively, the explicitly
  configured REMOTE profile below (live remote model quality is unqualified).

## Explicit remote model profile

FORGEAI-REMOTE-MODEL-PROFILE-1 keeps ForgeAI and its repository/checks local.
Model execution can use LegoAI's existing OpenAI-compatible REMOTE binding.
Provider, HTTPS endpoint and exact model are configuration; compute location
does not change task, Coding Agent, Reviewer or check semantics. Both
`--check-profile generic` and `--check-profile project` work independently.

```powershell
forgeai run --repo C:\work\repo --task "Describe one bounded change" --target src/example.py --binding openai-compatible-remote --remote-profile C:\operator\remote.toml --remote-custody C:\operator\forgeai-custody --check-profile generic
```

The custody directory must already exist outside the target repository and be
owned/protected by the operator. Do not share it between concurrent processes.
Credentials enter only through S1 hidden interactive provisioning, anew per
process, and the source is closed on exit. There is no credential flag,
environment, file or pipe fallback. The CLI uses the system TLS trust store;
trusted test composition supplies its synthetic CA. No insecure-TLS option or
automatic discovery is exposed.

`remote.toml` is limited to 16 KiB and exactly the fields below. This
**illustrative, non-runnable policy** asserts nothing about any real provider.
Replace every fact with an explicit operator attestation grounded in the
intended service's conditions; choose a current window of at most one hour:

```toml
provider = "operator-selected-provider"
base_url = "https://models.example.invalid/v1"
model = "exact-model-id"
repository = "operator-repository-identity"
revision = "policy-r1"
basis = "operator_attested"
processor = "Operator-attested processor name"
locations = ["Operator-attested jurisdiction"]
retention_days = 0
training = "no"
human_access = "none"
subprocessors = ["Operator-attested subprocessor name"]
not_before = 2026-10-10T12:00:00Z
not_after = 2026-10-10T12:30:00Z
```

These values construct existing processor facts and matching class conditions;
unknown mandatory facts fail closed. The CLI schema supports operator
attestations, bounded retention and named subprocessors. It never fetches or
verifies provider policies. No credential, header, source or command belongs in
this file. Revise the policy when facts change.

After guarded repository validation and any PROJECT preparation, ForgeAI
previews provider/model/origin/root, exact target/context paths, task digest,
fixed instructions, possible rework diagnostics and Reviewer material. Only
`y` or `yes` approves remote disclosure; default is No. Mutation has its own
later patch preview and approval. Declining disclosure produces no model call,
mutation approval, checks or rework.

Approval is single-run, bound to the immutable task (including constraints,
target operations and context), endpoint, model and policy. Every run has a
fresh configuration revision. The existing vocabulary admits the **ForgeAI
application consumer**, purpose `chat`, for both Agents: Core permits one
admission per binding. This is not a Coding-only admission reused for review.
Every invocation is independently gated and declared: initial Coding sends
PLATFORM_INSTRUCTION, TASK_TEXT and REPOSITORY_CONTENT; Reviewer and rework
also declare DERIVED_DIAGNOSTIC. Read-only context goes to Coding only.

Core owns durable attempt custody, current per-invocation Secret use and
verified HTTPS/T2. One attempt per Agent invocation, no retry/fallback, UNKNOWN
preservation and strict JSON decoding remain unchanged. The reference host has
no explicit close operation; custody handles follow its lifetime. S1 material
is explicitly closed by the CLI.

Qualification uses synthetic local TLS, including real Docker REMOTE + GENERIC
and REMOTE + PROJECT. The latter performs one labelled PyPI wheel acquisition;
checks remain offline. No Internet model provider is contacted:

```powershell
uv run python .\validate_forgeai_remote_model_profile_1.py
```

Agent-run qualification on 2026-10-10 passed the complete validator: 86 ForgeAI
profile/architecture tests, 509 REMOTE/security regressions, 274 LOCAL model/Agent
regressions, 252 Core architecture tests, 278 Engineering tests, both real Docker
REMOTE combinations, all static checks and every historical v0.1 validator phase
(including clean installation and both replay demos). Phase counts overlap.
The final run acquired one locked dependency wheel through the existing PROJECT
preparation; model traffic went only to synthetic local TLS. No live model
provider or real user-repository pilot was used.

The supplied maintainer transcript on 2026-10-10 also passed every validator
phase, including both real Docker REMOTE combinations and the complete historical
v0.1 validator, ending with `FORGEAI REMOTE MODEL PROFILE LOCAL VALIDATION PASSED`.
FORGEAI-REMOTE-MODEL-PROFILE-1 is therefore **LOCALLY QUALIFIED** for synthetic
local TLS, with explicit PyPI preparation and offline checks. This evidence is
separate from historical M6 and v0.1 qualification. No named GPU platform,
notebook deployment, ComfyUI,
production credential management, arbitrary OpenAI compatibility or live
remote model quality is qualified.

The [HF named-provider preflight](../../docs/hf-inference-compatibility.md) now
has GET discovery and bounded backend observations implemented by
PROVIDER-MODEL-DISCOVERY-2, locally qualified on 2026-10-10 at
`c7353ccf180a54effbf2e80a048e8ae4b8197dc8` (maintainer: 1,156 tests passed,
2 deselected, typing/lint/format/whitespace passed). The harness is **SYNTHETIC
LIVE-PROBE READY** after processor-identity review, with the readiness gate enabled;
focused closeout checks remain operator-run and pending. Separate live authorization
is required. No provider call has occurred, HF compatibility remains unqualified,
and no repository disclosure is authorized. The earlier 1,044-test record remains
the historical blocked preflight only.

## Local setup and task execution

**Setup:**

```powershell
cd examples/forgeai
uv sync --locked
ollama pull qwen2.5-coder:7b   # or any installed model; see --ollama-model
ollama serve                   # if not already running
```

**Run a task.** Start from a committed, clean working tree. Run from
`examples/forgeai`. From the repository root, add `--project
examples/forgeai` (`uv run --project examples/forgeai forgeai run ...`): the
root project does not install the `forgeai` command.

```powershell
uv run forgeai run `
    --repo C:\path\to\repo `
    --task "Reject negative quantities in reserve() and test it" `
    --target src/inventory/stock.py `
    --target tests/test_stock.py
```

- Give 1-8 `--target` paths, relative to the repository. A target is
  updated by default; write `PATH:create` for a new file.
- Add `--constraint TEXT` (up to 8) for extra instructions.
- Add `--context PATH` (up to 8) for existing files the Coding Agent may
  **read but never edit**. See "Read-only context" below.
- Model options: `--ollama-model`, `--ollama-url` (default
  `http://127.0.0.1:11434`) and `--ollama-timeout`.
- `--binding replay --replay FILE ...` uses recorded outputs instead of a
  live model.
- The older form `forgeai <repo> --objective ... --target ...` still works
  and also asks for approval.

**Read-only context.** `--target` is write scope. `--context` is disclosure
only: the listed files are sent to the Coding Agent as repository data, so
it can follow the project's imports, APIs, typing, test style and
configuration. Use it when the targets alone don't show the conventions,
typically when every target is `:create`:

```powershell
uv run forgeai run `
    --repo C:\path\to\repo `
    --task "Add restock(available, received) with tests" `
    --target src/inventory/restock.py:create `
    --target tests/test_restock.py:create `
    --context pyproject.toml `
    --context src/inventory/stock.py `
    --context tests/test_stock.py
```

- **Never write scope.** A proposal that changes a context-only file is
  rejected (`PATH_OUT_OF_SCOPE`) before approval, with nothing written.
  Editable scope comes from `--target` alone. A path can't be both a target
  and context; that is refused at startup.
- **You choose every file.** ForgeAI never searches, globs, follows imports
  or adds sibling files, and model or review output can never add one.
- **Bounds** (fail closed, never truncated): up to 8 files, 8192 bytes per
  file, 16384 bytes in total, and the Coding Agent's existing 32768-byte
  input limit for targets plus context together.
- **Path rules.** Paths are repository-relative. Absolute paths, `..`, hidden
  components such as `.env`, duplicates and case aliases are refused before
  anything runs. Files are read through the same authorized repository read
  boundary as targets, so workspace policy exclusions apply. A missing file,
  a directory or an oversized file rejects the run before the model is
  called, with an `evidence:` line explaining why.
- **Data, not instructions.** Context is framed as read-only data. Text
  inside it that looks like an instruction grants nothing. That's a prompt
  framing, not a guarantee about what a model does with it, so the patch
  preview and approval stay the control.
- **Both attempts, Coding Agent only.** A rework sees the same context. The
  independent reviewer does not receive it and reviews only the changed
  files.

**What you see:**
1. **Before any model call:** the repository, task, editable targets, the
   read-only context (listed separately and marked `read-only`),
   constraints, checks and model.
2. **Startup failures** stop here with a clear message: missing repository,
   not a Git repository, invalid target or context path, Ollama unreachable
   or model not installed, or no Git/Docker executable. A repository with no
   commit or with uncommitted changes is rejected before the model is
   called.
3. **Docker readiness**, checked before the scope is shown and before any
   model call. It uses the Engineering sandbox's metadata-only preflight:
   `docker info`, then `docker image inspect` of the pinned checks image. A
   not-ready sandbox refuses the run with `startup refused: ...` and one next
   action, exit code `2`. Nothing is called, written, checked or reviewed.
   - Docker CLI missing, or the Docker Desktop Linux engine unreachable: start
     Docker Desktop (Linux containers).
   - Qualified checks image absent: build it from
     `sandbox-images/python-checks` (CR-2a).
   - Required sandbox controls missing: use the Desktop Linux engine.

   ForgeAI never starts Docker and never pulls or builds images. Ready means
   only "ready right now". Checks can still fail later and are reported
   normally.
4. **Progress lines:** `[1/7] Repository verified`, `[2/7] Proposal
   generated`, `[3/7] Waiting for approval`, `[4/7] Changes applied`,
   `[5/7] Checks completed`, `[6/7] Review completed` and `[7/7] Final
   result`. A rework is announced with `[rework]`.
5. **The proposal**, before anything is written: a short proposal id, each
   changed path with create/update and its size, the per-file reason, the
   summary, risks and unknowns, and then **the exact patch**.
   - The patch is a unified diff of the proposed content against the
     current text the proposal was based on, bounded by
     `--- proposed patch ---` and `--- end of patch ---`. It is rendered in
     memory: no file read, no Git command, no write.
   - Its "before" side is verified against the same content digest the
     mutation precondition enforces, and approval is bound to the shown
     proposal id. What you see is exactly what will be written.
   - Control and bidirectional-text characters in proposed code are shown
     as `\uXXXX` escapes. They can't move the cursor, recolor or reorder
     the screen.
   - Only the whole patch is ever shown. If it exceeds 800 diff lines or
     96 KiB, ForgeAI prints `PREVIEW EXCEEDS DISPLAY BOUND`, does not ask,
     and declines. A change you can't fully see is never applied.

   Read the patch before answering. The checks and the reviewer can both
   miss weak code. In the first live pilot, tests that could never fail
   passed every check and were accepted by the 7B reviewer.

### Line endings

For UPDATE targets whose current text consistently uses CRLF, ForgeAI converts
LF-only proposals to CRLF before computing approval identity. Preview, approval,
mutation and evidence all use that same proposal, including on rework. CREATE,
LF or mixed current text, lone CR, and proposals already containing CR are left
unchanged. If conversion exceeds a file or aggregate proposal bound, the entire
original proposal is retained; nothing is truncated.

When both versions consistently use CRLF, the patch hides the CR terminators
and states `line endings: CRLF (both versions; not shown per line)` directly
under the file header. Mixed endings and lone or embedded CR remain escaped.
LF previews and the existing display bounds are unchanged.

**Approval.** Then comes `Apply this proposal? [y/N]`:
- Only `y` or `yes` applies the proposal. Anything else, an empty answer,
  EOF (closed or empty stdin) or Ctrl+C declines.
- A declined proposal writes **nothing** and runs no checks and no review.
- There is no automatic approval, and no `--yes` flag.
- Approval is bound to the exact change set shown. Approving one proposal
  can never apply a different one, and the existing content preconditions
  still refuse a file that changed in the meantime.
- A rework proposal needs its own approval: `Rework proposal (attempt 2,
  id …)`, the reason, the exact feedback the Coding Agent received, the full
  patch, then `Apply this rework proposal? [y/N]`.

**One bounded rework.** A run has at most two proposals. It gets one rework,
triggered by exactly one of these:
- **The attempt-1 checks reported code findings.** Every configured check
  completed, and each one that didn't pass is `failed` (the tool ran and
  found problems). The Coding Agent gets a bounded excerpt of those checks'
  own output as data: location-bearing lines such as `file.py:14` plus the
  message line before each, at most about 1 KB per check, with a note of any
  lines left out. It gets the same task and the same targets, and it reads
  the *current* candidate files, so the preconditions bind to candidate 1.
  Its new proposal is shown and approved like any other, applied through the
  same authorized mutation, and all checks run again. Candidate 1 is never
  reviewed. If the checks pass, the reviewer reviews candidate 2 once. If
  the reviewer then requires changes, the run stops: the budget is spent.
- **Review #1 required changes**, after all attempt-1 checks passed. This
  is unchanged from ForgeAI-3.

There is never a third proposal. ForgeAI never runs `ruff --fix` or any
other auto-fix, and changes code only through approved proposals.

A proposal that changes nothing is refused before approval, with its claimed fix
shown as unverified; earlier approved changes remain in the working tree.

A check that **could not complete** is never "repaired" by the model:
Docker or sandbox failure, timeout, a tool error, interrupted pytest
collection, or no tests collected. The run stops. A check finding can't
widen the scope either: a rework proposal touching a file outside your
targets is rejected.

**Final result.** The final block lists:
- the disposition and reason;
- run id, starting HEAD and attempt count;
- changed files and each check result;
- the review decision, findings and blocking-finding count;
- risks and unknowns;
- whether HEAD is unchanged;
- a `git -C <repo> diff -- <files>` command for inspecting the change.

No model is used to summarize.

**Invalid model output.** If the Coding Agent or the reviewer returns output
that fails its contract, the result names why. For example:

```
review output invalid:
  reason: REQUIRED_FIELD_MISSING (a required field is missing)
  field: findings[0].required_action
  no retry or repair was attempted; raw output is not shown
```

- **Reasons** are a closed set from the Engineering parsers:
  - `OUTPUT_CONTRACT`, `JSON_DOCUMENT_INVALID`;
  - `DUPLICATE_FIELD`, `REQUIRED_FIELD_MISSING`, `UNKNOWN_FIELD`,
    `FIELD_TYPE_INVALID`, `ARRAY_BOUNDS_EXCEEDED`, `ENUM_INVALID`;
  - `PATH_INVALID`, `PATH_OUT_OF_SCOPE`, `VALUE_INVALID`,
    `FINDING_REFERENCE_INVALID`.
- **The field** is a schema locator, such as `changes[1].reason`. It is
  never model text.
- **Raw model output and prompts are never printed or kept.** The failure is
  unchanged: invalid coding output stops the run with nothing written, and
  invalid review output stops it without retry or rework. Changes already
  applied remain, as the warning says.

**Failures.** There is no retry, no fallback and no rollback. If a run fails
after changes were applied (checks, review, or a declined rework), the result
says so with `WARNING: changes remain in the working tree` and lists the
files. ForgeAI never commits, resets, stashes or cleans. Exit codes: `0`
succeeded, `2` rejected before any model call, `1` everything else.

**Live pilot evidence** (same customers repository, task and targets):
- `qwen2.5-coder:7b`, ×2: correct guard but **vacuous** tests, which pass
  even without the guard. One review ACCEPTed them; one review output was
  invalid.
- `qwen2.5-coder:14b`, ×2: correct guard and **meaningful** tests (they
  fail without the guard), but written with `assert False`, which the
  repository's Ruff rules reject (B011). Without a rework the run stopped at
  checks. That's the case the check-feedback rework now handles: one
  supervised correction, still approved by you. On this machine Ollama ran
  CPU-only, so 14B needed `--ollama-timeout 1200`.

Neither model is qualified by these observations. 14B being better than 7B
is not a qualification.

A later 14B run on a task whose targets were all `:create` produced code that
ignored the repository's conventions: package import path, strict typing and
test isolation. With only new files as targets, the Coding Agent had seen no
existing code. That motivated `--context`. It makes the conventions
available; it does not make a model follow them.

**Known v0.1 limits.**
- Live-model quality is **unqualified**; only replay runs are qualified.
- The rework gets a bounded excerpt of check output. A finding that needs
  more context, or a file outside the targets, may not be fixable within one
  rework.
- Docker readiness is a point-in-time check. If Docker stops after
  startup, the check step fails after the approved changes were written,
  and the warning lists them.
- Startup checks the Ollama model list only, not the model's quality.

## Workflow

This describes the **current v0.1 behavior**. ForgeAI-3, the historical
behavior qualified on 2026-09-29, differed in two ways: it applied proposals
without operator approval, and only review #1 `CHANGES_REQUIRED` could
trigger the rework.

`RepositoryTaskWorker.run(task, context)` claims the workspace, checks the
initial Git state, and then runs **attempt 1**. It runs **attempt 2**, the
single rework, only when attempt 1 consumed the one rework budget, in exactly
one of two ways:
- attempt 1's checks completed and reported code findings; or
- they passed and review #1 completed with `CHANGES_REQUIRED`.

There is never an attempt 3.

1. **Claim the workspace.** The in-process `WorkspaceGuard` refuses a second
   concurrent run on the same repository. The guard stays held for the whole
   run, including any rework.
2. **Observe Git.** The repository must have a commit and no changes, not even
   untracked files. Otherwise the run is rejected. ForgeAI never stashes,
   resets, cleans, checks out or commits.
3. **Attempt**, run once, or twice when a rework happens:
   1. **Propose.** Call `CodingAgent.propose` once. It authorizes and reads the
      **current** content of the targets, then makes one governed model call.
   2. **Approve.** Show the exact bounded patch and ask the operator. Only an
      explicit `y` for this exact proposal identity continues; anything else
      stops with nothing written.
   3. **Apply** through `AuthorizedRepositoryMutation`. Current authority and
      digest preconditions are checked immediately before the write.
   4. **Check.** Run the full configured plan in order (Ruff check, mypy,
      pytest) through `AuthorizedEngineeringChecks` over
      `SandboxedEngineeringChecks`. There is no host fallback.
   5. **Observe Git.** HEAD must be unchanged, and the working-tree changes
      must equal the union of the paths applied so far.
   6. **On attempt 1 only:** if every check completed and the only failures
      are code findings (`FAILED`), start the check-feedback rework and skip
      the review of this candidate. Any other check failure is terminal.
   7. **Review**, only if steps 1–5 all passed. Re-read the final content of
      every changed file through `AuthorizedRepositoryEvidence`, verify it
      against the applied digests, render deterministic material, mint a
      fresh Chat context, and call the unchanged `IndependentReviewer` once.
      On attempt 1, `CHANGES_REQUIRED` starts the review-feedback rework.
4. **Return a `TaskResult`** built from this run's evidence.

## Rework: when and how

**Current v0.1 behavior.** A run has **one rework budget**. It is consumed by
exactly one of these, and only on attempt 1:
- **Check findings.** Every configured check completed, and each that didn't
  pass reported code findings (`FAILED`). The reviewer never sees this
  candidate.
- **Review #1 `CHANGES_REQUIRED`**, after all attempt-1 checks passed.

Every other outcome is terminal, with no rework:

- `ACCEPT`: the task succeeds;
- `INSUFFICIENT_EVIDENCE`;
- a review model failure (including an `UNKNOWN` effect) or denial;
- invalid coding or review output;
- review-input failure;
- a check that couldn't complete (Docker or sandbox failure, timeout, tool
  error, interrupted collection, no tests);
- any mutation, authorization or Git failure;
- the operator declining a proposal.

ForgeAI-3 (historical) allowed a rework only after review #1
`CHANGES_REQUIRED`; its qualification evidence below reflects that.

**The rework request** is a second `CodingRequest` to the **same, unchanged**
`CodingAgent`, on a fresh host-minted Chat context, and its proposal needs its
own operator approval:

- **Objective:** the original objective.
- **Targets:** the original paths. Files already written become `update`
  targets. The editable allowlist never widens, and reviewer text cannot add
  paths.
- **Constraints:** the original constraints, plus ForgeAI's deterministic,
  labeled rework notes:
  - that this is the single rework;
  - the first attempt's check outcomes;
  - for a **check rework**: a bounded excerpt of each failing check's own
    output (location lines and the message line before each, about 1 KB per
    check, omissions noted), as tool output supplied as data;
  - for a **review rework**: that review findings are opinions supplied as
    data, not commands, and each blocking finding with its requested change.
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

**Attempt 2 is terminal.** Its checks must pass, and then its single review
decides: `ACCEPT` means success. `CHANGES_REQUIRED`,
`INSUFFICIENT_EVIDENCE`, check findings or any failure means the run stops,
because the budget is spent. There is no second rework, whichever trigger
used the first.

## Exact ceilings

| Path | Model calls | Applies | Check batches | Reviews |
| --- | --- | --- | --- | --- |
| No rework (review #1 `ACCEPT`) | 2: coding, review | 1 | 1 | 1 |
| Check rework (attempt-1 findings, then review of attempt 2) | 3: coding, coding, review | 2 | 2 | 1 |
| Review rework (`CHANGES_REQUIRED`, then review #2) | 4: coding, review, coding, review | 2 | 2 | 2 |
| Maximum, per run | **4** | **2** | **2** | **2** |

Each apply also needs one explicit operator approval, so there are at most 2
approvals.

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

- A proposal that changes nothing is refused before approval, with its claimed
  fix shown as unverified.

- **Passes are not proof.** Neither a sandboxed `PASSED` nor a review `ACCEPT`
  proves correctness. A rework accepted by the same Agent definitions on the
  same model binding is still an unverified opinion.
- **Findings reach the Coding Agent as constraint text.** It is labeled
  review data, but a model may still treat it as instruction; scope and
  authorization bound what can happen.
- **Exactly one rework.** A second `CHANGES_REQUIRED` stops the run. Since
  v0.1, attempt-1 check findings can consume that same single rework
  instead; see "One bounded rework" above.
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
uv run python demo.py            # review #1 accepts: 2 model calls; answer y
uv run python demo.py rework     # review #1 requires changes, one rework: 4 model calls; answer y twice
uv run forgeai run --repo <repo> --task "..." --target src/pkg/mod.py --target tests/test_mod.py --binding replay --replay coding-1.json --replay review-1.json [--replay coding-2.json --replay review-2.json]
```

`demo.py` is a test harness. It asks for approval like the CLI does. It commits the fixture into a temporary
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

### Explicit project check profile (PROJECT v1)

`forgeai run --check-profile generic` remains the default historical fixed
checks image. `--check-profile project` explicitly authorizes a separate trusted
dependency-preparation operation before any Coding Agent, approval or mutation.
Preparation may acquire packages from PyPI; Ruff, mypy and pytest subsequently
run with Docker networking disabled and the unchanged check plan.

The first supported shape is a committed clean Python repository with `src/`,
`tests/`, static `[project]` metadata, `requires-python` compatible with the base
image's actual CPython **3.14.7**, and an up-to-date **uv.lock**. Runtime dependencies
and the optional `dev` dependency group are selected. uv **0.11.19** is required
on PATH. The host Python must also satisfy uv's locked-export compatibility check.
No target project install or build backend is executed. Only hashed binary wheels
from PyPI are acquired. Source-only packages, local/Git/URL dependencies, workspaces,
extras, other groups, custom uv configuration (except `package=false`), conflicting
base-tool dependencies and startup `.pth` hooks are unsupported. Other custom tool
tables and repository Dockerfiles/setup scripts supply no preparation commands.

Existing workspace limits apply to both metadata files: at most **65,536 text
characters**, at most 262,144 bytes; the manifest has a further 65,536-byte bound.
Existing check-input limits and the 128 MiB execution sandbox remain unchanged.
Projects requiring external services, additional pytest plugin selection or
different check commands are not qualified by this profile.

```powershell
forgeai run --repo C:\path\to\supported-project --task "Describe one bounded change" --target src/example.py --check-profile project
```

Preflight prints the profile, metadata presence, bounded Python requirement,
preparation status, abbreviated prepared image ID and offline check plan. The
workspace guard covers preparation and all subsequent work. Preparation rejection
has no proposal, approval, mutation, check batch, review or rework budget use;
the operator sees a closed preparation reason or sandbox infrastructure reason.
Actual code findings retain the existing single approved rework semantics.

The prepared image is derived locally from the exact qualified checks base.
The target checkout is never a build context. The immutable image ID selects
execution; no image-string CLI option exists. Prepared images remain local,
are not committed to this repository, and are not automatically reused on later
runs. The operator can remove a reported image ID with Docker when no longer needed.
This is bounded local qualification, not arbitrary-package safety, reproducible
builds generally or production supply-chain security.

Focused qualification (one explicitly labelled PyPI wheel-acquisition phase,
then offline checks; replay models only):

```powershell
uv run python .\validate_forgeai_project_check_profile_1.py
```

The fixture at `fixtures/project_checks` uses the existing ecosystem's small
`idna==3.20` dependency. GENERIC cannot import it; PROJECT must pass all three
checks, preserve base tool executable hashes and expose only loopback networking.
The focused validator also runs the full existing v0.1 regression validator.
Historical M6/CR-2 qualification does not cover PROJECT; its evidence is separate.

Agent-run qualification on 2026-10-10 passed the complete focused validator on
Windows/Docker Desktop: 278 Engineering tests, 17 ForgeAI profile tests, one real
dependency-preparation test, 106 Core composition regressions, affected static
checks, and every phase of the unchanged v0.1 validator (including clean install
and both replay demos). These phase counts overlap with historical regressions.
The qualified derived image was
`sha256:287e84039478daa135062674ccd1aff423ac8320b2f2fcebac9261d12e6bf033`.
Preparation acquired the locked wheel from PyPI; checks had only loopback
networking. No live model or real user-repository pilot was run.

The maintainer subsequently supplied a complete successful rerun transcript on
2026-10-10, confirming all the phases above and the final
`PROJECT CHECK PROFILE LOCAL VALIDATION PASSED` result. Its prepared image was
`sha256:1dc9678f8cfe2d29a8fa22b8ca9d81fd5bd572f8b1b35fe332479294b7d5e2cc`.
This closes the pending maintainer local-validation gate for this bounded profile;
real-project pilot and live-model qualification remain separate.

From the repository root, on Windows with Docker Desktop and the CR-2a image
present:

```powershell
uv run python .\validate_forgeai_v01.py   # v0.1 (pipes an explicit "y" to the demos)
uv run python .\validate_forgeai_3.py     # historical; its demo phases now prompt for approval
```

The v0.1 validator's phase 2/2b scope audits compare the original commits
`3993320..03d2c6eda0e74793f68720f36b0a5033edf7e2e1`. They establish the scope
of that historical slice, not the scope of later committed or uncommitted work.
Both commits must be available locally. All static checks, regression tests
and Docker demos run against the current checkout; later platform changes are
not rejected merely for falling outside the original slice's file allowlist.

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


## Provider interoperability before repository work

`FORGEAI-FREE-GPU-MODEL-PROVIDER-1` provides a separate read-only entry point:
`python -m forgeai.provider_cli`. It constructs no CodingAgent, mutation adapter,
Git adapter or sandbox. No fallback, retry, proxy configuration or tunnel is added.

Kaggle is one infrastructure environment with user-supplied successful runtime
qualification for Qwen/Qwen2.5-Coder-14B-Instruct-AWQ (Python 3.12, torch
2.7.0+cu128, transformers 4.51.3, vLLM 0.9.2, two Tesla T4s). ForgeAI depends only
on the OpenAI-compatible contract. A **separately available endpoint is required**;
a notebook is not assumed remotely reachable or an always-on service. This slice
has not contacted that runtime or qualified a live endpoint.

The typed `ProviderProfile` configuration shape is:

```text
provider_type = openai_compatible
base_url = exact versioned API root (maximum 512 characters)
model = exact model identifier (maximum 256 characters)
mode = local | remote
provider = operator-assigned ProviderId
timeout = 1..300 seconds (default 60)
auth_mode = none (local) | secret_source (remote)
disclosure_policy = None | existing RemoteDisclosureConfig
custody_policy = None | existing absolute directory outside repository
```

Local mode requires a loopback **IP literal**, avoiding DNS rebinding. There is no
credential input. The server is an explicitly trusted local process. From this
ForgeAI directory, with a separately running server:

```powershell
uv run --locked --offline --no-sync python -m forgeai.provider_cli --mode local --base-url http://127.0.0.1:8000/v1 --provider local-vllm --model Qwen/Qwen2.5-Coder-14B-Instruct-AWQ
```

`uv --offline` controls dependency resolution; it does not prohibit this explicitly
requested endpoint call. The command makes at most three fixed synthetic requests:
READY, exact JSON `{"status":"ready"}`, and `def add(a: int, b: int) -> int: return a + b` (AST checked,
never executed). Temperature zero, no streaming and max_tokens=512 are requested.
The existing adapter verifies the exact response model and finish_reason=stop.
The local transport caps bodies at 1 MiB; application output is capped at 4096
UTF-8 bytes. No result implies model quality or reproducibility. JSON is a prompted
behavioral check; native schema-constrained generation remains unsupported.

To request one file summary **after** those three checks pass, add:

```powershell
--repository D:\absolute\repository --repository-id my-repository --target src/example.py
```

A separate interactive approval names the actual repository, target, endpoint and
model. Only that file is read (maximum 16 KiB UTF-8); links/reparse points and
excluded paths fail closed. No listings, implicit context or recursive reads occur.
The operator must select source suitable for disclosure; this is not a secret
scanner. Output is untrusted text, never an instruction to execute or apply changes.

Remote mode additionally requires `--policy path/to/remote-policy.toml` and
`--custody C:/absolute/existing/custody`, uses HTTPS and the existing hidden
interactive Secret-source provision. Use the existing documented remote profile
TOML shape; endpoint/model/provider must exactly match the CLI. The synthetic-only
invocation loads a SYNTHETIC admission. When a target is explicitly configured,
the declared repository policy is also loaded, but the separate per-file approval
is still required after synthetic success. Neither a credential nor endpoint
approval permits repository disclosure. The existing host re-evaluates disclosure
at every invocation and retains its existing Secret/attempt/disclosure custody.
Never put a token in arguments, environment, profile files or chat.

Evidence returned to the operator consists of bounded check names, safe typed
failure and (for a summary) response SHA-256. Response text is not written to
custody. No automatic retry occurs, even for 429/503 or uncertain transport effects.
Failure facts distinguish endpoint unavailable, explicit model unavailable,
protocol incompatible, request rejected, disclosure not approved, response invalid,
timeout and provider execution failure. HTTP 404 alone cannot prove a missing
model: only a bounded explicit model-not-found code does. Missing observations
remain provider execution failure; effect extent remains the governed execution's.

Local HTTP socket timeouts do not guarantee hard cancellation of an in-flight
worker thread. Remote transport retains its existing absolute deadline/framing
constraints. A timeout is never proof that a provider did not execute the request.

From the repository root, run the supplied offline validation script:

```powershell
uv run --locked --offline --no-sync python .\validate_forgeai_free_gpu_model_provider_1.py
if ($LASTEXITCODE -ne 0) { throw 'Provider slice validation failed' }
# Includes legacy full ForgeAI tests; requires the existing qualified Docker setup:
uv run --locked --offline --no-sync python .\validate_forgeai_free_gpu_model_provider_1.py --full
if ($LASTEXITCODE -ne 0) { throw 'Full provider regression failed' }
```

See [ADR-025](../../adrs/ADR-025.md) for the minimal settings/diagnostic additions.
Mutation remains a later slice requiring synthetic, read-only and disclosure
qualification evidence. No live execution is authorized by these offline checks.


### Provider slice closeout contract

Canonical prompts below match the supplied Kaggle 1G prompt fixtures. Production
ForgeAI does not import that experiment. Test-only identity assertions prevent drift.

<!-- provider-synthetic:ready -->
```text
Return exactly the word READY.
```

<!-- provider-synthetic:json -->
```text
Return only this exact JSON object: {"status":"ready"}. Do not use Markdown or code fences. Do not add explanation, prose, whitespace lines, or any other text.
```

<!-- provider-synthetic:add -->
```text
Return only valid Python source code. Define exactly one function:
def add(a: int, b: int) -> int:
    return a + b
Do not use Markdown code fences. Do not include imports, comments, explanation, examples, or additional code.
```

READY accepts only exact `READY` (no whitespace normalization). JSON accepts exactly
the semantic object `{"status":"ready"}` with no duplicate keys or extra fields;
uppercase `READY` is rejected. ADD requires AST equivalence to:

```python
def add(a: int, b: int) -> int:
    return a + b
```

No fence stripping, prose extraction, output repair, retry or fallback occurs.
ADD source is parsed, never executed.

**Structured-output decision A:** this slice remains a generic prompted-behavior
check. Kaggle 1G additionally sent `response_format={"type":"json_object"}` for
JSON; ForgeAI sends no response_format. Its existing public schema contract is
not a JSON-object-mode switch, and the generic OpenAI-compatible binding does not
advertise schema support. No new public contract or Core change is introduced
for closeout. Kaggle evidence therefore does **not** qualify the exact ForgeAI
wire request. ADR-025 and its deterministic defaults/effect semantics are unchanged.

User-supplied live evidence records FREE-GPU-MODEL-RUNTIME-KAGGLE-1G as
`KAGGLE_RUNTIME_PASS`: Qwen/Qwen2.5-Coder-14B-Instruct-AWQ at revision
`eb3172f06a6d6b3a15f08947b0668d782e4d2d2c`, AWQ 4-bit, Python 3.12.3,
torch 2.7.0+cu128, transformers 4.51.3, vLLM 0.9.2, two Tesla T4 GPUs,
tensor_parallel_size=2; READY/JSON/ADD all PASS. This is infrastructure evidence,
not a reachable Windows endpoint or ForgeAI-to-Kaggle interoperability result.

Full closeout uses the same validator with `--full`. It requires Docker Desktop
Linux and the existing pinned checks image. Missing Docker is an environment
blocker; a new Docker functional failure stops validation for classification.
Full mode includes Engineering, clean-install/package checks, historical ForgeAI
and explicitly enabled real-Docker remote fixtures. Live model tests remain
unauthorized. The next slice, only after closeout, is research-only
`KAGGLE-FORGEAI-INTEGRATION-OPTIONS-1`; mutation is not next.


## Machine-readable run report (Developer Preview)

Add `--json-report` to either CLI form to append one final stdout line:
`forgeai-report: {JSON}`. The schema is `forgeai-run-report/1`. For example,
from `examples/forgeai`, with the existing qualified Docker checks image:

```powershell
uv run --locked --offline --no-sync python demo.py accept --json-report
uv run --locked --offline --no-sync python demo.py rework --json-report
```

The flag is opt-in; existing human output and exit codes are unchanged. No
report file is written. Operators can redirect stdout and select the line
beginning with `forgeai-report: `; preceding human output is not JSON and is
not subject to the report's data exclusions. Startup refusals before a
`TaskResult` exists produce no report line. Successful, failed and rejected
task results can all produce reports. JSON uses sorted keys, ASCII escaping
and compact separators, with a 65,536-byte UTF-8 limit excluding the prefix
and line terminator. If exceeded, the final line is exactly
`forgeai-report: REPORT_UNAVAILABLE (bound exceeded)`; the exit code is unchanged.

| Top-level field | Meaning |
| --- | --- |
| `schema` | Always `forgeai-run-report/1`. |
| `run_id` | Existing run identifier. |
| `disposition` | `TaskDisposition` name: `SUCCEEDED`, `REJECTED` or `FAILED`. |
| `failure` | Existing `TaskFailure` name, or `null`. |
| `model_binding` | `REPLAY`, `OLLAMA` or `OPENAI_COMPATIBLE_REMOTE`. |
| `model_quality` | `NOT_APPLICABLE_REPLAY` for replay; otherwise `UNQUALIFIED`. |
| `start_head` | Full starting commit ID, or `null` if unavailable. |
| `context_confirmed` | Recorded context-confirmation boolean. |
| `rework_used` | Whether the single rework was used. |
| `rework_trigger` | Existing trigger enum name, or `null`. |
| `changes_retained` | Whether any attempt recorded an applied mutation result, exactly as in the pilot projection. |
| `repository_effect` | `UNKNOWN` if any attempt has an uncertain mutation path; otherwise `KNOWN` if any has an applied result; otherwise `NONE`. |
| `rollback_performed` | Always `false`; reporting performs no rollback. |
| `attempts` | Ordered attempt objects described below. |
| `limitations` | Existing fixed evidence-limitations strings. |

| Attempt field | Meaning |
| --- | --- |
| `number` | Attempt number (1 or 2). |
| `coding_status` | Coding status enum name, or `null`. |
| `model_attempt` | Coding agent execution status enum name, or `null`. |
| `model_effect` | Coding model effect enum name, or `null`. |
| `proposal_valid` | Whether a validated proposal exists. |
| `mutation_approval` | `true`/`false` for the operator's decision; `null` if not asked. |
| `changed_paths` | Applied changes only: objects with repository-relative `path` and change-kind enum name `kind`; empty if not applied. |
| `mutation_uncertain` | Whether an uncertain mutation path was recorded. |
| `mutation_denied` | Whether mutation authorization was denied. |
| `mutation_conflict` | Whether a mutation precondition conflict was recorded. |
| `checks` | Objects with check-kind name `kind`, outcome name or `null` in `outcome`, and boolean `no_result`. |
| `review_status` | Reviewer status enum name, or `null` if no review result. |
| `review_decision` | Review decision enum name, or `null` if unavailable. |
| `blocking_findings` | Count of blocking findings; `null` if no parsed review is available. |

Reports never include objectives, task text, constraints, file contents, diffs,
proposal text or summaries, risks, unknowns, reviewer finding text, prompts,
model output, absolute/host paths, endpoint URLs, model names, remote profile
values, custody paths, credentials, environment values or exception messages.
Only explicit evidence fields are projected; evidence is never serialized wholesale.

Model quality is always `UNQUALIFIED` or `NOT_APPLICABLE_REPLAY`. There is no
`QUALIFIED` value and no input override. No live model is admitted by this slice;
DeepSeek, GLM and qwen3-coder-next remain unqualified. A successful replay or
task report does not qualify a model. For a fixed result and binding, encoding
is deterministic; separate runs retain their distinct run identifiers.

Maintainer validation from the repository root, using existing locked Python
3.14 environments with Git, uv, pytest, mypy and Ruff already installed:

```powershell
uv run --locked --offline --no-sync python .\validate_forgeai_dp_run_report_1.py
```

The validator clears `VIRTUAL_ENV` and `LEGOAI_QUALIFY_*`, sets `UV_OFFLINE=1`
and `PYTHONDONTWRITEBYTECODE=1`, and runs no installation or live model phase.
The maintainer-approved offline regression selection uses default testpaths
but excludes the historical end-to-end, clean-install and two LQ1 Docker test
modules, plus tests matching `real_docker` or `real_sandbox`. It prints these
exclusions and preserves pytest's skip/deselection summary. This is not full
integration qualification. The unchanged clean-install test also has an exact
module inventory that needs a separate scope-approved addition for `report.py`.
The strict scope phase rejects every untracked file outside this slice,
including unrelated local planning documents; preserve or relocate those
separately before running it. Validation status: **NOT RUN — Awaiting user execution**.

## Discovered repository guidance (Developer Preview)

Opt in with `--discover-guidance` on either CLI form, or pass it after the
demo scenario, for example `python demo.py accept --discover-guidance --json-report`.
The flag is supported for replay and Ollama bindings only. Combining it with
the remote binding is refused during argument handling, before file reads,
credential provisioning or host opening. Without the flag, the existing flow,
output and reads are unchanged.

Discovery computes exact paths from editable targets; it does not scan directories.
It deduplicates target ancestor directories case-insensitively, orders them by
depth and then path, and considers:

1. `AGENTS.md` in each ancestor, repository root first.
2. `CLAUDE.md` in each ancestor, repository root first.
3. Root `CONTRIBUTING.md`.
4. Root `README.md`.

Targets and explicit `--context` choices win: matching candidate paths are removed
case-insensitively. Hidden components are not allowed. Discovery performs no globbing,
recursive search, symlink following or traversal of links, ADRs or contracts mentioned
inside guidance text. It considers at most 16 candidates, keeping metadata entries
for the remainder as `NOT_CONSIDERED_LIMIT` without reading them.

Each candidate is read through its own **single-path authorized reader** with
`allowed_paths=(path,)`. Readers are constructed lazily in priority order, sharing
one independent local discovery host, workspace, reference, read security context,
authorization and clock. **Authorization is evaluated per read** by the existing
Engineering adapter, including its release check for successful acquisitions.
Discovery uses the existing operator grants; it mints none, calls no model and
performs no mutation or sandbox work. The normal task subsequently opens its own
host and retains the original grants and expiry when merging context.

The guidance inventory holds relative paths, closed statuses, observed UTF-8 sizes
and content digests only. Acquired text is discarded after computing metadata;
it is never cached or put into the summary. Existing operator context is measured
through authorized reads to account for the shared byte budget. If all eight
reference slots are already occupied, guidance is excluded without any discovery
reads. Required operator context is still checked by the existing task preflight.

| Status | Meaning |
| --- | --- |
| `INCLUDED` | Entire file fits: at most 8,192 bytes per file, four guidance files and 12,288 guidance bytes; combined operator context plus guidance stays within eight references and 16,384 bytes. |
| `NOT_PRESENT` | Acquisition returned `UNAVAILABLE`. The platform deliberately uses this for both missing and unreadable files; it does not prove absence. |
| `EXCEEDS_FILE_BOUND` | Observed size exceeds 8,192 bytes, or acquisition returned `BUDGET`; unavailable sizes/digests remain unknown. |
| `EXCLUDED_BUDGET` | File cannot fit the remaining budget, or a count/byte budget is exhausted. No truncation or summarization is performed. |
| `NOT_CONSIDERED_LIMIT` | Candidate is beyond the first 16 and was not read. |

Once a guidance or combined reference budget is exhausted, later candidates within
the cap are marked `EXCLUDED_BUDGET` without reader construction or reads. A file
whose observed size does not fit is excluded whole; if budget remains, a later
smaller file can still fit. Reaching the 16-candidate cap takes precedence for
the remainder. Selection is deterministic, but does not prove that all necessary
guidance fits or that instructions are semantically complete or consistent.

`DENIED`, `BOUNDARY` and unexpected errors stop discovery immediately; no later
reader is constructed. The CLI exits 2 with
`startup refused: guidance discovery <REASON>; no model was called and nothing was written`.
Exception text is never printed. Closed additional refusal reasons cover unsupported
bindings and unavailable or over-budget required operator context. No `TaskResult`
exists at this point, so `--json-report` emits no result line for these refusals.

On successful discovery, the header is
`repository guidance: discovered (read-only; confirm below)` followed by metadata
for every candidate. Included paths are appended to `TaskRequest.context` in
priority order. They remain **repository data**, never targets, constraints, system
instructions or authority. The existing context preflight reacquires the files and
lists them as references for operator confirmation; the existing stale-context and
proposal validation boundaries still apply. A proposal editing discovered guidance
is rejected `PATH_OUT_OF_SCOPE`. Discovery metadata is not a reusable snapshot or
permission to disclose content, and guidance cannot change grants or checks.

The discovery summary and `forgeai-run-report/1` line never contain guidance text.
The report schema is unchanged; it continues to report replay quality as
`NOT_APPLICABLE_REPLAY` and live binding quality as `UNQUALIFIED`.

From the repository root, using the existing locked Python 3.14 environments,
Git, uv and installed development dependencies, the maintainer runs:

```powershell
git status --short
uv run --locked --offline --no-sync python .\validate_forgeai_dp_guidance_preflight_1.py
git diff --check
git status --short
```

The validator retains the S1 environment sanitization, import paths, explicit Ruff
configuration and product-only offline selection. Its focused regression phase also
uses the existing `not real_docker and not real_sandbox` selection because the
selected context module contains a Windows real-sandbox test. Historical
`evaluation/tests` remain excluded, with pre-existing failures tracked separately
as `FORGEAI-EVAL-HARNESS-TRIAGE-1`. Real-Docker and clean-install checks remain
separate maintainer gates. No environment variables need setting, no dependencies
are installed, and no live-model qualification is claimed.

Verification: **NOT RUN — Awaiting user execution**.

## Repository context preflight

Before coding, ForgeAI now inspects the explicit targets and `--context` files
through their existing authorized reader. Missing, out-of-scope or oversized
required context stops before coding with bounded preflight evidence. CREATE
requires verified absence; supporting context is required when declared.

`READY_FOR_CONTEXT_CONFIRMATION` shows relative paths, roles, byte counts and
digests, not contents. Confirming this inventory is separate from remote model
disclosure and later proposal approval. Without an explicit confirmation, no
CodingAgent or IndependentReviewer is called. Programmatic `prepare_run` callers
must supply `confirm_context`; its default refuses. Each decision is bound to
the repository root/HEAD, run/tenant, exact task/scope and inventory digests.
The worker re-acquires authorized evidence immediately before coding, rejects
stale bindings, and hands that exact immutable bundle to CodingAgent. Rework
requires fresh preflight and confirmation. Confirmation grants no remote
disclosure or mutation permission. This does not certify semantic completeness
or qualify a model.

See [the preflight slice](../../planning/FORGEAI-REPOSITORY-CONTEXT-PREFLIGHT-1.md)
for bounds and limitations. The preflight maintainer validation passed.
The [confirmation slice](../../planning/FORGEAI-CONTEXT-CONFIRMATION-1.md)
passed its separate maintainer validator. This qualifies the local confirmation
boundary, not model quality or deployment.

The follow-up `FORGEAI-V0.2-BOUNDED-TASK-QUALIFICATION-1` combines the confirmed
context, coding, mutation approval, checks, independent review and bounded rework
gates in deterministic lifecycle tests. Its validator uses replay models and a
fake sandbox, alongside existing offline regressions. Real sandbox execution,
live model quality and global v0.2 qualification are outside that claim.
The maintainer supplied a successful result for this replay/fake-sandbox validator:

```powershell
uv run --locked --offline --no-sync python .\validate_forgeai_v0_2_bounded_task_qualification_1.py
if ($LASTEXITCODE -ne 0) { throw 'ForgeAI v0.2 bounded-task qualification failed' }
```

Run from the repository root with the existing locked environments. See the
[qualification record](../../planning/FORGEAI-CONTEXT-CONFIRMATION-1.md#follow-up-forgeai-v02-bounded-task-qualification-1)
for the exact coverage and limits.

The bounded-task maintainer validator has now passed with replay models and a
fake sandbox. The separately requested
[real-sandbox qualification](../../planning/FORGEAI-V0.2-REAL-SANDBOX-QUALIFICATION-1.md)
is pending. It uses the existing GENERIC PYTHON_CHECKS Docker image and replay
models, with no provider calls, image acquisition or dependency installation.
On the qualified Windows Docker Desktop Linux host, from the repository root:

```powershell
uv run --locked --offline --no-sync python .\validate_forgeai_v0_2_real_sandbox_qualification_1.py
if ($LASTEXITCODE -ne 0) { throw 'ForgeAI v0.2 real-sandbox qualification failed' }
```

This command runs real Docker workloads only when executed by the maintainer.
The pinned qualified image must already be present. Success would qualify the
bounded replay workflow with real checks, not live model quality or deployment.
