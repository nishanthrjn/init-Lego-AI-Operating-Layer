"""Maintainer-run documentary checks; no transport, credentials or network."""

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BASELINE = "37f83f8e01e627176a9a9e3a430e6688da166d05"
SLICE = "T2-BOUNDED-CHUNKED-RESPONSE-ADR-1"
ADDENDUM = "adrs/ADR-023-BOUNDED-CHUNKED-RESPONSE-ADDENDUM-1.md"
REVIEW = "planning/T2-BOUNDED-CHUNKED-RESPONSE-ADR-1.md"
VALIDATOR = "validate_t2_bounded_chunked_response_adr_1.py"
ALLOWED = frozenset({ADDENDUM, REVIEW, VALIDATOR})
DECISION = "T2_BOUNDED_CHUNKED_SUPPORT_RECOMMENDED"
DECISIONS = (
    DECISION,
    "T2_BOUNDED_CHUNKED_SUPPORT_NOT_RECOMMENDED",
    "UPSTREAM_ARCHITECTURE_DECISION_REQUIRED",
    "EVIDENCE_INSUFFICIENT",
)

# Exact policy/evidence anchors are independent negative-fixture targets.
POLICY = (
    "| Protocol | HTTP/1.1 response chunking only |",
    "| CL plus TE | Hard refusal, including duplicate/conflicting field forms; never prefer either |",
    "| Transfer coding | One field, one token chunked, ASCII case-insensitive, surrounding SP/HTAB only |",
    "| Coding chains | Refuse duplicate TE fields, comma lists, parameters, compression and unknown codings |",
    "| Chunk size | 1–6 ASCII hexadecimal digits, upper/lowercase; leading zeros within that limit |",
    "| Extensions | Refuse every chunk extension; maximum accepted extension bytes/count: 0/0 |",
    "| Trailers | Refuse every nonempty trailer section; maximum accepted trailer bytes/fields: 0/0 |",
    "| Line ending | Exact CRLF; no bare LF, whitespace around size, signs or 0x prefix |",
    "| Terminal | Zero size followed by CRLF and empty trailer-section CRLF required |",
    "| Decoded body cap | 4194304 bytes, existing T2 response-body cap |",
    "| Header cap | 32768 bytes including terminator, at most 64 fields, every completion path |",
    "| Size-line cap | 8 bytes including CRLF |",
    "| Framing cap | 32768 encoded framing bytes, excluding headers and decoded data |",
    "| Chunk-count cap | 6552 nonterminal chunks; terminal zero is separate and ends parsing |",
    "| Encoded body cap | 4227072 bytes, decoded body plus framing caps |",
    "| Deadline | Existing absolute monotonic attempt deadline; never reset per chunk/read |",
    "| Delivery | One fully decoded bounded body only after terminal and empty trailers complete |",
    "| Failure after send | UNKNOWN where remote work may have occurred; no partial-body delivery |",
    "| Retry | None; no replay, resume, fallback or automatic model reselection |",
    "| Provider branch | None; generic private T2 framing, never a KiSSKI-specific transport |",
    "| Streaming | stream=false; SSE and model-token streaming unsupported |",
    "| HTTP/2 | Excluded |",
)
EVIDENCE = (
    "| Model | qwen3-coder-next |",
    "| Request mode | stream=false |",
    "| Execution | exec-6b1bfe333b9e4809aeba4d060ce26e9e |",
    "| Connected | true |",
    "| TLS completed | true |",
    "| Request fully sent | true |",
    "| First byte seen | true |",
    "| Headers complete | true |",
    "| Protocol | HTTP/1.1 |",
    "| Header status | 200 |",
    "| Content-Length | absent |",
    "| Transfer-Encoding | present |",
    "| Framing | chunked |",
    "| Body bytes observed | 638 encoded bytes; not decoded entity bytes |",
    "| Body complete | false |",
    "| EOF seen | false |",
    "| Parser rejected | true |",
    "| Cap reached | false |",
    "| Read error | false |",
    "| Receive stage | read_body |",
    "| Deadline stage | unknown |",
    "| Failure category | protocol |",
    "| Send to first byte | 135 ms |",
    "| First byte to headers | 0 ms |",
    "| Headers to body complete | unknown |",
    "| Total receive | 135 ms |",
    "| Effect | UNKNOWN |",
    "| Attempt state | UNKNOWN |",
    "| Final classification | RESULT_INCONCLUSIVE |",
)
REQUIRED = {
    ADDENDUM: (
        "Status: Proposed — NOT ACCEPTED.",
        *POLICY,
        "## Authority and classification",
        "## Grammar and deliberately restricted interoperability",
        "## Parser, deadline and security",
        "## Effect and result truth",
        "## Application separation and safe diagnostics",
        "## Consequences and acceptance",
        "not a fully conforming general RFC 9112 recipient",
        "SIZE_LINE, DATA, DATA_CRLF, TERMINAL_CRLF,",
        "floor((32768 - 5) / 5) = 6552",
        "diagnostics remain optional evidence, never control input",
    ),
    REVIEW: (
        "Status: Proposed architecture recommendation; NOT ACCEPTED.",
        *EVIDENCE,
        "## Question and authority",
        "## Current implementation and sources",
        "## Security and proposed design",
        "## Alternatives",
        "## REUSE / EXTEND / CREATE and ownership",
        "## Later implementation acceptance matrix",
        "## Live requalification after acceptance and implementation",
        "## Documentary validation handoff",
        "SAIA live connectivity is NOT qualified",
        "coding quality is NOT qualified",
        "Chunked != SSE",
        "A: bounded generic T2 decoder",
        "B: KiSSKI-specific transport",
        "C: provider streaming/SSE",
        "D: switch provider/model",
        "E: keep unsupported",
        "no JSON Stage 3",
        "Recommendation is not implementation authority",
    ),
}


