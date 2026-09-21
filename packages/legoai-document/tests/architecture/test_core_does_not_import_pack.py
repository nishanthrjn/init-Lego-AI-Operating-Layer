"""Confirms Lego AI Core has no outward dependency on this optional pack.

This check lives inside legoai-document's own test suite (not inside the
legoai-reference repository's test suite) so that:

- legoai-document remains independently testable/installable even when
  checked out without its sibling legoai-reference checkout present
  (the check is skipped, not failed, if that sibling tree cannot be
  found at the conventional monorepo-relative location); and
- adding this check never perturbs legoai-reference's own test suite or
  its exact packaging-manifest assertions in
  tests/architecture/test_package_install.py.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest


def _conventional_core_src() -> Path | None:
    # packages/legoai-document/tests/architecture/<this file>
    #   -> parents[4] is the legoai-reference repository root in this
    #      monorepo layout.
    candidate = Path(__file__).resolve().parents[4] / "src" / "legoai"
    return candidate if candidate.is_dir() else None


def test_legoai_core_does_not_import_legoai_document() -> None:
    core_src = _conventional_core_src()
    if core_src is None:
        pytest.skip(
            "legoai-reference core src not found at the conventional monorepo path"
        )

    offenders: list[str] = []
    for path in core_src.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import) and any(
                alias.name.split(".")[0] == "legoai_document" for alias in node.names
            ):
                offenders.append(str(path.relative_to(core_src)))
            if (
                isinstance(node, ast.ImportFrom)
                and node.module
                and node.module.split(".")[0] == "legoai_document"
            ):
                offenders.append(str(path.relative_to(core_src)))
    assert offenders == []
