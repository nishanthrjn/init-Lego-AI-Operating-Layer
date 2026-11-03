"""P9 prompt-only and thinking-budget ablations; maintainer execution required."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import experimental as e
import test_two_track


class P9Tests(unittest.TestCase):
    def test_exact_ablations_preserve_base_and_workaround(self):
        base, a, b = (e.static_files(n) for n in ('p7a', 'p9a', 'p9b'))
        self.assertEqual({k for k in base if base[k] != a[k]}, {'prompts/system.md'})
        self.assertTrue(a['prompts/system.md'].endswith(base['prompts/system.md']))
        addition = a['prompts/system.md'][:-len(base['prompts/system.md'])].decode()
        for phrase in ('/tmp/repro.py', '/tmp/notes.md', 'target', 'file/function',
                       'repro command', 'edits made', 'next step', 'after each',
                       'run_command', '15 steps', 'cat /tmp/notes.md; git diff',
                       'Never recreate work'):
            self.assertIn(phrase, addition)
        self.assertEqual({k for k in a if a[k] != b[k]}, {'configs/sampling.yaml'})
        self.assertEqual(b['configs/sampling.yaml'], a['configs/sampling.yaml'].replace(
            b'thinking_budget: 4096', b'thinking_budget: 512'))
        self.assertIn(b'max_tool_calls: 28', a['eval_config.yaml'])
        self.assertIn(b'max_time_minutes: 6', a['eval_config.yaml'])

    def test_repinning_cannot_hide_extra_sampling_change(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'local_eval').mkdir()
            pins = json.loads((e.HERE / 'experimental-pins.json').read_bytes())
            for name in pins:
                for member in e.MEMBERS:
                    blob = (e.HERE.parent / 'candidates' / name / member).read_bytes()
                    if name == 'p9b' and member == 'configs/sampling.yaml':
                        blob = blob.replace(b'max_output_tokens: 8192', b'max_output_tokens: 4096')
                        pins[name][member] = e.digest(blob)
                    path = root / 'candidates' / name / member
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(blob)
            (root / 'local_eval/experimental-pins.json').write_text(json.dumps(pins))
            with patch.object(e, 'HERE', root / 'local_eval'):
                with self.assertRaisesRegex(ValueError, 'P9b thinking budget must be the only sampling change'):
                    e.static_files('p9b')

    def test_four_independent_configs_and_no_implicit_authorization(self):
        outputs = set()
        for candidate in ('p9a', 'p9b'):
            templates = [json.loads((e.HERE / 'configs' / f'{candidate}-dev16v-attempt{i}.json').read_bytes())
                         for i in (1, 2)]
            self.assertEqual({k for k in templates[0] if templates[0][k] != templates[1][k]}, {'output'})
            for attempt, template in enumerate(templates, 1):
                outputs.add(template['output'])
                self.assertTrue(template['output'].endswith(f'{candidate}-dev-16v-attempt{attempt}'))
                self.assertEqual(template['resume_previous'], '')
                for flag in ('experimental_authorized', 'gpu_authorized', 'official_environment_authorized'):
                    self.assertFalse(template[flag])
                with tempfile.TemporaryDirectory() as folder:
                    config = test_two_track.TwoTrackContractTests().fixture(folder, candidate, 'dev-16v')
                    for key in ('candidate', 'model_variant', 'model_path', 'vllm_extra_args'):
                        config[key] = template[key]
                    self.assertEqual(e.verify(config)['candidate'], candidate)
                    for changes in ({'subset': 'smoke-5'}, {'experimental_authorized': False},
                                    {'model_variant': 'gemma-4-e4b-it-qat-w4a16-ct'},
                                    {'zip_sha256': '0' * 64}):
                        with self.subTest(candidate=candidate, changes=changes), self.assertRaises(ValueError):
                            e.verify(dict(config, **changes))
        self.assertEqual(len(outputs), 4)


if __name__ == '__main__':
    unittest.main()
