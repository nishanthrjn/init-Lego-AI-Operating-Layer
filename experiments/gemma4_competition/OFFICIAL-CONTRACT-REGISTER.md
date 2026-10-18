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

## FORGEAI-GEMMA4-HARNESS-ARTIFACT-ACQUISITION-1

Decision: M1_PARTIAL_ADDITIONAL_ARTIFACTS_REQUIRED.
Main competition: M1 PARTIAL; M2 BLOCKED on runtime evidence independently of paper.
Baseline: c859f316bb4eff6a7a0cb86a5aabefe557e972c9.
Prior 23-artifact reconciliation: MAINTAINER_REPORTED_PASS (supplied transcript).
This acquisition review: NOT RUN — Awaiting maintainer execution of documentary gate.
NO IMPLEMENTATION, LIVE EXECUTION OR SUBMISSION AUTHORIZED.

No additional harness files were found in the supplied docs tree. A repository
filename search also found no HARNESS_README or wheel. This is a bounded local
inventory finding, not a claim that no official files exist elsewhere. The source
register records a fresh raw-byte inventory alongside the unchanged provenance
records. No new retrieval date, release identity or authenticity is inferred.
The requested README/compiler/tool inspection cannot be completed without bytes.
All earlier verified notebook/sample observations remain evidence at that level.

### Main-contract acquisition matrix

| Requested fact | Current evidence | What is still unknown |
| --- | --- | --- |
| README versus sample | Sample root and all includes available | README absent: cannot compare requirements/defaults against it |
| Exact agent fields/types | name/model/adapter strings; instruction include; tools sequence of strings plus agent_tool mapping; generate_content_config include in sample | Compiler-supported field set, requiredness, rejection rules and coercions; observed YAML value shapes are not normative types |
| Model enforcement | Notebook cell 8 asserts one model in four-name allowlist | Compiler/discovery/scorer allowlists and model revision enforcement |
| Tool contracts | Nine names and earlier overview signatures; prompts describe intended effects | Tool implementations, complete arguments, serialized return/error envelopes and failed-action effects |
| Filesystem | Notebook input/working paths; subprocess backend | Repository root, allowed commands, path/symlink confinement, escape controls and cleanup |
| Persistence | Same Evaluator is used by notebook | Whether edits persist across calls, reset per task or survive errors; UNKNOWN |
| submit_patch | Prompt calls it before a final summary; evaluator reads result.agent_patch | Whether it terminates agent, captures immediately or later, includes untracked files, or captures on timeout; UNKNOWN |
| Budgets | Sample 60 seconds / 10 tools / 1 minute / 50 turns; sampling 16384 output tokens | Enforced maxima, total model/tool/time accounting, retries and setup inclusion in scorer |
| Validation/output | Cell 12 validate_directory then ZIP; cell 10 displays id/prediction | Imported limits/extension list, final platform handoff and scoring patch lifecycle |

Cell 10 explicitly converts timeout_seconds/verification_timeout_seconds and
max_tool_calls to int, max_time_minutes to float, and max_turns (or max_llm_calls)
to optional int. Those notebook conversions do not prove compiler validation or
safe ranges. Sample thinking_budget is integer and include_thoughts boolean;
actual serving support cannot be inferred because litellm.drop_params=True.
Tool return type str in the earlier overview does not establish JSON contents.
No assumption of persistent edits or submit_patch termination is admissible yet.

### R1–R7 at this acquisition gate

| Blocker | Main-track disposition | Remaining evidence |
| --- | --- | --- |
| R1 | Captured main rules inspected; current amendments/entry checks remain external | Do not treat documentary pass as personal eligibility or rules acceptance |
| R2 | PARTIAL | Complete README and versioned compiler/package bytes |
| R3 | PARTIAL | Tool registry and implementations with return/error/effect contracts |
| R4 | PARTIAL | Enforced model allowlist, scorer inference/resource configuration |
| R5 | OPEN | Filesystem/lifecycle, persistence, cancellation, patch capture and budget enforcement |
| R6 | PARTIAL | Submission limits, final handoff and patch-output instructions |
| R7 | Paper only, PARTIAL | Preserve C2 judged-paper versus generic leaderboard discrepancy; separate clarification before paper submission |