def git(*args: str) -> bytes:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=True,
        capture_output=True,
        timeout=30,
    ).stdout


def decode(raw: bytes) -> str:
    return raw.decode("utf-8", errors="strict").replace("\r\n", "\n")


def paths(*args: str) -> set[str]:
    return {decode(item) for item in git(*args).split(b"\0") if item}


def scope(changed: set[str]) -> None:
    if changed - ALLOWED:
        raise ValueError(f"outside three-file scope: {sorted(changed - ALLOWED)}")


def whitespace(name: str, source: str) -> None:
    if not source.endswith("\n") or source.endswith("\n\n"):
        raise ValueError(f"invalid final newline: {name}")
    if any(line.rstrip() != line for line in source.splitlines()):
        raise ValueError(f"trailing whitespace: {name}")


def document(name: str, source: str) -> None:
    whitespace(name, source)
    normalized = " ".join(source.split()).casefold()
    for required in REQUIRED[name]:
        if " ".join(required.split()).casefold() not in normalized:
            raise ValueError(f"missing {name} invariant: {required}")
    status = REQUIRED[name][0]
    if re.findall(r"^Status: .+$", source, re.M) != [status]:
        raise ValueError(f"expected exactly one Proposed status: {name}")
    for row in POLICY if name == ADDENDUM else EVIDENCE:
        key = row.split("|", 2)[1].strip()
        matches = [
            line for line in source.splitlines() if line.startswith(f"| {key} |")
        ]
        if matches != [row]:
            raise ValueError(f"conflicting or missing table value: {name}: {key}")
    if sum(source.count(choice) for choice in DECISIONS) != 1:
        raise ValueError(f"expected one decision: {name}")
    if not source.endswith(f"Final decision: {DECISION}\n"):
        raise ValueError(f"incorrect final decision: {name}")


def rejected(name: str, source: str) -> None:
    try:
        document(name, source)
    except ValueError:
        return
    raise ValueError(f"negative documentary control accepted: {name}")


def fixtures(contents: dict[str, str]) -> None:
    scope(set(ALLOWED))
    for forbidden in (
        "src/legoai/reference/_credential_https.py",
        "pyproject.toml",
        "uv.lock",
        "adrs/ADR-023.md",
        "adrs/ADR-014.md",
        "adrs/ADR-INDEX.md",
    ):
        try:
            scope({forbidden})
        except ValueError:
            pass
        else:
            raise ValueError(f"scope fixture accepted: {forbidden}")
    for name, source in contents.items():
        document(name, source)
        # Whitespace wrapping is allowed; semantic table values are exact.
        document(name, source.replace("## ", "##  "))
        for fragment in REQUIRED[name]:
            # Anchors below are exact; case normalization is tested separately.
            start = source.casefold().find(fragment.casefold())
            if start < 0:
                # Prose may wrap: remove a unique word sequence's first word.
                words = fragment.split()
                pattern = r"\s+".join(re.escape(word) for word in words)
                mutated, count = re.subn(
                    pattern, "REMOVED", source, count=1, flags=re.IGNORECASE
                )
                if count != 1:
                    raise ValueError(f"fixture target absent: {fragment}")
            else:
                mutated = source[:start] + "REMOVED" + source[start + len(fragment) :]
            rejected(name, mutated)
        rejected(name, source + f"Final decision: {DECISION}\n")
        rejected(name, source.replace(DECISION, DECISIONS[1]))
        rejected(name, source.replace("Status: Proposed", "Status: Accepted", 1))
        rejected(name, source.replace("\n", " \n", 1))
        rows = POLICY if name == ADDENDUM else EVIDENCE
        rejected(name, source.replace(rows[0], rows[0] + "\n" + rows[0]))


def main() -> int:
    phase = "three-file scope; production, dependencies and accepted ADRs unchanged"
    try:
        print(f"[PHASE] {phase}", flush=True)
        changed = paths("diff", "--name-only", "-z", BASELINE)
        changed |= paths("diff", "--cached", "--name-only", "-z", BASELINE)
        changed |= paths("ls-files", "--others", "--exclude-standard", "-z")
        scope(changed)
        for name in ALLOWED:
            path = ROOT / name
            if path.is_symlink() or not path.is_file():
                raise ValueError(f"expected ordinary file: {name}")
            whitespace(name, decode(path.read_bytes()))
        phase = "proposed profile, exact evidence, bounds, effects and exclusions"
        print(f"\n[PHASE] {phase}", flush=True)
        contents = {name: decode((ROOT / name).read_bytes()) for name in REQUIRED}
        for name, source in contents.items():
            document(name, source)
        phase = "positive and negative documentary fixtures"
        print(f"\n[PHASE] {phase}", flush=True)
        fixtures(contents)
        phase = "staged documentary consistency"
        print(f"\n[PHASE] {phase}", flush=True)
        staged = paths("diff", "--cached", "--name-only", "-z", BASELINE)
        for name in staged:
            source = decode(git("show", f":{name}"))
            whitespace(name, source)
            if name in REQUIRED:
                document(name, source)
            if source != decode((ROOT / name).read_bytes()):
                raise ValueError(f"staged/working slice differs: {name}")
        for phase, args in (
            ("working whitespace", ("diff", "--check")),
            ("staged whitespace", ("diff", "--cached", "--check")),
        ):
            print(f"\n[PHASE] {phase}", flush=True)
            git(*args)
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        print(f"FAIL: {phase}: {exc}; later phases NOT RUN")
        return 1
    print(
        f"{SLICE} LOCAL DOCUMENT CHECKS PASSED; PROPOSED ONLY; "
        "NO IMPLEMENTATION OR LIVE EXECUTION AUTHORIZED"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
