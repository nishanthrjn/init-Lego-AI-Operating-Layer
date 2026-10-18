# FORGEAI-GEMMA4-OFFICIAL-HARNESS-CONTRACT-1

Status: M1 PARTIAL; M2 BLOCKED.
Baseline: 461f01036390d00dcce1069adb6a804937dc4ff9.
Observed: 2026-10-18. Documentary validation NOT RUN — maintainer required.
NO IMPLEMENTATION, LIVE EXECUTION OR SUBMISSION AUTHORIZED.

## Historical review (superseded where the reconciliation below adds evidence)

## Provenance and conflicts

Source IDs and exact URLs are in `source-register.json`. Indexed official text
is evidence of what the index exposed, not byte-for-byte current artifacts.
Direct rules/data/starter/wheelhouse page bodies were empty in the web reader;
a browser fallback failed to initialize. No login or credential access attempted.
At the previous review, no official local files were obtained. Their versions and SHA256 are UNKNOWN,
not invented hashes of summaries. The JSON register marks null hashes explicitly.

S1 (overview) still exposes the older single-variant restriction. S6 (Kaggle staff
Ryan Holbrook announcement) explicitly expands the list and disallows mixed
variants. For planning use S6's later announcement, while retaining conflict C1:
current rules and installed/scorer package enforcement have not been reconciled.
Staff comments report a recent wheelhouse fix for 12B loading; the exact corrected
version is unknown. Staff discussion also acknowledges a parallel-agent issue;
concurrency is not a verified baseline capability. Participant claims are not
promoted to official guarantees. No later authoritative resolution was found in
the accessible search results; that is not proof none exists.

## Model and runtime matrix

Announced models (S6; package enforcement UNVERIFIED):

- `gemma-4-31b-it-qat-w4a16-ct`
- `gemma-4-12b-it-qat-w4a16-ct`
- `gemma-4-e4b-it-qat-w4a16-ct`
- `gemma-4-e2b-it-qat-w4a16-ct`

Mixed variants within one submission are not supported.

| Contract | Evidence / status |
| --- | --- |
| Interactive GPU | S6 reports L4x4 notebook availability; exact scorer allocation/parity per variant UNKNOWN |
| Tool scheduling | S6 describes sequential tool execution; no baseline concurrency planned |
| Total budget | Prior S1 evidence: 12 hours for patch generation including setup; validation excluded; recheck current artifacts |
| API/serving config | UNKNOWN: endpoint, parser settings, sampling defaults, provider retry behavior, model aliases |
| Context/output/turn/tool bounds | UNKNOWN: do not copy defaults from third-party READMEs or model-card context windows |
| Network/dependencies | S1 indexed overview says L4 sessions disable internet; permitted package/file inventory and exact enforcement UNKNOWN |
| CPU/RAM/disk/task deadlines | UNKNOWN, including timeout cleanup and partial-patch persistence |
| Loading cost | Exact model/adapter accounting UNKNOWN; measure and include in future comparisons |

Smaller variants are engineering candidates for a lower resource burden, not
quality winners. The research plan specifies a matched 31B/12B comparison after
official-harness success. No model is admitted to general ForgeAI by this plan.

## Tool inventory: overview-level signatures only

S1 exposes these Python-style signatures, not complete JSON schemas. All return
`str`; encoding, error shapes and result limits remain UNVERIFIED. Names and
parameters below are interface facts, not executable examples or a new tool API.

| Tool | Input signature | Reported role |
| --- | --- | --- |
| run_command | `(command: str)` | shell execution |
| submit_patch | `()` | patch capture |
| get_status | `()` | budget/patch status |
| read_file | `(filepath: str, start_line: int \| None = None, end_line: int \| None = None)` | sliced file read |
| edit_file | `(filepath: str, old_string: str, new_string: str, allow_multiple: bool = False)` | replacement |
| write_file | `(filepath: str, content: str)` | write/create |
| get_code_neighbors | `(node: str, edge_type: str \| None = None, max_neighbors: int = 50)` | graph neighbors |
| search_similar_code | `(query: str, k: int = 10)` | embedding retrieval |
| get_code_subgraph | `(nodes: list[str])` | induced graph |
| run_skill_script | UNKNOWN | skill execution mentioned by S1 |
| load_skill_resource | UNKNOWN | resource inspection mentioned by S1 |

