# ForgeAI target-discovery decision recommendation

Date: 2026-10-04. **Status: recommendation only; not implementation authority.**
Inspected HEAD: `469e8dd` (adopted master roadmap), following Coding 1.0.1 at
`a3951f3`. No tracked changes preceded this task. Git reports an inaccessible
pre-existing `examples/forgeai/.lq13-test-temp/`; it was not inspected or changed.

This refines roadmap G07, with G02/G09 authority and future retention implications.
It does not close Coding/Reviewer live-quality work. All contracts, limits, action
names and slices described as proposed below require maintainer approval and
subsequent qualification. No source, fixtures, tests, validators or ADRs are changed.

**Recommendation:** reuse `RepositoryWorkspacePort.list_entries` beneath a new
Engineering authorized structure-acquisition facade and immutable structure value.
Use a distinct fixed disclosure action. Make one bounded model selection over
existing disclosed files, then require explicit ForgeAI operator confirmation.
Reuse the current Coding/worker handoff unchanged. Initial model selection is
**existing-file selection only**; an operator can separately add an exact CREATE
target through the existing explicit-target path.

## 1. Current state trace

Source paths below are relative to repository root. `E` means
`packages/legoai-engineering/src/legoai_engineering`; `F` means
`examples/forgeai/src/forgeai`. These are locators, not proposed namespaces.

| Question | Current source-backed answer |
| --- | --- |
| Where do targets originate? | Operator `--target` flags in `F/cli.py`; `_target` parses create/update and constructs `CodingTarget(RepositoryPath(path), operation)`. Programmatic callers can construct the same public values. `main` constructs TaskRequest and passes those paths to `local_profile`. |
| What carries them? | `E/coding/values.py`: CodingTarget and CodingRequest; `F/domain.py`: immutable TaskRequest with 1–8 CodingTargets; `F/composition.py`: ForgeAIConfig.editable_paths is separately trusted operator configuration. |
| Who validates them? | RepositoryPath validates portable relative syntax; CodingTarget restricts operation and administrative paths; TaskRequest rejects duplicates, case aliases and nested targets. CodingRequest/evidence recheck bounds. `E/coding/api.py::_parse` requires a proposed change to match an acquired path and its requested operation exactly. |
| Who reads contents? | CodingAgent calls CodingEvidencePort.acquire. `E/coding/authorized.py::AuthorizedCodingEvidence` delegates UPDATE reads to `AuthorizedRepositoryEvidence.acquire` in `E/analyst/authorized.py`; that calls RepositoryWorkspacePort.read_text. CREATE does authorized parent listing and target absence checks, without disclosing the listing. |
| What action covers content disclosure? | `REPOSITORY_READ_ACTION = "read-for-model-analysis"`; authorized named-file reads and disclosure to the operator-associated model, not general directory-map release. Separate governed Chat authorization also applies. |
| What resource binds disclosure? | `E/_authority.py::_bind`: operation.subject equals the operator-bound workspace ConfigurationRef; resource_scope equals its instance; action must match. TenantContext must match in acquire. `F/composition.py::prepare_run` binds that reference to the explicit workspace and allowed_paths. Default scope string is `workspace`, not a path-level permission set. |
| What authorizes mutation? | `E/repository/mutation_authorized.py`: fixed `apply-repository-changes`, current authorization before apply. Grants come through the public host/operator configuration. |
| How is editable allowlisting enforced? | `local_profile` receives editable_paths; prepare_run puts them in AuthorizedRepositoryEvidence.allowed_paths. Coding evidence refuses targets outside that tuple, and the parser only admits changes matching acquired targets. **AuthorizedRepositoryMutation itself has no per-path editable allowlist**: it authorizes the workspace action and delegates the validated changeset. This is trusted composition, not a hostile-code sandbox. |
| Can Analyst list directories? | Its injected RepositoryEvidencePort exposes only acquire(targets, tenant), returning named file contents. RepositoryAnalyst has no listing method/tool. The underlying workspace can list; that does not make listings Analyst evidence. |
| Can Coding request more paths? | No tool loop or acquisition from output. `_parse` rejects unknown paths. The model may write arbitrary prose, but it cannot successfully add a structured change outside acquired targets. |
| Can Reviewer expand scope? | No. `F/review.py::rework_targets` retains original targets, changing already-applied CREATE to UPDATE; rework_constraints renders findings as labeled data. `F/worker.py` permits only one bounded rework. |
| Can Git reach the model? | `E/git/ports.py::GitRepositoryPort.inspect` provides HEAD and changed/untracked paths to operator/application checks. Worker uses it for clean-start/integrity. Coding/Reviewer rendering contains no Git status, branch, diff or history. This is the current governed path, not a claim that arbitrary callers cannot paste Git text manually. |
| Who knows structure now? | LocalRepositoryWorkspace lists one directory; AuthorizedCodingEvidence inspects CREATE parents; SandboxedEngineeringChecks gathers configured input trees; LocalGitRepository observes repository state; ForgeAI composition knows the host root and configured target/check paths. Operator/CLI know explicit targets. Analyst/Coding/Reviewer do not receive a repository map. |

The current sequence remains: confirmed task -> authorized current Coding evidence
-> one proposal -> authorized mutation -> sandboxed Ruff/mypy/pytest -> Git integrity
-> authorized review evidence -> independent review -> optional single rework.

