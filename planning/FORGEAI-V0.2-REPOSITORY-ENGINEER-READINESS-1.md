# FORGEAI-V0.2-REPOSITORY-ENGINEER-READINESS-1

Status: LOCAL DOCUMENT CHECKS PASSED - maintainer execution reported.
Verification: Maintainer successfully ran `validate_forgeai_v0_2_repository_engineer_readiness_1.py`.
Recorded result: `FORGEAI-V0.2-REPOSITORY-ENGINEER-READINESS-1 LOCAL DOCUMENT CHECKS PASSED; FORGEAI_V0_2_IMPLEMENTATION_READY; NEXT: FORGEAI-REPOSITORY-CONTEXT-PREFLIGHT-1; V0.2 NOT QUALIFIED; NO IMPLEMENTATION OR LIVE EXECUTION AUTHORIZED`.
This records the documentary check only; historical reasoning below is preserved.
Baseline: `593fcbc42c976003af0942af1bfccefea55eff04`.
This is an implementation-readiness recommendation, not v0.2 qualification or
permission to implement the selected slice. This review creates only this document
and its documentary validator. No production, dependencies or ADRs change. ADR-027 remains
Deferred; Generative Media credential architecture is outside this review.

## 1. Current ForgeAI execution flow

Source is authoritative for behavior. Qualification below is attributed to recorded
maintainer evidence, not to tests executed during this review. Source identifiers
refer to the evidence register in section 2; symbols and focused tests identify
the particular contract rather than an entire directory as proof.

```text
CLI: explicit repo, objective, 1–8 create/update targets, constraints, 0–8 context files
  -> trusted ForgeAIConfig and fixed check/model profiles
  -> public Model host + authorized repository/coding/mutation/check adapters
  -> workspace guard; committed clean Git start required
  -> optional PROJECT check-environment preparation; unchanged Git anchor check
  -> remote disclosure admission when applicable
  -> CodingAgent acquires exact target/reference evidence and makes one governed call
  -> strict structured proposal parser; paths/operations/content bounds/preconditions
  -> exact escaped diff preview + identity-bound operator approval (default deny)
  -> authorized mutation, once; partial/uncertain effects retained on failure
  -> configured sandboxed checks in order; execution failures stop
  -> unchanged HEAD and changed-path integrity gate
  -> if only repairable code findings: spend the single rework allowance
  -> otherwise independent Reviewer after checks pass, using final changed files
  -> ACCEPT succeeds; INSUFFICIENT_EVIDENCE stops; CHANGES_REQUIRED can spend rework
  -> rework: current target/reference reads, bounded feedback, fresh Model context,
     another exact proposal approval, mutation/checks/review; second attempt terminal
  -> typed TaskResult/TaskEvidence + bounded CLI summary; no commit or push
```

`RepositoryTaskWorker._run/_attempt/_review/_rework` [S02] confirms this ordering.
There is no repository analyst, instruction discovery, planning agent, recursive
context search or sufficiency-agent call in this production sequence. PROJECT
preparation is a separate pre-model effect; it must not be confused with checks
running after patch approval [S03, S09]. Remote disclosure is also distinct from
read authorization and mutation approval [S03, S16].

## 2. Current qualified capabilities and source register

The [ForgeAI README](../examples/forgeai/README.md), sections “Status”, “ForgeAI
v0.1”, “One bounded rework”, “Explicit project check profile” and qualification
records, reports local Windows/Docker Desktop qualification with replay models.
Its “Explicit remote model profile” records synthetic TLS qualification, not
named-provider or live coding quality. Older statements about absent remote
support or pending historical runs do not override current source or later
records. [Public Model composition](../docs/model-composition.md) describes the
same disclosure/Secret ownership. No claim here extends those environments.