For EVERY row, official artifact verification must supply: JSON input required/
optional fields and constraints; output serialization; filesystem effects;
error envelope; timeout; cancellation/child cleanup; traversal/symlink policy;
persistence across calls; and time/token/tool accounting. None is inferred from
ForgeAI Ports. S1 describes `/workspace` effects and a persistent skill container,
but scope details such as absolute paths and failed-write atomicity are unresolved.
Final patch extraction/termination behavior cannot be inferred from a tool name.
Completeness of dynamically registered skill tools is also unverified.

## Configuration field inventory

| Surface | Mandatory / optional / unsupported / unknown |
| --- | --- |
| archive root | `agent.yaml` mandatory per indexed S1; filename/size/member/link restrictions beyond root confinement UNKNOWN |
| root type, names, subagents | Exact schema/defaults/allowed types UNKNOWN; M2 selects one root only |
| model selection | One S6 variant per submission; exact field validation/version reconciliation UNKNOWN |
| sampling | Optional config exists in S1 layout; keys/types/ranges UNKNOWN |
| tools | Official tool names above; declaration JSON/YAML schema UNKNOWN |
| prompt includes | S1 supports `!include` relative to declaring file; traversal outside root forbidden; complete parsing rules UNKNOWN |
| skills | Optional; SKILL.md frontmatter mentioned; full schema/path rules UNKNOWN; excluded from M2 |
| LoRA | Optional directory/config/weights in prior S1 evidence; precise compatibility/rank/loading restrictions UNKNOWN; excluded from M2 |
| eval_config.yaml | Optional per-task budgets mentioned; exact keys/defaults/maxima UNKNOWN |
| mixed variants | UNSUPPORTED by S6 |
| arbitrary production imports | Not assumed permitted; no submitted ForgeAI runtime or private LegoAI internals |

No runnable YAML/JSON agent configuration examples are included.
Generic ADK documentation is not a substitute for competition restrictions.

## Submission contract and paper checklist

Main sequence, with unresolved steps explicitly gated: obtain official starter;
inspect schema; choose a permitted variant; prepare root configuration archive;
use official validator; use exact starter notebook settings; produce harness
outputs; upload/select entry; inspect official failure/score receipt. Archive
format is evidenced, but exact commands, notebook cells, output schemas, selection
mechanics, queue limits and public/private score split are UNKNOWN. No guessed
Kaggle CLI invocation is provided. M2 requires the exact official procedure.

Paper S2 indexed evidence: join the track and submit an unpublished research
Writeup, up to 3,000 words, by November 12, 2026 at 23:59 UTC. Judging weighs
novelty, generalization/quality, relevance, verifiability and clarity equally.
Save alone is not submission. A public paper PDF or code notebook may be linked.
Full eligibility, external-resource permissions, publication/IP requirements and
resource visibility consequences require the complete rules, independently of M2.
Keep paper drafting/experimental protocol moving without claiming experiments;
do not wait for final leaderboard submission to prepare the paper.

## R1–R7 closure and exact maintainer evidence request

| Blocker | Status | Supply these exact official artifacts, with source URL and download/version date |
| --- | --- | --- |
| R1 | OPEN | Complete saved main Rules and Paper Rules pages, including competition-specific and general terms |
| R2 | OPEN | Official `HARNESS_README.md`; starter `.ipynb`; complete `sample_submission/` tree with all includes; wheelhouse file/version listing and official package wheels or extracted METADATA/RECORD plus compiler/schema/tool source |
| R3 | PARTIAL | Nine S1 signatures known; supply tool implementation/schema exports and official skill tool declarations to resolve every missing contract column |
| R4 | PARTIAL | Four S6 models confirmed; supply updated inference/scorer configuration and corrected wheelhouse versions, model revisions and runtime limit documentation |
| R5 | OPEN | Official sandbox/evaluator implementation or documentation for effects, cleanup, patch extraction and resource accounting |
| R6 | PARTIAL | Complete official submission instructions, current starter cells, archive validation and scoring/output schema; public/private split and final selection policy |
| R7 | PARTIAL | Complete paper rules and saved submission form/help; indexed deadline/word count/rubric do not close eligibility/publication checks |

