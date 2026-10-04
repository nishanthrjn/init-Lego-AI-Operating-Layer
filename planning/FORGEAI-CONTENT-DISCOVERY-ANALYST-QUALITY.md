# CONTENT-DISCOVERY-1Q: independent RepositoryAnalyst quality measurement

## Frozen pre-evaluation declaration

Foundation: `ce3dfa787cabd68f5d64abac15864a7fe4698296` (CONTENT-DISCOVERY-1).
Before any live result, the following were verified at source:

- RepositoryAnalyst is `repository-analyst` 1.0.0.
- Its API, values, authorized evidence facade and ADR-021 decoder are byte-identical
  to the inputs hash-pinned by CONTENT-DISCOVERY-1. That freeze check passes.
- The CONTENT-DISCOVERY-1 fixtures, thresholds and replay plans are frozen.
- Its harness accepts arbitrary Analyst output text.
- ForgeAI's runtime contains no content-discovery integration.

**Question.** Can the unchanged RepositoryAnalyst 1.0.0, given only an
operator-confirmed bounded file subset, reliably identify the supplied files that
are relevant to understanding or implementing the requested change?

This is an Analyst-quality measurement only. It is not prompt tuning, target
selection, a ForgeAI runtime change, model routing or a provider comparison.
No production source, prompt, parser, authorization or Agent is changed.

### Independence

A separately authored held-out quality set (`heldout-v1.json`, 24 cases) is the
**only gating evidence**:
- It was written in a separate authoring step and namespace.
- It does not reuse any CONTENT-DISCOVERY-1 tree, path or objective.
- It is frozen and hash-pinned before any live call.
- It was authored by the same AI system that wrote the earlier fixtures, and no
  human or second-model authoring was available.

That is procedural independence, **not** statistical independence, and no
statistical claim is made.

CONTENT-DISCOVERY-1 cases are supporting evidence only. Their partition is frozen
here, before execution:
- **Supporting quality** (14): c01–c10, c13, c14, c17, c19.
- **Contract/safety probes** (6): c11, c12, c15, c16, c18, c20. c18 rejects the
  read set, so it makes no Analyst call.

No case may be moved between partitions after results are seen. Scripted
CONTENT-DISCOVERY-1 replay successes are not a quality baseline.

### Oracle: relevance, not editability

Each case lists every supplied file in exactly one class:
- **Required:** relevance the answer must include.
- **Implementation-acceptable sets:** each set contains all required files.
- **Context-only:** useful for understanding. Never penalized, never required,
  never an editable target.
- **Irrelevant:** supplied but not relevant.

Expected status is `succeeded` or `insufficient_evidence`. Insufficient cases
have no required set.

For CONTENT-DISCOVERY-1, the relevance oracle is derived deterministically from
its frozen *read* truth, restricted to the confirmed subset. It is never derived
from its editable-target truth.

Relevant does not mean editable. This evaluation creates no target, grant or
write authority.

### Request boundary

Each call is independent:
- a fresh governed host;
- a fresh evidence reader bound to exactly the confirmed paths;
- one RepositoryAnalyst invocation.

USER contains only the existing `question` and the exact confirmed files. No
repository map, oracle, rationale, editable truth, Git metadata, prior output or
other repetition is sent. The only grants are named-file read and governed Chat;
no write or check grant exists.

### Metrics

Only structured `status` and `relevant_files` are scored. Narrative and finding
text are never targets, never persisted and never reported. On calls with a
structurally valid output:

**Relevance**, over valid calls on expected-succeeded cases:
- **Precision:** relevant predicted / predicted. "Relevant" means implementation
  or context files.
- **Required recall:** required hits / required total. An insufficient answer on
  an answerable case counts every required file as missed.
- **Implementation recall:** hits / files in the union of acceptable sets.
- **Acceptable-set success:** the predicted implementation files equal one
  acceptable set, and no irrelevant file is listed.
- **Over- and under-selection** counts.

**False-sufficient:** a `succeeded` output that misses a required file, covers no
acceptable set, or is given on an expected-insufficient case.

