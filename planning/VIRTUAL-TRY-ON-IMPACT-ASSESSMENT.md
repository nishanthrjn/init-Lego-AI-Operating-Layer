# Virtual Try-On — Impact Assessment and Design

Status: VTO-0 COMPLETE; ADR-020 ACCEPTED (2026-09-28); VTO-1 IMPLEMENTED —
LOCAL VALIDATION PENDING ([VTO-1](VIRTUAL-TRY-ON-VTO1.md)); local providers only. Current decisions are in §11a and ADR-020; earlier
sections are kept as the original analysis where they differ.
Builds on the [text-to-image slice](COMFYUI-TEXT-TO-IMAGE-VERTICAL-SLICE.md) and
[provider compatibility](COMFYUI-PROVIDER-COMPATIBILITY-SLICE.md). Evidence
comes from static, read-only inspection of the operator's ComfyUI 0.37.0
installation. Nothing was run, downloaded or modified.

## 1. What try-on adds

Text-to-image takes a short prompt and produces one image. Try-on takes **two
images** (a person and a garment) and produces one edited image of that
person. Three things are new:

1. **Personal image inputs.** A photo of an identifiable person enters
   LegoAI, is sent to a provider and may be stored there.
2. **Input transfer.** Images must reach the provider before submission,
   which adds external effects before the job exists.
3. **A second approved workflow shape.** It has image slots, a different
   model family and a different output geometry.

Everything else is reused unchanged:

- completion policy;
- single submission and no retry;
- reconciliation with zero POSTs;
- effect truth;
- driver selection and discovery;
- remote trust boundary;
- secret references;
- PNG validation;
- governance and Catalog composition.

## 2. Runtime evidence (ComfyUI 0.37.0, read-only)

| Fact | Consequence |
|---|---|
| Built-in `TextEncodeQwenImageEditPlus` accepts `image1..image3` plus a prompt; `ReferenceLatent`, `FluxKontextMultiReferenceLatentMethod`, `LoadImage`, `ImageScaleToTotalPixels`, `VAEEncode` are built in | Try-on is expressible with **built-in nodes only**, with no custom nodes, which keeps the current policy |
| Installed models: only `v1-5-pruned-emaonly.safetensors`; no diffusion model, text encoder or VAE for an edit model; no custom nodes | Live try-on needs an **operator-downloaded edit model**. LegoAI still never downloads models |
| Legacy `POST /upload/image` writes into the input directory; if the name exists it deduplicates by hash or renames `name (i).ext` unless `overwrite`; there is **no delete route** | An uploaded person photo stays on the shared runtime indefinitely |
| The upload route also accepts `type=temp`; `LoadImage` resolves `name [temp]`; temp is removed at server start **only when the asset manager is disabled** | `temp` narrows retention to the runtime's lifetime. It is not deletion, and it is conditional on runtime configuration |
| SD1.5 at 512² on this CPU took about 640 s | Qwen-Image-Edit and Flux Kontext are an order of magnitude larger. CPU runs will likely exceed the 1800 s ceiling, so live qualification realistically needs CUDA or Cloud |

The v2, Cloud and asset semantics that were open here are resolved in
§12. Cloud model-library availability is moot while Cloud personal-image
input is unsupported.

## 3. Proposed boundary

```
Application ── VirtualTryOnPort.try_on(TryOnRequest) -> GenerationResult
                                     reconcile(ProviderJobRef) -> ReconciliationResult (reused)
```

- **`TryOnRequest(person: ImageInput, garment: ImageInput, seed: int | None)`.**
  There is no free-form prompt. The approved workflow owns the edit
  instruction, which keeps untrusted text out of the graph. There are no
  hardware, model, mask or path fields.
- **`ImageInput`** is bounded **PNG-only** bytes (decided in §11a and
  ADR-020 §3; no media-type field).
  It is validated structurally (signature, dimensions, chunk/segment walk,
  ≤ 16 MiB, ≤ 2048² pixels) without decoding pixels, following the pattern
  in `png.py`. Its bytes never appear in a `repr` or in logs.
- **A separate port and capability** (`legoai.virtual-try-on` 1.0.0).
  Try-on is not a text-to-image variant, and widening `TextToImagePort`
  would change an application contract that is already qualified.
- **Results:** `GenerationResult` and `ReconciliationResult` are reused
  as-is. `GeneratedImage` needs **workflow-declared output geometry**
  instead of the fixed 512×512 default.

