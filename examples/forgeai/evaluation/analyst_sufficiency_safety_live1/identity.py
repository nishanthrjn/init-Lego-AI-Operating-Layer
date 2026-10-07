"""Closed live identity and read-only preflight for the safety baseline.

Reuses the qualified LIVE-1 provider probe, model/runtime pins and Git/digest
helpers unchanged. Admits only forgeai-analyst-sufficiency-safety-eval/2.
Never dispatches an Agent.
"""

import asyncio
import hashlib
import json
import platform
from collections.abc import Callable
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from analyst_design_live1.identity import HERE as LIVE1
from analyst_design_live1.identity import (
    MODEL,
    MODEL_DIGEST,
    URL,
    VERSION,
    digest,
    git,
    local_probe,
)
from analyst_design_live1.identity import ROOT as ROOT
from analyst_sufficiency_safety_eval2 import data as safety
from forgeai_eval.preflight import ServingIdentity
from legoai_engineering.analyst.sufficiency_definition import (
    evidence_sufficiency_definition,
)

from analyst_sufficiency_safety_live1.inputs import guard, prepare
from legoai.kernel.versions import Version

HERE = Path(__file__).resolve().parent
CONDITION = "forgeai-analyst-sufficiency-safety-live/1"
REPORT = "forgeai-analyst-sufficiency-safety-live-report/1"
EVALUATION = "forgeai-analyst-sufficiency-safety-eval/2"
REJECTED = ("forgeai-analyst-sufficiency-safety-eval/1",)
CALL_CEILING = 22
CALL_SECONDS = 600
TOTAL_SECONDS = 3600  # predeclared hard ceiling; never extended during a run
CLEANUP_RESERVE = 2  # LIVE-1 bounded client cleanup reserve
AGENT_SOURCES = (
    "packages/legoai-engineering/src/legoai_engineering/analyst/sufficiency_definition.py",
    "packages/legoai-engineering/src/legoai_engineering/analyst/sufficiency_agent.py",
    "packages/legoai-engineering/src/legoai_engineering/analyst/sufficiency.py",
    "packages/legoai-engineering/src/legoai_engineering/_json_document.py",
)
# Qualified LIVE-1 runtime reused unchanged: child, guard, diagnostics, lifecycle.
REUSED_RUNTIME = (
    "runtime.py",
    "diagnostics.py",
    "output_diagnostics.py",
    "lifecycle.py",
    "storage.py",
    "identity.py",
)
__all__ = [
    "AGENT_SOURCES",
    "CALL_CEILING",
    "CALL_SECONDS",
    "CLEANUP_RESERVE",
    "CONDITION",
    "EVALUATION",
    "HERE",
    "LIVE1",
    "MODEL",
    "MODEL_DIGEST",
    "REPORT",
    "ROOT",
    "TOTAL_SECONDS",
    "URL",
    "VERSION",
    "admit",
    "binding",
    "preflight",
    "safety",
    "verify_before_call",
]


def admit(condition: str) -> None:
    """Only the corrected safety condition may be baselined."""
    if condition in REJECTED or condition != EVALUATION:
        raise ValueError("SAFETY_CONDITION_NOT_ADMITTED: " + condition)


def binding() -> dict[str, Any]:
    admit(safety.CONDITION)
    frozen = safety.freeze()  # every SAFETY-EVAL-2 artifact digest, incl. scorer
    pins = json.loads((LIVE1 / "pins.json").read_text())
    agent = {name: pins[name] for name in AGENT_SOURCES}
    for name, expected in agent.items():
        if digest(ROOT / name) != expected:
            raise ValueError("FROZEN_IDENTITY_MISMATCH: " + name)
    definition = evidence_sufficiency_definition()
    if definition.behavior_version != Version(1, 0, 0):
        raise ValueError("AGENT_VERSION_MISMATCH")
    membership = [c.id for c, _ in safety.load()]
    if len(membership) != CALL_CEILING:
        raise ValueError("SAFETY_MEMBERSHIP_MISMATCH")
    return {
        "condition": CONDITION,
        "report": REPORT,
        "evaluation": EVALUATION,
        "evaluation_report": safety.REPORT,
        "frozen_digests": frozen,
        "freeze_manifest_digest": safety.FREEZE_DIGEST,
        "harness_sources": {
            p.name: digest(p) for p in HERE.iterdir() if p.suffix in {".py", ".json"}
        },
        "reused_runtime_sources": {
            name: digest(LIVE1 / name) for name in REUSED_RUNTIME
        },
        "parser_identity": agent,
        "agent": definition.agent_id.value,
        "agent_version": "1.0.0",
        "agent_fingerprint": hashlib.sha256(
            (repr(definition) + definition.system_prompt).encode()
        ).hexdigest(),
        "prompt_digest": hashlib.sha256(definition.system_prompt.encode()).hexdigest(),
        "model_requirement": "engineering-reasoning",
        "model": MODEL,
        "model_digest": MODEL_DIGEST,
        "provider": "local-ollama",
        "url": URL,
        "ollama_version": VERSION,
        "membership": membership,
        "N": 1,
        "call_ceiling": CALL_CEILING,
        "call_seconds": CALL_SECONDS,
        "total_seconds": TOTAL_SECONDS,
        "retry": False,
        "fallback": False,
        "acquisition": False,
        "reassessment": False,
    }


def preflight(
    directory: Path,
    *,
    url: str = URL,
    probe: Callable[[str, str, str], ServingIdentity] = local_probe,
    repository: Callable[..., str] = git,
) -> dict[str, Any]:
    """Zero semantic calls: identities, clean committed tree, local provider."""
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
        *AGENT_SOURCES,
        *(
            p.relative_to(ROOT).as_posix()
            for folder in (HERE, safety.HERE)
            for p in folder.iterdir()
            if p.suffix in {".py", ".json", ".md"}
        ),
        *((LIVE1 / name).relative_to(ROOT).as_posix() for name in REUSED_RUNTIME),
    ]
    for name in required:
        repository("cat-file", "-e", "HEAD:" + name)
    result["commit"] = repository("rev-parse", "HEAD")
    result["clean_tracked_tree"] = True
    result["credentials"] = "NONE"
    # Offline sweep: every frozen payload passes the leakage guard before any call.
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
