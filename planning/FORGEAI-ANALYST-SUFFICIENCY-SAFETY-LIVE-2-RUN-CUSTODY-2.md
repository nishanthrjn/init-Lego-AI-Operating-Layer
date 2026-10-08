# FORGEAI-ANALYST-SUFFICIENCY-SAFETY-LIVE-2-RUN-CUSTODY-2

Status: **LOCALLY QUALIFIED (2026-10-08; offline; 44/44 validator phases).**
This is an
offline evidence-custody slice only:
- no model or Ollama contact, no preflight or baseline rerun, and no live use
  of SAFETY-EVAL-3;
- no change to the Agent, prompt, parser, evaluators, model or runtime;
- no run artifact was modified or regenerated.

## 1. Why this slice exists

Commit `ade5d97` committed three live/2 run directories before they had exact
custody entries:
- the first live/2 BASELINE;
- two retained zero-call PREFLIGHTs.

The two PREFLIGHTs also sit under `examples/forgeai/evaluation/`, which the
custody scan did not cover. Until this slice, the live/2 custody check reported
the baseline as unrecognized and could not see the nested PREFLIGHTs at all.

## 2. Admitted artifacts

| Directory | Run | Mode | Git tree | Files | Inventory SHA-256 |
| --- | --- | --- | --- | --- | --- |
| `safety2-baseline-3cf8aba9a377/` | `69bcc2f3-9c5a-4489-b999-8bc6ee1c4046` | BASELINE | `6c0529d9444885a276c1e8f445989ed4579ded13` | 267 | `774d65914b0dea783dac1812d6b166c855d18332ecac8fdd5a71e08bad3721b8` |
| `evaluation/safety2-preflight-20261007-01/` | `bdbcfa91-0499-42f1-91f1-fdc72d6c3ab1` | PREFLIGHT | `24e26616ba5f575810e3c15180b6be0851afb3b7` | 3 | `41d0f0aab063fc3c335345c2bcd176e17da527e02334793b585d9878de36647e` |
| `evaluation/safety2-preflight-20261007-a/` | `002b8ba7-6569-48cc-99ce-4387a1bf20e9` | PREFLIGHT | `bed52e1f1ed70236a70208c60a2a6eb07f6c1ee6` | 3 | `33c7d199d7b6ca753e9e449a549b051516c6f9f7ff64470e2ef7928f12755582` |

Paths are relative to `examples/forgeai/`. All three were committed in
`ade5d97`. Each committed copy equals the working tree, no file is ignored, and
the inventories equal those pinned during SAFETY-EVAL-3 qualification.

**Baseline, recorded facts verified and not re-evaluated:**
- identities: condition `forgeai-analyst-sufficiency-safety-live/2`,
  evaluation `…-eval/2`, report `…-live-report/2`, mode BASELINE;
- provenance: HEAD `851dac3` with a clean tree;
- execution:
  - 22 planned, 22 attempted and 22 completed, COMPLETE;
  - no stop, CLIENT_COMPLETED;
  - one call per case in frozen order (no retry);
- results:
  - **decision G — AUTHORITY SAFETY FAILURE**;
  - 4 critical false-sufficient progressions;
  - 1 authority violation;
  - 4 invalid outputs;
- runtime: `qwen2.5-coder:14b` at the pinned digest, Ollama 0.40.0
  (expected and observed), credentials NONE.

It remains a failed safety baseline. Nothing relabels or normalizes it.

**Retained preflights, each pinned separately:**
- PREFLIGHT mode on the live/2 identities, HEAD `456a90a` with a clean tree;
- 0 calls, 0 attempted and 0 completed, no records or timings, and decision
  `PREFLIGHT - NO MEASUREMENT`;
- the same model, digest and Ollama 0.40.0, credentials NONE, and the leakage
  sweep PASSED.

No safety quality is assigned to them. A test proves they are not
interchangeable: each report is checked against its own pin.

## 3. Custody design (extension of the existing registry)

`analyst_sufficiency_safety_live2/custody.py`:
- **Registry.** `ARTIFACTS` keys are now paths relative to `examples/forgeai`.
  The existing top-level keys are unchanged; the new nested keys are
  `evaluation/<name>`. There is one registry and no second mechanism.
- **Bounded discovery.** Exactly two locations are scanned, `examples/forgeai/`
  and `examples/forgeai/evaluation/`; deeper directories and evaluator packages
  are never considered. A directory is a run directory if:
  - it matches the existing `-(smoke|preflight|baseline)-<12 hex>` form; or
  - it is a `live<N>-`/`safety<N>-` smoke, preflight or baseline run with any
    suffix.

  The older `lq1`/`amc1` experiment outputs fall outside the live-run families
  and are not scanned.
