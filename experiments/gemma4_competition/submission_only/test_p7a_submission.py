"""Confirmation gate regression tests; no compiler/model execution."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import qualify_p7a as q
import generate_self_contained as generator


def evidence():
    source = hashlib.sha256((q.HERE.parent / 'local_eval/source-pins.json').read_bytes()).hexdigest()
    doc = {'p7_selection': {'selected_candidate': 'p7a'},
           'p7a_confirmation_decision': {'status': 'PASSED', 'same_config_verified': True}}
    for attempt, solved in ((1, 11), (2, 10)):
        doc[f'p7a_attempt{attempt}'] = {
            'candidate': 'p7a', 'subset': 'dev-16v', 'attempt': attempt,
            'state': 'COMPLETED', 'verifiable': 16, 'resolved': solved, 'empty_patches': 3,
            'bootstrap_upper95_hours': 11, 'bootstrap_method': 'REPO_ANALYSIS_116_TASK_BOOTSTRAP_V1',
            'retained_path': f'external/attempt{attempt}', 'zip_sha256': q.ZIP_SHA256,
            'manifest_sha256': q.MANIFEST_SHA256, 'model': 'gemma-4-31b-it-qat-w4a16-ct',
            'source_pins_sha256': source}
    return doc


class P7aSubmissionTests(unittest.TestCase):
    def check(self, doc):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'evidence.json'
            raw = json.dumps(doc).encode()
            path.write_bytes(raw)
            result = q.require_confirmation_gate(path)
            self.assertEqual(result['development_evidence_sha256'], hashlib.sha256(raw).hexdigest())
            return result

    def test_inclusive_thresholds_and_mean(self):
        self.assertEqual(self.check(evidence())['development_gate'], 'PASSED')

    def test_status_label_cannot_replace_metrics_and_identity(self):
        for attempt in (1, 2):
            for key, value in (('empty_patches', 4), ('resolved', True), ('resolved', None),
                               ('bootstrap_upper95_hours', 11.01), ('bootstrap_upper95_hours', float('nan')),
                               ('bootstrap_method', 'MAINTAINER_16_TASK_RESAMPLING_20000_SEED0'),
                               ('state', 'RUNNING'), ('zip_sha256', '0' * 64),
                               ('manifest_sha256', '0' * 64), ('source_pins_sha256', None),
                               ('model', 'gemma-4-e4b-it-qat-w4a16-ct'), ('retained_path', None)):
                doc = evidence()
                doc[f'p7a_attempt{attempt}'][key] = value
                with self.subTest(attempt=attempt, key=key), self.assertRaises(ValueError):
                    self.check(doc)
        for attempt, value in ((1, 10), (2, 9)):
            doc = evidence()
            doc[f'p7a_attempt{attempt}']['resolved'] = value
            with self.assertRaises(ValueError):
                self.check(doc)

    def test_pending_missing_and_same_run_confirmation_blocked(self):
        for field in ('p7a_attempt2', 'p7a_confirmation_decision'):
            doc = evidence()
            del doc[field]
            with self.assertRaises(ValueError):
                self.check(doc)
        doc = evidence()
        doc['p7a_attempt2']['retained_path'] = doc['p7a_attempt1']['retained_path']
        with self.assertRaises(ValueError):
            self.check(doc)
        doc = evidence()
        doc['p7a_confirmation_decision']['same_config_verified'] = False
        with self.assertRaises(ValueError):
            self.check(doc)

    def test_guard_precedes_submission_writes(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / 'external.ipynb'
            argv = ['qualify_p7a.py', '--receipt', 'missing', '--results', 'missing', '--notebook', str(target)]
            with patch.object(sys, 'argv', argv), patch.object(q, 'require_confirmation_gate', side_effect=ValueError('blocked')):
                with self.assertRaisesRegex(ValueError, 'blocked'):
                    q.main()
            self.assertFalse(target.exists())

    def test_shared_generator_cannot_bypass_guard_or_use_stale_evidence(self):
        pins = {'reconciled': True, 'm2_result_understood': True}
        with patch.object(q, 'require_confirmation_gate', side_effect=ValueError('blocked')):
            with self.assertRaisesRegex(ValueError, 'blocked'):
                generator.build_notebook('p7a', pins, b'{}', b'payload')
        with patch.object(q, 'require_confirmation_gate', return_value={'development_gate': 'PASSED', 'development_evidence_sha256': 'a' * 64}):
            with self.assertRaisesRegex(ValueError, 'development evidence'):
                generator.build_notebook('p7a', pins, b'{}', b'payload')

    def test_generator_requires_evaluated_zip_even_with_passing_development(self):
        development = {'development_gate': 'PASSED', 'development_evidence_sha256': 'a' * 64}
        pins = dict(development, reconciled=True, m2_result_understood=True,
                    zip_sha256='0' * 64, zip_size=7359)
        with patch.object(q, 'require_confirmation_gate', return_value=development):
            with self.assertRaisesRegex(ValueError, 'evaluated experimental identity'):
                generator.build_notebook('p7a', pins, b'{}', b'payload')

    def test_submission_pins_are_placeholders(self):
        pins = generator.load_pins('p7a')
        if not pins['reconciled']:
            self.assertEqual(pins['development_gate'], 'PENDING_CONFIRMATION')
        else:
            self.assertEqual(pins['development_gate'], 'PASSED')
            self.assertEqual(len(pins['development_evidence_sha256']), 64)


if __name__ == '__main__':
    unittest.main()
