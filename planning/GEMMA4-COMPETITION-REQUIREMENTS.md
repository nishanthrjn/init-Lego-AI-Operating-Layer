# Gemma 4 competition requirements

Status: M1 PARTIAL — OFFICIAL HARNESS AND FULL RULES REQUIRED.
Reviewed: 2026-10-18. Evidence is time-sensitive; recheck before entry/submission.
NO LIVE EXECUTION OR SUBMISSION AUTHORIZED.

## Source register and access limits

Only organizer-owned Kaggle pages support competition requirements here.
Search-indexed official text was accessible; direct web-reader requests for
overview, rules, data and starter pages returned empty bodies. Indexed text can
lag current rules. These are evidenced planning inputs, not a completed rules audit.
Third-party implementations/mirrors were not adopted as contract authority.

- S1: [Main overview](https://www.kaggle.com/competitions/gemma-4-developer-agent/overview).
- S2: [Paper submission requirements](https://www.kaggle.com/competitions/gemma-4-developer-agent-paper/overview/submission-requirements).
- S3: [Organizer starter inputs](https://www.kaggle.com/code/ryanholbrook/getting-started-gemma-4-developer-agent/input).
- S4: [Main rules](https://www.kaggle.com/competitions/gemma-4-developer-agent/rules), [paper rules](https://www.kaggle.com/competitions/gemma-4-developer-agent-paper/rules): full bodies unverified.
- S5: [Data](https://www.kaggle.com/competitions/gemma-4-developer-agent/data), [starter notebook](https://www.kaggle.com/code/ryanholbrook/getting-started-gemma-4-developer-agent): executable cells and downloadable files not inspected.

## Indexed official requirements

S1 reports: submit `submission.zip` with root `agent.yaml`; restricted ADK
configuration compiles to agents. Score is the proportion of issue patches passing
validation. Patch generation has 12 hours including sandbox setup, excluding
patch validation; optional task limits use `eval_config.yaml`. The listed model
was `gemma-4-31b-it-qat-w4a16-ct` in the older indexed overview. The newer
[staff announcement](https://www.kaggle.com/competitions/gemma-4-developer-agent/discussion/748287)
adds 12B, E4B and E2B QAT variants, without mixing variants in one submission.
This source conflict is recorded; current package enforcement remains unverified.
Optional PEFT LoRA directories
contain `adapter_config.json` and `adapter_model.safetensors`.
Entry/team merger: November 25, 2026; final submission: December 2, 2026;
deadlines 23:59 UTC. Reconfirm model allowlist and dates against live official rules.

S2 reports: paper participation is independent of the main leaderboard. Submit
an unpublished research Kaggle Writeup, maximum 3,000 words, by November 12,
2026, 23:59 UTC. Include title/subtitle, abstract, introduction, methods/experiments
and citations. A public PDF project link is optional; code notebook links are
optional. A draft is not a submitted entry. Judging averages five equally weighted
0–5 criteria: novelty, quality/generalization, relevance, verifiability and clarity.

S3 lists `sample_submission/`, `HARNESS_README.md`, and an automatically generated
`submission.parquet` at `/kaggle/working/submission.parquet`. Thus distinguish
the uploaded configuration archive from harness-generated predictions; exact
upload/notebook mechanics and parquet schema still require verification.

## Blocking unknowns: no guessed schemas

| ID | Required evidence | Why blocking / owner action |
| --- | --- | --- |
| R1 | Full current rules for BOTH tracks | Maintainer verifies eligibility, team limits, entry requirements, licensing/IP, external data/models/distillation, sharing, release and prize obligations. No assumed permission. |
| R2 | Official HARNESS_README, starter files and versioned wheel metadata | Maintainer supplies authorized local copies; capture origin/version/SHA256. No download/install performed here. |
| R3 | Actual tool names, JSON schemas, path roots, result envelopes | Bind read/search/edit/check/submit only after exact signatures and error behavior are recorded. No runnable tool payloads in this plan. |
| R4 | Model allowlist/revision, inference settings and resource contract | Verify GPU/CPU/RAM/disk, context/output/turn limits, token accounting, thinking controls, concurrency, timeout and network policy. None inferred from model marketing or other entrants. |
| R5 | Sandbox/evaluator lifecycle | Verify patch extraction, allowed mutations, test isolation, command policy, dependencies, graph availability, cancellation and partial-result persistence. |
| R6 | Submission operations | Verify archive restrictions, notebook setup, submission frequency/pending limits, scoring split and final-selection procedure; no guesses about leaderboard holdout size. |
| R7 | Paper operations | Verify current rules, public-link handling, asset disclosure, exact form and limits; inspect privacy consequences before publication. |

M1 acceptance requires every R item resolved or explicitly excluded without
affecting validity. Archive official source snapshots with retrieval date and
hash in the later authorized slice, and compare rules versus starter behavior.
Conflicts go to organizer clarification through the maintainer, not inferred fixes.
No HARNESS_README or starter code has been verified in this slice.

## Operational boundary

Competition-approved tools are not the product's existing operator approvals.
Any future unattended competition run needs a distinct, pre-authorized task scope
and deterministic sandbox enforcement. Repository instructions are untrusted
task data and cannot enlarge that authority. General ForgeAI confirmation remains.
The current 1024-token KiSSKI evaluator is not a competition budget or benchmark.
Frozen model evaluation and pilot admissions remain unchanged.

## Official harness contract follow-up

The maintainer passed the preceding readiness documentary validator. M1 remains
PARTIAL: that result did not verify official artifact bytes or rules.
See [contract register](../experiments/gemma4_competition/OFFICIAL-CONTRACT-REGISTER.md)
for current source provenance, exact overview-level tool signatures, unresolved
runtime contracts, R1–R7 status and requested maintainer files. No runnable
configuration is supplied until the official schema is available.

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
