"""Attended SAIA qualification; default/--plan is inert, --live is explicit.

Trusted operator tooling, like kisski_compatibility_probe: private discovery
bootstrap and safe status inspection stay here, never in ForgeAI/domain code.
No repository files are read and no generated proposal is applied or executed.
"""

import argparse
import asyncio
import json
import sys
import tempfile
from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, NoReturn, cast

from legoai.execution.values import ExecutionState
from legoai.governance.disclosure import DisclosureClass, DisclosureDeclaration
from legoai.governance.secret import SecretRef
from legoai.governance.values import GrantId
from legoai.intelligence.model.routing import ModelRequirement
from legoai.intelligence.model.values import (
    ChatMessage,
    ChatRequest,
    ChatRole,
    ModelId,
    ProviderId,
)
from legoai.runtime._composition.provider_discovery import (
    discovery_consumer,
    discovery_purpose,
)
from legoai.runtime._composition.secret import _provision_interactively
from legoai.runtime.api import (
    CredentialSource,
    ExecutionDisclosure,
    GovernedChatResult,
    GovernedHost,
    LocalHostConfig,
    ModelBindingConfig,
    ModelDeployment,
    ModelPurpose,
    OpenAICompatibleSettings,
    OperatorGrant,
    RemoteDisclosureConfig,
    RemoteModelRuntime,
)
from legoai.runtime.local import (
    _remote_chat_http_status,
    open_credential_source,
    open_local_host,
)
from scripts import kisski_compatibility_probe as legacy

PROFILE = "kisski-saia"
AUTHORIZATION = "AUTHORIZE FORGEAI-KISSKI-SAIA-PROVIDER-QUALIFICATION-1 LIVE SYNTHETIC"
TINY_PROMPT = "Return the exact token KISSKI_OK."
EXPECTED_JSON = (
    '{"summary":"Synthetic fixture","changes":[{"path":"synthetic.txt",'
    '"operation":"create","content":"KISSKI_OK\\n","reason":"Fixture"}],'
    '"risks":[],"unknowns":[]}'
)
STRUCTURED_PROMPT = (
    "Return only this exact JSON object, without markdown or extra fields. "
    "It is a synthetic proposal fixture; do not execute or apply it. " + EXPECTED_JSON
)


class Outcome(Enum):
    PASS = "KISSKI-SAIA LIVE CONNECTIVITY QUALIFIED; STRUCTURED SYNTHETIC SMOKE PASSED"
    CONNECTIVITY_ONLY = (
        "KISSKI-SAIA LIVE CONNECTIVITY QUALIFIED; STRUCTURED SMOKE NOT RUN"
    )
    DECLINED = "DECLINED; LATER STAGES NOT RUN"
    DISCOVERY_FAILED = "DISCOVERY_FAILED; CHAT NOT RUN"
    REFUSED = "LOCAL_PREFLIGHT_REFUSED"
    INCONCLUSIVE = "RESULT_INCONCLUSIVE; INSPECT ATTEMPT CUSTODY; DO NOT REPLAY"
    PROVIDER_REJECTED = "PROVIDER_REJECTED; NO RETRY"
    CONTRACT_REJECTED = "CHAT_CONTRACT_REJECTED; NO RETRY"
    CONTENT_REJECTED = "SYNTHETIC_RESPONSE_MISMATCH; LATER STAGES NOT RUN"
    STRUCTURED_REJECTED = "LIVE CONNECTIVITY OBSERVED; STRUCTURED SMOKE FAILED"


def live_config(custody: Path) -> legacy.ProbeConfig:
    return replace(
        legacy.ProbeConfig.live(custody), provider_id=PROFILE, max_output_tokens=512
    )


def plan_lines(*, live: bool = False) -> tuple[str, ...]:
    state = (
        "LIVE REQUESTED; authorization pending"
        if live
        else "PLAN; no credential prompt or I/O"
    )
    return (
        "FORGEAI-KISSKI-SAIA-PROVIDER-QUALIFICATION-1 " + state,
        "profile: kisski-saia; kind: openai-compatible; deployment: REMOTE",
        "API root: https://chat-ai.academiccloud.de/v1; system TLS trust only",
        "Stage 1: one POST /v1/models (official documented listing method)",
        "Stage 2: one approved chat: " + TINY_PROMPT,
        "Stage 3: one separately approved fixed synthetic JSON proposal chat",
        "Maximum: 1 discovery + 2 chats; no retries, fallback or model reselection",
        "Two separate hidden S1 provisions: discovery and remote-model-bearer purposes",
        "SYNTHETIC only; no repository input, file mutation or generated-code execution",
        "512 output tokens per chat; 60-second client timeout; no provider-capacity claim",
        "Stage 4 coding quality is deferred to FORGEAI-KISSKI-CODING-MODEL-EVALUATION-1",
        "No live run is authorized by local validation; --live requires: " + AUTHORIZATION,
    )


