"""forgeai-analyst-sufficiency-safety-live/2: a runtime identity revision only.

Live/2 differs from live/1 in exactly one pinned value, the Ollama runtime
(0.35.1 -> 0.40.0), qualified by the recorded compatibility review in
runtime-compat-2.json. Every other identity is taken from the unchanged live/1
binding, which re-verifies SAFETY-EVAL-2, the Agent/prompt/parser pins, the
membership and the budgets. Live/1 stays pinned to 0.35.1 and is not modified.
Never dispatches an Agent.
"""

import asyncio
import json
import platform
from collections.abc import Callable
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from analyst_design_live1.identity import (
    MODEL,
    MODEL_DIGEST,
    URL,
    digest,
    git,
    local_probe,
)
from analyst_sufficiency_safety_eval2 import data as safety
from analyst_sufficiency_safety_live1 import identity as live1
from analyst_sufficiency_safety_live1.identity import ROOT
from analyst_sufficiency_safety_live1.inputs import guard, prepare
from forgeai_eval.preflight import ServingIdentity

HERE = Path(__file__).resolve().parent
CONDITION = "forgeai-analyst-sufficiency-safety-live/2"
REPORT = "forgeai-analyst-sufficiency-safety-live-report/2"
VERSION = "0.40.0"  # exact pin; no range, "latest" or installed-version acceptance
SUPERSEDES = live1.CONDITION
__all__ = [
    "CONDITION",
    "HERE",
    "MODEL",
    "MODEL_DIGEST",
    "REPORT",
    "ROOT",
    "SUPERSEDES",
    "URL",
    "VERSION",
    "binding",
    "compatibility",
    "preflight",
    "verify_before_call",
]


def compatibility() -> dict[str, Any]:
    """The frozen 0.35.1 -> 0.40.0 review; refuses an unresolved surface."""
    record: dict[str, Any] = json.loads(
        (HERE / "runtime-compat-2.json").read_text(encoding="utf-8")
    )
    if (
        record["condition"] != CONDITION
        or record["from"]["ollama"] != live1.VERSION
        or record["to"]["ollama"] != VERSION
        or record["to"]["model_digest"] != MODEL_DIGEST
    ):
        raise ValueError("RUNTIME_COMPATIBILITY_RECORD_MISMATCH")
    allowed = {"UNCHANGED", "COMPATIBLE CHANGE"}
    unresolved = [s["surface"] for s in record["surfaces"] if s["class"] not in allowed]
    if unresolved or record["decision"] != "COMPATIBLE":
        raise ValueError("RUNTIME_COMPATIBILITY_UNRESOLVED: " + ",".join(unresolved))
    return record


def binding() -> dict[str, Any]:
    base = live1.binding()  # SAFETY-EVAL-2 freeze, Agent/parser pins, membership
    if base["ollama_version"] != live1.VERSION or live1.VERSION == VERSION:
        raise ValueError("LIVE1_RUNTIME_PIN_CHANGED")
    record = compatibility()
    return {
        **base,
        "condition": CONDITION,
        "report": REPORT,
        "ollama_version": VERSION,
        "runtime_revision": {
            "supersedes": SUPERSEDES,
            "superseded_ollama_version": live1.VERSION,
            "compatibility_record_digest": digest(HERE / "runtime-compat-2.json"),
            "decision": record["decision"],
        },
        "live1_harness_sources": base["harness_sources"],
        "harness_sources": {
            p.name: digest(p) for p in HERE.iterdir() if p.suffix in {".py", ".json"}
        },
    }


def preflight(
    directory: Path,
    *,
    url: str = URL,
    probe: Callable[[str, str, str], ServingIdentity] = local_probe,
    repository: Callable[..., str] = git,
) -> dict[str, Any]:
    """Zero semantic calls; identical checks to live/1 except the exact pin."""
    parts = urlsplit(url)
    if (
        url != URL
        or parts.hostname != "127.0.0.1"
        or parts.username is not None
        or parts.password is not None
        or parts.query
    ):
        raise ValueError("LOCAL_CREDENTIAL_FREE_ENDPOINT_REQUIRED")
    result = binding()
    if directory.exists():
        raise ValueError("OUTPUT_ALREADY_EXISTS")
    if repository("status", "--porcelain", "--untracked-files=no"):
        raise ValueError("TRACKED_TREE_DIRTY")
    required = [
        *live1.AGENT_SOURCES,
        *(
            p.relative_to(ROOT).as_posix()
            for folder in (HERE, live1.HERE, safety.HERE)
            for p in folder.iterdir()
            if p.suffix in {".py", ".json", ".md"}
        ),
        *((live1.LIVE1 / n).relative_to(ROOT).as_posix() for n in live1.REUSED_RUNTIME),
    ]
    for name in required:
        repository("cat-file", "-e", "HEAD:" + name)
    result["commit"] = repository("rev-parse", "HEAD")
    result["clean_tracked_tree"] = True
    result["credentials"] = "NONE"
    for case, o in safety.load():
        guard(asyncio.run(prepare(case, o)))
    result["payload_leakage_preflight"] = "PASSED"
    observed = probe(url, MODEL, MODEL_DIGEST)
    if observed.model_name != MODEL or observed.model_digest != MODEL_DIGEST:
        raise ValueError("MODEL_IDENTITY_MISMATCH")
    if observed.ollama_version != VERSION:
        raise ValueError("RUNTIME_IDENTITY_REVIEW_REQUIRED")
    result["observed"] = {
        "model": observed.model_name,
        "digest": observed.model_digest,
        "ollama": observed.ollama_version,
    }
    result["platform"] = platform.platform()
    result["processor"] = platform.processor()
    return result


def verify_before_call(provenance: dict[str, Any]) -> None:
    if (
        git("status", "--porcelain", "--untracked-files=no")
        or git("rev-parse", "HEAD") != provenance["commit"]
    ):
        raise ValueError("RUNTIME_CHANGED_SINCE_PREFLIGHT")
    for key, value in binding().items():
        if provenance.get(key) != value:
            raise ValueError("IDENTITY_CHANGED_SINCE_PREFLIGHT")
