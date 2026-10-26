# LEGOAI-FORGEAI-COMFYUI-14-DAY-DELIVERY-REALIGNMENT-1 — MAINTAINER REVIEW REQUIRED

**Audit date:** 2026-10-26.
**Method:** read-only shallow clone of the public GitHub repository, plus file and code inspection.
- No tests, validators, Docker, model calls or Kaggle jobs were run.
- No files in the repository were changed.

## 1. Branch and HEAD

| Item | Finding |
|---|---|
| Product branch | `br-LegoAI-Comfy-ForgeAI-Gemma4-KISSKI` at `6cf6ce87206ce31a13fcc95b7995183a09561ad8` ("feat(gemma4): qualify P3 for submission", 2026-10-25) |
| `main` | the same commit (`6cf6ce8`) |
| `br-LegoAI-Comfy-ForgeAI-KISSKICoKaHF-Gemma` | also the same commit; a duplicate branch, and a source of confusion |
| Competition branch `br-ForgeAI-Gemma4` | `cc333ab` ("ForgeAI-Gemma4 verified commit"), exactly one commit ahead of `6cf6ce8` |
| Product-specific commits | **none yet**; the product branch is the shared baseline |
| Uncommitted changes on your machine | **UNKNOWN** (remote view only). Run `git status --short` and `git rev-parse HEAD` before slice 1 |
| Older media/KiSSKI branches | `br-LegoAIPyLLMComfyCR-ForgeAI-KISSKIColabKagHF` and `Master` are ancestors of HEAD (merged). `br-PyLLMComfy-CustomerRec-ForgeAI` and `br-LegoAI-PyLLM-ComfyUI-CustomerRec` are not ancestors, but their content (KiSSKI probe, collation pack) appears present in HEAD. Treat as superseded; not proven |

The repository contains everything from the competition up to P3 (`experiments/gemma4_competition/`, `validate_forgeai_gemma4_*`). **Do not evolve those files on the product branch.**

## 2. Evidence-backed status

| Area | Status | Evidence (code inspected) | Caveat |
|---|---|---|---|
| ForgeAI CLI `forgeai run` | **WORKING** (replay; locally qualified) | `examples/forgeai/src/forgeai/cli.py` `_parse`/`main`/`_execute`; README v0.1 qualification 2026-10-08 | Windows + Docker Desktop scope only |
| Repository + task selection, targets/context | **WORKING** | `--repo --task --target[:create] --context --constraint`; `TaskRequest` | Operator chooses every file |
| Context preflight + exact confirmation | **WORKING** (maintainer-qualified) | `repository_context.py` `preflight_context`, `bind_context`, `confirm_inventory`; `terminal_context_confirmer` | Exact explicit paths only; no discovery |
| Instruction/guidance discovery (AGENTS/CLAUDE/README) | **NOT IMPLEMENTED** | `FORGEAI-V0.2-REPOSITORY-ENGINEER-READINESS-1` item D = ABSENT | Main usability gap |
| Planning step | **PARTIAL** (by design) | `CodingProposal` summary/reasons/risks/unknowns before approval; readiness §8 rejects a PlannerAgent | No pre-code plan record |
| Proposal → preview → approval → mutation | **WORKING** | worker `_attempt`; identity-bound approval; 800-line/96 KiB preview bound | Live quality unqualified |
| Real sandbox checks (Ruff/mypy/pytest) | **WORKING** (maintainer-reported pass) | `SandboxedEngineeringChecks`, `DockerSandbox`, `PYTHON_CHECKS` | Doc header still says "MAINTAINER VALIDATION REQUIRED"; update once confirmed |
| Review + one bounded rework | **WORKING** | `MAX_ATTEMPTS = 2`; architecture tests enforce ceilings | Same model binding for coder and reviewer |
| Patch/result reporting | **PARTIAL** | `cli.summarize` (human text); pilot-only `projection()` in `scripts/` | No machine-readable report in the product CLI |
| Error handling/diagnostics | **WORKING** | closed failure reasons; exit codes 0/1/2; no raw output kept | |
| OpenAI-compatible REMOTE binding (KiSSKI-capable) | **WORKING** (synthetic TLS only) | `remote.py`, `--binding openai-compatible-remote`, S1 credentials, custody | Live provider quality unqualified |
| KiSSKI model admission | **BLOCKED** | `scripts/forgeai_kisski_bounded_live_pilot.py`: `ADMISSIONS = ()` | DeepSeek, GLM and qwen3-coder-next not admitted |
| Truthful model-quality label in `forgeai run` | **NOT IMPLEMENTED** | Admission register lives only in the pilot script; the CLI does not state model quality | Slice 1 adds the label |
| Kaggle vLLM runtime | **WORKING** (synthetic only) | `experiments/kaggle/free_gpu_model_runtime/evidence/qualification-20261010`: `KAGGLE_RUNTIME_PASS`, Qwen2.5-Coder-14B-AWQ on 2 GPUs | No quality claim |
| Kaggle ↔ ForgeAI live bridge | **BLOCKED** | `KAGGLE-JOB-BRIDGE` review: `CONTRACT_BLOCKED_SECURITY_GAP`; manual file transfer only | |
| ComfyUI text-to-image (local) | **WORKING** (maintainer live-validated on CPU) | `packages/legoai-generative-media`; `examples/comfyui-text-to-image/generate.py`; 512×512 SD1.x template pinned by SHA-256 | Fixed geometry; loopback IP only |
| ComfyUI on Kaggle GPU | **NOT IMPLEMENTED** | none | Fits the loopback-only adapter if ComfyUI runs inside the notebook VM |
| Script-to-Video (scenes, TTS, subtitles, assembly) | **NOT IMPLEMENTED** | No video, ffmpeg, TTS or subtitle code in `src/`, `packages/`, `examples/` or `scripts/` | |
| VTO (Qwen-Image-Edit-2509) | **PARTIAL**: deterministic VTO-1/2 qualified; VTO-3 live **BLOCKED** by CUDA | `VIRTUAL-TRY-ON-VTO3.md`: template digest approved, node preflight stops at missing model files | Needs GPU and an ADR-020 decision for Kaggle (§6) |
| ADRs | 001–011, 014–016, 020–024, 026 accepted; 017–019 proposed; 025 "implemented for review"; **027 deferred** | `adrs/` | |

