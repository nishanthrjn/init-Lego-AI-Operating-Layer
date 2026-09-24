# M7 — one-step Agent implementation plan

Status: design in progress; local validation not run.

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

Model request assessment: ChatRequest currently contains messages only;
the adapter has no output-token or response-size configuration. A post-response
Agent validator can bound accepted output, but cannot bound provider generation
or transport allocation. Resolve this distinction before claiming the requested
bounded model-output contract. No Model contract/adapter change has been made.

Validation remains user-run: Agent contracts/architecture/integration, routing
and Model regressions, Core suite, typing/lint/format, wheel/sdist/fresh install,
example and diff check. DocuMind is needed only if shared Model code changes.
M8 remains unstarted.