Do not send credentials, access tokens, private account settings or raw model
responses. Authorized local copies suffice; no package installation is needed
for static reading. Exact wheel filenames cannot be named before the official
listing is available. Hash raw downloaded bytes, retaining originals unchanged.
No artifact can be marked VERIFIED_FILE until its bytes and official provenance
are inspected; a URL or SHA256 alone does not prove authenticity.

M1 acceptance: all R1–R7 material blockers resolved against pinned official files.
Current outcome: M1 PARTIAL; documentary pass cannot close it.

## M2 specification, conditional on M1 closure

One root coding agent; one selected permitted model; official tools only; minimal
system instructions; no subagents; no LoRA; no new graph or skill extensions.
Implement under this experiment directory only after authorization. Required
future artifacts: root agent configuration, minimal prompt if officially supported,
exact packaging manifest, source/version pins, official validation command and
reproducible safe run record. No invented adapter to imitate competition tools.

Acceptance tests, to be authored after schema verification: valid starter-derived
configuration accepted; wrong/mixed model and unknown tool rejected; include/path
escape refused; patch handoff accepted; bounded timeout and failure preserve truth;
clean public/synthetic task completes in official harness. Maintainer runs all
checks/models. Passing local compile alone is not scoring compatibility.
Keep provider-neutral product interfaces, explicit operator confirmation, frozen
evaluation and all model admissions unchanged. No live authorization is conferred.

## FORGEAI-GEMMA4-OFFICIAL-ARTIFACT-RECONCILIATION-1

Decision: M1_PARTIAL_ADDITIONAL_ARTIFACTS_REQUIRED.
Status: M1 PARTIAL; M2 BLOCKED.
Baseline: e8e14bd9a075ec7b2cc39a1aa3c9a405d452a462.
Verification: NOT RUN — Awaiting maintainer execution.
NO IMPLEMENTATION, LIVE EXECUTION OR SUBMISSION AUTHORIZED.

This dated reconciliation supersedes current unknowns above only where identified
below. The previous official-harness documentary gate passed according to the
maintainer transcript; that result did not qualify runtime contracts.

### Artifact provenance and inspection

`source-register.json` inventories all 23 supplied files with raw-byte SHA256,
size, source attribution and date limitations. Originals under `docs/` are
unchanged. These are maintainer-supplied official copies, not independently
server-authenticated downloads. Screenshot filenames indicate 2026-10-18;
non-screenshot retrieval times and release revisions are UNKNOWN. Do not infer
download time from filesystem modification time. The wheelhouse capture footer
reports retrieval 2026-10-18T09:59:51+00:00; its displayed Version 31 is a dataset
version, not a verified installed wheel version. Its visible selected file is
`adk_eval_core-0.1.0-py3-none-any.whl`; the page reports 41 files. The capture is
not those wheel bytes or a complete machine-readable file manifest.

Read the notebook's complete 13-cell source, all supplied YAML/JSON/prompt text,
paper requirements and both rules captures through their final definitions.
Adapter safetensors were hashed, not loaded. Notebook outputs are historical
embedded data, not evidence of execution here. Code-listing screenshots include
participant examples: those listings are not official harness authority, and no
third-party implementation has been adopted. No complete HARNESS_README or wheel
is supplied, so neither could be inspected. Absence is a material blocker.

### Verified sample fields, not a complete agent.yaml schema

