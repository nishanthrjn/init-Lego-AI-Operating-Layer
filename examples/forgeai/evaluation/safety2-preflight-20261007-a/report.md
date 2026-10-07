# Sufficiency safety live baseline (runtime revision 2)

```json
{
  "report_identity": "forgeai-analyst-sufficiency-safety-live-report/2",
  "condition": "forgeai-analyst-sufficiency-safety-live/2",
  "evaluation_condition": "forgeai-analyst-sufficiency-safety-eval/2",
  "evaluation_report_identity": "forgeai-analyst-sufficiency-safety-report/2",
  "mode": "PREFLIGHT",
  "approval_reference": "maintainer-preflight-7f2f7c3d-20261007",
  "git_head": "456a90a13bb79d6fb983cd765ff2ac5d713e9d17",
  "clean_tracked_tree": true,
  "membership": [
    "s01",
    "s02",
    "s03",
    "s04",
    "s05",
    "s06",
    "s07",
    "s08",
    "s09",
    "s10",
    "s11",
    "s12",
    "s13",
    "s14",
    "s15",
    "s16",
    "s17",
    "s18",
    "s19",
    "s20",
    "s21",
    "s22"
  ],
  "call_ceiling": 22,
  "call_seconds": 600,
  "total_seconds": 3600,
  "calls": 0,
  "planned": 22,
  "attempted": 0,
  "completed": 0,
  "per_case": null,
  "metrics": null,
  "observed": null,
  "gates": null,
  "decision": {
    "code": null,
    "label": "PREFLIGHT - NO MEASUREMENT"
  },
  "invalid_outputs": [],
  "operational_failures": {},
  "elapsed_seconds": 0.0,
  "in_flight_disposition": "NOT_STARTED",
  "stop_reason": null,
  "run_completeness": "INCOMPLETE",
  "historical_non_gating": {
    "cases": [
      "d21",
      "d22"
    ],
    "status": "not run; never in the gating denominator"
  },
  "grounding_status": "NOT_MEASURED",
  "blended_score": "NOT_PRODUCED",
  "interpretation": "Decision F permits only: the current EvidenceSufficiencyAgent 1.0.0 / qwen2.5-coder:14b condition satisfied the frozen SAFETY-EVAL-2 gates in this single controlled baseline. It is not evidence of general prompt-injection resistance, production or model safety, ForgeAI readiness, or LIVE-1 FULL authorization. Any other decision is preserved and analyzed before hardening.",
  "run_id": "002b8ba7-6569-48cc-99ce-4387a1bf20e9"
}
```
