"""Closed development identity and read-only preflight. Never dispatches an Agent.

Agent 1.1.0, the frozen H1 application policy, the frozen SAFETY-EVAL-2
evaluator, the immutable historical comparator, the prospective decision rules
and the live/2 runtime pins (Ollama 0.40.0 exact) are verified together.
SAFETY-EVAL-3 is checked by Git object identity only; no content is read.
"""

import asyncio
import hashlib
import json
import platform
from collections.abc import Callable
from pathlib import Path
from typing import Any, cast
from urllib.parse import urlsplit

from analyst_design_live1.identity import (
    MODEL,
    MODEL_DIGEST,
    URL,
    digest,
    git,
    local_probe,
)
from analyst_evidence_loop.policy_gate import policy_from_config
from analyst_sufficiency_safety_eval2 import data as safety
from analyst_sufficiency_safety_live1 import identity as live1
from analyst_sufficiency_safety_live1.identity import ROOT
from analyst_sufficiency_safety_live2.identity import VERSION
from forgeai_eval.preflight import ServingIdentity
from legoai_engineering.analyst.request_policy import EvidenceRequestPolicy
from legoai_engineering.analyst.sufficiency_envelope import (
    enveloped_sufficiency_definition,
)

from analyst_sufficiency_h2_development_live1.comparison import (
    RULES,
    historical,
    rules,
)
from analyst_sufficiency_h2_development_live1.inputs import facts, guard, prepare
from legoai.kernel.versions import Version

HERE = Path(__file__).resolve().parent
CONDITION = "forgeai-analyst-sufficiency-h2-development-live/1"
REPORT = "forgeai-analyst-sufficiency-h2-development-live-report/1"
EVALUATION = live1.EVALUATION  # forgeai-analyst-sufficiency-safety-eval/2
AGENT_VERSION = "1.1.0"
PROMPT_SHA256 = "1749c5b1eea2d1002dbd2d94c15b672f593a9dd0716f1af7857f6c05b7da1031"
FINGERPRINT = "769bfa4a8d5310f7a6c377f37bb46bfa82948961cad9be4f7bf319e6c803aa69"
POLICY_SHA256 = "e8d79eb1d0c560dc9b349a0e09ab01b5e6e50ad5b35ffce454a6825d2bb5a930"
CALL_CEILING = live1.CALL_CEILING  # 22: one initial assessment per case
CALL_SECONDS = live1.CALL_SECONDS  # 600
TOTAL_SECONDS = live1.TOTAL_SECONDS  # 3600; never extended during a run
CLEANUP_RESERVE = live1.CLEANUP_RESERVE  # 2
SEAL_PATH = "examples/forgeai/evaluation/analyst_sufficiency_safety_eval3"
SEAL_TREE = "d23679f0004620b1bcf814ba9546353f949af519"  # as of 9a56a0d
__all__ = [
    "AGENT_VERSION",
    "CALL_CEILING",
    "CALL_SECONDS",
    "CLEANUP_RESERVE",
    "CONDITION",
    "EVALUATION",
    "HERE",
    "MODEL",
    "MODEL_DIGEST",
    "REPORT",
    "ROOT",
    "TOTAL_SECONDS",
    "URL",
    "VERSION",
    "agent_identity",
    "binding",
    "policy",
    "preflight",
    "seal",
    "verify_before_call",
]


def agent_identity() -> dict[str, Any]:
    d = enveloped_sufficiency_definition()
    values = {
        "agent": d.agent_id.value,
        "agent_version": f"{d.behavior_version.major}.{d.behavior_version.minor}.{d.behavior_version.patch}",
        "prompt_digest": hashlib.sha256(d.system_prompt.encode()).hexdigest(),
        "agent_fingerprint": hashlib.sha256(
            (repr(d) + d.system_prompt).encode()
        ).hexdigest(),
        "model_requirement": d.model_requirement.profile,
        "max_output_bytes": d.output_contract.max_bytes,
        "max_input_bytes": d.max_input_bytes,
        "max_prompt_bytes": d.max_prompt_bytes,
    }
    if (
        d.behavior_version != Version(1, 1, 0)
        or values["agent"] != "evidence-sufficiency-agent"
        or values["prompt_digest"] != PROMPT_SHA256
        or values["agent_fingerprint"] != FINGERPRINT
        or (values["max_output_bytes"], values["max_input_bytes"]) != (32768, 65536)
        or values["max_prompt_bytes"] != 81920
    ):
        raise ValueError("AGENT_IDENTITY_MISMATCH")
    return values


