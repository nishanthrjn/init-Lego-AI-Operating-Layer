"""Control boundary tests use only independent fixtures; no official imports or execution."""
import asyncio
import contextlib
import copy
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import analysis as a
import controls as c
import runtime as r
from test_local_eval import record, meta


class ControlTests(unittest.TestCase):
    def test_cpu_setup_executes_only_cell_two_and_records_environment(self):
        # Independent inert cell fixtures; no official code or installation executes.
        cells = {"starter_sha256": "fixture", "cells": {
            "2": {"source": "installation_ran = True"},
            "8": {"source": "raise AssertionError('serving must never run')"}}}
        with tempfile.TemporaryDirectory() as directory, \
                patch.object(r, "official_cells", return_value=cells), \
                patch.object(r, "installed_versions", side_effect=[{"pkg": "before"}, {"pkg": "after"}]), \
                patch.object(r.sys, "platform", "linux"), \
                patch.object(r.sys, "version_info", (3, 12)):
            _, evidence, namespace = c.install_official_environment(
                {"official_environment_authorized": True}, Path(directory))
            self.assertTrue(namespace["installation_ran"])
            self.assertEqual(evidence["state"], "OFFICIAL_INSTALL_COMPLETED")
            self.assertEqual(evidence["post_install_versions"], {"pkg": "after"})
            self.assertEqual(json.loads((Path(directory) / "environment.json").read_bytes()), evidence)

    def test_cpu_setup_requires_install_approval(self):
        with patch.object(r, "official_cells", return_value={}), \
                patch.object(r, "installed_versions") as versions:
            with self.assertRaisesRegex(ValueError, "explicit approval"):
                c.install_official_environment({}, Path("unused"))
            versions.assert_not_called()

    def test_classification_matrix(self):
        passed = c.safe_result(True, "NONE", 1)
        failed = c.safe_result(False, "VERIFICATION_FAILED", 1)
        env = c.safe_result(False, "HARNESS_ENVIRONMENT_ERROR", 1)
        self.assertEqual(c.classify(passed, failed), "VERIFIABLE")
        self.assertEqual(c.classify(env, failed), "ENV_BROKEN")
        self.assertEqual(c.classify(env, passed), "UNSOUND")
        self.assertEqual(c.classify(failed, failed), "UNSOUND")
        self.assertEqual(c.classify(passed, env), "UNSOUND")

    def test_repo_api_failure_vs_third_party(self):
        for output in ("AttributeError: module 'httpx' has no attribute 'Stream'",
                       "ImportError: cannot import name 'Stream' from 'httpx' (/workspace/httpx/__init__.py)"):
            result = a.verification_outcome(False, output, "encode/httpx")
            self.assertEqual(result["verification_status"], "UNRESOLVED_INCOMPLETE_API")
            self.assertFalse(result["resolved"])
            self.assertEqual(result["harness_errors"], [])
        for output in ("ERROR collecting test.py\nModuleNotFoundError: No module named 'dirty_equals'",
                       "ImportError: cannot import name 'IsDict' from 'dirty_equals'"):
            result = a.verification_outcome(False, output, "fastapi/fastapi")
            self.assertEqual(result["verification_status"], "HARNESS_ENVIRONMENT_ERROR")
            self.assertIsNone(result["resolved"])

    def test_no_controls_no_agent_verdict(self):
        report = a.summarize(meta(), [record()])
        self.assertIsNone(report["pass_rate"])
        self.assertEqual(report["excluded_counts"], {"UNASSESSED": 1})
        self.assertEqual(report["passed"], 0)
        self.assertEqual(report["descriptive_observations_not_control_qualified"]["passed"], 1)

    def test_retained_httpx_error_reclassified_without_rewriting(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            m = meta()
            m["task_repos"] = {"a": "encode/httpx"}
            row = dict(record(passed=False), repo="encode/httpx",
                       harness_errors=["VERIFICATION_ERROR_OR_INCOMPLETE"])
            raw = json.dumps(row).encode() + b"\n"
            (root / "run.json").write_bytes(a.canonical(m))
            (root / "tasks.jsonl").write_bytes(raw)
            logs = root / "official/test_outputs"
            logs.mkdir(parents=True)
            (logs / "a.log").write_text("STDOUT:\nERROR collecting test.py\nAttributeError: module 'httpx' has no attribute 'Stream'")
            _, rows = a.read_run(root)
            self.assertEqual(rows[0]["verification_status"], "UNRESOLVED_INCOMPLETE_API")
            self.assertEqual(rows[0]["harness_errors"], [])
            self.assertFalse(rows[0]["official_resolved"])
            self.assertEqual((root / "tasks.jsonl").read_bytes(), raw)

    def test_exclusions_and_rates_only_verifiable(self):
        m = meta(("a", "b", "c", "d"))
        rows = [record("a"), record("b", False), record("c"), record("d")]
        controls = {k: {"class": cls} for k, cls in zip(m["task_ids"],
                    ("VERIFIABLE", "VERIFIABLE", "ENV_BROKEN", "UNSOUND"))}
        report = a.summarize(m, rows, controls)
        self.assertEqual(report["passed"], 1)
        self.assertEqual(report["unresolved"], 1)
        self.assertEqual(report["pass_rate"], 0.5)
        self.assertEqual(report["repo_macro_pass_rate"], 0.5)
        self.assertEqual(report["excluded_counts"], {"ENV_BROKEN": 1, "UNSOUND": 1})

    def test_no_gold_or_errors_in_result_projection(self):
        sentinel = "SECRET_REFERENCE_PATCH_SENTINEL"
        task = SimpleNamespace(patch=sentinel, test_patch="TEST_SENTINEL", repo="encode/httpx")
        received = []
        async def verify(*args, **kwargs):
            received.append(kwargs["agent_patch"])
            return SimpleNamespace(resolved=True, test_output=sentinel, agent_patch=sentinel,
                                   test_exit_code=0, error=sentinel)
        for mode in ("GOLD", "EMPTY"):
            output = asyncio.run(c.verify_one(task, mode, verify, None, None, (None, None, None)))
            self.assertEqual(set(output), {"passed", "error_category", "seconds"})
            self.assertNotIn(sentinel, json.dumps(output))
        self.assertEqual(received, [sentinel, ""])
        async def broken(*args, **kwargs):
            raise ValueError(sentinel)
        output = asyncio.run(c.verify_one(task, "GOLD", broken, None, None, (None, None, None)))
        self.assertNotIn(sentinel, json.dumps(output))
        self.assertEqual(output["error_category"], "CONTROL_EXECUTION_ERROR")

    def test_no_approval_stops_before_io(self):
        with self.assertRaisesRegex(ValueError, "authorization"):
            c.preflight({})

    def test_notebook_inert_no_model_or_install_cells(self):
        notebook = json.loads((Path(__file__).parent / "controls.ipynb").read_bytes())
        source = "".join("".join(cell["source"]) for cell in notebook["cells"] if cell["cell_type"] == "code")
        for forbidden in ("pip install", "VllmServer", "run_agent", "tasks.jsonl"):
            self.assertNotIn(forbidden, source)
        self.assertIn("CPU_ONLY_CONFIRMED = False", source)
        self.assertTrue(all(not cell.get("outputs") for cell in notebook["cells"]))

    def test_control_hash_schema_and_task_set(self):
        root = Path(__file__).parent
        subset_digest = (root / "subsets.sha256").read_text().split()[0]
        frozen, _ = a.load_subset(root / "subsets.json", subset_digest, "dev-30")
        m = dict(meta(), subset_sha256=subset_digest)
        doc = {"schema": 1, "state": "COMPLETE", "backend": "subprocess", "verification_timeout_seconds": 300,
               **{k: m[k] for k in ("subset_sha256", "official_tasks_sha256", "source_pins_sha256", "runtime_pins")},
               "tasks": [{"task_id": r["task_id"], "repo": r["repo"], "class": "VERIFIABLE",
                          "gold": c.safe_result(True, "NONE", 1),
                          "empty": c.safe_result(False, "VERIFICATION_FAILED", 1)}
                         for r in frozen["dev-30"] + frozen["confirm-20"]]}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "controls.json"
            path.write_bytes(a.canonical(doc))
            self.assertEqual(len(a.load_controls(path, a.sha(path), m)), 50)
            with self.assertRaisesRegex(ValueError, "SHA256"):
                a.load_controls(path, "0" * 64, m)
            for mutation in ("payload", "duplicate", "incomplete", "wrong_class"):
                bad = copy.deepcopy(doc)
                if mutation == "payload": bad["tasks"][0]["patch"] = "DO_NOT_RETAIN"
                if mutation == "duplicate": bad["tasks"][-1] = bad["tasks"][0]
                if mutation == "incomplete": bad["state"] = "INCOMPLETE"
                if mutation == "wrong_class": bad["tasks"][0]["class"] = "ENV_BROKEN"
                path.write_bytes(a.canonical(bad))
                with self.assertRaises(ValueError):
                    a.load_controls(path, a.sha(path), m)


if __name__ == "__main__":
    unittest.main()
