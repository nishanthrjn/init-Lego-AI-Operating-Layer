"""X22 byte identity and private-use controls; no external download required."""
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

import experimental as e
import x22


class X22Tests(unittest.TestCase):
    def test_member_pins_and_independent_configs(self):
        data = e.static_files("x22")
        source = json.loads((e.HERE.parent / "results/x22-reference-provenance.json").read_bytes())
        self.assertEqual({k: e.digest(v) for k, v in data.items()},
                         {k: v["sha256"] for k, v in source["observed_members"].items()})
        self.assertEqual(data["configs/sampling.yaml"], e.static_files("p10")["configs/sampling.yaml"])
        configs = [json.loads((e.HERE / f"configs/x22-dev16v-attempt{i}.json").read_bytes()) for i in (1, 2)]
        self.assertEqual({k for k in configs[0] if configs[0][k] != configs[1][k]}, {"output"})
        for config in configs:
            self.assertEqual(config["reuse_scope"], x22.REUSE_SCOPE)
            self.assertEqual(config["model_variant"], "gemma-4-31b-it-qat-w4a16-ct")
            self.assertFalse(config["experimental_authorized"])
            self.assertFalse(config["gpu_authorized"])

    def test_preserves_original_bytes_and_refuses_tampering(self):
        data = {"a": b"fixture"}
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("a", data["a"])
        raw = stream.getvalue()
        pins = {"a": e.digest(data["a"])}
        with patch.object(x22, "SOURCE_SHA256", e.digest(raw)), patch.object(x22, "SOURCE_SIZE", len(raw)):
            with tempfile.TemporaryDirectory() as folder:
                outer = Path(folder) / "outer.zip"
                with zipfile.ZipFile(outer, "w") as archive:
                    archive.writestr("submission.zip", raw)
                self.assertEqual(x22.read_source_archive(outer, pins), raw)
            with self.assertRaisesRegex(ValueError, "identity"):
                x22.verify_source_zip(raw[:-1] + bytes([raw[-1] ^ 1]), pins)
            with self.assertRaisesRegex(ValueError, "member mismatch"):
                x22.verify_source_zip(raw, {"a": "0" * 64})
            with self.assertRaisesRegex(ValueError, "four pinned"):
                x22.verify_source_zip(raw, {"a": pins["a"], "extra": "0" * 64})

    def test_actual_identity_rejects_repacking(self):
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, "w") as archive:
            for name, raw in e.static_files("x22").items():
                archive.writestr(name, raw)
        with self.assertRaisesRegex(ValueError, "identity"):
            x22.verify_source_zip(stream.getvalue(), {})

    def test_runtime_refuses_missing_private_scope_or_submission_authority(self):
        from test_two_track import TwoTrackContractTests
        template = json.loads((e.HERE / "configs/x22-dev16v-attempt1.json").read_bytes())
        with tempfile.TemporaryDirectory() as folder:
            config = TwoTrackContractTests().fixture(folder, "x22", "dev-16v")
            for key in ("candidate", "model_variant", "model_path", "vllm_extra_args", "reuse_scope"):
                config[key] = template[key]
            manifest_path = Path(config["manifest"])
            manifest = json.loads(manifest_path.read_bytes())
            manifest.update(reuse_scope=x22.REUSE_SCOPE, submission_authorized=False)
            manifest_path.write_text(json.dumps(manifest))
            config["manifest_sha256"] = e.digest(manifest_path.read_bytes())
            with patch.object(x22, "verify_source_zip"):
                self.assertEqual(e.verify(config)["candidate"], "x22")
                with self.assertRaisesRegex(ValueError, "private local"):
                    e.verify(dict(config, reuse_scope="PUBLIC"))
                with self.assertRaises(ValueError):
                    e.verify(dict(config, model_variant="gemma-4-e4b-it-qat-w4a16-ct"))
                manifest["submission_authorized"] = True
                manifest_path.write_text(json.dumps(manifest))
                config["manifest_sha256"] = e.digest(manifest_path.read_bytes())
                with self.assertRaisesRegex(ValueError, "private local"):
                    e.verify(config)

    def test_submission_generator_refuses_even_claimed_qualified_pins(self):
        path = e.HERE.parent / "submission_only/generate_self_contained.py"
        spec = importlib.util.spec_from_file_location("x22_generator_test", path)
        generator = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(generator)
        with self.assertRaisesRegex(ValueError, "private local evaluation only"):
            generator.build_notebook("x22", {"reconciled": True, "m2_result_understood": True}, b"{}", b"")


if __name__ == "__main__":
    unittest.main()