## 4. Input transfer and effects (the main design problem)

Try-on introduces effects that happen *before* the job exists:

| Step | External effect | Effect if it fails or is lost |
|---|---|---|
| Upload person | Personal image stored on the provider | UNKNOWN disclosure; job effect NONE |
| Upload garment | Garment image stored | UNKNOWN disclosure; job effect NONE |
| Submit | Job | Existing semantics per driver (legacy UNKNOWN, v2 documented rejections NONE) |

Proposed invariants:

- **At most two uploads and exactly one submission per call, none retried.**
  Tests assert the exact count of POSTs by route.
- **Reconciliation remains zero-POST** and never re-uploads.
- **Upload names are fresh random UUIDs** (`<uuid4>.png`) with
  `overwrite=false`. They never derive from user filenames, and the legacy
  hash-deduplication rename is detected and treated as a failure. This
  prevents collisions with, or inference about, other users' files.
- **Upload disclosure is its own reported fact.** It is not folded into job
  effect. Result diagnostics state "inputs transferred: yes/no/unknown".
  Whether this needs a new `values` field or can reuse `evidence` is a design
  choice for VTO-1.
- **Legacy uses `type=temp`** with the `[temp]` annotation in the graph. The
  document states plainly that deletion is impossible through the API and
  that retention lasts until the runtime restarts (conditional on the asset
  manager being disabled).
- **v2 uses the documented assets API.** Its retention and deletion semantics
  must be verified first. If it can't be established, try-on on v2 or Cloud
  stays **PROVIDER CAPABILITY NOT ESTABLISHED**.

A driver capability is added only where behaviour branches:
`input_upload` (legacy temp route or v2 assets), plus
`input_deletion` recorded truthfully (legacy: no).

## 5. Workflow approval generalization

`ApprovedWorkflow` currently equals one hard-coded template, with the prompt
in slot 6, the seed in slot 3 and output node 9.

| Option | Assessment |
|---|---|
| **A. A closed set of fixed templates** (`TemplateKind.TEXT_TO_IMAGE`, `TemplateKind.TRY_ON`), each with its own fixed slots and exact-shape validation | **Recommended.** It keeps "fixed shape, digest-pinned, no DSL". Attribution (`attribute`) extends per kind: recover the seed plus the input names and verify the rest |
| B. A declared slot manifest per workflow | Rejected: it drifts into a workflow DSL |
| C. Custom try-on nodes (for example IDM-VTON or CatVTON wrappers) | Rejected for now: needs custom-node installation, which current policy forbids, and third-party code |

Workflow requirements then declare the edit model's files (diffusion model,
text encoder, VAE) instead of one checkpoint. Legacy preflight checks the
nodes and each model list through `/object_info`. v2 relies on submission
validation (`422`, no job).

## 6. Model choice (maintainer decision)

| Candidate | Built-in nodes | Multi-image | Notes |
|---|---|---|---|
| Qwen-Image-Edit (Plus) | `TextEncodeQwenImageEditPlus` | up to 3 images | Designed for multi-reference edits; large |
| Flux.1 Kontext (dev) | `ReferenceLatent`, `FluxKontextMultiReferenceLatentMethod` | yes | Large; license terms must be checked by the operator |

LegoAI stays model-agnostic behind the template. The choice fixes one
approved template, its required files and its output geometry. Model licence
review and the download are operator acts.

## 7. Security and privacy

This is the first capability that processes images of identifiable people:

- **Authorization:** the governed invocation must represent an operator act
  covering that subject's image. The reference host issues the local grant as
  it does today. Multi-user or production use needs real consent and IAM,
  which is out of scope and must be stated.
- **Minimization:** no logging of input bytes, filenames, EXIF or prompts.
  Evidence is status and code only, as now.
- **Metadata:** input EXIF and PNG text chunks (GPS, device) should be
  stripped structurally before transfer. Accepting PNG only makes this a
  chunk filter. **Decided: PNG only, with structural stripping (§11a,
  ADR-020 §3).**
- **Third-party disclosure:** a remote or Cloud profile sends the person's
  photo to Comfy. The configuration must opt in explicitly (for example
  `allow_personal_images_remote = true`), and it fails closed otherwise.
- **Retention:** document it per family (legacy until restart at best; v2 to
  be determined). Output PNGs may embed the workflow, as now.
