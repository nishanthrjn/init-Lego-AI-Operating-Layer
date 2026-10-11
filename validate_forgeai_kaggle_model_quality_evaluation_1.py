"""Maintainer-only offline checks. Does not launch a model or live notebook."""

from __future__ import annotations

import ast
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
EXPERIMENT = "experiments/kaggle/forgeai_model_quality_1"
BASELINE = "fc82cbd864c5a1e1e460a2168721f3b466c561fa"
VALIDATOR = Path(__file__).name


def git(*arguments: str) -> str:
    return subprocess.run(
        ["git", *arguments],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    ).stdout


def boundaries() -> None:
    changed = set(git("diff", BASELINE, "--name-only").splitlines())
    changed.update(git("ls-files", "--others", "--exclude-standard").splitlines())
    if any(
        path != VALIDATOR and not path.startswith(EXPERIMENT + "/") for path in changed
    ):
        raise ValueError("changes outside the experiment and validator")
    source = ROOT / EXPERIMENT
    baseline = json.loads((source / "contract-baseline.json").read_text())
    for name, expected in baseline.items():
        content = (ROOT / name).read_bytes().replace(b"\r\n", b"\n")
        if hashlib.sha256(content).hexdigest() != expected:
            raise ValueError("inspected contract changed; review frozen mirror")
    forbidden_imports = {
        "legoai",
        "legoai_engineering",
        "forgeai",
        "requests",
        "httpx",
        "urllib",
        "http",
        "socket",
        "kaggle",
        "huggingface_hub",
    }
    for path in source.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""]
            else:
                names = []
            if any(name.split(".")[0] in forbidden_imports for name in names):
                raise ValueError("production or external client import")
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                if node.func.id in {"eval", "exec", "compile"}:
                    raise ValueError("direct generated-code execution")
            if isinstance(node, ast.keyword) and node.arg == "shell":
                raise ValueError("shell execution prohibited")
        text = path.read_text(encoding="utf-8")
        for forbidden in (
            "https://",
            "http://",
            "0.0.0.0",
            "ngrok",
            "cloudflared",
            "localtunnel",
            "ssh -R",
        ):
            if forbidden in text:
                raise ValueError("external endpoint or tunnel")


def run(phase: str, command: list[str]) -> None:
    print(f"\n[PHASE] {phase}", flush=True)
    subprocess.run(command, cwd=ROOT, check=True, timeout=900)


def main() -> int:
    try:
        print("[PHASE] experiment scope, frozen contract sources and I/O boundary")
        boundaries()
        files = [
            str(path.relative_to(ROOT))
            for path in sorted((ROOT / EXPERIMENT).rglob("*.py"))
        ]
        files.append(VALIDATOR)
        run(
            "offline contracts, safety, scoring and reference fixtures",
            [
                sys.executable,
                "-m",
                "pytest",
                "-q",
                "-p",
                "no:cacheprovider",
                f"{EXPERIMENT}/tests",
            ],
        )
        run(
            "architecture",
            [
                sys.executable,
                "-m",
                "pytest",
                "-q",
                "-p",
                "no:cacheprovider",
                "tests/architecture",
            ],
        )
        manifest = (ROOT / EXPERIMENT / "manifest.json").read_bytes()
        package_digest = hashlib.sha256(manifest.replace(b"\r\n", b"\n")).hexdigest()
        print(f"Reviewed transfer manifest digest: {package_digest}", flush=True)
        run(
            "typing (Kaggle Linux)",
            [
                sys.executable,
                "-m",
                "mypy",
                "--explicit-package-bases",
                "--platform",
                "linux",
                *files,
            ],
        )
        run(
            "lint (portable Python syntax)",
            [
                sys.executable,
                "-m",
                "ruff",
                "check",
                "--target-version",
                "py310",
                *files,
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
                "--target-version",
                "py310",
                *files,
            ],
        )
        run("working whitespace", ["git", "diff", "--check"])
        run("staged whitespace", ["git", "diff", "--cached", "--check"])
    except (OSError, ValueError, subprocess.SubprocessError):
        print("FAIL: current phase; later phases NOT RUN")
        return 1
    print(
        "FORGEAI-KAGGLE-MODEL-QUALITY-EVALUATION-1 LOCAL CHECKS PASSED; "
        "MODEL QUALITY NOT MEASURED; NO LIVE EXECUTION AUTHORIZED"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
