"""P8 budget-only ablation and experimental authorization contracts."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import experimental as e
import test_two_track


class P8Tests(unittest.TestCase):
    def test_budget_only_control(self):
        before, after = e.static_files('p7a'), e.static_files('p8')
        self.assertEqual({k for k in before if before[k] != after[k]}, {'eval_config.yaml'})
        self.assertEqual(after['eval_config.yaml'], before['eval_config.yaml'].replace(
            b'max_tool_calls: 28\n', b'max_tool_calls: 40\n'))
        self.assertIn(b'max_time_minutes: 6\n', after['eval_config.yaml'])

    def test_repinning_cannot_hide_extra_budget_change(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'local_eval').mkdir()
            pins = json.loads((e.HERE / 'experimental-pins.json').read_bytes())
            for name in pins:
                for member in e.MEMBERS:
                    blob = (e.HERE.parent / 'candidates' / name / member).read_bytes()
                    if name == 'p8' and member == 'eval_config.yaml':
                        blob = blob.replace(b'max_time_minutes: 6', b'max_time_minutes: 7')
                        pins[name][member] = e.digest(blob)
                    path = root / 'candidates' / name / member
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(blob)
            (root / 'local_eval/experimental-pins.json').write_text(json.dumps(pins))
            with patch.object(e, 'HERE', root / 'local_eval'):
                with self.assertRaisesRegex(ValueError, 'only evaluation change'):
                    e.static_files('p8')

    def test_independent_configs_and_authorization_failures(self):
        templates = [json.loads((e.HERE / 'configs' / f'p8-dev16v-attempt{i}.json').read_bytes())
                     for i in (1, 2)]
        self.assertEqual({k for k in templates[0] if templates[0][k] != templates[1][k]}, {'output'})
        for attempt, template in enumerate(templates, 1):
            self.assertTrue(template['output'].endswith(f'p8-dev-16v-attempt{attempt}'))
            self.assertEqual(template['resume_previous'], '')
            for flag in ('experimental_authorized', 'gpu_authorized', 'official_environment_authorized'):
                self.assertFalse(template[flag])
            with tempfile.TemporaryDirectory() as folder:
                config = test_two_track.TwoTrackContractTests().fixture(folder, 'p8', 'dev-16v')
                for key in ('candidate', 'model_variant', 'model_path', 'vllm_extra_args'):
                    config[key] = template[key]
                self.assertEqual(e.verify(config)['candidate'], 'p8')
                for changes in ({'subset': 'smoke-5'}, {'experimental_authorized': False},
                                {'model_variant': 'gemma-4-e4b-it-qat-w4a16-ct'},
                                {'zip_sha256': '0' * 64}):
                    with self.subTest(changes=changes), self.assertRaises(ValueError):
                        e.verify(dict(config, **changes))

    def test_evidence_remains_failed_and_references_match(self):
        path = e.HERE.parent / 'results/dev-16v-comparison.json'
        records = json.loads(path.read_bytes())
        self.assertEqual(records['p7a_confirmation_decision']['status'], 'FAILED')
        self.assertEqual(records['p7a_confirmation_decision']['decision'], 'RETAIN_P5')
        self.assertEqual(records['p8_preregistered_gate']['attempts'], [1, 2])
        self.assertEqual(records['p8_preregistered_gate']['minimum_pooled_resolved'], 21)
        self.assertEqual(records['p8_preregistered_gate']['maximum_pooled_empty_patches'], 6)
        self.assertEqual(records['p8_preregistered_gate']['maximum_bootstrap_upper95_hours_each_run'], 11)
        paper = json.loads((e.HERE.parent / 'results/paper-evidence.json').read_bytes())
        claim = next(c for c in paper['claims'] if c['id'] == 'p7a_failed_confirmation_and_within_config_variance')
        self.assertEqual(claim['sha256'], e.digest(path.read_bytes()))


if __name__ == '__main__':
    unittest.main()
