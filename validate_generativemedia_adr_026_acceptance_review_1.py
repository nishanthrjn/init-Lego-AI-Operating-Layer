"""Maintainer-run documentary acceptance checks; no runtime/test/provider calls."""

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BASELINE = "c060ee1b8e0f8a7d75b0d3425817a06a583c5799"
SLICE = "GENERATIVE-MEDIA-ADR-026-ACCEPTANCE-REVIEW-1"
ADR = "adrs/ADR-026.md"
PARENT = "adrs/ADR-014.md"
INDEX = "adrs/ADR-INDEX.md"
VALIDATOR = "validate_generativemedia_adr_026_acceptance_review_1.py"
ALLOWED = frozenset({ADR, PARENT, INDEX, VALIDATOR})


def git(args: list[str]) -> bytes:
    return subprocess.run(
        ["git", *args], cwd=ROOT, check=True, capture_output=True, timeout=30
    ).stdout


def decode(data: bytes) -> str:
    return data.decode("utf-8", errors="strict").replace("\r\n", "\n")


def paths(args: list[str]) -> set[str]:
    return {decode(item) for item in git(args).split(b"\0") if item}


def original(name: str) -> str:
    return decode(git(["show", f"{BASELINE}:{name}"]))


def require(source: str, values: tuple[str, ...]) -> None:
    prose = " ".join(source.split())
    for value in values:
        if value not in prose:
            raise ValueError(f"missing acceptance declaration: {value}")


def whitespace(name: str, source: str) -> None:
    if not source.endswith("\n") or any(
        line.rstrip() != line for line in source.splitlines()
    ):
        raise ValueError(f"local whitespace violation: {name}")


def block(source: str) -> tuple[str, str]:
    begin = f"<!-- {SLICE} BEGIN -->"
    end = f"<!-- {SLICE} END -->"
    if source.count(begin) != 1 or source.count(end) != 1:
        raise ValueError("expected one bounded acceptance addendum")
    start = source.index(begin)
    stop = source.index(end, start) + len(end)
    addition = source[start:stop]
    # Callers compare historical text after removing only this bounded block.
    return source[:start] + source[stop:], addition


def scope() -> None:
    changed = paths(["diff", "--name-only", "--no-renames", "-z", BASELINE, "--"])
    changed |= paths(
        ["diff", "--cached", "--name-only", "--no-renames", "-z", BASELINE, "--"]
    )
    changed |= paths(["ls-files", "--others", "--exclude-standard", "-z"])
    if changed - ALLOWED:
        unexpected = sorted(changed - ALLOWED)
        raise ValueError(f"outside documentary acceptance scope: {unexpected}")
    for name in ALLOWED:
        path = ROOT / name
        if path.is_symlink() or not path.is_file() or path.stat().st_size > 100_000:
            raise ValueError(f"missing, symlinked or oversized slice file: {name}")
    # Pin the independent security decision and privacy restrictions explicitly.
    for name in ("adrs/ADR-027.md", "adrs/ADR-020.md", "adrs/ADR-023.md"):
        if (ROOT / name).read_text(encoding="utf-8") != original(name):
            raise ValueError(f"independent ADR changed: {name}")
    pending = (ROOT / "adrs/ADR-027.md").read_text(encoding="utf-8")
    if re.findall(r"^Status: (.+)$", pending, re.M) != ["Proposed"]:
        raise ValueError("ADR-027 must remain Proposed")


