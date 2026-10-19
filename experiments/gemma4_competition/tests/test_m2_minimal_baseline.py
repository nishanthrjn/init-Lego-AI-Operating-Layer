"""Offline policy/packaging controls; official compiler controls live in validator.

No model, provider, official package import or network request is made here.
Symlink creation requires the host's permission; failure is not silently skipped.
"""

import io
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch
import zipfile

import validate_forgeai_gemma4_m2_minimal_baseline_1 as gate
from experiments.gemma4_competition import portable_m2 as portable


class BaselinePolicyTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="gemma-m2-test-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.candidate = self.root / "candidate"
        shutil.copytree(gate.CANDIDATE, self.candidate)

    def test_exact_positive_and_crlf_refusal_for_byte_identity(self):
        original = gate.static_candidate(self.candidate)
        for name in gate.MEMBERS:
            (self.candidate / name).write_bytes(original[name].replace(b"\n", b"\r\n"))
        with self.assertRaises(ValueError):
            gate.static_candidate(self.candidate)

    def test_policy_rejects_configuration_mutations(self):
        mutations = [
            ("agent.yaml", "agent_class: LlmAgent", "agent_class: LlmAgent\nunknown: true"),
            ("agent.yaml", "  - read_file", "  - unknown_tool"),
            ("agent.yaml", gate.MODEL, "other-model"),
            ("agent.yaml", "prompts/system.md", "../outside.md"),
            ("agent.yaml", "agent_class: LlmAgent", "agent_class: LlmAgent\nadapter: extra"),
            ("agent.yaml", "agent_class: LlmAgent", "agent_class: LlmAgent\nsub_agents: []"),
            ("configs/sampling.yaml", "16384", "32769"),
            ("eval_config.yaml", "max_tool_calls: 10", "max_tool_calls: 11"),
        ]
        for name, old, new in mutations:
            with self.subTest(name=name, mutation=new):
                path = self.candidate / name
                before = path.read_bytes()
                path.write_bytes(before.replace(old.encode(), new.encode()))
                with self.assertRaises(ValueError):
                    gate.static_candidate(self.candidate)
                path.write_bytes(before)

    def test_missing_root(self):
        (self.candidate / "agent.yaml").unlink()
        with self.assertRaises(ValueError):
            gate.static_candidate(self.candidate)

    def test_extra_roots_files_adapters_and_mixed_model_policy(self):
        # These are our stricter application policy, not compiler rejections.
        for name, content in [
            ("root_agent.yaml", "model: another-model\n"),
            ("extra.exe", "extra"),
            ("extra.txt", "extra"),
            ("adapters/adapter.json", "{}"),
        ]:
            with self.subTest(name=name):
                extra = self.candidate / name
                extra.parent.mkdir(parents=True, exist_ok=True)
                extra.write_text(content, encoding="utf-8")
                with self.assertRaises(ValueError):
                    gate.static_candidate(self.candidate)
                extra.unlink()
                if extra.parent != self.candidate:
                    extra.parent.rmdir()

    def test_symlink_to_existing_file_rejected(self):
        path = self.candidate / "prompts/system.md"
        outside = self.root / "outside.md"
        path.rename(outside)
        path.symlink_to(outside)
        with self.assertRaises(ValueError):
            gate.static_candidate(self.candidate)

    def test_deterministic_zip_and_manifest_members(self):
        data = gate.static_candidate(self.candidate)
        first = gate.zip_bytes(data)
        second = gate.zip_bytes(dict(reversed(list(data.items()))))
        self.assertEqual(first, second)
        gate.inspect_zip(first, data)
        self.assertEqual(gate.sha(first), gate.sha(second))

    def test_extra_archive_root_rejected(self):
        data = gate.static_candidate(self.candidate)
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            for name, content in data.items():
                archive.writestr("baseline/" + name, content)
        with self.assertRaises(ValueError):
            gate.inspect_zip(buffer.getvalue(), data)

    def test_unsafe_archive_member_rejected_before_writing(self):
        data = gate.static_candidate(self.candidate)
        data["../secret"] = b"synthetic"
        with self.assertRaises(ValueError):
            gate.zip_bytes(data)

    def test_missing_dependency_cannot_pass_preflight(self):
        with patch.object(gate.metadata, "distribution", side_effect=gate.metadata.PackageNotFoundError):
            with self.assertRaises(gate.metadata.PackageNotFoundError):
                gate.environment_preflight({})

    def test_network_and_process_guards(self):
        for event in ("socket.connect", "socket.getaddrinfo", "subprocess.Popen", "os.system"):
            with self.subTest(event=event), self.assertRaises(gate.OfflineViolation):
                gate.deny_effects(event, ())

    def test_receipt_rejects_changed_input_and_missing_local_pass(self):
        receipt = self.root / "local-receipt.json"
        expected = {"fixture": {"sha256": "expected", "size": 1}}
        with patch.object(portable, "input_manifest", return_value=expected), patch.object(
            portable, "static_candidate", return_value={}
        ):
            valid = {"schema": 1, "state": "LOCAL_SCOPE_AND_STATIC_PASS", "inputs": expected}
            receipt.write_text(json.dumps(valid), encoding="utf-8")
            self.assertEqual(portable.verify_local_receipt(receipt), valid)
            for changed in (dict(valid, inputs={}), dict(valid, state="NOT_RUN")):
                receipt.write_text(json.dumps(changed), encoding="utf-8")
                with self.assertRaises(ValueError):
                    portable.verify_local_receipt(receipt)

    def test_manifest_contains_raw_candidate_hashes(self):
        entries = portable.input_manifest()
        for name in gate.MEMBERS:
            key = "experiments/gemma4_competition/baseline/" + name
            raw = (gate.CANDIDATE / name).read_bytes()
            self.assertEqual(entries[key], {"sha256": gate.sha(raw), "size": len(raw)})


if __name__ == "__main__":
    unittest.main()
