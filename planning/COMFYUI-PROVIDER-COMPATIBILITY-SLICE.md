# ComfyUI Provider Compatibility and Configuration Layer

Status: IMPLEMENTED — DETERMINISTIC AND LOCAL VALIDATED; CLOUD DETECTED, SUBMISSION NOT AUTHORIZED.

**Validation evidence (maintainer-run, 2026-09-28).**

- `uv run --locked python .alidate_comfyui_provider_compatibility.py`
  passed all 16 phases. That covers 37 configuration, 14 discovery, 115
  legacy-regression, 34 v2, 20 remote-transport, 51 reconciliation/effects
  and 8 reuse tests, the wheel build and import, and 254 affected existing
  checks.
- Local probe (`comfy-local.toml`, `api_family = "auto"`): reachable,
  discovered `legacy` 0.37.0, `submission performed: NO`.
- Configuration-driven local generation through the port-only
  `generative-media-minimal/app.py`: success, effect completed, one validated
  PNG.
- Cloud probe (`comfy-cloud.toml`, explicit `v2`): `unsupported_api`. The
  structured v2 `not_found` evidence was not observed, so v2 support on
  `cloud.comfy.org` is **PROVIDER CAPABILITY NOT ESTABLISHED**. The probe
  failed closed, and detection was not loosened. After the probe gained
  sanitized evidence, the re-run showed
  `v2 probe: status=404 type=application/json code=job_not_found`. Bearer
  auth is accepted (no 401/403) and the route answers with a structured
  error, but `job_not_found` appears in neither the v2 reference (which
  documents `not_found`) nor the Cloud v1 job reference. Comfy-Org's
  official `comfy-python-sdk` (`src/comfy_sdk/exceptions.py` at `c0c4a33`)
  confirms the discrepancy: "public-api currently returns entity-specific 404
  codes even though the spec documents the generic `not_found`". It maps
  `job_not_found` to `NotFound`. The v2 driver now normalizes exactly
  `{not_found, job_not_found}` in one place (`is_job_not_found`), used for
  both detection and job absence. Bare or other structured 404s are still
  rejected. Re-run of the Cloud probe is pending. Cloud submit, status,
  `/workflow` and signed-URL retrieval remain unqualified until one live
  Cloud generation.
- Cloud probe re-run after the fix: reachable, `api_family: v2`, capabilities
  as declared, `submission performed: NO`. Detection and Bearer auth for reads
  are validated live.
- Cloud generation through the unchanged `app.py` (config switch only):
  `failed`, effect `none`, no job, `AuthorizationDenied`/`forbidden`. This is
  a documented v2 rejection that creates no job, so no job was created and no
  credits were spent. The account or key can read jobs but is not permitted
  to submit. Neither the docs nor the SDK name the cause (the SDK's
  `403 not_enabled` applies to its separate Router surface). Results now carry
  sanitized evidence (status, media type, error-code identifier), so the next
  attempt shows Cloud's code. Cloud submit, status and retrieval remain
  unqualified.

Builds on [the text-to-image slice](COMFYUI-TEXT-TO-IMAGE-VERTICAL-SLICE.md).
No Core, ModelPort or `TextToImageRequest` change. No live runtime or Cloud
calls were made during implementation; only static checks ran.

## Provider-neutral boundary

```
Application ── TextToImagePort / JobReconciliationPort   (ports.py)
      │            ▲ returned by open_text_to_image(config)   (service.py)
      │            │ governed per call: prepare_local + invoke
      ▼
ComfyTextToImageAdapter  (comfyui.py) — deadline, effects, attribution, PNG
      │ ComfyDriver protocol (drivers/base.py) — internal, not Core
      ├── LegacyDriver (drivers/legacy.py)  /prompt /history /queue /view /object_info
      └── V2Driver     (drivers/v2.py)      /api/v2/jobs, /api/v2/assets
            │ Transport: LocalHTTP (loopback) | RemoteHTTPS (allowlisted origin)
```