Evidence inspected: [Engineering README](../packages/legoai-engineering/README.md),
[public consuming guide](../packages/legoai-engineering/docs/CONSUMING.md),
[ADR-018](../adrs/ADR-018.md),
[consumer-readiness plan](LEGOAI-CONSUMER-READINESS-PLAN.md),
[direction assessment](FORGEAI-4-AND-M8.4-DIRECTION.md),
[master roadmap](LEGOAI-FORGEAI-MASTER-ROADMAP-2026.md).
Existing regression evidence includes `packages/legoai-engineering/tests/test_coding.py`
(`test_request_cannot_expand_operator_scope`, authorization-before-I/O cases),
`tests/test_analyst.py` and `tests/test_authorized_effects.py` in that same package;
`examples/forgeai/tests/test_architecture.py::test_public_legoai_only_and_no_private_names`
and `examples/forgeai/tests/test_rework.py::test_rework_cannot_expand_scope`.
No tests were rerun for this decision-only task.

## 2. Four independent concepts

| Concept | What establishes it | What it does not establish |
| --- | --- | --- |
| Repository existence | Operator selects/binds a local workspace | Permission to disclose its names, contents or Git state |
| Structure disclosure | Explicit roots/filter policy plus current structure-disclosure grant and approved model destination | Content-read or mutation permission |
| Candidate selection | Validated advisory output over the disclosed map | Authority, correctness, completeness or permission to read candidate contents |
| Write authority | Operator-confirmed exact targets plus operator-owned policy and current effect grants | Permission to discover additional targets or skip mutation preconditions |

CodingAgent proposes; it never writes. The authorized mutation component writes.
Operator confirmation is a ForgeAI intent/configuration decision; it is not a
canonical Approval token or an automatic grant issued by model output.

## 3. Smallest reusable structure boundary

Proposed names are local Engineering vocabulary, subject to implementation review:
`RepositoryStructurePolicy`, `RepositoryStructure`, `AuthorizedRepositoryStructure`.
They reuse RepositoryPath, WorkspaceEntry and WorkspaceEntryKind. No Core types,
generic registry or provider-specific representation is needed.

| Alternative | Decision |
| --- | --- |
| Extend RepositoryWorkspacePort | Not needed: list_entries already has the right complete-or-fail one-directory semantics. Keep its signature and responsibility unchanged. |
| New low-level RepositoryStructurePort | Defer: no second acquisition semantics justify duplicating the existing workspace seam. |
| Pure immutable structure over existing workspace operations | Select for the result and deterministic validation/serialization helpers. Traversal itself performs I/O and must not be called pure. |
| Extend RepositoryEvidencePort | Reject: it promises exactly requested file texts. A directory-map result changes that responsibility and would contaminate Analyst's existing contract. |
| Authorized Engineering acquisition facade | Select: binds workspace, trusted structure policy, context, AuthorizationPort and clock; authorizes before every listing and before release. Similar ownership to AuthorizedRepositoryEvidence, without widening that class. |

The facade owns bounded traversal and authorization together. There is no public
“safe to disclose” marker a caller/model can set. A structure value can be built as
data for tests but confers no permission. The future selector must acquire/revalidate
through the trusted bound facade before each model call; it cannot treat a
deserialized map or matching digest as authorization. Pure helpers can validate and
serialize tuples; application code never imports `_authority` or private runtime
composition. Engineering may reuse its own private helper internally.

## 4. Model-visible information

| Candidate field | Disposition | Reason |
| --- | --- | --- |
| Workspace-relative path | INCLUDE | Minimal selection signal; exact spelling, no absolute host root. Paths themselves are confidential data. |
| FILE / DIRECTORY | INCLUDE | Distinguishes selectable files from layout context; reuse existing kinds. |
| Bounded root and coverage description | INCLUDE | Say the map covers selected roots with explicit exclusions, never the entire repository. It must not enumerate omitted names. |
| Depth | EXCLUDE as redundant field | Inferable from path; enforce it as a bound. |
| File size or size class | DEFER | Not necessary to choose initial file candidates; Port does not provide it. |
| Extension/type | EXCLUDE as extra field | Filename already carries suffix; do not infer a language or parse contents. |
| Git tracked/untracked/ignored, branch, diff, history | EXCLUDE | Different disclosure boundary; unnecessary for initial selection. |
| Timestamps, inode/device IDs, content digests | EXCLUDE | Acquisition internals or content/state disclosure without demonstrated need. |
| Project metadata read from files, dependencies, README text | DEFER | Content disclosure, requiring the separate read action and limits. |
| Absolute host paths, environment, grants, executable locations | EXCLUDE | No selection need; remain trusted configuration only. |
| Map hash, authorization IDs, tenant/principal identity | EXCLUDE from model input | Useful internal attribution, not a relevance signal. |

Initial policy denies **every dot-prefixed component**, including `.env`, `.env.*`,
`.git`, `.venv`, and dot directories, not merely hidden-file attributes. It also
denies case-insensitive components `secrets`, `credentials`, `private`, `node_modules`,
`build`, `dist`, `generated`, `vendor`, `__pycache__`. Operator-specific excluded
components and relative subtrees can only narrow this profile. No ignored-file
pattern is fetched from Git; `.gitignore` is neither parsed nor disclosed.

These names are a minimum deny set, not a privacy classifier. A path such as
`src/customer-acme-contract.py` remains sensitive even without a suspicious suffix.
An operator must authorize the chosen roots for the chosen model destination and
review the exact proposed map in a local preview before initial submission. Reject
or narrow roots/exclusions if names reveal confidential information. Preview shows
only filtered entries, never raw excluded names. Content stays unread.

Existing WorkspacePolicy excludes only exact component names and is not a hidden-path
filter. Reuse its minimum exclusions where expressible, then apply the additional
structure policy before adding an entry or traversing a directory. Existing adapter
validation can fail on an entry before that extra filtering; propagate failure
rather than weaken boundary checks to make discovery succeed.

## 5. Deterministic bounds and acquisition algorithm

