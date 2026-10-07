# forgeai-analyst-sufficiency-safety-live/2

**Status: LOCALLY QUALIFIED (2026-10-07; offline; 41/41 validator phases).
No preflight or baseline has been run under live/2; neither is authorized.** See
[the decision record](../../../../planning/FORGEAI-ANALYST-SUFFICIENCY-SAFETY-RUNTIME-IDENTITY-2.md).

This is a runtime identity revision only. Live/2 pins **Ollama 0.40.0**
exactly; live/1 (`../analyst_sufficiency_safety_live1/`) stays pinned to
0.35.1, unchanged and never baselined. The report identity is
`forgeai-analyst-sufficiency-safety-live-report/2`.

Everything else is live/1's, reused unchanged: the SAFETY-EVAL-2 condition,
Agent/prompt/parser pins, model tag and digest, membership and order, budgets,
leakage guard, controller, scoring, stop rules and report semantics.

## Modules

- `identity.py`: the live/2 binding (live/1's binding plus the 0.40.0 pin and
  the compatibility record) and the exact-pin preflight.
- `runtime-compat-2.json`: the frozen 0.35.1 → 0.40.0 provider review.
- `storage.py`: live/2 custody; validates with the unchanged live/1 rules.
- `harness.py`: the operator entry; runs the unchanged live/1 controller.
- `custody.py`: exact Git-tree pins for every committed run directory,
  including the live/1 refusal artifact.

## Operator commands

Run from `examples/forgeai/evaluation`. Each needs separate authorization.

```
uv run python -m analyst_sufficiency_safety_live2 PREFLIGHT --output <fresh dir> --approval-reference <ref>
uv run python -m analyst_sufficiency_safety_live2 BASELINE --output <fresh dir> --approval-reference <ref>
```

## Qualification

Run from the repository root, offline:
`uv run python .\validate_forgeai_analyst_sufficiency_safety_runtime_identity_2.py`.
