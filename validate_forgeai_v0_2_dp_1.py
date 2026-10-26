"""Maintainer-run DP gate: offline checks, then Windows real sandbox; no live models."""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parent
FORGEAI = ROOT / "examples/forgeai"
BASE = "5bc29f5d21b8118149166137249d9c348d57cd7e"
SELF = "validate_forgeai_v0_2_dp_1.py"
ALLOWED = frozenset(
    {
        SELF,
        "examples/forgeai/README.md",
        "examples/forgeai/tests/test_dp_packaging.py",
    }
)
PRESERVED = (
    "packages",
    "src",
    "scripts",
    "experiments",
    "planning",
    "adrs",
    "examples/forgeai/src/forgeai",
    "examples/forgeai/tests",
    ":(exclude)examples/forgeai/tests/test_dp_packaging.py",
)
# Maintainer-approved exclusions: these historical tests do not all honor
# LEGOAI_QUALIFY_* and would execute Docker or build/install wheels on Windows.
INTEGRATION_FILES = (
    "tests/test_end_to_end.py",
    "tests/test_clean_install.py",
    "evaluation/tests/test_lq1_fixtures_docker.py",
    "evaluation/tests/test_lq1_diagnostics_docker.py",
)
OFFLINE_SELECTION = "not real_docker and not real_sandbox"


def git_phase(phase: str, env: dict[str, str]) -> None:
    def git(*args: str) -> str:
        return subprocess.check_output(
            ["git", *args],
            cwd=ROOT,
            env=env,
            text=True,
            encoding="utf-8",
            timeout=30,
        )

    if phase == "scope":
        changed = (
            set(git("diff", "--name-only", BASE).splitlines())
            | set(git("diff", "--cached", "--name-only", BASE).splitlines())
            | set(git("ls-files", "--others", "--exclude-standard").splitlines())
        )
        if changed - ALLOWED:
            raise ValueError("outside slice scope: " + repr(sorted(changed - ALLOWED)))
    elif phase == "preservation":
        git("diff", "--quiet", BASE, "--", *PRESERVED)
        git("diff", "--cached", "--quiet", BASE, "--", *PRESERVED)
    elif phase == "whitespace":
        git("diff", "--check")
        git("diff", "--cached", "--check")
    else:
        raise ValueError("unsupported internal phase")


def acceptance_report(stdout: str, scenario: str) -> str:
    """Require a successful final replay report and accept's summary ordering."""
    if scenario not in {"accept", "rework"}:
        raise ValueError("unsupported acceptance scenario")
    lines = stdout.splitlines()
    reports = [line for line in lines if line.startswith("forgeai-report: ")]
    if len(reports) != 1 or stdout.rstrip().splitlines()[-1] != reports[0]:
        raise ValueError("expected exactly one final forgeai-report line")
    value: object = json.loads(reports[0].removeprefix("forgeai-report: "))
    if (
        not isinstance(value, dict)
        or value.get("disposition") != "SUCCEEDED"
        or value.get("model_quality") != "NOT_APPLICABLE_REPLAY"
        or value.get("rework_used") is not (scenario == "rework")
    ):
        raise ValueError("acceptance demo did not report the required replay outcome")
    if scenario == "accept":
        summaries = [
            index
            for index, line in enumerate(lines)
            if line == "repository guidance: discovered (read-only; confirm below)"
        ]
        headers = [
            index
            for index, line in enumerate(lines)
            if line == "ForgeAI v0.1: supervised local engineering task"
        ]
        if len(summaries) != 1 or len(headers) != 1 or summaries[0] >= headers[0]:
            raise ValueError("expected one guidance summary before the run header")
    return reports[0]


def require_real_results(path: Path) -> None:
    """A successful pytest exit with skipped real tests is not qualification."""
    cases = list(ElementTree.parse(path).getroot().iter("testcase"))
    if not cases or any(
        case.find(tag) is not None
        for case in cases
        for tag in ("skipped", "failure", "error")
    ):
        raise ValueError("real phase requires executed, passing tests with no skips")


