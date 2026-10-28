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
No P4 result, new adoption decision or statistical superiority is claimed.
