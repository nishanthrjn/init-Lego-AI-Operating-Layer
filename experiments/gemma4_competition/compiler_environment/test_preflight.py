"""Focused synthetic metadata controls. Maintainer execution only."""

import base64
import hashlib
import importlib.util
from pathlib import Path
import tempfile
import unittest
import zipfile

from packaging.utils import parse_wheel_filename


spec = importlib.util.spec_from_file_location("compiler_preflight", Path(__file__).with_name("preflight.py"))
assert spec is not None and spec.loader is not None
preflight = importlib.util.module_from_spec(spec)
spec.loader.exec_module(preflight)


def package(version="1.0", dependencies=(), python=">=3.12"):
    return {"version": version, "requires_dist": list(dependencies), "requires_python": python}


class MetadataContracts(unittest.TestCase):
    def test_missing_metadata_prevents_complete_closure(self):
        result = preflight.closure({"root": package(dependencies=["missing>=2"])}, ["root"], preflight.TARGET)
        self.assertFalse(result["closure_complete"])
        self.assertEqual(result["reachable"], ["missing", "root"])
        self.assertEqual(result["issues"][0]["requirements"], ["missing>=2"])

    def test_required_transitive_extras_are_not_discarded(self):
        available = {"root": package(dependencies=["auth[requests,pyopenssl]"]),
                     "auth": package(dependencies=["transport; extra == 'requests'",
                                                   "crypto; extra == 'pyopenssl'",
                                                   "dev-only; extra == 'dev'"]),
                     "transport": package(), "crypto": package()}
        result = preflight.closure(available, ["root"], preflight.TARGET)
        self.assertTrue(result["closure_complete"])
        self.assertEqual(result["issues"], [])
        self.assertNotIn("dev-only", result["reachable"])
        self.assertIn("crypto", result["reachable"])

    def test_repeated_constraints_all_checked(self):
        available = {"a": package(dependencies=["c>=1"]), "b": package(dependencies=["c<1"]), "c": package()}
        result = preflight.closure(available, ["a", "b"], preflight.TARGET)
        self.assertEqual(result["issues"][0]["kind"], "SUPPLIED_VERSION_CONSTRAINT_MISMATCH")
        self.assertEqual(result["issues"][0]["parent"], "b")

    def test_target_marker_and_python_boundary(self):
        available = {"root": package(dependencies=["win; sys_platform == 'win32'",
                                                   "linux; sys_platform == 'linux'"]),
                     "win": package(python=">=3.13")}
        result = preflight.closure(available, ["root"], preflight.TARGET)
        self.assertNotIn("linux", result["reachable"])
        self.assertEqual(result["issues"][0]["kind"], "REQUIRES_PYTHON_MISMATCH")

    def test_linux_abi3_not_windows_compatible(self):
        linux = parse_wheel_filename("example-1.0-cp39-abi3-manylinux_2_17_x86_64.whl")[3]
        windows = parse_wheel_filename("example-1.0-cp39-abi3-win_amd64.whl")[3]
        self.assertFalse(linux.intersection(preflight.target_tags()))
        self.assertTrue(windows.intersection(preflight.target_tags()))

    def test_direct_url_requires_review_without_fetch(self):
        result = preflight.closure({}, ["example @ https://invalid.example/test.whl"], preflight.TARGET)
        self.assertIn("DIRECT_URL_REQUIRES_REVIEW", [x["kind"] for x in result["issues"]])

    def test_record_valid_and_tampered_bytes(self):
        body = b"synthetic bytes"
        expected = base64.urlsafe_b64encode(hashlib.sha256(body).digest()).rstrip(b"=").decode()
        with tempfile.TemporaryDirectory() as temporary:
            for content in (body, b"tampered bytes"):
                path = Path(temporary) / "fixture.whl"
                with zipfile.ZipFile(path, "w") as archive:
                    archive.writestr("example.py", content)
                    archive.writestr("example-1.0.dist-info/RECORD",
                                     f"example.py,sha256={expected},{len(body)}\nexample-1.0.dist-info/RECORD,,\n")
                if content == body:
                    preflight.verify_record(path)
                else:
                    with self.assertRaises(ValueError):
                        preflight.verify_record(path)


if __name__ == "__main__":
    unittest.main()
