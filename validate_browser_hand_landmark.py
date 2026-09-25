"""User-run qualification launcher. Never installs, fixes source, or changes Git state."""
from __future__ import annotations

import ast
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
PACKAGE = ROOT / "packages" / "legoai-browser-hand-landmarks"


class ValidationFailure(Exception):
    def __init__(self, message: str, code: int = 1) -> None:
        super().__init__(message)
        self.code = code if code != 0 else 1


def run(command: list[str], cwd: Path = PACKAGE) -> None:
    print("+ " + subprocess.list2cmdline(command), flush=True)
    try:
        result = subprocess.run(command, cwd=cwd, shell=False, check=False)
    except OSError as error:
        raise ValidationFailure("Could not start required command: " + str(error)) from error
    if result.returncode:
        raise ValidationFailure("Command failed.", result.returncode)


def npm_cli(node: str) -> Path:
    npm = shutil.which("npm.cmd" if os.name == "nt" else "npm")
    if npm is None:
        raise ValidationFailure("npm is missing. Install Node.js 24 and reopen the terminal.")
    resolved = Path(npm).resolve()
    candidates = [
        resolved.parent / "node_modules" / "npm" / "bin" / "npm-cli.js",
        Path(node).resolve().parent / "node_modules" / "npm" / "bin" / "npm-cli.js",
    ]
    if resolved.name == "npm-cli.js":
        candidates.insert(0, resolved)
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise ValidationFailure("Cannot locate npm-cli.js beside Node/npm; no shell fallback is used.")


def python_boundaries() -> None:
    # No Python production change: inspect packaging/import boundaries, not the
    # unrelated full Python test suite. Browser qualification does not qualify M8.3.
    import tomllib

    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    project = data["project"]
    if any(any(word in dependency.lower() for word in ("mediapipe", "onnx", "browser-hand"))
           for dependency in project["dependencies"]):
        raise ValidationFailure("Browser dependency leaked into Python Core.")
    wheel = data["tool"]["hatch"]["build"]["targets"]["wheel"]["packages"]
    if wheel != ["src/legoai"]:
        raise ValidationFailure("Python wheel boundary changed; review required.")
    for source in (ROOT / "src" / "legoai").rglob("*.py"):
        tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
        for item in ast.walk(tree):
            modules: list[str] = []
            if isinstance(item, ast.Import):
                modules = [alias.name for alias in item.names]
            elif isinstance(item, ast.ImportFrom):
                modules = [item.module or ""]
            if any(name.split(".")[0] in {"mediapipe", "onnxruntime", "javascript"} for name in modules):
                raise ValidationFailure("Browser import found in Python Core.")
    print("Python production unchanged by this slice: packaging/import boundary inspection only.", flush=True)


def main() -> int:
    completed: list[str] = []
    current = "environment"
    print("=" * 60)
    print("Browser Hand-Landmark Local Inference Validation")
    print("=" * 60, flush=True)
    try:
        if sys.version_info < (3, 11):
            raise ValidationFailure("Python 3.11+ is required for this standard-library launcher.")
        print("[PHASE 1] environment", flush=True)
        run([sys.executable, "--version"], ROOT)
        node = shutil.which("node")
        git = shutil.which("git")
        if node is None or git is None:
            raise ValidationFailure("Node.js 24 and Git must be installed and on PATH.")
        cli = npm_cli(node)
        npm = [node, str(cli)]
        run([node, "--version"])
        run([node, "-e", "if (process.versions.node.split('.')[0] !== '24') { console.error('Node.js 24 is required'); process.exit(1); }"])
        run([*npm, "--version"])
        completed.append(current)

        def phase(number: int, name: str, scripts: list[str]) -> None:
            nonlocal current
            current = name
            print(f"\n[PHASE {number}] {name}", flush=True)
            for script in scripts:
                run([*npm, "run", script])
            completed.append(name)

        current = "dependency integrity"
        print("\n[PHASE 2] dependency integrity (read-only installed-tree check)", flush=True)
        if not (PACKAGE / "node_modules").is_dir():
            raise ValidationFailure(
                "Dependencies are not installed. Explicit one-time setup:\n"
                "npm.cmd --prefix packages/legoai-browser-hand-landmarks ci --ignore-scripts\n"
                "Then rerun this launcher. Nothing was installed automatically."
            )
        run([node, "tools/check-installed.mjs"])
        run([*npm, "ls", "--all"])
        completed.append(current)
        phase(3, "TypeScript", ["typecheck"])
        phase(4, "static checks", ["static"])
        phase(5, "contract and asset tests", ["test:compile", "test:contracts"])
        phase(6, "worker/backpressure/lifecycle tests", ["test:lifecycle"])
        phase(7, "local-only network tests", ["test:network"])
        phase(8, "production build", ["build"])
        current = "architecture checks"
        print("\n[PHASE 9] architecture checks", flush=True)
        run([node, "tools/static-check.mjs", "--architecture"])
        completed.append(current)
        current = "affected Python checks"
        print("\n[PHASE 10] affected Python checks", flush=True)
        python_boundaries()
        completed.append(current)
        current = "git diff check"
        print("\n[PHASE 11] git diff check", flush=True)
        run([git, "diff", "--check"], ROOT)
        completed.append(current)
    except (ValidationFailure, OSError, ValueError, KeyError) as error:
        print("\n" + "=" * 60)
        for phase_name in completed:
            print("[PASS] " + phase_name)
        print("[FAIL] " + current + ": " + str(error), file=sys.stderr)
        print("VALIDATION FAILED — later required phases were NOT RUN.")
        return error.code if isinstance(error, ValidationFailure) else 1
    except KeyboardInterrupt:
        print("\nVALIDATION INTERRUPTED — not qualified.", file=sys.stderr)
        return 130
    print("\n" + "=" * 60)
    for phase_name in completed:
        print("[PASS] " + phase_name)
    print("AUTOMATED LOCAL VALIDATION PASSED")
    print("MANUAL BROWSER VALIDATION STILL REQUIRED")
    print("Start: npm.cmd --prefix packages/legoai-browser-hand-landmarks run dev")
    print("Open: http://127.0.0.1:5174")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
