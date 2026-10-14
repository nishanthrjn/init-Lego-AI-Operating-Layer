"""Maintainer-run documentary checks only; local files and read-only Git."""

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BASELINE = "40ee5a20cd3911edaf51efe0c0b1a329b346daa2"
SLICE = "OPENAI-COMPAT-FUNCTION-CALL-NULL-COMPATIBILITY-REVIEW-1"
DOCUMENT = f"planning/{SLICE}.md"
SELF = "validate_openai_compat_function_call_null_compatibility_review_1.py"
ALLOWED = {DOCUMENT, SELF}
DECISION = "ACCEPT_FUNCTION_CALL_NULL_EQUIVALENCE"
OPTIONS = (
    DECISION,
    "KEEP_STRICT_PRESENCE_REJECTION",
    "MORE_EVIDENCE_REQUIRED",
    "NEW_ARCHITECTURE_DECISION_REQUIRED",
)
REQUIRED = (
    "Scope: legacy function_call absent or JSON null only.",
    "Production acceptance remains unchanged in this review.",
    "No implementation or live execution is authorized by this review.",
    "exec-8425fb5a51484bc0b15d08e53dc5e095",
    "HTTP 200; HTTP/1.1 chunked; body complete; 626 decoded body bytes;",
    "terminal chunk seen; parser_rejected=false; JSON valid; returned model matches.",
    "Observed: function_call_present=true; function_call_shape=NULL.",
    "Observed: tool_calls_present=false; tool_calls_shape=ABSENT.",
    "Historical result: FUNCTION_CALL_PRESENT; ModelFailure.PROTOCOL_INCOMPATIBLE;",
    "CHAT_CONTRACT_REJECTED; NO RETRY; completed attempt; chat effect none.",
    "Current policy: any tool_calls key presence rejects, then any function_call key presence rejects, regardless of value.",
    "No tool execution, function dispatch, new host action, disclosure admission, Secret-use permission, custody schema or retry policy is introduced.",
    "The future rule is provider-neutral; no provider-name or model-name branch.",
    'The future legacy-field gate may use message.get("function_call") is None.',
    "Tool_calls policy unchanged: every present tool_calls value remains rejected.",
    "Non-null function_call values remain rejected: {}, nonempty objects, [], nonempty arrays, strings, numbers, booleans and every other non-null value.",
    "Future accepted responses use existing SUCCEEDED/COMPLETED mapping; historical rejected/NONE results are not rewritten.",
    "Governance assessment: no new ADR required for this null-only adapter compatibility rule.",
    "Usage semantics unchanged: missing/non-object usage becomes None; invalid individual token counts become None; only nonnegative exact integers are retained.",
    "Diagnostics preserve function_call_present=true and function_call_shape=NULL after future acceptance.",
    "Next slice: OPENAI-COMPAT-FUNCTION-CALL-NULL-1",
    "No live connectivity or coding quality is qualified by this review.",
)
MATRIX = (
    "| A | function_call absent | Accept if all else valid |",
    "| B | function_call null | Accept if all else valid |",
    "| C | function_call {} | Reject |",
    "| D | function_call nonempty object | Reject without reading name/arguments |",
    "| E | function_call [] | Reject |",
    "| F | function_call nonempty array | Reject |",
    "| G | function_call string, including empty | Reject |",
    "| H | function_call number, including zero | Reject |",
    "| I | function_call boolean, including false | Reject |",
    "| J | tool_calls absent plus function_call null | Accept if all else valid |",
    "| K | tool_calls present plus function_call null | TOOL_CALL_PRESENT wins for null/empty/nonempty tool values |",
    "| L | Accepted explicit null diagnostics | Present true, shape NULL; no raw content |",
    "| M | Authority and dispatch | No tool/function execution path; content remains data |",
    "| N | Effects and custody | Existing success/rejection/UNKNOWN mappings and completed transport facts preserved |",
    "| O | Otherwise malformed response with null | Reject at existing first gate |",
)


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, check=True, timeout=30
    ).stdout.decode("utf-8").replace("\r\n", "\n")


