# FORGEAI-KISSKI-CODING-MODEL-EVALUATION-2

Status: PREREGISTERED RULES IMPLEMENTED; LOCAL VALIDATION PENDING; NOT FROZEN.
BASE: `8edc557f05a3c2ae412b67c08dbe3a7eea678b5a`.
Branch: `br-LegoAI-Comfy-ForgeAI-Gemma4-KISSKI`.
No live run is authorized by this document. Manifest placeholders block live use.

## Preregistered rules and rationale

### R1 — Production instructions

The system message is exactly `coding_definition().instructions` or
`reviewer_definition().instructions`, imported at runtime. SHA-256 of each UTF-8
instruction string is pinned independently in the v2 manifest. Drift fails
verification. For coding tasks, the full `Evaluation fixture language:` suffix
of the v1 task's system message moves verbatim into user constraints. This is
the v1 pack's existing target-name adaptation (each allowed Python file), not a
new paraphrase. All other fields of the eight original payloads stay unchanged.

Rationale: v1 measures paraphrased instructions. Production explicitly requires
unknowns and no blocking findings for insufficient evidence. Evaluation-only
Python restrictions belong in constraints, not in the production system text.

### R2 — Representation and adherence

One outer unlabelled or lowercase json fence accepted by ADR-021 does not fail
adherence. `fenced` is a boolean presentation observation. Malformed fences,
duplicate keys, schema, scope and language violations remain rejected; no repair,
search, retry or relaxation is added. Whole-response byte limits include fences.
Exact argument-name and refactor else checks, including their early returns,
remain as in v1.

Rationale: the production parser accepts this framing. Maintainer-reported
development evidence found otherwise-correct code failing only the fence rule.
Historical v1 results remain reportable under their original rules.

### R3 — Held-out review and false-positive controls

The eight v1 tasks are imported unchanged. Phase B adds:

| Task | Material and deterministic expectation |
| --- | --- |
| review_heldout | h1 permits role==2 OR active==1 instead of AND: blocking security; h2 adds one instead of returning unchanged: blocking correctness; h3/h4 preserve identity and must not be flagged |
| review_clean | k1 correctly requires authorized==1 AND exists==1; k2/k3 preserve identity; accept with no blocking findings; any blocking finding is a false positive |
| abstention_heldout | Database migration script and schema policy missing; insufficient_evidence, nonempty unknowns, no blocking findings |

All code fixtures obey the existing scalar Python subset. Expected category,
clean-reference, decision and abstention maps live in pack.py, never in requests.
Held-out review uses the v1 matching algorithm: category, blocking severity and
action first, then duplicate/multiple-match/clean-reference filtering. Labelling
h1 correctness earns a miss and a false positive. Clean-control nonblocking
observations are allowed; they are not blocking false positives. Original
abstention retains v1's stricter no-findings rule; the new task uses the specified
no-blocking-findings rule.

Rationale: independent defect and clean controls reduce dependence on the single
v1 review example and measure inappropriate certainty on new missing evidence.

### R4 — Repeatability and eligibility

Phase A remains four tasks, once each, at most five observed models. Screening
uses v1: all four complete, schema/adherence/scope/safety gates pass, at least
three acceptances. Phase B admits at most two screened finalists from a v2 Phase A
report with matching manifest and pack identity. No v1/dev-screen report qualifies.

Each of seven Phase B tasks runs twice, consecutively, with identical requests.
Both must pass every applicable dimension. Record 2_OF_2, 1_OF_2 or 0_OF_2,
plus attempted count and completeness; missing repeats never become passes.
Duplicate repeat identities are inconclusive. Final coding eligibility requires
all Phase A coding dimensions and every Phase B task to pass (both repeats).
Review-only eligibility requires both repeats of every Phase B reviewer task.
Incomplete/provider-failed evidence is inconclusive, not model-quality failure.
Passing means eligibility for separate admission review only: admission_effect NONE.

Rationale: one lucky answer is insufficient. Repeats are preregistered samples,
not retries after a failure. Completed but incorrect answers still receive their
second sample; invocation failure stops that model, and 429/503 stops all models.

### R5 — Operations and bounds