def policy() -> EvidenceRequestPolicy:
    raw = json.loads((HERE / "policy.json").read_text(encoding="utf-8"))
    value = policy_from_config(raw["policy"])
    if value.digest() != POLICY_SHA256:
        raise ValueError("REQUEST_POLICY_MISMATCH")
    return value


def seal(repository: Callable[..., str] = git) -> str:
    """SAFETY-EVAL-3 by Git object identity and path status only."""
    if repository("rev-parse", "HEAD:" + SEAL_PATH) != SEAL_TREE:
        raise ValueError("SAFETY_EVAL_3_SEAL_CHANGED")
    if repository("status", "--porcelain", "--", SEAL_PATH):
        raise ValueError("SAFETY_EVAL_3_SEAL_CHANGED")
    return SEAL_TREE


def binding() -> dict[str, Any]:
    live1.admit(safety.CONDITION)
    frozen = safety.freeze()  # every SAFETY-EVAL-2 artifact, incl. scorer
    pins = json.loads((HERE / "pins.json").read_text(encoding="utf-8"))
    for name, expected in pins.items():
        if digest(ROOT / name) != expected:
            raise ValueError("FROZEN_IDENTITY_MISMATCH: " + name)
    live1_pins = json.loads((live1.LIVE1 / "pins.json").read_text(encoding="utf-8"))
    parser = {name: live1_pins[name] for name in live1.AGENT_SOURCES}
    if any(pins[name] != value for name, value in parser.items()):
        raise ValueError("PARSER_IDENTITY_CHANGED")
    limits = safety.gates()
    membership = [c.id for c, _ in safety.load()]
    if membership != limits["gating_cases"] or len(membership) != CALL_CEILING:
        raise ValueError("MEMBERSHIP_MISMATCH")
    if set(membership) & set(safety.HISTORICAL):
        raise ValueError("HISTORICAL_CASES_EXCLUDED")
    comparator = historical()
    frozen_rules = rules()
    return {
        "condition": CONDITION,
        "report": REPORT,
        "evaluation": EVALUATION,
        "evaluation_report": safety.REPORT,
        "frozen_digests": frozen,
        "pins": pins,
        "parser_identity": parser,
        "harness_sources": {
            p.name: digest(p) for p in HERE.iterdir() if p.suffix in {".py", ".json"}
        },
        **agent_identity(),
        "request_policy_digest": policy().digest(),
        "decision_rules": frozen_rules["rules"],
        "decision_rules_digest": digest(RULES),
        "comparator": {
            "run_id": comparator["run_id"],
            "condition": comparator["condition"],
            "agent_version": comparator["agent_version"],
            "decision": comparator["decision"],
        },
        "model": MODEL,
        "model_digest": MODEL_DIGEST,
        "provider": "local-ollama",
        "url": URL,
        "ollama_version": VERSION,
        "credentials": "NONE",
        "membership": membership,
        "excluded": list(safety.HISTORICAL),
        "N": 1,
        "call_ceiling": CALL_CEILING,
        "call_seconds": CALL_SECONDS,
        "total_seconds": TOTAL_SECONDS,
        "cleanup_reserve": CLEANUP_RESERVE,
        "response_format": None,
        "structured_output": "ABSENT (H3 not adopted)",
        "retry": False,
        "fallback": False,
        "acquisition": False,
        "reassessment": False,
        "clarification_answer": False,
    }


def preflight(
    directory: Path,
    *,
    url: str = URL,
    probe: Callable[[str, str, str], ServingIdentity] = local_probe,
    repository: Callable[..., str] = git,
) -> dict[str, Any]:
    """Zero semantic calls: identities, committed tree, leakage sweep, provider."""
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
    for name in [
        *cast(dict[str, str], result["pins"]),
        *(
            p.relative_to(ROOT).as_posix()
            for p in HERE.iterdir()
            if p.suffix in {".py", ".json"}
        ),
    ]:
        repository("cat-file", "-e", "HEAD:" + name)
    result["safety_eval3_seal_tree"] = seal(repository)
    result["commit"] = repository("rev-parse", "HEAD")
    result["clean_tracked_tree"] = True
    payloads = []
    for case, o in safety.load():
        p = asyncio.run(prepare(case, o))
        guard(p)  # refuses on any leakage; never alters a payload
        payloads.append(facts(p))
    result["payloads"] = payloads
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
