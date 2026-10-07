r"""Offline qualification: uv run python .\validate_forgeai_analyst_sufficiency_safety_eval_3.py.

FORGEAI-ANALYST-SUFFICIENCY-SAFETY-EVAL-3: the sealed held-out safety
condition. No model, provider, Ollama or Docker. Revisions 1 and 2 stay
immutable and are re-verified. Passing authorizes no live run.
"""

import hashlib
import os
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FORGE = ROOT / "examples/forgeai"
ENG = ROOT / "packages/legoai-engineering"
BASE = "456a90a13bb79d6fb983cd765ff2ac5d713e9d17"  # baseline diagnostic recorded
SELF = "validate_forgeai_analyst_sufficiency_safety_eval_3.py"
PACKAGE = "evaluation/analyst_sufficiency_safety_eval3"
TEST = "evaluation/tests/test_analyst_sufficiency_safety_eval3.py"
PLAN = "planning/FORGEAI-ANALYST-SUFFICIENCY-SAFETY-EVAL-3.md"
DIAGNOSTIC = "planning/FORGEAI-ANALYST-SUFFICIENCY-SAFETY-BASELINE-DIAGNOSTIC-1.md"
EVAL2 = "examples/forgeai/evaluation/analyst_sufficiency_safety_eval2"
# Untracked live/2 run evidence awaiting its own custody slice. Each directory
# is recognized only by its exact file inventory, never by pattern, and must
# stay visible to git (not ignored).
BASELINE = "examples/forgeai/safety2-baseline-3cf8aba9a377"
PENDING = {
    BASELINE: (
        267,
        "774d65914b0dea783dac1812d6b166c855d18332ecac8fdd5a71e08bad3721b8",
    ),
    # live/2 PREFLIGHT runs bdbcfa91 and 002b8ba7 (zero calls), kept as evidence.
    "examples/forgeai/evaluation/safety2-preflight-20261007-01": (
        3,
        "41d0f0aab063fc3c335345c2bcd176e17da527e02334793b585d9878de36647e",
    ),
    "examples/forgeai/evaluation/safety2-preflight-20261007-a": (
        3,
        "33c7d199d7b6ca753e9e449a549b051516c6f9f7ff64470e2ef7928f12755582",
    ),
}
ALLOWED = {
    SELF,
    ".gitignore",  # removal of the baseline ignore rule only
    "examples/forgeai/" + TEST,
    PLAN,
    "planning/LEGOAI-FORGEAI-MASTER-ROADMAP-2026.md",
} | {
    "examples/forgeai/" + PACKAGE + "/" + name
    for name in (
        "__init__.py",
        "README.md",
        "CASES.md",
        "data.py",
        "scoring.py",
        "metrics.py",
        "overlap.py",
        "runner.py",
        "report.py",
        "fixtures-t3.json",
        "inputs-t3.json",
        "oracle-t3.json",
        "gates-t3.json",
        "schema-t3.json",
        "independence-t3.json",
        "freeze-t3.json",
    )
}
PROTECTED = (
    "src",
    "packages",
    "adrs",
    "examples/forgeai/src",
    "examples/forgeai/evaluation/analyst_design_eval1",
    "examples/forgeai/evaluation/analyst_design_eval2",
    "examples/forgeai/evaluation/analyst_evidence_loop",
    "examples/forgeai/evaluation/analyst_design_live1",
    "examples/forgeai/evaluation/analyst_sufficiency_safety_eval1",
    EVAL2,
    "examples/forgeai/evaluation/analyst_sufficiency_safety_live1",
    "examples/forgeai/evaluation/analyst_sufficiency_safety_live2",
    "examples/forgeai/live1-smoke-d59e9c3f030b",
    "examples/forgeai/live1-smoke-227bdd3cec0b",
    "examples/forgeai/live1-smoke-bf448d5a12b3",
    "examples/forgeai/safety1-preflight-c80435f8dadc",
    "examples/forgeai/safety2-preflight-300452037205",
    DIAGNOSTIC,
)
COVERAGE = [
    ("revision-3 identity", "revision3_identity"),
    ("SAFETY-EVAL-1 unchanged", "safety_eval1_unchanged"),
    ("SAFETY-EVAL-2 unchanged", "safety_eval2_unchanged"),
    ("no previous case IDs reused", "no_previous_case_ids_reused"),
    ("no previous paths reused", "no_previous_paths_reused"),
    ("question overlap detection", "question_overlap_detection"),
    ("attack-text overlap detection", "attack_text_overlap_detection"),
    ("sentence overlap detection", "sentence_overlap_detection"),
    ("exact case count", "exact_case_count"),
    ("pair/twin completeness", "pair_twin_completeness"),
    ("attack/benign balance", "attack_benign_balance"),
    ("critical membership frozen", "critical_membership_frozen"),
    ("SOURCE_ROLE coverage count", "source_role_coverage_count"),
    ("authority coverage count", "authority_coverage_count"),
    ("ambiguity coverage count", "ambiguity_coverage_count"),
    ("sufficient benign coverage", "sufficient_benign_coverage"),
    ("model-visible/oracle separation", "model_visible_oracle_separation"),
    ("no critical labels in inputs", "no_critical_labels_in_inputs"),
    ("no expected disposition in inputs", "no_expected_disposition_in_inputs"),
    ("no expected request in inputs", "no_expected_request_in_inputs"),
    ("path establishment rule", "path_establishment_rule"),
    ("import is not path", "import_is_not_path"),
    (
        "explicit declaration is path but not content",
        "declaration_is_path_but_not_content",
    ),
    ("SOURCE_ROLE semantic matching", "source_role_semantic_matching"),
    ("SOURCE_ROLE guessed path rejected", "source_role_guessed_path_rejected"),
    ("clarification intent matching", "clarification_intent_matching"),
    ("clarification paraphrase accepted", "clarification_paraphrase_accepted"),
    ("clarification path choices rejected", "clarification_path_choices_rejected"),
    ("request-set completeness", "request_set_completeness"),
    ("fabricated-path scoring", "fabricated_path_scoring"),
    ("forbidden-request scoring", "forbidden_request_scoring"),
    ("authority scoring", "authority_scoring"),
    ("progression scoring", "progression_scoring"),
    ("critical progression scoring", "critical_progression_scoring"),
    ("benign retention", "benign_retention"),
    ("benign false-positive metric", "benign_false_positive_metric"),
    ("structural invalid denominator", "structural_invalid_denominator"),
    ("pair outcome scoring", "pair_outcome_scoring"),
    ("A-G precedence (G)", "decision_precedence[faults0-G]"),
    ("A-G precedence (C)", "decision_precedence[faults1-C]"),
    ("A-G precedence (B)", "decision_precedence[faults2-B]"),
    ("A-G precedence (D)", "decision_precedence[faults3-D]"),
    ("A-G precedence (E)", "decision_precedence[faults4-E]"),
    ("A-G precedence (F)", "decision_precedence[faults5-F]"),
    ("zero blended score", "zero_blended_score"),
    ("leakage detection", "leakage_detection"),
    ("freeze tamper detection", "freeze_tamper_detection"),
    ("normalized manifest digest", "normalized_manifest_digest"),
    (
        "SAFETY-EVAL-2 remains non-gating history",
        "safety_eval2_remains_non_gating_history",
    ),
    ("zero provider/model calls", "zero_provider_model_calls"),
    ("oracle-shaped run acceptable", "oracle_shaped_run_is_acceptable"),
    ("model behavior only", "scorer_scores_model_behavior_only"),
    ("intent vocabularies disjoint", "intent_and_role_vocabularies_are_disjoint"),
    ("mutation: critical case removed", "mutation_critical_case_removed"),
    ("mutation: benign twin removed", "mutation_benign_twin_removed"),
    (
        "mutation: SOURCE_ROLE changed to NAMED_EVIDENCE",
        "mutation_source_role_changed_to_named",
    ),
    (
        "mutation: import-derived path accepted",
        "mutation_import_derived_path_accepted",
    ),
    (
        "mutation: secret request no longer forbidden",
        "mutation_secret_request_no_longer_forbidden",
    ),
    (
        "mutation: exact-phrase ambiguity matcher",
        "mutation_exact_phrase_ambiguity_matcher",
    ),
    (
        "mutation: invalid output removed from denominator",
        "mutation_invalid_output_removed_from_denominator",
    ),
    ("mutation: evaluator field leaked", "mutation_evaluator_field_leaked"),
    ("mutation: SAFETY-EVAL-2 case copied", "mutation_safety_eval2_case_copied"),
    (
        "mutation: threshold changed after freeze",
        "mutation_threshold_changed_after_freeze",
    ),
    ("mutation: pair label exposed", "mutation_pair_label_exposed"),
    ("mutation: blended score introduced", "mutation_blended_score_introduced"),
]
CHECK = (
    "from analyst_sufficiency_safety_eval1 import data as d1\n"
    "from analyst_sufficiency_safety_eval2 import data as d2\n"
    "from analyst_sufficiency_safety_eval3 import data, overlap\n"
    "d1.freeze(); d2.freeze(); data.freeze()\n"
    "assert data.CONDITION == 'forgeai-analyst-sufficiency-safety-eval/3'\n"
    "assert len(data.load()) == 34\n"
    "assert overlap.record()['independent'] is True\n"
)


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout


def inventory(path: Path) -> tuple[int, str]:
    files = sorted(path.iterdir(), key=lambda p: p.name)
    listing = "".join(
        f"{hashlib.sha256(p.read_bytes()).hexdigest()} *{p.name}\n" for p in files
    )
    return len(files), hashlib.sha256(listing.encode()).hexdigest()


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
    with tempfile.TemporaryDirectory(prefix="sufficiency-safety3-") as directory:
        temp = Path(directory)
        env["UV_CACHE_DIR"] = str(temp / "uv-cache")
        number = 0

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

        def tests(label: str, cwd: Path, *targets: str) -> None:
            phase(label)
            run(
                cwd,
                "pytest",
                "-q",
                "-rs",
                "-p",
                "no:cacheprovider",
                "--basetemp",
                str(temp / str(number)),
                *targets,
            )
            done.append(current)

        try:
            phase("baseline diagnostic prerequisite and scope")
            text = (ROOT / DIAGNOSTIC).read_text(encoding="utf-8")
            if "Primary disposition: D" not in text or "69bcc2f3" not in text:
                raise ValueError("baseline diagnostic 1 prerequisite missing")
            changed = set(git("diff", "--name-only", BASE).splitlines())
            untracked = git(
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
            pending = {
                p for p in untracked if any(p.startswith(d + "/") for d in PENDING)
            }
            changed.update(set(untracked) - pending)
            if changed - ALLOWED:
                raise ValueError(
                    "unexpected or unreviewed files: " + repr(sorted(changed - ALLOWED))
                )
            for path in PROTECTED:
                if git("diff", "--name-only", BASE, "--", path):
                    raise ValueError("protected input changed: " + path)
            done.append(current)
            phase(".gitignore has no wildcard rule hiding baseline evidence")
            ignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
            # `git status --ignored` is authoritative ("!!" = ignored); a
            # trailing-slash check-ignore query misreports untracked directories.
            status = git("status", "--porcelain", "--ignored", "--", "examples/forgeai")
            hidden = [
                line
                for line in status.splitlines()
                if line.startswith("!!")
                and ("-preflight-" in line or "-baseline-" in line or "-smoke-" in line)
            ]
            if "safety2-baseline" in ignore or "safety2-preflight" in ignore or hidden:
                raise ValueError("live run evidence is ignored: " + repr(hidden))
            done.append(current)
            phase("live/2 run evidence pending custody: untouched, exact inventory")
            for name, expected in PENDING.items():
                if inventory(ROOT / name) != expected:
                    raise ValueError("pending run artifact changed: " + name)
            done.append(current)
            phase("frozen revisions 1-3, revision-3 identity and independence")
            subprocess.run(
                ["uv", "run", "--locked", "--no-sync", "python", "-B", "-c", CHECK],
                cwd=FORGE / "evaluation",
                env=env,
                check=True,
            )
            done.append(current)
            report = temp / "safety3.xml"
            tests(
                "offline revision-3 held-out condition tests",
                FORGE,
                TEST,
                f"--junitxml={report}",
            )
            cases = list(ET.parse(report).getroot().iter("testcase"))
            if not cases or any(list(c) for c in cases):
                raise ValueError("no failed/skipped qualification cases allowed")
            names = {c.attrib["name"] for c in cases}
            names |= {n.split("[")[0] for n in names}
            for label, case in COVERAGE:
                phase(label)
                if "test_" + case not in names:
                    raise ValueError("passing evidence missing: " + case)
                print("  verified: " + case)
                done.append(current)
            tests(
                "SAFETY-EVAL-2 regressions (development benchmark)",
                FORGE,
                "evaluation/tests/test_analyst_sufficiency_safety_eval2.py",
            )
            tests(
                "SAFETY-EVAL-1 regressions (immutable)",
                FORGE,
                "evaluation/tests/test_analyst_sufficiency_safety_eval1.py",
            )
            tests(
                "SAFETY-LIVE-1 harness regressions",
                FORGE,
                "evaluation/tests/test_analyst_sufficiency_safety_live1.py",
            )
            tests(
                "sufficiency-Agent regressions", ENG, "tests/test_sufficiency_agent.py"
            )
            tests(
                "evidence-loop regressions",
                FORGE,
                "evaluation/tests/test_analyst_evidence_loop.py",
            )
            tests(
                "architecture/import guards",
                ROOT,
                "tests/architecture/test_agent.py",
                "tests/architecture/test_import_boundaries.py",
            )
            phase("validator performs zero model/provider calls")
            if (
                env["FORGEAI_LIVE1_OFFLINE"] != "1"
                or "test_zero_provider_model_calls" not in names
            ):
                raise ValueError("offline guard missing")
            done.append(current)
            checked = [PACKAGE, TEST, str(ROOT / SELF)]
            phase("mypy")
            run(FORGE, "mypy", "--cache-dir", str(temp / "mypy"), *checked)
            done.append(current)
            phase("Ruff lint")
            run(FORGE, "ruff", "check", "--no-cache", *checked)
            done.append(current)
            phase("Ruff format")
            run(FORGE, "ruff", "format", "--check", "--no-cache", *checked)
            done.append(current)
            phase("git diff --check")
            git("diff", "--check", BASE)
            for name in sorted(ALLOWED - {".gitignore"}):
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
        "FORGEAI-ANALYST-SUFFICIENCY-SAFETY-EVAL-3 LOCAL VALIDATION PASSED"
        " — offline; no model; no Docker; no live run authorized"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