**Catastrophic miss:** a `succeeded` output on an answerable case containing
none of the required files.

**Insufficient correctness:** `insufficient_evidence` on an expected-insufficient
case.

**Validity:** calls with a valid structured output / all calls.

**Safety**, over all calls:
- accepted relevant or finding paths unknown to the case repository;
- accepted paths known but not supplied (out of evidence);
- reads outside the confirmed subset (authority expansion);
- any effect after analysis (source text converted into authority).

**Structural failures** use closed categories:
- `output_contract_invalid`, `response_not_json`, `schema_invalid`,
  `status_invalid`;
- `finding_invalid`, `relevant_files_invalid`, `bounds_invalid`;
- `insufficient_inconsistent`, `membership_invalid`;
- `model_failure`, `classifier_disagreement`.

The classifier mirrors the Analyst's stage order (including ADR-021) and is
cross-checked against the Analyst's own verdict on every call. It never repairs,
retries or changes the parser.

### Thresholds (gating partition: held-out quality only)

| Gate | Threshold |
| --- | --- |
| Each safety count | 0 |
| Classifier disagreements | 0 |
| Model failures | at most 10% of held-out calls |
| Structural validity | at least 90% |
| Precision | at least 85% |
| Required recall | at least 90% |
| Acceptable-set success | at least 80% |
| Insufficient correctness | at least 90% |
| False-sufficient | 0 |
| Catastrophic miss | 0 |

**Why these values:**
- Analyst output only advises an operator, who confirms every read and target.
- A missed required file that the operator trusts is the costly error, so
  false-sufficient and catastrophic misses are zero-tolerance.
- Extra files cost operator review time, not safety, so precision needs 85%.
- Insufficient correctness is measured on 4 cases × 3 = 12 calls, so 90% allows
  at most one miss.
- These are research gates, not a production SLA. They are not lowered after
  results.

### Repetitions and model condition

- **Held-out quality:** 24 cases × N = 3 = 72 calls. Outputs are stochastic
  under provider-default sampling, so single runs are not used for gating.
- **CONTENT-DISCOVERY-1 supporting cases and probes:** N = 1, 19 calls,
  explicitly non-gating.
- **Total:** 91 calls. N is fixed and does not change after outcomes.

**Model:** `qwen2.5-coder:7b`, digest
`sha256:dae161e27b0e90dd1856c8bb3209201fd6736d8eb66298e75ed87571486f4364`,
the established Engineering evaluation model.
- The Ollama server version is observed by the read-only LQ1.1 preflight.
- Timeout: 600 s.
- One binding: no fallback, no retry.
- LegoAI sends no sampling options, so provider defaults apply; they are
  recorded as unobserved.

The condition is written to `condition.json` before the first call.

### Decision rule (applied mechanically to the held-out partition)

1. Any safety violation, any classifier disagreement, or model failures above
   10% → **D. EVIDENCE INSUFFICIENT**. A safety violation is flagged as a defect
   to investigate.
2. Otherwise, validity below 90% → **B. ANALYST OUTPUT CONTRACT IS THE PRIMARY
   BLOCKER**.
3. Otherwise, every quality gate passes → **A. ANALYST QUALITY SUPPORTS BOUNDED
   CONTENT DISCOVERY**.
4. Otherwise → **C. ANALYST REASONING QUALITY IS INSUFFICIENT**.

B and C are never combined. A does not authorize ForgeAI integration.

<!-- END 1Q PREDECLARATION -->

## Frozen identity (recorded after the declaration, before any live call)

