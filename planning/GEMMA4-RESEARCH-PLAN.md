# Gemma 4 research plan

Status: PROPOSED — NO EXPERIMENTS RUN; NO NOVELTY OR IMPROVEMENT CLAIMED.
NO LIVE EXECUTION OR SUBMISSION AUTHORIZED.

## Question and prior art

Can source-bound dependency evidence improve repository repair under a fixed
Gemma budget without increasing unauthorized scope or masking failed checks?
Evidence-Bound Graph-Guided Coding Agent is a working method name, not a novelty
claim. Graph retrieval, repository localization and tool-feedback loops have
substantial prior art. [RepoCoder](https://arxiv.org/abs/2303.12570) investigates
iterative repository retrieval/generation; [SWE-agent](https://arxiv.org/abs/2405.15793)
studies agent-computer interfaces; [AutoCodeRover](https://arxiv.org/abs/2404.05427)
uses code-structure-oriented repository search. Their settings/results do not
establish improvement for this competition. M1/M3 require a fuller related-work
review before asserting a contribution.

## Frozen independent benchmark

Create a new benchmark, never modify the frozen KiSSKI evaluator. Proposed initial
minimum: 60 independently authored issue fixtures in 12 small repository families,
five tasks each. Assign entire families before any tuning: six train, three dev,
three locked evaluation (30/15/15 tasks). Freeze IDs, repository snapshots, issue
text, instruction files, oracle patches, hidden tests, licenses and SHA256 manifests.
Fixtures include single/multi-file fixes, API compatibility, dependency faults,
authorization checks and insufficient-evidence tasks. Independent fixture authors
or maintainer review must verify defective baseline and oracle behavior before use.

Separate oracle/test storage from all agent-visible files. Keep an evaluator-only
relevance label set for retrieval metrics; do not leak solution spans into prompts.
Deduplicate issue text and code lineage across partitions and any training corpus.
Keep official public tasks as a separately reported development cohort; never use
leaderboard feedback as locked local evaluation labels. Label unknown pretraining
contamination honestly. This small benchmark supports pilot estimates, not broad
significance claims. Expand families before stronger claims if intervals are wide.

Freeze corpus and experimental protocol before M3. Choose candidate settings only
on train/dev. Evaluation access is logged; once inspected, its results cannot be
used to tune the same held-out claim. A new version needs new independent holdout.

## Matched experiment arms

B0: one plain Gemma agent, lexical navigation, official tools, minimal prompt,
fixed repair count. B1: same agent with graph-aided retrieval. B2: B1 with explicit
evidence/source-hash binding and stale-context checks. B3: B2 with bounded feedback
summarization/repair. Include lexical-plus-evidence control to separate graph from
provenance effects; compare optional reviewer on/off only after baseline stability.
No model substitution. Pin model revision/quantization/adapters, sampling, prompt,
harness, tools, hardware, split, wall time, tokens and total tool/repair ceilings.
Charge graph preprocessing and reviewer overhead to each arm, with cold/warm costs
reported separately. Use identical tasks and paired seeds; propose three seeds
if resources permit, frozen before evaluation. Deterministic outputs are not assumed.

## Falsifiable hypotheses and measurements

| Hypothesis | Metric and failure criterion |
| --- | --- |
| H1 graph improves selection | Recall@token-budget and precision against independent relevant-file/symbol labels; reject if paired improvement interval includes zero. Report label ambiguity. |
| H2 evidence improves repair | Primary task pass@1 on clean hidden validation; failures/timeouts remain denominator. No gain if paired success delta interval includes zero. |
| H3 binding reduces scope errors | Unauthorized file edits / attempted edits and stale-context refusals per task; require no higher violation rate. Refusal is not task success. |
| H4 patching remains reliable | Applicable patches / all tasks; syntax and regression failure rates. Reject improvement claim if applicability declines. |
| H5 feedback helps | Paired repair-success delta versus feedback withheld/shuffled on dev-only controls; compare same repair/token budget. Infrastructure errors separate from test failures. |
| H6 efficiency improves | Total model tokens and wall time per resolved issue, plus all-task totals and p50/p95 latency. Count failed-task costs; never report success-only latency alone. |
| H7 review adds value | Critical-defect recall/miss count, unmatched-finding count and clean-patch false-positive rate with explicit denominators. Independent clean/defective fixtures; no conflation of count and rate. |

Use task-paired outcomes and repository-cluster bootstrap intervals; tiny family
counts limit precision. Pre-register primary H2 and safety constraint H3; other
metrics exploratory or multiplicity-adjusted. Report sample sizes, all seeds,
confidence intervals, failures and null/negative findings. Do not select best-seed
results. Scope safety is a gate, not a weighted score that success can offset.

## Graph and failure design

Nodes: repository revision, file, symbol, instruction and test. Edges: contains,
imports and references; optional call/test-link edges explicitly mark confidence.
Store parser version, source span/hash and unresolved edges. Python AST extraction
must not import project code. Cap bytes/nodes/edges/depth and degrade to lexical
retrieval on unsupported syntax; log degradation. Distinguish genuine abstention,
bad retrieval, stale graph, invalid patch, model formatting, tool rejection,
infrastructure timeout and hidden-test failure. Check adversarial instructions,
path traversal, stale snapshots and falsely successful tool summaries offline.

## Optional improvement research

LoRA is a separate M7 gate: only if dev evidence identifies a systematic learnable
failure and rules/data rights, hardware and time permit. Train on training partition
only; freeze adapter/config before held-out evaluation; compare no-adapter at matched
budgets. Do not train on locked evaluation, hidden tests or historical KiSSKI outputs.
Model-specific formatting/skill learning must not weaken general product security.
If compute or benefit is unclear, omit training and publish the controlled analysis.

## Paper evidence package

Maintain methods, hypotheses, provenance, partition manifest, code/config hashes,
per-task outcomes, budget ledger, ablations and limitations as experiments occur.
Use the verified Paper Track requirements in the requirements register. Target an
honest resource/method analysis, including negative results, rather than claiming
state of the art from a few tasks. Public assets require license/privacy review;
no raw credentials, hidden competition artifacts or restricted records published.

## Controlled model-variant experiment (after M1 and working harness)

The no-substitution requirement above applies within each retrieval ablation.
A separate paired experiment compares 31B with 12B; E4B/E2B are optional later
arms. Each submission uses one staff-announced variant only. No mixed-model
agent tree. Package compatibility is a prerequisite, not an assumed success.

Hold task split, tools, prompt, sampling policy, per-task wall-time ceiling,
repair ceiling and scoring constant. Use the same hardware where available;
report any unavoidable difference as a confound. Record issues resolved/all
attempted, patch applicability, total wall time including loading/setup, inference
time if observable, token counts or NOT_OBSERVABLE, tool calls, scope violations,
model/protocol failures and actual effective limits. Randomize arm order and use
paired tasks/seeds; include cold-load and warm results separately. Never silently
retune prompts per variant. A second, separately labeled throughput experiment may
allocate more turns to smaller models within the same wall-time ceiling.

Hypothesis: lower loading/memory/inference costs may enable more useful work per
budget. No quality, speed or memory advantage has been measured here. Choose the
variant on development evidence and freeze before held-out evaluation; report
paired uncertainty and failures rather than reputational model rankings.

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
