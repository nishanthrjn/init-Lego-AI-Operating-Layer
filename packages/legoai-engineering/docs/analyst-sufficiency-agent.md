# Evidence sufficiency Agent

ENG-ANALYST-SUFFICIENCY-AGENT-1: **LOCALLY QUALIFIED**.

`EvidenceSufficiencyAgent` in `legoai_engineering.analyst.sufficiency_agent`
performs one governed assessment of supplied evidence. Its distinct definition
`evidence-sufficiency-agent` version **1.0.0** uses the provider-neutral
`engineering-reasoning` ModelRequirement. RepositoryAnalyst **1.0.3**, its prompt,
parser and six-field final analysis are unchanged. No new ADR is needed: this
is the explicitly authorized consumer of the qualified sufficiency vocabulary
under existing Engineering/M7 ownership and ADR-021 representation rules.

## Consumer API and authority

```python
agent = EvidenceSufficiencyAgent(agent_runtime)
result = await agent.assess(
    context, manifest, current_manifest=lambda: application.current_manifest
)
```

`context` is the host-issued ExecutionContext; `manifest` is an immutable
EvidenceManifest. The caller must authorize acquisition and disclosure to the
configured model through the existing evidence path before constructing it.
The Agent receives no workspace, reader, grants, editable targets or tools.
EvidenceRequest is inert data and SUFFICIENT is advisory. Neither grants reads,
edits, acquisition, mutation or progression. Operator/application review remains
mandatory. The governed runtime owns model routing, authorization, effects,
timeout/cancellation and execution identity; no provider is pinned here.

The required `current_manifest` accessor synchronously returns the application's
current in-memory observation. It must not perform acquisition or other I/O.
It is checked before disclosure and after the awaited runtime returns. A change
to question, evidence text/path, provenance, expectations, clarification or
unknowns returns STALE_ASSESSMENT; old output is never rebound to new input.
This detects caller-observed changes, not unobserved filesystem changes or an
atomic repository snapshot. Before later use, the application must again call
`assessment.validate_for(current_manifest)` and obtain operator review.

## Model input

Deterministic UTF-8 JSON contains only question, supplied file path/text pairs,
declared expectations (including exact named requirements or role bindings),
operator clarification requests/answers and explicit unknown prerequisites.
Declaration keys and unknowns are sorted; paths/text remain exact. No trusted
digests, provenance label, oracle labels, rationales, gate thresholds, case
classification or future paired outcomes are added. A path mentioned in supplied
text remains visible as evidence; no unsupplied file content is disclosed.
Caller-provided declarations are judgments and must not be populated from hidden
oracle answers in a model-quality evaluation.

Existing bounds remain: question 2048 UTF-8 bytes; 1–8 files; 8192 bytes/file;
24576 evidence bytes total; existing declaration/request bounds. JSON escaping
can expand even valid values. A 65536-byte serialized input limit returns
BUDGET_EXHAUSTED before invocation rather than truncating; total prompt budget is
81920 bytes. Whole model reply limit is 32768 bytes including an optional fence.
These are accepted-content limits, not guarantees about provider generation cost.

## Exact semantic output

All four top-level keys and all four request keys are mandatory:

```json
{
  "disposition": "missing_governing_evidence",
  "explanation": "The requested conclusion depends on an unsupplied source.",
  "governing_sources": [],
  "requests": [
    {"kind": "source_role", "description": "Governing implementation", "path": null, "choices": []}
  ]
}
```

The parser directly constructs existing EvidenceRequest and
EvidenceSufficiencyAssessment values. Manifest/question/evidence attribution is
bound by application code to the original manifest; model identity fields are
rejected as unknown fields. No parallel public result vocabulary is introduced.

- `sufficient`: governing evidence supports analysis of this exact question,
  subject to review; at least one supplied citation, no requests or unmet
  declared prerequisites. It is neither verified correctness nor permission.