## 3. Feasibility (14 days, ending 2026-11-08)

| Goal | Feasible by Nov 8? | Reason |
|---|---|---|
| ForgeAI v0.2 Developer Preview with replay + real sandbox | **High** | Most of the pipeline exists; the gaps are reporting, guidance discovery, packaging and docs |
| KiSSKI live coding in the DP | **Low–medium** | Needs a newly qualified model; no candidate so far. Plan for the DP to ship KiSSKI as *experimental, not admitted* |
| Script-to-Video: one small GPU-generated demo | **Medium–high** for a storyboard video (GPU stills + CPU motion/TTS/subtitles); **Low** for true generative video clips in 14 days | |
| VTO still image on Kaggle | **Medium–low** | Model size vs T4 16 GB and ~30 GB RAM is unproven; ADR-020 decision needed first |
| Priority 3 (dramas, education, social) | **After Nov 8** | |

## 4. ForgeAI v0.2 Developer Preview — acceptance contract

The DP is accepted when **all** of these hold, with maintainer-run evidence:

1. `forgeai run` works from `examples/forgeai` on a clean committed `src/` + `tests/` + `pyproject.toml` repository. *(exists)*
2. Context preflight lists targets, explicit context **and discovered repository guidance files**, and requires confirmation. *(slice 2)*
3. Proposal preview, exact approval, mutation, real Docker checks, review and at most one rework. *(exists)*
4. Every completed run can print a bounded machine-readable report with truthful model quality. *(slice 1)*
5. `python demo.py accept|rework` gives a reproducible replay + real-sandbox demonstration. *(exists; slice 1 adds the flag passthrough)*
6. The KiSSKI path is reachable via the explicit remote profile and is labelled `UNQUALIFIED`. A live demo happens only if a model passes the unchanged admission rule and you separately authorize it.
7. One consolidated DP validator (reusing the existing phases) passes on the qualified Windows + Docker host.
8. A README "Developer Preview" section: quickstart, supported scope, known limitations, and "not an unattended or commercial coding agent".

**Not required:** live model qualification, arbitrary repository layouts, commit/push, hosted use.

## 5. KiSSKI feasibility and blocker disposition

- **What works:** the generic adapter (`function_call: null` compatibility), bounded receive, synthetic structured smoke for `qwen3-coder-next`, the pilot harness, and the frozen pack `2bab09bd…`.
- **What blocks a live DP demo:** an empty admission register. Disposition: **KEEP BLOCKED**. Do not weaken the frozen pack, its budgets (`OUTPUT_TOKENS = 1024`) or the all-dimensions rule.
- **Smallest legitimate routes, in order:**
  1. Ship the DP on replay + real sandbox, with KiSSKI labelled experimental. **Always available.**
  2. A separately versioned dev-screen (pack v2, new digest, frozen v1 untouched) with **redacted raw-output retention**, so adherence failures can finally be diagnosed. Then one fresh, unchanged-v1 Phase A/B for the best current KiSSKI candidate. Requires your live authorization.
  3. Only if (2) passes: a reviewed `Admission` row, then the existing disposable pilot.
