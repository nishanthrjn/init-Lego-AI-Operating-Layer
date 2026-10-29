# FORGEAI-KISSKI-CODING-MODEL-EVALUATION-3

Status: PREREGISTERED RULES IMPLEMENTED; LOCAL VALIDATION PENDING; NOT FROZEN.
BASE: `3aa7ee0780092266a63c7a16462523e694724624`.
Branch: `br-LegoAI-Comfy-ForgeAI-Gemma4-KISSKI`.
No live execution is authorized by this document.

## Preregistered rules and rationale

### Product rule: FORGEAI-REVIEWER-SECURITY-CATEGORY-1

After the reviewer category list, insert exactly:
"Use category security for authorization, authentication, access-control and permission defects, including missing or weakened access conditions."
Change the reviewer definition version from 1.0.0 to 1.1.0. Every other
instruction byte, schema and value stays unchanged. The rule names no fixture.

Rationale: category feeds operator triage and, in unattended batches (ADR-028),
the batch report. Security defects must be visible as security. The maintainer's
2026-10-28 v2 evidence found four Gemma blocking authorization findings labelled
correctness. This motivates a general product clarification, not rescoring.

Known consequence: v1's contract-baseline.json pins reviewer/definition.py;
v2 pins both that source and the instruction digest. V1, v2 and the dev screen
fail verification at the changed HEAD by design. Do not refresh their pins.
Historical v2 reproduction commit: `3aa7ee0780092266a63c7a16462523e694724624`
(maintainer supplied). Historical v1 reproduction commit: awaiting maintainer.
The v2 verdict remains final; see the separate v2 results document.

### R1' — Current production instructions

System messages equal the runtime production coding and reviewer instructions.
Pin their exact UTF-8 SHA-256 digests, including reviewer 1.1.0 and unchanged
coding text. Reuse v2's payload construction and verbatim fixture-language
constraints. All original task payloads remain identical to v2.

Rationale: measure the actual clarified product behavior under a new freeze.

### R3' — Two new held-out controls

Keep all seven v2 Phase B tasks. They are partly seen: r3 and h1 motivated the
product change. Add these independent deterministic controls, not instruction
tuning examples:

| Task | Requirement and expected result |
| --- | --- |
| review_heldout2 | s1 requires token_valid==1 AND expired==0 but ignores expired: blocking security; s2 requires 0 for negative values, else the value, but returns value unconditionally: blocking correctness; s3/s4 preserve values and must not be flagged |
| review_clean2 | c1 correctly checks token_valid==1 AND expired==0; c2/c3 preserve values: accept with no blocking findings |

Fixtures use only the v1 scalar Python subset. Expected maps remain in pack.py,
not requests. Reuse v2 matching semantics: wrong category means miss plus false
positive; duplicate or clean-reference findings do not earn credit. Any blocking
finding on review_clean2 fails. Nonblocking observations follow v2 clean controls.

Rationale: distinguish generalization from improvement on already seen defects.

### Unchanged R2, R4, R5 and R6

ADR-021 outer fences are presentation facts, not adherence failures. Signature
and refactor else rules remain unchanged. Phase A uses the same four tasks and
screening rule; at most two finalists enter B. Each of nine B tasks runs twice
with identical requests; a task must pass 2/2. Missing or duplicate repeats do
not pass. Phase A provenance must match the v3 manifest and pack.

`qualified_all_tasks` is the admission-eligibility gate: complete evidence for
the four A tasks and every B task passing both repeats. `heldout_only` reports
the two new tasks and their joint pass separately, informational only. There is
no review-only shortcut around this gate. Incomplete evidence is inconclusive;
complete failing evidence is MODEL_NOT_QUALIFIED. Admission effect is NONE.

At most 20 A chats or 36 B chats, one discovery per phase, 1024 output tokens,
60-second timeout, SYNTHETIC disclosure, no retries. Start spacing is monotonic,
default 20 seconds, choices 0/10/20/30/60. HTTP 429/503 stop the entire run;
other invocation failures stop that model. Closed discovery and pre-call refusal
reasons, external custody, suppressed unknown errors and optional separately
confirmed raw retention remain as v2. Credential length remains unavailable
through the existing opaque credential source; no new credential inspection.

The v3 manifest pins all v3 sources, this document, reused dependencies, both
instruction strings, ADR-021 and the recorded v2 manifest digest
`a5038d5a7a357c06f9ae0c3487b71a0663ffc0430dae06b9eeab56825920a1e9`.
Do not call v1 or v2 verify at HEAD. Historical source preservation is checked
against BASE, with the intentional production definition change excluded.
Placeholder values refuse live use as MANIFEST_NOT_FROZEN before credentials.
Only the maintainer emits hashes, reviews, saves and commits the freeze before
any live run. No hash is invented or computed by the implementation agent.

## Implementation plan

