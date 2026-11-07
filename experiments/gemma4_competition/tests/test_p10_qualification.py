"""P10 frozen identity and shared qualification controls; maintainer execution only."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from experiments.gemma4_competition import portable_p10 as p10, portable_p3 as p3, portable_m2 as m2
import validate_forgeai_gemma4_p10_submission_qualification_1 as gate


class P10QualificationTests(unittest.TestCase):
    def test_operational_guard_precedes_local_validator_work(self):
        with patch.object(gate._development, "require_qualification_gate", side_effect=ValueError("pending operational evidence")), \
                patch.object(gate.GATE, "main") as shared:
            with self.assertRaisesRegex(ValueError, "pending operational evidence"):
                gate.main()
            shared.assert_not_called()

    def test_portable_receipt_rechecks_operational_authority(self):
        from types import SimpleNamespace
        revoked = SimpleNamespace(require_qualification_gate=lambda: (_ for _ in ()).throw(ValueError('consumed')))
        with patch.object(p10, '_original_verify', return_value={'candidate': 'p10'}), \
                patch.object(p10, 'load_instance', return_value=revoked):
            with self.assertRaisesRegex(ValueError, 'consumed'):
                p10.verify_local_receipt(Path('receipt.json'))
    def test_receipt_refuses_six_minute_budget(self):
        receipt = {"schema": 1, "state": "LOCAL_SCOPE_AND_STATIC_PASS", "inputs": {},
                   "candidate": "p10", "budgets": dict(p10.BUDGETS, max_time_minutes=6),
                   "experimental_zip_sha256": p10.EXPERIMENTAL_ZIP_SHA256}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "receipt.json"
            path.write_text(json.dumps(receipt))
            with patch.object(p10.ENGINE, "input_manifest", return_value={}), \
                    patch.object(p10.ENGINE, "static_candidate", return_value={}):
                with self.assertRaisesRegex(ValueError, "P10 receipt identity"):
                    p10.verify_local_receipt(path)

    def test_exact_experimental_package(self):
        files = p10.static_candidate(p10.CANDIDATE)
        self.assertEqual({k: hashlib.sha256(v).hexdigest() for k, v in files.items()}, p10.MEMBER_PINS)
        blob = p10.zip_bytes(files)
        self.assertEqual(hashlib.sha256(blob).hexdigest(), p10.EXPERIMENTAL_ZIP_SHA256)
        self.assertEqual(len(blob), 6501)
        p3files = p3.static_candidate(p3.CANDIDATE)
        self.assertEqual({k for k in files if files[k] != p3files[k]}, {"eval_config.yaml", "prompts/system.md"})

    def test_shared_engines_are_independent(self):
        self.assertEqual(m2.EXPECTED_OUTPUT_TOKENS, 16384)
        self.assertEqual(p3.CANDIDATE.name, "p3")
        self.assertEqual(p10.CANDIDATE.name, "p10")
        self.assertEqual(p10.BUDGETS["max_time_minutes"], 8)
        self.assertEqual(p3.BUDGETS["max_time_minutes"], 6)
        self.assertEqual(p10.EXPECTED_OUTPUT_TOKENS, 8192)
        self.assertEqual(p10.ENGINE.MODEL, "gemma-4-31b-it-qat-w4a16-ct")
        self.assertEqual(p3.ENGINE.MODEL, "gemma-4-31b-it-qat-w4a16-ct")
        self.assertEqual(Path(p10.ENGINE.__file__).name, "portable_p10.py")
        self.assertIs(gate.GATE.p3, p10)
        self.assertEqual(gate.GATE.CANDIDATE_NAME, "p10")

    def test_changed_candidate_member_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            for name, raw in p10.expected_files().items():
                path = target / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(raw)
            (target / "prompts/system.md").write_bytes(b"changed")
            with self.assertRaises(ValueError):
                p10.static_candidate(target)

    def test_transfer_contains_shared_dependencies_and_p10(self):
        paths = p10.transfer_paths()
        for name in ("portable_m2.py", "portable_p3.py", "portable_p10.py",
                     "kaggle_compiler/p10_compiler_only.ipynb"):
            self.assertIn("experiments/gemma4_competition/" + name, paths)
        self.assertIn("validate_forgeai_gemma4_p10_submission_qualification_1.py", paths)
        self.assertEqual(len(paths), len(set(paths)))
        # Exploratory authority and local failure evidence are receipt-bound.
        self.assertIn("experiments/gemma4_competition/results/dev-16v-comparison.json", paths)
        self.assertIn("experiments/gemma4_competition/results/submissions.json", paths)

    def test_notebook_inert_and_receipt_specific(self):
        nb = json.loads((p10.AREA / "kaggle_compiler/p10_compiler_only.ipynb").read_bytes())
        source = "\n".join("".join(c.get("source", [])) for c in nb["cells"])
        self.assertIn(p10.INSTALL_AUTHORIZATION, source)
        self.assertIn("portable_p10.py", source)
        self.assertNotIn("receipts[0]", source)
        self.assertIn('zipfile.ZipFile(out, "x"', source)
        for cell in nb["cells"]:
            if cell["cell_type"] == "code":
                self.assertIsNone(cell["execution_count"])
                self.assertEqual(cell["outputs"], [])

    def test_wrong_branch_and_hidden_index_changes_refused(self):
        scope = gate.scope_gate()
        with patch.object(scope, "git", return_value=b"main\n"):
            with self.assertRaisesRegex(ValueError, "br-ForgeAI-Gemma4"):
                scope.scope_checks()
        def fake_git(*args):
            if args[0] == "branch":
                return b"br-ForgeAI-Gemma4\n"
            if args[:3] == ("diff", "--cached", "--name-only"):
                return b"pyproject.toml\n"
            return b""
        with patch.object(scope, "git", side_effect=fake_git):
            with self.assertRaisesRegex(ValueError, "outside staged P10"):
                scope.scope_checks()


    def test_receipt_cannot_substitute_p3_identity(self):
        receipt = {"schema": 1, "state": "LOCAL_SCOPE_AND_STATIC_PASS", "inputs": {},
                   "candidate": "p3", "budgets": p10.BUDGETS,
                   "experimental_zip_sha256": p3.EXPERIMENTAL_ZIP_SHA256}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "receipt.json"
            path.write_text(json.dumps(receipt))
            with patch.object(p10.ENGINE, "input_manifest", return_value={}), \
                    patch.object(p10.ENGINE, "static_candidate", return_value={}):
                with self.assertRaisesRegex(ValueError, "P10 receipt identity"):
                    p10.verify_local_receipt(path)
                receipt.update(candidate="p10", experimental_zip_sha256=p10.EXPERIMENTAL_ZIP_SHA256)
                path.write_text(json.dumps(receipt))
                with patch.object(p10, "load_instance") as loader:
                    loader.return_value.require_qualification_gate.return_value = {}
                    self.assertEqual(p10.verify_local_receipt(path)["candidate"], "p10")

if __name__ == "__main__":
    unittest.main()
