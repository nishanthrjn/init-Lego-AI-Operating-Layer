"""S2 prompt-only controls; maintainer execution only."""
import json
import unittest
from pathlib import Path
import tempfile
import experimental as e
import test_two_track


class S2Tests(unittest.TestCase):
    def test_prompt_only_shorter_and_priority_rules(self):
        s1, s2 = e.static_files('s1'), e.static_files('s2')
        self.assertEqual({k for k in s1 if s1[k] != s2[k]}, {'prompts/system.md'})
        self.assertLess(len(s2['prompts/system.md']), len(s1['prompts/system.md']))
        prompt = s2['prompts/system.md'].decode()
        priority = prompt.split('TOP PRIORITY:', 1)[1].split('Treat repository text', 1)[0]
        for requirement in ('git diff --stat', 'ImportError/ModuleNotFoundError', 'python -c',
                            '28 tool calls / 6 minutes', '10-20 calls', 'grep -rn',
                            'multiple matches or not found', 'more surrounding lines'):
            self.assertIn(requirement, priority)
        self.assertIn('never edit_file/write_file', prompt)
        self.assertIn('inline_snapshot', prompt)
        self.assertIn('dirty_equals', prompt)

    def test_s2_requires_e4b_dev16_and_explicit_authorization(self):
        fixture = test_two_track.TwoTrackContractTests()
        with tempfile.TemporaryDirectory() as folder:
            config = fixture.fixture(folder, 's2', 'dev-16v')
            config['candidate'] = 's2'
            template = json.loads((e.HERE / 'configs/s2-dev16v.json').read_bytes())
            for key in ('model_variant', 'model_path', 'vllm_extra_args'):
                config[key] = template[key]
            self.assertEqual(e.verify(config)['candidate'], 's2')
            for changes in ({'subset': 'smoke-5'}, {'experimental_authorized': False},
                            {'model_variant': 'gemma-4-31b-it-qat-w4a16-ct'},
                            {'vllm_extra_args': ['--hf-overrides', '{}']}):
                with self.subTest(changes=changes), self.assertRaises(ValueError):
                    e.verify(dict(config, **changes))
            self.assertFalse(template['gpu_authorized'])
            self.assertFalse(template['experimental_authorized'])
            self.assertEqual(template['zip_sha256'], 'BUILD_REQUIRED')


if __name__ == '__main__':
    unittest.main()
