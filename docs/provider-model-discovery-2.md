# PROVIDER-MODEL-DISCOVERY-2

Status: **LOCALLY QUALIFIED** (2026-10-10), from maintainer-run offline evidence.
Qualifying commit: `c7353ccf180a54effbf2e80a048e8ae4b8197dc8` on branch
`br-LegoAIPyLLMComfyCR-ForgeAI-KISSKIColabKagHF`. `git status --short` was empty
before closeout edits; the implementation was committed and the tracked tree clean.
No tests or static checks were run by the agent. No provider API call occurred.

The maintainer ran:

```powershell
uv run --locked --offline --no-sync python .\validate_provider_model_discovery_2.py
```

The final supplied transcript passed every phase:

- Discovery v2, HF synthetic flow, KISSKI POST and REMOTE/security: **723 passed**
  in 99.11s, including GET/POST_EMPTY wire shape, method/custody binding, parser
  bounds, Secret/S1/T2/custody and OpenAI-compatible REMOTE regressions.
- Architecture/package tests: **364 passed** in 28.54s.
- ForgeAI REMOTE profile: **69 passed, 2 deselected** in 19.43s. The deselected
  cases acquire real Docker dependencies; synthetic TLS coverage ran.
- Total: **1,156 passed**, 2 deselected; mypy passed on **16 source files**,
  Ruff lint passed, **16 files already formatted**, and `git diff --check` passed.

The transcript ended with `PROVIDER-MODEL-DISCOVERY-2 OFFLINE CHECKS PASSED;
LIVE GATE STILL DISABLED; no HF API calls, no named-provider qualification`.
That gate state records the qualifying commit, before this readiness closeout.
Post-edit checks are provided in the [HF closeout instructions](hf-inference-compatibility.md)
and remain operator-run; these new edits are not included in the historical counts.

Qualification is limited to synthetic local TLS, closed GET/POST_EMPTY discovery,
bounded optional backend observations, no routing, no retry and no fallback.
It establishes neither HF nor KISSKI compatibility, arbitrary provider discovery,
provider availability, model quality, ForgeAI live quality, HF repository disclosure
safety, free-GPU qualification nor production remote inference.

## Contract and ADR review

ADR-023 retains SRCP-1 ordering, custody, recipient binding and containment.
ADR-024 section 22 explicitly selects the documented provider method and treats
the result as an observation, not policy or routing. Neither makes POST-only or
IDs-only a normative invariant. No ADR amendment is required for this bounded
extension. ModelPort, Model errors, S1 and disclosure classes are unchanged.

Historical **v1** qualification remains POST_EMPTY with an ID-only observation.
**v2** adds GET and opt-in bounded selection metadata. Existing callers default
to POST_EMPTY and the ID-only parser, including the unchanged KISSKI harness.

## Exact request identity

`ProviderDiscoveryMethod` contains only GET and POST_EMPTY. The admission and
trusted DiscoveryEndpoint carry the enum, never arbitrary method strings.
Mismatch refuses before an attempt or connection. ProviderControlAttempt carries
the same value; the exchange compares it with the transport target before DNS,
claim or credential handoff. Both discovery shapes require an empty body.
Model attempts cannot use a discovery target; GET cannot target chat/embeddings.

GET sends exactly Host, Accept, Authorization and Connection: close. No body,
Content-Type or Content-Length is sent. Existing POST encoding is preserved,
including Content-Length: 0 for POST_EMPTY. No arbitrary headers, URLs, methods,
redirects, proxies, compression, cookies, pooling, retry or fallback are added.
The existing bounded response framing, TLS and timeout/currentness semantics
remain. A 405 stops; the harness never tries the other method.

New custody records have kind `provider-control-v2` and an explicit method.
Historical `provider-control` records are decoded as POST_EMPTY because that was
their sole qualified meaning. Legacy records with a method field, or new records
without it, are rejected. Opening historical custody does not rewrite records,
restore dispatch authority or resend. Model-attempt records are unchanged.

## Optional selection observation

ModelDiscovery retains `models: tuple[ModelId, ...]` and adds `catalog`, a tuple
of immutable DiscoveredModel values. The latter holds a model ID, input/output
modality tuples and optional DiscoveredProvider entries (ID, status, input/output
USD-per-million-token prices). Absent facts stay absent. Status strings are
observations; only a consuming profile decides which status is eligible.

The opt-in protocol profile reads `architecture.input_modalities`,
`architecture.output_modalities`, `providers[].provider`, `status` and
`pricing.input`/`pricing.output`. Unknown fields are discarded. This vocabulary
is defined by its semantics, with no named-provider branch or identifiers in
Core. The motivating official [catalog contract](https://huggingface.co/docs/inference-providers/hub-api#list-openai-compatible-models)
documents backend status, modalities and USD-per-million-token prices.

Bounds: 4 MiB response, 1,024 models, 256-character model IDs, 32 providers/model,
128-character provider IDs, eight modalities per direction, 32-character
modality/status strings, finite numeric prices from zero through 1,000,000.
Selection identifiers are unpadded printable ASCII without whitespace or
wildcards. Duplicate JSON keys, model IDs, backend IDs or modalities, malformed
present fields, oversized values, non-finite numbers and bool/string prices
are rejected. Missing prices/status/modalities do not make the parser fail but
cannot satisfy a harness policy that requires them. ID-only v1 parsing still
ignores metadata. No raw catalog or selection metadata is persisted in custody.

## HF consumer and qualification

The [HF harness](../scripts/hf_inference_compatibility_probe.py) opts into GET
and the richer profile. Selection and coding policy are entirely in that script;
discovery changes no Catalog, binding, grant, disclosure admission or route.
See [HF operator instructions](hf-inference-compatibility.md).

The new regression suite covers both request shapes, method substitution at
admission and exchange, versioned/legacy custody, 405 without fallback, empty
bodies, rejected method strings, parser bounds and malformed metadata. The HF
suite covers local TLS discovery/chat, selection membership, missing/unsupported
facts, separate Secret purposes, approval decline, live gate and safe coarse
diagnostics. Existing KISSKI, Secret/T2, REMOTE and ForgeAI regressions remain
part of the operator validator. The maintainer results above qualify that scope.

From the repository root, using existing locked local environments:

```powershell
uv run --locked --offline --no-sync python .\validate_provider_model_discovery_2.py
```

The validator runs the new and existing suites, architecture/package checks,
mypy, Ruff lint/format and whitespace checks. It uses synthetic local TLS only,
does not acquire dependencies or invoke a live provider, and excludes the real
Docker dependency-acquisition cases. Missing environments can be prepared with
`uv sync --locked --offline` at the root and with
`uv sync --project .\examples\forgeai --locked --offline`.
The validator remains offline even after the readiness closeout enables the
harness gate. It invokes only `--plan` and synthetic tests; qualification does not
itself execute or authorize a probe. The success marker now states that live
execution requires separate authorization.
