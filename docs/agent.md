# M7 — minimal reusable Agent foundation

**M7 COMPLETE — LOCALLY QUALIFIED FOR THE DOCUMENTED ONE-STEP SCOPE**

An Agent is a bounded software Actor using explicit behavior and externally
governed actions. A Model produces candidate information; a Role describes
responsibility; a Workflow owns process progression; a Team coordinates Actors.
None is interchangeable with an Agent, Capability, Tool or Principal.

## Scope and contracts

ADR-002 places the contracts in `legoai.execution.agent`. `values` contains
AgentId, AgentOutputContract and AgentExecutionStatus. `ports` contains
AgentDefinition, AgentRequest, AgentResult, AgentChatResult, AgentChatPort and
AgentRuntimePort. Definition/request/result records are immutable and slotted.

- AgentId identifies reusable behavior, distinct from the supplied ExecutionId.
  AgentDefinition records behavior Version, fixed instructions, logical
  ModelRequirement, output contract and input/prompt byte budgets. Changing
  behavior requires an operator-managed new version. No registry is introduced.
- AgentRequest carries nonblank strict UTF-8 text and the existing
  ExecutionContext, including explicit tenant, security reference, correlation,
  causation and optional deadline. Identity or instructions never grant authority.
- Instructions: at most 16384 UTF-8 bytes. Request text: at most 65536 bytes and
  no larger than the definition's max_input_bytes (1–65536). max_prompt_bytes
  (1–131072) covers the complete SYSTEM and USER text, including the deterministic
  output instruction. It measures content bytes, not provider framing or tokens.
  Inconsistent definition budgets fail at construction. Inputs are never truncated.
- AgentOutputContract accepts nonblank strict UTF-8 text of 1–max_bytes, where
  max_bytes is 1–65536. Invalid encodings, empty/blank and oversized responses
  fail explicitly. Validation checks character length before encoding to avoid
  allocating an encoding proportional to an already oversized response.
- AgentResult records the exact definition, ExecutionId, route decision, status,
  unchanged downstream ExecutionResult when present, and validated output only
  on success. Construction itself enforces success/output invariants. No arbitrary
  metadata, raw failed content, hidden reasoning or automatic Artifact is retained.

`OneStepAgentRuntime` in `legoai.reference.agent` constructs two Chat messages:
fixed SYSTEM instructions plus output constraint, and explicit USER input. Exactly
one model invocation may occur. There is no max_steps field or configurable loop;
only one step is supported. Calls retain no conversation. This is a per-request
driver, not a persistent Agent instance or implementation of its full lifecycle.

## Governed path and failures

The reference runtime calls M6.5 ModelRouterPort once. NO_MATCH and AMBIGUOUS
produce ROUTING_FAILED without invoking the model. Route/configuration identity
must match the request's operation subject; malformed wiring raises before I/O.
The selected immutable decision is passed unchanged to AgentChatPort.

Private `runtime._composition.agent.GovernedAgentChat` associates the exact
ConfiguredModelBinding and existing Coordinator. It coordinates authorization
and dispatch, then calls the unchanged invoke_routed_chat helper. The helper
checks pins and claims invocation once. No ModelPort/provider is accessible to
the reference Agent driver. The injected Port is trusted operator wiring, not
an attestation of arbitrary hostile Python implementations.

MODEL_FAILED retains the downstream error and effect, including UNKNOWN.
Successful Chat followed by invalid Agent output yields OUTPUT_INVALID while
preserving the model's SUCCEEDED/COMPLETED result. SUCCEEDED requires validated
bounded text. Agent status is a per-request result classification, not a new
canonical ExecutionState or Agent operational-instance state.

No retry, fallback, tool calling, memory, Workflow, Team, delegation, external
framework or provider expansion exists. No usage-accounting consumer is present,
so ModelUsage is not copied into a second accounting structure. Unexpected errors
and cancellation propagate; no false terminal result is manufactured. The existing
Coordinator enforces its admission deadline semantics; Agent adds no timeout or
claim of terminating an in-flight provider call. Existing volatile replay,
dispatch currentness and trusted-process limitations remain.

**Agent accepted-output size is bounded.** Provider generation, output-token
generation, HTTP/provider response allocation, transport memory and provider-side
cost are **not** bounded by this policy. ChatRequest, ModelPort, Ollama and shared
governed invocation are unchanged. Future Model/runtime optimization must address
token limits, bounded response transport, provider-specific max-token translation
and generation-cost/resource budgeting; none is implemented here.

## Public consumption path (ADR-014, CR-1b)

Applications obtain the governed Agent path through the public local host.
They never import `legoai.reference.*` or `legoai.runtime._composition.*`,
and never construct `Grant` or `SecurityContext` values. The wiring described
above remains the host's private implementation.

