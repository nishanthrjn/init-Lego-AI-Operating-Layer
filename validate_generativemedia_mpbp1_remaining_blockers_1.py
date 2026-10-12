"""Maintainer-run documentary checks; local files/Git only, no project imports."""

import re
import subprocess
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent
BASELINE = "cb0f4fb02c9140c2e2ab1f1a12d30405725c0676"
SLICE = "GENERATIVE-MEDIA-MPBP1-REMAINING-BLOCKERS-1"
REVIEW = f"planning/{SLICE}.md"
PARENT = "planning/GENERATIVE-MEDIA-ADR-027-BLOCKER-RESOLUTION-1.md"
VALIDATOR = "validate_generativemedia_mpbp1_remaining_blockers_1.py"
ALLOWED = frozenset({REVIEW, PARENT, VALIDATOR})
STATES = (
    "RESOLUTION_DRAFT_READY",
    "STILL_BLOCKED",
    "RESOLUTION_DRAFT_READY",
    "RESOLUTION_DRAFT_READY",
    "RESOLUTION_DRAFT_READY",
)
COMMAND = (
    "uv run --locked --offline --no-sync python "
    ".\\validate_generativemedia_mpbp1_remaining_blockers_1.py\n"
    "if ($LASTEXITCODE -ne 0) { throw 'MPBP-1 remaining blocker validation failed' }"
)
METADATA = (
    f"<!-- {SLICE} CURRENT BEGIN -->\n"
    f"Current resolution record: [{SLICE}]({SLICE}.md).\n"
    "Current states: B-01 RESOLUTION_DRAFT_READY; B-02 STILL_BLOCKED; "
    "B-03 RESOLUTION_DRAFT_READY; B-04 RESOLUTION_DRAFT_READY; "
    "B-05 RESOLUTION_DRAFT_READY. No blocker is CLOSED; all approvals remain pending.\n"
    "Prior blocker-package document validation: maintainer-run LOCAL DOCUMENT "
    "CHECKS PASSED. This new remaining-blockers slice awaits maintainer validation.\n"
    "Historical baseline, states, reasoning and handoff below describe the "
    "preceding slice and are preserved unchanged.\n"
    f"<!-- {SLICE} CURRENT END -->\n"
)
SECTIONS = (
    "B-02 authoritative evidence register",
    "B-02 decision test and alternatives",
    "B-03 source and composition decision",
    "B-03 validity-margin criterion",
    "B-05 custody selection and source evidence",
    "B-05 transactions, root and recovery",
    "B-05 capacity, retention and disposition",
    "Independent disclosure and six effect facts",
    "B-01 and B-04 cross-check",
    "Current exits and maintainer handoff",
    "Final package decision",
)
SOURCES = (
    "https://docs.comfy.org/development/cloud/overview",
    "https://raw.githubusercontent.com/Comfy-Org/docs/main/openapi-cloud.yaml",
    "https://raw.githubusercontent.com/Comfy-Org/ComfyUI/master/server.py",
    "https://raw.githubusercontent.com/Comfy-Org/docs/main/openapi-v2.yaml",
    "https://docs.comfy.org/development/api-development/getting-an-api-key",
    "https://trust.comfy.org/controls",
    "https://www.comfy.org/privacy",
)


def git(args: list[str]) -> bytes:
    return subprocess.run(
        ["git", *args], cwd=ROOT, check=True, capture_output=True, timeout=30
    ).stdout


def decode(value: bytes) -> str:
    return value.decode("utf-8", errors="strict").replace("\r\n", "\n")


def paths(args: list[str]) -> set[str]:
    return {decode(item) for item in git(args).split(b"\0") if item}


def scope(changed: set[str]) -> None:
    if changed - ALLOWED:
        raise ValueError(f"outside three-file documentary scope: {sorted(changed - ALLOWED)}")


def require(source: str, values: tuple[str, ...]) -> None:
    prose = " ".join(source.split())
    for value in values:
        if value not in prose:
            raise ValueError(f"missing documentary boundary: {value}")