def whitespace(source: str) -> None:
    if not source.endswith("\n") or source.endswith("\n\n"):
        raise ValueError("exactly one final newline required")
    if any(line.rstrip() != line for line in source.splitlines()):
        raise ValueError("trailing whitespace")


def document(source: str) -> None:
    whitespace(source)
    if not source.startswith(f"# {SLICE}\n"):
        raise ValueError("wrong review title")
    if source.count(f"Decision: {DECISION}\n") != 1:
        raise ValueError("singular decision required")
    if any(source.count(option) != (1 if option == DECISION else 0) for option in OPTIONS):
        raise ValueError("conflicting decision")
    for required in (*REQUIRED, *MATRIX):
        if source.count(required) != 1:
            raise ValueError("missing or duplicated invariant: " + required)


def scope() -> None:
    changed = set(git("diff", "--name-only", "--no-renames", BASELINE).splitlines())
    changed.update(
        git("diff", "--cached", "--name-only", "--no-renames", BASELINE).splitlines()
    )
    changed.update(git("ls-files", "--others", "--exclude-standard").splitlines())
    if changed - ALLOWED:
        raise ValueError("outside documentary scope: " + repr(changed - ALLOWED))
    for name in ALLOWED:
        path = ROOT / name
        if path.is_symlink() or not path.is_file():
            raise ValueError("missing or symlinked documentary file: " + name)
        whitespace(path.read_text(encoding="utf-8"))


def fixtures(source: str) -> None:
    document(source)
    document(
        source.replace(
            "Date: 2026-10-14.",
            "Date: 2026-10-14.\nEditorial note: documentary fixture only.",
            1,
        )
    )
    mutations = [source.replace(line, "", 1) for line in (*REQUIRED, *MATRIX)]
    mutations.extend(source + f"Decision: {option}\n" for option in OPTIONS)
    mutations.extend(
        (
            source.replace("function_call_shape=NULL", "function_call_shape=ABSENT", 1),
            source.replace("| C | function_call {} | Reject |", "| C | function_call {} | Accept |"),
            source.replace("| H | function_call number, including zero | Reject |", "| H | function_call number, including zero | Accept |"),
            source + "\n",
            source.replace("# " + SLICE, "# Wrong review", 1),
        )
    )
    for index, value in enumerate(mutations):
        try:
            document(value)
        except ValueError:
            continue
        raise ValueError(f"negative documentary fixture accepted: {index}")


def main() -> int:
    phase = "two-file documentary scope; production, acceptance and ADRs unchanged"
    try:
        print("[PHASE] " + phase, flush=True)
        scope()
        phase = "live evidence, null-only decision, authority and future test matrix"
        print("\n[PHASE] " + phase, flush=True)
        source = (ROOT / DOCUMENT).read_text(encoding="utf-8")
        document(source)
        phase = "positive and negative documentary fixtures"
        print("\n[PHASE] " + phase, flush=True)
        fixtures(source)
        phase = "staged documentary consistency"
        print("\n[PHASE] " + phase, flush=True)
        indexed = set(git("ls-files", "--", *sorted(ALLOWED)).splitlines())
        if DOCUMENT in indexed:
            document(git("show", ":" + DOCUMENT))
        if SELF in indexed:
            whitespace(git("show", ":" + SELF))
        for phase, args in (
            ("working whitespace", ("diff", "--check", BASELINE)),
            ("staged whitespace", ("diff", "--cached", "--check", BASELINE)),
        ):
            print("\n[PHASE] " + phase, flush=True)
            git(*args)
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(f"FAIL: {phase}: {error}; later phases NOT RUN")
        return 1
    print(
        f"{SLICE} LOCAL DOCUMENT CHECKS PASSED; {DECISION}; "
        "PRODUCTION UNCHANGED; NO IMPLEMENTATION OR LIVE EXECUTION AUTHORIZED"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
