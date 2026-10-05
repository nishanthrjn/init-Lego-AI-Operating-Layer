# ANALYST-CONTRACT-DIAG-1: content-free RepositoryAnalyst structural diagnostics

## Pre-run declaration

Foundation: `6df48a1` (CONTENT-DISCOVERY-1Q result recorded). CONTENT-DISCOVERY-1Q
measured 0/91 structurally valid RepositoryAnalyst replies, all classified
`schema_invalid`, and reached decision **B: ANALYST OUTPUT CONTRACT IS THE
PRIMARY BLOCKER** (see
[the 1Q record](FORGEAI-CONTENT-DISCOVERY-ANALYST-QUALITY.md)). This slice
identifies *which* structural stage blocks. It is evaluation-only and changes
no production source, prompt, parser, version or decoder.

**Verified before editing:**
- `git diff 2edc3f7..HEAD` over `src`, `packages` and `examples/forgeai/src`
  is empty.
- The Analyst definition fingerprint is unchanged:
  `924bdaac617c51341b56d27bb3aef53a7e37dd358d85e37f43bdf4e5c9a659b7`.
- The 1Q frozen inputs still verify.

### The exact Analyst contract (source: `analyst/api.py`, `analyst/values.py`)

`_parse` runs these stages in order:

1. **ADR-021 decoding**, then `json.loads` with duplicate-key rejection.
2. **Field set.** The top level must be an object with **exactly**
   `status, summary, relevant_files, findings, risks, unknowns`. Field order
   is not checked; canonical order here is the definition prompt's order.
3. **Status.** `status` must be a string naming `succeeded` or
   `insufficient_evidence`.
4. **Findings.** `findings` must be an array of at most 8 entries. Each entry
   is an object with exactly `text` and `paths` and must satisfy
   `RepositoryFinding`.
5. **`RepositoryAnalysis(...)` arguments**, in evaluation order: `summary`
   (string), `relevant_files` (array of at most 8 path strings), `risks`, then
   `unknowns` (arrays of at most 8 strings). Then the constructor's own checks:
   summary text bounds, duplicate relevant paths, then risk and unknown text
   bounds.
6. **Insufficient-evidence rule.** An `insufficient_evidence` answer needs
   unknowns and no findings.
7. **Membership** (`RepositoryAnalysisResult`): every cited path must be a
   supplied file.

**Constraint from 1Q's coarse classifier.** 1Q's `schema_invalid` could only
have been one of: a duplicate key, a non-object top level, a field-set
mismatch, a non-string summary, or risks/unknowns in the wrong shape. Status,
findings and relevant-files failures had their own 1Q categories, and none
occurred.

### Taxonomy (first failure only)

| Category | Refines 1Q |
| --- | --- |
| `response_not_json` | `response_not_json` |
| `duplicate_key` | `schema_invalid` |
| `top_level_not_object` | `schema_invalid` |
| `field_set_invalid` | `schema_invalid` |
| `status_invalid` | `status_invalid` |
| `findings_shape_invalid` | `finding_invalid` |
| `finding_entry_invalid` | `finding_invalid` |
| `summary_type_invalid` | `schema_invalid` |
| `relevant_files_shape_invalid` | `relevant_files_invalid` |
| `risks_shape_invalid` | `schema_invalid` |
| `unknowns_shape_invalid` | `schema_invalid` |
| `summary_bounds_invalid` | `bounds_invalid` |
| `relevant_files_duplicate` | `relevant_files_invalid` |
| `narrative_bounds_invalid` | `bounds_invalid` |
| `insufficient_inconsistent` | `insufficient_inconsistent` |
| `membership_invalid` | `membership_invalid` |
| `output_contract_invalid` | `output_contract_invalid` (runtime contract) |
| `model_failure` | `model_failure` |
| `classifier_disagreement` | `classifier_disagreement` |

**How classification is checked.** Accept/reject verdicts come from the real
public value constructors. Each call is cross-checked twice:
- against the Analyst's own verdict (disagreement → `classifier_disagreement`);
- against 1Q's coarse classifier (`coarse_consistent`).

Later stages are never evaluated after the first failure.

**Structural observations**, recorded once the top level is an object:
- the expected field count (6) and the actual field count;
- the missing required field names, in canonical order, from the closed
  contract vocabulary only;
- the *count* of unexpected fields;
- the JSON type of each required field (`string`, `array`, `object`, `null`,
  `number`, `boolean` or `missing`);
- a closed `status_value` (`succeeded`, `insufficient_evidence`, `other`,
  `non_string`).

