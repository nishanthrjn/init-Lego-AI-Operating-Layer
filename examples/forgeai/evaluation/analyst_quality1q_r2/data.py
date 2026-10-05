"""Frozen r2 identity: the unchanged 1Q workload, pinned to RepositoryAnalyst 1.0.1.

Nothing here re-authors cases, oracle, thresholds, partition or N: those are the
1Q inputs, verified by the 1Q freeze (whose Analyst pins are its 1.0.0 history).
This module adds only the r2 preregistration and the 1.0.1 identity a live run
must match.
"""

import ast
import hashlib
import json
import subprocess
from pathlib import Path
from typing import cast

from analyst_quality1q import data as q
from content_discovery1 import data as cd1

HERE = Path(__file__).resolve().parent
ROOT = q.ROOT
PREREGISTRATION = "preregistration-r2.json"
PREREGISTRATION_DIGEST = (
    "f724f81f4fcbaf3e54f82fa7cd5fb97739eaa2ab4da4b2fb827bc696f4e6fbf7"
)
PREDECLARATION = "planning/FORGEAI-CONTENT-DISCOVERY-ANALYST-QUALITY-R2.md"
MARKER = "<!-- END 1Q-R2 PREDECLARATION -->"
API = "packages/legoai-engineering/src/legoai_engineering/analyst/api.py"


class AnalystIdentityError(RuntimeError):
    """The current Analyst is not the 1.0.1 behavior this condition measures."""


def read() -> dict[str, object]:
    return cast(
        dict[str, object],
        json.loads((HERE / PREREGISTRATION).read_text(encoding="utf-8-sig")),
    )


def predeclaration_digest() -> str:
    doc = (ROOT / PREDECLARATION).read_text(encoding="utf-8-sig")
    prefix, found, _ = doc.partition(MARKER)
    if not found:
        raise ValueError("r2 predeclaration marker missing")
    return hashlib.sha256((prefix + MARKER + "\n").encode()).hexdigest()


def parser_identity(source: str) -> str:
    """Digest of the Analyst API module without its definition function.

    Equal identities mean the parser, request construction and result mapping
    are the same code; only the Agent definition (prompt, version) may differ.
    """
    module = ast.parse(source)
    module.body = [
        node
        for node in module.body
        if not (
            isinstance(node, ast.FunctionDef)
            and node.name == "repository_analyst_definition"
        )
    ]
    return hashlib.sha256(ast.dump(module).encode()).hexdigest()


def committed_text(commit: str, path: str) -> str:
    blob = subprocess.run(
        ["git", "show", f"{commit}:{path}"], cwd=ROOT, capture_output=True, check=True
    ).stdout
    return blob.decode("utf-8-sig").replace("\r\n", "\n").replace("\r", "\n")


def freeze() -> dict[str, str]:
    """Verify the 1Q inputs, then the r2 preregistration; returns digests."""
    digests = q.freeze()
    if q.digest(HERE / PREREGISTRATION) != PREREGISTRATION_DIGEST:
        raise ValueError("r2 preregistration changed after freeze")
    pre = read()
    if pre["predeclaration_digest"] != predeclaration_digest():
        raise ValueError("r2 predeclaration changed after freeze")
    reused = cast(dict[str, str], pre["reused"])
    if reused != {
        "manifest": digests["manifest"],
        "heldout": digests["heldout"],
        "partition": digests["partition"],
        "thresholds": digests["thresholds"],
        "preregistration": digests["preregistration"],
        "cd1_manifest": digests["cd1_manifest"],
    }:
        raise ValueError("r2 does not reuse the frozen 1Q inputs")
    analyst = cast(dict[str, object], pre["analyst"])
    commit = str(analyst["implementation_commit"])
    for path, expected in cast(dict[str, str], analyst["sources"]).items():
        if cd1.committed_digest(commit, path) != expected:
            raise ValueError(f"{path} differs at the implementation commit")
    old = parser_identity(
        committed_text(str(q.read("preregistration-v1.json")["foundation"]), API)
    )
    new = parser_identity(committed_text(commit, API))
    if not old == new == analyst["parser_identity"]:
        raise ValueError("Analyst parser differs from the 1.0.0 parser")
    return {**digests, "r2_preregistration": PREREGISTRATION_DIGEST}


def require_live_identity() -> None:
    """A live r2 sample requires exactly the preregistered Analyst 1.0.1."""
    analyst = cast(dict[str, object], read()["analyst"])
    if q.analyst_version() != analyst["version"]:
        raise AnalystIdentityError(
            f"RepositoryAnalyst {q.analyst_version()} is not {analyst['version']}"
        )
    if q.definition_fingerprint() != analyst["definition_fingerprint"]:
        raise AnalystIdentityError("RepositoryAnalyst definition fingerprint differs")
    for path, expected in cast(dict[str, str], analyst["sources"]).items():
        if q.digest(ROOT / path) != expected:
            raise AnalystIdentityError(f"{path} differs from the pinned source")
    try:
        subprocess.run(
            [
                "git",
                "merge-base",
                "--is-ancestor",
                str(analyst["implementation_commit"]),
                "HEAD",
            ],
            cwd=ROOT,
            capture_output=True,
            check=True,
        )
    except subprocess.CalledProcessError as error:
        raise AnalystIdentityError(
            "the Analyst implementation commit is not an ancestor of HEAD"
        ) from error