The following are **proposed initial hard ceilings**, not measured optimal settings.
An operator may lower them, never enlarge them through task/model data.

| Dimension | Proposed bound / behavior |
| --- | --- |
| Roots | 1–8 explicit non-overlapping relative directory roots; no implicit whole-workspace `None` root. Dot/sensitive roots prohibited. Root entries count in the map. Root-level individual files can be manually targeted initially; do not widen to root scanning to include them. |
| Depth | At most 6 components from workspace root; roots count. Files at depth 6 permitted; admitted directory at depth 6 fails LIMIT rather than implying its unvisited subtree is complete. |
| Map entries | At most 512 total FILE/DIRECTORY entries, including configured roots. No truncation or top-N filtering. |
| Directory work | At most 64 list calls per complete pass; each bound workspace listing policy has max_entries ≤512, counting even excluded entries as the existing adapter does. At most two passes, hence ≤128 list calls and ≤65,536 scanned directory entries by this upper bound. |
| Bytes | Canonical model-visible map envelope ≤16,384 strict UTF-8 bytes, including entries and coverage description. Check before any model invocation. |
| Names | Existing RepositoryPath grammar and ≤240 code-point path bound; additionally strict UTF-8, ≤960 bytes/path and ≤128 code points/component. Reject unencodable text, format/control characters that could mislead preview, and case-fold aliases. Never normalize/rename paths to fit. |
| Exclusion configuration | ≤32 extra single-component names and ≤32 explicit relative excluded subtrees; immutable, validated with the same path bounds. Combined exact-name WorkspacePolicy must stay within its existing 32-name limit; remaining narrowing occurs in structure validation. Invalid policy fails before I/O. |
| Ordering | Traverse roots and child directories deterministically by exact relative path ordering; final entries globally sorted by path. Canonical serializer is fixed/versioned; no OS enumeration-order dependency. |
| Duplicates | Reject duplicate paths, case aliases, conflicting kinds and overlapping roots, including from fake/future adapters. No merging that hides ambiguity. |
| Overflow | Entire acquisition fails with LIMIT; no partial map returned, previewed as complete or sent. Operator may explicitly submit a narrower new request; no automatic restart. |

Each listing must return complete sorted direct children of the requested directory.
Validate every result's parent, path, kind and membership before use; do not trust an
adapter to return arbitrary paths or grandchildren. Do not traverse excluded entries.
No read_text call occurs. Roots are established as directories by a successful
list call. A first bounded pass builds the filtered map; a second identical bounded
pass must match before release. This detects some ordinary structural churn, not
an atomic snapshot or every transient change. The two passes share a hard total
call budget. They are validation passes, not retry on failure.

Preserve `E/repository/local.py` safeguards: checked root/ancestor identity,
link/reparse refusal, containment, same-device checks, regular single-link files,
directory-change detection and complete-or-fail behavior. Symlinks, Windows reparse
points, hard-linked files, special entries, invalid names, cross-device boundaries,
permission/I/O failures or changed root identity fail acquisition when encountered.
Excluded names need not be traversed to inspect their targets. UNC/device roots,
network filesystems and hostile concurrent namespace mutation remain unsupported.
This synchronous Port provides **no hard I/O deadline/cancellation guarantee**;
finite entry/call counts are not a wall-clock guarantee. Remote access cannot
inherit stronger promises by implementing this interface nominally.

## 6. Authorization model

Recommend the fixed action **`read-structure-for-model-analysis`**, following existing
`read-for-model-analysis` and the direction document's proposed naming. Do not reuse
the content action: CREATE parent inspection explicitly does not disclose listings.

| Concern | Proposed rule |
| --- | --- |
| Grant issuer | Trusted operator configuration via LocalHostConfig/OperatorGrant and host-issued SecurityContext. Neither selector nor preview manufactures grants. |
| Subject/resource | Existing workspace ConfigurationRef as operation.subject; resource_scope exactly reference.instance. No path list encoded in a scope string. Root/exclusion/model-destination association is trusted immutable composition, separate from workspace grant. |
| Tenant/workspace | Acquire tenant must equal the context's TenantContext; bind the same reference to the actual workspace adapter. Configuration/reference alone cannot prove a host directory identity. |
| Expiry/revocation | Re-evaluate current Governance with a fresh timestamp on every protected acquisition and release; no cached ALLOWED result. Expired/revoked/stale-policy authority stops subsequent work. |
| Approvals | Approval-bearing contexts refused as in ADR-018. ForgeAI confirmation is not consumption of a governance Approval. |
| Timing | Evaluate before the first list, before every subsequent list in both passes, before returning a bundle, and again immediately before the selector submits the authorized map to governed Chat. No discovery model call after a failed check. |
| Unavailable | Explicit authority-unavailable failure, not denial or implicit allowance. No fallback, partial release or retry. |
| Destination | Operator binds disclosure to the configured model destination/profile. Switching model destination, tenant, roots, policy or workspace invalidates prior consent and requires fresh acquisition/confirmation. |

Invariant: **denied disclosure -> zero model-visible structure** on that operation.
Earlier already-authorized disclosures cannot be recalled by later revocation; retain
their truthful effect facts. Collection and final authorization precede model-visible
serialization/submission. Governed Chat independently requires invoke-capability.

[ADR-005](../adrs/ADR-005.md) requires explicit scoped authority;
[ADR-007](../adrs/ADR-007.md) requires honest protected-handoff semantics.
The existing Engineering wrapper is a trusted local check-before-effect pattern,
not an atomic remote disclosure transaction. A final structure check and the Chat
dispatch are not automatically one linearized authorization event. Preserve that
limitation: do not claim revocation can stop a request already handed off. If review
requires stronger atomic cross-action handoff than ADR-018's current profile, stop
and resolve that narrower gap before implementation instead of inventing a guarantee.

