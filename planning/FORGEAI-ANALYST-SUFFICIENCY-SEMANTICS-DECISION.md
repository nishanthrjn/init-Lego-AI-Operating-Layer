# ANALYST-SUFFICIENCY-SEMANTICS-DECISION: what `succeeded` and `insufficient_evidence` mean

Status: decision record (2026-10-06). There are no changes to production code,
prompts, parser, oracle, thresholds or models, and no model run. This record
settles semantics only. Any later prompt change must encode exactly what is
approved here.

## 1. Problem statement

The `succeeded` / `insufficient_evidence` status is RepositoryAnalyst's only
signal for whether the supplied evidence answers the question.
- Under Analyst 1.0.1 the model under-answered: it abstained on most answerable
  cases.
- Under 1.0.2 both models over-answered: they marked genuinely insufficient
  cases `succeeded`.
- ANALYST-MODEL-COMPARE-1 showed that a stronger model solves answerable cases
  but not this discrimination.

Before any further prompt change, the canonical meaning of both statuses has to
be fixed, independently of the current fixtures.

## 2. Evidence summary (recorded facts; no causal claim)

| Condition | Analyst | Model | Held-out answerable success | Held-out insufficient correctness | False-sufficient |
| --- | --- | --- | --- | --- | --- |
| r2 (`2e8f1ab`) | 1.0.1 | 7b | 13/60 | 11/12 | 1 |
| insufficient diagnostic (`fa4aa8f`) | 1.0.1 | 7b | 17/60 | 10/12 | 2 |
| R3 (`9442ef3`) | 1.0.2 | 7b | 28/60 | 3/12 | 10 |
| model comparison (`46ef93f`) | 1.0.2 | 14b | **59/60** | 4/12 | 8 |

The 14b passes validity, precision (98.1%), required recall (98.7%) and
acceptable set (95.0%). It fails only insufficient correctness and
false-sufficient. Every held-out false-sufficient call is on q19 (2/3), q21
(3/3) and q22 (3/3). q20 abstained correctly 3/3.

**How to read this evidence:**
- The results show that answerable-case reasoning scales with the model.
- They show that the 1.0.2 wording moved status decisions toward `succeeded`
  for both models.
- They do **not** prove that the oracle is correct, or that 1.0.1 was correct;
  1.0.1 abstained on almost everything.

The semantics below are grounded in the product and architecture, and use the
evaluations only as diagnostics.

## 3. Current 1.0.2 wording (status policy, verbatim excerpts)

- "choose succeeded when the supplied evidence is sufficient for a defensible
  analysis of the question, that is, when you can identify the relevant supplied
  files, state findings supported by them and explain any remaining gaps."
- "Choose insufficient_evidence only when missing or unavailable evidence
  prevents a defensible analysis of the question."
- "Do not choose insufficient_evidence merely because the wider repository is
  not visible, some uncertainty or risk remains, **related files may exist
  elsewhere**, or a requested change or behavior is not yet implemented in the
  supplied code."
- "For a change request, the absence of the requested behavior is not missing
  evidence; if the supplied evidence identifies and explains the relevant code,
  the status is succeeded."

**What the wording gets right:**
- uncertainty is not insufficiency;
- an unimplemented future behavior is not missing evidence.

**What it gets wrong:**
- "Identify the relevant supplied files" can be met by a caller or a list of
  candidates, so it does not require the evidence that **governs** the
  requested conclusion.
- "Related files may exist elsewhere" is too broad. It is true of almost every
  question, and it covers the case where the one file that matters is the
  missing one.
- Ambiguity among supplied candidates is not addressed at all.

## 4. Canonical semantic definitions (adopted)

**Governing evidence:** the supplied content without which the requested
conclusion cannot be stated without guessing. For example:
- the definition or implementation whose behavior or value the question
  concerns;
- the authoritative data or configuration source that holds it;
- the content that establishes which of several candidates is meant.

It is determined by the question, never by a path count.

