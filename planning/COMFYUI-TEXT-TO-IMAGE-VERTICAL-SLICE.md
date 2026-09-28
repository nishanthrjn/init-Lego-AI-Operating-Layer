# Local ComfyUI Text-to-Image Integration

Status: IMPLEMENTED — LOCALLY VALIDATED (deterministic suite and live generation;
see slice 2 validation evidence). Live cancellation (`--cancel-after`) is not recorded.
Assessment authority: [ComfyUI impact assessment](COMFYUI-INTEGRATION-IMPACT-ASSESSMENT.md).
No Core, ModelPort or browser contract changes. No live runtime calls or tests run
internally; only syntax/import sanity and focused static source review/formatting.

## Scope and ownership

`packages/legoai-generative-media` owns immutable task values, TextToImagePort,
fixed workflow validation, private ComfyUI transport/adapter, explicit composition
and deterministic tests. `examples/comfyui-text-to-image` is the operator consumer.
No new Kernel primitive, Artifact owner, Model provider, Workflow engine or registry.

Host composition binds one exact configuration revision, approved workflow,
Catalog entry and active Plugin lifecycle record. Requirement compatibility uses
the existing resolver. Authorization/dispatch remain existing reference owners;
claim_invocation prevents a second invocation of the same in-process Execution.
The synchronous deterministic string helper is not used. Unknown external effects
are settled explicitly. No exactly-once, durable recovery or hostile-process claim.
The local reference host explicitly creates operator authority; env/JSON do not.

## Contract and workflow

Request: bounded UTF-8 prompt and optional 63-bit nonnegative seed. Result:
GenerationResult with truthful effect and optional bounded GeneratedImage carrying
job/workflow/seed attribution. It owns bytes, not canonical Artifact custody.

One original built-in-node template is prepared for operator review. Exact bytes
are SHA-256 pinned at startup, then checked against the single supported shape.
Only prompt/seed slots change per invocation. Fixed 512x512 PNG, batch one and
sampler settings. Checkpoint is an operator profile basename, never consumer data.
Template source is an explicit operator file read with a byte ceiling, not a
filesystem path supplied in TextToImageRequest. No generic graph DSL or node loader.

## Transport and lifecycle

Literal loopback HTTP only, explicit port, no hostname resolution, proxy routing,
redirects or compression. Each request has bounded connect/exchange time, header,
JSON and image bytes. Preflight checks required built-in node declarations and
that the approved checkpoint is listed. This does not prove model compatibility;
live generation is required. Route declarations were read in the external local
server source (/prompt, /history/{prompt_id}, /object_info/{node_class}, /view).
The external runtime was not modified or run and its live version is unqualified.

One submission -> bounded history polling -> exactly output node 9 and one output
image -> safe filename/subfolder query -> bounded PNG validation -> typed result.
No direct output-directory reads. External filenames are locators, not trusted
paths or permanent image identity. PNG structure/CRC/dimensions are validated
without decoding compressed image pixels. No renderability/quality claim until live
inspection. Default ceilings and constraints are documented in the package README.

## Effects and cancellation

| Phase | Failure effect |
|---|---|
| Input/preflight before submission | NONE |
| Submission might have been accepted, including malformed/lost response | UNKNOWN |
| Polling deadline/cancel/runtime error without stronger evidence | UNKNOWN |
| Confirmed terminal generation success, retrieval/validation fails | COMPLETED generation; failed result |
| Validated PNG | COMPLETED, successful image result |

Cancellation stops local waits/I/O and propagates GenerationCancelled with the
known job/effect receipt; Execution settlement retains those facts. The outer
execution deadline preserves that receipt rather than losing the job ID.
No global or scoped interrupt is implemented: the safe shared-runtime default
is unknown provider cessation. There is no retry, queue clearing or deletion.
Diagnostic sink failures cannot alter settled effects; observations contain only
safe operation/configuration/category/size fields. Provider receipt is not Evidence
custody. No raw prompts, history, image bytes or provider tracebacks are logged.

## Security, hardware and limitations

Trusted single operator, not multi-tenant isolation or a sandbox for ComfyUI.
Built-in-node allowlisting cannot attest the code actually served by a compromised
runtime. Literal loopback does not authenticate the runtime. Model compatibility,
quality, CPU/CUDA performance and cancellation reconciliation require live evidence.
CPU, CUDA and low/high-VRAM modes have identical application semantics; runtime
hardware selection remains external deployment responsibility. No hardware flags
or installation paths occur in the application task contract.

