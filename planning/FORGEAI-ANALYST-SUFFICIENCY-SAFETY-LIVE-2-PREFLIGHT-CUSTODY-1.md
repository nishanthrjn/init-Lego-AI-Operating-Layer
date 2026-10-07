# FORGEAI-ANALYST-SUFFICIENCY-SAFETY-LIVE-2-PREFLIGHT-CUSTODY-1

Status: **LOCALLY QUALIFIED (2026-10-07; offline; 29/29 validator phases).**
This is a custody and admission slice only. Nothing was re-run, Ollama was not invoked,
and no semantic call was made. No Agent, prompt, parser, evaluator, model,
gate, scorer, membership, budget, runtime identity or compatibility record
changed.

## 1. Live/2 PREFLIGHT passed

| Field | Value |
| --- | --- |
| Condition | `forgeai-analyst-sufficiency-safety-live/2` |
| Report | `forgeai-analyst-sufficiency-safety-live-report/2` |
| Run | `8b147424-5231-4758-9e0f-05730f6174bc` |
| Directory | `examples/forgeai/safety2-preflight-300452037205/` |
| Result | PREFLIGHT PASSED (`PREFLIGHT - NO MEASUREMENT`, no stop reason) |
| Git HEAD at execution | `dff9cc045a635d4c8437ea78d8ce86c0ec7c3e4b` (clean tracked tree) |
| Committed in | `72cb346` (unchanged) |
| Semantic Agent / model calls | 0 / 0 |

The committed report also records:
- `qwen2.5-coder:14b` with
  `sha256:9ec8897f747e246e970bc5cfdda85d22f1123dc2e3d34978a010a75968716849`
  (expected and observed);
- Ollama 0.40.0 (expected and observed);
- credentials `NONE`;
- leakage preflight `PASSED`;
- membership s01–s22, with d21/d22 non-gating;
- 22 calls, 600 s per call, 3600 s total;
- empty records and timings.

This is a preflight only. It is not baseline evidence and makes no quality
claim.

## 2. Admission

The committed directory holds exactly `run.json`, `report.json` and
`report.md` (Git tree `5f5f49375b83b9fca58873ea9f15e3f9b409840b`). Nothing
was normalized or regenerated.

`analyst_sufficiency_safety_live2/custody.py` gains one exact entry, which
pins that directory name to that tree id. It also adds a `preflight()` check
that re-verifies the committed report fields listed above on every custody
verification.

The existing behavior is unchanged:
- there are no globs and no `safety2-preflight-*` rule;
- any other run directory (committed or untracked) still fails;
- any change to a pinned directory, committed or in the working tree, still
  fails;
- the seven prior pins (six LIVE-1 directories and the live/1 refusal
  `safety1-preflight-c80435f8dadc`) are byte-identical.

## 3. Effect on the recorded live/2 binding

`custody.py` is one of the live/2 package files whose digest goes into the
binding. The admission therefore changes exactly one value: the
`harness_sources["custody.py"]` digest, compared with the 8b147424 preflight
provenance. A test pins this, and every other binding field is equal.

The runtime and experiment identity are unchanged. A future BASELINE runs its
own preflight at execution time, which records the then-current digests.

## 4. Other change

In the runtime-identity-2 tests, one assertion meant "no run directory starts
with safety2". That is no longer true once the live/2 preflight exists. It is
replaced with "no `-baseline-` directory". The validator allows only this
single-line change to that file.

## 5. Verification (offline)

There are 23 custody tests covering the 16 required items, plus
report-field refusals and the binding-digest effect. The validator
`validate_forgeai_analyst_sufficiency_safety_live_2_preflight_custody_1.py`
checks:
- scope against `72cb346`;
- protected live/2 identity, runtime, compatibility, evaluator and historical
  files;
- exact custody;
- preflight report integrity;
- that no baseline directory exists;
- that the identities and pins are unchanged;
- the custody tests and coverage phases;
- the runtime-identity-2, SAFETY-LIVE-1 and SAFETY-EVAL-2 regressions;
- that no provider is called;
- mypy, Ruff and the diff check.

## 6. Next gate

1. The operator runs
   `uv run python .\validate_forgeai_analyst_sufficiency_safety_live_2_preflight_custody_1.py`,
   then commits and confirms a clean tree.
2. **Separately authorized:** the 22-call BASELINE on live/2. It is not
   authorized here.

## 7. Local qualification

Operator qualification passed on 2026-10-07 (implementation commit `fa89394`):
all **29/29 phases** of
`uv run python .\validate_forgeai_analyst_sufficiency_safety_live_2_preflight_custody_1.py`.
The run covered:
- scope and protected files against `72cb346`;
- exact custody (8 pinned directories), live/2 preflight report integrity,
  no baseline directory, and unchanged identities and pins;
- the 23 custody tests and 18 coverage phases;
- regressions: runtime identity 2 (27), SAFETY-LIVE-1 (57) and SAFETY-EVAL-2
  (33);
- the zero-provider check, mypy, Ruff lint and format, and the diff check.

This is offline custody evidence only: no model, provider or Docker, and no
new run. It is not baseline evidence and does not authorize the 22-call
BASELINE, which needs separate authorization and a clean tracked tree.
