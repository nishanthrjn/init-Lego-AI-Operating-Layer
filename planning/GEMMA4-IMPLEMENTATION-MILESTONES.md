# Gemma 4 implementation milestones

Status: PROPOSED; M1 PARTIAL; ALL EXECUTION REQUIRES MAINTAINER AUTHORIZATION.
NO LIVE EXECUTION OR SUBMISSION AUTHORIZED.

All dates below are internal targets, not organizer requirements. See the sourced
requirements register for official indexed deadlines and revalidation blockers.
No milestone pass is inferred from this documentary validator. Maintainer gates
require pasted results and artifact identity before dependent work proceeds.

| Milestone / target | Scope and dependencies | Acceptance and tests | Evidence, risk and maintainer gate |
| --- | --- | --- | --- |
| M1 Verified requirements / Oct 20 | Resolve R1–R7 for both tracks; acquire authorized official README/starter/schema snapshots without installing; no predecessor | Every tool/input/output/budget and entry/submission rule traceable; source-conflict review and missing-field negative checks | URL/date/version/hash register and rule checklist; risk inaccessible/stale docs. Maintainer confirms official artifacts and requirements before M2. |
| M2 Minimum valid submission / Oct 23 | M1; single-agent declarative starter, minimal prompt, no graph/LoRA; competition-local packaging | Official config/package validation and one authorized synthetic/public-task end-to-end run; bad model/tool/path config rejected, patch handoff evidenced | Archive/hash, pinned harness/model, safe logs and outcome; risk unknown schemas/resource incompatibility. Maintainer separately authorizes checks/model run and confirms actual accepted artifact. |
| M3 Baseline benchmark / Oct 26 | M2; independent fixtures and frozen train/dev/eval partition; plain Gemma B0 | Oracle and defective-baseline checks, leakage audit, matched-budget ledger, all tasks accounted including timeouts | Frozen protocol, per-task results and costs; risk weak fixtures or compute shortfall. Maintainer accepts benchmark validity and baseline before optimization. |
| M4 Graph/context / Oct 30 | M3; bounded syntax-only index and retrieval, provenance and stale detection | Symbol/import edge fixtures, unresolved/dynamic edges, byte/node/depth caps, instruction applicability, malicious text/path controls; paired dev retrieval ablation | Graph/version hashes, relevance metrics and overhead; risk graph noise/index cost. Maintainer requires benefit or retains lexical baseline. |
| M5 Controlled patch/test loop / Nov 2 | M2/M3; M4 only if useful; fixed repair/budget policy and official tools | Fail-closed paths, changed snapshots, test/environment failure distinction, timeout/cancellation, duplicate action and budget exhaustion tests; paired dev loop ablation | Effect/result traces and patch hashes; risk wasting budget or confusing tool success with task success. Maintainer validates deterministic boundaries and authorizes any live experiment separately. |
| M6 Ablation/failure analysis / Nov 6 | M3–M5; freeze selected system before locked evaluation | Paired arms, independent review fixture labels, matched total budgets, all-task denominators, uncertainty intervals and null results | Reproducible tables, failure taxonomy and contamination statement; risk small sample/p-hacking. Maintainer signs off defensible claims before paper. |
| M7 Optional LoRA / decision by Oct 27 | M3 dev evidence and M1 permission; parallel optional branch, never on critical path | Data-rights/split audit; no-adapter control; official adapter compatibility; dev gain under equal costs; one frozen held-out evaluation | Adapter/data/config hashes and resource costs; risk training time and leakage. Maintainer authorizes training independently or records OMITTED. Any included adapter must finish M6 before M8. |
| M8 Paper Track / draft Nov 8, submit target Nov 10 | M6; M7 only if completed; M1 paper rules | Reproduce tables, verify word count/citations/public links, redact restricted assets, distinguish proposed from measured, verify submitted-not-draft receipt | Paper/writeup version, evidence bundle and receipt; risk short deadline. Maintainer reviews and explicitly authorizes publication/submission; agent does not submit. |
| M9 Final leaderboard / freeze Nov 27, target Nov 30 | M2/M6 and M1 current rules; entry completed by verified deadline | Official final archive checks, clean rerun on permitted cohort, limits/runtime accounting, no hidden-data leakage; confirm selected final entry | Immutable archive/config/model hashes, scoring receipt and rollback artifact; risk queues/rule changes. Maintainer separately authorizes final upload and selection. |

