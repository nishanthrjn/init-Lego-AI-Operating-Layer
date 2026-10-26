# Gemma 4 competition: independent continuation

Maintainer review snapshot: **2026-10-26**, branch **br-ForgeAI-Gemma4**, HEAD
`6cf6ce87206ce31a13fcc95b7995183a09561ad8` before this documentary edit.
The initially open product branch was clean at the same commit; the checkout
was switched to the existing competition branch. No branch history was changed.
Product work is independent: no merges, shared Core/Ports changes or product
release gates for competition needs. Reusable improvements require a written
cherry-pick proposal with ownership, tests and risks; execution is separate.

## Current state and entry points

One root Gemma 4 31B LlmAgent, official tools, no LoRA/subagents/ForgeAI imports.
Qualified packages: M2, B2, P1 and P3. Public scores (maintainer-reported):
**0.05 / 0.12 / 0.10 / 0.15**. Preserve P1's failed dataset-based attempt as a
separate historical record. P3: receipt `02a7f680`, ZIP `19b4e772`, 5,100 bytes;
qualification pins are committed in `6cf6ce8`. External install evidence records
Python 3.12.13, five scoped wheels and four official environment deviations.

| Workflow | Current entry point | Interpretation |
|---|---|---|
| Evidence | [paper index](results/paper-evidence.json), [submissions](results/submissions.json), [six-run table](results/dev-16v-comparison.md) | Source hashes and evidence limits; derived analysis still pending where marked |
| Candidate design | [candidates](candidates/README.md) | Historical slices below current instructions; do not rerun old qualification automatically |
| Qualification | [compiler workflow](kaggle_compiler/README.md), `p3_compiler_only.ipynb`, root P3 validator | Local receipt → CPU compile → reconcile → staged consistency; fresh candidate needs its own pins |
| Submission | [submission-only](submission_only/README.md), `generate_self_contained.py` | Reconciled pins only; CPU/Internet Off, no datasets, rerun-safe; separate submission approval |
| Evaluation | [local evaluation](local_eval/README.md), `local_eval.ipynb` | Gold-free tooling, official GPU path, frozen controls; raw outputs external |

Local development scores P1/P1b/P1c/P2/P3/P3g are **8/8/7/8/8/7 of 16**.
Controls `05706c6a`: 24/50 verifiable, reproduction reported identical; dev-16v
is a tuning set, not a held-out claim. P3 has zero observed context crashes
and approximately eight-hour mean projection. P2 had three context crashes.
Graph tools were used in only 3/32 P2+P3g task-runs: this does not test their
potential benefit under reliable adoption. CPU localization file recall@10 is
L .31, T1 .32, T2 .35, fusion .44. The served 32,768 context with a 16,384 output
reservation leaves nominally 16,384 input tokens; P3 reserves 8,192. See pinned
`local_eval/official-cells.json`, cell 8, and the paper index. Do not claim
statistical improvement from public scores with reported +/-3-task variability.

## Command cheat sheet (maintainer only; not executed)

From repository root, use the locked environment. Start with documentary review;
do not rerun historical scope validators for this new documentation slice.

```powershell
git branch --show-current  # must be br-ForgeAI-Gemma4
git diff -- experiments/gemma4_competition/README.md experiments/gemma4_competition/results/submissions.json experiments/gemma4_competition/results/paper-evidence.json
Get-FileHash experiments/gemma4_competition/results/submissions.json -Algorithm SHA256
# Must equal the public_scores_and_noise claim's SHA256 in paper-evidence.json.

# Optional future analysis: existing results only, no model.
$p3Run = 'D:\Downloads\local_eval_p3\local_eval_p3_dev16v\forgeai-local-eval-p3-dev-16v-attempt1'
uv run --locked --offline --no-sync python -B experiments/gemma4_competition/local_eval/analysis.py summary $p3Run --controls experiments/gemma4_competition/local_eval/evidence/controls-05706c6a.json --controls-sha256 05706c6a948a67bfaf991ed0282d11308aac79865a614a68c6c582fe01f67033
if ($LASTEXITCODE -ne 0) { throw 'P3 summary failed' }
```