def documents(contents: dict[str, str]) -> None:
    source = contents[ADR]
    if re.findall(r"^Status: (.+)$", source, re.M) != ["Accepted"]:
        raise ValueError("ADR-026 must match acceptance decision")
    if source.count("\n## Decision\n") != 1:
        raise ValueError("expected exactly one ADR decision section")
    if re.findall(r"^(?:ACCEPT|REVISE|BLOCK)_ADR_026$", source, re.M) != [
        "ACCEPT_ADR_026"
    ]:
        raise ValueError("expected one explicit ACCEPT_ADR_026 decision")
    require(
        source,
        (
            BASELINE,
            "Decision authority: repository maintainer",
            "Acceptance date: 2026-10-11.",
            "Evidence reviewed:",
            "Residual limitations:",
            "Acceptance-review document validation: pending maintainer execution.",
            "Implementation authorization: none. Live execution authorization: none.",
            "ADR-027 remains Proposed",
            "Model SRCP-1 is unchanged.",
            "Remote personal-image VTO remains unsupported.",
            "EXTENDED_WITHOUT_CONFLICT",
            "GOVERNED-EXECUTION-PUBLIC-FACADE-1",
            "GENERATIVE-MEDIA-PUBLIC-EXECUTION-MIGRATION-1",
            "GENERATIVE-MEDIA-CONSTRUCTION-ADMISSION-1",
        ),
    )
    for letter in "ABCDEFGH":
        if f"| {letter} — " not in source:
            raise ValueError(f"missing explicit acceptance question: {letter}")
    whitespace(ADR, source)

    parent = contents[PARENT]
    old_parent = original(PARENT)
    remainder, addition = block(parent)
    if remainder != old_parent + "\n\n":
        raise ValueError("ADR-014 historical text changed beyond appended addendum")
    require(
        addition,
        (
            "## 15. Addendum",
            "Status: Accepted",
            "[ADR-026](ADR-026.md)",
            "ADR-027 remains Proposed and unaccepted.",
            "ADR-020 still prohibits remote personal-image VTO.",
        ),
    )
    whitespace(PARENT, addition + "\n")

    index = contents[INDEX]
    old_index = original(INDEX)
    remainder, addition = block(index)
    # Insertion replaced one heading, adding a block followed by two newlines.
    remainder = remainder.replace(
        "\n\n\n\n### Original planning record",
        "\n\n### Original planning record",
        1,
    )
    prefix = "| [ADR-026](ADR-026.md) |"
    old_rows = [line for line in old_index.splitlines() if line.startswith(prefix)]
    new_rows = [line for line in remainder.splitlines() if line.startswith(prefix)]
    if len(old_rows) != 1 or len(new_rows) != 1:
        raise ValueError("expected one ADR-026 index registration")
    require(new_rows[0], ("Accepted 2026-10-11", "ADR-014 section 15"))
    if remainder.replace(new_rows[0], old_rows[0], 1) != old_index:
        raise ValueError("unrelated index text or ADR-027 registration changed")
    require(addition, ("ADR-027 remains Proposed", "No production implementation"))
    whitespace(INDEX, addition + "\n")


def main() -> int:
    phase = "document-only scope; independent ADR-027/020/023 preserved"
    try:
        print(f"[PHASE] {phase}", flush=True)
        scope()
        phase = "ADR-026 acceptance, ADR-014 addendum and index consistency"
        print(f"\n[PHASE] {phase}", flush=True)
        current = {
            name: (ROOT / name).read_text(encoding="utf-8")
            for name in (ADR, PARENT, INDEX)
        }
        documents(current)
        whitespace(VALIDATOR, (ROOT / VALIDATOR).read_text(encoding="utf-8"))
        phase = "staged acceptance consistency"
        print(f"\n[PHASE] {phase}", flush=True)
        staged = {name: decode(git(["show", f":{name}"])) for name in current}
        if any(staged[name] != original(name) for name in staged):
            documents(staged)
        for phase, args in (
            ("working whitespace", ["diff", "--check", BASELINE, "--"]),
            ("staged whitespace", ["diff", "--cached", "--check", BASELINE, "--"]),
        ):
            print(f"\n[PHASE] {phase}", flush=True)
            subprocess.run(["git", *args], cwd=ROOT, check=True, timeout=30)
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        print(f"FAIL: {phase}: {exc}; later phases NOT RUN")
        return 1
    print(
        f"{SLICE} LOCAL DOCUMENT CHECKS PASSED; ADR-026 ACCEPTED; "
        "ADR-027 PROPOSED; NO IMPLEMENTATION OR LIVE EXECUTION AUTHORIZED"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