The paper issue alone is not a main-runtime M2 blocker. Even setting R7 aside,
R2–R6 are material unresolved main-competition contracts. Neither track is
silently declared complete. No need for another model run to resolve these gaps.

### Exact minimal M2 file specification, conditional only

Proposed competition-owned output tree after M1 and separate implementation
approval: agent.yaml, prompts/system.md, configs/sampling.yaml and optional
eval_config.yaml, packaged at ZIP root. No ForgeAI runtime imports or new Ports.
Root field plan uses only observed names: name (one stable string), model (exact
12B notebook ID), instruction (!include prompts/system.md), tools (read_file,
edit_file, write_file, run_command, get_status, submit_patch), and
 generate_content_config (!include configs/sampling.yaml).
Sampling proposal retains 0.2 temperature, 0.95 top_p, 16384 max_output_tokens,
and thinking_config with 4096 thinking_budget / true include_thoughts until
compiler limits can be inspected. Optional evaluation proposal retains the
sample's timeout_seconds=60, max_tool_calls=10, max_time_minutes=1, max_turns=50.
These are exact candidate values, NOT validated runnable configuration.
No adapter, subagent, graph extensions or skills. Removing sample-only fields
must be checked against the official compiler; no default is invented.

Future acceptance requires official package validation of this minimal config,
known-bad model/tool/path/budget controls, and separately authorized patch handoff
and timeout tests after documented contracts are reconciled. Full task duration,
patch extraction and successful scoring cannot be inferred from ZIP creation.
This slice authors none of the proposed agent files and executes no checks.

### Minimal maintainer acquisition request

Supply under docs (or identify another local location):

1. Complete official HARNESS_README.md for the starter release, not a screenshot
   of its filename or a third-party replacement.
2. Versioned wheelhouse file listing plus the actual wheels providing
   adk_submission and swegemma (including adk_eval_core if it provides referenced
   behavior), and any referenced compiler/tool/sandbox dependency source needed
   to follow those contracts. Complete extracted sources with dist-info
   METADATA/RECORD are an alternative. No installation or model weights needed.
3. Official scorer inference/resource and final submission/patch-output
   instructions, only to the extent not already included in items 1–2.

For each acquisition retain source URL, version and actual retrieval timestamp.
The existing notebook/sample/screenshots do not need to be acquired again.
The exact wheel filenames beyond the visible listing cannot safely be guessed.
Do not supply credentials, account exports or provider responses.

The existing offline reconciliation validator is extended for this acquisition
slice, not duplicated. It pins the four changed documents and unchanged supporting
plans/artifacts, rejects out-of-scope changes and checks staged consistency.
It cannot qualify missing contracts. Use the command in the current milestones
section. Historical gate output remains recorded above.

### Supplied HARNESS_README reconciliation (supersedes initial acquisition finding)

The maintainer identified docs/HARNESS_README.md after the initial inventory.
All ten sections have now been read as text; the inventory now contains 24 files.
Its raw size/SHA256 are recorded in source-register.json. Exact source URL,
download timestamp and matching package release remain unknown. Official origin
is maintainer-attested; source filenames/line references inside prose are not
inspection of the referenced implementation. Earlier absence/UNKNOWN statements
are historical; the following upgrades them to DOCUMENTED, not source-verified.
Decision remains M1_PARTIAL_ADDITIONAL_ARTIFACTS_REQUIRED; M2 BLOCKED.

#### Schema documented by guide sections 2–3

