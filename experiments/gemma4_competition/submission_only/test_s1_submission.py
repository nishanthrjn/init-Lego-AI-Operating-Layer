"""S1 operational gate and shared notebook preparation controls."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import qualify_s1 as q
import generate_self_contained as generator


def fixtures():
    return ({'s1_dev16v_attempt1': {
        'candidate': 's1', 'subset': 'dev-16v', 'state': 'COMPLETED', 'tasks': 16,
        'operational_gate': 'PASSED_MAINTAINER_REPORTED', 'zip_sha256': q.ZIP_SHA256,
        'manifest_sha256': q.MANIFEST_SHA256, 'model_variant': q.MODEL,
        'harness_errors': 0, 'all_tool_attempted': 100, 'all_tool_rejected': 5,
        'tool_argument_rejection_definition': 'mandatory input parameters are not present',
        'bootstrap_upper95_hours': 10.5}, 's2_dev16v_attempt1': {'gate': 'FAILED'}},
        {'s1_local_selection': {'candidate': 's1', 'purpose': 'E4B_BONUS_ENTRY'}})


class S1SubmissionTests(unittest.TestCase):
    def check(self, doc, registry):
        with tempfile.TemporaryDirectory() as directory:
            path, submissions = Path(directory) / 'evidence.json', Path(directory) / 'submissions.json'
            path.write_text(json.dumps(doc))
            submissions.write_text(json.dumps(registry))
            result = q.require_qualification_gate(path, submissions)
            self.assertEqual(result['development_evidence_sha256'], hashlib.sha256(path.read_bytes()).hexdigest())
            self.assertEqual(result['selection_evidence_sha256'], hashlib.sha256(submissions.read_bytes()).hexdigest())
            return result

    def test_inclusive_operational_thresholds_and_purpose(self):
        pins = self.check(*fixtures())
        self.assertEqual(pins['development_gate'], 'PASSED')
        self.assertEqual(pins['qualification_purpose'], 'E4B_BONUS_ENTRY')
        self.assertEqual(pins['model_variant'], q.MODEL)

    def test_label_does_not_replace_metrics_or_identity(self):
        for key, value in (('tool_argument_rejection_definition', 'all errors'), ('harness_errors', None), ('harness_errors', False), ('harness_errors', 1),
                           ('all_tool_attempted', None), ('all_tool_attempted', 0),
                           ('all_tool_rejected', None), ('all_tool_rejected', -1), ('all_tool_rejected', 6),
                           ('bootstrap_upper95_hours', None), ('bootstrap_upper95_hours', float('nan')),
                           ('bootstrap_upper95_hours', True), ('bootstrap_upper95_hours', 10.51),
                           ('model_variant', 'gemma-4-31b-it-qat-w4a16-ct'),
                           ('zip_sha256', '0' * 64), ('manifest_sha256', '0' * 64), ('state', 'RUNNING')):
            doc, registry = fixtures()
            doc['s1_dev16v_attempt1'][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.check(doc, registry)

    def test_explicit_selection_and_s2_rejection_required(self):
        doc, registry = fixtures()
        registry['s1_local_selection']['purpose'] = 'EXPLORATORY_LB_MEASUREMENT'
        with self.assertRaises(ValueError):
            self.check(doc, registry)
        doc, registry = fixtures()
        doc['s2_dev16v_attempt1']['gate'] = 'PASSED'
        with self.assertRaises(ValueError):
            self.check(doc, registry)

    def test_guard_precedes_writes(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 's1.ipynb'
            args = ['qualify_s1.py', '--receipt', 'missing', '--results', 'missing', '--notebook', str(output)]
            with patch.object(sys, 'argv', args), patch.object(q, 'require_qualification_gate', side_effect=ValueError('blocked')):
                with self.assertRaisesRegex(ValueError, 'blocked'):
                    q.main()
            self.assertFalse(output.exists())

    def test_generator_refuses_stale_evidence_and_wrong_zip(self):
        expected = self.check(*fixtures())
        pins = dict(expected, reconciled=True, m2_result_understood=True, zip_size=6501, zip_sha256=q.ZIP_SHA256)
        with patch.object(q, 'require_qualification_gate', return_value=expected):
            with self.assertRaisesRegex(ValueError, 'operational evidence'):
                generator.build_notebook('s1', dict(pins, selection_evidence_sha256='0' * 64), b'{}', b'')
            with self.assertRaisesRegex(ValueError, 'E4B experimental identity'):
                generator.build_notebook('s1', dict(pins, zip_sha256='0' * 64), b'{}', b'')

    def test_unreconciled_pins_stay_blocked(self):
        pins = generator.load_pins('s1')
        self.assertEqual(pins['qualification_purpose'], 'E4B_BONUS_ENTRY')
        self.assertEqual(pins['model_variant'], q.MODEL)
        if not pins['reconciled']:
            self.assertEqual(pins['zip_size'], 0)
            with self.assertRaises(ValueError):
                generator.build_notebook('s1', pins, b'{}', b'')


if __name__ == '__main__':
    unittest.main()
