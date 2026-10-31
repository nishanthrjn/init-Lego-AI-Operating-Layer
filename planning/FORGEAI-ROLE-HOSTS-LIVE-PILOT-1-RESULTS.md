# FORGEAI-ROLE-HOSTS-LIVE-PILOT-1 — Results

Date: 2026-10-31

Branch: `br-LegoAI-Comfy-ForgeAI-Gemma4-KISSKI` at `e015d47`.

Provenance: results transcribed from the maintainer-supplied run record.

## Run conditions

- Attended remote role mode.
- Coder: `gemma-4-31b-it`, provider `kisski-saia`, quality `UNQUALIFIED`.
- Reviewer: `deepseek-v4-flash-0731`, provider `kisski-saia`, quality `UNQUALIFIED`.
- `--test-strength` enabled.
- The operator approved every disclosure and patch.

## Fixture runs

Fixtures: `examples/forgeai/evaluation/fixtures`. Each task used a fresh repository,
with no extra constraints beyond the task's own.

| Fixture | Result | Attempts and rework | Test strength | Review | Run ID |
| --- | --- | --- | --- | --- | --- |
| temperature-units | SUCCEEDED | 2; attempt 1 Ruff I001; rework fixed it | DISCRIMINATING | ACCEPT | `exec-c0244d8c852c4d15a7007c2835bfece7` |
| stock-validation | SUCCEEDED | 2; attempt 1 Ruff I001; rework fixed it | DISCRIMINATING | ACCEPT | `exec-2b3313b3480445a5a90dcef4d2860b32` |
| pager-boundaries | SUCCEEDED | 1 | DISCRIMINATING | ACCEPT | `exec-f7dda9f7d86a4207a2ed1f001ea4ae79` |
| text-slug (create) | SUCCEEDED | 1 | DISCRIMINATING | ACCEPT | `exec-b479d3c9f9ff43459f5b4f652b059cd0` |

## Earlier stock_task sandbox runs

The following 2026-10-31 runs used the `stock_task` sandbox (demo fixture):

| Run ID | Conditions and outcome |
| --- | --- |
| `exec-2a5d295468fb4a2997f226108bf3e73d` | Attempt 1 Ruff I001; rework claimed a fix but changed nothing. Stopped with `PROPOSAL_NO_CHANGE`: the first live no-op guard catch. |
| `exec-aceb8c5e74ae4aba93a9350981bedc83` | With an operator import-order constraint: `SUCCEEDED`, 1 attempt, `DISCRIMINATING`, `ACCEPT`. |

The first live run, on **2026-10-29**, used a single model:
`exec-56a3bfc53d064885a0a9f7234d6c35e4`. Rework falsely claimed a fix; the run
ended with `CHECKS_FAILED`.

## Conclusions and evidence limits

- **4/4 fixture tasks succeeded.**
- Ruff I001 (third-party/first-party import grouping) is the recurring coder
  failure. Across the four rework opportunities recorded above, two fixed the
  problem and two falsely claimed a fix.
- The reviewer accepted every candidate submitted for review, so reviewer
  defect detection is not yet evidenced live.
- This is **attended pilot evidence**, not model qualification or admission.
  Both role models remain `UNQUALIFIED`.
