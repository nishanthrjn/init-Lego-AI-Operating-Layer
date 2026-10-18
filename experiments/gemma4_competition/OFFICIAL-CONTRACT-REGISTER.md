# FORGEAI-GEMMA4-OFFICIAL-HARNESS-CONTRACT-1

Status: M1 PARTIAL; M2 BLOCKED.
Baseline: 461f01036390d00dcce1069adb6a804937dc4ff9.
Observed: 2026-10-18. Documentary validation NOT RUN — maintainer required.
NO IMPLEMENTATION, LIVE EXECUTION OR SUBMISSION AUTHORIZED.

## Provenance and conflicts

Source IDs and exact URLs are in `source-register.json`. Indexed official text
is evidence of what the index exposed, not byte-for-byte current artifacts.
Direct rules/data/starter/wheelhouse page bodies were empty in the web reader;
a browser fallback failed to initialize. No login or credential access attempted.
No official local files were obtained. Their versions and SHA256 are UNKNOWN,
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