- **An ADR is required:** "Personal image inputs in generative media"
  (retention, deletion limits, remote opt-in, metadata stripping,
  authorization scope). Per `CLAUDE.md`, this is a significant decision, and
  `security/SECURITY.md` must be checked for applicable clauses first.
  **Done:** this is [ADR-020](../adrs/ADR-020.md), accepted 2026-09-28.

## 8. Feasibility gate

Deterministic implementation needs no model and no GPU; fakes suffice.
**Live qualification** needs one of:

- a local CUDA GPU with an operator-downloaded edit model; or
- Comfy Cloud with credits (currently exhausted), the edit model in its
  library, and the remote personal-image opt-in.

A CPU-only run is expected to exceed the 1800 s ceiling. The ceiling should
not be raised speculatively. If needed, it should be re-derived from a
measured run.

## 9. Proposed slice plan

| Slice | Content | Needs live runtime |
|---|---|---|
| VTO-0 | Maintainer decisions (§10), the ADR, and v2 asset-API verification | No |
| VTO-1 | `ImageInput` validation and metadata stripping; driver `upload` for legacy temp and v2 assets; the upload-effect invariants | No (fakes) |
| VTO-2 | `TemplateKind.TRY_ON` template, `VirtualTryOnPort`, service, capability offer, output geometry, attribution, a two-consumer reuse test | No (fakes) |
| VTO-3 | Live qualification on the chosen runtime, plus reconciliation of a real job | Yes (GPU or Cloud) |

## 10. Decisions required before VTO-1 (resolved; see §11a)

1. **Model family:** decided, Qwen-Image-Edit-2509 (§11a).
2. **Input formats:** decided, **PNG only** (§11a, ADR-020 §3).
3. **Remote personal images:** decided, local only (§11a, ADR-020 §8).
4. **Qualification runtime:** decided, local CUDA (§11a).
5. **ADR:** decided, ADR-020 Accepted 2026-09-28 (platform maintainer).

## 11. Non-goals

No custom nodes, model downloads, masks or segmentation pipelines, garment
catalogues, LoRA, ControlNet, batch processing, video, WebSocket, storage or
Artifact publication, or face or identity processing beyond passing the
image to the approved workflow.

## 11a. Maintainer decisions (2026-09-28)

1. **Model family:** Qwen-Image-Edit-2509 (Qwen Image Edit Plus). It stays
   behind the approved template; LegoAI never downloads models. Models must
   be **switchable without application changes** (ADR-020 §11, §13 below).
2. **Input format:** PNG only for v1. JPEG waits for a real consumer.
3. **Remote personal images:** local providers only. Remote stays fail-closed
   (ADR-020 §8).
4. **Qualification runtime:** local CUDA ComfyUI for VTO-3. VTO-1 and VTO-2
   stay deterministic and GPU-free. The 1800 s ceiling is unchanged.
5. **ADR owner:** the LegoAI platform maintainer, as Generative Media /
   Security boundary owner. [ADR-020](../adrs/ADR-020.md) is Accepted
   (2026-09-28).

## 12. VTO-0 provider asset findings (read-only; nothing uploaded or mutated)

Sources:

- the local ComfyUI 0.37.0 source: `server.py` upload handler,
  `folder_paths.py`, `nodes.py` `LoadImage`, `app/assets/api/routes.py`,
  `app/assets/services/asset_management.py`, `main.py`;
- docs.comfy.org: v2 *Upload an asset*, *Delete an asset record*,
  *Asset bytes*, and *Data Retention*.

**Legacy / self-hosted OSS (default flags)**

- *Upload:* `POST /upload/image` (multipart `image`, `type` = input/temp,
  `subfolder`, `overwrite`) returns `{"name","subfolder","type"}`. On a name
  clash the server either keeps the existing file (same hash) or renames it
  to `name (i).ext`. Any returned name other than the requested one is a
  failure.
- *Workflow reference:* the `LoadImage` input is the name string.
  `name [temp]` resolves to the temp directory, and `VALIDATE_INPUTS` checks
  that the annotated file exists.
- *Retention:* input files persist indefinitely. The temp directory is
  removed **only at server start, and only when the asset manager is
  disabled** (the default without `--enable-assets`).
- *Deletion:* no route deletes uploaded files. With `--enable-assets`,
  `DELETE /api/assets/{id}` removes a database record only; the source states
  that content with zero records stays servable. It is not deletion evidence.
