# DISCOVERY-2A — target selection evaluation and contract decision

Date: 2026-10-04. Evaluation foundation: `84da572d8071288980425cd62c7b632cf686dc13`.
Maintainer authorized this evaluation/design slice, not a production selector.
DISCOVERY-1 is locally qualified: the supplied operator log reports all 25 phases
PASS and one expected POSIX-only skip on Windows. Earlier implementation records
remain historical and are not rewritten here.

**Decision: EVIDENCE INSUFFICIENT.** No model selector is justified for implementation
by this experiment. Determinism is useful on explicit names; this small authored
suite does not establish workload sufficiency, material operator savings, or that a
model would resolve the remaining failures. A model's ability to guess an opaque
module's purpose must not be confused with evidence of that purpose.

## Foundation and scope

Inspected the target-discovery decision, master roadmap, ADR-018, Engineering
README/CONSUMING guide, structure values/facade and tests, Analyst API/values,
Coding contracts, ForgeAI TaskRequest/composition/worker and LQ1 infrastructure.
The current source matches the qualified acquisition boundary: relative names and
kinds, explicit roots, mandatory filtering, bounded complete maps, two equal passes,
current authorization before every listing and release, no contents or model calls.
The trusted adapter-policy and synchronous/non-atomic limitations still apply.

RepositoryAnalyst's definition is in `analyst/api.py`, not a separate definition
module. It consumes exactly requested named-file contents; findings cite supplied
paths. A structure map is not its evidence. Coding still accepts only changes to
acquired operator targets, with mandatory per-change reason; TaskRequest retains
1–8 explicit CodingTargets. ForgeAI composition separately binds editable paths;
worker sequencing and bounded rework are unchanged.

Only a new evaluation namespace, its tests, this document, a short roadmap note
and a root validator change. No production API, authority, ADR, historical LQ1
fixture/report or Agent definition changes. The package is outside the runtime
wheel. No model, network, Git input, filesystem crawling, contents, AST, embedding,
provider configuration or external search enters the selection algorithm.

## Frozen fixtures and truth

Namespace `forgeai-discovery-paths`, revision 1, contains **17 synthetic cases** in
`examples/forgeai/evaluation/discovery2a/fixtures-v1.json`. No source content is
needed. Fixture text has a pinned canonical LF SHA-256 in the integrity test.
Any future semantic change requires a new fixture revision; do not tune revision 1
or change its oracle to fit a baseline. Baseline revision 1 and report schema 1
are separate from LQ1 schema/revisions.

The 11 requested categories are present. Six additional variants are justified:
a depth refusal paired with the boundary success; large overflow and policy-narrowed
variants paired with the large admitted map; a pre-rename counterpart; multiple
acceptable alternatives to prove coherent-set scoring; opaque names to expose an
information ceiling. No candidate-selection oracle is passed to the baseline.

Each fixture records explicit REQUIRED, ACCEPTABLE complete sets, IRRELEVANT and
FORBIDDEN paths; expected status, CREATE need, acquisition-refusal expectation and
failure classification. Required paths must belong to every acceptable set.
Alternatives are not unioned. The irrelevant class means not justified for selection
under this objective/oracle, including unresolved ambiguous choices; it does not
assert a file can never be useful. All files are classified and sets are validated.
Forbidden entries exactly match declared policy exclusions and never enter the map.

For ambiguous/opaque/CREATE cases there is no accepted target set; correct behavior
is insufficient evidence. The exact future CREATE filename is absent and remains
operator-owned. The rename pair carries an evaluator-known semantic continuity;
that history is intentionally absent from selector input. It is a test of missing
signal, not proof the map encodes the rename.

Maps are constructed from synthetic declarations through the unchanged public
RepositoryStructurePolicy/RepositoryStructure values. This is pure fixture setup,
not an authorization simulation or permission to disclose a real map. The production
DISCOVERY-1 regression separately verifies authorized traversal. Depth and serialized
map overflow fail before selection; the narrower large case excludes the noise tree
explicitly, never silently truncates. No boundary failure counts as selector success.

