# DISCOVERY-2A.1 held-out target-selection evaluation

## Pre-evaluation declaration — frozen before fixture authorship

Foundation: `6b9c44110edaea12be4906afd8547c36b0f3a3da`.
The 17 original fixtures and three revision-1 baselines reproduce (68 tests passed)
and are unchanged. DISCOVERY-2A changed no production source. No production selector
exists. This slice imports the original baselines unchanged; no fourth algorithm,
model, contents, Git input, runtime or authority change is permitted.

This section and `discovery2a_holdout/thresholds-v1.json` are written and hashed
before any held-out fixtures or selector results are produced. “Committed to the
artifact” means a persisted, hash-pinned declaration, not a Git commit; the user
has not authorized a Git commit. The manifest will bind the declaration, threshold,
original-source, fixture and truth hashes in that sequence. It proves integrity
and documents procedure, not independently witnessed chronology.

### Decision thresholds

These conservative research gates apply to a human-confirmed, bounded discovery
profile, not universal production standards. Evaluate each baseline independently:
no mixture that chooses a different method using fixture ground truth.

- Safety: zero forbidden disclosure, undisclosed or directory acceptance, and
  zero accepted candidate sets exceeding 8. Any violation blocks suitability.
- Overall candidate precision >=80%; candidate recall and required-path recall
  >=90%; exact acceptable-set success >=80% on actionable tasks.
- Correct expected abstention >=90%; CREATE-safe abstention >=90%, reported
  separately. An abstention does not prove semantic recognition of CREATE.
- False-sufficient selections =0; catastrophic misses =0. A succeeded selection
  missing required paths without satisfying an acceptable alternative is false
  sufficient. Omitting all nonempty required paths is catastrophic.
- Actionable correction operations: median <=1; nearest-rank p90 <=3. Also require
  total actionable corrections <=75% of explicit operator target-entry operations
  (a conservative 25% reduction in counted work, not elapsed time or search effort).
- Each EASY, MEDIUM and HARD actionable stratum: precision >=80%, required recall
  >=90%, acceptable-set success >=75%, median corrections <=1 and p90 <=3.
  PATH_ONLY_UNDERDETERMINED expected abstention >=90%. No average hides a stratum.

Why: silent omissions are especially costly before governed coding, excess candidates
expand review burden, and explicit abstention preserves the need for operator input.
Human confirmation does not excuse false sufficiency. Per-stratum thresholds prevent
obvious tasks from masking failures on cross-file changes. Abstention, CREATE and
correction denominators will be explicit; zero denominators are null, not passes.
No threshold may be lowered after results. Safety/quality gates are separate, with
no single composite score.

### Workload and difficulty protocol

Author 36 bounded synthetic tasks from routine engineering use cases: bug fixes,
validation, tests, package interfaces, configuration, documentation and new features.
Cover all 17 requested strata at least twice; add two coverage cases, not hundreds
of repetitive variants. No file contents or historical Git facts enter selection.
All maps must fit DISCOVERY-1 bounds; acquisition-limit experiments already exist.
All fixtures include excluded synthetic paths. No exact original full paths,
objectives, target sets or whole trees may be reused. Shared mandatory exclusion
component names and generic filenames are unavoidable conceptual vocabulary, not
reuse of an original complete path/tree. Each new tree must have multiple files.

Difficulty is frozen before execution:

- EASY: explicit filename/task lexical alignment, minimal relationship inference.
- MEDIUM: relationships visible in directory/module naming or explicit named parts.
- HARD: weak/misleading naming, synonyms or multi-file architectural relationships
  whose relevance is described by the objective and visible names.
- PATH_ONLY_UNDERDETERMINED: intent, implementation identity or behavior cannot be
  established from the supplied objective and names/kinds; expected abstention.
  CREATE-only tasks also belong here: no existing disclosed file can meet the need.

Per task: (1) write objective, (2) synthetic tree, (3) truth, (4) difficulty and
information-gap classification, (5) freeze hashes, (6) only then execute selectors.
The workload inventory and manifest will record these steps. Fixture independence
is procedural, not statistically independent. The same AI system authors and
scores these fixtures, knows the original study and baseline definitions, and
cannot claim blindness or population representativeness. Author from use cases,
not original failures. No selectors may run during authorship; freeze all 36 first.

### Correction and metric protocol

Count concrete correction operations, not seconds/minutes or observed human actions.
For each coherent acceptable set, compute the legitimate correction sequence:

- A valid nonempty proposal containing useful targets: REMOVE each excess member,
  ADD each missing target. Do not reject a useful partial set merely to reduce count.
- A succeeded proposal with no useful target, or any invalid proposal: REJECT once,
  ADD every target. Discarding the whole set does not also count per-path removals.
- An empty insufficient result on an otherwise actionable request: ADD each target;
  no clarification is invented when the request already defines the needed work.
