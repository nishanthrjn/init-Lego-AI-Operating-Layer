"""Attended fixed-model synthetic diagnostic; default mode performs no I/O."""

import argparse
import re
import sys
import tempfile
from collections.abc import Callable, Set
from pathlib import Path
from typing import NoReturn

from scripts import kisski_compatibility_probe as legacy
from scripts import kisski_saia_qualification as saia

VERSION = "OPENAI-COMPAT-FINISH-REASON-LIVE-DIAGNOSTIC-1"
AUTHORIZATION = "AUTHORIZE " + VERSION + " LIVE SYNTHETIC"
MODEL = "qwen3.5-397b-a17b"
CATEGORIES = frozenset(
    {
        "ABSENT",
        "NULL",
        "STOP",
        "LENGTH",
        "CONTENT_FILTER",
        "TOOL_CALLS",
        "FUNCTION_CALL",
        "OTHER_STRING",
        "NON_STRING",
    }
)


def safe_line(line: str) -> str | None:
    """Allowlist the existing probe's safe observations, never arbitrary text."""
    name, separator, value = line.partition(": ")
    if not separator:
        return None
    if name == "chat execution" and re.fullmatch(r"exec-[a-z0-9]{1,64}", value):
        return "execution_id: " + value
    if name == "chat HTTP status" and re.fullmatch(r"[2-5][0-9]{2}", value):
        return "http_status_class: " + value[0] + "xx"
    fields: dict[str, tuple[str, Set[str]]] = {
        "chat attempt state": (
            "transport_completion",
            {"none", "intended", "not_sent", "provider_rejected", "completed", "unknown"},
        ),
        "chat effect": ("effect", {"none", "completed", "partial", "unknown"}),
        "chat contract finish_reason_category": ("finish_reason_category", CATEGORIES),
        "chat contract returned_model_matches_requested": (
            "model_identity_match",
            {"true", "false"},
        ),
        "chat receive request_fully_sent": ("request_fully_sent", {"true", "false"}),
        "chat receive body_complete": ("response_complete", {"true", "false"}),
    }
    if name in fields:
        output, allowed = fields[name]
        return output + ": " + value if value in allowed else None
    if name == "chat contract rejection_reason":
        allowed_reasons = {
            "VALIDATED",
            "JSON_INVALID",
            "ROOT_NOT_OBJECT",
            "MODEL_FIELD_MISSING",
            "MODEL_FIELD_NOT_STRING",
            "MODEL_ID_MISMATCH",
            "CHOICES_MISSING",
            "CHOICES_NOT_LIST",
            "CHOICE_COUNT_INVALID",
            "CHOICE_NOT_OBJECT",
            "FINISH_REASON_MISSING",
            "FINISH_REASON_INVALID",
            "MESSAGE_MISSING",
            "MESSAGE_NOT_OBJECT",
            "ROLE_INVALID",
            "CONTENT_MISSING",
            "CONTENT_NULL",
            "CONTENT_NOT_STRING",
            "TOOL_CALL_PRESENT",
            "FUNCTION_CALL_PRESENT",
            "RESULT_CONSTRUCTION_FAILED",
        }
        return "contract_reason: " + value if value in allowed_reasons else None
    return None


def run(
    config: legacy.ProbeConfig,
    *,
    ask: Callable[[str], str],
    write: Callable[[str], None],
) -> saia.Outcome:
    """Trusted entry after CLI authorization; no model selection by the operator."""

    def fixed_selection(question: str) -> str:
        if question == "Enter one exact displayed model ID (blank declines): ":
            return MODEL
        if question == "Approve one tiny SYNTHETIC chat with this model? [y/N] ":
            return ask("Approve one SYNTHETIC token chat with " + MODEL + "? [y/N] ")
        raise ValueError("unexpected diagnostic stage")

    def project(line: str) -> None:
        safe = safe_line(line)
        if safe is not None:
            write(safe)

    write("selected_model: " + MODEL)
    return saia.run(config, ask=fixed_selection, write=project, diagnostic_only=True)


class SafeParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        self.exit(2, "Invalid options; use --plan or --live.\n")


def main(options: list[str] | None = None) -> int:
    parser = SafeParser(allow_abbrev=False)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--plan", action="store_true")
    mode.add_argument("--live", action="store_true")
    args = parser.parse_args(options)
    print(VERSION + "; attended diagnostic only; no model-quality claim")
    print("selected_model: " + MODEL)
    print("Maximum 1 discovery + 1 chat; no retry, fallback, reselection or continuation")
    print("SYNTHETIC token request; 512 output tokens; 60-second timeout")
    print("Two separate hidden S1 provisions; no repository input")
    print("Required authorization: " + AUTHORIZATION)
    if not args.live:
        print("PLAN ONLY; no credentials or provider calls")
        return 0
    if not (sys.stdin.isatty() and sys.stdout.isatty()):
        print("Interactive terminal required; no provider calls")
        return 2
    if input("Type exact authorization: ") != AUTHORIZATION:
        print("Declined; no credentials or provider calls")
        return 2
    try:
        custody = Path(tempfile.mkdtemp(prefix="finish-reason-diagnostic-"))
        print("local custody directory: " + str(custody))
        outcome = run(saia.live_config(custody), ask=input, write=print)
    except (Exception, KeyboardInterrupt):
        print("invocation_outcome: INCONCLUSIVE; inspect custody; no retry")
        return 1
    print("invocation_outcome: " + outcome.name)
    print("DIAGNOSTIC ONLY; acceptance unchanged; no model quality qualified; no retry")
    return 0 if outcome is saia.Outcome.CONNECTIVITY_ONLY else 1


if __name__ == "__main__":
    raise SystemExit(main())
