"""P7A frozen identity and shared qualification controls; maintainer execution only."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from experiments.gemma4_competition import portable_p7a as p7a, portable_p3 as p3, portable_m2 as m2
import validate_forgeai_gemma4_p7a_submission_qualification_1 as gate


class P7AQualificationTests(unittest.TestCase):
    def test_confirmation_guard_precedes_local_validator_work(self):
        with patch.object(gate._development, "require_confirmation_gate", side_effect=ValueError("pending confirmation")), \
                patch.object(gate.GATE, "main") as shared:
            with self.assertRaisesRegex(ValueError, "pending confirmation"):
                gate.main()
            shared.assert_not_called()

    def test_exact_experimental_package(self):
        files = p7a.static_candidate(p7a.CANDIDATE)
        self.assertEqual({k: hashlib.sha256(v).hexdigest() for k, v in files.items()}, p7a.MEMBER_PINS)
        blob = p7a.zip_bytes(files)
        self.assertEqual(hashlib.sha256(blob).hexdigest(), p7a.EXPERIMENTAL_ZIP_SHA256)
        self.assertEqual(len(blob), 7359)
        p3files = p3.static_candidate(p3.CANDIDATE)
        self.assertEqual({k for k in files if files[k] != p3files[k]}, {"prompts/system.md"})

    def test_shared_engines_are_independent(self):
        self.assertEqual(m2.EXPECTED_OUTPUT_TOKENS, 16384)
        self.assertEqual(p3.CANDIDATE.name, "p3")
        self.assertEqual(p7a.CANDIDATE.name, "p7a")
        self.assertEqual(p7a.EXPECTED_OUTPUT_TOKENS, 8192)
        self.assertEqual(Path(p7a.ENGINE.__file__).name, "portable_p7a.py")
        self.assertIs(gate.GATE.p3, p7a)
        self.assertEqual(gate.GATE.CANDIDATE_NAME, "p7a")

    def test_changed_candidate_member_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            for name, raw in p7a.expected_files().items():
                path = target / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(raw)
            (target / "prompts/system.md").write_bytes(b"changed")
            with self.assertRaises(ValueError):
                p7a.static_candidate(target)

    def test_transfer_contains_shared_dependencies_and_p7a(self):
        paths = p7a.transfer_paths()
        for name in ("portable_m2.py", "portable_p3.py", "portable_p7a.py",
                     "kaggle_compiler/p7a_compiler_only.ipynb"):
            self.assertIn("experiments/gemma4_competition/" + name, paths)
        self.assertIn("validate_forgeai_gemma4_p7a_submission_qualification_1.py", paths)
        self.assertEqual(len(paths), len(set(paths)))
        # Development evidence can arrive after CPU qualification without changing candidate receipts.
        self.assertNotIn("experiments/gemma4_competition/results/dev-16v-comparison.json", paths)

    def test_notebook_inert_and_receipt_specific(self):
        nb = json.loads((p7a.AREA / "kaggle_compiler/p7a_compiler_only.ipynb").read_bytes())
        source = "\n".join("".join(c.get("source", [])) for c in nb["cells"])
        self.assertIn(p7a.INSTALL_AUTHORIZATION, source)
        self.assertIn("portable_p7a.py", source)
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
            with self.assertRaisesRegex(ValueError, "outside staged P7A"):
                scope.scope_checks()


    def test_receipt_cannot_substitute_p3_identity(self):
        receipt = {"schema": 1, "state": "LOCAL_SCOPE_AND_STATIC_PASS", "inputs": {},
                   "candidate": "p3", "budgets": p7a.BUDGETS,
                   "experimental_zip_sha256": p3.EXPERIMENTAL_ZIP_SHA256}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "receipt.json"
            path.write_text(json.dumps(receipt))
            with patch.object(p7a.ENGINE, "input_manifest", return_value={}), \
                    patch.object(p7a.ENGINE, "static_candidate", return_value={}):
                with self.assertRaisesRegex(ValueError, "P7A receipt identity"):
                    p7a.verify_local_receipt(path)
                receipt.update(candidate="p7a", experimental_zip_sha256=p7a.EXPERIMENTAL_ZIP_SHA256)
                path.write_text(json.dumps(receipt))
                self.assertEqual(p7a.verify_local_receipt(path)["candidate"], "p7a")

if __name__ == "__main__":
    unittest.main()
