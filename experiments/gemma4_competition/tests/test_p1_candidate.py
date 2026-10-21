"""P1 requirements and failure boundaries; offline maintainer execution only."""
import contextlib
import io
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from experiments.gemma4_competition import portable_m2 as m2
from experiments.gemma4_competition import portable_p1 as p1
import validate_forgeai_gemma4_p1_procedure_prompt_1 as gate


class P1Tests(unittest.TestCase):
    def test_only_prompt_and_budgets_differ(self):
        data = p1.static_candidate(p1.CANDIDATE)
        prior = {n: (p1.AREA / "candidates/b2" / n).read_bytes() for n in p1.MEMBERS}
        self.assertEqual({n for n in data if data[n] != prior[n]}, {"prompts/system.md", "eval_config.yaml"})
        self.assertEqual(data["eval_config.yaml"], b"evaluation:\n  timeout_seconds: 180\n  max_tool_calls: 28\n  max_time_minutes: 6\n  max_turns: 80\n")
        self.assertEqual(data["agent.yaml"], (m2.CANDIDATE / "agent.yaml").read_bytes())
        self.assertEqual(data["configs/sampling.yaml"], (m2.CANDIDATE / "configs/sampling.yaml").read_bytes())

    def test_prompt_budget_tool_and_sampling_mutations_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "candidate"
            shutil.copytree(p1.CANDIDATE, target)
            for name in p1.MEMBERS:
                path = target / name
                original = path.read_bytes()
                for bad in (original + b"\nextra\n", original.replace(b"\n", b"\r\n")):
                    with self.subTest(name=name):
                        path.write_bytes(bad)
                        with self.assertRaises(ValueError):
                            p1.static_candidate(target)
                path.write_bytes(original)

    def test_original_m2_module_not_rebound(self):
        self.assertEqual(m2.CANDIDATE, p1.AREA / "baseline")
        self.assertEqual(m2.static_candidate(m2.CANDIDATE)["eval_config.yaml"], m2.EVALUATION.encode())
        self.assertNotEqual(m2.EVALUATION, p1.EVALUATION)

    def test_cross_candidate_receipts_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            receipt = Path(temporary) / "local-receipt.json"
            record = {"schema": 1, "state": "LOCAL_SCOPE_AND_STATIC_PASS", "candidate": "p1",
                      "budgets": p1.BUDGETS, "prompt_sha256": p1.PROMPT_SHA256, "inputs": p1.input_manifest()}
            receipt.write_text(json.dumps(record), encoding="utf-8")
            p1.verify_local_receipt(receipt)
            with self.assertRaises(ValueError):
                m2.verify_local_receipt(receipt)
            for bad in ({"candidate": "b2"}, {"budgets": {}}, {"prompt_sha256": "0" * 64}):
                receipt.write_text(json.dumps({**record, **bad}), encoding="utf-8")
                with self.assertRaises(ValueError):
                    p1.verify_local_receipt(receipt)

    def test_shared_algorithms_and_p1_worker_dispatch(self):
        for name in ("official_controls", "scoped_install", "inspect_zip", "zip_bytes", "worker"):
            self.assertEqual(getattr(p1, name).__code__.co_filename, getattr(m2, name).__code__.co_filename)
        self.assertEqual(Path(p1.ENGINE.__file__), p1.AREA / "portable_p1.py")
        self.assertIn("experiments/gemma4_competition/kaggle_compiler/p1_compiler_only.ipynb", p1.transfer_paths())
        self.assertNotIn("experiments/gemma4_competition/submission_only/first_submission.ipynb", p1.transfer_paths())

    def test_zip_is_deterministic_and_exact(self):
        data = p1.static_candidate(p1.CANDIDATE)
        blob = p1.zip_bytes(data)
        self.assertEqual(blob, p1.zip_bytes(data))
        p1.inspect_zip(blob, data)
        changed = dict(data, **{"eval_config.yaml": b"wrong"})
        with self.assertRaises(ValueError):
            p1.inspect_zip(blob, changed)

    def test_wrong_receipt_stops_before_compiler_worker(self):
        with patch.object(p1.ENGINE, "verify_local_receipt", side_effect=ValueError("wrong candidate")), \
             patch.object(p1.ENGINE.subprocess, "run") as run:
            with self.assertRaises(ValueError):
                p1.run_portable(Path("receipt"), Path("output"))
            run.assert_not_called()

    def test_phase_failure_names_contract(self):
        stderr = io.StringIO()
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(stderr):
            with self.assertRaises(gate.PhaseFailure):
                gate.phase("receipt", lambda: p1.require(False, "wrong candidate"))
        self.assertIn("FAIL: receipt: wrong candidate", stderr.getvalue())

    def submission_helper(self):
        notebook = json.loads((p1.AREA / "submission_only/first_submission.ipynb").read_text(encoding="utf-8"))
        cell = next(c for c in notebook["cells"] if c.get("id") == "copy-helper")
        namespace = {}
        exec(compile("".join(cell["source"]), "copy-helper", "exec"), namespace)
        return namespace

    def test_p1_placeholder_and_cross_candidate_pins_refused(self):
        ns = self.submission_helper()
        ns["CANDIDATE_PINS"]["p1"] = {"manifest_sha256": None}
        with self.assertRaises(ValueError):
            ns["selected_pins"]("p1")
        for source in ("m2", "b2"):
            pins = dict(ns["CANDIDATE_PINS"][source], reconciled=True, m2_result_understood=True)
            pins["authorization"] = "AUTHORIZE FORGEAI GEMMA4 SUBMISSION OF P1 PACKAGE " + pins["receipt_sha256"][:8]
            ns["CANDIDATE_PINS"]["p1"] = pins
            with self.assertRaises(ValueError):
                ns["selected_pins"]("p1")

    def test_p1_independent_pins_require_own_authorization(self):
        ns = self.submission_helper()
        pins = {"manifest_sha256": "a" * 64, "zip_sha256": "b" * 64,
                "receipt_sha256": "c" * 64, "zip_size": 100,
                "reconciled": True, "m2_result_understood": True,
                "authorization": "AUTHORIZE FORGEAI GEMMA4 SUBMISSION OF P1 PACKAGE cccccccc"}
        ns["CANDIDATE_PINS"]["p1"] = pins
        self.assertEqual(ns["selected_pins"]("p1"), pins)
        with self.assertRaisesRegex(ValueError, "authorization"):
            ns["prepare_submission"](Path("absent"), Path("absent"), Path("unused"), "wrong", "p1")


if __name__ == "__main__":
    unittest.main()