def host_config(
    config: legacy.ProbeConfig, credential: SecretRef, model: ModelId, now: datetime
) -> LocalHostConfig:
    """Existing binding/admission types only; configuration is not authority."""
    settings = OpenAICompatibleSettings(
        config.base_url,
        model.value,
        None,
        config.timeout_seconds,
        config.max_output_tokens,
        provider_id=ProviderId(config.provider_id),
        deployment=ModelDeployment.REMOTE,
        bearer_credential=credential,
    )
    window = (now - timedelta(minutes=1), now + timedelta(minutes=30))
    return LocalHostConfig(
        legacy._revision(),
        legacy._principal(),
        legacy._policy(),
        (
            OperatorGrant(
                GrantId("saia-chat"),
                "invoke-capability",
                ModelPurpose.CHAT.capability_id.value,
                *window,
            ),
            OperatorGrant(
                GrantId("saia-secret"), "secret-use", credential.exact.identity, *window
            ),
        ),
        (
            ModelBindingConfig(
                legacy.BINDING, ModelRequirement("saia-synthetic"), settings
            ),
        ),
        2,
        disclosure=RemoteDisclosureConfig(
            (legacy.declaration(config),), (legacy.chat_admission(config, model, now),)
        ),
    )


def _unique(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for name, value in pairs:
        if name in result:
            raise ValueError("duplicate field")
        result[name] = value
    return result


def structured_matches(content: str) -> bool:
    """Fixed fixture equality only; this is not a second CodingProposal parser."""
    try:
        if len(content) > 4096 or len(content.encode("utf-8")) > 4096:
            return False
        return bool(
            json.loads(content, object_pairs_hook=_unique) == json.loads(EXPECTED_JSON)
        )
    except ValueError, RecursionError:
        return False


def chat_failure(
    result: GovernedChatResult, attempt: tuple[str, set[str]] | None
) -> Outcome | None:
    if result.execution.final_state is ExecutionState.SUCCEEDED:
        return None
    if attempt is None:
        return Outcome.REFUSED
    if attempt[0] == "not_sent":
        return (
            Outcome.REFUSED
            if attempt[1] == {"refused_at_gate"}
            else Outcome.INCONCLUSIVE
        )
    if attempt[0] == "unknown":
        return Outcome.INCONCLUSIVE
    if attempt[0] == "provider_rejected":
        return Outcome.PROVIDER_REJECTED
    return Outcome.CONTRACT_REJECTED


async def chat_once(
    host: GovernedHost,
    config: legacy.ProbeConfig,
    prompt: str,
    write: Callable[[str], None],
) -> tuple[GovernedChatResult, Outcome | None]:
    context = host.model_execution(
        ModelPurpose.CHAT,
        disclosure=ExecutionDisclosure(
            legacy.PROBE_CONSUMER,
            DisclosureDeclaration(frozenset({DisclosureClass.SYNTHETIC})),
        ),
    )
    result = await host.governed_chat(
        context, ChatRequest((ChatMessage(ChatRole.USER, prompt),))
    )
    execution = result.execution
    attempt = legacy._attempt_for(config.custody, execution.execution_id.value)
    status = _remote_chat_http_status(host, execution.execution_id)
    write(f"chat execution: {execution.execution_id.value}")
    write(f"chat attempt state: {attempt[0] if attempt else 'none'}")
    write(f"chat effect: {execution.effect.value}")
    if status is not None:
        write(f"chat HTTP status: {status}")
    if execution.error is not None:
        write(
            f"chat error: {execution.error.category.value} / "
            f"{execution.error.recoverability.value}"
        )
    # Never print provider text, even a short excerpt of a successful response.
    return result, chat_failure(result, attempt)


async def chat_stages(
    host: GovernedHost,
    config: legacy.ProbeConfig,
    ask: Callable[[str], str],
    write: Callable[[str], None],
) -> Outcome:
    result, failure = await chat_once(host, config, TINY_PROMPT, write)
    if failure is not None:
        return failure
    if result.response is None or result.response.content != "KISSKI_OK":
        return Outcome.CONTENT_REJECTED
    write("stage 2: exact synthetic token passed; coding quality NOT QUALIFIED")
    if ask("Approve one fixed SYNTHETIC JSON proposal chat? [y/N] ").strip() != "y":
        return Outcome.CONNECTIVITY_ONLY
    result, failure = await chat_once(host, config, STRUCTURED_PROMPT, write)
    if failure is not None:
        return failure
    if result.response is None or not structured_matches(result.response.content):
        return Outcome.STRUCTURED_REJECTED
    return Outcome.PASS


def run(
    config: legacy.ProbeConfig,
    *,
    ask: Callable[[str], str],
    write: Callable[[str], None],
    clock: Callable[[], datetime] = lambda: datetime.now(UTC),
) -> Outcome:
    """Trusted entry after CLI opt-in; tests substitute only synthetic S1/TLS."""
    source: CredentialSource = open_credential_source(legacy._scope())
    try:
        # No public discovery bootstrap exists. Reuse the existing trusted
        # probe seam; it stays out of all application/Model contracts.
        owned_source = cast(Any, source)._source
        credential = _provision_interactively(
            owned_source, "saia-discovery", discovery_purpose(), discovery_consumer()
        )
        discovered = legacy._discover(config, owned_source, credential, clock(), clock)
        write(f"discovery outcome: {discovered.outcome.value}")
        write(f"discovery state: {discovered.state.value if discovered.state else 'none'}")
        if discovered.attempt_id is not None:
            write(f"discovery attempt: {discovered.attempt_id.value}")
        if discovered.status is not None:
            write(f"discovery HTTP status: {discovered.status}")
        if legacy.classify_discovery(discovered) is not None:
            return Outcome.DISCOVERY_FAILED
        # Escape terminal-control characters in provider-controlled identifiers.
        for number, model in enumerate(discovered.models, 1):
            write(f"{number}. {json.dumps(model.value, ensure_ascii=True)}")
        answer = ask("Select one listed model number (blank declines): ").strip()
        if not answer.isascii() or not answer.isdecimal() or len(answer) > 4:
            return Outcome.DECLINED
        index = int(answer)
        if not 1 <= index <= len(discovered.models):
            return Outcome.DECLINED
        model = discovered.models[index - 1]
        write("pinned model: " + json.dumps(model.value, ensure_ascii=True))
        if ask("Approve one tiny SYNTHETIC chat with this model? [y/N] ").strip() != "y":
            return Outcome.DECLINED
        # The public source provisions only remote-model-bearer. The first
        # revision cannot serve chat; no material is copied between purposes.
        chat_credential = source.provision("saia-chat")
        host = open_local_host(
            host_config(config, chat_credential, model, clock()),
            {"revision": "r1", "binding": legacy.BINDING},
            clock=clock,
            remote=RemoteModelRuntime(
                source, config.custody, config.margin, config.trust_anchor
            ),
        )
        return asyncio.run(chat_stages(host, config, ask, write))
    finally:
        source.close()


class _SafeParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        # argparse normally echoes invalid arguments, possibly a pasted key.
        self.exit(2, "Invalid options; only --plan or --live is accepted.\n")


def main(options: list[str] | None = None) -> int:
    parser = _SafeParser(description="SAIA synthetic qualification", allow_abbrev=False)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--plan", action="store_true")
    group.add_argument("--live", action="store_true")
    args = parser.parse_args(options)
    for line in plan_lines(live=args.live):
        print(line)
    if not args.live:
        return 0
    if not (sys.stdin.isatty() and sys.stdout.isatty()):
        print("Live execution refused: interactive terminal required")
        return 2
    if input("Type the exact live authorization above: ").strip() != AUTHORIZATION:
        print("Live execution declined; no credentials or provider calls")
        return 2
    custody = Path(tempfile.mkdtemp(prefix="kisski-saia-qualification-"))
    print(f"local custody directory: {custody}")
    try:
        outcome = run(live_config(custody), ask=input, write=print)
    except Exception, KeyboardInterrupt:
        # No raw exceptions/tracebacks: preserve custody and do not infer no send.
        outcome = Outcome.INCONCLUSIVE
    print("FINAL CLASSIFICATION: " + outcome.value)
    print("No repository disclosure/mutation; ForgeAI coding quality NOT QUALIFIED")
    return 0 if outcome in {Outcome.PASS, Outcome.CONNECTIVITY_ONLY} else 1


if __name__ == "__main__":
    raise SystemExit(main())