Paper and final-entry deadlines differ: do not serialize paper preparation after
the final leaderboard run. Reserve a paper buffer; if M4/M7 slip, submit only
supported baseline/ablation findings. Do not sacrifice valid M2/M3 for training.
If M1 remains blocked, pause implementation instead of inventing tool signatures.

## Validation responsibilities

Agent may author future source/tests only when requested. Maintainer runs all
tests, official harness commands, models, Docker, builds and training. Each
future slice supplies exact version-grounded commands after M1; placeholders here
are deliberately not executable guessed official CLI syntax. Separate actions
cover data acquisition, rules acceptance, compute, publication and submission.
Production ForgeAI exact context confirmation and authorized mutation remain.

## Current slice documentary command

Working directory: repository root. Existing locked Python environment; no new
environment variables, credentials or dependencies. No network or provider use.

```powershell
uv run --locked --offline --no-sync python .\validate_forgeai_gemma4_competition_readiness_1.py
if ($LASTEXITCODE -ne 0) { throw 'Gemma 4 competition planning validation failed' }
```

Expected: local document checks passed; M1 partial; official harness/rules review
required; no implementation, live execution or submission authorized.
Verification: NOT RUN — Awaiting maintainer execution.

## M1 follow-up gate

The readiness documentary gate passed per maintainer transcript. The
[official-contract register](../experiments/gemma4_competition/OFFICIAL-CONTRACT-REGISTER.md)
keeps every R1–R7 blocker open or partial. No executable competition agent is
authorized until artifact reconciliation closes M1. The four-variant announcement
changes model-selection planning, not package qualification. M2 remains one root
agent, one model, official tools, no subagents/LoRA/custom graph extensions.

## Official artifact reconciliation — 2026-10-18

Current decision: M1_PARTIAL_ADDITIONAL_ARTIFACTS_REQUIRED; M2 BLOCKED.
The [official contract register](../experiments/gemma4_competition/OFFICIAL-CONTRACT-REGISTER.md)
contains the authoritative reconciliation and conditional minimal M2 specification.
The source register pins all 23 supplied files by raw SHA256 and byte size.
Earlier statements that no local artifacts/rules were inspected describe the
previous review, not the current evidence. Both complete rules captures, notebook
source and sample configuration have now been inspected without execution.
HARNESS_README, package/compiler/tool source and scorer limits remain unavailable.
Notebook model allowlisting is not package enforcement. R1–R7 remain open/partial;
paper generic leaderboard terms versus judged-Writeup requirements require
clarification. M1 is not complete; no dependent M2 implementation is authorized.
The single-root, no-LoRA baseline remains the smallest proposed implementation.
Graph library demonstrations do not prove graph-tool contract or measured benefit;
research comparisons remain matched-budget, independent and unexecuted.

The previous official-harness documentary validation passed per maintainer output.
New reconciliation verification: NOT RUN — Awaiting maintainer execution.
Run from repository root, existing locked environment, no new environment variables:

```powershell
uv run --locked --offline --no-sync python .\validate_forgeai_gemma4_official_artifact_reconciliation_1.py
if ($LASTEXITCODE -ne 0) { throw 'Gemma 4 official artifact reconciliation failed' }
```

Expected: local document checks passed; M1 partial; M2 blocked.
NO IMPLEMENTATION, LIVE EXECUTION OR SUBMISSION AUTHORIZED.

## Harness artifact acquisition gate — 2026-10-18

FORGEAI-GEMMA4-HARNESS-ARTIFACT-ACQUISITION-1:
M1_PARTIAL_ADDITIONAL_ARTIFACTS_REQUIRED; main-competition M2 BLOCKED.
The maintainer's preceding 23-artifact reconciliation passed. No new README,
compiler/tool package or lifecycle evidence was found in the supplied docs tree.
See the acquisition matrix, R1–R7 dispositions, exact conditional M2 file plan
and minimal three-item acquisition request in
[OFFICIAL-CONTRACT-REGISTER.md](../experiments/gemma4_competition/OFFICIAL-CONTRACT-REGISTER.md).
Sample shapes/defaults and notebook observations are not package guarantees.
Persistence and submit_patch termination remain UNKNOWN; do not implement them
from generic ADK behavior. Paper C2 remains separate; main R2–R6 independently
block M2. Product interfaces, KiSSKI custody, evaluator and admissions are unchanged.

