"""Export only the maintained starter and reduced, standalone Chat contracts."""

from __future__ import annotations

import argparse
import ast
import os
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples" / "assessment_starter"
BACKEND_FILES = [
    "src/assessment_starter/__init__.py",
    "src/assessment_starter/api/__init__.py",
    "src/assessment_starter/application/__init__.py",
    "src/assessment_starter/core/__init__.py",
    "pyproject.toml",
    ".env.example",
    "src/assessment_starter/core/config.py",
    "src/assessment_starter/fixtures.py",
    "src/assessment_starter/application/answer_service.py",
    "src/assessment_starter/api/schemas.py",
    "src/assessment_starter/api/routes.py",
    "src/assessment_starter/main.py",
    "tests/conftest.py",
    "tests/test_answer_service.py",
    "tests/test_api.py",
]
FRONTEND_FILES = [
    "package.json",
    "tsconfig.json",
    "vite.config.ts",
    "eslint.config.js",
    "index.html",
    "src/main.tsx",
    "src/App.tsx",
    "src/App.test.tsx",
    "src/test/setup.ts",
    "vitest.config.ts",
    "src/style.css",
    "package-lock.json",
]
CONTRACTS = '''"""Standalone Chat-only values, deliberately reduced from the source platform."""

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol


class ChatRole(StrEnum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


@dataclass(frozen=True, slots=True)
class ChatMessage:
    role: ChatRole
    content: str

    def __post_init__(self) -> None:
        if type(self.role) is not ChatRole or type(self.content) is not str:
            raise TypeError("ChatMessage requires ChatRole and text")


@dataclass(frozen=True, slots=True)
class ChatRequest:
    messages: tuple[ChatMessage, ...]

    def __post_init__(self) -> None:
        if type(self.messages) is not tuple or not self.messages:
            raise ValueError("ChatRequest requires a non-empty immutable tuple")
        if any(type(message) is not ChatMessage for message in self.messages):
            raise TypeError("ChatRequest requires ChatMessage values")


@dataclass(frozen=True, slots=True)
class ChatResult:
    content: str

    def __post_init__(self) -> None:
        if type(self.content) is not str:
            raise TypeError("ChatResult requires text")


class ModelPort(Protocol):
    async def chat(self, request: ChatRequest) -> ChatResult: ...


class FixedModel:
    """Offline fixed response; one independent instance per composition."""

    def __init__(self, result: ChatResult) -> None:
        if type(result) is not ChatResult:
            raise TypeError("FixedModel requires ChatResult")
        self._result = result
        self.chat_calls = 0

    async def chat(self, request: ChatRequest) -> ChatResult:
        if type(request) is not ChatRequest:
            raise TypeError("chat requires ChatRequest")
        self.chat_calls += 1
        return self._result
'''
FIXTURES = '''"""Offline application composition."""

from app.model import ChatResult, FixedModel


def make_model() -> FixedModel:
    return FixedModel(
        ChatResult(
            "This is a deterministic offline answer. Replace the injected model to add a real provider.",
        )
    )
'''
README = """# Standalone assessment starter

This generated project has no dependency on LegoAI. Its immutable Chat contracts
were deliberately reduced to roles, messages, requests, response text, an async
ModelPort and FixedModel. Provider/model identities, usage accounting, embedding,
tenant context, routing, governance, plugins, execution, agents, RAG, workflow,
and configuration persistence are omitted.

FixedModel is the default: no API key, external model call or token consumption.
Python 3.14, uv and Node.js 22.12+ (or Node 24) are required.

## Run

In one terminal:

```powershell
cd backend
uv sync
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
```

In another:

```powershell
cd frontend
npm install
npm run dev
```

Open the URL printed by Vite. Its development proxy forwards /api to localhost:8000.
GET http://127.0.0.1:8000/health returns {"status":"ok"}.
POST /api/v1/ask accepts {"question":"Hello"} and returns {"answer":"..."}.
The same fixed answer is intentional. Empty, non-string, oversized or extra-field
requests are rejected. Dependencies must be installed before offline use.
On Windows with restricted PowerShell script execution, use npm.cmd.

## Verify

```powershell
cd backend
uv run pytest
uv run mypy src tests
uv run ruff check .
uv run ruff format --check .
cd ../frontend
npm test
npm run build
npm run lint
```

Tests use an in-process HTTP client and prohibit external socket connections.
No Docker or Git initialization is required. Built frontend assets need a host
that proxies /api to the backend; Vite preview is a static preview, not that host.

## Extend

Implement async chat(request: ChatRequest) -> ChatResult in an adapter and inject
it with create_app(model=your_adapter). Keep SDK types and credentials inside
explicit adapter composition. Define provider timeout, cancellation and safe error
translation before enabling live calls. Do not silently add retries.

This is a local application starter, not a production deployment: authentication,
rate limits, persistence, HTTPS and deployment policy are not supplied.
No provider generation or transport resource guarantees are implied.

Generated from the maintained in-repository example by export_assessment_starter.py.
Regenerate from that source; --force overwrites generated files and preserves
unrelated destination files. It does not merge local edits or delete stale files.
"""
GITIGNORE = """__pycache__/
*.py[cod]
.venv/
.pytest_cache/
.mypy_cache/
.ruff_cache/
node_modules/
dist/
build/
*.egg-info/
.env
.env.*
!.env.example
.DS_Store
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite generated files only; preserve unrelated files",
    )
    return parser.parse_args()


def reject_links(path: Path) -> None:
    for part in (path, *path.parents):
        if part.is_symlink() or part.is_junction():
            raise ValueError("Linked destination paths are not supported")


def validate_destination(destination: Path, force: bool = False) -> Path:
    path = Path(os.path.abspath(destination.expanduser()))
    reject_links(path)
    if path == Path(path.anchor) or path == Path.home().resolve():
        raise ValueError("Choose a dedicated project directory")
    if path == ROOT or path in ROOT.parents or ROOT in path.parents:
        raise ValueError("Destination must be outside the source repository")
    if path.exists():
        if not path.is_dir():
            raise ValueError("Destination is not a directory")
        if not force:
            raise ValueError(
                "Destination exists; use --force to overwrite generated files"
            )
    return path


def read_source(directory: str, name: str) -> str:
    path = EXAMPLE / directory / name
    if path.is_symlink() or not path.is_file():
        raise ValueError("Missing or linked starter source: " + name)
    return path.read_text(encoding="utf-8")


def copy_backend_example() -> dict[str, str]:
    files: dict[str, str] = {}
    for name in BACKEND_FILES:
        content = read_source("backend", name)
        target = name.replace("src/assessment_starter/", "src/app/")
        if name == "src/assessment_starter/fixtures.py":
            content = FIXTURES
        elif name == "pyproject.toml":
            content = content.replace(', "legoai-reference"', "")
            content = content.replace(
                '[tool.uv.sources]\nlegoai-reference = { path = "../../..", editable = true }\n\n',
                "",
            ).replace("src/assessment_starter", "src/app")
        else:
            content = content.replace("assessment_starter.", "app.")
            for module in (
                "legoai.intelligence.model.ports",
                "legoai.intelligence.model.values",
                "legoai.reference.model_fake",
            ):
                content = content.replace(module, "app.model")
        files["backend/" + target] = content
    return files


def copy_frontend() -> dict[str, str]:
    return {
        "frontend/" + name: read_source("frontend", name) for name in FRONTEND_FILES
    }


def verify_contents(files: dict[str, str]) -> None:
    for name, content in files.items():
        if "legoai." in content or "legoai-reference" in content:
            raise ValueError("Unrewritten platform dependency: " + name)
        if name.endswith(".py"):
            ast.parse(content, filename=name)


def verify_export(destination: Path) -> None:
    # Only inspect generated files, never unrelated user files under --force.
    expected = build_files()
    actual = {
        name: (destination / name).read_text(encoding="utf-8") for name in expected
    }
    verify_contents(actual)
    if actual != expected:
        raise ValueError("Export does not match the maintained starter")


def build_files() -> dict[str, str]:
    files = copy_backend_example() | copy_frontend()
    files["backend/src/app/model.py"] = CONTRACTS
    files["README.md"] = README
    files[".gitignore"] = GITIGNORE
    verify_contents(files)
    return files


def export(destination: Path, force: bool = False) -> Path:
    destination = validate_destination(destination, force)
    files = build_files()
    # Preflight every output before modifying any existing file. Local trusted
    # filesystem only; no claim of protection against concurrent hostile mutation.
    for name in files:
        target = destination / name
        reject_links(target)
        for parent in target.parents:
            if parent.exists() and not parent.is_dir():
                raise ValueError("Output parent is not a directory")
        if target.exists() and (not target.is_file() or target.stat().st_nlink != 1):
            raise ValueError("Output must be an ordinary, unshared file")
    destination.mkdir(parents=True, exist_ok=True)
    for name, content in files.items():
        target = destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        # Atomic per-file replacement, not a transaction across the whole export.
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", newline="\n", dir=target.parent, delete=False
        ) as stream:
            temporary = Path(stream.name)
            stream.write(content)
        try:
            temporary.replace(target)
        finally:
            temporary.unlink(missing_ok=True)
    verify_export(destination)
    return destination


def main() -> None:
    args = parse_args()
    try:
        destination = export(args.destination, args.force)
    except (ValueError, OSError) as error:
        raise SystemExit("Export failed: " + str(error)) from None
    print("Created standalone project: " + str(destination))
    print("No dependencies installed, Git state changed, or model calls made.")


if __name__ == "__main__":
    main()