def main() -> int:
    env = os.environ.copy()
    env.pop("VIRTUAL_ENV", None)
    for name in tuple(env):
        if name.startswith("LEGOAI_QUALIFY_"):
            env.pop(name)
    env.pop("LEGOAI_SANDBOX_CHECKS_IMAGE", None)
    env["UV_OFFLINE"] = "1"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    # Match the existing pilot validator: its projection lives at repository root.
    import_paths = (str(ROOT), str(FORGEAI), str(FORGEAI / "src"))
    env["PYTHONPATH"] = os.pathsep.join(import_paths)
    env["MYPYPATH"] = str(ROOT)
    phase = "setup"
    uv = shutil.which("uv")

    def project(name: str, *args: str) -> None:
        nonlocal phase
        phase = name
        if uv is None:
            raise ValueError("uv required; existing locked environments required")
        print("\n[PHASE] " + name, flush=True)
        subprocess.run(
            [uv, "run", "--locked", "--offline", "--no-sync", "python", *args],
            cwd=FORGEAI,
            env=env,
            check=True,
        )

    def real_project(name: str, *args: str) -> None:
        with TemporaryDirectory(prefix="forgeai-dp-results-") as temporary:
            results = Path(temporary) / "results.xml"
            project(name, *args, "--junitxml=" + str(results))
            require_real_results(results)

    try:
        if len(sys.argv) == 3 and sys.argv[1] == "--phase":
            phase = sys.argv[2]
            git_phase(phase, env)
            return 0
        if len(sys.argv) != 1:
            raise ValueError("no operator arguments supported")
        validator = str(ROOT / SELF)
        project("scope", validator, "--phase", "scope")
        project("preservation", validator, "--phase", "preservation")
        pytest = ("-m", "pytest", "-q", "-p", "no:cacheprovider")
        phase = "offline exclusion paths"
        for path in INTEGRATION_FILES:
            if not (FORGEAI / path).is_file():
                raise ValueError("excluded test file missing: " + path)
        print(
            "Offline regression exclusions (maintainer approved): "
            + ", ".join(INTEGRATION_FILES)
            + "; selection: "
            + OFFLINE_SELECTION,
            flush=True,
        )
        print(
            "EXCLUDED: evaluation/tests (historical evaluation harnesses; "
            "not touched by this slice; pre-existing failures tracked separately "
            "as FORGEAI-EVAL-HARNESS-TRIAGE-1)",
            flush=True,
        )
        print(
            "Product tests only; pytest reports skipped/deselected counts. "
            "This is not full integration or clean-install qualification.",
            flush=True,
        )
        project(
            "product suite, offline regressions only",
            *pytest,
            "tests",
            *("--ignore=" + path for path in INTEGRATION_FILES),
            "-k",
            OFFLINE_SELECTION,
        )
        project("strict typing", "-m", "mypy", "src", "tests", validator)
        project(
            "lint",
            "-m",
            "ruff",
            "check",
            "--no-cache",
            "--config",
            str(FORGEAI / "pyproject.toml"),
            "--config",
            'lint.isort.known-first-party = ["forgeai", "forgeai_eval", "scripts"]',
            "src",
            "tests",
            "demo.py",
        )
        project(
            "lint validator",
            "-m",
            "ruff",
            "check",
            "--no-cache",
            "--config",
            str(ROOT / "pyproject.toml"),
            validator,
        )
        project(
            "format",
            "-m",
            "ruff",
            "format",
            "--check",
            "--no-cache",
            "--config",
            str(FORGEAI / "pyproject.toml"),
            "src",
            "tests",
            "demo.py",
        )
        project(
            "format validator",
            "-m",
            "ruff",
            "format",
            "--check",
            "--no-cache",
            "--config",
            str(ROOT / "pyproject.toml"),
            validator,
        )
        project("whitespace", validator, "--phase", "whitespace")

        if os.name != "nt":
            print("REAL PHASES NOT RUN (requires Windows Docker Desktop)")
            print(
                "FORGEAI-V0.2-DP OFFLINE CHECKS PASSED; "
                "REAL PHASES NOT RUN; NOT QUALIFIED"
            )
            return 0
        project(
            "Docker engine and pinned PYTHON_CHECKS image readiness; metadata only",
            "-c",
            "import shutil,sys; from pathlib import Path; "
            "from legoai_engineering.sandbox.docker import "
            "DockerSandbox,DockerSandboxConfig,SandboxImage; "
            "from legoai_engineering.sandbox.errors import SandboxError; "
            "cli=shutil.which('docker'); "
            "sys.exit('Docker CLI missing: make the existing Docker Desktop CLI available') "
            "if cli is None else None; "
            "sandbox=DockerSandbox(DockerSandboxConfig(Path(cli),SandboxImage.PYTHON_CHECKS)); "
            "\ntry:\n sandbox.verify_ready()\nexcept SandboxError as error:\n "
            "print('Docker prerequisite failed:',error.reason.value); "
            "print('Ensure Docker Desktop Linux engine is running and the already-qualified "
            "PYTHON_CHECKS image is present. No automatic start/build/pull/install.'); "
            "sys.exit(1)",
        )
        real_project(
            "real end-to-end and offline clean install",
            *pytest,
            "tests/test_end_to_end.py",
            "tests/test_clean_install.py",
        )
        # Synthetic local TLS server plus real checks; no live provider/model.
        env["LEGOAI_QUALIFY_FORGEAI_REMOTE"] = "1"
        try:
            real_project(
                "previously deselected real-Docker regressions",
                *pytest,
                "tests",
                *("--ignore=" + path for path in INTEGRATION_FILES),
                "--ignore=tests/test_v0_2_real_sandbox_qualification.py",
                "-k",
                "real_docker or real_sandbox",
            )
        finally:
            env.pop("LEGOAI_QUALIFY_FORGEAI_REMOTE", None)
        env["LEGOAI_QUALIFY_FORGEAI_V02_SANDBOX"] = "1"
        try:
            for label, selector in (
                ("successful confirmed-context real checks", "success"),
                ("one real check-triggered rework", "check_rework"),
                ("negative controls: zero Docker workloads", "negative_pre_effect"),
            ):
                real_project(
                    label,
                    *pytest,
                    "tests/test_v0_2_real_sandbox_qualification.py",
                    "-k",
                    selector,
                )
        finally:
            env.pop("LEGOAI_QUALIFY_FORGEAI_V02_SANDBOX", None)
        # test_clean_install.py: context confirmation + approval per attempt.
        for scenario, answers in (
            ("accept", "y\ny\n"),
            ("rework", "y\ny\ny\ny\n"),
        ):
            phase = "acceptance demo: " + scenario
            print("\n[PHASE] " + phase, flush=True)
            assert uv is not None
            command = [
                uv,
                "run",
                "--locked",
                "--offline",
                "--no-sync",
                "python",
                "demo.py",
                scenario,
            ]
            if scenario == "accept":
                command.append("--discover-guidance")
            command.append("--json-report")
            completed = subprocess.run(
                command,
                cwd=FORGEAI,
                env=env,
                input=answers,
                text=True,
                encoding="utf-8",
                capture_output=True,
                timeout=600,
                check=False,
            )
            try:
                completed.check_returncode()
                report = acceptance_report(completed.stdout, scenario)
            except ValueError, subprocess.SubprocessError:
                print(completed.stdout)
                print(completed.stderr, file=sys.stderr)
                raise
            print(report, flush=True)

    except (
        OSError,
        ValueError,
        ElementTree.ParseError,
        subprocess.SubprocessError,
    ) as error:
        print(f"FAIL [{phase}] {error}; later phases NOT RUN")
        return 1
    print(
        "FORGEAI-V0.2-DP LOCALLY QUALIFIED; "
        "REPLAY MODELS AND REAL SANDBOXED CHECKS; "
        "MODEL QUALITY UNQUALIFIED; NO LIVE MODEL EXECUTION"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
