"""Closed live identity and read-only preflight. Never dispatches an Agent."""

import hashlib
import json
import multiprocessing
import os
import platform
import subprocess
from collections.abc import Callable
from http.client import HTTPConnection
from multiprocessing.connection import Connection
from pathlib import Path
from typing import Any

from analyst_design_eval2.data import freeze
from forgeai_eval.preflight import ServingIdentity
from legoai_engineering.analyst.sufficiency_definition import (
    evidence_sufficiency_definition,
)

from legoai.kernel.versions import Version

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
CONDITION = "forgeai-analyst-design-live/1"
PROFILE = "forgeai-analyst-sufficiency-live-profile/1"
REPORT = "forgeai-analyst-sufficiency-live-report/1"
MODEL = "qwen2.5-coder:14b"
MODEL_DIGEST = "sha256:9ec8897f747e246e970bc5cfdda85d22f1123dc2e3d34978a010a75968716849"
URL = "http://127.0.0.1:11434"
VERSION = "0.35.1"
SMOKE = ("d01", "d05", "d09", "d13", "d20", "d21")


def digest(path: Path) -> str:
    return hashlib.sha256(
        path.read_text(encoding="utf-8").replace("\r\n", "\n").encode()
    ).hexdigest()


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, text=True, check=True, timeout=10
    ).stdout.strip()


def binding() -> dict[str, Any]:
    pins = json.loads((HERE / "pins.json").read_text())
    for name, expected in pins.items():
        if digest(ROOT / name) != expected:
            raise ValueError("FROZEN_IDENTITY_MISMATCH: " + name)
    definition = evidence_sufficiency_definition()
    if definition.behavior_version != Version(1, 0, 0):
        raise ValueError("AGENT_VERSION_MISMATCH")
    return {
        "condition": CONDITION,
        "profile": PROFILE,
        "report": REPORT,
        "evaluation": "forgeai-analyst-design-eval/2",
        "frozen_digests": freeze(),
        "harness_sources": {
            p.name: digest(p) for p in HERE.iterdir() if p.suffix in {".py", ".json"}
        },
        "source_pins": pins,
        "profile_document_digest": pins[
            "planning/FORGEAI-ANALYST-SUFFICIENCY-LIVE-PROFILE-1.md"
        ],
        "experiment_decision_digest": pins[
            "planning/FORGEAI-ANALYST-DESIGN-LIVE-1-DECISION.md"
        ],
        "parser_identity": {
            k: v
            for k, v in pins.items()
            if k.endswith(
                ("sufficiency_agent.py", "sufficiency.py", "_json_document.py")
            )
        },
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
        "N": 1,
        "smoke": list(SMOKE),
        "smoke_calls": 6,
        "full_calls": 68,
        "call_seconds": 600,
        "smoke_seconds": 1800,
        "full_seconds": 21600,
        "retry": False,
        "fallback": False,
        "final_analysis_calls": 0,
    }


def health_child(pipe: Connection) -> None:
    try:
        if os.environ.get("FORGEAI_LIVE1_OFFLINE") == "1":
            raise ValueError("OFFLINE_PROVIDER_FORBIDDEN")
        objects = []
        for path in ("/api/version", "/api/tags"):
            connection = HTTPConnection("127.0.0.1", 11434, timeout=5)
            try:
                connection.request("GET", path)
                response = connection.getresponse()
                if response.status != 200:
                    raise ValueError("provider_status")
                body = response.read(1048577)
                if len(body) > 1048576:
                    raise ValueError("provider_response_bound")
                objects.append(json.loads(body))
            finally:
                connection.close()
        version, tags = objects
        matches = [m for m in tags["models"] if m["name"] == MODEL]
        if len(matches) != 1:
            raise ValueError("model_not_installed")
        pipe.send(
            (version["version"], matches[0]["name"], "sha256:" + matches[0]["digest"])
        )
    except Exception:
        pipe.send(None)
    finally:
        pipe.close()


def local_probe(url: str, model: str, digest: str) -> ServingIdentity:
    if (url, model, digest) != (URL, MODEL, MODEL_DIGEST):
        raise ValueError("LOCAL_PROVIDER_IDENTITY_REQUIRED")
    context = multiprocessing.get_context("spawn")
    reader, writer = context.Pipe(duplex=False)
    process = context.Process(target=health_child, args=(writer,))
    process.start()
    writer.close()
    try:
        if not reader.poll(10):
            raise ValueError("PROVIDER_UNAVAILABLE")
        value = reader.recv()
        if value is None:
            raise ValueError("PROVIDER_UNAVAILABLE_OR_INVALID")
        return ServingIdentity(*value)
    finally:
        reader.close()
        if process.is_alive():
            process.terminate()
        process.join(0.5)
        if process.is_alive():
            process.kill()
            process.join(0.5)
        if process.is_alive():
            raise ValueError("PREFLIGHT_TERMINATION_UNCONFIRMED")
        process.close()


def preflight(
    directory: Path,
    *,
    url: str = URL,
    probe: Callable[[str, str, str], ServingIdentity] = local_probe,
    repository: Callable[..., str] = git,
) -> dict[str, Any]:
    if url != URL:
        raise ValueError("LOCAL_CREDENTIAL_FREE_ENDPOINT_REQUIRED")
    result = binding()
    if directory.exists():
        raise ValueError("OUTPUT_ALREADY_EXISTS")
    if repository("status", "--porcelain", "--untracked-files=no"):
        raise ValueError("TRACKED_TREE_DIRTY")
    required = list(result["source_pins"]) + [
        p.relative_to(ROOT).as_posix()
        for p in HERE.iterdir()
        if p.suffix in {".py", ".json"}
    ]
    for name in required:
        repository("cat-file", "-e", "HEAD:" + name)
    result["commit"] = repository("rev-parse", "HEAD")
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