## 7. Candidate-selection contract

Propose an Engineering `TargetSelectionProposal`, separate from CodingProposal and
RepositoryAnalysis. One bounded one-step Agent call over objective, constraints and
the authorized map; no filesystem/tool Port in the model, no content loop, no retry.
Reuse AgentRuntimePort and configured `engineering-reasoning` only after admission;
do not alter Coding/Analyst/Reviewer definitions or versions.

Proposed closed JSON output keys: `status`, `candidates`, `unknowns`.
Status is `succeeded` or `insufficient_evidence`; each candidate has exactly `path`
and `reason`. Candidates contain 0–8 distinct exact map FILE paths; success requires
at least one. For insufficient_evidence, candidates may be a partial advisory set
but unknowns must be nonempty. No candidate directory, operation, score, permission
or executable instruction is accepted. Reason is a nonblank descriptive explanation
≤1024 UTF-8 bytes, not correctness or authority. Unknowns are 0–8 nonblank strings
≤1024 bytes each. Accepted output ≤16,384 UTF-8 bytes; exact keys/types, duplicate
JSON-key rejection, ADR-021 raw/exact-fenced decoding. No repair or defaults.

Input objective ≤2048 UTF-8 bytes, constraints ≤8 x 1024 bytes, map ≤16,384 bytes;
validate complete serialized USER ≤32,768 bytes and total SYSTEM+USER ≤49,152 bytes.
Escaping/envelope overhead counts. Narrative can mention names not in the map; it is
untrusted prose and never parsed into targets. Candidate validation independently
requires exact disclosed membership, FILE kind, structure policy compliance and
existing CodingTarget UPDATE eligibility. A well-formed but unknown/excluded path
rejects the **whole** proposal; never silently drop it to produce apparent success.

### CREATE resolution

The earlier direction assessment suggested permitting a new filename under a mapped
parent. That conflicts with this task's stronger initial requirement that candidates
reference **only disclosed paths** and unknown paths fail. Choose the narrower
contract: model candidates are existing files; CREATE is manually entered by the
operator after a selection reports missing evidence/new-file need. Do not smuggle a
future filename through reason/unknowns parsing. Manual CREATE is a distinct
operator request, within operator policy and the current CodingTarget/M4 contract.
The model never successfully selects an undisclosed path in this initial profile.

## 8. Operator confirmation boundary

ForgeAI owns local preview, candidate presentation and the confirmation interaction.
Engineering owns bounded acquisition/selection and validation. Existing governance
owns actual effect authority. These responsibilities agree with the assembly guide's
application-ownership and public-composition principles.

Proposed interaction has two explicit consent points: approve the filtered map for
the configured model destination, then approve the **exact final target set** after
selection. An explicit operator policy may pre-authorize a known-safe structure
profile later; do not add an implicit “accept everything” default initially.

| Operator choice | Result |
| --- | --- |
| Accept all | Validate current candidates/policy, render final paths and UPDATE kinds, then confirm exact set. |
| Accept subset | Removed candidates are absent from task.targets and editable_paths. No hidden union with the original proposal. |
| Reject all / no confirmation | Terminal no-selection result; no worker invocation, Coding, mutation or checks. Discovery's prior model effect still exists. |
| Add manual path | Treat as operator input, not model candidate. Revalidate against separately configured operator-owned editing policy and current CodingTarget restrictions. Show path and CREATE/UPDATE explicitly before final confirmation. |

Manual paths may lie outside the disclosed map if inside the operator's independent
editing policy. This grants no structure disclosure retroactively. Mandatory
sensitive-path exclusions remain in this initial profile; overriding them requires
a separately reviewed policy, not typing a path at the prompt. Missing CREATE
parents remain unsupported; no directory creation. Reject empty final set as no
task, and reject >8, duplicate/case-alias or ancestor/descendant target sets.

Model text is displayed as untrusted text, never evaluated, shell-expanded or used
as configuration. Confirmation is tied to workspace, objective/constraints, map
identity, model condition and exact final targets; changing any requires renewed
confirmation. Initial implementation is process-local; loading an unsigned proposal
file cannot act as consent. Separate CLI invocations must reconstruct explicit
operator input and revalidate rather than trusting a saved “approved” flag.

## 9. Authority handoff into existing ForgeAI

After confirmation, the trusted application constructs an immutable tuple of
CodingTarget values: selected files are UPDATE; manually supplied CREATE/UPDATE
remain explicit. It constructs TaskRequest with original approved objective and
constraints, and ForgeAIConfig.editable_paths from **exactly that final tuple**.
Trusted local_profile/prepare_run binds the repository to the workspace reference
and existing read/mutation/check actions. Model outputs supply none of those grants,
scope strings, host paths, providers or executables. Discovery itself should run
with only structure and Chat authority, not pre-issued write/check grants.

The resulting worker can be reused unchanged. Current APIs can express this safe
handoff for their documented trusted-composition model. The additions needed are
the new discovery facade/action and ForgeAI confirmation/policy orchestration, not
a generic permission framework or a worker rewrite. Operator editing policy exists
as trusted configuration constraints; it must be established before candidate
selection and cannot be calculated from candidate relevance.

Do not misstate the guarantee: the mutation wrapper does not independently filter
every path. Safety relies on trusted composition, the exact evidence allowlist and
Coding parser. Hostile in-process code can call workspace-authorized mutation APIs;
this proposal does not strengthen that threat model. Qualification must capture the
constructed task/config and prove paths removed at confirmation cannot reach
mutation through the supported worker, including rework.

