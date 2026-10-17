# FORGEAI-V0.2-REAL-SANDBOX-QUALIFICATION-1

Status: IMPLEMENTED — MAINTAINER VALIDATION REQUIRED.
Verification: **NOT RUN — Awaiting user execution**.

## Authority, baseline and scope

The maintainer requested qualification of the existing confirmed-context task
flow using real GENERIC Docker checks and replay models. Shared AGENTS.md,
accepted ADR-002/014 public composition boundaries and ADR-024 §8 disclosure
separation remain authoritative. No production behavior or accepted ADR changes.

Git baseline: `dca0cb999298b9ccfaea97ff318635fe2b9a4b45`. The preceding bounded-task
qualification remains uncommitted. Its existing test, validator and planning
record are pinned by normalized text SHA-256 in this validator, including staged
versions when present. README changes are limited to this follow-up. No existing
qualification file is deleted or relaxed to pass the scope gate.

The maintainer supplied passing evidence for preflight, exact context confirmation
and bounded-task qualification. The latest result was:

`FORGEAI-V0.2-BOUNDED-TASK-QUALIFICATION-1 LOCAL CHECKS PASSED; CONFIRMED-CONTEXT TASK LIFECYCLE LOCALLY QUALIFIED; REPLAY MODELS AND FAKE SANDBOX ONLY; NO LIVE MODEL QUALITY, REAL SANDBOX OR GLOBAL V0.2 QUALIFICATION; NO LIVE EXECUTION OR DEPLOYMENT AUTHORIZED`

That result is not real-sandbox evidence. This new slice is still pending.

## Reuse and exact scenarios

Reuse the existing disposable committed src/tests/pyproject Git fixture, recorded
proposal and review responses, `b011_proposal`, REWORK repair, public host,
WorkspaceGuard, authorized mutation, SandboxedEngineeringChecks, DockerSandbox
and SandboxImage.PYTHON_CHECKS. The test observer delegates every execute call to
DockerSandbox; it never supplies check outcomes. No second check engine or
sandbox implementation is introduced. No production defect has been established
by source inspection. A real execution failure must be classified from maintainer
evidence before considering a correction.

1. Success: explicit targets plus required pyproject.toml context; context
   confirmation; fresh acquisition; replay coding proposal; separate approval;
   actual mutation; actual Ruff, mypy and pytest; replay independent ACCEPT.
2. Check-triggered rework: reuse the existing intentionally invalid `assert False`
   fixture; actual Ruff B011 finding; fresh context confirmation; existing replay
   repair; separate approval; three real checks again; one final replay ACCEPT.
3. Four pre-effect controls: declined confirmation, changed confirmed bytes,
   declined proposal and denied mutation each require zero sandbox execute calls.

Tests assert exact event order, configured CheckRequest equality, check kinds and
results, exact changed paths, unchanged context-only bytes and HEAD, no added
paths, exact model input, retained first-attempt effects, released guard and
bounded TaskEvidence. The initial fixture creation commits only the disposable
repository; the task flow never commits, resets, stashes, cleans, pushes or rolls
back anything.

## Context and invocation proof

An observation-only wrapper around the existing authorized CodingEvidencePort
records returned immutable bundles. Each coding attempt requires exactly two
acquisitions: preflight and fresh authorized comparison. The bundles must match,
and the target/current_text/reference payload must equal those exact bytes.
Recorded decision inventory digests must equal confirmed preflight digests.
Rework requires new observations, changed bundle and a distinct confirmation
identity. A third unchecked read fails the count assertion.

Success has one coding call, one review, one approval/apply and three real checks.
Check rework has two coding calls, one final review, two approvals/applies and six
real checks. No first review runs on the failing candidate. No third attempt,
retry, provider reselection or fallback is introduced.

## Check identity and containment

GENERIC plan only: RUFF_CHECK, MYPY, PYTEST. Equality with the trusted worker plan
is asserted for every batch. Models provide proposal data, never commands, flags,
image selection, network settings, environment changes or install instructions.
PROJECT dependency preparation is excluded from real scenarios.

Use the existing qualified PYTHON_CHECKS image, whose recorded immutable local ID
at this baseline is
`sha256:4c64580306983d70e059f5f133f6bb3f82657c9c61fa96f562f42594f20269df`.
Production owns this identity. The validator clears the candidate-image override;
it does not substitute or qualify a rebuilt image.

