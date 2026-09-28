# VTO-3 — Live Local CUDA Qualification

Status: LIVE QUALIFICATION PREPARED — OPERATOR RUN REQUIRED.
Qualifies the VTO-2 `VirtualTryOnPort` against a real local CUDA ComfyUI.
It adds no new architecture, only operator tooling.
Authority: [ADR-020](../adrs/ADR-020.md), [VTO-2](VIRTUAL-TRY-ON-VTO2.md).

## Tooling added (offline-tested in `validate_virtual_try_on_vto2.py` phase 13b)

| Tool | Change |
|---|---|
| `service.preflight_virtual_try_on(config)` | Read-only readiness report. All I/O goes through read-only budgets, so a POST is structurally impossible. It checks, in order: local-only policy, approved template (digest and exact shape), provider reachability and API family, upload capability, and every node plus the three model files. It stops at the first failure. |
| `service.WriteCounter` | Wraps the transport factory and counts every write *attempt* by kind (upload vs submission), never content. |
| `try_on_cli.py` | Exactly one mode: `--preflight`, `--live` (generation, explicit opt-in) or `--reconcile JOB_ID`. It prints counted uploads and submissions, elapsed seconds, and `--expect-sha256` for the same-job digest check. `--live` runs the read-only preflight first and stops before any upload if it fails. |
| `prepare_template.py --config` | Writes the exact approved graph from the configured model files to `try_on.path`, never overwrites, and prints kind, geometry, models and SHA-256. |
| Legacy preflight messages | Name the missing node class or `Node.input` (public identifiers only). |
| `configs/tryon-local.toml` | `max_wait_seconds = 1800` (the existing maximum, not raised); `path = comfyui-proof/tryon-workflow.json`. |

## Prerequisites (operator)

1. **Local ComfyUI on a CUDA GPU,** started by you on `http://127.0.0.1:8188`.
   LegoAI never launches it or selects a device.
2. **Qwen-Image-Edit-2509 components**, installed by you. LegoAI never
   downloads them. Under `ComfyUI\models\`:

   | Folder | Default filename |
   |---|---|
   | `diffusion_models\` | `qwen_image_edit_2509_fp8_e4m3fn.safetensors` |
   | `text_encoders\` | `qwen_2.5_vl_7b_fp8_scaled.safetensors` |
   | `vae\` | `qwen_image_vae.safetensors` |

   Different compatible filenames go in `[try_on]` of
   `examples/virtual-try-on/configs/tryon-local.toml`, followed by a new
   template and digest. No code changes.
3. **Two non-sensitive test PNGs** (a person and a garment): 8-bit RGB or
   RGBA, 64–2048 px per side, 16 MiB or less. Keep them **outside the
   repository**. `comfyui-proof/` is tracked by git, so personal inputs and
   outputs must never go there.

## Commands (PowerShell, repository root)

```powershell
# 0. Deterministic regression first (no provider contact)
uv run python .\validate_virtual_try_on_vto2.py

# Private working folder outside the repository
$vto = "$env:USERPROFILE\legoai-vto3"; New-Item -ItemType Directory -Force $vto | Out-Null
#   copy your two test PNGs to "$vto\person.png" and "$vto\garment.png"

# 1. Prepare the approved template (no network; never overwrites)
uv run python examples/virtual-try-on/prepare_template.py --config examples/virtual-try-on/configs/tryon-local.toml
#   review comfyui-proof\tryon-workflow.json, then set try_on.sha256 in the config to the printed SHA-256

# 2. Read-only preflight (uploads 0, submissions 0)
uv run python examples/virtual-try-on/try_on_cli.py --config examples/virtual-try-on/configs/tryon-local.toml --preflight

# 3. One live generation (explicit --live; 2 uploads, 1 submission)
uv run python examples/virtual-try-on/try_on_cli.py --config examples/virtual-try-on/configs/tryon-local.toml --live --person "$vto\person.png" --garment "$vto\garment.png" --seed 42 --output "$vto\tryon-result.png"

# 4. Reconcile the SAME job (no uploads, no submission)
uv run python examples/virtual-try-on/try_on_cli.py --config examples/virtual-try-on/configs/tryon-local.toml --reconcile JOB_ID --expect-sha256 GENERATION_SHA256 --output "$vto\tryon-reconciled.png"
```

## Hard pass criteria

**Generation (step 3):**

- `preflight: PASS`;
- `uploads performed: 2`;
- `submissions attempted: 1`;
- `input_disclosure: completed`;
- `outcome: success`;
- `effect: completed`;
- `width: 768 height: 1024`;
- one PNG written, with PNG validation implied by success.

**Reconciliation (step 4):**

- `uploads performed: 0`;
- `submission performed: NO`;
- `status: COMPLETED`;
- `effect: completed`;
- `width: 768 height: 1024`;
- `digest matches generation: YES`.

Also record the elapsed seconds. There is no retry anywhere.

## Timeout behaviour

The wait is bounded at 1800 s. If a run exceeds it, the result is DEADLINE
with effect UNKNOWN and the job ID kept. In that case:

- record the evidence;
- do not rerun;
- reconcile later with `--reconcile`;
- stop qualification.

Only then would a separately justified completion-policy change be
considered.

## Failure semantics (unchanged, and must be observed as such)

| Failure | Disclosure / effect |
|---|---|
| Preflight fails | Disclosure none, 0 uploads, 0 submissions |
| First upload fails | No second upload, 0 submissions |
| Second upload fails | 0 submissions |
| Submission acknowledgement uncertain | Disclosure completed, effect unknown, no retry |
| Retrieval fails after completion | Effect completed, error reported separately |

A ComfyUI out-of-memory error surfaces as a provider failure category. It
is measured evidence for that machine only, not a universal VRAM claim.

## Privacy constraints

- **Local only:** no Cloud (ADR-020 §8).
- **Inputs:** stripped of metadata before upload, uploaded as `temp` under
  random names, and never deleted by LegoAI.
- **ComfyUI retention:** ComfyUI keeps inputs and outputs until its own
  temp and output cleanup runs.
- **Output handling:** the output shows a person. Keep it outside the
  repository, and do not paste images, only the text evidence.

## Qualitative observations (operator; not a pass/fail score)

- Does the image open?
- Is the person's identity broadly preserved?
- Is the garment visibly transferred?
- Are there severe artifacts?
- Are the pose and scene preserved?
- Is it usable?

If execution passes but quality is poor, record "runtime qualified; workflow
quality needs tuning". That leads to a separate tuning slice, not an
architecture change.

## Evidence to record

- the validator summary;
- the prepare-template output: kind, geometry, models, SHA-256;
- the full preflight output;
- the full generation output;
- the full reconciliation output;
- the qualitative notes above;
- GPU model and VRAM, as operator-supplied context only.

## Known limitations

- **Single run:** one run on one machine proves execution, not throughput
  or a minimum VRAM.
- **Preflight is point-in-time:** the provider can change between preflight
  and generation, and generation re-checks.
- **Quality:** instruction wording and sampler settings are untuned.