## 10. Analyst role and distinct-responsibility test

Keep RepositoryAnalyst unchanged. It analyzes supplied file text and validates cited
membership; feeding a synthetic map as a pretend file would violate that evidence
meaning. Adding structure acquisition/selection would materially change its contract
and require a behavior/version review, with no demonstrated benefit over composition.

Selection has a distinct input (names/kinds), output (advisory target candidates),
evaluation (selection precision/recall), and disclosure action. That justifies a
separate small Engineering specialization **if** deterministic filtering is
insufficient in the planned fixture evaluation; it does not justify a new Agent
runtime, tool loop or Team. Deterministic filters apply approved roots/exclusions
first. An objective-based heuristic is an evaluation baseline, not a substitute for
complete declared map coverage or authority.

Analyst is a credible second consumer of the discovery front end: select paths,
operator approves reads, then analyze real files. Code-search/refactoring consumers
are future possibilities, not existing adoption claims. If fixtures show a
deterministic selector is sufficient, stop before building the model selector.

## 11. Git disclosure

Exclude tracked/untracked/ignored status, branch, HEAD, diff, history and Git-derived
ranking from the model map. Current Git inspect is bounded read-only operator data;
it is not a disclosure grant or a complete tracked-file enumeration API.
Keep ForgeAI's clean-start and post-mutation integrity checks unchanged.

A filesystem entry that Git happens to ignore/untrack could still exist under an
approved structure root. **No Git status is disclosed, but this is not a guarantee
that every mapped file is tracked.** Approved roots/exclusions/preview must handle
that privacy concern. Do not advertise “ignored files excluded” without a separately
authorized mechanism; adding Git filtering would need a new justified decision.

## 12. Content-assisted discovery, later stage only

Names alone can be insufficient. Initial selection must be allowed to say so.
If measurement demonstrates a need, use this separately approved bounded stage:

`authorized map -> advisory candidate read paths -> operator confirms read subset
-> existing read-for-model-analysis authority -> AuthorizedRepositoryEvidence
-> existing Analyst -> operator confirms final editable targets`.

Reuse AuthorizedRepositoryEvidence unchanged for ≤8 exact named files and its
existing aggregate limits. Read permission is not write permission: read-only
context files need not become Coding targets. No directory traversal driven by
Analyst findings, recursive content search or iterative tool loop. If refined target
selection needs files outside the map/read subset, stop for another explicit
operator request. No automatic second model call in the initial selector slice.

## 13. Closed failure stages and effects

Proposed discovery-specific categories below are a planning vocabulary, not changes
to existing Core or Engineering enums. Public failures carry stage/category/counts,
not sensitive entry names or exception strings.

| Stage/category | Meaning and required outcome |
| --- | --- |
| CONFIGURATION_INVALID | Invalid roots/bounds/destination binding; no listing/model call. |
| AUTHORIZATION_DENIED | Scope/tenant mismatch, expiry, revocation or disallowed current policy; no subsequent listing/release/model call. |
| AUTHORITY_UNAVAILABLE | Current decision cannot be established; fail closed, distinguish from denial. |
| WORKSPACE_UNAVAILABLE | Missing root, permissions or I/O failure; no partial map. |
| BOUNDARY_VIOLATION | Escape, link/reparse, cross-device boundary or inconsistent adapter path; no map. |
| STRUCTURE_LIMIT_EXCEEDED | Depth, entries, bytes, calls or path bounds exceeded; no truncation. |
| UNSUPPORTED_ENTRY | Invalid kind/name/encoding or unsupported filesystem entry; no map. |
| STRUCTURE_CHANGED | Adapter reports CHANGED or two bounded acquisition passes differ; stop, never retry automatically. |
| MODEL_FAILED | Governed model denied/unavailable/failed; preserve AgentResult/effect classification, including UNKNOWN. No candidate handoff. |
| MODEL_OUTPUT_INVALID | Malformed JSON, wrong schema/type, duplicates or bounds; no repair/retry. |
| CANDIDATE_OUTSIDE_STRUCTURE | Structured path absent from map or not FILE; reject entire proposal before confirmation/handoff. |
| CANDIDATE_OUTSIDE_POLICY | Disclosed member not Coding-eligible or outside configured selection/editing policy; reject entire proposal. |
| OPERATOR_REJECTED | Explicit rejection is a normal terminal disposition, not provider failure. No Coding call/effect. |
| STALE_CONFIRMATION | Map/condition/confirmed target kind no longer matches revalidated state; invalidate confirmation and stop. |

Classification order is configuration, authority, acquisition, model execution,
syntax/shape, candidate membership, candidate policy, confirmation/revalidation.
Only the first failing stage is reported; it proves nothing about later fields.
Listing/model disclosure may already have happened before a later rejection;
“no Coding effect” must not be rendered as “no effects at all.” Preserve the
[ADR-008](../adrs/ADR-008.md) distinction between intended operation and attempts.
Timeout, cancellation and lost acknowledgment do not cause automatic replay or
imply remote/model effect NONE. A new operator request is a new explicit operation,
not an invisible retry by discovery.

## 14. TOCTOU and staleness

Create an internal deterministic digest of the versioned canonical filtered map,
including root/filter policy identity; bind its record to workspace reference,
operator configuration revision and acquisition time. This is advisory map identity,
not a filesystem snapshot, content digest, authority token or canonical Evidence.
Hashing paths does not anonymize them; keep digests in restricted records.

After model selection and before final target confirmation, reacquire under current
authority and compare the map/policy identity. A difference invalidates the proposal
for automatic handoff; operator can explicitly start a fresh discovery request or
manually specify targets. There is no refresh/reselection loop. Each reacquisition
has the same two-pass ceilings; the process-local initial flow allows at most two
acquisitions (initial and pre-confirmation), hence ≤256 list calls overall.
Waiting longer is not consent and cannot authorize a second model call.

