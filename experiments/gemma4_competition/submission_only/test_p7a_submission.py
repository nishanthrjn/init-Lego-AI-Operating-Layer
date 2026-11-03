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
            with patch.object(sys, 'argv', argv), patch.object(q, 'require_qualification_gate', side_effect=ValueError('blocked')):
                with self.assertRaisesRegex(ValueError, 'blocked'):
                    q.main()
            self.assertFalse(target.exists())

    def test_shared_generator_cannot_bypass_guard_or_use_stale_evidence(self):
        pins = {'reconciled': True, 'm2_result_understood': True}
        with patch.object(q, 'require_qualification_gate', side_effect=ValueError('blocked')):
            with self.assertRaisesRegex(ValueError, 'blocked'):
                generator.build_notebook('p7a', pins, b'{}', b'payload')
        with patch.object(q, 'require_qualification_gate', return_value={'development_gate': 'PASSED', 'development_evidence_sha256': 'a' * 64}):
            with self.assertRaisesRegex(ValueError, 'development evidence'):
                generator.build_notebook('p7a', pins, b'{}', b'payload')

    def test_generator_requires_evaluated_zip_even_with_passing_development(self):
        development = {'development_gate': 'PASSED', 'development_evidence_sha256': 'a' * 64}
        pins = dict(development, reconciled=True, m2_result_understood=True,
                    zip_sha256='0' * 64, zip_size=7359)
        with patch.object(q, 'require_qualification_gate', return_value=development):
            with self.assertRaisesRegex(ValueError, 'evaluated experimental identity'):
                generator.build_notebook('p7a', pins, b'{}', b'payload')

    def test_submission_pins_are_placeholders(self):
        pins = generator.load_pins('p7a')
        if not pins['reconciled']:
            self.assertEqual(pins['development_gate'], 'PENDING_CONFIRMATION')
        else:
            self.assertIn(pins['development_gate'], ('PASSED', 'FAILED'))
            self.assertEqual(len(pins['development_evidence_sha256']), 64)



class P7aExploratoryTests(unittest.TestCase):
    def fixtures(self):
        doc = evidence()
        doc['p7a_confirmation_decision'] = {'status': 'FAILED', 'decision': 'RETAIN_P5'}
        doc['p7a_attempt2'].update(resolved=7, empty_patches=5)
        amendment = {
            'amendment_id': 'P7A-EXPLORATORY-LB-1', 'candidate': 'p7a',
            'purpose': 'EXPLORATORY_LB_MEASUREMENT', 'status': 'AUTHORIZED_PENDING_QUALIFICATION',
            'execution_status': 'NOT_SUBMITTED', 'local_adoption': 'NOT_ADOPTED',
            'local_confirmation': 'FAILED', 'zip_sha256': q.ZIP_SHA256,
            'experimental_manifest_sha256': q.MANIFEST_SHA256, 'zip_size': 7359,
            'adopt_public_score_at_least': 0.17, 'p5_mean_public_score': 0.14,
            'otherwise': 'RETAIN_P5', 'final_selection_rules': 'UNCHANGED',
            'recorded_before_any_p7a_public_score': True, 'maximum_submissions': 1,
            'submissions_used': 0, 'submission_ids': [], 'public_score': None,
        }
        return doc, {'p7a_exploratory_authorization': amendment, 'runs': []}

    def check(self, doc, registry):
        with tempfile.TemporaryDirectory() as folder:
            path, submissions = Path(folder) / 'evidence.json', Path(folder) / 'submissions.json'
            path.write_text(json.dumps(doc))
            submissions.write_text(json.dumps(registry))
            pins = q.require_qualification_gate(path, submissions)
            self.assertEqual(pins['development_evidence_sha256'], hashlib.sha256(path.read_bytes()).hexdigest())
            self.assertEqual(pins['exploratory_authorization_sha256'], hashlib.sha256(submissions.read_bytes()).hexdigest())
            with self.assertRaises(ValueError):
                q.require_confirmation_gate(path)
            return pins

    def test_exploration_does_not_reclassify_failed_local_gate(self):
        pins = self.check(*self.fixtures())
        self.assertEqual(pins['development_gate'], 'FAILED')
        self.assertEqual(pins['local_adoption'], 'NOT_ADOPTED')
        self.assertEqual(pins['qualification_purpose'], 'EXPLORATORY_LB_MEASUREMENT')
        self.assertEqual(pins['maximum_submissions'], 1)

    def test_consumed_revoked_scored_and_wrong_identity_refused(self):
        for key, value in (('submissions_used', 1), ('submissions_used', False),
                           ('maximum_submissions', 2), ('maximum_submissions', True),
                           ('submission_ids', ['123']), ('public_score', 0.17),
                           ('recorded_before_any_p7a_public_score', False),
                           ('status', 'REVOKED'), ('execution_status', 'SCORING'),
                           ('zip_sha256', '0' * 64), ('experimental_manifest_sha256', '0' * 64),
                           ('adopt_public_score_at_least', 0.15), ('purpose', 'ADOPTION')):
            doc, registry = self.fixtures()
            registry['p7a_exploratory_authorization'][key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                self.check(doc, registry)

    def test_existing_submission_and_changed_local_decision_refused(self):
        doc, registry = self.fixtures()
        registry['runs'] = [{'candidate': 'p7a', 'status': 'SCORING', 'public_score': None}]
        with self.assertRaises(ValueError):
            self.check(doc, registry)
        doc, registry = self.fixtures()
        doc['p7a_confirmation_decision']['status'] = 'PASSED'
        with self.assertRaises(ValueError):
            self.check(doc, registry)

    def test_missing_amendment_does_not_bypass_failed_confirmation(self):
        doc, _ = self.fixtures()
        with self.assertRaises(ValueError):
            self.check(doc, {'runs': []})

    def test_generator_rejects_stale_amendment_pin(self):
        pins = self.check(*self.fixtures())
        supplied = dict(pins, reconciled=True, m2_result_understood=True,
                        zip_sha256=q.ZIP_SHA256, zip_size=7359)
        supplied['exploratory_authorization_sha256'] = '0' * 64
        with patch.object(q, 'require_qualification_gate', return_value=pins):
            with self.assertRaisesRegex(ValueError, 'development evidence'):
                generator.build_notebook('p7a', supplied, b'{}', b'payload')

    def test_generator_preserves_exploratory_purpose(self):
        development = self.check(*self.fixtures())
        payload = b'x' * 7359
        digest = hashlib.sha256(payload).hexdigest()
        manifest = {'state': 'PORTABLE_COMPILE_AND_PACKAGE_PASS',
                    'local_receipt_sha256': 'a' * 64, 'zip_sha256': digest, 'zip_size': len(payload)}
        raw = json.dumps(manifest).encode()
        pins = dict(development, reconciled=True, m2_result_understood=True, zip_sha256=digest,
                    zip_size=len(payload), receipt_sha256='a' * 64,
                    manifest_sha256=hashlib.sha256(raw).hexdigest(), authorization='test authorization')
        with patch.object(q, 'require_qualification_gate', return_value=development), patch.object(q, 'ZIP_SHA256', digest):
            notebook = generator.build_notebook('p7a', pins, raw, payload)
        source = ''.join(''.join(c['source']) for c in notebook['cells'])
        self.assertIn('EXPLORATORY_LB_MEASUREMENT', source)
        self.assertIn('one manual submission only', source)
        self.assertIn("'development_gate': 'FAILED'", source)

if __name__ == '__main__':
    unittest.main()
