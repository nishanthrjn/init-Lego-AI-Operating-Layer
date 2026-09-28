# VTO-2 — Provider-Neutral Virtual Try-On Capability

Status: IMPLEMENTED — DETERMINISTIC VALIDATION PENDING.
Authority: [ADR-020](../adrs/ADR-020.md), the
[assessment](VIRTUAL-TRY-ON-IMPACT-ASSESSMENT.md) §11a–§16 and
[VTO-1](VIRTUAL-TRY-ON-VTO1.md). No Core change. `TextToImagePort` and
`TextToImageRequest` are unchanged. No live ComfyUI, CUDA, model or real
image was used. Only static checks ran.

## Capability contract

```
VirtualTryOnPort.try_on(TryOnRequest) -> GenerationResult
VirtualTryOnPort.reconcile(ProviderJobRef) -> ReconciliationResult
TryOnRequest(person: ImageInput, garment: ImageInput, seed: int | None)
```

- **Excluded from the request:** prompt, workflow, model, checkpoint,
  endpoint, provider, device, geometry, mask, filename, URL and consent flag.
- **Capability offer:** `legoai.virtual-try-on` 1.0.0 (`TRY_ON_OFFER`),
  admitted through the existing Plugin admission, Catalog, configuration
  revision, governance, and claim/settle path.
- **Governed composition:** `invoke_try_on`, sharing one governed
  implementation (`_invoke`) with text-to-image. The try-on path is marked
  `may_disclose`, so a governance deadline or fallback never reports
  disclosure as NONE once the call has started.
- **Application entry point:** `service.open_virtual_try_on(config)` returns
  a `TryOnService` that implements the port.

## Execution order (fail before disclosure)

| Step | Where | On failure |
|---|---|---|
| 1. Request type | adapter | TypeError (programming error) |
| 2. Provider and config resolution | `open_virtual_try_on` | configuration error |
| 3. Governance: grant, dispatch, claim | `prepare_local` + `invoke_try_on` | CONFLICT, nothing sent |
| 4. Local deployment | adapter | POLICY_VIOLATION `remote_personal_images_forbidden`; zero requests |
| 5. `input_upload` capability | adapter | `capability_missing`; zero requests |
| 6. Node and model preflight (`/object_info`: 12 node classes, plus `unet_name`, `clip_name`, `vae_name` lists) | legacy driver | effect NONE, disclosure NONE, zero uploads |
| 7. Person upload, then garment upload, once each | VTO-1 `ImageTransfer` (shared deadline) | effect NONE; disclosure NONE, PARTIAL or UNKNOWN; **zero `/prompt`** |
| 8. Patch the approved TRY_ON template | `ApprovedTryOnWorkflow.graph` | effect NONE, disclosure COMPLETED, zero `/prompt` |
| 9. Submit exactly once | shared engine | UNKNOWN from dispatch onwards; documented rejection gives NONE |
| 10. Bounded wait, then one validated 768×1024 PNG | shared engine | DEADLINE/FAILED with the job kept; retrieval failure keeps COMPLETED |

Nothing is ever retried. `GenerationResult.input_disclosure` carries the
transfer outcome independently of `effect`. Some valid combinations:

| Situation | `input_disclosure` | `effect` |
|---|---|---|
| Success | COMPLETED | COMPLETED |
| Submission acknowledgement lost after both uploads | COMPLETED | UNKNOWN |
| Second upload uncertain, nothing submitted | UNKNOWN | NONE |
| Cancelled during an upload | UNKNOWN | NONE |

## Engine refactor (shared, not duplicated)

`ComfyEngine[W: ApprovedTemplate]` owns everything from submission onwards:

- the deadline;
- the single submission;
- polling;
- effect truth;
- output validation against the template's geometry;
- reconciliation through `seed_of`.

Each capability supplies only a `prepare` step returning `(graph, seed)`.
Pre-submission refusals return a complete result (`Refused`). Text-to-image
now runs through the same `_execute`, with identical results and
`input_disclosure` always NONE.

Legacy preflight was generalized from one checkpoint to each template's
declared `required_models`. Drivers stay API-family specific: there is no
Qwen driver, and the template layer owns all Qwen semantics.

## Approved template (`TemplateKind.TRY_ON`, `qwen-image-edit-2509`)

The graph is an original API-format graph using built-in nodes only. Its
node inputs were checked against the ComfyUI 0.37 sources, and the bundled
2509 template was used as evidence, not copied.

| Node | Class | Fixed values |
|---|---|---|
| 1 | UNETLoader | `unet_name` = configured diffusion model, `weight_dtype` default |
| 2 | CLIPLoader | `clip_name` = configured text encoder, `type` `qwen_image` |
| 3 | VAELoader | `vae_name` = configured VAE |
| 4 | ModelSamplingAuraFlow | shift 3.0 |
| 5 | CFGNorm | strength 1.0 |
| 6 | LoadImage | **person slot** `"<uuid4>.png [temp]"` |
| 7 | LoadImage | **garment slot** `"<uuid4>.png [temp]"` |
| 8 | ImageScale | lanczos, 768×1024, `crop="center"` |
| 9 | SaveImage | single output node, prefix `legoai_tryon` |
| 10 | VAEEncode | scaled person → latent |
| 11 | TextEncodeQwenImageEditPlus | fixed instruction; `image1` = scaled person, `image2` = garment |
| 12 | TextEncodeQwenImageEditPlus | empty prompt; the same image and VAE references (mirrors the reference template) |
| 13 | KSampler | **seed slot**; 20 steps, CFG 4.0, euler/simple, denoise 1.0 |
| 14 | VAEDecode | — |

