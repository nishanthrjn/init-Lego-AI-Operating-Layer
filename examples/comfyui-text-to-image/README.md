# Local ComfyUI live qualification (operator-run)

Prerequisite: run `python .\validate_comfyui_text_to_image.py` from repository root
and obtain a passing deterministic result first. The launcher never starts ComfyUI.
The helper uses the root Python 3.14 environment and repository source; no install
of the optional package is needed for this example.

1. Start your external ComfyUI installation yourself using its documented CPU,
   CUDA or low-VRAM CUDA profile. LegoAI neither selects nor starts that profile.
   Keep the runtime at `D:\Work\Projects\AI-Applications\ComfyUI\ComfyUI_windows_portable`
   outside this repository. Confirm http://127.0.0.1:8188 is reachable.
2. Identify one ALREADY INSTALLED compatible checkpoint basename. The fixed proof
   requires CheckpointLoaderSimple, EmptyLatentImage, CLIPTextEncode, KSampler,
   VAEDecode and SaveImage. No custom nodes. No checkpoint discovery/download.
3. Create a fresh local proof directory and set its installed checkpoint name:

```powershell
New-Item -ItemType Directory -Path .\comfyui-proof
$checkpoint = 'REPLACE_WITH_INSTALLED_CHECKPOINT.safetensors'
.\.venv\Scripts\python.exe examples/comfyui-text-to-image/generate.py --prepare-template --workflow .\comfyui-proof\workflow.json --checkpoint $checkpoint
```

Review the generated seven-node API graph. It fixes all parameters except prompt
and seed and uses the original project-owned template shape. Generating a digest
is NOT approval: explicitly review/approve those bytes and the checkpoint before
using the digest printed above. The adapter verifies the pinned digest and exact
supported shape at startup. Any edit requires fresh review and a matching pin.

4. Invoke one generation, replacing the digest placeholder:

```powershell
.\.venv\Scripts\python.exe examples/comfyui-text-to-image/generate.py --workflow .\comfyui-proof\workflow.json --sha256 APPROVED_SHA256 --checkpoint $checkpoint --endpoint http://127.0.0.1:8188 --prompt "a red ceramic mug on a wooden table" --seed 42 --output .\comfyui-proof\mug.png
```

The destination must not exist; the helper refuses overwrite. It prints outcome,
effect, job ID, byte length and digest, never prompt/image bytes. Verify one PNG
exists, opens locally, and represents the requested image. Compare the displayed
job with the runtime UI/history and verify one submission; this is manual behavioral
qualification, not implied by the deterministic fake-server tests.

5. Repeat with a fresh destination and `--cancel-after 5`. Expect cancellation and
UNKNOWN provider cessation; if the job is already known its ID is retained. No
provider stop is claimed or attempted. Reconcile/stop that job yourself in ComfyUI
if needed. This prevents interrupting other users/jobs. Repeat with `--timeout 5`
to observe bounded deadline behavior. Do not blindly repeat an UNKNOWN submission.
5a. **Reconcile an existing job without resubmitting.** Use the job ID printed
by an earlier UNKNOWN/deadline result. Use the same workflow, digest and
checkpoint so the job can be attributed. `--output` is optional and must not
already exist.

```powershell
.\.venv\Scripts\python.exe examples/comfyui-text-to-image/generate.py --workflow .\comfyui-proof\workflow.json --sha256 APPROVED_SHA256 --checkpoint $checkpoint --reconcile JOB_ID --output .\comfyui-proof\reconciled.png
```

It always prints `submission performed: NO`, then a status: COMPLETED (with PNG
size and SHA-256), PENDING, FAILED, NOT_FOUND (history no longer exposed, for
example after a ComfyUI restart; this does not mean the job never ran) or
UNRESOLVED. Repeat it as often as you like; it is read-only.

5b. **Long CPU runs.** `--timeout` sets the total completion wait for new jobs,
up to 1800 s. For example, `--timeout 900` covers the observed ~640 s CPU run.
The value belongs to operator configuration, not to the request.

6. If another hardware profile is available, operator-restart ComfyUI with that
profile and repeat the SAME application command with a new destination. One profile
is sufficient for the first local qualification; cross-hardware equality is not claimed.

Paste the full validation output, ComfyUI version/profile, safe outcome/effect/job
summary, PNG size/digest, whether it opens and matches the prompt, and cancellation
receipt. Do not paste model files, images, raw workflow/history errors, secrets or
machine dumps. On failure no retry is automatic; investigate before a new attempt.

CPU/CUDA/low-VRAM differences can change speed, memory failures and supported models,
not application request fields. This helper never launches runtimes, downloads
models, installs nodes or mutates the external installation.
