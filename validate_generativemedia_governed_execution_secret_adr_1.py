"""Maintainer-run ADR document/scope checks; no runtime or external execution."""

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BASELINE = "c7cf5f68e029a596077c4a47c9bfea6179c6747c"
SLICE = "GENERATIVE-MEDIA-GOVERNED-EXECUTION-SECRET-ADR-1"
INDEX = "adrs/ADR-INDEX.md"
VALIDATOR = "validate_generativemedia_governed_execution_secret_adr_1.py"
ADRS = {
    "adrs/ADR-026.md": "Public governed execution composition boundary",
    "adrs/ADR-027.md": "Generative Media purpose-bound probe credential profile",
}
ALLOWED = frozenset({*ADRS, INDEX, VALIDATOR})
DEPENDENCIES = (2, 5, 7, 8, 9, 10, 14, 15, 20, 23, 24)
RELATIONSHIPS = (
    "PRESERVED",
    "EXTENDED_WITHOUT_CONFLICT",
    "REQUIRES_ADDENDUM",
    "SUPERSEDED_IN_PART",
    "NOT_APPLICABLE",
)
SECTIONS = (
    "Context",
    "Decision question",
    "Decision drivers",
    "Constraints",
    "Considered alternatives",
    "Evidence",
    "Decision",
    "Consequences",
    "Migration / reversibility",
    "Security impact",
    "Resource impact",
    "Conformance impact",
    "Follow-up decisions and implementation gates",
    "Acceptance record",
)


def git(args: list[str]) -> bytes:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=True,
        capture_output=True,
        timeout=30,
    ).stdout


def decoded(data: bytes) -> str:
    return data.decode("utf-8", errors="strict").replace("\r\n", "\n")


def paths(args: list[str]) -> set[str]:
    return {decoded(item) for item in git(args).split(b"\0") if item}


def check_scope() -> None:
    changed = paths(["diff", "--name-only", "--no-renames", "-z", BASELINE, "--"])
    changed |= paths(
        ["diff", "--cached", "--name-only", "--no-renames", "-z", BASELINE, "--"]
    )
    changed |= paths(["ls-files", "--others", "--exclude-standard", "-z"])
    unexpected = sorted(changed - ALLOWED)
    if unexpected:
        raise ValueError(f"changes outside ADR-only slice: {unexpected!r}")
    for name in sorted(ALLOWED):
        path = ROOT / name
        if path.is_symlink() or not path.is_file():
            raise ValueError(f"missing or symlinked slice file: {name}")
        if path.stat().st_size > 100_000:
            raise ValueError(f"slice file exceeds review bound: {name}")

    previous = paths(["ls-tree", "-r", "--name-only", "-z", BASELINE, "--", "adrs"])
    allocated = {
        int(match.group(1))
        for name in previous
        if (match := re.match(r"adrs/ADR-(\d{3})(?:[-.]|$)", name))
    }
    if max(allocated) != 25 or {26, 27} & allocated:
        raise ValueError("baseline allocation is not the reviewed ADR-001..025 set")
    found: dict[int, str] = {}
    for path in (ROOT / "adrs").glob("ADR-*.md"):
        match = re.match(r"ADR-(\d{3})(?:[-.]|$)", path.name)
        if match is None:
            continue
        number = int(match.group(1))
        if number in found:
            raise ValueError(f"duplicate ADR number: {number}")
        found[number] = path.relative_to(ROOT).as_posix()
    added = {name for number, name in found.items() if number not in allocated}
    if added != set(ADRS):
        raise ValueError("expected exactly two new ADR files: ADR-026 and ADR-027")


def require(source: str, declarations: tuple[str, ...]) -> None:
    prose = " ".join(source.split())
    for declaration in declarations:
        if declaration not in prose:
            raise ValueError(f"missing review declaration: {declaration}")


