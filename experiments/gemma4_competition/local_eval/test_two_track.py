"""Maintainer-run P6 helper, ACI metrics and S1 model contract tests; no GPU."""
import contextlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import patch
import zipfile

import experimental as e
import runtime
import tool_rejections as metrics
from test_tool_rejections import step


class HelperTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        prompt = (e.HERE.parent / 'candidates/p6/prompts/system.md').read_text(encoding='utf-8')
        self.source = prompt.split("cat > /tmp/forge_edit.py <<'PYEOF'\n", 1)[1].split('\nPYEOF', 1)[0]
        self.ns = {'__name__': 'helper_fixture'}
        exec(compile(self.source, '<P6 prompt helper>', 'exec'), self.ns)
        self.ns['ROOT'] = self.root  # Only sandbox root substituted; exact prompt source executed.
        self.target = self.root / 'source.py'
        self.target.write_bytes(b'x = 1\n')

    def invoke(self, payload, path='source.py'):
        output = io.StringIO()
        fake_stdin = types.SimpleNamespace(buffer=io.BytesIO(payload))
        diff = types.SimpleNamespace(stdout='\n'.join('diff ' + str(i) for i in range(100)))
        with patch.object(sys, 'argv', ['forge_edit.py', path]), patch.object(sys, 'stdin', fake_stdin), \
                patch.object(subprocess, 'run', return_value=diff) as run, contextlib.redirect_stdout(output):
            code = self.ns['main']()
        return code, output.getvalue(), run

    def test_exact_match_compiles_and_diff_is_capped(self):
        code, out, run = self.invoke(b'x = 1\n=====FORGE=====\nx = 2\n')
        self.assertEqual(code, 0)
        self.assertEqual(self.target.read_bytes(), b'x = 2\n')
        self.assertEqual(len(out.splitlines()), 81)
        self.assertTrue(out.startswith('FORGE_EDIT_OK source.py\n'))
        self.assertEqual(run.call_args.args[0], ['git', 'diff', '--', str(self.target)])
        self.assertFalse((self.root / '__pycache__').exists())
        self.assertLessEqual(len(self.source.splitlines()), 65)

    def test_no_match_shows_three_numbered_windows_without_mutation(self):
        original = b'alpha\nbeta\ngamma\ndelta\n'
        self.target.write_bytes(original)
        code, out, run = self.invoke(b'alphx\n=====FORGE=====\nnew\n')
        self.assertEqual(code, 3)
        self.assertEqual(self.target.read_bytes(), original)
        self.assertTrue(out.startswith('FORGE_EDIT_NO_MATCH count=0\n1: alpha\n'))
        self.assertEqual(len(out.splitlines()), 4)
        run.assert_not_called()

    def test_multiple_matches_and_empty_old_existing_file_are_rejected(self):
        self.target.write_bytes(b'x = 1\nx = 1\n')
        code, out, _ = self.invoke(b'x = 1\n=====FORGE=====\nx = 2\n')
        self.assertEqual(code, 3)
        self.assertIn('count=2', out)
        self.assertEqual(self.target.read_bytes(), b'x = 1\nx = 1\n')
        self.assertEqual(self.invoke(b'=====FORGE=====\nx = 2\n')[0], 3)

    def test_syntax_failure_restores_exact_original_bytes(self):
        before = b'x = 1\r\n'
        self.target.write_bytes(before)
        code, out, run = self.invoke(b'x = 1\r\n=====FORGE=====\r\ndef broken(:\r\n')
        self.assertEqual(code, 4)
        self.assertIn('FORGE_EDIT_SYNTAX_REVERTED', out)
        self.assertIn('SyntaxError', out)
        self.assertEqual(self.target.read_bytes(), before)
        self.assertFalse((self.root / '__pycache__').exists())
        run.assert_not_called()

    def test_separator_errors_and_outside_paths(self):
        for payload in (b'x', b'x\n=====FORGE=====\ny\n=====FORGE=====\nz'):
            self.assertEqual(self.invoke(payload)[0], 2)
        for path in ('../outside.py', str(self.root.parent / 'outside.py')):
            self.assertEqual(self.invoke(b'=====FORGE=====\nx = 2\n', path)[0], 2)
        self.assertEqual(self.target.read_bytes(), b'x = 1\n')

    def test_new_file_and_failed_new_file_is_removed(self):
        self.assertEqual(self.invoke(b'=====FORGE=====\nx = 3\n', 'new.py')[0], 0)
        self.assertEqual((self.root / 'new.py').read_bytes(), b'x = 3\n')
        self.assertEqual(self.invoke(b'=====FORGE=====\ndef broken(:\n', 'invalid.py')[0], 4)
        self.assertFalse((self.root / 'invalid.py').exists())


