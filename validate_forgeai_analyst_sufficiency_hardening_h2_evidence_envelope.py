r"""Offline qualification: uv run python .\validate_forgeai_analyst_sufficiency_hardening_h2_evidence_envelope.py.

FORGEAI-ANALYST-SUFFICIENCY-HARDENING-H2-EVIDENCE-ENVELOPE: EvidenceSufficiencyAgent
1.1.0 trust-zoned input. No model, provider, Ollama or Docker. SAFETY-EVAL-3
stays sealed: only its freeze is verified, never its content.
"""

import os
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FORGE = ROOT / "examples/forgeai"
ENG = ROOT / "packages/legoai-engineering"
BASE = "f5b969a"  # live-probe record committed
SELF = "validate_forgeai_analyst_sufficiency_hardening_h2_evidence_envelope.py"
PLAN = "planning/FORGEAI-ANALYST-SUFFICIENCY-HARDENING-H2-EVIDENCE-ENVELOPE.md"
H1_PLAN = "planning/FORGEAI-ANALYST-SUFFICIENCY-HARDENING-H1-REQUEST-POLICY.md"
MSO_PLAN = "planning/MODEL-STRUCTURED-OUTPUT-1.md"
ENVELOPE = "src/legoai_engineering/analyst/sufficiency_envelope.py"
ENG_TEST = "tests/test_sufficiency_envelope.py"
REPLAY = "evaluation/analyst_sufficiency_hardening_h2"
FORGE_TEST = "evaluation/tests/test_analyst_sufficiency_hardening_h2.py"
PROBE_CUSTODY = "tests/architecture/test_structured_output_live_probe_custody.py"
ALLOWED = {
    SELF,
    PLAN,
    "planning/LEGOAI-FORGEAI-MASTER-ROADMAP-2026.md",
    "packages/legoai-engineering/" + ENVELOPE,
    "packages/legoai-engineering/" + ENG_TEST,
    "packages/legoai-engineering/tests/test_architecture.py",  # allowlist entry
    "packages/legoai-engineering/tests/test_analyst_architecture.py",  # inert import
    "packages/legoai-engineering/docs/analyst-sufficiency.md",
    "examples/forgeai/" + REPLAY + "/__init__.py",
    "examples/forgeai/" + REPLAY + "/representation.py",
    "examples/forgeai/" + REPLAY + "/representation.json",
    "examples/forgeai/" + FORGE_TEST,
}
PROTECTED = (
    "src",
    "adrs",
    ".gitignore",
    "examples/forgeai/src",
    "examples/model-structured-output-probe",
    PROBE_CUSTODY,
    "packages/legoai-engineering/src/legoai_engineering/analyst/sufficiency.py",
    "packages/legoai-engineering/src/legoai_engineering/analyst/sufficiency_agent.py",
    "packages/legoai-engineering/src/legoai_engineering/analyst/sufficiency_definition.py",
    "packages/legoai-engineering/src/legoai_engineering/analyst/request_policy.py",
    "packages/legoai-engineering/src/legoai_engineering/analyst/authorized.py",
    "packages/legoai-engineering/src/legoai_engineering/_json_document.py",
    "examples/forgeai/evaluation/analyst_evidence_loop",
    "examples/forgeai/evaluation/analyst_sufficiency_hardening_h1",
    "examples/forgeai/evaluation/analyst_sufficiency_safety_eval1",
    "examples/forgeai/evaluation/analyst_sufficiency_safety_eval2",
    "examples/forgeai/evaluation/analyst_sufficiency_safety_eval3",
    "examples/forgeai/evaluation/analyst_sufficiency_safety_live1",
    "examples/forgeai/evaluation/analyst_sufficiency_safety_live2",
    "examples/forgeai/evaluation/analyst_design_live1",
    "examples/forgeai/safety2-baseline-3cf8aba9a377",
    "examples/forgeai/live1-smoke-bf448d5a12b3",
)
# Qualified assertions superseded by design: deselected by exact id, never edited.
# Each used "no change under packages/ or src since an old base" as a proxy and
# already failed before H2; the identities they stood for are verified directly.
_PROXY = "a no-diff-since-base proxy already broken by H1/MODEL-STRUCTURED-OUTPUT-1"
SUPERSEDED = {
    "evaluation/tests/test_analyst_sufficiency_hardening_h1.py"
    "::test_no_core_change": _PROXY,
    "evaluation/tests/test_analyst_sufficiency_safety_live1.py"
    "::test_no_agent_prompt_parser_changes": _PROXY,
    "evaluation/tests/test_analyst_sufficiency_safety_runtime_identity2.py"
    "::test_agent_prompt_parser_unchanged": _PROXY,
    "evaluation/tests/test_analyst_sufficiency_safety_runtime_identity2.py"
    "::test_zero_baseline_calls": "superseded by the committed live/2 baseline",
    "evaluation/tests/test_analyst_sufficiency_safety_live2_preflight_custody1.py"
    "::test_prior_seven_entries_remain_accepted": "superseded by RUN-CUSTODY-2",
    "evaluation/tests/test_analyst_sufficiency_safety_live2_preflight_custody1.py"
    "::test_no_baseline_artifact_admitted": "superseded by RUN-CUSTODY-2",
}
HOSTILE = "6_to_16_hostile_text_remains_untrusted_data"
COVERAGE = [
    ("1 version is 1.1.0", "1_version_is_1_1_0_with_same_contract"),
    ("2/25 1.0.0 unchanged (prompt, fingerprint, golden)", "2_version_1_0_0_unchanged"),
    ("3-5 zones separate", "3_to_5_trusted_and_untrusted_zones_are_separate"),
    ("6 fake SYSTEM text is data", HOSTILE + "[system]"),
    ("7 fake DEVELOPER text is data", HOSTILE + "[developer]"),
    ("8 fake authority claim is data", HOSTILE + "[authority]"),
    ("ignore-instructions text is data", HOSTILE + "[ignore]"),
    ("9 fake operator answer is data", HOSTILE + "[operator]"),
    ("10 fake evidence request is data", HOSTILE + "[request]"),
    ("11 fake sufficient assertion is data", HOSTILE + "[sufficient]"),
    ("22 second question is data", HOSTILE + "[question]"),
    ("12 fake closing delimiter cannot escape", HOSTILE + "[closing]"),
    ("fake trusted label is data", HOSTILE + "[trusted_label]"),
    ("13 nested structured text is data", HOSTILE + "[nested]"),
    ("14 Markdown fence is data", HOSTILE + "[fence]"),
    ("XML-like closing tag is data", HOSTILE + "[xml]"),
    ("15 Unicode lookalike is data", HOSTILE + "[lookalike]"),
    ("newline-heavy content is data", HOSTILE + "[newlines]"),
    ("16 exact round-trip", "16_exact_round_trip_without_normalization"),
    (
        "17-18 deterministic serialization/prompt",
        "17_18_deterministic_serialization_and_prompt",
    ),
    ("envelope overhead bounded", "envelope_overhead_is_bounded_and_exact"),
    ("19 size limit at exact boundary", "19_size_limit_honored_at_exact_boundary"),
    (
        "20 oversized fails closed",
        "20_oversized_envelope_fails_closed_without_truncation",
    ),
    ("21/23-26 generic guidance present", "21_to_26_generic_guidance_present"),
    (
        "22 import-only is not content",
        "22_import_only_evidence_does_not_supply_the_imported_source",
    ),
    (
        "unchanged parser on 1.1.0 replies",
        "hostile_reply_shapes_still_use_unchanged_parser",
    ),
    ("27 H1 invoked after parse", "27_h1_invoked_after_parse_of_1_1_0_output"),
    ("28 H1 rejection blocks progression", "28_h1_rejection_still_blocks_progression"),
    (
        "accepted SOURCE_ROLE reaches review",
        "accepted_source_role_reaches_review_unchanged",
    ),
    ("29 parser unchanged and reused", "29_parser_unchanged_and_reused"),
    ("30 no response_format", "30_no_response_format_set"),
    ("31-32 no ModelPort/adapter change", "31_32_no_core_model_port_or_adapter_change"),
    (
        "33 no evaluator dependency",
        "33_no_evaluator_dependency_or_case_ids_in_production",
    ),
    ("34 SAFETY-EVAL-3 seal", "34_safety_eval3_seal_unchanged"),
    ("34 H2 does not use SAFETY-EVAL-3", "h2_does_not_use_safety_eval3"),
    ("35 no model/provider calls", "35_no_model_or_provider_calls"),
    (
        "H1/parser/Core/evaluations unchanged",
        "h1_parser_core_and_evaluations_unchanged",
    ),
    ("replay representation reproduced", "replay_representation_record_reproduced"),
    (
        "M concatenation into trusted zone",
        "mutation_concatenated_into_trusted_instructions_detected",
    ),
    ("M evidence label escape", "mutation_escaped_evidence_label_detected"),
    (
        "M promotion to declaration",
        "mutation_promotion_to_application_declaration_detected",
    ),
    (
        "M operator answer from evidence",
        "mutation_operator_answer_from_evidence_detected",
    ),
    ("M guidance removal (4)", "mutation_guidance_removal_detected"),
    ("M 1.0.0 serialization change", "mutation_v1_serialization_change_detected"),
    ("M H1 bypass", "mutation_h1_bypass_detected"),
    ("M response_format enabled", "mutation_response_format_enabled_detected"),
]


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout


