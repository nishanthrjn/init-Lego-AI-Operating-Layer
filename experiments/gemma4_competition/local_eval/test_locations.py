import json
from pathlib import Path
import unittest
from unittest.mock import patch
from location_metadata import locations, parse_diff, apply_text, functions_at, export
from location_review import classify, retained_patch
from test_local_eval import record

PATCH = "--- a/mod.py\n+++ b/mod.py\n@@ -2 +2 @@\n-    return 1\n+    return 2\n"


class LocationTests(unittest.TestCase):
    def test_inherited_patch_requires_ancestor_and_matching_candidate(self):
        row = {"task_id": "a", "inherited_from_run_sha256": "pin"}
        self.assertIsNone(retained_patch(Path("new"), row, {}, {}))
        prior = {"candidate": "p1b", "package_sha256": "p", "official_tasks_sha256": "t"}
        with patch("location_review.read_run", return_value=(prior, [{"task_id": "a"}])):
            self.assertEqual(retained_patch(Path("new"), row, {"pin": Path("old")}, prior), Path("old/official/patches/a.patch"))
            with self.assertRaises(ValueError):
                retained_patch(Path("new"), row, {"pin": Path("old")}, dict(prior, candidate="p1c"))

    def test_metadata_only_and_test_exclusion(self):
        patch = PATCH + "--- a/tests/test_mod.py\n+++ b/tests/test_mod.py\n@@ -1 +1 @@\n-SECRET_TEST\n+SECRET_TEST_NEW\n"
        result = locations({"instance_id": "x", "repo": "psf/requests", "patch": patch},
                           lambda _: "def target():\n    return 1\n")
        self.assertEqual(result["gold_files"], ["mod.py"])
        self.assertEqual(result["gold_functions"][0]["name"], "target")
        self.assertEqual(result["lines_changed_count"], 2)
        blob = json.dumps(result, indent=2)
        for forbidden in ("return 1", "return 2", "SECRET_TEST", "@@", "--- a/", "+++ b/"):
            self.assertNotIn(forbidden, blob)
        self.assertFalse(any(line.startswith(("+", "-")) for line in blob.splitlines()))

    def test_nested_scope_and_unresolved(self):
        scopes = functions_at("class C:\n    async def f(self):\n        return 1\n", [3])
        self.assertEqual(scopes[0]["name"], "C.f")
        self.assertEqual(functions_at(None, [1])[0]["name"], "UNRESOLVED")

    def test_text_delta_and_unsafe_path(self):
        change = parse_diff(PATCH)[0]
        self.assertEqual(apply_text("def target():\n    return 1\n", change), "def target():\n    return 2\n")
        with self.assertRaises(ValueError):
            apply_text("def other():\n    return 3\n", change)
        with self.assertRaises(ValueError):
            parse_diff(PATCH.replace("mod.py", "../../escape.py"))

    def test_classification_is_location_evidence_not_guess(self):
        gold = locations({"instance_id": "x", "repo": "psf/requests", "patch": PATCH}, lambda _: "def target():\n    return 1\n")
        row = record(passed=False)
        self.assertEqual(classify(row, gold, PATCH)["category"], "RIGHT_LOCATION_WRONG_FIX")
        self.assertEqual(classify(row, gold, PATCH.replace("mod.py", "other.py"))["category"], "WRONG_LOCATION")
        self.assertEqual(classify(dict(row, patch_bytes=0), gold, "")["category"], "NO_EDIT")
        self.assertEqual(classify(dict(row, failure_categories=["TOOL_CALL_FORMAT_FAILURE"]), gold, PATCH)["category"], "TOOL_FORMAT/OTHER")
        self.assertEqual(classify(row, gold, None)["reason"], "PATCH_UNAVAILABLE")

    def test_export_gate_before_data_access(self):
        with self.assertRaises(ValueError):
            export(Path("absent"), Path("absent"), "", False, False)

    def test_notebook_embeds_reviewed_source_and_is_inert(self):
        root = Path(__file__).parent
        doc = json.loads((root / "gold_location_export.ipynb").read_bytes())
        code = "".join("".join(c["source"]) for c in doc["cells"] if c["cell_type"] == "code")
        self.assertIn((root / "location_metadata.py").read_text(), code)
        self.assertIn("CPU_CONFIRMED = False", code)
        self.assertNotIn("pip install", code)
        self.assertTrue(all(not c.get("outputs") for c in doc["cells"]))