| ID | Exact production/document source and symbols | Focused evidence / limit |
| --- | --- | --- |
| S01 | [domain.py](../examples/forgeai/src/forgeai/domain.py): TaskRequest, TaskEvidence, TaskFailure, MAX_ATTEMPTS | [test_domain.py](../examples/forgeai/tests/test_domain.py); typed task and evidence, not repository understanding |
| S02 | [worker.py](../examples/forgeai/src/forgeai/worker.py): RepositoryTaskWorker._run/_attempt/_review/_rework | [test_worker.py](../examples/forgeai/tests/test_worker.py): test_final_state_integrity, test_denied_check_starts_no_sandbox; [test_rework.py](../examples/forgeai/tests/test_rework.py) |
| S03 | [composition.py](../examples/forgeai/src/forgeai/composition.py): ForgeAIConfig, prepare_run, local_profile | [test_architecture.py](../examples/forgeai/tests/test_architecture.py), [test_v01_product.py](../examples/forgeai/tests/test_v01_product.py); trusted wiring owns paths, grants, model and sandbox |
| S04 | [cli.py](../examples/forgeai/src/forgeai/cli.py): _parse, main, preview, terminal_approver, summarize | [test_v01_supervision.py](../examples/forgeai/tests/test_v01_supervision.py): test_4_displayed_approved_and_applied_identity_are_one, test_7_8_oversized_patch_is_refused_not_truncated |
| S05 | [coding/api.py](../packages/legoai-engineering/src/legoai_engineering/coding/api.py): CodingAgent.propose, _parse; [coding/values.py](../packages/legoai-engineering/src/legoai_engineering/coding/values.py): CodingRequest, CodingEvidence, CodingProposal | [test_coding_m4.py](../packages/legoai-engineering/tests/test_coding_m4.py), [test_coding_context.py](../packages/legoai-engineering/tests/test_coding_context.py); strict JSON proposal, not native provider-constrained decoding |
| S06 | [coding/definition.py](../packages/legoai-engineering/src/legoai_engineering/coding/definition.py): coding_definition; [coding/authorized.py](../packages/legoai-engineering/src/legoai_engineering/coding/authorized.py): AuthorizedCodingEvidence | [test_v01_context.py](../examples/forgeai/tests/test_v01_context.py): test_instruction_text_in_context_stays_repository_data, test_context_disclosure_is_never_mutation_authority, test_review_feedback_cannot_add_context_and_reviewer_sees_none |
| S07 | [repository/ports.py](../packages/legoai-engineering/src/legoai_engineering/repository/ports.py): RepositoryWorkspacePort; [repository/local.py](../packages/legoai-engineering/src/legoai_engineering/repository/local.py): LocalRepositoryWorkspace | [test_workspace.py](../packages/legoai-engineering/tests/test_workspace.py); bounded listing/read, link and boundary refusals, no hard synchronous I/O deadline |
| S08 | [repository/structure.py](../packages/legoai-engineering/src/legoai_engineering/repository/structure.py): RepositoryStructurePolicy; [repository/structure_authorized.py](../packages/legoai-engineering/src/legoai_engineering/repository/structure_authorized.py): AuthorizedRepositoryStructure.acquire | [test_structure.py](../packages/legoai-engineering/tests/test_structure.py): test_authority_each_listing_and_release, test_stability_no_retry, test_bounds; two equal bounded listings are not an atomic content snapshot |
| S09 | [checks/_commands.py](../packages/legoai-engineering/src/legoai_engineering/checks/_commands.py): _arguments; [checks/preparation.py](../packages/legoai-engineering/src/legoai_engineering/checks/preparation.py): inspect_check_project, prepare_check_environment | [test_project_check_profile.py](../examples/forgeai/tests/test_project_check_profile.py): test_model_cannot_change_profile_or_installation_command, test_dirty_repository_does_not_start_preparation; [test_checks_sandboxed.py](../packages/legoai-engineering/tests/test_checks_sandboxed.py) |
| S10 | [repository/mutation.py](../packages/legoai-engineering/src/legoai_engineering/repository/mutation.py): FileChange, RepositoryChangeSet; [repository/mutation_authorized.py](../packages/legoai-engineering/src/legoai_engineering/repository/mutation_authorized.py): AuthorizedRepositoryMutation | [test_mutation.py](../packages/legoai-engineering/tests/test_mutation.py), [test_authorized_effects.py](../packages/legoai-engineering/tests/test_authorized_effects.py); authority and byte preconditions remain separate |
| S11 | [git/ports.py](../packages/legoai-engineering/src/legoai_engineering/git/ports.py): GitRepositoryPort.inspect; [git/local.py](../packages/legoai-engineering/src/legoai_engineering/git/local.py): LocalGitRepository.inspect | [test_git.py](../packages/legoai-engineering/tests/test_git.py); HEAD and changed/untracked paths, not a general Git command API |
| S12 | [review.py](../examples/forgeai/src/forgeai/review.py): render_proposal, checks_material, check_rework_constraints; [reviewer/api.py](../packages/legoai-engineering/src/legoai_engineering/reviewer/api.py): IndependentReviewer | [test_review.py](../examples/forgeai/tests/test_review.py), [test_v01_check_rework.py](../examples/forgeai/tests/test_v01_check_rework.py): test_21_no_third_attempt_is_representable, test_23_24_check_text_and_model_claims_grant_no_authority |
| S13 | [analyst/authorized.py](../packages/legoai-engineering/src/legoai_engineering/analyst/authorized.py): AuthorizedRepositoryEvidence.acquire | [test_analyst.py](../packages/legoai-engineering/tests/test_analyst.py), [test_v01_context.py](../examples/forgeai/tests/test_v01_context.py): test_denied_disclosure_rejects_before_model; exact allowed paths and current authorization per read/final release |
| S14 | [analyst/sufficiency.py](../packages/legoai-engineering/src/legoai_engineering/analyst/sufficiency.py): EvidenceManifest, SufficiencyDisposition; [analyst/api.py](../packages/legoai-engineering/src/legoai_engineering/analyst/api.py): RepositoryAnalyst | [test_sufficiency_envelope.py](../packages/legoai-engineering/tests/test_sufficiency_envelope.py), [test_analyst_sufficiency_semantics.py](../packages/legoai-engineering/tests/test_analyst_sufficiency_semantics.py); declarations/advice cannot prove semantic completeness |
| S15 | [CONTENT-DISCOVERY R4 record](FORGEAI-CONTENT-DISCOVERY-ANALYST-QUALITY-R4.md), frozen gates and mechanical decision | Recorded 14b/Analyst 1.0.3 condition: insufficient correctness 5/11, six false-sufficients; stop prompt modification. Not a claim about every model or later experiment |
| S16 | [remote.py](../examples/forgeai/src/forgeai/remote.py), [runtime/api.py](../src/legoai/runtime/api.py), [runtime/local.py](../src/legoai/runtime/local.py) | [test_remote_profile.py](../examples/forgeai/tests/test_remote_profile.py); public Model host, supported S1 and per-invocation disclosure reused, not implemented in ForgeAI |
| S17 | [ADR-026](../adrs/ADR-026.md), [public execution API](../src/legoai/runtime/api.py) | [test_governed_execution.py](../tests/integration/composition/test_governed_execution.py); available public facade, not an additional ForgeAI credential/effect authority |
| S18 | [evaluation/content_discovery1/wiring.py](../examples/forgeai/evaluation/content_discovery1/wiring.py), [runtime identity record](FORGEAI-ANALYST-SUFFICIENCY-SAFETY-RUNTIME-IDENTITY-2.md) | Evaluation-only read/structure/Chat wiring; identity qualification explicitly does not establish semantic safety or a production worker integration |