def check_document(name: str, source: str) -> None:
    identity = Path(name).stem
    if not source.startswith(f"# {identity} — {ADRS[name]}\n"):
        raise ValueError(f"wrong ADR title/identity: {name}")
    if re.findall(r"^Status: (.+)$", source, re.M) != ["Proposed"]:
        raise ValueError(f"ADR must remain Proposed: {name}")
    if re.findall(r"^## (.+)$", source, re.M) != list(SECTIONS):
        raise ValueError(f"expected template sections with one Decision: {name}")
    require(
        source,
        (
            BASELINE,
            "Pending maintainer decision. Recommendation: Option A.",
            "Decision-maker: not recorded. Acceptance date: not recorded.",
            "No production implementation authorized.",
            "No live execution authorized.",
            "Remote personal-image VTO remains unsupported.",
            "Model SRCP-1 is unchanged",
            "No public raw Secret/material callback approved.",
            "No universal generic capability host approved.",
            "GENERATIVE-MEDIA-CONSTRUCTION-ADMISSION-1",
            "Blocked amendment scope",
            "SRP",
            "OCP",
            "LSP",
            "ISP",
            "DIP",
            "DRY",
            "KISS",
            "YAGNI",
            "SoC",
            "Law of Demeter",
        ),
    )
    for number in DEPENDENCIES:
        identity = f"ADR-{number:03d}"
        prefix = f"| [{identity}]({identity}.md) | "
        rows = [line for line in source.splitlines() if line.startswith(prefix)]
        if len(rows) != 1 or rows[0].split(" | ")[1] not in RELATIONSHIPS:
            raise ValueError(f"missing/invalid dependency classification: {identity}")
    if name.endswith("027.md"):
        require(
            source,
            (
                "Initial implementation scope: provider-control/probe only.",
                "Raw env lookup is not permission. SecretRef alone is not permission.",
                "MPBP-1",
                "Late use is detected, not prevented.",
                "remote source-image upload, remote garment upload and remote VTO job submission",
            ),
        )
    fences = re.findall(r"^```([^\n]*)\n(.*?)^```[ \t]*$", source, re.M | re.S)
    if source.count("```") != len(fences) * 2:
        raise ValueError("unbalanced document fences")
    if any(language != "mermaid" for language, _ in fences):
        raise ValueError("only static diagrams are allowed; no executable examples")
    if re.search(
        r"https?://|--live\b|\b(?:curl|wget|Invoke-WebRequest)\b|"
        r"(?:^|[`>])\s*(?:uv\s+run|python(?:3)?\s|docker\s|pip\s)",
        source,
        re.M | re.I,
    ):
        raise ValueError("live endpoint or executable instruction in ADR")
    for link in re.findall(r"\]\(([^)]+)\)", source):
        target = ((ROOT / name).parent / link).resolve()
        if not target.is_relative_to(ROOT) or not target.is_file():
            raise ValueError(f"missing or external evidence link: {link}")


def check_index(source: str, baseline: str) -> None:
    begin = f"<!-- {SLICE} BEGIN -->\n"
    end = f"<!-- {SLICE} END -->\n\n"
    if source.count(begin) != 1 or source.count(end) != 1:
        raise ValueError("expected one bounded index registration addendum")
    start = source.index(begin)
    stop = source.index(end, start) + len(end)
    block = source[start:stop]
    if source[:start] + source[stop:] != baseline:
        raise ValueError("unrelated index content/status/history changed")
    for name, title in ADRS.items():
        identity = Path(name).stem
        prefix = f"| [{identity}]({identity}.md) | {title} | C / P2 / 2 | "
        rows = [line for line in block.splitlines() if line.startswith(prefix)]
        if len(rows) != 1 or " | Proposed." not in rows[0]:
            raise ValueError(f"missing Proposed index registration: {identity}")
    require(block, ("M-01", "H-01", "Blocked", "No live execution authorized."))
    check_whitespace(INDEX, block)


def check_whitespace(name: str, source: str) -> None:
    if not source.endswith("\n"):
        raise ValueError(f"missing final newline: {name}")
    if any(line.rstrip() != line for line in source.splitlines()):
        raise ValueError(f"trailing whitespace: {name}")


def main() -> int:
    phase = "four-file ADR scope; production, APIs and dependencies unchanged"
    try:
        print(f"[PHASE] {phase}", flush=True)
        check_scope()
        phase = "two unique Proposed ADRs; dependencies and restricted decisions"
        print(f"\n[PHASE] {phase}", flush=True)
        for name in ADRS:
            check_document(name, (ROOT / name).read_text(encoding="utf-8"))
        phase = "index registration; unrelated history preserved"
        print(f"\n[PHASE] {phase}", flush=True)
        old_index = decoded(git(["show", f"{BASELINE}:{INDEX}"]))
        check_index((ROOT / INDEX).read_text(encoding="utf-8"), old_index)
        phase = "local and staged document invariants and whitespace"
        print(f"\n[PHASE] {phase}", flush=True)
        tracked = paths(["ls-files", "-z", "--", *sorted(ALLOWED)])
        for name in sorted(ALLOWED):
            if name != INDEX:
                check_whitespace(name, (ROOT / name).read_text(encoding="utf-8"))
            if name in tracked:
                staged = decoded(git(["show", f":{name}"]))
                if name == INDEX:
                    if staged != old_index:
                        check_index(staged, old_index)
                else:
                    check_whitespace(f"index:{name}", staged)
                    if name in ADRS:
                        check_document(name, staged)
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
        f"{SLICE} LOCAL DOCUMENT CHECKS PASSED; ADR-026 AND ADR-027 PROPOSED; "
        "ARCHITECTURE APPROVAL PENDING; NO IMPLEMENTATION OR LIVE EXECUTION AUTHORIZED"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
