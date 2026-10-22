"""Independent fixtures; no official packages, models or verification runs."""
import hashlib
import asyncio
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

import fidelity as f
import controls as c


class FidelityTests(unittest.TestCase):
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