## 3. Target v0.2 definition

BOUNDED REPOSITORY ENGINEER: one attended, local, clean committed Python
repository, one engineering objective, explicit read/disclosure scope, a bounded
evidence bundle, operator-confirmed edit targets and exact proposal approval,
approved contained checks, independent review and at most one repair.
Start with the qualified src/tests/pyproject layout. Success may be an implemented
candidate with evidence, or an honest insufficient/blocked result before mutation.
No autonomous company, unattended service, project manager, deployment/incident
operator, multi-agent organization or self-improving loop is required.

Useful v0.2 reduces the operator's need to find every context file while retaining
the operator's scope decisions. It does not promise arbitrary-repository support,
perfect architecture comprehension, or correctness solely from passing checks.

## 4. A–S capability walkthrough

Task: “Add a bounded validation rule to an existing src/inventory module and tests,
preserving its public contract and repository instructions.” Status describes the
current production worker, not capability existence elsewhere in the repository.
IMPLEMENTED_AND_QUALIFIED refers only to the recorded local/replay scope [S01–S04].

| Item | Required behavior | Current classification | Exact source/test evidence and residual |
| --- | --- | --- | --- |
| A | Establish repository identity/scope | IMPLEMENTED_AND_QUALIFIED | S01 TaskRequest; S02 _run; S03 ForgeAIConfig; S11 inspect; test_worker.test_final_state_integrity. Explicit bound root, clean committed start; no root search |
| B | Inspect repository structure | PARTIAL | S07/S08 exist with test_structure; S03 prepare_run does not wire structure into the worker |
| C | Locate relevant files | PARTIAL | S04 --target/--context; S06 test_create_targets_receive_existing_context_exactly. Operator selection only; S18 experiments are not production discovery |
| D | Discover local instruction hierarchy | ABSENT | S03/S06 disclose only exact selected references; test_no_context_sends_no_context_and_reads_nothing_else; no AGENTS/CLAUDE hierarchy stage |
| E | Use applicable architecture/contracts | PARTIAL | S05 CodingEvidence and S06 supplied read-only text can carry selected documents; no applicability/completeness enforcement |
| F | Understand tests/check commands | PARTIAL | S03 local_profile and S09 fixed commands, PROJECT metadata; no general repository-command discovery or task-specific adequacy proof |
| G | Plan before editing | PARTIAL | S05 CodingProposal summary/reasons/risks/unknowns precede mutation; no separate scope/evidence plan before code generation |
| H | Identify affected files | PARTIAL | S01/S05 targets bound by operator; no target discovery; test_v01_check_rework.test_8_22_rework_cannot_add_a_target |
| I | Avoid speculative refactors | PARTIAL | S01 constraints, S04 approval, S12 review criteria constrain intent; semantic relevance still model/operator judgment |
| J | Generate bounded patch | IMPLEMENTED_AND_QUALIFIED | S05 _parse/CodingProposal; test_coding_m4. Bounded full-file CREATE/UPDATE proposal; CLI renders a diff; live quality unqualified |
| K | Validate structure before mutation | IMPLEMENTED_AND_QUALIFIED | S05 _parse; S04 test_13_malformed_coding_output_is_diagnosed; S10 exact byte preconditions |
| L | Obtain exact mutation authority | IMPLEMENTED_AND_QUALIFIED | S02 _attempt; S04 identity-bound approval test; S10 authorized mutation independently gates use |
| M | Apply only approved changes | IMPLEMENTED_AND_QUALIFIED | S02 _attempt; S10 test_mutation/test_authorized_effects; conflicts stop, no blind replay |
| N | Run only approved deterministic checks | IMPLEMENTED_AND_QUALIFIED | S03 configured CheckRequest plan, S09 closed argv, S02 denied-check test. Trusted profile/grants, not model-generated shell commands |
| O | Interpret check failures | PARTIAL | S02 distinguishes code findings from infrastructure; S12 bounded feedback; test_v01_check_rework.test_6_rework_feedback_is_bounded_check_output. Semantic repair quality unqualified |
| P | One bounded repair | IMPLEMENTED_AND_QUALIFIED | S01 MAX_ATTEMPTS=2; S02 _rework; S12 test_21_no_third_attempt_is_representable; each mutation asks again |
| Q | Independent final review | IMPLEMENTED_AND_QUALIFIED | S02 _review, S12 IndependentReviewer/test_review. Distinct Agent identity; same model binding, not independent weights or correctness proof |
| R | Report evidence/risks/limitations | PARTIAL | S01 TaskEvidence/LIMITATIONS, S04 summarize, S12 render_proposal. Missing context-selection/instruction provenance and coverage report |
| S | Preserve partial/failed effect truth | IMPLEMENTED_AND_QUALIFIED | S02 _finish/_attempt, S10 mutation partial/uncertain results; test_worker/test_mutation. No durable resume or automatic rollback claim |

