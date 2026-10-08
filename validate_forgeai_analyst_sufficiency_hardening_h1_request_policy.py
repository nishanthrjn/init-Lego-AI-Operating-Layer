r"""Offline qualification: uv run python .\validate_forgeai_analyst_sufficiency_hardening_h1_request_policy.py.

FORGEAI-ANALYST-SUFFICIENCY-HARDENING-H1-REQUEST-POLICY: the deterministic
request-policy guard. No model, provider, Ollama or Docker. SAFETY-EVAL-3
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
BASE = "7fdee8f"  # hardening design recorded
SELF = "validate_forgeai_analyst_sufficiency_hardening_h1_request_policy.py"
PLAN = "planning/FORGEAI-ANALYST-SUFFICIENCY-HARDENING-H1-REQUEST-POLICY.md"
DESIGN = "planning/FORGEAI-ANALYST-SUFFICIENCY-HARDENING-DESIGN-1.md"
POLICY = "src/legoai_engineering/analyst/request_policy.py"
ENG_TEST = "tests/test_analyst_request_policy.py"
GATE = "evaluation/analyst_evidence_loop/policy_gate.py"
REPLAY = "evaluation/analyst_sufficiency_hardening_h1"
FORGE_TEST = "evaluation/tests/test_analyst_sufficiency_hardening_h1.py"
ALLOWED = {
    SELF,
    PLAN,
    "planning/LEGOAI-FORGEAI-MASTER-ROADMAP-2026.md",
    "packages/legoai-engineering/" + POLICY,
    "packages/legoai-engineering/" + ENG_TEST,
    "packages/legoai-engineering/tests/test_architecture.py",  # allowlist entry
    "packages/legoai-engineering/docs/CONSUMING.md",
    "packages/legoai-engineering/docs/analyst-sufficiency.md",
    "examples/forgeai/" + GATE,
    "examples/forgeai/" + REPLAY + "/__init__.py",
    "examples/forgeai/" + REPLAY + "/replay.py",
    "examples/forgeai/" + FORGE_TEST,
}
PROTECTED = (
    "src",
    "adrs",
    ".gitignore",
    "examples/forgeai/src",
    "packages/legoai-engineering/src/legoai_engineering/analyst/sufficiency.py",
    "packages/legoai-engineering/src/legoai_engineering/analyst/sufficiency_agent.py",
    "packages/legoai-engineering/src/legoai_engineering/analyst/sufficiency_definition.py",
    "packages/legoai-engineering/src/legoai_engineering/analyst/authorized.py",
    "packages/legoai-engineering/src/legoai_engineering/_json_document.py",
    "examples/forgeai/evaluation/analyst_evidence_loop/sequence.py",
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
SUPERSEDED = {
    "evaluation/tests/test_analyst_sufficiency_safety_live1.py"
    "::test_no_agent_prompt_parser_changes": "asserted no change anywhere under "
    "packages/ since eb67277; H1 adds an Engineering module. The Agent, prompt "
    "and parser files themselves are verified unchanged (H1 test 47, pins).",
}
COVERAGE = [
    ("1 supplied file path accepted", "supplied_file_path_accepted"),
    ("2 declared requirement path accepted", "declared_requirement_path_accepted"),
    ("3 bounded exact occurrence accepted", "bounded_exact_occurrence_accepted"),
    ("4 import-only path rejected", "unestablished_paths_rejected[app/settings.py]"),
    ("5 package-name path rejected", "unestablished_paths_rejected[pkg/tools.py]"),
    (
        "6 conventional-layout guess rejected",
        "unestablished_paths_rejected[config/settings.yaml]",
    ),
    (
        "7 invented path rejected",
        "unestablished_paths_rejected[app/generated/rules_table.json]",
    ),
    ("8 longer-path substring rejected", "longer_path_substring_rejected"),
    ("9 prefix collision rejected", "prefix_collision_rejected"),
    (
        "10 traversal escape rejected",
        "traversal_and_noncanonical_paths_cannot_be_requested",
    ),
    (
        "11 established, in scope, granted accepted",
        "established_in_scope_granted_accepted",
    ),
    ("12 established outside roots rejected", "established_outside_roots_rejected"),
    ("13 empty roots reject named requests", "empty_roots_reject_named_requests"),
    (
        "14-15 sensitive/operator-only without grant rejected",
        "non_ordinary_class_without_grant_rejected",
    ),
    (
        "16 granted non-ordinary class accepted",
        "non_ordinary_class_accepted_only_when_granted",
    ),
    ("17 unknown classification fails closed", "unknown_classification_fails_closed"),
    ("18 no hardcoded sensitive path behavior", "no_hardcoded_sensitive_path_behavior"),
    (
        "19 innocent attack vocabulary no effect",
        "innocent_attack_vocabulary_has_no_effect",
    ),
    (
        "20 application classification controls",
        "application_classification_controls_result",
    ),
    ("21-22 SOURCE_ROLE accepted without path", "source_role_accepted_without_path"),
    ("23 SOURCE_ROLE never rewritten", "source_role_never_rewritten"),
    ("24 intent clarification accepted", "intent_clarification_accepted"),
    ("25 known path as choice rejected", "known_path_as_clarification_choice_rejected"),
    (
        "26 path-looking text not rejected",
        "path_looking_text_not_a_known_identity_is_not_rejected",
    ),
    ("27-30 rejected assessment unchanged", "rejected_assessment_unchanged"),
    ("31 no retry", "no_retry_and_no_second_assessment"),
    ("32 pure: no model, no I/O", "pure_no_io_no_model_no_retry"),
    (
        "33/35 no acquisition, no progression",
        "no_progression_or_acquisition_after_rejection",
    ),
    ("34 no operator review on rejection", "rejected_decision_never_reaches_review"),
    (
        "accepted assessment forwarded unchanged",
        "accepted_assessment_reaches_review_unchanged",
    ),
    ("policy required; config strict", "gate_requires_policy_and_config_is_strict"),
    ("36 original baseline unchanged", "original_baseline_unchanged"),
    ("37 raw metrics unchanged", "raw_metrics_unchanged_and_copied"),
    ("38 guarded outcome separate", "guarded_outcome_is_separate"),
    ("39 fabricated requests rejected", "fabricated_requests_rejected_by_generic_rule"),
    (
        "40 forbidden classification rejected",
        "forbidden_classification_rejected_by_generic_policy",
    ),
    ("no model-improvement claim", "guard_does_not_claim_model_improvement"),
    (
        "d13 path clarification rejected",
        "path_valued_clarification_rejected_on_recorded_d13",
    ),
    ("41 no evaluator information needed", "no_evaluator_information_needed"),
    ("42 historical run files unmodified", "historical_run_files_never_modified"),
    ("43 no evaluator import in production", "production_imports_no_evaluator_package"),
    ("44 no case IDs in production", "no_case_ids_in_production"),
    ("45 no model/provider dependency", "no_model_or_provider_dependency"),
    ("46 no Core change", "no_core_change"),
    ("47 Agent/prompt/parser unchanged", "agent_prompt_parser_unchanged"),
    ("48 SAFETY-EVAL-2 unchanged", "safety_eval2_unchanged"),
    ("49 SAFETY-EVAL-3 unchanged", "safety_eval3_unchanged"),
    ("50 run custody unchanged", "run_custody_unchanged"),
    ("policy digest canonical", "policy_digest_is_canonical"),
    ("no keyword security", "no_keyword_security_in_source"),
    ("audit record safe", "audit_record_is_safe"),
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
    with tempfile.TemporaryDirectory(prefix="hardening-h1-") as directory:
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
            phase("hardening-design prerequisite and scope")
            design = (ROOT / DESIGN).read_text(encoding="utf-8")
            if "Selected target architecture: E" not in design:
                raise ValueError("hardening design 1 prerequisite missing")
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
                    SELF,
                ).splitlines()
            )
            if changed - ALLOWED:
                raise ValueError("unexpected files: " + repr(sorted(changed - ALLOWED)))
            for path in PROTECTED:
                if git("diff", "--name-only", BASE, "--", path):
                    raise ValueError("protected input changed: " + path)
            arch = git(
                "diff",
                BASE,
                "--",
                "packages/legoai-engineering/tests/test_architecture.py",
            )
            edits = [
                x
                for x in arch.splitlines()
                if x.startswith(("+", "-")) and not x.startswith(("+++", "---"))
            ]
            if any(x.startswith("-") for x in edits) or len(edits) > 9:
                raise ValueError("architecture test changed beyond the allowlist entry")
            done.append(current)
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
            production = (ENG / POLICY).read_text(encoding="utf-8") + (
                FORGE / GATE
            ).read_text(encoding="utf-8")
            replay_source = (FORGE / REPLAY / "replay.py").read_text(encoding="utf-8")
            if "eval3" in production or "eval3" in replay_source:
                raise ValueError("SAFETY-EVAL-3 used by H1")
            done.append(current)
            tests("Engineering request-policy tests", ENG, ENG_TEST, junit=True)
            tests("ForgeAI gate and replay tests", FORGE, FORGE_TEST, junit=True)
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
            )
            tests(
                "evidence-loop regressions",
                FORGE,
                "evaluation/tests/test_analyst_evidence_loop.py",
            )
            tests(
                "SAFETY-EVAL-2 and SAFETY-EVAL-3 scorer regressions",
                FORGE,
                "evaluation/tests/test_analyst_sufficiency_safety_eval2.py",
                "evaluation/tests/test_analyst_sufficiency_safety_eval3.py",
            )
            tests(
                "SAFETY-LIVE-1 harness and run-custody-2 regressions",
                FORGE,
                "evaluation/tests/test_analyst_sufficiency_safety_live1.py",
                "evaluation/tests/test_analyst_sufficiency_safety_live2_run_custody2.py",
            )
            tests(
                "Core architecture/import guards",
                ROOT,
                "tests/architecture/test_agent.py",
                "tests/architecture/test_import_boundaries.py",
            )
            phase("validator performs zero model/provider calls")
            if env["FORGEAI_LIVE1_OFFLINE"] != "1":
                raise ValueError("offline guard missing")
            done.append(current)
            phase("mypy")
            run(ENG, "mypy", "--cache-dir", str(temp / "mypy-eng"), POLICY, ENG_TEST)
            run(
                FORGE,
                "mypy",
                "--cache-dir",
                str(temp / "mypy-forge"),
                GATE,
                REPLAY,
                FORGE_TEST,
                str(ROOT / SELF),
            )
            done.append(current)
            phase("Ruff lint")
            run(ENG, "ruff", "check", "--no-cache", POLICY, ENG_TEST)
            run(
                FORGE,
                "ruff",
                "check",
                "--no-cache",
                GATE,
                REPLAY,
                FORGE_TEST,
                str(ROOT / SELF),
            )
            done.append(current)
            phase("Ruff format")
            run(ENG, "ruff", "format", "--check", "--no-cache", POLICY, ENG_TEST)
            run(
                FORGE,
                "ruff",
                "format",
                "--check",
                "--no-cache",
                GATE,
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
        "FORGEAI-ANALYST-SUFFICIENCY-HARDENING-H1-REQUEST-POLICY LOCAL VALIDATION "
        "PASSED — offline; no model; no Docker; no live run authorized"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
