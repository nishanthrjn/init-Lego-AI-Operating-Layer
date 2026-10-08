r"""Offline ADR-024 qualification: uv run python .\validate_remote_disclosure_governance_1.py.

REMOTE-DISCLOSURE-GOVERNANCE-1: `model-disclosure/1` values, processor
declarations, operator admissions, the pure evaluator and host-open
validation. No provider, network, Docker or credential is used; REMOTE stays
refused. Existing installed project environments are required; never syncs.
"""

import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BASE = "b8eb555"  # ADR-024 accepted; last commit before this slice
PRODUCTION = (
    "src/legoai/governance/disclosure.py",
    "src/legoai/runtime/api.py",
    "src/legoai/runtime/local.py",
)
TESTS = (
    "tests/unit/governance/test_disclosure.py",
    "tests/integration/composition/test_remote_disclosure.py",
    "tests/architecture/test_remote_disclosure.py",
    "tests/architecture/test_import_boundaries.py",
)
SELF = "validate_remote_disclosure_governance_1.py"
PYTHON_FILES = (*PRODUCTION, *TESTS, SELF)
ALLOWED = set(PYTHON_FILES) | {
    "docs/model-composition.md",
    "planning/LEGOAI-FORGEAI-MASTER-ROADMAP-2026.md",
}
UNIT = "tests/unit/governance/test_disclosure.py"
HOST = "tests/integration/composition/test_remote_disclosure.py"
ARCH = "tests/architecture/test_remote_disclosure.py"


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, encoding="utf-8", check=True
    ).stdout


def scope() -> None:
    changed = set(git("diff", "--name-only", BASE).splitlines())
    changed.update(
        git(
            "ls-files",
            "--others",
            "--exclude-standard",
            "--",
            ".",
            ":(exclude)examples/forgeai/.lq13-test-temp/**",
            ":(exclude)examples/forgeai/aq1q-r4-qwen2.5-coder-14b/**",
        ).splitlines()
    )
    if changed - ALLOWED:
        raise RuntimeError("unexpected scope: " + repr(sorted(changed - ALLOWED)))


