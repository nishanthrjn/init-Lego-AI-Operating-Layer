"""P3 qualification invariants; no compiler or provider invocation."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import sys
from unittest.mock import patch
import subprocess

from experiments.gemma4_competition import portable_p3 as p3


class P3QualificationTests(unittest.TestCase):
    def test_scope_git_reports_whitespace_location_without_content(self):
        import validate_forgeai_gemma4_p3_submission_qualification_1 as gate
        result = subprocess.CompletedProcess(
            ["git"], 2, b"README.md:1255: new blank line at EOF.\n+private text\n", b"")
        with patch.object(gate.subprocess, "run", return_value=result):
            with self.assertRaisesRegex(ValueError, "README.md:1255") as caught:
                gate.scope_git("diff", "--check", gate.BASE)
        self.assertNotIn("private text", str(caught.exception))

    def test_scope_git_keeps_successful_output_and_wiring(self):
        import validate_forgeai_gemma4_p3_submission_qualification_1 as gate
        result = subprocess.CompletedProcess(["git"], 0, b"file.py\n", b"")
        with patch.object(gate.subprocess, "run", return_value=result):
            self.assertEqual(gate.scope_git("diff", "--name-only", gate.BASE), b"file.py\n")
        self.assertIs(gate.scope_gate().git, gate.scope_git)

    def test_shared_default_and_p3_override_are_independent(self):
        from experiments.gemma4_competition import portable_m2
        self.assertEqual(portable_m2.EXPECTED_OUTPUT_TOKENS, 16384)
        self.assertEqual(p3.EXPECTED_OUTPUT_TOKENS, 8192)

    def test_experimental_members_and_archive_are_preserved(self):
        files = p3.static_candidate(p3.CANDIDATE)
        self.assertEqual({name: hashlib.sha256(raw).hexdigest() for name, raw in files.items()}, p3.MEMBER_PINS)
        self.assertEqual(hashlib.sha256(p3.zip_bytes(files)).hexdigest(), p3.EXPERIMENTAL_ZIP_SHA256)

    def test_changed_sampling_refused(self):
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary)
            for name, raw in p3.expected_files().items():
                path = target / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(raw)
            with (target / "configs/sampling.yaml").open("ab") as stream:
                stream.write(b"\n# changed\n")
            with self.assertRaises(ValueError):
                p3.static_candidate(target)

    def test_cpu_notebook_inert_and_candidate_bound(self):
        notebook = json.loads((p3.AREA / "kaggle_compiler/p3_compiler_only.ipynb").read_bytes())
        source = "\n".join("".join(cell.get("source", [])) for cell in notebook["cells"])
        self.assertIn(p3.INSTALL_AUTHORIZATION, source)
        self.assertIn("portable_p3.py", source)
        for cell in notebook["cells"]:
            if cell["cell_type"] == "code":
                self.assertIsNone(cell["execution_count"])
                self.assertEqual(cell["outputs"], [])

    def test_transfer_includes_p3_and_shared_engine(self):
        paths = p3.transfer_paths()
        self.assertIn("experiments/gemma4_competition/portable_p3.py", paths)
        self.assertIn("experiments/gemma4_competition/portable_m2.py", paths)
        self.assertEqual(len(paths), len(set(paths)))

    def test_paper_projection_preserves_missing_and_unknown(self):
        directory = str(p3.AREA / "local_eval")
        sys.path.insert(0, directory)
        try:
            from paper_evidence import project
            meta = {"task_ids": ["a", "b", "c"], "task_repos": {"a": "r", "b": "r", "c": "s"}}
            rows = [{"task_id": "a", "resolved": None}, {"task_id": "c", "resolved": True}]
            selected, actual = project(meta, rows, {"a", "b"})
            self.assertEqual(selected["task_ids"], ["a", "b"])
            self.assertEqual(actual, [{"task_id": "a", "resolved": None}])
            self.assertEqual(meta["task_ids"], ["a", "b", "c"])
        finally:
            sys.path.remove(directory)


if __name__ == "__main__":
    unittest.main()
