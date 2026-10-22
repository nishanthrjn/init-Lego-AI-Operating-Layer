"""Independent fixtures; no official packages, models or verification runs."""
import hashlib
import asyncio
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import fidelity as f
import controls as c


class FidelityTests(unittest.TestCase):
    def test_notebook_diagnostics_routes_to_import_origin_worker(self):
        config = {}
        entry = f.notebook_mode(config, "diagnostics", f.AUTH.format(operation="DIAGNOSTIC"))
        self.assertEqual(entry, "fidelity.py")
        self.assertEqual(config["operation"], "DIAGNOSTIC")
        # Exercise the actual worker with independent official-module fixtures.
        import sys
        import types
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            snapshot = root / "snapshot"
            snapshot.touch()
            task = SimpleNamespace(repo="psf/requests", patch="gold", test_patch="test")
            class SubprocessManager:
                def __init__(self, **kwargs): pass
                def exec(self, *args):
                    return SimpleNamespace(exit_code=0, stdout="ORIGIN=/workspace/src/requests/__init__.py\n")
                def stop(self, *args): pass
                def cleanup_all(self): pass
            async def verify(manager, *args, **kwargs):
                manager.stop("fixture")
                return SimpleNamespace(resolved=False, test_output="AssertionError", test_exit_code=1)
            modules = {}
            for name, attributes in {
                "swegemma.models": {"load_tasks": lambda _: [task]},
                "swegemma.config": {"EvalConfig": lambda **kw: kw},
                "swegemma.deduplication": {"resolve_task_snapshot_paths": lambda *a: (snapshot, None, None)},
                "swegemma.harness.verification": {"verify_task": verify},
                "swegemma.sandbox": {"SubprocessManager": SubprocessManager},
            }.items():
                modules[name] = types.ModuleType(name)
                modules[name].__dict__.update(attributes)
            task.instance_id = "requests_fixture"
            config.update(controls="fixture", fidelity_output="/kaggle/working/fixture")
            captured = []
            with patch.dict(sys.modules, modules), patch.dict("os.environ", {"TMPDIR": directory}), \
                    patch.object(c, "preflight", return_value=(root, [{"task_id": task.instance_id, "repo": task.repo}], "pin")), \
                    patch.object(c, "sha", return_value="inventory"), \
                    patch.object(f, "frozen_controls", return_value={"official_tasks_sha256": "inventory", "tasks": [{"task_id": task.instance_id, "class": "UNSOUND"}]}), \
                    patch.object(Path, "resolve", lambda self: self), patch.object(Path, "is_dir", return_value=True), \
                    patch.object(c, "write_json", side_effect=lambda p, value: captured.append(value)):
                c.worker(config, task.instance_id, config["operation"], root / "result.json")
            self.assertEqual(captured[0]["import_origin"]["status"], "OBSERVED")
            self.assertEqual(captured[0]["import_origin"]["file"], "/workspace/src/requests/__init__.py")

    def test_mode_authorizations_are_not_interchangeable(self):
        for mode in ("diagnostics", "reverify", "invalid"):
            with self.assertRaises(ValueError):
                f.notebook_mode({}, mode, c.AUTHORIZATION)

    def test_gpu_notebook_output_subset_guard(self):
        notebook = json.loads((Path(__file__).parent / "local_eval.ipynb").read_bytes())
        source = "".join("".join(cell["source"]) for cell in notebook["cells"] if cell["cell_type"] == "code")
        start = source.index("if CONFIG['subset'] not in Path(CONFIG['output']).name:")
        guard = "\n".join(source[start:].splitlines()[:2])
        for output, valid in (("/tmp/p1-smoke-5-1", True), ("/tmp/p1-dev-30-1", False)):
            namespace = {"CONFIG": {"subset": "smoke-5", "output": output}, "Path": Path}
            if valid:
                exec(guard, namespace)
            else:
                with self.assertRaises(RuntimeError):
                    exec(guard, namespace)

    def test_reverification_uses_retained_patch_not_gold(self):
        seen = []
        async def verifier(*args, **kwargs):
            seen.append(kwargs["agent_patch"])
            return SimpleNamespace(resolved=True, test_output="", test_exit_code=0)
        task = SimpleNamespace(patch="GOLD_SECRET", test_patch="TEST_SECRET", repo="tiangolo/fastapi")
        result = asyncio.run(c.verify_one(task, "EMPTY", verifier, None, None,
                                          (None, None, None), agent_patch="RETAINED_AGENT"))
        self.assertEqual(seen, ["RETAINED_AGENT"])
        self.assertTrue(result["passed"])
        self.assertNotIn("SECRET", str(result))

    def test_gold_diagnostic_projection_does_not_retain_patch(self):
        async def verifier(*args, **kwargs):
            return SimpleNamespace(resolved=False, test_output="GOLD_SECRET\nImportError: TEST_SECRET", test_exit_code=2)
        task = SimpleNamespace(patch="GOLD_SECRET", test_patch="TEST_SECRET", repo="psf/requests")
        diagnostic = {}
        asyncio.run(c.verify_one(task, "GOLD", verifier, None, None,
                                 (None, None, None), diagnostic=diagnostic))
        self.assertNotIn("SECRET", str(diagnostic))

    def test_frozen_controls_and_subset_counts(self):
        root = Path(__file__).parent
        controls = f.frozen_controls(root / "evidence/controls-05706c6a.json")
        subsets = json.loads((root / "subsets.json").read_bytes())
        for name, expected in (("dev-30", 16), ("confirm-20", 8)):
            ids = {row["task_id"] for row in subsets[name]}
            self.assertEqual(sum(r["class"] == "VERIFIABLE" and r["task_id"] in ids for r in controls["tasks"]), expected)

    def test_tail_no_reference_or_arbitrary_payload(self):
        tail = f.safe_tail("secret source\n+gold secret\nImportError: private payload\n", "+gold secret", "secret source")
        self.assertEqual(len(tail), 3)
        self.assertNotIn("secret", str(tail))
        self.assertNotIn("private payload", str(tail))
        self.assertEqual(tail[-1], "ImportError")
        self.assertEqual(len(f.safe_tail("x\n" * 80, "", "")), 60)

    def test_import_probe_before_cleanup_preserves_manager_type(self):
        events = []
        class Manager:
            def exec(self, sandbox, command):
                events.append("probe")
                self.command = command
                return SimpleNamespace(exit_code=0, stdout="ORIGIN=/workspace/src/requests/__init__.py\n")
            def stop(self, sandbox):
                events.append("stop")
        manager = Manager()
        original_type = type(manager)
        row = f.observe_import(manager, "psf/requests")
        manager.stop("fixture")
        self.assertEqual(events, ["probe", "stop"])
        self.assertIs(type(manager), original_type)
        self.assertEqual(row["file"], "/workspace/src/requests/__init__.py")

    def test_patch_identity_and_escape_refusal(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "agent.patch"
            path.write_bytes(b"independent fixture")
            config = {"previous_run": directory, "patches": {"task": {
                "path": "agent.patch", "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}}}
            self.assertEqual(f.patch_input(config, "task"), "independent fixture")
            config["patches"]["task"]["sha256"] = "0" * 64
            with self.assertRaises(ValueError):
                f.patch_input(config, "task")
            config["patches"]["task"]["path"] = "../escape.patch"
            with self.assertRaises(ValueError):
                f.patch_input(config, "task")

    def test_historical_control_hash_mismatch(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "controls.json"
            path.write_text("{}")
            with self.assertRaisesRegex(ValueError, "hash mismatch"):
                f.frozen_controls(path)


if __name__ == "__main__":
    unittest.main()
