# FORGEAI-ANALYST-SUFFICIENCY-SAFETY-RUNTIME-IDENTITY-2

Status: **implemented, local validation pending (2026-10-07).** This is a
runtime compatibility and identity slice only. No safety case was run, no
semantic model call was made, no synthetic inference probe was sent, and no
PREFLIGHT or BASELINE was run.

- New live condition: **`forgeai-analyst-sufficiency-safety-live/2`**
- Report identity: `forgeai-analyst-sufficiency-safety-live-report/2`
- Package: `examples/forgeai/evaluation/analyst_sufficiency_safety_live2/`
- Validator: `validate_forgeai_analyst_sufficiency_safety_runtime_identity_2.py`

## 1. Why preflight refused

The authorized live/1 PREFLIGHT refused correctly with
`RUNTIME_IDENTITY_REVIEW_REQUIRED`: the local Ollama server reported 0.40.0,
and live/1 pins 0.35.1. The model tag, model digest, endpoint, SAFETY-EVAL-2
binding and clean tree all matched. No semantic call was made.

## 2. Historical refusal (preserved exactly)

| Field | Value |
| --- | --- |
| Directory | `examples/forgeai/safety1-preflight-c80435f8dadc/` |
| Run | `6c557182-67a9-4851-9260-058c36e896be` |
| Committed in | `ecbdf24` |
| Git tree | `be52fc954ed30e980ab85db7ea83692389581899` |
| Disposition | `RUNTIME_IDENTITY_REVIEW_REQUIRED` |
| Observed / required | Ollama 0.40.0 / 0.35.1 |
| Semantic calls | 0 |

The artifact is not modified or backfilled. `custody.py` pins it by Git tree
id, alongside the six earlier LIVE-1 smoke and preflight directories. The new
validator accepts exactly this set: any other run directory (committed or
untracked) or any change to a pinned one fails. A future run directory needs
its own reviewed entry. Earlier slice validators keep their own historical
scope and are not edited.

## 3. Why live/1 is preserved

- **live/1:** Ollama 0.35.1, locally qualified (70/70), never baselined. Its
  package, validator and qualification record are unchanged; a test proves it
  still pins 0.35.1.
- **live/2:** Ollama 0.40.0, the candidate future baseline condition.

Changing the live/1 pin in place would rewrite a qualified identity. A new
condition keeps every run attributable to exactly one runtime.

## 4. Provider surface actually relied upon

- Preflight probe: `GET /api/version` (version) and `GET /api/tags` (name,
  digest, exactly one row for the tag).
- `OllamaModelAdapter.chat`: `POST /api/chat` with `model`,
  `messages[{role, content}]` and `stream: false`. No `options`, so no
  `num_ctx`, sampling or `format` override is sent.
- Response fields read: `message.content` (string), `prompt_eval_count`,
  `eval_count`.
- Error mapping: any non-200 → rejected; connection refused → preflight
  error; timeout or reset → uncertain.
- Timeout and cancellation: the client urllib timeout plus LIVE-1 child
  supervision and termination. Both are client-side.

## 5. Compatibility findings (0.35.1 → 0.40.0)

Evidence:
- the Ollama source comparison `v0.35.1...v0.40.0` (26 commits, 206 files;
  diff SHA-256 recorded);
- the release notes;
- local metadata-only probes (`/api/version`, `/api/tags`, `/api/show`, with no
  model load).

The full record is
[runtime-compat-2.json](../examples/forgeai/evaluation/analyst_sufficiency_safety_live2/runtime-compat-2.json).

| Surface | Class |
| --- | --- |
| `GET /api/version` | UNCHANGED |
| `GET /api/tags` | COMPATIBLE CHANGE (additive `runner`; manifest-list rows would fail closed) |
| Model identity and digest | UNCHANGED (v1 tags preserved; template/system/params covered by the digest) |
| Legacy GGUF migration (new) | COMPATIBLE CHANGE (no qwen2 migrator, so the model is not migrated) |
| `/api/chat` request fields | COMPATIBLE CHANGE (optional `runner` only; omitted) |
| `/api/chat` response fields | UNCHANGED |
| Non-streaming behavior | UNCHANGED |
| Error mapping | COMPATIBLE CHANGE (new 400 still maps to rejected) |
| Timeout/cancellation | UNCHANGED (client-side) |
| UTF-8/text handling | UNCHANGED |
| Default context length | UNCHANGED (largest prompt about 4k characters, far below the smallest tier) |
| Local endpoint | UNCHANGED |
| Inference engine (llama.cpp b11232 → b11351) | COMPATIBLE CHANGE (no contract change) |

No MATERIAL or UNKNOWN contract surface was found. A synthetic chat call was
not needed and was not made: it would add no contract evidence.

**Limit.** The engine update means outputs are not claimed to be numerically
identical to 0.35.1. That is why live/2 is a separate pinned runtime identity.
No live/1 baseline exists to compare against. Earlier LIVE-1 design-eval
smokes ran on 0.35.1 and are not directly comparable to live/2 runs.

## 6. Live/2 identity

`identity.binding()` starts from the unchanged live/1 binding, which
re-verifies:
- the SAFETY-EVAL-2 freeze;
- the Agent 1.0.0, fingerprint, prompt and parser pins;
- the model tag and digest;
- the membership and budgets.

It then replaces only the condition, the report identity and
`ollama_version = "0.40.0"`. It also records the superseded runtime, the
compatibility-record digest, and both the live/1 and live/2 harness source
digests.

The preflight accepts exactly `0.40.0`. It refuses 0.35.1, 0.40.1, 0.41.0,
"0.40", release candidates, "latest" and an empty version. Otherwise it runs
the same zero-semantic-call checks as live/1, including the 22-payload leakage
sweep.

## 7. Unchanged experiment semantics

Live/2 reuses these from live/1, unchanged:
- the controller (`execute`);
- the leakage guard;
- the scorer and A–G decision;
- the stop rules;
- the lifecycle;
- the report schema and validation rules.

`storage.Store` stamps the live/2 report identity and validates with the
live/1 rules. A live/2 report is never accepted as a live/1 report.

Nothing changed in: Agent, prompt, parser, SAFETY-EVAL-2, scorer, gates,
membership, order, payload representation, path, progression or authority
semantics.

## 8. Verification (offline)

There are 27 tests covering the 20 required items, with the version-rejection
cases parametrized. The validator runs:
- the scope and qualification prerequisites;
- the Smoke 3 inventory;
- the identity, pin, compatibility and custody checks;
- the 25 coverage phases;
- regressions:
  - SAFETY-LIVE-1;
  - SAFETY-EVAL-2;
  - the LIVE-1 runtime;
  - the sufficiency Agent;
  - the Ollama adapter and local host;
  - the ForgeAI CLI binding;
  - architecture;
- the zero-provider/no-baseline guard, mypy, Ruff and the diff check.

All of it runs under `FORGEAI_LIVE1_OFFLINE=1`.

## 9. Next authorization gate

1. The operator runs
   `uv run python .\validate_forgeai_analyst_sufficiency_safety_runtime_identity_2.py`,
   then commits and confirms a clean tree.
2. **Separately authorized:** a new PREFLIGHT against
   `forgeai-analyst-sufficiency-safety-live/2` with Ollama 0.40.0, from
   `examples/forgeai/evaluation`:
   `uv run python -m analyst_sufficiency_safety_live2 PREFLIGHT --output <fresh dir> --approval-reference <ref>`.
   Its new run directory will need a custody entry before later validators
   accept it.
3. The 22-call BASELINE, hardening and LIVE-1 FULL remain unauthorized.