In-memory authority/configuration lifecycle, no persistent job recovery; workflow
approval is an operator act, not a hash or environment variable. Returned PNGs may
contain provider metadata; do not treat them as sanitized for public distribution.
No automatic remote cessation or output retention guarantee. Core resource claims
are not GPU reservations. Package wheel qualification reuses the pinned root dev
toolchain and imports the wheel from a temporary location without installing it.

## Long-running jobs and reconciliation (slice 2)

Status: IMPLEMENTED — LOCALLY VALIDATED (maintainer-run, 2026-09-28). No Core,
ModelPort or TextToImageRequest change.

**Validation evidence (maintainer-run).**

- `python .alidate_comfyui_text_to_image.py` passed all 13 phases: typing,
  lint, contracts, transport, effects/composition, 97 policy/reconciliation
  tests (phase 7b), architecture, wheel build and import-without-install, and
  254 affected existing-repository checks. The phase 11 CRLF notice is
  informational only.
- Long-running policy: a new live generation with `--timeout 900` completed
  successfully (outcome success, effect completed). No hidden 300 s ceiling
  remains.
- Reconciliation: `--reconcile` of the earlier deadline-exceeded job
  `21829e58-1423-4262-a6ab-334fe4bd698f` printed `submission performed: NO`,
  `status: COMPLETED`, effect completed, and retrieved one validated PNG.
- Knowledge refinement: that job was UNKNOWN at LegoAI's 300 s deadline and
  was later shown COMPLETED by reconciliation, live and in the dedicated
  deterministic test.

Not recorded: repeat-reconciliation digest comparison, visual inspection of
the images, and elapsed time of the 900 s run.

**Evidence.** A real CPU generation of the fixed workflow took about 10m40s
(~640 s). LegoAI's 300 s deadline expired first and correctly returned
deadline exceeded / effect UNKNOWN / cessation UNKNOWN with the job ID. ComfyUI
kept running and later completed the image.

**Why 300 s could not be raised by flag alone.** Previously there were five
timing controls, and they were coupled: `timeout_seconds` (validated <= 300),
`poll_interval` (<= 5), `max_polls` (validated <= 300 and set separately),
LocalHTTP's hardcoded 10 s exchange / 3 s connect, and `prepare_local(timeout)`
(the Execution deadline). `--timeout 900` failed the 300 s validation. Even
without that check, 300 polls at 1 s would have ended the wait near 300 s.

**Completion policy.** `CompletionPolicy(max_wait_seconds=300,
poll_interval_seconds=1, request_timeout_seconds=10)` replaces those fields as
the single operator-side control. Its bounds are:

- total wait: finite, 0.5..1800 s;
- poll interval: 0.05..30 s and at most a tenth of the total wait;
- request timeout: 0.01..60 s and at most the total wait.

Hard maximum: 1800 s. That is the smallest round bound covering the known
900 s need, with ~2.8x headroom over the observed run for CPU variance. The
poll count is derived (`max_wait // interval + 1`) as a termination backstop
only. Operators set one value: `CompletionPolicy.for_wait(t)` derives
`interval = min(1, t/10)` and `request_timeout = min(10, t)`, which is what
the CLI `--timeout` uses. Zero, negative, NaN, infinity, None and bool values are rejected.

The total deadline is measured with a monotonic clock. The clock and sleep are
injectable, so tests simulate 640-900 s jobs instantly. A real-time
`asyncio.timeout` backstop remains in place. Each HTTP exchange gets
`min(request_timeout, remaining)`. If the request bound expires first, the
result is a DependencyFailure, not an exceeded total deadline. One hung call
cannot consume the whole wait.

The composition layer converts Core's absolute UTC `ExecutionContext.deadline`
to a relative timeout once, at invoke. That is a Core contract and is
unchanged. `prepare_local` now validates its timeout against the same 1800 s
ceiling. The CLI passes `policy.max_wait_seconds` to it and includes all three
policy values in the configuration-revision digest. CPU, CUDA and low-VRAM
runtimes use the identical application request; only the operator's policy
differs.

**Reconciliation.** `LocalComfyUIAdapter.reconcile(ProviderJobRef)`
(`JobReconciliationPort`) inspects one existing job and returns a
`ReconciliationResult`:

