# FORGEAI-ANALYST-DESIGN-LIVE-1 CHILD-FAILURE DIAGNOSTIC

Date: 2026-10-07. Status: diagnostic complete; fixes recommended, not implemented.

**Disposition C — BOTH HARNESS AND REPORTING DEFECTS IDENTIFIED.**

## Evidence identity and preservation

Failed smoke `8abbc78f-628e-4aec-b0da-b822620304e7` used commit
`1ee84add9383c070ecd521de418b8acb72ee8898`, with a clean tracked tree.
The model was `qwen2.5-coder:14b`, digest
`sha256:9ec8897f747e246e970bc5cfdda85d22f1123dc2e3d34978a010a75968716849`,
Ollama 0.35.1, Windows 11 build 26200. Preflight passed.

All files in [failed smoke](../examples/forgeai/live1-smoke-d59e9c3f030b/)
and [preflight](../examples/forgeai/live1-preflight-411899d3f557/) were inspected
read-only. Neither directory was changed. No smoke was rerun, no model or
provider was called, and no new live run identity was created for diagnosis.

The only established live outcome is runtime smoke failure before a completed
assessment: six planned slots, one attempted, zero completed results, five
subsequent slots never attempted. `SMOKE_RUNTIME_FAILURE`,
`SUFFICIENCY_PROFILE_RUNTIME_FAILED`, and `SERVER_EFFECT_UNKNOWN` remain intact.
Grounding is NOT_MEASURED; aggregate is NOT_APPLICABLE. G07 remains open.

## Earliest failure boundary

**D — child composition/host initialization failure is ESTABLISHED in an
independent zero-provider reproduction of the committed live composition path.**
It supplies `{"revision": "live1"}` to `open_local_host`, omitting mandatory
`binding`. `capture_model_selection` requires exactly `revision` and `binding`.
The resulting `ModelCompositionError(invalid_configuration)` becomes
`HostError(invalid_configuration)` before adapter construction, Agent entry,
or ModelPort dispatch. The configured binding ID is `ollama`.

Sources: [live runtime](../examples/forgeai/evaluation/analyst_design_live1/runtime.py),
[model selection](../src/legoai/runtime/_composition/model_selection.py),
[local host](../src/legoai/runtime/local.py), and
[binding definition](../examples/forgeai/src/forgeai/cli.py).
This is a harness configuration defect; the runtime correctly enforces its
existing configuration contract. No Core redesign is indicated.

Historical artifacts alone establish the parent receiving a decoded child
error/invalid-result envelope, not its exception category or exact failing
stage. For an artifact-only classification, distinguishing D from later child
failures is NOT ESTABLISHED (boundary I). The deterministic source defect and
fenced reproduction identify D without pretending to supply a missing
historical trace. Parent failure before child creation is CONTRADICTED by the
recorded `child_failure` branch at this commit. A model semantic failure,
provider completion, or an Ollama-caused failure is NOT ESTABLISHED.

## Ordered invocation and custody timeline

Times below are UTC filesystem modification observations, not persisted child
event timestamps. Logical ordering follows the committed harness; unknown
child events have no invented timestamps.

| Event | Historical status | Evidence |
| --- | --- | --- |
| Run admitted | YES | `run.json`, modified 09:23:27.421928; preflight succeeded |
| Initial Agent input/projection constructed | YES | Parent constructs manifest/projection before claiming call; source ordering |
| Call slot claimed | YES | `attempted_calls=1`, call 001 |
| Attempt marked started | YES | `call-001-started.json`, 09:23:27.597925; d01/initial/initial, timeout 600 s |
| Child process requested | YES | Committed path to returned `child_failure` passes `process.start()` |
| Child created/target entered | YES | Inferred from decoded child envelope; no PID/start timestamp retained |
| Child host composition completed | UNKNOWN | No historical stage marker; independent reproduction fails here |
| Governed request leakage check completed | UNKNOWN | No completion marker; null digest alone cannot locate failure |
| Governed Agent call entered | UNKNOWN | No historical marker; NO in fenced reproduction |
| ModelPort dispatch entered | UNKNOWN | No historical marker; NO in fenced reproduction |
| HTTP inference request initiated | UNKNOWN | No historical dispatch receipt; NO in fenced reproduction |
| Provider accepted inference | UNKNOWN | No invocation-correlated provider evidence |
| Response received | UNKNOWN | No retained response receipt |
| Parse begun | UNKNOWN | No retained parse-stage marker |
| Parsed result recorded | NO | Empty records and null payload digest |
| Finish record persisted | YES | `call-001-finished.json`, 09:23:28.192991; child_failure, 0.5949281999928644 s |
| Report persisted | YES | JSON 09:23:28.260217; Markdown 09:23:28.287715 |
| Subsequent five slots started | NO | Immediate stop, one lifecycle pair only |

