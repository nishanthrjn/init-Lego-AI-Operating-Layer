"""Maintainer-run deferral document checks; local files/Git only."""

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BASELINE = "8efdcea1d9b55d54edf9bae59a5642acf6e1d032"
SLICE = "GENERATIVE-MEDIA-ADR-027-DEFER-1"
ADR = "adrs/ADR-027.md"
INDEX = "adrs/ADR-INDEX.md"
REVIEW = "planning/GENERATIVE-MEDIA-MPBP1-REMAINING-BLOCKERS-1.md"
VALIDATOR = "validate_generativemedia_adr_027_defer_1.py"
ALLOWED = frozenset({ADR, INDEX, REVIEW, VALIDATOR})
DECISION = "ADR_027_DEFERRED_PENDING_PROVIDER_CONTRACT"
SAFETY = "GENERATIVE-MEDIA-CREDENTIALED-PATH-FAIL-CLOSED-1"
REPLACEMENTS = (
    (
        "Status: Proposed — NOT ACCEPTED.",
        "Status: Preserved proposal evidence — non-normative; ADR-027 Deferred.",
    ),
    (
        "ADR-027: Proposed. Readiness: Blocked. H-01: OPEN.",
        "Historical review state: ADR-027: Proposed. Readiness: Blocked. H-01: OPEN.",
    ),
    (
        "Verification: NOT RUN — Awaiting user execution.",
        "Verification: Maintainer-run "
        "validate_generativemedia_mpbp1_remaining_blockers_1.py PASSED; "
        "local document checks only.",
    ),
    (
        "Expected: LOCAL DOCUMENT CHECKS PASSED;",
        "Recorded maintainer result: GENERATIVE-MEDIA-MPBP1-REMAINING-BLOCKERS-1 "
        "LOCAL DOCUMENT CHECKS PASSED;",
    ),
    (
        "Paste output before further changes.",
        "All reported phases passed, including positive/negative fixtures "
        "and working/staged checks.",
    ),
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
        raise ValueError(f"outside deferral document scope: {sorted(changed - ALLOWED)}")


def require(source: str, fragments: tuple[str, ...]) -> None:
    normalized = " ".join(source.split())
    for fragment in fragments:
        if fragment not in normalized:
            raise ValueError(f"missing deferral evidence: {fragment}")


def whitespace(name: str, source: str) -> None:
    if not source.endswith("\n") or any(
        line.rstrip() != line for line in source.splitlines()
    ):
        raise ValueError(f"whitespace violation: {name}")


def block(source: str) -> tuple[str, str]:
    begin = f"<!-- {SLICE} BEGIN -->\n"
    end = f"<!-- {SLICE} END -->\n"
    if source.count(begin) != 1 or source.count(end) != 1:
        raise ValueError("expected one bounded current-status block")
    start = source.index(begin)
    stop = source.index(end, start) + len(end)
    return source[:start] + source[stop:], source[start:stop]


def documents(contents: dict[str, str], originals: dict[str, str]) -> None:
    adr = contents[ADR]
    if re.findall(r"^Status: (.+)$", adr, re.M) != ["Deferred"]:
        raise ValueError("ADR-027 must be Deferred")
    remainder, current = block(adr)
    expected = originals[ADR].replace("Status: Proposed\n", "Status: Deferred\n", 1)
    expected = expected.replace("\nReadiness: ", "\nHistorical readiness: ", 1)
    if remainder != expected:
        raise ValueError("ADR-027 historical reasoning changed")
    if current.count(DECISION) != 1:
        raise ValueError("expected one deferral decision")
    require(
        current,
        (
            f"Deferral decision: {DECISION}",
            "explicit repository maintainer instruction, 2026-10-12",
            "ADR-INDEX section 14, item 6",
            "B-02 remains STILL_BLOCKED",
            "B-01, B-03, B-04 and B-05 are preserved proposed resolution drafts",
            "non-normative and not implementation authority",
            "Reopen trigger:",
            "at least one concrete real provider/deployment",
            "credential issuer/account identity, intended recipient",
            "supported authentication mechanism",
            "exact provider-control operation and method/path",
            "observational semantics, bounded request/response contract",
            "required metadata/disclosure behavior",
            "Insufficient triggers:",
            "a 200 response, experimental bearer acceptance, a working SDK",
            "supported remote credentialed provider operation is NOT ESTABLISHED",
            "Comfy Cloud is not selected",
            "H-01 OPEN",
            "unsupported/unqualified credential paths still exist in implementation",
            "Credentialed media remains unsupported/unqualified",
            "remote VTO remains unsupported",
            "local ComfyUI text-to-image, local image transfer",
            "local VTO deterministic implementation",
            "public governed execution migration, M-01 CLOSED, M-04 CLOSED",
            "explicit secret-free diagnostics where supported",
            f"{SAFETY} requires separate implementation authorization",
            "environment credential lookup, Secret/raw credential resolution",
            "bearer material acquisition, authenticated transport construction",
            "credentialed provider send",
            "No implementation authorization is granted here",
            "return the main development stream to ForgeAI",
            "until the reopen trigger is satisfied",
            "No security, credential, provider or live qualification follows",
        ),
    )
    if re.search(r"H-01\s*(?::|is|remains)?\s*CLOSED", current, re.I):
        raise ValueError("H-01 must remain open")
    whitespace(ADR, current)

    prefix = "| [ADR-027](ADR-027.md) |"
    index = contents[INDEX]
    rows = [line for line in index.splitlines() if line.startswith(prefix)]
    old_rows = [line for line in originals[INDEX].splitlines() if line.startswith(prefix)]
    if len(rows) != 1 or len(old_rows) != 1:
        raise ValueError("one ADR-027 index entry required")
    if index.replace(rows[0], old_rows[0], 1) != originals[INDEX]:
        raise ValueError("unrelated index history changed")
    if rows[0].split("|")[:5] != old_rows[0].split("|")[:5]:
        raise ValueError("ADR identity/dependencies changed")
    require(
        rows[0],
        (
            "Deferred 2026-10-12 by explicit maintainer decision",
            "Reopen only on authoritative concrete provider/deployment evidence",
            "B-02 STILL_BLOCKED",
            "B-01/B-03/B-04/B-05 preserved non-normative proposals",
            "H-01 OPEN; M-01 and M-04 CLOSED",
            "no implementation or live authority",
        ),
    )
    # Preserve historical Markdown hard breaks elsewhere in the index.
    whitespace(INDEX, rows[0] + "\n")

    remainder, current_review = block(contents[REVIEW])
    expected_review = originals[REVIEW]
    for old, new in REPLACEMENTS:
        if old not in expected_review:
            raise ValueError("baseline evidence wording differs")
        expected_review = expected_review.replace(old, new, 1)
    if remainder != expected_review:
        raise ValueError("research changed beyond disposition/evidence metadata")
    require(
        current_review,
        (
            "ADR-027 / MPBP-1 Deferred by explicit maintainer decision",
            "B-02 remains STILL_BLOCKED",
            "B-01/B-03/B-04/B-05 remain preserved proposed resolution drafts",
            "H-01 OPEN; M-01 CLOSED; M-04 CLOSED",
            SAFETY,
            "return to ForgeAI",
            "No implementation or live execution authorized",
        ),
    )
    require(
        remainder,
        (
            "GENERATIVE-MEDIA-MPBP1-REMAINING-BLOCKERS-1 "
            "LOCAL DOCUMENT CHECKS PASSED; PACKAGE INCOMPLETE; B-02 STILL BLOCKED; "
            "ADR-027 PROPOSED; H-01 OPEN; NO IMPLEMENTATION OR LIVE EXECUTION AUTHORIZED.",
            REPLACEMENTS[2][1],
        ),
    )
    if "NOT RUN" in remainder or "Paste output before further changes" in remainder:
        raise ValueError("completed validation still described as pending")
    whitespace(REVIEW, contents[REVIEW])
    whitespace(VALIDATOR, contents[VALIDATOR])


def controls(contents: dict[str, str], originals: dict[str, str]) -> None:
    """Positive and negative in-memory document fixtures only."""
    documents(contents, originals)
    for name, old, new in (
        (ADR, "Status: Deferred", "Status: Accepted"),
        (ADR, "H-01 OPEN", "H-01 CLOSED"),
        (ADR, "Reopen trigger:", "Trigger omitted:"),
        (ADR, "at least one concrete real provider/deployment", "future desire"),
        (ADR, SAFETY, "UNRELATED-SLICE"),
        (ADR, "## Context", "## Rewritten history"),
        (INDEX, "Deferred 2026-10-12", "Accepted 2026-10-12"),
        (REVIEW, REPLACEMENTS[2][1], REPLACEMENTS[2][0]),
        (REVIEW, "PACKAGE INCOMPLETE; B-02 STILL BLOCKED;", "PACKAGE READY;"),
        (REVIEW, "## 4. B-03 validity-margin criterion", "## Changed research"),
    ):
        changed = dict(contents)
        if old not in changed[name]:
            raise ValueError("negative fixture target missing")
        changed[name] = changed[name].replace(old, new, 1)
        try:
            documents(changed, originals)
        except ValueError:
            continue
        raise ValueError("unsafe deferral fixture accepted")
    scope(set(ALLOWED))
    for name in ("adrs/ADR-020.md", "src/legoai/runtime/api.py", "uv.lock"):
        try:
            scope({name})
        except ValueError:
            continue
        raise ValueError("out-of-scope mutation fixture accepted")


def main() -> int:
    phase = "four-file deferral scope; accepted ADRs, production and dependencies unchanged"
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
                raise ValueError(f"missing, symlinked or oversized document: {name}")
            contents[name] = path.read_text(encoding="utf-8")
        originals = {
            name: decode(git(["show", f"{BASELINE}:{name}"]))
            for name in (ADR, INDEX, REVIEW)
        }
        for number in (7, 10, 20, 23, 26):
            name = f"adrs/ADR-{number:03}.md"
            original = decode(git(["show", f"{BASELINE}:{name}"]))
            if (ROOT / name).read_text(encoding="utf-8") != original:
                raise ValueError(f"protected accepted ADR changed: {name}")
            if number == 26 and "Status: Accepted\n" not in original:
                raise ValueError("ADR-026 must remain Accepted")
        phase = "deferral trigger, preserved proposals and completed prior validation"
        print(f"\n[PHASE] {phase}", flush=True)
        documents(contents, originals)
        phase = "positive and negative documentary controls"
        print(f"\n[PHASE] {phase}", flush=True)
        controls(contents, originals)
        phase = "staged disposition consistency"
        print(f"\n[PHASE] {phase}", flush=True)
        if staged:
            documents(
                {name: decode(git(["show", f":{name}"])) for name in ALLOWED}, originals
            )
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
        f"{SLICE} LOCAL DOCUMENT CHECKS PASSED; ADR-027 DEFERRED; "
        "B-02 STILL BLOCKED; H-01 OPEN; NO IMPLEMENTATION OR LIVE EXECUTION AUTHORIZED"
    )
    print(DECISION)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