def whitespace(name: str, source: str) -> None:
    if not source.endswith("\n") or any(
        line.rstrip() != line for line in source.splitlines()
    ):
        raise ValueError(f"local whitespace violation: {name}")


def documents(contents: dict[str, str], original: str) -> None:
    expected_parent = original.replace(
        "Status: Proposed — NOT ACCEPTED.\n",
        "Status: Proposed — NOT ACCEPTED.\n" + METADATA,
        1,
    )
    if contents[PARENT] != expected_parent:
        raise ValueError("historical package changed beyond exact current metadata")
    source = contents[REVIEW]
    if re.findall(r"^Status: (.+)$", source, re.M) != ["Proposed — NOT ACCEPTED."]:
        raise ValueError("proposal must not be accepted")
    if re.findall(r"\bREMAINING_BLOCKER_RESOLUTION_[A-Z_]+\b", source) != [
        "REMAINING_BLOCKER_RESOLUTION_INCOMPLETE"
    ] or not source.endswith("REMAINING_BLOCKER_RESOLUTION_INCOMPLETE\n"):
        raise ValueError("expected one final incomplete decision")
    headings = [f"{number}. {title}" for number, title in enumerate(SECTIONS, 1)]
    if re.findall(r"^## (.+)$", source, re.M) != headings:
        raise ValueError("missing, duplicate or reordered sections")
    require(
        source,
        (
            f"Baseline: `{BASELINE}`.",
            "ADR-027: Proposed. Readiness: Blocked. H-01: OPEN.",
            "No blocker is CLOSED. Architecture approval is pending.",
            "Verification: NOT RUN — Awaiting user execution.",
            "No implementation or live execution authorized.",
            "Credentialed media NOT QUALIFIED; remote VTO UNSUPPORTED.",
            "SRCP-1 remains Model-only. No generic credential service approved.",
            "B-02 remains STILL_BLOCKED.",
            "No remote provider/family is selected for activation.",
            "No qualified margin -> protected send refused.",
            "No universal retention duration.",
            "Unresolved records cannot be evicted.",
            "Full capacity refuses new H.",
            "Current INTACT_LOCAL_V1 excludes power loss",
            "ADR-020 remote-VTO prohibition is preserved.",
            "Job effect is NONE because MPBP-1 submits no jobs",
            "Complete 401/403 cannot erase credential use.",
            "Crash cannot replay.",
        ),
    )
    if re.search(r"H-01\s*(?::|is|remains)?\s*CLOSED", source, re.I):
        raise ValueError("H-01 cannot be closed")
    rows = [line for line in source.splitlines() if line.startswith("| B-")]
    if len(rows) != 5:
        raise ValueError("expected five blocker rows")
    for number, (row, state) in enumerate(zip(rows, STATES, strict=True), 1):
        fields = [item.strip() for item in row.strip("|").split("|")]
        if (
            len(fields) != 4
            or fields[:2] != [f"B-{number:02}", state]
            or any(not item for item in fields)
            or f"B-{number:02}: {state}." not in source
        ):
            raise ValueError("inconsistent blocker state or missing owner/exit")
    evidence = [line for line in source.splitlines() if re.match(r"\| E\d+ \|", line)]
    if len(evidence) != len(SOURCES):
        raise ValueError("incomplete authoritative evidence register")
    for number, (row, url) in enumerate(zip(evidence, SOURCES, strict=True), 1):
        fields = [item.strip() for item in row.strip("|").split("|")]
        if (
            len(fields) != 5
            or fields[0] != f"E{number}"
            or url not in fields[1]
            or any(not item for item in fields)
        ):
            raise ValueError("missing citation, version, proposition or limitation")
    require(source, ("DOCUMENTED FACT", "SOURCE-CODE FACT", "INFERENCE", "UNKNOWN"))
    if "UNKNOWN:" not in evidence[-1] or "Fetch failed" not in evidence[-1]:
        raise ValueError("unretrieved privacy text must remain unknown")
    provider_test = source.split("## 2. B-02 decision test and alternatives\n", 1)[1]
    provider_test = provider_test.split("## 3. B-03 source and composition decision\n", 1)[0]
    for letter in "ABCDEFGHIJ":
        if len(re.findall(rf"^\| {letter} [^|]+\|", provider_test, re.M)) != 1:
            raise ValueError(f"missing provider decision test: {letter}")
    links = re.findall(r"\]\((https://[^)]+)\)", source)
    if set(links) != set(SOURCES) or any(
        urlsplit(url).hostname
        not in {
            "docs.comfy.org",
            "raw.githubusercontent.com",
            "trust.comfy.org",
            "www.comfy.org",
        }
        for url in links
    ):
        raise ValueError("unexpected external citation")
    if re.findall(r"```([^\n]*)\n(.*?)```", source, re.S) != [
        ("powershell", COMMAND + "\n")
    ]:
        raise ValueError("only the offline document validator command is allowed")
    if any(value in source for value in ("--live", "curl ", "Authorization:", "api_key=")):
        raise ValueError("live instructions or credential examples forbidden")
    for name, text in contents.items():
        whitespace(name, METADATA if name == PARENT else text)