Harness elapsed time was 2.8598498000064865 s. The input projection checks in
the parent are distinct from the child request-level leakage guard.

## Dispatch truth and provider evidence

Historical provider dispatch is **UNKNOWN**: neither definite dispatch nor
confirmed absence is established by retained per-invocation telemetry.
`SERVER_EFFECT_UNKNOWN` is retained, not converted to NONE. The reproduction
proves pre-dispatch failure in the diagnostic execution, not a retrospective
provider receipt for the failed run. A short duration is not dispatch proof.

Existing local Ollama `server.log` and rotations were inspected without
contacting Ollama. No exact run UUID, invocation label `d01-initial-initial`,
or smoke directory suffix matched. Around 11:23 local time (09:23 UTC), the
log records successful `/api/version` and `/api/tags` GETs at 11:23:13–14 and
11:23:27. No inference access entry was found in that minute. Access logs are
not an exact invocation ledger; absence cannot establish non-dispatch.
Preflight confirms model availability/digest/version, not inference acceptance.

## Process, Windows, and environment findings

The operator process used the ForgeAI virtual environment Python, cwd
`examples/forgeai`, `PYTHONPATH=evaluation`, and UTF-8 mode. Invocation was
module-based (`-m analyst_design_live1 SMOKE`) with an argument list and
separate output/approval-reference arguments, not a shell-constructed command.
The child uses Python multiprocessing `spawn`, not a custom shell command.
No custom creation flags, process-group management, or Windows quoting layer
is present in the harness. Paths are handled by Python; no separator defect
was observed. Spawn transfers the manifest and expected projection through
multiprocessing serialization; a one-way Pipe transfers the result envelope.
The parent's writer closes after start and the child's writer closes on exit.

No historical child PID, resolved child command line, exit code, Windows
status/signal, stdout/stderr capture, or complete inherited environment was
retained. Console inheritance provides no durable diagnostics. Parent CLI
exit 0 means it emitted the failure report, not that the child succeeded.
A child error envelope is not evidence of an abnormal process exit.

The supervisor polls in at most 50 ms intervals against the 600 s deadline.
Timeout and observed child exit have separate categories (`timeout`,
`child_exit`). Cleanup terminates a still-alive child, joins for 0.5 s, then
kills/joins if necessary; it does not retain exit status. It may terminate a
child after receiving its envelope. The historical 0.59 s failure is not the
600 s timeout. No temp/output-path or input-file defect was found; lifecycle
and report persistence succeeded. The child receives inputs as objects.

Read-only import checks found Python 3.14.5 (64-bit, MSC v1944), executable
`examples/forgeai/.venv/Scripts/python.exe`. Core, Engineering, and harness
imports resolve this checkout's editable sources. No package/import defect
was observed. Historical full environment/sys.path identity was not captured,
so exact equivalence of every inherited variable is NOT ESTABLISHED.

## Why qualification missed the defect

The actual-provider branch builds its own local host with the incomplete
selection. Offline governed tests instead use `host_for(Replay(output))`,
which correctly supplies `{"revision": "r1", "binding": "replay"}`.
The 65-phase/598-test qualification (including 69 harness tests) therefore did
not establish validity of the actual-provider composition branch. Agent,
prompt, parser, frozen fixtures, evaluator, and model quality are not implicated
by this failure. No completed assessment supports changing them.

