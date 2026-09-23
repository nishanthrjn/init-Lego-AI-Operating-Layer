# Engineering M6 — sandbox strategy assessment

Date: 2026-09-23. Status: Linux backend and pinned Python image confirmed by
maintainer; threat-scope gate unresolved; implementation and qualification pending.
Authority: the maintainer's current M6-only instruction, IA-001 and ADR-016,
subject to existing security, execution and package ownership contracts.
M1–M5 remain qualified within their recorded scopes. This record does not
qualify M6 or authorize later milestones.

## Observed environment and outstanding evidence

Read-only command discovery found:

- Docker CLI: `C:\Program Files\Docker\Docker\resources\bin\docker.exe`.
- WSL launcher: `C:\WINDOWS\system32\wsl.exe`.
- No Podman executable was returned by the same discovery.

Executable discovery does not establish a running daemon, Linux container mode,
local versus remote endpoint, resource-controller support, image availability,
or isolation. No runtime command, test, build, installation, image pull or
workload was executed internally. The maintainer retains local validation.

Required next evidence, executed locally by the maintainer:

```powershell
docker version
docker context show
docker image ls --digests --no-trunc
```

These commands do not install or pull anything. A daemon error is prerequisite
evidence, not a reason to weaken isolation or fall back to M5 host execution.
An empty image list requires a separately documented image preparation step;
no unverified digest, `latest` tag or automatic image acquisition is selected.
The endpoint and chosen image must be reviewed before backend-specific work is
treated as a concrete local qualification target.

### Returned local runtime evidence

The maintainer supplied successful prerequisite output on 2026-09-23:

- Docker client and Engine 29.5.3, API 1.54.
- Docker Desktop 4.77.0 (228796), server `linux/amd64`.
- Active context `desktop-linux`.
- containerd 2.2.4, runc 1.3.5 and docker-init 0.19.0.

This establishes reachable Linux Engine availability. It does not prove resource
enforcement, network isolation, safe artifact extraction or descendant cleanup.
The returned inventory contains database, application, .NET SDK, Alpine, mail
and telemetry images, but no dedicated Python reference image. Do not infer the
contents, credentials or suitability of unrelated application images.

