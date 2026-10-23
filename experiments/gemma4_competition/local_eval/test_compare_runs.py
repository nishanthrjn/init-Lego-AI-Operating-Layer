import unittest
from compare_runs import table
from test_local_eval import meta, record


class ComparisonTests(unittest.TestCase):
    def test_union_exclusion_and_missing_are_distinct(self):
        runs = {"P1": (meta(("a", "b", "c")), [record("a"), record("b")]),
                "P1b": (meta(("a",)), [record("a", False)])}
        output = table(runs, {"a": {"class": "VERIFIABLE"}, "b": {"class": "UNSOUND"}, "c": {"class": "VERIFIABLE"}})
        self.assertIn("| a | VERIFIABLE | RESOLVED | UNRESOLVED |", output)
        self.assertIn("| b | UNSOUND | EXCLUDED | NOT_PLANNED |", output)
        self.assertIn("| c | VERIFIABLE | MISSING | NOT_PLANNED |", output)

    def test_unknown_and_provenance(self):
        row = dict(record(), completed_result=False, attempt_id="attempt1")
        output = table({"P1": (meta(), [row])}, {"a": {"class": "VERIFIABLE"}})
        self.assertIn("UNKNOWN (attempt attempt1)", output)

    def test_mismatch_and_duplicate_refused(self):
        with self.assertRaises(ValueError):
            table({"A": (meta(), [record()]), "B": (dict(meta(), runtime_pins={}), [record()])}, {})
        with self.assertRaises(ValueError):
            table({"A": (meta(), [record(), record()])}, {})