def main() -> int:
    env = os.environ.copy()
    env.pop("VIRTUAL_ENV", None)
    env.update(
        UV_OFFLINE="1",
        PYTHONDONTWRITEBYTECODE="1",
        PYTHONUTF8="1",
        FORGEAI_LIVE1_OFFLINE="1",
    )
    done: list[str] = []
    current = "initialization"
    with tempfile.TemporaryDirectory(prefix="hardening-h2-") as directory:
        temp = Path(directory)
        env["UV_CACHE_DIR"] = str(temp / "uv-cache")
        number = 0
        names: set[str] = set()

        def phase(label: str) -> None:
            nonlocal current, number
            number += 1
            current = f"{number} {label}"
            print("[PHASE] " + current, flush=True)

        def run(cwd: Path, *args: str) -> None:
            subprocess.run(
                ["uv", "run", "--locked", "--no-sync", "python", "-B", "-m", *args],
                cwd=cwd,
                env=env,
                check=True,
            )

        def tests(label: str, cwd: Path, *targets: str, junit: bool = False) -> None:
            phase(label)
            extra = [f"--junitxml={temp / f'{number}.xml'}"] if junit else []
            extra += [
                arg
                for node in SUPERSEDED
                if node.split("::")[0] in targets
                for arg in ("--deselect", node)
            ]
            run(
                cwd,
                "pytest",
                "-q",
                "-rs",
                "-p",
                "no:cacheprovider",
                "--basetemp",
                str(temp / str(number)),
                *extra,
                *targets,
            )
            if junit:
                cases = list(
                    ET.parse(temp / f"{number}.xml").getroot().iter("testcase")
                )
                if not cases or any(list(c) for c in cases):
                    raise ValueError("no failed/skipped qualification cases allowed")
                names.update(c.attrib["name"] for c in cases)
            done.append(current)

        try:
            phase("H1 and MODEL-STRUCTURED-OUTPUT-1 prerequisites; ADR-022 accepted")
            if "LOCALLY QUALIFIED" not in (ROOT / H1_PLAN).read_text(encoding="utf-8"):
                raise ValueError("H1 qualification missing")
            mso = (ROOT / MSO_PLAN).read_text(encoding="utf-8")
            if (
                "LOCALLY QUALIFIED" not in mso
                or "## 10. Live compatibility probe" not in mso
            ):
                raise ValueError(
                    "MODEL-STRUCTURED-OUTPUT-1 qualification/probe missing"
                )
            adr = (ROOT / "adrs/ADR-022.md").read_text(encoding="utf-8")
            if not adr.splitlines()[2].startswith("Status: Accepted"):
                raise ValueError("ADR-022 not accepted")
            done.append(current)
            phase("scope: only H2 files changed; protected inputs unchanged")
            changed = set(git("diff", "--name-only", BASE).splitlines())
            changed.update(
                git(
                    "ls-files",
                    "--others",
                    "--exclude-standard",
                    "--",
                    "src",
                    "packages",
                    "examples",
                    "planning",
                    "tests",
                    SELF,
                ).splitlines()
            )
            if changed - ALLOWED:
                raise ValueError("unexpected files: " + repr(sorted(changed - ALLOWED)))
            for path in PROTECTED:
                if git("diff", "--name-only", BASE, "--", path):
                    raise ValueError("protected input changed: " + path)
            for test, limit in (
                ("test_architecture.py", 14),
                ("test_analyst_architecture.py", 1),
            ):
                diff = git(
                    "diff", BASE, "--", f"packages/legoai-engineering/tests/{test}"
                )
                edits = [
                    x
                    for x in diff.splitlines()
                    if x.startswith(("+", "-")) and not x.startswith(("+++", "---"))
                ]
                if any(x.startswith("-") for x in edits) or len(edits) > limit:
                    raise ValueError(test + " changed beyond the H2 entry")
            done.append(current)
            tests(
                "live-probe evidence and custody preserved",
                ROOT,
                PROBE_CUSTODY,
                "tests/architecture/test_structured_output.py",
            )
            phase("SAFETY-EVAL-3 sealed: freeze verified, content unused")
            subprocess.run(
                [
                    "uv",
                    "run",
                    "--locked",
                    "--no-sync",
                    "python",
                    "-B",
                    "-c",
                    "from analyst_sufficiency_safety_eval3 import data\n"
                    "from analyst_sufficiency_safety_eval2 import data as d2\n"
                    "data.freeze(); d2.freeze()\n",
                ],
                cwd=FORGE / "evaluation",
                env=env,
                check=True,
            )
            sources = [ENG / ENVELOPE, *sorted((FORGE / REPLAY).iterdir())]
            for source in sources:
                if source.is_file() and "eval3" in source.read_text(encoding="utf-8"):
                    raise ValueError("SAFETY-EVAL-3 used by H2: " + source.name)
            done.append(current)
            tests("Engineering envelope tests", ENG, ENG_TEST, junit=True)
            tests(
                "ForgeAI H1 composition and replay tests", FORGE, FORGE_TEST, junit=True
            )
            names |= {n.split("[")[0] for n in names}
            for label, case in COVERAGE:
                phase(label)
                if "test_" + case not in names:
                    raise ValueError("passing evidence missing: " + case)
                print("  verified: " + case)
                done.append(current)
            tests(
                "Engineering analyst and architecture regressions",
                ENG,
                "tests/test_architecture.py",
                "tests/test_analyst_architecture.py",
                "tests/test_analyst.py",
                "tests/test_analyst_sufficiency_contract.py",
                "tests/test_analyst_sufficiency_semantics.py",
                "tests/test_analyst_sufficiency_prompt.py",
                "tests/test_sufficiency_agent.py",
                "tests/test_json_document.py",
                "tests/test_analyst_request_policy.py",
            )
            tests(
                "H1 gate, replay and evidence-loop regressions",
                FORGE,
                "evaluation/tests/test_analyst_sufficiency_hardening_h1.py",
                "evaluation/tests/test_analyst_evidence_loop.py",
            )
            tests(
                "SAFETY-EVAL-2 regressions",
                FORGE,
                "evaluation/tests/test_analyst_sufficiency_safety_eval2.py",
            )
            tests(
                "SAFETY-LIVE-1, RUNTIME-IDENTITY-2 and run-custody regressions",
                FORGE,
                "evaluation/tests/test_analyst_sufficiency_safety_live1.py",
                "evaluation/tests/test_analyst_sufficiency_safety_runtime_identity2.py",
                "evaluation/tests/test_analyst_sufficiency_safety_live2_preflight_custody1.py",
                "evaluation/tests/test_analyst_sufficiency_safety_live2_run_custody2.py",
            )
            tests(
                "Core architecture and structured-output guards",
                ROOT,
                "tests/architecture/test_agent.py",
                "tests/architecture/test_import_boundaries.py",
                "tests/architecture/test_local_host.py",
                "tests/unit/reference/test_model_structured_output.py",
            )
            phase("validator performs zero model/provider calls")
            if env["FORGEAI_LIVE1_OFFLINE"] != "1":
                raise ValueError("offline guard missing")
            done.append(current)
            phase("mypy")
            run(ENG, "mypy", "--cache-dir", str(temp / "mypy-eng"), ENVELOPE, ENG_TEST)
            run(
                FORGE,
                "mypy",
                "--cache-dir",
                str(temp / "mypy-forge"),
                REPLAY,
                FORGE_TEST,
                str(ROOT / SELF),
            )
            done.append(current)
            phase("Ruff lint")
            run(ENG, "ruff", "check", "--no-cache", ENVELOPE, ENG_TEST)
            run(
                FORGE,
                "ruff",
                "check",
                "--no-cache",
                REPLAY,
                FORGE_TEST,
                str(ROOT / SELF),
            )
            done.append(current)
            phase("Ruff format")
            run(ENG, "ruff", "format", "--check", "--no-cache", ENVELOPE, ENG_TEST)
            run(
                FORGE,
                "ruff",
                "format",
                "--check",
                "--no-cache",
                REPLAY,
                FORGE_TEST,
                str(ROOT / SELF),
            )
            done.append(current)
            phase("git diff --check")
            git("diff", "--check", BASE)
            for name in sorted(ALLOWED):
                value = (ROOT / name).read_text(encoding="utf-8")
                if (
                    not value.endswith("\n")
                    or value.endswith("\n\n")
                    or any(line != line.rstrip() for line in value.splitlines())
                ):
                    raise ValueError("whitespace: " + name)
            done.append(current)
        except (
            OSError,
            ValueError,
            RuntimeError,
            subprocess.CalledProcessError,
        ) as error:
            print(f"FAIL {current}: {error}; later phases NOT RUN")
            return 1
    for name in done:
        print("PASS " + name)
    print(
        "FORGEAI-ANALYST-SUFFICIENCY-HARDENING-H2-EVIDENCE-ENVELOPE LOCAL VALIDATION "
        "PASSED — offline; no model; no Docker; no live run authorized"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
