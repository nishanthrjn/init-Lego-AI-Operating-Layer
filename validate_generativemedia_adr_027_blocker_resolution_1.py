"""Maintainer-run document invariants; local files/Git, no project imports."""

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BASELINE = "e1376135509185b9b4f91f4b23d14fc9e501a1d6"
SLICE = "GENERATIVE-MEDIA-ADR-027-BLOCKER-RESOLUTION-1"
REVIEW = f"planning/{SLICE}.md"
VALIDATOR = "validate_generativemedia_adr_027_blocker_resolution_1.py"
PROPOSALS = {
    "planning/ADR-007-MPBP-1-PROPOSED-ADDENDUM.md": (
        "6.2 item 7, 6.3, 8 and 18",
        "Strict real-time validity at H is unsupported.",
        "Every continuation MUST re-enter G",
    ),
    "planning/ADR-010-MPBP-1-PROPOSED-ADDENDUM.md": (
        "section 8.2 step 5, section 8.3 and section 23 scope",
        "One exact revision remains frozen",
        "Section 23 remains SRCP-1 only",
    ),
    "planning/ADR-023-MPBP-1-PROPOSED-CROSS-REFERENCE.md": (
        "sections 7–8 and 11–12, relationship metadata only",
        "SRCP-1 remains Model-only.",
        "Media receives no authority by analogy",
    ),
}
ALLOWED = frozenset({REVIEW, VALIDATOR, *PROPOSALS})
COMMAND = (
    "uv run --locked --offline --no-sync python "
    ".\\validate_generativemedia_adr_027_blocker_resolution_1.py\n"
    "if ($LASTEXITCODE -ne 0) { throw 'ADR-027 blocker-resolution validation failed' }"
)
SECTIONS = (
    "Governing evidence and scope",
    "B-01 proposed upstream language",
    "B-02 one client route and remaining provider evidence",
    "B-03 source, lifetime and composition",
    "B-04 ordered participation contract",
    "B-05 custody, disclosure and effects",
    "Closed failure and effect mapping",
    "Proposed numeric ceilings and unresolved parameters",
    "Public API and design-principle review",
    "Blocker exit matrix",
    "Maintainer validation and next action",
    "Final package decision",
)


def git(args: list[str]) -> bytes:
    return subprocess.run(
        ["git", *args], cwd=ROOT, check=True, capture_output=True, timeout=30
    ).stdout


def decode(data: bytes) -> str:
    return data.decode("utf-8", errors="strict").replace("\r\n", "\n")


def paths(args: list[str]) -> set[str]:
    return {decode(item) for item in git(args).split(b"\0") if item}


def scope(changed: set[str]) -> None:
    if changed - ALLOWED:
        raise ValueError(f"outside five-file document scope: {sorted(changed - ALLOWED)}")


def require(source: str, fragments: tuple[str, ...]) -> None:
    normalized = " ".join(source.split())
    for fragment in fragments:
        if fragment not in normalized:
            raise ValueError(f"missing document invariant: {fragment}")


def whitespace(name: str, source: str) -> None:
    if not source.endswith("\n") or any(
        line.rstrip() != line for line in source.splitlines()
    ):
        raise ValueError(f"new-file whitespace violation: {name}")


