# M6 implementation plan and scoped decision

Maintainer decision, 2026-09-23: engineering workload isolation is distinct
from Plugin isolation. The Phase D planning gate is clarified accordingly.
ADR-012 remains Proposed; no canonical or accepted ADR meaning changes.
This additive ADR-016 reference capability is not a governed invocation facade.

Implement `legoai_engineering.sandbox`: immutable bounded script/text inputs,
policy, artifacts/results, typed failures and a replaceable synchronous Port.
Keep Docker configuration and private process transport outside the Port.
Zero runtime dependencies; no new distribution without a second consumer.

Use the selected Windows Docker Desktop Linux backend and pinned Python image.
Pass explicit input bytes, never host mounts. A private, size/inode-bounded
tmpfs Docker volume holds the workspace. Two non-root, capability-free
containers mount it: the workload writable, a trusted collector read-only.
Start the collector first to retain the tmpfs mount after workload termination.
Run the script as workload PID 1. Confirm that container has stopped before
the collector opens explicit artifact paths. This avoids racing descendants,
executing collectors alongside untrusted processes, or extracting host archives.
The collector does not load workspace modules (`python -I -B`).

Both containers have network disabled, read-only roots, finite memory/CPU/PID
limits and private bounded temporary storage. CLI calls use an empty private
Docker configuration, explicit local Desktop endpoint and minimal environment.
No image pull, dependency installation, shell string or caller runtime flags.

All control/capture steps have deadlines and bounded pipes. Track generated
resource identities before creation; cleanup removes both containers then the
volume, checks absence, and reports uncertainty on lost control or ambiguous
creation. Cancellation is cooperative polling through a signal; cleanup ignores
that signal. Interpreter termination/host crash is outside guaranteed cleanup.

Qualification covers values, import/dependency boundaries, installed wheel,
real workload exits, source/canary/secret isolation, network, non-root/capabilities,
read-only root, resource limits, output/artifact bounds, unsafe links/special files,
descendants, cancellation and cleanup. Fault injection supplements real-backend
tests for control/cleanup loss. No tests or toolchain commands run internally.

Protected assets: source checkout, other host files, host environment secrets,
Docker control endpoint. Trusted enforcement base: host adapter/interpreter,
operator-selected pinned image, Docker daemon/Desktop backend, runtime, Linux
kernel. Repository Python may use OS APIs, spawn descendants, mutate sandbox
files, emit malformed output, and attempt filesystem/network escape.

Explicit exclusions: kernel/runtime exploits; compromised Docker daemon;
compromised host administrator; compromised reference image; hostile co-located
Plugins; cross-tenant isolation; side-channel resistance; production multi-tenant
sandbox service guarantees. These components/threats are outside M6 protection.

M1–M5 retain their existing qualification. M6 implementation and scoped local
qualification are complete based on maintainer-supplied results below. M6.5 and
M7 remain unstarted. See the package README for reproducible validation commands.

## Implementation review and limitations

`SandboxExecutionPort.execute` is a synchronous preparatory capability under
ADR-016, separate from `EngineeringCheckPort`. It does not implement the complete
governed canonical isolation-use lifecycle in Contracts §26.2; future composition
must supply admission, authorization, effect/resource accounting and custody.
No direct Core/private runtime dependency or duplicate canonical owner is added.
The scope clarification changes only forward planning; ADR-012 remains Proposed.

The backend is deliberately Windows Docker Desktop Linux, `linux/amd64`, cgroup
v2, with the already selected image digest. No generic OCI/cross-platform support
is implied. Both containers drop all capabilities and run UID/GID 65534; the
collector is not a root supervisor. The only shared mount is the generated tmpfs
volume. The collector's mount is read-only and its process namespace is separate.
Docker confirms workload exit before collection. No archive is extracted on host.