The engine owns everything that must not be duplicated:

- the completion policy and monotonic `Budget`;
- effect transitions and the no-resubmission rule;
- the reconcile disposition;
- workflow attribution (`ApprovedWorkflow.attribute`);
- `GeneratedImage` PNG validation.

A driver translates one API family into `JobObservation`s, which reuse
`ReconciliationStatus`. There is no new lifecycle enum. Applications never
see local vs. cloud, routes, versions, auth format, polling or asset
conventions.

## Supported API families

| Family | Where | Evidence used | Status |
|---|---|---|---|
| `legacy` | OSS ComfyUI server (inspected: 0.37.0) | `/system_stats` → `system.comfyui_version` | Live-qualified in previous slices |
| `v2` (beta) | Comfy Cloud `https://cloud.comfy.org`, `https://{deployment}.run.comfy.app`, self-hosted via `comfy-api-proxy` | structured `404 {"error":{"code":"not_found"}}` for a well-formed unknown job id | Deterministic only; live pending |
| Cloud v1 (`X-API-Key`, `/api/prompt`…) | — | — | Not implemented: upstream deprecated it in favour of v2, and its `/api/view` semantics are undocumented (**PROVIDER CAPABILITY NOT ESTABLISHED**) |

Sources: docs.comfy.org `api-reference/v2` (submit, job status, workflow,
request cancellation, asset bytes), `development/cloud/overview`, and the
installed OSS server source (`server.py`, `comfy_execution/jobs.py`).

Compatibility assumptions (v2):

- `POST /api/v2/jobs {"workflow": <API graph>}` returns `201` with a Job whose
  `id` is a canonical UUID.
- `Idempotency-Key` is reject-on-duplicate, with no replay. A duplicate is
  never re-executed.
- Status values are `queued`, `running`, `canceling`, `succeeded`, `failed`,
  `canceled` and `expired`.
- `GET /api/v2/jobs/{id}/workflow` returns `format: "api"`, the graph that was
  executed. `format: "save"` is treated as not attributable.
- Outputs carry `node_id`, `content_type` and an asset `id`.
- `/api/v2/assets/{id}/content` serves bytes on self-hosted deployments and
  returns a `302` to a signed `storage.googleapis.com` URL (roughly 6 h
  validity) on Cloud and serverless.

Overlapping names are never assumed to share semantics. For example, the
legacy `/api/jobs` routes in OSS 0.37 are not used.

## Capability discovery

- An explicit `api_family = "legacy" | "v2"` is trusted without probing when
  generating. `probe_provider` confirms only that family.
- `auto` probes read-only and bounded (`GET` only through a read-only budget,
  within 3 × request timeout).
- Detection requires positive, structured evidence. It is never inferred from
  a plain `200` or a generic `404`.
- If neither or both families match (for example, a Cloud endpoint that also
  answers legacy routes), `unsupported_api` is returned and the operator must
  set `api_family` explicitly. If both probes fail at the transport level, the
  result is `provider_unavailable`. A v2 `401`/`403` is `authentication_failed`.

The typed result is `ProviderProfile(family, version | None, Capabilities)`.
It carries only the capabilities that current behaviour branches on:

| Capability | legacy | v2 | Used for |
|---|---|---|---|
| `node_preflight` | yes | no (no documented catalogue) | `/object_info` node/checkpoint check before submission |
| `idempotent_submission` | no | yes | Recorded; each submission uses a fresh key and is never repeated |
| `durable_job_lookup` | no (in-memory history) | yes (until `expires_at`) | Diagnostics; reconcile truthfulness |
| `job_scoped_cancel` | no (present in 0.37 but not live-qualified) | yes (documented) | Recorded only; see Cancellation |

Version strings are informational and isolated in discovery. Behaviour
branches only on capabilities.

## Configuration schema (TOML)

