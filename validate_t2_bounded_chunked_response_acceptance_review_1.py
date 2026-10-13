"""Maintainer-run acceptance document checks; local files and Git only."""

import re
import subprocess
from pathlib import Path

import validate_t2_bounded_chunked_response_adr_1 as proposal

ROOT = Path(__file__).resolve().parent
BASELINE = "2209ead3ef395ba035475a50622a2d106b00f26e"
SLICE = "T2-BOUNDED-CHUNKED-RESPONSE-ACCEPTANCE-REVIEW-1"
ADR = proposal.ADDENDUM
INDEX = "adrs/ADR-INDEX.md"
REVIEW = f"planning/{SLICE}.md"
VALIDATOR = "validate_t2_bounded_chunked_response_acceptance_review_1.py"
ALLOWED = frozenset({ADR, INDEX, REVIEW, VALIDATOR})
STATUS = "Status: Accepted — maintainer-delegated decision; local document validation pending."
DECISION = "ACCEPT_BOUNDED_CHUNKED_ADDENDUM"
OPTIONS = (
    DECISION,
    "MODIFY_BEFORE_ACCEPTANCE",
    "REJECT_BOUNDED_CHUNKED_ADDENDUM",
    "NEW_ADR_REQUIRED",
)
PRIOR_RESULT = (
    "T2-BOUNDED-CHUNKED-RESPONSE-ADR-1 LOCAL DOCUMENT CHECKS PASSED; "
    "PROPOSED ONLY; NO IMPLEMENTATION OR LIVE EXECUTION AUTHORIZED"
)
RESULT = (
    f"{SLICE} LOCAL DOCUMENT CHECKS PASSED; "
    "BOUNDED CHUNKED RESPONSE ARCHITECTURE ACCEPTED; "
    "IMPLEMENTATION AUTHORIZED SEPARATELY; NO LIVE EXECUTION AUTHORIZED"
)
REQUIRED = (
    "Classification A: compatible bounded extension of ADR-023/T2.",
    "Date: 2026-10-13.",
    PRIOR_RESULT,
    "638 encoded bytes observed and first byte at 135 ms",
    "exec-6b1bfe333b9e4809aeba4d060ce26e9e",
    "attempt state UNKNOWN, effect UNKNOWN, final RESULT_INCONCLUSIVE",
    "Content-Length absent, Transfer-Encoding present",
    "No response-body correctness, successful model execution, live connectivity or coding quality is established",
    "| CL+TE | ACCEPT hard refusal; do not select precedence or normalize ambiguous lengths |",
    "| Coding chains | ACCEPT refusal of gzip/compress chains, duplicate TE, repeated chunked, parameters and unknown codings; one token only |",
    "| Extensions | ACCEPT refusal of every extension; removes grammar/metadata surface; no observed evidence requires extensions |",
    "| Trailers | ACCEPT refusal of all nonempty trailers; accept only required empty CRLF closure; no new metadata authority or disclosure |",
    "| Decoded body: 4194304 bytes | ACCEPT |",
    "| Framing overhead: 32768 bytes | ACCEPT |",
    "| Size line: 8 bytes including CRLF | ACCEPT |",
    "| Nonterminal chunks: 6552 | ACCEPT |",
    "| Encoded body: 4227072 bytes | ACCEPT |",
    "| Headers: 32768 bytes and 64 fields | ACCEPT |",
    "| Deadline: existing absolute monotonic attempt deadline | ACCEPT |",
    "No bound requires modification",
    "not a fully conforming general RFC 9112 recipient",
    "HTTP chunked transfer framing != OpenAI streaming",
    "Exclude SSE, stream=true, text/event-stream, token-by-token Model API, partial ModelResult publication, streaming tool calls, HTTP/2, request-body chunking, decompression, pooling, retry, replay, resume, fallback and arbitrary transfer codings",
    "No provider-name test is allowed",
    "Never retain the entire encoded wire body to decode afterward",
    "No timeout reset, slow-drip extension or automatic continuation outside the budget",
    "No chunk-parser outcome can rewrite a possible remote effect to NONE",
    "No custody schema change is required",
    "durable INTENDED/outcome facts, exact execution/attempt identity and reconciliation semantics unchanged",
    "No payload, raw extension/trailer, Authorization or credential material",
    "Next slice: T2-BOUNDED-CHUNKED-RESPONSE-1",
    "No live execution is authorized",
    "no JSON Stage 3",
    "assistant content == KISSKI_OK",
    "valid finish_reason (stop under the existing runner contract)",
    RESULT,
)
CRITERIA = (
    "Valid single chunk", "Valid multiple chunks", "Upper/lowercase hexadecimal",
    "Malformed size line", "Overlong size line", "Decoded aggregate body overflow",
    "Framing-overhead overflow", "Chunk-count overflow", "Premature EOF",
    "Missing chunk CRLF", "Terminal zero and empty trailer closure",
    "Every chunk extension", "Every nonempty trailer", "CL+TE refused",
    "Coding chains, duplicate fields/tokens", "Timeout before terminal chunk",
    "Timeout mid-chunk", "No deadline reset", "Qualified Content-Length regressions",
    "Safe diagnostics", "No response-body or credential/canary leakage",
    "UNKNOWN effect truth", "No retry, replay, resume", "SRCP-1, disclosure",
    "KiSSKI-like synthetic", "Existing LOCAL/Ollama/remote Model regressions",
)
PRINCIPLES = (
    "SRP", "OCP", "LSP", "ISP", "DIP", "DRY", "KISS", "YAGNI", "SoC",
    "Law of Demeter",
)