- An underdetermined requirement: CLARIFY once; REJECT once if it presents a
  succeeded/nonempty/invalid proposal. No invented additions or ordinary false
  negatives for unknown or excluded paths.
- A clear CREATE-only requirement: CREATE once for an operator-specified new target,
  REJECT once for succeeded/nonempty/invalid output. No invented CREATE path is
  accepted or counted as selector success; no unnecessary CLARIFY is added.

Choose the acceptable set with fewest total operations, then fewest additions,
then exact lexical set order. No union of mutually alternative sets. Precision and
recall use that same coherent set. Required-path recall remains separately defined.
False-sufficient uses satisfied alternative subsets (so irrelevant extras alone
are not a required-path omission); exact acceptable-set success requires equality.
Raw irrelevant proposals, irrelevant candidates per succeeded output, and candidate
count / smallest acceptable-set size are separate over-selection measures.
Report median, arithmetic mean and nearest-rank p90 (sorted element ceil(.9*n)-1)
for actionable tasks, with all-task corrections separately shown.

The operator-targeted reference counts manually supplying every target in the
smallest acceptable set, CLARIFY for ambiguous/opaque tasks, CREATE for new-file
needs. Its conceptual accuracy is oracle-defined, not empirically measured. This
reference omits search/review time for both workflows and proves no autonomy gain.

### Predeclared architecture decision logic

A: DETERMINISTIC PATH-ONLY SELECTION SUFFICIENT only if one frozen baseline meets
every safety, quality, burden and difficulty gate. No automatic production promotion.

If A fails, compare two evidence gates (neither overrides a safety failure):

B: MODEL PATH-ONLY SELECTOR JUSTIFIED only if at least four actionable tasks across
at least two preclassified semantic strata have visible map-only signal, all three
baselines miss the acceptable set, and each task's best baseline needs >=2 corrections.
Their relationships must be plausibly recoverable from names/objective, not hidden
contents/history; confirm distinct responsibility and no new authority. This
justifies a bounded model experiment, not a claim of measured model superiority.

C: CONTENT-ASSISTED DISCOVERY JUSTIFIED only if at least four tasks across two
strata are preclassified as missing behavioral/implementation evidence (excluding
mere requirement ambiguity and CREATE), such that no path-only reasoning can
resolve them, and existing named-file evidence/Analyst stages are the appropriate
next step. Correct abstention on these is not a selector defect. This gate concerns
coverage of the broader workflow, not a request to punish correct abstention.

If both B and C meet their gates, report EVIDENCE INSUFFICIENT to choose the next
architecture without independently establishing workload importance. If neither
meets its gate, report EVIDENCE INSUFFICIENT. A safety failure always blocks A/B;
requires separate review, never a quality-average workaround. No live or production
implementation follows automatically from any outcome. Same-author independence
limits all conclusions; stronger evidence would be independently authored or real
supervised tasks.

<!-- END FROZEN PREDECLARATION -->

## Authorship and freeze record

The persisted predeclaration above was created first, then the thresholds and
preregistration record, then all 36 task/truth records and their manifest. No
held-out selector was executed during fixture authorship. Schema/provenance and
independent correction examples were checked before the first result calculation.
The result artifacts were created with exclusive-create writes after that freeze.
No fixture, oracle, threshold or baseline was revised after seeing results.

Provenance files under `examples/forgeai/evaluation/discovery2a_holdout/`:

- [preregistration-v1.json](../examples/forgeai/evaluation/discovery2a_holdout/preregistration-v1.json): foundation and original-file identities.
- [thresholds-v1.json](../examples/forgeai/evaluation/discovery2a_holdout/thresholds-v1.json): numerical gates.
- [fixtures-v1.json](../examples/forgeai/evaluation/discovery2a_holdout/fixtures-v1.json): objectives, synthetic trees and preclassified difficulty/information gaps.
- [truth-v1.json](../examples/forgeai/evaluation/discovery2a_holdout/truth-v1.json): separate required/acceptable/irrelevant/forbidden sets and statuses.
- [manifest-v1.json](../examples/forgeai/evaluation/discovery2a_holdout/manifest-v1.json): per-task objective/tree/truth/fixture hashes and recorded order.

Canonical text hashing normalizes checkout newlines and excludes a UTF-8 BOM.
Predeclaration SHA-256: `dbb5f3134416db111882062c4f74e7ce8f86d69e60a731605b1f35f428ae9c16`.
Threshold SHA-256: `99cdc6e6f4599293bee55e727c140aca06ecdb4bd0b37b5433a83e65f9c6fa7f`.
Fixture SHA-256: `0b80fba810194d181b53a4baf4a64fe36920c8fbeacf5775d45bdb073f0ddf43`.
Truth SHA-256: `8090b246599729f71579006fa179a87d62e9512fb8113863ce51027209d0afa0`.
Manifest SHA-256: `0b4cfd4d1f9d4b42e7f53cc8b2af372bb36c445a53ab2fb7b618c62d7784f019`.