def documents(contents: dict[str, str]) -> None:
    source = contents[REVIEW]
    if re.findall(r"^Status: (.+)$", source, re.M) != ["Proposed — NOT ACCEPTED."]:
        raise ValueError("package must be explicitly non-accepted")
    if re.findall(r"\bBLOCKER_RESOLUTION_[A-Z_]+\b", source) != [
        "BLOCKER_RESOLUTION_INCOMPLETE"
    ] or not source.endswith("BLOCKER_RESOLUTION_INCOMPLETE\n"):
        raise ValueError("expected one final incomplete package decision")
    headings = [f"{number}. {title}" for number, title in enumerate(SECTIONS, 1)]
    if re.findall(r"^## (.+)$", source, re.M) != headings:
        raise ValueError("missing, reordered or duplicate contract section")
    require(
        source,
        (
            f"Baseline: `{BASELINE}`.",
            "ADR-027: Proposed. Readiness: Blocked. H-01: OPEN.",
            "No blocker is CLOSED. Architecture approval is pending.",
            "No implementation or live execution authorized.",
            "Credentialed media NOT QUALIFIED; remote VTO UNSUPPORTED.",
            "SRCP-1 remains Model-only. No generic credential framework approved.",
            "Verification: NOT RUN — Awaiting user execution.",
            "Sole local client candidate: legacy GET /system_stats.",
            "No supported remote provider route is selected or qualified.",
            "G = final ordered currentness gate",
            "H = protected OS credential-bearing send acceptance",
            "INTENDED must have durable custody before H.",
            "UNRESOLVED: B-03-MARGIN",
            "UNRESOLVED: B-05-CUSTODY",
            "No public API added or approved.",
            "ADR-020 decision 8 and remote personal-image VTO prohibition remain unchanged.",
        ),
    )
    if re.search(r"H-01\s*(?::|is|remains)?\s*CLOSED", source, re.I):
        raise ValueError("H-01 cannot be closed")
    rows = [line for line in source.splitlines() if line.startswith("| B-")]
    states = (
        "RESOLUTION_DRAFT_READY",
        "STILL_BLOCKED",
        "STILL_BLOCKED",
        "RESOLUTION_DRAFT_READY",
        "STILL_BLOCKED",
    )
    if len(rows) != 5:
        raise ValueError("expected five blocker exit rows")
    for number, (row, state) in enumerate(zip(rows, states, strict=True), 1):
        fields = [item.strip() for item in row.strip("|").split("|")]
        if (
            len(fields) != 7
            or fields[:2] != [f"B-{number:02}", state]
            or any(not item or item.lower() in {"tbd", "none"} for item in fields)
        ):
            raise ValueError("blocker owner/evidence/approval/proof/exit incomplete")
        if f"B-{number:02} state: {state}." not in source:
            raise ValueError("blocker section and exit matrix disagree")
    for invalidator in (
        "Principal/tenant eligibility",
        "Grant",
        "Policy",
        "Approval",
        "Provider binding publication/currentness",
        "Configuration revision",
        "Secret mapping",
        "Secret revision",
        "Secret retirement",
        "Source teardown",
        "Cancellation",
        "Execution close",
        "Deadline/expiry",
        "Required custody availability",
        "Frozen wire/recipient binding",
    ):
        matching = [
            line
            for line in source.splitlines()
            if line.startswith(f"| {invalidator} |")
        ]
        if len(matching) != 1:
            raise ValueError(f"missing participation row: {invalidator}")
        fields = [item.strip() for item in matching[0].strip("|").split("|")]
        if (
            len(fields) != 8
            or any(not item for item in fields)
            or not fields[4].startswith("Yes")
        ):
            raise ValueError("incomplete invalidator participation contract")
    # Only the maintainer's offline document-validation command is executable prose.
    fences = re.findall(r"```([^\n]*)\n(.*?)```", source, re.S)
    if fences != [("powershell", COMMAND + "\n")]:
        raise ValueError("unexpected executable or live-provider instructions")
    if "--live" in source or "curl " in source:
        raise ValueError("live-provider command forbidden")
    for name, fragments in PROPOSALS.items():
        proposal = contents[name]
        if re.findall(r"^Status: (.+)$", proposal, re.M) != [
            "Proposed — NOT ACCEPTED."
        ]:
            raise ValueError("addenda must be non-accepted proposals")
        require(
            proposal,
            (
                "Semantic owner:",
                "Affected clauses:",
                "This proposal has no present normative effect.",
                "## Exact candidate text",
                "Risk introduced:",
                "Residual limitation:",
                "Acceptance condition:",
                *fragments,
            ),
        )
        if "```" in proposal or "--live" in proposal:
            raise ValueError("proposal must not contain execution instructions")
    for name, text in contents.items():
        whitespace(name, text)


