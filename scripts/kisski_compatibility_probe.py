"""KISSKI-COMPATIBILITY-1: operator-run compatibility probe for GWDG SAIA.

Proves only that LegoAI's qualified provider-neutral path interoperates with
one real OpenAI-compatible service. It is not an adapter, a ForgeAI
integration, routing, a benchmark or a model-quality evaluation.

At most two governed external calls, each made exactly once:
  1. `POST {api_root}/models` (PROVIDER-MODEL-DISCOVERY-1; empty body).
  2. `POST {api_root}/chat/completions` through the public governed host
     (OPENAI-COMPATIBLE-REMOTE-1), carrying SYNTHETIC content only.
If call 1 does not list models, call 2 never happens. Nothing is retried and
nothing falls back.

The API key enters only through S1 hidden interactive input, twice, because
S1 binds each revision to exactly one Secret purpose. It is never read from
arguments, environment, files or pipes, and is never printed. GWDG facts live
only in this script; Core has no provider special case.

Usage:
    uv run python .\\scripts\\kisski_compatibility_probe.py --plan   # no network
    uv run python .\\scripts\\kisski_compatibility_probe.py          # LIVE (gated)
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sqlite3
import sys
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any
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
from legoai.kernel.errors import ErrorCategory, Recoverability
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

PROMPT = "Return exactly the word READY."
PROBE_CONSUMER = "legoai-compat-probe"
BINDING = "kisski-probe"
DISCOVERY_IDENTITY = "gwdg-saia-discovery"
CHAT_IDENTITY = "gwdg-saia-chat"
REPLY_BOUND = 64
SAIA_DOCS = "https://docs.hpc.gwdg.de/services/ai-services/saia/index.html"
KISSKI_LLM = "https://kisski.gwdg.de/en/leistungen/2-02-llm-service/"
VERIFIED_ON = date(2026, 10, 9)


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
        return ProbeConfig(
            "gwdg-saia", "https://chat-ai.academiccloud.de", "/v1", None, custody
        )

    @property
    def base_url(self) -> str:
        return self.origin + self.api_root


class Classification(Enum):
    """The one final classification of a probe run.

    Only categories the typed results can prove. They do not separate a TLS
    failure from a connection failure (both NOT_SENT), chunked framing from
    truncation or timeout (all UNKNOWN), or a model-identity mismatch from
    another chat-contract rejection; those report as RESULT_INCONCLUSIVE or
    CHAT_CONTRACT_INCOMPATIBLE with the observed state and effect.
    """

    PASS = "KISSKI COMPATIBILITY PASS"
    AUTHENTICATION_FAILURE = "KISSKI AUTHENTICATION FAILURE"
    AUTHORIZATION_FAILURE = "KISSKI AUTHORIZATION FAILURE"
    MODEL_DISCOVERY_CONTRACT_INCOMPATIBLE = (
        "KISSKI MODEL-DISCOVERY CONTRACT INCOMPATIBLE"
    )
    CHAT_CONTRACT_INCOMPATIBLE = "KISSKI CHAT-CONTRACT INCOMPATIBLE"
    PROVIDER_AVAILABILITY_FAILURE = "KISSKI PROVIDER AVAILABILITY FAILURE"
    LOCAL_PREFLIGHT_FAILURE = "KISSKI LOCAL-PREFLIGHT FAILURE"
    RESULT_INCONCLUSIVE = "KISSKI RESULT INCONCLUSIVE"


def plan_lines(config: ProbeConfig, *, live: bool) -> list[str]:
    """The run header: PLAN (nothing happens) or LIVE RUN (calls may occur)."""
    if live:
        header = [
            "KISSKI-COMPATIBILITY-1 LIVE RUN",
            "up to 2 governed external calls may occur:",
            f"  1. POST {config.api_root}/models",
            f"  2. POST {config.api_root}/chat/completions only after discovery "
            "+ valid operator selection",
        ]
    else:
        header = [
            "KISSKI-COMPATIBILITY-1 PLAN",
            "no credential prompt",
            "no DNS",
            "no network",
        ]
    return header + [
        f"provider: {config.provider_id}",
        f"API root: {config.base_url}",
        "TLS: system trust store; certificate and hostname verified",
        "credential prompts: 2 hidden inputs of the same API key",
        f"  1. purpose {discovery_purpose()} (model discovery)",
        f"  2. purpose {credential_purpose()} (REMOTE chat)",
        "governed external operations (maximum 2, each at most once, no retry):",
        f"  1. POST {config.api_root}/models (empty body)",
        "  then: the operator selects one listed model id by number",
        f"  2. POST {config.api_root}/chat/completions (only if 1 listed models)",
        "disclosure classes: SYNTHETIC only",
        f"synthetic content: {PROMPT!r} (one user message)",
    ]


def declaration(config: ProbeConfig) -> ProcessorDeclaration:
    """Only facts the verified documentation states for the API service.

    Training: provider-declared on the KISSKI LLM service page. Retention: the
    no-storage statements concern the Chat AI service and web conversations;
    the SAIA API documentation states nothing on API request logging or
    retention, so it is UNKNOWN. Location, human access and subprocessors are
    not established: UNKNOWN. SYNTHETIC needs none of them (ADR-024 §11).
    """
    saia = SourceReference(f"GWDG SAIA API documentation {SAIA_DOCS}", VERIFIED_ON)
    kisski = SourceReference(f"KISSKI LLM service page {KISSKI_LLM}", VERIFIED_ON)
    return ProcessorDeclaration(
        "gwdg-saia",
        "r1",
        config.provider_id,
        config.origin,
        config.api_root,
        ProcessorIdentityFact("GWDG (with KISSKI)", FactBasis.PROVIDER_DECLARED, saia),
        LocationFact(None, FactBasis.UNKNOWN),
        RetentionFact(RetentionKind.UNKNOWN, None, FactBasis.UNKNOWN),
        TrainingFact(TrainingUse.NO, FactBasis.PROVIDER_DECLARED, kisski),
        HumanAccessFact(HumanAccess.UNKNOWN, FactBasis.UNKNOWN),
        SubprocessorsFact(SubprocessorsKind.UNKNOWN, frozenset(), FactBasis.UNKNOWN),
    )


def chat_admission(
    config: ProbeConfig, model: ModelId, now: datetime
) -> DisclosureAdmission:
    """SYNTHETIC only, exactly one model, the probe binding and consumer."""
    return DisclosureAdmission(
        "kisski-compat-1",
        "a1",
        frozenset({BINDING}),
        config.provider_id,
        config.origin,
        config.api_root,
        frozenset({model.value}),
        PROBE_CONSUMER,
        frozenset({ModelPurpose.CHAT.value}),
        "gwdg-saia",
        "r1",
        frozenset({DisclosureClass.SYNTHETIC}),
        (),
        frozenset(),
        now - timedelta(minutes=1),
        now + timedelta(minutes=30),
    )


def discovery_admission(
    config: ProbeConfig, credential: SecretRef, now: datetime
) -> ProviderDiscoveryAdmission:
    return ProviderDiscoveryAdmission(
        "kisski-discovery-1",
        "d1",
        config.provider_id,
        config.origin,
        config.api_root,
        ProviderOperation.MODEL_DISCOVERY,
        discovery_consumer(),
        credential.exact,
        now - timedelta(minutes=1),
        now + timedelta(minutes=15),
    )


def _scope() -> ReferenceScope:
    return ReferenceScope("operator", TenantId("kisski-compat"))


def _principal() -> PrincipalRef:
    return PrincipalRef("operator", PrincipalId("compat-operator"))


def _policy() -> PolicyRef:
    return PolicyRef("operator", "compat-probe", Version(1, 0, 0))


def _revision() -> ConfigurationRevisionRef:
    return ConfigurationRevisionRef(
        ConfigurationRef(
            ApplicationRef(_scope(), ApplicationId("kisski-compatibility-probe")),
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
            discovery_admission(config, credential, now),
            DiscoveryEndpoint(
                config.provider_id, config.origin, config.api_root, credential
            ),
            consumer=discovery_consumer(),
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


def classify_discovery(result: ModelDiscovery) -> Classification | None:
    """None means listed models: the probe may continue."""
    outcome = result.outcome
    if outcome is DiscoveryOutcome.LISTED:
        return None if result.models else Classification.RESULT_INCONCLUSIVE
    if outcome is DiscoveryOutcome.REFUSED:
        return Classification.LOCAL_PREFLIGHT_FAILURE
    if outcome is DiscoveryOutcome.MALFORMED:
        return Classification.MODEL_DISCOVERY_CONTRACT_INCOMPATIBLE
    if outcome is DiscoveryOutcome.PROVIDER_REJECTED:
        # The exact status proves only the provider's answer, not its cause:
        # 401 rejects authentication (a mistyped, expired or inactive key is
        # not distinguished); 403 refuses access (not proof the endpoint or
        # method is invalid).
        status = result.status
        if status == 401:
            return Classification.AUTHENTICATION_FAILURE
        if status == 403:
            return Classification.AUTHORIZATION_FAILURE
        if status in (404, 405):
            return Classification.MODEL_DISCOVERY_CONTRACT_INCOMPATIBLE
        if status == 429 or (status is not None and status >= 500):
            return Classification.PROVIDER_AVAILABILITY_FAILURE
        return Classification.RESULT_INCONCLUSIVE
    # NOT_SENT (connection or TLS not established; the typed result does not
    # say which) and UNKNOWN (sent; no complete response: chunked framing,
    # truncation or timeout are not distinguished) stay inconclusive.
    return Classification.RESULT_INCONCLUSIVE


def select_model(
    models: tuple[ModelId, ...], ask: Callable[[str], str], write: Callable[[str], None]
) -> ModelId | None:
    """The operator picks one listed id by number; nothing is chosen for them."""
    write("Listed model ids (as advertised now; no availability guarantee):")
    for number, model in enumerate(models, start=1):
        write(f"  {number}. {model.value}")
    answer = ask(f"Select exactly one model by number (1-{len(models)}): ").strip()
    if not answer.isdecimal() or not 1 <= int(answer) <= len(models):
        return None
    return models[int(answer) - 1]


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


def classify_chat(result: Any, attempt: tuple[str, set[str]] | None) -> Classification:
    execution = result.execution
    if execution.final_state is ExecutionState.SUCCEEDED:
        return Classification.PASS
    error = execution.error
    if error is not None and error.category is ErrorCategory.POLICY_VIOLATION:
        return Classification.LOCAL_PREFLIGHT_FAILURE
    if attempt is None:
        return Classification.LOCAL_PREFLIGHT_FAILURE
    state, observations = attempt
    if state == "not_sent":
        if observations == {"refused_at_gate"}:
            return Classification.LOCAL_PREFLIGHT_FAILURE
        return Classification.RESULT_INCONCLUSIVE  # TLS or connection; not split
    if state == "unknown":
        return Classification.RESULT_INCONCLUSIVE  # effect UNKNOWN, reported
    if state == "provider_rejected":
        retryable = (
            error is not None
            and error.recoverability is Recoverability.POTENTIALLY_RETRYABLE
        )
        # 429/503 are retryable rejections; other complete non-2xx (including
        # 401/403) are terminal and the Model path does not retain the status.
        return (
            Classification.PROVIDER_AVAILABILITY_FAILURE
            if retryable
            else Classification.RESULT_INCONCLUSIVE
        )
    # COMPLETED transport rejected by the shared parser: model identity,
    # finish reason or shape (the Model path does not say which).
    return Classification.CHAT_CONTRACT_INCOMPATIBLE


def run_probe(
    config: ProbeConfig,
    *,
    write: Callable[[str], None],
    ask: Callable[[str], str],
    read: Callable[[str], str] | None = None,
    interactive: Callable[[], bool] | None = None,
    clock: Callable[[], datetime] = lambda: datetime.now(UTC),
) -> Classification:
    """One probe run: at most one `/models` call, then at most one chat call."""
    for line in plan_lines(config, live=True):
        write(line)
    write(
        "You will be asked for the same API key twice (hidden input). LegoAI "
        "binds each credential revision to exactly one purpose; nothing is "
        "copied between them. Never paste the key anywhere else."
    )
    hidden: dict[str, Any] = {}
    if read is not None:
        hidden["read"] = read
    if interactive is not None:
        hidden["interactive"] = interactive
    source = open_credential_source(_scope())
    try:
        discovery_ref = _provision_interactively(
            source._source,  # type: ignore[attr-defined]
            DISCOVERY_IDENTITY,
            discovery_purpose(),
            discovery_consumer(),
            **hidden,
        )
        chat_ref = _provision_interactively(
            source._source,  # type: ignore[attr-defined]
            CHAT_IDENTITY,
            credential_purpose(),
            credential_consumer(),
            **hidden,
        )
    except PermissionError, TypeError, ValueError:
        write("credential provisioning refused (hidden interactive input required)")
        return _final(write, Classification.LOCAL_PREFLIGHT_FAILURE)
    try:
        now = clock()
        discovered = _discover(
            config,
            source._source,  # type: ignore[attr-defined]
            discovery_ref,
            now,
            clock,
        )
        write(f"discovery attempt: {_id(discovered.attempt_id)}")
        write(f"discovery disposition: {discovered.outcome.value}")
        if discovered.status is not None:
            # Exact status of a complete response: safe typed metadata only.
            write(f"discovery HTTP status: {discovered.status}")
        verdict = classify_discovery(discovered)
        if verdict is not None:
            write("no chat call is made")
            return _final(write, verdict)
        write(f"discovered model count: {len(discovered.models)}")
        selected = select_model(discovered.models, ask, write)
        if selected is None:
            write("invalid selection; no chat call is made")
            return _final(write, Classification.LOCAL_PREFLIGHT_FAILURE)
        write(f"selected model id: {selected.value}")
        return _chat(config, source, chat_ref, selected, clock, write)
    finally:
        source.close()


def _chat(
    config: ProbeConfig,
    source: Any,
    credential: SecretRef,
    model: ModelId,
    clock: Callable[[], datetime],
    write: Callable[[str], None],
) -> Classification:
    """Call 2 through the public governed host REMOTE path, SYNTHETIC only."""
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
    admission = chat_admission(config, model, now)
    processor = declaration(config)
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
        return _final(write, Classification.LOCAL_PREFLIGHT_FAILURE)
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
    if result.response is not None:
        reply = result.response.content[:REPLY_BOUND]
        write(f"synthetic reply (bounded): {reply!r}")
        write(
            "synthetic instruction followed: "
            + ("yes" if result.response.content.strip() == "READY" else "no")
        )
        write(f"response model id: {result.response.model_identity.value}")
    return _final(write, verdict)


def _id(value: Any) -> str:
    return "none" if value is None else str(value.value)


def _final(write: Callable[[str], None], verdict: Classification) -> Classification:
    write(f"FINAL CLASSIFICATION: {verdict.value}")
    return verdict


def main(options: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="KISSKI-COMPATIBILITY-1 probe")
    parser.add_argument(
        "--plan", action="store_true", help="print the plan; no prompt, DNS or network"
    )
    arguments = parser.parse_args(options)
    if arguments.plan:
        for line in plan_lines(ProbeConfig.live(Path("<not created>")), live=False):
            print(line)
        return 0
    if not (sys.stdin.isatty() and sys.stdout.isatty()):
        print("FINAL CLASSIFICATION: " + Classification.LOCAL_PREFLIGHT_FAILURE.value)
        print("an interactive terminal is required for hidden credential input")
        return 2
    custody = Path(tempfile.mkdtemp(prefix="kisski-compat-"))
    print(f"local custody directory: {custody}")
    verdict = run_probe(ProbeConfig.live(custody), write=print, ask=input)
    return 0 if verdict is Classification.PASS else 1


if __name__ == "__main__":
    raise SystemExit(main())
