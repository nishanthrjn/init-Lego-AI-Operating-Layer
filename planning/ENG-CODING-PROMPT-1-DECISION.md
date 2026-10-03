# ENG-CODING-PROMPT-1 — decision recommendation

Status: Decision ready for maintainer review; recommendation only, not implementation authority.
Date: 2026-10-03

## Evidence and scope

The post-LQ1.4 measurement at commit 2b2255a54bcf84216ed56fc640c9e574e88a7f7c
used qwen2.5-coder:7b, digest
sha256:dae161e27b0e90dd1856c8bb3209201fd6736d8eb66298e75ed87571486f4364,
Ollama 0.35.1, fixture/hidden revisions 1, N=3 / 12 runs, and the same hardware
class as the post-LQ1.3 run. Coding: 7 valid, 5 change_fields_invalid, no
response_not_json. All five first rejected entries (index 0, attempt 1)
omitted only reason: pager-boundaries 1, temperature-units 1, text-slug 3.
Path/operation/content omissions were zero at that rejection stage. This does
not establish validity of their values or later entries. Seven hidden passes,
three CHECKS_FAILED, four REVIEW_OUTPUT_INVALID, zero application successes,
zero rework. Representation was non-blocking. No implementation defect was
established. LQ1.4 only observes; model-quality changes are not caused by it.

## Source trace and semantics

- [coding/definition.py](../packages/legoai-engineering/src/legoai_engineering/coding/definition.py):
  coding-agent v1.0.0 supplies static SYSTEM guidance. The model creates reason
  in its JSON response; neither caller nor runtime supplies a default.
- [coding/api.py](../packages/legoai-engineering/src/legoai_engineering/coding/api.py):
  `_parse` requires exactly path, operation, content, reason for each entry,
  checks path/kind against acquired targets, creates FileChange with trusted
  digest, then collects reason strings in change order. A missing key rejects
  the whole proposal before that entry's path/operation/content validation.
  Request JSON contains objective, constraints and targets/current_text;
  output guidance lives in the definition, not an application prompt override.
- [coding/values.py](../packages/legoai-engineering/src/legoai_engineering/coding/values.py):
  CodingProposal stores `reasons: tuple[str, ...]`, repr-excluded, exactly one
  per change. `_strings` / `_bytes` enforce nonblank UTF-8, <=1024 bytes each.
  CodingResult retains the AgentResult and validates definition attribution.
- [repository/mutation.py](../packages/legoai-engineering/src/legoai_engineering/repository/mutation.py):
  FileChange contains path, kind, expected digest and text, not reason.
  [worker.py](../examples/forgeai/src/forgeai/worker.py) applies only
  `coding.proposal.changeset`; mutation authorization and effects do not use reason.
- [domain.py](../examples/forgeai/src/forgeai/domain.py): AttemptEvidence retains
  CodingProposal, and TaskEvidence retains attempts. This is inspectable typed
  local evidence, not automatic durable canonical Evidence or an audit journal.
- [review.py](../examples/forgeai/src/forgeai/review.py): render_proposal pairs
  changes and reasons with strict zip and sends each explanation with its
  path/operation/material identifier. The worker passes that text into ReviewRequest.
- [reviewer/api.py](../packages/legoai-engineering/src/legoai_engineering/reviewer/api.py):
  IndependentReviewer serializes request.proposal into its USER input. It consumes
  rendered text, not CodingProposal directly. Reasons are shown on both attempts.
  Rework constraints use review findings/check outcomes, not a direct reasons input.
- [Engineering README](../packages/legoai-engineering/README.md), M8.3 section;
  [consuming guide](../packages/legoai-engineering/docs/CONSUMING.md), compatibility
  section; [M8.3 plan](M8.3-BOUNDED-CODING-PLAN.md): reasons are ordered metadata
  separate from M4 changes. CLI renders the proposal summary, not each reason;
  LQ1 raw reports exclude rationale text. Diagnostic proposal fingerprints include
  reasons in memory for classifier agreement, never as report content.