The exact imported baseline is DISCOVERY-2A revision 1: lexical, path_score,
conservative. Its source SHA-256 is
`d7faeea71f4b125c4ee5a81e4a6e625dba6cabcb882d1c4bbc82a8b12d22387f`.
All six original namespace files are additionally hash-pinned, including historical
results and fixtures; original tests still reproduce those results. No algorithm bug
was found; quality limitations are not contract violations or implementation defects.

Difficulty distribution: **3 EASY, 12 MEDIUM, 12 HARD, 9 PATH_ONLY_UNDERDETERMINED**.
There are 27 actionable tasks and 9 expected abstentions (2 intent ambiguities,
2 CREATE needs, 5 missing-content/identity cases). Every requested workload class
has at least two examples; opaque and renamed classes each have a third. The small
EASY stratum is intentionally not a production-weighted workload and is reported
separately. Its lexical alignment includes morphological similarity, not a guarantee
that the frozen tokenizer matches it. Difficulty was not revised after failure.
The largest admitted serialized map is 8,663 bytes. All maps fit DISCOVERY-1 limits.

**Fixture independence is procedural, not statistically independent.** The same AI
system authored and evaluated this set, with knowledge of prior baselines/results.
This is not a true blind benchmark, a random workload sample or a measured human
study. Hashes establish reproducibility, not an independently witnessed timeline.
Authoring from use cases and freezing before execution reduces tuning leakage;
it cannot eliminate same-author bias. The content-information-gap classification
is an authored architectural premise, not experimentally observed file contents.

## Aggregate results

Frozen count-only [JSON](../examples/forgeai/evaluation/discovery2a_holdout/results-v1.json)
and deterministic [Markdown report](../examples/forgeai/evaluation/discovery2a_holdout/results-v1.md)
contain complete counts, per-fixture/difficulty results, thresholds and identities.
No path, objective, model text, host data, source contents or timestamps enter them.
All three baselines were run unchanged on all 36 tasks, once per deterministic
condition; repeated verification is not extra independent evidence.

| Metric | Lexical | Path score | Conservative |
| --- | ---: | ---: | ---: |
| Precision | 36/65 = 55.38% | 42/82 = 51.22% | 9/11 = 81.82% |
| Candidate recall | 36/46 = 78.26% | 42/46 = 91.30% | 9/46 = 19.57% |
| Required recall | 33/43 = 76.74% | 39/43 = 90.70% | 9/43 = 20.93% |
| Acceptable sets | 10/27 = 37.04% | 8/27 = 29.63% | 3/27 = 11.11% |
| Correct expected abstention | 6/9 | 5/9 | 9/9 |
| CREATE-safe abstention | 2/2 | 2/2 | 2/2 |
| False-sufficient selections | 1 | 1 | 8 |
| Catastrophic misses | 0 | 0 | 2 |
| False success on underdetermined requests | 3 | 4 | 0 |
| Irrelevant candidates per succeeded output | 1.04 | 1.3214 | 0.1818 |
| Mean candidate count / smallest acceptable set (actionable) | 1.4815 | 1.7191 | 0.2840 |
| Actionable median / p90 / mean corrections | 1 / 4 / 1.1111 | 1 / 2 / 1.1481 | 1 / 2 / 1.4444 |
| Actionable total corrections | 30 | 31 | 39 |
| All-task median / p90 / mean corrections | 1 / 2 / 1.1667 | 1 / 2 / 1.2222 | 1 / 2 / 1.3333 |
| All-task total corrections | 42 | 44 | 48 |
| REMOVE | 20 | 27 | 0 |
| ADD | 10 | 4 | 37 |
| REJECT | 3 | 4 | 2 |
| CLARIFY | 7 | 7 | 7 |
| CREATE | 2 | 2 | 2 |

Candidate-count distributions, positions 0..8:
lexical `[11,2,11,9,1,2,0,0,0]`;
path_score `[8,1,9,11,5,2,0,0,0]`;
conservative `[25,11,0,0,0,0,0,0,0]`.
No accepted set exceeds 8. CREATE correctness means safe abstention; the lexical
methods do not have a CREATE understanding mechanism, so no stronger recognition
claim follows from these two examples.

The operator-targeted reference requires **46 target-entry operations on actionable
tasks**, plus seven clarification and two CREATE operations: **55 overall**.
Actionable corrections are 65.22%, 67.39% and 84.78% of the reference respectively.
The first two meet the 75% counted-work threshold, but fail other quality gates.
These are exact operations under the declared correction model, **not actions
observed from a human operator**, search cost, seconds/minutes or autonomy improvement.
Whole rejected sets are counted once; no duplicate removal charge. Every correction
still presupposes an operator able to determine the correct target set.

## Failure interpretation and security

- Over-selection comes from shared tokens and directory context; a higher recall
  from path scoring often accompanies more irrelevant candidates.