def git(*args: str) -> bytes:
    return subprocess.run(
        ["git", *args], cwd=ROOT, check=True, capture_output=True, timeout=30
    ).stdout


def decode(raw: bytes) -> str:
    return raw.decode("utf-8", errors="strict").replace("\r\n", "\n")


def paths(*args: str) -> set[str]:
    return {decode(item) for item in git(*args).split(b"\0") if item}


def scope(changed: set[str]) -> None:
    if changed - ALLOWED:
        raise ValueError(f"outside four-file acceptance scope: {sorted(changed - ALLOWED)}")


def block(source: str) -> tuple[str, str]:
    begin = f"\n<!-- {SLICE} BEGIN -->\n"
    end = f"<!-- {SLICE} END -->\n"
    if source.count(begin) != 1 or source.count(end) != 1:
        raise ValueError("expected one acceptance metadata block")
    start = source.index(begin)
    stop = source.index(end, start) + len(end)
    return source[:start] + source[stop:], source[start:stop]


def require(source: str, fragments: tuple[str, ...]) -> None:
    normalized = " ".join(source.split())
    for fragment in fragments:
        if " ".join(fragment.split()) not in normalized:
            raise ValueError(f"missing acceptance invariant: {fragment}")


def singular(source: str) -> None:
    if sum(source.count(option) for option in OPTIONS) != 1:
        raise ValueError("expected one acceptance decision")
    if re.findall(r"^Decision: (.+)$", source, re.M) != [DECISION]:
        raise ValueError("incorrect acceptance decision")


def documents(contents: dict[str, str], originals: dict[str, str]) -> None:
    remainder, current = block(contents[ADR])
    if re.findall(r"^Status: .+$", remainder, re.M) != [STATUS]:
        raise ValueError("addendum acceptance status mismatch")
    restored = remainder.replace(STATUS, "Status: Proposed — NOT ACCEPTED.", 1)
    if restored != originals[ADR]:
        raise ValueError("proposal contract or historical reasoning changed")
    proposal.document(ADR, restored)
    singular(current)
    require(current, (
        "2026-10-13", PRIOR_RESULT,
        "Local document validation of this acceptance record is pending",
        "T2-BOUNDED-CHUNKED-RESPONSE-1",
        "No live execution is authorized", "UNKNOWN historical effects",
    ))
    proposal.whitespace(ADR, contents[ADR])
    remainder, metadata = block(contents[INDEX])
    if remainder != originals[INDEX]:
        raise ValueError("unrelated index history changed")
    # Legacy index Markdown hard-break spaces are preserved, not normalized.
    proposal.whitespace(INDEX, metadata)
    require(metadata, (
        "Accepted by maintainer-delegated architecture review",
        "local document validation pending", "ADR-023 §7.3",
        "T2-BOUNDED-CHUNKED-RESPONSE-1", "No live execution authorized",
    ))
    review = contents[REVIEW]
    proposal.whitespace(REVIEW, review)
    singular(review)
    if re.findall(r"^Status: .+$", review, re.M) != [
        "Status: Architecture accepted by maintainer-delegated review; document validation pending."
    ]:
        raise ValueError("review status mismatch")
    require(review, REQUIRED)
    for offset, phrase in enumerate(CRITERIA):
        key = chr(ord("A") + offset)
        rows = re.findall(rf"^\| {key} \| (.+) \|$", review, re.M)
        if len(rows) != 1 or not rows[0].startswith(phrase):
            raise ValueError(f"missing or conflicting implementation criterion {key}")
    for name in PRINCIPLES:
        if len(re.findall(rf"^\| {re.escape(name)} \| .+ \|$", review, re.M)) != 1:
            raise ValueError(f"design review missing or duplicated: {name}")