For a new candidate, obtain approval for its isolated delta, static controls and
experimental package, evaluate on dev-16v, then confirm a frozen winner using
only VERIFIABLE confirm-20 tasks. Require the bootstrap 95% upper bound for
116 tasks plus startup to stay below 11 hours. Qualification then follows its
own local/CPU/reconcile path; never repoint P3 pins at another package.
Use `submission_only/generate_self_contained.py --candidate NAME --manifest FILE
--package FILE --output FRESH_EXTERNAL_IPYNB` only after reconciliation. Review
the printed hashes and authorization before any separately approved Kaggle run.

## External evidence inventory

Paths below were observed present by filesystem inspection, not revalidated.
They are required only for the corresponding reproduction workflow, not product
development. Preserve hashes when relocating; change path arguments, not evidence.

| Purpose | External path |
|---|---|
| P3 receipt | `D:\Downloads\p3-qualification\bundle-02a7f680\local-receipt.json` |
| P3 compiler outputs | `D:\Downloads\p3-qualification\kaggle-results\gemma4-p3-compiler` |
| P1 development | `D:\Downloads\local-eval-p1-dev30\forgeai-local-eval-p1-dev30-attempt1` |
| P1b merged view | `D:\Downloads\local_eval_p1_dev30\p1b\forgeai-local-eval-p1b-dev-16v-attempt2` |
| P1b ancestor/config | `D:\Downloads\local-eval-p1b-dev16v\forgeai-local-eval-p1b-dev-16v-attempt1`; sibling `local-eval-config.json` |
| P1c | `D:\Downloads\local_eval_p1_dev30\p1c\forgeai-local-eval-p1c-dev-16v-attempt1` |
| P2 | `D:\Downloads\local_eval_p2_dev16v\forgeai-local-eval-p2-dev-16v-attempt1` |
| P3 / P3g | `D:\Downloads\local_eval_p3\local_eval_p3_dev16v\forgeai-local-eval-p3-dev-16v-attempt1`; `local_eval_p3g_dev16v\forgeai-local-eval-p3g-dev-16v-attempt1` under the same parent |
| P1 smoke | `D:\Downloads\local-eval-p1-smoke5\forgeai-local-eval-p1-smoke5-attempt1` |
| B2 qualification | `D:\Downloads\gemma-b2-transfer-parent-eouf5647\bundle\local-receipt.json`; `D:\Downloads\gemma4-b2-compiler-d7195f13\gemma4-b2-compiler` |
| Infrastructure / selection metadata | `D:\Downloads\competition-infra`; `D:\Downloads\gemma4-dev-metadata\public_dev_task_metadata.jsonl` |
| Experimental packages | `D:\Downloads\gemma-p1b-experiment`, `gemma-p1c-experiment`, `gemma-p2-experiment`, `gemma-p3-experiment`, `gemma-p3g-experiment` under Downloads |
| Retained diagnostics | `D:\Downloads\p1-dev30-trace-review.json`; `D:\Downloads\p1b-resume-preparation` |

Historical example paths `D:\Downloads\forgeai-local-eval-p1-smoke5-attempt1`,
`dev-16v-comparison.md`, `gemma-location-review`, and `p3-six-run-review-1` are
absent. The first has the nested smoke path above; the others are proposed output
destinations, not missing mandatory inputs. `run-a`, `run-b`, `YOUR-*` are
placeholders. Temporary receipt paths are not durable; use preserved copies.
Raw traces, downloaded notebooks, binaries and full task data stay external.
Commit only reviewed safe metadata/hash records. Never place gold data in GPU
tooling inputs. The 41 preserved official wheels remain under `docs/archive`.

## Proposed remaining plan — no execution authorized