- **Stop condition:** no candidate passes unchanged v1 by **Nov 5** → the DP ships with route 1 and no further live spend before release.
- **Terms:** KiSSKI is a free research service. Keep the KiSSKI path labelled non-commercial research use, and re-read current service terms before live runs.

## 6. ComfyUI video and VTO feasibility

**Kaggle execution model (no tunnel, no new credentials in LegoAI):**
- A Kaggle notebook is one bounded batch job. It installs a pinned ComfyUI and Python 3.14 (via pinned `uv`), and starts ComfyUI on `127.0.0.1:8188` inside the VM.
- It runs the *unchanged* LegoAI generative-media package against that loopback endpoint. This is exactly what the adapter supports.
- It writes PNG/MP4 outputs plus a provenance manifest (digests, workflow SHA, seed, model file names) to `/kaggle/working`.
- You trigger it and download outputs yourself (Kaggle UI or official Kaggle CLI). Kaggle credentials never enter LegoAI, the repo or prompts.

**Risks and decisions:**
- **Python 3.14 on Kaggle** is unverified for this package. The 1G runtime experiment already proves pinned-uv bootstrapping works there; the probe confirms it.
- **GPU quota is shared with the competition.** Your 30 GPU-hours/week cover both branches, and L4×4 burns them at 2×. Budget the product at **≤ 6 GPU-h/week**. Never attach product notebooks to the competition (competition hardware is restricted).
- **Video, staged:**
  - v1 is a storyboard video: GPU scene stills (existing 512×512 template, so first output is square 1:1), then CPU Ken-Burns motion (ffmpeg), local TTS, SRT subtitles and MP4 assembly.
  - v2 adds true text-to-video clips with a small permissively licensed model as a new reviewed workflow template and output validator. Verify license and VRAM before choosing.
- **VTO on Kaggle conflicts with ADR-020's "personal images stay local".** The adapter would see "local" (loopback inside the VM), but the images leave your machine.
  - Proposed rule: Kaggle VTO is allowed **only for synthetic or public-licensed sample images**, declared as such.
  - That needs an explicit decision, probably a short ADR or an ADR-020 supersession. Do not set `deployment = "local"` for Kaggle as a workaround.
  - Model fit (Qwen-Image-Edit-2509 fp8 ≈ 20 GB diffusion + ≈ 9 GB text encoder on a 16 GB T4 with ~30 GB RAM) is **UNKNOWN**; probe first. A smaller quantized variant would need a newly reviewed template digest.

## 7. Existing components to reuse

- **ForgeAI:**
  - `forgeai.cli` (`main`, `_execute`, `summarize`, confirmers);
  - `forgeai.worker.RepositoryTaskWorker`;
  - `forgeai.repository_context`;
  - `forgeai.remote` (REMOTE profile, disclosure preview);
  - `demo.py` and its fixtures;
  - `tests/forgeai_support.py`;
  - the pilot `projection()` derivations.
- **Engineering:** `CodingAgent`, `IndependentReviewer`, `AuthorizedRepositoryEvidence`/`Mutation`/`Structure`, `SandboxedEngineeringChecks`, `DockerSandbox`.
- **KiSSKI:**
  - `scripts/kisski_saia_qualification.py` (discovery);
  - `scripts/kisski_coding_eval/` (frozen pack runner and scorer);
  - the pilot script.
- **Media:**
  - `legoai_generative_media.service.open_text_to_image` / `open_virtual_try_on` / `preflight_virtual_try_on`;
  - `examples/comfyui-text-to-image/generate.py`;
  - `examples/virtual-try-on/try_on_cli.py` and `prepare_template.py`;
  - `comfyui-proof/workflow.json` and `tryon-workflow.json`.
- **Kaggle:** the `experiments/kaggle/free_gpu_model_runtime` bootstrap pattern (pinned uv, sanitized child environment, `/opt/bin/nvidia-smi`).

## 8. Missing pieces and risks

**Missing:**
- machine-readable run report;
- guidance discovery;
- DP packaging, docs and consolidated validator;
- Kaggle ComfyUI job notebook and manifest;
- scene planner, TTS, subtitles and assembly;
- VTO deployment decision;
- KiSSKI dev-screen with diagnosable outputs.

