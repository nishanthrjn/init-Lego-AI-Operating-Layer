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
- An earlier attempt requested a model that was not installed in the local
  Ollama. Every run was a provider-side `MODEL_FAILED`, which measured
  configuration, not model behavior, so it is not a baseline.

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
| `forgeai_eval/` | Harness: fixtures, hidden tests, runner, metrics, report |
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
- **ForgeAI-3 regressions.**

A replay demo writes a report too. It is harness evidence only:

```powershell
cd examples/forgeai
uv run python evaluation/run.py replay --output lq1-replay
```

## Live baseline procedure (maintainer only)

1. Start Docker Desktop and Ollama, and pull the chosen model.
2. Record the model's immutable identity yourself, for example the digest
   from `ollama show <model>` or `ollama list`. The harness never infers it.
3. From `examples/forgeai`, run:

   ```powershell
   uv run python evaluation/run.py live `
     --model <model-name> --model-digest <digest> --ollama-version <version> `
     --hardware "<cpu/gpu/ram class>" --repetitions 3 --output lq1-baseline
   ```

   Use at least 3 repetitions (N ≥ 3). Missing metadata aborts before any
   run.
4. Share `lq1-baseline/report.json` and `report.md`. They contain
   identifiers, enums, counts and timings only: no source, prompts, model
   output, environment or host paths.

**What a report records:** mode, provider, binding, model name and digest,
Ollama version, ForgeAI commit (marked `+dirty-runtime` if runtime sources
are modified), fixture and hidden-test revisions and digests, hardware class,
platform, start time and N.

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
correction. The harness does not query the server version; that is a known
gap. A re-run with the correct value would produce a clean record.

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
- **Windows + Docker Desktop only**, the qualified sandbox scope.
