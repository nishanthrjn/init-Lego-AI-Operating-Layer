# FORGEAI-GEMMA4-M3-FIRST-SUBMISSION-READINESS-1

Date: 2026-10-20. Status: authored; maintainer execution pending.
This is first-submission preparation, not completion of the research plan's
baseline-results milestone. No score, model quality or submission is claimed.

## Closed M2 evidence and immutable first package

Maintainer supplied local 28-test PASS, official compiler/package reconciliation
PASS and pre-commit consistency PASS. Source commit inspected:
`d06ed1a` (`evidence(gemma4): record M2 official compiler and package validation`).
Committed evidence: [M2 manifest](../evidence/m2-ca6a05b4/kaggle-results/manifest.json).

- Receipt: `ca6a05b46844c86369c7aaef3d989b542c5f3c5f63fcc91c7fce5997742893d9`.
- ZIP SHA256: `78051300426d369e83a788f57bc6284c56c85d07cc32d6de87fbdc49c9da7e2d`.
- ZIP size: 1,566 bytes.
- Committed manifest SHA256: `91660911e8122cf4e6080add5d52972072f69eb13b8e7f048d1dfac108afac37`.
- Python 3.12.13 Linux; CPU notebook; Internet Off, as reported in M2 evidence.
- Correction to task summary: manifest records **four** deviations, not three:
  missing bigquery-storage; google-auth version; pydantic version; aiplatform's
  google-genai version constraint. None is erased or declared harmless.

The first package remains the M2 31B single-root candidate with budgets
`60 / 10 / 1 / 50` in timeout-seconds/tool-calls/time-minutes/turns order.
No candidate, evidence, production or frozen-evaluator file is changed.

## Stored official source citations and limits

Notebook cell numbers below are zero-based positions in the supplied notebook,
not execution counters. This review uses stored artifacts; it does not verify
current Kaggle UI, rules or hidden scorer source through the network.

| Topic | Stored evidence | Finding / limit |
| --- | --- | --- |
| Submission object | [Official overview screenshot](../docs/CompetitionWebPages-Screenshots/kaggle_com_competitions_gemma_4_developer_agent_overview_20261018_111039.png), Evaluation | A ZIP containing agent configuration, with agent.yaml at archive root. Configurations are described as compiled into ADK agents for evaluation. |
| Notebook output path | [Official starter](../docs/getting-started-gemma-4-developer-agent.ipynb), cells 4 and 12 | Cell 4 sets WORKING_DIR=/kaggle/working; cell 12 makes WORKING_DIR/submission.zip. Our copy uses exactly this output path. |
| Scoring handoff | [HARNESS_README](../docs/HARNESS_README.md), sections 2.2, 8.1 and 8.2 | Stage 1 evaluates the submission configuration and produces submission.parquet predictions; Stage 2 verifies generated patches. The ZIP is configuration, not M2's in-memory compiled object or precomputed predictions. |
| Recompilation | Overview Evaluation; README sections 2.1–2.2 | Runtime compilation of configuration is documented. Exact hidden entry-point calls, compile frequency, caching, extraction sequence and parity with the M2 compile are UNKNOWN. Do not claim the scorer consumes an M2 compiled executable as-is. |
| Select/submit | Starter cell 12 ends after producing ZIP | Exact live UI clicks, notebook-version selection, upload-versus-output selection, and queue behavior are UNKNOWN from the supplied artifacts. No submit API or automatic handoff is authored. Maintainer must confirm the competition interface accepts the saved output ZIP before submitting. |
| 12-hour cap | Overview screenshot, Issue Scoring | Patch generation has 12 hours, including sandbox setup and excluding final patch validation. It is an aggregate patch-generation constraint, not 12 hours for each agent. Exact clock start, scheduling/cancellation and partial-output handling at global expiry are UNKNOWN. |
| Local demonstration | Starter cell 10 | Evaluates tasks[:2] sequentially via evaluate_task, including verification, using subprocess sandbox. This is not evidence of hidden scorer task count/concurrency. |
| Task parallelism | README section 9, CLI --concurrency | Public CLI supports parallel tasks. Hidden scoring concurrency, batching and allocation are UNKNOWN. ParallelAgent is agent composition, not proof of task-level parallelism. |
| Hardware / serving | README section 3.1 | Documents 4 x NVIDIA L4, 24 GB each; vLLM tensor_parallel_size=4, gpu_memory_utilization=0.90, max_model_len=32768, Gemma4 tool/reasoning parsers. These are documented scoring provisions, not measured throughput or a fresh observation of hidden hosting. Our packaging notebook uses no GPU or serving. |