def controls(contents: dict[str, str]) -> None:
    """Positive and negative in-memory document fixtures, not production tests."""
    documents(contents)
    proposal = next(iter(PROPOSALS))
    for name, before, after in (
        (REVIEW, "ADR-027: Proposed.", "ADR-027: Accepted."),
        (REVIEW, "H-01: OPEN.", "H-01: CLOSED."),
        (REVIEW, "| B-02 |", "| B-01 |"),
        (REVIEW, "| Governance | Exact current grant/revocation |", "| | |"),
        (REVIEW, "| Media provider-contract maintainer and Security |", "| |"),
        (
            REVIEW,
            "## 8. Proposed numeric ceilings and unresolved parameters",
            "## Missing",
        ),
        (REVIEW, "SRCP-1 remains Model-only.", "SRCP-1 includes media."),
        (REVIEW, "No generic credential framework approved.", "Framework approved."),
        (REVIEW, COMMAND, "curl https://example.invalid"),
        (
            REVIEW,
            "BLOCKER_RESOLUTION_INCOMPLETE",
            "BLOCKER_RESOLUTION_INCOMPLETE\nBLOCKER_RESOLUTION_INCOMPLETE",
        ),
        (proposal, "Status: Proposed — NOT ACCEPTED.", "Status: Accepted."),
        (proposal, "Acceptance condition:", "Condition omitted:"),
    ):
        changed = dict(contents)
        if before not in changed[name]:
            raise ValueError("negative fixture target missing")
        changed[name] = changed[name].replace(before, after, 1)
        try:
            documents(changed)
        except ValueError:
            continue
        raise ValueError("unsafe document fixture was accepted")
    scope(set(ALLOWED))
    for forbidden in ("src/legoai/runtime/api.py", "uv.lock", "adrs/ADR-020.md"):
        try:
            scope({forbidden})
        except ValueError:
            continue
        raise ValueError("out-of-scope mutation fixture was accepted")


def main() -> int:
    phase = "five-file proposal scope; production, dependencies and ADRs unchanged"
    try:
        print(f"[PHASE] {phase}", flush=True)
        working = paths(["diff", "--name-only", "--no-renames", "-z", BASELINE, "--"])
        staged = paths(
            ["diff", "--cached", "--name-only", "--no-renames", "-z", BASELINE, "--"]
        )
        untracked = paths(["ls-files", "--others", "--exclude-standard", "-z"])
        scope(working | staged | untracked)
        contents = {}
        for name in sorted(ALLOWED):
            path = ROOT / name
            if path.is_symlink() or not path.is_file() or path.stat().st_size > 100_000:
                raise ValueError(f"missing, symlinked or oversized package file: {name}")
            contents[name] = path.read_text(encoding="utf-8")
        for number in (7, 10, 20, 23, 26, 27):
            name = f"adrs/ADR-{number:03}.md"
            original = decode(git(["show", f"{BASELINE}:{name}"]))
            if (ROOT / name).read_text(encoding="utf-8") != original:
                raise ValueError(f"protected ADR changed: {name}")
        phase = "non-accepted addenda, five blockers, ordering and exact package decision"
        print(f"\n[PHASE] {phase}", flush=True)
        documents(contents)
        phase = "positive and negative document fixtures"
        print(f"\n[PHASE] {phase}", flush=True)
        controls(contents)
        phase = "staged document invariants"
        print(f"\n[PHASE] {phase}", flush=True)
        if staged:
            documents({name: decode(git(["show", f":{name}"])) for name in ALLOWED})
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
        f"{SLICE} LOCAL DOCUMENT CHECKS PASSED; PACKAGE INCOMPLETE; "
        "ADR-027 PROPOSED; READINESS BLOCKED; H-01 OPEN; "
        "NO IMPLEMENTATION OR LIVE EXECUTION AUTHORIZED"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
