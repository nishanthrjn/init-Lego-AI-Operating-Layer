"""Frozen comparison identity: R3 everything, except the model condition.

The Analyst 1.0.2 identity, workload, oracle, thresholds, N and request path are
R3's and are verified by the R3 freeze (which runs the 1Q freeze). This module
adds the comparison preregistration, the candidate registry and the operator's
committed model-digest pins. Nothing here changes RepositoryAnalyst or routing.
"""

import hashlib
import json
import re
from pathlib import Path
from typing import cast

from analyst_quality1q import data as q
from analyst_quality1q_r3 import data as r3

HERE = Path(__file__).resolve().parent
ROOT = q.ROOT
PREREGISTRATION = "preregistration-compare1.json"
PREREGISTRATION_DIGEST = (
    "64654f476af01f6d3ab4b799225f4dade5d1e498ee6a4fdffb38bb3c1a40c6a2"
)
PINS = "model-pins.json"
PREDECLARATION = "planning/FORGEAI-ANALYST-MODEL-COMPARISON.md"
MARKER = "<!-- END MODEL-COMPARE-1 PREDECLARATION -->"
DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")


class CandidateError(RuntimeError):
    """The model is not a registered, pinned comparison candidate."""


def read() -> dict[str, object]:
    return cast(
        dict[str, object],
        json.loads((HERE / PREREGISTRATION).read_text(encoding="utf-8-sig")),
    )


def pins() -> dict[str, str | None]:
    value = json.loads((HERE / PINS).read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError("model pins must be an object")
    for model, digest in value.items():
        if digest is not None and not (
            isinstance(digest, str) and DIGEST.fullmatch(digest)
        ):
            raise ValueError(f"{model}: pin must be null or sha256:<64 hex>")
    return cast(dict[str, str | None], value)


def predeclaration_digest() -> str:
    doc = (ROOT / PREDECLARATION).read_text(encoding="utf-8-sig")
    prefix, found, _ = doc.partition(MARKER)
    if not found:
        raise ValueError("comparison predeclaration marker missing")
    return hashlib.sha256((prefix + MARKER + "\n").encode()).hexdigest()


def candidates() -> dict[str, dict[str, object]]:
    rows = cast(list[dict[str, object]], read()["candidates"])
    return {str(row["model"]): row for row in rows}


def freeze() -> dict[str, str]:
    """Verify R3 (and through it 1Q), then this preregistration and the pins."""
    digests = r3.freeze()
    if q.digest(HERE / PREREGISTRATION) != PREREGISTRATION_DIGEST:
        raise ValueError("comparison preregistration changed after freeze")
    pre = read()
    if pre["predeclaration_digest"] != predeclaration_digest():
        raise ValueError("comparison predeclaration changed after freeze")
    r3_pre = r3.read()
    if pre["analyst"] != r3_pre["analyst"] or pre["reused"] != r3_pre["reused"]:
        raise ValueError("comparison does not reuse the R3 Analyst and workload")
    if pre["model_condition"] != r3_pre["model_condition"]:
        raise ValueError("control model condition differs from R3")
    registered = set(candidates())
    if set(pins()) != registered:
        raise ValueError("model pins must cover exactly the registered candidates")
    control = cast(dict[str, object], pre["model_condition"])
    if control["name"] in registered:
        raise ValueError("the control is the recorded R3 condition, not a candidate")
    return {**digests, "compare1_preregistration": PREREGISTRATION_DIGEST}


def require_live_identity() -> None:
    """Every comparison condition requires exactly the R3 Analyst 1.0.2."""
    r3.require_live_identity()


def require_candidate(model: str, digest: str) -> dict[str, object]:
    """A registered candidate whose committed pin equals the requested digest."""
    registry = candidates()
    if model not in registry:
        raise CandidateError(f"{model} is not a registered comparison candidate")
    pinned = pins()[model]
    if pinned is None:
        raise CandidateError(
            f"{model}: acquisition pending; record its digest in {PINS} and commit"
        )
    if digest != pinned:
        raise CandidateError(f"{model}: digest differs from the committed pin")
    return registry[model]


def smoke_plan() -> tuple[tuple[q.Case, int], ...]:
    """The frozen, non-gating smoke subset: one call per listed case."""
    wanted = cast(list[str], read()["smoke_cases"])
    cases = {case.id: case for case, _ in q.plan()}
    return tuple((cases[case_id], 1) for case_id in wanted)