Exactly one agent.yaml/agent.yml/root_agent.yaml/root_agent.yml is documented.
Missing/multiple roots raise MissingRootConfigError/MultipleRootConfigsError.
Default agent_class is LlmAgent. Documented LlmAgent fields: name (required str),
model (str, required unless host default), adapter (str or None), description and
instruction (str, up to 1,000,000 chars), tools (list of names/agent_tool references/
inline agents), skills (list[str] or None), sub_agents (list of config_path refs),
output_key (str or None), include_contents (default or none), transfer-disallow
flags (bool or None), generate_content_config (dict or None). SequentialAgent and
ParallelAgent use name/description/sub_agents/callbacks; LoopAgent max_iterations
is int 1–500, default 500. Callbacks' full schema is not supplied; excluded from M2.

Includes load md/txt as UTF-8 text and yaml/yml recursively, depth 10 with cycle
checks. Documented limits: 10,000 files, 1,000 YAML files, 50 MiB YAML/expansion,
50 MiB per skill, 500 agents, depth 50, 1,000 skills, 10,000,000 total instruction
chars. Extensions: yaml/yml/md/txt/py/json/safetensors; no pickle weights.
Generation fields: temperature, top_p, top_k, max_output_tokens, presence_penalty,
frequency_penalty, stop_sequences, response_mime_type, seed, thinking_config.
Output 1–32768 (default 16384); thinking budget 0–32768 (default 4096);
include_thoughts bool; thinking_level MINIMAL/LOW/MEDIUM/HIGH/NONE. Temperature
>=0, top_p 0–1, top_k >=1. Generation-level tools/system_instruction/http_options/
safety_settings/response_schema are documented rejected. No generic ADK fields
are inferred. Section 3 documents scorer validation of one of the four exact
quantized variants, with ParticipantVisibleError for invalid selections; the
notebook corroborates the four strings, not package implementation parity.

#### All nine built-in tools: documented responses/effects (section 6)

Arguments remain the exact signatures in the earlier tool table. Each returns a
JSON string. Budget-gated errors have status/error_type/error_message/details;
the separate ToolErrorPlugin instead documents status/error_type/error. Preserve
these different envelopes. No universal error-normalization contract is inferred.

| Tool | Documented result and effect |
| --- | --- |
| run_command(command) | bash -c in /workspace; success stdout/stderr/exit_code; nonzero CommandError with output in details; TimeoutExceeded does not itself end session; stdout/stderr each capped 5000 chars |
| submit_patch() | patch_size/files_changed; captures diff in submitted_patch, sets patch_submitted; ends loop after current turn/final response, not necessarily mid-tool sequence; no tool-count charge but wall-clock gate remains |
| get_status() | used/remaining tools, patch flag/size, remaining time, max turns and command timeout; no tool-count charge |
| read_file(filepath,start_line=None,end_line=None) | filepath/content/start_line/end_line/total_lines/is_truncated; 1-based inclusive slices; 150 lines and 10000 chars; tool-count charged |
| edit_file(filepath,old_string,new_string,allow_multiple=False) | filepath/occurrences/strategy/diff/is_truncated; exact then whitespace then regex matching; FileEditError for ambiguous matches without allow_multiple, missing/empty file or empty old string; charged; documented ambiguity refusal has no write |
| write_file(filepath,content) | filepath/size; creates parents and creates/overwrites file; charged |
| get_code_neighbors(node,edge_type=None,max_neighbors=50) | node/neighbors/count/is_truncated; name resolution exact/suffix/case-insensitive/substring; charged |
| search_similar_code(query,k=10) | query/results(node_name,code,similarity)/count/is_truncated; offline stored-node similarity or lexical fallback; charged |
| get_code_subgraph(nodes:list[str]) | nodes/edges(from,to,type)/node_count/edge_count/is_truncated; charged |

Graph outputs and edit diffs use 5000-char caps. File tools strip leading /
or /workspace/ and reject .. traversal; string numeric/bool coercions documented.
This does not prove symlink handling in implementation. No shell command allowlist
is described: run_command is shell execution subject to environment, not a
verified list of safe commands. Skill tools are excluded from M2; full skill
argument contracts remain absent. Generic error descriptions do not prove write
atomicity for every failure.

#### Lifecycle, budgets and patch output (sections 4–9)