def must_reject(contents: dict[str, str], originals: dict[str, str]) -> None:
    try:
        documents(contents, originals)
    except ValueError:
        return
    raise ValueError("negative documentary fixture was accepted")


def fixtures(contents: dict[str, str], originals: dict[str, str]) -> None:
    documents(contents, originals)
    allowed = dict(contents)
    allowed[REVIEW] = allowed[REVIEW].replace("## Decision", "##  Decision")
    documents(allowed, originals)
    for fragment in REQUIRED:
        pattern = r"\s+".join(re.escape(word) for word in fragment.split())
        altered, count = re.subn(pattern, "REMOVED", contents[REVIEW])
        if not count:
            raise ValueError(f"fixture target absent: {fragment}")
        must_reject({**contents, REVIEW: altered}, originals)
    for key in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
        altered = re.sub(rf"^\| {key} \| .+\n", "", contents[REVIEW], flags=re.M)
        must_reject({**contents, REVIEW: altered}, originals)
    for name in (ADR, REVIEW):
        altered = contents[name].replace(DECISION, OPTIONS[1])
        must_reject({**contents, name: altered}, originals)
        altered = contents[name].replace(f"Decision: {DECISION}", f"Decision: {DECISION}\nDecision: {DECISION}")
        must_reject({**contents, name: altered}, originals)
    must_reject({**contents, ADR: contents[ADR].replace("4194304", "8388608")}, originals)
    must_reject({**contents, INDEX: contents[INDEX] + "Changed history\n"}, originals)
    must_reject({**contents, ADR: contents[ADR].replace(STATUS, "Status: Proposed")}, originals)
    scope(set(ALLOWED))
    for forbidden in ("src/legoai/reference/_credential_https.py", "uv.lock", "pyproject.toml", "adrs/ADR-023.md", proposal.REVIEW):
        try:
            scope({forbidden})
        except ValueError:
            continue
        raise ValueError(f"scope fixture accepted: {forbidden}")


def main() -> int:
    phase = "four-file documentary scope; production, dependencies and accepted ADR bodies preserved"
    try:
        print(f"[PHASE] {phase}", flush=True)
        changed = paths("diff", "--name-only", "-z", BASELINE)
        changed |= paths("diff", "--cached", "--name-only", "-z", BASELINE)
        changed |= paths("ls-files", "--others", "--exclude-standard", "-z")
        scope(changed)
        originals = {name: decode(git("show", f"{BASELINE}:{name}")) for name in (ADR, INDEX)}
        contents = {}
        for name in (ADR, INDEX, REVIEW):
            path = ROOT / name
            if path.is_symlink() or not path.is_file():
                raise ValueError(f"expected regular document: {name}")
            contents[name] = decode(path.read_bytes())
        proposal.whitespace(VALIDATOR, decode((ROOT / VALIDATOR).read_bytes()))
        phase = "acceptance, preserved evidence, exact bounds and implementation gates"
        print(f"\n[PHASE] {phase}", flush=True)
        documents(contents, originals)
        # Scope excludes edits to the original evidence record; inspect baseline too.
        proposal.document(proposal.REVIEW, decode(git("show", f"{BASELINE}:{proposal.REVIEW}")))
        phase = "positive and negative documentary fixtures"
        print(f"\n[PHASE] {phase}", flush=True)
        fixtures(contents, originals)
        phase = "staged acceptance consistency"
        print(f"\n[PHASE] {phase}", flush=True)
        staged = paths("diff", "--cached", "--name-only", "-z", BASELINE)
        if staged:
            if staged != ALLOWED:
                raise ValueError("stage the complete four-file acceptance slice or leave it unstaged")
            staged_docs = {name: decode(git("show", f":{name}")) for name in contents}
            documents(staged_docs, originals)
            for name in staged:
                if decode(git("show", f":{name}")) != decode((ROOT / name).read_bytes()):
                    raise ValueError(f"staged/working content differs: {name}")
        for phase, args in (
            ("working whitespace", ("diff", "--check")),
            ("staged whitespace", ("diff", "--cached", "--check")),
        ):
            print(f"\n[PHASE] {phase}", flush=True)
            git(*args)
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        print(f"FAIL: {phase}: {exc}; later phases NOT RUN")
        return 1
    print(RESULT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