No A–S requirement is waived as NOT_REQUIRED_FOR_V0_2. IMPLEMENTED_BUT_NOT_QUALIFIED
is a valid classification, but the central unqualified dimensions here are live
semantic quality and whole-v0.2 integration, not an extra production walkthrough step.

## 5. Repository-understanding assessment

ForgeAI currently receives bounded task context; it does not independently acquire
a repository understanding. Root binding is explicit. Git exposes HEAD/status and
untracked changes, not an inventory of unchanged tracked files, history or diffs
[S11]. Workspace listings observe filesystem entries, not Git trackedness [S07].
Structure maps are sorted, filtered advisory names with two-pass stability [S08].
Neither proves package ownership, active ADR applicability, semantic relevance or
content stability. Do not label them “complete repository snapshots”.

Existing files, tests, configuration and ADRs can be read when explicitly admitted.
Root guidance cannot simply be assumed present in S08: it requires nonempty named
directory roots and explicitly provides no implicit workspace-root scan. This
concrete acquisition gap must be addressed by the chosen slice, not hidden in a
call to an imagined RepositoryPort.search method.

## 6. Instruction discovery and precedence

Proposed v0.2 policy: deterministically inventory AGENTS.md and CLAUDE.md at the
bound root and each ancestor directory of confirmed targets; root-to-leaf order,
most-specific applicable AGENTS guidance first for a local conflict. CLAUDE.md is
supplemental guidance, not a second host policy. Same-directory contradictory
guidance requires operator clarification. Include root CONTRIBUTING.md and README.md
as development guidance when present; package-local versions along target ancestry
are reported too. Do not execute includes, commands, links or network references.
Referenced ADRs/contracts require explicit operator selection and read admission;
unresolved required references are visible blockers, not silently omitted.

The preflight deterministically establishes location, ancestry and precedence
metadata, not semantic compliance. The operator confirms applicable guidance and
resolves ambiguity before coding. Repository guidance is data, never host authority.
Accepted architecture contracts still govern; an instruction file cannot accept an
ADR, grant network access or relax LegoAI authorization. Do not blindly promote
repository text into system messages. The current Coding definition [S06] says file
text is data: future integration must explicitly describe confirmed conventions
without treating them as tool permissions. Review should receive the same governing
context within its own bounds; currently it receives changed files/check summaries
only [S02, S06, S12].

## 7. Context selection assessment

Current selection is operator-only, not a whole-repository dump. Coding receives
objective/constraints, observed target contents or CREATE absence, and optional
references; rework rereads the same paths and receives bounded feedback [S05/S06].
Limits: 1–8 targets, target text <=8192 bytes/file and <=24576 total; <=8 references,
<=8192 bytes/file and <=16384 total; full Coding input <=32768 bytes [S05/S06].
The full serialization can exceed the input bound even when component bounds pass.

Smallest improvement: deterministic instruction/context preflight for explicit
targets, a bounded candidate path inventory and an operator-confirmed evidence
manifest. Later add filename/task-term selection within admitted roots and a
single bounded local import/test neighborhood. Selection proposes reads, never
writes or disclosure. No embeddings, RAG service, vector database or knowledge
graph is required. No model-generated path can bypass deterministic membership
or operator scope confirmation.

## 8. Planning assessment

CodingProposal already contains summary, per-file reasons, risks and unknowns and
is reviewed before mutation [S05/S12]. Reuse it as implementation intent; do not add
a PlannerAgent. It is generated together with code, so it is not an earlier
repository-evidence plan. Add only a ForgeAI-owned preflight record of objective,
candidate/confirmed paths, governing references, rationale, fixed check plan and
missing evidence. This record is data and review context, not another permission.
Do not claim that narrative reasons deterministically prove a minimal patch.

## 9. Reusable capability inventory