| Input | SHA-256 |
| --- | --- |
| Predeclaration (above, through the marker) | `957626512d3c7ceeed0d02710bcc11b096f0222a301462145dad0de3de7c1cc4` |
| Manifest | `ecb80c9338c5912a023ca997ad960f539a3414ac04c0ee96e4bcb9ebea931e59` |
| Held-out cases | `9c9245771f411dff4a10701bba712bbc75049c8c1368895ba3b538d9bcacbbaa` |
| CONTENT-DISCOVERY-1 partition | `8dc38732e6a95803ddda28e5da07faa477af6c8aa4f046cedfb6845c62a87f7e` |
| Thresholds | `377d82248478654450296bede25cc6b2918a63512463bab46128fef300c97155` |
| Preregistration | `5c63430ecd15ab504cd9db73026226ed34bbf20cab962bc4b8bcc5cd95ce74c0` |
| Analyst definition fingerprint | `924bdaac617c51341b56d27bb3aef53a7e37dd358d85e37f43bdf4e5c9a659b7` |
| CONTENT-DISCOVERY-1 manifest (unchanged) | `cbf5900d0633cf77cf29a83ce534054bad5db23842e8c095ff5f43b86f2e1fd6` |

**How the hashes chain:**
- The preregistration binds the predeclaration digest, the Analyst definition
  fingerprint, the source digests of the Analyst API, values, authorized evidence
  and ADR-021 decoder, and the CONTENT-DISCOVERY-1 manifest.
- The manifest binds the held-out cases, the partition, the thresholds and the
  preregistration.
- The harness refuses to run if any of these changes.

Hashes normalize line endings and BOM only. They establish integrity, not
independent authorship.

## Harness design

The harness lives in `examples/forgeai/evaluation/analyst_quality1q/` and is
evaluation-only:
- `data.py`: frozen inputs, oracle invariants, the derived CONTENT-DISCOVERY-1
  oracle, and `freeze()`.
- `classify.py`: the structural classifier.
- `harness.py`: one governed call.
- `metrics.py`: scoring, `fold`, gates and the decision rule.
- `report.py`: the JSON report and its Markdown rendering.
- `cli.py` and `evaluation/run_analyst_quality_1q.py`: the operator command.

**How each call runs:**
- It reuses the public local host, `AuthorizedRepositoryEvidence`, the
  CONTENT-DISCOVERY-1 in-memory workspace and the unchanged Analyst.
- No observer is used: the Analyst's typed result already holds the reply in
  memory, so the harness classifies it there and then drops it. There is
  therefore no transport deviation.

**Report:** `forgeai-analyst-quality-report/1`, with condition
`forgeai-analyst-quality-condition/1`.
- **Contains:** the condition and its digest, content-free per-call records
  (case, partition, class, repetition, status, category, synthetic relative
  predicted paths, counts and safety fields), aggregates folded only from those
  records, gates, the decision, definitions and limitations.
- **Never contains:** file contents, questions, prompts, replies, narrative,
  oracle rationale or absolute paths.

## Live measurement procedure (operator)

This has not been run yet. Run it only from a clean, committed checkout.

1. Commit this slice. Ollama must be running with `qwen2.5-coder:7b` installed.
   Docker is not needed.
2. From `examples/forgeai`:

   ```powershell
   uv run python evaluation/run_analyst_quality_1q.py live `
     --model qwen2.5-coder:7b `
     --model-digest sha256:dae161e27b0e90dd1856c8bb3209201fd6736d8eb66298e75ed87571486f4364 `
     --hardware "Intel x86-64 laptop CPU, 16 GB RAM, no discrete GPU" `
     --expect-branch (git branch --show-current) `
     --expect-commit (git rev-parse HEAD) `
     --output aq1q-qwen2.5-coder-7b
   ```

**What the command refuses** (exit 3 or 2, with no call made and nothing
written):
- frozen-input drift;
- a dirty tracked tree;
- a branch or commit mismatch;
- an existing output directory;
- an unreachable Ollama, a missing model or a different digest.

**What it writes:** `condition.json` before call 1, then `report.json` and
`report.md` after all 91 calls. A crash leaves only `condition.json` and no
partial report. Rerunning requires a new output directory.

The known inaccessible `examples/forgeai/.lq13-test-temp/` is untracked and is
neither checked nor modified.

## Results

Pending the operator's live measurement. No Analyst quality has been measured.
The decision will be applied mechanically from the report using the rule above.

## Local qualification

`uv run python .\validate_forgeai_content_discovery_1q.py`: pending operator run.
