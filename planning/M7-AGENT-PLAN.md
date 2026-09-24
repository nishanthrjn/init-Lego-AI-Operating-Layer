# M7 — one-step Agent implementation plan

Status: M7 COMPLETE — locally qualified for the documented one-step scope.

Authority: SPEC Agent and §5.4; ADR-002 §9 and Agent location;
ADR-015 lifetime limits; ADR-016 composition direction. Contracts belong to
`legoai.execution.agent`, not Intelligence. No canonical AgentId exists in
the current Kernel; a distinct execution-owner AgentId is needed.

Preflight: clean working tree at c75dd5b. Reviewed 12cbfaa's formatting,
import cleanup, test typing and validation scripts; documentation code-block
changes are formatting only. No unrelated behavioral change found.
M6 production last changed at 659cae0; unchanged since qualification.
The outstanding test is
`tests/test_sandbox_docker.py::test_cpu_memory_pid_and_storage_controls`.
It checks cgroup CPU/memory/swap/PID settings, tmpfs size/inode/mount flags,
PID exhaustion and workspace ENOSPC. Earlier OOM occurred while running
this combined workload; cause is not established. Only this test is due for
a separate local rerun; no M6 change is planned.

Proposed slice: immutable versioned definition, bounded UTF-8 request and
output contract, explicit execution context, one model step, exact M6.5 route,
typed result retaining downstream effect knowledge. No persistent operational
Agent instance or lifecycle supervisor is claimed. An owned invocation Port
separates the reference driver from private composition; only composition calls
the existing governed model helper and Coordinator. No direct ModelPort in
the Agent driver. No tools, memory, workflow, team, retries or fallback.

Model request decision (maintainer clarified): bound only accepted Agent output
after governed Chat completes. Reject empty, invalid UTF-8 or oversized content,
never truncate. No provider generation, transport allocation or cost bound is
claimed. Preserve ChatRequest, ModelPort, adapters and shared governed invocation.
Defer output token limits, bounded response transport, provider-specific token
translation and generation-cost/resource budgeting to future Model/runtime work.

Implementation: owner-local identity/output/status values; Port-level definition,
request/result records carry allowed Model values and existing Execution context.
The reference driver receives ModelRouterPort and an Agent-owned governed Chat
Port. Private composition realizes the latter with the existing Coordinator and
invoke_routed_chat. It never returns raw output as a successful Agent result until
validation. Result retains the unchanged downstream ExecutionResult, even when
Agent output validation fails after a successful model call. Unexpected errors
and cancellation propagate; no fabricated terminal result or retry.

Validation remains user-run: Agent contracts/architecture/integration, routing
and Model regressions, Core suite, typing/lint/format, wheel/sdist/fresh install,
example and diff check. DocuMind is needed only if shared Model code changes.
M8 remains unstarted.

Decision record: [ADR-017](../adrs/ADR-017.md), Proposed, records the scoped
composition and accepted-output decision without changing canonical documents.
Same-assistant static review checked owner direction, replay/error propagation,
no hidden retry, UTF-8 preallocation bounds and wheel/sdist inventory updates.
No independent review or internal execution is claimed. Maintainer evidence:
53 M7 tests, 100 routing/Model regressions and 1,478 Core tests passed; mypy,
lint, formatting, build/fresh install, example and whitespace checks passed.
The corrected targeted M6 resource-control test passed in 3.33s. Housekeeping
is closed; M6 production code and limits are unchanged. See docs/agent.md for
the environment/test-defect distinction and qualified limitations.
AGENT_M7_COMPLETE = YES. M8 remains unstarted.