**`succeeded`:** the supplied evidence contains the governing evidence for the
requested conclusion. That includes, where the question requires it,
identifying the current implementation or authoritative source and its
ownership, so the Analyst can state the conclusion and support its findings
with supplied paths.
- `succeeded` does **not** mean certainty.
- Residual uncertainty that does not change the conclusion goes in `risks` and
  `unknowns`: for example, untested edge cases, unseen callers, deployment
  context, or the effect of the change elsewhere.

**`insufficient_evidence`:** the supplied evidence does not permit the requested
conclusion without guessing beyond it, because governing evidence is absent or
the target is materially ambiguous. Qualifying situations:
1. **Governing implementation absent:** the code that determines what the
   question asks about is not supplied. A reference to it (an import, a call
   site, a docstring naming its location) is evidence that it exists and where,
   **not** evidence of its content.
2. **Authoritative data or configuration absent:** the value, message, rule or
   setting the question concerns lives in an unsupplied source.
3. **Unresolved ownership or ambiguity:** several supplied candidates plausibly
   match the request, and the evidence does not establish which one is meant or
   authoritative.
4. **Required relationship not establishable:** the question asks how supplied
   parts relate, and the supplied evidence does not show that relationship.

**Not qualifying:**
- context that would merely be useful but is not needed;
- the general possibility of unseen related files;
- residual risk;
- absent future behavior (section 5).

**Field consequences:** these are the existing parser invariants; nothing
changes.
- Under `insufficient_evidence`, `findings` is empty and `unknowns` names what
  is missing or ambiguous.
- `relevant_files` may list the supplied context or candidates.

## 5. Absent future behavior vs absent current implementation

| Concept | Meaning | Status consequence |
| --- | --- | --- |
| **A. Absent requested future behavior** | The question asks for something that does not exist yet (add a field, add a warning, support a new case). | Not missing evidence. If the supplied evidence contains the current code the change must build on or modify, the conclusion is defensible, so `succeeded`. |
| **B. Absent governing current implementation** | The supplied files reference, call or document the code or data the question is about, but that code or data is not supplied. | Missing governing evidence, so `insufficient_evidence`. A caller is not the owner, and a reference is not the content. |
| **C. Ambiguous ownership or target** | Several supplied candidates plausibly match, and nothing supplied decides between them. | Materially ambiguous, so `insufficient_evidence`. |

The concepts are independent. A request can be A and B at once: new behavior
whose required base implementation is unsupplied. In that case B governs.

## 6. Ambiguity semantics (adopted)

If several supplied candidates plausibly own or govern the requested behavior,
and the supplied evidence cannot establish which one is meant or authoritative,
the Analyst returns `insufficient_evidence`:
- it lists the candidates in `relevant_files`;
- it names the unresolved choice in `unknowns`;
- it does not select one speculatively.