## Baselines and alternatives

All three baselines consume only objective and a validated RepositoryStructure.
They output evaluation-local `status`, `candidates`, `unknowns`; no production
TargetSelectionProposal is published. Results are advisory, never editable scope.
Paths retain exact spelling. Membership validation accepts only disclosed FILE
entries, rejects the whole result on unknown/forbidden/directory candidates, rejects
duplicates and more than eight candidates, and validates status/unknown semantics.

Tokenization splits ASCII camel-case boundaries, applies NFC and Unicode casefold
for comparison, and extracts Unicode alphanumeric tokens (underscore separates).
It does not normalize returned paths, stem words, expand synonyms or infer language.
Scores descending then exact path ascending give stable ordering. No thresholds
were tuned per fixture; these are three intentionally simple mechanism probes.

| Approach | Assessment |
| --- | --- |
| A: lexical | Select positive filename-stem/objective token overlap, descending overlap, top 8. |
| B: path/token score | Score = twice filename overlap plus full-path overlap; select positive scores, top 8. Directories supply context but are never candidates. |
| C: conservative heuristic | Same score; abstain for no signal, explicit “new file”, or tied highest scores; otherwise return one candidate. Tests whether precision/abstention helps at the expense of multi-file recall. |
| D: existing RepositoryAnalyst | Not applicable to map-only selection: named-file text evidence and findings are a different contract. Preserve it for a separately confirmed read subset later. |
| E: dedicated one-step selector | Plausible separate responsibility, but unmeasured; do not implement or infer improved quality from a lower deterministic exact-set rate. |
| F: shortlist then model | Unmeasured. Top-k can irreversibly remove relevant paths; an extra model cannot recover absent candidates or absent evidence. No implementation justified. |

Reuse wins here: existing structure values, pytest/static tooling and a small
standalone evaluation. No generic selector interface or production Agent is added.

## Metric definitions

For each valid proposal, choose one coherent acceptable set with minimum symmetric
difference (path-lexical tie break). TP is intersection with that set, FP its excess,
FN its deficit. No-set cases have target size zero; proposing paths there is excess.
Invalid proposals are rejected wholesale and separately counted; accepted-candidate
precision never masks their invalid/proposed counts.

- Candidate precision: summed TP / accepted candidates; zero denominator is null.
- Candidate recall: summed TP / chosen acceptable-set sizes (not required-only).
- Required-path recall: required hits / explicit required paths, separately reported.
- Exact acceptable-set rate: succeeded and exactly one accepted set / eligible
  cases. Abstention and invalid proposals on eligible cases are misses.
- Irrelevant/forbidden/unknown/non-file proposals: raw proposed-path counts. Unknown
  excludes known forbidden entries so diagnostics do not double count them.
- Over/under-selection counts: cases with removals/additions; raw edit counts also
  reported. Choosing two mutually alternative paths has an excess, even if neither
  is irrelevant in isolation.
- Correction operations: candidate removals + additions + proposal rejections.
  Rejection is one additional operator action, not another path edit. Correction
  runs count presented cases requiring any such action.
- Insufficient-evidence correctness: correct insufficient outputs / expected
  insufficient cases that reached selection. False abstentions also lower recall,
  exact-set and overall status correctness; this metric alone is not abstention quality.
- Candidate-count distribution includes presented zero-candidate abstentions;
  preselection failures are separate, not zero-candidate successes.
- Manual CREATE paths and emitted insufficient-evidence cases needing clarification
  are separate workflow interventions. False abstentions also incur clarification.
  Clarification includes deciding an operator-owned CREATE path;
  the counts can overlap and must not be blindly summed.

All aggregates fold per-fixture count records with explicit denominators. No
composite score. Unauthorized/undisclosed candidate acceptance and forbidden map
exposure must be zero. Proposals are not grants: no actual grant or mutation
acceptance is exercised or claimed in this synthetic evaluation.

## Results (deterministic, no repeated-run inflation)

The checked `results-v1.json` is a count-only artifact. It records fixture IDs,
closed categories/outcomes, method IDs and counts; no paths, objective, contents,
prompts, host information, arbitrary output or model text. Tests recompute it exactly.

