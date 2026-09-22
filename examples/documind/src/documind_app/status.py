"""`legoai-documind status` -- a plain operational reachability probe.

Deliberately **not** a governed capability invocation: it never resolves a
Catalog entry, authorizes, or dispatches. It is a diagnostic convenience
that asks the configured Ollama instance which models it currently has
pulled, so the CLI can tell the user *why* `ingest`/`ask` might fail before
they hit a governed-invocation error. `GET /api/tags` performs no model
inference and has no effect worth governing.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass

from documind_app.config import DocuMindConfig

_STATUS_TIMEOUT_SECONDS = 5.0


@dataclass(frozen=True, slots=True)
class OllamaStatus:
    reachable: bool
    detail: str
    available_models: tuple[str, ...]
    chat_model_available: bool
    embedding_model_available: bool


def _model_matches(available: str, configured: str) -> bool:
    return (
        available == configured
        or available.split(":", 1)[0] == configured.split(":", 1)[0]
    )


def check_ollama_status(config: DocuMindConfig) -> OllamaStatus:
    url = config.base_url.rstrip("/") + "/api/tags"
    try:
        with urllib.request.urlopen(url, timeout=_STATUS_TIMEOUT_SECONDS) as response:
            payload = json.loads(response.read())
    except urllib.error.URLError as exc:
        return OllamaStatus(
            False, f"could not reach {config.base_url}: {exc}", (), False, False
        )
    except (TimeoutError, json.JSONDecodeError, OSError) as exc:
        return OllamaStatus(
            False, f"error contacting {config.base_url}: {exc}", (), False, False
        )

    models = payload.get("models") if isinstance(payload, dict) else None
    names = tuple(
        str(entry["name"])
        for entry in models or ()
        if isinstance(entry, dict) and "name" in entry
    )
    return OllamaStatus(
        True,
        f"reachable at {config.base_url}",
        names,
        any(_model_matches(name, config.chat_model) for name in names),
        any(_model_matches(name, config.embedding_model) for name in names),
    )
