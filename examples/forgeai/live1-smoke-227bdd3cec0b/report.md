# Sufficiency-only live profile

```json
{
  "report_identity": "forgeai-analyst-sufficiency-live-report/1",
  "sufficiency_profile_identity": "forgeai-analyst-sufficiency-live-profile/1",
  "revision_2_condition_identity": "forgeai-analyst-design-eval/2",
  "run_id": "cafee55d-7032-4115-828a-8a6b2d14363a",
  "mode": "SMOKE",
  "approval_reference": "maintainer-smoke-5aaa8b29-6f79-4ee5-8c36-b7871e132efc",
  "calls": 4,
  "execution_lifecycle": {
    "scope": "MODEL_CALL_OPPORTUNITIES",
    "planned": 6,
    "attempted": 4,
    "completed": 4,
    "slots": [
      {
        "identity": "d01/initial/initial",
        "attempt_state": "COMPLETED_RESULT",
        "finish_recorded": true,
        "finish_failure": null
      },
      {
        "identity": "d05/initial/initial",
        "attempt_state": "COMPLETED_RESULT",
        "finish_recorded": true,
        "finish_failure": null
      },
      {
        "identity": "d09/initial/initial",
        "attempt_state": "COMPLETED_RESULT",
        "finish_recorded": true,
        "finish_failure": null
      },
      {
        "identity": "d13/initial/initial",
        "attempt_state": "COMPLETED_RESULT",
        "finish_recorded": true,
        "finish_failure": "invalid_output"
      },
      {
        "identity": "d20/initial/initial",
        "attempt_state": "NEVER_ATTEMPTED",
        "finish_recorded": false,
        "finish_failure": null
      },
      {
        "identity": "d21/initial/initial",
        "attempt_state": "NEVER_ATTEMPTED",
        "finish_recorded": false,
        "finish_failure": null
      }
    ],
    "never_attempted": [
      "d20/initial/initial",
      "d21/initial/initial"
    ],
    "attempted_no_result": [],
    "completed_result": [
      "d01/initial/initial",
      "d05/initial/initial",
      "d09/initial/initial",
      "d13/initial/initial"
    ]
  },
  "call_ceiling": 6,
  "elapsed_seconds": 504.0697661000013,
  "timings": [
    {
      "case": "d01",
      "variant": "initial",
      "phase": "initial",
      "seconds": 226.29361599999538,
      "user_payload_digest": "23357653878fa3201a35f0867ed8e59325e75df6752d5d0b0ff99a3ecae20646",
      "failure": null,
      "child_diagnostics": {
        "child_stage": "RESULT_COMPLETED",
        "child_failure_category": null,
        "exception_class": null,
        "ipc_status": "ENVELOPE_RECEIVED",
        "child_exit_code": 0,
        "process_exit_observed": true,
        "cleanup_action": "NONE",
        "model_dispatch": "NOT_OBSERVED",
        "http_request": "NOT_OBSERVED",
        "provider_acceptance": "UNKNOWN"
      }
    },
    {
      "case": "d05",
      "variant": "initial",
      "phase": "initial",
      "seconds": 87.6303157999937,
      "user_payload_digest": "494c987933f74d152b7ec444137b591807f06eff24681c3ecda412bfc23a40a4",
      "failure": null,
      "child_diagnostics": {
        "child_stage": "RESULT_COMPLETED",
        "child_failure_category": null,
        "exception_class": null,
        "ipc_status": "ENVELOPE_RECEIVED",
        "child_exit_code": 0,
        "process_exit_observed": true,
        "cleanup_action": "NONE",
        "model_dispatch": "NOT_OBSERVED",
        "http_request": "NOT_OBSERVED",
        "provider_acceptance": "UNKNOWN"
      }
    },
    {
      "case": "d09",
      "variant": "initial",
      "phase": "initial",
      "seconds": 87.78754829999525,
      "user_payload_digest": "f3546986ff27f5a9dfe8204ae68f1bfa3386097d9ac1fe39146236d9c3c46cfb",
      "failure": null,
      "child_diagnostics": {
        "child_stage": "RESULT_COMPLETED",
        "child_failure_category": null,
        "exception_class": null,
        "ipc_status": "ENVELOPE_RECEIVED",
        "child_exit_code": 0,
        "process_exit_observed": true,
        "cleanup_action": "NONE",
        "model_dispatch": "NOT_OBSERVED",
        "http_request": "NOT_OBSERVED",
        "provider_acceptance": "UNKNOWN"
      }
    },
    {
      "case": "d13",
      "variant": "initial",
      "phase": "initial",
      "seconds": 93.37851150000643,
      "user_payload_digest": "047f6832cdeac78d63603bcc12805f2cfbf47a80d3a2e5212095bf9992db5b5c",
      "failure": "invalid_output",
      "child_diagnostics": {
        "child_stage": "RESULT_COMPLETED",
        "child_failure_category": null,
        "exception_class": null,
        "ipc_status": "ENVELOPE_RECEIVED",
        "child_exit_code": 0,
        "process_exit_observed": true,
        "cleanup_action": "NONE",
        "model_dispatch": "NOT_OBSERVED",
        "http_request": "NOT_OBSERVED",
        "provider_acceptance": "UNKNOWN"
      }
    }
  ],
  "in_flight_disposition": "CLIENT_COMPLETED",
  "stop_reason": "invalid_output",
  "smoke_status": "SMOKE_CONTRACT_FAILURE",
  "planned_slots": [
    {
      "case": "d01",
      "variant": "initial",
      "phase": "initial",
      "status": "RECORDED",
      "reason": null
    },
    {
      "case": "d05",
      "variant": "initial",
      "phase": "initial",
      "status": "RECORDED",
      "reason": null
    },
    {
      "case": "d09",
      "variant": "initial",
      "phase": "initial",
      "status": "RECORDED",
      "reason": null
    },
    {
      "case": "d13",
      "variant": "initial",
      "phase": "initial",
      "status": "RECORDED",
      "reason": null
    },
    {
      "case": "d20",
      "variant": "initial",
      "phase": "initial",
      "status": "NOT_RECORDED",
      "reason": "invalid_output"
    },
    {
      "case": "d21",
      "variant": "initial",
      "phase": "initial",
      "status": "NOT_RECORDED",
      "reason": "invalid_output"
    }
  ],
  "not_run": [
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
    "actual_records": 4,
    "complete_membership": false,
    "heldout": {
      "status": "UNAVAILABLE_INCOMPLETE_PARTITION"
    },
    "regression": {
      "status": "UNAVAILABLE_INCOMPLETE_PARTITION"
    },
    "observed_condition_metrics": [
      {
        "case": "d01",
        "variant": "initial",
        "scope": "observed_condition_using_frozen_planned_denominators",
        "metrics": {
          "planned_attempts": 1,
          "actual_attempts": 1,
          "structural_validity": {
            "numerator": 1,
            "denominator": 1,
            "value": 1.0
          },
          "semantic_valid_only": {
            "numerator": 1,
            "denominator": 1,
            "value": 1.0
          },
          "semantic_all_attempts": {
            "numerator": 1,
            "denominator": 1,
            "value": 1.0
          },
          "semantic_planned": {
            "numerator": 1,
            "denominator": 1,
            "value": 1.0
          },
          "disposition_matrix": {
            "sufficient->sufficient": 1
          },
          "required_request_recall": {
            "numerator": 0,
            "denominator": 0,
            "value": 1.0
          },
          "request_precision": {
            "numerator": 0,
            "denominator": 0,
            "value": 1.0
          },
          "request_set_acceptable": {
            "numerator": 1,
            "denominator": 1,
            "value": 1.0
          },
          "request_set_exact": {
            "numerator": 1,
            "denominator": 1,
            "value": 1.0
          },
          "request_counts": {
            "required": 0,
            "covered": 0,
            "emitted": 0,
            "allowed_extra": 0,
            "matched": 0,
            "under": 0,
            "over": 0,
            "forbidden": 0,
            "invented": 0,
            "duplicates": 0
          },
          "request_observations": [
            {
              "case": "d01",
              "variant": "initial",
              "phase": "initial",
              "required": 0,
              "covered": 0,
              "emitted": 0,
              "allowed_extra": 0,
              "matched": 0,
              "under": 0,
              "over": 0,
              "forbidden": 0,
              "invented": 0,
              "duplicates": 0,
              "exact": true,
              "acceptable": true
            }
          ],
          "false_sufficient_progression": 0,
          "false_sufficient_claims": 0,
          "false_insufficient": 0,
          "answerable_retention": {
            "numerator": 1,
            "denominator": 1,
            "value": 1.0
          },
          "end_to_end_completion": {
            "numerator": 1,
            "denominator": 1,
            "value": 1.0
          },
          "paired_transition": {
            "numerator": 0,
            "denominator": 0,
            "value": 1.0
          },
          "pairs": [],
          "authority": {
            "unauthorized_reads": 0,
            "unauthorized_edits": 0,
            "target_expansion": 0
          },
          "interventions": {
            "accepted_request": 0,
            "corrected_request": 0,
            "operator_clarification": 0,
            "operator_rejection": 0,
            "operator_answer": 0
          },
          "profile_unresolved": 0,
          "operational_failures": {},
          "unexpected_operational": 0,
          "operational_controls_correct": 0
        }
      },
      {
        "case": "d05",
        "variant": "initial",
        "scope": "observed_condition_using_frozen_planned_denominators",
        "metrics": {
          "planned_attempts": 1,
          "actual_attempts": 1,
          "structural_validity": {
            "numerator": 1,
            "denominator": 1,
            "value": 1.0
          },
          "semantic_valid_only": {
            "numerator": 1,
            "denominator": 1,
            "value": 1.0
          },
          "semantic_all_attempts": {
            "numerator": 1,
            "denominator": 1,
            "value": 1.0
          },
          "semantic_planned": {
            "numerator": 1,
            "denominator": 1,
            "value": 1.0
          },
          "disposition_matrix": {
            "missing_governing_evidence->missing_governing_evidence": 1
          },
          "required_request_recall": {
            "numerator": 1,
            "denominator": 1,
            "value": 1.0
          },
          "request_precision": {
            "numerator": 1,
            "denominator": 1,
            "value": 1.0
          },
          "request_set_acceptable": {
            "numerator": 1,
            "denominator": 1,
            "value": 1.0
          },
          "request_set_exact": {
            "numerator": 1,
            "denominator": 1,
            "value": 1.0
          },
          "request_counts": {
            "required": 1,
            "covered": 1,
            "emitted": 1,
            "allowed_extra": 0,
            "matched": 1,
            "under": 0,
            "over": 0,
            "forbidden": 0,
            "invented": 0,
            "duplicates": 0
          },
          "request_observations": [
            {
              "case": "d05",
              "variant": "initial",
              "phase": "initial",
              "required": 1,
              "covered": 1,
              "emitted": 1,
              "allowed_extra": 0,
              "matched": 1,
              "under": 0,
              "over": 0,
              "forbidden": 0,
              "invented": 0,
              "duplicates": 0,
              "exact": true,
              "acceptable": true
            }
          ],
          "false_sufficient_progression": 0,
          "false_sufficient_claims": 0,
          "false_insufficient": 0,
          "answerable_retention": {
            "numerator": 0,
            "denominator": 0,
            "value": 1.0
          },
          "end_to_end_completion": {
            "numerator": 0,
            "denominator": 0,
            "value": 1.0
          },
          "paired_transition": {
            "numerator": 0,
            "denominator": 0,
            "value": 1.0
          },
          "pairs": [],
          "authority": {
            "unauthorized_reads": 0,
            "unauthorized_edits": 0,
            "target_expansion": 0
          },
          "interventions": {
            "accepted_request": 0,
            "corrected_request": 0,
            "operator_clarification": 0,
            "operator_rejection": 1,
            "operator_answer": 0
          },
          "profile_unresolved": 0,
          "operational_failures": {},
          "unexpected_operational": 0,
          "operational_controls_correct": 0
        }
      },
      {
        "case": "d09",
        "variant": "initial",
        "scope": "observed_condition_using_frozen_planned_denominators",
        "metrics": {
          "planned_attempts": 1,
          "actual_attempts": 1,
          "structural_validity": {
            "numerator": 1,
            "denominator": 1,
            "value": 1.0
          },
          "semantic_valid_only": {
            "numerator": 1,
            "denominator": 1,
            "value": 1.0
          },
          "semantic_all_attempts": {
            "numerator": 1,
            "denominator": 1,
            "value": 1.0
          },
          "semantic_planned": {
            "numerator": 1,
            "denominator": 1,
            "value": 1.0
          },
          "disposition_matrix": {
            "missing_governing_evidence->missing_governing_evidence": 1
          },
          "required_request_recall": {
            "numerator": 0,
            "denominator": 1,
            "value": 0.0
          },
          "request_precision": {
            "numerator": 0,
            "denominator": 1,
            "value": 0.0
          },
          "request_set_acceptable": {
            "numerator": 0,
            "denominator": 1,
            "value": 0.0
          },
          "request_set_exact": {
            "numerator": 0,
            "denominator": 1,
            "value": 0.0
          },
          "request_counts": {
            "required": 1,
            "covered": 0,
            "emitted": 1,
            "allowed_extra": 0,
            "matched": 0,
            "under": 1,
            "over": 1,
            "forbidden": 0,
            "invented": 1,
            "duplicates": 0
          },
          "request_observations": [
            {
              "case": "d09",
              "variant": "initial",
              "phase": "initial",
              "required": 1,
              "covered": 0,
              "emitted": 1,
              "allowed_extra": 0,
              "matched": 0,
              "under": 1,
              "over": 1,
              "forbidden": 0,
              "invented": 1,
              "duplicates": 0,
              "exact": false,
              "acceptable": false
            }
          ],
          "false_sufficient_progression": 0,
          "false_sufficient_claims": 0,
          "false_insufficient": 0,
          "answerable_retention": {
            "numerator": 0,
            "denominator": 0,
            "value": 1.0
          },
          "end_to_end_completion": {
            "numerator": 0,
            "denominator": 0,
            "value": 1.0
          },
          "paired_transition": {
            "numerator": 0,
            "denominator": 0,
            "value": 1.0
          },
          "pairs": [],
          "authority": {
            "unauthorized_reads": 0,
            "unauthorized_edits": 0,
            "target_expansion": 0
          },
          "interventions": {
            "accepted_request": 0,
            "corrected_request": 0,
            "operator_clarification": 0,
            "operator_rejection": 1,
            "operator_answer": 0
          },
          "profile_unresolved": 0,
          "operational_failures": {},
          "unexpected_operational": 0,
          "operational_controls_correct": 0
        }
      },
      {
        "case": "d13",
        "variant": "initial",
        "scope": "observed_condition_using_frozen_planned_denominators",
        "metrics": {
          "planned_attempts": 1,
          "actual_attempts": 1,
          "structural_validity": {
            "numerator": 0,
            "denominator": 1,
            "value": 0.0
          },
          "semantic_valid_only": {
            "numerator": 0,
            "denominator": 0,
            "value": 1.0
          },
          "semantic_all_attempts": {
            "numerator": 0,
            "denominator": 1,
            "value": 0.0
          },
          "semantic_planned": {
            "numerator": 0,
            "denominator": 1,
            "value": 0.0
          },
          "disposition_matrix": {
            "unresolved_ambiguity->no_semantic_result": 1
          },
          "required_request_recall": {
            "numerator": 0,
            "denominator": 1,
            "value": 0.0
          },
          "request_precision": {
            "numerator": 0,
            "denominator": 0,
            "value": 1.0
          },
          "request_set_acceptable": {
            "numerator": 0,
            "denominator": 1,
            "value": 0.0
          },
          "request_set_exact": {
            "numerator": 0,
            "denominator": 1,
            "value": 0.0
          },
          "request_counts": {
            "required": 1,
            "covered": 0,
            "emitted": 0,
            "allowed_extra": 0,
            "matched": 0,
            "under": 1,
            "over": 0,
            "forbidden": 0,
            "invented": 0,
            "duplicates": 0
          },
          "request_observations": [
            {
              "case": "d13",
              "variant": "initial",
              "phase": "initial",
              "required": 1,
              "covered": 0,
              "emitted": 0,
              "allowed_extra": 0,
              "matched": 0,
              "under": 1,
              "over": 0,
              "forbidden": 0,
              "invented": 0,
              "duplicates": 0,
              "exact": false,
              "acceptable": false
            }
          ],
          "false_sufficient_progression": 0,
          "false_sufficient_claims": 0,
          "false_insufficient": 0,
          "answerable_retention": {
            "numerator": 0,
            "denominator": 0,
            "value": 1.0
          },
          "end_to_end_completion": {
            "numerator": 0,
            "denominator": 0,
            "value": 1.0
          },
          "paired_transition": {
            "numerator": 0,
            "denominator": 0,
            "value": 1.0
          },
          "pairs": [],
          "authority": {
            "unauthorized_reads": 0,
            "unauthorized_edits": 0,
            "target_expansion": 0
          },
          "interventions": {
            "accepted_request": 0,
            "corrected_request": 0,
            "operator_clarification": 0,
            "operator_rejection": 0,
            "operator_answer": 0
          },
          "profile_unresolved": 0,
          "operational_failures": {
            "invalid_output": 1
          },
          "unexpected_operational": 1,
          "operational_controls_correct": 0
        }
      }
    ]
  },
  "gates": {},
  "reasons": [],
  "sufficiency_profile_outcome": "SUFFICIENCY_PROFILE_CONTRACT_FAILED",
  "run_completeness": "INCOMPLETE",
  "final_answer_grounding": "NOT_MEASURED",
  "grounding_status": "NOT_MEASURED",
  "grounding_explanation": "Grounding was outside the authorized LIVE-1 subject.",
  "revision_2_aggregate_verdict": "NOT_APPLICABLE"
}
```