The overview's Code/Submission instructions do not establish the exact current
UI workflow. First scored run remains an attended, separately approved action.
If the interface requests an incompatible file or execution path, stop for
clarification; do not fabricate predictions or run the starter evaluator.

## Budget semantics

[HARNESS_README section 7.1](../docs/HARNESS_README.md) explicitly attributes
the four submission keys to Stage 1 `load_submission_eval_config`.

| Key | Meaning | Documented default | Environment override |
| --- | --- | --- | --- |
| timeout_seconds | Single sandbox command timeout, not total task/model timeout | 300 seconds | SWE_TIMEOUT_SECONDS |
| max_tool_calls | Per-task agent tool-call budget | 100 in inference.py; None in CLI | SWE_MAX_TOOL_CALLS |
| max_time_minutes | Per-task agent-loop wall clock | 60 minutes | SWE_MAX_TIME_MINUTES |
| max_turns | Per-task reasoning turns, not output tokens | 500 (None becomes 500) | SWE_MAX_TURNS / SWE_MAX_LOOP_ITERATIONS |

README section 6.1 documents command timeout as
`min(command_timeout_seconds, max(5, int(remaining_time_seconds)))`. Thus a
five-second floor exists in this calculation; do not assume perfectly strict
aggregate wall-time enforcement. Numeric clamps on submitted budget values,
precedence between both turn override names, and actual scoring environment
values are UNKNOWN from the available hidden-entry-point evidence.

README 7.1 says container creation, wheel installation and snapshot extraction
finish before the agent clock starts. Those costs still count toward the
overview's global cap. Stage 2 verification has a documented fixed 300-second
scorer timeout; it is not controlled by submission timeout_seconds. README also
lists SWE_TIMEOUT_SECONDS for metric.py, so effective hosted verification
overrides remain UNKNOWN rather than being treated as a participant control.
README 7.2 describes compaction/caching and transient retry delays; no throughput
or overhead measurements are inferred from them.

The [sample eval_config](../docs/sample_submission/eval_config.yaml) is 60/10/1/50,
matching M2. README 7.1's illustrative YAML uses timeout_seconds=300 instead.
Starter cell 10 reads these keys plus local-only alternatives
verification_timeout_seconds and max_llm_calls; those extra demo fields do not
establish additional supported submission keys and are not proposed here.

## Proposed later frozen budget variants — not implemented

Keep prompts, model, tools and sampling fixed to isolate the budget intervention.
Every variant needs separate authorization and its own M2-style directory/full
compile/negative-control/package validation, new manifest/hash and result record.
Do not modify or rescore the historical M2 artifact.

| Variant | timeout_seconds | max_tool_calls | max_time_minutes | max_turns | Rationale |
| --- | ---: | ---: | ---: | ---: | --- |
| B1 conservative | 60 | 20 | 2 | 60 | Double the agent window; modest navigation/edit/feedback allowance. |
| B2 moderate | 90 | 40 | 4 | 100 | More room for one repair cycle and slower commands. |
| B3 extended | 120 | 80 | 8 | 160 | Investigate tasks needing longer feedback; highest global-cap risk. |

All choices are proposals, not measured optima or proven accepted runtime values.
Turn/tool maxima do not guarantee they can be consumed before the time budget.

12 hours = 720 minutes = 43,200 seconds. Let N be hidden task count, C effective
task concurrency, S per-task setup minutes and W model startup/other overhead.
For serial execution the planning envelope is `W + N*(S+b)` minutes. An idealized
parallel estimate is `W + ceil(N/C)*(S+b)`, but shared GPU contention, scheduling,
timeouts and soft overruns can invalidate it. N, C, S, W and throughput are
UNKNOWN/UNMEASURED. Tensor parallel size four does not imply C=4.

| Agent budget b | Zero-overhead serial ceiling floor(720/b) | Illustrative ceiling with 120 minutes reserved floor(600/b) |
| --- | ---: | ---: |
| M2: 1 minute | 720 tasks | 600 tasks |
| B1: 2 minutes | 360 tasks | 300 tasks |
| B2: 4 minutes | 180 tasks | 150 tasks |
| B3: 8 minutes | 90 tasks | 75 tasks |

The 120-minute reserve is an UNMEASURED planning assumption, not a documented
allowance. For an illustrative N=100, C=1 and aggregate overhead=120 minutes,
M2/B1/B2/B3 take 220/320/520/920 minutes respectively; B3 exceeds 720 by 200.
This does not assert N=100. Do not use these tables to guarantee completion.
Prefer measuring the first unchanged M2 scored run before authorizing B1; defer
B2/B3 until task timing/coverage evidence can support the global-cap decision.

