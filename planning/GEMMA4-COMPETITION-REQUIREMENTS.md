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
is `gemma-4-31b-it-qat-w4a16-ct` for every agent. Optional PEFT LoRA directories
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