**Risks:**
- one maintainer running three workstreams plus the competition;
- shared GPU quota;
- Kaggle Python 3.14 bootstrap;
- VTO model fit;
- no admissible KiSSKI model;
- doc-status drift (several planning headers still say "MAINTAINER VALIDATION REQUIRED" after reported passes);
- validator sprawl (120 root-level validators).

## 9. Fourteen-day plan

| Dates | WS1 ForgeAI | WS2 KiSSKI | WS3 Media/Kaggle |
|---|---|---|---|
| Oct 26–28 | **S1 `FORGEAI-DP-RUN-REPORT-1`** → validate → commit | K1 offline: dev-screen pack v2 + redacted output custody (design and code) | C1 offline: Kaggle text-to-image job notebook + manifest (reuse `generate.py`) |
| Oct 29 – Nov 1 | **S2 `FORGEAI-DP-GUIDANCE-PREFLIGHT-1`**: AGENTS/CLAUDE/CONTRIBUTING/README on target ancestry proposed as read-only references in the existing confirmation; oversize shown, never truncated | K2 (**live authorization**): discovery + dev-screen of 1–2 candidates | C1 run (~1 GPU-h); C2 storyboard → MP4 assembly (CPU) |
| Nov 2–4 | **S3 DP packaging**: README DP section, limits, consolidated DP validator | K3 (**live authorization**): fresh unchanged-v1 Phase A/B for the best candidate → admission review | C2 Kaggle run of a 3–5 scene demo; provenance check |
| Nov 5–6 | **S4** maintainer DP qualification on Windows + Docker | Stop condition at Nov 5; pilot only if admitted | C3: VTO decision + Kaggle feasibility probe with synthetic samples |
| Nov 7–8 | Tag DP; status headers updated | Labels final | Buffer; record honest results |

**Global stop conditions:**
- Any slice whose validator fails twice → stop and re-scope, never loosen checks.
- GPU usage for the product > 6 h/week → pause WS3.
- Any security decision (VTO deployment, credentials) → maintainer decision before code.

## 10. Workstream ownership

You are the single executor and approver for all three. Astra implements one slice at a time. This thread designs, reviews and writes prompts. The competition branch stays with its own thread.

Suggested daily order: WS1 first (DP is P0), then WS3, then WS2 live steps when authorized. If a second person is available, WS3 is the cleanest hand-off.

## 11. First high-value slice

**`FORGEAI-DP-RUN-REPORT-1`:** an opt-in `--json-report` flag that prints one bounded `forgeai-run-report/1` JSON line.

- It mirrors the pilot projection and adds changed paths, blocking count and start HEAD.
- `model_quality` is limited to `NOT_APPLICABLE_REPLAY` or `UNQUALIFIED`.
- No file write: the architecture tests forbid ForgeAI host writes.
- No change to existing output.

Why first:
- It closes DP items 4 and 6 and the "reproducible maintainer evidence" requirement.
- It touches only the application layer.
- It is the measurement base for KiSSKI screening and the DP validator.

## 12. Coding-agent prompt

See `FORGEAI-DP-RUN-REPORT-1_coding-agent-prompt.md`.

## 13. Future maintainer validation gates

| Gate | Command / evidence | Pass label |
|---|---|---|
| S1 | `uv run --locked --offline --no-sync python .\validate_forgeai_dp_run_report_1.py` | `FORGEAI-DP-RUN-REPORT-1 LOCAL CHECKS PASSED; …` |
| S2 | guidance-preflight validator (offline, fake sandbox) | `… LOCAL CHECKS PASSED` |
| S3/S4 | consolidated DP validator: offline phases + `LEGOAI_QUALIFY_FORGEAI_V02_SANDBOX=1` real Docker phases + `demo.py accept/rework --json-report` | `FORGEAI-V0.2-DP LOCALLY QUALIFIED; REPLAY + REAL SANDBOX; MODEL QUALITY UNQUALIFIED` |
| K2/K3 | your typed live authorization; v2 dev-screen report; unchanged v1 Phase A/B report | admission review decision |
| C1 | Kaggle notebook output: PNG passes the existing validator + provenance manifest digests | `KAGGLE-COMFYUI-T2I-1 GPU ARTIFACT PRODUCED` (single run, no quality claim) |
| C2 | MP4 + SRT + manifest; ffprobe duration/streams recorded | storyboard demo produced |
| C3 | written VTO deployment decision before any Kaggle VTO code | decision recorded |

## 14. Commit message

No repository files were changed by this audit. After S1 passes:

```
feat(forgeai): add bounded machine-readable run report (FORGEAI-DP-RUN-REPORT-1)
```