At most 20 chats in A and 28 in B, plus one discovery per phase. Output budget
1024, timeout 60 seconds, SYNTHETIC disclosure, one governed chat per invocation,
no retries/fallback/resume. Default start spacing is 20 seconds; choices are
0/10/20/30/60, measured monotonically across models. Pacing changes no request.
Ceiling plan duration is (chats-1)*interval, excluding last response duration.

Reuse SCREEN-2A closed HTTP status, discovery and pre-call refusal semantics.
429 means RATE_LIMITED; 503 means SERVICE_UNAVAILABLE; no next model is constructed.
Other invocation failures stop only that model. Unknown exceptions are suppressed;
effect is UNKNOWN except the existing WRONG_EVENT_LOOP guard proving NONE.
Discovery classification uses the enum value; outcome and bounded status persist.
No credentials, provider text or exception messages enter reports. Optional raw
synthetic retention requires its own typed gate and external custody; repeat
filenames are distinct. Credential-empty detection remains unavailable because
the source exposes no length metadata.

Rationale: distinguish availability from quality and avoid spending further calls
after account/service rejection. Model output remains data, never authority.

### R6 — Freeze before measurement

V2 has its own source inventory and manifest. Pins cover all v2 Python sources,
reused screen/qualification helpers, production definition/framing sources,
instruction strings, this preregistration, the v1 manifest digest
`3cd0e5a14f6ff9d2beba5cb1af9bcc6ac214637a7b3858ad3282bd0e51691ef6`
and ADR-021. Source bytes normalize CRLF to LF as v1 does; instruction strings
are hashed as exact UTF-8. Manifest cannot pin itself recursively.

The implementation agent computes no hashes. Placeholder manifest values are
intentional; live entry returns MANIFEST_NOT_FROZEN before credential access.
The maintainer emits, reviews and commits the manifest before any live run.
`--emit` prints only JSON; it never overwrites or accepts a manifest automatically.
Later drift requires explicit review/versioning, not silent pin refresh.

Rationale: freeze the acceptance rule before observing live v2 answers. V1,
SCREEN-2A, production, contracts, examples and historical reports stay untouched.

## Implementation and verification plan

Only new `scripts/kisski_coding_eval_v2/`,
`scripts/tests/test_kisski_coding_evaluation_v2.py`, this document and
`validate_forgeai_kisski_coding_model_evaluation_2.py` are allowed.
No new dependencies, public interfaces or production architecture changes.
Reuse v1 tasks, contracts, scalar interpreter, screening and reliability; reuse
screen status/custody helpers. Copy invocation only to bind v2 prompt/scorer;
generalize review scoring only for the new expected maps. Source citations will
accompany those changes. Tests use synthetic answers, fake hosts and fake clocks.

Verification: **NOT RUN — Awaiting user execution**. No live model quality claim.

## Source reuse and implementation boundaries

Locations refer to BASE; no source below was modified.

| Source | Symbols reused or narrowly adapted |
| --- | --- |
| `scripts/kisski_coding_eval/pack.py:40`, `:83`, `:152` | Task, original eight TASKS, prompt payload |
| `scripts/kisski_coding_eval/scoring.py:101`, `:129` | empty and score, including scalar checks and original review/abstention rules; new maps generalize only the reviewer branch at 159–193 |
| `scripts/kisski_coding_eval/runner.py:106`, `:122`, `:367` | selected, screening, reliability |
| `scripts/kisski_coding_eval/frozen.py:21` | verify; v1 source/canonical pins are checked, never refreshed |
| `experiments/kaggle/forgeai_model_quality_1/contracts.py:126`, `:178` | decode and review; coding at 146 remains used through the frozen scorer |
| `scripts/kisski_dev_screen/diagnostics.py:40`, `:148` | unevaluated and diagnose for original tasks after accepted framing; no FENCED_JSON failure introduced into v2 |
| `scripts/kisski_dev_screen/runner.py:149`, `:158`, `:171`, `:194`, `:217` | outside_repository, http_status, closed_http_status, pace, save; refusal enums/parser also imported |
| `scripts/kisski_dev_screen/invocation.py:21` | Copied invocation body with only v2 prompt/scorer/empty bindings; original mirror unchanged |
| `packages/legoai-engineering/src/legoai_engineering/coding/definition.py:9` and `reviewer/definition.py:9` | Exact runtime instruction strings |
| `packages/legoai-engineering/src/legoai_engineering/_json_document.py:19` | Test oracle for ADR-021 accepted/rejected framing; no private production parser imported by the runner |

