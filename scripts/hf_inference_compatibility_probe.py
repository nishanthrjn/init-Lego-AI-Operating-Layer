"""HF synthetic compatibility orchestration; separately authorized live probe ready.

Uses only governed discovery and REMOTE chat. No repository content, ambient
credentials, retry or fallback. --plan performs no credential/DNS/network I/O.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sqlite3
import sys
import tempfile
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, NoReturn
from uuid import uuid4

from legoai.capabilities.values import CapabilityId, CapabilityOffer
from legoai.evidence.custody import CustodyAccess
from legoai.execution.values import ExecutionState
from legoai.governance.disclosure import (
    DisclosureAdmission,
    DisclosureClass,
    DisclosureDeclaration,
    FactBasis,
    HumanAccess,
    HumanAccessFact,
    LocationFact,
    ProcessorDeclaration,
    ProcessorIdentityFact,
    RetentionFact,
    RetentionKind,
    SourceReference,
    SubprocessorsFact,
    SubprocessorsKind,
    TrainingFact,
    TrainingUse,
)
from legoai.governance.provider_control import (
    ProviderDiscoveryAdmission,
    ProviderDiscoveryMethod,
    ProviderOperation,
)
from legoai.governance.secret import SecretRef
from legoai.governance.values import Grant, GrantId, PolicyRef, Principal
from legoai.intelligence.model.routing import ModelRequirement
from legoai.intelligence.model.values import (
    ChatMessage,
    ChatRequest,
    ChatRole,
    ModelId,
    ProviderId,
)
from legoai.kernel.context import TenantContext
from legoai.kernel.identity import ApplicationId, PrincipalId, TenantId
from legoai.kernel.references import (
    ApplicationRef,
    ConfigurationRef,
    ConfigurationRevisionRef,
    PrincipalRef,
    ReferenceScope,
)
from legoai.kernel.versions import Version
from legoai.plugins.ports import PluginAdmissionId
from legoai.plugins.values import PluginDeclaration
from legoai.reference._credential_https import tls_context
from legoai.reference._durable_evidence import _EvidenceStore
from legoai.reference._remote_attempts import _RemoteAttemptStore
from legoai.reference._secret_ledger import _SecretLedger
from legoai.reference.catalog import InMemoryCatalog
from legoai.reference.governance import (
    InMemoryApprovalRegistry,
    InMemoryGrantRegistry,
    InMemoryPolicyRegistry,
)
from legoai.reference.model_openai_compatible import (
    DiscoveredModel,
    DiscoveredProvider,
    openai_compatible_plugin_id,
    openai_compatible_release,
)
from legoai.reference.plugins import activate, admit, initialize, inspect, validate
from legoai.reference.secret import _SecretClock
from legoai.runtime._composition.provider_discovery import (
    DiscoveryEndpoint,
    DiscoveryOutcome,
    ModelDiscovery,
    discover_remote_models,
    discovery_consumer,
    discovery_purpose,
)
from legoai.runtime._composition.remote_model import (
    credential_consumer,
    credential_purpose,
)
from legoai.runtime._composition.secret import _provision_interactively, _SecretUses
from legoai.runtime.api import (
    ExecutionDisclosure,
    HostError,
    LocalHostConfig,
    ModelBindingConfig,
    ModelDeployment,
    ModelPurpose,
    OpenAICompatibleSettings,
    OperatorGrant,
    RemoteDisclosureConfig,
    RemoteModelRuntime,
)
from legoai.runtime.local import open_credential_source, open_local_host

ORIGIN = "https://router.huggingface.co"
API_ROOT = "/v1"
PROVIDER = "huggingface-inference-router"
CONSUMER = "hf-inference-compatibility-probe"
PROBE_CONSUMER = CONSUMER
BINDING = "hf-synthetic-probe"
DISCOVERY_PURPOSE = "provider-model-discovery"
CHAT_PURPOSE = "remote-model-bearer"
PROMPT = "Return exactly the word READY."
LIVE_READY = True  # Maintainer qualification/readiness closeout: 2026-10-10.
DOCS = "https://huggingface.co/docs/inference-providers/"
RETRIEVED = date(2026, 10, 10)
CODING_MODELS = (
    "Qwen/Qwen2.5-Coder-32B-Instruct",
    "Qwen/Qwen3-Coder-480B-A35B-Instruct",
)
# Service identities from official provider pages; unknown IDs are ineligible.
BACKENDS = (
    ("fireworks-ai", "Fireworks AI", "fireworks-ai"),
    ("novita", "Novita", "novita"),
    ("together", "Together AI", "together"),
    ("nscale", "Nscale", "nscale"),
)


@dataclass(frozen=True)
class ProbeConfig:
    """Fixed live provider facts; tests replace origin and trust anchor only."""

    provider_id: str
    origin: str
    api_root: str
    trust_anchor: Path | None
    custody: Path
    timeout_seconds: float = 60.0
    max_output_tokens: int = 16
    margin: timedelta = timedelta(minutes=5)

    @staticmethod
    def live(custody: Path) -> ProbeConfig:
        # System trust store only: no custom anchor for the real provider.
        return ProbeConfig(PROVIDER, ORIGIN, API_ROOT, None, custody)

    @property
    def base_url(self) -> str:
        return self.origin + self.api_root


class Classification(Enum):
    """Requested closed vocabulary; no unsupported live diagnoses are emitted."""

    HF_COMPATIBILITY_PASS = "HF_COMPATIBILITY_PASS"
    AUTHENTICATION_FAILURE = "AUTHENTICATION_FAILURE"
    AUTHORIZATION_FAILURE = "AUTHORIZATION_FAILURE"
    MODEL_DISCOVERY_INCOMPATIBLE = "MODEL_DISCOVERY_INCOMPATIBLE"
    PROVIDER_IDENTITY_INDETERMINATE = "PROVIDER_IDENTITY_INDETERMINATE"
    RESPONSE_FRAMING_INCOMPATIBLE = "RESPONSE_FRAMING_INCOMPATIBLE"
    MODEL_IDENTITY_INCOMPATIBLE = "MODEL_IDENTITY_INCOMPATIBLE"
    CHAT_CONTRACT_INCOMPATIBLE = "CHAT_CONTRACT_INCOMPATIBLE"
    PROVIDER_AVAILABILITY_FAILURE = "PROVIDER_AVAILABILITY_FAILURE"
    CREDIT_OR_QUOTA_EXHAUSTED = "CREDIT_OR_QUOTA_EXHAUSTED"
    RESULT_INCONCLUSIVE = "RESULT_INCONCLUSIVE"


@dataclass(frozen=True, slots=True)
class Candidate:
    model: ModelId
    backend: DiscoveredProvider
    service: str
    source: str

    @property
    def request_model(self) -> str:
        return f"{self.model.value}:{self.backend.provider}"


class RejectionReason(Enum):
    MODEL_NOT_ALLOWED = "MODEL_NOT_ALLOWED"
    BACKEND_NOT_ALLOWED = "BACKEND_NOT_ALLOWED"
    BACKEND_STATUS_NOT_LIVE = "BACKEND_STATUS_NOT_LIVE"
    INPUT_MODALITY_MISSING = "INPUT_MODALITY_MISSING"
    OUTPUT_MODALITY_MISSING = "OUTPUT_MODALITY_MISSING"
    MODALITY_SHAPE_UNSUPPORTED = "MODALITY_SHAPE_UNSUPPORTED"
    INPUT_PRICE_MISSING = "INPUT_PRICE_MISSING"
    OUTPUT_PRICE_MISSING = "OUTPUT_PRICE_MISSING"
    INPUT_PRICE_ABOVE_LIMIT = "INPUT_PRICE_ABOVE_LIMIT"
    OUTPUT_PRICE_ABOVE_LIMIT = "OUTPUT_PRICE_ABOVE_LIMIT"


@dataclass(frozen=True, slots=True)
class CandidateEvaluation:
    model: ModelId = field(repr=False)
    provider: str = field(repr=False)
    eligible: bool
    reasons: tuple[RejectionReason, ...]


def evaluate_candidate(
    model: DiscoveredModel, provider: DiscoveredProvider
) -> CandidateEvaluation:
    """Pure policy evaluation of parser-normalized observations; no authority."""
    reasons: list[RejectionReason] = []
    if model.model.value not in CODING_MODELS:
        reasons.append(RejectionReason.MODEL_NOT_ALLOWED)
    if provider.provider not in {key for key, _, _ in BACKENDS}:
        reasons.append(RejectionReason.BACKEND_NOT_ALLOWED)
    if provider.status != "live":
        reasons.append(RejectionReason.BACKEND_STATUS_NOT_LIVE)
    if not model.input_modalities:
        reasons.append(RejectionReason.INPUT_MODALITY_MISSING)
    if not model.output_modalities:
        reasons.append(RejectionReason.OUTPUT_MODALITY_MISSING)
    if (model.input_modalities and model.input_modalities != ("text",)) or (
        model.output_modalities and model.output_modalities != ("text",)
    ):
        reasons.append(RejectionReason.MODALITY_SHAPE_UNSUPPORTED)
    if provider.input_price is None:
        reasons.append(RejectionReason.INPUT_PRICE_MISSING)
    if provider.output_price is None:
        reasons.append(RejectionReason.OUTPUT_PRICE_MISSING)
    if provider.input_price is not None and not 0 <= provider.input_price <= 5:
        reasons.append(RejectionReason.INPUT_PRICE_ABOVE_LIMIT)
    if provider.output_price is not None and not 0 <= provider.output_price <= 5:
        reasons.append(RejectionReason.OUTPUT_PRICE_ABOVE_LIMIT)
    return CandidateEvaluation(
        model.model, provider.provider, not reasons, tuple(reasons)
    )


def _overlap_text_safe(value: str, limit: int) -> bool:
    """Display guard only; never changes eligibility or establishes identity."""
    return (
        0 < len(value) <= limit
        and all(33 <= ord(char) <= 126 and char != "*" for char in value)
        and "://" not in value
        and not value.lower().startswith("hf_")
    )


def eligibility_lines(result: ModelDiscovery) -> tuple[str, ...]:
    """Bounded observations, not processor identity, admission or routing.

    Only allowlisted models may expose observed backend IDs. JSON escaping
    prevents delimiter ambiguity. URLs and HF-token-shaped text are refused.
    The input is normalized discovery values, never raw response or Secret data.
    """
    if result.outcome is not DiscoveryOutcome.LISTED or result.models != tuple(
        item.model for item in result.catalog
    ):
        return (
            "eligibility diagnostics unavailable: no consistent listed observation",
        )
    counts = dict.fromkeys(RejectionReason, 0)
    pairs = eligible = allowed_models = empty_models = 0
    samples: list[tuple[DiscoveredModel, DiscoveredProvider, CandidateEvaluation]] = []
    for model in result.catalog:
        allowed_models += model.model.value in CODING_MODELS
        empty_models += not model.providers
        for provider in model.providers:
            evaluation = evaluate_candidate(model, provider)
            pairs += 1
            eligible += evaluation.eligible
            for reason in evaluation.reasons:
                counts[reason] += 1
            if (
                RejectionReason.MODEL_NOT_ALLOWED not in evaluation.reasons
                and _overlap_text_safe(provider.provider, 128)
                and (provider.status is None or _overlap_text_safe(provider.status, 32))
                and all(
                    _overlap_text_safe(value, 32)
                    for value in model.input_modalities + model.output_modalities
                )
            ):
                samples.append((model, provider, evaluation))
    samples.sort(key=lambda item: (item[0].model.value, item[1].provider))
    lines = [
        f"discovered models: {len(result.catalog)}",
        f"allowlisted models observed: {allowed_models}",
        f"models without backend observations: {empty_models}",
        f"observed model/backend pairs: {pairs}",
        f"eligible pairs: {eligible}",
        "rejection summary (counts overlap; each reason counts pairs):",
        *(f"  {reason.value}: {counts[reason]}" for reason in RejectionReason),
    ]
    for model, provider, evaluation in samples[:4]:
        lines.append(
            "overlap observation (not authority): "
            + json.dumps(
                {
                    "model": model.model.value,
                    "backend": provider.provider,
                    "status": provider.status,
                    "input_modalities": model.input_modalities,
                    "output_modalities": model.output_modalities,
                    "input_price": provider.input_price,
                    "output_price": provider.output_price,
                    "reasons": [reason.value for reason in evaluation.reasons],
                },
                ensure_ascii=True,
                allow_nan=False,
                separators=(",", ":"),
            )
        )
    return tuple(lines)


def shortlist(result: ModelDiscovery) -> tuple[Candidate, ...]:
    """Closed coding allowlist, text-only, live, known identity and <=$5/M each.

    Ordered by the visible allowlist then backend ID, never price/size/speed.
    Missing price, modality, status or identity makes an entry ineligible.
    """
    if result.outcome is not DiscoveryOutcome.LISTED:
        return ()
    if result.models != tuple(item.model for item in result.catalog):
        return ()
    choices: list[Candidate] = []
    for allowed in CODING_MODELS:
        for item in result.catalog:
            if item.model.value != allowed:
                continue
            for backend_id, service, page in BACKENDS:
                for backend in item.providers:
                    if backend.provider != backend_id:
                        continue
                    if not evaluate_candidate(item, backend).eligible:
                        continue
                    choices.append(
                        Candidate(
                            item.model, backend, service, DOCS + "providers/" + page
                        )
                    )
    return tuple(choices[:3])


def select_pair(
    result: ModelDiscovery, ask: Callable[[str], str], write: Callable[[str], None]
) -> Candidate | None:
    choices = shortlist(result)
    if not choices:
        return None
    for number, candidate in enumerate(choices, 1):
        write(
            f"{number}. {candidate.request_model}; text/chat; advertised live; "
            f"USD/M input={candidate.backend.input_price} "
            f"output={candidate.backend.output_price}"
        )
    answer = ask("Select one numbered pair (blank declines): ").strip()
    if answer not in {str(n) for n in range(1, len(choices) + 1)}:
        return None
    return choices[int(answer) - 1]


def declaration(config: ProbeConfig, selected: Candidate) -> ProcessorDeclaration:
    identity = SourceReference(
        f"HF router {DOCS}index; backend {selected.source}", RETRIEVED
    )
    return ProcessorDeclaration(
        "hf-probe-processor",
        "r1",
        config.provider_id,
        config.origin,
        config.api_root,
        ProcessorIdentityFact(
            f"Hugging Face router; inference processor {selected.service}",
            FactBasis.PROVIDER_DECLARED,
            identity,
        ),
        LocationFact(None, FactBasis.UNKNOWN),
        RetentionFact(RetentionKind.UNKNOWN, None, FactBasis.UNKNOWN),
        TrainingFact(TrainingUse.UNKNOWN, FactBasis.UNKNOWN),
        HumanAccessFact(HumanAccess.UNKNOWN, FactBasis.UNKNOWN),
        SubprocessorsFact(SubprocessorsKind.UNKNOWN, frozenset(), FactBasis.UNKNOWN),
    )


def chat_admission(
    config: ProbeConfig, selected: Candidate, now: datetime
) -> DisclosureAdmission:
    return DisclosureAdmission(
        "hf-synthetic-chat",
        "a1",
        frozenset({BINDING}),
        config.provider_id,
        config.origin,
        config.api_root,
        frozenset({selected.request_model}),
        CONSUMER,
        frozenset({ModelPurpose.CHAT.value}),
        "hf-probe-processor",
        "r1",
        frozenset({DisclosureClass.SYNTHETIC}),
        (),
        frozenset(),
        now,
        now + timedelta(minutes=15),
    )


def classify_discovery(result: ModelDiscovery) -> Classification | None:
    if result.outcome is DiscoveryOutcome.LISTED:
        return None
    if result.outcome is DiscoveryOutcome.MALFORMED:
        return Classification.MODEL_DISCOVERY_INCOMPATIBLE
    if result.outcome is DiscoveryOutcome.PROVIDER_REJECTED:
        if result.status == 401:
            return Classification.AUTHENTICATION_FAILURE
        if result.status == 403:
            return Classification.AUTHORIZATION_FAILURE
        if result.status in (404, 405):
            return Classification.MODEL_DISCOVERY_INCOMPATIBLE
        if result.status is not None and 500 <= result.status <= 599:
            return Classification.PROVIDER_AVAILABILITY_FAILURE
    return Classification.RESULT_INCONCLUSIVE


def classify_chat(result: Any, attempt: tuple[str, set[str]] | None) -> Classification:
    if result.execution.final_state is ExecutionState.SUCCEEDED:
        if result.response is not None and result.response.content == "READY":
            return Classification.HF_COMPATIBILITY_PASS
        return Classification.RESULT_INCONCLUSIVE
    if attempt is not None and attempt[0] == "completed":
        return Classification.CHAT_CONTRACT_INCOMPATIBLE
    return Classification.RESULT_INCONCLUSIVE


def discovery_admission(
    credential: SecretRef, now: datetime, config: ProbeConfig | None = None
) -> ProviderDiscoveryAdmission:
    """Prepare exact authority from a future S1 revision; perform no I/O.

    The future operator confirmation must precede calling this factory.
    """
    if type(credential) is not SecretRef:
        raise TypeError("exact Secret reference required")
    if credential.use_requirement != DISCOVERY_PURPOSE:
        raise ValueError("discovery requires its separate Secret purpose")
    return ProviderDiscoveryAdmission(
        "hf-inference-discovery-1",
        "d1",
        PROVIDER,
        ORIGIN if config is None else config.origin,
        API_ROOT,
        ProviderOperation.MODEL_DISCOVERY,
        CONSUMER,
        credential.exact,
        now,
        now + timedelta(minutes=15),
        ProviderDiscoveryMethod.GET,
    )


def _scope() -> ReferenceScope:
    return ReferenceScope("operator", TenantId("hf-compat"))


def _principal() -> PrincipalRef:
    return PrincipalRef("operator", PrincipalId("compat-operator"))


def _policy() -> PolicyRef:
    return PolicyRef("operator", "compat-probe", Version(1, 0, 0))


def _revision() -> ConfigurationRevisionRef:
    return ConfigurationRevisionRef(
        ConfigurationRef(
            ApplicationRef(_scope(), ApplicationId("hf-compatibility-probe")),
            "probe",
        ),
        "r1",
        Version(1, 0, 0),
    )


def _discover(
    config: ProbeConfig,
    source: Any,
    credential: SecretRef,
    now: datetime,
    clock: Callable[[], datetime],
) -> ModelDiscovery:
    """Call 1 through the qualified seam; custody is closed afterwards so the
    host can open the same attempt store as its single writer."""
    domain = source._domain
    tenant = TenantContext(_scope().tenant_id)
    principal = Principal(_principal())
    grants = InMemoryGrantRegistry(_domain=domain)
    catalog = InMemoryCatalog(_domain=domain)
    offer = CapabilityOffer(CapabilityId(discovery_consumer()), Version(1, 0, 0))
    plugin = PluginDeclaration(
        openai_compatible_plugin_id(), openai_compatible_release(), (offer,)
    )
    record = admit(
        validate(inspect(plugin), plugin, evaluated_at=now),
        tenant,
        PluginAdmissionId(f"discovery-consumer-{uuid4().hex}"),
        established_at=now,
    )
    entry = catalog.publish(
        activate(initialize(record, established_at=now), established_at=now),
        plugin,
        offer,
        established_at=now,
    )
    uses_directory = config.custody / "discovery-secret-uses"
    uses_directory.mkdir()
    _SecretLedger.provision(uses_directory / "source.db")
    _EvidenceStore.provision(uses_directory / "evidence.db")
    access = CustodyAccess(_scope(), principal)
    attempts_path = config.custody / "remote-attempts.db"
    _RemoteAttemptStore.provision(attempts_path)
    ledger = _SecretLedger(uses_directory / "source.db", access, domain)
    evidence = _EvidenceStore(uses_directory / "evidence.db", access, domain)
    attempts = _RemoteAttemptStore(attempts_path, domain, clock)
    try:
        uses = _SecretUses(
            entry,
            domain,
            grants,
            InMemoryPolicyRegistry(_domain=domain),
            InMemoryApprovalRegistry(_domain=domain),
            catalog,
            ledger,
            evidence,
            _SecretClock(domain, host=clock),
            source,
        )
        grant = Grant(
            GrantId("grant-discovery"),
            principal,
            principal,
            tenant,
            "secret-use",
            credential.exact.identity,
            False,
            now - timedelta(minutes=1),
            now + timedelta(minutes=15),
        )
        return discover_remote_models(
            discovery_admission(credential, now, config),
            DiscoveryEndpoint(
                config.provider_id,
                config.origin,
                config.api_root,
                credential,
                ProviderDiscoveryMethod.GET,
                True,
            ),
            consumer=CONSUMER,
            attempts=attempts,
            uses=uses,
            configuration=_revision(),
            principal=principal,
            grant=grant,
            policy=_policy(),
            tls=tls_context(config.trust_anchor),
            timeout=config.timeout_seconds,
            margin=config.margin,
            clock=clock,
        )
    finally:
        attempts.close()
        evidence.close()
        ledger.close()


def _attempt_for(custody: Path, execution: str) -> tuple[str, set[str]] | None:
    path = custody / "remote-attempts.db"
    conn = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
    try:
        row = conn.execute(
            "SELECT state,observations FROM attempts WHERE execution_id=?",
            (execution,),
        ).fetchone()
    finally:
        conn.close()
    if row is None:
        return None
    return row[0], set(json.loads(row[1]))


def _chat(
    config: ProbeConfig,
    source: Any,
    credential: SecretRef,
    selected: Candidate,
    clock: Callable[[], datetime],
    write: Callable[[str], None],
) -> Classification:
    """Call 2 through the public governed host REMOTE path, SYNTHETIC only."""
    model = ModelId(selected.request_model)
    now = clock()
    window = (now - timedelta(minutes=1), now + timedelta(minutes=30))
    settings = OpenAICompatibleSettings(
        config.base_url,
        model.value,
        None,
        config.timeout_seconds,
        config.max_output_tokens,
        ProviderId(config.provider_id),
        ModelDeployment.REMOTE,
        bearer_credential=credential,
    )
    admission = chat_admission(config, selected, now)
    processor = declaration(config, selected)
    host_config = LocalHostConfig(
        _revision(),
        _principal(),
        _policy(),
        (
            OperatorGrant(
                GrantId("grant-chat"),
                "invoke-capability",
                ModelPurpose.CHAT.capability_id.value,
                *window,
            ),
            OperatorGrant(
                GrantId("grant-chat-secret"),
                "secret-use",
                credential.exact.identity,
                *window,
            ),
        ),
        (ModelBindingConfig(BINDING, ModelRequirement("compat-probe"), settings),),
        1,
        disclosure=RemoteDisclosureConfig((processor,), (admission,)),
    )
    write(f"disclosure admission: {admission.admission_id}@{admission.revision}")
    write(f"processor declaration: {processor.declaration_id}@{processor.revision}")
    write("disclosure classes: SYNTHETIC")
    try:
        host = open_local_host(
            host_config,
            {"revision": "r1", "binding": BINDING},
            clock=clock,
            remote=RemoteModelRuntime(
                source, config.custody, config.margin, config.trust_anchor
            ),
        )
    except HostError as error:
        write(f"host open refused: {error.failure.value}")
        return _final(write, Classification.RESULT_INCONCLUSIVE)
    synthetic = ExecutionDisclosure(
        PROBE_CONSUMER,
        DisclosureDeclaration(frozenset({DisclosureClass.SYNTHETIC})),
    )

    async def chat() -> Any:
        context = host.model_execution(ModelPurpose.CHAT, disclosure=synthetic)
        return await host.governed_chat(
            context, ChatRequest((ChatMessage(ChatRole.USER, PROMPT),))
        )

    result = asyncio.run(chat())
    execution = result.execution
    attempt = _attempt_for(config.custody, execution.execution_id.value)
    write(f"chat execution: {execution.execution_id.value}")
    write(f"chat attempt state: {attempt[0] if attempt else 'none'}")
    write(f"chat effect: {execution.effect.value}")
    if execution.error is not None:
        write(
            f"chat error: {execution.error.category.value} / "
            f"{execution.error.recoverability.value}"
        )
    verdict = classify_chat(result, attempt)
    if verdict is Classification.HF_COMPATIBILITY_PASS:
        write("synthetic reply: READY")
    return _final(write, verdict)


def _final(write: Callable[[str], None], verdict: Classification) -> Classification:
    write(f"FINAL CLASSIFICATION: {verdict.value}")
    return verdict


def run_probe(
    config: ProbeConfig,
    *,
    write: Callable[[str], None],
    ask: Callable[[str], str],
    read: Callable[[str], str] | None = None,
    interactive: Callable[[], bool] | None = None,
    clock: Callable[[], datetime] = lambda: datetime.now(UTC),
) -> Classification:
    """One discovery then one selected SYNTHETIC chat; no retry/fallback.

    Only an explicit loopback TLS fixture is runnable before qualification.
    There is no CLI switch that bypasses the live readiness gate.
    """
    synthetic = (
        config.trust_anchor is not None
        and re.fullmatch(r"https://localhost:[0-9]{1,5}", config.origin) is not None
    )
    if (
        config.provider_id != PROVIDER
        or config.api_root != API_ROOT
        or (
            not synthetic
            and (
                not LIVE_READY
                or config.origin != ORIGIN
                or config.trust_anchor is not None
            )
        )
    ):
        write("live execution refused: local qualification required")
        return _final(write, Classification.RESULT_INCONCLUSIVE)
    hidden: dict[str, Any] = {}
    if read is not None:
        hidden["read"] = read
    if interactive is not None:
        hidden["interactive"] = interactive
    source = open_credential_source(_scope())
    try:
        discovery_ref = _provision_interactively(
            source._source,  # type: ignore[attr-defined]
            "hf-discovery",
            discovery_purpose(),
            discovery_consumer(),
            **hidden,
        )
        discovered = _discover(
            config,
            source._source,  # type: ignore[attr-defined]
            discovery_ref,
            clock(),
            clock,
        )
        write(f"router: {PROVIDER}; API root: {config.base_url}")
        write(
            f"discovery attempt: {discovered.attempt_id.value if discovered.attempt_id else 'none'}"
        )
        write(f"discovery outcome: {discovered.outcome.value}")
        write(
            f"discovery state: {discovered.state.value if discovered.state else 'none'}"
        )
        if discovered.status is not None:
            write(f"discovery HTTP status: {discovered.status}")
        verdict = classify_discovery(discovered)
        if verdict is not None:
            return _final(write, verdict)
        for line in eligibility_lines(discovered):
            write(line)
        selected = select_pair(discovered, ask, write)
        if selected is None:
            return _final(write, Classification.PROVIDER_IDENTITY_INDETERMINATE)
        write(f"frozen model: {selected.request_model}; backend: {selected.service}")
        if (
            ask("Approve one SYNTHETIC chat with this pair? [y/N] ").strip().lower()
            != "y"
        ):
            return _final(write, Classification.RESULT_INCONCLUSIVE)
        chat_ref = _provision_interactively(
            source._source,  # type: ignore[attr-defined]
            "hf-chat",
            credential_purpose(),
            credential_consumer(),
            **hidden,
        )
        return _chat(config, source, chat_ref, selected, clock, write)
    except Exception:
        # Boundary containment: never print exception text or a provider body.
        # Durable attempts remain available for inspection; no diagnosis guessed.
        write("probe stopped; inspect local attempt custody; no retry")
        return _final(write, Classification.RESULT_INCONCLUSIVE)
    finally:
        source.close()


def plan_lines() -> tuple[str, ...]:
    return (
        "HF-INFERENCE-PROVIDERS-COMPATIBILITY-1 SYNTHETIC LIVE-PROBE READY"
        if LIVE_READY
        else "HF-INFERENCE-PROVIDERS-COMPATIBILITY-1 LIVE GATE DISABLED",
        f"API root: {ORIGIN}{API_ROOT}",
        f"discovery method: GET {ORIGIN}{API_ROOT}/models",
        f"possible chat: POST {ORIGIN}{API_ROOT}/chat/completions",
        "provider metadata required for backend pinning; max shortlist size: 3",
        "coding allowlist: " + ", ".join(CODING_MODELS),
        "backend allowlist: " + ", ".join(item[0] for item in BACKENDS),
        "policy: advertised live; text-only; known identity; input/output <= USD 5/M each",
        "one operator-selected exact model:provider; no arbitrary model or method input",
        "future maximum: 1 discovery + 1 chat; plan/default provider calls: 0",
        "credential prompts now: 0; future: 2 separate hidden interactive S1 provisions",
        "discovery purpose: provider-model-discovery; chat purpose: remote-model-bearer",
        "SYNTHETIC only: " + PROMPT,
        "no retry; no fallback; no repository disclosure",
        "coarse typed results preserved; insufficient evidence is RESULT_INCONCLUSIVE",
        "separate authorization required: "
        "AUTHORIZE HF-INFERENCE-PROVIDERS-COMPATIBILITY-1 LIVE PROBE",
    )


class _SafeParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        self.exit(2, "Invalid options. Use --plan; token arguments are forbidden.\n")


def main(options: list[str] | None = None) -> int:
    parser = _SafeParser(description=__doc__, allow_abbrev=False)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--plan", action="store_true")
    modes.add_argument("--live", action="store_true")
    args = parser.parse_args(options)
    if args.plan:
        for line in plan_lines():
            print(line)
        return 0
    if not args.live or not LIVE_READY:
        print("Live execution refused: local qualification and authorization required")
        return 2
    if not (sys.stdin.isatty() and sys.stdout.isatty()):
        print("Interactive terminal required")
        return 2
    custody = Path(tempfile.mkdtemp(prefix="hf-compat-"))
    print(f"local custody directory: {custody}")
    try:
        result = run_probe(ProbeConfig.live(custody), write=print, ask=input)
    except EOFError, KeyboardInterrupt:
        print("Stopped; inspect custody; result inconclusive")
        return 2
    return 0 if result is Classification.HF_COMPATIBILITY_PASS else 1


if __name__ == "__main__":
    raise SystemExit(main())