Reason is a model-supplied per-change explanation useful to review and inspection.
It is descriptive metadata with a real completeness/alignment invariant, not
write authority, correctness proof, or a verified account of internal reasoning.
The existing sources require its presence and shape, not the truth or quality
of its explanation. Dropping it would preserve M4 execution mechanics but lose
that proposal/review contract guarantee.

## Current prompt assessment

Small exact fragments from coding_definition():

> Changes contains 1-8 objects with exactly path, operation, content, reason.

> Reason is nonblank text <=1024 bytes.

Thus the prompt does more than ask for JSON. All four keys are enumerated,
`exactly` already makes them mandatory, and reason's nonblank bound reinforces
that requirement; it does not literally use MUST or mandatory. Path semantics,
operation matching (create/update) and complete-content semantics are explicit.
Reason has a type/size constraint but no explicit semantic definition. There
are no CREATE/UPDATE examples or exact JSON skeleton. The contract does not
reasonably grant permission to omit explanatory metadata, although the prose
could be made more salient. Omission does not establish model intent.

## Alternatives

| Option | Assessment |
| --- | --- |
| A unchanged | Safe and coherent; continues rejecting omissions with no additional cost. Leaves the measured five first-entry failures unaddressed; those proposals are not proven otherwise valid. |
| B clarify existing prompt | Recommended bounded experiment: retain all validation and explicitly describe every change's mandatory explanation. Small, reusable Engineering change; effectiveness remains unmeasured. |
| C shared schema guidance | Not justified yet. Potential consumers are Coding, Reviewer and Analyst, but all are in Engineering; Reviewer finding_invalid is not yet a demonstrated schema-guidance need. No independent package/provider requirement establishes a Core abstraction. |
| D optional reason | Changes CodingProposal completeness and consumers' assumptions. Requires an explicit missingness representation and updated review rendering; no requirement shows explanations are dispensable. Success counts alone do not justify it. |
| E synthesize/default | Fabricates or substitutes rationale and confuses provenance. An explicitly labelled system explanation would be a different contract, not a silent default. |
| F retry/repair | Extra governed model calls need new execution identity, budgets, effect/cancellation/failure rules and evidence of the rejected attempt. Local repair would still invent rationale. Changes one-call-per-attempt and comparison conditions. |
| G provider-native enforcement | Separate from C. JSON validity alone does not require reason; schema enforcement would need an adapter capability and explicit unsupported-provider behavior. Do not embed an Ollama setting in CodingAgent. Not justified by current scope. |

C would require deciding schema ownership/subset, AgentDefinition to ChatRequest
propagation, provider capability negotiation, and fail-closed unsupported-provider
handling versus an explicitly declared guidance-only mode (never silent downgrade).
Adapters would need mappings, bounds, refusals/error semantics and conformance
tests. Generic contracts and behavior versions, supported provider declarations,
and report condition identity would change. Revisit only with independent
consumer requirements and supported-provider evidence. No new dependency now.

## Recommendation and ownership

Recommend **ENG-CODING-PROMPT-1 — explicit per-change output-contract guidance**.
Extend the existing reusable Engineering definition; do not create a Core facility
or put ForgeAI-specific wording in the Agent. This still belongs in Engineering
if ForgeAI disappears: every CodingAgent consumer uses the same proposal contract.

Proposed scope, only after approval:
- State every change MUST contain exactly the four keys, none optional.
- Define reason as a brief explanation of why that specific change addresses the
  supplied objective/constraints; it is unverified narrative, not authorization
  or a claim that checks ran. Do not request hidden reasoning.
- Add a compact four-key shape with metasyntactic value placeholders, clearly
  labelled as a shape illustration, never literal output. No example source,
  task-specific values, fixture hints or separate CREATE/UPDATE examples.
- Preserve all existing bounds, exact validation, target/kind authority, duplicate
  protection, one call per attempt, model effects, provider independence and
  ForgeAI sequencing. Do not change Reviewer or add diagnostics.

## Versioning and ADR disposition

