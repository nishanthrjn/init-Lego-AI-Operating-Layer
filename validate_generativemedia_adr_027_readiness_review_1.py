"""Maintainer-run document checks; local files/Git only, no project imports."""

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BASELINE = "5dd89f66cc1207ca22c8a9704a002c4d4f9ab67c"
SLICE = "GENERATIVE-MEDIA-ADR-027-READINESS-REVIEW-1"
ADR = "adrs/ADR-027.md"
INDEX = "adrs/ADR-INDEX.md"
REVIEW = f"planning/{SLICE}.md"
VALIDATOR = "validate_generativemedia_adr_027_readiness_review_1.py"
ALLOWED = frozenset({ADR, INDEX, REVIEW, VALIDATOR})
METADATA = (
    "Readiness: Blocked — ADR_027_BLOCKED, reviewed 2026-10-12; "
    "five architecture blockers remain.\n"
    f"Readiness record: [{SLICE}](../planning/{SLICE}.md).\n"
    "Current prerequisite snapshot: ADR-026 Accepted; public facade and media "
    "migration locally qualified; M-01 and M-04 CLOSED; H-01 OPEN. "
    "Historical context below is unchanged.\n"
    "Readiness validation: NOT RUN — Awaiting user execution. "
    "No acceptance, implementation or live execution authorized.\n"
)
HEADINGS = (
    "Current H-01 call chain",
    "ADR-027 proposed profile",
    "Actual probe semantics",
    "ADR-007 currentness analysis",
    "ADR-010 compatibility",
    "ADR-023 relationship",
    "Purpose and recipient binding",
    "Material lifetime and source",
    "Disclosure separation",
    "Retry and effect semantics",
    "Invalidation and revocation ordering",
    "Evidence record",
    "Public API impact",
    "SOLID, KISS, YAGNI and ownership review",
    "Blocker matrix",
    "Exact readiness decision",
    "Next step and maintainer handoff",
)


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


def scope_paths(changed: set[str]) -> None:
    if changed - ALLOWED:
        raise ValueError(f"outside document-only scope: {sorted(changed - ALLOWED)}")


def whitespace(name: str, source: str) -> None:
    if not source.endswith("\n") or any(
        line.rstrip() != line for line in source.splitlines()
    ):
        raise ValueError(f"local whitespace violation: {name}")


def review(source: str) -> None:
    decisions = re.findall(
        r"\bADR_027_(?:READY_FOR_DECISION|BLOCKED|REVISION_REQUIRED)\b", source
    )
    if decisions != ["ADR_027_BLOCKED"]:
        raise ValueError("expected exactly one blocked readiness decision")
    expected = [f"{number}. {title}" for number, title in enumerate(HEADINGS, 1)]
    if re.findall(r"^## (.+)$", source, re.M) != expected:
        raise ValueError("missing, duplicate or reordered review sections")
    for declaration in (
        f"Review baseline: `{BASELINE}`.",
        "Readiness decision: ADR_027_BLOCKED",
        "ADR-027 status: Proposed; MPBP-1 readiness: Blocked.",
        "H-01: OPEN. M-01: CLOSED. M-04: CLOSED.",
        "Verification: NOT RUN — Awaiting user execution.",
        "No acceptance, implementation or live execution authorized.",
        "Credentialed media NOT QUALIFIED; remote VTO UNSUPPORTED.",
    ):
        if declaration not in source:
            raise ValueError(f"missing review declaration: {declaration}")
    if re.search(r"H-01\s*(?::|is|remains)?\s*CLOSED", source, re.I):
        raise ValueError("H-01 must not be marked closed")
    rows = [line for line in source.splitlines() if line.startswith("| B-")]
    if len(rows) != 5:
        raise ValueError("expected exactly five blocker rows")
    for number, row in enumerate(rows, 1):
        fields = [field.strip() for field in row.strip("|").split("|")]
        if (
            len(fields) != 5
            or fields[0] != f"B-{number:02}"
            or any(not field or field.lower() in {"tbd", "none"} for field in fields)
            or "ADR-" not in fields[2]
        ):
            raise ValueError("incomplete or duplicate blocker fields")
    for boundary in (
        "No retry, fallback Secret/provider",
        "No Model disclosure class",
        "durable INTENDED custody before H",
        "physical zeroization",
        "not additional readiness blockers",
        "No new generic SecretService",
    ):
        if boundary not in source:
            raise ValueError(f"missing explicit boundary: {boundary}")


