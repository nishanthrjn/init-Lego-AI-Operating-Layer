"""Candidate identity and placeholder controls; no external execution."""
import contextlib
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest


class CandidateSelectionTests(unittest.TestCase):
    def setUp(self):
        notebook = json.loads((Path(__file__).parent / "first_submission.ipynb").read_text(encoding="utf-8"))
        self.ns = {}
        helper = next(cell for cell in notebook["cells"] if cell["id"] == "copy-helper")
        exec(compile("".join(helper["source"]), "copy-helper", "exec"), self.ns)

    def test_b2_placeholders_and_unknown_candidate_refused_before_io(self):
        self.ns["CANDIDATE_PINS"]["b2"] = {
            "manifest_sha256": None, "zip_sha256": None, "receipt_sha256": None,
            "zip_size": None, "authorization": None,
            "reconciled": False, "m2_result_understood": False,
        }
        for candidate in ("b2", "unknown", "M2"):
            with self.assertRaises(ValueError):
                self.ns["prepare_submission"](Path("absent"), Path("absent"), Path("unused"), "", candidate)

    def test_b2_cannot_use_m2_identity_pins(self):
        pins = dict(self.ns["CANDIDATE_PINS"]["m2"], reconciled=True, m2_result_understood=True)
        pins["authorization"] = "AUTHORIZE FORGEAI GEMMA4 SUBMISSION OF B2 PACKAGE " + pins["receipt_sha256"][:8]
        self.ns["CANDIDATE_PINS"]["b2"] = pins
        with self.assertRaisesRegex(ValueError, "cannot reuse M2"):
            self.ns["selected_pins"]("b2")

    def test_matching_b2_fixture_copies_exact_bytes(self):
        payload = b"independent B2 copy-boundary fixture"
        receipt_hash = "c" * 64
        manifest = {
            "state": "PORTABLE_COMPILE_AND_PACKAGE_PASS",
            "local_receipt_sha256": receipt_hash,
            "zip_sha256": hashlib.sha256(payload).hexdigest(),
            "zip_size": len(payload),
        }
        raw = json.dumps(manifest).encode()
        authorization = "AUTHORIZE FORGEAI GEMMA4 SUBMISSION OF B2 PACKAGE cccccccc"
        self.ns["CANDIDATE_PINS"]["b2"] = {
            "manifest_sha256": hashlib.sha256(raw).hexdigest(),
            "zip_sha256": manifest["zip_sha256"], "receipt_sha256": receipt_hash,
            "zip_size": len(payload), "authorization": authorization,
            "reconciled": True, "m2_result_understood": True,
        }
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "manifest.json").write_bytes(raw)
            (root / "submission.zip.bin").write_bytes(payload)
            with contextlib.redirect_stdout(io.StringIO()):
                report = self.ns["prepare_submission"](
                    root / "manifest.json", root / "submission.zip.bin",
                    root / "submission.zip", authorization, "b2",
                )
            self.assertEqual(report["state"], "B2_PACKAGE_COPIED_UNCHANGED")
            self.assertEqual((root / "submission.zip").read_bytes(), payload)

    def test_qualified_b2_pins_do_not_accept_m2_manifest(self):
        pins = {"manifest_sha256": "a" * 64, "zip_sha256": "b" * 64, "receipt_sha256": "c" * 64,
                "zip_size": 123, "authorization": "AUTHORIZE FORGEAI GEMMA4 SUBMISSION OF B2 PACKAGE cccccccc",
                "reconciled": True, "m2_result_understood": True}
        self.ns["CANDIDATE_PINS"]["b2"] = pins
        evidence = Path(__file__).parents[1] / "evidence/m2-ca6a05b4/kaggle-results"
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "submission.zip"
            with self.assertRaises(ValueError):
                self.ns["prepare_submission"](evidence / "manifest.json", evidence / "submission.zip",
                                              output, pins["authorization"], "b2")
            self.assertFalse(output.exists())

    def test_b2_requires_understood_m2_result_and_reconciliation(self):
        pins = {"manifest_sha256": "a" * 64, "zip_sha256": "b" * 64, "receipt_sha256": "c" * 64,
                "zip_size": 123, "authorization": "AUTHORIZE FORGEAI GEMMA4 SUBMISSION OF B2 PACKAGE cccccccc",
                "reconciled": True, "m2_result_understood": True}
        for key in ("reconciled", "m2_result_understood"):
            self.ns["CANDIDATE_PINS"]["b2"] = dict(pins, **{key: False})
            with self.assertRaises(ValueError):
                self.ns["selected_pins"]("b2")


if __name__ == "__main__":
    unittest.main()