[docs/agent.md](../docs/agent.md) explicitly requires an operator-managed new
version for changed behavior. [ADR-017](../adrs/ADR-017.md) identifies reusable
behavior by definition/version; its status is Proposed with scoped implemented
M7 authority, not Accepted. [ADR-018](../adrs/ADR-018.md) has the same scoped
status and governs Engineering ownership. [ADR-021](../adrs/ADR-021.md) is
Accepted; its unchanged-version rationale depended on unchanged instructions.
A prompt change MUST therefore get a new Coding behavior version. Recommend
1.0.1 (from 1.0.0), subject to maintainer approval. Version's implementation
is an exact ordered triple, explicitly not inferred SemVer compatibility;
that numeric choice is a proposal, not a repository-mandated patch policy.
AgentId and public API shapes remain unchanged; definition equality changes.
Package release version is a separate boundary and need not change for this
unreleased definition revision. Reviewer/Analyst versions stay unchanged.

No new ADR is required for this recommendation: no architectural mechanism,
public schema, dependency direction or authority changes. The M8.3 plan already
placed this specialization under ADR-018 without a new ADR; docs/agent.md
already governs behavior revisions. Record this as a versioned definition slice.
ADR-INDEX was inspected; do not allocate an ADR merely for wording. C/D/E/F/G
would require a new assessment of significant contract/architecture change.
ADR-021's historical prompt non-goal remains intact; do not edit its decision.

## Qualification and live follow-up

Likely implementation files: coding/definition.py; focused Coding definition/
request tests and existing coding tests as needed; Engineering README; this
planning record and evaluation README; proposed validate_engineering_coding_prompt.py.
No Coding parser/values, mutation, Reviewer, Core or adapter production edits.

The proposed validator (not created) should be runnable as
`uv run python .\validate_engineering_coding_prompt.py` and prove:
- raw and ADR-021 fenced valid replay proposals retain identical parsed values;
- missing reason, unexpected keys, duplicates, bad scope/kind/content remain rejected;
- no synthesis, repair, additional call or effect changes;
- captured governed model requests contain the new guidance and new definition
  version, within instruction/total prompt bounds, with USER inputs unchanged;
- existing Coding replay/authorization/M4 cases, attribution checks and import
  boundaries hold; Reviewer definition/request behavior is unchanged;
- ForgeAI-1/2/3 and the full LQ1 validator remain green, including classifier
  agreement, privacy and observer non-interference for the new condition.
Full qualification remains operator-run; no tests or live calls are run for
this decision-only documentation change.

LQ1 RunMetadata has a ForgeAI commit but no dedicated Agent/prompt revision
field or override flag. Do not invent one. Use a committed clean runtime and
record coding-agent 1.0.1 plus its exact commit in the evaluation record and
new output-directory name; the report commit resolves the precise definition.
A +dirty-runtime identity alone cannot identify uncommitted prompt bytes.
Do not expand report metadata in this slice without a separate need.
Fixture/hidden revisions stay 1 because their contents stay unchanged; schema 3
can stay because diagnostic meanings do not change. Old reports are immutable.

After approval, implementation and qualification, a fresh operator-run measurement
uses qwen2.5-coder:7b, reverified installed full digest (same if still installed),
N=3, fixture/hidden revision 1, same hardware/check image, observed Ollama version.
Label it a NEW PROMPT-CONTRACT condition. Compare reason omissions, valid Coding
proposals, check/review reach and hidden outcomes descriptively; no success
threshold, causal guarantee, benchmark or retroactive equivalence claim.

## Separate follow-up and stop boundary

Reviewer finding_invalid occurred 4/4; all four corresponding hidden outcomes
passed. Investigate its contract separately after the Coding decision; do not
infer which finding field failed or change its prompt/schema/diagnostics here.
Target discovery, M8.4, Workflow, Team, routing and check-failure rework remain
deferred. No implementation or additional live measurement in this decision.

CODING CONTRACT DECISION READY — RECOMMEND ENG-CODING-PROMPT-1
