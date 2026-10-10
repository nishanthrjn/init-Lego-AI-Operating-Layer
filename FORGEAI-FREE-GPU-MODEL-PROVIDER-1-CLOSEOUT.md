# FORGEAI-FREE-GPU-MODEL-PROVIDER-1 CLOSEOUT

FULL VALIDATION PENDING. No commit created. This report supersedes the earlier
slice report's validation status. Scope is closeout only.

1. **Approval defect root cause.** The evaluation caller was stale. `run_task`
   intentionally requires a keyword-only approval callback; its explicit proposal
   approval boundary was introduced in committed slice d7172c8. The evaluation
   runner omitted it. Historical replay fixtures supply deterministic proposal
   and reviewer outputs and expect an approved disposable fixture transaction.
2. **Correction.** `RunSettings.approve` is required and forwarded unchanged to
   `run_task`. The evaluation CLI uses the existing terminal approver; test
   settings explicitly use the existing proposal-bound fixture approval helper.
3. **Approval proof.** Production `run_task` remains unchanged and required.
   Noninteractive CLI input declines; no auto-approval or new bypass exists.
   Regression tests inspect both required signatures and prove explicit decline
   reaches `PROPOSAL_DECLINED`, with no changed paths and no sandbox calls.
4. **READY.** Prompt `Return exactly the word READY.`; output must equal `READY`
   without trimming whitespace.
5. **JSON.** Canonical object is exactly `{"status":"ready"}` semantically,
   with one key; duplicate keys, uppercase READY, fences and prose fail.
   The exact Kaggle 1G prompt is reused and documented in the ForgeAI README.
6. **ADD.** Canonical function is `def add(a: int, b: int) -> int:` followed by
   `return a + b`. Strict AST equivalence; generated code is parsed, never run.
   Exact prompt identity is tested against the Kaggle fixture and README.
   No fence stripping, prose extraction, output repair, retry or fallback.
7. **Structured output: decision A.** ForgeAI tests generic prompted behavior.
   Current public request/settings contracts do not expose `response_format`.
   No Core extension is justified for this closeout. ForgeAI sends no such field;
   Kaggle 1G used `{"type":"json_object"}` for JSON. Matching prompts do not make
   the wire contracts identical; Kaggle evidence does not qualify ForgeAI's
   exact request. Tests assert the field is absent.
8. **ADR-025.** Unchanged, as are ModelPort, Agent contracts, effects, deterministic
   defaults and safe failure facts. No new retry authority or body diagnostics.
9. **Files changed.** Complete closeout inventory appears below.
10. **Tests changed.** Provider cases use lowercase JSON and annotated ADD; added
    literal READY, prompt/document/experiment identity, drift rejection and
    never-execute coverage. Evaluation settings and CLI wrappers explicitly
    inject fixture approval. Existing historical outcome/metric assertions remain
    intact. Two new tests cover required approval and mutation-free decline.
11. **Docker prerequisite.** Operator-restored Docker Desktop Linux was available:
    engine 29.5.3, existing checks image
    `sha256:4c64580306983d70e059f5f133f6bb3f82657c9c61fa96f562f42594f20269df`.
    Readiness test passed. Full remote suite: 44 passed, including real Docker.
    Missing Docker remains an environment blocker, not a reason to modify code.
12. **Scoped validator.** FAILED: provider/architecture 82 passed; Core 2541 passed;
    remote TLS 42 passed/2 deselected; Engineering 170 passed/1 skipped;
    evaluation approval regressions 26 passed/2 failed. Later static phases were
    not reached by that validator. Log: `provider-closeout-scoped.log`.
13. **Full validator.** FAILED: prerequisites passed; provider/architecture 82
    passed; Core 2541 passed; remote including Docker 44 passed; Engineering
    731 passed/1 skipped/1 failed at `test_build_inventory_and_fresh_install`.
    Full validator stopped before historical ForgeAI and static phases. Its
    Engineering wheel-inventory assertion failed before the fresh-install part
    of that test. Log: `provider-closeout-full.log`.
14. **Skips/deselections.** Scoped remote: two real-Docker cases deselected by
    default mode; both ran and passed in full mode. Scoped Engineering: one
    Windows-inapplicable POSIX special-file boundary skip. Full Engineering:
    one explicit dependency-acquisition qualification skip at
    `test_check_preparation_docker.py:42` (existing opt-in test). No additional
    exclusions introduced to hide failures. Initial separate historical run:
    71 skips required `FORGEAI_LIVE1_OFFLINE=1`; this setup omission is corrected
    in the validator. Corrected historical rerun: zero skips/deselections before
    its fail-fast stop. Aborted phases are not passes.
15. **Core.** 2541 tests passed in both validator runs, including architecture
    and existing Core package checks. No Core source changes.
