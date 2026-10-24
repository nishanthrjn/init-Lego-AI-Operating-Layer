"""Offline fixtures only; no official imports, packages, dataset or evaluation."""
import hashlib
import json
from pathlib import Path
import unittest
import tempfile
from unittest.mock import patch

import experimental
import localization as study


class LocalizationTests(unittest.TestCase):
    def test_recall_uses_all_gold_files_and_known_functions(self):
        gold = {"gold_files": ["a.py", "b.py"], "gold_functions": [
            {"file": "a.py", "name": "f"}, {"file": "b.py", "name": "UNRESOLVED"}]}
        ranked = [{"file": "x.py", "function": "x"}, {"file": "a.py", "function": "f"}]
        result = study.metrics(ranked, gold)
        self.assertEqual(result["file_recall@1"], 0)
        self.assertEqual(result["file_recall@3"], .5)
        self.assertEqual(result["file_mrr"], .5)
        self.assertEqual(result["function_recall@5"], 1)

    def test_no_known_functions_is_unknown_not_zero(self):
        self.assertIsNone(study.metrics([], {"gold_files": ["a.py"], "gold_functions": []})["function_recall@5"])

    def test_export_projection_drops_code_and_arbitrary_tool_strings(self):
        index = study.index_sources({"pkg/a.py": "def f():\n    return 'SECRET_SOURCE_SENTINEL'\n"})
        output = study.names_only(["pkg.a.f", "+SECRET_SOURCE_SENTINEL", "def x(): print('bad')"], index)
        raw = json.dumps(output)
        self.assertNotIn("SECRET", raw)
        self.assertNotIn("def ", raw)
        self.assertNotIn("+", raw)
        self.assertEqual(output[0], {"name": "pkg.a.f", "file": "pkg/a.py", "function": "f"})
        self.assertTrue(all(r["name"] == "UNRESOLVED" for r in output[1:]))

    def test_lexical_and_fusion_deterministic_no_gold_argument(self):
        index = study.index_sources({"a.py": "def decode_ansi():\n    return ansi\n", "b.py": "table = 0\n"})
        self.assertTrue(study.lexical("decode_ansi ansi", index)[0].startswith("a"))
        self.assertIn("a.decode_ansi", study.lexical("decode_ansi ansi", index))
        self.assertEqual(study.fuse(["a", "b"], ["b", "a"]), ["a", "b"])

    def test_unavailable_tasks_not_silently_dropped(self):
        report = study.summarize([{"task_id": "rich_4076", "repo": "Textualize/rich", "state": "UNAVAILABLE"}])
        self.assertEqual(report["overall"]["unavailable"], 1)
        self.assertEqual(report["diagnosed_failures"]["tasks"], 1)

    def test_p2_scope_tools_and_unchanged_budgets(self):
        p2 = experimental.static_files("p2")
        p1b = experimental.static_files("p1b")
        self.assertEqual({k for k in p2 if p2[k] != p1b[k]}, {"agent.yaml", "prompts/system.md"})
        for name in (b"search_similar_code", b"get_code_neighbors", b"get_code_subgraph"):
            self.assertEqual(p2["agent.yaml"].count(b"  - " + name + b"\n"), 1)
        self.assertTrue(p2["prompts/system.md"].startswith(p1b["prompts/system.md"]))

    def test_gold_metadata_identity_and_no_extra_fields(self):
        from location_review import validate_metadata
        raw = (study.HERE / "evidence/gold-locations.json").read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(), study.GOLD_SHA)
        doc = json.loads(raw)
        validate_metadata(doc)
        self.assertEqual(len(doc["tasks"]), 129)
        self.assertEqual(sum(r["location_status"] == "RESOLVED" for r in doc["tasks"]), 65)

    def test_authorization_precedes_install(self):
        with patch("runtime.install_official_environment") as install:
            with self.assertRaises(ValueError):
                study.run({})
            install.assert_not_called()

    def test_notebook_inert_cpu_only(self):
        nb = json.loads((study.HERE / "localization_study.ipynb").read_bytes())
        code = "\n".join("".join(c["source"]) for c in nb["cells"] if c["cell_type"] == "code")
        self.assertIn("CPU_ONLY_CONFIRMED = False", code)
        self.assertIn("AUTHORIZATION = ''", code)
        self.assertNotIn("VllmServer", code)
        self.assertNotIn("cell_8", code)
        for cell in nb["cells"]:
            if cell["cell_type"] == "code":
                self.assertIsNone(cell["execution_count"])
                self.assertEqual(cell["outputs"], [])

    def test_gpu_refuses_gold_tooling_before_environment_or_model(self):
        import runtime
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "evidence").mkdir()
            (root / "evidence/gold-locations.json").write_text("{}")
            with patch.object(runtime, "HERE", root), patch.object(runtime, "prepare") as prepare:
                with self.assertRaisesRegex(ValueError, "gold-location"):
                    runtime.worker({}, root)
                prepare.assert_not_called()

    def test_tool_error_not_zero_recall(self):
        report = study.summarize([{"task_id": "x", "repo": "r", "metrics": {
            "T1": None, "T2": None, "L": {"file_mrr": 0.5}, "L+T1": None}}])
        self.assertEqual(report["overall"]["methods"]["T1"], {"unavailable_tasks": 1})
        self.assertEqual(report["overall"]["methods"]["L"]["file_mrr"]["mean"], .5)


if __name__ == "__main__":
    unittest.main()