**Representation:** `raw`, `fenced_json`, `fenced_unlabelled`, or `other` (a
fence that is not ADR-021's).

### Privacy

Records may contain only:
- case ID, partition, class and repetition;
- runtime status, stage and representation;
- field counts, missing contract names, unexpected count, field JSON types and
  status value;
- the coarse category and timing.

They never contain source contents, questions, prompts, replies, summary,
finding, risk or unknown text, unexpected field names, host paths or
credentials. Sentinel tests enforce this.

No quality metric is computed from rejected replies.

### Condition

This is the **same frozen CONTENT-DISCOVERY-1Q condition**:
- the 1Q freeze;
- the 24 held-out cases × N=3, plus 19 supporting and probe calls, for 91 in
  total;
- 1Q's request path and governed host;
- `qwen2.5-coder:7b` at `sha256:dae161e2…f4364`, 600 s timeout, provider
  defaults, no fallback or retry.

The 1Q raw replies were never retained, so this is a **fresh run** of that
condition, not a reclassification. The condition records linkage to 1Q:
commit `2edc3f7`, condition digest `2cdb9710…afbf`, report SHA-256
`f03d213f…b93d`, decision B.

Report schema: `forgeai-analyst-contract-diagnostic-report/1`.

### Pattern rule (applied mechanically to all invalid calls)

Let N be the number of invalid calls, excluding model failures.

1. If parse/representation stages (`response_not_json`,
   `top_level_not_object`, `output_contract_invalid`) are at least 50% of N:
   **E. NON-JSON / REPRESENTATION**.
2. Otherwise, if `field_set_invalid` is at least 50% of N, look only at the
   field-set failures:
   - at least half have only unexpected fields (nothing missing) →
     **C. UNEXPECTED-FIELD**;
   - otherwise, one required field is missing in at least 80% of them **and**
     accounts for at least 80% of all missing names →
     **A. SINGLE-FIELD OMISSION**;
   - otherwise → **B. MIXED REQUIRED-FIELD OMISSION**.
3. Otherwise, if type/shape stages are at least 50% of N:
   **D. TYPE/SHAPE**.
4. Otherwise: **F. MIXED STRUCTURAL**.

**Default mapping to a next decision**, to be confirmed after interpretation:

| Pattern | Next decision |
| --- | --- |
| A | 1. ANALYST PROMPT CONTRACT CLARIFICATION JUSTIFIED |
| B, C, D | 2. PROVIDER-NEUTRAL STRUCTURED SCHEMA GUIDANCE REQUIRES DECISION, unless one narrow repeated mismatch dominates (then 1) |
| E | 4. REPRESENTATION ISSUE REOPENED, if ADR-021 envelopes (`other`) dominate; otherwise 5 |
| F | 5. EVIDENCE INSUFFICIENT |

Option 3, PARSER/CONTRACT REVIEW, is chosen only on explicit evidence that the
contract is overconstrained for downstream need. One example: the dominant
omission is a field whose absence the downstream evaluation never uses, which
would need a separate semantic argument.

No fix is implemented in this slice.

<!-- END DIAG-1 PREDECLARATION -->

## Harness

The package `examples/forgeai/evaluation/analyst_contract_diag1/` contains:
- `diagnose.py`: the classifier;
- `runner.py`: the unchanged 1Q request path, plus in-memory diagnosis;
- `report.py`: fold, pattern rule, render and write;
- `cli.py`.

The entry point is `evaluation/run_analyst_contract_diag_1.py`.

Replay qualification runs all 91 calls through the real Analyst with zero
disagreements and zero coarse inconsistencies.

## Live procedure (operator)

1. Commit this slice.
2. Confirm Ollama is running: `curl.exe http://127.0.0.1:11434/api/version`.
3. From `examples/forgeai`, run:

   ```powershell
   uv run python evaluation/run_analyst_contract_diag_1.py live `
     --model qwen2.5-coder:7b `
     --model-digest sha256:dae161e27b0e90dd1856c8bb3209201fd6736d8eb66298e75ed87571486f4364 `
     --hardware "Intel x86-64 laptop CPU, 16 GB RAM, no discrete GPU" `
     --expect-branch (git branch --show-current) `
     --expect-commit (git rev-parse HEAD) `
     --output acd1-qwen2.5-coder-7b
   ```

**Refusal conditions** are the same as 1Q, with no call and nothing written:
- frozen-input drift;
- a dirty tracked tree;
- a branch or commit mismatch;
- an existing output directory;
- an unreachable Ollama, missing model or digest mismatch.

## Results

Pending the operator's live run.

## Local qualification

`uv run python .\validate_forgeai_analyst_contract_diag_1.py`: pending operator
run.