Deadlines checked 2026-10-26: paper **Nov 12**, entry/team merge **Nov 25**, final
submission **Dec 2**, all **23:59 UTC**. Official rules endpoints returned no
readable body; dates are corroborated by official [main timeline/prizes](https://www.kaggle.com/competitions/gemma-4-developer-agent/overview/prizes)
and [paper overview](https://www.kaggle.com/competitions/gemma-4-developer-agent-paper/overview/description).
Recheck before submission. This plan does not authorize a team merge or Git merge.

Quota estimates are planning assumptions, not measured allocations: L4x4 charges
2x session hours per the official main page. P3 dev-16v estimate is
`(16*244 + 370)/3600 = 1.19 h`, about **2.4 quota-hours**. Setup/install/idle time
can increase this; reserve 1.5–2 h/session (3–4 quota-hours). Account balance and
scoring-job charging are UNKNOWN; queue time is not GPU runtime.

| Window | Proposed action and decision gate | L4x4 quota reservation |
|---|---|---|
| Oct 27–Nov 1 | Two exact-package P3 dev-16v replicates, distinct attempt IDs; retain errors/timings and paired outcomes. Optionally two identical public submissions only with approval and available daily slots. | 6–8 quota-hours for local runs; scorer cost unknown |
| Nov 2–6 | P4 feasibility: only max_time_minutes 6→7, preserve P3 prompt/model/tools/sampling and other limits. Build only after review. Smoke then dev-16v, with stop if bootstrap upper-bound projection exceeds 11 h or errors recur. | Smoke 1–2 plus dev 3–5 quota-hours |
| Nov 7–10 | Freeze best candidate; evaluate on eight VERIFIABLE confirm-20 tasks once, no tuning against outcomes. Freeze paper artifacts and limitations. | 2–3 quota-hours |
| By Nov 11 | Finalize reproducible paper/writeup, citations, noise and weak graph adoption as limitations; no novelty or improvement claim without supporting evidence. Maintainer submits before Nov 12 deadline. | CPU/editor only |
| Nov 13–20 | Optional E4B feasibility: first reconcile updated official model registry/serving pins; then smoke-5 and, only if viable, dev-16v. No LoRA or subagents. Separate package and compiler qualification. | Reserve 1–2 + 3–5 quota-hours; UNMEASURED, do not assume speedup |
| Nov 21–25 | Check entry/team eligibility; replicate finalist only if uncertainty affects selection, retain P3 fallback. | 3–5 quota-hours discretionary |
| Nov 26–Dec 1 | Freeze hashes, qualify finalists and prepare self-contained versions; allow scoring turnaround before Dec 2. Maintainer selects final two explicitly. | CPU preparation; scorer cost unknown |

Core local plan reserves **12–18 quota-hours**, optional E4B **4–7**, plus
**3–5** discretionary: total **19–30**, excluding scorer usage and failures.
Do not schedule against an assumed weekly quota; confirm account capacity first.
P4's seven-minute cap gives `116*7/60 = 13.53 h` before setup: it is NOT worst-case
time-safe. Only measured runtime distributions can justify it; proportional
scaling of P3's eight-hour mean to 9.33 h is a hypothesis, not acceptance.

The newer official [prize page](https://www.kaggle.com/competitions/gemma-4-developer-agent/overview/prizes)
confirms a $10,000 E2B/E4B bonus requiring an eligible package among the final two.
The [staff model announcement](https://www.kaggle.com/competitions/gemma-4-developer-agent/discussion/748287)
confirms `gemma-4-e4b-it-qat-w4a16-ct`; the older cached 31B-only overview is stale.
Public eligibility does not establish compatibility with our pinned wheel bytes.

Final-two criteria: qualified immutable packages; reliable scoring completion;
11-hour bootstrap gate; replicated local evidence and held-out confirmation;
public scores interpreted with noise, not highest single draw. Prefer complementary
task outcomes if evidenced. Keep P3 as fallback. Include E4B only if eligible,
time-safe and worth sacrificing a general-track finalist slot; the bonus is not
automatic. No product-branch dependency and no reusable-change proposal needed
for this documentary slice. **Verification NOT RUN; await maintainer review.**