**Architectural fit:**
- It matches the evidence-first contract ("do not claim contents of files not
  supplied") and ADR-005's principle that ambiguous mappings cannot establish
  protected authority.
- It keeps the downstream step, operator-confirmed editable targets,
  meaningful: the Analyst surfaces the ambiguity instead of resolving it by
  guess.
- Analytical ambiguity is not an authorization question. Resolving it is the
  operator's job, through clarification or a separately confirmed evidence
  read, not the Analyst's.

## 7. Relevance vs sufficiency

Relevance and sufficiency are separate judgements.
- A file can be relevant (a caller, a candidate, a context module) while the
  evidence is still insufficient.
- `relevant_files` may be non-empty under `insufficient_evidence`, as the
  parser already permits.
- `findings` stay empty under `insufficient_evidence`. A finding is a conclusion
  supported by evidence; when the governing evidence is absent there is no
  supported conclusion to state.
- `unknowns` must name the missing governing evidence or the unresolved
  ambiguity.

No parser change is warranted. Relevance never becomes editability, and nothing
in this record creates a target, grant or read.

## 8. Expected-insufficient oracle audit

**Held-out (gating), frozen `heldout-v1.json`:**

| Case | Question (paraphrased) | Supplied | Missing or unresolved | Category | Insufficient under section 4? |
| --- | --- | --- | --- | --- | --- |
| q19 | change the percentage applied by `apply_loyalty_discount` | `cart/checkout.py` (imports and calls it), `cart/items.py` | the definition, in unsupplied `cart/loyalty.py` | B: governing implementation absent | **Yes** |
| q20 | fix the next-run calculation bug for monthly jobs | `jobs/runner.py` (calls `schedule.next_run`), `jobs/models.py` | the schedule module | B: governing implementation absent | **Yes** |
| q21 | update the customer message for declined card payments | `payments/errors.py` (docstring: messages live in a translation catalog), `payments/gateway.py` | the catalog | B: authoritative data absent | **Yes** |
| q22 | make the timeout longer | four timeout constants in three files | which timeout is meant | C: ambiguous target | **Yes** |

**Answerable control for concept A:** q11 (add a currency code) and q12
(record a failed-login warning) request behavior that does not yet exist, and
their governing current code is supplied. They are correctly `succeeded` under
section 5. The frozen workload therefore tests both sides of the distinction.

**Non-gating CD-1 partitions** (supporting and probe; never gate):

| Case | Question | Category | Insufficient under section 4? |
| --- | --- | --- | --- |
| c13 (supporting) | identify which component applies rounding | B: the driver imports an unsupplied module | Yes |
| c14 (supporting) | determine the preferred export format | C: two implementations; preference not evidenced | Yes |
| c16 (probe) | choose whether to retain or remove historic records | C: the decision is not evidenced | Yes |
| c20 (probe) | introduce a new file for absent archival support | A and B: frozen read truth requires the unsupplied `archive/options.py` | Yes |
| **c15** (probe) | add a new file for missing device enrollment | **A only:** the supplied file shows enrollment is absent; no required read is unsupplied | **No.** Under section 5 this is absent future behavior with its relevant current code supplied. Its `insufficient_evidence` label is **semantically inconsistent** with the adopted definition. |

The c15 label comes from the CONTENT-DISCOVERY-1 create-probe design, which
tested that discovery invents no create targets. That is an authority concern,
not an evidence-sufficiency concern. It is recorded here and **not edited**.

## 9. q19, q20, q21, q22 under the 14b (fixture structure only; no narrative)

The three failing cases share one feature: the supplied evidence **names or
points at** the governing source, without containing it.
- **q19:** the supplied caller imports and calls the exact symbol in the
  question, so a plausible answer ("change the rate in `apply_loyalty_discount`")
  can be written from the call site alone. The 1.0.2 clause "related files may
  exist elsewhere" and the "identify the relevant code" criterion both read as
  satisfied by the caller.
- **q21:** the supplied docstring states where the messages live. Explaining
  *where* the answer lies reads as a "defensible analysis", although the content
  that must change is absent.
- **q22:** every candidate is supplied and relevant. Listing all of them
  satisfies "identify the relevant supplied files". The 1.0.2 policy says
  nothing about choosing among candidates.

**q20 is the useful contrast.** Its structure resembles q19 (a caller of an
unsupplied module), but the question asks to *fix a bug in a calculation*. No
plausible conclusion can be written without the calculation's logic, so the
missing content is self-evidently governing. In q19 a parameter-style change can
be phrased from the call site alone.

**The semantic distinction q20 exposes:** whether the governing evidence is
supplied, not whether the question can be *phrased* from what is supplied. A
reference to unsupplied code or data is not that code or data. This is exactly
category B in section 4.

## 10. Option comparison

| Criterion | A. Strict evidence sufficiency | B. Contextual best-effort | C. Task-type dependent |
| --- | --- | --- | --- |
| Avoids fabricated ownership | Yes: no conclusion beyond the governing evidence | No: a caller or a guess becomes a `succeeded` answer | Partly, depending on how each type is defined |
| Fits operator-confirmed reads and targets | Yes: insufficiency surfaces what to read or confirm next | Weak: downstream steps see confident output built on missing evidence | Yes, but with more contract surface |
| Usefulness to ForgeAI | High: `relevant_files` and `unknowns` still carry context under insufficiency | Superficially high; misleading when the owner is missing | High in principle |
| Objective evaluation | Yes: the governing evidence is decidable from the question and the supplied set | Hard: "useful" has no stable criterion | Needs a type taxonomy, an oracle per type and classifier risk |
| Minimal special cases | One definition, parametrised by "the requested conclusion" | One definition, but it erodes the status signal | Several standards |
| Reusable beyond ForgeAI | Yes | Yes | Tied to a question taxonomy |
| Consistent with the evidence | 14b already meets the answerable side; only discrimination remains | Would relabel q19, q21 and q22 as successes; that is fixture-driven and loses the signal | Not needed: A already adapts to the question through "requested conclusion" |

**Option B is rejected.** It collapses the status into "found something
related", which is exactly the R3/14b failure mode, and it would let downstream
steps act on a caller as if it were the owner.

**Option C is rejected for now.** "Governing evidence for the requested
conclusion" already varies naturally with the question. A type taxonomy adds
contract and evaluation surface without a demonstrated need.

## 11. Selected semantics

**Option A: strict evidence sufficiency**, as defined in sections 4-7.

## 12. Oracle consequence

**CURRENT ORACLE SEMANTICS CONSISTENT**, for the gating held-out oracle.
- All four held-out expected-insufficient labels (q19-q22) remain
  `insufficient_evidence` under section 4.
- The answerable concept-A cases (q11, q12) remain `succeeded`.
- No gating label requires revision, so R4 may reuse the frozen held-out
  workload and oracle unchanged.

**Explicit exception, non-gating:** the CD-1 probe c15 label conflicts with
section 5.
- It is not edited, and it affects no gate or decision: probes never gate.
- Any future workload that gates on CD-1 cases must be a **new frozen oracle
  revision** that relabels c15 or redesigns it as an authority probe.
- Until then, R4 reports c15 separately as a known label conflict.

## 13. Prompt consequence

**NARROW ANALYST SEMANTICS CLARIFICATION JUSTIFIED.**

The semantic delta, generic and with no fixture wording:
1. **Define sufficiency by governing evidence.** `succeeded` requires that the
   evidence governing the requested conclusion is supplied: the implementation,
   data or configuration the question concerns, and its owner where the
   question requires it. `succeeded` does not require certainty, and residual
   uncertainty goes in `risks` and `unknowns`. This is kept from 1.0.2.
2. **Replace "related files may exist elsewhere" with the distinction.**
   - Unseen context that the conclusion does not depend on does not justify
     `insufficient_evidence`.
   - Missing governing evidence does justify it.
   - A reference to unsupplied code or data (an import, a call, a stated
     location) does not supply its content.
3. **Keep the future-behavior rule, with its limit.** Absence of requested
   future behavior is not missing evidence, provided the current code the change
   depends on is supplied.
4. **Add the ambiguity rule.** If several supplied candidates plausibly match
   and the evidence does not establish which is meant or authoritative, return
   `insufficient_evidence`: list the candidates in `relevant_files`, state the
   unresolved choice in `unknowns`, and do not select one.
5. **State relevance under insufficiency.** `relevant_files` may list supplied
   context or candidates under `insufficient_evidence`. `findings` remain empty
   and `unknowns` name what is missing. This restates the existing invariants.

**Unchanged:** the six-field schema, parser, values, bounds, membership,
decoder, evidence path, authority, model and provider. This is a version bump
only (1.0.2 → 1.0.3).

**This does not reopen open-ended prompt tuning.** If R4 fails insufficient
correctness under this contract with the 14b, prompt modification stops, and
the task design and Analyst contract are reassessed. One option to weigh then:
a separate, operator-visible sufficiency or evidence-acquisition step.

## 14. Model consequence: `qwen2.5-coder:14b`

**QUALIFIED CANDIDATE FOR NEXT SEMANTIC EXPERIMENT.**
- It achieves near-complete answerable-case performance on this workload, which
  isolates the semantic variable.
- It is pinned at `sha256:9ec8897f…16849`.
- It is not configured globally, has no routing or fallback, and carries no
  claim of overall Analyst qualification.

## 15. `phi4:14b` disposition

**DEFER PHI4 COMPARISON.**
- A second model family measured under the current, semantically ambiguous
  wording cannot separate model from semantics.
- At about 4-5 h per run on this host, there is no strong reason to run it
  before the contract is settled.
- Its pin stays recorded for a possible later run.

## 16. Exact next slice (not implemented)

1. **ENG-ANALYST-SUFFICIENCY-SEMANTICS-1:** RepositoryAnalyst 1.0.2 → 1.0.3.
   - SYSTEM guidance encodes the section 13 delta exactly: generic wording, no
     fixture terms.
   - Parser, values and schema are unchanged.
   - Request-level and semantic tests cover the governing-evidence,
     reference-is-not-content, future-behavior and ambiguity rules, plus parser
     regressions.
   - r2, the insufficient diagnostic, R3 and the model comparison are pinned to
     history and refuse 1.0.3.
2. **CONTENT-DISCOVERY-1Q-R4**, after local qualification and a commit.
   - Pins Analyst 1.0.3 and uses `qwen2.5-coder:14b` at its pinned digest.
   - Reuses the frozen held-out workload, oracle, thresholds, N, decision
     function and the R3/comparison report blocks.
   - Reports c15 as a known non-gating label conflict.
   - Measures insufficient correctness and false-sufficient primarily, and
     must not regress the answerable gates (required recall, acceptable set,
     answerable success).
   - Has a predeclared stop rule: a C or B outcome under the clear contract
     ends prompt modification.

Safety and authority are unchanged throughout: confirmed evidence only, read
and Chat grants, no target, mutation or worker integration.
`insufficient_evidence` never authorizes another read.

## 17. G07 implications

**G07 (evaluated understanding/discovery quality) remains open.** The blocker
is now narrowly located: discriminating governing-evidence insufficiency. The
answerable side is met on this workload with the 14b.

**If R4 passes every frozen gate**, decision A justifies the separately
approved CONTENT-DISCOVERY-2 bounded-orchestration decision. Even then, G07 is
narrowed, not closed, from one synthetic workload.

CONTENT-DISCOVERY-2 and ForgeAI integration remain deferred.

## 18. Implementation status (ENG-ANALYST-SUFFICIENCY-SEMANTICS-1)

Status (2026-10-06): **implemented and locally qualified** (41/41 phases, 52 including sub-phases; no live model or Docker).

- RepositoryAnalyst 1.0.2 → 1.0.3. Only the `analyst/api.py` instruction text
  and version change.
- The SYSTEM guidance encodes the section 13 delta as generic wording:
  governing evidence, `succeeded` requiring it, the four
  `insufficient_evidence` situations, reference-is-not-content, unseen context
  vs governing evidence, future behavior and its limit, ambiguity, and
  relevance vs sufficiency.
- The 1.0.2 clause "related files may exist elsewhere" is removed.
- The parser, schema, evidence, oracle, model, provider, routing and retry are
  unchanged.
- c15 remains a non-gating contract probe, unmodified.
- R2 and the insufficient diagnostic remain pinned to 1.0.1. R3 and the model
  comparison are pinned to 1.0.2 and refuse 1.0.3.
- No new ADR; this record is the rationale.
- Validator: `validate_engineering_analyst_sufficiency_semantics.py`, 41 phases,
  no live model.

Next, unchanged from section 16: CONTENT-DISCOVERY-1Q-R4, after local
qualification and a commit. Live behavior of 1.0.3 is not yet measured. G07
remains open.