- The conservative one-candidate rule loses necessary multi-file changes and can
  choose an irrelevant top-ranked file. It has eight false-sufficient selections,
  including two complete required-target misses. High precision alone is inadequate.
- Synonyms, morphological forms and package naming gaps produce missing candidates.
  These are limitations of the frozen mechanisms, not proof of a need for an LLM.
- Requirement ambiguity requires clarification; CREATE remains an operator-owned
  path. Neither is resolved by guessing more file names.
- Five preclassified cases (h16, h29, h30, h35, h36) lack behavior/implementation
  identity across opaque-name and renamed-module strata. Names/kinds alone cannot
  establish that evidence. A model could guess, but could not verify the mapping.

All baseline outputs satisfy the four hard safety invariants: **zero forbidden
map disclosure, undisclosed acceptance, directory acceptance and oversized accepted
sets**. Separate adversarial tests reject unknown paths, excluded paths, directories
and >8 members. This proves synthetic membership/filtering behavior, not new grants,
a live model boundary or protection from arbitrary hostile callers. Existing
DISCOVERY-1 authorization regression tests remain the evidence for acquisition.
No excluded path contributes a required-path false negative.

## Architecture decision and single next slice

**CONTENT-ASSISTED DISCOVERY JUSTIFIED**, for a separately approved, bounded staged
experiment addressing missing implementation/behavior evidence in this workload.
No baseline meets A. The model-path-only gate has only h25 (one task, one stratum)
meeting its material semantic-failure condition, below four tasks/two strata.
C has five preclassified missing-evidence tasks across two strata and meets its
predeclared gate. This does not establish content assistance as necessary for every
task, establish real-world prevalence, or license arbitrary repository reads.

**Single recommended next slice: CONTENT-DISCOVERY-1 — bounded operator-confirmed
read-subset evaluation using existing AuthorizedRepositoryEvidence and
RepositoryAnalyst.** Preserve the staged architecture:

    authorized structure
        -> advisory read candidates
        -> operator confirms exact read subset
        -> AuthorizedRepositoryEvidence
        -> RepositoryAnalyst
        -> operator confirms editable targets

The operator may supply the advisory subset manually for that experiment; no model
selector or production discovery integration is a prerequisite. Test whether bounded
content resolves the specific evidence gaps, using separately authored fixtures or
real supervised tasks if possible. Freeze oracle and outcome criteria first. Do not
add recursive model reads, a tool-loop Agent, write/check authority, or cached grants.
Content acquisition and any eventual Analyst model call retain existing current
read/model authorization. The current slice runs no model or content stage.

ADR-018 and all production contracts remain unchanged; no new ADR is allocated.
A future design must confirm existing named-file disclosure/destination semantics
are sufficient; any new authority boundary requires review. G07 remains open.
The roadmap receives only a short status/link note; the prior DISCOVERY-2A decision
remains unchanged as historical evidence. This outcome is a scoped architecture
recommendation, not production readiness or automatically authorized implementation.

## Validation

Run from repository root:

```powershell
uv run python .\validate_forgeai_discovery_2a1.py
```

The 24 phases cover scope, original immutability, schema/non-reuse/truth, thresholds,
baseline identities, deterministic execution, membership/security, correction and
false-sufficient calculation, minimal alternatives, per-difficulty/aggregate folding,
report consistency/privacy, DISCOVERY-1/2A and ForgeAI architecture regressions,
mypy, Ruff and diff checks. No Docker dependency or live model is involved.
Execution result will be appended after the complete validator run.

## Complete frozen per-fixture, per-difficulty and gate tables

The following is a deterministic rendering of the frozen result artifact.

### Frozen results

Synthetic counts only; no human timing or live models.

| Method | Precision | Recall | Required recall | Exact | Abstention | False sufficient | Median / p90 / mean |
| --- | --- | --- | --- | --- | --- | --- | --- |
| lexical | 0.5538461538461539 | 0.782608695652174 | 0.7674418604651163 | 10/27 | 6/9 | 1 | 1 / 4 / 1.1111111111111112 |
| path_score | 0.5121951219512195 | 0.9130434782608695 | 0.9069767441860465 | 8/27 | 5/9 | 1 | 1 / 2 / 1.1481481481481481 |
| conservative | 0.8181818181818182 | 0.1956521739130435 | 0.20930232558139536 | 3/27 | 9/9 | 8 | 1 / 2 / 1.4444444444444444 |

### Per-difficulty results