## Reporting defect and diagnostic loss

**Reporting bug ESTABLISHED:** `harness.py` computes `not_run` from absence in
completed `rows`. The attempt counter and started record are persisted before
supervision; a failing call produces no completed row. Consequently d01 is
listed in `not_run` despite its lifecycle proving an attempt.

The current report lacks an explicit per-slot distinction between
NEVER_ATTEMPTED, ATTEMPTED_NO_RESULT, and COMPLETED_RESULT. Separate lifecycle
files permit reconstruction for this run, but the `not_run` list does not.
No documented scoring-only meaning makes this misleading label intentional.
Do not repair the historical report or synthesize a semantic result.

`child_failure` also loses safe information: the child sends the exception
class, but the parent discards it and conflates exceptions with wrong result
types. Launch/import, composition, Agent, transport, and protocol stages are
not durably differentiated. Launch failure or EOF can follow other exception
paths; timeout/child_exit categories do not replace exit-code evidence.
Existing evidence is sufficient to identify both defects, insufficient for a
complete historical dispatch/exit reconstruction.

## Offline checks performed

1. Import/executable/cwd inspection and read-only source/artifact/log review.
2. A temporary Windows-spawned probe executed the unchanged actual-provider
   composition branch with socket connect/DNS/send audit fences and an Agent
   entry sentinel. Its event loop was initialized before the fence to permit
   Windows' standard-library local self-pipe. It observed selection
   `{"revision":"live1"}`, then HostError and ModelCompositionError, both
   `invalid_configuration`; zero Agent entries and zero network attempts.
   Probe child exit 0 means the expected error was captured successfully.
   No model request, HTTP probe, or new live run was made; temporary scripts
   were removed.
3. The initial probe placed the fence before event-loop initialization and
   blocked Windows' own self-pipe connection. That diagnostic setup failed
   (exit 1 and event-loop cleanup warnings); it is not smoke failure evidence.
   The corrected probe above separates loop startup from provider fencing.
4. Existing offline `test_supervised_agent_and_timeout`: **1 passed in 1.04 s**,
   exercising Replay child completion and timeout with offline mode enabled.
5. Documentation diff/links and preserved artifact hashes checked.

To repeat the existing zero-provider regression from repository root:

```powershell
$previousOffline = $env:FORGEAI_LIVE1_OFFLINE
try {
    $env:FORGEAI_LIVE1_OFFLINE = "1"
    Push-Location examples/forgeai
    try {
        .\.venv\Scripts\python.exe -m pytest -q evaluation/tests/test_analyst_design_live1.py::test_supervised_agent_and_timeout -p no:cacheprovider
    } finally { Pop-Location }
} finally { $env:FORGEAI_LIVE1_OFFLINE = $previousOffline }
```

This test alone does not cover the defective live composition branch. No full
validator rerun or new local qualification is claimed for this documentation.

## Smallest separately authorized fix

Proposed slice: **FORGEAI-ANALYST-DESIGN-LIVE-1 HARNESS-RUNTIME-FIX-1**.

- Supply the existing explicit `ollama` binding selection in harness host
  composition. Add a zero-provider regression covering that branch before
  Agent/model dispatch, not just the separate Replay branch.
- Derive attempted/unattempted/completed accounting from call lifecycle;
  preserve denominators and failures without fabricating parsed output.
- Retain safe bounded child stage, exception/failure category, IPC status,
  invocation identity, and observed exit code (including cleanup context).
  Distinguish launch, bootstrap, composition, pre-dispatch Agent, transport,
  timeout, abnormal exit, and invalid protocol/result. Add dispatch markers
  only where the existing boundary can truthfully observe them; a request
  start is not provider acceptance. Never infer NONE from missing markers.
