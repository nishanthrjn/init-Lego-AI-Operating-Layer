"""Offline regression tests. Run only by explicit maintainer execution."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import experimental
import tool_rejections as t


def step(name="edit_file", response=t.PHRASE, arguments=None):
    return {"source": "agent", "tool_calls": [{"tool_call_id": "1", "function_name": name,
            "arguments": arguments or {"filepath": "x", "new_string": "x`,old_string:"}}],
            "observation": {"content": response, "extra": {"tool_name": name}}}


class ToolRejectionTests(unittest.TestCase):
    def test_rejections_and_identical_resends(self):
        r = t.inspect_trace({"steps": [step()] * 27})
        self.assertEqual(r["edit_write_rejected"], 27)
        self.assertEqual(r["rejection_rate"], 1)
        self.assertEqual(r["consecutive_identical_resends"], 26)
        self.assertEqual(r["max_consecutive_identical_rejections"], 27)
        self.assertEqual(r["failure_categories"], ["TOOL_ARGUMENT_REJECTED"])

    def test_intervening_call_breaks_streak_and_argument_text_is_not_response(self):
        r = t.inspect_trace({"steps": [step(), step("run_command", "ok", {"command": t.PHRASE}), step()]})
        self.assertEqual(r["max_consecutive_identical_rejections"], 1)
        self.assertEqual(r["consecutive_identical_resends"], 0)
        self.assertAlmostEqual(r["all_tool_rejection_rate"], 2 / 3)

    def test_all_tools_gate_separate_from_edit_denominator(self):
        r = t.inspect_trace({"steps": [step("run_command")]})
        self.assertIsNone(r["rejection_rate"])
        self.assertEqual(r["all_tool_rejection_rate"], 1)
        clean = t.inspect_trace({"steps": [step("run_command", "ok")]})
        self.assertEqual(clean["all_tool_rejection_rate"], 0)
        self.assertIsNone(clean["rejection_rate"])

    def test_ambiguous_or_missing_observation_is_unknown(self):
        s = step()
        s["tool_calls"].append(dict(s["tool_calls"][0], tool_call_id="2"))
        r = t.inspect_trace({"steps": [s]})
        self.assertIsNone(r["all_tool_rejection_rate"])
        self.assertEqual(r["edit_write_unknown"], 2)
        s["observation"]["extra"]["tool_call_id"] = "2"
        r = t.inspect_trace({"steps": [s]})
        self.assertEqual(r["edit_write_rejected"], 1)
        self.assertEqual(r["edit_write_unknown"], 1)

    def test_source_edit_evidence_is_output_only(self):
        marker = "FORGEAI_SOURCE_EDIT_COMPLETED"
        r = t.inspect_trace({"steps": [step("run_command", json.dumps({"stdout": marker + "\n", "exit_code": 0})),
                                      step("run_command", "ok", {"command": "print('" + marker + "')"})]})
        self.assertEqual(r["run_command_source_edits_evidenced"], 1)
        self.assertIn("LOWER_BOUND", r["source_edit_count_status"])

    def test_aggregate_missing_trace_cannot_pass(self):
        r = t.inspect_trace({"steps": [step("run_command", "ok")]})
        combined = t.aggregate([r, {"status": "MISSING"}])
        self.assertIsNone(combined["all_tool_rejection_rate"])
        self.assertFalse(combined["all_tool_coverage_complete"])
        self.assertEqual(combined["missing_trace_tasks"], 1)
        self.assertIsNone(t.aggregate([])["all_tool_rejection_rate"])

    def test_trace_file_hash_and_safe_task_identity(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.assertEqual(t.task_report(root, "rich_1")["status"], "MISSING")
            directory = root / "official/traces"
            directory.mkdir(parents=True)
            (directory / "trace_rich_1.json").write_text(json.dumps({"steps": [step()]}))
            report = t.task_report(root, "rich_1")
            self.assertEqual(len(report["trace_sha256"]), 64)
            self.assertEqual(report["edit_write_rejected"], 1)
            with self.assertRaises(ValueError):
                t.task_report(root, "../escape")

    def test_p5_changes_only_prompt_and_preserves_p3_text(self):
        p3, p5 = experimental.static_files("p3"), experimental.static_files("p5")
        self.assertEqual({k for k in p3 if p3[k] != p5[k]}, {"prompts/system.md"})
        prefix, suffix = p3["prompts/system.md"].split(b"\n4. Verify before submitting.", 1)
        self.assertTrue(p5["prompts/system.md"].startswith(prefix))
        self.assertTrue(p5["prompts/system.md"].endswith(b"\n4. Verify before submitting." + suffix))
        self.assertIn(b"<<'EOF'", p5["prompts/system.md"])
        self.assertIn(b"FORGEAI_SOURCE_EDIT_COMPLETED", p5["prompts/system.md"])

    def test_p5_configs_are_independent_and_not_authorized(self):
        configs = [json.loads((experimental.HERE / "configs" / f"p5-dev16v-attempt{i}.json").read_bytes()) for i in (1, 2)]
        self.assertNotEqual(configs[0]["output"], configs[1]["output"])
        for config in configs:
            self.assertEqual(config["candidate"], "p5")
            self.assertFalse(config["gpu_authorized"])
            self.assertFalse(config["experimental_authorized"])
            self.assertEqual(config["resume_previous"], "")


    def test_patch_production_zero_is_not_unknown_and_missing_is_not_zero(self):
        import analysis
        from test_local_eval import meta, record
        rows = [dict(record("a"), patch_bytes=12), dict(record("b"), patch_bytes=0)]
        with patch.object(analysis, "projection", return_value={"gate": "UNKNOWN"}):
            summary = analysis.summarize_observations(meta(("a", "b")), rows)
            self.assertEqual(summary["patch_production"]["share"], 0.5)
            rows[1]["patch_bytes"] = None
            summary = analysis.summarize_observations(meta(("a", "b")), rows)
            self.assertIsNone(summary["patch_production"]["share"])
            summary = analysis.summarize_observations(meta(("a", "b")), rows[:1])
            self.assertIsNone(summary["patch_production"]["share"])
            self.assertIsNone(summary["tool_argument_rejections"]["all_tool_rejection_rate"])

    def test_read_run_adds_category_without_mutating_retained_files(self):
        import analysis
        from test_local_eval import meta, record
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "run.json").write_text(json.dumps(meta()))
            raw = (json.dumps(record()) + "\n").encode()
            (root / "tasks.jsonl").write_bytes(raw)
            directory = root / "official/traces"
            directory.mkdir(parents=True)
            (directory / "trace_a.json").write_text(json.dumps({"steps": [step()]}))
            _, rows = analysis.read_run(root)
            self.assertIn("TOOL_ARGUMENT_REJECTED", rows[0]["failure_categories"])
            self.assertEqual((root / "tasks.jsonl").read_bytes(), raw)

    def test_build_emits_matching_configs_and_refuses_overwrite(self):
        import contextlib
        import io
        import sys
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "p5"
            with patch.object(sys, "argv", ["experimental.py", "p5", "--output", str(output)]):
                with contextlib.redirect_stdout(io.StringIO()):
                    experimental.main()
                manifest = output / "manifest.json"
                package = output / "submission.zip.bin"
                for attempt in (1, 2):
                    config = json.loads((output / f"p5-dev16v-attempt{attempt}.json").read_bytes())
                    self.assertEqual(config["manifest_sha256"], experimental.digest(manifest.read_bytes()))
                    self.assertEqual(config["zip_sha256"], experimental.digest(package.read_bytes()))
                    self.assertFalse(config["experimental_authorized"])
                with self.assertRaises(FileExistsError):
                    experimental.main()

if __name__ == "__main__":
    unittest.main()
