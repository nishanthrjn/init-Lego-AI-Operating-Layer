# FORGEAI-ANALYST-EVIDENCE-LOOP-1

**IMPLEMENTED — LOCAL VALIDATION PENDING.** Evaluation-only scripted application
sequence; not a production Analyst workflow, new Agent or semantic-quality claim.
Prerequisite: [locally qualified sufficiency contracts](../../../../packages/legoai-engineering/docs/analyst-sufficiency.md).

## Sequence and operator ownership

`EvidenceSequence` starts with an immutable initial manifest and an externally
composed `AuthorizedRepositoryEvidence`. Initial evidence must already have been
acquired through that authorized seam; fixtures do this too. The sequence does
not issue a grant or construct a workspace adapter.

1. Submit a scripted `EvidenceSufficiencyResult` under a fresh `ExecutionId`.
2. Review its coverage and requests. `OperatorReview` binds the exact manifest
   identity and assessment invocation, with an explicit accept/decline choice.
3. If sufficient, `progress` records review and returns `ELIGIBLE_FOR_ANALYSIS`.
4. Otherwise, `advance` permits one operator-selected acquisition **or** one
   clarification. A batch of up to eight named requests may share that round.
5. Rebuild the manifest and submit a second, separately attributed assessment.
   An unresolved reassessment stops immediately. A sufficient reassessment still
   needs fresh progression review; the acquisition review cannot stand in for it.

`ASSESS`, `REVIEW` and `ACQUIRING` are intermediate evaluation states. The
decision states are `ELIGIBLE_FOR_ANALYSIS` and `STOPPED`. A stopped sequence
cannot be revived. No automatic loop, retry, callback or recursive expansion
exists. Invalid sequencing also stops; it cannot create another call slot.

`PathSelection` is trusted operator/application input: a current request index
and exact known repository path. A named request must match that path exactly.
A source-role request contains no filename; the operator supplies its path.
No path is extracted from descriptions, imports, directory listings or model
text. One path per selected request is supported in this bounded profile.

`ClarificationSelection` supplies an answer and the explicit revised question.
It updates the matching declaration, or adds one for a newly raised request.
Choices must satisfy the existing contract. Unrelated declarations/unknowns are
preserved. Acquisition and clarification cannot be combined in this one-round
profile; a condition requiring both must stop unresolved for separate handling.
Declining review also stops visibly, without acquisition.

## Authority and attribution

The reader is concretely checked at composition and used through
`RepositoryEvidencePort`. Operator consent does not override its path allowlist,
tenant, current read-for-model-analysis/disclosure authorization or release check.
Every acquired file passes `AuthorizedRepositoryEvidence`; no filesystem read
bypass exists in the sequence. Denial remains an operational failure.

New evidence consists only of the initial files plus the exact selected additions.
Replacing an existing path, case-insensitive duplicates, unrequested additions
and unrelated reader responses are refused. There is no hidden-fixture union.
Source-role expectations are bound only to explicitly selected supplied paths.
The immutable `RoundRecord` retains selections and before/after identities;
observations also retain both assessments and operator reviews. Raw content is
excluded from repr; no report serializer or persistence is added.

Every successful round changes manifest identity. Old assessments/reviews fail
against the revised condition. `advance`, `progress` and the optional scripted
analysis claim require the caller's current manifest. Changed question, contents,
paths, provenance or clarification causes a visible stale stop. The sequence
does not independently detect disk changes: manifests remain read observations,
not snapshots. Stable workspace/trusted composition limitations remain explicit.
A future actual Analyst composition must revalidate its reacquired evidence
before model dispatch; this slice does not implement that integration.

Eligibility has no editable targets, Coding/Reviewer scope, mutation authority,
grant or production worker invocation. It does not prove source-role relevance,
semantic completeness or final-answer correctness. Operator review is an
application record, not an authenticated credential or ADR-010 Approval.

## Fixed budgets and failure behavior

- At most two sufficiency assessment submissions; at most one scripted final
  analysis claim; at most one acquisition/clarification round.
- Invocation identities are unique across both kinds within this sequence.
  `claim_scripted_analysis` accounts for a fake call slot only: it never invokes
  RepositoryAnalyst, M7 or a model. No execution-global registry is introduced.
- At most eight cumulative complete files, 8192 UTF-8 bytes per file and 24576
  total bytes; a revised question retains the existing 2048-character/byte bound.
  Seven initial plus two selected files fails before acquisition. Aggregate
  overflow after authorized acquisition releases no revised manifest/eligibility.
- Round reservation precedes acquisition. Concurrent/reentrant second requests
  fail closed. No retry follows partial reads or release denial. Unexpected
  adapter errors/cancellation stop the sequence and propagate their original cause.

Closed operational failures remain distinct: invalid output, model failure,
acquisition denied, evidence unavailable, authorization failure, budget exhausted,
stale assessment and prerequisites unmet. Reader `DENIED`, `UNAVAILABLE`,
`BOUNDARY` and `BUDGET` map respectively to acquisition denied, evidence
unavailable, authorization failure and budget exhausted. The existing reader
does not distinguish unavailable governance from unavailable evidence; this
evaluation does not invent that distinction. Semantic unresolved, operator
decline, invalid review/sequence and duplicate invocation are separate stop reasons.

## Scripted coverage and qualification

Flows A–H cover direct sufficiency, q21-like catalog acquisition, q22-like intent
clarification, q19-like denied implementation acquisition, unresolved reassessment,
stale inputs, unrelated evidence and exhaustion of the single round. Additional
cases cover per-read/release revocation, unavailable/boundary errors, cumulative
bounds, all operational failures, unique identities, no target promotion and
closed imports. Fixtures use a synthetic workspace behind the actual authorized
reader and public local-host governance; all assessment outputs are scripted.

Run from repository root:

```powershell
uv run python .\validate_forgeai_analyst_evidence_loop_1.py
```

The 42-phase validator runs the full scripted suite once and references its
passing named cases for individual requirements. It also runs authorized-reader,
sufficiency-contract, legacy Analyst, M7, worker, frozen R3/R4 and architecture
regressions; mypy; Ruff lint/format; and diff integrity. Dependencies are offline
and installed; no live model, external provider or Docker is used.

RepositoryAnalyst 1.0.3, its prompt/parser, Core, ForgeAI production code and
frozen evaluation history remain unchanged. No UI, discovery, Workflow, Team,
Planner, persistence or execution resume is implemented. G07 remains open.
The next slice is FORGEAI-ANALYST-DESIGN-EVAL-1, requiring separate authorization;
neither that slice nor any live condition is implemented here.
