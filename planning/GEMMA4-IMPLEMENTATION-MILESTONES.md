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