- **Refusals.** Any unpinned run directory in either location fails, whether
  committed, untracked or **git-ignored** (via `git status --ignored`). Any
  change to a pinned one fails: a different tree id, or working-tree
  modifications or extra files.
- **Integrity checks.** `baseline()` and the generalized `preflight()` verify
  the recorded historical facts above. The original `preflight()` behavior and
  error label for run `8b147424` are preserved.
- **Pins.** No globs, prefixes or "all preflights". The eight earlier pins are
  byte-identical; the three new entries are additions.

## 4. Effect on the live/2 binding

`custody.py` is a live/2 harness source, so its digest is recorded in the
binding. The only change against the `8b147424` preflight provenance is
`harness_sources["custody.py"]` (a test pins this). The following are all
unchanged:
- Agent, prompt and parser;
- model and digest, and the Ollama 0.40.0 pin;
- SAFETY-EVAL-2, membership, gates, budgets and scorer;
- progression and authority semantics.

No new runtime identity is created. A future live run re-preflights and records
the then-current digests.

## 5. Seals

- **SAFETY-EVAL-3:** byte-for-byte unchanged and `freeze()` verified. It stays
  sealed for the final held-out evaluation.
- **SAFETY-EVAL-2:** unchanged. It remains the development benchmark,
  historical regression and non-gating continuity metric; s12 is not patched.

## 6. Superseded assertions (deselected, not edited)

Three qualified assertions encode facts this slice changes by design. The
validator deselects them by exact node id; every other test in their suites
runs.

| Test | Superseded fact |
| --- | --- |
| `preflight_custody1::test_prior_seven_entries_remain_accepted` | exactly 8 pins (now 11) |
| `preflight_custody1::test_no_baseline_artifact_admitted` | no baseline pin (baseline admitted) |
| `runtime_identity2::test_zero_baseline_calls` | no baseline directory (baseline exists) |

The earlier slices' own validators stay pinned to their historical scope.

## 7. Verification (offline)

There are 38 custody tests covering the 28 required items, plus baseline
report-field refusals, the no-retry record, nested-run rejections and
evaluator-name exclusions.

The validator `validate_forgeai_analyst_sufficiency_safety_live_2_run_custody_2.py`
runs:
- the SAFETY-EVAL-3 qualification prerequisite and scope;
- the `.gitignore` check;
- exact custody of all 11 directories with the frozen evaluators;
- the tests and 30 coverage phases;
- regressions: preflight-custody-1 and runtime-identity-2 (with the
  superseded assertions deselected), SAFETY-LIVE-1, SAFETY-EVAL-2 and
  SAFETY-EVAL-3;
- the zero-provider check, mypy, Ruff and the diff check.

## 8. Next gate

1. The operator runs
   `uv run python .\validate_forgeai_analyst_sufficiency_safety_live_2_run_custody_2.py`,
   then commits.
2. Next substantive slice: **FORGEAI-ANALYST-SUFFICIENCY-HARDENING-DESIGN-1**.
   - It may use SAFETY-EVAL-2, baseline diagnostic 1 and the d09/d13/d21
     history as development evidence.
   - It must not inspect SAFETY-EVAL-3 case content.

No model call is authorized by this slice.

## 9. Local qualification

Operator qualification passed on 2026-10-08 (implementation commit `852fa90`):
all **44/44 phases** of
`uv run python .\validate_forgeai_analyst_sufficiency_safety_live_2_run_custody_2.py`.
The run covered:
- the SAFETY-EVAL-3 qualification prerequisite and scope against `9a56a0d`;
- no ignore rule for live run evidence;
- exact custody of all 11 run directories, with SAFETY-EVAL-2/3 freezes
  verified;
- the 38 custody tests and 30 coverage phases;
- regressions:
  - preflight-custody-1 (21 passed, 2 superseded deselected);
  - runtime-identity-2 (26 passed, 1 superseded deselected);
  - SAFETY-LIVE-1 (57), SAFETY-EVAL-2 (33), SAFETY-EVAL-3 scorer (65);
- the zero-provider check, mypy, Ruff lint and format, and the diff check.

This is offline custody evidence only: no model or provider call and no rerun.
The baseline remains a failed safety baseline (decision G). SAFETY-EVAL-3
remains sealed.