Immediately after confirmation, construct the run using the same workspace and
approved values. Coding re-reads confirmed UPDATE targets, observes CREATE absence,
and M4 digest/absence preconditions remain authoritative at mutation. Replacements,
links, changed kinds and dirty Git start fail through existing checks. A path-only
map cannot detect a content change that preserves layout; Coding intentionally uses
current authorized content, not a supposed discovery snapshot. If an operator wants
approval of exact contents, that is a separate future content-bound approval scope.

No sequence of two scans eliminates races or ABA changes. Stable trusted local
namespace remains a prerequisite; hostile concurrent mutation is unsupported.
No map identity replaces current authority or proves mutation is safe.

## 15. Privacy and representation boundary

Model input contains only the approved filtered relative names/kinds and approved
objective/constraints, with fixed coverage wording. Directory/file names are quoted
as data; instructions embedded in names or model reasons confer no authority.
No bytes are read merely to answer a structure request.

Paths, roots, candidate reasons, unknowns, objectives, map bodies and local host
configuration are repr-excluded where stored. Operator preview is a deliberate
local disclosure channel; render control/format characters safely or reject them.
Public diagnostics/logs use closed stages, counts, elapsed time and safe correlation
IDs, never raw paths, reasons, model text, provider bodies or absolute paths.
Evaluation reports use synthetic fixture IDs, metrics and failure categories;
ground-truth fixture definitions may contain synthetic paths. Real customer map
content must not be copied into evaluation reports. No new LQ1 schema is implied.

Absolute paths may exist only in trusted local adapter/operator configuration,
as they do today in ForgeAIConfig. They are prohibited in map/proposal/model output
contracts and ordinary public diagnostics. Audit retention of relative paths, if
later introduced, needs explicit access/retention rules rather than assuming logs
are safe because paths are relative.

## 16. Evaluation design before implementation

The following are **fixture specifications to implement later**, not added files or
executed tests. Freeze a separate discovery fixture revision; do not change LQ1's
historical fixture/hidden revisions or retrofit its reports.

| Synthetic fixture | Structure and objective | Ground truth / expected observation |
| --- | --- | --- |
| Obvious target | `src/temperature.py`, unrelated helper, `tests/test_temperature.py`; change conversion rule | Required source + test pair; irrelevant helper is false positive. |
| Ambiguous target | `src/auth/reset.py`, `src/admin/reset.py`; underspecified reset request | Multiple acceptable hypotheses; insufficient_evidence expected until objective clarified. No forced arbitrary exact set. |
| Related files | Service, validator and separate tests for one feature | Explicit acceptable sets/minimal required files; measure partial recall. |
| Generated/vendor | Approved src root contains generated/vendor subtrees and real implementation | Forbidden trees absent from map; selecting their paths invalid. |
| Secret-like names | `.env`, `secrets/`, `credentials/`, `private/`, `.git/` and safe files | Zero forbidden path disclosure; include deceptive mixed-case variants. |
| Nested structures | Trees at and beyond depth ceiling | Boundary fixture succeeds at permitted file depth; deeper admitted directory fails before model. |
| Similar decoys | `src/billing.py`, `src/billing_old.py`, unrelated `tests/test_billing_ui.py` | Ground truth distinguishes relevance; measure decoy false positives. |
| CREATE required | Existing `src/auth/` with no reset implementation | Selector signals insufficient evidence/new-file need without returning an unknown path; operator manually supplies exact CREATE target under policy. Measure creation requirement recognition separately. |
| Tests separated | Implementation under src, tests under independent approved tests root | Both roots considered; no privilege inferred from root membership. |
| Renamed module | Fixture before/after a module rename | Old path invalid against new map; changed map before confirmation gives STALE_CONFIRMATION. |
| Irrelevant large tree | Many irrelevant admitted entries; another version excludes that subtree | Overflow is LIMIT, not top-N success. Explicit narrower policy succeeds with truthful coverage. |
| Adversarial acquisition | Case aliases, fake adapter out-of-parent entries, symlink/reparse/special entries, authority revoked between lists | Fail closed; no model-visible map. Platform-specific real filesystem cases qualified locally. |

Ground truth records acceptable target sets, required paths, allowed alternative
sets and forbidden paths **before** model runs. Hidden selection truth is never
included in model prompts. Include cases with no justified selection. For every
set metric score against a documented coherent acceptable set; do not use the union
of alternatives to reward mutually inconsistent choices. Report per-fixture raw
counts and aggregate denominators, not only one score.

| Metric | Definition |
| --- | --- |
| Candidate precision | Correct proposed existing-file candidates / proposed existing-file candidates, against acceptable ground truth. Empty prediction precision is N/A, not 100%. |
| Candidate recall | Correct required existing-file candidates / required existing-file candidates. Empty prediction with nonempty required set is zero. CREATE-only/ambiguous no-set cases reported separately. |
| Exact-set rate | Valid proposed sets equal to an accepted full set / eligible runs; malformed/failed eligible runs count as misses, not dropped. |
| Operator correction rate | Runs where a proposal needs additions/removals or rejection / runs presented; also report failures before presentation and changes per run. Manual CREATE is a separate expected intervention. |
| Unauthorized-path proposal count | Structured candidates outside disclosed membership or configured policy, even though rejected; keep distinct from an actual disclosure/effect violation. |
| Disclosure violation count | Any prohibited name/content/host path sent to the model; **zero acceptable failures**. |
| False omission count | Required existing target paths absent from proposal; separate policy-excluded/unavailable ground truth to expose profile limitations. |
| Unauthorized mutation count | Any mutation outside the exact confirmed target set; **zero acceptable failures**. |