Edit only the production reviewer definition. Add v3 pack/scoring/freeze/runner,
new offline tests, this preregistration, the separate v2 evidence record and the
v3 validator. Import v2 prompts/scoring for old tasks and shared empty/passed
helpers. Bind copied invocation and runner orchestration to v3 without modifying
historical module globals. Add expected maps and generalize only new task scoring
and aggregate eligibility. No production schema, value or architecture changes.

Tests cover exact old/new instruction text and version, both new fixtures,
wrong-category misses/false positives, clean controls, all v2 behaviors with the
v3 pack, repeated calls, stops, pacing, refusal gates, freeze drift and admission
isolation. The validator runs Engineering reviewer and offline ForgeAI reviewer
regressions, then typing/lint/format/whitespace and a nonfailing manifest report.
Verification: NOT RUN — Awaiting user execution.

## Reused symbols and implementation boundaries

Locations refer to BASE. Historical files remain unchanged.

| Source | Reuse |
| --- | --- |
| `scripts/kisski_coding_eval_v2/__init__.py` | Repository Engineering source bootstrap |
| `scripts/kisski_coding_eval_v2/pack.py:75`, `:82` | instructions and prompt; eleven old tasks imported unchanged |
| `scripts/kisski_coding_eval_v2/scoring.py:19`, `:25`, `:110` | empty, old-task score, passed |
| `scripts/kisski_coding_eval_v2/scoring.py:134` | Repeatability adapted for 22 records and explicit all-task gate |
| `scripts/kisski_coding_eval_v2/frozen.py:44` | content and ManifestNotFrozen; never historical verify |
| `scripts/kisski_coding_eval_v2/invocation.py:22` | Copied only to bind v3 prompt/scorer; same governed call and disclosure |
| `scripts/kisski_coding_eval_v2/runner.py:55` onward | Orchestration adapted to v3 pack, manifest, reports and invocation |
| `scripts/kisski_coding_eval/runner.py:106`, `:122`, `:367` | selected, screening, reliability |
| `scripts/kisski_dev_screen/runner.py` | Closed status/refusal, pace, custody and save helpers |
| `experiments/kaggle/forgeai_model_quality_1/contracts.py:126`, `:178` | decode and review |

V2 invocation binds prompt/scorer at module scope; importing its invoke would
use v2 expected maps for new tasks. The local binding avoids modifying historical
globals. The v3 source inventory pins reused sources independently of historical
verification. No new public interface or dependency was introduced.

The unchanged Engineering test_reviewer.py has no exact-text/version assertion
to update. The new v3 test embeds the old production text and asserts the exact
single-sentence insertion, all remaining UTF-8 bytes and behavior_version 1.1.0.
The validator runs the unchanged Engineering reviewer suite as well.

The separate v2 results record contains the maintainer's per-task outcomes.
Historical v1/dev-screen reproduction hash is still pending: the follow-up
contained `<paste full hash>`. Resolve this metadata before freezing this document.

## Maintainer commands

Working directory: repository root. Prerequisites: existing locked Python 3.14
uv environment with development dependencies. The validator supplies source paths
to child processes; no installs, credentials or operator environment variables
are needed. ForgeAI checks use replay models and exclude real_docker and
real_sandbox; they do not qualify Docker, clean installation or live model quality.

Run the offline gate first and paste its results:

```powershell
uv run --locked --offline --no-sync python .\validate_forgeai_kisski_coding_model_evaluation_3.py
git diff --check
```

Expected: all phases pass; `V3 MANIFEST FROZEN: NO` is allowed with placeholders.
After local validation and preregistration review, emit and inspect the manifest:

```powershell
$v3Manifest = uv run --locked --offline --no-sync python -m scripts.kisski_coding_eval_v3.frozen --emit
if ($LASTEXITCODE -ne 0) { throw 'Manifest emission failed' }
$v3Manifest
```

After reviewing the output, save the captured emission as UTF-8 without BOM:

```powershell
[System.IO.File]::WriteAllText(
    (Join-Path (Get-Location) 'scripts/kisski_coding_eval_v3/manifest.json'),
    ($v3Manifest -join "`n") + "`n",
    [System.Text.UTF8Encoding]::new($false)
)
uv run --locked --offline --no-sync python .\validate_forgeai_kisski_coding_model_evaluation_3.py
git diff --check
```

Expected: `V3 MANIFEST FROZEN: YES`. Review and commit the slice and manifest
before any separately authorized live run. Verification checks bytes; committing
the reviewed freeze is a maintainer procedure. Never refresh pins after live
evidence to make verification pass.

Inert plans (no credentials or provider calls):

```powershell
uv run --locked --offline --no-sync python -m scripts.kisski_coding_eval_v3.runner --plan --phase A
uv run --locked --offline --no-sync python -m scripts.kisski_coding_eval_v3.runner --plan --phase B
```

Expected ceilings: A 20 chats, B 36 chats; default spacing 20 seconds. Live B
requires a matching v3 Phase A report. Historical v2 reports do not qualify.
