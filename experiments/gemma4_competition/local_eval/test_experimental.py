import json
from pathlib import Path
import sys
import tempfile
import unittest
import analysis as a
import experimental as e


class ExperimentalTests(unittest.TestCase):
    def test_static_ablation_scope(self):
        b, c = e.static_files("p1b"), e.static_files("p1c")
        self.assertEqual({k for k in b if b[k] != c[k]}, {"configs/sampling.yaml"})
        self.assertIn(b"thinking_budget: 2048", c["configs/sampling.yaml"])
        self.assertIn(b"max_output_tokens: 8192", c["configs/sampling.yaml"])

    def test_package_identity_and_no_submission_qualification(self):
        sys.path.insert(0, str(e.HERE.parent))
        from portable_m2 import zip_bytes, inspect_zip
        data = e.static_files("p1b")
        blob = zip_bytes(data)
        self.assertEqual(blob, zip_bytes(data))
        inspect_zip(blob, data)
        with tempfile.TemporaryDirectory() as directory:
            package, manifest = Path(directory) / "p.bin", Path(directory) / "m.json"
            package.write_bytes(blob)
            m = {"state": e.STATE, "candidate": "p1b", "zip_sha256": e.digest(blob), "zip_size": len(blob)}
            manifest.write_text(json.dumps(m))
            config = {"candidate": "p1b", "subset": "dev-16v", "experimental_authorized": True,
                      "manifest": str(manifest), "package": str(package), "manifest_sha256": a.sha(manifest), "zip_sha256": a.sha(package)}
            self.assertEqual(e.verify(config)["state"], e.STATE)
            with self.assertRaises(ValueError):
                a.verify_package(package, manifest, a.sha(manifest), "no receipt")
            for change in ({"experimental_authorized": False}, {"subset": "confirm-20"}, {"zip_sha256": "0" * 64}, {"manifest_sha256": "0" * 64}):
                with self.assertRaises(ValueError):
                    e.verify(dict(config, **change))

    def test_bootstrap_seed_and_constant_arithmetic(self):
        first = a.projection([120] * 16, 100, True)
        self.assertEqual(first, a.projection([120] * 16, 100, True))
        self.assertAlmostEqual(first["bootstrap_upper95_hours"], (116 * 120 + 100) / 3600)
        self.assertEqual(first["gate"], "PASS")
        self.assertEqual(a.projection([400] * 16, 100, True)["gate"], "FAIL")

    def test_p95_informational_not_gate(self):
        result = a.projection([100] * 18 + [400] * 2, 0, True)
        self.assertGreater(result["p95_hours"], 11)
        self.assertEqual(result["gate"], "PASS")
