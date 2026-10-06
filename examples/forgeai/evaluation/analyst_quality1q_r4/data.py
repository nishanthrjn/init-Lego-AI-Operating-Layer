"""Frozen R4 identity: the unchanged 1Q workload, Analyst 1.0.3, the pinned 14b.

Cases, oracle, partition, thresholds and N are the 1Q inputs, verified by the 1Q
freeze. The model digest is the committed ANALYST-MODEL-COMPARE-1 pin. This
module adds only the R4 preregistration and the identity a live run must match.
"""

import hashlib
import json
import subprocess
from pathlib import Path
from typing import cast

from analyst_model_compare1 import data as compare
from analyst_quality1q import data as q
from analyst_quality1q_r2 import data as r2
from content_discovery1 import data as cd1

HERE = Path(__file__).resolve().parent
ROOT = q.ROOT
PREREGISTRATION = "preregistration-r4.json"
PREREGISTRATION_DIGEST = (
    "0a0c2040eb2e6dbbe05fb3b20f0c654bf12bce78f845db9985b6bb8f0db2374b"
)
PREDECLARATION = "planning/FORGEAI-CONTENT-DISCOVERY-ANALYST-QUALITY-R4.md"
MARKER = "<!-- END 1Q-R4 PREDECLARATION -->"
API = r2.API
REUSED = ("manifest", "heldout", "partition", "thresholds", "preregistration")


class AnalystIdentityError(RuntimeError):
    """The current Analyst is not the 1.0.3 behavior this condition measures."""


class ModelConditionError(RuntimeError):
    """The requested model is not the preregistered model condition."""


def read() -> dict[str, object]:
    return cast(
        dict[str, object],
        json.loads((HERE / PREREGISTRATION).read_text(encoding="utf-8-sig")),
    )


def predeclaration_digest() -> str:
    doc = (ROOT / PREDECLARATION).read_text(encoding="utf-8-sig")
    prefix, found, _ = doc.partition(MARKER)
    if not found:
        raise ValueError("R4 predeclaration marker missing")
    return hashlib.sha256((prefix + MARKER + "\n").encode()).hexdigest()


def known_conflicts() -> dict[str, dict[str, object]]:
    rows = cast(list[dict[str, object]], read()["known_non_gating_label_conflicts"])
    return {str(row["case"]): row for row in rows}


def _verify_conflicts() -> None:
    """Each known conflict is an unedited, non-gating contract probe."""
    partition = q.read("partition-v1.json")
    probes = cast(list[str], partition["contract_probes"])
    supporting = cast(list[str], partition["supporting_quality"])
    cases = {case.id: case for case in q.load_cd1()}
    for case_id, row in known_conflicts().items():
        if case_id not in probes or case_id in supporting or partition["gating"]:
            raise ValueError(f"{case_id} is not a non-gating contract probe")
        if cases[case_id].partition != row["partition"]:
            raise ValueError(f"{case_id} partition differs")
        if cases[case_id].oracle.expected != row["recorded_expected"]:
            raise ValueError(f"{case_id} recorded label differs")


def freeze() -> dict[str, str]:
    """Verify the 1Q inputs, then the R4 preregistration; returns digests."""
    digests = q.freeze()
    if q.digest(HERE / PREREGISTRATION) != PREREGISTRATION_DIGEST:
        raise ValueError("R4 preregistration changed after freeze")
    pre = read()
    if pre["predeclaration_digest"] != predeclaration_digest():
        raise ValueError("R4 predeclaration changed after freeze")
    reused = cast(dict[str, str], pre["reused"])
    if reused != {k: digests[k] for k in reused} or set(reused) != {
        *REUSED,
        "cd1_manifest",
    }:
        raise ValueError("R4 does not reuse the frozen 1Q inputs")
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
        raise ValueError("Analyst parser differs from the prior conditions")
    model = cast(dict[str, object], pre["model_condition"])
    if compare.pins().get(str(model["name"])) != model["digest"]:
        raise ValueError("R4 model digest differs from the committed pin")
    _verify_conflicts()
    return {**digests, "r4_preregistration": PREREGISTRATION_DIGEST}


def working_parser_identity() -> str:
    """Parser identity of the Analyst API module in the working tree."""
    return r2.parser_identity((ROOT / API).read_text(encoding="utf-8"))


def require_live_identity() -> None:
    """A live R4 sample requires exactly the preregistered Analyst 1.0.3."""
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


def require_model(name: str, digest: str) -> None:
    model = cast(dict[str, object], read()["model_condition"])
    if name != model["name"] or digest != model["digest"]:
        raise ModelConditionError("model name/digest differs from the preregistration")
