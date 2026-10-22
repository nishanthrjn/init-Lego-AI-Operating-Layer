"""Independent fixture controls; no official imports, GPU, subprocess or network calls."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

import analysis as a
import runtime as r


def inventory():
    return [{"instance_id": f"{repo}-{i}", "repo": "org/" + repo,
             "kind": "bug" if i % 2 else "feature"}
            for repo, count in (("fastapi", 67), ("httpx", 1), ("requests", 13), ("rich", 48)) for i in range(count)]


def record(tid="a", passed=True):
    return {"schema": 1, "task_id": tid, "repo": "org/httpx", "resolved": passed,
            "wall_seconds": 120.0, "agent_seconds": 100.0, "model_turns": 10,
            "tool_calls": {"run_command": 3, "get_code_neighbors": 2}, "tokens": None,
            "submit_patch_called": True, "patch_bytes": 12, "files_changed": ["a.py"],
            "test_files_touched": None, "stray_files": None, "stop_reason": "submitted",
            "last_tool_error": None, "harness_errors": [], "seconds_per_model_turn": 10.0,
            "verification_status": "passed" if passed else "failed"}


def meta(ids=("a",)):
    return {"task_ids": list(ids), "task_repos": {i: "org/httpx" for i in ids},
            "subset_sha256": "a" * 64, "subset": "smoke-5", "source_sha256": "b" * 64,
            "runtime_pins": {"swegemma": "0.2.11"}, "startup_seconds": 100.0,
            "source_pins_sha256": "c" * 64, "official_tasks_sha256": "d" * 64,
            "completion_state": "COMPLETED"}


class SubsetTests(unittest.TestCase):
    def test_balanced_nested_and_order_independent(self):
        doc = a.freeze(inventory(), "a" * 64, "kind")
        self.assertEqual(doc, a.freeze(list(reversed(inventory())), "a" * 64, "kind"))
        self.assertEqual(len(doc["dev-30"]), 30)
        self.assertEqual(len({x["task_id"] for x in doc["dev-30"]}), 30)
        self.assertTrue({r["task_id"] for r in doc["smoke-5"]} <= {r["task_id"] for r in doc["dev-30"]})
        self.assertFalse({r["task_id"] for r in doc["confirm-20"]} & {r["task_id"] for r in doc["dev-30"]})
        self.assertEqual(sorted(a.Counter(x["repo"] for x in doc["dev-30"]).values()), [1, 6, 11, 12])
        self.assertTrue(all(set(r) == {"task_id", "repo", "label"} for r in doc["dev-30"]))

    def test_no_inferred_labels(self):
        rows = [{"instance_id": r["instance_id"], "repo": r["repo"]} for r in inventory()]
        self.assertEqual({x["label"] for x in a.freeze(rows, "a" * 64)["dev-30"]}, {None})

    def test_solution_test_issue_payload_columns_refused(self):
        for key in ("patch", "test_patch", "problem_statement", "issue", "solution"):
            rows = inventory()
            rows[0][key] = "FORBIDDEN_PAYLOAD"
            with self.assertRaisesRegex(ValueError, "metadata-only"):
                a.freeze(rows, "a" * 64, "kind")

    def test_duplicate_and_wrong_inventory_refused(self):
        for rows in (inventory()[:-1], inventory()[:-1] + [inventory()[0]]):
            with self.assertRaises(ValueError):
                a.freeze(rows, "a" * 64, "kind")

    def test_subset_pin_refuses_modified_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "subset.json"
            p.write_bytes(a.canonical(a.freeze(inventory(), "a" * 64, "kind")))
            pin = a.sha(p)
            self.assertEqual(len(a.load_subset(p, pin, "smoke-5")[1]), 5)
            p.write_bytes(p.read_bytes() + b" ")
            with self.assertRaises(ValueError):
                a.load_subset(p, pin, "smoke-5")

    def test_committed_subsets_are_metadata_only_and_pinned(self):
        root = Path(__file__).parent
        pin = (root / "subsets.sha256").read_text().split()[0]
        doc, rows = a.load_subset(root / "subsets.json", pin, "dev-30")
        self.assertEqual(len(rows), 30)
        for name in a.ALLOCATIONS:
            for entry in doc[name]:
                self.assertEqual(set(entry), {"task_id", "repo", "label"})
                self.assertRegex(entry["task_id"], r"^[A-Za-z0-9_.-]+$")
                self.assertRegex(entry["repo"], r"^[A-Za-z0-9_-]+/[A-Za-z0-9_-]+$")
                self.assertIsNone(entry["label"])

    def test_regeneration_against_external_metadata_if_available(self):
        source = Path(r"D:\Downloads\gemma4-dev-metadata\public_dev_task_metadata.jsonl")
        if not source.is_file():
            self.skipTest("external metadata not present; committed byte and schema controls still apply")
        rows = [json.loads(line) for line in source.read_text().splitlines()]
        expected = a.canonical(a.freeze(rows, a.sha(source)))
        self.assertEqual(expected, (Path(__file__).parent / "subsets.json").read_bytes())


class PackageTests(unittest.TestCase):
    def test_bin_and_manifest_are_both_pinned(self):
        with tempfile.TemporaryDirectory() as tmp:
            p, m = Path(tmp) / "submission.zip.bin", Path(tmp) / "manifest.json"
            p.write_bytes(b"fixture")
            manifest = {"state": "PORTABLE_COMPILE_AND_PACKAGE_PASS", "zip_size": 7,
                        "zip_sha256": a.sha(p), "local_receipt_sha256": "c" * 64}
            m.write_bytes(a.canonical(manifest))
            pin = a.sha(m)
            self.assertEqual(a.verify_package(p, m, pin, "c" * 64), manifest)
            p.write_bytes(b"changed")
            with self.assertRaisesRegex(ValueError, "package byte"):
                a.verify_package(p, m, pin, "c" * 64)
            m.write_bytes(m.read_bytes() + b" ")
            with self.assertRaisesRegex(ValueError, "manifest raw"):
                a.verify_package(p, m, pin, "c" * 64)

    def test_archive_traversal_refused_before_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "bad.zip"
            with zipfile.ZipFile(p, "w") as z:
                z.writestr("../outside", "bad")
            with self.assertRaises(ValueError):
                a.extract_package(p, Path(tmp) / "out")
            self.assertFalse((Path(tmp) / "out").exists())

    def test_valid_archive_extracts_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "fixture.bin"
            with zipfile.ZipFile(p, "w") as z:
                z.writestr("agent.yaml", b"fixture\n")
            a.extract_package(p, Path(tmp) / "out")
            self.assertEqual((Path(tmp) / "out/agent.yaml").read_bytes(), b"fixture\n")


class EvidenceTests(unittest.TestCase):
    def test_schema_rejects_invalid_values(self):
        a.validate_record(record())
        for key, value in (("resolved", 1), ("wall_seconds", float("nan")), ("model_turns", -1),
                           ("tool_calls", {"read_file": -1}), ("stop_reason", "guessed")):
            bad = dict(record(), **{key: value})
            with self.assertRaises(ValueError):
                a.validate_record(bad)

    def test_torn_last_line_keeps_completed_record(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "run.json").write_bytes(a.canonical(meta()))
            (root / "tasks.jsonl").write_bytes(json.dumps(record()).encode() + b'\n{"task_id":')
            self.assertEqual(len(a.read_run(root)[1]), 1)

    def test_projection_arithmetic_and_gate(self):
        p = a.projection([360.0] * 30, 1200, True)
        self.assertEqual(p["gate"], "FAIL")
        self.assertAlmostEqual(p["mean_hours"], (116 * 360 + 1200) / 3600)
        self.assertEqual(a.projection([120] * 5, 100, True)["gate"], "PASS")
        self.assertEqual(a.projection([120], 100, False)["gate"], "INCONCLUSIVE")

    def test_p95_and_exact_eleven_hour_boundary(self):
        self.assertEqual(a.projection([1] * 19 + [1000], 0, True)["p95_task_seconds"], 1)
        self.assertEqual(a.projection([39600 / 116], 0, True)["gate"], "PASS")

    def test_unknown_not_scored_as_failure_and_graph_tools_counted(self):
        m = meta(("a", "b"))
        out = a.summarize(m, [record()])
        self.assertIsNone(out["pass_rate"])
        self.assertEqual(out["pass_rate_lower_bound"], 0.5)
        self.assertEqual(out["tool_usage"]["get_code_neighbors"], 2)
        self.assertEqual(out["time_fit"]["gate"], "INCONCLUSIVE")

    def test_macro_differs_from_task_weighted_rate(self):
        m = meta(("a", "b", "c"))
        m["task_repos"] = {"a": "org/httpx", "b": "org/rich", "c": "org/rich"}
        rows = [record("a", True), dict(record("b", False), repo="org/rich"), dict(record("c", False), repo="org/rich")]
        out = a.summarize(m, rows)
        self.assertAlmostEqual(out["pass_rate"], 1 / 3)
        self.assertEqual(out["repo_macro_pass_rate"], 0.5)

    def test_harness_error_cannot_pass_time_gate(self):
        row = dict(record(), harness_errors=["setup error"])
        self.assertEqual(a.summarize(meta(), [row])["time_fit"]["gate"], "INCONCLUSIVE")

    def test_exact_sign_test_and_ties(self):
        ids = tuple(str(i) for i in range(7))
        aa = [record(i, False) for i in ids]
        bb = [record(i, i != "6") for i in ids]
        out = a.paired(meta(ids), aa, meta(ids), bb)
        self.assertEqual(out["ties"], 1)
        self.assertEqual(out["exact_two_sided_sign_test_p"], 0.03125)

    def test_comparison_rejects_subset_changes_and_partial_runs(self):
        changed = copy.deepcopy(meta())
        changed["subset_sha256"] = "d" * 64
        with self.assertRaises(ValueError):
            a.paired(meta(), [record()], changed, [record()])
        with self.assertRaises(ValueError):
            a.paired(meta(), [], meta(), [record()])

    def test_stop_reason_requires_explicit_evidence(self):
        self.assertEqual(r.stop_reason("Agent exceeded tool call budget (28 calls)", False), "call_budget")
        self.assertEqual(r.stop_reason(None, False), "unknown")
        self.assertEqual(r.stop_reason(None, True), "submitted")

    def test_authorization_precedes_any_input_io(self):
        with self.assertRaisesRegex(ValueError, "authorization"):
            r.prepare({"candidate": "p1", "subset": "smoke-5", "authorization": ""})

    def test_holdout_requires_separate_winner_confirmation(self):
        with self.assertRaisesRegex(ValueError, "held-out"):
            r.prepare({"candidate": "p1", "subset": "confirm-20", "gpu_authorized": True,
                       "authorization": "AUTHORIZE FORGEAI GEMMA4 LOCAL EVAL p1 ON confirm-20"})

    def test_watchdog_tracks_detached_descendants_without_pid_reuse(self):
        tracked = {}
        r.track_descendants(10, tracked, {10: (1, "root"), 11: (10, "child"), 12: (11, "grandchild"), 99: (1, "unrelated")})
        self.assertEqual(tracked, {10: "root", 11: "child", 12: "grandchild"})
        # A reused root PID must not adopt unrelated children into our kill set.
        r.track_descendants(10, tracked, {10: (1, "reused"), 20: (10, "unrelated-child"), 12: (1, "grandchild")})
        self.assertNotIn(20, tracked)

    def test_notebook_has_no_submission_or_install_cell(self):
        notebook = json.loads((Path(__file__).parent / "local_eval.ipynb").read_bytes())
        cells = "\n".join("".join(c["source"]) for c in notebook["cells"] if c["cell_type"] == "code")
        self.assertNotIn("pip install", cells)
        self.assertNotIn("kaggle competitions submit", cells)
        self.assertIn('"gpu_authorized": False', cells)
        self.assertTrue(all(c.get("execution_count") is None and not c.get("outputs") for c in notebook["cells"]))

    def test_official_cells_are_exact_starter_source(self):
        root = Path(__file__).parent
        starter = root.parent / "docs/getting-started-gemma-4-developer-agent.ipynb"
        original = json.loads(starter.read_bytes())
        copied = r.official_cells()
        self.assertEqual(copied["starter_sha256"], hashlib.sha256(starter.read_bytes()).hexdigest())
        for index in (2, 8):
            self.assertEqual(copied["cells"][str(index)]["source"], "".join(original["cells"][index]["source"]))

    def test_official_cell_tampering_refused(self):
        from unittest.mock import patch
        root = Path(__file__).parent
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            document = json.loads((root / "official-cells.json").read_bytes())
            document["cells"]["8"]["source"] += "\n# altered\n"
            (target / "official-cells.json").write_text(json.dumps(document))
            (target / "source-pins.json").write_bytes((root / "source-pins.json").read_bytes())
            with patch.object(r, "HERE", target), self.assertRaisesRegex(ValueError, "source changed"):
                r.official_cells()

    def test_environment_install_is_explicit_and_only_official(self):
        root = Path(__file__).parent
        notebook = json.loads((root / "local_eval.ipynb").read_bytes())
        source = "".join(notebook["cells"][1]["source"])
        self.assertIn('"official_environment_authorized": False', source)
        runtime_source = (root / "runtime.py").read_text()
        self.assertNotIn('"pip", "install"', runtime_source)
        self.assertLess(runtime_source.index('"official-starter-cell-2"'), runtime_source.index('"official-starter-cell-8"'))
        self.assertIn('"environment.json"', runtime_source)


class DependencyClassificationTests(unittest.TestCase):
    def test_collection_missing_module_is_not_agent_failure(self):
        outcome = a.verification_outcome(False, "STDOUT:\nERROR collecting tests/test_x.py\nModuleNotFoundError: No module named 'dirty_equals'")
        self.assertIsNone(outcome["resolved"])
        self.assertFalse(outcome["official_resolved"])
        self.assertEqual(outcome["verification_status"], "HARNESS_ENVIRONMENT_ERROR")
        row = dict(record(), **outcome)
        self.assertNotIn("tests_fail", a.categories(row))
        report = a.summarize(meta(), [row])
        self.assertEqual(report["harness_environment_errors"], 1)
        self.assertEqual(report["unresolved"], 0)
        self.assertIsNone(report["pass_rate"])
        self.assertEqual(report["time_fit"]["gate"], "INCONCLUSIVE")

    def test_ordinary_assertions_and_noncollection_imports_not_reclassified(self):
        for output in ("STDOUT:\nAssertionError", "STDOUT:\nModuleNotFoundError: No module named 'foo'", "STDOUT:\nERROR collecting test.py\nSyntaxError"):
            self.assertFalse(a.verification_outcome(False, output)["resolved"])
            self.assertEqual(a.verification_outcome(False, output)["harness_errors"], [])

    def test_summary_reports_task_budget_tokens_and_macro(self):
        rows = [record("a"), dict(record("b", False), stop_reason="call_budget", tokens=42)]
        report = a.summarize(meta(("a", "b")), rows)
        self.assertEqual(report["pass_rate"], 0.5)
        self.assertEqual(report["repo_macro_pass_rate"], 0.5)
        self.assertEqual(report["tool_call_limit_hits"], 1)
        self.assertEqual(report["observed_tokens"], 42)
        self.assertEqual(report["tokens_unknown_tasks"], 1)
        self.assertEqual(len(report["per_task"]), 2)

    def test_retained_log_projection_preserves_historical_bytes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "run.json").write_bytes(a.canonical(meta()))
            raw = a.canonical(record(passed=False)).replace(b"\n", b"") + b"\n"
            (root / "tasks.jsonl").write_bytes(raw)
            logs = root / "official/test_outputs"
            logs.mkdir(parents=True)
            (logs / "a.log").write_text("ERROR collecting test.py\nModuleNotFoundError: No module named 'dirty_equals'")
            _, rows = a.read_run(root)
            self.assertIsNone(rows[0]["resolved"])
            self.assertEqual((root / "tasks.jsonl").read_bytes(), raw)


if __name__ == "__main__":
    unittest.main()
