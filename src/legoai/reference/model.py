"""LegoAI v0.1: `OllamaModelAdapter` -- the reference `ModelPort` realization
for the default v0.1 provider, per `planning/documind/
EMBEDDING-CAPABILITY-DESIGN.md` SS12's live-verified recommendation: direct
HTTP against Ollama's native `/api/chat` and `/api/embed` endpoints, no
`ollama` package, no Semantic Kernel/Microsoft Agent Framework, no
`httpx`/`requests` dependency -- stdlib `urllib.request` only, preserving
Gate-2's zero-new-runtime-dependency invariant (`planning/
V0.1-DOCUMIND-IMPLEMENTATION-PLAN.md` SS E).

This module lives beside `legoai.reference.execution`/`.governance`/
`.catalog` (the same "reference realization of a public Port" placement
ADR-002 already established repeatedly), never inside
`legoai.intelligence.model` itself -- that module's own SS9.2 I-row
permissions exclude nothing relevant here, but keeping the concrete,
provider-specific, network-performing realization in `legoai.reference`
mirrors every prior Gate-2 Port/realization split exactly.

**Blocking I/O, bridged explicitly, never inside the event loop thread.**
`urllib.request.urlopen` is a synchronous, blocking call. Both `chat`/
`embed` wrap their actual HTTP call in `asyncio.to_thread(...)` -- the
smallest possible bridge for exactly one blocking call per invocation, not
ADR-015 SS10's full bounded-worker-pool bridge (that section's own text:
"the first cooperative deterministic slice need not use the thread
bridge... blocking paths become supported only after their worker
acceptance/cancellation/exit are qualified" -- a full pool is future,
separately-qualified work; one `to_thread` call per request is the smallest
correct increment for v0.1's synchronous local-Ollama scope).

**Effect-phase classification, stated once here, not reinvented per call
site:**

    connection refused / DNS failure / other pre-send error -> ModelPreflightError
    socket timeout while waiting for a response after the request was sent
        -> ModelResponseUncertainError (never re-classified as "definitely
           nothing happened" -- ADR-015's own "do not fabricate certainty"
           principle, applied here for the first genuinely uncertain effect
           in this codebase)
    a complete HTTP response is received but is a non-2xx status, malformed
        JSON, or missing an expected field -> ModelResponseRejectedError
    a complete, well-formed response that fails this capability's own
        mandatory validation (wrong embedding count/dimension/non-finite
        numbers, per EMBEDDING-CAPABILITY-DESIGN.md SS18)
        -> ModelResponseRejectedError

No raw `urllib`/`http.client`/`json` exception ever escapes this module --
every failure is re-raised as exactly one of the three `ModelPort`-declared
exception classes, so a composition-layer caller never needs to interpret
Python's own low-level exception hierarchy to decide `EffectExtent`.
"""

from __future__ import annotations

import asyncio
import json
import math
import urllib.error
import urllib.request
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import NoReturn

from legoai.capabilities.values import CapabilityId, CapabilityOffer
from legoai.intelligence.model.ports import (
    ModelPreflightError,
    ModelResponseRejectedError,
    ModelResponseUncertainError,
)
from legoai.intelligence.model.values import (
    ChatRequest,
    ChatResult,
    EmbeddingRequest,
    EmbeddingResult,
    ModelId,
    ModelUsage,
    ProviderId,
)
from legoai.kernel.versions import Version
from legoai.plugins.values import PluginDeclaration, PluginId


def ollama_plugin_id() -> PluginId:
    """The one fixed Plugin identity this module's Adapter realizes --
    mirrors `legoai.reference.deterministic.text_normalization_plugin_id`'s
    exact pattern for M11's own trusted-implementation correspondence."""
    return PluginId("legoai.reference", "ollama-model-adapter")


def ollama_release() -> Version:
    return Version(1, 0, 0)


def ollama_chat_capability_id() -> CapabilityId:
    return CapabilityId("legoai.intelligence.model.chat")


def ollama_embedding_capability_id() -> CapabilityId:
    return CapabilityId("legoai.intelligence.model.embedding")


def ollama_chat_offer() -> CapabilityOffer:
    return CapabilityOffer(ollama_chat_capability_id(), ollama_release())


def ollama_embedding_offer() -> CapabilityOffer:
    return CapabilityOffer(ollama_embedding_capability_id(), ollama_release())


def ollama_declaration() -> PluginDeclaration:
    """The inert Plugin declaration published to the Catalog for this one
    trusted Adapter -- one Plugin release, two Capability offers (chat,
    embedding), per task SS47 ("publish provider capabilities through the
    existing Catalog... do not create a parallel provider registry")."""
    return PluginDeclaration(
        ollama_plugin_id(),
        ollama_release(),
        (ollama_chat_offer(), ollama_embedding_offer()),
    )


@dataclass(frozen=True, slots=True)
class OllamaModelConfig:
    """Explicit Adapter configuration (task SS13): base URL, chat model,
    embedding model, timeout, all mandatory -- no hidden machine-specific
    default beyond the one documented local Ollama convention
    (`http://localhost:11434`), and no secret field (a local Ollama
    instance requires no authentication; EMBEDDING-CAPABILITY-DESIGN.md
    SS14)."""

    base_url: str = field(repr=False)
    chat_model: str
    embedding_model: str
    timeout_seconds: float

    def __post_init__(self) -> None:
        if type(self.base_url) is not str or not self.base_url:
            raise TypeError("Ollama config requires a non-empty base_url")
        if type(self.chat_model) is not str or not self.chat_model:
            raise TypeError("Ollama config requires a non-empty chat_model")
        if type(self.embedding_model) is not str or not self.embedding_model:
            raise TypeError("Ollama config requires a non-empty embedding_model")
        if type(self.timeout_seconds) not in (int, float) or self.timeout_seconds <= 0:
            raise TypeError("Ollama config requires a positive timeout_seconds")


