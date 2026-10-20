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


class ScopedInstallTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="gemma-install-test-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.pins = {}
        for name, version in portable.INSTALL_PACKAGES.items():
            filename = f"{name.replace('-', '_')}-{version}-py3-none-any.whl"
            data = name.encode()
            (self.root / filename).write_bytes(data)
            self.pins[name] = {"filename": filename, "sha256": portable.sha(data), "size": len(data)}
        self.bundle = self.root / "bundled"
        self.bundle.mkdir()
        self.duplicates = {}
        for name in portable.PACKAGES:
            path = self.bundle / (name + ".fixture")
            path.write_bytes(name.encode())
            self.duplicates[name] = path
        self.enterContext(patch.object(portable, "install_pins", return_value=self.pins))
        self.enterContext(patch.object(portable, "wheel_pins", return_value=self.duplicates))

    def test_exactly_five_names_ignore_other_wheels(self):
        (self.root / "torch-99-py3-none-any.whl").write_bytes(b"never select")
        selected = portable.select_install_wheels(self.root)
        self.assertEqual(set(selected), set(portable.INSTALL_PACKAGES))
        self.assertEqual({p.name for p in selected.values()}, {
            "adk_submission-0.2.13-py3-none-any.whl", "adk_eval_core-0.1.0-py3-none-any.whl",
            "swegemma-0.2.11-py3-none-any.whl", "google_adk-1.36.1-py3-none-any.whl",
            "google_genai-2.11.0-py3-none-any.whl",
        })

    def test_wrong_version_does_not_substitute_for_missing_wheel(self):
        (self.root / self.pins["google-adk"]["filename"]).rename(self.root / "google_adk-1.36.2-py3-none-any.whl")
        with self.assertRaises(ValueError):
            portable.select_install_wheels(self.root)

    def test_hash_mismatch_stops_before_pip(self):
        receipt = self.root / "receipt.json"
        receipt.write_text("{}", encoding="utf-8")
        (self.root / self.pins["google-genai"]["filename"]).write_bytes(b"changed")
        with patch.object(portable.sys, "platform", "linux"), patch.object(
            portable.sys, "version_info", (3, 12)
        ), patch.object(portable, "verify_local_receipt"), patch.object(
            portable, "mounted_inventory", return_value=portable.wheelhouse_contract()[0]
        ), patch.object(portable.subprocess, "run") as run, patch("builtins.print"):
            evidence = portable.scoped_install(portable.INSTALL_AUTHORIZATION, receipt,
                                               self.root, self.root / "output")
            self.assertEqual(evidence["state"], "ENVIRONMENT_BLOCKED")
            run.assert_not_called()

    def test_bundled_duplicate_mismatch_rejected(self):
        self.duplicates["swegemma"].write_bytes(b"changed")
        with self.assertRaises(ValueError):
            portable.select_install_wheels(self.root)

    def test_install_runs_only_five_paths_then_pip_check(self):
        receipt = self.root / "receipt.json"
        receipt.write_text("{}", encoding="utf-8")
        output = self.root / "output"
        with patch.object(portable.sys, "platform", "linux"), patch.object(
            portable.sys, "version_info", (3, 12)
        ), patch.object(portable, "verify_local_receipt"), patch.object(
            portable, "mounted_inventory", return_value=portable.wheelhouse_contract()[0]
        ), patch.object(
            portable, "direct_requirement_scope", return_value=portable.wheelhouse_contract()[2]
        ), patch.object(portable, "installed_versions", side_effect=[
            dict.fromkeys(portable.INSTALL_PACKAGES, "MISSING"), portable.INSTALL_PACKAGES
        ]), patch.object(portable.subprocess, "run", side_effect=[
            portable.subprocess.CompletedProcess([], 0, "", ""),
            portable.subprocess.CompletedProcess([], 0, "No broken requirements found.\n", ""),
        ]) as run, patch("builtins.print"):
            evidence = portable.scoped_install(portable.INSTALL_AUTHORIZATION, receipt, self.root, output)
        self.assertEqual(evidence["state"], "SCOPED_INSTALL_PASS")
        self.assertTrue((output / "install-evidence.json").is_file())
        self.assertEqual(run.call_count, 2)
        self.assertEqual(run.call_args_list[0].args[0], [
            portable.sys.executable, "-m", "pip", "install", "--no-deps", "--no-index", "--force-reinstall",
            *(str(self.root / self.pins[name]["filename"]) for name in portable.INSTALL_PACKAGES),
        ])
        self.assertEqual(run.call_args_list[1].args[0], [portable.sys.executable, "-m", "pip", "check"])

    def test_credential_names_removed_path_preserved(self):
        secrets = {name: "synthetic-value" for name in (
            "KAGGLE_SECRET", "KAGGLE_DATA_PROXY_URL", "access_token", "API_KEY", "MY_SECRET", "PASSWORD",
            "HF_HOME", "GOOGLE_APPLICATION_CREDENTIALS",
        )}
        source = {**secrets, "PATH": "/bin", "LD_LIBRARY_PATH": "/lib", "HOME": "/old",
                  "KAGGLE_DISABLE_GOOGLE_GENERATIVE_AI_INTEGRATION": "true"}
        env, removed = portable.child_environment(source, "/temporary")
        self.assertEqual(removed, sorted(secrets))
        self.assertTrue(set(secrets).isdisjoint(env))
        self.assertEqual(env["KAGGLE_DISABLE_GOOGLE_GENERATIVE_AI_INTEGRATION"], "true")
        self.assertEqual(env["PATH"], "/bin")
        self.assertEqual(env["LD_LIBRARY_PATH"], "/lib")
        self.assertEqual(env["HOME"], "/temporary")
        self.assertEqual(env["TMPDIR"], "/temporary")
        self.assertEqual(env["CUDA_VISIBLE_DEVICES"], "")
        self.assertEqual(source["HOME"], "/old")

    def test_inventory_mismatch_blocks_before_install(self):
        receipt = self.root / "receipt.json"
        receipt.write_text("{}", encoding="utf-8")
        with patch.object(portable.sys, "platform", "linux"), patch.object(
            portable.sys, "version_info", (3, 12)
        ), patch.object(portable, "verify_local_receipt"), patch.object(
            portable.subprocess, "run"
        ) as run, patch("builtins.print"):
            evidence = portable.scoped_install(portable.INSTALL_AUTHORIZATION, receipt,
                                               self.root, self.root / "output")
        self.assertEqual(evidence["state"], "ENVIRONMENT_BLOCKED")
        self.assertEqual(len(evidence["inventory"]), 5)
        run.assert_not_called()

    def test_reconcile_requires_install_evidence_before_pass(self):
        receipt = self.root / "receipt.json"
        receipt.write_text("{}", encoding="utf-8")
        with patch.object(portable, "verify_local_receipt"), patch("builtins.print") as printed:
            with self.assertRaises(FileNotFoundError):
                gate.reconcile(receipt, self.root)
            printed.assert_not_called()

    def valid_evidence(self, stdout="No broken requirements found.\n", code=0, stderr=""):
        inventory = portable.wheelhouse_contract()[0]
        check = portable.scoped_pip_check(portable.subprocess.CompletedProcess([], code, stdout, stderr),
                                          inventory, portable.INSTALL_PACKAGES)
        evidence = {"schema": 2, "local_receipt_sha256": "receipt", "inventory": inventory,
                    "selected_wheels": self.pins, "install_returncode": 0,
                    "pre_versions": dict.fromkeys(portable.INSTALL_PACKAGES, "MISSING"),
                    "post_versions": portable.INSTALL_PACKAGES, "removed_environment_names": [],
                    "pip_check": check}
        evidence["state"] = portable.install_state(evidence)
        return evidence

    def test_install_evidence_rejects_blocked_or_other_receipt(self):
        evidence = self.valid_evidence()
        path = self.root / "install-evidence.json"
        path.write_text(json.dumps(evidence), encoding="utf-8")
        self.assertEqual(portable.verify_install_evidence(path, "receipt"), evidence)
        for changes in ({"state": "ENVIRONMENT_BLOCKED"}, {"local_receipt_sha256": "other"},
                        {"post_versions": {}}, {"selected_wheels": {}}, {"inventory": []}, {"pip_check": None}):
            path.write_text(json.dumps(dict(evidence, **changes)), encoding="utf-8")
            with self.assertRaises(ValueError):
                portable.verify_install_evidence(path, "receipt")

    FOUR_FINDINGS = (
        "google-adk 1.36.1 requires google-cloud-bigquery-storage, which is not installed.\n"
        "google-genai 2.11.0 has requirement google-auth[requests]<3.0.0,>=2.48.1, but you have google-auth 2.47.0.\n"
        "google-genai 2.11.0 has requirement pydantic<3.0.0,>=2.12.5, but you have pydantic 2.12.3.\n"
        'google-cloud-aiplatform 1.148.1 has requirement google-genai<2.0.0,>=1.66.0; python_version >= "3.10", but you have google-genai 2.11.0.\n'
    )

    def test_reported_four_findings_are_deviations_not_harmlessness(self):
        evidence = self.valid_evidence(self.FOUR_FINDINGS, 1)
        self.assertEqual(evidence["state"], "SCOPED_INSTALL_PASS_WITH_OFFICIAL_DEVIATIONS")
        findings = evidence["pip_check"]["findings"]
        self.assertEqual(len(findings), 4)
        self.assertEqual({r["classification"] for r in findings}, {"OFFICIAL_ENVIRONMENT_DEVIATION"})
        self.assertEqual(findings[0]["kind"], "missing")
        self.assertEqual(findings[1]["installed_version"], "2.47.0")
        path = self.root / "install-evidence.json"
        path.write_text(json.dumps(evidence), encoding="utf-8")
        self.assertEqual(portable.verify_install_evidence(path, "receipt"), evidence)

    def test_omitted_wheel_dependency_is_divergent(self):
        evidence = self.valid_evidence(
            "google-adk 1.36.1 has requirement transformers>=5.13.1, but you have transformers 4.0.0.\n", 1)
        self.assertEqual(evidence["state"], "ENVIRONMENT_BLOCKED")
        self.assertEqual(evidence["pip_check"]["findings"][0]["classification"], "DIVERGENT_FROM_OFFICIAL")

    def test_unparseable_line_and_stderr_block(self):
        for stdout, stderr in (("unexpected output\n", ""), (self.FOUR_FINDINGS, "warning\n"),
                               (self.FOUR_FINDINGS + "\n", "")):
            with self.subTest(stdout=stdout, stderr=stderr):
                self.assertEqual(self.valid_evidence(stdout, 1, stderr)["state"], "ENVIRONMENT_BLOCKED")

    def test_out_of_scope_lines_retained_but_not_classified(self):
        raw = self.FOUR_FINDINGS + "moviepy 1.0 has requirement decorator<5, but you have decorator 5.1.0.\n"
        check = self.valid_evidence(raw, 1)["pip_check"]
        self.assertEqual(check["stdout"], raw)
        self.assertEqual(len(check["records"]), 5)
        self.assertEqual(len(check["findings"]), 4)
        self.assertEqual(check["out_of_scope_count"], 1)

    def test_reconcile_rejects_tampered_classification(self):
        receipt = self.root / "receipt.json"
        receipt.write_text("{}", encoding="utf-8")
        evidence = self.valid_evidence(self.FOUR_FINDINGS, 1)
        evidence["local_receipt_sha256"] = portable.sha(receipt.read_bytes())
        evidence["pip_check"]["findings"][0]["classification"] = "HARMLESS"
        (self.root / "install-evidence.json").write_text(json.dumps(evidence), encoding="utf-8")
        with patch.object(portable, "verify_local_receipt"), patch("builtins.print") as printed:
            with self.assertRaisesRegex(ValueError, "classification evidence mismatch"):
                gate.reconcile(receipt, self.root)
            printed.assert_not_called()

    def test_only_exact_observed_edge_can_be_deferred(self):
        from packaging.requirements import Requirement
        findings = self.valid_evidence(self.FOUR_FINDINGS, 1)["pip_check"]["findings"]
        requirement = Requirement("pydantic<3.0.0,>=2.12.5")
        self.assertTrue(portable.evidenced_deviation(findings, "google-genai", "2.11.0", requirement, "2.12.3"))
        for name, version, req, installed in (
            ("other", "2.11.0", requirement, "2.12.3"),
            ("google-genai", "2.11.1", requirement, "2.12.3"),
            ("google-genai", "2.11.0", requirement, "2.12.2"),
            ("google-genai", "2.11.0", Requirement("pydantic>=3"), "2.12.3"),
            ("google-genai", "2.11.0", requirement, None),
        ):
            self.assertFalse(portable.evidenced_deviation(findings, name, version, req, installed))

    def test_metadata_preflight_defers_only_reported_failures(self):
        from types import SimpleNamespace
        findings = self.valid_evidence(self.FOUR_FINDINGS, 1)["pip_check"]["findings"]
        distributions = {name: SimpleNamespace(version=version, metadata={}, requires=[])
                         for name, version in portable.INSTALL_PACKAGES.items()}
        distributions["google-adk"].requires = ["google-cloud-bigquery-storage>=2"]
        distributions["google-genai"].requires = ["pydantic<3.0.0,>=2.12.5"]
        distributions["pydantic"] = SimpleNamespace(version="2.12.3", metadata={}, requires=[])

        def distribution(name):
            if name not in distributions:
                raise portable.metadata.PackageNotFoundError(name)
            return distributions[name]

        with patch.object(portable.metadata, "distribution", side_effect=distribution):
            # pip omits constraints in missing-package lines. The same missing
            # identity at the same dependent version is still an exact edge.
            versions = portable.environment_preflight({}, findings)
            self.assertEqual(versions["pydantic"], "2.12.3")
            distributions["pydantic"].requires = ["unobserved-dependency>=1"]
            with self.assertRaises(portable.metadata.PackageNotFoundError):
                portable.environment_preflight({}, findings)


if __name__ == "__main__":
    unittest.main()
