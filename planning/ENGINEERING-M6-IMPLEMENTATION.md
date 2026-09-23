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

M1–M5 retain their existing qualification. M6 implementation is complete; local
validation is pending. M6.5 and M7 remain unstarted. No M6 protection is locally
qualified yet. See the package README for exact commands and qualification tests.

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
