# FORGEAI-FREE-GPU-MODEL-PROVIDER-1 CLOSEOUT

**LOCALLY QUALIFIED** for the bounded provider-interoperability composition using
synthetic/local TLS/loopback fixtures and full historical ForgeAI regressions.
The exact `--full` validator exited **0** during this reconciliation. No commit
created; maintainer review of the result remains pending. No live endpoint,
Kaggle connectivity, model-quality or free-GPU mutation claim is made.

See the final validation evidence at the end of this report. The earlier closeout
findings below are retained as historical failure evidence, superseded by the
reconciliation appendix and successful final run.

### Previous checkpoint evidence (before reconciliation)

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


## FORGEAI-PROVIDER-CLOSEOUT-REGRESSION-RECONCILIATION-1

Status: **LOCALLY QUALIFIED** after the exact full validator exited 0.
Checkpoint `6b53404` is retained; no commit,
production change, live model, disclosure, tunnel or Kaggle integration in this slice.
The findings above describe the previous closeout attempt; the evidence below
records the subsequent regression reconciliation.

### Engineering inventory forensics

The wheel configuration deliberately ships `src/legoai_engineering`. All eleven
files are committed runtime modules, not test or experiment files. An underscore
means private Python API, not exclusion from the wheel: `_prepare_program` is
imported by preparation. Removing it would break that runtime path. The exact
inventory test had not been reconciled with these independently introduced modules.
Only its explicit expected set changed; packaging rules are unchanged, and the
assertion still rejects any extra or missing package file.

| Module under legoai_engineering | Introducing commit | Owning slice | Ship? | Evidence / prior qualification |
| --- | --- | --- | --- | --- |
| agent_output.py | bcb7c71 | v0.1 supervision | Yes | Coding/reviewer api and values import it; test_agent_output; roadmap records 25/25 local phases |
| analyst/request_policy.py | 8aaf3bf | HARDENING-H1-REQUEST-POLICY | Yes | Public consuming-guide contract; test_analyst_request_policy; H1 record reports 65/65 |
| analyst/sufficiency.py | ead49cc | analyst sufficiency contracts | Yes | request_policy, sufficiency_agent and envelope import its values; test_analyst_sufficiency_contract; subsequently exercised by qualified H1/H2 |
| analyst/sufficiency_agent.py | 261e129 | model-backed sufficiency agent | Yes | envelope imports parser/request; test_sufficiency_agent; H2 record preserves and qualifies shared parser |
| analyst/sufficiency_definition.py | 261e129 | model-backed sufficiency agent | Yes | sufficiency_agent imports definition; test_sufficiency_agent; H2 retained 1.0.0 contract |
| analyst/sufficiency_envelope.py | c49825b | HARDENING-H2-EVIDENCE-ENVELOPE | Yes | H2 development runtime consumer; test_sufficiency_envelope; 579a8d1 records 62/62 qualification |
| checks/_prepare_program.py | 0b1c096 | ENGINEERING-PREPARED-CHECK-ENV-1 | Yes | checks.preparation imports _INSTALL; preparation/Docker tests; roadmap records complete validator plus maintainer rerun |
| checks/preparation.py | 0b1c096 | prepared checks / PROJECT-CHECK-PROFILE-1 | Yes | Public consuming-guide API and ForgeAI composition consumer; preparation/Docker tests; same qualification |
| repository/structure.py | 84da572 | DISCOVERY-1 | Yes | Public consuming-guide API; structure and structure-install tests; original record still says local qualification pending |
| repository/structure_authorized.py | 84da572 | DISCOVERY-1 | Yes | Public consuming-guide authorized adapter; structure-install tests; no invented prior qualification claim |
| sandbox/prepared.py | 0b1c096 | ENGINEERING-PREPARED-CHECK-ENV-1 | Yes | Docker adapter and preparation import it; preparation/Docker tests; same qualified project profile |

Prior **wheel-inventory** qualification for these additions was not established:
that is the stale check being repaired and executed now. Intended distribution
is established independently by source ownership, imports and installed API tests.
The focused build/inventory/fresh-install test now passes (1 test).

### Historical scope

`579a8d1` recorded operator qualification of H2 implementation `c49825b` (62/62).
The H2 development harness `95744d7` used that base to prove it changed neither
Core nor Engineering while preserving the historical comparison and sealed inputs.
Later committed Engineering work includes `232dde4` readiness, `bcb7c71`
supervision, `03d2c6e` read-only context and `0b1c096` prepared checks. The roadmap
records qualified supervision/prepared-check profiles. Later remote/Core slices
also legitimately changed Core. An unlimited current-tree freeze is a stale proxy
for the historical slice's isolation, not a product invariant.

The repaired test still compares protected run/harness directories and five
explicit H1/H2 analyst implementation files to **579a8d1** and checks their clean
status. It additionally proves product-source isolation between **579a8d1 and
95744d7**. Neither reference is HEAD; no assertion is deleted or made empty.

