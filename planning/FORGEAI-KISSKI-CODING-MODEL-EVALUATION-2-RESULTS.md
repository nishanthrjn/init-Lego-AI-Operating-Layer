# FORGEAI-KISSKI-CODING-MODEL-EVALUATION-2 — Results

Evidence: maintainer-reported live run, 2026-10-28. No live run or custody-file
inspection was performed by the implementation agent. This separate record does
not alter the pinned v2 preregistration, scoring or manifest.

- V2 manifest: `a5038d5a7a357c06f9ae0c3487b71a0663ffc0430dae06b9eeab56825920a1e9`.
- Pack: `92c43f68…a7bf` (abbreviated as supplied; full digest not supplied).
- Historical v2 commit: `3aa7ee0780092266a63c7a16462523e694724624`.
- Historical v1/dev-screen reproduction commit:
  `3aa7ee0780092266a63c7a16462523e694724624` (maintainer confirmed).
  V1 and dev-screen files are unchanged from SCREEN-2A through that commit;
  the commit only added v2 files. It reproduces all three historical evaluations.
- Phase A custody: `kisski-eval-v2-fv91olhs`.
- Phase B custody: `kisski-eval-v2-_h2a2pi8`.
- Reported run total: 36 chats, all completed, HTTP 200, no rate-limit stops.
  The per-model totals below are 18 outputs each (4 A + 14 B), also 36 combined.

## Per-task evidence

Here “repeat” identifies a sampling repetition; r1/r2/r3 inside review findings
are material IDs, not repetition numbers.

| Task | gemma-4-31b-it | deepseek-v4-flash-0731 |
| --- | --- | --- |
| bug (A) | pass | pass |
| refactor (A) | pass | pass |
| api (A) | pass | pass |
| diagnosis (A) | pass | pass |
| multi (B) | both pass; 2_OF_2 | both pass; 2_OF_2 |
| security (B) | both pass; 2_OF_2 | both pass; 2_OF_2 |
| abstention (B) | both pass; 2_OF_2 | repeat 1 SCHEMA_INVALID; repeat 2 REFERENCE_INVALID; 0_OF_2 |
| review (B) | both find r1/r2, miss r3, WRONG_CATEGORY false positive; repeat 2 also DUPLICATE_REF; 0_OF_2 | repeat 1 SCHEMA_INVALID; repeat 2 schema valid, r1 found, r2/r3 missed, one WRONG_CATEGORY false positive; 0_OF_2 |
| review_heldout (B) | both find h2, miss h1, one WRONG_CATEGORY false positive; 0_OF_2 | both schema valid, zero true positives, missed critical, zero false positives; 0_OF_2 |
| review_clean (B) | both pass; 2_OF_2 | repeat 1 REFERENCE_INVALID; repeat 2 SCHEMA_INVALID; 0_OF_2 |
| abstention_heldout (B) | both pass; 2_OF_2 | repeat 1 pass (correct abstention); repeat 2 REFERENCE_INVALID; 1_OF_2 |

Gemma: MODEL_NOT_QUALIFIED. Zero malformed outputs out of 18. In all four
review/review_heldout responses, the authorization defect (r3/h1) appeared as a
blocking correctness finding instead of security. Diagnostics report
WRONG_CATEGORY in each, and DUPLICATE_REF in review repeat 2.

DeepSeek: MODEL_NOT_QUALIFIED. All coding tasks passed. Six of 18 outputs were
malformed: abstention twice, review once, review_clean twice and
abstention_heldout once. Additional reviewer defects were missed as recorded
above. These are quality observations with completed HTTP-200 responses, not
evidence of the earlier dev-screen account/service rejection.

## Final conclusion

No model qualified. The v2 verdict is final and is not rescored under the new
production instruction. The next step is separately preregistered, frozen v3,
with two new held-out controls. V3 success would establish eligibility for a
separate admission review only; it has no admission effect.

The general reviewer category clarification deliberately invalidates v1/v2 and
dev-screen verification at the changed HEAD. Historical pins remain untouched;
reproduce historical evaluation at its recorded commit rather than refreshing
pins to match the new product definition.
