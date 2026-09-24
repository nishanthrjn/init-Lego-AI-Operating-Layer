# M7 — minimal reusable Agent foundation

**IMPLEMENTATION COMPLETE — LOCAL VALIDATION PENDING**

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
Do not run the whole Engineering suite. If this passes, record the earlier OOM
as a non-reproduced regression observation. Otherwise classify from evidence as
code, test, environment, Docker-runtime or configuration defect; do not attribute
it automatically to M7. M7 failures additionally may be toolchain/dependency defects.

M1–M6.5 retain their documented qualification. M7 local evidence is pending;
`AGENT_M7_COMPLETE = NO`. M8 specialized engineering Agents remain unstarted.