- `missing_governing_evidence`: at least one named/source-role request. References
  to absent implementation/configuration/data do not provide their contents.
- `unresolved_ambiguity`: at least one operator clarification request. More files
  cannot stand in for operator intent. Mixed evidence/intent requests are allowed.

Named evidence requires an exact relative path identified by supplied evidence,
with no choices. A source role carries description only, null path and empty
choices. Clarification carries null path and zero or 2–8 distinct choices.
Descriptions are nonblank <=1024 UTF-8 bytes, choices <=256 bytes, explanations
<=2048 bytes; request/citation arrays contain at most eight distinct entries.
Existing value/path/citation validation remains authoritative. Whether a named
path is semantically justified by source text remains an untrusted claim for
operator review; the parser does not infer imports or path provenance. A role
cannot carry a structured path, and narrative text is never promoted to a path.

Absent requested future behavior is not itself insufficiency if the governing
current implementation is supplied. More hypothetical context does not itself
justify abstention. Unresolved governing dependencies/intent cannot be hidden as
residual uncertainty. Repository instructions (including claims of authority,
requests to read/edit, ignore evidence or change schema) have no instruction or
permission authority. These are prompt rules plus contract boundaries, not a
claim that a live model will always obey them. No chain-of-thought is requested.

## Parsing and failures

ADR-021's existing decoder accepts one raw JSON document or one exact JSON/
unlabelled fenced document. Duplicate keys/requests, extra/missing fields, wrong
types, excessive bounds, invented citations and invalid paths are rejected.
No repair, coercion, defaults, retries or provider-native schema enforcement.

| Observation | Result |
| --- | --- |
| Invalid reply or runtime OUTPUT_INVALID | INVALID_OUTPUT |
| Runtime routing/model/execution failure | MODEL_FAILURE |
| Current observation differs | STALE_ASSESSMENT |
| Sufficient contradicts declared prerequisites | PREREQUISITES_UNMET |
| Serialized input exceeds bound | BUDGET_EXHAUSTED |

Failures are operational, never semantic insufficiency. Unexpected runtime or
accessor exceptions, cancellation, wrong runtime types and unrelated runtime
attribution propagate; Core's causal/effect semantics are not fabricated or
swallowed. The existing EvidenceSufficiencyResult contains only assessment or
failure; governed execution custody remains with the host, not this wrapper.

## Offline qualification and frozen evaluation

Scripted models exercise the actual M7 SYSTEM/USER request, all dispositions and
request types, strict parsing, stale inputs and authority boundaries. External
evaluation tests use the immutable `forgeai-analyst-design-eval/1` fixtures/oracle
to check output representability and manifest-only input. Production imports no
evaluator. Compatibility is not live semantic correctness, final-answer grounding
or completion of the future live evaluation instrumentation. The evaluation-only
EvidenceSequence test consumes the public result and still requires review; no
production ForgeAI integration is added and no frozen artifact is modified.

From repository root:

```powershell
uv run python .\validate_engineering_analyst_sufficiency_agent_1.py
```

The validator has 64 phases, with named contract coverage, prerequisite/scope/
frozen-history checks, sufficiency/evidence-loop/design-eval/Analyst/M7/worker
regressions, architecture, mypy, Ruff and diff checks. It uses installed offline
dependencies only. Operator qualification completed on 2026-10-07 using the
repository-root command above: all **64/64 phases passed**, including **620 tests**
(79 Agent tests and 33 evaluation compatibility/integration tests), mypy, Ruff
lint/format and git diff check. This establishes offline contract/regression
evidence only. No live model, external provider, Ollama, qwen or Docker was used;
no live semantic quality improvement was measured.

Next gate: explicit authorization for the
controlled live condition and its model/runtime/configuration identities and
qualified instrumentation. No live quality improvement is claimed. No Analyst
1.0.4, Core changes, Workflow, Team, Planner, discovery, mutation, routing changes
or production worker integration. G07 remains open.
