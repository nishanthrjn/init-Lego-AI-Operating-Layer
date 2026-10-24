"""Offline candidate and per-task context-failure controls."""
import json
from pathlib import Path
import tempfile
import unittest

import analysis
import continuation
import experimental
from test_local_eval import record, meta


def jsonl_record(value):
    return (json.dumps(value, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")


class P3Tests(unittest.TestCase):
    def test_output_only_and_graph_only_deltas(self):
        base = experimental.static_files("p1b")
        p3 = experimental.static_files("p3")
        graph = experimental.static_files("p3g")
        self.assertEqual({k for k in base if base[k] != p3[k]}, {"configs/sampling.yaml"})
        self.assertEqual(p3["configs/sampling.yaml"], base["configs/sampling.yaml"].replace(
            b"max_output_tokens: 16384", b"max_output_tokens: 8192"))
        self.assertIn(b"thinking_budget: 4096", p3["configs/sampling.yaml"])
        self.assertEqual({k for k in p3 if p3[k] != graph[k]}, {"agent.yaml", "prompts/system.md"})
        for marker in (b"3. Make an early", b"6. Finish explicitly"):
            self.assertEqual(p3["prompts/system.md"].split(marker)[1], graph["prompts/system.md"].split(marker)[1])
        self.assertIn(b"at most three graph calls", graph["prompts/system.md"])

    def test_context_error_is_agent_outcome_without_masking_other_errors(self):
        row = dict(record(passed=False), patch_bytes=0,
                   harness_errors=["HARNESS_ERROR_DETAILS_IN_EXTERNAL_LOG", "OTHER_INFRA_ERROR"])
        projected = continuation.project(row, error="Sandbox execution error: litellm.ContextWindowExceededError")
        self.assertIn("CONTEXT_WINDOW_EXCEEDED", analysis.categories(projected))
        self.assertEqual(projected["harness_errors"], ["OTHER_INFRA_ERROR"])
        self.assertEqual(projected["verification_status"], "UNRESOLVED")
        self.assertEqual(row["harness_errors"][0], "HARNESS_ERROR_DETAILS_IN_EXTERNAL_LOG")

    def test_model_prose_cannot_establish_context_error(self):
        projected = continuation.project(record(passed=False), log="I might get ContextWindowExceededError")
        self.assertNotIn("CONTEXT_WINDOW_EXCEEDED", projected["failure_categories"])

    def test_official_session_timeout_is_not_context_failure(self):
        row = dict(record(passed=False), stop_reason="time_budget",
                   harness_errors=["HARNESS_ERROR_DETAILS_IN_EXTERNAL_LOG"])
        projected = continuation.project(row, error="Agent exceeded session timeout (6.0 min)")
        self.assertEqual(projected["verification_status"], "UNRESOLVED")
        self.assertEqual(projected["harness_errors"], [])
        self.assertNotIn("CONTEXT_WINDOW_EXCEEDED", projected["failure_categories"])
        self.assertIn("budget_exhausted", analysis.categories(projected))

    def test_structured_official_error_is_task_bound_and_history_unchanged(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "official").mkdir()
            (root / "run.json").write_bytes(analysis.canonical(meta()))
            row = dict(record(passed=False), harness_errors=["HARNESS_ERROR_DETAILS_IN_EXTERNAL_LOG"])
            raw = jsonl_record(row)
            (root / "tasks.jsonl").write_bytes(raw)
            official = {"instance_id": "a", "repo": row["repo"], "resolved": False,
                        "error": "litellm.ContextWindowExceededError: maximum context length"}
            target = root / "official/task_results.jsonl"
            target.write_bytes(jsonl_record(official))
            _, rows = analysis.read_run(root)
            self.assertIn("CONTEXT_WINDOW_EXCEEDED", rows[0]["failure_categories"])
            self.assertEqual(rows[0]["harness_errors"], [])
            self.assertEqual((root / "tasks.jsonl").read_bytes(), raw)
            target.write_bytes(jsonl_record(dict(official, repo="wrong")))
            with self.assertRaisesRegex(ValueError, "identity"):
                analysis.read_run(root)

    def test_duplicate_official_results_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "official").mkdir()
            (root / "run.json").write_bytes(analysis.canonical(meta()))
            row = record()
            (root / "tasks.jsonl").write_bytes(jsonl_record(row))
            item = {"instance_id": "a", "repo": row["repo"], "resolved": True, "error": None}
            (root / "official/task_results.jsonl").write_bytes(jsonl_record(item) * 2)
            with self.assertRaisesRegex(ValueError, "identity"):
                analysis.read_run(root)


if __name__ == "__main__":
    unittest.main()