Next step is static official-artifact acquisition/review, not an agent/model run.
Existing offline validator extended; no separate harness or tests duplicated.
Working directory: repository root; existing locked uv environment and Git;
no new dependencies, environment variables or credentials required.

```powershell
uv run --locked --offline --no-sync python .\validate_forgeai_gemma4_official_artifact_reconciliation_1.py
if ($LASTEXITCODE -ne 0) { throw 'Gemma 4 harness artifact acquisition validation failed' }
```

Expected: FORGEAI-GEMMA4-HARNESS-ARTIFACT-ACQUISITION-1 LOCAL DOCUMENT CHECKS PASSED;
M1_PARTIAL_ADDITIONAL_ARTIFACTS_REQUIRED; M2 BLOCKED.
Verification: NOT RUN — Awaiting maintainer execution.
NO IMPLEMENTATION, LIVE EXECUTION OR SUBMISSION AUTHORIZED.

### README supplied after initial acquisition inventory

HARNESS_README.md is now inspected and pinned: 24 artifacts total. Its documented
schema, tools, lifecycle, persistence, patch capture and budgets are reconciled
in the official register. Earlier statements of README absence are historical.
Package source parity remains unverified; C3 include traversal, C4 protected patch
handling and C5 size-boundary discrepancies are recorded. M1 remains PARTIAL;
M2 BLOCKED. Supply matching package source/version evidence and resolution of
those discrepancies; do not reacquire the README. The same manual command above
now covers the README pin and updated documentary controls. NOT RUN — Awaiting
maintainer execution. No implementation, live execution or submission authorized.

## Versioned implementation inspection — 2026-10-18

FORGEAI-GEMMA4-VERSIONED-HARNESS-IMPLEMENTATION-1:
M1_PARTIAL_ADDITIONAL_ARTIFACTS_REQUIRED; main M2 BLOCKED.
Prior acquisition documentary gate passed per maintainer transcript. Supplied
41 wheels bring inventory to 65 artifacts. Compiler 0.2.13, core 0.1.0 and
swegemma 0.2.11 source were statically inspected; originals preserved. C3–C5 are
resolved for those bytes in the official register, with release parity still
unconfirmed. Main blocking evidence is now scripts/inference.py, scripts/metric.py,
referenced scorer/bootstrap configuration and release/environment provenance.
Paper discrepancy is separate, not a main-track block. No new agent or runtime
qualification is claimed; existing isolated minimal M2 spec remains conditional.

Run from repository root in the existing locked environment (Git required;
no new environment variables, credentials, installs or network):

```powershell
uv run --locked --offline --no-sync python .\validate_forgeai_gemma4_official_artifact_reconciliation_1.py
if ($LASTEXITCODE -ne 0) { throw 'Gemma 4 versioned harness evidence validation failed' }
```

Expected: FORGEAI-GEMMA4-VERSIONED-HARNESS-IMPLEMENTATION-1 LOCAL DOCUMENT CHECKS PASSED;
M1 PARTIAL; M2 BLOCKED. Verification: NOT RUN — Awaiting maintainer execution.
NO IMPLEMENTATION, LIVE EXECUTION OR SUBMISSION AUTHORIZED.

## Scorer entry-point decision — 2026-10-18

M1_PARTIAL_M2_BASELINE_CONDITIONALLY_UNBLOCKED.
The current official register supersedes the earlier blanket M2 block for
single-root candidate construction and offline official validation only.
Use the exact 31B baseline, six tools and four-file configuration specified there.
Public ZIP handoff and pinned compiler suffice for that limited scope; hidden
scorer source availability is unestablished and is not a required acquisition.
No hidden parity, leaderboard correctness, quality or runtime isolation claim.
M1 remains partial; later smoke needs public setup/environment evidence and
separate authorization. No agent is implemented in this documentary slice.

