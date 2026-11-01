"""P7 ablation and authorization controls; maintainer execution only."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import experimental as e
import test_two_track


class P7Tests(unittest.TestCase):
    def test_exact_ablation_and_preserved_workaround(self):
        p5, a, b = (e.static_files(name) for name in ('p5', 'p7a', 'p7b'))
        self.assertEqual({k for k in p5 if p5[k] != a[k]}, {'prompts/system.md'})
        self.assertEqual({k for k in a if a[k] != b[k]}, {'configs/sampling.yaml'})
        self.assertEqual(b['configs/sampling.yaml'], a['configs/sampling.yaml'].replace(
            b'thinking_budget: 4096', b'thinking_budget: 2048'))
        for member in ('agent.yaml', 'eval_config.yaml'):
            self.assertEqual(p5[member], b[member])
        def workaround(files):
            return files['prompts/system.md'].split(b'Source-edit path workaround:', 1)[1].split(
                b'\n4. Verify before submitting.', 1)[0]
        self.assertEqual(workaround(p5), workaround(a))
        prompt = a['prompts/system.md'].decode()
        for phrase in ('first ~5 tool calls', 'grep -rn', 'tool call 12 / minute 3',
                       'git diff --stat', 'Never submit an empty diff', 'small',
                       'sed -i or regex substitution', 'git checkout -- <file>',
                       'best current valid diff', '180 elapsed seconds'):
            self.assertIn(phrase, prompt)
        self.assertNotIn('150 elapsed seconds', prompt)
        self.assertNotIn('source edit by tool call 10', prompt)

    def test_other_sampling_change_rejected_even_with_updated_pin(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'local_eval').mkdir()
            pins = json.loads((e.HERE / 'experimental-pins.json').read_bytes())
            for name in pins:
                for member in e.MEMBERS:
                    blob = (e.HERE.parent / 'candidates' / name / member).read_bytes()
                    if name == 'p7b' and member == 'configs/sampling.yaml':
                        blob = blob.replace(b'max_output_tokens: 8192', b'max_output_tokens: 4096')
                        pins[name][member] = e.digest(blob)
                    path = root / 'candidates' / name / member
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(blob)
            (root / 'local_eval/experimental-pins.json').write_text(json.dumps(pins))
            with patch.object(e, 'HERE', root / 'local_eval'):
                with self.assertRaisesRegex(ValueError, 'only sampling change'):
                    e.static_files('p7b')

    def test_model_subset_identity_and_unapproved_configs(self):
        outputs = []
        for candidate in ('p7a', 'p7b'):
            template = json.loads((e.HERE / 'configs' / (candidate + '-dev16v.json')).read_bytes())
            outputs.append(template['output'])
            self.assertEqual(template['model_variant'], 'gemma-4-31b-it-qat-w4a16-ct')
            for flag in ('gpu_authorized', 'experimental_authorized', 'official_environment_authorized'):
                self.assertFalse(template[flag])
            self.assertEqual(template['resume_previous'], '')
            with tempfile.TemporaryDirectory() as folder:
                config = test_two_track.TwoTrackContractTests().fixture(folder, candidate, 'dev-16v')
                for key in ('candidate', 'model_variant', 'model_path', 'vllm_extra_args'):
                    config[key] = template[key]
                self.assertEqual(e.verify(config)['candidate'], candidate)
                for changes in ({'subset': 'smoke-5'}, {'subset': 'confirm-20'},
                                {'experimental_authorized': False},
                                {'model_variant': 'gemma-4-e4b-it-qat-w4a16-ct'},
                                {'vllm_extra_args': ['--hf-overrides', '{}']},
                                {'zip_sha256': '0' * 64}):
                    with self.subTest(candidate=candidate, changes=changes), self.assertRaises(ValueError):
                        e.verify(dict(config, **changes))
        self.assertNotEqual(*outputs)


if __name__ == '__main__':
    unittest.main()
