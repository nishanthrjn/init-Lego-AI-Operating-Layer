# VTO-1 — Bounded PNG Image Inputs, Metadata Stripping, Local ComfyUI Upload

Status: IMPLEMENTED — LOCAL VALIDATION PENDING.
Authority: [ADR-020](../adrs/ADR-020.md) (Accepted 2026-09-28) and the
[Virtual Try-On assessment](VIRTUAL-TRY-ON-IMPACT-ASSESSMENT.md) §11a–§16.
No Core change and no application-contract change. `TextToImageRequest` is
still `(prompt, seed)`.

## Scope

This slice builds the reusable, privacy-sensitive **input transfer**
boundary. It does not include `VirtualTryOnPort`, the Qwen workflow,
generation submission, JPEG support, or Cloud or v2 image upload (all VTO-2
or later).

| Module | Adds |
|---|---|
| `png.py` | `strip_png`, `MAX_INPUT_BYTES`, `MIN_INPUT_SIDE`, `MAX_INPUT_SIDE` |
| `values.py` | `ImageInput`, `UploadedImageRef`, `InputTransfer`, `InputTransferCancelled`; `GenerationResult.input_disclosure`; reason `remote_personal_images_forbidden` |
| `http.py` | `NotSent`; request bodies up to one input image plus framing; caller-supplied `Content-Type` |
| `drivers/base.py` | `Capabilities.input_upload` / `input_byte_deletion`; `ComfyDriver.upload`; `DeadlineBeforeSend`, `ProviderRenamed` |
| `drivers/legacy.py` | `LegacyDriver.upload` (temp upload) |
| `drivers/v2.py` | Declares no upload (`input_upload=False`) |
| `transfer.py` | `ImageTransfer` (ordering, local-only, disclosure) |
| `service.py` | `open_image_transfer(config)` |

The names are not specific to try-on. Any future generative-media capability
that needs local, privacy-sensitive image inputs can reuse them.

## PNG contract (`ImageInput(content: bytes)`)

- **Type:** `bytes` only. Mutable or aliasable buffers (`bytearray`,
  `memoryview`) are rejected. There are no filename, path, URL, provider,
  model, prompt, mask, consent or hardware fields.
- **Limits:** at most 16 MiB; each side 64–2048 px inclusive; 8-bit RGB (2)
  or RGBA (6) only; compression, filter and interlace all 0.
- **Rejected:**
  - a wrong signature;
  - truncation, a missing IEND, or bytes after IEND;
  - a bad CRC or a non-alphabetic chunk type;
  - an unknown critical chunk;
  - IHDR that isn't first or is duplicated;
  - PLTE after IDAT, duplicated, or of bad length;
  - non-consecutive IDAT;
  - IEND without IDAT, or a non-empty IEND;
  - palette, greyscale, 16-bit, interlaced or out-of-bounds input;
  - `tRNS`, because dropping it would change how pixels are read.

  Palette input is not supported in v1, so PLTE is never required.
- **Stored form:** construction replaces `content` with the stripped PNG, and
  the original bytes are not retained. Equality and hashing therefore ignore
  metadata. `repr` shows only width and height.
- **Digest:** `sha256` covers the stripped bytes, for local diagnostics only.
  It is never used as a provider identifier.

## Stripping algorithm (ADR-020 §3)

1. Walk the chunks once with bounded counts (at most 4096 chunks), verifying
   every CRC before a chunk is accepted.
2. Keep, byte for byte and in order: the signature, IHDR, every IDAT, and
   IEND.
3. Drop every ancillary chunk, including `tEXt`, `zTXt`, `iTXt`, `eXIf`,
   `tIME`, `iCCP`, `sRGB`, `gAMA`, `cHRM`, `pHYs` and private ones. Also drop
   the optional truecolour PLTE.
4. Pixels are never decompressed, decoded or re-encoded. The IDAT bytes are
   identical, so pixel data is unchanged. Colour-management chunks are
   removed deliberately.
5. Any deviation rejects the image. There is no unstripped fallback. The
   result reparses to itself and passes the existing output validator.

## Input disclosure (ADR-020 §4)

`InputTransfer.disclosure` and `GenerationResult.input_disclosure` reuse the
canonical `EffectExtent` as a separately named effect:

| Value | Meaning |
|---|---|
| NONE | No byte of any input was sent |
| PARTIAL | Some inputs acknowledged; the rest were provably not sent |
| COMPLETED | Every input acknowledged (a provider rename still counts as stored) |
| UNKNOWN | An upload may have delivered bytes without an acknowledgement |

"Provably not sent" means one of:

- `NotSent`: the connection was never established, or the transport was
  refused structurally;
