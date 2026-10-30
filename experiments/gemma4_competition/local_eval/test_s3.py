"""S3 controls; tests are executed only by the maintainer."""
import json
import tempfile
import unittest
import experimental as e
import test_two_track


class S3Tests(unittest.TestCase):
    def test_prompt_only_delta_size_and_corruption_rules(self):
        before, after = e.static_files('s2'), e.static_files('s3')
        self.assertEqual({k for k in before if before[k] != after[k]}, {'prompts/system.md'})
        self.assertLessEqual(len(after['prompts/system.md']), len(before['prompts/system.md']) + 400)
        prompt = after['prompts/system.md'].decode()
        for text in ('Never use sed -i or regex substitution', 'python3 exact-string replace',
                     'git checkout -- <file>', 'Never submit a file you believe is corrupted',
                     'non-empty, small', 'only intended source files', 'revert and redo',
                     'unrelated pre-existing changes', 'git diff --stat',
                     'mandatory input', 'never resend that call'):
            self.assertIn(text, prompt)
        self.assertNotIn('never edit_file/write_file', prompt)
        self.assertNotIn('run_command source-edit rule below', prompt)

    def test_s3_e4b_dev16_contract_and_unauthorized_defaults(self):
        template = json.loads((e.HERE / 'configs/s3-dev16v.json').read_bytes())
        with tempfile.TemporaryDirectory() as folder:
            config = test_two_track.TwoTrackContractTests().fixture(folder, 's3', 'dev-16v')
            for key in ('candidate', 'model_variant', 'model_path', 'vllm_extra_args'):
                config[key] = template[key]
            self.assertEqual(e.verify(config)['candidate'], 's3')
            for changes in ({'subset': 'smoke-5'}, {'subset': 'confirm-20'},
                            {'experimental_authorized': False},
                            {'model_variant': 'gemma-4-31b-it-qat-w4a16-ct'},
                            {'vllm_extra_args': ['--hf-overrides', '{}']}):
                with self.subTest(changes=changes), self.assertRaises(ValueError):
                    e.verify(dict(config, **changes))
        for key in ('gpu_authorized', 'experimental_authorized', 'official_environment_authorized'):
            self.assertFalse(template[key])
        self.assertEqual(template['zip_sha256'], 'BUILD_REQUIRED')


if __name__ == '__main__':
    unittest.main()
