"""P10 eligibility tests; fixtures do not mutate real evidence."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import qualify_p10 as q
import generate_self_contained as generator


def fixtures():
    return ({
        "p10_timing_amendment": {"id": "P10-FRIEND-ATTEMPT2-TIMING-1",
            "status": "AUTHORIZED_RUN_IDENTITY_ONLY", "attempt": 2,
            "effective_method": "REPO_ANALYSIS_116_TASK_BOOTSTRAP_V1",
            "attempt1_recording": "DEFERRED_UNTIL_AFTER_BOTH_SUBMISSIONS"},
        "p10_attempt2": {"candidate": "p10", "subset": "dev-16v", "attempt": 2,
            "state": "COMPLETED", "complete": True, "tasks": 16, "verifiable": 16,
            "controls_status": "PINNED_CONTROLS_APPLIED", "time_fit_gate": "PASS",
            "bootstrap_method": "REPO_ANALYSIS_116_TASK_BOOTSTRAP_V1",
            "zip_sha256": q.ZIP_SHA256, "manifest_sha256": q.MANIFEST_SHA256,
            "zip_size": 6501, "model_variant": q.MODEL,
            "tool_argument_rejection_definition": "mandatory input parameters are not present",
            "harness_errors": 0, "all_tool_attempted": 100, "all_tool_rejected": 5,
            "bootstrap_upper95_hours": 11.0, "resolved": 0}},
        {"p10_local_selection": {"candidate": "p10", "purpose": "EXPLORATORY_LB_MEASUREMENT",
            "status": "NOT_SUBMITTED", "gate": "PASSED", "eligibility_attempt": 2,
            "adopt_public_score_at_least": 0.17, "submissions_used": 0,
            "maximum_submissions_after_gate": 1, "public_score": None}, "runs": []})


class P10SubmissionTests(unittest.TestCase):
    def check(self, doc, registry):
        with tempfile.TemporaryDirectory() as folder:
            evidence, selection = Path(folder) / "evidence.json", Path(folder) / "selection.json"
            evidence.write_text(json.dumps(doc))
            selection.write_text(json.dumps(registry))
            return q.require_qualification_gate(evidence, selection)

    def test_thresholds_inclusive_and_accuracy_not_a_gate(self):
        result = self.check(*fixtures())
        self.assertEqual(result["development_gate"], "PASSED")
        self.assertEqual(result["qualification_purpose"], "EXPLORATORY_LB_MEASUREMENT")

    def test_metrics_and_repository_method_cannot_be_replaced_by_label(self):
        for key, value in (("bootstrap_upper95_hours", 11.01), ("bootstrap_upper95_hours", None),
                           ("bootstrap_upper95_hours", float("nan")), ("bootstrap_upper95_hours", True),
                           ("bootstrap_method", "MAINTAINER_REPORTED"), ("harness_errors", False),
                           ("harness_errors", 1), ("all_tool_rejected", 6), ("all_tool_attempted", 0),
                           ("all_tool_rejected", None), ("complete", False), ("attempt", 1),
                           ("model_variant", "gemma-4-e4b-it-qat-w4a16-ct"), ("zip_sha256", "0" * 64)):
            doc, registry = fixtures()
            doc["p10_attempt2"][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.check(doc, registry)

    def test_consumed_or_scored_measurement_refused(self):
        for key, value in (("submissions_used", 1), ("submissions_used", False),
                           ("maximum_submissions_after_gate", 2), ("public_score", 0.18)):
            doc, registry = fixtures()
            registry["p10_local_selection"][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.check(doc, registry)
        doc, registry = fixtures()
        registry["runs"] = [{"candidate": "p10", "status": "SCORING"}]
        with self.assertRaises(ValueError):
            self.check(doc, registry)

    def test_identity_amendment_required(self):
        doc, registry = fixtures()
        doc["p10_timing_amendment"]["status"] = "PENDING"
        with self.assertRaises(ValueError):
            self.check(doc, registry)

    def test_generator_checks_evidence_and_evaluated_package(self):
        expected = self.check(*fixtures())
        pins = dict(expected, reconciled=True, m2_result_understood=True,
                    zip_size=6501, zip_sha256=q.ZIP_SHA256)
        with patch.object(q, "require_qualification_gate", return_value=expected):
            with self.assertRaisesRegex(ValueError, "operational evidence"):
                generator.build_notebook("p10", dict(pins, selection_evidence_sha256="0" * 64), b"", b"")
            with self.assertRaisesRegex(ValueError, "evaluated experimental"):
                generator.build_notebook("p10", dict(pins, zip_sha256="0" * 64), b"", b"")


if __name__ == "__main__":
    unittest.main()
