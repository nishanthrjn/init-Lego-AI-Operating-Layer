import json
from pathlib import Path
import unittest
import analysis as a
from trace_review import review


class TraceReviewTests(unittest.TestCase):
    def test_derived_subset_exact_and_pinned(self):
        root = Path(__file__).parent
        path = root / "dev-16v.json"
        _, rows = a.load_subset(path, a.sha(path), "dev-16v")
        self.assertEqual(len(rows), 16)
        self.assertEqual(sum(r["repo"].lower().endswith("/fastapi") for r in rows), 8)
        with self.assertRaises(ValueError):
            a.load_subset(path, "0" * 64, "dev-16v")

    def test_submit_errors_timing_and_unknown_fields(self):
        steps = [{"source": "agent", "step_id": i, "extra": {"elapsed_s": i * 10},
                  "tool_calls": [{"function_name": "submit_patch", "tool_call_id": str(i)}],
                  "observation": {"extra": {"elapsed_s": i * 10 + 2, "tool_name": "submit_patch"}, "content": "error fixture"}}
                 for i in (1, 2)]
        result = review({"steps": steps})
        self.assertEqual(len(result["submit_patch_calls"]), 2)
        self.assertEqual(result["submit_patch_calls"][0]["response"], "error fixture")
        self.assertEqual(result["turns"][1]["model_plus_overhead_gap_seconds"], 8)
        self.assertIsNone(result["turns"][0]["thinking_tokens"])
        self.assertIsNone(result["final_git_status"])

    def test_edit_and_last_status(self):
        calls = [("edit_file", {}), ("run_command", {"command": "git status --short"})]
        result = review({"steps": [{"source": "agent", "step_id": i,
            "tool_calls": [{"function_name": name, "arguments": args}],
            "observation": {"extra": {"tool_name": name}, "content": "fixture"}}
            for i, (name, args) in enumerate(calls)]})
        self.assertEqual(result["first_observed_edit_attempt"]["step_id"], 0)
        self.assertEqual(result["last_recorded_git_status"]["response"], "fixture")