Docker documents local-driver tmpfs volumes on Linux/Desktop in
[volume create](https://docs.docker.com/reference/cli/docker/volume/create/).
The extra collector is necessary to retain the mount across workload exit and
avoid the documented tmpfs limitations of
[docker cp](https://docs.docker.com/reference/cli/docker/container/cp/).
These primary references justify design choices, not qualification claims.
The workload runs as the namespace init process: Linux specifies descendant
termination when that process exits in
[pid_namespaces(7)](https://man7.org/linux/man-pages/man7/pid_namespaces.7.html).
Real descendant observation and post-execution Docker resource absence remain
mandatory local tests of this implementation, not consequences inferred from
documentation alone.

Review covers bounded pipe transport, encoded input sizing, immutable values,
safe logical paths, fixed flags, EOF/deadline/cancellation, no ambient Docker
configuration, ancestor link and hardlink rejection, stopped-writer ordering,
and cleanup uncertainty. Fault injection tests preserve original causes when
cleanup supersedes failure. A lost creation acknowledgement remains uncertain
even if a subsequent listing is empty; no implicit retry is authorized.

No test, Docker workload, package build, formatter, linter or typechecker was run
internally. Local validation must establish the actual boundary and M1–M5
regressions before `ENGINEERING_M6_COMPLETE = YES` may be recorded.

## Returned local validation and closure

The maintainer supplied a real Windows Docker Desktop Linux run: Docker Engine
29.5.3 / Desktop 4.77.0, the expected local named pipe, and the pinned image on
`linux/amd64`. Pytest reported **265 passed, 1 skipped in 95.68 seconds**; the
only skip was the pre-existing POSIX special-file boundary. Thus no M6 test
skipped. Mypy passed for **48 source files**. The sandbox example printed
`hello isolated LegoAI` and `source unchanged; synthetic host secret absent`.
The diff check reported only LF-to-CRLF conversion warnings.

Initial remaining failures were code style defects: two Ruff I001 import-order
findings and formatting differences in four files. The reported edits were
applied without behavioral changes. A subsequent single tuple-layout correction
resolved the last format finding. Final maintainer output reports **All checks
passed!** and **48 files already formatted**; the diff check emitted only
LF-to-CRLF conversion warnings. No internal validation command was run.
`ENGINEERING_M6_COMPLETE = YES` for the declared reference scope. Stop here;
M6.5 and M7 remain unstarted.

## Completion report

Evidence is the maintainer's local execution, not an independent security audit.
Fault injection covers control/cleanup loss; real daemon compromise, outages and
host-crash recovery are not qualified. Historical assessment text is superseded
by this closure for current milestone status.

| # | Requested item | Result |
| --- | --- | --- |
| 1 | Package placement | Separate `sandbox` module group in `legoai-engineering`; no second consumer justifies another distribution. |
| 2 | Files created | `sandbox/{__init__,values,errors,ports,docker,_process,_programs}.py`; `tests/test_sandbox.py`, `tests/test_sandbox_docker.py`; `examples/sandbox_intake.py`; this implementation record. |
| 3 | Files modified | Root/package READMEs; `tests/test_architecture.py`, `tests/test_package_install.py`; forward plan and M6 assessment. Final corrections changed only imports/formatting in `docker.py`, `values.py` and the two affected test files. |
| 4 | Sandbox types | `SandboxRequest`, `SandboxPolicy`, `SandboxArtifact`, `SandboxResult`, `SandboxFailure`, `SandboxError`, `CancellationSignal`. |
| 5 | Port | `SandboxExecutionPort.execute(request, cancellation)`. |
| 6 | Adapter | `DockerSandbox`, with inert operator-owned `DockerSandboxConfig`. |
| 7 | Backend | Windows Docker Desktop 4.77.0, Engine 29.5.3, Linux amd64, desktop-linux named pipe; pinned Python digest recorded in README. |
| 8 | Rationale | Available reference runtime with namespace/cgroup controls; avoids hand-building Windows isolation; generic Port remains backend-independent. |
| 9 | Runtime dependencies | None added. |
| 10 | Prerequisites | CPython 3.14, Docker Desktop Linux CLI/daemon, cgroup v2/seccomp, preloaded pinned image. |
| 11 | Preparation | Explicit bounded supplied text, optionally acquired through M2; bounded encoded stdin transfer into private tmpfs volume. |
| 12 | Source semantics | No source bind mount; only selected bytes copied. No atomic cross-file snapshot claim. |
| 13 | Writable surfaces | Private `/work` 32 MiB/4,096 inodes; `/tmp` 8 MiB/1,024 inodes; `/dev/shm` 8 MiB; private device surfaces; image root read-only. |
| 14 | Host filesystem | Real canary/source escape attempts passed within the declared trusted-runtime scope. |
| 15 | Git metadata | `.git` excluded; no host Git configuration or credential mounts. |
| 16 | Environment | Host CLI retains SystemRoot/WINDIR plus private TEMP/TMP; workload receives fixed PATH/LANG/HOME/TMPDIR only. |
| 17 | Secrets | Synthetic host secret absent in real workload/example; explicitly supplied file contents remain caller disclosure responsibility. |
| 18 | Network | Disabled; loopback-only namespace and non-loopback denial tested; no host network, published ports or control socket. |
| 19 | Timeout | Default 60 seconds, range 1–300 across preparation/run/collection; cleanup separately bounded to 60 seconds. |
| 20 | Descendants | Observed real descendant before timeout/cancellation; container removal checked; post-parent writer test passed. |
| 21 | CPU | One CPU quota per container; cgroup quota/period verified, not scheduling fairness or performance guarantees. |
| 22 | Memory | 128 MiB per container, swap disabled; cgroup settings and actual OOM tested. |
| 23 | PIDs | 32 per container; bounded creation reached EAGAIN. |
| 24 | Output | Independently bounded stdout/stderr; real overflow tests passed. |
| 25 | Artifacts | At most 16 explicit paths; default 256 KiB each/1 MiB aggregate, supported ceilings 1 MiB each/4 MiB aggregate. |
| 26 | Extraction | Separate read-only collector after workload termination; descriptor-relative no-follow opens; reject links/hardlinks/special files/traversal; no host archive extraction. |
| 27 | Privilege restrictions | No privileged mode, added capabilities, host PID/network, host mounts or Docker socket; no-new-privileges required. |
| 28 | User | Both containers UID/GID 65534; workload PID 1; non-root and effective capabilities checked. |
| 29 | Runtime unavailable | Typed `RUNTIME_UNAVAILABLE`; no host-execution fallback. |
| 30 | Image unavailable | Typed `ENVIRONMENT_UNAVAILABLE`; no automatic image pull. |
| 31 | Nonzero exit | Completed `SandboxResult` with observed exit code; only Docker-observed OOM classified as `RESOURCE_LIMIT`. |
| 32 | Cleanup | Remove workload, collector and generated volume; confirm absence; no broad prune. |
| 33 | Cleanup failure | Typed `CLEANUP`, safe generated recovery IDs, preserved causal chain; lost creation acknowledgement remains uncertain. Fault-injection coverage, not real outage qualification. |
| 34 | Cancellation | Cooperative Event-compatible signal; sandbox-wide cleanup; KeyboardInterrupt unwinds cleanup. Async cancellation requires explicit signal bridging. |
| 35 | M4 direction | Returned artifacts are untrusted data; source application still needs M4 preconditions and external governance. |
| 36 | M5 direction | Engineering checks remain separate; sandboxed pytest/Ruff/mypy composition is not implemented. |
| 37 | Governance | Mechanism only; no authorization flag, admission facade, resource reservation or automatic canonical Evidence custody. |
| 38 | ADR-012 | Remains Proposed; engineering workload isolation does not qualify hostile/untrusted Plugin admission. |
| 39 | Architecture tests | Import direction, inert initialization, closed host process boundary, fixed flags and replaceable Port consumer passed. |
| 40 | Isolation tests | Host/source, secrets, network, privilege, resource limits, output/artifact bounds, unsafe files and lifetime tests passed. |
| 41 | Real backend | All M6 Windows Docker tests passed; no M6 skips. |
| 42 | Packaging | Wheel/sdist inventory and fresh installation checks included in passing pytest suite. |
| 43 | Pytest | 265 passed, 1 expected POSIX-only skip, 95.68 seconds. |
| 44 | Mypy | No issues in 48 source files. |
| 45 | Ruff | Final lint passed; 48 files already formatted. |
| 46 | Example | Printed `hello isolated LegoAI` and `source unchanged; synthetic host secret absent`. |
| 47 | M1 regression | Included in passing suite; prior scope retained. |
| 48 | M2 regression | Included; only existing POSIX special-file test skipped on Windows. |
| 49 | M3 regression | Included in passing suite; prior scope retained. |
| 50 | M4 regression | Included in passing suite; prior scope retained. |
| 51 | M5 regression | Included in passing suite; trusted-local scope retained. |
| 52 | Canonical documents | No SPEC, Architecture, Contracts, Security or accepted ADR semantics changed. |
| 53 | ADR-016 | Additive reusable capability; no Core-private dependency, new distribution or speculative owner. |
| 54 | Limitations | Fixed reference environment/script workload; no atomic input snapshot, global concurrency budget, automatic mutation or forced-host-termination cleanup guarantee. |
| 55 | Residual risks | Kernel/runtime exploits; compromised daemon, host administrator or image; hostile co-located Plugins; cross-tenant attacks; side channels; production multi-tenant service guarantees are explicitly excluded. |
| 56 | Qualified scope | Bounded repository-controlled/generated Python engineering workloads on the tested Windows Docker Desktop Linux profile, with trusted enforcement base and documented exclusions. |
| 57 | Non-qualified scope | Plugin isolation/admission, general hostile-code execution across LegoAI, other backends/platforms, multi-tenant production deployment and complete governed isolation lifecycle. |
| 58 | Next milestone | M6.5 model/provider registry and routing, only under a subsequent task. |
| 59 | M7 started? | No. M6.5 also remains unstarted. |
| 60 | Completion | `ENGINEERING_M6_COMPLETE = YES` for the scoped reference qualification. |
