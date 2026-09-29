# ForgeAI-LQ1: live-model evaluation harness

> **THIS IS NOT A PRODUCTION BENCHMARK.** It measures the unchanged ForgeAI-3
> application on a small frozen fixture set, with the recorded model, hardware
> and revisions only.

**Status:** harness implemented; harness validation pending
(`validate_forgeai_lq1.py`). **No live baseline has been recorded.**

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