The existing H2 validator explicitly documents six other superseded assertions.
To run the whole suite without deselecting them, corresponding tests now retain
historical source isolation against their introducing commits (`8aaf3bf`,
`c49825b`, `f19d32b`, `731f69c`) while retaining current prompt/parser identity
checks and protected-file assertions. RUN-CUSTODY-2 (`852fa90`, qualified in its
planning record) explicitly admitted three additional pinned artifacts. Tests now
verify all original seven pins plus the preflight and those three exact pins;
only the one approved baseline is accepted and an unknown baseline still fails.
PREFLIGHT retains zero-call/no-execution assertions regardless of admitted past
artifacts. These replace stale proxies/counts, not custody behavior. Focused
coverage for these additional historical reconciliations: 28 passed.

### Replay case 6

The roadmap records `c005f46` check-feedback rework as locally qualified (26/26
phases, including real Docker). `test_v01_check_rework` explicitly requires
terminal CHECKS_FAILED when the second check batch fails, with no reviewer or
third proposal. Production sequencing is correct.

Old queue: initial coding proposal, then REVIEW_ACCEPT. Actual call #2 is coding
rework after deterministic check findings, so consuming reviewer-shaped JSON
correctly caused PROPOSAL_INVALID. The fixture was stale.

New queue: initial coding proposal -> explicit approval -> three checks (mypy
fails) -> coding REWORK -> separate explicit approval -> three checks (mypy fails)
-> terminal CHECKS_FAILED. No review invocation. The fixture asserts exactly two
model calls and six sandbox checks, with no attempt review. The failure category
is preserved; expected attempts increase from one to two. Aggregate coding
invalid count stays one with denominator nine; rework count becomes two, recovery
1/2; second-attempt checks and not-run review include case 6; model total is 15.
The combined runner/H2 focused tests pass (12 tests).

### Boundaries and verification

Only tests and this appendix change. Worker, MAX_ATTEMPTS, approval, rework,
review gating, mutation, Core, ModelPort, provider contracts, structured-output
decision A and Kaggle remain unchanged. READY/JSON/ADD contracts remain pinned.
No test skip or deselection was added. Historical revision assertions continue
to depend on existing repository history, as before.

Scoped validator: **exit 0**, 82 provider/architecture, 2541 Core, 42 remote
(2 Docker cases deselected in default mode), 170 Engineering (one Windows POSIX
special-file skip), 28 evaluation approval/architecture tests. Mypy 15 Core/change
targets and 30 ForgeAI files passed; lint, formatting and whitespace passed.
Independent typing of all eight changed test files passed. Full run pending.
Logs: `reconciliation-focused.log`, `reconciliation-package.log`,
`reconciliation-historical-focused.log`, `reconciliation-scoped.log`,
`reconciliation-full.log` (local ignored logs).

Qualification requires exit 0 from the
exact `validate_forgeai_free_gpu_model_provider_1.py --full` entry point.

Proposed commit (not created):
`test(forgeai): reconcile package inventory and historical qualification contracts`


First reconciliation full run: provider 82, Core 2541, remote/Docker 44 passed;
Engineering stopped at 1069 passed, one optional acquisition skip, one additional
historical H2 freeze failure (`test_31_32_no_core_model_port_or_adapter_change`).
The provider checkpoint d7172c8 intentionally changed model ports/values after H2.
That test now proves H2 isolation between f5b969a and c49825b, retaining adjacent
current parser reuse and request-shape checks. All 42 envelope tests passed after
this correction. It is the same historical-scope repair, not a Core semantic fix.
The required scoped-then-full sequence will be repeated after focused checks.


Related LQ1 real-Docker diagnostics fixture reproduced the same stale queue:
`broken_proposal, REVIEW_ACCEPT` yielded PROPOSAL_INVALID. Its second payload is
now the same intentionally broken candidate with update operations, so both real
check batches retain F401 and the wrong assertion. CHECKS_FAILED and diagnostic
expectations remain unchanged; added two-call/two-attempt/no-review assertions.
The corrected real-Docker test passed (1 test, 29.38s). All changed historical
modules passed together (189 tests), and all 42 H2 envelope tests passed.


Final full run progress: provider/architecture 82 passed; Core 2541 passed;
remote TLS including Docker 44 passed; Engineering **1118 passed, 2 skipped**.
The two existing Engineering skips are optional explicit dependency acquisition
(`test_check_preparation_docker.py:42`) and the Windows-inapplicable POSIX
special-file boundary (`test_workspace.py:333`). No new skip/deselection.
Historical ForgeAI and the final static phases remain pending at this point.