class OllamaModelAdapter:
    """Reference `ModelPort` realization backed by a local Ollama instance.
    Constructing this performs no I/O and no capability invocation --
    identical construction-inertness discipline to every prior Gate-2
    reference realization."""

    def __init__(self, config: OllamaModelConfig, provider_id: ProviderId) -> None:
        self._config = config
        self._provider_id = provider_id

    async def chat(self, request: ChatRequest) -> ChatResult:
        if type(request) is not ChatRequest:
            raise TypeError("chat requires ChatRequest")
        body = {
            "model": self._config.chat_model,
            "messages": [
                {"role": message.role.value, "content": message.content}
                for message in request.messages
            ],
            "stream": False,
        }
        payload = await asyncio.to_thread(self._post, "/api/chat", body)
        message = payload.get("message")
        if not isinstance(message, dict) or "content" not in message:
            raise ModelResponseRejectedError(
                "Ollama /api/chat response missing message.content"
            )
        content = message["content"]
        if type(content) is not str:
            raise ModelResponseRejectedError(
                "Ollama /api/chat response message.content is not a string"
            )
        usage = ModelUsage(
            prompt_tokens=_optional_int(payload.get("prompt_eval_count")),
            completion_tokens=_optional_int(payload.get("eval_count")),
        )
        return ChatResult(
            content, ModelId(self._config.chat_model), self._provider_id, usage
        )

    async def embed(self, request: EmbeddingRequest) -> EmbeddingResult:
        if type(request) is not EmbeddingRequest:
            raise TypeError("embed requires EmbeddingRequest")
        body = {"model": self._config.embedding_model, "input": list(request.inputs)}
        payload = await asyncio.to_thread(self._post, "/api/embed", body)
        raw_vectors = payload.get("embeddings")
        if not isinstance(raw_vectors, list):
            raise ModelResponseRejectedError(
                "Ollama /api/embed response missing embeddings list"
            )
        if len(raw_vectors) != len(request.inputs):
            raise ModelResponseRejectedError(
                f"Ollama /api/embed returned {len(raw_vectors)} vectors for "
                f"{len(request.inputs)} inputs"
            )
        vectors: list[tuple[float, ...]] = []
        dimension: int | None = None
        for raw_vector in raw_vectors:
            if not isinstance(raw_vector, list) or not raw_vector:
                raise ModelResponseRejectedError(
                    "Ollama /api/embed returned an empty or non-list vector"
                )
            if dimension is None:
                dimension = len(raw_vector)
            elif len(raw_vector) != dimension:
                raise ModelResponseRejectedError(
                    "Ollama /api/embed returned vectors of inconsistent dimension"
                )
            components: list[float] = []
            for raw_component in raw_vector:
                try:
                    component = float(raw_component)
                except (TypeError, ValueError) as exc:
                    raise ModelResponseRejectedError(
                        "Ollama /api/embed returned a non-numeric vector component"
                    ) from exc
                if not math.isfinite(component):
                    raise ModelResponseRejectedError(
                        "Ollama /api/embed returned a non-finite vector component"
                    )
                components.append(component)
            vectors.append(tuple(components))
        return EmbeddingResult(
            tuple(vectors),
            dimension if dimension is not None else 0,
            ModelId(self._config.embedding_model),
            self._provider_id,
        )

    def _post(self, path: str, body: Mapping[str, object]) -> dict[str, object]:
        """Synchronous HTTP POST, run only via `asyncio.to_thread`. Never
        called directly from `chat`/`embed`'s own coroutine body."""
        url = self._config.base_url.rstrip("/") + path
        data = json.dumps(body).encode("utf-8")
        http_request = urllib.request.Request(
            url, data=data, headers={"Content-Type": "application/json"}, method="POST"
        )
        try:
            with urllib.request.urlopen(
                http_request, timeout=self._config.timeout_seconds
            ) as response:
                raw = response.read()
                status = response.status
        except TimeoutError as exc:
            raise ModelResponseUncertainError(
                f"Ollama request to {path} timed out awaiting a response"
            ) from exc
        except urllib.error.HTTPError as exc:
            raw = exc.read()
            status = exc.code
            return self._reject_on_error_status(path, status, raw)
        except urllib.error.URLError as exc:
            if isinstance(exc.reason, TimeoutError):
                raise ModelResponseUncertainError(
                    f"Ollama request to {path} timed out awaiting a response"
                ) from exc
            raise ModelPreflightError(
                f"Ollama request to {path} could not be sent: {exc.reason}"
            ) from exc
        except OSError as exc:
            raise ModelPreflightError(
                f"Ollama request to {path} could not be sent: {exc}"
            ) from exc
        if status != 200:
            return self._reject_on_error_status(path, status, raw)
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ModelResponseRejectedError(
                f"Ollama response from {path} is not valid JSON"
            ) from exc
        if not isinstance(parsed, dict):
            raise ModelResponseRejectedError(
                f"Ollama response from {path} is not a JSON object"
            )
        return parsed

    @staticmethod
    def _reject_on_error_status(path: str, status: int, raw: bytes) -> NoReturn:
        try:
            body = json.loads(raw)
            detail = body.get("error") if isinstance(body, dict) else None
        except json.JSONDecodeError:
            detail = None
        message = f"Ollama request to {path} failed with HTTP {status}"
        if detail:
            message = f"{message}: {detail}"
        raise ModelResponseRejectedError(message)


def _optional_int(value: object) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value
