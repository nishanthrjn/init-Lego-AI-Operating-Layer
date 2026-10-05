"""Frozen R3 identity: the unchanged 1Q workload, pinned to RepositoryAnalyst 1.0.2.

Cases, oracle, partition, thresholds and N are the 1Q inputs, verified by the 1Q
freeze. This module adds only the R3 preregistration and the 1.0.2 identity a
live run must match. Parser identity and committed-source helpers are r2's.
"""

import hashlib
import json
import subprocess
from pathlib import Path
from typing import cast

from analyst_quality1q import data as q
from analyst_quality1q_r2 import data as r2
from content_discovery1 import data as cd1

HERE = Path(__file__).resolve().parent
ROOT = q.ROOT
PREREGISTRATION = "preregistration-r3.json"
PREREGISTRATION_DIGEST = (
    "6499b45ee5b720bcd2b7830140831c721994d87874c2dcf435f73a0cfec7a6b6"
)
PREDECLARATION = "planning/FORGEAI-CONTENT-DISCOVERY-ANALYST-QUALITY-R3.md"
MARKER = "<!-- END 1Q-R3 PREDECLARATION -->"
API = r2.API


class AnalystIdentityError(RuntimeError):
    """The current Analyst is not the 1.0.2 behavior this condition measures."""


def read() -> dict[str, object]:
    return cast(
        dict[str, object],
        json.loads((HERE / PREREGISTRATION).read_text(encoding="utf-8-sig")),
    )


def predeclaration_digest() -> str:
    doc = (ROOT / PREDECLARATION).read_text(encoding="utf-8-sig")
    prefix, found, _ = doc.partition(MARKER)
    if not found:
        raise ValueError("R3 predeclaration marker missing")
    return hashlib.sha256((prefix + MARKER + "\n").encode()).hexdigest()


def freeze() -> dict[str, str]:
    """Verify the 1Q inputs, then the R3 preregistration; returns digests."""
    digests = q.freeze()
    if q.digest(HERE / PREREGISTRATION) != PREREGISTRATION_DIGEST:
        raise ValueError("R3 preregistration changed after freeze")
    pre = read()
    if pre["predeclaration_digest"] != predeclaration_digest():
        raise ValueError("R3 predeclaration changed after freeze")
    reused = cast(dict[str, str], pre["reused"])
    if reused != {k: digests[k] for k in reused} or set(reused) != {
        "manifest",
        "heldout",
        "partition",
        "thresholds",
        "preregistration",
        "cd1_manifest",
    }:
        raise ValueError("R3 does not reuse the frozen 1Q inputs")
    analyst = cast(dict[str, object], pre["analyst"])
    commit = str(analyst["implementation_commit"])
    for path, expected in cast(dict[str, str], analyst["sources"]).items():
        if cd1.committed_digest(commit, path) != expected:
            raise ValueError(f"{path} differs at the implementation commit")
    previous = cast(dict[str, object], r2.read()["analyst"])
    if not (
        r2.parser_identity(r2.committed_text(commit, API))
        == previous["parser_identity"]
        == analyst["parser_identity"]
    ):
        raise ValueError("Analyst parser differs from the 1.0.1 parser")
    return {**digests, "r3_preregistration": PREREGISTRATION_DIGEST}


def working_parser_identity() -> str:
    """Parser identity of the Analyst API module in the working tree."""
    return r2.parser_identity((ROOT / API).read_text(encoding="utf-8"))


def require_live_identity() -> None:
    """A live R3 sample requires exactly the preregistered Analyst 1.0.2."""
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
    if working_parser_identity() != analyst["parser_identity"]:
        raise AnalystIdentityError("RepositoryAnalyst parser identity differs")
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
