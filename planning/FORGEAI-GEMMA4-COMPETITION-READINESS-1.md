# FORGEAI-GEMMA4-COMPETITION-READINESS-1

Status: PLANNING ONLY — M1 PARTIAL; M2 BLOCKED ON OFFICIAL HARNESS CONTRACTS.
Baseline: `fd9ce282249067a0c68187d2ff56447d8fd29108`.
Verification: NOT RUN — Awaiting maintainer execution.
NO LIVE EXECUTION OR SUBMISSION AUTHORIZED.

## Decision and ownership

Design one competition-specific application using the official declarative
submission boundary, with one Gemma agent initially. Do not ship the ForgeAI CLI
as a presumed Kaggle entry point. Do not build a second generic agent framework.
Keep harness configuration and any allowed sandbox skills in a future isolated
`experiments/gemma4_competition/` tree, pending M1. This path is proposed, not created.
Keep generic product behavior in its current owners; extract reusable helpers
only after two concrete consumers share semantics and authorization/effects.

The [requirements register](GEMMA4-COMPETITION-REQUIREMENTS.md) distinguishes
indexed official evidence from missing contracts. Exact tool binding cannot be
implemented honestly until R1–R7 are resolved. This is a conditional engineering
path, not a valid submission or a competition compliance claim.

Existing qualification is bounded maintainer evidence, not Kaggle qualification.
DeepSeek remains NO_MODEL_QUALIFIED / MODEL_NOT_QUALIFIED.
GLM remains KEEP_GLM53_NOT_ADMITTED. Pilot ADMISSIONS remains empty.
No prior task is reopened and no KiSSKI admission transfers to Gemma.

## Prioritized gap matrix

| Priority / capability | Class | Existing owner / public interface | Competition action and limit |
| --- | --- | --- | --- |
| P0 submission/tool contract | CREATE | No verified Kaggle adapter | Pin official schema and minimal starter first; R1–R7 block binding. |
| P0 task authority | ADAPT | `forgeai.domain`, `forgeai.repository_context`; product confirmation/preflight | Separate pre-authorized competition task root/actions/budget; never bypass product confirmation or forge an operator approval. |
| P0 repository reads | REUSE | `legoai_engineering.repository.api.inspect_text`; `RepositoryText`, `InspectionRequest`; `repository.ports.RepositoryWorkspacePort` | Pure bounded text search reusable where sandbox packaging permits; filesystem port needs genuine sandbox semantics, not host reads. |
| P0 mutation/check boundary | ADAPT | `repository.mutation_ports.RepositoryMutationPort`; `checks.ports.EngineeringCheckPort`; authorized wrappers in composition | Use official tools as sole competition effect owner. Do not claim substitute conformance until failure/cancellation/authorization contracts match. |
| P0 model execution | EXCLUDE from submission initially | `legoai.runtime.api` public model values; `legoai.runtime.local.open_local_host` in product composition only | Kaggle owns inference. No remote KiSSKI host, credentials or private adapters in submission. Public `ModelPort` is available for independent product work, not assumed compatible with harness tools. |
| P1 coding/review | ADAPT | `legoai_engineering.coding.api.CodingAgent`, `reviewer.api.IndependentReviewer` | Public reusable product components, but their bounded proposal/review contracts differ from an ADK tool loop. Reuse criteria, not private parsers or forced wire formats. |
| P1 evidence and context | ADAPT | `forgeai.repository_context.ContextPreflight`, `ContextItem`, application worker/review/rework | Competition provenance records and stale-snapshot rejection; do not import application internals into Core. |
| P1 repository graph | CREATE | `repository.structure.RepositoryStructure` provides structure, not a complete semantic graph | Bounded Python symbol/import/reference index with unresolved edges; language fallback to text. Optional provided graph requires freshness/provenance checks. |
| P1 instruction discovery | CREATE | Preflight is not a general repository-instruction resolver | Ancestor/applicable instruction collection, deterministic precedence, bounded reads, conflict reporting; instruction text cannot authorize effects. |
| P1 budget/feedback | CREATE | Existing worker has one bounded rework | Separate task ledger, deterministic tool-outcome categories and capped competition repairs; product worker unchanged. |
| P2 sandbox implementation | EXCLUDE | `sandbox.docker.DockerSandbox`, `checks.sandboxed.SandboxedEngineeringChecks` | Keep for product/local qualified scope; do not nest Docker or assume PYTHON_CHECKS image in Kaggle. |
| P2 tuning/multi-agent | EXCLUDE initially | None required | LoRA optional after ablation evidence; no delegation without measured benefit. |

Inspected `examples/forgeai/README.md`, composition.py, repository_context.py,
Engineering README/public API modules and `src/legoai/runtime/api.py`.
ADR-014/026 public host ownership applies: consumers must not import
`legoai.reference.*` or `legoai.runtime._composition.*`. No new Port proposed.

## Minimal competition flow (proposed, not official tool schemas)

1. Accept issue plus harness repository identity and immutable run policy.
2. Discover bounded paths and applicable instructions; reject escapes/symlinks
   per verified harness policy. Record truncation and missing evidence.
