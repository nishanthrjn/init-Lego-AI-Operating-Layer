"""LegoAI v0.1: `legoai.intelligence.model` public semantic values -- the
smallest Model interaction vocabulary DocuMind's two effectful capabilities
(chat/text generation, batch embedding) require.

ADR-002 SS7.3/SS15 reserves exactly this package for exactly this purpose
("Model Interaction descriptors, validation/usage, Model Port... a Model
Adapter imports that Port; an outer permitted consumer obtains governed
Execution attribution and invokes it"); SS9.2's I-row foreign-target maximum
is K, C, M, A, G, R, O, X -- **no E (Execution)**. This module and its
sibling `ports.py` therefore never import `legoai.execution`/
`legoai.reference.execution`: governed invocation attribution is composed
around these values by an outer caller (`legoai.runtime._composition`),
exactly the same split M11 already established between
`legoai.reference.execution` (capability-agnostic) and
`legoai.runtime._composition.governed` (the actual correspondence/typed
call) -- see `planning/V0.1-DOCUMIND-IMPLEMENTATION-PLAN.md` SS D/E.

Preserved conceptual separations (task's own framing):

    Model != Agent != Workflow != Retriever != Memory != Provider != Plugin

This module defines only what a Model *result* and *request* mean -- never
a provider SDK type, a `dict[str, Any]` options bag, or a
`ChatHistory`/`Agent` object from any framework. Provider-specific
configuration (endpoint, timeout, batch size, exact model name to bind to)
is Adapter configuration (`legoai.reference.model`), never part of these
request/result contracts -- mirroring `planning/documind/
EMBEDDING-CAPABILITY-DESIGN.md` SS13's already-settled reasoning, applied
identically to chat.

`ModelId`/`ProviderId` are declared **facts about which model/provider
actually produced a result** -- never caller-selected inputs on a request.
A request never names the model it wants; Catalog/Resolution (already
governed, per Gate-2) decides which published offer answers a given
capability, and the Adapter's own configuration decides which concrete
model backs that offer. This mirrors exactly how `DispatchPermit`/
`CatalogEntry` carry attribution facts, never caller-chosen implementation
selection.
"""

from dataclasses import dataclass, field
from enum import Enum

from legoai.kernel.identity import _validate


@dataclass(frozen=True, slots=True)
class ModelId:
    """Opaque identity of the specific model that produced a result (e.g.
    ``"llama3.2"``, ``"nomic-embed-text"``) -- a declared fact, never a
    caller-supplied request field. Construction claims nothing about the
    model's availability, capability, or trustworthiness."""

    value: str = field(repr=False)

    def __post_init__(self) -> None:
        _validate(self.value)


@dataclass(frozen=True, slots=True)
class ProviderId:
    """Opaque identity of the provider/Adapter instance that produced a
    result (e.g. an Ollama endpoint identity) -- distinct from `ModelId`,
    since the same model name could in principle be served by different
    providers (EMBEDDING-CAPABILITY-DESIGN.md SS11)."""

    value: str = field(repr=False)

    def __post_init__(self) -> None:
        _validate(self.value)