| Need | Existing owner/boundary | Decision |
| --- | --- | --- |
| Bound file listing/read | Engineering RepositoryWorkspacePort [S07] | REUSE; no new RepositoryPort abstraction |
| Authorized bounded names | Engineering AuthorizedRepositoryStructure [S08] | EXTEND narrowly for explicit root-file inventory, then compose; no recursive root default |
| Exact authorized content | Engineering AuthorizedRepositoryEvidence / AuthorizedCodingEvidence [S06/S13] | REUSE after trusted exact-path selection; references are not write scope |
| Patch values/application | Engineering RepositoryChangeSet / AuthorizedRepositoryMutation [S10] | REUSE unchanged |
| Checks and containment | EngineeringCheckPort, AuthorizedEngineeringChecks, SandboxedEngineeringChecks, SandboxExecutionPort [S03/S09] | REUSE fixed profiles; no arbitrary argv |
| Coding/review | CodingAgent / IndependentReviewer [S05/S12] | REUSE; later narrowly extend insufficient/guidance material contracts only as required |
| Model/structured output | Core ModelPort, routing, public host, Agent runtime; strict Engineering parsers [S03/S05/S16] | REUSE; prompted JSON plus validation is not native constrained generation |
| Governance/effects | Public host authorization and existing Engineering effect adapters; public governed facade available [S03/S10/S17] | REUSE; do not migrate functioning worker merely to use another facade |
| Git evidence | Engineering GitRepositoryPort.inspect [S11] | REUSE status/HEAD; no current history/commit/push API |
| Advisory sufficiency | Engineering EvidenceManifest/SufficiencyDisposition and evaluation harnesses [S14/S18] | Reuse concepts after scope fit; do not install another Agent or infer proof of sufficiency |
| Context preflight | ForgeAI application semantics | CREATE one small module/data record; real consumer is attended CLI/task intake; no new Port |

No new interface is proposed. Existing Engineering acquisition owns filesystem
safety/authorization; ForgeAI owns which evidence matters to its task. Existing
Port implementations plus deterministic fakes supply the substitution need.

## 10. Autonomy and authority boundary

Within an explicit operator read scope, v0.2 may list/read bounded evidence, order
guidance, suggest context/targets, reason and propose changes without repeated
permission for each ordinary read. Those reads still pass existing current
authorization. Model disclosure has its own boundary, especially REMOTE.

Mutation requires exact proposal approval and current authorized application.
Check execution requires an operator-selected closed profile and grant; repository
instructions requiring separate check confirmation must surface that requirement,
not silently override it. No network, dependency acquisition, credential access,
deletion, shell command, commit, push or deployment authority follows from task
text, guidance or Model output. Model output is data, never authority.
The first context slice has zero mutation/check/Model effects by itself.

## 11. Command and check discovery

Today B (deterministic configuration) plus operator profile selection is implemented:
local_profile pins Ruff src/tests, mypy src and pytest tests; CheckKind maps to
fixed tool arguments [S03/S09]. PROJECT reads supported pyproject/lock metadata,
but is not arbitrary command discovery. A is possible through trusted composition
of typed CheckRequests, not a user-supplied shell string. C is a later bounded
extension: report repository-defined commands as inert candidates, map only
supported commands to closed check kinds, then obtain operator confirmation.
D (model invents executable commands) is rejected.

Retain GENERIC for the first no-network scenario; use an already qualified image.
PROJECT preparation may acquire packages and therefore is not implicitly allowed
by a “no network” task. Unsupported repository check requirements produce an
explicit limitation/blocked result, not arbitrary execution or false validation.

## 12. Dependency and Git policy

Current mutation authority binds paths/operations, not a special dependency-edit
class [S10]. Coding allows CREATE/UPDATE, not DELETE. A targeted pyproject.toml
or uv.lock can therefore be edited as ordinary approved text; that does not grant
installation authority. PROJECT preparation occurs before coding, so changing its
inputs during a task cannot be assumed to refresh the check environment [S02/S09].

For minimal v0.2, reject dependency-manifest/lock changes from the ordinary task
profile with an explicit separately-authorized-task outcome. No uv add, pip/npm
install or arbitrary fetch. A later dependency slice must distinguish approved
text changes, acquisition, prepared-image identity and checks of the final inputs.

Reuse read-only HEAD/status and exact CLI diff from acquired before/proposed after
bytes. No general Git diff/history API currently exists; unchanged tracked-file
inventory would require a separate bounded extension if a real task needs it.
Full history, branch creation, commits, push and PR operations are not required
for this v0.2. Preserve no automatic reset, rollback, commit or push.

## 13. Large-repository bounds

Retain S08 ceilings: <=8 declared non-overlapping roots, depth <=6, <=512 entries,
<=64 listing calls per pass, <=16384 serialized bytes and <=512 scanned entries
per directory. Mandatory hidden/sensitive/generated exclusions remain; they are
not a secret scanner. All acquisition failures are explicit; no partial map called
complete, no silent top-N drop of mandatory instructions.

For the selected preflight, root-file inventory is explicit and counts against the
same budgets. Read only confirmed exact paths; keep existing Coding limits above.
Guidance plus source/test context that cannot fit produces CONTEXT_INCOMPLETE with
the failing bound and required operator narrowing. No automatic truncation of
guidance, fabricated summaries or repeated search-until-success. A future bounded
search can rank task terms then one import/test neighborhood with stable path
tie-breaking, but ranking cannot assert sufficiency. Do not call all untracked
files safe; the clean-start gate currently refuses untracked changes too.

