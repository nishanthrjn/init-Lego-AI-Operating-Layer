"""Offline fixtures only; never install, compile or contact Kaggle."""
import ast
import base64
import contextlib
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest

import generate_self_contained as generator
from embedded_payload import materialize


class SelfContainedTests(unittest.TestCase):
    def setUp(self):
        self.payload = b"independent package boundary fixture"
        self.manifest = {"state": "PORTABLE_COMPILE_AND_PACKAGE_PASS", "local_receipt_sha256": "a" * 64,
                         "zip_sha256": hashlib.sha256(self.payload).hexdigest(), "zip_size": len(self.payload)}
        self.raw = json.dumps(self.manifest).encode()
        self.pins = {"manifest_sha256": hashlib.sha256(self.raw).hexdigest(),
                     "receipt_sha256": "a" * 64, "zip_sha256": self.manifest["zip_sha256"],
                     "zip_size": len(self.payload), "authorization": "fixture approval",
                     "reconciled": True, "m2_result_understood": True}

    def emit(self, payload, output, authorization="fixture approval"):
        with contextlib.redirect_stdout(io.StringIO()):
            return materialize(base64.b64encode(payload).decode(), self.pins, authorization, output)

    def test_generated_notebook_contains_exact_bytes_and_no_inputs(self):
        nb = generator.build_notebook("fixture", self.pins, self.raw, self.payload)
        source = "".join(nb["cells"][-1]["source"])
        assignments = {n.targets[0].id: ast.literal_eval(n.value) for n in ast.parse(source).body
                       if isinstance(n, ast.Assign) and not isinstance(n.value, ast.Call)}
        self.assertEqual(base64.b64decode(assignments["PAYLOAD_BASE64"]), self.payload)
        self.assertEqual(assignments["PINS"], self.pins)
        self.assertEqual(assignments["AUTHORIZATION"], "")
        self.assertNotIn("/kaggle/input", json.dumps(nb))
        self.assertTrue(all(not c.get("outputs") and c.get("execution_count") is None for c in nb["cells"]))
        # Exercise the exact helper embedded into the notebook with temporary output.
        ns = {}
        exec("".join(nb["cells"][1]["source"]), ns)
        with tempfile.TemporaryDirectory() as directory, contextlib.redirect_stdout(io.StringIO()):
            output = Path(directory) / "submission.zip"
            ns["materialize"](assignments["PAYLOAD_BASE64"], self.pins, "fixture approval", output)
            self.assertEqual(output.read_bytes(), self.payload)

    def test_unreconciled_refused(self):
        with self.assertRaisesRegex(ValueError, "Reconciled"):
            generator.build_notebook("fixture", dict(self.pins, reconciled=False), self.raw, self.payload)

    def test_manifest_and_package_tampering_refused(self):
        for raw, payload in ((self.raw + b" ", self.payload), (self.raw, b"wrong")):
            with self.assertRaises(ValueError):
                generator.build_notebook("fixture", self.pins, raw, payload)

    def test_create_then_identical_rerun(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "submission.zip"
            self.assertEqual(self.emit(self.payload, output)["state"], "CREATED")
            stamp = output.stat().st_mtime_ns
            self.assertEqual(self.emit(self.payload, output)["state"], "ALREADY_PRESENT_IDENTICAL")
            self.assertEqual(output.stat().st_mtime_ns, stamp)
            self.assertEqual(list(Path(directory).iterdir()), [output])

    def test_replace_reports_old_hash(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "submission.zip"
            output.write_bytes(b"previous")
            report = self.emit(self.payload, output)
            self.assertEqual(report["state"], "REPLACED_DIFFERENT")
            self.assertEqual(report["replaced_sha256"], hashlib.sha256(b"previous").hexdigest())
            self.assertEqual(output.read_bytes(), self.payload)
            self.assertEqual(list(Path(directory).iterdir()), [output])

    def test_bad_payload_or_authorization_never_changes_output(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "submission.zip"
            output.write_bytes(b"preserve")
            for payload, authorization in ((b"tampered", "fixture approval"), (self.payload, "")):
                with self.assertRaises(ValueError):
                    self.emit(payload, output, authorization)
                self.assertEqual(output.read_bytes(), b"preserve")

    def test_existing_candidate_pin_loading(self):
        self.assertEqual(generator.load_pins("p1")["zip_size"], 4736)
        for candidate in ("m2", "b2", "p1"):
            self.assertTrue(generator.load_pins(candidate)["reconciled"])
        with self.assertRaises(KeyError):
            generator.load_pins("unknown")


if __name__ == "__main__":
    unittest.main()