Guide documents one persistent Container A /workspace across task tool calls,
then a separate fresh Container B for verification. This persistence is a
lifecycle inference from shared context and final working-tree diff, not an
executed observation. Docker default: no network, 4 GiB, 2 vCPUs, fresh phases;
optional pooling wipes workspace and temporary artifacts. Subprocess rewrites
workspace/tmp/wheels/usr-local-bin references to temporary directories and kills
the process group on command timeout. Such rewriting alone is not proof of
host filesystem isolation. Notebook subprocess versus guide Docker default is
now documented as supported backend variation, not necessarily a contradiction.

Agent timer starts after setup. Defaults: 60 minutes/task, 100 tools in inference
(None CLI), 500 turns; total-token/cost budgets None. Sample overrides stay
1 minute/10 tools/50 turns. Phase-1 command timeout defaults 300s and is bounded
by min(command_timeout,max(5,int(remaining_time))); verification 300s on scorer.
Scorer environment overrides are listed in section 7, not read here. 32768 is
combined context, not an overall task token allowance. Prior 12-hour total
patch-generation statement is not independently reconciled by per-task limits.
ModelRetryPlugin documents up to five transient retries with bounded exponential
backoff; this is official harness behavior, not a change to ForgeAI/KiSSKI retry
policy. Runtime accounting of all nested retries still requires source review.

submit_patch and fallback use git add -N plus binary diff against
_swegemma_baseline (fallback HEAD), including new nonexcluded files. Section 8
says protected tests/configs are stripped. If no explicit submission, stopping,
exhaustion or timeout may recover nonempty edits before teardown; timeout does
not imply no effect. Fresh verification strips/resets protected paths, applies
agent/test patches and requires exit 0 plus valid JUnit with required tests passed
and none skipped. Stage 1 scripts/inference.py produces submission.parquet with
id/prediction; notebook cell 10 only displays those columns. Cell 12 validates
and creates submission.zip; the package scorer transforms it later. These are
documented stages, not an instruction to fabricate a parquet in the notebook.

#### Conflicts and remaining evidence

C3: section 2.2 bans .. include components, but official sample analyzer uses
../prompts/analyzer.md and ../configs/sampling.yaml. Need version-matched compiler
source or organizer correction. Proposed M2 root-only includes avoid this case.
C4: section 8 strips protected files; section 10 says config edits appear in
agent_patch; baseline descriptions alternate tagged baseline and HEAD. Need exact
extraction/filtering source. M2 must not edit protected tests/configs regardless.
C5: prose requires size <3 GiB, notebook accepts <= imported bound; exact boundary
requires definition. Proposed M2 stays far below either. These discrepancies do
not justify guessing other contracts or claiming packages have been inspected.
Guide's simplified exit-code sequence diagram is qualified by section 8's stricter
JUnit criterion; use the latter for planning, subject to source corroboration.

R1 unchanged captured main rules; R2 PARTIAL (README now supplied, source absent);
R3 PARTIAL (nine documented contracts, implementation absent); R4 PARTIAL
(documented scorer allowlist/resources, package absent); R5 PARTIAL (documented
lifecycle/persistence/cleanup, implementation and isolation parity absent);
R6 PARTIAL (ZIP-to-parquet documented, limits conflict/final handoff outstanding);
R7 unchanged separate paper issue. No main contract is held open solely by R7.

Conditional M2 file/field/value proposal above remains valid as a documentary
specification. No subagent/adapter/skill/graph extension; root-only includes avoid
C3. Add prompt requirements: targeted verification before final submit_patch;
no protected test/config edits; remove scratch files before capture; account for
partial-patch fallback. Do not equate tool success with resolved test outcome.
Do not execute the guide's installation, CLI, shell or model examples here.

Minimal remaining request: version-matched compiler/tool/sandbox/inference/metric
package sources with METADATA/RECORD and wheelhouse listing; README download URL
and release identity; authoritative resolution of C3–C5 and final submission/
total-runtime instructions if not included in that release. No need to supply
README, notebook or sample again. No model weights required.
