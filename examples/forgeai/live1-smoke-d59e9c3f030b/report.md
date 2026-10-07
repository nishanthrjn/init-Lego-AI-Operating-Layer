# Sufficiency-only live profile

```json
{
  "report_identity": "forgeai-analyst-sufficiency-live-report/1",
  "sufficiency_profile_identity": "forgeai-analyst-sufficiency-live-profile/1",
  "revision_2_condition_identity": "forgeai-analyst-design-eval/2",
  "run_id": "8abbc78f-628e-4aec-b0da-b822620304e7",
  "mode": "SMOKE",
  "approval_reference": "maintainer-smoke-30c418b6-5de9-4a53-bc94-d089cb783d8b",
  "calls": 1,
  "call_ceiling": 6,
  "elapsed_seconds": 2.8598498000064865,
  "timings": [
    {
      "case": "d01",
      "variant": "initial",
      "phase": "initial",
      "seconds": 0.5949281999928644,
      "user_payload_digest": null,
      "failure": "child_failure"
    }
  ],
  "in_flight_disposition": "SERVER_EFFECT_UNKNOWN",
  "stop_reason": "child_failure",
  "smoke_status": "SMOKE_RUNTIME_FAILURE",
  "planned_slots": [
    {
      "case": "d01",
      "variant": "initial",
      "phase": "initial",
      "status": "NOT_RECORDED",
      "reason": "child_failure"
    },
    {
      "case": "d05",
      "variant": "initial",
      "phase": "initial",
      "status": "NOT_RECORDED",
      "reason": "child_failure"
    },
    {
      "case": "d09",
      "variant": "initial",
      "phase": "initial",
      "status": "NOT_RECORDED",
      "reason": "child_failure"
    },
    {
      "case": "d13",
      "variant": "initial",
      "phase": "initial",
      "status": "NOT_RECORDED",
      "reason": "child_failure"
    },
    {
      "case": "d20",
      "variant": "initial",
      "phase": "initial",
      "status": "NOT_RECORDED",
      "reason": "child_failure"
    },
    {
      "case": "d21",
      "variant": "initial",
      "phase": "initial",
      "status": "NOT_RECORDED",
      "reason": "child_failure"
    }
  ],
  "not_run": [
    "d01/initial",
    "d05/initial",
    "d09/initial",
    "d13/initial",
    "d20/initial",
    "d21/initial"
  ],
  "metrics": {
    "planned": {
      "records": 70,
      "heldout": 66,
      "semantic": 62,
      "required_requests": 45,
      "answerable": 18,
      "pair_edges": 24
    },
    "actual_records": 0,
    "complete_membership": false,
    "heldout": {
      "status": "UNAVAILABLE_INCOMPLETE_PARTITION"
    },
    "regression": {
      "status": "UNAVAILABLE_INCOMPLETE_PARTITION"
    },
    "observed_condition_metrics": []
  },
  "gates": {},
  "reasons": [
    "child_failure"
  ],
  "sufficiency_profile_outcome": "SUFFICIENCY_PROFILE_RUNTIME_FAILED",
  "run_completeness": "INCOMPLETE",
  "final_answer_grounding": "NOT_MEASURED",
  "grounding_status": "NOT_MEASURED",
  "grounding_explanation": "Grounding was outside the authorized LIVE-1 subject.",
  "revision_2_aggregate_verdict": "NOT_APPLICABLE"
}
```