Maintainer command (repository root, existing locked environment and Git;
no new environment variables or credentials):

```powershell
uv run --locked --offline --no-sync python .\validate_forgeai_gemma4_official_artifact_reconciliation_1.py
if ($LASTEXITCODE -ne 0) { throw 'Gemma 4 scorer entry-point reconciliation failed' }
```

Expected: scorer reconciliation local document checks pass; conditional baseline
unblocking only. NOT RUN — Awaiting maintainer execution. M2 implementation awaits
this result and a separate request; live execution and submission are not authorized.

## M2 minimal baseline authoring — 2026-10-18

FORGEAI-GEMMA4-M2-MINIMAL-BASELINE-1: M2_BASELINE_SOURCE_PREPARED.
Verification: **NOT RUN — Awaiting maintainer execution.** The preceding
documentary gate passed per the maintainer's supplied output. This separately
requested slice authors a candidate and offline controls; it does not establish
official compilation, runtime isolation, task success or Kaggle acceptance.
M1 remains partial. No live model execution or submission is authorized.

Baseline Git commit: `a4cfd4282c3d0ea885554cb9a5159cdb115b44bc`.
Scope is four new candidate files, one root validator, one focused standard-library
test module and this milestone update. Existing registers, official samples and
wheels, production ForgeAI/LegoAI, KiSSKI custody, frozen evaluation and empty
pilot admissions are preserved. No dependency or lock changes.

Candidate (also the exact ZIP member layout, without `baseline/` prefix):

```text
experiments/gemma4_competition/baseline/
  agent.yaml
  prompts/system.md
  configs/sampling.yaml
  eval_config.yaml
```

One `LlmAgent`, `forgeai_gemma4_baseline`, uses
`gemma-4-31b-it-qat-w4a16-ct` and exactly run_command, read_file, edit_file,
write_file, get_status, submit_patch. Root instruction and generation config use
the verified `!include` syntax. Sampling stays temperature 0.2, top_p 0.95,
max_output_tokens 16384, thinking_budget 4096, include_thoughts true. Evaluation
stays timeout_seconds 60, max_tool_calls 10, max_time_minutes 1, max_turns 50.
The instruction is copied exactly from the latest official contract register;
the validator derives its expected text from that preserved record. Prompt
policy does not itself enforce security, protected-file handling or tool effects.

### Static source basis and validation design

Pinned adk-submission 0.2.13 `schema.py`, `yaml_loader.py`, `registry.py`,
`compiler.py`, `context.py` and `builders/llm.py` supply the actual field,
include, registry and constructor contracts. Its `resolvers/generation.py`
constructs Google generation types and applies the library's LiteLLM reasoning
patch; it is not bypassed. swegemma 0.2.11 `config.build_submission_limits`
supplies actual limits/constraints; importing it also imports package runtime
dependencies, even though no evaluator or sandbox is constructed. adk-eval-core
0.1.0 remains a pinned dependency. Raw wheel hashes are checked against the
unchanged source register; installed Python sources and METADATA of these three
packages must exactly match the supplied wheels before imports.

The official gate calls `validate_directory` and full `compile_submission` with
closed registries and the real generation types. Its injected agent constructor
captures resolved values and its inert model/tool objects refuse invocation.
This validates compilation with offline factories, not a live ADK agent or the
hidden scoring factory. The child receives an empty home and a minimal environment;
Python audit hooks refuse network/process effects and common credential-file
reads. These guards are defense in depth for trusted pinned packages, not a
general OS sandbox against arbitrary native code. No external output or raw
exception is printed; failures expose bounded categories. Import-time effects
or unavailable imports stop validation, never trigger installation or fallback.

Positive controls: exact canonical files (LF/CRLF equivalent), include resolution,
compiled identity/prompt/model/tools/sampling, stable ZIP bytes independent of
dictionary order, archive reinspection and SHA256 manifest. Package bytes use LF,
ZIP_STORED, lexical member order, 1980 timestamp, Unix regular-file 0644 modes,
no extra members, and a local cap below 1 MiB (well below the official 3 GiB).
Artifacts are written exclusively into a newly created temporary directory after
compiler success. Historical custody is never an output destination.

