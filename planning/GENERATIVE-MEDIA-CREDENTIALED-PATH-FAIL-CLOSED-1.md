# GENERATIVE-MEDIA-CREDENTIALED-PATH-FAIL-CLOSED-1

Status: IMPLEMENTED — MAINTAINER VALIDATION REQUIRED.
Verification: **NOT RUN — Awaiting user execution**.
Debt: **H-01 CLOSURE PENDING LOCAL VALIDATION**; H-01 remains open.
Baseline: `a61590446b34586a0f30fa8da50020a801ee5cd5`.

## Authority and scope

Explicit maintainer authorization is for removing unsupported credential behavior.
ADR-026 is Accepted; ADR-027 remains Deferred under
`ADR_027_DEFERRED_PENDING_PROVIDER_CONTRACT`; B-02 is STILL_BLOCKED.
Credentialed media is unsupported/unqualified; remote VTO remains unsupported.
No MPBP-1, new credential interface, provider adapter, source, custody, Core,
Model, dependency or accepted-ADR change. M-01 and M-04 remain closed.
Accepted ADR-020 governs remote personal-image refusal; ADR-026 permits the
secret-free execution facade without accepting any credential profile.

## Pre-fix source trace

```text
ProviderConfig / TOML -> validate auth + env:NAME syntax (no material)
probe_provider -> resolve_secret(ref, os.environ or supplied mapping)
  -> mapping.get(NAME) -> raw token -> factory(origin, token)
  -> LocalHTTP / RemoteHTTPS -> retained Bearer Authorization
  -> explicit confirm OR auto discover (v2 then legacy) -> provider send
open_text_to_image / open_image_transfer -> _driver -> same resolver/factory
  -> discover -> driver -> workflow/adapter -> subsequent provider operations
open_virtual_try_on -> M-04 remote refusal; local -> _driver -> same path
preflight_virtual_try_on -> remote refusal; local workflow -> same resolver
  -> factory -> confirm/discover -> driver preflight
direct resolve_secret -> supplied mapping.get -> raw token
direct LocalHTTP / RemoteHTTPS(token=...) -> Authorization -> _exchange send
```

Discovery and family confirmation consume the constructed transport; they own
protocol observations, not credential authority. The pre-fix public resolver
could return raw material independently of service construction. Low-level token
parameters could also bypass a service-only correction. These paths are closed.

## Correction and observable behavior

Service admission uses only `auth != "none" or secret_ref is not None`, before
factory selection, resolution, workflow loading or discovery. Configuration
parsing and reference recognition remain unchanged. Local does not imply
secret-free: local bearer configurations refuse too. Current remote configuration
requires bearer auth, so configured remote operations refuse without weakening
that rule. No fallback or alternate family/endpoint is attempted after refusal.

The existing public `ProviderError` uses `POLICY_VIOLATION` with the new closed
reason `credentialled_provider_unsupported`. It contains no reference, variable
name, material, upstream evidence or exception cause. This is not a missing-key,
invalid-key or authentication-rejected result. VTO preflight preserves its report
contract and records a failed credential-scope line. Remote VTO still returns its
earlier independent M-04 refusal before credential admission.

`resolve_secret` retains its signature as a refusing compatibility entry point:
None returns None, any reference refuses without reading the supplied mapping.
Service code no longer imports or calls it and no longer imports os. Existing
`environ` arguments remain accepted but unused; mere mapping presence on a
secret-free configuration does not trigger refusal or inspection.

The default transport factory refuses credentialed configurations and non-None
tokens before HTTP construction. Direct HTTP token parameters refuse with a safe
ValueError carrying the same reason before TLS setup or Authorization creation.
The exchange also rejects a non-None authorization argument before writing;
request headers accept only Content-Type and Idempotency-Key, used by existing
drivers. No Authorization material is serialized. Secret-free protocol budgets,
framing, deadlines, cancellation, reconciliation and effect truth are unchanged.
Transport injection is trusted Python host/test wiring, not hostile-code isolation;
arbitrary injected code cannot be certified credential-free by inspecting config.

## Prepared verification

The new `test_credential_scope.py` matrix covers local/remote, auto/legacy/v2,
supplied/default environment, injected/default factories and all five service
entry points. Raising environment/mapping sentinels and resolution, workflow,
discovery, confirmation, HTTP and network spies prove refusal ordering. These
cases fail on the pre-fix resolver/factory paths. Direct resolver/factory/transport
and header bypass controls supplement the service tests. An explicit secret-free
diagnostic succeeds using a deterministic fake even with raising mappings.

Existing credential-positive tests now assert the intentionally changed refusal
contract, rather than preserving unsupported token transmission. Existing local
text/VTO invocation, transfer, diagnostics, public facade and effect tests remain
positive controls. Architecture controls detect environment access in the three
credential entry modules, with forbidden and allowed snippets. This supplements,
rather than substitutes for, behavior tests. Model Secret regression sources are
unchanged and run with synthetic canaries only; no real credentials are requested.

The maintainer validator checks the exact changed-file scope, focused and existing
deterministic suites, architecture, Model Secret regressions, offline wheel builds
and isolated install/refusal smoke checks, typing, lint, format and working/staged
whitespace. It does not select socket-server tests, Docker/GPU/ComfyUI workloads
or live scripts. Child environments copy only named platform/process settings,
not credential variables. Dependencies must already be installed/cached.

## Design review

SRP/SoC: admission decides supported scope, config still represents data, drivers
retain protocols. OCP: future accepted credentials require their own reviewed
profile, never a bypass of this refusal. LSP: secret-free driver contracts remain.
ISP: no new interface. DIP/LoD: no Secret or private Runtime dependency.
DRY: existing auth/reference facts drive one service guard; lower entry points
independently reject their own raw-material arguments. KISS/YAGNI: refusal replaces
resolution; no speculative MPBP-1 mechanism, broker, callback or transport Port.

## Maintainer procedure and closure

Run from the repository root in the existing locked Python 3.14 uv environment.
Prerequisites: pytest, mypy, Ruff, hatchling/editables and uv already available;
offline build requirements satisfied. No credential environment variables needed.

```powershell
uv run --locked --offline --no-sync python .\validate_generativemedia_credentialed_path_fail_closed_1.py
if ($LASTEXITCODE -ne 0) { throw 'Generative Media credential fail-closed validation failed' }
```

Paste the complete output. Expected: every phase passes and exit code is zero.
Only after successful maintainer validation may the slice be recorded as
`GENERATIVE-MEDIA-CREDENTIALED-PATH-FAIL-CLOSED-1 LOCALLY QUALIFIED` and
`H-01 CLOSED FOR SUPPORTED SCOPE`.
The claim means: no supported Generative Media operation resolves/uses credentials;
unsupported credential-bearing paths refuse before material access/use.
It does not qualify security globally, any provider, credentials, live ComfyUI,
remote VTO or MPBP-1. ADR-027 stays Deferred and its reopening trigger is unchanged.

After validation, record that narrow closure, prepare the safety commit under
maintainer control, stop media credential architecture work, and return to ForgeAI.
No commit or next milestone is performed in this preparation.
