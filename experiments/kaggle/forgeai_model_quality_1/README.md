# ForgeAI Kaggle model quality evaluation 1

Status: IMPLEMENTED; MAINTAINER VALIDATION REQUIRED. No evaluation executed.

This is a personal, synthetic, manual-transfer experiment. Its question is
whether one pinned coding model merits further investigation for ForgeAI.
It neither implements nor authorizes the blocked Kaggle job bridge.

## Frozen plan

- Model: `Qwen/Qwen2.5-Coder-14B-Instruct-AWQ`.
- Revision: `eb3172f06a6d6b3a15f08947b0668d782e4d2d2c`, AWQ 4-bit.
- Runtime: Python 3.12.3, torch 2.7.0+cu128, transformers 4.51.3,
  vLLM 0.9.2, two Tesla T4 GPUs, tensor parallelism 2.
- Ten scenarios, ten initial generations and at most one rework: **11 calls**.
- Every call: temperature 0, seed 0, input <=16384 UTF-8 bytes and <=3072
  tokenizer tokens including chat framing; output <=1024 tokens and <=16384
  UTF-8 bytes; 180-second generation deadline. No retry, fallback or third proposal.
- Startup/identity deadline: 900 seconds; each deterministic check: 30 seconds.
- No HTTP client, inference endpoint, download, Kaggle API, polling or tunnel.
  vLLM tensor-parallel workers use local interprocess communication.

The 1G evidence established READY/JSON/ADD at a 512-token model context.
This evaluation needs a 4096-token context and uses vLLM in-process generation.
**Those are unqualified runtime variations**, despite retaining the pinned
weights/packages/GPU/quantization/TP settings. A load or resource failure is
inconclusive and never justifies changing configuration or model during a run.

## Dedicated inventory

| Scenario | Role | Oracle / dimension emphasis |
|---|---|---|
| SIMPLE_BUG_FIX | Coding | Inclusive endpoints; regression test detects original |
| CREATE_WITH_CONTEXT | Coding | Clamp; exact supplied module/function docstrings |
| TYPE_SAFETY | Coding | Integer return on negative branch; strict mypy |
| RUFF_TRAP | Coding | Correct addition without dead local F841 |
| SCOPE_TRAP | Coding | Clamp to 9 despite read-only legacy policy; no extra edits |
| VACUOUS_TEST_TRAP | Coding | Absolute difference; test distinguishes old/new |
| CHECK_FEEDBACK_REWORK | Coding x at most 2 | Maximum; preserve unequal/equal cases |
| REVIEW_GOOD_PATCH | Reviewer | Accept correct inclusive-length implementation |
| REVIEW_BAD_PATCH | Reviewer | Reject blocking off-by-one with supplied reference |
| REVIEW_VACUOUS_TEST | Reviewer | Reject test passing old and fixed implementations |

All fixture code and objectives were written for this experiment. No source
file from production is uploaded or inserted in prompts. `scenarios.py` owns
the tiny fixtures; `fixtures/PROVENANCE.md` records their origin. Reference
solutions and correctness oracles are evaluator-only, excluded from initial
prompts. A rework receives bounded deterministic findings and oracle examples.
No ambiguous coding case is included: the current CodingProposal requires at
least one change, so a no-change refusal would confound contract scoring.

## Contract representation and limitations

`contracts.py` mirrors the current Coding/Reviewer JSON fields, enums, string
bounds, target membership, blocking-action and decision consistency rules.
ADR-021 permits raw JSON or one unlabeled/json fence; raw-JSON compliance is
also recorded separately. This is **evaluation-only duplication**, bound by
the package manifest. It is not a new production schema or authorization owner.

The inspected repository baseline is `fc82cbd864c5a1e1e460a2168721f3b466c561fa`:
CodingRequest/CodingProposal in `legoai_engineering.coding.values`,
ReviewRequest/Review in `legoai_engineering.reviewer.values`, agent definitions,
ADR-021, and `forgeai.review.check_rework_constraints`.
The combined prompt uses the production `current_text` target field and the
Reviewer `proposal: {material_id, text}` envelope. Producer attribution stays
host-side, just as in the production model-visible payload. Evaluation output
is capped at 16 KiB for both roles and NUL is rejected in every string; these
are explicitly tighter evaluation limits than some production narrative fields.
ExecutionContext, canonical evidence, mutation authority and real workspace
preconditions are deliberately not fabricated. Request material preserves
objective/targets/constraints/current text/read-only context and
objective/criteria/proposal/evidence shapes, but does not emulate
production execution attribution. Complete-file proposals, not patches, are used.

Only completed first-attempt oracle/Ruff/mypy findings trigger rework. The
second prompt includes the actual first proposal as current text, same targets
now updated, original objective and bounded check-finding data. No model output
is modified to force a failure. If the first proposal is already correct or
unusable, rework is explicitly NOT_EXERCISED and the suite cannot be promising.
This is an honest coverage limitation, not an automatic retry opportunity.

## Candidate execution boundary

Strict JSON and exact fixed paths/operations are checked before any write.
Candidate file text is further restricted to a deliberately tiny scalar Python
language by `safety.py`. No attribute access, subscripts, loops, recursion,
decorators, dynamic imports, reflective calls, tool directives, file access,
shells or arbitrary helper calls are admitted. Only tests may call `solve` with
bounded integer literals. This excludes many valid general Python solutions
and is reported as a suite limitation, not general model unsafety.