def controls(contents: dict[str, str], original: str) -> None:
    """In-memory document fixtures only; no production tests or network."""
    documents(contents, original)
    for name, before, after in (
        (REVIEW, "ADR-027: Proposed.", "ADR-027: Accepted."),
        (REVIEW, "H-01: OPEN.", "H-01: CLOSED."),
        (REVIEW, "| B-02 | STILL_BLOCKED |", "| B-02 | RESOLUTION_DRAFT_READY |"),
        (REVIEW, "| B-05 |", "| B-03 |"),
        (REVIEW, "| Media provider-contract owner and Security |", "| |"),
        (REVIEW, SOURCES[0], "https://example.invalid/unofficial"),
        (REVIEW, "UNKNOWN: operative policy", "DOCUMENTED FACT: operative policy"),
        (REVIEW, "No generic credential service approved.", "Generic service approved."),
        (REVIEW, "No qualified margin -> protected send refused.", "Use a default margin."),
        (REVIEW, COMMAND, "curl https://example.invalid"),
        (
            REVIEW,
            "REMAINING_BLOCKER_RESOLUTION_INCOMPLETE",
            "REMAINING_BLOCKER_RESOLUTION_INCOMPLETE\nREMAINING_BLOCKER_RESOLUTION_INCOMPLETE",
        ),
        (PARENT, "## 2. B-01 proposed upstream language", "## Changed history"),
    ):
        changed = dict(contents)
        if before not in changed[name]:
            raise ValueError("negative fixture target missing")
        changed[name] = changed[name].replace(before, after, 1)
        try:
            documents(changed, original)
        except ValueError:
            continue
        raise ValueError("unsafe document fixture accepted")
    scope(set(ALLOWED))
    for name in ("src/legoai/runtime/api.py", "uv.lock", "adrs/ADR-027.md"):
        try:
            scope({name})
        except ValueError:
            continue
        raise ValueError("forbidden file scope accepted")


def main() -> int:
    phase = "three-file scope; production, dependencies and accepted ADRs unchanged"
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
                raise ValueError(f"missing, symlinked or oversized file: {name}")
            contents[name] = path.read_text(encoding="utf-8")
        original = decode(git(["show", f"{BASELINE}:{PARENT}"]))
        phase = "evidence limits, proposed decisions and historical preservation"
        print(f"\n[PHASE] {phase}", flush=True)
        documents(contents, original)
        phase = "positive and negative document fixtures"
        print(f"\n[PHASE] {phase}", flush=True)
        controls(contents, original)
        phase = "staged document consistency"
        print(f"\n[PHASE] {phase}", flush=True)
        if staged:
            staged_contents = {
                name: decode(git(["show", f":{name}"])) for name in ALLOWED
            }
            documents(staged_contents, original)
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
        "B-02 STILL BLOCKED; ADR-027 PROPOSED; H-01 OPEN; "
        "NO IMPLEMENTATION OR LIVE EXECUTION AUTHORIZED"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