| Method | Difficulty | Precision | Recall | Required recall | Exact | Abstention | Median / p90 / mean |
| --- | --- | --- | --- | --- | --- | --- | --- |
| lexical | EASY | 0.6666666666666666 | 0.6666666666666666 | 0.6666666666666666 | 1/3 | 0/0 | 1 / 1 / 0.6666666666666666 |
| lexical | MEDIUM | 0.8181818181818182 | 0.8571428571428571 | 0.85 | 6/12 | 0/0 | 0.5 / 1 / 0.5833333333333334 |
| lexical | HARD | 0.5161290322580645 | 0.7272727272727273 | 0.7 | 3/12 | 0/0 | 1.5 / 4 / 1.75 |
| lexical | PATH_ONLY_UNDERDETERMINED | 0.0 | None | None | 0/0 | 6/9 | None / None / None |
| path_score | EASY | 0.6666666666666666 | 0.6666666666666666 | 0.6666666666666666 | 1/3 | 0/0 | 1 / 1 / 0.6666666666666666 |
| path_score | MEDIUM | 0.7 | 1.0 | 1.0 | 6/12 | 0/0 | 0.5 / 2 / 0.75 |
| path_score | HARD | 0.5277777777777778 | 0.8636363636363636 | 0.85 | 1/12 | 0/0 | 1.0 / 4 / 1.6666666666666667 |
| path_score | PATH_ONLY_UNDERDETERMINED | 0.0 | None | None | 0/0 | 5/9 | None / None / None |
| conservative | EASY | 1.0 | 0.3333333333333333 | 0.3333333333333333 | 1/3 | 0/0 | 1 / 1 / 0.6666666666666666 |
| conservative | MEDIUM | 1.0 | 0.2857142857142857 | 0.3 | 2/12 | 0/0 | 1.0 / 2 / 1.25 |
| conservative | HARD | 0.5 | 0.09090909090909091 | 0.1 | 0/12 | 0/0 | 2.0 / 3 / 1.8333333333333333 |
| conservative | PATH_ONLY_UNDERDETERMINED | None | None | None | 0/0 | 9/9 | None / None / None |

### Per-fixture results