| Status | Meaning | Effect |
|---|---|---|
| PENDING | job is in the provider's running/pending queue | UNKNOWN |
| COMPLETED | history reports success; image or separate retrieval error | COMPLETED |
| FAILED | history reports `status_str: error` for this job | UNKNOWN |
| NOT_FOUND | provider no longer exposes the job (restart, eviction, clear) | UNKNOWN |
| UNRESOLVED | unreachable, malformed or unattributable evidence | UNKNOWN |

`ReconciliationStatus` is a provider observation, not a Core lifecycle and not
another ExecutionState. The effect is derived from the status, so it cannot
contradict it. NOT_FOUND never implies never-ran, failed or NONE.

**No-resubmission invariant.** Reconciliation wraps its transport in
`ReadOnlyTransport`, which raises a non-result RuntimeError on any non-GET or
body-bearing request. POST /prompt is therefore structurally unreachable, not
just unused. Tests assert POST count = 0 and GET-only calls for every scenario.
Reconcile never retries, interrupts, clears queues or deletes history.

**Race ordering.** Reconcile checks history, then `/queue`, then history
again. ComfyUI's `PromptQueue.task_done` removes a job from the running set and
inserts it into history under one mutex, and `get` moves it from pending to
running under the same mutex. So a job absent from the queue is either found by
the history recheck or genuinely no longer exposed.

**Attribution and trust limitation.** Reconcile accepts only
`provider == "comfyui"` and this adapter's binding. The history (or queue)
entry must name the exact job ID. Its recorded graph must be exactly
reproducible by `ApprovedWorkflow.bind` from the prompt and seed recorded in
that graph, which pins every other node and value to the SHA-256-approved
template. The seed in `GeneratedImage` comes from that recorded graph. Only
output node 9 with exactly one PNG is accepted, with the existing safe-locator
and PNG checks.

What this does **not** prove:

- that LegoAI, rather than another loopback client, submitted the job;
- anything about the configuration revision, operation or correlation
  identity, which the current submission does not send and ComfyUI history
  does not carry;
- that the file behind an output locator was not replaced after completion.
  Filenames are provider locators, and a cleared output directory can reuse
  names.

ComfyUI history is self-reported by an unauthenticated local runtime. There is
no cryptographic linkage.

**Knowledge refinement.** A deadline result of effect UNKNOWN, followed later
by a reconciliation showing COMPLETED, is not a contradiction. Each reflects
the evidence available at its time. The earlier receipt is not mutated. A
dedicated deterministic test covers UNKNOWN, then PENDING, then COMPLETED, with
one POST in total.

**Repeated reconciliation** is read-only. The same exposed output yields the
same bytes and SHA-256. There is no durable custody, exactly-once claim or
cross-restart ledger.

**Core boundary (not a gap for this slice).** Reconciliation runs as an
explicit operator act outside the ExecutionCoordinator. It does not reopen or
re-settle the original Execution, which stays settled with effect UNKNOWN.
Writing reconciled knowledge back as a governed, linked observation (ADR-008
§9) would need a Core owner-record update path. That is deferred together with
the durable ledger and is not faked here.

**Cancellation stays conservative.** Cancelling the LegoAI wait does not cancel
the ComfyUI job, and cessation stays UNKNOWN. There is no `/interrupt`, queue
mutation or runtime termination. The inspected runtime source has a
job-scoped cancel route. Adopting it needs version-specific qualification and
is deferred.

## Validation and exact live procedure

Run `python .\validate_comfyui_text_to_image.py`. It uses stdlib orchestration,
streams output, stops on failure, and runs contracts, fake/local-server transport,
effects/cancellation, composition, architecture, temporary wheel import and affected
existing checks. It never installs dependencies, changes source/Git state, starts
ComfyUI or claims live success. Temporary tool/build outputs are removed on exit.

Follow [the example instructions](../examples/comfyui-text-to-image/README.md) for
operator runtime startup, checkpoint prerequisites, template approval, exact command,
explicit output path, cancellation and optional second hardware profile. Paste
validation output and safe result evidence. Do not run Virtual Try-On afterward.

Deferred: governed reconciliation write-back/durable job ledger, remote TLS/auth
and Secret integration, job-scoped cancellation after
version-specific proof, Artifact publication/storage, process management, downloads,
custom nodes, generic graph editing, WebSocket transport, retry/recovery, GPU scheduling,
Virtual Try-On, ControlNet and LoRA management.
