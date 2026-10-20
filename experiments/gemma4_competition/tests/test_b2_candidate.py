"""B2 boundaries, executed only by the maintainer."""
import contextlib
import io
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from experiments.gemma4_competition import portable_b2 as b2
from experiments.gemma4_competition import portable_m2 as m2
import validate_forgeai_gemma4_b2_candidate_1 as gate
import validate_forgeai_gemma4_m2_minimal_baseline_1 as m2_gate


class B2CandidateTests(unittest.TestCase):
    def test_exact_budget_only_difference(self):
        baseline = m2.static_candidate(m2.CANDIDATE)
        candidate = b2.static_candidate(b2.CANDIDATE)
        self.assertEqual([n for n in baseline if baseline[n] != candidate[n]], ["eval_config.yaml"])
        self.assertEqual(candidate["eval_config.yaml"], (
            b"evaluation:\n  timeout_seconds: 90\n  max_tool_calls: 40\n"
            b"  max_time_minutes: 4\n  max_turns: 100\n"))

    def test_changed_budget_or_extra_key_refused(self):
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "candidate"
            shutil.copytree(b2.CANDIDATE, target)
            path = target / "eval_config.yaml"
            for data in (b2.EVALUATION.replace("90", "91"), b2.EVALUATION + "  other: 1\n"):
                path.write_text(data, encoding="utf-8", newline="\n")
                with self.assertRaises(ValueError):
                    b2.static_candidate(target)

    def test_non_budget_change_refused(self):
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "candidate"
            shutil.copytree(b2.CANDIDATE, target)
            with (target / "prompts/system.md").open("ab") as stream:
                stream.write(b"\nchanged")
            with self.assertRaises(ValueError):
                b2.static_candidate(target)

    def test_m2_receipt_bound_bytes_and_default_behavior_unchanged(self):
        manifest = json.loads((b2.AREA / "evidence/m2-ca6a05b4/kaggle-results/manifest.json").read_text())
        self.assertEqual(m2.input_manifest(), manifest["inputs"])
        self.assertEqual(m2.CANDIDATE, b2.AREA / "baseline")
        self.assertEqual(m2.static_candidate(m2.CANDIDATE)["eval_config.yaml"], m2.EVALUATION.encode())
        self.assertEqual(m2_gate.shared, m2)

    def test_b2_child_dispatch_and_receipt_inputs(self):
        self.assertEqual(Path(b2.ENGINE.__file__), b2.AREA / "portable_b2.py")
        self.assertIn("experiments/gemma4_competition/portable_b2.py", b2.transfer_paths())
        self.assertIn("experiments/gemma4_competition/candidates/b2/eval_config.yaml", b2.transfer_paths())
        self.assertNotEqual(b2.input_manifest(), m2.input_manifest())

    def test_cross_candidate_receipts_and_results_refused(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            m2_receipt = root / "m2.json"
            b2_receipt = root / "b2.json"
            m2_receipt.write_text(json.dumps({"schema": 1, "state": "LOCAL_SCOPE_AND_STATIC_PASS",
                                             "inputs": m2.input_manifest()}))
            b2_receipt.write_text(json.dumps({"schema": 1, "state": "LOCAL_SCOPE_AND_STATIC_PASS",
                                             "candidate": "b2", "budgets": b2.BUDGETS,
                                             "inputs": b2.input_manifest()}))
            m2.verify_local_receipt(m2_receipt)
            b2.verify_local_receipt(b2_receipt)
            with self.assertRaises(ValueError):
                gate.reconcile(m2_receipt, root)
            with self.assertRaises(ValueError):
                m2_gate.reconcile(b2_receipt, root)
            # Valid B2 receipt with real M2 results must also fail receipt binding.
            with self.assertRaises(ValueError):
                gate.reconcile(b2_receipt, b2.AREA / "evidence/m2-ca6a05b4/kaggle-results")
            # The reciprocal result mismatch reaches the same shared check.
            install = json.loads((b2.AREA / "evidence/m2-ca6a05b4/kaggle-results/install-evidence.json").read_text())
            install["local_receipt_sha256"] = b2.sha(b2_receipt.read_bytes())
            (root / "install-evidence.json").write_text(json.dumps(install))
            with self.assertRaises(ValueError):
                m2_gate.reconcile(m2_receipt, root)

    def test_shared_compiler_and_packaging_functions_are_delegated(self):
        # The wrapper binds configuration; shared implementation source remains
        # pinned by M2's manifest and no compiler clone exists.
        self.assertEqual(b2.official_controls.__code__.co_filename, m2.official_controls.__code__.co_filename)
        self.assertEqual(b2.run_portable.__code__.co_filename, m2.run_portable.__code__.co_filename)
        self.assertEqual(b2.scoped_install.__code__.co_filename, m2.scoped_install.__code__.co_filename)
        with patch.object(b2.ENGINE, "verify_local_receipt", side_effect=ValueError("refused")):
            with contextlib.redirect_stdout(io.StringIO()), self.assertRaises(ValueError):
                b2.run_portable(Path("wrong-receipt"), Path("unused-output"))


if __name__ == "__main__":
    unittest.main()
