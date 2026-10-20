"""Offline copy-boundary tests. Maintainer execution only; no Kaggle calls."""
import contextlib
import io
import json
from pathlib import Path
import shutil
import tempfile
import unittest

AREA = Path(__file__).resolve().parent


class SubmissionCopyTests(unittest.TestCase):
    def setUp(self):
        notebook = json.loads((AREA / "first_submission.ipynb").read_text(encoding="utf-8"))
        self.namespace = {}
        helper = next(c for c in notebook["cells"] if c["id"] == "copy-helper")
        exec(compile("".join(helper["source"]), "copy-helper", "exec"), self.namespace)
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.evidence = self.root / "m2-evidence"
        shutil.copytree(AREA.parent / "evidence/m2-ca6a05b4/kaggle-results",
                        self.evidence / "kaggle-results")
        self.manifest = self.evidence / "kaggle-results/manifest.json"
        self.package = self.evidence / "kaggle-results/submission.zip"
        self.output = self.root / "submission.zip"

    def copy(self, authorization=None):
        with contextlib.redirect_stdout(io.StringIO()):
            return self.namespace["prepare_submission"](
                self.manifest, self.package, self.output,
                self.namespace["AUTHORIZATION_REQUIRED"] if authorization is None else authorization)

    def test_exact_archive_copied_without_repacking(self):
        report = self.copy()
        self.assertEqual(report["state"], "M2_PACKAGE_COPIED_UNCHANGED")
        self.assertEqual(self.output.read_bytes(), (self.evidence / "kaggle-results/submission.zip").read_bytes())

    def test_renamed_bin_input_preserves_exact_bytes(self):
        renamed = self.root / "submission.zip.bin"
        self.package.rename(renamed)
        self.package = renamed
        self.copy()
        self.assertEqual(self.output.read_bytes(), renamed.read_bytes())

    def test_wrong_bin_bytes_of_correct_size_are_rejected(self):
        renamed = self.root / "submission.zip.bin"
        data = bytearray(self.package.read_bytes())
        data[0] ^= 1
        renamed.write_bytes(data)
        self.package = renamed
        with self.assertRaises(ValueError):
            self.copy()
        self.assertFalse(self.output.exists())

    def test_wrong_authorization_writes_nothing(self):
        with self.assertRaises(ValueError):
            self.copy("")
        self.assertFalse(self.output.exists())

    def test_changed_archive_refused_before_write(self):
        with (self.evidence / "kaggle-results/submission.zip").open("ab") as stream:
            stream.write(b"tampered")
        with self.assertRaises(ValueError):
            self.copy()
        self.assertFalse(self.output.exists())

    def test_changed_manifest_refused_before_write(self):
        with (self.evidence / "kaggle-results/manifest.json").open("ab") as stream:
            stream.write(b" ")
        with self.assertRaises(ValueError):
            self.copy()
        self.assertFalse(self.output.exists())

    def test_existing_output_preserved(self):
        self.output.write_bytes(b"prior evidence")
        with self.assertRaises(FileExistsError):
            self.copy()
        self.assertEqual(self.output.read_bytes(), b"prior evidence")

    def test_missing_input_writes_nothing(self):
        (self.evidence / "kaggle-results/submission.zip").unlink()
        with self.assertRaises(FileNotFoundError):
            self.copy()
        self.assertFalse(self.output.exists())


if __name__ == "__main__":
    unittest.main()
