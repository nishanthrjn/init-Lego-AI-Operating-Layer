"""Run Ruff in a disposable trusted project using this environment's executable."""

import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

from legoai_engineering.checks.local import LocalCheckTools, LocalEngineeringChecks
from legoai_engineering.checks.values import CheckKind, CheckPolicy, CheckRequest
from legoai_engineering.repository.local import LocalWorkspaceRoot
from legoai_engineering.repository.workspace import RepositoryPath


def main() -> None:
    base = Path(sys.executable).parent
    suffix = ".exe" if os.name == "nt" else ""
    tools = LocalCheckTools(
        base / ("pytest" + suffix),
        base / ("ruff" + suffix),
        base / ("mypy" + suffix),
    )
    with TemporaryDirectory(prefix="legoai-m5-") as directory:
        root = Path(directory).resolve()
        (root / "ruff.toml").write_text('lint.select = ["F"]\n', encoding="utf-8")
        (root / "sample.py").write_text("value: int = 1\n", encoding="utf-8")
        adapter = LocalEngineeringChecks(LocalWorkspaceRoot(root), tools, CheckPolicy())
        result = adapter.check(
            CheckRequest(CheckKind.RUFF_CHECK, (RepositoryPath("sample.py"),))
        )
        print(f"{result.kind.value}: {result.outcome.value}")


if __name__ == "__main__":
    main()
