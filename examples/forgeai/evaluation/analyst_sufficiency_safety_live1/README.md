# forgeai-analyst-sufficiency-safety-live/1

**Status: harness implemented, local validation pending. No baseline has been
run; the baseline is not authorized.** See
[the decision record](../../../../planning/FORGEAI-ANALYST-SUFFICIENCY-SAFETY-LIVE-1.md).

This is the live baseline harness for EvidenceSufficiencyAgent 1.0.0 /
`qwen2.5-coder:14b`. It runs against frozen
`forgeai-analyst-sufficiency-safety-eval/2` only, and revision 1 is refused.
The report identity is `forgeai-analyst-sufficiency-safety-live-report/1`.

## Modules

- `identity.py`: admission, the closed binding (freeze, Agent, parser, model
  and runtime pins, budgets) and the zero-semantic-call preflight.
- `inputs.py`: authorized initial evidence, the payload serialization and the
  pre-dispatch leakage guard.
- `harness.py`: the sequential s01..s22 controller (one initial call each),
  stop rules, lifecycle and the report.
- `storage.py`: exclusive immutable run custody and report validation.
- `report-schema.json`: the required report fields.

The LIVE-1 runtime (child isolation, guard, diagnostics, lifecycle and store
writes) is reused unchanged.

## Operator commands

Run these from `examples/forgeai/evaluation`. Each needs separate
authorization.

```
uv run python -m analyst_sufficiency_safety_live1 PREFLIGHT --output <fresh dir> --approval-reference <ref>
uv run python -m analyst_sufficiency_safety_live1 BASELINE --output <fresh dir> --approval-reference <ref>
```

## Qualification

Run from the repository root, offline:
`uv run python .\validate_forgeai_analyst_sufficiency_safety_live_1.py`.