16. **Historical ForgeAI.** Initial separate fail-fast run: 1110 passed,
    71 skipped, one failure at `test_zero_provider_model_calls` because the
    required `FORGEAI_LIVE1_OFFLINE=1` fence was absent. The validator now sets
    that existing offline fence explicitly. Corrected run: **1006 passed,
    one failed, zero skipped/deselected** in 460.73s. Failure:
    `test_40_41_historical_baseline_and_harnesses_unchanged` at
    `test_analyst_sufficiency_h2_development_live1.py:444`; it compares Engineering
    source to Git baseline `579a8d1`, which differs from current committed source.
    This closeout changes no Engineering source. Neither baseline nor assertion
    was weakened. Logs: `provider-closeout-historical.log` and
    `provider-closeout-historical-offline.log`. Later tests were not run.
    Scoped replay case 6 yields `PROPOSAL_INVALID` instead of `CHECKS_FAILED`;
    aggregate invalid coding outputs are 2 instead of 1. The existing worker's
    bounded check-failure rework consumes the fixture's reviewer response as a
    coding proposal. Approval now exposes this incompatible historical replay.
    Neither the expected results nor production rework/model policy was changed.
17. **No Kaggle Core coupling.** `git diff --name-only -- src/legoai adrs/ADR-025.md`
    was empty; Core source search for Kaggle had no matches. Only a test reads
    the experiment fixture; production ForgeAI does not import experiments.
18. **No live endpoint/tunnel.** No Kaggle/HF/KISSKI/Colab or paid-provider calls,
    tunnel, public endpoint, new dependency or repository disclosure. Local TLS,
    loopback and disposable Docker fixtures are validation only. Notebook-local
    serving is not Windows endpoint reachability.
19. **Remaining blockers.** Engineering wheel inventory lists 11 unexpected
    modules (listed below), with none missing; historical replay outcome and
    metric mismatch; historical H2 baseline `579a8d1` differs from current
    committed Engineering source; all phases aborted by these failures still
    need completion. The exact full entry point was run before the subsequent
    offline-fence correction; the corrected historical suite was rerun separately,
    not represented as a successful full-validator rerun.
    These are not corrected by weakening assertions or silently dropping phases.
20. **Locally qualified? No.** Closeout remains pending successful full regression
    and package/install checks. User-supplied Kaggle 1G `KAGGLE_RUNTIME_PASS`
    remains infrastructure evidence only; detailed pinned runtime facts are in
    the ForgeAI README. Next slice only after closeout succeeds:
    `KAGGLE-FORGEAI-INTEGRATION-OPTIONS-1`, research only; not started here.
21. **Proposed commit (not created).**
    `fix(forgeai): reconcile provider contracts and explicit evaluation approval`

## Independent static verification

Core/change-target mypy: 15 files passed; Core-target lint and format passed
(16 files formatted). ForgeAI mypy: 30 files passed; all affected evaluation modules: 11 files passed.
All 14 changed Python files passed Ruff check and Ruff format --check.
`git diff --check` passed. Three focused safety/approval tests passed separately.
These checks do not convert the failed full validator into a pass.

## Engineering inventory mismatch

Additional wheel files under `legoai_engineering/`:

- `agent_output.py`
- `analyst/request_policy.py`
- `analyst/sufficiency.py`
- `analyst/sufficiency_agent.py`
- `analyst/sufficiency_definition.py`
- `analyst/sufficiency_envelope.py`
- `checks/_prepare_program.py`
- `checks/preparation.py`
- `repository/structure.py`
- `repository/structure_authorized.py`
- `sandbox/prepared.py`

This is a packaging inventory assertion failure, not a Docker functional failure.
Engineering production and package tests were not changed during closeout.

## Reproduction

After resolving the reported regression contracts, retain the exact entry point:

```powershell
uv run --locked --offline --no-sync python .\validate_forgeai_free_gpu_model_provider_1.py --full
if ($LASTEXITCODE -ne 0) { throw 'Full provider closeout failed' }
```

The existing validator remains fail-fast; later phases are not claimed if an
earlier phase fails. Full mode enables existing real-Docker remote qualification,
uses the existing pinned checks image, sets the existing `FORGEAI_LIVE1_OFFLINE=1`
fence, and includes the full Engineering suite.
The default scoped run now also checks the evaluation approval regression path.

## Closeout file inventory

- `examples/forgeai/README.md`
- `examples/forgeai/evaluation/README.md`
- `examples/forgeai/evaluation/forgeai_eval/runner.py`
- `examples/forgeai/evaluation/run.py`
- `examples/forgeai/evaluation/tests/diag_support.py`
- `examples/forgeai/evaluation/tests/eval_support.py`
- `examples/forgeai/evaluation/tests/test_lq1_diagnostics.py`
- `examples/forgeai/evaluation/tests/test_lq1_diagnostics_docker.py`
- `examples/forgeai/evaluation/tests/test_lq1_fixtures_docker.py`
- `examples/forgeai/evaluation/tests/test_lq1_observer.py`
- `examples/forgeai/evaluation/tests/test_lq1_preflight.py`
- `examples/forgeai/evaluation/tests/test_lq1_runner.py`
- `examples/forgeai/evaluation/tests/test_lq1_unreachable.py`
- `examples/forgeai/src/forgeai/provider.py`
- `examples/forgeai/tests/test_provider.py`
- `validate_forgeai_free_gpu_model_provider_1.py`
- `FORGEAI-FREE-GPU-MODEL-PROVIDER-1.md`
- `FORGEAI-FREE-GPU-MODEL-PROVIDER-1-CLOSEOUT.md`