## 14. Insufficiency behavior

Current task acquisition failures expose denied/unavailable/budget categories;
Reviewer can return INSUFFICIENT_EVIDENCE. Coding's schema requires 1–8 changes
and has no explicit “no safe patch” success alternative [S01/S05/S12]. `unknowns`
is narrative, not an abstention gate. This is a concrete implementation gap.

First preflight adds a ForgeAI-only CONTEXT_INCOMPLETE result before any Coding
invocation, preserving precise missing/unreadable/conflicting/over-budget evidence.
That covers deterministic insufficiency only. A later minimal CodingResult/schema
extension must support a typed abstention if insufficiency is discovered while
reasoning, with zero proposal approval/mutation and bounded clarification data.
Do not encode it as an empty invalid patch or generic provider failure.

S14 distinguishes declarations from semantic completeness. S15's frozen R4 condition
failed sufficiency gates; S18's later runtime identity qualification explicitly
does not prove safety reasoning. Neither justifies giving an Analyst permission
to decide read scope or to certify a task ready. Operator confirmation and honest
coverage reports remain necessary; uncertainty is allowed, not a model defect to
hide with retries.

## 15. Multi-agent decision

Keep CodingAgent and IndependentReviewer. No PlannerAgent, RepositoryAgent,
TestAgent, SecurityAgent or ManagerAgent. Deterministic repository inspection is
not an Agent. The reviewer provides a distinct assessment role, not authority or
independent model weights. No evidence justifies a larger agent organization.

## 16. Model versus system gaps

| Category | Concrete observation | Response |
| --- | --- | --- |
| ARCHITECTURE_GAP | No new Core authority or Port is required for the selected preflight; task-specific selection belongs to ForgeAI | Keep ownership; no architecture decision prerequisite identified for this slice |
| IMPLEMENTATION_GAP | Missing production structure/instruction intake, context provenance, pre-coding insufficiency and dependency-edit guard | Implement bounded application behavior using existing public boundaries |
| MODEL_QUALITY_GAP | Live coding/review reliability unqualified; R4 Analyst false-sufficiency failures in its recorded condition | Evaluate frozen task/model conditions separately; do not add framework machinery |
| PROVIDER_LIMITATION | Native schema-constrained generation is not established by strict JSON parsing or synthetic provider smoke | Keep parser/refusal; separately qualify exact provider/model protocol |
| ENVIRONMENT_LIMITATION | Qualified Windows/Docker and supported Python layout/check image; PROJECT preparation may need acquisition | Refuse unsupported/no-network preparation requirements; do not silently run host checks |
| EVALUATION_GAP | No end-to-end v0.2 real-repository held-out task qualification | Add offline/replay controls first, then separately authorized live quality evaluation |

## 17. Real-use acceptance scenario

Given a clean committed local Python Git repository with src/inventory/stock.py,
tests/test_stock.py, root AGENTS.md and a package-local AGENTS.md specifying its
public contract, task “reject negative reservation quantities and add tests”,
no network, no installation, and an already available qualified checks image:

1. Establish root and HEAD, list only admitted scope, find both guidance levels,
   select relevant source/test/config evidence, and show coverage and exclusions.
2. Operator confirms read bundle and target CREATE/UPDATE scope. Missing governing
   reference, conflicting instruction or budget failure stops before Coding.
3. Produce bounded proposal intent and patch; refusal/abstention is truthful when
   evidence is inadequate. Instruction text cannot authorize extra effects.
4. Decline control writes zero files. Acceptance binds exactly displayed bytes;
   stale target preconditions refuse. Only approved files may change.
5. Run only the approved fixed checks in the sandbox, no acquisition/network.
   Infrastructure failure stops; code findings can trigger one newly approved repair.
6. Review final changed text plus applicable governing evidence; final SUCCESS
   requires deterministic gates and ACCEPT. No third attempt; unknown effects remain.
7. Report initial/final HEAD, changed files, approvals, checks, review, provenance,
   unresolved risks and limitations. No commit/push; no global correctness claim.

Objective pass criteria: expected instruction order/paths and exclusion list;
zero out-of-scope reads/writes/calls; exact approved/applied identity; hidden test
asserting negative quantity rejection; existing positive behavior retained; required
check outcomes observed; <=2 attempts; terminal review ACCEPT for the answerable
case. Negative fixtures must produce explicit non-success with truthful effects.
Replay validates plumbing, not live model usefulness. The complete scenario needs
later integration/quality evidence; the next slice alone cannot qualify v0.2.

## 18. Gap matrix, ranked by implementation dependency

