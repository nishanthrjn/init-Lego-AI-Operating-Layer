"""Live-run preflight: read-only verification of the serving Ollama (LQ1.1).

Before any live fixture run, the harness asks the local Ollama server what is
actually serving, through `GET /api/version` and `GET /api/tags` only. It never
pulls, creates, deletes, generates or chats here. The observed server version
and the verified model digest become the report metadata; operator text never
overrides them.

Any failure is a closed `PreflightFailure`. It is raised before ForgeAI runs,
is never retried and has no fallback. These are harness setup failures, not
ForgeAI `TaskFailure` values.
"""

import json
import re
from dataclasses import dataclass
from enum import StrEnum
from http.client import HTTPException
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import ProxyHandler, Request, build_opener

VERSION_PATH = "/api/version"
TAGS_PATH = "/api/tags"
TIMEOUT_SECONDS = 10.0
MAX_RESPONSE_BYTES = 1_048_576
REQUESTED_DIGEST = re.compile(r"sha256:[0-9a-f]{64}")
OBSERVED_DIGEST = re.compile(r"[0-9a-f]{64}")


class PreflightFailure(StrEnum):
    """Why a live run was refused before any fixture ran."""

    OLLAMA_UNREACHABLE = "ollama_unreachable"
    OLLAMA_RESPONSE_INVALID = "ollama_response_invalid"
    MODEL_NOT_INSTALLED = "model_not_installed"
    MODEL_DIGEST_MISMATCH = "model_digest_mismatch"


class PreflightError(Exception):
    """The serving environment does not match the requested live baseline."""

    def __init__(self, failure: PreflightFailure, detail: str) -> None:
        super().__init__(f"{failure.name}: {detail}")
        self.failure = failure
        self.detail = detail


@dataclass(frozen=True, slots=True)
class ServingIdentity:
    """What the Ollama server reported, after verification."""

    ollama_version: str
    model_name: str
    model_digest: str


def _get_json(base_url: str, path: str, timeout: float) -> object:
    # No proxies: the preflight must observe the local server itself.
    opener = build_opener(ProxyHandler({}))
    request = Request(base_url.rstrip("/") + path, method="GET")
    try:
        with opener.open(request, timeout=timeout) as response:
            body = response.read(MAX_RESPONSE_BYTES + 1)
    except HTTPError as error:
        raise PreflightError(
            PreflightFailure.OLLAMA_RESPONSE_INVALID,
            f"GET {path} returned HTTP {error.code}",
        ) from error
    except (URLError, HTTPException, OSError) as error:
        raise PreflightError(
            PreflightFailure.OLLAMA_UNREACHABLE, f"GET {path} failed: {error}"
        ) from error
    if len(body) > MAX_RESPONSE_BYTES:
        raise PreflightError(
            PreflightFailure.OLLAMA_RESPONSE_INVALID,
            f"GET {path} response exceeds {MAX_RESPONSE_BYTES} bytes",
        )
    try:
        return json.loads(body)
    except (ValueError, RecursionError) as error:  # incl. JSON and UTF-8 errors
        raise PreflightError(
            PreflightFailure.OLLAMA_RESPONSE_INVALID, f"GET {path} is not JSON"
        ) from error


def _invalid(detail: str) -> PreflightError:
    return PreflightError(PreflightFailure.OLLAMA_RESPONSE_INVALID, detail)


def verify_ollama(
    base_url: str,
    model: str,
    model_digest: str,
    timeout: float = TIMEOUT_SECONDS,
) -> ServingIdentity:
    """Verify the server, the exact model name and its full digest.

    Raises ValueError for malformed operator input (before any request) and
    PreflightError for anything the server reports or fails to report.
    """
    location = urlsplit(base_url)
    if location.scheme not in {"http", "https"} or not location.netloc:
        raise ValueError("--ollama-url must be an http(s) URL")
    if not model.strip():
        raise ValueError("--model must be non-empty")
    if REQUESTED_DIGEST.fullmatch(model_digest) is None:
        raise ValueError("--model-digest must be sha256:<64 lowercase hex digits>")

    version = _get_json(base_url, VERSION_PATH, timeout)
    if not isinstance(version, dict):
        raise _invalid(f"{VERSION_PATH} is not an object")
    observed_version = version.get("version")
    if not isinstance(observed_version, str) or not observed_version.strip():
        raise _invalid(f"{VERSION_PATH} has no version string")

    tags = _get_json(base_url, TAGS_PATH, timeout)
    entries = tags.get("models") if isinstance(tags, dict) else None
    if not isinstance(entries, list):
        raise _invalid(f"{TAGS_PATH} has no models list")
    # Exact name only: no tag completion, no "latest" or quantization substitute.
    matches = [
        entry
        for entry in entries
        if isinstance(entry, dict) and entry.get("name") == model
    ]
    if not matches:
        raise PreflightError(
            PreflightFailure.MODEL_NOT_INSTALLED,
            f"{model!r} is not an installed model name (exact match required)",
        )
    if len(matches) > 1:
        raise _invalid(f"{TAGS_PATH} lists {model!r} more than once")
    observed = matches[0].get("digest")
    if not isinstance(observed, str) or OBSERVED_DIGEST.fullmatch(observed) is None:
        raise _invalid(f"{TAGS_PATH} has no full digest for {model!r}")
    observed_digest = f"sha256:{observed}"
    if observed_digest != model_digest:
        raise PreflightError(
            PreflightFailure.MODEL_DIGEST_MISMATCH,
            f"{model!r} is {observed_digest}, not the requested {model_digest}",
        )
    return ServingIdentity(observed_version.strip(), model, observed_digest)
