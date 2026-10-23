import json
from pathlib import Path
import tempfile
import unittest
import analysis as a
import continuation as c
from test_local_eval import record, meta


class ContinuationTests(unittest.TestCase):
    def test_agent_failures_continue_and_format_is_unresolved(self):
        for error in ("Agent completed execution without calling submit_patch.",
                      "Agent exceeded session timeout (6 min)", "Agent exceeded tool call budget",
                      "Agent exceeded turns budget (80 turns)"):
            self.assertFalse(c.fatal_error(error))
        row = dict(record(passed=False), patch_bytes=0, stop_reason="error",
                   harness_errors=["HARNESS_ERROR_DETAILS_IN_EXTERNAL_LOG"])
        result = c.project(row, "Agent completed execution without calling submit_patch.",
                           "Reached maximum continuation nudges (3)")
        self.assertFalse(result["resolved"])
        self.assertEqual(result["harness_errors"], [])
        self.assertEqual(result["failure_categories"], ["NO_PATCH", "TOOL_CALL_FORMAT_FAILURE"])
        self.assertIn("TOOL_CALL_FORMAT_FAILURE", a.categories(result))

    def test_load_and_server_failures_stop(self):
        for error in ("Failed to load agent", "Compilation failed", "vLLM server unavailable", "APIConnectionError"):
            self.assertTrue(c.fatal_error(error))

    def test_merge_refuses_completed_duplicate(self):
        self.assertEqual(len(c.merge([{"task_id": "a"}], [{"task_id": "b"}])), 2)
        with self.assertRaises(ValueError):
            c.merge([{"task_id": "a"}], [{"task_id": "a"}])

    def test_resume_pins_identity_incomplete_and_provenance(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            old = dict(meta(("a", "b")), candidate="p1b", package_mode="EXPERIMENTAL_UNQUALIFIED",
                       manifest_sha256="m", package_sha256="p", model="model", official_cell_sha256={})
            (root / "run.json").write_bytes(a.canonical(old))
            (root / "config.json").write_bytes(a.canonical(old))
            rows = [dict(record("a"), completed_result=True), dict(record("b", False), completed_result=False)]
            (root / "tasks.jsonl").write_bytes(b"".join((json.dumps(r) + "\n").encode() for r in rows))
            (root / "completion.json").write_bytes(a.canonical({"state": "HARNESS_ERROR"}))
            manifest = {"config_sha256": c.digest(root / "config.json"),
                        "files": {name: c.digest(root / name) for name in ("run.json", "tasks.jsonl", "completion.json")}}
            path = root / "manifest.json"
            path.write_bytes(a.canonical(manifest))
            config = dict(old, resume_manifest=str(path), resume_manifest_sha256=c.digest(path),
                          resume_previous=str(root), resume_previous_config=str(root / "config.json"))
            kept, _ = c.load_resume(config, old)
            self.assertEqual([r["task_id"] for r in kept], ["a"])
            self.assertEqual(kept[0]["attempt_id"], manifest["files"]["run.json"])
            for key in c.IDENTITY:
                with self.assertRaises(ValueError):
                    c.load_resume(config, dict(old, **{key: "changed"}))
            (root / "tasks.jsonl").write_text("tampered")
            with self.assertRaisesRegex(ValueError, "hash mismatch"):
                c.load_resume(config, old)

    def test_offline_projection_preserves_historical_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "run.json").write_bytes(a.canonical(meta()))
            row = dict(record(passed=False), patch_bytes=0, harness_errors=["HARNESS_ERROR_DETAILS_IN_EXTERNAL_LOG"])
            raw = (json.dumps(row) + "\n").encode()
            (root / "tasks.jsonl").write_bytes(raw)
            logs = root / "official/logs"
            logs.mkdir(parents=True)
            (logs / "a.log").write_text('<|tool_call>call:read_file malformed')
            _, rows = a.read_run(root)
            self.assertIn("TOOL_CALL_FORMAT_FAILURE", rows[0]["failure_categories"])
            self.assertEqual((root / "tasks.jsonl").read_bytes(), raw)