3. Retrieve lexical matches and nearby definitions/tests first. Later add typed
   graph edges, each tied to file hash and source span. Never treat an inferred
   call edge as confirmed dependency or complete context.
4. Produce a small plan with target paths, evidence references and check intent.
   Model plans are proposals; deterministic scope checks precede effects.
5. Apply the smallest patch through the official approved mutation tool only.
   Reject stale evidence, unapproved paths, hidden-test access and policy changes.
6. Run permitted checks through the official sandbox; preserve exit status,
   timeout, truncation and environment errors. Never map missing checks to pass.
7. Allow initially at most one repair after failed validation (design parameter,
   not Kaggle rule). Further budgets require development evidence and re-freeze.
8. Stop on success, budget exhaustion, unsafe scope, uncertain effect or repeated
   identical failure. No blind replay of mutations. Submit only through the
   verified completion interface; no guarantee that an intermediate patch survives.

Use a monotonic task deadline and aggregate session ledger. Reserve budget for
final checks and patch handoff before planning. Charge retrieval, graph building,
model reasoning/output, tools and setup; numeric limits remain M1/M3 decisions.
At each call enforce remaining wall time, context allowance, tool count and
output cap. Deterministic summaries preserve error locations and evidence IDs;
they never manufacture successful outcomes. Log run/config/model/harness hashes,
patch hash, tool outcomes and actual budget usage; exclude secrets and raw hidden
tests. Rebuild graph entries for changed files before subsequent decisions.

## Strategy and first slice

First slice: FORGEAI-GEMMA4-OFFICIAL-HARNESS-CONTRACT-1.
Resolve R1–R7 with official artifacts and record exact configuration/tool schemas,
versions, bounds and allowed extension points. Then M2 creates a single-agent
starter-derived baseline with no graph, reviewer swarm or LoRA. Do not invent a
local harness emulator to fill missing official contracts.

Optimize valid end-to-end execution before search sophistication. Compare graph
retrieval to lexical retrieval at identical budgets; keep it only with evidence.
Paper work proceeds in parallel with experimentation, but no agents are delegated
in this planning slice. See [research](GEMMA4-RESEARCH-PLAN.md) and
[milestones](GEMMA4-IMPLEMENTATION-MILESTONES.md). No novelty/improvement claimed.

## Local documentary gate

Run the new validator from repository root in the existing locked environment:

```powershell
uv run --locked --offline --no-sync python .\validate_forgeai_gemma4_competition_readiness_1.py
if ($LASTEXITCODE -ne 0) { throw 'Gemma 4 competition planning validation failed' }
```

It checks only scope, required documentary controls and whitespace; it
does not validate Kaggle rules or execute any harness/model. The pre-existing
GLM validator working edit is pinned and preserved separately from this slice.

## Official-contract follow-up

Maintainer supplied LOCAL DOCUMENT CHECKS PASSED for the readiness slice above.
Its earlier verification line describes the implementation handoff, not current
evidence. [Official contract review](../experiments/gemma4_competition/OFFICIAL-CONTRACT-REGISTER.md)
confirms the newer four-variant staff announcement, but M1 remains PARTIAL and
M2 blocked on package/schema/rules evidence. Current follow-up validation is
pending; do not use the earlier validator as proof of harness compliance.

## Official artifact reconciliation — 2026-10-18

Current decision: M1_PARTIAL_ADDITIONAL_ARTIFACTS_REQUIRED; M2 BLOCKED.
The [official contract register](../experiments/gemma4_competition/OFFICIAL-CONTRACT-REGISTER.md)
contains the authoritative reconciliation and conditional minimal M2 specification.
The source register pins all 23 supplied files by raw SHA256 and byte size.
Earlier statements that no local artifacts/rules were inspected describe the
previous review, not the current evidence. Both complete rules captures, notebook
source and sample configuration have now been inspected without execution.
HARNESS_README, package/compiler/tool source and scorer limits remain unavailable.
Notebook model allowlisting is not package enforcement. R1–R7 remain open/partial;
paper generic leaderboard terms versus judged-Writeup requirements require
clarification. M1 is not complete; no dependent M2 implementation is authorized.
The single-root, no-LoRA baseline remains the smallest proposed implementation.
Graph library demonstrations do not prove graph-tool contract or measured benefit;
research comparisons remain matched-budget, independent and unexecuted.

The previous official-harness documentary validation passed per maintainer output.
New reconciliation verification: NOT RUN — Awaiting maintainer execution.
Run from repository root, existing locked environment, no new environment variables:

```powershell
uv run --locked --offline --no-sync python .\validate_forgeai_gemma4_official_artifact_reconciliation_1.py
if ($LASTEXITCODE -ne 0) { throw 'Gemma 4 official artifact reconciliation failed' }
```

Expected: local document checks passed; M1 partial; M2 blocked.
NO IMPLEMENTATION, LIVE EXECUTION OR SUBMISSION AUTHORIZED.
