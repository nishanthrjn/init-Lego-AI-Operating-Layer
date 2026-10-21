"""Offline diagnostic/scope controls. Run only by the maintainer."""
import contextlib
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import validate_forgeai_gemma4_validator_diagnostics_1 as gate


class DiagnosticTests(unittest.TestCase):
    def test_both_candidates_print_phase_exact_valueerror_and_nonzero(self):
        for candidate in ("m2", "b2"):
            with self.subTest(candidate=candidate), tempfile.TemporaryDirectory() as temporary:
                stderr, stdout = io.StringIO(), io.StringIO()
                with patch.object(gate, "scope_checks"), patch.object(
                    gate, "preserved_bundle", return_value=Path(temporary)
                ), patch.object(gate, "historical_reconcile", side_effect=ValueError("receipt mismatch")), \
                    contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                    result = gate.cli(["--candidate", candidate, "--receipt", "receipt.json",
                                       "--reconcile", "results"])
                self.assertEqual(result, 1)
                self.assertIn("[PHASE] historical " + candidate.upper(), stdout.getvalue())
                self.assertIn("receipt mismatch; later phases NOT RUN", stderr.getvalue())
                self.assertNotIn("HISTORICAL_PACKAGE_RECONCILED", stdout.getvalue())

    def test_non_contract_error_does_not_print_payload(self):
        def fail():
            raise RuntimeError("SECRET_CANARY")
        output = io.StringIO()
        with contextlib.redirect_stderr(output), self.assertRaises(gate.ReportedFailure):
            gate.phase("reconciliation", fail)
        self.assertIn("RuntimeError", output.getvalue())
        self.assertNotIn("SECRET_CANARY", output.getvalue())

    def scope_fixture(self, root, *, dirty=(), changed=(), original=None):
        note = root / gate.README
        note.parent.mkdir(parents=True)
        note.write_bytes(b"Historical B2 note\n\nDiagnostic appendix\n")
        def fake_git(*args):
            if args == ("rev-parse", gate.SLICE + "^"):
                return gate.PARENT.encode() + b"\n"
            if args == ("merge-base", gate.SLICE, "HEAD"):
                return gate.SLICE.encode() + b"\n"
            if args == ("diff", "--name-only", gate.PARENT, gate.SLICE):
                return "\n".join(sorted(gate.SLICE_FILES if original is None else original)).encode()
            if args[:4] == ("diff", "--name-only", gate.SLICE, "HEAD"):
                return "\n".join(changed).encode()
            if args == ("diff", "--name-only", "HEAD"):
                return b""
            if args == ("ls-files", "--others", "--exclude-standard"):
                return "\n".join(dirty).encode()
            if args == ("show", gate.SLICE + ":" + gate.README):
                return b"Historical B2 note\n"
            raise AssertionError("unexpected Git operation: " + repr(args))
        return fake_git

    def test_clean_committed_slice_or_descendant_passes(self):
        # Only the pinned slice is diffed, so unrelated later committed files do
        # not get admitted into the original slice's allowlist.
        for head in (gate.SLICE, "later-descendant"):
            with self.subTest(head=head), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                fake = self.scope_fixture(root)
                with patch.object(gate, "ROOT", root), patch.object(gate, "git", side_effect=fake):
                    gate.scope_checks()

    def test_extra_untracked_file_fails_with_named_path(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fake = self.scope_fixture(root, dirty=("evidence/copied-bundle.json",))
            with patch.object(gate, "ROOT", root), patch.object(gate, "git", side_effect=fake):
                with self.assertRaisesRegex(ValueError, "evidence/copied-bundle.json"):
                    gate.scope_checks()

    def test_later_committed_slice_edit_fails(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fake = self.scope_fixture(root, changed=("validate_forgeai_gemma4_b2_candidate_1.py",))
            with patch.object(gate, "ROOT", root), patch.object(gate, "git", side_effect=fake):
                with self.assertRaisesRegex(ValueError, "committed B2 slice changed"):
                    gate.scope_checks()

    def test_original_slice_allowlist_not_widened(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fake = self.scope_fixture(root, original=gate.SLICE_FILES | {"unexpected.py"})
            with patch.object(gate, "ROOT", root), patch.object(gate, "git", side_effect=fake):
                with self.assertRaisesRegex(ValueError, "file set differs"):
                    gate.scope_checks()

    def test_internal_evidence_refused_before_read(self):
        with self.assertRaisesRegex(ValueError, "outside the repository"):
            gate.external_path(gate.ROOT / "evidence/receipt.json", "receipt file")

    def test_wrong_receipt_refused_before_import(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            receipt = root / "receipt.json"
            receipt.write_bytes(b"not authenticated evidence")
            for name in ("install-evidence.json", "compiler-output.json", "manifest.json", "submission.zip"):
                (root / name).write_bytes(b"fixture")
            with self.assertRaisesRegex(ValueError, "receipt SHA256 differs"):
                gate.preserved_bundle("b2", receipt, root)


if __name__ == "__main__":
    unittest.main()
