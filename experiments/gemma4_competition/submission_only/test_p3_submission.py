"""Only reconciled P3 pins may produce a submission notebook."""
import ast
import unittest

from qualify_p3 import replace_entry
from generate_self_contained import build_notebook


class P3SubmissionTests(unittest.TestCase):
    def test_pin_update_preserves_other_candidates(self):
        source = 'CANDIDATE_PINS = {"m2": {"hash": "old"}, "b2": {}, "p1": {}, "p3": {"reconciled": False}}\n'
        updated = replace_entry(source, {"reconciled": True})
        before = ast.literal_eval(ast.parse(source).body[0].value)
        after = ast.literal_eval(ast.parse(updated).body[0].value)
        for name in ("m2", "b2", "p1"):
            self.assertEqual(before[name], after[name])
        self.assertTrue(after["p3"]["reconciled"])

    def test_pending_pins_refuse_generation(self):
        with self.assertRaises(ValueError):
            build_notebook("p3", {"reconciled": False}, b"{}", b"unqualified")


if __name__ == "__main__":
    unittest.main()
