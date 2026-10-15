"""Private ADR-014 §14 ModelPort adapter: the OpenAI-compatible wire contract.

Construction is inert. Blocking stdlib HTTP runs in to_thread; cancellation
does not stop an in-flight provider request. No redirects, ambient proxies,
credentials, streaming, retries or fallback. Local response buffering is capped
at 1 MiB; this is not a general resource-budget or hard-cancellation system.

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
from enum import Enum
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
    ModelFailure,
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

    deterministic: bool = False

    def __post_init__(self) -> None:
        if type(self.deterministic) is not bool:
            raise TypeError("deterministic must be bool")
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
    raise ModelResponseRejectedError(
        "Model response outside qualified protocol",
        failure=ModelFailure.PROTOCOL_INCOMPATIBLE,
    )


def _optional_tokens(value: object) -> int | None:
    return value if type(value) is int and value >= 0 else None


class _FinishReasonCategory(Enum):
    ABSENT = "ABSENT"
    NULL = "NULL"
    STOP = "STOP"
    LENGTH = "LENGTH"
    CONTENT_FILTER = "CONTENT_FILTER"
    TOOL_CALLS = "TOOL_CALLS"
    FUNCTION_CALL = "FUNCTION_CALL"
    OTHER_STRING = "OTHER_STRING"
    NON_STRING = "NON_STRING"


def _finish_reason_category(choice: dict[str, object]) -> _FinishReasonCategory:
    if "finish_reason" not in choice:
        return _FinishReasonCategory.ABSENT
    value = choice["finish_reason"]
    if value is None:
        return _FinishReasonCategory.NULL
    if type(value) is not str:
        return _FinishReasonCategory.NON_STRING
    return {
        "stop": _FinishReasonCategory.STOP,
        "length": _FinishReasonCategory.LENGTH,
        "content_filter": _FinishReasonCategory.CONTENT_FILTER,
        "tool_calls": _FinishReasonCategory.TOOL_CALLS,
        "function_call": _FinishReasonCategory.FUNCTION_CALL,
    }.get(value, _FinishReasonCategory.OTHER_STRING)


class _CallFieldShape(Enum):
    ABSENT = "ABSENT"
    NULL = "NULL"
    EMPTY_OBJECT = "EMPTY_OBJECT"
    NONEMPTY_OBJECT = "NONEMPTY_OBJECT"
    EMPTY_ARRAY = "EMPTY_ARRAY"
    NONEMPTY_ARRAY = "NONEMPTY_ARRAY"
    STRING = "STRING"
    NUMBER = "NUMBER"
    BOOLEAN = "BOOLEAN"
    OTHER = "OTHER"


def _call_field_shape(message: dict[str, object], field: str) -> _CallFieldShape:
    if field not in message:
        return _CallFieldShape.ABSENT
    value = message[field]
    if value is None:
        return _CallFieldShape.NULL
    if type(value) is dict:
        return (
            _CallFieldShape.NONEMPTY_OBJECT if value else _CallFieldShape.EMPTY_OBJECT
        )
    if type(value) is list:
        return _CallFieldShape.NONEMPTY_ARRAY if value else _CallFieldShape.EMPTY_ARRAY
    if type(value) is str:
        return _CallFieldShape.STRING
    if type(value) is bool:
        return _CallFieldShape.BOOLEAN
    if type(value) in (int, float):
        return _CallFieldShape.NUMBER
    return _CallFieldShape.OTHER


class _ChatContractReason(Enum):
    JSON_INVALID = "JSON_INVALID"
    ROOT_NOT_OBJECT = "ROOT_NOT_OBJECT"
    MODEL_FIELD_MISSING = "MODEL_FIELD_MISSING"
    MODEL_FIELD_NOT_STRING = "MODEL_FIELD_NOT_STRING"
    MODEL_ID_MISMATCH = "MODEL_ID_MISMATCH"
    CHOICES_MISSING = "CHOICES_MISSING"
    CHOICES_NOT_LIST = "CHOICES_NOT_LIST"
    CHOICE_COUNT_INVALID = "CHOICE_COUNT_INVALID"
    CHOICE_NOT_OBJECT = "CHOICE_NOT_OBJECT"
    FINISH_REASON_MISSING = "FINISH_REASON_MISSING"
    FINISH_REASON_INVALID = "FINISH_REASON_INVALID"
    MESSAGE_MISSING = "MESSAGE_MISSING"
    MESSAGE_NOT_OBJECT = "MESSAGE_NOT_OBJECT"
    ROLE_INVALID = "ROLE_INVALID"
    CONTENT_MISSING = "CONTENT_MISSING"
    CONTENT_NULL = "CONTENT_NULL"
    CONTENT_NOT_STRING = "CONTENT_NOT_STRING"
    TOOL_CALL_PRESENT = "TOOL_CALL_PRESENT"
    FUNCTION_CALL_PRESENT = "FUNCTION_CALL_PRESENT"
    RESULT_CONSTRUCTION_FAILED = "RESULT_CONSTRUCTION_FAILED"
    VALIDATED = "VALIDATED"


def _observe_contract(
    observer: Callable[[_ChatContractReason], None] | None,
    reason: _ChatContractReason,
) -> None:
    if observer is not None:
        try:
            observer(reason)
        except Exception:
            # Optional evidence must not alter parsing, errors or effects.
            pass


def _json_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    fields: dict[str, object] = {}
    for name, value in pairs:
        if name in fields:
            raise ValueError("Duplicate JSON field")
        fields[name] = value
    return fields


def _invalid_constant(value: str) -> NoReturn:
    raise ValueError("Non-JSON numeric constant")


def _payload(
    status: int,
    raw: bytes,
    *,
    _observer: Callable[[_ChatContractReason], None] | None = None,
) -> dict[str, object]:
    """Shared status mapping and JSON decoding of one complete response.

    Only a closed model-not-found code is projected; no provider text is retained.
    """
    if status in (429, 503):
        raise ModelResponseRetryableRejectedError(
            f"Model rejected HTTP {status}", failure=ModelFailure.REQUEST_REJECTED
        )
    if not 200 <= status < 300:
        failure = ModelFailure.REQUEST_REJECTED
        # Status 404 alone does not distinguish endpoint from missing model.
        # A bounded explicit code does; never expose message/details/body.
        if len(raw) <= 4096:
            try:
                rejected = _json_body(raw)
                detail = rejected.get("error") if type(rejected) is dict else None
                if type(detail) is dict and detail.get("code") in (
                    "model_not_found",
                    "model_not_available",
                ):
                    failure = ModelFailure.MODEL_UNAVAILABLE
            except ModelResponseRejectedError, ValueError, UnicodeError, RecursionError:
                pass
        raise ModelResponseRejectedError(
            f"Model rejected HTTP {status}", failure=failure
        )
    return _json_body(raw, _observer=_observer)


def _finite_float(text: str) -> float:
    value = float(text)
    if not math.isfinite(value):
        raise ValueError("non-finite catalog number")
    return value


def _json_body(
    raw: bytes,
    *,
    finite_numbers: bool = False,
    _observer: Callable[[_ChatContractReason], None] | None = None,
) -> dict[str, object]:
    """The one strict JSON decoding of a complete success body."""
    invalid = False
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
        invalid = True
    if not isinstance(payload, dict):
        _observe_contract(
            _observer,
            _ChatContractReason.JSON_INVALID
            if invalid
            else _ChatContractReason.ROOT_NOT_OBJECT,
        )
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
        self._contract_reason: _ChatContractReason | None = None
        self._call_shapes: tuple[_CallFieldShape, _CallFieldShape] | None = None
        self._finish_category: _FinishReasonCategory | None = None

    def _record_finish_category(self, choice: dict[str, object]) -> None:
        self._finish_category = _finish_reason_category(choice)

    def _record_call_shapes(self, message: dict[str, object]) -> None:
        self._call_shapes = (
            _call_field_shape(message, "function_call"),
            _call_field_shape(message, "tool_calls"),
        )

    def _record_contract(self, reason: _ChatContractReason) -> None:
        self._contract_reason = reason

    def _contract_reject(self, reason: _ChatContractReason) -> NoReturn:
        _observe_contract(self._record_contract, reason)
        _reject()

    def _chat_contract_items(self) -> tuple[tuple[str, str], ...]:
        """Ephemeral closed projection; no body, content or model IDs retained."""
        reason = self._contract_reason
        if type(reason) is not _ChatContractReason:
            return ()
        items = [
            ("rejection_reason", reason.value),
            (
                "json_valid",
                "false" if reason is _ChatContractReason.JSON_INVALID else "true",
            ),
        ]
        if reason is _ChatContractReason.MODEL_ID_MISMATCH:
            items.append(("returned_model_matches_requested", "false"))
        elif reason not in {
            _ChatContractReason.JSON_INVALID,
            _ChatContractReason.ROOT_NOT_OBJECT,
            _ChatContractReason.MODEL_FIELD_MISSING,
            _ChatContractReason.MODEL_FIELD_NOT_STRING,
        }:
            items.append(("returned_model_matches_requested", "true"))
        if type(self._finish_category) is _FinishReasonCategory:
            items.append(("finish_reason_category", self._finish_category.value))
        shapes = self._call_shapes
        if (
            type(shapes) is tuple
            and len(shapes) == 2
            and all(type(shape) is _CallFieldShape for shape in shapes)
        ):
            for field, shape in zip(
                ("function_call", "tool_calls"), shapes, strict=True
            ):
                items.append(
                    (
                        field + "_present",
                        str(shape is not _CallFieldShape.ABSENT).lower(),
                    )
                )
                items.append((field + "_shape", shape.value))
        return tuple(items)

    async def chat(self, request: ChatRequest) -> ChatResult:
        self._contract_reason = None
        self._call_shapes = None
        self._finish_category = None
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
        if self._config.deterministic:
            body["temperature"] = 0
        payload = await self._request("/chat/completions", body)
        model = payload.get("model")
        if type(model) is not str or model != self._config.chat_model:
            self._contract_reject(
                _ChatContractReason.MODEL_FIELD_MISSING
                if "model" not in payload
                else _ChatContractReason.MODEL_FIELD_NOT_STRING
                if type(model) is not str
                else _ChatContractReason.MODEL_ID_MISMATCH
            )
        choices = payload.get("choices")
        if not isinstance(choices, list) or len(choices) != 1:
            self._contract_reject(
                _ChatContractReason.CHOICES_MISSING
                if "choices" not in payload
                else _ChatContractReason.CHOICES_NOT_LIST
                if not isinstance(choices, list)
                else _ChatContractReason.CHOICE_COUNT_INVALID
            )
        choice = choices[0]
        if not isinstance(choice, dict):
            self._contract_reject(_ChatContractReason.CHOICE_NOT_OBJECT)
        try:
            self._record_finish_category(choice)
        except Exception:
            # Optional observation must never change acceptance or failure.
            self._finish_category = None
        if choice.get("finish_reason") != "stop":
            self._contract_reject(
                _ChatContractReason.FINISH_REASON_MISSING
                if "finish_reason" not in choice
                else _ChatContractReason.FINISH_REASON_INVALID
            )
        message = choice.get("message")
        if not isinstance(message, dict):
            self._contract_reject(
                _ChatContractReason.MESSAGE_MISSING
                if "message" not in choice
                else _ChatContractReason.MESSAGE_NOT_OBJECT
            )
        if message.get("role") != "assistant":
            self._contract_reject(_ChatContractReason.ROLE_INVALID)
        if type(message.get("content")) is not str:
            self._contract_reject(
                _ChatContractReason.CONTENT_MISSING
                if "content" not in message
                else _ChatContractReason.CONTENT_NULL
                if message.get("content") is None
                else _ChatContractReason.CONTENT_NOT_STRING
            )
        try:
            self._record_call_shapes(message)
        except Exception:
            # Observation failure must not change the following presence gates.
            self._call_shapes = None
        if "tool_calls" in message:
            self._contract_reject(_ChatContractReason.TOOL_CALL_PRESENT)
        if "function_call" in message and message["function_call"] is not None:
            self._contract_reject(_ChatContractReason.FUNCTION_CALL_PRESENT)
        raw_usage = payload.get("usage")
        usage = None
        if isinstance(raw_usage, dict):
            usage = ModelUsage(
                _optional_tokens(raw_usage.get("prompt_tokens")),
                _optional_tokens(raw_usage.get("completion_tokens")),
            )
        try:
            result = ChatResult(
                message["content"], ModelId(model), self._provider_id, usage
            )
        except Exception:
            _observe_contract(
                self._record_contract, _ChatContractReason.RESULT_CONSTRUCTION_FAILED
            )
            raise
        _observe_contract(self._record_contract, _ChatContractReason.VALIDATED)
        return result

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
        return _payload(
            status,
            raw,
            _observer=self._record_contract if path == "/chat/completions" else None,
        )

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
                # Read error replies to establish completion; only _payload's
                # closed diagnostic projection is exposed. Truncation is UNKNOWN.
                raw = response.read(1_048_577)
                if len(raw) > 1_048_576:
                    raise ModelResponseUncertainError(
                        "Model response exceeds bound",
                        failure=ModelFailure.PROTOCOL_INCOMPATIBLE,
                    )
                length = response.headers.get("Content-Length")
                if length is not None and len(raw) != int(length):
                    raise ModelResponseUncertainError("Incomplete Model response")
        except urllib.error.URLError as error:
            if isinstance(error.reason, (ConnectionRefusedError, socket.gaierror)):
                raise ModelPreflightError(
                    "Model connection not established",
                    failure=ModelFailure.ENDPOINT_UNAVAILABLE,
                ) from None
            if isinstance(error.reason, TimeoutError):
                raise ModelResponseUncertainError(
                    "Model timeout", failure=ModelFailure.TIMEOUT
                ) from None
            raise ModelResponseUncertainError("Model transport uncertain") from None
        except TimeoutError:
            raise ModelResponseUncertainError(
                "Model timeout", failure=ModelFailure.TIMEOUT
            ) from None
        except OSError, http.client.HTTPException, ValueError:
            raise ModelResponseUncertainError("Model transport uncertain") from None
        return _payload(
            status,
            raw,
            _observer=self._record_contract if path == "/chat/completions" else None,
        )
