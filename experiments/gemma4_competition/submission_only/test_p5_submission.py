"""Independent P5 eligibility fixtures; no compiler, provider or model execution."""
import ast
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch, MagicMock
import qualify_p3
import qualify_p5
import generate_self_contained as generator


def evidence():
    doc = {"p5_adoption_decision": {"status": "PASSED"},
           "tool_argument_rejection_evidence": {"patch_production_baseline": {
               "tasks_per_run": 16, "p3_attempt1": 11, "p3_attempt2": 7}}}
    for attempt, solved in ((1, 9), (2, 5)):
        doc[f"p5_attempt{attempt}"] = {"candidate": "p5", "subset": "dev-16v", "attempt": attempt,
            "state": "COMPLETED", "verifiable": 16, "resolved": solved,
            "retained_path": f"external/run{attempt}", "all_tool_attempted": 100,
            "all_tool_rejected": 5, "nonempty_patch_tasks": 9,
            "bootstrap_upper95_hours_approx": 11, "run_command_heredoc_edits_observed": 20}
    return doc


class P5SubmissionTests(unittest.TestCase):
    def check(self, doc):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "evidence.json"
            raw = json.dumps(doc).encode()
            path.write_bytes(raw)
            pins = qualify_p5.require_two_run_gate(path)
            self.assertEqual(pins["development_evidence_sha256"], hashlib.sha256(raw).hexdigest())
            return pins

    def test_thresholds_inclusive_and_mean_over_both_runs(self):
        self.assertEqual(self.check(evidence())["development_gate"], "PASSED")

    def test_status_label_cannot_override_bad_or_missing_metrics(self):
        for key, value in (("resolved", 4), ("resolved", True), ("resolved", None),
                           ("all_tool_rejected", 6), ("all_tool_attempted", 0),
                           ("nonempty_patch_tasks", 8), ("bootstrap_upper95_hours_approx", 11.01),
                           ("bootstrap_upper95_hours_approx", float("nan")),
                           ("state", "RUNNING"), ("verifiable", 15), ("candidate", "p3"),
                           ("run_command_heredoc_edits_observed", 0), ("retained_path", "external/run1")):
            with self.subTest(key=key, value=value):
                doc = evidence()
                doc["p5_attempt2"][key] = value
                with self.assertRaises(ValueError):
                    self.check(doc)

    def test_either_run_failing_rejections_or_patch_gate_blocks(self):
        for attempt in (1, 2):
            for key, value in (("all_tool_rejected", 6), ("nonempty_patch_tasks", 8)):
                doc = evidence()
                doc[f"p5_attempt{attempt}"][key] = value
                with self.assertRaises(ValueError):
                    self.check(doc)

    def test_zero_edit_write_attempts_can_pass_but_not_without_patches(self):
        doc = evidence()
        doc["p5_attempt2"].update(edit_file_calls=0, write_file_calls=0, all_tool_rejected=0)
        self.check(doc)
        doc["p5_attempt2"]["nonempty_patch_tasks"] = 0
        with self.assertRaises(ValueError):
            self.check(doc)

    def test_pending_missing_attempt_and_missing_baseline_block(self):
        for field in ("p5_adoption_decision", "p5_attempt2", "tool_argument_rejection_evidence"):
            doc = evidence()
            del doc[field]
            with self.assertRaises(ValueError):
                self.check(doc)
        doc = evidence()
        doc["p5_adoption_decision"]["status"] = "PENDING_ATTEMPT2"
        with self.assertRaises(ValueError):
            self.check(doc)

    def test_p5_pin_materialization_preserves_other_candidates(self):
        source = 'CANDIDATE_PINS = {"p3": {"reconciled": True}, "p5": {"reconciled": False}}\n'
        updated = qualify_p3.replace_entry(source, {"reconciled": True}, "p5")
        actual = ast.literal_eval(ast.parse(updated).body[0].value)
        self.assertEqual(actual["p3"], {"reconciled": True})
        self.assertTrue(actual["p5"]["reconciled"])

    def test_blocked_guard_precedes_reconciliation_and_writes(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "external.ipynb"
            argv = ["qualify_p5.py", "--receipt", "missing", "--results", "missing", "--notebook", str(output)]
            with patch.object(sys, "argv", argv), patch.object(qualify_p5, "require_two_run_gate", side_effect=ValueError("blocked")):
                with self.assertRaisesRegex(ValueError, "blocked"):
                    qualify_p5.main()
            self.assertFalse(output.exists())

    def test_shared_generator_rejects_stale_or_missing_development_pins(self):
        pins = {"reconciled": True, "m2_result_understood": True}
        with patch.object(qualify_p5, "require_two_run_gate", return_value={"development_gate": "PASSED", "development_evidence_sha256": "a" * 64}):
            with self.assertRaisesRegex(ValueError, "development evidence"):
                generator.build_notebook("p5", pins, b"{}", b"payload")

    def test_pending_pins_cannot_generate(self):
        with self.assertRaises(ValueError):
            generator.build_notebook("p5", {"reconciled": False}, b"{}", b"unqualified")


    def test_successful_preparation_reconciles_then_updates_only_p5(self):
        import contextlib
        import io
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            receipt = root / "receipt.json"
            receipt.write_bytes(b"fixture receipt")
            results = root / "results"
            results.mkdir()
            payload = b"fixture reconciled payload"
            manifest = {"state": "PORTABLE_COMPILE_AND_PACKAGE_PASS",
                        "local_receipt_sha256": hashlib.sha256(receipt.read_bytes()).hexdigest(),
                        "zip_sha256": hashlib.sha256(payload).hexdigest(), "zip_size": len(payload)}
            (results / "manifest.json").write_text(json.dumps(manifest))
            (results / "submission.zip").write_bytes(payload)
            source = 'CANDIDATE_PINS = {"p3": {"hash": "preserved"}, "p5": {"reconciled": False}}\n'
            target = root / "first_submission.ipynb"
            target.write_text(json.dumps({"cells": [{"id": "copy-helper", "source": [source]}]}))
            output = root / "selfcontained.ipynb"
            gate_pins = {"development_gate": "PASSED", "development_evidence_sha256": "a" * 64}
            gate = MagicMock()
            argv = ["qualify_p5.py", "--receipt", str(receipt), "--results", str(results), "--notebook", str(output)]
            with patch.object(sys, "argv", argv), patch.object(qualify_p3, "HERE", root), \
                    patch.object(qualify_p5, "require_two_run_gate", return_value=gate_pins), \
                    patch("importlib.import_module", return_value=gate), contextlib.redirect_stdout(io.StringIO()):
                qualify_p5.main()
            gate.reconcile.assert_called_once_with(receipt, results)
            updated = json.loads(target.read_bytes())
            pins = ast.literal_eval(ast.parse("".join(updated["cells"][0]["source"])).body[0].value)
            self.assertEqual(pins["p3"], {"hash": "preserved"})
            self.assertTrue(pins["p5"]["reconciled"])
            self.assertEqual(pins["p5"]["development_evidence_sha256"], "a" * 64)
            generated = json.loads(output.read_bytes())
            self.assertTrue(all(not c.get("outputs") for c in generated["cells"]))
            self.assertIn('AUTHORIZATION = ""', "".join(generated["cells"][-1]["source"]))

if __name__ == "__main__":
    unittest.main()
