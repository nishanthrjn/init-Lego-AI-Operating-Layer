"""Private ADR-014 §14 ModelPort adapter: the OpenAI-compatible wire contract.

Construction is inert. Blocking stdlib HTTP runs in to_thread; cancellation
does not stop an in-flight provider request. No redirects, ambient proxies,
credentials, streaming, retries or fallback. Complete bodies are buffered,
as in the existing Ollama adapter; this is not a resource-budget system.

OPENAI-COMPATIBLE-REMOTE-1: a REMOTE binding reuses exactly this request
encoding, status mapping and response parsing. Its one exchange is supplied
per governed invocation by trusted composition (the credential-bearing
transport stays there); this module never sees a credential or header.
"""

import asyncio
import http.client
import json
import math
import socket
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import NoReturn

from legoai.capabilities.values import CapabilityOffer
from legoai.intelligence.model.ports import (
    ModelPreflightError,
    ModelResponseRejectedError,
    ModelResponseRetryableRejectedError,
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
from legoai.reference.model_capabilities import model_chat_offer, model_embedding_offer


def openai_compatible_plugin_id() -> PluginId:
    return PluginId("legoai.reference", "openai-compatible-model-adapter")


def openai_compatible_release() -> Version:
    return Version(1, 0, 0)


def openai_compatible_declaration(*, embedding: bool) -> PluginDeclaration:
    offers: tuple[CapabilityOffer, ...] = (model_chat_offer(),)
    if embedding:
        offers += (model_embedding_offer(),)
    return PluginDeclaration(
        openai_compatible_plugin_id(), openai_compatible_release(), offers
    )


@dataclass(frozen=True, slots=True)
class OpenAICompatibleModelConfig:
    """Private validated execution settings; URL is the versioned API root.

    max_output_tokens is bounded to 1..2**31-1 when present. This local
    representation bound is not a promise of provider capacity.
    """

    base_url: str = field(repr=False)
    chat_model: str
    embedding_model: str | None
    timeout_seconds: float
    max_output_tokens: int | None

    def __post_init__(self) -> None:
        if type(self.base_url) is not str:
            raise TypeError("base_url must be text")
        try:
            self.base_url.encode("ascii")
            url = urllib.parse.urlsplit(self.base_url)
            valid = (
                url.scheme in {"http", "https"}
                and bool(url.hostname)
                and url.username is None
                and url.password is None
                and not url.query
                and not url.fragment
                and url.port != 0
                and not any(
                    c.isspace() or ord(c) < 32 or ord(c) == 127 for c in self.base_url
                )
            )
        except ValueError, UnicodeError:
            valid = False
        if not valid:
            raise ValueError("invalid credential-free API root")
        names = (
            (self.chat_model,)
            if self.embedding_model is None
            else (self.chat_model, self.embedding_model)
        )
        for name in names:
            ModelId(name)
            if (
                not isinstance(name, str)
                or not name.strip()
                or any(ord(c) < 32 or ord(c) == 127 for c in name)
            ):
                raise ValueError("invalid model name")
            name.encode("utf-8")
        if type(self.chat_model) is not str:
            raise TypeError("chat model required")
        if (
            type(self.timeout_seconds) not in (int, float)
            or self.timeout_seconds <= 0
            or self.timeout_seconds > 1e308
            or not math.isfinite(self.timeout_seconds)
        ):
            raise ValueError("timeout must be positive and finite")
        if self.max_output_tokens is not None and (
            type(self.max_output_tokens) is not int
            or not 1 <= self.max_output_tokens <= 2**31 - 1
        ):
            raise ValueError("invalid max_output_tokens")


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(
        self,
        req: urllib.request.Request,
        fp: object,
        code: int,
        msg: str,
        headers: object,
        newurl: str,
    ) -> None:
        return None


def _reject() -> NoReturn:
    raise ModelResponseRejectedError("Model response outside qualified protocol")


def _optional_tokens(value: object) -> int | None:
    return value if type(value) is int and value >= 0 else None


def _json_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    fields: dict[str, object] = {}
    for name, value in pairs:
        if name in fields:
            raise ValueError("Duplicate JSON field")
        fields[name] = value
    return fields


def _invalid_constant(value: str) -> NoReturn:
    raise ValueError("Non-JSON numeric constant")


def _payload(status: int, raw: bytes) -> dict[str, object]:
    """Shared status mapping and JSON decoding of one complete response.

    Error bodies are never decoded or retained in diagnostics.
    """
    if status in (429, 503):
        raise ModelResponseRetryableRejectedError(f"Model rejected HTTP {status}")
    if not 200 <= status < 300:
        raise ModelResponseRejectedError(f"Model rejected HTTP {status}")
    return _json_body(raw)


def _finite_float(text: str) -> float:
    value = float(text)
    if not math.isfinite(value):
        raise ValueError("non-finite catalog number")
    return value


def _json_body(raw: bytes, *, finite_numbers: bool = False) -> dict[str, object]:
    """The one strict JSON decoding of a complete success body."""
    try:
        payload = json.loads(
            raw,
            object_pairs_hook=_json_object,
            parse_constant=_invalid_constant,
            parse_float=_finite_float if finite_numbers else float,
        )
    except ValueError, UnicodeError, RecursionError:
        # Reject outside the handler so JSONDecodeError.doc (the provider
        # body) is not retained in the public exception's causal chain.
        payload = None
    if not isinstance(payload, dict):
        _reject()
    return payload


def _max_listed_models() -> int:
    """Bound on advertised models accepted from one model-list response."""
    return 1024


def parse_model_list(raw: bytes) -> tuple[ModelId, ...]:
    """Bounded OpenAI-compatible model-list parser (PROVIDER-MODEL-DISCOVERY-1).

    Accepts only `{"data": [{"id": "<model>"}, ...]}` and extracts the ids;
    every other field is ignored and nothing is retained. Malformed structure,
    invalid or duplicate ids, or more than the bound fail closed. The result
    is an observation of what was advertised, never configuration.
    """
    data = _json_body(raw).get("data")
    if not isinstance(data, list) or len(data) > _max_listed_models():
        _reject()
    models: list[ModelId] = []
    for item in data:
        if not isinstance(item, dict):
            _reject()
        name = item.get("id")
        if (
            type(name) is not str
            or not 1 <= len(name) <= 256
            or not name.strip()
            or any(ord(c) < 32 or ord(c) == 127 for c in name)
        ):
            _reject()
        models.append(ModelId(name))
    if len(set(models)) != len(models):
        _reject()
    return tuple(models)


@dataclass(frozen=True, slots=True)
class DiscoveredProvider:
    """Advertised backend facts only; prices are USD per million tokens."""

    provider: str = field(repr=False)
    status: str | None = field(default=None, repr=False)
    input_price: float | None = field(default=None, repr=False)
    output_price: float | None = field(default=None, repr=False)


@dataclass(frozen=True, slots=True)
class DiscoveredModel:
    """Optional catalog selection evidence; never authority or a route."""

    model: ModelId = field(repr=False)
    providers: tuple[DiscoveredProvider, ...] = field(default=(), repr=False)
    input_modalities: tuple[str, ...] = field(default=(), repr=False)
    output_modalities: tuple[str, ...] = field(default=(), repr=False)


def _catalog_text(value: object, bound: int) -> str:
    if (
        type(value) is not str
        or not 1 <= len(value) <= bound
        or value != value.strip()
        or any(
            not c.isascii() or not c.isprintable() or c.isspace() or c in "*?"
            for c in value
        )
    ):
        _reject()
    return value


def _modalities(value: object) -> tuple[str, ...]:
    if not isinstance(value, list) or len(value) > 8:
        _reject()
    result = tuple(_catalog_text(item, 32) for item in value)
    if len(set(result)) != len(result):
        _reject()
    return result


def _price(value: object) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        _reject()
    if not 0 <= value <= 1_000_000 or not math.isfinite(value):
        _reject()
    return float(value)


def parse_model_catalog(raw: bytes) -> tuple[DiscoveredModel, ...]:
    """Opt-in selection profile: bounded architecture/providers/pricing fields.

    Unknown fields are discarded. Absent optional facts remain absent. This
    profile does not change the historical ID-only parser's acceptance scope.
    """
    if len(raw) > 4_194_304:
        _reject()
    ids = parse_model_list(raw)
    data = _json_body(raw, finite_numbers=True)["data"]
    assert isinstance(data, list)
    models: list[DiscoveredModel] = []
    for model, item in zip(ids, data, strict=True):
        _catalog_text(model.value, 256)
        architecture = item.get("architecture", {})
        if not isinstance(architecture, dict):
            _reject()
        inputs = _modalities(architecture.get("input_modalities", []))
        outputs = _modalities(architecture.get("output_modalities", []))
        raw_providers = item.get("providers", [])
        if not isinstance(raw_providers, list) or len(raw_providers) > 32:
            _reject()
        providers: list[DiscoveredProvider] = []
        for backend in raw_providers:
            if not isinstance(backend, dict):
                _reject()
            name = _catalog_text(backend.get("provider"), 128)
            status = backend.get("status")
            if status is not None:
                status = _catalog_text(status, 32)
            prices = backend.get("pricing", {})
            if not isinstance(prices, dict):
                _reject()
            providers.append(
                DiscoveredProvider(
                    name,
                    status,
                    _price(prices.get("input")),
                    _price(prices.get("output")),
                )
            )
        if len({p.provider for p in providers}) != len(providers):
            _reject()
        models.append(DiscoveredModel(model, tuple(providers), inputs, outputs))
    return tuple(models)


class OpenAICompatibleModelAdapter:
    """One non-streaming request per invocation behind the unchanged ModelPort.

    `exchange`, when given, performs the one request instead of local HTTP:
    it takes the path and encoded JSON body and returns the status and body
    of one complete response, or raises a Model error. Trusted composition
    supplies it per governed invocation; it runs on the calling thread.
    """

    def __init__(
        self,
        config: OpenAICompatibleModelConfig,
        provider_id: ProviderId,
        *,
        exchange: Callable[[str, bytes], tuple[int, bytes]] | None = None,
    ) -> None:
        if (
            type(config) is not OpenAICompatibleModelConfig
            or type(provider_id) is not ProviderId
        ):
            raise TypeError("adapter requires validated config and ProviderId")
        if exchange is not None and not callable(exchange):
            raise TypeError("exchange must be callable")
        self._config = config
        self._provider_id = provider_id
        self._exchange = exchange

    async def chat(self, request: ChatRequest) -> ChatResult:
        if type(request) is not ChatRequest:
            raise TypeError("chat requires ChatRequest")
        if request.response_format is not None:
            # ADR-022 support is not implemented or qualified for this adapter.
            # Refuse before any request rather than silently ignore it.
            raise ModelPreflightError(
                "structured output is not supported by this adapter"
            )
        body: dict[str, object] = {
            "model": self._config.chat_model,
            "messages": [
                {"role": m.role.value, "content": m.content} for m in request.messages
            ],
            "stream": False,
        }
        if self._config.max_output_tokens is not None:
            body["max_tokens"] = self._config.max_output_tokens
        payload = await self._request("/chat/completions", body)
        model = payload.get("model")
        if type(model) is not str or model != self._config.chat_model:
            _reject()
        choices = payload.get("choices")
        if not isinstance(choices, list) or len(choices) != 1:
            _reject()
        choice = choices[0]
        if not isinstance(choice, dict) or choice.get("finish_reason") != "stop":
            _reject()
        message = choice.get("message")
        if (
            not isinstance(message, dict)
            or message.get("role") != "assistant"
            or type(message.get("content")) is not str
            or "tool_calls" in message
            or "function_call" in message
        ):
            _reject()
        raw_usage = payload.get("usage")
        usage = None
        if isinstance(raw_usage, dict):
            usage = ModelUsage(
                _optional_tokens(raw_usage.get("prompt_tokens")),
                _optional_tokens(raw_usage.get("completion_tokens")),
            )
        return ChatResult(message["content"], ModelId(model), self._provider_id, usage)

    async def embed(self, request: EmbeddingRequest) -> EmbeddingResult:
        if type(request) is not EmbeddingRequest:
            raise TypeError("embed requires EmbeddingRequest")
        if self._config.embedding_model is None:
            raise ModelPreflightError("Embedding purpose unavailable")
        payload = await self._request(
            "/embeddings",
            {
                "model": self._config.embedding_model,
                "input": list(request.inputs),
            },
        )
        model = payload.get("model")
        if type(model) is not str or model != self._config.embedding_model:
            _reject()
        data = payload.get("data")
        if not isinstance(data, list) or len(data) != len(request.inputs):
            _reject()
        vectors: list[tuple[float, ...]] = []
        for index, item in enumerate(data):
            if (
                not isinstance(item, dict)
                or type(item.get("index")) is not int
                or item["index"] != index
            ):
                _reject()
            vector = item.get("embedding")
            if not isinstance(vector, list) or not vector:
                _reject()
            if any(type(component) not in (int, float) for component in vector):
                _reject()
            try:
                vectors.append(tuple(float(component) for component in vector))
            except OverflowError, ValueError:
                _reject()
        try:
            return EmbeddingResult(
                tuple(vectors),
                len(vectors[0]) if vectors else 0,
                ModelId(model),
                self._provider_id,
            )
        except TypeError, ValueError:
            _reject()

    async def _request(self, path: str, body: dict[str, object]) -> dict[str, object]:
        if self._exchange is None:
            return await asyncio.to_thread(self._post, path, body)
        status, raw = self._exchange(path, json.dumps(body).encode("utf-8"))
        return _payload(status, raw)

    def _post(self, path: str, body: dict[str, object]) -> dict[str, object]:
        request = urllib.request.Request(
            self._config.base_url.rstrip("/") + path,
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        # Explicit empty proxy map avoids ambient proxy configuration/credentials.
        opener = urllib.request.build_opener(
            urllib.request.ProxyHandler({}), _NoRedirect()
        )
        try:
            try:
                response = opener.open(request, timeout=self._config.timeout_seconds)
            except urllib.error.HTTPError as error:
                response = error
            with response:
                status = response.code
                # Read even error replies to establish completion, but never decode
                # or retain their bodies in diagnostics. Truncation stays UNKNOWN.
                raw = response.read()
                length = response.headers.get("Content-Length")
                if length is not None and len(raw) != int(length):
                    raise ModelResponseUncertainError("Incomplete Model response")
        except urllib.error.URLError as error:
            if isinstance(error.reason, (ConnectionRefusedError, socket.gaierror)):
                raise ModelPreflightError("Model connection not established") from None
            raise ModelResponseUncertainError("Model transport uncertain") from None
        except OSError, http.client.HTTPException, ValueError:
            raise ModelResponseUncertainError("Model transport uncertain") from None
        return _payload(status, raw)