Select Docker Desktop's Linux backend as the reference implementation target.
Use the Docker Official Python `3.14.7-slim-bookworm` image as the proposed first
script-only environment, then bind the adapter configuration to its returned
repository digest. This matches the pack's CPython 3.14 baseline and avoids
adding a test-tool installation requirement to the first isolation proof.
The versioned tag is for explicit preparation only, not immutable runtime identity.
The official image publisher currently lists this tag:
[Python image tags](https://hub.docker.com/_/python/tags?name=3.14.7-slim-bookworm).

Run this separate, intentional one-time download locally. It does not execute a
workload, alter other images or install Docker; it does use network and local disk.

```powershell
docker --context desktop-linux pull --platform linux/amd64 python:3.14.7-slim-bookworm
docker --context desktop-linux image inspect python:3.14.7-slim-bookworm --format '{{json .RepoDigests}}'
docker --context desktop-linux image inspect python:3.14.7-slim-bookworm --format '{{.Os}}/{{.Architecture}} {{.Id}}'
```

Return all output, including acquisition failures. Record the actual digest rather
than inventing one. Digest pinning fixes content identity, not publisher trust or
proof of safety. No automatic pulling will be part of sandbox execution; missing
runtime environments must produce an explicit unavailable condition.
See [Docker image pull](https://docs.docker.com/reference/cli/docker/image/pull/).

### Returned image evidence

The maintainer successfully pulled and inspected the proposed image. Reported
platform: `linux/amd64`. Reported immutable repository reference:

```text
python@sha256:82bc3c539b8813ada9d68c63b40158fa002f7f33de9bf3312a3dfdc0620dff56
```

The reported image ID has the same SHA-256 value. Retain repository reference
and image ID as distinct concepts even when the displayed values coincide.
No further image download is requested. This closes the runtime/image
availability prerequisite, not the isolation or architecture qualification gate.

## Candidate comparison

| Candidate | Isolation and controls | Windows, integration and operational tradeoff | Disposition |
|---|---|---|---|
| Docker Desktop Linux containers | Container filesystem/process/network namespaces and cgroup controls, within Desktop's Linux backend; shared backend kernel remains trusted | Linux Engine availability confirmed by maintainer; private bounded CLI integration and pinned images fit the first consumer; actual control tests still required | Selected reference target; image preparation and qualification pending |
| Windows Sandbox / Hyper-V guest | Separate kernel; configurable networking and mapped folders | Strong Windows boundary, but guest provisioning, unattended result transport and repeatable lifecycle require additional engineering; Windows-specific prerequisites | Alternative if container scope cannot meet the required threat model |
| WSL distribution alone | Linux environment with host integration; launching inside a distribution is not workload confinement | Installed launcher does not establish an isolated per-job environment; host interoperability and filesystem access require separate controls | Not selected as the workload boundary; may underpin Docker Desktop |
| Restricted Windows token / Job / AppContainer mechanisms | Different primitives cover different privilege, process and resource properties | Requires native API implementation, filesystem/network policy design and extensive Windows-specific proof | Do not hand-build for this first slice |
| External sandbox service / remote execution | Depends on provider boundary and evidence; introduces external disclosure and lifecycle dependencies | Credentials, service availability, cost and remote data policy; no configured service identified | Future replaceable adapter, not current prerequisite |

This comparison selects a direction, not an assertion that every OCI runtime
implements Docker flags or provides equivalent guarantees. The first adapter
should name the actually qualified backend precisely. Generic requests must
contain no Docker flags, image references or container handles.

Primary references: [Docker run controls](https://docs.docker.com/engine/containers/run/),
[Docker Desktop Windows permissions and backend boundary](https://docs.docker.com/desktop/setup/install/windows-permission-requirements/),
[WSL backend](https://docs.docker.com/desktop/features/wsl/), and
[Windows Sandbox configuration](https://learn.microsoft.com/en-us/windows/security/application-security/application-isolation/windows-sandbox/windows-sandbox-configure-using-wsb-file).
These describe mechanisms; they are not local qualification evidence.

## Smallest proposed slice

Keep the first engineering-specific implementation in `legoai-engineering` under
a separate sandbox module group. There is no current second consumer requiring a
new distribution. Separate pure values/Port from the backend so later extraction
does not impose Docker or engineering-check semantics on a generic contract.

Start with one bounded Python-script workload over explicitly selected text
inputs. Reuse M1 text values, M2 relative paths and bounded acquisition; do not
recursively copy the checkout, `.git`, `.venv`, credentials or host caches.
Snapshot construction must state its stable-namespace and cross-file consistency
limitations. No caller executable, arbitrary host argv, runtime flags, image
choice, host mount, environment bag or shell string belongs in the request.

Prefer transfer of bounded input bytes into an isolated working area, without
mounting the original source at all. Workload writes must remain sandbox-local.
Return only explicitly requested, bounded artifacts as data. Do not apply them
to the source: later M4 proposals retain digest preconditions and external
authorization. M5 check semantics remain authoritative for later sandboxed
checks; do not duplicate their outcome mapping in this script-first proof.

The operator chooses a pre-existing immutable environment identity. The adapter
must reject unsupported image/runtime settings rather than silently inherit
entrypoints, host mounts or broader privilege. Proposed defaults: network off,
non-root workload, no added capabilities or privilege escalation, no host PID or
network namespace, read-only root filesystem and explicitly bounded writable
workspace/temp surfaces. No Docker socket, user home or credentials are exposed.
CPU, memory, PID and writable-storage enforcement need backend-specific evidence.

Use bounded private CLI calls, independent stdout/stderr limits, closed stdin
except deliberate bounded input transport, explicit endpoint/configuration and
no automatic pulls. Identify each execution internally before creation so a
lost acknowledgment still permits targeted cleanup. Timeout/cancellation must
terminate the sandbox, not merely the Docker client. Cleanup failure must retain
enough safe identity for operator reconciliation without reporting success.

Artifact extraction is a separate untrusted-data boundary. Its implementation
must bound count, per-file bytes and aggregate bytes; reject traversal, aliases,
links and special files; and avoid extracting arbitrary archives onto the host.
The collection design must account for live descendants and races. A successful
container invocation alone does not establish artifact safety or truthful output.

## Authority and unresolved ADR-012

`adrs/ADR-012.md` is absent. The actual available record is
[ADR-INDEX §ADR-012](../adrs/ADR-INDEX.md#adr-012--isolation-mechanism-for-expanded-plugin-threat-scope),
which remains Proposed and addresses expanded Plugin threat scope. M6 must not
create acceptance by implication or claim hostile Plugin admission.

Workload isolation can inform that future decision, but does not isolate the
trusted host adapter, Core, Docker daemon or privileged co-located components.
The forward plan also gates hostile-code claims on ADR-012. Before qualification,
the M6 threat statement must reconcile its bounded workload claims with that
gate explicitly; changing canonical security or admission semantics requires
stopping and reporting the conflict under the maintainer's instruction.

### Scope decision requiring maintainer resolution

The forward plan's Phase D architecture check says **"Decide ADR-012 for
hostile-code scope"**. The latest M6 instruction §113 says not to conflate
engineering workload isolation with Plugin isolation or automatically accept
ADR-012. Section 112 requires a stop if canonical security/execution semantics
would need changing. The ADR index scopes ADR-012 to expanded Plugin threats,
but also restricts its deferred scope to trusted contributions. These texts do
not yet explicitly state whether this engineering-workload increment falls
inside or outside the forward plan's broader hostile-code gate.

This is not a claim that a Python workload is a Plugin. It is a mismatch between
the broader forward-plan gate and the narrower proposed implementation scope.
Do not silently resolve it by calling arbitrary repository code trusted, marking
ADR-012 Accepted, or claiming Docker availability supplies isolation evidence.

Recommended resolution: explicitly scope this M6 as an additive **engineering
workload isolation reference adapter**, leaving Plugin admission and ADR-012
unresolved. Clarify the Phase D gate accordingly under maintainer direction.
That scope would require the following concrete protection profile:

| Item | Proposed scope, requiring implementation and local proof |
|---|---|
| Attacker | Repository Python can use standard OS APIs, fork descendants, change its sandbox files, emit malformed output and attempt local/network escape |
| Protected assets | Original source checkout, other host files, host environment secrets and Docker control endpoint |
| Trusted enforcement base | Host adapter and interpreter, operator-selected image, Docker daemon/Desktop backend, runtime and Linux kernel |
| Inputs | Explicit bounded text files only; no source bind mount, host home, `.git`, `.venv` or credentials |
| Workload | One explicit script; non-root execution; no new privileges or caller-defined runtime options |
| Writes | Bounded private sandbox workspace/temp; source changes require later M4 proposals |
| Network | Disabled; no host networking, published ports or Docker socket |
| Lifetime | Sandbox-wide termination and observed cleanup; daemon/control loss reports uncertainty, never success |
| Artifacts | Explicit bounded paths collected after writers cannot race collection; reject links, special files and traversal; results remain untrusted data |
| Exclusions | Kernel/runtime exploits, compromised host administrator/daemon/image, hostile co-located Plugins, cross-tenant isolation, side-channel resistance and production service guarantees |

An alternative is to resolve ADR-012 first with a broader isolation decision.
Neither alternative is recorded as accepted here. Production implementation
remains stopped at this scope decision; no additional environment commands are
needed to resolve it. M1–M5 stay unchanged and qualified for their existing scopes.

Governance remains external. No `authorized=True`, duplicate Core execution
states, synthetic resource reservations, automatic Evidence custody or public
runtime facade is introduced. Sandbox activity is effectful even when source
files remain unchanged. Backend/local cleanup and runtime unavailability must
not be represented as proof of no effects.

## Implementation and qualification plan

1. Review remaining full authority/source/test material before production edits;
   resolve local runtime/image evidence and freeze the supported threat scope.
2. Specify inert bounded input, workload, policy, artifact and result/error values;
   a replaceable sandbox Port; and trusted backend configuration.
3. Implement controlled input preparation, constrained backend lifecycle, bounded
   capture, safe artifact collection and explicit cleanup/uncertainty handling.
4. Add pure/architecture/packaging tests and real-backend fixtures. Prove host
   canary and synthetic secret invisibility, unchanged source, network policy,
   timeout and descendant termination, artifact traversal/link/size rejection,
   output limits, resource controls and cleanup on success/failure/interruption.
5. Add a temporary-workspace example and a threat table that distinguishes
   implementation intent from locally demonstrated protections. Statically review
   and then hand off exact local tests and prerequisite commands. No mocked-only
   qualification and no M1–M5 regression waiver.

No production code or test was changed during this assessment. M6 implementation
is pending; `ENGINEERING_M6_COMPLETE = NO`. M6.5 model routing and M7 Agent work
remain unstarted. The broader roadmap's M6.5-before-Agents ordering is retained.
