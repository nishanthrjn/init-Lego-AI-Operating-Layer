# Virtual Try-On — Impact Assessment and Design

Status: ASSESSMENT ONLY — NO IMPLEMENTATION AUTHORIZED.
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

Not yet verified (required before VTO-1):

- Comfy API v2 asset upload: endpoint shape, retention, and whether assets
  can be deleted.
- Cloud model-library availability of the chosen edit model.

## 3. Proposed boundary

```
Application ── VirtualTryOnPort.try_on(TryOnRequest) -> GenerationResult
                                     reconcile(ProviderJobRef) -> ReconciliationResult (reused)
```

- **`TryOnRequest(person: ImageInput, garment: ImageInput, seed: int | None)`.**
  There is no free-form prompt. The approved workflow owns the edit
  instruction, which keeps untrusted text out of the graph. There are no
  hardware, model, mask or path fields.
- **`ImageInput`** is bounded bytes (PNG or JPEG) plus a declared media type.
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
  chunk filter. JPEG needs APPn segment removal. This is a maintainer
  decision.
- **Third-party disclosure:** a remote or Cloud profile sends the person's
  photo to Comfy. The configuration must opt in explicitly (for example
  `allow_personal_images_remote = true`), and it fails closed otherwise.
- **Retention:** document it per family (legacy until restart at best; v2 to
  be determined). Output PNGs may embed the workflow, as now.
- **An ADR is required:** "Personal image inputs in generative media"
  (retention, deletion limits, remote opt-in, metadata stripping,
  authorization scope). Per `CLAUDE.md`, this is a significant decision, and
  `security/SECURITY.md` must be checked for applicable clauses first.

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

## 10. Decisions required before VTO-1

1. **Model family:** Qwen-Image-Edit (Plus) or Flux Kontext. This fixes the
   template, the files and the geometry.
2. **Input formats:** PNG only (simplest metadata stripping) or PNG plus
   JPEG.
3. **Remote personal images:** allowed with an explicit opt-in, or local
   only for now.
4. **Qualification runtime:** local CUDA or Cloud (after credits).
5. **ADR ownership and approval** for personal-image handling.

## 11. Non-goals

No custom nodes, model downloads, masks or segmentation pipelines, garment
catalogues, LoRA, ControlNet, batch processing, video, WebSocket, storage or
Artifact publication, or face or identity processing beyond passing the
image to the approved workflow.