## Maintainer steps

1. Review this note and `first_submission.ipynb`; local offline tests may be run
   from the repository root in the existing environment:

   ```powershell
   uv run --locked --offline --no-sync python -B -m unittest discover -s experiments/gemma4_competition/submission_only -p test_first_submission.py
   if ($LASTEXITCODE -ne 0) { throw 'M3 submission-only controls failed' }
   ```

   Expected: eight tests pass. They copy fixtures into temporary directories only;
   no compilation, installs, models, Kaggle calls or M2 evidence mutation.
   Do not rerun the closed M2 slice validator to validate these new M3 files.

2. After local success and explicit notebook-execution approval, prepare two
   private input files: the unchanged committed `manifest.json`, and a copy of
   the M2 ZIP named **submission.zip.bin**. Kaggle auto-extracts uploaded `.zip`
   files in the maintainer's observed dataset workflow; the `.bin` suffix keeps
   the package available as bytes. Do not repack the ZIP or rename/edit original
   M2 evidence. Preserve the manifest bytes, including line endings.

   To prepare a fresh staging directory outside the repository:

   ```powershell
   $m3Upload = Join-Path $env:TEMP ('gemma4-m3-upload-' + [guid]::NewGuid().ToString('N'))
   New-Item -ItemType Directory -Path $m3Upload | Out-Null
   Copy-Item -LiteralPath '.\experiments\gemma4_competition\evidence\m2-ca6a05b4\kaggle-results\manifest.json' -Destination (Join-Path $m3Upload 'manifest.json')
   Copy-Item -LiteralPath '.\experiments\gemma4_competition\evidence\m2-ca6a05b4\kaggle-results\submission.zip' -Destination (Join-Path $m3Upload 'submission.zip.bin')
   Write-Output $m3Upload
   ```

   Upload those two files directly as a private Kaggle input. Set MANIFEST_PATH
   and PACKAGE_PATH to their actual mounted file paths. Set Accelerator None,
   Internet Off before execution. This note does not authorize publishing the
   dataset. Output remains `/kaggle/working/submission.zip`; all original hash,
   size, receipt, authorization and overwrite checks remain enforced.

3. Import the new submission-only notebook (not the starter or compiler notebook).
   Set AUTHORIZATION to:
   `AUTHORIZE FORGEAI GEMMA4 M3 FIRST SUBMISSION OF M2 PACKAGE ca6a05b4`.
   Run only its helper and copy cells. Expected M2_PACKAGE_COPIED_UNCHANGED and
   the exact ZIP hash above. No package installation or model execution occurs.
   An existing output causes refusal; preserve it before using a fresh session.

4. Save the output/notebook version. Have the maintainer inspect current official
   rules, eligibility, limits and UI handoff. Only after a separate submission
   decision select this version's `/kaggle/working/submission.zip` if the UI
   supports that operation. The exact selection sequence is UNKNOWN here.
   Do not select submission.parquet or the evidence bundle. The authored notebook
   never clicks Submit or calls a submission API.

5. Stop after that first scored attempt; do not automatically resubmit on failure.
   Preserve failure or partial-result evidence as carefully as a score.

## Evidence to retain

- Immutable M2 receipt, manifest, ZIP/hash, environment deviation report and
  original compiler/package qualification evidence.
- M3 notebook source, executed notebook/version ID and URL, copy output/hash,
  private input dataset version/ID, CPU/Internet settings and runtime version.
- Competition ID and submission ID; exact selected filename/notebook version;
  operator authorization and submission timestamp in UTC.
- Queued/start/completion timestamps when exposed, final status and public score
  as displayed (including precision). Record UNKNOWN when a timestamp is absent.
- All available scoring logs, warnings, errors, timings, resource readings,
  task counts/coverage and partial outputs. Hidden/unavailable items remain UNKNOWN.
- Whether the score is public/provisional or final; leaderboard position is a
  time-stamped observation, not a stable quality claim. No invented private score.

Record the first run separately from later variants. Its score is not evidence
that recorded dependency deviations are generally harmless. No model-quality,
hidden-scorer parity or competition acceptance claim follows from this readiness
slice alone. External submission executes models and incurs competition runtime;
the CPU copy-only notebook itself does not.

Proposed commit: `feat(gemma4): prepare hash-pinned first M2 submission notebook`.

VERIFICATION: NOT RUN — AWAITING MAINTAINER EXECUTION.