- `DeadlineBeforeSend`: the operation deadline expired before the attempt.

Everything after a request may have started counts as UNKNOWN: timeouts,
resets, non-200 responses, malformed or oversized acknowledgements, and
redirects. Job effect and disclosure are independent; for example,
`effect = NONE` with `input_disclosure = UNKNOWN` is valid. Text-to-image
always reports `NONE`. Cancellation during an upload raises
`InputTransferCancelled` carrying UNKNOWN disclosure and the refs
acknowledged so far.

## Upload behaviour

- **Order and attempts:** up to two inputs are uploaded in the caller's
  order, person first and then garment for try-on (VTO-2). Each input is
  attempted **once**. The first failure ends the transfer, and nothing is
  retried.
- **Request:** a legacy `POST /upload/image` multipart request with parts
  `image` (filename `<uuid4>.png`, `image/png`, stripped bytes),
  `type=temp` and `overwrite=false`. There is no subfolder. The boundary is
  `legoai-<uuid4 hex>`, and it is refused before sending if it occurs in the
  image.
- **Acknowledgement:** it must equal
  `{"name": <requested>, "subfolder": "", "type": "temp"}` and be at most
  64 KiB. A well-formed acknowledgement with a different name
  (dedup or collision rename) raises `ProviderRenamed`, which counts as
  stored but fails. Anything else is malformed and counts as UNKNOWN.
- **Result:** `UploadedImageRef(provider_name, storage="temp")` is the only
  locator. It is not an Artifact, not durable storage, not ownership and not
  a deletion guarantee. No ComfyUI path is ever exposed.
- **Transport:** the existing `LocalHTTP`, with a literal loopback origin,
  redirects rejected, proxies bypassed, bounded body, response and timeout,
  and no second HTTP client.

## Local-only restriction (ADR-020 §8)

- `open_image_transfer` derives `local` from `deployment = "local"`.
- Remote and Cloud configurations are refused before any I/O:
  POLICY_VIOLATION with reason `remote_personal_images_forbidden`,
  disclosure NONE, zero requests.
- As defence in depth, `LegacyDriver.upload` refuses a `RemoteHTTPS`
  transport even if it is wired by hand.
- A local driver without `input_upload` (v2 via proxy) fails with
  `capability_missing`.
- `allow_personal_images_remote` stays reserved. Configuration rejects it as
  an unknown key.

## Retention and deletion

`input_byte_deletion = False` for every profile. LegoAI never calls a
record-delete API, never touches ComfyUI directories, and never claims
deletion. `type=temp` shortens retention to the runtime's lifetime, and only
when ComfyUI's asset manager is disabled. It is provider behaviour, not
guaranteed deletion.

## Capabilities

| Profile | `input_upload` | `input_byte_deletion` |
|---|---|---|
| Legacy OSS | True | False |
| Comfy API v2 / Cloud | False (upload documented; retention and deletion not established) | False |

No other storage capability was added.

## Deterministic tests

`uv run python .\validate_virtual_try_on_vto1.py` runs these phases:

1. environment, uv and Python;
2. dependency pins;
3. mypy;
4. ruff lint;
5. ruff format check;
6. PNG contract;
7. stripping;
8. disclosure effect;
9. legacy upload transport, including a real `LocalHTTP` against an
   in-process loopback server;
10. local/remote policy;
11. reconciliation (still zero POST, even after uploads);
12. text-to-image compatibility;
13. architecture (no logging or printing on image-byte paths; no provider
    types in contracts);
14. wheel build and import;
15. the remaining generative-media tests;
16. `git diff --check`.

All images are generated synthetically in the tests. No real photos, no live
ComfyUI, no Cloud and no GPU are involved.

## Known limitations

- **Temp retention:** retention on the local runtime is the operator's
  responsibility (ADR-020 §7).
- **Colour management:** rendering may differ slightly after dropping it.
- **Formats:** palette, greyscale, 16-bit and transparent PNGs are rejected
  in v1.
- **Result fields:** `ReconciliationResult` does not carry
  `input_disclosure`, because reconciliation never uploads. The assessment's
  §15 plan to add it to both results was narrowed to the one result that
  needs it.

## VTO-2 handoff

- Compose `TryOnRequest(person, garment, seed)` → `ImageTransfer.upload((person,
  garment))`.
- Bind `UploadedImageRef.provider_name` as `"<name> [temp]"` into the
  approved `TemplateKind.TRY_ON` graph (§13 of the assessment).
- Submit exactly once through the existing engine.
- Report `GenerationResult(input_disclosure=transfer.disclosure, …)`.
- A failed transfer never submits.