```python
from legoai.execution.agent.ports import AgentRequest
from legoai.runtime.api import LocalHostConfig, ModelPurpose
from legoai.runtime.local import open_local_host

# Composition root: operator configuration (grants, bindings, capacity) plus
# trusted code (a TrustedModelContribution or the built-in OllamaSettings).
host = open_local_host(config, {"revision": "r1", "binding": "offline"})

# Application code: public contracts only.
context = host.model_execution(ModelPurpose.CHAT)
result = await host.agent_runtime().run(definition, AgentRequest(context, text))
```

- `agent_runtime()` is bound to the binding pinned when the host opened. It
  takes no provider argument, and M7's single call with no retry is unchanged.
- `AgentRequest.context` must come from `model_execution(ModelPurpose.CHAT)` on
  the same host. Another host's context fails with `HostError(FOREIGN_CONTEXT)`
  before any model work.
- Denied authority (an unconfigured, expired or not-yet-valid operator grant)
  never reaches the provider. The effect mapping (NONE/COMPLETED/UNKNOWN) is
  the existing one.
- A host is confined to its opening thread and the event loop of its first
  async use (`WRONG_EVENT_LOOP`), and to `max_executions` minted contexts
  (`CAPACITY_EXHAUSTED`). Both are reference-host limits, not scalability
  claims.

See [ADR-014](../adrs/ADR-014.md) and the runnable
[`examples/local_host.py`](../examples/local_host.py).

## Local validation required

No runnable validation was performed internally. From the repository root, run
each command only after the previous command succeeds. Fresh explicit basetemp
paths avoid the previously observed shared Windows pytest cleanup failure.

```powershell
uv sync --locked --group dev --no-install-project
uv sync --locked --group dev --no-build-isolation
$m7Temp = Join-Path ([IO.Path]::GetTempPath()) ('legoai-m7-' + [guid]::NewGuid().ToString('N'))
uv run --locked --no-sync python -m pytest --basetemp "$m7Temp-agent" -q tests/unit/execution/test_agent.py tests/architecture/test_agent.py tests/integration/composition/test_agent.py
uv run --locked --no-sync python -m pytest --basetemp "$m7Temp-model" -q tests/unit/reference/test_model_routing.py tests/architecture/test_model_routing.py tests/unit/intelligence/test_model_values.py tests/unit/reference/test_model.py tests/integration/composition/test_model_governed.py
uv run --locked --no-sync python -m pytest --basetemp "$m7Temp-core"
uv run --locked --no-sync python -m mypy src tests examples/agent.py
uv run --locked --no-sync ruff check .
uv run --locked --no-sync ruff format --check .
uv build --no-build-isolation
uv run --locked --no-sync python examples/agent.py
git diff --check
```

The full Core suite builds wheel/sdist, checks inventories, installs offline into
a fresh environment and runs the Agent example outside the checkout using that
wheel. Expected example output: `succeeded`, then `A bounded Agent result.`
No live provider is needed. DocuMind need not rerun: shared Model code is unchanged.

After Core validation, separately rerun only the outstanding M6 observation:

```powershell
Push-Location packages/legoai-engineering
try {
    $m6Temp = Join-Path ([IO.Path]::GetTempPath()) ('legoai-m6-check-' + [guid]::NewGuid().ToString('N'))
    uv run --locked --no-sync python -m pytest --basetemp $m6Temp -q tests/test_sandbox_docker.py::test_cpu_memory_pid_and_storage_controls
    if ($LASTEXITCODE -ne 0) { throw 'Separate M6 regression observation requires classification' }
} finally {
    Pop-Location
}
```

Docker Desktop must be running with the qualified local image/configuration.
Do not run the whole Engineering suite. Classify failures from evidence as code,
test, environment, Docker-runtime or configuration defects; do not attribute
them automatically to M7. M7 failures additionally may be toolchain/dependency defects.

## Returned qualification evidence

Maintainer logs: M7 focused 53 passed; routing/Model regressions 100 passed;
Core 1,478 passed including fresh installation; format check 284 files clean;
git diff --check clean. Prior returned mypy (121 files), Ruff lint, build and
Agent example passed. No internal execution is claimed.

The first M6 setup failure was an ENVIRONMENT DEFECT (Docker unavailable).
With Docker available, the OOM reproduced. Source review identified a TEST DEFECT:
the PID probe started many independent Python interpreters inside the 128 MiB
memory limit, allowing memory exhaustion to precede PID exhaustion. The probe
now uses blocked copy-on-write fork children, requires pids.current == 32 at
EAGAIN, and kills/reaps its children. Existing memory/storage/CPU/PID assertions
and all M6 production limits remain unchanged. The maintainer's targeted rerun
passed: 1 passed in 3.33s. The environment failure and corrected test defect are
closed; M6 qualification remains valid for its documented scope.

All required local qualification evidence has been received.
`AGENT_M7_COMPLETE = YES`. M8 specialized engineering Agents remain unstarted.