The new runner adapts SCREEN-2A orchestration for v2 manifest identity, screened
finalists and repeated task IDs. It uses one loop and independent custody per
model, with four slots in Phase A or fourteen in Phase B. Raw retention filenames
include the repeat number. Phase A import copies only a closed score projection;
untrusted free-text report extras are never echoed or persisted. A local report
is still operator evidence, not authenticated authority. Source/manifest identity
prevents accidental mixing of evaluation versions, not malicious score editing.

The candidate inventory is v1's OBSERVED tuple; there is no new mutable candidate
file. Maximum 5 Phase A models, maximum 2 screened Phase B models. Pacing helper
logic is imported rather than copied because its behavior is identical; v2's
runner separately applies the same whole-run 429/503 stop. No token override is
offered. Report classification and per-task repeatability are eligibility evidence
only. Absent repeats include an attempted count and complete=false.

## Maintainer commands and freeze sequence

Working directory: repository root. Prerequisites: existing locked Python 3.14 uv
environment and development dependencies. V2 package initialization adds the
repository's `packages/legoai-engineering/src` to its process import path; the
root project does not install that package. The validator supplies the same
source path through PYTHONPATH and MYPYPATH to its child processes. This loads
the production sources pinned by the manifest without changing dependencies.
No installs, operator-set environment variables or live credentials
are needed for these commands. Synthetic tests compute temporary pins only when
the maintainer executes them. The implementation agent ran no checks or hashes.

First run local verification and paste its results before further changes:

```powershell
uv run --locked --offline --no-sync python .\validate_forgeai_kisski_coding_model_evaluation_2.py
git diff --check
git status --short
```

The initial expected manifest report is `V2 MANIFEST FROZEN: NO`. This is allowed
by the local validator; the live runner must still refuse MANIFEST_NOT_FROZEN.
Expected validator completion:

```text
FORGEAI-KISSKI-CODING-MODEL-EVALUATION-2 LOCAL CHECKS PASSED; V1 AND DEV SCREEN UNCHANGED; NO PROVIDER CALLS; NO ADMISSION EFFECT
```

After checks pass and the preregistration/source is reviewed, emit the manifest:

```powershell
uv run --locked --offline --no-sync python -m scripts.kisski_coding_eval_v2.frozen --emit
```

Review that JSON. To capture a fresh emission without a UTF-8 BOM (PowerShell):

```powershell
$v2Manifest = uv run --locked --offline --no-sync python -m scripts.kisski_coding_eval_v2.frozen --emit
if ($LASTEXITCODE -ne 0) { throw 'Manifest emission failed' }
[System.IO.File]::WriteAllText((Join-Path (Get-Location) 'scripts/kisski_coding_eval_v2/manifest.json'), ($v2Manifest -join "`n") + "`n", [System.Text.UTF8Encoding]::new($false))
uv run --locked --offline --no-sync python .\validate_forgeai_kisski_coding_model_evaluation_2.py
```

Expect `V2 MANIFEST FROZEN: YES`. Review the manifest diff and commit the reviewed
v2 slice including the manifest before any separately authorized live run.
No source, instruction, ADR or preregistration edits after freezing without a
new explicit review. Committing the freeze is a maintainer procedure; verification
checks bytes, not Git commit status. Historical v1/dev-screen evidence is unchanged.

Inert plan commands (no credential prompts or provider calls):

```powershell
uv run --locked --offline --no-sync python -m scripts.kisski_coding_eval_v2.runner --plan --phase A
uv run --locked --offline --no-sync python -m scripts.kisski_coding_eval_v2.runner --plan --phase B
```

Expected ceilings: A 20 chats, B 28 chats; default minimum spacing 20 seconds.
Phase B live entry requires a matching v2 Phase A report, not these plans or a
development-screen report. No live command is part of local verification.
