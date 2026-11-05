"""P10 time-cap-only experiment controls; maintainer execution only."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import experimental as e
import test_two_track


class P10Tests(unittest.TestCase):
    def test_only_time_cap_changes_from_p5(self):
        before, after = e.static_files("p5"), e.static_files("p10")
        self.assertEqual({k for k in before if before[k] != after[k]}, {"eval_config.yaml"})
        self.assertEqual(after["eval_config.yaml"], before["eval_config.yaml"].replace(
            b"max_time_minutes: 6\n", b"max_time_minutes: 8\n"))

    def test_repinning_cannot_hide_extra_budget_change(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "local_eval").mkdir()
            pins = json.loads((e.HERE / "experimental-pins.json").read_bytes())
            for name in pins:
                for member in e.MEMBERS:
                    blob = (e.HERE.parent / "candidates" / name / member).read_bytes()
                    if name == "p10" and member == "eval_config.yaml":
                        blob = blob.replace(b"max_tool_calls: 28", b"max_tool_calls: 40")
                        pins[name][member] = e.digest(blob)
                    path = root / "candidates" / name / member
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(blob)
            (root / "local_eval/experimental-pins.json").write_text(json.dumps(pins))
            with patch.object(e, "HERE", root / "local_eval"):
                with self.assertRaisesRegex(ValueError, "only evaluation change"):
                    e.static_files("p10")

    def test_paper_archive_path_is_valid_json(self):
        paper = json.loads((e.HERE.parent / "results/paper-evidence.json").read_bytes())
        claim = next(c for c in paper["claims"] if c["id"] == "p9_disk_state_and_512_thinking_final")
        self.assertEqual(claim["retained_archive"],
                         r"C:\Work\Gemma4Localtest\archive\gemma4-all-local-eval-runs.zip")

    def test_config_authority_and_model_contract(self):
        template = json.loads((e.HERE / "configs/p10-dev16v-attempt1.json").read_bytes())
        self.assertEqual(template["candidate"], "p10")
        self.assertTrue(template["output"].endswith("p10-dev-16v-attempt1"))
        for flag in ("experimental_authorized", "gpu_authorized", "official_environment_authorized"):
            self.assertFalse(template[flag])
        self.assertEqual(template["resume_previous"], "")
        with tempfile.TemporaryDirectory() as folder:
            config = test_two_track.TwoTrackContractTests().fixture(folder, "p10", "dev-16v")
            for key in ("candidate", "model_variant", "model_path", "vllm_extra_args"):
                config[key] = template[key]
            self.assertEqual(e.verify(config)["candidate"], "p10")
            for changes in ({"candidate": "p5"}, {"subset": "smoke-5"}, {"experimental_authorized": False},
                            {"model_variant": "gemma-4-e4b-it-qat-w4a16-ct"},
                            {"zip_sha256": "0" * 64}):
                with self.subTest(changes=changes), self.assertRaises(ValueError):
                    e.verify(dict(config, **changes))


if __name__ == "__main__":
    unittest.main()