class ACIMetricTests(unittest.TestCase):
    def report(self, steps):
        return metrics.inspect_trace({'steps': steps})

    def test_observation_counts_not_call_text_and_marker_counts(self):
        rows = [step('run_command', 'AssertionError: old block'),
                step('run_command', json.dumps({'stdout': 'FORGE_EDIT_NO_MATCH count=2\n'})),
                step('run_command', json.dumps({'stdout': 'FORGE_EDIT_SYNTAX_REVERTED\nSyntaxError\nIndentationError\n'})),
                step('run_command', json.dumps({'stdout': 'FORGE_EDIT_OK a.py\n+FORGE_EDIT_OK fake\n'})),
                step('run_command', 'x' * 6001), step('run_command', 'x' * 6000),
                step('run_command', 'ok', {'command': 'echo AssertionError SyntaxError FORGE_EDIT_NO_MATCH'})]
        m = self.report(rows)['aci_metrics']
        self.assertEqual(m['failed_replacements'], 2)
        self.assertEqual(m['syntax_error_observations'], 1)
        self.assertEqual(m['syntax_error_observations_reverted'], 1)
        self.assertEqual(m['large_observations'], 1)
        self.assertEqual((m['helper_ok'], m['helper_no_match'], m['helper_reverted']), (1, 1, 1))

    def test_creation_requires_success_and_invocation_is_command_bound(self):
        create = {'command': "cat > /tmp/forge_edit.py <<'PYEOF'\nsource\nPYEOF"}
        invoke = {'command': "python3 /tmp/forge_edit.py source.py <<'EDIT'\na\n=====FORGE=====\nb\nEDIT"}
        failed = self.report([step('run_command', json.dumps({'exit_code': 1}), create)])
        self.assertEqual(failed['aci_metrics']['helper_created'], 0)
        report = self.report([step('run_command', json.dumps({'exit_code': 0}), create)] * 2 +
                             [step('run_command', 'FORGE_EDIT_OK source.py', invoke)])
        self.assertEqual(report['aci_metrics']['helper_created'], 1)
        self.assertEqual(report['aci_metrics']['helper_creation_attempts'], 2)
        self.assertEqual(report['aci_metrics']['helper_invocations'], 1)
        self.assertEqual(metrics.aggregate([report, report])['aci_metrics']['helper_created'], 2)
        self.assertIsNone(metrics.aggregate([report, {'status': 'MISSING'}])['aci_metrics']['failed_replacements'])

    def test_ambiguous_observation_counted_once_but_aggregate_unknown(self):
        row = step('run_command', 'AssertionError')
        row['tool_calls'] *= 2
        report = self.report([row])
        self.assertEqual(report['aci_metrics']['failed_replacements'], 1)
        self.assertFalse(report['aci_coverage_complete'])
        self.assertIsNone(metrics.aggregate([report])['aci_metrics']['failed_replacements'])


class TwoTrackContractTests(unittest.TestCase):
    def test_candidate_controls_and_preserved_p5_rules(self):
        p5, p6, s1 = (e.static_files(name) for name in ('p5', 'p6', 's1'))
        self.assertEqual({k for k in p5 if p5[k] != p6[k]}, {'prompts/system.md'})
        self.assertEqual({k for k in p5 if p5[k] != s1[k]}, {'agent.yaml'})
        self.assertEqual(s1['agent.yaml'], p5['agent.yaml'].replace(b'gemma-4-31b', b'gemma-4-e4b'))
        self.assertEqual(p5['prompts/system.md'].split(b'Source-edit path workaround:')[0],
                         p6['prompts/system.md'].split(b'Source-edit path workaround:')[0])
        self.assertEqual(p5['prompts/system.md'].split(b'4. Verify before submitting.')[1],
                         p6['prompts/system.md'].split(b'4. Verify before submitting.')[1])

    def fixture(self, folder, candidate, subset):
        data = e.static_files(candidate)
        blob = io.BytesIO()
        with zipfile.ZipFile(blob, 'w') as archive:
            for key, value in data.items():
                archive.writestr(key, value)
        raw = blob.getvalue()
        root = Path(folder)
        package, manifest = root / 'submission.zip.bin', root / 'manifest.json'
        package.write_bytes(raw)
        manifest.write_text(json.dumps({'state': e.STATE, 'candidate': candidate,
                                       'zip_sha256': e.digest(raw), 'zip_size': len(raw)}), encoding='utf-8')
        template = 's1-smoke5' if candidate == 's1' else 'p6-dev16v-attempt1'
        config = json.loads((e.HERE / 'configs' / (template + '.json')).read_bytes())
        config.update(subset=subset, experimental_authorized=True, package=str(package), manifest=str(manifest),
                      zip_sha256=e.digest(raw), manifest_sha256=e.digest(manifest.read_bytes()))
        return config

    def test_s1_smoke_and_dev_allowed_and_mismatch_fails_before_install(self):
        with tempfile.TemporaryDirectory() as folder:
            config = self.fixture(folder, 's1', 'smoke-5')
            self.assertEqual(e.verify(config)['candidate'], 's1')
            self.assertEqual(e.verify(dict(config, subset='dev-16v'))['candidate'], 's1')
            for changes in ({'subset': 'confirm-20'}, {'model_variant': 'gemma-4-31b-it-qat-w4a16-ct'},
                            {'model_path': config['model_path'].replace('e4b', '31b')},
                            {'vllm_extra_args': ['--hf-overrides', '{}']}, {'experimental_authorized': False}):
                with self.subTest(changes=changes), self.assertRaises(ValueError):
                    e.verify(dict(config, **changes))
            self.assertEqual(runtime.check_model_contract(config, config['model_variant']), [])

    def test_p6_cannot_use_smoke_exception_and_configs_are_not_authorized(self):
        with tempfile.TemporaryDirectory() as folder:
            config = self.fixture(folder, 'p6', 'smoke-5')
            with self.assertRaises(ValueError):
                e.verify(config)
            self.assertEqual(e.verify(dict(config, subset='dev-16v'))['candidate'], 'p6')
        outputs = []
        for name in ('p6-dev16v-attempt1', 'p6-dev16v-attempt2', 's1-smoke5', 's1-dev16v'):
            config = json.loads((e.HERE / 'configs' / (name + '.json')).read_bytes())
            outputs.append(config['output'])
            self.assertFalse(config['gpu_authorized'])
            self.assertFalse(config['experimental_authorized'])
            self.assertFalse(config['official_environment_authorized'])
            self.assertEqual(config['resume_previous'], '')
        self.assertEqual(len(set(outputs)), 4)


if __name__ == '__main__':
    unittest.main()