- *Ownership:* none. The shared, unauthenticated runtime has no per-user
  ownership.
- *Reconciliation:* never needs uploads. The history graph carries the UUID
  input names, so attribution can verify the template shape.

**Comfy API v2 (Cloud, deployments, comfy-api-proxy)**

- *Upload:* `POST /api/v2/assets` (multipart `file`, `content_type`,
  `file_path`, optional `expected_hash`, `tags`, `expires_in` of 60–604 800 s,
  optional `Idempotency-Key`) returns an Asset with `id` (UUID), blake3
  `hash`, `expires_at` and `created_new`.
- *Retention:* `expires_in` overrides the default, but a dedup hit "extends
  its retention, never shortens it". When bytes are physically removed at
  expiry is not stated.
- *Deletion:* `DELETE /api/v2/assets/{id}` deletes the **record**; the blob
  stays while anything references it. Physical deletion is unspecified. A
  repeat returns `404`, indistinguishable from an unknown or foreign ID.
  `409` means the asset is in use.
- *Workflow reference:* how a submitted API graph references an asset is not
  documented on these pages (`missing_asset` exists as a 422 code).
- *Ownership:* implied per account by the 404 wording, not stated.
- *comfy-api-proxy:* how v2 assets map onto a local runtime's storage is
  undocumented.

**Comfy Cloud**

All of the v2 points apply. In addition, the Data Retention page states that
uploaded content is "retained for as long as necessary to operate, analyze,
and improve the service". Account-data deletion is by request to support.
Only Partner Node inputs and outputs have a stated 24 h deletion.

### Capability matrix

| Provider family | Upload | Temp / bounded retention | Byte deletion | Persistent asset reference | Workflow reference | Remote personal images |
|---|---|---|---|---|---|---|
| Legacy OSS (default) | VERIFIED | VERIFIED as retention reduction only (until restart, asset manager disabled) | UNSUPPORTED | UNSUPPORTED (name locator only) | VERIFIED (`name [temp]`) | n/a (local only) |
| Legacy OSS + `--enable-assets` | VERIFIED | UNSUPPORTED (temp cleanup disabled) | UNSUPPORTED (record-only delete) | NOT ESTABLISHED | NOT ESTABLISHED | n/a |
| v2 via comfy-api-proxy (local) | NOT ESTABLISHED | NOT ESTABLISHED | NOT ESTABLISHED | NOT ESTABLISHED | NOT ESTABLISHED | n/a |
| Comfy API v2 deployments | VERIFIED (documented) | NOT ESTABLISHED | NOT ESTABLISHED | VERIFIED (UUID + blake3) | NOT ESTABLISHED | UNSUPPORTED (ADR-020 §8) |
| Comfy Cloud | VERIFIED (documented) | NOT ESTABLISHED | NOT ESTABLISHED | VERIFIED (UUID + blake3) | NOT ESTABLISHED | **UNSUPPORTED FOR PERSONAL-IMAGE INPUT** |

**Capability model.** No change in VTO-0. VTO-1 adds exactly
`input_upload: bool` and `input_byte_deletion: bool` (False for every current
profile) to `Capabilities`, with its first consumer and tests. Adding them now
would be speculative. `persistent_asset_reference` is not needed for local
temp upload and stays unmodelled.

**Cloud gate.** Upload exists, but retention and deletion are not
established, and the published retention policy conflicts with
minimization. Cloud try-on is therefore **UNSUPPORTED FOR PERSONAL-IMAGE
INPUT**. Local capability is qualified independently and is not blocked by
this.

## 13. Qwen-Image-Edit-2509 template requirements (for VTO-2; not built)

Source: ComfyUI's bundled official template
`comfyui_workflow_templates_json/templates/image_qwen_image_edit_2509.json`
(UI format with a subgraph), inspected read-only. It is prior art only.
VTO-2 authors an original API-format graph and does not copy the file.

