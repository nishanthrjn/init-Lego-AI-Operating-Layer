"""External qualification must leave all repository inputs unchanged."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
import qualify_p3 as shared
import generate_self_contained as generator
from experiments.gemma4_competition import qualification_pair as pair


class JointQualificationTests(unittest.TestCase):
    def test_two_external_qualifications_preserve_repository_and_create_no_notebooks(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            repo, outside = root / "repo", root / "external"
            repo.mkdir()
            outside.mkdir()
            helper = repo / "first_submission.ipynb"
            helper.write_bytes(b"unchanged repository sentinel")
            before = hashlib.sha256(helper.read_bytes()).hexdigest()
            receipt = outside / "receipt.json"
            receipt.write_text("{}")
            results = outside / "compiler"
            results.mkdir()
            (results / "manifest.json").write_text(json.dumps({"zip_sha256": "a" * 64, "zip_size": 1}))
            (results / "submission.zip").write_bytes(b"x")
            fake_gate = SimpleNamespace(scope_gate=lambda: SimpleNamespace(scope_checks=Mock()), reconcile=Mock())
            for candidate in ("s1", "p10"):
                output = outside / (candidate + "-pins.json")
                argv = ["qualify", "--receipt", str(receipt), "--results", str(results), "--pins-output", str(output)]
                with patch.object(sys, "argv", argv), patch.object(shared, "ROOT", repo), \
                        patch.object(shared, "HERE", repo), \
                        patch("importlib.import_module", return_value=fake_gate), \
                        patch.object(generator, "build_notebook", return_value={}), \
                        patch.object(pair, "require_frozen", return_value="b" * 40):
                    shared.main(candidate, guard=lambda: {}, external_only=True)
                self.assertEqual(json.loads(output.read_bytes())["candidate"], candidate)
                self.assertEqual(hashlib.sha256(helper.read_bytes()).hexdigest(), before)
                self.assertEqual(list(repo.iterdir()), [helper])
            self.assertFalse(list(outside.glob("*.ipynb")))

    def test_external_output_cannot_target_repository(self):
        with tempfile.TemporaryDirectory() as folder:
            repo = Path(folder)
            argv = ["qualify", "--receipt", "unused", "--results", "unused",
                    "--pins-output", str(repo / "pins.json")]
            with patch.object(sys, "argv", argv), patch.object(shared, "ROOT", repo):
                with self.assertRaisesRegex(ValueError, "external"):
                    shared.main("p10", external_only=True)

    def test_external_generator_rejects_cross_candidate_pins_before_output(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            pins, output = root / "pins.json", root / "notebook.ipynb"
            pins.write_text(json.dumps({"schema": 1, "candidate": "s1", "baseline": "a" * 40, "pins": {}}))
            argv = ["generate", "--candidate", "p10", "--pins-file", str(pins),
                    "--manifest", "unused", "--package", "unused", "--output", str(output)]
            with patch.object(sys, "argv", argv), patch.object(pair, "require_frozen", return_value="a" * 40):
                with self.assertRaisesRegex(ValueError, "candidate/common baseline"):
                    generator.main()
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
