"""Offline requirements controls; execution belongs to the maintainer."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import analysis
import experimental
from compare_runs import agreement_section
from test_local_eval import meta, record


def replicate_meta(attempt):
    return dict(meta(("a", "b")), candidate="p3", package_sha256="1" * 64,
                manifest_sha256="2" * 64, package_mode="EXPERIMENTAL_UNQUALIFIED",
                evaluation_config={"max_time_minutes": 6}, model="model", model_input="/model/2",
                official_cell_sha256={"2": "3" * 64, "8": "4" * 64}, python="3.12.13",
                torch_version="2.10", cuda_version="12.8", gpu_names=["L4"] * 4,
                concurrency=1, wall_guard_seconds=7200, attempt_id=attempt)


class P4ReplicateTests(unittest.TestCase):
    def test_p4_exact_time_only_delta(self):
        p3, p4 = experimental.static_files("p3"), experimental.static_files("p4")
        self.assertEqual({k for k in p3 if p3[k] != p4[k]}, {"eval_config.yaml"})
        self.assertEqual(p4["eval_config.yaml"], p3["eval_config.yaml"].replace(
            b"max_time_minutes: 6\n", b"max_time_minutes: 7\n"))

    def test_p4_scope_refuses_other_budget_even_with_updated_hash(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "local_eval").mkdir()
            pins = json.loads((experimental.HERE / "experimental-pins.json").read_bytes())
            for name in pins:
                for member in experimental.MEMBERS:
                    data = (experimental.HERE.parent / "candidates" / name / member).read_bytes()
                    if name == "p4" and member == "eval_config.yaml":
                        data = data.replace(b"max_turns: 80", b"max_turns: 81")
                        pins[name][member] = experimental.digest(data)
                    target = root / "candidates" / name / member
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(data)
            (root / "local_eval/experimental-pins.json").write_text(json.dumps(pins))
            with patch.object(experimental, "HERE", root / "local_eval"):
                with self.assertRaisesRegex(ValueError, "time cap"):
                    experimental.static_files("p4")

    def setUp(self):
        self.first, self.second = replicate_meta("attempt1"), replicate_meta("attempt2")
        self.a = [record("a", True), record("b", False)]
        self.b = [record("a", False), record("b", True)]
        self.controls = {tid: {"class": "VERIFIABLE"} for tid in ("a", "b")}

    def test_p4_archive_verified_only_as_experimental(self):
        import sys
        sys.path.insert(0, str(experimental.HERE.parent))
        from portable_m2 import zip_bytes
        blob = zip_bytes(experimental.static_files("p4"))
        with tempfile.TemporaryDirectory() as directory:
            package, manifest = Path(directory) / "p.bin", Path(directory) / "m.json"
            package.write_bytes(blob)
            manifest.write_text(json.dumps({"state": experimental.STATE, "candidate": "p4",
                                           "zip_sha256": experimental.digest(blob), "zip_size": len(blob)}))
            config = {"candidate": "p4", "subset": "dev-16v", "experimental_authorized": True,
                      "manifest": str(manifest), "package": str(package),
                      "manifest_sha256": analysis.sha(manifest), "zip_sha256": analysis.sha(package)}
            self.assertEqual(experimental.verify(config)["state"], "EXPERIMENTAL_UNQUALIFIED")
            with self.assertRaises(ValueError):
                experimental.verify(dict(config, subset="confirm-20"))
            with self.assertRaises(ValueError):
                analysis.verify_package(package, manifest, analysis.sha(manifest), "no receipt")

    def agreement(self):
        return analysis.same_config_agreement(self.first, self.a, self.second, self.b, self.controls)

    def test_equal_totals_still_have_two_flips(self):
        result = self.agreement()
        self.assertEqual(result["a_passed"], result["b_passed"])
        self.assertEqual(result["flip_count"], 2)
        self.assertEqual(result["agreement_rate"], 0)
        self.assertEqual([r["task_id"] for r in result["per_task"] if r["flipped"]], ["a", "b"])
        output = agreement_section({"P3a": (self.first, self.a), "P3b": (self.second, self.b)},
                                   self.controls, "P3a=P3b")
        self.assertIn("noise floor = 2 task flips", output)

    def test_full_agreement(self):
        self.b = copy.deepcopy(self.a)
        self.assertEqual(self.agreement()["flip_count"], 0)
        self.assertEqual(self.agreement()["agreement_rate"], 1)

    def test_changed_or_missing_identity_refused(self):
        for key in ("package_sha256", "evaluation_config", "runtime_pins", "task_ids",
                    "manifest_sha256", "model", "wall_guard_seconds"):
            with self.subTest(key=key):
                self.second = replicate_meta("attempt2")
                self.second[key] = "different"
                with self.assertRaises(ValueError):
                    self.agreement()
        self.second = replicate_meta("attempt2")
        del self.second["evaluation_config"]
        with self.assertRaises(ValueError):
            self.agreement()

    def test_incomplete_resumed_same_attempt_and_unknown_refused(self):
        for changes in ({"completion_state": "INCOMPLETE"}, {"attempt_id": "attempt1"},
                        {"resume_manifest_sha256": "f" * 64}, {"inherited_task_ids": ["a"]}):
            self.second = dict(replicate_meta("attempt2"), **changes)
            with self.assertRaises(ValueError):
                self.agreement()
        self.second = replicate_meta("attempt2")
        for rows in ([record("a"), record("a")], [record("a")],
                     [record("a", None), record("b")],
                     [dict(record("a"), completed_result=False), record("b")],
                     [dict(record("a"), harness_errors=["ENV_ERROR"]), record("b")]):
            self.b = rows
            with self.assertRaises(ValueError):
                self.agreement()


if __name__ == "__main__":
    unittest.main()