Also report abstention/insufficient-evidence frequency, invalid outputs, model effects,
map-limit failures, map bytes/entries, latency and total model calls. Compare with
operator targeting and a deterministic filename heuristic. Repeat live runs with
frozen model digest, definition/prompt, runtime commit, hardware and destination;
N≥3 initially is descriptive, not production qualification. Predeclare quality
thresholds before the future live evaluation. Security failures block qualification
regardless of precision/recall; high exact-set rate cannot compensate for disclosure.

## 17. Human confirmation and authority tests

Future tests must capture actual constructed requests/configuration and actual model
calls/effects, not merely test a UI flag:

1. Valid subset -> explicit acceptance -> exactly matching TaskRequest and editable_paths.
2. Remove a candidate -> absent from Coding evidence; a Coding reply attempting it
   is rejected; zero mutation to that path, including attempt 2.
3. Reject all/empty/no confirmation -> zero Coding, mutation and check calls; prior
   discovery model effect remains recorded.
4. Invented candidate -> candidate validation fails before confirmation/handoff.
5. Excluded/sensitive path -> absent from model input and invalid if proposed.
6. Manual addition -> accepted only under pre-existing operator editing policy;
   manual CREATE separately proves existing parent/absence and normal M4 rules.
7. Final confirmation -> immutable exact values; later mutation of UI/proposal
   collections cannot change the task or configuration.
8. Reviewer requests another path -> existing rework target tuple unchanged;
   out-of-scope Coding output rejected.
9. Wrong tenant/workspace/action, expired/revoked/unavailable authority -> zero
   further map disclosure; no cached decision after map preview.
10. Map/policy/model condition changes before confirmation -> stale/invalidated,
    no automatic acceptance, refresh or second model call.
11. Tampered persisted proposal or forged “confirmed” boolean -> cannot supply
    trusted operator configuration or issue grants.
12. Captured SYSTEM/USER requests prove map-only disclosure; no Git data, raw
    excluded names, file text, absolute host root, grants or credentials.

Retain existing public-import architecture tests, Coding parser/effect tests,
Reviewer non-interference, ForgeAI worker/rework suites and real Docker regressions.

## 18. Reuse analysis

If ForgeAI disappeared, bounded authorized structure disclosure still belongs in
Engineering: Analyst users need a safe way to identify which files to supply.
Both share the same workspace, path grammar, disclosure policy and current-authority
semantics. Future search/refactoring products are additional plausible consumers,
not a reason to build general search now. Pure map values, bounded authorized
acquisition and validated selection are reusable; customer objectives, confirmation
UX, freelance scope, task creation and delivery orchestration remain ForgeAI-owned.

This does not claim two deployed consumers of a selector already exist. Require
an Analyst composition example alongside ForgeAI integration to demonstrate the
proposed reuse rather than declaring it by naming two roles.

## 19. Future MCP interaction

No MCP is implemented here. The semantic acquisition remains provider-neutral.
A future MCP-backed workspace can replace local access only if it meets the full
list_entries semantics: complete bounded direct children, validated relative paths,
truthful failures and declared timing/trust guarantees. Paginated or partial remote
results must not masquerade as complete local listings.

If asynchronous cancellation/deadlines or server-side snapshot evidence are required,
design the smallest justified remote acquisition Port then; the present synchronous
Port expressly does not promise them. Do not create RepositoryStructurePort now
solely to reserve an MCP slot. The future path remains application -> Engineering
semantic acquisition -> current authorization -> admitted repository adapter -> MCP
server. Server discovery neither authorizes name disclosure nor grants writes, and
server-returned paths are validated as untrusted data. MCP admission/session/secret
decisions stay separate from this ADR-018 profile.

## 20. Future durable-state interaction

Useful retained facts: workspace reference, filtered map identity and policy revision,
acquisition time, selection definition/model/configuration identity, advisory proposal,
exact operator-confirmed paths and operations, objective/constraint identity,
authorization/evidence references, terminal failure and known/unknown model effects.
Store sensitive path/reason content only under explicit access/retention policy;
never persist raw grants, secrets or a boolean that can replay authority.

These are future project/audit facts, not prerequisites for a process-local prototype.
The initial flow does not resume after a crash. A crash invalidates in-memory consent;
operator re-establishes current state and authority. Roadmap G02 still gates serious
pilot retention/recovery. ConfigurationStorePort is not a generic discovery journal;
TaskResult is not long-term memory. No persistence API is proposed in this slice.

## 21. ADR disposition

**ADR-018 ADDENDUM SUFFICIENT**

ADR-018 already owns Engineering's trusted workspace association, model disclosure,
fixed actions, per-effect current authorization and approval refusal. Its CR-3
addendum establishes precedent for adding a fixed action without changing the ADR's
status or inventing a new governance owner. Structure disclosure is a bounded
extension of that decision, not a new Core authorization framework.

The addendum must explicitly cover the new action, root/filter/destination association,
authorization timing/limitations, completeness bounds, operator-confirmed handoff
and model-only-existing-path rule. It must not relabel structure permission as content
or write authority. ADR-005/007/008 remain governing constraints; no retry, atomic
snapshot, durable approval or remote handoff guarantee is introduced.

ADR-018 is still **Proposed with scoped implementation**, not Accepted. This
recommendation does not change that status, and existing scoped authority does not
authorize discovery. Repository ADR governance provides no requirement to allocate
a new number for this same-owner additive profile. Prepare/review an addendum only
after maintainer approval of this recommendation; change no ADR in this task.