- Test failure envelopes, Windows spawn, attempt accounting, and diagnostic
  persistence offline. No raw prompts, hidden oracle, secrets, arbitrary
  exception text, or chain-of-thought logging is needed.

Only harness/reporting changes are proposed. No revision-2/profile/Agent/
prompt/parser/model/oracle/gate/threshold/smoke-membership/call-ceiling change
is authorized. No runtime/Core or adapter behavior change is needed.
After separately authorized implementation: rerun offline validator, locally
re-qualify, commit, establish a clean tree, and obtain explicit authorization
for a NEW smoke identity. FULL remains unauthorized. No blind retry.

## Immutable file inventory (SHA-256)

| Directory | File | SHA-256 |
| --- | --- | --- |
| preflight-411899d3f557 | run.json | `1bd0821ed3e6e89b8df831f00582a4ffe3161332984f9a29d03263ad1feec541` |
| preflight-411899d3f557 | report.json | `a46c79ff8e0fbb14130c39659ec6fdb5994232310e85348d9a0c1ef3ed1a0c6b` |
| preflight-411899d3f557 | report.md | `e8eb9e905ed19a1e0dc8ba6a078de74d87cdeec988c8051f693892963fe800ca` |
| smoke-d59e9c3f030b | run.json | `cdc20108dee207d77a9cfc13320a956394041daebeb09166198b53cd6e325550` |
| smoke-d59e9c3f030b | call-001-started.json | `068f215c00c4ef1ea3770e5defe12c429ddfc3ffadafa5567b7a5e79e0d1c4e0` |
| smoke-d59e9c3f030b | call-001-finished.json | `b8d4c9a3640eff835db4c85acc0e28690675cb238b12d516d6abd521be0de74c` |
| smoke-d59e9c3f030b | report.json | `8c6436ac2e5d370b7412561d743d4a2370a80df2ee8eba2c47910a78ed6583ed` |
| smoke-d59e9c3f030b | report.md | `81085e6e9e06b478f7e39fb819857678e8f4aa12d3c78fd8e5400e3061336b1c` |

HARNESS AND REPORTING FIX REQUIRED


## HARNESS-RUNTIME-FIX-1 implementation record — 2026-10-07

Maintainer separately authorized the bounded harness fix after the diagnostic.
**IMPLEMENTED — LOCAL VALIDATION PENDING.** The original findings and all eight
historical artifacts above are unchanged; no diagnostic fields are backfilled.

Implemented explicit existing `binding=ollama` selection; durable per-model-slot
NEVER_ATTEMPTED / ATTEMPTED_NO_RESULT / COMPLETED_RESULT accounting; bounded
closed child stage/failure/IPC diagnostics, allowlisted exception class, observed
exit status and distinct cleanup actions. The actual live composition branch is
covered by zero-provider fenced tests, including intentional missing binding.
Windows spawn tests cover composition, Replay results, error envelopes, EOF,
invalid protocol/results, abnormal exit, timeout and launch failure. Returned
Agent semantic failures remain results. The 68-call execution partition stays
separate from 70 frozen semantic slots.

The canonical offline validator is extended to 99 phases. Run from repository
root: `uv run python .\validate_forgeai_analyst_design_live_1.py`.
Operator qualification is pending; implementation checks are not operator approval.
The module README documents custody fields and unobservable dispatch boundaries.
No provider acceptance is claimed; uncertain effects remain UNKNOWN.

No Core, adapter, Agent, prompt/parser, frozen evaluator/profile, model, gates,
thresholds, call ceilings, smoke membership or authority semantics changed.
After operator qualification, commit only when authorized, establish a clean
tracked tree, and request explicit authorization for a NEW smoke identity.
Neither smoke nor FULL is authorized by this implementation or qualification.
No live call or new live run was made; G07 remains open.

Implementation verification completed offline: **99/99 validator phases passed**,
including **617 tests (88 harness tests)**, mypy, Ruff lint/format and diff checks.
This is the implementation check, not the pending maintainer/operator execution
of the validator. No provider endpoint, smoke, FULL or Docker was invoked.