| Element | Requirement |
|---|---|
| Loaders | `UNETLoader` (`diffusion_models/`, reference file `qwen_image_edit_2509_fp8_e4m3fn.safetensors`, weight `default`); `CLIPLoader` (`text_encoders/qwen_2.5_vl_7b_fp8_scaled.safetensors`, type `qwen_image`); `VAELoader` (`vae/qwen_image_vae.safetensors`) |
| Model path | `ModelSamplingAuraFlow` shift 3, then `CFGNorm` strength 1, then `KSampler` |
| Person slot | `LoadImage` (`<uuid>.png [temp]`) → scaling (see Geometry) → `VAEEncode` for the latent, and `image1` of the positive encoder |
| Garment slot | `LoadImage` (`<uuid>.png [temp]`) → `image2` of the positive `TextEncodeQwenImageEditPlus` |
| Edit instruction | Fixed text owned by the approved template (not in the request). Wording is chosen and reviewed in VTO-2 |
| Negative | `TextEncodeQwenImageEditPlus` with an empty prompt. Its image wiring is to be mirrored from the reference template in VTO-2 |
| Sampler | `euler` / `simple`, denoise 1, **20 steps, CFG 4** (the reference template's non-Lightning path) |
| Seed slot | `KSampler.seed` (request seed, default 0), as in text-to-image |
| Output | `VAEDecode` → built-in `SaveImage` as the single output node, one PNG (the reference uses `SaveImageAdvanced`; `SaveImage` keeps output validation unchanged) |
| Geometry | `FluxKontextImageScale` picks a size from the input aspect ratio, so output size varies. VTO-2 decides between a fixed `ImageScale` to one declared portrait size (deterministic, recommended) and declaring the allowed set |
| Capabilities | `node_preflight` (legacy), `input_upload`, `deployment = local` |
| Excluded | The Lightning LoRA path (LoRA management is a non-goal) and `ComfySwitchNode`/primitive plumbing |

**Model switching.** The three model filenames are operator profile values,
like today's checkpoint, and preflight checks them against the `/object_info`
choices. Swapping for another compatible build, such as a different
precision, is a configuration change plus re-approval of the template digest.
Qwen-Image-Edit-2511 is documented as an enhanced 2509 sharing the text
encoder and VAE, but whether its graph is identical is **NOT ESTABLISHED**.
Treat it as a new approved template until verified. A different family (for
example Flux Kontext) would be a new closed template kind
(`TemplateKind.TEXT_TO_IMAGE`, `TemplateKind.TRY_ON`, …). None of these
change application code.

## 14. Input contract (final; implemented in VTO-1/VTO-2)

```
TryOnRequest(person: ImageInput, garment: ImageInput, seed: int | None)
ImageInput(content: bytes)   # PNG only; repr hides bytes
```

- **Excluded:** filename, path, URL, model, hardware, prompt, mask, provider,
  endpoint, consent flag.
- **Validation:** PNG signature, exact chunk walk with CRCs,
  8-bit RGB/RGBA non-interlaced, ≤ 16 MiB, bounded dimensions (for example
  64–2048 px per side), no trailing data.
- **Stripping:** before transfer, as ADR-020 §3 specifies.

`VirtualTryOnPort` is provider-neutral and composes through the existing
configuration, driver registry and governance path. Applications never see
the legacy/v2 or local/Cloud distinction, CUDA, Qwen file names or upload
routes.

## 15. Planned result extension (VTO-1)

`GenerationResult` gains `input_disclosure: EffectExtent = NONE`
(ADR-020 §4). As implemented in VTO-1, `ReconciliationResult` does not carry
it, because reconciliation never uploads. Text-to-image leaves it
`NONE`. Reconciliation always reports `NONE`, because it never uploads.

## 16. VTO-1 authorization gate

| Prerequisite | State |
|---|---|
| Personal-image ADR ready/accepted per repo governance | DONE (ADR-020 Accepted 2026-09-28) |
| PNG-only decision recorded | DONE (§11a) |
| Local legacy upload semantics verified | DONE (§12) |
| Disclosure/effect distinction settled | DONE (ADR-020 §4) |
| No-upload-retry rule settled | DONE (ADR-020 §5) |
| Metadata stripping policy settled | DONE (ADR-020 §3) |
| Local-only remote policy settled | DONE (ADR-020 §8) |

**Decision: VTO-1 is READY — LOCAL PROVIDERS ONLY.** Cloud is not required
and remains unsupported for personal-image input.

Next slice after acceptance, exactly: **VTO-1 — Bounded PNG Image Inputs +
Metadata Stripping + Local ComfyUI Upload.** It covers:

- `ImageInput` validation;
- PNG metadata stripping;
- bounded upload with the `input_disclosure` state;
- at most two uploads, with no upload retries;
- local legacy temp upload;
- deterministic fake-provider tests.