def main() -> int:
    env = os.environ.copy()
    env.pop("VIRTUAL_ENV", None)
    env.update(UV_OFFLINE="1", PYTHONDONTWRITEBYTECODE="1")
    completed: list[str] = []
    phase = "1 scope guard (no ForgeAI, Engineering or adapter change)"
    cache = ROOT / ".pytest_cache"
    cache.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="disclosure-1-", dir=cache) as temporary:
        temp = Path(temporary)

        def run(name: str, args: list[str], cwd: Path = ROOT) -> None:
            nonlocal phase
            phase = name
            print("[PHASE] " + phase, flush=True)
            command = (
                [sys.executable, "-B", "-m"]
                if cwd == ROOT
                else [
                    "uv",
                    "run",
                    "--locked",
                    "--no-sync",
                    "--offline",
                    "python",
                    "-B",
                    "-m",
                ]
            )
            subprocess.run([*command, *args], cwd=cwd, env=env, check=True)
            completed.append(name)

        def tests(name: str, *selectors: str, cwd: Path = ROOT) -> None:
            run(
                name,
                [
                    "pytest",
                    "-q",
                    "-p",
                    "no:cacheprovider",
                    "--basetemp",
                    str(temp / name.split()[0]),
                    *selectors,
                ],
                cwd,
            )

        def focused(number: int, name: str, file: str, *names: str) -> None:
            tests(f"{number} {name}", *(file + "::" + n for n in names))

        try:
            print("[PHASE] " + phase, flush=True)
            scope()
            completed.append(phase)
            focused(
                2,
                "closed vocabulary and fact basis",
                UNIT,
                "test_vocabulary_is_exactly_model_disclosure_1",
                "test_declared_facts_cannot_claim_mechanical_verification",
                "test_fact_basis_rules",
                "test_source_reference_is_bounded_and_hidden_from_repr",
            )
            focused(
                3,
                "immutable exact values, no default admission",
                UNIT,
                "test_values_are_immutable",
                "test_no_default_admission_exists",
                "test_admission_shape_is_exact",
                "test_no_wildcard_repository",
                "test_repositories_are_named_exactly_for_repository_classes",
                "test_conditions_only_tighten",
                "test_admission_requires_one_condition_set_per_real_class",
                "test_endpoint_parts_normalize_https_only",
            )
            focused(
                4,
                "pure evaluator refusal matrix",
                UNIT,
                "test_admitted_when_everything_matches",
                "test_each_mismatch_refuses",
                "test_unclassified_is_never_admitted",
                "test_unadmitted_class_refuses_and_content_cannot_widen",
                "test_unadmitted_repository_refuses",
                "test_changed_declaration_revision_invalidates_admission",
                "test_unacceptable_condition_refuses",
                "test_ambiguous_admissions_refuse_rather_than_choose",
                "test_refusal_taxonomy_is_closed",
            )
            focused(
                5,
                "DERIVED_DIAGNOSTIC lineage",
                UNIT,
                "test_derived_diagnostic_requires_repository_content_in_admission",
                "test_derived_diagnostic_lineage_is_enforced",
            )
            focused(
                6,
                "unknown mandatory facts and the SYNTHETIC exception",
                UNIT,
                "test_unknown_mandatory_fact_refuses_for_real_content",
                "test_synthetic_permits_the_allowed_unknown_facts",
            )
            focused(
                7,
                "evaluator purity",
                UNIT,
                "test_evaluator_is_pure_and_deterministic",
                "test_admitted_decision_must_name_its_admission",
            )
            tests("8 all disclosure governance tests", UNIT)
            focused(
                9,
                "REMOTE still refused with valid disclosure",
                HOST,
                "test_remote_still_refused_with_valid_declaration_and_admission",
                "test_remote_still_refused_without_disclosure",
            )
            focused(
                10,
                "LOCAL unchanged",
                HOST,
                "test_disclosure_is_optional_and_defaults_to_none",
                "test_valid_disclosure_with_local_selection_opens_inertly",
                "test_ollama_and_openai_local_do_not_need_disclosure",
            )
            tests("11 host-open disclosure validation", HOST)
            tests(
                "12 disclosure ownership and boundaries",
                ARCH,
                "tests/architecture/test_import_boundaries.py",
                "tests/architecture/test_local_host.py",
                "tests/architecture/test_openai_compatible.py",
            )
            tests(
                "13 runtime, OpenAI-compatible, Ollama and governed Model",
                "tests/integration/composition/test_local_host.py",
                "tests/integration/composition/test_model_selection.py",
                "tests/integration/composition/test_openai_compatible.py",
                "tests/integration/composition/test_model_governed.py",
                "tests/unit/reference/test_openai_compatible.py",
                "tests/unit/reference/test_model.py",
            )
            tests(
                "14 Core unit, integration and contract regressions",
                "tests/unit",
                "tests/integration",
                "tests/contract",
            )
            tests(
                "15 DocuMind regressions",
                "tests/unit",
                "tests/integration",
                cwd=ROOT / "examples/documind",
            )
            tests(
                "16 ForgeAI regressions",
                "tests/test_architecture.py",
                "tests/test_worker.py",
                "tests/test_review.py",
                "tests/test_rework.py",
                cwd=ROOT / "examples/forgeai",
            )
            run(
                "17 mypy",
                [
                    "mypy",
                    "--cache-dir",
                    str(temp / "mypy"),
                    "src",
                    UNIT,
                    HOST,
                    ARCH,
                    str(Path(__file__).resolve()),
                ],
            )
            run("18 Ruff lint", ["ruff", "check", "--no-cache", *PYTHON_FILES])
            run(
                "19 Ruff format",
                ["ruff", "format", "--check", "--no-cache", *PYTHON_FILES],
            )
            phase = "20 git diff check"
            print("[PHASE] " + phase, flush=True)
            git("diff", "--check", BASE)
            completed.append(phase)
        except (subprocess.CalledProcessError, RuntimeError, OSError) as error:
            for name in completed:
                print("PASS " + name)
            print("FAIL " + phase + ": " + str(error))
            return 1
    for name in completed:
        print("PASS " + name)
    print(
        "REMOTE-DISCLOSURE-GOVERNANCE-1 LOCAL VALIDATION PASSED - offline; "
        "REMOTE still refused; no provider, network or credential"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