```toml
[provider]
type = "comfyui"                 # only admitted provider type
endpoint = "http://127.0.0.1:8188"
api_family = "auto"              # auto | legacy | v2
deployment = "local"             # local (literal loopback) | remote (HTTPS)
binding = "comfyui-local"        # ProviderJobRef.binding
allowed_origins = []             # remote: must contain the endpoint origin
download_origins = []            # remote: signed-URL hosts for one redirect hop
[provider.auth]
type = "none"                    # none | bearer
secret_ref = "env:COMFY_API_KEY" # bearer only; env:NAME is the only form
[completion]
max_wait_seconds = 900           # optional poll_interval_seconds / request_timeout_seconds
[workflow]
path = "…/workflow.json"         # relative to the config file
sha256 = "…"; checkpoint = "…"; identity = "local-txt2img"; version = "1"
requires = []                    # optional capability names, e.g. ["node_preflight"]
```

Parsing is strict: unknown keys fail, and the error names the key but never
echoes its value. `GenerationConfig.digest` is the configuration revision
bound into governance. It covers every non-secret setting, including the
secret reference name, and never a secret value. The loopback profile
`local_config(...)` keeps the previous CLI flags working unchanged.

**Precedence.** The file is the only source of settings. The environment is
read only to resolve the explicitly named `env:NAME` reference, because
credentials must not be committed. There are no other environment overrides.

## Secret handling

- `resolve_secret("env:NAME")` is an adapter-local resolver, not a
  secret-management system; no repository-wide mechanism exists yet (ADR-010
  is accepted but unimplemented).
- The token lives only inside the transport and is sent as
  `Authorization: Bearer …` to the configured API origin only.
- The token never reaches signed-URL downloads, the request body, a URL,
  `TextToImageRequest`, a workflow file, a `repr`, an error message or the
  diagnostics.
- Tokens are restricted to visible ASCII of at most 4096 characters, which
  also blocks header injection.

## Local vs. remote trust

- **Local:** literal loopback IP with an explicit port. Redirects are
  rejected, proxies bypassed, and bearer auth is optional (for
  `comfy-api-proxy`).
- **Remote:**
  - HTTPS with the default TLS context (certificate and hostname
    verification on).
  - The canonical origin must be listed in `allowed_origins`.
  - Bearer auth by secret reference is mandatory.
  - No URL credentials, query or path; no proxies.
  - Responses are bounded.
  - Redirects are returned, never followed. The only exception is the v2
    asset hop: exactly one hop, only to an HTTPS origin in
    `download_origins`, without credentials, and a second redirect fails.
  - DNS resolution is the operating system's. Admitting an origin is an
    operator act, not SSRF protection against a malicious operator.

## Driver selection and extension

`discovery.DRIVERS` is a closed map: `{"legacy": …, "v2": …}`. Configuration
selects a key, never an import path. There is no `importlib`, `eval` or
`getattr` in config, discovery or service code, and tests enforce this.

**Adding a family** (for example a future ComfyUI core with native v2):

1. Write `drivers/<family>.py` implementing `ComfyDriver`, plus a read-only
   probe that returns structured evidence.
2. Add it to `DRIVERS`, `FAMILIES` and `ProviderProfile`.
3. Declare its `Capabilities` truthfully.
4. Map documented no-job rejections to `SubmissionRejected` only.
5. Add fake-transport tests.

No application, Core or engine change is needed.

## Workflow portability

Provider compatibility (the family plus its capabilities) is separate from
workflow compatibility:

- The workflow declares `required_nodes`, which are derived from the approved
  template.
- The checkpoint is an operator profile setting.
- Optional `requires` names capabilities the workflow needs. A missing one
  fails with `capability_missing` before anything is dispatched (effect
  NONE).
- On legacy, preflight checks nodes and the checkpoint.
- On v2, the provider validates the workflow at submission (`422`, no job
  created, effect NONE).
