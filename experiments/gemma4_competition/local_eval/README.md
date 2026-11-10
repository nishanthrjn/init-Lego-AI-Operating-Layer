# FORGEAI-GEMMA4-M3-LOCAL-EVAL-HARNESS-1

## P3 replicate / P4 time-budget preparation

See the [current offline-authoring instructions](../README.md#forgeai-gemma4-p3-replicate-and-p4-time-budget-1)
for the two JSON run configs, P4 package command, projections and selection rule.
`analysis.py summary A --compare B --same-config` and
`compare_runs.py --run A=FOLDER --run B=FOLDER --same-config A=B` now expose
per-task replicate flips and agreement under strict identical-config checks.
Both require pinned controls; the latter also requires `--output`.
Execution remains **NOT RUN — Awaiting user execution**. Historical text follows.

## FORGEAI-GEMMA4-P3-CONTEXT-FIX-AND-GRAPH-REDO-1

Authored; NOT RUN. Historical candidates, packages and run artifacts remain
unchanged. P3 and P3g are experimental, not submission qualified. Packaging and
category recomputation are maintainer actions, not already completed results.

### Evidence and interpretation

The three original study artifacts are preserved in
`../results/localization-study-attempt1/` with `preserved-sha256.json`. Git preserves
their raw bytes. summary.json SHA256:
`c806c382ab488ee544323ff5ee7d08cb2e3b3590b15aed71ee19747749eb8927`.
The original hashes.json also references per-task JSONs that intentionally remain
external; it is not a claim that those files are committed. study.jsonl is ranked
names/metadata only. File Recall@5 L/T1/T2/fusion: .204/.310/.311/.365; Recall@10:
.307/.322/.353/.443. Function Recall@10: .041/.147/.149/.162. These are the original
reported metrics, not rerun/revised numbers or evidence of an agent improvement.

P2 completed execution in approximately 4150 s with eight recorded successes.
Its only graph invocation was get_code_neighbors once; search_similar_code was
never called. dev-16v-comparison.json preserves that descriptive result and the
remaining qualified-summary limitation. The documented symbol-query contract
(HARNESS_README §6 tool 8; swegemma 0.2.11 tools/graph.py:205–211,448–460) conflicts
with P2's issue-behaviour instruction at the intended-use level: the tool supports
a fallback but advertises symbols. This motivates, but does not prove, P3g.

The pinned official starter **cell 8**, retained in official-cells.json, explicitly
sets `VllmConfig(max_model_len=32768)`. The actual serving owner is
**adk-submission 0.2.13**, `adk_submission/server.py:125,152,698–699`: the field
defaults to 32768 and becomes `--max-model-len`. We do not attribute that option
to swegemma or claim hidden-scoring settings are identical.

P2's task-bound official error records explicitly report ContextWindowExceededError
for rich_3934, fastapi_14419 and rich_3471: requested output 16384 plus at least
16385 input exceeded 32768. Retained P1b attempt2 official records confirm rich_3471 has the same exception;
all 16 P1c official task records contain no ContextWindowExceededError. With output 8192 the nominal input
allowance is 24576 instead of 16384; special tokens, growing prompts and actual
serving settings still matter. Lower output capacity may also truncate generation.
P3 holds thinking_budget=4096 fixed to isolate the output reservation from P1c's
thinking-budget change. Existing M2/B2/P1 submissions are not rewritten.

### Outcome projection and provenance

Independent inspection of retained official task-result fields confirms P1b
attempt2 has eight new records plus eight inherited tasks: rich_3471 has the
context exception, and rich_4079 reports `Agent exceeded session timeout (6.0 min)`.
P1c's 16 records contain the same timeout for fastapi_5624, rich_3934,
fastapi_5077, rich_4079 and fastapi_15589, and no context exception. These are
distinct failure mechanisms; a timeout must not be labelled a context failure.
The newly reported hyphenated download paths were absent during inspection;
commands below use the accessible, hash-identical `local_eval_p1_dev30` copies.
No category summary or evaluation was executed to establish these field readings.

analysis.read_run now reads optional official/task_results.jsonl, requires unique
task/repo identities and agreement with retained official resolution, and passes
the structured error to continuation.project. Exact ContextWindowExceededError
adds CONTEXT_WINDOW_EXCEEDED and treats the per-task request failure as UNRESOLVED.
Only the generic HARNESS_ERROR_DETAILS_IN_EXTERNAL_LOG flag is removed; independent
infrastructure/verification errors remain. Model prose mentioning the exception
does not establish an error. No raw errors are added to committed records.

Historical JSONL is never rewritten. Run the summary commands below to recompute
derived categories. Expected P2 projection: eight resolved, seven unresolved and
fastapi_15800 still unknown unless separately adjudicated. Its verification error
is not a context failure; no complete pass rate or time gate is manufactured here.
Resume manifests created now also pin official/task_results.jsonl when present.
Older manifests that omit this classification-bearing file must be regenerated
to a fresh external directory using continuation.py before a future resume.

### Candidate boundaries and maintainer sequence

P3 differs from P1b only by `max_output_tokens: 8192` in sampling.yaml; thinking
4096, model, six tools, prompt and 180/28/6/80 budgets are unchanged. P3g differs
from P3 only by adding the three graph tools and replacing prompt section 2 with
bounded grep -> symbol -> neighbors/similar-symbol lookup, at most three graph
calls. All other prompt sections, budget and sampling remain byte-identical.

From repository root in the existing uv environment (no credentials needed):

```powershell
uv run --locked --offline --no-sync python -B -m unittest discover -s experiments/gemma4_competition/local_eval -p 'test_*.py'
if ($LASTEXITCODE -ne 0) { throw 'P3 context and candidate controls failed' }
uv run --locked --offline --no-sync python -B experiments/gemma4_competition/local_eval/experimental.py p3 --output 'C:\Work\Gemma4Localtest\gemma-p3-experiment'
if ($LASTEXITCODE -ne 0) { throw 'P3 packaging failed' }
uv run --locked --offline --no-sync python -B experiments/gemma4_competition/local_eval/experimental.py p3g --output 'C:\Work\Gemma4Localtest\gemma-p3g-experiment'
if ($LASTEXITCODE -ne 0) { throw 'P3g packaging failed' }
$controls = 'experiments/gemma4_competition/local_eval/evidence/controls-05706c6a.json'
$controlsHash = '05706c6a948a67bfaf991ed0282d11308aac79865a614a68c6c582fe01f67033'
uv run --locked --offline --no-sync python -B experiments/gemma4_competition/local_eval/analysis.py summary 'C:\Work\Gemma4Localtest\local_eval_p2_dev16v\forgeai-local-eval-p2-dev-16v-attempt1' --controls $controls --controls-sha256 $controlsHash
if ($LASTEXITCODE -ne 0) { throw 'P2 category projection failed' }
# Set these to actual extracted run directories, not ZIP files or tooling folders.
$p1bRun = 'C:\Work\Gemma4Localtest\local_eval_p1_dev30\p1b\forgeai-local-eval-p1b-dev-16v-attempt2'
$p1cRun = 'C:\Work\Gemma4Localtest\local_eval_p1_dev30\p1c\forgeai-local-eval-p1c-dev-16v-attempt1'
foreach ($run in @($p1bRun, $p1cRun)) {
    if (-not (Test-Path -LiteralPath "$run\run.json" -PathType Leaf)) { throw 'Set the actual retained run path' }
    uv run --locked --offline --no-sync python -B experiments/gemma4_competition/local_eval/analysis.py summary $run --controls $controls --controls-sha256 $controlsHash
    if ($LASTEXITCODE -ne 0) { throw 'Historical category projection failed' }
}
```

For a merged P1b view, task errors can only be newly derived where the corresponding
official records are present. Analyze attempt2 separately if its error records are
not in the merged folder; absence is UNKNOWN, never evidence of zero errors.

Expected tests OK; package state EXPERIMENTAL_UNQUALIFIED and printed ZIP/manifest
hashes; output directories must be fresh. No ZIP is produced by this coding slice.
After successful offline checks, use the existing GPU notebook with a **gold-free**
tooling dataset. Run **P3 first, then P3g**, both on dev-16v and pinned controls.
Attach each respective .zip.bin and manifest, set experimental_authorized true,
package_mode EXPERIMENTAL_UNQUALIFIED, candidate p3/p3g, and paste its printed pins.
Use separate fresh output directories containing `dev-16v`. Authorization phrases:
`AUTHORIZE FORGEAI GEMMA4 LOCAL EVAL p3 ON dev-16v` and
`AUTHORIZE FORGEAI GEMMA4 LOCAL EVAL p3g ON dev-16v`.
Keep existing GPU/Internet-Off confirmations and serving cells unchanged. Compare
context errors, graph adherence, paired task outcomes and the existing time-fit
gate; do not infer superiority from aggregate counts alone. Do not attach the CPU
study dataset or gold-location metadata. No submission is authorized.

## FORGEAI-GEMMA4-P2-LOCALIZATION-STUDY-AND-CANDIDATE-1

Implementation and tests authored; execution NOT RUN. No experimental ZIP has
been built in this slice. P2 is EXPERIMENTAL_UNQUALIFIED, never submission-ready.

Reviewed metadata is preserved byte-for-byte at `evidence/gold-locations.json`,
SHA256 `c366076d5d2862d6a3c07c5db6f977c06bdcef8f94657f3f6591501826290c54`.
Its 129 records comprise 65 RESOLVED and 64 PARTIAL; unknown scopes are not zero
recall. Metadata contains paths/scopes/counts, no patch, issue or source text.
The maintainer's 11 solved patches and localization examples motivate a hypothesis,
not a measured P2 improvement or a causal attribution of every NO_EDIT outcome.
`fastapi_15800` stays in the study: patch size alone does not justify excluding it.
Previously reported public-notebook opinions are unverified, not study authority.

### Pinned source findings

All line references below are inside the preserved swegemma 0.2.11 wheel.
HARNESS_README §6 tools 7–9 documents these three interfaces:

| Tool | Implementation / contract |
|---|---|
| `search_similar_code(query: str, k: int = 10)` | `tools/graph.py:197–288`: JSON `status`, `results[{node_name,code,similarity}]`, count/truncation; `SimilaritySearchError` on failure |
| `get_code_neighbors(node: str, edge_type: str \| None = None, max_neighbors: int = 50)` | `tools/graph.py:88–194`: JSON neighbors/count/truncation, `GraphLookupError`; callers/callees, optional relation filter |
| `get_code_subgraph(nodes: list[str])` | `tools/graph.py:291–421`: JSON nodes, directed edges/from/to/type and counts/truncation; `SubgraphExtractionError` |

`tools/__init__.py:43–45` binds these exact names; graph.py:424 onward supplies
ADK factory wrappers. README §2 tools registry permits named registered tools.
This establishes static name availability, NOT an executed P2 compilation pass.
The unchanged evaluator compiles the package when loading it; load/compile failure
must stop the GPU run. No official package changes or synthetic compiler bypass.

Each tool uses repo/base_commit and graph/embedding paths from context and
`use_local_storage=True` (graph.py:138–162,237–259,344–364).
`graph/retrieval_utils.py:785–863` selects an existing embedding for a resolved
symbol, otherwise falls back to lexical node/code token overlap.
`graph/embedding_utils.py:388–436` looks up stored values and returns None when
missing: no live embedding model. Thus T1(issue text) is generally the official
LEXICAL FALLBACK, not neural semantic embedding of the issue. No LLM needed.
Missing/unsupported graph, embedding or snapshot inputs are UNAVAILABLE, not
evidence of poor localization. Hidden scorer retrieval parity remains UNKNOWN.

### Frozen CPU study protocol and setup

1. First run the offline tests below. Upload a **CPU-only** tooling dataset containing
   the complete local_eval directory, pinned official-cells.json and the reviewed
   gold metadata. Attach public competition data and official wheelhouse at
   `/kaggle/input/datasets/metric/gemma-4-developer-agent-wheelhouse`.
2. Import `localization_study.ipynb`. Accelerator **None**, Internet **Off**; no
   model/candidate input. Set TOOLS to the attached local_eval directory, a fresh
   OUTPUT, and all three confirmation flags True. Approval:
   `AUTHORIZE FORGEAI GEMMA4 LOCALIZATION STUDY CPU`.
3. Run only that notebook's cell. The worker reuses unchanged, hash-checked starter
   **cell 2** via runtime.install_official_environment, never cell 8 or evaluator.
   It records environment.json. No other installation or dependency repair.
4. The study launches a fresh CPU child per public task (300 s timeout), sequentially,
   with a 3 h loop guard and 11400 s notebook subprocess guard. Quota/runtime cost
   UNMEASURED. Download the entire output outside the repo; do not commit traces.

Snapshot enumeration follows official `deduplication.py:1311–1368`; Python source
is read from tar members and a base-to-task delta reconstructed in memory with
exact context checks. It is never imported/executed. This restricted textual reader
does not claim full Git parity: unsupported deltas produce UNAVAILABLE. Tests and
non-Python files are excluded from the retrieval corpus, so their gold locations
remain in file-recall denominators but cannot be retrieved by this baseline.

Retrieval receives only issue text, repo, base commit and snapshot graph/embedding
inputs. Gold is passed only to metrics after retrieval. Raw response code and query
strings never enter exported results. Unmapped graph symbols become UNRESOLVED;
mapping uses unique snapshot AST module/scope names, never gold to disambiguate.

Frozen methods: T1 top 10 from the official query tool; T2 top hit then its first
10 neighbors, second hit then its first 10 neighbors, then remaining T1 hits
(stable deduplication, official neighbor order). A fourth call characterizes the
induced subgraph of the first two hits without changing ranking. L is casefolded
identifier token hit density over snapshot modules/scopes; ties by symbol name.
L+T1 is reciprocal-rank fusion with fixed constant 60 and equal weights.
No parameter selection from gold. Method CPU and actual tool response character
counts/timings are retained; raw responses are discarded. Source indexing CPU is
reported separately. CPU time excludes child startup; wall timings accompany calls.

`study.jsonl` records metrics and ranked NAMES only, incrementally. summary.json
reports per repo, overall, and the six supplied diagnosis examples, with explicit
UNAVAILABLE counts. File Recall@1/3/5/10 deduplicates ranked files; function
Recall@5/10 uses known (file,qualified-scope) pairs, including known scopes within
PARTIAL gold records. MRR is first correct file rank. A null function metric has
no known gold function denominator; it is not counted as zero. Unmapped entries
consume a rank. Error returns remain explicitly marked PARTIAL_UNAVAILABLE and
must not be interpreted as valid zero-retrieval evidence. hashes.json pins outputs.

**Holdout limitation:** this explicitly requested all-129 localization study uses
confirm-20 as diagnostic data too. It is no longer untouched localization evaluation
data. Claims of generalization require a separate untouched set. HTTPX n=1 is
anecdotal. These are retrieval metrics, not agent task-success or correctness claims.

### P2 experimental package and dev-16v

P2 preserves P1b model, sampling and 180/28/6/80 budgets exactly. Only agent.yaml
(three registered tools added) and prompts/system.md (Localization section appended)
change. Four graph calls share the original 28 calls; the early-edit deadline and
finish reserve are unchanged. No graph-tool requirement was added to P1b/P1c.

From repository root, existing uv environment, no credentials/environment overrides:

```powershell
uv run --locked --offline --no-sync python -B -m unittest discover -s experiments/gemma4_competition/local_eval -p 'test_*.py'
if ($LASTEXITCODE -ne 0) { throw 'P2 localization controls failed' }
uv run --locked --offline --no-sync python -B experiments/gemma4_competition/local_eval/experimental.py p2 --output 'C:\Work\Gemma4Localtest\gemma-p2-experiment'
if ($LASTEXITCODE -ne 0) { throw 'P2 experimental packaging failed' }
```

Expected: tests OK; packaging prints EXPERIMENTAL_UNQUALIFIED, ZIP size/SHA256 and
manifest SHA256, submission_authorized false. Output directory must be fresh.

For GPU comparison, make a **separate tooling dataset without
evidence/gold-locations.json or its .sha256**. Do not attach the CPU study dataset
or any gold-location output. The GPU worker refuses tooling containing that JSON.
Attach the unchanged official GPU inputs plus P2 submission.zip.bin and manifest.
Use local_eval.ipynb with candidate `p2`, subset `dev-16v`, package_mode
`EXPERIMENTAL_UNQUALIFIED`, experimental_authorized true; paste the generated
ZIP/manifest hashes and set fresh output containing `dev-16v`. Exact approval:
`AUTHORIZE FORGEAI GEMMA4 LOCAL EVAL p2 ON dev-16v`.
Follow the existing GPU confirmation and official-cell setup instructions below.
Compare against P1b under frozen controls; apply the existing bootstrap 11 h gate.
No submission, compile/reconciliation qualification or new model admission follows.

## FORGEAI-GEMMA4-FAILURE-LOCATION-DIAGNOSIS-1

Authored, NOT RUN. Gold location metadata is evaluation-only privileged evidence.
Never attach it to a GPU/agent notebook, prompt, tool input, skill or retrieval
index. Keep raw task data, reference/test patches and snapshot code inside Kaggle.
No reference files have been read or exported by the coding agent in this slice.

### CPU export (competition data only)

1. After offline tests pass, create/import `gold_location_export.ipynb` in a fresh
   Kaggle notebook. Settings: Accelerator **None**, Internet **Off**. Attach only
   the public competition data at `/kaggle/input/competitions/gemma-4-developer-agent`.
   The notebook embeds the reviewed standard-library source; no tooling dataset,
   wheelhouse, model, install, official evaluation, or repository execution required.
2. Set CPU_CONFIRMED and INTERNET_OFF_CONFIRMED to True. Set AUTHORIZATION_INPUT:
   `AUTHORIZE FORGEAI GEMMA4 GOLD LOCATION METADATA EXPORT CPU`.
3. Execute the single code cell. It reads reference patch LOCATION data in memory,
   never accesses test_patch for extraction, and parses snapshot Python with AST
   without importing/executing it. Archives are read in place, not extracted.
4. Download only gold-locations.json and gold-locations.sha256. Retain printed
   GOLD_LOCATIONS_SHA256 independently. Review the metadata schema before any
   decision to commit the JSON; this task creates no actual export or commit.

The metadata contains 129 task IDs/repos, non-test gold file paths, qualified
deepest enclosing AST function/class names with pre-change source spans, hunk and
added+deleted line counts, and resolution status. No source/diff/issue/test text.
Insertion-only changes use an old-line anchor; new functions, module-level changes,
syntax errors, unsupported diffs or unavailable snapshots are UNRESOLVED/PARTIAL.
Exact task inventory SHA256 binds the export to the evaluation input.

Snapshot filename precedence follows pinned swegemma 0.2.11
`deduplication.py:1311–1377`: fallback, base+delta, then standalone .tgz/.tar.gz;
repo normalization is at lines 25–45. HARNESS_README §4.2 documents deduplicated
snapshots. Only exact-context textual deltas are reconstructed in memory.
Binary/ambiguous delta layouts stay unresolved; no shell/git application or
silent fallback to the wrong snapshot is used. Metadata-only errors replace raw
exceptions to prevent source snippets appearing in notebook output.

### Offline comparison

Use retained run folders and the original attempt1 folder for inherited P1b
patches. Add `--attempt` for every earlier ancestor if there are multiple resumes.
Paths below requiring new run/export locations are entered by the maintainer:

```powershell
uv run --locked --offline --no-sync python -B -m unittest discover -s experiments/gemma4_competition/local_eval -p 'test_*.py'
if ($LASTEXITCODE -ne 0) { throw 'Location diagnosis controls failed' }
$gold = Read-Host 'Absolute path to reviewed gold-locations.json FILE'
$goldSha = Read-Host 'Exact printed GOLD_LOCATIONS_SHA256'
$p1b = Read-Host 'Absolute path to completed merged P1b run DIRECTORY'
$p1c = Read-Host 'Absolute path to completed P1c run DIRECTORY'
uv run --locked --offline --no-sync python -B experiments/gemma4_competition/local_eval/location_review.py --gold $gold --gold-sha256 $goldSha --controls experiments/gemma4_competition/local_eval/evidence/controls-05706c6a.json --run 'P1=C:\Work\Gemma4Localtest\local-eval-p1-dev30\forgeai-local-eval-p1-dev30-attempt1' --run "P1b=$p1b" --run "P1c=$p1c" --attempt 'C:\Work\Gemma4Localtest\local-eval-p1b-dev16v\forgeai-local-eval-p1b-dev-16v-attempt1' --output 'C:\Work\Gemma4Localtest\gemma-location-review'
if ($LASTEXITCODE -ne 0) { throw 'Location comparison failed' }
```

Expected external outputs: locations.json with file/function hit/miss, extra files,
patch SHA256, reasons and per-run category counts; locations.md with per-task ×
run categories. Only VERIFIABLE controls receive verdicts. Missing patches/results
and incomplete or environment-error outcomes are OTHER, never inferred NO_EDIT.

Classification precedence for unresolved rows: TOOL_CALL_FORMAT_FAILURE ->
TOOL_FORMAT/OTHER; zero retained patch bytes -> NO_EDIT; no gold-file overlap ->
WRONG_LOCATION; overlapping known gold function span -> RIGHT_LOCATION_WRONG_FIX;
complete known gold locations but no scope overlap -> WRONG_LOCATION. Uncertain
scope evidence -> TOOL_FORMAT/OTHER. Resolved rows remain RESOLVED and are not
counted as unresolved failures. No new scorer or test execution is involved.

Important limits: agent patch alone does not contain the full original AST.
`agent_functions` therefore names only exported scopes intersecting agent old-line
changes, and explicitly marks other scopes UNRESOLVED. It does not invent qualified
names from hunk heading text. Location overlap is a diagnostic heuristic, not proof
that an alternative valid fix could not touch another location. A source edit later
reverted may yield NO_EDIT; this means no retained patch, not no editing activity.
Counts cannot establish causal benefit or select a new method until reviewed.
No candidate, agent runtime, production code or historical result was changed.


## FORGEAI-GEMMA4-LOCAL-EVAL-CONTINUE-AND-RESUME-1

NOT RUN. `runtime.py` previously stopped on every unexpected experimental
`result.error`. Official swegemma 0.2.11 `harness/agent_runner.py:965–970,
1026–1046, 1078–1100` distinguishes budget exhaustion and returning without
submission from exceptions. A returned no-patch outcome is not a failed load.
The broad guard is removed. Completed evaluator results continue; recognized
load/compile/server failures stop, as do escaping evaluator exceptions. The
bounded fatal-error recognizer covers retained textual errors; unfamiliar provider
error wording may require a further narrow classifier update. Raw errors remain
in external official evidence, never promoted to authority.

Nudge exhaustion/malformed tool text produces TOOL_CALL_FORMAT_FAILURE; empty
patches produce NO_PATCH. Known agent outcomes clear only the prior generic
HARNESS_ERROR_DETAILS_IN_EXTERNAL_LOG label, preserving independent environment
errors. A passing official verification is not changed into failure merely because
an earlier malformed tool call occurred. Analysis includes these failure counts.

Static retained evidence review: `fastapi_14419` emitted malformed read_file text
in its official log and has a complete false result, zero patch bytes, and no
successful submission. Derived verdict: UNRESOLVED (TOOL_CALL_FORMAT_FAILURE,
NO_PATCH). Source hashes and disposition are in
`evidence/p1b-attempt1-disposition.json`; no original bytes or completion state
were changed. The earlier attempt remains historically HARNESS_ERROR because of
our runtime guard. That completed task is NOT retried by resume. A genuinely
interrupted task (no complete result, or escaping exception) IS retried.

### Maintainer offline preparation

From repository root, first run tests; then prepare an external resume manifest
and derived reclassified rows (no model/verification calls):

```powershell
uv run --locked --offline --no-sync python -B -m unittest discover -s experiments/gemma4_competition/local_eval -p 'test_*.py'
if ($LASTEXITCODE -ne 0) { throw 'Continue/resume controls failed' }
uv run --locked --offline --no-sync python -B experiments/gemma4_competition/local_eval/continuation.py 'C:\Work\Gemma4Localtest\local-eval-p1b-dev16v\forgeai-local-eval-p1b-dev-16v-attempt1' --config 'C:\Work\Gemma4Localtest\local-eval-p1b-dev16v\local-eval-config.json' --output 'C:\Work\Gemma4Localtest\p1b-resume-preparation'
if ($LASTEXITCODE -ne 0) { throw 'P1b resume preparation failed' }
```

Expected derived fastapi_14419 categories as above. Manifest pins run.json,
original config, tasks.jsonl, completion.json and all classification-bearing
official agent/verification logs. The original results/config remain external.
Truncated final JSONL rows are not completed evidence. Duplicate task IDs refuse.

### Separately authorized new GPU attempt

Attach the unchanged prior attempt folder, original config and generated manifest
privately alongside the existing inputs. Update tooling, retain the same P1b
package, dev-16v and runtime pins. Fill the notebook's visible fields:

- resume_manifest: mounted resume-manifest.json.
- resume_manifest_sha256: printed RESUME_MANIFEST_SHA256.
- resume_previous: mounted prior attempt folder.
- resume_previous_config: mounted original local-eval-config.json.
- output: a fresh candidate/subset attempt directory; never the previous directory.

Keep the existing exact candidate/subset authorization, GPU/Internet/install
gates. Resume is refused on candidate/subset/package/manifest/runtime/source/model/
task identity changes. Mutable dataset paths may differ, but underlying pins may
not. New attempts copy their config into output/config.json. `tasks.jsonl` is the
merged per-task view, with attempt_id and inherited_from_run_sha256; old traces
remain in the referenced prior folder. Complete failures are retained, not retried.
Only missing/incomplete tasks run. No historical result is overwritten.

Merged time-fit includes previous plus new startup seconds conservatively;
timings span multiple attempts and are not a single uninterrupted benchmark.
Resume does not waive the time-fit gate or authorize submission. Preserve the
entire attempt chain. Stop for maintainer results; no execution performed here.

## FORGEAI-GEMMA4-P1-DEV30-REVIEW-1

Maintainer reports P1 dev-30 completed in 2.45h: control-filtered 8/16
(FastAPI 5/8, Rich 3/8; repo macro 0.5). This is not independently recomputed
here. Config/run metadata, not the former smoke5 directory name, identifies the
subset. Mean task time 277s implies 116*277/3600 = 8.93h before startup;
this is not the p95 time-fit gate or a guarantee. No comparison improvement claim.

Exact manual summary (repository root; no execution by coding agent):

```powershell
uv run --locked --offline --no-sync python -B experiments/gemma4_competition/local_eval/analysis.py summary 'C:\Work\Gemma4Localtest\local-eval-p1-dev30\forgeai-local-eval-p1-dev30-attempt1' --controls experiments/gemma4_competition/local_eval/evidence/controls-05706c6a.json --controls-sha256 05706c6a948a67bfaf991ed0282d11308aac79865a614a68c6c582fe01f67033
if ($LASTEXITCODE -ne 0) { throw 'P1 dev-30 controlled summary failed' }
```

Trace review reads only selected retained agent traces, never test/reference
patches. It writes exclusively to a new external output file. Tool response text
may contain repository data: do not commit reports. Missing timings/tokens/status
remain null. Timestamp deltas are explicitly model-plus-overhead and tool-observation
intervals, not measured inference latency. First edit is an observed attempt, not
proof of successful mutation. Arbitrary shell/Python edits cannot be reliably
inferred. Last recorded git status is not assumed to describe the final workspace.

```powershell
uv run --locked --offline --no-sync python -B experiments/gemma4_competition/local_eval/trace_review.py 'C:\Work\Gemma4Localtest\local-eval-p1-dev30\forgeai-local-eval-p1-dev30-attempt1' rich_3454 requests_7315 rich_4070 rich_3934 rich_3471 rich_4076 fastapi_15589 rich_4075 fastapi_15800 rich_4079 fastapi_11194 --output 'C:\Work\Gemma4Localtest\p1-dev30-trace-review.json'
if ($LASTEXITCODE -ne 0) { throw 'P1 trace review failed' }
```

`dev-16v.json` is a separate derived frozen subset, preserving original dev-30
order, with eight FastAPI and eight Rich tasks; original subsets.json is unchanged.
Its raw SHA256 is `5a91f0513a3cdddea3eb7a2a3f5208ebdd40a5ab41821f29f6a31a4f07585056`.
It records both parent and frozen controls hashes. Future GPU configuration:
subset `dev-16v`, subset_file `TOOLS / 'dev-16v.json'`, subset_sha256 as above,
output directory containing `dev-16v`, authorization ending `ON dev-16v`.
Attach the complete tooling directory including evidence/controls-05706c6a.json.
This is a selected development population, not all-repository generalization;
confirm-20 remains held out. No GPU execution is authorized by these edits.

Reproducibility: maintainer reports second controls hash f0a2d0ed… matches
05706c6a… in class and GOLD/EMPTY outcomes for **50/50** tasks. Timing/byte equality
is not claimed; the first controls remain authoritative. See the full hashes below.

Tests added for derived selection/pins, repeated submit responses, timing unknowns,
edit attempts and last recorded status. Run the existing `test_*.py` discovery
command below and paste results. Verification NOT RUN.

## FORGEAI-GEMMA4-LOCAL-EVAL-FIDELITY-1

### Reproducibility observation and visible CPU mode

Maintainer reports a second completed CPU control run with raw SHA256
`f0a2d0edd1e6885e993918c13d0532c93629084073ed3cb34d7507f1f2a4b871`:
all 50 task classes and GOLD/EMPTY outcomes match the first run. This is reported
outcome reproducibility, not byte identity (timings/provenance may differ), nor
verification fidelity. The frozen set remains **05706c6a**. The second run was
plain controls; it produced no import-origin evidence. Its bytes have not been
independently inspected in this change.

`controls.ipynb` now exposes MODE explicitly. Select exactly one and use its exact
AUTHORIZATION; all CPU, Internet-Off and official-install approval gates remain:

| MODE | AUTHORIZATION | Worker/output |
|---|---|---|
| `controls` | `AUTHORIZE FORGEAI GEMMA4 LOCAL EVAL CONTROLS ON dev-30+confirm-20 CPU` | controls.py; controls.json |
| `diagnostics` | `AUTHORIZE FORGEAI GEMMA4 CPU FIDELITY DIAGNOSTIC` | fidelity.py; excluded-task import-origin and redacted-tail records |
| `reverify` | `AUTHORIZE FORGEAI GEMMA4 CPU FIDELITY REVERIFY` | fidelity.py; retained agent-patch verification results |

For the next diagnostic attempt set `MODE = 'diagnostics'`, set CONTROLS_FILE to
the attached **05706c6a** controls file, and choose a fresh FIDELITY_OUTPUT directory
directly under `/kaggle/working`. No previous-run/patch input is needed in this mode.
The notebook prints the selected mode and worker before launching. Expect
`*.diagnostic.json` with `import_origin` plus `*.result.json`, provenance.json and
environment.json. A failed/timed-out worker may produce only a result error;
do not interpret missing import records as proof of import correctness.
For reverify also configure PREVIOUS_RUN and PATCHES as described below.
Do not manually replace the notebook launch command anymore: MODE chooses it.
All diagnostic/reverification outputs remain external to Git.

The GPU notebook refuses output directory names missing the exact configured
subset string. For `smoke-5`, use e.g. `p1-smoke-5-attempt1`, not `p1-smoke5-attempt1`.
Historical output directories are unchanged.

Status: authored, NOT RUN. Historical CPU controls are preserved byte-for-byte in
`evidence/controls-05706c6a.json`, SHA256
`05706c6a948a67bfaf991ed0282d11308aac79865a614a68c6c582fe01f67033`.
No Git commit was performed. These classes describe the observed subprocess
environment, not intrinsic task quality or organizer verification parity.

| Subset | VERIFIABLE | ENV_BROKEN | UNSOUND |
|---|---:|---:|---:|
| dev-30 | 16 | 2 | 12 |
| confirm-20 | 8 | 5 | 7 |

Applied to the previously retained P1 smoke observations, only fastapi_14492 is
VERIFIABLE: 1/1, repo-macro 1.0 over FastAPI alone. Exclusions: three UNSOUND
(requests_6644, rich_3130, httpx_3672) and one ENV_BROKEN (fastapi_12942).
The requests pass is excluded. This is a manual evidence join, not a newly run
analysis or new model-quality claim. Confirmation controls must not guide tuning.

### Static fidelity findings

- HARNESS_README §§4.1–4.2, 8.2 describes setup and separate verification;
  starter cell 10 selects subprocess, not Docker.
- Pinned swegemma 0.2.11 `harness/verification.py:384–424` invokes editable setup,
  test-dependency setup (fast-path default), and workspace test configuration.
  Our controls invoke that same verifier. `container_setup.py:506–530` explicitly
  skips both install functions for SubprocessManager; `531–556` invokes setup.py
  only after that return. This is an official backend difference, not a locally
  omitted verifier call.
- `sandbox/subprocess.py:389–399, 418–498` exposes host site-packages and sets
  PYTHONPATH to the workspace root. `adk_eval_core/sandbox/subprocess_sandbox.py`
  provides subprocess command execution; the swegemma manager chooses these paths.
- Exported `sandbox/setup.py:290–320` adds workspace and child directories to
  workspace_paths.pth; `352–361` calls editable installation before fast-path.
  Its SHA256 remains in dependency-source-pins.json. Blindly invoking that script
  would add an install and would not match the official subprocess path.

Thus src-layout imports from installed copies are a supported hypothesis, NOT
an observed origin. No import-path override or installation is added. Exact Docker
parity cannot be established under the current no-install/no-Docker constraints.
The diagnostic records actual sandbox module.__file__ before teardown.

Requests ~100s durations alone do not prove network access/timeouts. Whether the
particular failing tests require network is UNKNOWN without their diagnostics;
no reference tests were read to reconstruct failures. Rich/FastAPI gold failure
causes likewise remain UNKNOWN. Organizer gold-pass curation was supplied by the
maintainer; these local failures do not invalidate that claim or condemn tasks.

### Future CPU diagnostics and retained-patch re-verification

Use the existing CPU notebook settings/inputs and authorization gates below.
Attach historical controls as metadata. Do not run this during development.
Create an external JSON configuration using the same CPU controls fields
(`authorization`, CPU/Internet confirmations, official_environment_authorized,
wheelhouse, data), plus:

```json
{
  "operation": "DIAGNOSTIC",
  "fidelity_authorization": "AUTHORIZE FORGEAI GEMMA4 CPU FIDELITY DIAGNOSTIC",
  "controls": "/kaggle/input/YOUR-CONTROLS/controls.json",
  "fidelity_output": "/kaggle/working/fidelity-diagnostic"
}
```

Merge these keys with the existing config, not a standalone replacement. In the
CPU notebook worker launch, replace `controls.py` with `fidelity.py` and pass this
config path. Official cell 2 runs once; no cell 8, candidate, model, or GPU.
Only historical UNSOUND/ENV_BROKEN tasks run GOLD. Each receives the existing
900s watchdog; the sequence has an 11h verification guard. Fresh output required.

For retained agent patches use operation REVERIFY and authorization
`AUTHORIZE FORGEAI GEMMA4 CPU FIDELITY REVERIFY`. Attach the previous run privately;
add `previous_run` (its mounted root) and `patches`, an explicit task-ID mapping:

```json
{"patches": {"fastapi_14492": {"path": "relative/path/to/retained-agent.patch", "sha256": "EXACT_RAW_PATCH_SHA256"}}}
```

Choose actual retained patch paths; no guessed filenames, gold fallback, model
invocation or changed historical records. Patch bytes and containment are checked
before installation. Re-verification uses the current unchanged official verifier;
it does NOT claim the fidelity problem is fixed. New per-task results are separate.

Diagnostics retain module origin and a conservative projection of the last 60
gold-output lines: error types only, with arbitrary text/source redacted. Reference
and test patch lines are explicitly suppressed. This sacrifices detailed assertion
messages to avoid retaining gold; no raw output is written. Origin probing is an
additional observation before teardown and may affect diagnostic timings.
No diagnostic files may be committed. Preserve provenance/environment/results
externally; do not download temporary sandbox contents.

Manual offline checks (repository root, existing uv environment):

```powershell
uv run --locked --offline --no-sync python -B -m unittest discover -s experiments/gemma4_competition/local_eval -p 'test_*.py'
if ($LASTEXITCODE -ne 0) { throw 'Local evaluation fidelity controls failed' }
uv run --locked --offline --no-sync python -B experiments/gemma4_competition/local_eval/analysis.py summary 'C:\Work\Gemma4Localtest\local-eval-p1-smoke5\forgeai-local-eval-p1-smoke5-attempt1' --controls experiments/gemma4_competition/local_eval/evidence/controls-05706c6a.json --controls-sha256 05706c6a948a67bfaf991ed0282d11308aac79865a614a68c6c582fe01f67033
if ($LASTEXITCODE -ne 0) { throw 'Historical smoke analysis failed' }
```

Expected: tests pass; one eligible resolved smoke task, three UNSOUND and one
ENV_BROKEN excluded. STOP for maintainer results before any Kaggle execution.

## FORGEAI-GEMMA4-LOCAL-EVAL-CONTROLS-1

Status: authored; **NOT RUN — awaiting maintainer execution**. This section
supersedes the dependency-repair proposal and unqualified scorable-rate reporting
below. Maintainer decision: no additional installs or repairs; exclude tasks that
cannot be verified in the official environment. Candidates and historical attempts
remain unchanged. No controls results or controls.json are fabricated in Git.

### CPU control contract

`controls.ipynb` / `controls.py` run GOLD and EMPTY once each for all 30 development
and 20 disjoint confirmation IDs, in frozen order. GOLD supplies `Task.patch` as
`agent_patch`; EMPTY supplies an empty string. Both call official
`swegemma.harness.verification.verify_task` directly, not an agent/Evaluator loop.
Every call gets a new subprocess manager and fresh official verification workspace.
There are no model, serving, compilation, training or submission calls.
FORGEAI-GEMMA4-LOCAL-EVAL-CONTROLS-ENVIRONMENT-1 adds only the unchanged official
starter cell 2 installation, executed once in the controls process before verification.
The shared `runtime.install_official_environment` verifies `official-cells.json`
against the pinned starter and cell hashes. It never executes cell 8. The official
cell may install serving distributions, but no serving process or model is started.
No task-specific dependency repair or other installation is permitted.

Pinned source contracts:

- `swegemma/models/task.py:116–129`: `Task.patch` is gold; `test_patch` is verifier
  input. Read only inside the future Kaggle worker, never by the coding agent.
- `swegemma/evaluate.py:271–273, 359–377`: public snapshot resolver and verifier
  call signature reused; no secret-hydration fallback is used.
- `swegemma/harness/verification.py:345–358, 384–427, 435–462, 628–719`: fresh
  verification setup, protected-path filtering, patch application, official pytest
  and JUnit predicates, finally/cleanup. GOLD uses the same protected-file filtering
  as candidates; a filtered gold patch is not silently repaired.
- `swegemma/config.py:88–119`: subprocess EvalConfig, 300s command and verification
  limits; `models=None` is unused because no agent call is made.
- Starter cell 10 and HARNESS_README §§4, 8.2: the existing public subprocess
  verification path. Dependency-install skips remain unchanged. No Docker parity
  is claimed; only official starter cell 2 provisions the common environment.

Each GOLD/EMPTY worker is limited to 900s including imports/setup/teardown;
the whole run is limited to 11h plus cleanup grace. No retries/resume or task
replacement. Incomplete attempts remain INCOMPLETE and cannot qualify a task list.
CPU time is UNMEASURED; 100 verification calls with 300s pytest limits alone could
consume 8h20m, excluding setup. The total guard may stop the run before all 50 pairs.

Reference patches exist only in worker memory and temporary official verifier
scratch under `/tmp`, which is removed after the worker. Official verifier needs
temporary patch files to apply GOLD. They are never copied to retained outputs.
Worker stdout/stderr go to the null device; exceptions are reduced to bounded
categories, and no official result/trace writer is called. No task/test/issue text
is included in the output. A quota kill can prevent cleanup: do not download `/tmp`
or arbitrary session files, and end the disposable session. Process ancestry
cleanup has the same non-cgroup limitation documented for the agent harness.

`controls.json` contains fixed provenance hashes, runtime versions, backend,
verification timeout and task rows: ID, repo, class, GOLD/EMPTY boolean/category/
duration. The final raw-file SHA256 is printed as `CONTROLS_SHA256`; retain it
independently and provide it when analyzing. Only this reviewed metadata evidence
file may later be committed, not patches, tasks.jsonl, logs or executed notebooks.

| Control observations | Class |
|---|---|
| GOLD passes; EMPTY fails with a test or own-API verdict | VERIFIABLE |
| GOLD has a third-party import environment error; EMPTY does not pass | ENV_BROKEN |
| EMPTY passes, or GOLD otherwise fails | UNSOUND |
| GOLD passes but EMPTY times out/has environment or execution error | UNSOUND (cannot establish a meaningful failing baseline) |

Timeouts, missing public specs and control execution errors are bounded categories,
not invented missing-dependency diagnoses. Control metadata for confirm-20 is an
environment/soundness screen only; it does not authorize candidate tuning on that
holdout. The reference patch is never exposed to an agent.

### Maintainer steps

1. Run offline fixture controls from repository root in the existing uv environment:

   ```powershell
   uv run --locked --offline --no-sync python -B -m unittest discover -s experiments/gemma4_competition/local_eval -p 'test_*.py'
   if ($LASTEXITCODE -ne 0) { throw 'Local evaluation CPU control tests failed' }
   ```

   Existing descriptive-statistics tests remain, now explicitly testing raw
   observations. New tests cover gold/empty classification, third-party vs own-API
   errors, exclusions, pin/schema/task coverage, no approval effects and no gold
   in projected output. STOP and paste results before notebook execution.

2. Open the official starter in Kaggle and click **Copy & Edit**. Before running
   any cell, open notebook settings and select **Accelerator: None**, **Internet: Off**.
   Use **Add Input** to attach the competition public data, official wheelhouse
   (`/kaggle/input/datasets/metric/gemma-4-developer-agent-wheelhouse`), and your
   updated complete `local_eval/` tooling dataset, including `official-cells.json`
   and `source-pins.json`. Remove any model/candidate inputs inherited from the starter.
   Replace the starter cells with the cells from `controls.ipynb`; do not Run All
   with starter cells still present. The controls worker, not a manually executed
   starter cell, performs the pinned cell 2 installation. Never run cells 8/10.
   If the official installation or pinned metadata/source checks fail, preserve
   `environment.json` and stop; do not add installs or substitute dependencies.

3. Set TOOLS to the attached tooling directory, both CPU/Internet confirmations
   to true, and `OFFICIAL_ENVIRONMENT_AUTHORIZED = True` after reviewing the
   official cell 2 effects. Set AUTHORIZATION to:

   ```text
   AUTHORIZE FORGEAI GEMMA4 LOCAL EVAL CONTROLS ON dev-30+confirm-20 CPU
   ```

   Execute the controls cells only. Outputs are fresh `/kaggle/working/controls.json`
   and `/kaggle/working/environment.json`; existing evidence causes refusal before
   installation. The latter records starter/cell hashes, pre/post package versions,
   installation duration and state, as in GPU runs. Its cell-hash map identifies
   the pinned starter sources; it does not indicate cell 8 execution.
   Download both files, retain the printed controls digest, and review them.
   Keep environment evidence outside Git; only reviewed controls metadata may be committed.
   No automatic commits or submissions.

4. Analyze the retained smoke run with completed controls and its independently
   retained SHA256 (replace both placeholders):

   ```powershell
   $controlsFile = 'C:\Work\Gemma4Localtest\YOUR-CONTROLS\controls.json'
   $controlsSha = 'PASTE_PRINTED_CONTROLS_SHA256'
   uv run --locked --offline --no-sync python -B experiments/gemma4_competition/local_eval/analysis.py summary 'C:\Work\Gemma4Localtest\local-eval-p1-smoke5\forgeai-local-eval-p1-smoke5-attempt1' --controls $controlsFile --controls-sha256 $controlsSha
   if ($LASTEXITCODE -ne 0) { throw 'Control-qualified summary failed' }
   ```

All 50 task IDs, raw control hash, subset/data/source pins, runtime versions,
backend, timeout and bounded metadata schema must match. These pins are not a
claim that every unpinned CPU/GPU host package is identical. Environment changes
require new controls; do not merge outputs across different provisioning baselines.
Only VERIFIABLE tasks enter agent pass rates, repo-macro and paired sign tests.
Excluded counts are reported per class; repositories with no eligible tasks are
explicitly omitted from macro averaging. Runs with unknown eligible outcomes do
not get a complete pass rate. All observed task times remain in time projections
to avoid artificially improving throughput by dropping slow excluded tasks.

### Corrected retained smoke interpretation (static log review, not a run)

| Task | Retained verifier evidence | Descriptive classification |
|---|---|---|
| requests_6644 | Previously supplied resolved=true | Passed observation |
| fastapi_14492 | Previously supplied resolved=true | Passed observation |
| rich_3130 | Previously supplied verification failed | Unresolved observation |
| httpx_3672 | `AttributeError: module 'httpx' has no attribute 'Stream'` | UNRESOLVED_INCOMPLETE_API; agent-side API failure, not a third-party dependency failure |
| fastapi_12942 | `ModuleNotFoundError: No module named 'dirty_equals'` | HARNESS_ENVIRONMENT_ERROR |

The two logs were read from the external retained `official/test_outputs/`
directory; no historical file was rewritten. The derived HTTPX row removes the
generic VERIFICATION_ERROR_OR_INCOMPLETE flag while preserving its false official
verdict. FastAPI retains official_resolved=false but resolved=null. Ambiguous
errors remain unknown; no raw traceback, missing attribute name or patch is placed
in controls.json. The failing module named in an import exception drives ownership,
not the mere presence of repository frames earlier in the traceback.

Corrected descriptive totals: 2 passes, 2 unresolved, 1 environment error; all five
submitted, zero recorded call-budget stops. Previous supplied projections remain
7.238h mean / 9.444h p95, INCONCLUSIVE. **No control-qualified rate is available yet.**
Without --controls, summary emits CONTROLS_REQUIRED, all five UNASSESSED, and null
agent pass/macro rates; raw observations are under
`descriptive_observations_not_control_qualified`. The earlier 2/4=50% describes raw
non-environment observations only and is not a control-qualified result. Do not
fabricate VERIFIABLE classifications before running GOLD/EMPTY.

## Dependency investigation: FORGEAI-GEMMA4-LOCAL-EVAL-DEPENDENCY-FIX-1

Status: classification/summary implemented; **provisioning correction blocked by
missing dependency evidence after public setup inspection**. No tests or workloads
run by the coding agent.

### Export inspection, 2026-10-22

The maintainer supplied four text files under external
`C:\Work\Gemma4Localtest\competition-infra`. Exact raw-byte SHA256 and sizes are recorded in
`dependency-source-pins.json`; source files remain outside Git. Provenance is the
maintainer-reported CPU/Internet-Off export of the public competition input;
dataset version and exact export timestamp were not supplied.

- `sandbox/setup.py:290–320, 355–361`: fast path adds workspace paths and configures
  test discovery; it does not install missing test wheels. It assumes pre-baked
  dependencies (or the harness's Docker wheel injection).
- `sandbox/setup.py:114–119, 363–390`: slow path collects declared dependencies and
  installs only names present in `/wheels`. Missing names are silently omitted;
  pip runs with `check=False`. Merely invoking it does not prove readiness.
- `sandbox/setup.py:193–213, 352–353`: editable install precedes either path and
  has a fallback that omits `--no-index`; do not execute this on the serving host
  or presume it provides a safe subprocess provisioning bridge.
- `wheels-listing.txt`: no `dirty_equals`/`dirty-equals` distribution filename is
  present. A filename listing cannot rule out vendored code inside other archives,
  but establishes no independently installable wheel for this missing module.
- `docker/` export contains only `imp.py` (compatibility shim) and `telnetlib.py`;
  no Dockerfile, image digest or package installation recipe is available.

Therefore the request's `dirty_equals wheels found: <paste ...>` is an unfilled
placeholder, not evidence that the wheel exists. Wiring the supplied fast-path
script into subprocess verification would not fix the observed missing module.
The current starter-compatible evaluator remains unchanged; no official-source
patch, host installation, dependency stub or backend switch is introduced.

Smallest next evidence: the organizer's participant-accessible dependency artifact
or documented provisioning recipe that supplies `dirty_equals` (and its required
dependencies) for the public subprocess evaluator. If this is not distributed,
request organizer clarification for fastapi_12942 public verification. Do not seek
hidden evaluator data or download a substitute dependency without separate scope.
Do not spend another GPU evaluation on this unresolved environment condition.

Maintainer reports P1 smoke-5 completed with 2/5 official resolved, startup 411.5s,
mean task wall 221s. Mean projection `(411.5 + 116*221)/3600 = 7.235h` is descriptive,
not a PASS: p95 is not supplied and fastapi_12942 collection failed with missing
`dirty_equals`. Preserve that attempt; do not rerun or rewrite it automatically.

Static source findings (the pinned wheel bytes, not installed code):

| Source | Finding |
|---|---|
| HARNESS_README §§4.1–4.2, 8.2 | Docker uses swebench-sandbox:latest; agent and verification have separate lifecycles; documented setup stages wheels and installs test dependencies. |
| Starter notebook cell 10 (zero-based) | Explicit subprocess backend and `wheels_dir=DATA_DIR / 'wheels'`; our EvalConfig already matches these provisioning fields. |
| swegemma 0.2.11 `harness/container_setup.py:506–530` | Both editable package installation and test-dependency installation explicitly return for SubprocessManager/SubprocessSandbox. This is a material backend distinction from the general README setup description. |
| Same file, `21–55`, `61–86`, `318–343`, `393–413`, `531–572` | Docker path resolves public sandbox/setup.py, discovers wheels, injects cached packages and invokes official setup.py with --fast-path and repo. Wheel staging alone is not dependency installation. |
| swegemma `sandbox/subprocess.py:33–41, 328–399` | Per-task virtualenv uses system_site_packages and exposes host site-packages; this does not ensure repository test dependencies exist. |
| adk-eval-core 0.1.0 `sandbox/subprocess_sandbox.py:38–54, 57–100` | Sanitized command environment and bounded process execution, not repository dependency provisioning. |
| swegemma `results.py:39–88`; README §9.2 | Official verification output is retained under test_outputs/<instance_id>.log. |

Confirmed code gap: using the official starter's subprocess configuration skips
the Docker dependency installer. Exact cause of this run's missing module still
needs runtime/setup evidence. No ad hoc dirty_equals installation, wheel unpacking,
class-name bypass, official-package monkeypatch or Docker switch is implemented.
The public setup and wheel-listing inspection above narrows the remaining evidence
to the missing official dependency/provisioning recipe. Do not provide tasks.jsonl,
reference patches or hidden data. Running setup.py on the host has not been shown
safe or equivalent to Docker verification.

New task rows classify explicit ModuleNotFoundError plus pytest collection/conftest
loading evidence as `HARNESS_ENVIRONMENT_ERROR`, with `resolved=null` and
`official_resolved=false`. Ordinary assertion failures remain unresolved. This is
an operational environment classification, not proof of ultimate causality:
candidate-created imports can also cause collection failures and require review.
No error is converted to a pass. Analysis separates environment errors from
resolved/unresolved, reports scorable denominators explicitly, and leaves the
full-subset pass rate and time-fit gate inconclusive when outcomes are unknown.

Analyze a downloaded folder without modifying it (existing uv environment,
repository root; substitute the actual external path):

```powershell
uv run --locked --offline --no-sync python -B experiments/gemma4_competition/local_eval/analysis.py summary 'C:\Work\Gemma4Localtest\YOUR-P1-SMOKE5-OUTPUT'
if ($LASTEXITCODE -ne 0) { throw 'Local evaluation summary failed' }
```

The JSON report includes a per-task table (`per_task`), overall and repo-macro
rates, scorable rates/denominators, stop reasons, tool-call-limit hits, tool usage,
known token totals/unknown counts and mean/p95 time projections. Retained official
verification logs are consulted to derive environment classifications for old
rows in memory; historical tasks.jsonl and official results remain unchanged.
Without the retained log an old unresolved row cannot be reclassified from a
task ID or this README. Excluded repositories are explicit in scorable macro rates.

Manual controls (includes four new classification/summary tests):

```powershell
uv run --locked --offline --no-sync python -B -m unittest discover -s experiments/gemma4_competition/local_eval -p test_local_eval.py
if ($LASTEXITCODE -ne 0) { throw 'Local evaluation dependency diagnostic controls failed' }
```

STOP for results and setup artifacts before any further GPU evaluation.

## Environment update: FORGEAI-GEMMA4-LOCAL-EVAL-ENVIRONMENT-1

The notebook runs the official starter's installation
and serving source unchanged inside the existing watchdog worker, then the harness.
No extra installation is added. Existing authorization, package identity, subset,
holdout, runtime-source and wall-clock gates remain.

Official source: `docs/getting-started-gemma-4-developer-agent.ipynb`:

| Zero-based notebook cell | Code-cell ordinal | Purpose | SHA256 of joined UTF-8 source |
|---|---|---|---|
| 2 | First | Official wheelhouse installation | `c3032e216b0a393aec76180338e56f3ae5d7d995b5de9913f78b79a1fa1105af` |
| 8 | Fourth | Official VllmServer and model registry | `05c129500663d3b377f0ffec84ff7145a942e5414717f1a7733108c619c71b9a` |

`official-cells.json` preserves that source exactly. The worker authenticates both
sources and executes them in one namespace, using `exec(compile(...))`. This keeps
official source unchanged while preserving process-level timeout and cleanup and
avoiding stale notebook imports after package replacement. Do not run a second
copy manually in the notebook kernel. A bridge supplies `AGENT_DIR` (the verified
candidate) and `re`, normally set by starter cell 4. We do not run cell 4, which
copies/mutates sample agents and selects 12B. Cell 8 discovers the actual candidate
model and supplies the exact `models` and `adapters` objects used by evaluation.
The previous handwritten VllmServer configuration has been removed. Official
sample evaluation cell 10 and packaging cell 12 are not executed.

### Click-by-click maintainer setup

1. Open the official **Getting Started: Gemma 4 Developer Agent** notebook from
   the competition **Code** tab. Click **Copy & Edit**. Do not Run All.
2. In the copy choose **File > Import Notebook** and import this repository's
   `local_eval.ipynb`, replacing the example cells. If the UI lacks import, replace
   the copied cells with the local_eval cells in order. Remove original runnable
   demo/evaluation/submission cells before execution. Official cell source remains
   in the attached tooling, executed unchanged by the gated worker.
3. Set **Notebook options / Settings > Accelerator: GPU L4 x4** and **Internet: Off**.
   Use a fresh disposable session with no secrets. GPU quota includes idle time.
4. In **Input > Add Input / Add Data**, attach these five inputs:
   - Competition: **Gemma 4 Developer Agent**, public data at
     `/kaggle/input/competitions/gemma-4-developer-agent`.
   - Official dataset: **metric/gemma-4-developer-agent-wheelhouse**, at
     `/kaggle/input/datasets/metric/gemma-4-developer-agent-wheelhouse`.
   - Model: **Google Gemma 4 > other > gemma-4-31b-it-qat-w4a16-ct > version 2**,
     at `/kaggle/input/models/google/gemma-4/other/gemma-4-31b-it-qat-w4a16-ct/2`.
     Select 31B, not the starter's 12B example. A different mount/version stops.
   - Private harness tooling dataset: the whole current `local_eval/` directory,
     including `official-cells.json`, `source-pins.json`, modules and frozen subsets.
     Set `TOOLS` to its actual mounted path.
   - Private reconciled candidate package dataset: unchanged `manifest.json` and
     `submission.zip.bin`. Use `.bin` to prevent upload auto-extraction. Fill the
     trusted manifest/receipt pins from reconciliation, not a replacement manifest.
5. Review all configuration and choose smoke-5 first. Set a fresh output path,
   the exact candidate/subset authorization, existing approval flags, and the new
   **official_environment_authorized=true**. This explicitly approves the official
   whole-wheelhouse installation and cutlass `.pth` cleanup in this session only.
6. Run the configuration cell, then the launch cell. The watchdog starts before
   installation. Worker order: unchanged cell 2, installed-version/source checks,
   candidate and four-L4 checks, unchanged cell 8, frozen-subset evaluation.
   The official install cell lacks `--no-index`; the worker retains `PIP_NO_INDEX=1`
   and Kaggle Internet Off is mandatory. No other pip commands are authorized.
7. On failure, preserve evidence and stop; do not repair dependencies ad hoc or
   relax source pins. Do not rerun completed tasks automatically.
8. Download the complete output directory and stop the Kaggle session. Analyze
   externally with the existing commands. Never commit outputs or downloaded traces.

New `environment.json` records starter hash, cell hashes, pre/post-install package
versions, post-server versions, installation duration and server startup duration.
`run.json` also records the cell hashes and installation duration. A failed install
retains STARTED evidence and `worker.log`; it never fabricates a successful state.
Package/source checks occur after the official install. The GPU environment remains
unverified until maintainer execution; prior CPU compiler qualification is distinct.

The watchdog includes installation in its total limit. The established 116-task
projection remains measured server startup plus task wall times; installation is
reported separately, so it is not an all-inclusive session-time projection.
Quota/throughput remain UNMEASURED; hidden scorer parity/concurrency remain UNKNOWN.

Existing tests are retained. Added controls compare exact source to starter cells,
reject altered source, and check explicit install approval/evidence plumbing.
Run the existing unittest command and STOP for review before GPU execution.

Status: IMPLEMENTED, MAINTAINER VALIDATION PENDING. No tests, notebooks, models,
installations, evaluations, submissions or commits were executed by the coding
agent. Metadata was read and the approved frozen ID lists were authored as data.
This is public-development tooling, isolated from ForgeAI production, candidate
packages, historical evidence, pilot admissions and frozen KiSSKI evaluations.

## Frozen selection and research boundary

The maintainer supplied the external metadata-only file
`C:\Work\Gemma4Localtest\gemma4-dev-metadata\public_dev_task_metadata.jsonl`.
Its raw SHA256 is
`8c84d46169b5ca97437151a341792754c4672eafdaba5187abe3e74e3606f7e7`.
It contains 129 rows with only `instance_id`, `repo`, `base_commit`, `created_at`:
67 FastAPI, 48 Rich, 13 Requests, **1 HTTPX**. No bug/feature labels exist;
none are inferred from issue text, filenames, patches, or tests. The coding agent
did not read the official tasks.jsonl or any reference/test payload.

The approved allocation supersedes the infeasible equal-repository request:

| Subset | FastAPI | Requests | Rich | HTTPX | Purpose |
|---|---:|---:|---:|---:|---|
| `smoke-5` | 2 | 1 | 1 | 1 | Runtime/instrumentation smoke; nested in dev-30 |
| `dev-30` | 12 | 6 | 11 | 1 | Development and matched candidate comparisons |
| `confirm-20` | 8 | 4 | 8 | 0 | Disjoint held-out confirmation of a winner only |

Dev-30 gives broad FastAPI/Rich coverage while retaining six Requests tasks and
the only HTTPX task. It is intentionally not proportional to the population;
report both overall task-weighted and equal-repository macro pass rates. HTTPX
results are **anecdotal, n=1**. Confirm-20 excludes HTTPX because none remain;
its macro average covers three repositories, not four. Before choosing confirm-20,
freeze the winning candidate and the development comparison report hash. Set
`confirmation_only=true` and `winner_evidence_sha256` to that reviewed report's
SHA256. These fields record maintainer approval; they do not algorithmically prove
a winner. Never tune from confirmation results, select alternative holdouts after
seeing outcomes, or merge smoke tasks as additional independent dev observations.

`subsets.json` commits only chosen IDs, repository names, null/explicit labels,
seed/schema/inventory count and metadata source hash. `subsets.sha256` pins its
raw LF bytes:
`627f17c74f81450a5ff1787175a30ab9af7ebd9588697ef9e1bbe29367920316`.
Seed `20261021` ranks repository order and IDs by SHA256 of `seed:value`.
Selection alternates explicit bug/feature strata when supplied; here all labels
are null. Confirm selection takes the next ranked IDs after dev selections.
Smoke uses the approved quotas from the same ranked lists. No RNG-version drift,
resampling, replacement, or duplicated HTTPX task is used. The remaining
post-dev pools have 55/7/37 FastAPI/Requests/Rich tasks; confirm consumes 8/4/8.

The metadata source stays outside Git. The selection CLI rejects unexpected
columns (including patches, issue text, tests and solutions). It writes a new
file exclusively, never overwriting the committed freeze. The official tasks file
is resolved **only inside Kaggle by the official task loader/evaluator**. Selected
IDs and repos must match. The whole official task-file hash is retained in the run
record so paired comparisons reject a changed runtime dataset, without exporting
its contents. No reference patches are supplied by this tooling to model prompts.
Official public verification data goes only through the existing evaluator path.
Missing public verification data blocks execution; hidden bundles are not sought.

## Reused source contracts and limits

Source pin authority is the supplied wheel/document bytes recorded in
`source-pins.json`, including all Python members of the three harness wheels.
After the authorized official installation, runtime preflight checks installed
versions and those member bytes without further repair. The selected official wheel files are also
hash-checked in the attached wheelhouse. The new Python modules use standard
library code on the laptop; official dependencies are imported only by the
explicitly authorized GPU worker.

| Contract | Inspected authoritative location | Reuse / limitation |
|---|---|---|
| Dataset path and loading | [starter](../docs/getting-started-gemma-4-developer-agent.ipynb), code cell index 4 (zero-based notebook cells) | Official `load_tasks`, `tasks.jsonl`, snapshots/graphs/embeddings/wheels inputs |
| Serving and four permitted quantized models | starter cell 8; [HARNESS_README](../docs/HARNESS_README.md) §§3.1–3.3 | `discover_declared_models`, `discover_adapters`, `VllmConfig`, `VllmServer`, `create_model_registry`; loopback, TP=4, 32768 context, 0.90 memory, Gemma4 tool/reasoning parsers, model-specific 12B override |
| Official local evaluation | starter cell 10; README §§4, 7.1, 9.1 | `EvalConfig`, `Evaluator.evaluate_task`, subprocess backend, original candidate budgets, 300s default verification timeout, same cache/compaction settings; sequential calls |
| Verification | swegemma 0.2.11 `evaluate.py:221–391`; `harness/verification.py:618–719`; README §8.2 | Keep official resolved flag and verification behavior. Measure enclosing call, including setup and finally/teardown. No custom patch acceptance or test-score predicate |
| Timing and counters | `context.py:184–199, 388–445`; adk-eval-core 0.1.0 `tracing/trace.py:23–78, 373–431` | Agent active time, model-call count, trace tool requests by name and tokens when usage exists |
| Incremental evidence | `results.py:39–88`; README §9.2 | Official patch/test-output artifacts plus our append/flush/fsync task JSONL. Do not replace or merge original attempts |
| Protected files and fallback | README §§8.1–8.2; `tools/execution.py:76–116` | Official filtering and fallback unchanged; filtered final patches cannot prove test files were never touched |
| Runtime package preparation | starter cell 2 | Exact pinned cell executed inside the watchdog after explicit environment approval. It replaces wheelhouse packages and removes cutlass `.pth` hooks in the disposable session |

Local dependency pins: adk-submission 0.2.13, adk-eval-core 0.1.0, swegemma 0.2.11,
google-adk 1.36.1, google-genai 2.11.0, vLLM 0.19.1, transformers 5.13.1.
The broad serving environment is distinct from the previous CPU compiler-only
five-wheel install; that CPU qualification does not qualify GPU serving.
Any missing distribution, source mismatch or import failure is ENVIRONMENT_BLOCKED
or HARNESS_ERROR, not a coding-model failure. No additional package download,
installation, compatibility exception, candidate adjustment, or model fallback.

**UNKNOWN:** private scorer concurrency, hidden task count, hidden environment
overrides, full scorer/bootstrap parity, and leaderboard equivalence. Sequential
execution is a controlled local experimental choice, not a verified hidden-scorer
fact. The 116-task projection is the requested planning assumption.

The official subprocess backend uses local workspaces/venvs and path translation;
it is **not an OS security boundary** (`sandbox/subprocess.py:421–500`). We preserve
the starter's path and do not add privileged Docker or claim isolation from all
attached files. Use only a disposable public-dev session with no secrets or private
datasets. Credentials are removed from worker environment names; the local API
uses the non-secret placeholder `EMPTY`. No hidden tests are attached. The runner
refuses an ancestor `secret` directory to avoid official secret-hydration fallback
(`evaluate.py:81–177`). Internet Off is a mandatory Kaggle UI setting confirmed
by the operator; environment flags alone do not enforce network isolation.

## Recorded evidence and interpretation

`run.json`: candidate, package/manifest/receipt/subset/source hashes, task order and
repos, source/package/Python versions, candidate budgets, model input, UTC epoch,
server startup seconds and wall guard. `tasks.jsonl`: task ID/repo, official resolved
flag, enclosing wall time, active agent time, model turns, tool-name request counts
(including graph tools if declared), budget-counted calls, observed token totals,
submit requested/succeeded, captured patch bytes and changed files, stop reason,
last tool-error presence/name and harness-error category. `events.jsonl` records
task starts. Official traces, patch and verification logs remain in `official/`.

`seconds_per_model_turn = agent_seconds / model_turns` includes tool/reasoning
overhead; it is **not model-serving latency**. Tool requests are not guaranteed
successful mutations. Token totals are null when no usage metadata was observed.
Successful explicit edit_file/write_file responses can establish positive protected
test/config-file touches. Otherwise test-file touches remain UNKNOWN, never false.
Stray-file intent and wrong-location diagnosis remain UNKNOWN:
the public trace/final patch does not reliably expose every transient shell effect,
and no reference-patch comparison is permitted. Do not label a patch “wrong
location” merely because tests fail. Review external traces manually if needed;
never feed verifier/reference output back into the agent loop. `tests_fail` requires
official verification failure evidence; non-test infrastructure errors are distinct.
Stop categories use explicit harness messages; if cleared/unrecorded, use unknown,
not a guessed threshold. Last-tool error detail is retained only in the external
trace; aggregate JSONL never echoes tool arguments, code, prompts, or environment values.

The parent watchdog bounds the entire worker including imports, server startup,
setup and evaluation (after the parent's read-only input/package preflight).
It sends TERM then KILL to the worker process group with at most 10s cleanup grace.
Because adk-eval-core `sandbox/subprocess_sandbox.py:81` starts command sessions
separately, the parent also samples `/proc` descendant PID/start-tick identities
every second and terminates those tracked children, including detached sessions.
Normal completion also cleans up those processes. This is not a cgroup/security
containment guarantee: a process orphaned between samples may evade ancestry
tracking; the first smoke must verify serving cleanup, and the operator must end
the disposable Kaggle session after retaining results. No process arguments or
environment values are read by the watchdog.
A quota/kernel kill can prevent final cleanup or completion.json; preserve all
completed JSONL lines. An unterminated final line is excluded as a torn write.
A started task without a completed row is incomplete, never a fabricated failure.
There is no task retry/resume loop. Official model-invocation retry behavior, if
present in the harness, is unchanged. Review the official execution path before
comparing it to other runtimes.

Analysis reports task-weighted and repo-macro pass rates, per-repo counts,
nonexclusive no-edit/no-submit/budget-exhausted/tests-fail/harness-error counts,
unknown telemetry, and tool usage. Partial runs show lower bounds and no completed
pass-rate claim. Paired comparisons require matching subset/data/runtime pins and
complete known outcomes with no harness errors. They list B wins/losses/ties and
the exact two-sided sign test over discordant pairs. Small samples, shared-repo
dependence, stochastic runs and development-set tuning prevent causal claims from
a single p-value. P1 changes both prompt and budget versus B2; it is not a pure
prompt ablation. Keep confirm-20 out of all tuning decisions.

## Time-fit gate and GPU cost

Both projections include measured server startup:

`mean_hours = (startup_seconds + 116 * mean(task_wall_seconds)) / 3600`

`p95_hours = (startup_seconds + 116 * nearest_rank_p95(task_wall_seconds)) / 3600`

Either estimate **above 11h => FAIL**. Both at/below 11h with a complete error-free
run => PASS; missing startup, partial tasks, harness errors or incomplete process
completion => INCONCLUSIVE. This is a required development gate before every future
submission, not a submission authorization or a bound on leaderboard runtime.
Sample p95 is not a statistical confidence limit. Mean/p95 extrapolation across
non-proportional strata, especially one HTTPX task, has substantial uncertainty.

Agent-only envelopes (verification/setup/startup add time):

| Candidate | smoke-5 | dev-30 | confirm-20 |
|---|---:|---:|---:|
| M2, 1 min/task | 5 min | 30 min | 20 min |
| B2, 4 min/task | 20 min | 120 min | 80 min |
| P1, 6 min/task | 30 min | 180 min | 120 min |

Serving startup has a 20-minute timeout; verification normally has a 5-minute
per-command timeout. Thus P1 smoke planning is 30 min agent + up to 25 min of one
verification command/task + 20 min startup = 75 min **before setup/other commands**,
not a guaranteed runtime ceiling. Notebook smoke guard defaults to 2h, configurable
up to 11h; consider 8h for dev-30 only after measured smoke. These are administrative
limits, not expected measured durations. Actual runtime and throughput: UNMEASURED.
Maintainer reports L4x4 consumes GPU quota at 2x wall time; quota accounting is
not independently verified here. Estimate `2 * allocated_session_hours`, including
setup/idle; first smoke measurements must replace estimates. Stop the GPU session
after retaining evidence. For P1, 116 * 6 min = 11.6h **before** startup/verification,
so budget saturation would fail the 11h projection gate. Do not increase budgets
without measured task wall times and explicit authorization.

## Maintainer validation and operation

From repository root, existing uv environment; no GPU, extra installs or environment
variables needed for the standard-library tests:

```powershell
uv run --locked --offline --no-sync python -B -m unittest discover -s experiments/gemma4_competition/local_eval -p test_local_eval.py
if ($LASTEXITCODE -ne 0) { throw 'Local evaluation offline controls failed' }
```

The test suite checks subset pinning/allocations/disjointness/no sensitive columns,
optional exact regeneration against the external metadata, package and manifest
tampering, traversal, JSONL schemas/torn lines, projections, macro averages, paired
sign tests and inert authorization/notebook boundaries. Expected: all controls pass;
only external-metadata regeneration may skip on another machine. No official/GPU
runtime imports or evaluation occurs in these tests. **STOP and paste results.**

Optional deterministic selection reproduction, performed by the maintainer only;
write outside the repo and compare to committed subsets.json before changing any pin:

```powershell
$subsetReproduction = Join-Path $env:TEMP ('gemma-subsets-' + [guid]::NewGuid().ToString('N') + '.json')
uv run --locked --offline --no-sync python -B experiments/gemma4_competition/local_eval/analysis.py freeze 'C:\Work\Gemma4Localtest\gemma4-dev-metadata\public_dev_task_metadata.jsonl' $subsetReproduction
if ($LASTEXITCODE -ne 0) { throw 'Subset reproduction failed' }
Get-FileHash -LiteralPath $subsetReproduction -Algorithm SHA256
```

After local controls PASS, separately approve the first smoke-5 GPU run:

1. Review and privately attach the complete `local_eval/` directory, the reconciled
   candidate manifest and unchanged `submission.zip.bin`, competition public data,
   official wheelhouse, and matching permitted model. No downloaded trace or complete
   task source enters Git. Verify `manifest_sha256` and `receipt_sha256` from retained
   reconciliation evidence; a manifest claiming portable PASS alone is insufficient.
2. Follow the Copy & Edit and five-input setup above in a disposable Python 3.12
   Linux session. Explicitly approve the official installation with
   `official_environment_authorized=true`; previous CPU scoped-install approval
   does not authorize this broader operation. Keep Internet Off.
3. Import `local_eval.ipynb`, set Accelerator **L4x4**, Internet **Off**. Review the
   GPU-quota effect before enabling the accelerator. Set input paths, candidate,
   raw manifest/receipt pins, fresh output path, and flags. Use the exact phrase
   `AUTHORIZE FORGEAI GEMMA4 LOCAL EVAL p1 ON smoke-5` (replace candidate/subset
   deliberately). All approval flags default false; confirm-20 has an extra gate.
4. First code cell records config exclusively; second launches the watchdog and
   official path. Expected successful state: COMPLETED, five durable task rows,
   populated run metadata and official artifacts. Harness/environment failure or
   guard expiration stops nonzero and preserves partial evidence. Do not automatically
   repeat completed tasks. No Kaggle submission operation is included.
5. Download the entire new output directory outside the repository. Analyze:

```powershell
$localEvalResults = 'C:\Work\Gemma4Localtest\forgeai-local-eval-p1-smoke5-attempt1'
uv run --locked --offline --no-sync python -B experiments/gemma4_competition/local_eval/analysis.py analyze $localEvalResults
if ($LASTEXITCODE -ne 0) { throw 'Local evaluation analysis failed' }
# Only for separately authorized complete matched-subset runs:
uv run --locked --offline --no-sync python -B experiments/gemma4_competition/local_eval/analysis.py analyze 'C:\Work\Gemma4Localtest\run-a' --compare 'C:\Work\Gemma4Localtest\run-b'
if ($LASTEXITCODE -ne 0) { throw 'Paired local evaluation analysis failed' }
```

Retain all run/manifest/receipt/subset/package identities, runtime versions, UTC
timestamps, raw official artifacts and partial attempts externally. Commit only
deliberately reviewed metadata/hash records, never traces, patches, test outputs,
candidate binaries, notebooks downloaded after execution or full task data.
Local public-dev performance is development evidence only: no model admission,
production change, leaderboard correctness or general coding-quality qualification.

# P3 submission qualification and six-run evidence

P3 is selected for submission preparation, not yet compiler-qualified or submitted.
Maintainer-reported dev-16v successes are P1/P1b/P1c/P2/P3/P3g = 8/8/7/8/8/7.
P3 and P3g have zero observed context-window errors, with four and five session
timeouts respectively. P3g used two graph calls; P2 used one. These single runs
do not establish superiority. Raw run evidence is unchanged. The retained
metadata table preserves UNKNOWN outcomes; the offline analysis below applies
the existing structured-error projection rather than rewriting history.

The record and source hashes are in `../results/dev-16v-comparison.json`, its
Markdown table, and `../results/paper-evidence.json`. Paper values must retain
their recorded provenance: public scores and noise are maintainer-reported;
approximate mean-time projections are not the bootstrap upper-bound gate.
Gold file overlap is diagnostic and does not prove correctness.

Run from the repository root, using the existing locked environment. No command
below has been executed by the coding agent. First perform local preparation:

```powershell
uv run --locked --offline --no-sync python -B .\validate_forgeai_gemma4_p3_submission_qualification_1.py --local-only
if ($LASTEXITCODE -ne 0) { throw 'P3 local preparation failed' }
```

Expected: focused offline controls pass, an external transfer bundle is printed,
and `P3_LOCAL_SCOPE_AND_STATIC_PASS; PORTABLE COMPILATION REQUIRED`.
The four P3 candidate files and deterministic ZIP must match the retained
experimental package (`19b4e77257004e5440e23520f05e83ab755257fd6ff43c71d38539b9d62c676f`).
The shared compiler retains M2's default output expectation of 16384; the P3
instance expects 8192. This shared-source change requires a NEW P3 receipt.
Historical M2 receipts remain evidence for their historical source bytes,
not qualification of this changed checkout.

Next, import `../kaggle_compiler/p3_compiler_only.ipynb` into a fresh Kaggle CPU
session (Accelerator None, Internet Off). Attach the NEW transfer bundle and
official wheelhouse, correct BUNDLE, and use fresh output paths. After reviewing
the existing five-wheel scoped installation, set the exact authorization:
`AUTHORIZE FORGEAI GEMMA4 P3 KAGGLE CPU SCOPED INSTALL AND COMPILER ONLY`.
Run the compiler-only notebook; no model, evaluation, GPU or submission is
authorized by this operation. Download its complete results outside the repo.

```powershell
$p3Receipt = Read-Host 'Absolute path to NEW P3 local-receipt.json FILE'
$p3Results = Read-Host 'Absolute path to NEW gemma4-p3-compiler DIRECTORY'
uv run --locked --offline --no-sync python -B .\validate_forgeai_gemma4_p3_submission_qualification_1.py --receipt $p3Receipt --reconcile $p3Results
if ($LASTEXITCODE -ne 0) { throw 'P3 reconciliation failed' }
```

Only successful reconciliation may emit `P3_OFFICIAL_COMPILER_VALIDATED` and
`P3_PACKAGE_VALIDATED`. The P3 submission pins are intentionally null/false
until then. Generate the rerun-safe, self-contained notebook and materialize
only P3's pins using the shared generator:

```powershell
$p3Notebook = Join-Path $env:TEMP ('p3-self-contained-' + [guid]::NewGuid().ToString('N') + '.ipynb')
uv run --locked --offline --no-sync python -B experiments/gemma4_competition/submission_only/qualify_p3.py --receipt $p3Receipt --results $p3Results --notebook $p3Notebook
if ($LASTEXITCODE -ne 0) { throw 'P3 submission preparation failed' }
# Review and stage the slice, then:
uv run --locked --offline --no-sync python -B .\validate_forgeai_gemma4_p3_submission_qualification_1.py --pre-commit --receipt $p3Receipt --reconcile $p3Results
if ($LASTEXITCODE -ne 0) { throw 'P3 pre-commit consistency failed' }
```

Expected final label: `P3_PRE_COMMIT_STAGED_CONSISTENCY_PASSED`. The generated
notebook remains external and requires separate operator authorization before
execution/submission. No public score or model-quality qualification follows
from compiler/package validation. The results register stays NOT_SUBMITTED.

For the full derived six-run analysis, use a fresh external destination:

```powershell
uv run --locked --offline --no-sync python -B experiments/gemma4_competition/local_eval/paper_evidence.py --controls experiments/gemma4_competition/local_eval/evidence/controls-05706c6a.json --controls-sha256 05706c6a948a67bfaf991ed0282d11308aac79865a614a68c6c582fe01f67033 --run 'p1=C:\Work\Gemma4Localtest\local-eval-p1-dev30\forgeai-local-eval-p1-dev30-attempt1' --run 'p1b=C:\Work\Gemma4Localtest\local_eval_p1_dev30\p1b\forgeai-local-eval-p1b-dev-16v-attempt2' --run 'p1c=C:\Work\Gemma4Localtest\local_eval_p1_dev30\p1c\forgeai-local-eval-p1c-dev-16v-attempt1' --run 'p2=C:\Work\Gemma4Localtest\local_eval_p2_dev16v\forgeai-local-eval-p2-dev-16v-attempt1' --run 'p3=C:\Work\Gemma4Localtest\local_eval_p3\local_eval_p3_dev16v\forgeai-local-eval-p3-dev-16v-attempt1' --run 'p3g=C:\Work\Gemma4Localtest\local_eval_p3\local_eval_p3g_dev16v\forgeai-local-eval-p3g-dev-16v-attempt1' --output 'C:\Work\Gemma4Localtest\p3-six-run-review-1'
if ($LASTEXITCODE -ne 0) { throw 'Six-run analysis failed' }
```

Expected external files: `dev-16v-comparison.md` and `six-run-analysis.json`,
including per-run source hashes, control-filtered summaries and existing
bootstrap time-fit projections. Review the 11-hour upper-bound gate before
authorizing a future submission. Do not replace approximate reported projections
with an unexecuted calculation. Paste maintainer results before proceeding.

## FORGEAI-GEMMA4-P5-EDIT-PATH-WORKAROUND-1

Authored only: **NOT RUN — Awaiting user execution**. No package, analysis,
notebook, test or submission was executed. All eight historical runs stay intact.
P5 copies P3's agent.yaml, eval_config.yaml and configs/sampling.yaml byte for byte;
only prompts/system.md gains the source-edit workaround. The builder checks this
and preservation of all original P3 prompt text against pinned bytes.

Source changes use run_command with a quoted `<<'EOF'` Python heredoc, byte reads,
a nonempty old-text uniqueness assertion, actual replacement, byte write and
`git diff -- <file>`. The prompt forbids edit_file/write_file for source changes
and identical resends after missing mandatory arguments. Each completed source
file modification emits `FORGEAI_SOURCE_EDIT_COMPLETED` after the diff.

The analyzer matches the rejection phrase in tool observations, not arguments,
and reports attempted/rejected counts by tool per task, identical resends after
rejection, maximum identical rejection streak, edit/write rejection fraction,
and all-tool rejection fraction. A 27-call identical rejected streak contains
26 resends. Missing/ambiguous observations and absent traces leave rates null;
zero edit/write attempts are N/A, not 0%. Other tools remain in the all-tool gate.
Trace file hashes accompany task metrics. Retained files are read, never rewritten.

Per-task `run_command_source_edits_evidenced` counts dedicated completion-marker
lines in observed stdout (or plain output), never command text. These are lower
bounds, not full counts of arbitrary shell edits. Review unmarked commands and
patch artifacts before asserting exact counts; historical absence of markers is
not proof of zero edits. `patch_bytes` and `patch_production.share` independently
measure final nonempty patches, so editing then reverting still yields no patch.
Metric fields are under summary.descriptive_observations_not_control_qualified;
per-task provenance is under summary.per_task. No model-quality claim follows.

### Preregistered decision, incorporating maintainer refinement

Use two independent, complete P5 dev-16v runs with identical candidate bytes,
sampling, budgets, task subset, environment and source pins. Do not resume or
merge attempts, cherry-pick a replicate, or tune between attempts.

All conditions are required:

1. **Each run**: rejected observations across ALL tools / all attempted tool calls
   <=0.05. Report both rates and their arithmetic mean (not pooled). Report the
   edit/write ratio separately; N/A when no edit/write calls occurred. Missing
   traces, unmatched observations, zero total calls or incomplete tasks cannot pass.
2. **Each run**: nonempty-patch task share >= arithmetic mean of the two P3 shares
   (P3 attempt1 and attempt2). Missing patch bytes mean UNKNOWN. Even with zero
   edit/write attempts, a smaller patch share FAILS: stopped editing is not avoidance.
3. Record source edits via run_command per task, including marker counts and any
   manual adjudication for unmarked edits. Do not promote marker lower bounds to
   exact historical counts. Preserve trace hashes with the adjudication.
4. Mean solved across two P5 runs >=7 (P3 baseline 8 and 6). Unknown verdicts block
   this gate, rather than being converted to unsuccessful tasks.
5. Each P5 run's existing bootstrap upper95 full-run time projection <=11 hours
   (equivalently the maximum of the two bounds <=11). Preserve startup cost and
   the existing 116-task/10,000-draw method; no new timing method after results.

Report all 16 task outcomes for P3 attempt1, P3 attempt2, P5 attempt1 and P5
attempt2: each P5 versus each P3, and P5 versus P5 flips. Retain P3 on FAIL or
UNKNOWN. Passing creates selection eligibility only; official compiler/package
qualification, reconciliation and explicit submission authorization remain required.

### Manual offline checks and build

Prerequisites: existing locked uv environment with Python; no installation or
new environment variables. Working directory is the relocated repository
`C:\Work\ForgeAI-Gemma4`, branch br-ForgeAI-Gemma4. The earlier repository path
is absent on this machine. These are maintainer commands, not executed results.

```powershell
Set-Location 'C:\Work\ForgeAI-Gemma4'
uv run --locked --offline --no-sync python -B -m unittest discover -s experiments/gemma4_competition/local_eval -p 'test_*.py'
if ($LASTEXITCODE -ne 0) { throw 'Offline tests failed; paste output and stop' }
```

Expected: offline unit tests pass, including rejection/observation matching,
repeat interruption, zero denominator, missing evidence, marker counts, P5 prompt
scope and distinct unauthorized config defaults. Paste results before further
implementation. No test outcome is claimed here.

Separate, maintainer-controlled build, once checks are accepted:

```powershell
uv run --locked --offline --no-sync python -B experiments/gemma4_competition/local_eval/experimental.py p5 --output 'C:\Work\Gemma4Localtest\gemma-p5-experiment-attempts1-2'
if ($LASTEXITCODE -ne 0) { throw 'P5 package build failed; paste output and stop' }
```

Expected fresh external directory: submission.zip.bin, manifest.json,
p5-dev16v-attempt1.json, p5-dev16v-attempt2.json. Printed state is
EXPERIMENTAL_UNQUALIFIED with ZIP and manifest SHA256. Existing output directories
are refused. Both generated configs contain the same real build hashes; committed
config templates deliberately say BUILD_REQUIRED. This is experimental packaging,
not official portable compilation. No submission package is qualified by this build.

### Future P5 configs (not authorization to execute now)

Use the generated configs under the build output; committed templates are
`configs/p5-dev16v-attempt1.json` and `configs/p5-dev16v-attempt2.json`.
Use the existing official local-evaluation Kaggle setup, model, wheelhouse and
Internet Off. Attach current local_eval sources including tool_rejections.py,
experimental-pins.json and the unchanged dev-16v.json, plus the new package and
manifest. Adjust only mounted input paths to the actual attached locations.
Keep candidate=p5, subset=dev-16v, package_mode=EXPERIMENTAL_UNQUALIFIED,
wall_seconds=10800, all resume fields empty and separate fresh output directories.
The six-minute per-task budget remains P3's; the wall guard is not a time-fit result.

After separate operator approval, set authorization exactly to
`AUTHORIZE FORGEAI GEMMA4 LOCAL EVAL p5 ON dev-16v` and set gpu_authorized,
official_environment_authorized, internet_off_confirmed and experimental_authorized
true. package_reconciled remains false for this experimental path. Templates
remain unauthorized in git. The existing runtime positional-config interface is:

```text
python -B /actual/mounted/local_eval/runtime.py /actual/path/p5-dev16v-attempt1.json
python -B /actual/mounted/local_eval/runtime.py /actual/path/p5-dev16v-attempt2.json
```

These are separate fresh sessions, not simultaneous jobs or a command to run now.
Retain each complete output directory including run.json, tasks.jsonl,
completion.json, official/task_results.jsonl, official/traces, patches and logs.
Failures remain evidence; do not overwrite or silently retry an attempt.

### Eight-run recomputation (maintainer only)

Supply the actual run roots containing run.json, not an outer download folder.
P1b must be the established merged logical run; if inherited task traces are not
present, report missing coverage and recover their provenance separately rather
than counting absent traces as zero. No guessed path or copied trace is substituted.
Use a fresh external output directory. The eight labels are fixed below.

```powershell
Set-Location 'C:\Work\ForgeAI-Gemma4'
$gemmaRuns = @()
foreach ($gemmaLabel in @('p1','p1b','p1c','p2','p3','p3g','p3att2','p4')) {
    $gemmaRoot = Read-Host "Absolute retained run root containing run.json for $gemmaLabel"
    $gemmaRuns += @('--run', ($gemmaLabel + '=' + $gemmaRoot))
}
uv run --locked --offline --no-sync python -B experiments/gemma4_competition/local_eval/paper_evidence.py @gemmaRuns --controls experiments/gemma4_competition/local_eval/evidence/controls-05706c6a.json --controls-sha256 05706c6a948a67bfaf991ed0282d11308aac79865a614a68c6c582fe01f67033 --output 'C:\Work\Gemma4Localtest\p5-eight-run-rejection-review-1'
if ($LASTEXITCODE -ne 0) { throw 'Evidence export failed; paste output and stop' }
```

Expected dev-16v-comparison.md and eight-run-analysis.json. P1 is restricted to
P3's 16 task IDs; P1b merged attempts count once. All-tool rates, patch shares,
per-tool and per-task rejection counts and repeat counts are newly derived only
when this command succeeds. Compare the supplied historical counts 17/40, 25/48,
13/36 and 30/59; investigate discrepancies, never change code to force agreement.
Current committed comparison and paper-evidence records explicitly remain
MAINTAINER_REPORTED / RECOMPUTATION_NOT_RUN. No complete eight-run rates invented.

After both future P5 runs, use the existing summary and comparison interfaces:

```powershell
$gemmaCompare = @()
foreach ($gemmaLabel in @('P3a1','P3a2','P5a1','P5a2')) {
    $gemmaRoot = Read-Host "Absolute complete run root for $gemmaLabel"
    uv run --locked --offline --no-sync python -B experiments/gemma4_competition/local_eval/analysis.py summary $gemmaRoot --controls experiments/gemma4_competition/local_eval/evidence/controls-05706c6a.json --controls-sha256 05706c6a948a67bfaf991ed0282d11308aac79865a614a68c6c582fe01f67033
    if ($LASTEXITCODE -ne 0) { throw 'Summary failed; stop' }
    $gemmaCompare += @('--run', ($gemmaLabel + '=' + $gemmaRoot))
}
uv run --locked --offline --no-sync python -B experiments/gemma4_competition/local_eval/compare_runs.py @gemmaCompare --same-config P3a1=P3a2 --same-config P5a1=P5a2 --controls experiments/gemma4_competition/local_eval/evidence/controls-05706c6a.json --controls-sha256 05706c6a948a67bfaf991ed0282d11308aac79865a614a68c6c582fe01f67033 --output 'C:\Work\Gemma4Localtest\p5-four-run-flips-1.md'
if ($LASTEXITCODE -ne 0) { throw 'Per-task comparison failed; stop' }
```

The per-task four-column table exposes all cross-candidate flips; same-config
sections quantify replicate flips. Apply the preregistered gates above to the
four summaries; there is no automatic submission or adoption action.

The P1 dataset-notebook ERROR record also retains the maintainer's likely
scorer-exception-wave explanation (forum reports from approximately October 21).
It is a hypothesis alongside the earlier dataset-input hypothesis; cause stays
UNKNOWN, status ERROR, score null. No new causal claim or live Kaggle verification.

## FORGEAI-GEMMA4-TWO-TRACK-P6-AND-E4B-S1-1

Implementation authored; **NOT RUN — Awaiting user execution**. This section
preregisters both tracks before their first run. P5 remains the 31B submission
candidate until P6 satisfies every condition below. S1 is an experimental E4B
baseline, not submission-qualified. Existing candidate bytes, receipts, official
cells, source/wheel pins and committed result records are unchanged.

### Candidate controls and P6 interface

P6 changes only P5's prompts/system.md. Its exact helper source lives inside
that prompt (not as a fifth package member). The agent creates
/tmp/forge_edit.py once on the first edit; every subsequent source edit uses
python3 /tmp/forge_edit.py with a quoted EDIT heredoc. The helper enforces one
separator, a relative path inside /workspace, and exactly one matching old block.
No-match responses show the three best available windows, deterministically
ranked by difflib ratio and then line number. Python compilation uses a temporary
bytecode destination; failure restores exact original bytes or removes a newly
created file. Success prints at most 80 diff lines. Empty old text is allowed
only for a new file. Blocks retain line endings; use exact full lines. New files
remain untracked until the harness captures them; git diff alone does not display
their contents, so inspect them with the bounded viewer before submission.

The P5 prohibition on edit_file/write_file, missing-argument resend prohibition,
/tmp scratch rule, edit deadline, finish reserve and single submission rule
remain. P6 replaces P5's inline edit template with the helper; retaining both
competing edit mechanisms would contradict the every-source-edit requirement.
Search is capped at 40 lines, views at b-a <=120, listings at 50, test/reproduction
output at 60; never cat files longer than 200 lines. These are prompt instructions,
not new harness-enforced limits. py_compile detects syntax, not semantic defects.
The helper is about 60 lines and uses only Python's standard library.

S1 changes only agent.yaml's model from gemma-4-31b-it-qat-w4a16-ct to
**gemma-4-e4b-it-qat-w4a16-ct**. Prompt, sampling and evaluation config are
byte-identical to P5. Both tracks retain the six-minute task cap and 8192 output /
4096 thinking-token settings. The shared deterministic packager emits the same
four members and fresh external manifests; no duplicated compiler logic.

The ACI motivation is supported by the [SWE-agent paper](https://arxiv.org/abs/2405.15793)
and its [interface ablations](https://openreview.net/pdf?id=mXpq6ut8J3): editing
feedback and bounded file views affect performance. Those results motivate this
experiment; they do not predict a Gemma improvement.

### E4B serving evidence and limits (reviewed 2026-10-29)

The retained [official starter](https://www.kaggle.com/code/ryanholbrook/getting-started-gemma-4-developer-agent)
(`../docs/getting-started-gemma-4-developer-agent.ipynb`, source SHA256
abc9ad7fbce3aa4f15983828a0528d5c1bec58cccf3f82cead6d2d2ed63a768f) and
`../docs/HARNESS_README.md` (SHA256
517a6ba6c38413b49c6cb14e54ab0031d3efbc7a7624c31810f8d6ef617c8601)
list E4B. Pinned serving cell 8 uses model version 2, TP4 on four GPUs,
max_model_len=32768 and gpu_memory_utilization=0.90. Its
MODEL_VLLM_EXTRA_ARGS maps **12B only** to --hf-overrides with architectures
["Gemma4ForCausalLM"] and model_type "gemma4". E4B receives an empty tuple.
The runtime reads that pinned mapping rather than duplicating or guessing flags;
new configs explicitly record model_variant and vllm_extra_args=[]. Package/model
and config/official-argument mismatches stop before installation for P6/S1;
run.json records both model_variant and actual planned serving args.

The [official staff discussion](https://www.kaggle.com/competitions/gemma-4-developer-agent/discussion/748287)
reports a later wheelhouse fix in response to **12B** loading failures involving
vision_embedder.patch_dense.weight after the override. It does not establish an
E4B-specific requirement, nor provide a wheel SHA256 for that fix. Do not copy
the 12B override to E4B or modify model weights.

Our pinned versions are vllm 0.19.1, transformers 5.13.1, adk-submission 0.2.13,
swegemma 0.2.11, adk-eval-core 0.1.0, google-adk 1.36.1, google-genai 2.11.0.
Pinned vLLM wheel SHA256:
73c69bafca24fbdad44690c44d6c6446514351e6f3cc9a6057cba05e66051310.
All seven exact wheel hashes remain in source-pins.json. Version strings alone
cannot establish whether a wheel contains the staff loading fix.

The live [official wheelhouse](https://www.kaggle.com/datasets/metric/gemma-4-developer-agent-wheelhouse)
page did not expose a readable file/version inventory during this review.
**E4B is configured by our pinned official environment; successful serving with
those exact bytes is NOT VERIFIED.** S1 smoke-5 is the serving check. No pin
update is justified by the available E4B evidence. If current mounted bytes fail
the pin check, stop; do not suppress it. A proposed update requires the exact
new official dataset version, complete wheel SHA256 inventory, starter source
and cell hashes, and old/new loader-source diff. Review which distributions and
source pins changed, update them together in a separate authorized slice, and
rerun environment controls. Retain old pins and runs as a separate environment;
do not relabel cross-environment runs as identical-config replicates. The exact
new version/hash is currently unknown; no invented upgrade target is supplied.

### Metrics and preregistered decisions

Every analysis summary now includes aci_metrics at run level and under each
task's tool_argument_rejections. Counts are per official tool observation,
not per occurrence or echoed command. failed_replacements counts observations
containing AssertionError OR FORGE_EDIT_NO_MATCH; syntax_error_observations
counts SyntaxError OR IndentationError. syntax_error_observations_reverted is
the subset with the actual printed revert marker. large_observations counts raw
observation content longer than 6000 characters. Helper OK/no-match/revert counts
come from output marker lines; helper_invocations counts run_command invocations.
helper_created counts tasks with a creation command and matched exit_code=0;
helper_creation_attempts also exposes unconfirmed/failed attempts. Missing or
ambiguous trace coverage yields null aggregate metrics, never an apparent zero.
Existing rejection, patch, timeout, context and timing metrics are preserved.
These substring/command metrics are operational proxies, not proof that every
AssertionError was a source edit or that every invocation modified a file.

Maintainer-reported P5 baselines (recomputation still required): failed
replacements 9/7 (mean 8.0), syntax observations 2/4 (mean 3.0), large observations
9/10, session timeouts 4/3; solved 9/9 and nonempty patches 11/12.
The new analyzer must confirm or explain differences before a P6 decision.
Do not alter the preregistered thresholds to fit new observations.

Adopt P6 only after two independent, complete dev-16v runs with comparable pinned
environment and full trace/patch telemetry, if ALL hold:

| Measure | Required result |
|---|---|
| Mean solved | >=10 of 16 across the two runs |
| Mean failed replacements | <8.0 |
| Mean syntax error observations | <3.0 |
| All-tool argument rejection rate | <=5% in EACH run |
| Nonempty patches | >=11 tasks in EACH run |
| Bootstrap upper95 total | <=11 hours in EACH run |

Otherwise retain P5. Unknown/incomplete data cannot pass. Report per-task flips
for each P6 run against BOTH P5 runs, plus within-P6 replicate flips. Time fit
uses the existing deterministic 116-task empirical bootstrap including startup;
its small-sample and hidden-concurrency limitations remain.

S1 submission gate: complete frozen dev-16v run, zero harness errors (inspect
both harness_errors and HARNESS_ENVIRONMENT_ERROR, not just completion label),
all-tool argument rejection rate <=5% with complete coverage, bootstrap upper95
<=**10.5 hours**. Do not use the generic analysis time gate's 11-hour PASS label
for this stricter decision. smoke-5 does not qualify S1. No solved-count floor
is added to this baseline gate; compare E4B candidates separately from 31B.
If time fit fails, do not submit: propose S2's shorter max_time_minutes only
after examining measured per-task agent and total durations, cap-hit frequency,
startup and harness overhead. A capped-duration bootstrap is a planning estimate,
not measured S2 evidence: shorter caps can change behavior and success. Choose
and preregister a conservative cap with <=10.5h projected fit, then rerun S2;
no numeric cap is guessed before S1 measurements exist.

### Maintainer commands: offline checks, then builds

Prerequisites: repository C:\Work\ForgeAI-Gemma4 on br-ForgeAI-Gemma4, existing
locked uv environment/cache; no new dependencies, credentials or environment
variables required for offline tests. These tests execute the helper extracted
from the prompt against temporary fixture files; they do not run agents or GPU
workloads. Tests mock git diff and remap only /workspace to a temporary directory.

```powershell
Set-Location 'C:\Work\ForgeAI-Gemma4'
uv run --locked --offline --no-sync python -B -m unittest discover -s experiments/gemma4_competition/local_eval -p 'test_*.py'
if ($LASTEXITCODE -ne 0) { throw 'Tests failed; paste output and stop' }
```

Expected: all tests OK, including test_two_track.py helper success/revert/no-match/
separator/path/new-file controls, observation metrics, model mismatch and narrow
S1 smoke authorization. STOP and paste results before advancing. No tests have
been run by the coding agent. After review of passing output, build to fresh
external directories (existing destinations deliberately fail):

```powershell
uv run --locked --offline --no-sync python -B experiments/gemma4_competition/local_eval/experimental.py p6 --output 'C:\Work\Gemma4Localtest\gemma-p6-experiment-attempts1-2'
if ($LASTEXITCODE -ne 0) { throw 'P6 build failed; stop' }
uv run --locked --offline --no-sync python -B experiments/gemma4_competition/local_eval/experimental.py s1 --output 'C:\Work\Gemma4Localtest\gemma-s1-experiment'
if ($LASTEXITCODE -ne 0) { throw 'S1 build failed; stop' }
```

Expected per directory: submission.zip.bin, manifest.json, and two generated
configs with actual ZIP/manifest hashes. Output reports EXPERIMENTAL_UNQUALIFIED
and submission_authorized=false. ZIP hashes/sizes are deliberately not invented
before the maintainer builds. Source configs remain unapproved with BUILD_REQUIRED
hashes; use the generated external configs, not those placeholders.

| Config | Model | Frozen subset | Independent output directory under /kaggle/working |
|---|---|---|---|
| p6-dev16v-attempt1.json | 31B | dev-16v | forgeai-local-eval-p6-dev-16v-attempt1 |
| p6-dev16v-attempt2.json | 31B | dev-16v | forgeai-local-eval-p6-dev-16v-attempt2 |
| s1-smoke5.json | E4B | smoke-5 | forgeai-local-eval-s1-smoke-5-attempt1 |
| s1-dev16v.json | E4B | dev-16v | forgeai-local-eval-s1-dev-16v-attempt1 |

### Kaggle run order and teammate account

Run S1 smoke-5 FIRST, retain startup/timing/serving evidence, and stop on model
load, wheel mismatch or harness failure. Only after review run S1 dev-16v.
Schedule P6 attempt1 and attempt2 as independent sessions with empty resume
fields; both must use identical model/package/wheel/tooling dataset versions.
Coordinate allocation within the shared ~30 L4x4-hours/week budget; measure
actual session setup, work and idle usage, stop sessions promptly, and avoid
simultaneous duplicate experiments. The 10800-second watchdog in each config
is an evaluation-session guard, not a hidden-set time prediction.

For each account, use Copy & Edit of the official starter, import local_eval.ipynb
into that copy, L4x4, Internet Off. Attach the public competition data, exact
pinned official wheelhouse, the selected official model Other/version 2, the
reviewed local_eval tooling directory as a private dataset, and the matching
external experiment directory as another private dataset. Do not attach hidden
data. Keep the same pinned dataset versions for both maintainers.

Grant the teammate collaborator access to the private tooling/package datasets
and the notebook. Each teammate must have their own competition/model access.
Dataset owner slugs in mounted paths stay those of the dataset owner; they do
not automatically become the teammate's username. The teammate uses Copy & Edit
and Save Version -> Save & Run All from THEIR account. They must explicitly
approve the config for their run and record account, notebook/version and dataset
versions with the retained outputs. No quota is consumed by merely sharing inputs.

In the first code cell, retain the notebook's imports and safety checks, set TOOLS
to the actual private tooling mount, and replace the hardcoded CONFIG dictionary
with loading the generated selected config. Example for S1 smoke (substitute
OWNER and actual dataset slugs; other runs use the table's matching config):

```python
TOOLS = Path('/kaggle/input/datasets/OWNER/local-eval/local_eval')
CONFIG = json.loads(Path('/kaggle/input/datasets/OWNER/s1-experiment/s1-smoke5.json').read_text())
CONFIG['package'] = '/kaggle/input/datasets/OWNER/s1-experiment/submission.zip.bin'
CONFIG['manifest'] = '/kaggle/input/datasets/OWNER/s1-experiment/manifest.json'
CONFIG['subset_file'] = str(TOOLS / ('subsets.json' if CONFIG['subset'] == 'smoke-5' else 'dev-16v.json'))
# Set only after the operator approves this exact candidate/subset and GPU session:
CONFIG['authorization'] = 'AUTHORIZE FORGEAI GEMMA4 LOCAL EVAL s1 ON smoke-5'
CONFIG['gpu_authorized'] = True
CONFIG['official_environment_authorized'] = True
CONFIG['internet_off_confirmed'] = True
CONFIG['experimental_authorized'] = True
```

For S1 dev use authorization `AUTHORIZE FORGEAI GEMMA4 LOCAL EVAL s1 ON dev-16v`;
for both P6 runs `AUTHORIZE FORGEAI GEMMA4 LOCAL EVAL p6 ON dev-16v`.
Keep generated hash pins, model_path, model_variant, vllm_extra_args=[] and output
identity intact. Do not turn package_reconciled on: these are experiments.
Run only the local_eval notebook's two code cells in order: config recording,
then gated runtime. The worker executes pinned official install cell 2 and serving
cell 8, then selected public tasks; do not run original starter sample-eval,
compiler or submission cells. No new self-contained submission notebook is created.

Retain the complete output folder, including environment.json, run.json,
tasks.jsonl, events.jsonl, completion.json, worker.log and all official traces,
patches and task results. Preserve failures as failures. Store S1 outputs at
C:\Work\Gemma4Localtest\local_eval_s1_smoke5 and local_eval_s1_dev16v; P6 at
local_eval_p6_dev16v_attempt1 and local_eval_p6_dev16v_attempt2. These directories
must directly contain run.json (remove an extra extraction nesting by choosing
the correct root, not by editing evidence). No scores are expected or promised.

### Recompute retained metrics without overwriting evidence

After offline tests pass, the following exports all ten retained comparable
runs (eight earlier plus two P5). Enter the real run root for each label; P1b
is the merged run, once. P1's dev-30 is restricted to the frozen dev-16v IDs by
the existing exporter. Missing old traces yield null metrics and need recovery,
not invented zeros. Historical results files are not rewritten by these commands.

```powershell
$aciRuns = @()
foreach ($aciLabel in @('p1','p1b','p1c','p2','p3','p3g','p3att2','p4','p5att1','p5att2')) {
    $aciRoot = Read-Host "Exact retained run root for $aciLabel (contains run.json)"
    $aciRuns += @('--run', ($aciLabel + '=' + $aciRoot))
}
uv run --locked --offline --no-sync python -B experiments/gemma4_competition/local_eval/paper_evidence.py @aciRuns --controls experiments/gemma4_competition/local_eval/evidence/controls-05706c6a.json --controls-sha256 05706c6a948a67bfaf991ed0282d11308aac79865a614a68c6c582fe01f67033 --output 'C:\Work\Gemma4Localtest\p6-retained-aci-review-1'
if ($LASTEXITCODE -ne 0) { throw 'ACI export failed; paste output and stop' }
```

Expected external dev-16v-comparison.md and run-analysis.json with per-task and
aggregate ACI metrics, trace hashes and rejection rates. Compare P5 9/7 replacement
and 2/4 syntax counts; investigate rather than adjust data/code to force agreement.
Recomputation is NOT RUN. Reviewed derived values can be promoted to committed
comparison/paper evidence in a later authorized results slice.

After future runs, summarize each root using this interface (change the root for
each run). The summary includes mean time, bootstrap upper95, patch production,
rejections, ACI counts, timeout/context categories and per-task outcomes:

```powershell
uv run --locked --offline --no-sync python -B experiments/gemma4_competition/local_eval/analysis.py summary 'C:\Work\Gemma4Localtest\local_eval_s1_dev16v' --controls experiments/gemma4_competition/local_eval/evidence/controls-05706c6a.json --controls-sha256 05706c6a948a67bfaf991ed0282d11308aac79865a614a68c6c582fe01f67033
if ($LASTEXITCODE -ne 0) { throw 'Summary failed; stop' }
uv run --locked --offline --no-sync python -B experiments/gemma4_competition/local_eval/compare_runs.py --run 'P5a1=C:\Work\Gemma4Localtest\local_eval_p5_dev16v_attempt1' --run 'P5a2=C:\Work\Gemma4Localtest\local_eval_p5_dev16v_attempt2' --run 'P6a1=C:\Work\Gemma4Localtest\local_eval_p6_dev16v_attempt1' --run 'P6a2=C:\Work\Gemma4Localtest\local_eval_p6_dev16v_attempt2' --same-config P6a1=P6a2 --controls experiments/gemma4_competition/local_eval/evidence/controls-05706c6a.json --controls-sha256 05706c6a948a67bfaf991ed0282d11308aac79865a614a68c6c582fe01f67033 --output 'C:\Work\Gemma4Localtest\p6-vs-p5-flips-1.md'
if ($LASTEXITCODE -ne 0) { throw 'Flip comparison failed; stop' }
```

Apply the preregistered thresholds to complete metrics, not labels. Keep best 31B
and best eligible E4B as separate final picks; never mix variants within one
submission. The [official prize rules](https://www.kaggle.com/competitions/gemma-4-developer-agent/overview/prizes)
place the E2B/E4B bonus among the final two selections. Passing public-development
gates still requires separate official compilation, byte-identity reconciliation
and submission qualification; it does not predict hidden scores or award eligibility.

## S2 E4B prompt-only follow-up

S1 dev-16v attempt1 is recorded in results: 3/16 solved, eight empty submissions,
five wrong patches, no time_budget, mean 78 s and eight calls; operational gate
PASSED as reported by the maintainer. S1 remains the E4B fallback. Reported ~1.6%
rejections does not supply the exact denominator; bootstrap upper95 was not supplied.
No independent operational qualification or submission was executed here.

S2 copies S1's agent.yaml, eval_config.yaml and configs/sampling.yaml byte for
byte. Only prompts/system.md changes, from 5553 to 4056 bytes. Its priority rules
require an actual source edit and diff before submission, continue with a small
Python reproduction after missing test-only dependencies, explain the 28-call /
six-minute budget, search exact issue identifiers first, and recover non-unique
edit targets by rereading more context. The edit_file recovery rule is conditional
on accidental use; the inherited run_command-only source-edit rule remains.
S2 is a shorter prompt revision, not an isolated single-rule ablation.

Preregistered S2 gate, before execution: complete dev-16v; solved >=5/16 AND
empty patches <=3 AND projected time <=10.5 hours, using the existing bootstrap
upper95 time-fit for consistency with S1. Existing E4B operational controls remain
prerequisites. Unknown metrics cannot establish a pass. Otherwise keep S1.

No tests/builds executed. Use the existing locked environment from repository root;
no additional environment variables or dependencies. First run tests and paste
results; stop before building until those results are reviewed:

```powershell
Set-Location 'C:\Work\ForgeAI-Gemma4'
uv run --locked --offline --no-sync python -B -m unittest discover -s experiments/gemma4_competition/local_eval -p 'test_*.py'
if ($LASTEXITCODE -ne 0) { throw 'Tests failed; paste output and stop' }
```

Expected OK including S2 prompt-only/shorter-prompt and E4B model/subset checks.
After review, build with the shared packager to a fresh external directory:

```powershell
uv run --locked --offline --no-sync python -B experiments/gemma4_competition/local_eval/experimental.py s2 --output 'C:\Work\Gemma4Localtest\gemma-s2-experiment'
if ($LASTEXITCODE -ne 0) { throw 'S2 build failed; stop' }
```

Expected EXPERIMENTAL_UNQUALIFIED, submission_authorized=false, submission.zip.bin,
manifest.json and s2-dev16v.json with real ZIP/manifest hashes. The printed JSON
reports zip_sha256, manifest_sha256 and files['prompts/system.md']; no hashes
are invented for unbuilt artifacts. Upload this fresh directory as the private
s2-experiment dataset. Use the existing local_eval notebook and generated config,
E4B version 2, pinned wheelhouse, empty extra args, dev-16v, and authorization
AUTHORIZE FORGEAI GEMMA4 LOCAL EVAL s2 ON dev-16v only when approving the run.
Keep the S1 fallback and all historical evidence intact.

## S3: final E4B prompt iteration after S2 failure

S2 attempt1 is recorded in results: 3/16 solved, two empty patches, eleven wrong
patches, zero harness errors; 1927 s including reported startup 338 s. It failed
the solved >=5 gate, so S1 remains the fallback. The reported rich_3454 regression
involved sed -i regex corruption of rich/highlighter.py, a 115366-byte patch and
submission despite recognizing the damage. No independent trace analysis ran.

S3 changes ONLY S2's prompts/system.md. The other three members are byte-identical.
Prompt length is 4304 bytes versus S2's 4056 (+248, within the +400-byte cap).
It prohibits sed -i/regex edits, permits edit_file or python3 exact-string edits,
requires reverting damaged edits with git checkout -- <file> and redoing them,
and requires a nonempty, small, intended-source-only diff before submission.
Unrelated pre-existing changes must be preserved before a file restore. This is
an instruction for the evaluated agent, not a checkout performed in this repo.
The contradictory S2 run_command-only restriction is removed; missing-argument
errors still require switching to run_command without resending the failed call.

Preregistered S3 gate: completed dev-16v with solved >=5/16 AND empty patches <=3
AND no task patch >20000 bytes (20 KB, decimal) AND bootstrap upper95 <=10.5 h.
All metrics must be known; existing E4B operational prerequisites still apply.
Otherwise freeze S1 as the E4B entry and STOP E4B iteration. No threshold tuning
or another E4B candidate after a failed S3 gate is authorized by this slice.

NOT RUN — Awaiting user execution. From C:\Work\ForgeAI-Gemma4 in the existing
locked uv environment, no new dependencies or environment variables:

```powershell
Set-Location 'C:\Work\ForgeAI-Gemma4'
uv run --locked --offline --no-sync python -B -m unittest discover -s experiments/gemma4_competition/local_eval -p 'test_*.py'
if ($LASTEXITCODE -ne 0) { throw 'Tests failed; paste output and stop' }
```

Expected OK, including S3 prompt-only, size, corruption-rule and E4B model/subset
controls. Paste results and stop before building until they are reviewed.
After successful review, the shared experimental builder command is:

```powershell
uv run --locked --offline --no-sync python -B experiments/gemma4_competition/local_eval/experimental.py s3 --output 'C:\Work\Gemma4Localtest\gemma-s3-experiment'
if ($LASTEXITCODE -ne 0) { throw 'S3 build failed; stop' }
```

Expected fresh external submission.zip.bin, manifest.json, s3-dev16v.json with
actual hashes; state EXPERIMENTAL_UNQUALIFIED and submission_authorized=false.
No bundle or ZIP/manifest hash has been generated here. Use the same reviewed
local-eval workflow, E4B version 2 and pinned wheelhouse with no extra vLLM args.
The generated config remains unapproved until the maintainer approves its GPU
run with AUTHORIZE FORGEAI GEMMA4 LOCAL EVAL s3 ON dev-16v and the existing flags.

## P7a/P7b: 31B commit-early experiments; S3 paused

P5 public 0.13 is already recorded: p5_selfcontained v2, scriptVersionId 363609276,
ZIP 6db4109a73cfea1c803c17e86f498406461141904dac58efe441f10cca1fe219.
P5 remains the frozen 31B fallback. Public >=0.20 is a target, not a prediction.
S3 is PAUSED_NOT_BUILT by maintainer instruction: do not build or run it. Its
previous gate and source remain historical preparation, not an active run request.

P7a changes only P5's prompt. It adds top-priority exact-identifier localization
in the first ~5 calls, first source edit by call ~12/minute 3, a nonempty/small/
intended diff requirement, no sed -i/regex code edits, damaged-file recovery and
submission of the best current valid diff near budget limits. The old call-10 /
150-second edit deadline is replaced by call-12 / 180 seconds to avoid conflicting
instructions. The entire P5 run_command edit workaround is byte-identical; no
helper creation is introduced. Commit early means edit source, not git commit.
P7b has exactly the P7a prompt and changes only thinking_budget 4096 -> 2048.
Both retain P5 agent.yaml (83a97b8a...), eval_config (2c8a983a...), output cap8192,
temperature, tools, finish reserve and six-minute task budget.

### Preregistered gate

Run one complete frozen dev-16v screening run for each candidate. A candidate
must solve >=11/16, have <=3 empty patches and bootstrap upper95 <=11 h. Select
among passing candidates by highest solved, then fewer empty patches, then lower
bootstrap upper95, then P7a. This deterministic tie-break is recorded before runs.
Fix the winner before confirmation; run that unchanged package/config/environment
once more independently on dev-16v. Mean solved across the selected screening run
and its confirmation must be >=10.5/16; confirmation must also meet <=3 empty
patches and <=11 h upper95. Complete, known metrics are required. Otherwise keep
P5; do not switch to the runner-up after a failed confirmation without a separate
preregistration. This confirmation is a same-config dev-16v repeat, not held-out
confirm-20. Passing does not imply public >=0.20 or authorize submission.

### Maintainer sequence (NOT RUN)

Existing locked uv environment at C:\Work\ForgeAI-Gemma4; no new dependencies
or environment variables. First run tests and paste output; stop pending review:

```powershell
Set-Location 'C:\Work\ForgeAI-Gemma4'
uv run --locked --offline --no-sync python -B -m unittest discover -s experiments/gemma4_competition/local_eval -p 'test_*.py'
if ($LASTEXITCODE -ne 0) { throw 'Tests failed; paste output and stop' }
```

Expected OK, including exact P7 ablations, preserved workaround, rejection of
extra sampling changes even with updated pins, and model/subset/authorization
controls. After successful review, build to fresh external directories:

```powershell
uv run --locked --offline --no-sync python -B experiments/gemma4_competition/local_eval/experimental.py p7a --output 'C:\Work\Gemma4Localtest\gemma-p7a-experiment'
if ($LASTEXITCODE -ne 0) { throw 'P7a build failed; stop' }
uv run --locked --offline --no-sync python -B experiments/gemma4_competition/local_eval/experimental.py p7b --output 'C:\Work\Gemma4Localtest\gemma-p7b-experiment'
if ($LASTEXITCODE -ne 0) { throw 'P7b build failed; stop' }
```

Expected each directory: submission.zip.bin, manifest.json and matching
p7a-dev16v.json or p7b-dev16v.json with actual ZIP/manifest pins. State remains
EXPERIMENTAL_UNQUALIFIED; submission_authorized=false. ZIP/manifest hashes are
pending because no build ran. Configs use official 31B Other/version 2 and empty
extra serving args, frozen dev-16v and independent attempt1 outputs, with every
authorization false and resume fields empty. Use the existing private-dataset /
local_eval notebook workflow, reviewed tooling, pinned wheelhouse, L4x4 and
Internet Off; set real dataset mounts without changing generated hashes.
Approve only the exact desired run using
AUTHORIZE FORGEAI GEMMA4 LOCAL EVAL p7a ON dev-16v or
AUTHORIZE FORGEAI GEMMA4 LOCAL EVAL p7b ON dev-16v and existing approval flags.
For the selected confirmation, reuse identical package/config settings and pins,
change only output to a fresh ...-attempt2 directory, and leave resume fields
empty. Do not merge or resume attempt1 as a confirmation. Retain all raw outputs,
traces and environment identities. Subsequent qualification is a separate step.

## P8: replicated tool-budget screening (preregistered, not run)

P7a confirmation failed (11+7)/2=9.0<10.5 and attempt2 had5 empty patches.
P5 remains the frozen31B entry. P8 changes ONLY P7a eval_config.yaml:
max_tool_calls28->40. Six minutes,80 turns,180-second command timeout, agent,
prompt and sampling remain byte-identical. No compiler/package logic is duplicated.

Local official-source review: [HARNESS_README section7.1](../docs/HARNESS_README.md#71-default-budgets-evaluationbudget-eval_configyaml--harness-limits-harnesslimits)
documents configurable tool calls and default100 (not a maximum).
The pinned [starter notebook](../docs/getting-started-gemma-4-developer-agent.ipynb)
reads `int(eval_section.get('max_tool_calls', 100))` and forwards it unchanged.
Archived `swegemma-0.2.11-py3-none-any.whl`, `swegemma/budget.py` and
`config.py`, define an optional integer budget and pass the override through.
No hard upper maximum was found in these pinned sources;40 is below the
starter default100. This is a pinned-source finding, not a claim about later rules.

Protocol: both fresh dev-16v attempts are required; run concurrently on the two
maintainer accounts with the same package, model, controls, wheelhouse and
settings. No resume or shared output directory. Adopt only if pooled solved>=21/32,
pooled empty<=6, AND each authoritative repo bootstrap upper95<=11 h. Require
complete16-task runs and known metrics. Otherwise keep P5. No one-run selection.
Report account/environment identities and per-task flips; local gate success
alone does not authorize a submission. S3 remains paused.

Maintainer commands (existing locked offline environment, repository root):

```powershell
Set-Location 'C:\Work\ForgeAI-Gemma4'
uv run --locked --offline --no-sync python -B -m unittest discover -s experiments/gemma4_competition/local_eval -p 'test_*.py'
if ($LASTEXITCODE -ne 0) { throw 'Tests failed; paste output and stop' }
```

Expected OK including P8 budget-only control, rejection of extra changes even
with new pins, two independent configs and experimental model/approval checks.
Paste results before progressing. After successful checks, the build command is:

```powershell
uv run --locked --offline --no-sync python -B experiments/gemma4_competition/local_eval/experimental.py p8 --output 'C:\Work\Gemma4Localtest\gemma-p8-experiment-attempts1-2'
if ($LASTEXITCODE -ne 0) { throw 'P8 build failed; stop' }
```

Expected: submission.zip.bin, manifest.json, p8-dev16v-attempt1.json and
p8-dev16v-attempt2.json; EXPERIMENTAL_UNQUALIFIED, submission_authorized=false.
ZIP/manifest hashes await the maintainer build. Output directory must not exist.
Upload the single package and current local_eval tooling to shared private datasets;
give both accounts access. Each account uses its own Copy & Edit + Save & Run All
with the corresponding generated config in the existing local_eval notebook,
31B Other/version2 model, pinned wheelhouse, L4x4 and Internet Off. Replace dataset
mount placeholders, preserve generated hashes, review existing authorization
flags and use `AUTHORIZE FORGEAI GEMMA4 LOCAL EVAL p8 ON dev-16v` for each run.
Output folders end in p8-dev-16v-attempt1/attempt2. Retain run.json, completion,
traces and task results from both runs; do not overwrite or merge them.

Verification: NOT RUN — awaiting maintainer execution. No tests, builds,
validators, notebooks or evaluations executed for this slice.

## P9a/P9b: state on disk and thinking budget (preregistered, not run)

P8 is final REJECTED; attempt2 CANCELLED per maintainer. P5 remains frozen.
P9a adds only a concise state-on-disk block to the entire P7a prompt:
/tmp/repro.py and /tmp/notes.md preserve the target, reproduction, edits and next
step across summarized history. All writes remain via run_command; source-edit
workaround and existing P7a rules remain intact. P9b changes only thinking_budget
4096->512 relative to P9a. Both keep P7a's28 calls,6 minutes and8192 output tokens;
this is not a continuation of P8's40-call setting.

Two fresh full dev-16v runs per variant (four total), fixed package/environment
within each pair, distinct output directories, no resume. A variant passes only
if pooled solved>=21/32 AND pooled empty<=6 AND BOTH authoritative repo bootstrap
upper95<=11 h. All outcomes/patch/time metrics must be known. If one passes, select
it; if both pass, higher pooled solved wins. Equal pooled solved retains P5
(conservative tie policy); neither passing also retains P5. Do not choose from
single-run results. Submission qualification remains a separate step.

Compaction investigation: runtime.py:250-251 reconstructs the same15/2/14336/5
settings as official starter cell index10(id1b3f20ba), source-lines68-72, and
HARNESS_README.md:568-575. Cell8 is server setup, not the evaluation cell.
No compaction-only LOCAL_EVAL_DIVERGENCE established; exact deployed scorer
parity remains unverified. There is no documented agent.yaml/eval_config.yaml
submission override for compaction. Summary model, prompt and token settings
are UNKNOWN from available pinned bytes: Google ADK defaults are delegated and
the registered1.36.1 wheel is absent. Do not infer that512 applies to summary
calls. Positive thinking_budget is mapped per ordinary agent request to vLLM
extra_body.thinking_token_budget; it is not a task-wide quota. Compaction is not
guaranteed exactly every15 tool calls; thresholds also apply. See paper-evidence
source review and maintainer-measurement limitations.

Manual controls, existing locked offline environment, repository root:

```powershell
Set-Location 'C:\Work\ForgeAI-Gemma4'
uv run --locked --offline --no-sync python -B -m unittest discover -s experiments/gemma4_competition/local_eval -p 'test_*.py'
if ($LASTEXITCODE -ne 0) { throw 'Tests failed; paste output and stop' }
```

Expected OK including P9 static controls, extra-sampling-change rejection,
four independent configs, and model/subset/authorization checks. Paste results
before proceeding. After successful tests and review, build commands are:

```powershell
$p9aOutput = 'C:\Work\Gemma4Localtest\gemma-p9a-experiment-' + [guid]::NewGuid().ToString('N')
uv run --locked --offline --no-sync python -B experiments/gemma4_competition/local_eval/experimental.py p9a --output $p9aOutput
if ($LASTEXITCODE -ne 0) { throw 'P9a build failed; stop' }
$p9bOutput = 'C:\Work\Gemma4Localtest\gemma-p9b-experiment-' + [guid]::NewGuid().ToString('N')
uv run --locked --offline --no-sync python -B experiments/gemma4_competition/local_eval/experimental.py p9b --output $p9bOutput
if ($LASTEXITCODE -ne 0) { throw 'P9b build failed; stop' }
```

Each output: submission.zip.bin, manifest.json and variant-dev16v-attempt1.json /
attempt2.json with generated package/manifest hashes; EXPERIMENTAL_UNQUALIFIED,
submission_authorized=false. ZIP/manifest hashes await maintainer builds.
Use shared private datasets and the existing local_eval notebook with the pinned
31B Other/version2 model, wheelhouse, L4x4 and Internet Off. Each account gets
its assigned fresh config; replace dataset mount placeholders only, preserve
hashes, and review the existing approval flags. Exact approval phrases:
AUTHORIZE FORGEAI GEMMA4 LOCAL EVAL p9a ON dev-16v
AUTHORIZE FORGEAI GEMMA4 LOCAL EVAL p9b ON dev-16v
Keep all four raw run directories distinct and retain traces/environment metadata.
No runtime, compaction, compiler or package implementation was changed.
Verification NOT RUN — awaiting maintainer execution.

## P10: P5 eight-minute timing screen (preregistered, not run)

P10 preserves all P5 bytes except evaluation.max_time_minutes6->8.
Tool cap28, agent, prompt and sampling are unchanged. The exact P5 prompt still
describes6 minutes and an edit deadline at300 seconds: this experiment changes
the harness allowance, not the prompt deadline. P4 previously tested7 minutes
on P3; the claim that no time-cap experiment ever occurred is not supported.

Pinned-source review: docs/HARNESS_README.md:542-554 explicitly permits
max_time_minutes overrides (default60 minutes). Official starter code cell10
converts this value to float; OFFICIAL-CONTRACT-REGISTER.md:358-361 records
that conversion and cautions that it alone does not prove ranges.
docs/archive/swegemma-0.2.11-py3-none-any.whl!swegemma/config.py:107,149-177
accepts int/float and forwards it to EvaluationBudget; swegemma/budget.py:15-18
declares a float time_minutes with default60.0. No numerical min/max range
or prohibition on8 was found in these pinned sources. Eight is compatible with
the pinned configuration path; this does not remove the total platform limit.

One complete dev-16v timing run, no resume. Record accuracy, but do not gate on
it. Eligibility requires COMPLETED with16 results, zero harness errors,
exact-phrase tool-argument rejections/all requested calls<=5%, and repo
bootstrap upper95<=11.0 h. Unknown metrics block eligibility. Then, and only
after separate official package qualification, permit ONE exploratory public
submission. Adopt P10 only if public>=0.17; otherwise retain P5.
If upper95>11.0 h, prepare P10b with7 minutes; do not build it speculatively.
All other failures block submission. Neither public submission nor qualification
is performed by the experimental builder.

Forum claims (including staff's whole-submission failure above12 h and exclusion
of queue time) and projected mean9.0-9.4 h / upper95 10.8-11.4 h are recorded in
paper-evidence.json as maintainer reports, not independently verified rules.
The6->8-minute projection holds other task durations fixed; it is not an absolute
worst case. All116 tasks at8 minutes take15.47 h before startup.

Manual prerequisites: C:\Work\ForgeAI-Gemma4, branch br-ForgeAI-Gemma4,
existing locked offline uv environment. No new environment variables required.

~~~powershell
Set-Location 'C:\Work\ForgeAI-Gemma4'
uv run --locked --offline --no-sync python -B -m unittest discover -s experiments/gemma4_competition/local_eval -p 'test_*.py'
if ($LASTEXITCODE -ne 0) { throw 'Local evaluation tests failed; paste output and stop' }
~~~

Expected OK, including time-only identity, refusal of extra changes even after
repinning, authorization refusal and wrong-model/package rejection. Paste the
results before proceeding. Verification: NOT RUN — Awaiting user execution.

Subsequent maintainer build (not executed here):

~~~powershell
$p10Output = 'C:\Work\Gemma4Localtest\gemma-p10-experiment-' + [guid]::NewGuid().ToString('N')
uv run --locked --offline --no-sync python -B experiments/gemma4_competition/local_eval/experimental.py p10 --output $p10Output
if ($LASTEXITCODE -ne 0) { throw 'P10 build failed; paste output and stop' }
~~~

Expected EXPERIMENTAL_UNQUALIFIED, candidate p10, submission_authorized false;
submission.zip.bin, manifest.json and p10-dev16v-attempt1.json externally.
ZIP and manifest hashes are build outputs, not claimed before execution.
Use the generated config with the existing local-evaluation notebook workflow:
replace mounted dataset paths, preserve31B model path, supply the exact
AUTHORIZE FORGEAI GEMMA4 LOCAL EVAL p10 ON dev-16v phrase and explicitly enable
the existing operator authorization flags only when launching the timing run.
P9 final attempt2 results are already recorded; P9 remains rejected.

## X22 private local sensitivity check (preregistered, not run)

Attribution: a public leaderboard notebook, provenance unrecorded.
Author, URL, version and license: NOT FOUND. Maintainer authorizes PRIVATE LOCAL
EVALUATION ONLY; this is not a license grant. No submission or prompt quotation.
Keep the candidate, datasets, traces and evaluation artifacts private.
The reported0.22 score is maintainer-supplied, not independently verified.
Source label c9829b6ac709 has an unknown convention and is not an identity pin.

Exact source: Downloads/results (10).zip -> submission.zip,3031 B,
SHA25680f4b123502f36dfd62745ca6aee9a9cd26f681338e52f75c8b3c302d6100767.
Four files under candidates/x22 are unchanged source bytes; member hashes are
in experimental-pins.json and results/x22-reference-provenance.json.
The builder reuses the nested ZIP exactly, never repacks it. No package built here.

Two fresh independent dev-16v runs, x22-dev16v-attempt1.json and
x22-dev16v-attempt2.json,31B model. Both must complete16 tasks; incomplete/missing
results do not trigger either interpretation. Pooled>=22/32:
PROMPT_FAMILY_EFFECT_DETECTED. Otherwise:
DEV16V_DID_NOT_REPRODUCE_PUBLIC_GAP. P5 reference18/32.
This is a sensitivity check, not adoption/submission permission.
Our seven ablations are described by the maintainer as one prompt family.
Timeout and registered tools also differ, so this is not a pure prompt causal test.

Manual tests (existing locked offline environment; no new environment variables):

~~~powershell
Set-Location 'C:/Work/ForgeAI-Gemma4'
uv run --locked --offline --no-sync python -B -m unittest discover -s experiments/gemma4_competition/local_eval -p 'test_*.py'
if ($LASTEXITCODE -ne 0) { throw 'Tests failed; paste output and stop' }
~~~

Expected OK, including unchanged members, original archive identity, independent
configs and submission-generator refusal. Verification NOT RUN — Awaiting user
execution. Paste results before proceeding.

Subsequent manual build (not executed):

~~~powershell
$x22Output = 'C:/Work/Gemma4Localtest/gemma-x22-private-' + [guid]::NewGuid().ToString('N')
uv run --locked --offline --no-sync python -B experiments/gemma4_competition/local_eval/experimental.py x22 --source-archive 'C:/Users/gayat/Downloads/results (10).zip' --output $x22Output
if ($LASTEXITCODE -ne 0) { throw 'X22 build failed; stop' }
~~~

Expected EXPERIMENTAL_UNQUALIFIED, PRIVATE_LOCAL_EVALUATION_ONLY,
submission_authorized false, original3031-byte ZIP SHA256 above, manifest SHA256,
and both generated config files. Configure private dataset mount paths using
the existing local_eval workflow and generated hashes. Authorization phrase:
AUTHORIZE FORGEAI GEMMA4 LOCAL EVAL x22 ON dev-16v.
All authorization flags remain false until the maintainer explicitly launches.
No X22 submission qualifier or public submission notebook is provided.
