"""HF-INFERENCE-PROVIDERS-COMPATIBILITY-1: blocked, offline preflight.

HF documents GET /v1/models. Qualified discovery/T2 supports POST only and
returns ids without backend metadata. There is deliberately no live execution
path until these gaps have an approved, qualified resolution. No credential,
environment, repository or network reads, including when --live is requested.
"""

import argparse
from datetime import datetime, timedelta
from enum import Enum
from typing import NoReturn

from legoai.governance.provider_control import (
    ProviderDiscoveryAdmission,
    ProviderOperation,
)
from legoai.governance.secret import SecretRef

ORIGIN = "https://router.huggingface.co"
API_ROOT = "/v1"
PROVIDER = "huggingface-inference-router"
CONSUMER = "hf-inference-compatibility-probe"
DISCOVERY_PURPOSE = "provider-model-discovery"
CHAT_PURPOSE = "remote-model-bearer"
PROMPT = "Return exactly the word READY."


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


def discovery_admission(
    credential: SecretRef, now: datetime
) -> ProviderDiscoveryAdmission:
    """Prepare exact authority from a future S1 revision; perform no I/O.

    This value is not an execution path and does not make GET supported.
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
        ORIGIN,
        API_ROOT,
        ProviderOperation.MODEL_DISCOVERY,
        CONSUMER,
        credential.exact,
        now,
        now + timedelta(minutes=15),
    )


def plan_lines() -> tuple[str, ...]:
    """Static plan: no credential reads, DNS, network or generated authority."""
    return (
        "HF-INFERENCE-PROVIDERS-COMPATIBILITY-1 PREFLIGHT BLOCKED",
        "router operator: Hugging Face Inference Providers",
        f"API root: {ORIGIN}{API_ROOT}",
        f"documented discovery: GET {ORIGIN}{API_ROOT}/models",
        "qualified discovery transport: POST only; GET is not implemented",
        f"planned chat: POST {ORIGIN}{API_ROOT}/chat/completions",
        "future maximum: 1 discovery + 1 chat; executable calls now: 0",
        "model-visible disclosure class: SYNTHETIC only; no repository input",
        "discovery is provider-control, not model-visible disclosure",
        f"fixed future synthetic message: {PROMPT}",
        "credential prompts now: 0; future: 2 hidden interactive S1 prompts",
        f"separate Secret purposes: {DISCOVERY_PURPOSE}; {CHAT_PURPOSE}",
        "no token arguments, environment, config files, pipes or chat",
        "future routing: one operator-selected model:backend-provider",
        "refuse unsuffixed models, :auto, :fastest, :cheapest and :preferred",
        "qualified discovery discards backend status/pricing/modalities",
        "no adequately established live model/backend pairing; stop before chat",
        "no retry; no fallback; no alternate provider or model",
        "response model must match exactly; finish_reason must be stop",
        "bounded Content-Length framing remains mandatory",
        "typed model-mismatch/framing/quota diagnostics are not available",
        "classification: " + Classification.PROVIDER_IDENTITY_INDETERMINATE.value,
        "classification scope: local preflight; no provider response observed",
        "live execution disabled; authorization alone cannot remove these blockers",
    )


class _SafeParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        # Argparse otherwise echoes unknown arguments, possibly including a token.
        self.exit(2, "Invalid options. Use --plan; token arguments are forbidden.\n")


def main(options: list[str] | None = None) -> int:
    parser = _SafeParser(description=__doc__, allow_abbrev=False)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--plan", action="store_true", help="show the offline plan")
    modes.add_argument("--live", action="store_true", help="refused: preflight blocked")
    args = parser.parse_args(options)
    for line in plan_lines():
        print(line)
    # Default fails closed. --plan succeeds only at displaying the blocked plan.
    return 0 if args.plan else 2


if __name__ == "__main__":
    raise SystemExit(main())