Each method: 17 fixtures, **15 presented, 2 acquisition refusals**, 12 exact-set
eligible, 3 expected-insufficient cases. These authored fixtures are not independent
samples of production demand; percentages are descriptive only.

| Metric | Lexical | Path score | Conservative |
| --- | ---: | ---: | ---: |
| Candidate precision | 14/20 = 70% | 14/20 = 70% | 9/9 = 100% |
| Candidate recall | 14/15 = 93.33% | 14/15 = 93.33% | 9/15 = 60% |
| Required-path recall | 13/14 = 92.86% | 13/14 = 92.86% | 9/14 = 64.29% |
| Exact acceptable sets | 9/12 = 75% | 9/12 = 75% | 7/12 = 58.33% |
| Irrelevant proposals | 5 | 5 | 0 |
| Over-selection cases | 3 | 3 | 0 |
| Under-selection cases | 1 | 1 | 5 |
| Removed / added | 6 / 1 | 6 / 1 | 0 / 6 |
| Rejected proposals | 1 | 1 | 0 |
| Correction operations | 8 | 8 | 6 |
| Correction runs | 4/15 | 4/15 | 5/15 |
| Insufficient correct | 2/3 | 2/3 | 3/3 |
| Invalid / forbidden / unknown proposals | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| Forbidden disclosure / undisclosed acceptance | 0 / 0 | 0 / 0 | 0 / 0 |
| Manual CREATE / clarification | 1 / 3 | 1 / 3 | 1 / 6 |

Candidate distributions for counts 0..8:
lexical/path score `[3,7,3,1,1,0,0,0,0]`;
conservative `[6,9,0,0,0,0,0,0,0]`.

The table below uses E=exact acceptable set, I=correct insufficient evidence,
O=over-selection, U=under-selection, A=acquisition refusal. Lexical and path-score
outcomes coincide on this suite; distinct rankings do not establish distinct utility.

| ID | Category | Lexical / path | Conservative | Explanation / limitation |
| --- | --- | --- | --- | --- |
| d01 | Obvious | E | E | Explicit filename signal suffices. |
| d02 | Ambiguous | O (remove 2, reject) | I | Requirement ambiguity; a model cannot choose the operator's intent. |
| d03 | Related files | E | U (add 2) | Conservative one-file rule loses cross-directory relationships already exposed by names. |
| d04 | Generated/vendor | E | E | Excluded trees never reach selection. |
| d05 | Secret-like names | E | E | Policy filtering, not model discretion, protects excluded names. |
| d06 | Depth boundary | E | E | Permitted boundary file remains selectable. |
| d07 | Similar-name decoys | O (remove 3) | U (add 1) | Misleading names/lexical ties; neither demonstrates need for an LLM. |
| d08 | CREATE required | I | I | Abstention, one manual CREATE path; lexical abstention is lack of overlap, not semantic CREATE understanding. |
| d09 | Separate roots | E | U (add 1) | One-file rule omits implementation; map has enough signal for the broader baseline. |
| d10 | Renamed module | U (add 1) | U (add 1) | Missing semantic relationship/history; name association is plausible but unverified. |
| d11 | Large admitted tree | E | E | Irrelevant admitted names do not reduce matching here. |
| d12 | Depth overflow | A | A | Acquisition limit, not selection failure. |
| d13 | Large overflow | A | A | Serialized-map limit, not permission for truncation. |
| d14 | Large narrowed policy | E | E | Explicit exclusion restores bounded input. |
| d15 | Before rename | E | E | Paired with d10: loss of naming signal. |
| d16 | Valid alternatives | O (remove 1) | U (add 1) | Multiple valid choices; selecting both is not an accepted set. |
| d17 | Opaque filenames | I | I | Absent content; path-only reasoning cannot establish behavior. |