class ChatRole(Enum):
    """The minimal role vocabulary DocuMind's answering capability needs.
    No `function`/`tool` role exists here -- no Tool/Agent concept is part
    of this v0.1 slice (task SS50)."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


@dataclass(frozen=True, slots=True)
class ChatMessage:
    """One role-attributed message. Content is plain text -- never a
    provider-native content-block/multimodal-part structure; v0.1 has no
    multimodal requirement."""

    role: ChatRole
    content: str = field(repr=False)

    def __post_init__(self) -> None:
        if type(self.role) is not ChatRole:
            raise TypeError("chat message requires ChatRole")
        if type(self.content) is not str:
            raise TypeError("chat message content must be str")


@dataclass(frozen=True, slots=True)
class ChatRequest:
    """An ordered conversation to complete. Carries no model/provider
    selection (see module docstring), no raw provider options bag, and no
    Agent/Goal/Team concept. `messages` must be non-empty -- an empty
    conversation has no meaningful completion."""

    messages: tuple[ChatMessage, ...]

    def __post_init__(self) -> None:
        if type(self.messages) is not tuple or any(
            type(message) is not ChatMessage for message in self.messages
        ):
            raise TypeError(
                "chat request messages must be an immutable tuple of ChatMessage"
            )
        if len(self.messages) == 0:
            raise ValueError("chat request requires at least one message")


@dataclass(frozen=True, slots=True)
class ModelUsage:
    """Observed, post-hoc resource facts a provider makes available --
    never a pre-reservation or a claim that capacity was reserved (task
    SS45: "declared estimate/bound... distinct from actual recorded
    usage"). Both fields are `None` when the provider does not report them;
    this type never fabricates a count the provider did not supply."""

    prompt_tokens: int | None
    completion_tokens: int | None

    def __post_init__(self) -> None:
        for value in (self.prompt_tokens, self.completion_tokens):
            if value is not None and (type(value) is not int or value < 0):
                raise TypeError(
                    "model usage token counts must be a nonnegative int or None"
                )


@dataclass(frozen=True, slots=True)
class ChatResult:
    """A completed chat response. `model_identity`/`provider_identity` are
    mandatory declared facts (never omitted, never fabricated) -- SPEC S-12
    material-fact traceability, applied identically to
    `EMBEDDING-CAPABILITY-DESIGN.md` SS11's already-settled reasoning for
    embeddings."""

    content: str = field(repr=False)
    model_identity: ModelId
    provider_identity: ProviderId
    usage: ModelUsage | None

    def __post_init__(self) -> None:
        if type(self.content) is not str:
            raise TypeError("chat result content must be str")
        if type(self.model_identity) is not ModelId:
            raise TypeError("chat result requires ModelId")
        if type(self.provider_identity) is not ProviderId:
            raise TypeError("chat result requires ProviderId")
        if self.usage is not None and type(self.usage) is not ModelUsage:
            raise TypeError("chat result usage must be ModelUsage or None")


@dataclass(frozen=True, slots=True)
class EmbeddingRequest:
    """A batch of text to embed. One canonical shape, always a tuple --
    deliberately no separate scalar entry point
    (EMBEDDING-CAPABILITY-DESIGN.md SS9: a live-verified provider-level
    scalar/array asymmetry makes a single always-batch shape both simpler
    and safer)."""

    inputs: tuple[str, ...]

    def __post_init__(self) -> None:
        if type(self.inputs) is not tuple or any(
            type(item) is not str for item in self.inputs
        ):
            raise TypeError(
                "embedding request inputs must be an immutable tuple of str"
            )


@dataclass(frozen=True, slots=True)
class EmbeddingResult:
    """Ordered embedding vectors, one per `EmbeddingRequest.inputs` entry,
    all of identical `dimension` -- `dimension` is an **observed** fact
    about the actual response, never a hardcoded constant
    (EMBEDDING-CAPABILITY-DESIGN.md SS10). Construction enforces the exact
    mandatory validation SS18 requires: count match is the caller's
    responsibility to have already established, but internal
    consistency (uniform positive dimension, all-finite numbers) is
    enforced here, unconditionally, by every caller that constructs this
    type.

    For a genuinely empty `inputs`/`vectors` (EMBEDDING-CAPABILITY-DESIGN.md
    SS26's open question, resolved here): `dimension` is exactly `0` --
    there is no vector to observe a dimension from, so `0` states that
    honestly rather than fabricating a positive number. Any non-empty
    `vectors` still requires a positive, uniformly-observed `dimension`."""

    vectors: tuple[tuple[float, ...], ...]
    dimension: int
    model_identity: ModelId
    provider_identity: ProviderId

    def __post_init__(self) -> None:
        if type(self.vectors) is not tuple or any(
            type(vector) is not tuple for vector in self.vectors
        ):
            raise TypeError(
                "embedding result vectors must be an immutable tuple of tuples"
            )
        if type(self.dimension) is not int or isinstance(self.dimension, bool):
            raise TypeError("embedding result dimension must be an int")
        if len(self.vectors) == 0:
            if self.dimension != 0:
                raise ValueError("empty embedding result dimension must be exactly 0")
        elif self.dimension <= 0:
            raise ValueError("embedding result dimension must be positive")
        if type(self.model_identity) is not ModelId:
            raise TypeError("embedding result requires ModelId")
        if type(self.provider_identity) is not ProviderId:
            raise TypeError("embedding result requires ProviderId")
        for vector in self.vectors:
            if len(vector) != self.dimension:
                raise ValueError("embedding result vector length must equal dimension")
            for component in vector:
                if (
                    type(component) is not float
                    or component != component
                    or component
                    in (
                        float("inf"),
                        float("-inf"),
                    )
                ):
                    raise ValueError(
                        "embedding result vector components must be finite floats"
                    )