| Gap ID | Required v0.2 behavior | Current evidence | Classification | Owner | REUSE / EXTEND / CREATE | Security/effect impact | Complexity | Testing requirement | Blocker? | Proposed slice |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| G01 | Authorized bounded inventory including root guidance | S07/S08 exist; S03 not wired | IMPLEMENTATION_GAP | Engineering acquisition + ForgeAI composition | EXTEND | Read/structure authority only; explicit root scope | Medium | Bounds, root files, exclusions, stale maps, deny-before-I/O | Yes, first prerequisite | Selected context preflight |
| G02 | Instruction ancestry and operator-confirmed evidence bundle | S06 exact manual context only | IMPLEMENTATION_GAP | ForgeAI | CREATE | Guidance/disclosure not permission | Medium | Nested/conflicting/missing/oversized guidance; zero Model calls | Yes, alongside G01 | Selected context preflight |
| G03 | Explicit deterministic context insufficiency | S01 acquisition errors; no preflight artifact | IMPLEMENTATION_GAP | ForgeAI | EXTEND | Stop before model/mutation; no fake completeness | Small | Missing required evidence and all bound failures | Yes, alongside G02 | Selected context preflight |
| G04 | Bounded relevance/target suggestions from task | S18 experiment; S04 manual targets | IMPLEMENTATION_GAP | ForgeAI | EXTEND | Suggestions cannot widen target/read/disclosure authority | Medium | Held-out relevant files, ambiguous tasks, operator rejection | Yes for full target-discovery use; not prerequisite to G01 | Later bounded selection |
| G05 | Reasoning-stage abstention and governing evidence in review | S05 requires changes; S02 reviewer lacks reference context | IMPLEMENTATION_GAP | Engineering coding contract + ForgeAI review | EXTEND | No manufactured patch; reference budget/currentness preserved | Medium | Typed no-patch output, review context, stale guidance, no retry | Yes before complete v0.2 claim | Later minimal coding/review integration |
| G06 | Dependency/check requirements surfaced separately | S09 PROJECT prep before coding; S10 ordinary file mutation | IMPLEMENTATION_GAP | ForgeAI profile | EXTEND | Deny ordinary dependency edits; no automatic install/command execution | Small | Manifest/lock change blocked; unsupported check command inert | Yes before general feature tasks | Later task-admission guard |
| G07 | Exact approved patch, contained checks, bounded repair/effect truth | S02/S04/S09/S10/S12 | IMPLEMENTATION_GAP | ForgeAI integration | REUSE | Preserve qualified authority and effect contracts | Small | Existing v0.1 regressions plus new intake integration | No missing mechanism; regression gate | Integrate unchanged mechanisms |
| G08 | Reliable live proposal/review and abstention quality | S15 and README limits | MODEL_QUALITY_GAP | Evaluation/operator | REUSE | Model remains advisory even when scores improve | Medium | Frozen real tasks, negative tasks, leakage/authority controls | Qualification blocker, not coding prerequisite | Later quality evaluation |
| G09 | Exact provider and no-network runtime availability | S09/S16; provider smoke separate from worker | ENVIRONMENT_LIMITATION | Operator/deployment | REUSE | Existing image only; no implicit live authorization | Small | Offline refusal and preinstalled-image control | Deployment prerequisite | Existing environment preflight |
| G10 | End-to-end repository-engineer evidence | No production v0.2 pipeline | EVALUATION_GAP | ForgeAI | CREATE | No premature product qualification | Medium | Section 17 replay then separately authorized live evaluation | Release blocker | Final bounded v0.2 acceptance |

No generic architecture rewrite is a blocker. G01–G03 are one cohesive intake
increment; G04–G06 are subsequent gaps, not automatically authorized work.

## 19. Ordered implementation sequence

1. G01–G03: selected deterministic context preflight; qualify it independently.
2. G06: conservative dependency/check admission before extending task selection.
3. G04: bounded relevant-file suggestions and operator-confirmed target selection.
4. G05: minimal coding abstention and reviewer governing-context integration.
5. G07/G10: full pipeline regression and section 17 deterministic acceptance.
6. G08/G09: separately authorized provider/environment and live quality evidence.

Existing patch/approval/check/rework machinery is reused throughout. No step adds
an unlimited loop. Do not proceed past any slice's maintainer validation gate.

## 20. Exactly one next implementation slice

Selected next slice: `FORGEAI-REPOSITORY-CONTEXT-PREFLIGHT-1`.

Scope: deterministic read-only preflight for the existing explicit-target Python
profile. Inventory declared source/test/document roots; discover root and target-
ancestor guidance; produce an operator-reviewable bounded path/provenance/coverage
record and either READY_FOR_CONTEXT_CONFIRMATION or CONTEXT_INCOMPLETE. It does
not call a model, execute checks, prepare PROJECT environments, mutate or start a
coding run. The confirmed exact paths can be supplied to existing --context;
integrated handoff must re-read/re-authorize them, not reuse stale material.

Concrete implementation path:

- REUSE RepositoryWorkspacePort.list_entries/read_text, typed paths, existing
  workspace link/bound checks, Git inspect and authorized content acquisition.
