"""Common baseline must be explicit, committed, clean and receipt-matched."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from experiments.gemma4_competition import qualification_pair as pair


class PairBaselineTests(unittest.TestCase):
    def fake_git(self, *args):
        if args[0] == "branch":
            return b"br-ForgeAI-Gemma4\n"
        if args[0] == "rev-parse":
            return b"a" * 40 + b"\n"
        return b""

    def test_clean_commit_and_matching_receipt(self):
        with patch.object(pair, "BASE", "a" * 40), patch.object(pair, "git", side_effect=self.fake_git):
            self.assertEqual(pair.require_frozen(), "a" * 40)
            with tempfile.TemporaryDirectory() as folder:
                receipt = Path(folder) / "receipt.json"
                receipt.write_text(json.dumps({"baseline": "a" * 40, "git_head": "a" * 40}))
                self.assertEqual(pair.require_frozen(receipt), "a" * 40)
                receipt.write_text(json.dumps({"baseline": "b" * 40, "git_head": "a" * 40}))
                with self.assertRaisesRegex(ValueError, "Receipt"):
                    pair.require_frozen(receipt)

    def test_missing_or_changed_baseline_and_dirty_tree_refused(self):
        with patch.object(pair, "BASE", ""), self.assertRaises(ValueError):
            pair.require_frozen()
        with patch.object(pair, "BASE", "b" * 40), patch.object(pair, "git", side_effect=self.fake_git):
            with self.assertRaisesRegex(ValueError, "same committed HEAD"):
                pair.require_frozen()
        def dirty(*args):
            return b" M tracked.py\n?? untracked.txt\n" if args[0] == "status" else self.fake_git(*args)
        with patch.object(pair, "BASE", "a" * 40), patch.object(pair, "git", side_effect=dirty):
            with self.assertRaisesRegex(ValueError, "clean"):
                pair.require_frozen()


if __name__ == "__main__":
    unittest.main()