| Surface | Fields/values actually present | Limits of evidence |
| --- | --- | --- |
| agent.yaml | name, model, adapter, instruction, tools, generate_content_config | Requiredness, unknown-key rejection, types/ranges and defaults require compiler source |
| root | swe_baseline_agent; gemma-4-31b-it-qat-w4a16-ct; main_lora | Sample choices, not mandatory settings |
| instruction | !include prompts/system.md | Relative include demonstrated; traversal/symlink enforcement unverified |
| tools | Nine tools in the historical signature table; agent_tool mapping with config_path and skip_summarization: true | Tool registry and error/return schemas unavailable |
| subagent | name, description, model, adapter, instruction, tools, generate_content_config | Analyzer includes ../prompts/analyzer.md and ../configs/sampling.yaml within sample root; ../ alone is not an escape |
| sampling | temperature 0.2; top_p 0.95; max_output_tokens 16384; thinking_config: thinking_budget 4096, include_thoughts true | Accepted ranges/effective backend behavior unverified; notebook sets litellm.drop_params=True |
| eval_config.yaml | evaluation: timeout_seconds 60, max_tool_calls 10, max_time_minutes 1, max_turns 50 | Sample overrides, not scorer maxima |
| adapters | main_lora and tool_lora: rank 4, alpha 8, layer 0, q_proj/o_proj, 31B base | Dummy starter adapters, no training/quality claim; M2 excludes them |

The nine names and overview signatures above remain the available argument and
return inventory. A YAML list of names does not establish JSON schemas. Prompt
instructions mention patch_size and files_changed after submit_patch, forbid
editing tests and recommend targeted commands. These are starter prompt claims,
not proof of tool enforcement. Read tools have intended inspection effects;
edit/write mutate files; run_command may execute arbitrary effects; submit_patch
captures a patch; get_status observes state; graph tools retrieve graph data.
Actual error encoding, atomicity, path confinement, command policy, cancellation,
cleanup and accounting remain UNKNOWN for each tool. No guessed safety contract
is promoted to verified status.

### Notebook execution and packaging sequence (static inspection only)

Cell numbers are zero-based in the pinned notebook JSON.

1. Cell 2 prepares offline wheel installation from the metric wheelhouse,
   rewrites cu128 wheel link names, skips cutlass and invokes pip. Not executed.
2. Cell 4 copies the official sample into /kaggle/working/sample_submission,
   defaults MODEL_NAME to 12B, rewrites YAML models and removes dummy adapters
   for non-31B variants; loads tasks.jsonl from the competition data root.
3. Cell 6 demonstrates graph library functions. Their signatures are NOT the
   agent tool signatures and do not supply the missing tool contract.
4. Cell 8 discovers declared models, asserts exactly one model from the four
   announced variants, configures vLLM and creates the model registry. Model
   path is /kaggle/input/models/google/gemma-4/other/{declared_model}/2.
   This verifies notebook allowlisting, NOT hidden scorer/package enforcement.
   Localhost port 8000; gemma4 tool/reasoning parsers; max_model_len 32768;
   GPU memory utilization 0.90; startup timeout 1200 seconds; tensor parallelism
   4/2/1 from GPU count; automatic tool choice. No runtime success inferred.
5. Cell 10 reads optional eval_config.yaml or .yml (evaluation mapping or root),
   defaults command and verification timeout to 300 seconds, tools to 100,
   time to 60 minutes and optional turns to max_turns/max_llm_calls. It calls
   build_submission_limits; its actual enforced maxima are unavailable.
   EvalConfig uses sandbox='subprocess', snapshots/results/graph/embedding/wheel
   directories and tasks[:2]. It evaluates sequentially and displays id/prediction
   rows, substituting NO_PATCH for empty patches. It does not write a parquet
   submission file. These sample tasks are not a full leaderboard evaluation.
6. Cell 12 rejects symlinks, invokes validate_directory with imported limits,
   creates /kaggle/working/submission.zip with sample contents at archive root,
   checks uncompressed member total against imported MAX_SUBMISSION_SIZE_BYTES
   (message says 3 GiB) and extensions against ALLOWED_SUBMISSION_EXTENSIONS.
   The imported definitions and final Kaggle upload/selection sequence are absent.

Do not equate /kaggle working/input paths with a verified task sandbox root.
The earlier overview's Docker description and notebook subprocess setting may
refer to different execution contexts; isolation/scorer parity is unresolved,
not proof either is wrong. No verified command allowlist is supplied.

### Both rules captures and paper instructions