- EXTEND Engineering's existing RepositoryStructurePolicy/AuthorizedRepositoryStructure
  with an opt-in bounded root-file inventory. Root listing uses None only inside
  the bound workspace; emit admitted regular root-file entries, never recursively
  traverse every root directory. Preserve existing default behavior, two passes,
  exclusions, per-list/final authorization and budgets. No new Port/action issuer.
  The existing REPOSITORY_STRUCTURE_ACTION must be explicitly granted by trusted
  preflight composition; do not infer it from a Chat or mutation grant.
- CREATE ForgeAI `repository_context.py` for task-specific guidance ancestry,
  candidate classification and coverage/status values. Root/ancestor guidance
  selection is deterministic; semantic conflict resolution is operator-owned.
  No direct filesystem bypass, private Core imports or copied authorization logic.
- EXTEND CLI/composition with a separate attended read-only preflight entry point
  and operator read-root configuration. Bind root/HEAD, policy and observed content
  digests; report unavailable or changed evidence explicitly. Do not auto-convert
  discovery into model disclosure, editable scope or a runnable task.
- Preserve <=8 final reference paths/16 KiB total and full coding-budget limits.
  If mandatory instruction files themselves exceed those bounds, stop and request
  narrowing/another reviewed capability change. Do not silently discard instructions.

Likely files: `examples/forgeai/src/forgeai/repository_context.py` (new),
`domain.py`, `composition.py`, `cli.py`; Engineering
`repository/structure.py` and `repository/structure_authorized.py`;
focused `test_repository_context.py` (new), existing structure/context/CLI/architecture
tests and ForgeAI documentation. No worker, Model, Secret, mutation or sandbox
mechanism change is expected for this standalone preflight. Public acquisition
extension needs its existing package/install regression controls.

Required tests: known-good root and nested guidance; absent optional files versus
unreadable required files; root inventory defaults unchanged; symlink/reparse and
case-alias refusal; exclusions and every byte/count/depth/list bound; denied/revoked
authorization before read/release; two-pass changes; dirty/wrong repository;
instruction injection inert; no model/mutation/check/network/credential calls;
stable deterministic order; context-only files never become targets; oversized
mandatory guidance reports incomplete. A successful preflight must not certify
semantic sufficiency or architecture compliance.

Qualification claim after maintainer evidence only: ForgeAI can prepare a bounded,
authorized, operator-reviewable instruction/context inventory for explicitly
scoped local Python tasks, or report context incomplete before any Model/effect
execution. This is not yet repository-engineer task success or live quality.

Why it wins: source acquisition is the prerequisite for reliable plans, relevant
patches and task-specific validation. It removes concrete manual context omission
without touching qualified effect mechanisms or adopting the Analyst's failed
sufficiency judgment. Scope is narrower than automatic target discovery.

## 21. Explicit non-goals and design review

No generic workflow engine, service locator, agent framework expansion, vector
database, knowledge graph, unattended daemon, unlimited loop, model-controlled
authority, duplicated authorization, arbitrary shell tool, dependency acquisition,
commit/push, remote deployment or media credential work. No ADR is created/accepted.

SRP/SoC: Engineering acquires safely; ForgeAI selects task context; Model reasons.
OCP: opt-in root-file support preserves old structure defaults. LSP: existing Port
listing/read failure contracts remain. ISP: no new interface. DIP/LoD: public
composition and Ports only, no private Core traversal. DRY: reuse authorization,
paths, byte budgets and exact approval. KISS/YAGNI: one deterministic preflight
record rather than more agents or a retrieval platform. Application engineering
semantics legitimately require ForgeAI code; “everything by config” is not a goal.

## 22. Qualification strategy and maintainer handoff

This review's validator performs document/static invariants only: two-file review
scope against the baseline, source links/symbols, complete A–S and gap matrices,
single decision/slice, authority limits, positive/negative document fixtures,
working and staged text/whitespace. It never imports production or runs product
behavior, tests, builds, models, providers or network. Textual checks cannot prove
the review's reasoning or future implementation correctness.

Unrelated maintainer edits to AGENTS.md and CLAUDE.md were already present when
work resumed. They are preserved, excluded from this review's changes, and pinned
by normalized text digests in the validator. Their staged versions may match the
baseline or those pinned edits; further instruction edits require an explicit
update to this scope record before validation. Both review files must be either
unstaged or staged together.

From the repository root, use the existing locked uv environment; Git and Python
are required. No credentials, special environment variables or new dependencies.

```powershell
uv run --locked --offline --no-sync python .\validate_forgeai_v0_2_repository_engineer_readiness_1.py
if ($LASTEXITCODE -ne 0) { throw 'ForgeAI v0.2 readiness validation failed' }
```

Expected: all document phases pass and exit code zero. Paste the complete output.
No validator was run internally. Future implementation requires a separate user
request; each implementation slice needs its own deterministic contracts, boundary
controls, typing/lint/format and relevant existing regressions run by the maintainer.
Only separately authorized live evaluation can assess actual coding usefulness.

Decision meaning: requirements and an owner-local implementation path for the
selected next slice are concrete; no new architectural authority decision is
required to start that slice. The whole v0.2 product remains unimplemented and
unqualified. There is exactly one selected next slice, named in section 20.

FORGEAI_V0_2_IMPLEMENTATION_READY