Reuse Engineering test_sandbox_checks_docker and test_checks_sandboxed_docker
for pinned toolchain, network denial, filesystem/input boundaries, privilege and
resource limits, output bounds, cancellation and cleanup. The host-versus-sandbox
comparison case is explicitly excluded so these checks do not execute fixture
code through the host adapter. Existing synthetic contract suites cover trusted
command construction and no host fallback. This does not claim full Docker
isolation against every threat.

## Negative-control mapping

| Requirement | Evidence selected by validator |
| --- | --- |
| A-D zero Docker workloads before effects | New four-case pre-effect suite |
| E infrastructure failure is not code feedback | Existing real missing-Docker test, check adapter timeout/resource/cancellation cases and worker regressions |
| F unexpected Git changes stop | Existing worker final-state and rework integrity tests |
| G check feedback cannot widen paths | Existing check-rework and context scope regressions |
| H reviewer cannot authorize effects | Existing review/rework, independent approval and architecture controls |
| I no third proposal | Existing real persistent-finding test and bounded lifecycle ceilings |
| J no rollback/commit/push | New HEAD/path assertions, retained-effect regressions and architecture controls |

Partial/uncertain effects retain the existing failure semantics. Infrastructure
failures stop and are not relabeled as ordinary tool findings. Historical real
ForgeAI-1/2/3 and v0.1 tests are supplementary; the new positive/rework tests must
pass on the current confirmation path.

## Validator and prerequisites

New tests: examples/forgeai/tests/test_v0_2_real_sandbox_qualification.py.
New validator: validate_forgeai_v0_2_real_sandbox_qualification_1.py.
Documentation: this file and examples/forgeai/README.md only.

Required environment: qualified Windows Docker Desktop Linux host, existing
Docker CLI on PATH, running engine with supported resource/seccomp controls,
already-qualified pinned PYTHON_CHECKS image, Git, Python 3.14 and existing locked
root/ForgeAI/Engineering environments. No credentials are required.

The validator first enforces scope and preserved evidence. It then calls the
existing public metadata-only verify_ready in the ForgeAI environment. Missing
CLI, engine, image or unsupported controls fail before workloads. It reports the
closed reason and directs the maintainer to make the existing qualified setup
available. It never starts Docker, builds, pulls, repairs or installs anything.
An absent image requires a separately managed qualified-image restoration;
substituting an arbitrary tag or rebuilt image is not an acceptable workaround.

Only the focused phases receive LEGOAI_QUALIFY_FORGEAI_V02_SANDBOX=1. This opt-in
is removed before ordinary regressions so older offline validators do not silently
begin Docker execution merely by discovering the new test module. Real phases
fail on missing prerequisites; the validator rejects non-Windows execution rather
than qualifying a skipped real suite.

Phases include focused success/rework/negative tests, historical real workflows,
Engineering real containment/check suites, current context and bounded lifecycle,
ForgeAI offline regressions, Engineering sandbox/check/mutation/path contracts,
LOCAL/REMOTE model and custody preservation, KiSSKI synthetic compatibility,
architecture, typing, lint, formatting and working/staged whitespace. Synthetic
protocol regressions may use local test servers; no external provider is called.
No build/clean-install suite or live model is included.

From the repository root, the maintainer runs:

```powershell
uv run --locked --offline --no-sync python .\validate_forgeai_v0_2_real_sandbox_qualification_1.py
if ($LASTEXITCODE -ne 0) { throw 'ForgeAI v0.2 real-sandbox qualification failed' }
```

The agent has not executed tests, validators, Docker, tools, builds, network calls,
models or commits. All current results remain pending.

## Exact permitted success claim

Only after successful maintainer execution:

`FORGEAI-V0.2-REAL-SANDBOX-QUALIFICATION-1 LOCALLY QUALIFIED; CONFIRMED-CONTEXT BOUNDED TASK FLOW VERIFIED WITH REAL SANDBOXED CHECKS; REPLAY MODELS ONLY; NO LIVE MODEL QUALITY OR GLOBAL V0.2/DEPLOYMENT QUALIFICATION; NO LIVE PROVIDER EXECUTION AUTHORIZED`

Limits: one bounded synthetic repository, the existing GENERIC profile, current
qualified Windows/Docker/image environment. No live coding-quality, arbitrary
repository, global v0.2 readiness, deployment or comprehensive isolation claim.

If this passes, recommend separately authorized
FORGEAI-V0.2-KISSKI-BOUNDED-LIVE-PILOT-1 with one exact evidence-supported model,
explicit disclosure and mutation approvals, a bounded test repository and at most
one rework. That pilot is not implemented or authorized here.

Proposed commit: `test(forgeai): qualify confirmed context with real sandbox checks`.