Second full run passed Engineering (1118/2 existing skips) and reached 1623
ForgeAI passes before the synthetic LQ1 diagnostics aggregate exposed two more
stale reviewer payloads after check failures. Both are now valid coding rework
payloads, retaining failed checks; aggregate diagnostics explicitly count both
batches (five valid coding outputs, seven raw representations, four failed Ruff
checks/two unavailable, doubled observed Ruff and pytest findings). The separate
invalid-output cases remain intact. All four report diagnostics tests and typing,
lint and format passed. The full LQ1 family is checked before another exact
scoped/full sequence. No production classifier or parser was changed.


All **243 LQ1 tests passed** (260.20s, no skips/deselections), including the real
Docker diagnostics and fixture checks. The final scoped validator exited 0;
`reconciliation-scoped-complete.log` records every phase. The exact full validator
is rerun after that pass; its final evidence belongs in
`reconciliation-full-complete.log`.

### Reconciliation file inventory

- `FORGEAI-FREE-GPU-MODEL-PROVIDER-1.md`
- `FORGEAI-FREE-GPU-MODEL-PROVIDER-1-CLOSEOUT.md`
- `examples/forgeai/evaluation/tests/test_analyst_sufficiency_h2_development_live1.py`
- `examples/forgeai/evaluation/tests/test_analyst_sufficiency_hardening_h1.py`
- `examples/forgeai/evaluation/tests/test_analyst_sufficiency_hardening_h2.py`
- `examples/forgeai/evaluation/tests/test_analyst_sufficiency_safety_live1.py`
- `examples/forgeai/evaluation/tests/test_analyst_sufficiency_safety_live2_preflight_custody1.py`
- `examples/forgeai/evaluation/tests/test_analyst_sufficiency_safety_runtime_identity2.py`
- `examples/forgeai/evaluation/tests/test_lq1_diagnostics.py`
- `examples/forgeai/evaluation/tests/test_lq1_diagnostics_docker.py`
- `examples/forgeai/evaluation/tests/test_lq1_runner.py`
- `packages/legoai-engineering/tests/test_package_install.py`
- `packages/legoai-engineering/tests/test_sufficiency_envelope.py`


### Final validation evidence — LOCALLY QUALIFIED

Both exact commands completed successfully on the final test changes:

```powershell
uv run --locked --offline --no-sync python .\validate_forgeai_free_gpu_model_provider_1.py
if ($LASTEXITCODE -ne 0) { throw 'Scoped provider validation failed' }
uv run --locked --offline --no-sync python .\validate_forgeai_free_gpu_model_provider_1.py --full
if ($LASTEXITCODE -ne 0) { throw 'Full provider validation failed' }
```

| Final full phase | Result |
| --- | --- |
| Docker Desktop Linux and pinned checks image | Passed |
| Provider / ForgeAI architecture | 82 passed |
| Core, including architecture/package regressions | 2541 passed |
| Remote TLS, including real Docker | 44 passed; no deselections |
| Full Engineering, including package/fresh install | 1118 passed, 2 existing skips |
| Full historical ForgeAI, including clean install and Docker | 1847 passed; no skips/deselections |
| Evaluation approval / architecture | 28 passed |
| Core/change-target mypy | 15 files passed |
| ForgeAI mypy | 30 files passed |
| Ruff lint | Passed in both validator scopes |
| Ruff format --check | 16 Core/change targets and 30 ForgeAI files passed |
| git diff --check | Passed |
| Exact --full command | **Exit 0** |

Final logs: `reconciliation-scoped-complete.log` and
`reconciliation-full-complete.log`. Logs are local ignored artifacts. All eleven
changed Python test files additionally passed typing (from their package working
directories), lint and formatting. One exploratory typing invocation from the
repository root used the wrong relative mypy paths; rerunning from the required
ForgeAI directory passed without code changes.

Every final skip/deselection:

- Scoped remote mode: 2 real-Docker deselections, both executed and passed in full.
- Scoped Engineering: 1 POSIX special-file test inapplicable on Windows.
- Full Engineering: `test_check_preparation_docker.py:42`, existing explicit
  dependency-acquisition opt-in; `test_workspace.py:333`, POSIX special-file
  boundary inapplicable on Windows.
- Full ForgeAI: zero skips/deselections. No tests were excluded to obtain green.

No failures remain in the exact full validator. Earlier failed attempts are
preserved above for traceability, not current blockers. Production source diff
is empty for Core, Engineering and ForgeAI. Packaging configuration, worker,
approval, MAX_ATTEMPTS, rework, review, effects and provider contracts are unchanged.
The canonical prompts and structured-output decision A remain intact.

This qualifies bounded local provider interoperability only. No Kaggle, Hugging
Face, KISSKI, Colab, paid API, live model, tunnel or repository disclosure occurred.
Kaggle integration remains a later research-only slice and was not started.
No commit, squash or history rewrite was performed.

Final proposed commit:
`test(forgeai): reconcile package inventory and historical qualification contracts`