- Workflows are never modified to fit.

## Effects and errors

| Situation | legacy | v2 |
|---|---|---|
| Transport loss or malformed acknowledgement after dispatch | UNKNOWN | UNKNOWN (key stays claimed; never resubmitted) |
| Documented rejection (`401`, `402`, `403`, `422` workflow/asset, `429`) | n/a (unchanged legacy semantics) | **NONE** — upstream documents that no job was created |
| `5xx`, `422 idempotency_key_reuse` | — | UNKNOWN |
| Provider says failed / canceled | FAILED, UNKNOWN | FAILED, UNKNOWN (`reason=canceled`) |
| `expired` | — | not success: FAILED on generate, UNRESOLVED on reconcile (`reason=expired`) |

Errors map to existing `ErrorCategory` values plus a closed `reason` code:

| Reason | Category |
|---|---|
| `authentication_failed`, `forbidden` | AuthorizationDenied |
| `insufficient_credits`, `rate_limited`, `queue_full`, `provider_unavailable`, `upstream_error`, `output_unavailable`, `expired` | DependencyFailure |
| `invalid_workflow`, `missing_asset` | ValidationError |
| `unsupported_api`, `capability_missing` | VersionMismatch |

Raw provider messages are never propagated.

## Cancellation

LegoAI cancellation still stops only the local wait, and cessation stays
UNKNOWN on every driver. v2 documents a job-scoped cancel, but it only
requests cancellation: it takes effect at node boundaries, and serverless
bills GPU time consumed before the interrupt takes effect. Representing a
requested-but-unconfirmed cessation would need a new `Cessation` value, so
this slice records `job_scoped_cancel` and does not call it. Nothing ever
calls a provider-global interrupt.

## Application reuse

Two consumers use only `config`, `service`, `ports`, `values` and
`workflow`, which tests check by AST:

- `examples/generative-media-minimal/app.py`
- `examples/comfyui-text-to-image/generate.py` (plus `probe_provider.py`)

The same `consume()` function runs unchanged against legacy and v2 services
built from different configurations. Switching provider means changing
`--config`.

## Observability

`TextToImageService.describe()` returns:

- API family and version (or "not observable");
- endpoint origin and deployment;
- binding;
- workflow SHA-256;
- the supported capabilities.

Results add the job ID, effect, reconciliation status, reason and output
SHA-256. Credentials, prompts, image bytes and raw provider responses are
excluded. Core `Observation` fields are unchanged; provider fields stay in
package diagnostics, because adding them to Core would be a Core change.

## Validation

`uv run --locked python .\validate_comfyui_provider_compatibility.py` runs 16
phases:

1. environment, uv and Python;
2. dependency integrity;
3. mypy;
4. ruff lint;
5. ruff format check;
6. configuration;
7. discovery;
8. legacy regression;
9. v2;
10. remote transport;
11. reconciliation and effects;
12. reuse;
13. architecture;
14. wheel build and import;
15. affected existing tests;
16. `git diff --check`.

The launcher never runs `uv add`, `uv lock` or `uv sync`, never contacts any
provider, and strips `COMFY_API_KEY` from the test environment. The previous
`validate_comfyui_text_to_image.py` still works.

## Known limitations

- v2 and Cloud are qualified only against deterministic fakes built from the
  documentation. The API is in beta and may change; incompatibilities fail
  closed.
- v2 attribution assumes the executed `api` graph equals the submitted graph.
  A mismatch yields UNRESOLVED.
- The legacy family keeps its in-memory history. There is no durable job
  ledger, and reconciliation does not write back to Core.
- Signed-storage responses may be labelled `application/octet-stream`. PNG
  validation, not the label, decides acceptance.
- The Cloud model library is not preflighted. A missing checkpoint is
  rejected at submission.
- Out of scope: Cloud v1, WebSocket/SSE, uploads/assets input, cancellation
  wiring, installation, process launch and GPU concerns.
