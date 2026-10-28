Controls: 05706c6a. Retained metadata transcription; UNKNOWN is not an unresolved verdict. No superiority claim.

| Task | P1 | P1b | P1c | P2 | P3 | P3g |
|---|---|---|---|---|---|---|
| fastapi_14492 | RESOLVED | RESOLVED | RESOLVED | RESOLVED | RESOLVED | RESOLVED |
| rich_3905 | RESOLVED | RESOLVED | RESOLVED | RESOLVED | RESOLVED | RESOLVED |
| fastapi_5624 | RESOLVED | RESOLVED | UNRESOLVED | RESOLVED | RESOLVED | RESOLVED |
| rich_3454 | RESOLVED | RESOLVED | RESOLVED | RESOLVED | RESOLVED | RESOLVED |
| rich_3934 | UNRESOLVED | UNRESOLVED | UNRESOLVED | UNKNOWN | UNRESOLVED | UNRESOLVED |
| fastapi_15800 | UNRESOLVED | UNRESOLVED | UNRESOLVED | UNKNOWN | UNRESOLVED | UNRESOLVED |
| rich_4075 | UNRESOLVED | UNRESOLVED | UNRESOLVED | UNRESOLVED | UNRESOLVED | UNRESOLVED |
| fastapi_14419 | RESOLVED | UNRESOLVED | RESOLVED | UNKNOWN | UNRESOLVED | UNRESOLVED |
| rich_3471 | UNRESOLVED | UNKNOWN | UNRESOLVED | UNKNOWN | UNRESOLVED | UNRESOLVED |
| fastapi_5077 | RESOLVED | UNRESOLVED | UNRESOLVED | RESOLVED | RESOLVED | UNRESOLVED |
| rich_4079 | UNRESOLVED | UNRESOLVED | UNRESOLVED | UNRESOLVED | UNRESOLVED | UNRESOLVED |
| fastapi_11194 | UNRESOLVED | RESOLVED | RESOLVED | RESOLVED | RESOLVED | RESOLVED |
| rich_4076 | UNRESOLVED | UNRESOLVED | UNRESOLVED | UNRESOLVED | UNRESOLVED | UNRESOLVED |
| fastapi_14786 | RESOLVED | RESOLVED | RESOLVED | RESOLVED | RESOLVED | RESOLVED |
| rich_3067 | RESOLVED | RESOLVED | RESOLVED | RESOLVED | RESOLVED | RESOLVED |
| fastapi_15589 | UNRESOLVED | RESOLVED | UNRESOLVED | UNRESOLVED | UNRESOLVED | UNRESOLVED |

P3 dev-16v same-config replicate (maintainer-reported; attempt2 artifacts not
independently analyzed). The historical six-run table above retains P3 attempt1.
Attempt2 completed in 4935 s and is retained at
`C:\Work\Gemma4Localtest\local_eval_p3_dev16v_attempt2`.

| Measure | P3 attempt1 | P3 attempt2 |
|---|---:|---:|
| Resolved / verifiable | 8/16 | 6/16 |
| ContextWindowExceeded | 0 | 0 |
| Session timeouts | 4 | 6 |
| Mean task duration (approximate) | 244 s | 273 s |
| Mean-based projected runtime (approximate) | 8.0 h | 8.9 h |

Two outcome flips: `fastapi_5624` 1 -> 0 and `fastapi_11194` 1 -> 0
(the latter via session timeout). Attempt2 session timeouts: `rich_3934`,
`fastapi_14419`, `rich_3471`, `rich_4079`, `fastapi_11194`, `fastapi_15589`.

Observed noise floor for the maintainer's decision: **2 flips**. This is one
same-config replicate, not an estimated population bound or significance test.
P4 must satisfy **both >=11/16 resolved and bootstrap_upper95_hours <=11 h**.
The 8.9 h projection is mean-based and does not establish bootstrap gate success.
At this pre-registration stage no P4 result or adoption decision was available; the later decision is recorded below.

P4 dev-16v attempt1: **COMPLETED**, 4597 s, retained at
`C:\Work\Gemma4Localtest\local_eval_p4_dev16v`. Maintainer-reported results:
8/16, two session timeouts (P3 attempts: four and six), zero context errors,
mean task duration approximately 253 s, mean-based projection approximately
8.3 h, bootstrap upper95 approximately 8.7 h. Timeout task identities were not
supplied. Gains versus P3 attempt1: `fastapi_14419`, `rich_4079`; losses:
`fastapi_5624`, `fastapi_11194`. The maintainer reports `rich_4079` as its first
success in eight runs (unsolved in the seven earlier runs).

**Decision: retain P3.** P4 - P3 attempt1 = 0 <= observed flip floor 2;
8/16 fails the pre-registered >=11/16 score requirement. The reported bootstrap
8.7 h meets <=11 h, but both conditions are required. Four paired outcome flips
(two gains, two losses) are distinct from the zero net gain. No superiority claim.

Eight comparable dev-16v runs, confirmed by the maintainer: P1 (dev-30
restricted to dev-16v), P1b (attempt1+attempt2 merged as one run), P1c, P2,
P3 attempt1, P3g, P3 attempt2 and P4 attempt1. There is no ninth run.
UNKNOWN below preserves historical verdicts; it is not an unresolved outcome.
Solve frequency uses all eight runs and is pending where any verdict is UNKNOWN.
P3 attempt2/P4 columns are transcribed from the reported exhaustive flips.

| Task | P3 attempt2 | P4 attempt1 | Confirmed solved | Confirmed unresolved | Unknown | Solve frequency |
|---|---|---|---:|---:|---:|---|
| fastapi_14492 | RESOLVED | RESOLVED | 8 | 0 | 0 | 8/8 |
| rich_3905 | RESOLVED | RESOLVED | 8 | 0 | 0 | 8/8 |
| fastapi_5624 | UNRESOLVED | UNRESOLVED | 5 | 3 | 0 | 5/8 |
| rich_3454 | RESOLVED | RESOLVED | 8 | 0 | 0 | 8/8 |
| rich_3934 | UNRESOLVED | UNRESOLVED | 0 | 7 | 1 | Pending: 1 UNKNOWN |
| fastapi_15800 | UNRESOLVED | UNRESOLVED | 0 | 7 | 1 | Pending: 1 UNKNOWN |
| rich_4075 | UNRESOLVED | UNRESOLVED | 0 | 8 | 0 | 0/8 |
| fastapi_14419 | UNRESOLVED | RESOLVED | 3 | 4 | 1 | Pending: 1 UNKNOWN |
| rich_3471 | UNRESOLVED | UNRESOLVED | 0 | 6 | 2 | Pending: 2 UNKNOWN |
| fastapi_5077 | RESOLVED | RESOLVED | 5 | 3 | 0 | 5/8 |
| rich_4079 | UNRESOLVED | RESOLVED | 1 | 7 | 0 | 1/8 |
| fastapi_11194 | UNRESOLVED | UNRESOLVED | 5 | 3 | 0 | 5/8 |
| rich_4076 | UNRESOLVED | UNRESOLVED | 0 | 8 | 0 | 0/8 |
| fastapi_14786 | RESOLVED | RESOLVED | 8 | 0 | 0 | 8/8 |
| rich_3067 | RESOLVED | RESOLVED | 8 | 0 | 0 | 8/8 |
| fastapi_15589 | UNRESOLVED | UNRESOLVED | 1 | 7 | 0 | 1/8 |