| ID | Method | Difficulty | Status | Exact | False sufficient | REMOVE / ADD / REJECT / CLARIFY / CREATE | Failure |
| --- | --- | --- | --- | --- | --- | --- | --- |
| h01 | lexical | EASY | succeeded | 1 | 0 | 0 / 0 / 0 / 0 / 0 | none |
| h02 | lexical | EASY | succeeded | 0 | 0 | 1 / 0 / 0 / 0 / 0 | none |
| h03 | lexical | MEDIUM | succeeded | 1 | 0 | 0 / 0 / 0 / 0 / 0 | none |
| h04 | lexical | MEDIUM | succeeded | 1 | 0 | 0 / 0 / 0 / 0 / 0 | none |
| h05 | lexical | HARD | succeeded | 0 | 0 | 2 / 0 / 0 / 0 / 0 | misleading_naming |
| h06 | lexical | HARD | succeeded | 0 | 0 | 2 / 0 / 0 / 0 / 0 | misleading_naming |
| h07 | lexical | HARD | insufficient_evidence | 0 | 0 | 0 / 1 / 0 / 0 / 0 | semantic_relationship |
| h08 | lexical | HARD | insufficient_evidence | 0 | 0 | 0 / 1 / 0 / 0 / 0 | semantic_relationship |
| h09 | lexical | HARD | insufficient_evidence | 0 | 0 | 0 / 4 / 0 / 0 / 0 | multi_file_relationship |
| h10 | lexical | HARD | succeeded | 1 | 0 | 0 / 0 / 0 / 0 / 0 | none |
| h11 | lexical | PATH_ONLY_UNDERDETERMINED | succeeded | 0 | 0 | 0 / 0 / 1 / 1 / 0 | requirement_ambiguity |
| h12 | lexical | PATH_ONLY_UNDERDETERMINED | succeeded | 0 | 0 | 0 / 0 / 1 / 1 / 0 | requirement_ambiguity |
| h13 | lexical | PATH_ONLY_UNDERDETERMINED | insufficient_evidence | 0 | 0 | 0 / 0 / 0 / 0 / 1 | none |
| h14 | lexical | PATH_ONLY_UNDERDETERMINED | insufficient_evidence | 0 | 0 | 0 / 0 / 0 / 0 / 1 | none |
| h15 | lexical | HARD | succeeded | 0 | 0 | 1 / 0 / 0 / 0 / 0 | misleading_naming |
| h16 | lexical | PATH_ONLY_UNDERDETERMINED | insufficient_evidence | 0 | 0 | 0 / 0 / 0 / 1 / 0 | none |
| h17 | lexical | MEDIUM | succeeded | 0 | 0 | 1 / 0 / 0 / 0 / 0 | multiple_valid_choices |
| h18 | lexical | HARD | succeeded | 0 | 0 | 2 / 0 / 0 / 0 / 0 | multiple_valid_choices |
| h19 | lexical | EASY | insufficient_evidence | 0 | 0 | 0 / 1 / 0 / 0 / 0 | none |
| h20 | lexical | MEDIUM | succeeded | 1 | 0 | 0 / 0 / 0 / 0 / 0 | none |
| h21 | lexical | HARD | succeeded | 0 | 0 | 4 / 0 / 0 / 0 / 0 | misleading_naming |
| h22 | lexical | HARD | succeeded | 0 | 0 | 4 / 0 / 0 / 0 / 0 | misleading_naming |
| h23 | lexical | MEDIUM | succeeded | 1 | 0 | 0 / 0 / 0 / 0 / 0 | none |
| h24 | lexical | MEDIUM | succeeded | 1 | 0 | 0 / 0 / 0 / 0 / 0 | none |
| h25 | lexical | MEDIUM | insufficient_evidence | 0 | 0 | 0 / 2 / 0 / 0 / 0 | package_relationship |
| h26 | lexical | MEDIUM | succeeded | 0 | 1 | 0 / 1 / 0 / 0 / 0 | package_relationship |
| h27 | lexical | MEDIUM | succeeded | 0 | 0 | 1 / 0 / 0 / 0 / 0 | context_relationship |
| h28 | lexical | MEDIUM | succeeded | 0 | 0 | 1 / 0 / 0 / 0 / 0 | context_relationship |
| h29 | lexical | PATH_ONLY_UNDERDETERMINED | insufficient_evidence | 0 | 0 | 0 / 0 / 0 / 1 / 0 | none |
| h30 | lexical | PATH_ONLY_UNDERDETERMINED | insufficient_evidence | 0 | 0 | 0 / 0 / 0 / 1 / 0 | none |
| h31 | lexical | MEDIUM | succeeded | 1 | 0 | 0 / 0 / 0 / 0 / 0 | none |
| h32 | lexical | MEDIUM | succeeded | 0 | 0 | 1 / 0 / 0 / 0 / 0 | cross_directory_relationship |
| h33 | lexical | HARD | succeeded | 1 | 0 | 0 / 0 / 0 / 0 / 0 | none |
| h34 | lexical | HARD | succeeded | 1 | 0 | 0 / 0 / 0 / 0 / 0 | none |
| h35 | lexical | PATH_ONLY_UNDERDETERMINED | succeeded | 0 | 0 | 0 / 0 / 1 / 1 / 0 | absent_behavior |
| h36 | lexical | PATH_ONLY_UNDERDETERMINED | insufficient_evidence | 0 | 0 | 0 / 0 / 0 / 1 / 0 | none |
| h01 | path_score | EASY | succeeded | 1 | 0 | 0 / 0 / 0 / 0 / 0 | none |
| h02 | path_score | EASY | succeeded | 0 | 0 | 1 / 0 / 0 / 0 / 0 | none |
| h03 | path_score | MEDIUM | succeeded | 1 | 0 | 0 / 0 / 0 / 0 / 0 | none |
| h04 | path_score | MEDIUM | succeeded | 1 | 0 | 0 / 0 / 0 / 0 / 0 | none |
| h05 | path_score | HARD | succeeded | 0 | 0 | 2 / 0 / 0 / 0 / 0 | misleading_naming |
| h06 | path_score | HARD | succeeded | 0 | 0 | 2 / 0 / 0 / 0 / 0 | misleading_naming |
| h07 | path_score | HARD | insufficient_evidence | 0 | 0 | 0 / 1 / 0 / 0 / 0 | semantic_relationship |
| h08 | path_score | HARD | insufficient_evidence | 0 | 0 | 0 / 1 / 0 / 0 / 0 | semantic_relationship |
| h09 | path_score | HARD | succeeded | 0 | 1 | 0 / 1 / 0 / 0 / 0 | multi_file_relationship |
| h10 | path_score | HARD | succeeded | 0 | 0 | 1 / 0 / 0 / 0 / 0 | multi_file_relationship |
| h11 | path_score | PATH_ONLY_UNDERDETERMINED | succeeded | 0 | 0 | 0 / 0 / 1 / 1 / 0 | requirement_ambiguity |
| h12 | path_score | PATH_ONLY_UNDERDETERMINED | succeeded | 0 | 0 | 0 / 0 / 1 / 1 / 0 | requirement_ambiguity |
| h13 | path_score | PATH_ONLY_UNDERDETERMINED | insufficient_evidence | 0 | 0 | 0 / 0 / 0 / 0 / 1 | none |
| h14 | path_score | PATH_ONLY_UNDERDETERMINED | insufficient_evidence | 0 | 0 | 0 / 0 / 0 / 0 / 1 | none |
| h15 | path_score | HARD | succeeded | 0 | 0 | 1 / 0 / 0 / 0 / 0 | misleading_naming |
| h16 | path_score | PATH_ONLY_UNDERDETERMINED | succeeded | 0 | 0 | 0 / 0 / 1 / 1 / 0 | missing_identity |
| h17 | path_score | MEDIUM | succeeded | 0 | 0 | 1 / 0 / 0 / 0 / 0 | multiple_valid_choices |
| h18 | path_score | HARD | succeeded | 0 | 0 | 2 / 0 / 0 / 0 / 0 | multiple_valid_choices |
| h19 | path_score | EASY | insufficient_evidence | 0 | 0 | 0 / 1 / 0 / 0 / 0 | none |
| h20 | path_score | MEDIUM | succeeded | 1 | 0 | 0 / 0 / 0 / 0 / 0 | none |
| h21 | path_score | HARD | succeeded | 0 | 0 | 4 / 0 / 0 / 0 / 0 | misleading_naming |
| h22 | path_score | HARD | succeeded | 0 | 0 | 4 / 0 / 0 / 0 / 0 | misleading_naming |
| h23 | path_score | MEDIUM | succeeded | 1 | 0 | 0 / 0 / 0 / 0 / 0 | none |
| h24 | path_score | MEDIUM | succeeded | 1 | 0 | 0 / 0 / 0 / 0 / 0 | none |
| h25 | path_score | MEDIUM | succeeded | 0 | 0 | 2 / 0 / 0 / 0 / 0 | package_relationship |
| h26 | path_score | MEDIUM | succeeded | 0 | 0 | 1 / 0 / 0 / 0 / 0 | package_relationship |
| h27 | path_score | MEDIUM | succeeded | 0 | 0 | 2 / 0 / 0 / 0 / 0 | context_relationship |
| h28 | path_score | MEDIUM | succeeded | 0 | 0 | 2 / 0 / 0 / 0 / 0 | context_relationship |
| h29 | path_score | PATH_ONLY_UNDERDETERMINED | insufficient_evidence | 0 | 0 | 0 / 0 / 0 / 1 / 0 | none |
| h30 | path_score | PATH_ONLY_UNDERDETERMINED | insufficient_evidence | 0 | 0 | 0 / 0 / 0 / 1 / 0 | none |
| h31 | path_score | MEDIUM | succeeded | 1 | 0 | 0 / 0 / 0 / 0 / 0 | none |
| h32 | path_score | MEDIUM | succeeded | 0 | 0 | 1 / 0 / 0 / 0 / 0 | cross_directory_relationship |
| h33 | path_score | HARD | succeeded | 1 | 0 | 0 / 0 / 0 / 0 / 0 | none |
| h34 | path_score | HARD | succeeded | 0 | 0 | 1 / 0 / 0 / 0 / 0 | multi_file_relationship |
| h35 | path_score | PATH_ONLY_UNDERDETERMINED | succeeded | 0 | 0 | 0 / 0 / 1 / 1 / 0 | absent_behavior |
| h36 | path_score | PATH_ONLY_UNDERDETERMINED | insufficient_evidence | 0 | 0 | 0 / 0 / 0 / 1 / 0 | none |
| h01 | conservative | EASY | succeeded | 1 | 0 | 0 / 0 / 0 / 0 / 0 | none |
| h02 | conservative | EASY | insufficient_evidence | 0 | 0 | 0 / 1 / 0 / 0 / 0 | none |
| h03 | conservative | MEDIUM | succeeded | 0 | 1 | 0 / 1 / 0 / 0 / 0 | cross_directory_relationship |
| h04 | conservative | MEDIUM | insufficient_evidence | 0 | 0 | 0 / 2 / 0 / 0 / 0 | cross_directory_relationship |
| h05 | conservative | HARD | insufficient_evidence | 0 | 0 | 0 / 1 / 0 / 0 / 0 | misleading_naming |
| h06 | conservative | HARD | insufficient_evidence | 0 | 0 | 0 / 1 / 0 / 0 / 0 | misleading_naming |
| h07 | conservative | HARD | insufficient_evidence | 0 | 0 | 0 / 1 / 0 / 0 / 0 | semantic_relationship |
| h08 | conservative | HARD | insufficient_evidence | 0 | 0 | 0 / 1 / 0 / 0 / 0 | semantic_relationship |
| h09 | conservative | HARD | insufficient_evidence | 0 | 0 | 0 / 4 / 0 / 0 / 0 | multi_file_relationship |
| h10 | conservative | HARD | succeeded | 0 | 1 | 0 / 2 / 0 / 0 / 0 | multi_file_relationship |
| h11 | conservative | PATH_ONLY_UNDERDETERMINED | insufficient_evidence | 0 | 0 | 0 / 0 / 0 / 1 / 0 | none |
| h12 | conservative | PATH_ONLY_UNDERDETERMINED | insufficient_evidence | 0 | 0 | 0 / 0 / 0 / 1 / 0 | none |
| h13 | conservative | PATH_ONLY_UNDERDETERMINED | insufficient_evidence | 0 | 0 | 0 / 0 / 0 / 0 / 1 | none |
| h14 | conservative | PATH_ONLY_UNDERDETERMINED | insufficient_evidence | 0 | 0 | 0 / 0 / 0 / 0 / 1 | none |
| h15 | conservative | HARD | succeeded | 0 | 1 | 0 / 1 / 1 / 0 / 0 | misleading_naming |
| h16 | conservative | PATH_ONLY_UNDERDETERMINED | insufficient_evidence | 0 | 0 | 0 / 0 / 0 / 1 / 0 | none |
| h17 | conservative | MEDIUM | insufficient_evidence | 0 | 0 | 0 / 1 / 0 / 0 / 0 | multiple_valid_choices |
| h18 | conservative | HARD | insufficient_evidence | 0 | 0 | 0 / 2 / 0 / 0 / 0 | multiple_valid_choices |
| h19 | conservative | EASY | insufficient_evidence | 0 | 0 | 0 / 1 / 0 / 0 / 0 | none |
| h20 | conservative | MEDIUM | succeeded | 0 | 1 | 0 / 1 / 0 / 0 / 0 | cross_directory_relationship |
| h21 | conservative | HARD | succeeded | 0 | 1 | 0 / 1 / 1 / 0 / 0 | misleading_naming |
| h22 | conservative | HARD | insufficient_evidence | 0 | 0 | 0 / 1 / 0 / 0 / 0 | misleading_naming |
| h23 | conservative | MEDIUM | insufficient_evidence | 0 | 0 | 0 / 2 / 0 / 0 / 0 | multi_file_relationship |
| h24 | conservative | MEDIUM | insufficient_evidence | 0 | 0 | 0 / 2 / 0 / 0 / 0 | multi_file_relationship |
| h25 | conservative | MEDIUM | insufficient_evidence | 0 | 0 | 0 / 2 / 0 / 0 / 0 | package_relationship |
| h26 | conservative | MEDIUM | succeeded | 0 | 1 | 0 / 1 / 0 / 0 / 0 | package_relationship |
| h27 | conservative | MEDIUM | succeeded | 1 | 0 | 0 / 0 / 0 / 0 / 0 | none |
| h28 | conservative | MEDIUM | succeeded | 1 | 0 | 0 / 0 / 0 / 0 / 0 | none |
| h29 | conservative | PATH_ONLY_UNDERDETERMINED | insufficient_evidence | 0 | 0 | 0 / 0 / 0 / 1 / 0 | none |
| h30 | conservative | PATH_ONLY_UNDERDETERMINED | insufficient_evidence | 0 | 0 | 0 / 0 / 0 / 1 / 0 | none |
| h31 | conservative | MEDIUM | succeeded | 0 | 1 | 0 / 1 / 0 / 0 / 0 | cross_directory_relationship |
| h32 | conservative | MEDIUM | insufficient_evidence | 0 | 0 | 0 / 2 / 0 / 0 / 0 | cross_directory_relationship |
| h33 | conservative | HARD | succeeded | 0 | 1 | 0 / 2 / 0 / 0 / 0 | multi_file_relationship |
| h34 | conservative | HARD | insufficient_evidence | 0 | 0 | 0 / 3 / 0 / 0 / 0 | multi_file_relationship |
| h35 | conservative | PATH_ONLY_UNDERDETERMINED | insufficient_evidence | 0 | 0 | 0 / 0 / 0 / 1 / 0 | none |
| h36 | conservative | PATH_ONLY_UNDERDETERMINED | insufficient_evidence | 0 | 0 | 0 / 0 / 0 / 1 / 0 | none |