Only admitted file text enters a fresh temporary fixture. Fixed pytest, Ruff
and mypy commands run with a minimal environment, plugin auto-loading disabled,
explicit isolated configs and discarded output. No model-produced command or
raw response is executed or passed to eval/exec. This language gate is not an
OS sandbox for arbitrary Python. Use only a disposable credential-free session.

Tests for selected fixes must pass the candidate and fail the original in two
fresh pytest processes, with bytecode caching disabled. Exit 1 means assertions
failed; collection/tool errors and timeouts are inconclusive, not test strength.
Tests passing both versions produce VACUOUS_TEST. Hidden fixture oracle tests
separately guard correctness so a model cannot win by writing weak tests.

## Frozen scoring

Separate PASS/FAIL/NOT_APPLICABLE dimensions: CONTRACT_VALIDITY,
TASK_CORRECTNESS, TEST_STRENGTH, SCOPE_DISCIPLINE, CONTEXT_USE, STATIC_QUALITY,
REVIEW_ACCURACY, REWORK_QUALITY. No LLM grader or aggregate-only percentage.
FAIL means a required gate was not established; after an earlier rejection it
does not imply a tool ran and observed an assertion failure. NOT_APPLICABLE is
reserved for dimensions outside that scenario, never a way to skip a required
test-strength or context gate.

Promising requires complete coverage, 100% contract validity, zero scope
violations, at least 6/7 final coding correctness and static-quality passes,
all applicable context/test-strength/review/rework checks passing. These
thresholds are frozen before live results. Six of seven allows one isolated
coding failure while retaining strict boundary, testing and review gates.

Reviewer rubric checks decision, exact finding count/category/severity,
supplied evidence references, nonblank action and conservative defect/action
keywords. False-positive/false-negative fields are retained. This reproducible
lexical rubric can reject equivalent wording and does not prove reasoning;
it is not an LLM judge. No known-bad acceptance can receive a passing score.

Final vocabulary: MODEL_QUALITY_PROMISING, MODEL_QUALITY_INSUFFICIENT,
MODEL_CONTRACT_UNSTABLE, EVALUATION_INCOMPLETE, RESULT_INCONCLUSIVE.
Infrastructure failure is inconclusive; missing scenarios/rework are incomplete;
invalid output contracts or generation truncation are unstable; failed quality
gates are insufficient. A completed tool failure stops further generation.

## Package and later handoff

`manifest.json` binds the exact transfer file allowlist and normalized LF SHA256
digests. Its own SHA256 is the package identity. The ZIP carries only this
allowlist under `forgeai_model_quality_1/`; tests, repository source, local
results, account data and environment files are excluded. `package.build`
creates a new ZIP exclusively; it is not invoked by a live run.

The thin `kaggle_quality.ipynb` is disabled (`AUTHORIZED = False`). It requires
the separately reviewed manifest digest entered in the notebook,
the exact package extraction directory, a reviewed local snapshot already at
`/tmp/legoai-kaggle-runtime-1/model`, and the qualified Python executable at
`/tmp/legoai-kaggle-runtime-1/venv/bin/python`. No installer or downloader is
included. Evaluation tools are separately pinned in requirements-evaluation.txt;
they do not change the repository's dependencies.

The worker uses the documented [vLLM 0.9.2 LLM interface](https://docs.vllm.ai/en/v0.9.2/api/vllm/entrypoints/llm.html)
with a local model/tokenizer path, remote code disabled and fixed sampling.
Interface documentation is not runtime qualification.

Before any later authorization, review/create
`/kaggle/working/reviewed_model_inventory.json` with exactly `model_id`,
`model_revision`, and `files` mapping the ten fixed weight/tokenizer filenames
in runtime_worker.py to independently reviewed SHA256 digests. It is **not**
auto-created or accepted from model output. Hash matching binds observed bytes;
the operator's separately reviewed acquisition provenance binds those bytes
to the named revision. No placeholder receipt is supplied. Missing identity,
tool versions, hardware or runtime closes the gate before generation.

No live command or installation is authorized by this document. After local
validation, separately review this package digest, the inventory provenance,
11-call ceiling, fixtures, result schema, notebook and runtime variation.

## Results and comparison

Exclusive output directory: `/kaggle/working/forgeai-quality-result`.
`forgeai_kaggle_quality_result.json` (<=128 KiB) includes evaluation/package/model
identity, actual runtime identity, per-case dimensions and safe failures,
prompt/output digests, attempt timings, call count and frozen decision.
`forgeai_kaggle_quality_report.md` provides the per-case dimension table and
qualification limits. No raw model output, raw tool log, credentials, account
identifiers or environment dump are exported. An existing result directory
refuses reuse rather than overwriting evidence.

No automatic local baseline. Future 7B/14B baselines need separate records and
the same suite identity; no comparative conclusion exists now. A promising
result is not production quality, arbitrary-repository performance, commercial
suitability, unattended mutation safety, connectivity or availability.

## Maintainer validation (offline, no GPU)

From the repository root:

```powershell
uv run --locked --offline --no-sync python .\validate_forgeai_kaggle_model_quality_evaluation_1.py
if ($LASTEXITCODE -ne 0) { throw 'ForgeAI Kaggle model-quality validation failed' }
```

Paste the complete phase output. No test, validator, model or notebook was
executed during implementation. A local pass only permits a separate handoff
review; it does not authorize a live session.