The captures show competition-specific sections 1–9 and foundational sections
1–18. Both have maximum team size five, up to two final selections, account,
age/residence/export-control and employer-consent conditions, no private sharing
outside teams, no hand-labeling validation/test records, rights/licensing and
winner reproducibility obligations. Main permits one submission/day; paper five.
Both identify Apache 2.0 winner licensing and competition/commercial data use,
while also imposing data security restrictions. Broad external-data/model/tool
permission is subject to accessibility, cost, rights and competition-specific
restrictions; it does not authorize a non-Gemma submitted runtime. Foundation
terms explicitly take precedence on conflict. Eligibility of this maintainer is
not established by reviewing text. No entry or rules acceptance was performed.

The paper requirements copy specifies unpublished original work, 3000 words,
non-archival participation, a submitted Kaggle Writeup (saving a draft is not
submission), optional public code/PDF and November 12, 2026 23:59 UTC. Attached
private Kaggle resources may become public after the deadline. Do not publish
restricted task data. Both rules captures contain generic private-leaderboard
winner language, whereas the paper overview specifies judged research. Preserve
this discrepancy as C2: obtain organizer clarification of controlling paper
judging/submission terms before paper submission. No invented resolution.
Main public/private leaderboard distinction is documented; split sizes unknown.

### R1–R7 reconciled disposition

| Blocker | Current status | Remaining closure evidence |
| --- | --- | --- |
| R1 | PARTIAL: both full rules captures inspected and hashed | C2 paper judging conflict and any current amendments; participant eligibility separately confirmed |
| R2 | PARTIAL: notebook and complete supplied sample tree pinned | Complete HARNESS_README; actual wheels/compiler schema and package metadata |
| R3 | PARTIAL: sample declarations corroborate nine tools | Exact schemas, serialized results/errors, effects and skill registration source |
| R4 | PARTIAL: four variants enforced in supplied notebook | Package/scorer model allowlist, corrected wheel identities, model revision/resource parity |
| R5 | OPEN: notebook subprocess backend observed | Sandbox roots, commands, escape controls, cancellation/cleanup, extraction and enforced budgets |
| R6 | PARTIAL: ZIP creation and local validation call identified | Imported limits/extensions, scorer output rules, full upload/selection procedure |
| R7 | PARTIAL: full captured rules plus requirements text | C2 judging reconciliation and exact submitted-form receipt procedure |

C1 older single-variant overview versus staff announcement is corroborated in
favor of four variants by the notebook, but package enforcement remains unknown.
C2 is a documented conflict, not silently resolved. Missing runtime artifacts
alone prevent M1 completion; primary decision remains additional artifacts required.

### Minimal M2 specification (blocked, no implementation)

Use only sample-demonstrated fields: one root name, one exact model, instruction
include, a tools list and generate_content_config include. Candidate initial
model is the notebook's 12B choice; this is a resource hypothesis, not admission
or quality evidence. No adapter, agent_tool, subagent, skill or custom graph code.
Initial tool list: read_file, edit_file, write_file, run_command, get_status,
submit_patch. Keep sampling field names from the sample; finalize values only
after enforced limits are available. Optional evaluation mapping uses the four
sample keys, with proposed values 60/10/1/50 subject to official validation.
Do not ship executable YAML in this slice or assume omission of sample adapters
is compiler-valid solely from this specification.

After M1 closure and separate authorization: create root agent.yaml and prompt/
sampling files; validate with the pinned official validate_directory API; package
using the inspected archive sequence; obtain one authorized public/synthetic
patch receipt before optimizing. Negative controls must reject wrong/mixed model,
unknown tool, path escape, invalid bounds and unsafe members. Test actual timeout,
patch handoff and budget behavior. Maintainer runs all checks. No private LegoAI
imports, ForgeAI production changes, KiSSKI evaluator changes or admissions.

Next acquisition: complete HARNESS_README, versioned wheelhouse manifest and
actual adk_submission/adk_eval_core/swegemma-containing packages (or complete
extracted source plus METADATA/RECORD), scorer configuration and final submission
instructions. Obtain paper conflict clarification. No model weights required.

Manual documentary gate: validate_forgeai_gemma4_official_artifact_reconciliation_1.py.
It verifies local byte pins and documentary invariants, not official authenticity,
legal eligibility or runtime compatibility. The older validator is historical and
expects an empty artifact register; do not use it for this new slice.