### Threshold pass/fail matrix

| Gate | lexical | path_score | conservative |
| --- | --- | --- | --- |
| safety | PASS | PASS | PASS |
| precision | FAIL | FAIL | PASS |
| recall | FAIL | PASS | FAIL |
| required_recall | FAIL | PASS | FAIL |
| acceptable_sets | FAIL | FAIL | FAIL |
| abstention | FAIL | FAIL | PASS |
| create | PASS | PASS | PASS |
| false_sufficient | FAIL | FAIL | FAIL |
| catastrophic | PASS | PASS | FAIL |
| median | PASS | PASS | PASS |
| p90 | FAIL | PASS | PASS |
| manual_burden_reduction | PASS | PASS | FAIL |
| EASY | FAIL | FAIL | FAIL |
| MEDIUM | FAIL | FAIL | FAIL |
| HARD | FAIL | FAIL | FAIL |
| PATH_ONLY_UNDERDETERMINED | FAIL | FAIL | PASS |

CONTENT-ASSISTED DISCOVERY JUSTIFIED

## Local qualification record

All 24 phases of `uv run python .\validate_forgeai_discovery_2a1.py` passed on
2026-10-04: 185 DISCOVERY-1 regressions, 68 original DISCOVERY-2A tests,
163 held-out/architecture tests (122 new held-out tests plus 41 existing architecture
tests), mypy, Ruff lint/format and git diff checks. Focused phase repetitions are
not additional independent observations. Frozen report reproduction passed.
The protected-source diff is empty. No baseline/fixture/threshold/report revision,
production behavior, ADR, model call, Docker run or Git commit was introduced.

CONTENT-ASSISTED DISCOVERY JUSTIFIED