Official compiler negative controls use isolated copies: unknown field, unknown
tool, unregistered model, output 32769 and parent-directory include escape.
Separate baseline-policy controls cover those plus missing agent.yaml, links,
disallowed/extra files, adapters/subagent declarations, budget drift, mixed-model
extra roots, unsafe ZIP paths and an enclosing archive directory. No claim that
the official compiler rejects every configuration excluded by this narrower
baseline. The symlink test requires host permission to create a temporary symlink;
it fails rather than silently skips when unavailable. No source fixture is edited.
All controls remain unexecuted by the coding agent.

### Maintainer execution and environment gate

Working directory: repository root. Prerequisites: Git on PATH, Python >=3.12,
readable preserved wheel bytes, temporary-directory write access and permission
to create a temporary file symlink (Windows Developer Mode or equivalent existing
host policy). No credentials or additional environment variables are required.
The existing project Python 3.14 environment has no declared Kaggle dependencies;
an environment-blocked result is expected if they are absent.

```powershell
uv run --locked --offline --no-sync python .\validate_forgeai_gemma4_m2_minimal_baseline_1.py
if ($LASTEXITCODE -ne 0) { throw 'Gemma 4 M2 baseline validation failed or environment blocked' }
```

This runs the focused standard-library tests, then the guarded official compiler
in the same interpreter, then packages only after success. To run only the focused
policy tests separately (this does not qualify the compiler or package):

```powershell
uv run --locked --offline --no-sync python -B -m unittest discover -s experiments/gemma4_competition/tests -p test_m2_minimal_baseline.py
if ($LASTEXITCODE -ne 0) { throw 'Gemma 4 M2 offline policy controls failed' }
```

If a separate environment is needed, its provisioning is a later explicit
maintainer decision; this validator installs nothing. It must contain the exact
supplied adk-submission 0.2.13, adk-eval-core 0.1.0 and swegemma 0.2.11 bytes,
google-adk 1.36.1, google-genai 2.11.0, packaging, and their compatible non-extra
dependency closure. The validator checks installed distribution metadata,
Requires-Python and Requires-Dist recursively before official imports and records
resolved versions on success. Core dependencies include PyYAML, pydantic,
docker (library only), rich, numpy, cachetools, networkx, python-dotenv, litellm,
pandas, tokenizers, torchvision, transformers, safetensors and accelerate. The
full authoritative constraints are the preserved wheel METADATA, not this list.
No serving extras, vLLM startup, model weights, Docker engine or GPU are needed
for this compile-only gate. All transitive dependency compatibility must still
be satisfied; the 41-wheel collection is not claimed to be a complete environment.

For an already provisioned compatible environment, set the path to its existing
interpreter (no activation/install performed by this command):

```powershell
$gemmaCompilerPython = Read-Host 'Absolute path to the existing compatible Python executable'
& $gemmaCompilerPython -B .\validate_forgeai_gemma4_m2_minimal_baseline_1.py
if ($LASTEXITCODE -ne 0) { throw 'Gemma 4 M2 baseline validation failed or environment blocked' }
```

Expected states are sequential: M2_BASELINE_LOCAL_STATIC_CHECKS_PASSED,
M2_BASELINE_OFFICIAL_COMPILER_VALIDATED, then M2_BASELINE_PACKAGE_VALIDATED with
artifact directory/hash/manifest. Missing/incompatible dependencies produce
OFFICIAL_COMPILER_VALIDATION_BLOCKED_BY_ENVIRONMENT and
M2_BASELINE_INCONCLUSIVE_ENVIRONMENT_BLOCKED, exit 2; no package qualification.
Other failed controls exit 1. Staged versions must match working versions if
staged; the validator never stages files. Paste results before further work.

After a complete offline pass, the smallest next separately authorized slice is
a public-task smoke readiness review of the exact candidate/environment and public
task setup. Model execution and Kaggle submission require their own authorization.
Hidden scorer parity, leaderboard correctness, quality, and the Paper Track
discrepancy remain unresolved. M3 benchmark/research work does not begin on the
strength of compiler validation alone.

Proposed commit: `feat(gemma4): prepare minimal M2 baseline and offline compiler gate`.