No measured elapsed human effort is available. Correction counts are an edit/action
proxy, excluding inspection time, verification burden and acquisition-policy repair.
Selecting all 15 reference target memberships manually is a possible comparison
count, not a timed operator baseline or an autonomy improvement claim. Conservative
saves two counted operations but affects more cases and loses recall; it is not a
proven winner. Model quality/cost, latency and correction savings remain unmeasured.

## Model justification gate

| Gate | Evidence / verdict |
| --- | --- |
| Useful structure signal | Yes for explicit names and related tests. |
| Important deterministic semantic failures | Some authored failures; production importance/frequency not established. Many are avoidable heuristic or intent problems. |
| Model reasoning can address failures | Plausible for name associations; not demonstrated, and opaque names/rename history may require evidence. |
| Materially reduced operator effort | Not established: only edit proxies, no model comparator or timed operator study. |
| Contents unnecessary in most cases | This deliberately selected suite cannot establish a population-level “most”. |
| Distinct from Analyst | Yes: path/kind advice versus analysis of acquired file texts. |
| Reusable beyond ForgeAI | Plausible for selecting an Analyst read subset; no second consumer proof in this slice. |

The gate does not pass. A model selector is neither implemented nor approved;
no future payload or production selection contract is frozen here. The earlier
conceptual contract remains a proposal: exact status/candidates/unknowns, 0–8
FILE members, descriptive bounded reasons, nonempty succeeded/unknown rules,
no operation/permission/confidence, no CREATE invention, repair/default/retry.
Whether it deserves a distinct Engineering specialization remains conditional on
measured input/output/failure/evaluation responsibility and demonstrated reuse,
not simply use of AgentRuntimePort.

If separately justified later, input stays objective ≤2048 UTF-8 bytes, constraints
≤8×1024, approved map ≤16384, USER ≤32768 and SYSTEM+USER ≤49152. No contents,
Git, grants, host paths or mutation/check data. The selector has zero direct filesystem
capability. A trusted owner must freshly acquire/authorize structure before model
submission and separately obtain governed Chat authority; no cached ALLOW or extra
write/check grants. A map/digest is not permission.

Content-assisted discovery is necessary to establish behavior for opaque names and
may be needed to verify a renamed module; it is not shown necessary for the entire
profile. Preserve the proposed separate flow: authorized map -> advisory read
candidates -> operator-confirmed read subset -> AuthorizedRepositoryEvidence ->
RepositoryAnalyst -> operator-confirmed editable targets. No recursive model reads
or content-assisted implementation is authorized here.

## Verification, ADR and next slice

`validate_forgeai_discovery_2a.py` covers 19 phases: scope, fixture/truth schemas,
determinism, membership, forbidden invariant, bound, insufficient/CREATE semantics,
metrics, fold/frozen report, privacy, production isolation, DISCOVERY-1 regressions,
ForgeAI/LQ1 architecture, mypy, Ruff lint/format and diff checks. No Docker dependency
exists: evaluation is pure synthetic data and the only filesystem tests are existing
DISCOVERY-1 local tests. No live provider is invoked.

From repository root:

```powershell
uv run python .\validate_forgeai_discovery_2a.py
```

All 19 validator phases passed locally on 2026-10-04, including 185 DISCOVERY-1
regressions and 109 evaluation/architecture tests (68 new evaluation tests plus
41 existing architecture tests), mypy and Ruff. Repeated focused phase selections
are not independent observations or extra unique tests. ADR-018 remains unchanged and
Proposed; no new ADR. Its existing addendum specifically covers acquisition, not
selector implementation. The prior recommendation that a same-owner addendum is
sufficient remains applicable if selection is later approved; the actual submission
and handoff profile still needs explicit approval, not inferred new authority.

**Single recommended next slice: DISCOVERY-2A.1 — held-out path-only evaluation and
operator correction study.** Freeze independently authored representative tasks,
acceptable sets, a useful workload subset and success/intervention thresholds before
running them. Measure the same deterministic baselines and actual operator effort;
classify irreducible information gaps separately. No production selector or live-model
measurement is approved by this recommendation. G07 remains open; neither target
confirmation nor broader autonomous discovery has shipped.

EVIDENCE INSUFFICIENT