Fixed instruction, part of the approved bytes; any change means a new
digest and review:

> Dress the person in the garment shown in the second reference image.
> Preserve the person's identity, pose and scene while replacing only the
> clothing as naturally as possible.

- **Mutable slots:** exactly 6.image, 7.image and 13.seed. Tests assert that
  nothing else changes.
- **Approval:** approved bytes must equal `tryon_template(models)` exactly,
  with serialized comparison, and match the pinned SHA-256.
- **Excluded:** the Lightning LoRA, switch or primitive nodes, and custom
  nodes.

## Fixed geometry decision: 768×1024 portrait

- **Encoder behaviour:** the Qwen encoder rescales reference images
  internally in a deterministic way (about 384² for vision, about 1 MP
  multiples of 8 for reference latents).
- **What sets the output:** output size is determined solely by the latent
  from `VAEEncode` of the scaled person image.
- **Alignment:** 768 and 1024 are multiples of 16 (VAE ×8, patch ×2).
- **Size:** about 0.79 MP, close to the model's roughly 1 MP working area,
  and within the package's 1024 px output ceiling.
- **Scaling policy: crops.** `ImageScale` with `crop="center"` centre-crops
  to 3:4, then resizes. That preserves aspect ratio with no distortion or
  padding, deterministically (verified in `comfy/utils.common_upscale`).
  Portrait people photos lose little.
- **Validation:** output is validated at exactly 768×1024, and any other
  size is a VALIDATION_ERROR with effect COMPLETED. Text-to-image keeps
  512×512.

No OUTPUT GEOMETRY BLOCKER applies.

## Model configuration and switching

```toml
[try_on]
template = "qwen-image-edit-2509"          # closed set
diffusion_model = "qwen_image_edit_2509_fp8_e4m3fn.safetensors"
text_encoder = "qwen_2.5_vl_7b_fp8_scaled.safetensors"
vae = "qwen_image_vae.safetensors"
path = "…/tryon_workflow.json"             # written by prepare_template.py
sha256 = "…"                               # after operator review
```

- The `[provider]` and `[completion]` tables are the same as for
  text-to-image. Parsing is strict, so a key such as `prompt` or `width` is
  rejected.
- The configuration digest binds the template, the model files and the
  workflow digest.
- Switching to a compatible precision or build means editing the
  filenames, running `prepare_template.py`, reviewing, and updating the
  digest. The application does not change.
- A different model family would be a new closed template kind.

## Attribution and reconciliation

Reconciliation proves that the recorded graph equals the TRY_ON template
re-bound with its own recorded values. It checks:

- the configured models;
- the instruction;
- the sampler;
- the geometry;
- the output node;
- generated `"<uuid4>.png [temp]"` input locators (distinct);
- an integer seed.

It recovers the seed and both `UploadedImageRef`s.

- **Never:** reconciliation makes zero upload POSTs and zero `/prompt`
  POSTs, and never re-uploads.
- **Kept semantics:** pending, failed and missing jobs keep the existing
  meanings. Repeated reconciliation returns the same digest.
- **Kind isolation:** a text-to-image adapter never attributes a try-on job,
  and the reverse also holds.
- **Limitation:** without a durable ledger, reconciliation verifies that
  locators are well-formed generated names but cannot compare them against
  the names uploaded by the original call.

## N-application reuse

- **Consumers:** `examples/virtual-try-on-minimal/minimal_tryon.py` and
  `examples/virtual-try-on/try_on_cli.py` import only `config`, `service`,
  `ports` and `values`. An AST test forbids driver, template, node,
  upload-route and CUDA names.
- **Runtime proof:** both run against a governed service built from
  configuration.
- **Operator tooling:** `prepare_template.py` writes the template for
  review. It is outside the consumer rule.

## Validation

`uv run python .\validate_virtual_try_on_vto2.py` runs 19 phases:

1. environment;
2. dependency pins;
3. mypy;
4. ruff lint;
5. ruff format check;
6. contract;
7. preflight;
8. workflow;
9. composition;
10. effects;
11. geometry;
12. reconciliation;
13. reuse;
14. architecture;
15. wheel build and import;
16. VTO-1 regressions;
17. provider-compatibility regressions;
18. affected generative-media tests;
19. `git diff --check`.

## Known limitations

- **Live behaviour:** not observed yet. Output quality, the instruction's
  effectiveness, VRAM and timing are unqualified until VTO-3.
- **Cropping:** centre-crop can cut the edges of non-3:4 person photos.
- **Preflight coverage:** preflight depends on `node_preflight`, which every
  current upload-capable driver has.
- **Local only:** Cloud and remote try-on stay unsupported (ADR-020 §8).

## VTO-3 prerequisites (live qualification; not performed)

- A local CUDA ComfyUI with the operator-installed Qwen-Image-Edit-2509
  components listed above.
- A template generated with `prepare_template.py`, reviewed, and pinned by
  its digest in the config.
- Two non-sensitive test PNGs chosen by the maintainer.
- One live generation (`try_on_cli.py`), confirming:
  - exactly two uploads and one submission;
  - an actual output of 768×1024;
  - `input_disclosure` COMPLETED.
- One reconciliation of the same job (`--reconcile`), with zero uploads and
  zero submissions.
- No CPU run is required.