## 22. Proposed implementation slices

Reduce the suggested four-way split to three slices: deterministic acquisition and
its disclosure authorization ship together. A stand-alone map helper may be pure,
but do not publish a model-facing acquisition API before its authority guard exists.
All filenames below are proposals, not files created by this decision.

| Slice | Owner / likely files | Public API impact | Tests and qualification | Dependencies | Stop condition |
| --- | --- | --- | --- | --- | --- |
| DISCOVERY-1: bounded authorized structure acquisition | Engineering `repository/structure.py` (values/policy), `repository/structure_authorized.py` (facade), focused tests and consuming guide; ADR-018 addendum separately approved | Additive structure values/facade; existing workspace/evidence Ports unchanged | Deterministic fake-Port and real local filesystem tests: counts/bytes/depth/exclusions, malformed adapter entries, two-pass change, current authority before every list/release, preview privacy; mypy/Ruff/import and wheel proof. No live model. | Maintainer approval plus ADR-018 profile; current M2/CR-3 | Stop if required bounds/completeness cannot be proved through existing Port, or stronger revocation/snapshot guarantee is required. No selector/ForgeAI effects. |
| DISCOVERY-2: bounded selection | Engineering `discovery/values.py`, `definition.py`, `api.py` plus tests and Analyst example; names finalized during implementation | Additive specialization using existing Agent runtime; no Coding/Analyst changes | Actual request capture, exact membership/parser/UNKNOWN/single-call tests; independent synthetic fixtures and deterministic baseline; separately authorized live selection measurement | Qualified DISCOVERY-1, approved model-destination association, deterministic baseline shows need | Stop if model selection adds no value or quality/privacy criteria fail. Do not implement repair/retry to inflate results. |
| FORGEAI-DISCOVERY-1: confirmation and handoff | ForgeAI proposed discovery/confirmation application module, CLI and composition orchestration, tests/evaluation documentation | Application UX/types additive; TaskRequest/CodingTarget/worker contracts reused unchanged | All §17 tests, unchanged ForgeAI/Coding/Reviewer regressions, real Docker supported flow; operator preview/confirmation exercise and held-out selection/handoff evaluation | Qualified discovery slices, approved operator editing policy; Coding/Reviewer level-1 quality before rollout | Stop if handoff needs broader authority, >8 targets, directories or unsupported workload. No automatic worker launch without confirmation. |

Content-assisted discovery, model-proposed CREATE names, persistence and MCP are
separate later decisions only if the corresponding evidence requires them. No
new mandatory generic Workflow/Team dependency enters these slices.

## 23. Non-goals and discrepancies

No production code, new fixture files, Agent implementation, recursive arbitrary
content reads, search engine, embeddings/vector store, MCP, Workflow, Team, M8.4,
automatic write-scope expansion, Git disclosure, retries, filesystem traversal
outside approved workspace/roots, DI/container or framework is authorized here.
No commit is requested or made. Historical live reports remain immutable.

Material refinements/discrepancies from inspection:

- Earlier direction permits invented CREATE filenames under mapped directories;
  this recommendation narrows initial model selection to existing disclosed files
  to satisfy the present unknown-path rejection requirement. Manual CREATE remains.
- Roadmap shorthand about exact target authority must not be read as per-file
  grants or a mutation-wrapper allowlist. Actual scope is a workspace grant plus
  trusted exact-target acquisition/parser enforcement.
- Existing M2 has no aggregate traversal budget, arbitrary hidden-name filtering,
  recursive snapshot or hard deadline. These cannot be inferred from bounded
  list_entries; the proposed profile adds aggregation/filtering and preserves
  unsupported concurrency/timing conditions.
- Git metadata exclusion does not guarantee all mapped files are tracked or
  unignored; claiming that would require a different acquisition policy.
- Analyst cannot list; CREATE's internal parent listing proves neither general
  directory disclosure authority nor target discovery support.
- ADR-018 remains Proposed; the roadmap's adoption is not approval of a new action.

The roadmap receives only a short status/link note. No maturity label is promoted
to implemented or qualified by this recommendation.

**Single recommended first implementation slice, after explicit decision approval:
DISCOVERY-1 — bounded authorized repository-structure acquisition, with deterministic
local tests and no model invocation.**

## DISCOVERY-1 implementation record — 2026-10-04

Maintainer approved this decision and the first slice. **Bounded authorized
structure acquisition is implemented; operator local qualification pending.**
The original recommendation remains historical. The narrow ADR-018 addendum was
appended under that explicit approval; ADR status remains Proposed.

Public Engineering `repository.structure` supplies immutable policy/result values,
safe closed failures, canonical versioned representation and SHA-256 map identity;
`repository.structure_authorized` supplies the distinct fixed action and two-pass
acquisition. See the [consuming guide](../packages/legoai-engineering/docs/CONSUMING.md#discovery-1--bounded-authorized-structure-acquisition)
for exact limits, privacy, failure translations and composition obligations.

The unchanged workspace Port does not expose its adapter policy. Trusted composition
must bind an adapter with ≤512 scanned entries/directory and no exclusions beyond
the declared structure policy. This obligation is explicit; output validation does
not pretend to attest an adapter's internal work. No lower Port or Core change.
Two equal filtered passes and current final authority are required; no snapshot or
atomic disclosure/revocation claim. No source content, Git, model, target selection,
write authority or ForgeAI/operator-confirmation behavior is implemented.

Operator validation: `uv run python .\validate_engineering_discovery_1.py` from root.
Local filesystem, fake/replay and HTTP-stub tests only; no live model or Docker.
DISCOVERY-2 remains unimplemented and is not authorized by this implementation.