def documents(contents: dict[str, str], old_adr: str, old_index: str) -> None:
    adr = contents[ADR]
    if re.findall(r"^Status: (.+)$", adr, re.M) != ["Proposed"]:
        raise ValueError("ADR-027 must remain Proposed")
    if adr != old_adr.replace("Status: Proposed\n", "Status: Proposed\n" + METADATA, 1):
        raise ValueError("ADR-027 changed outside exact readiness metadata")
    index = contents[INDEX]
    prefix = "| [ADR-027](ADR-027.md) |"
    old_rows = [line for line in old_index.splitlines() if line.startswith(prefix)]
    rows = [line for line in index.splitlines() if line.startswith(prefix)]
    if len(rows) != 1 or len(old_rows) != 1:
        raise ValueError("expected one ADR-027 index entry")
    if index.replace(rows[0], old_rows[0], 1) != old_index:
        raise ValueError("unrelated index history or acceptance changed")
    if rows[0].split("|")[:4] != old_rows[0].split("|")[:4]:
        raise ValueError("ADR identity, title or priority changed")
    for value in (
        "ADR-026 Accepted, integration locally qualified",
        "Proposed; readiness Blocked (2026-10-12)",
        "H-01 OPEN; M-01 and M-04 CLOSED",
        "Five blockers B-01–B-05",
        f"../planning/{SLICE}.md",
        "No acceptance or implementation authority",
    ):
        if value not in rows[0]:
            raise ValueError(f"inconsistent index metadata: {value}")
    review(contents[REVIEW])
    for name, source in contents.items():
        # The unchanged index contains historical Markdown hard breaks.
        # Its exact baseline preservation is enforced above; check our row only.
        whitespace(name, rows[0] + "\n" if name == INDEX else source)


def controls(contents: dict[str, str], old_adr: str, old_index: str) -> None:
    """Pure in-memory positive/negative document fixtures; no runtime checks."""
    documents(contents, old_adr, old_index)
    for name, before, after in (
        (ADR, "Status: Proposed", "Status: Accepted"),
        (ADR, "## Context", "## Altered context"),
        (INDEX, "Proposed; readiness Blocked", "Accepted; readiness Blocked"),
        (
            INDEX,
            "No acceptance or implementation authority |\n",
            "No acceptance or implementation authority | \n",
        ),
        (INDEX, "# Lego AI Operating Layer", "#  Lego AI Operating Layer"),
        (REVIEW, "ADR_027_BLOCKED", "ADR_027_READY_FOR_DECISION"),
        (REVIEW, "H-01: OPEN", "H-01: CLOSED"),
        (REVIEW, "## 8. Material lifetime and source", "## Missing"),
        (REVIEW, "| B-02 |", "| B-01 |"),
        (
            REVIEW,
            "Architecture/Runtime maintainer and Security/Secret Access maintainer",
            "",
        ),
    ):
        altered = dict(contents)
        if before not in altered[name]:
            raise ValueError("invalid negative fixture")
        altered[name] = altered[name].replace(before, after, 1)
        try:
            documents(altered, old_adr, old_index)
        except ValueError:
            continue
        raise ValueError("negative document control was accepted")
    try:
        review(contents[REVIEW] + "\nADR_027_BLOCKED\n")
    except ValueError:
        pass
    else:
        raise ValueError("duplicate decision control was accepted")
    scope_paths(set(ALLOWED))
    try:
        scope_paths({"src/legoai/runtime/api.py"})
    except ValueError:
        pass
    else:
        raise ValueError("production mutation control was accepted")


def main() -> int:
    phase = "four-file documentary scope; accepted ADRs and production preserved"
    try:
        print(f"[PHASE] {phase}", flush=True)
        working = paths(["diff", "--name-only", "--no-renames", "-z", BASELINE, "--"])
        staged = paths(
            ["diff", "--cached", "--name-only", "--no-renames", "-z", BASELINE, "--"]
        )
        untracked = paths(["ls-files", "--others", "--exclude-standard", "-z"])
        scope_paths(working | staged | untracked)
        contents = {}
        for name in sorted(ALLOWED):
            path = ROOT / name
            if path.is_symlink() or not path.is_file() or path.stat().st_size > 100_000:
                raise ValueError(f"missing, symlinked or oversized slice file: {name}")
            contents[name] = path.read_text(encoding="utf-8")
        for number in (7, 10, 14, 20, 23, 24, 26):
            name = f"adrs/ADR-{number:03}.md"
            if (ROOT / name).read_text(encoding="utf-8") != original(name):
                raise ValueError(f"protected accepted ADR changed: {name}")
        phase = "readiness/status, historical preservation and complete blockers"
        print(f"\n[PHASE] {phase}", flush=True)
        old_adr, old_index = original(ADR), original(INDEX)
        documents(contents, old_adr, old_index)
        phase = "positive and negative document controls"
        print(f"\n[PHASE] {phase}", flush=True)
        controls(contents, old_adr, old_index)
        phase = "staged slice consistency"
        print(f"\n[PHASE] {phase}", flush=True)
        if staged:
            staged_contents = {
                name: decode(git(["show", f":{name}"])) for name in ALLOWED
            }
            # Validate each snapshot independently. A committed document slice
            # can remain valid while its validator correction is still unstaged.
            documents(staged_contents, old_adr, old_index)
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
        f"{SLICE} LOCAL DOCUMENT CHECKS PASSED; ADR-027 PROPOSED; "
        "READINESS BLOCKED; H-01 OPEN; NO IMPLEMENTATION OR LIVE EXECUTION AUTHORIZED"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
