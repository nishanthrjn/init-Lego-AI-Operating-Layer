"""Maintainer-run offline gate. Never installs or starts a Kaggle workload."""

from __future__ import annotations

import ast
import json
import subprocess
import sys
from pathlib import Path

from experiments.kaggle.comfyui_t2i_job_1.job_runner import pin_errors

ROOT = Path(__file__).resolve().parent
BASE = "71583827c09a192515b8a54c3a0cdb8cb3650e21"
EXPERIMENT = "experiments/kaggle/comfyui_t2i_job_1"
FILES = (
    f"{EXPERIMENT}/job_runner.py",
    f"{EXPERIMENT}/runtime_probe.py",
    f"{EXPERIMENT}/tests/test_job.py",
    "validate_kaggle_comfyui_t2i_job_1.py",
)
ALLOWED = frozenset(
    (
        *FILES,
        *(
            f"{EXPERIMENT}/{name}"
            for name in (
                "README.md",
                "job_manifest.json",
                "provenance.schema.json",
                "kaggle_job.ipynb",
            )
        ),
    )
)
ERRORS = (OSError, ValueError, subprocess.SubprocessError)


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    ).stdout


def scope() -> None:
    changed = set(git("diff", "--name-only", "-z", BASE).split("\0"))
    changed.update(git("ls-files", "--others", "--exclude-standard", "-z").split("\0"))
    changed.discard("")
    if changed - ALLOWED:
        raise ValueError(
            "out-of-scope changes: " + ", ".join(sorted(changed - ALLOWED))
        )


def grammar() -> None:
    for name in FILES:
        ast.parse((ROOT / name).read_text(encoding="utf-8"), feature_version=(3, 10))
    notebook = json.loads((ROOT / EXPERIMENT / "kaggle_job.ipynb").read_bytes())
    for cell in notebook["cells"]:
        if cell["cell_type"] == "code":
            ast.parse("".join(cell["source"]), feature_version=(3, 10))


def main() -> int:
    phase = "scope"

    def run(name: str, argv: list[str]) -> None:
        nonlocal phase
        phase = name
        print(f"\n[PHASE] {name}", flush=True)
        subprocess.run(argv, cwd=ROOT, check=True, timeout=900)

    try:
        print("[PHASE] scope", flush=True)
        scope()
        run(
            "product boundary",
            [
                "git",
                "diff",
                "--quiet",
                BASE,
                "--",
                "src",
                "packages",
                "examples",
                "comfyui-proof",
                "experiments/gemma4_competition",
                "experiments/kaggle/free_gpu_model_runtime",
                "experiments/kaggle/forgeai_model_quality_1",
            ],
        )
        for name, path in (
            ("experiment contracts", f"{EXPERIMENT}/tests"),
            ("architecture", "tests/architecture"),
        ):
            run(
                name,
                [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", path],
            )
        run(
            "strict typing",
            [
                sys.executable,
                "-m",
                "mypy",
                "--explicit-package-bases",
                "--platform",
                "linux",
                *FILES,
            ],
        )
        run(
            "lint",
            [
                sys.executable,
                "-m",
                "ruff",
                "check",
                "--no-cache",
                "--target-version",
                "py310",
                *FILES,
            ],
        )
        run(
            "format",
            [
                sys.executable,
                "-m",
                "ruff",
                "format",
                "--check",
                "--no-cache",
                "--target-version",
                "py310",
                *FILES,
            ],
        )
        phase = "Python 3.10 grammar"
        print(f"\n[PHASE] {phase}", flush=True)
        grammar()
        run("whitespace", ["git", "diff", "--check"])
        phase = "pin report"
        print(f"\n[PHASE] {phase}", flush=True)
        manifest = json.loads((ROOT / EXPERIMENT / "job_manifest.json").read_bytes())
        missing = pin_errors(manifest)
        print(
            "RUNNABLE ON KAGGLE: "
            + ("NO (missing: " + ", ".join(missing) + ")" if missing else "YES")
        )
    except ERRORS:
        print(f"FAIL [{phase}]; later phases NOT RUN")
        return 1
    print(
        "KAGGLE-COMFYUI-T2I-JOB-1 LOCAL CHECKS PASSED; "
        "NOT RUN ON KAGGLE; NO GPU ARTIFACT CLAIMED"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
