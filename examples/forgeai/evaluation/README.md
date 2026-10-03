# ForgeAI-LQ1: live-model evaluation harness

> **THIS IS NOT A PRODUCTION BENCHMARK.** It measures the unchanged ForgeAI-3
> application on a small frozen fixture set, with the recorded model, hardware
> and revisions only.

**Status:**
- **Harness validated** (2026-10-01). All `validate_forgeai_lq1.py` phases
  passed, including real-Docker fixture validity: every template fails its
  hidden tests, and every reference solution succeeds and passes them.
- **Live baseline recorded** (2026-10-01) for `llama3.2:latest`, as a
  measurement, not a pass/fail result. See [Recorded baseline](#recorded-baseline-llama32latest-2026-10-01),
  including its metadata erratum.
- **LQ1.1 live-run preflight validated** (2026-10-01). All 32 phases of
  `validate_forgeai_lq1.py` passed, including the new phases 13b–13d:
  - 13b: preflight success and recording of the observed version;
  - 13c: unreachable server, missing model and digest mismatch fail closed,
    with zero runs and no report;
  - 13d: replay mode needs no preflight.

  These ran against a local HTTP stub; no live model was contacted. Live
  runs now verify the serving Ollama before fixture 1 and record the
  *observed* server version; see [Live-run preflight](#live-run-preflight-lq11).
  The recorded `llama3.2` baseline predates LQ1.1.
- **LQ1.2 content-free failure diagnostics validated** (2026-10-01). All 42
  phases of `validate_forgeai_lq1.py` passed, including the new phases 13e–13m
  and 14c:
  - 13e: the closed taxonomy;
  - 13f/13h: every Coding and Reviewer category, each agreeing with ForgeAI's
    own parser verdict;
  - 13g: fenced JSON remains rejected;
  - 13i/13j: Ruff rule and pytest failure-kind extraction;
  - 13k: the aggregate is the fold of the run rows, and schema 2 keeps every
    schema-1 metric;
  - 13l: sentinel privacy;
  - 13m: observer non-interference (equal `TaskResult`, byte-identical
    requests);
  - 14c: extraction from real check-image output in Docker.

  New reports (schema 2) say *why* a Coding or Reviewer reply was rejected
  and *which* Ruff rules or pytest failure kinds failed; see
  [Failure diagnostics](#failure-diagnostics-lq12). Validation used replay and
  local HTTP stubs only; no live model was contacted. The three recorded
  baselines (schema 1) predate LQ1.2 and stay unchanged.
- **Diagnostic live measurement** (2026-10-01, `qwen2.5-coder:7b`, schema 2,
  not committed):
  - Coding: 11 of 12 replies `response_not_json`, all 11 Markdown-fenced; the
    one unfenced reply was `valid`.
  - Reviewer: the single reply was fenced, `response_not_json`.
  - 0 classifier disagreements.

  This evidence led to [ADR-021](../../../adrs/ADR-021.md).
- **ENG-JSON-1 (ADR-021) locally qualified** (2026-10-02;
  `validate_engineering_json_document.py`, all 30 phases, including the full
  LQ1 harness suite, 193 tests). Engineering
  Agents now also accept one exact Markdown fence (label `json` or none)
  around the JSON document. The harness mirrors that stage and reports
  `representation` and `fence_label`. **Reports move to schema 3:**
  `response_not_json` no longer includes exactly fenced documents, so schema-2
  and schema-3 rates are not comparable. Schema-1 and schema-2 reports stay
  unchanged.
- An earlier attempt requested a model that was not installed in the local
  Ollama. Every run was a provider-side `MODEL_FAILED`, which measured
  configuration, not model behavior, so it is not a baseline.

## Post-ADR-021 measurement and LQ1.3

The operator confirmed the full post-ENG-JSON-1 `validate_forgeai_lq1.py`
pass. The 2026-10-02 schema-3 measurement used `qwen2.5-coder:7b`, Ollama
0.35.0, commit `5bad993`, fixture/hidden revisions 1, N=3 (12 runs).
The representation blocker was removed: Coding had 8 valid and 5
`change_fields_invalid` replies; Reviewer had 3 valid and 1 `finding_invalid`.
Eight runs passed hidden tests, but only two succeeded and passed hidden
tests. Four runs ended in `CHECKS_FAILED`. One live rework reached a second
Coding attempt, rejected as `change_fields_invalid`. No implementation defect
was established. This is a failure-shape measurement, not a benchmark or
qualification verdict. Raw reports remain uncommitted and immutable.

**ForgeAI-LQ1.3: locally qualified (operator-confirmed 2026-10-02).** Evaluation-only
change-entry diagnostics retain the existing `change_fields_invalid` category
and schema 3. Additive features record `change_field_failure` (missing_only,
unexpected_only, missing_and_unexpected), zero-based `change_entry_index`,
`missing_required_field_count`, `unexpected_field_count`,
`expected_field_count`, and `actual_field_count`. They are null outside this
failure stage. Existing `missing_fields` / `unexpected_fields` remain
top-level counts. The invocation's existing `attempt` preserves rework identity.

Both CREATE and UPDATE require exactly path, operation, content and reason;
no keys are optional. The observer records counts only at the first rejected
entry, before validating its path or operation; later entries are not examined.
Value-type failures retain their existing categories. No operation context or
model-generated key names are recorded. Aggregates `change_field_failures`
and `per_fixture_change_field_failures` fold invocation records only. `other`
means an old record lacks detail, not a new parser stage. Historical reports
cannot reveal the five past failures more precisely and are never backfilled.

Reviewer diagnostics stay unchanged: `finding_invalid` combines key equality
and constructor validation, so the same technique could describe only its
key-set subset in a separately scoped follow-up. No contract relaxation,
runtime, prompt, provider, gate or retry change is part of LQ1.3.

Focused assistant checks passed: 23 LQ1.3 tests and 92 existing output/report
regression tests; Ruff lint/format and mypy passed. The operator subsequently
provided the complete `uv run python .\validate_forgeai_lq1.py` output, ending
in `FORGEAI-LQ1 HARNESS VALIDATION PASSED`. All phases passed, including
LQ1.3 phases 13n-13u, architecture checks, real-Docker fixture validity and
check diagnostics, mypy, Ruff, and 89 ForgeAI regression tests. Runtime source
change guards passed. The validator used replay and local HTTP stubs; it did
not contact a live model. This qualifies the harness, not live model quality.

## Purpose

ForgeAI-1/2/3 are **architecture-qualified with replay models**. That proves
the flow, governance, sandboxed checks, review and bounded rework work with
recorded model outputs. It says nothing about how well a **live** model
codes, reviews or reworks.

LQ1 measures that separately:

- it provisions fresh fixture repositories;
- it runs the **unchanged** ForgeAI-3 flow (`forgeai.composition.run_task`)
  with one operator-selected binding;
- it then checks each result against **hidden acceptance tests** the
  application never sees;
- it reports typed metrics.

It changes no ForgeAI or LegoAI runtime code. It adds no quality threshold:
the first live run is a **baseline measurement**, not a release gate.

| | Architecture qualification (ForgeAI-1/2/3) | Live evaluation (LQ1) |
| --- | --- | --- |
| Model | Replay (recorded outputs) | One admitted live binding (Ollama) |
| Question answered | Does the flow behave as specified? | How does the real model behave on frozen tasks? |
| Result | Pass or fail | Measurements only |
| Oracle | Deterministic tests | Hidden acceptance tests |

## Layout

This directory is evaluation infrastructure only. It is **not** in the
installed `forgeai` wheel.

| Path | Contents |
| --- | --- |
| `manifest.json` | Fixture-set name, `revision`, `hidden_revision`, and per-fixture and set digests |
| `fixtures/<id>/repository/` | Template repository: `src/`, `tests/` (the visible tests) and `pyproject.toml` |
| `fixtures/<id>/task.json` | Category, objective, targets and constraints (the `TaskRequest`) |
| `fixtures/<id>/reference_proposal.json` | Known-good Coding output, for **replay self-tests only**; never given to a live model |
| `hidden/<id>/test_acceptance.py` | Hidden acceptance tests, the operator-held oracle |
| `replay/review_accept.json` | Recorded reviewer output for replay mode |
| `forgeai_eval/` | Harness: fixtures, hidden tests, runner, metrics, report, live-run preflight, reply observers and failure diagnostics |
| `run.py` | Command for replay self-demo and the live baseline |
| `tests/` | Harness self-tests |

## Fixture set: `forgeai-lq1`, revision 1, hidden-test revision 1

| Fixture | Category | Task |
| --- | --- | --- |
| `stock-validation` | Input validation / error handling | Reject invalid `reserve` requests with `ValueError` (the ForgeAI demo task) |
| `pager-boundaries` | Boundary / off-by-one | 1-based pages; `page_count` rounds up |
| `temperature-units` | Missing branch / edge case | Kelvin, case-insensitive units, reject unknown units |
| `text-slug` | New module (CREATE) | Create `textkit.slug.slugify` and its tests |

**Scope.** Every fixture is a small `src/` + `tests/` Python project within
ForgeAI's limits:
- two operator-supplied targets;
- files of at most 8 KiB, and within the reviewer's 4 KiB material bound;
- no deletes, network, installs or target discovery.

**Revisions are verified.** `load_fixture_set` recomputes line-ending
normalized SHA-256 digests of each template, task and hidden-test tree, and
refuses to run if any differs from `manifest.json`. Changing a fixture needs
a new `revision`; changing hidden tests needs a new `hidden_revision`.
Results from different revisions must not be compared.

## Hidden-test isolation

The hidden tests are the independent oracle, so they never reach ForgeAI:

- they live under `hidden/`, outside every template, and are never copied
  into a provisioned repository;
- they are not in `TaskRequest`, the targets, the editable allowlist,
  ForgeAI's `CheckInputPolicy` or its check plan;
- they appear in no Coding evidence, no review material and no model request;
- they run only **after** ForgeAI returns its final `TaskResult`.

**How they run.** An in-memory `HiddenOverlay` presents the evaluated
repository plus a virtual `acceptance/` directory to the existing
`SandboxedEngineeringChecks`. That adapter copies them into **one ephemeral
sandbox execution** of `pytest acceptance`. The evaluated repository is never
modified, and hidden tests never run on the host.

**If ForgeAI applied no change** (for example it was rejected, or the model
or proposal failed), the hidden tests are recorded as `not_run`.

`tests/test_lq1_isolation.py` proves all of this at the real boundaries.
- A recording replay model inspects every model request.
- Recording sandboxes inspect every file ForgeAI's checks and the oracle
  send.
- A sentinel string that exists only in hidden tests is searched for
  everywhere.
- The test asserts the oracle's sandbox call comes strictly after all of
  ForgeAI's calls.

## Metrics

Metrics are computed only from typed `TaskResult`, `AttemptEvidence`,
`ReviewResult` and `CheckResult` values plus harness timings. **Nothing is
parsed from CLI text.** Exact definitions are in every report, and in
`forgeai_eval/metrics.py`:

| Group | Metrics |
| --- | --- |
| Completion | Succeeded, rejected and failed rates over all runs |
| Independent correctness | Hidden pass rate; succeeded-and-hidden-pass rate; succeeded-but-hidden-fail rate |
| Structured output | Coding and reviewer output-invalid rates |
| Checks | Per-kind outcome distributions for attempt 1 and attempt 2 |
| Review | Decision distributions for review 1 and review 2 |
| Reviewer vs hidden (**MODEL-JUDGE MEASUREMENT**) | Final review × hidden outcome matrix; `accept_but_hidden_fail` and related counts |
| Rework | Invocation rate; recovery rate (review 1 `changes_required`, then final `accept` and hidden pass); failed-recovery categories |
| Execution | Model invocations per run; run and hidden-test seconds; failure histogram; `UNKNOWN` model-effect count; per-call latency **unavailable** |
| M8.4 signals (**MODEL-JUDGE MEASUREMENT**) | Testing-category findings; hidden fails with no blocking testing finding |

**How to read them:**
- **Reviewer figures are model-judge measurements.** The Independent Reviewer
  is itself a model; its `ACCEPT` is not ground truth.
- **`accept_but_hidden_fail` is a count of observations,** not a calibrated
  false-positive rate.
- **The oracle is narrow.** Hidden tests cover only the behaviors they
  encode.
- **Rates carry their counts.** Every rate records its numerator and
  denominator; an empty denominator is reported explicitly as unavailable.

## Failure diagnostics (LQ1.2)

**Why.** The first three live measurements ended mostly in
`PROPOSAL_INVALID` (27 of 36 Coding calls) and `CHECKS_FAILED`. Those labels
are opaque: they cannot tell a Markdown-fenced reply from a wrong field name,
or an import-order lint from a failing assertion. A later structured-output
or check-policy decision needs that distinction as evidence, not as a guess.

**What it measures.** LQ1.2 measures the **existing** contracts. It changes no
prompt, parser, schema, gate, retry or model setting.

**Representation (ADR-021, schema 3).** The classifier mirrors the
engineering decoder exactly:
- one exact fence (opening line ` ``` ` or ` ```json `, closing line ` ``` `)
  is decoded, and the enclosed document is classified;
- every other fenced or prose reply is `response_not_json`, exactly as
  ForgeAI rejects it.

Each reply records three representation features:
- `representation`: `raw`, `fenced` (an exact ADR-021 envelope) or `none` (a
  fence that is not ADR-021's);
- `fence_label`: `json`, `none` or `other`, or null when the reply is not
  fenced;
- `markdown_fence`: whether the reply starts with a fence.

Schema-2 reports predate ADR-021: there, every fenced reply was
`response_not_json`.

**Coding reply categories.** These are the first stage that rejected the
reply, in the CodingAgent's own order:

| Stage | Categories |
| --- | --- |
| Agent output contract | `output_limit`, `output_text_invalid` (empty, blank or not UTF-8) |
| JSON | `response_not_json`, `duplicate_json_key`, `top_level_not_object`, `top_level_fields_invalid` |
| Changes | `changes_not_bounded_array`, `change_entry_not_object`, `change_fields_invalid`, `path_invalid`, `operation_invalid`, `path_not_requested_target`, `operation_target_mismatch`, `content_invalid`, `reason_invalid` |
| Change set | `changes_empty`, `duplicate_change_target`, `changeset_invalid` |
| Narrative and limits | `summary_invalid`, `narrative_invalid` (risks/unknowns), `content_limit`, `proposal_constraint_invalid` |
| Accepted | `valid` |

**Reviewer reply categories:** `output_limit`, `output_text_invalid`,
`response_not_json`, `schema_invalid`, `finding_invalid`, `decision_invalid`,
`decision_inconsistent` (a decision that contradicts its blocking findings),
`valid`.

**Assigned when reconciling with ForgeAI's evidence:**
- `model_failure`: ForgeAI recorded a model failure, whatever the transport
  saw.
- `classifier_disagreement`: the classification disagrees with ForgeAI's own
  verdict, or with the parsed proposal or review (compared in memory by
  one-way fingerprint). It is counted, never hidden.
- `observation_unavailable`: the call could not be matched to evidence.

**Check diagnostics.** These are parsed from the bounded check output ForgeAI
already holds:
- **Ruff:** rule codes only (`E501`, `I001`, `F401`, …, or `invalid-syntax`),
  reconciled with Ruff's own `Found N errors.` total. Otherwise the check is
  `RUFF_DIAGNOSTIC_UNAVAILABLE`.
- **pytest:** failure kinds only: `assertion_failure`, `did_not_raise`,
  `exception_failure`, `setup_error`, `import_error`, `collection_error`,
  `no_tests`, `timeout`, `infrastructure_error`, `pytest_error`,
  `unknown_test_failure`. They are reconciled with pytest's own failed and
  error totals; otherwise `PYTEST_DIAGNOSTIC_UNAVAILABLE`.

The patterns are pinned to the qualified image (ruff 0.16.8, pytest 9.1.1)
and checked against it in real Docker. The metrics above remain typed-only;
only these diagnostics read tool output.

**How replies are observed.** No reply text enters ForgeAI evidence, and
none is stored.
- **Live:** LegoAI has no public seam to wrap the admitted Ollama ModelPort,
  so a local `ChatObserver` sits between ForgeAI's **real, unchanged**
  adapter and Ollama. It forwards `POST /api/chat` byte-for-byte and returns
  Ollama's status and body unchanged. It never originates a request.
- **Replay:** `ObservingModel` wraps the harness-owned model and returns the
  original result object.
- **Either way,** each reply is classified in memory, and only its category
  and structural counts are kept.

**One documented deviation.** If Ollama refuses connections mid-run, a
direct call would record a NONE model effect. Through the observer it
becomes UNKNOWN, which is more conservative, and is counted as an
`upstream_unreachable` transport. The preflight makes this rare.

**Content-free policy.** Reports hold categories, counts, booleans and closed
rule or kind identifiers only. They contain no reply text, generated code,
prompts, repository source, hidden-test content, Ruff or pytest messages,
test names, tracebacks or host paths. Sentinel tests enforce this.

**Report schemas 2 and 3.** Schema 2 added a per-run `diagnostics` record and
a top-level `diagnostics` aggregate. The aggregate is computed only by folding
the run records (`fold`), so it can always be re-derived from the report
itself.

Schema 3 (ADR-021):
- changes the meaning of `response_not_json`;
- adds the `representation` and `fence_label` features;
- adds `representation_counts` and `fence_label_counts` per Agent.

Every schema-1 field is unchanged. Schema-1 and schema-2 reports are
historical evidence; the harness never reads or rewrites them.

**Diagnostics do not change behavior.** Tests run ForgeAI's real Ollama
adapter against a scripted Ollama, direct and through the observer, and
require an equal `TaskResult` projection and byte-identical requests. The
scenarios are success, invalid replies, provider errors and adapter timeout.

## Replay self-test (harness validation, no model quality)

```powershell
uv run python .\validate_forgeai_lq1.py      # from the repository root
```

The validator never contacts a live model. Its checks:

- **Replay scenarios with exact expected totals:** success with hidden pass;
  success with hidden fail; rework recovery; proposal failure; reviewer
  output failure; deterministic check failure; hidden-test infrastructure
  failure.
- **Harness behavior:** isolation, report completeness, JSON/Markdown
  consistency, and the unreachable-provider path.
- **Architecture** checks.
- **Real Docker:** every fixture's template **fails** its hidden tests, and
  its reference solution **succeeds and passes** them.
- **LQ1.2 diagnostics:**
  - the closed taxonomy;
  - every Coding and Reviewer category, each agreeing with ForgeAI's own
    parser verdict;
  - fenced JSON stays rejected;
  - Ruff and pytest extraction, including real-Docker output;
  - aggregate = fold of run rows;
  - sentinel privacy tests;
  - observer non-interference.
- **ForgeAI-3 regressions.**

A replay demo writes a report too. It is harness evidence only:

```powershell
cd examples/forgeai
uv run python evaluation/run.py replay --output lq1-replay
```

## Live baseline procedure (maintainer only)

1. Start Docker Desktop and Ollama, and pull the chosen model.
2. State the model you intend to measure: its exact installed name (with
   tag, as `ollama list` shows it) and its full digest as
   `sha256:<64 hex digits>`. Read the digest from Ollama's
   `GET /api/tags` (`ollama list` shows only a 12-character prefix).
3. From `examples/forgeai`, run:

   ```powershell
   uv run python evaluation/run.py live `
     --model <model-name:tag> --model-digest sha256:<64-hex> `
     --hardware "<cpu/gpu/ram class>" --repetitions 3 --output lq1-baseline
   ```

   Use at least 3 repetitions (N ≥ 3). Missing or malformed arguments abort
   with exit code 2 before any request or run. There is no
   `--ollama-version`: the harness observes the version itself.
4. Share `lq1-baseline/report.json` and `report.md`. They contain
   identifiers, enums, counts and timings only: no source, prompts, model
   output, environment or host paths.

**What a report records:** mode, provider, binding, the verified model name
and digest, the **observed** Ollama server version, ForgeAI commit (marked
`+dirty-runtime` if runtime sources are modified), fixture and hidden-test
revisions and digests, hardware class (operator-supplied), platform, start
time and N.

## Live-run preflight (LQ1.1)

Before fixture 1, live mode asks the local Ollama server what is actually
serving. It is read-only and Ollama-specific (the only live binding LQ1
uses):

| Request | Verified |
| --- | --- |
| `GET /api/version` | The server is reachable and reports a version; that **observed** version goes into the report |
| `GET /api/tags` | An installed model has **exactly** the requested name, and its full digest equals `--model-digest` |

The preflight never pulls, creates, deletes, generates or chats, and never
uses a proxy. It does not retry and has no fallback. Matching is exact:
no tag completion (`llama3.2` is not `llama3.2:latest`), no substitute tag
or quantization, and no partial-digest match.

**On failure**, the command prints the reason to stderr, exits **3**, runs
**zero** ForgeAI tasks and writes **no** `report.json` or `report.md`:

| Failure | Meaning |
| --- | --- |
| `OLLAMA_UNREACHABLE` | No HTTP answer from `--ollama-url` (refused, timed out, network error) |
| `OLLAMA_RESPONSE_INVALID` | An answer that is not the expected JSON: HTTP error, no version, no models list, a duplicated or non-64-hex digest, or over 1 MiB |
| `MODEL_NOT_INSTALLED` | No installed model has exactly the requested name |
| `MODEL_DIGEST_MISMATCH` | The named model is installed with a different digest |

These are evaluation-harness setup failures, not ForgeAI `TaskFailure`
values; ForgeAI never starts. Real provider failures during the run itself
are still recorded per run as `MODEL_FAILED`.

**Residual gap.** The check happens once, before fixture 1. If the operator
upgrades or swaps the model while the run is in progress, the preflight
cannot see it. Do not change Ollama during a baseline.

## Recorded baseline: `llama3.2:latest` (2026-10-01)

> **MEASUREMENT, NOT PASS/FAIL. NOT A PRODUCTION BENCHMARK.** One small
> local model on four frozen tasks, N = 3. It is not comparable across
> models, revisions or hardware.

**Identity**

| Key | Value |
| --- | --- |
| Model | `llama3.2:latest`, digest `sha256:a80c4f17acd55265feec403c7aef86be0c25983ab279d83f3bcd3abbcb5b8b72` (3.2B, Q4_K_M) |
| Provider | Ollama, native `/api/chat`, no JSON `format` constraint, server-default context of 4096 tokens |
| Ollama | **0.35.0 served the run**; the report records `0.34.4` (see the erratum) |
| ForgeAI commit | `cde17fbcf69c90aa41d40ef0b5e72a68cc29b61f` (no `+dirty-runtime`) |
| Fixture set | `forgeai-lq1` revision 1 (`sha256:e547108c…6b64c`), hidden revision 1 (`sha256:556ed8e1…e3ac1`) |
| Hardware / platform | Intel x86-64 laptop CPU, 16 GB RAM, no discrete GPU; Windows 11 (AMD64) |
| Runs | 4 fixtures × 3 repetitions = 12; total 1345 s |
| Report | `report.json` SHA-256 `70e4a87d4e4df06b51c5e8c65b8ffa0c62da7ba5c304c440399485241fa4f3f6` (kept by the maintainer; not committed) |

**Erratum: Ollama version.** The operator passed `--ollama-version 0.34.4`,
so `report.json` records that value. However, Ollama's server log shows it
was upgraded and restarted as `0.35.0` at 13:20 local time (11:20 UTC), and
the run started at 12:13:08 UTC. The run was therefore served by **0.35.0**.
The report file is evidence and is left unedited; this README carries the
correction. At the time, the harness did not query the server version; the
LQ1.1 preflight closes that gap. A re-run with the correct value would produce a clean record.

**Results** (counts are numerator/denominator)

| Metric | Value |
| --- | --- |
| Disposition | SUCCEEDED 0/12, REJECTED 0/12, FAILED 12/12 |
| Hidden pass rate | 0/12. Outcomes: `not_run` 10, `failed` 2 |
| Succeeded and hidden pass | 0/12 |
| Succeeded but hidden fail | unavailable (0 succeeded runs) |
| Coding output invalid | 10/12 Coding invocations |
| Reviewer output invalid | 1/1 review invocations |
| Review 1 distribution | `not_completed:output_invalid` 1, `not_run` 11; no `accept`, `changes_required` or `insufficient_evidence` |
| Reviewer vs hidden (MODEL-JUDGE MEASUREMENT) | One observation: `output_invalid` × hidden `failed`. No ACCEPT occurred, so `accept_but_hidden_fail` is 0 by absence, not by evidence |
| Rework | Invocation 0/12; recovery unavailable (0/0) |
| Failure histogram | `PROPOSAL_INVALID` 10, `CHECKS_FAILED` 1, `REVIEW_OUTPUT_INVALID` 1; `MODEL_FAILED` 0 |
| Model invocations | 13 in total (1–2 per run); `UNKNOWN` model effects 0 |
| Run wall-clock | min 35.8 s, mean 110.9 s, max 215.7 s; per-call latency unavailable |
| Hidden-test wall-clock | 4.5 s and 5.4 s for the two executed oracles |
| M8.4 signals (MODEL-JUDGE MEASUREMENT) | Testing findings 0; hidden fail without a testing blocker 2 |

**Per fixture**

| Fixture | Failures | Note |
| --- | --- | --- |
| `stock-validation` | `PROPOSAL_INVALID` ×2, `CHECKS_FAILED` ×1 | The one valid proposal failed the visible `ruff_check` and `pytest` (mypy passed); the hidden tests failed |
| `pager-boundaries` | `PROPOSAL_INVALID` ×3 | No change applied |
| `temperature-units` | `PROPOSAL_INVALID` ×2, `REVIEW_OUTPUT_INVALID` ×1 | The one valid proposal passed every visible check, but the hidden tests failed; the reviewer output was invalid |
| `text-slug` | `PROPOSAL_INVALID` ×3 | No change applied (CREATE task) |

**Observations** (descriptive only)

1. **Structured output is the dominant failure.** Ten of twelve runs ended
   before any effect, because the Coding output did not validate as a
   proposal. Reports carry no model output by design, so the reason within
   each output is not recorded.
2. **The context window is excluded as the cause.** Ollama's log shows no
   truncation for any chat request in the run window: `truncated = 0`, with
   at most 1,051 tokens per request against the 4096-token context.
3. **The visible checks are not a sufficient oracle.** In `temperature-units`
   rep 2, a change passed `ruff_check`, `mypy` and `pytest` yet failed the
   hidden tests. The reviewer, the only remaining gate, produced invalid
   output, so the run correctly ended FAILED rather than SUCCEEDED.
4. **Rework was never reached.** By design, ForgeAI-3 reworks only after a
   completed review returns `CHANGES_REQUIRED`. Here, every run stopped
   earlier (invalid proposal, failed checks or invalid review), so this
   baseline gives no evidence about rework behavior.
5. **Fail-closed behavior held.** No run succeeded with failing hidden
   tests, and no `UNKNOWN` model effect or harness crash occurred.

**Limitations of this baseline.** It covers a single 3B quantized model, CPU
only and N = 3. The Ollama version is misrecorded in the report (see the
erratum). It has no per-call latency. Because no review completed, the
reviewer cannot be characterized. This baseline sets no threshold.

## Limitations

- **Not a benchmark.** It is not a production benchmark, a model leaderboard
  or a comparison between models. LQ1 records one baseline model.
- **Narrow scope.** Four small Python tasks cannot characterize general
  coding ability. With small N, rates are descriptive only.
- **The reviewer is a model judge,** and the hidden tests are an oracle only
  for what they encode.
- **No per-call latency.** Per-model-call latency is not observable through
  the public APIs, so it is reported as unavailable; LQ1 adds no tracing.
- **Model invocations are counted from recorded evidence.** For replay they
  match the replay model's call counter.
- **Targets are operator-supplied.** Target discovery is out of scope.
- **Diagnostics name a stage, not an intent.** A category is the first
  contract stage that rejected a reply. Stage *order* mirrors the private
  parsers; the accept/reject verdict comes from the real public validators
  and is cross-checked against ForgeAI on every live call. Mypy detail is not
  collected (mypy passed every applied live change so far).
- **Windows + Docker Desktop only**, the qualified sandbox scope.


## Post-LQ1.3 measurement and LQ1.4

The 2026-10-03 live measurement used qwen2.5-coder:7b, Ollama 0.35.1,
fixture/hidden revisions 1, N=3 (12 runs). Coding: 4 valid,
6 change_fields_invalid, 2 response_not_json. All six field failures were
missing_only, entry 0, one missing, zero unexpected, expected 4 / actual 3:
stock-validation 2, pager-boundaries 2, text-slug 2, temperature-units 0.
Reviewer: 2 finding_invalid. CHECKS_FAILED: 2. Hidden: 4 passed, 8 not_run;
successful + hidden-pass: 0; rework: 0. No implementation defect established.
Ollama changed from 0.35.0 to 0.35.1, so aggregate differences cannot be
attributed solely to harness revisions. This is a measurement, not a benchmark.

**ForgeAI-LQ1.4 locally qualified (operator-confirmed 2026-10-03).** Evaluation-only
`missing_required_fields` adds a JSON array selected solely from the
repository-owned required-key vocabulary, ordered path, operation, content,
reason. It is null outside exact-key rejection, and empty for unexpected-only
failures. Only the first rejected entry is described; index and attempt are
preserved. Unexpected names are never recorded, only their count.
`missing_required_field_counts` and `per_fixture_missing_required_field_counts`
fold invocation records (each omitted field once per invocation); zero counts
are omitted. Markdown adds a Missing required fields column. Schema stays 3.
Historical absent detail means unavailable, not no omissions; reports are
immutable and cannot be backfilled. Runtime, parser, prompts, Reviewer,
provider settings, checks and rework are unchanged. No dependencies added.
Validate with `uv run python .\validate_forgeai_lq1.py`; focused LQ1.4 phases
13v-13ad preserve all earlier phases and require no live model. No new live
measurement or contract change is authorized by this slice.

Focused assistant verification: 140 tests passed (25 new LQ1.4 cases plus
115 existing diagnostic cases), using replay and local HTTP stubs. Mypy,
Ruff lint/format, runtime-source diff guard and git diff --check passed.
The operator supplied the full `uv run python .\validate_forgeai_lq1.py`
pass, ending in `FORGEAI-LQ1 HARNESS VALIDATION PASSED` with LQ1.4 included.
All phases passed: LQ1.4 phases 13v-13ad, existing harness phases, runtime
source guards, architecture checks, real-Docker fixture validity and check
diagnostics, mypy, Ruff lint/format, and 89 ForgeAI regression tests.
The validator used replay and local HTTP stubs; it contacted no live model.
This qualifies the harness. Which required fields the live model omits
remains unmeasured with LQ1.4; historical reports cannot be backfilled.
