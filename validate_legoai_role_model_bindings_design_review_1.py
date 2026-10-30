"""Maintainer-run documentary checks; no product imports or workloads."""

from __future__ import annotations

import fnmatch
import os
from pathlib import Path
import re
import subprocess
import sys


BASE = "7da850c089df8e1e845a2205fc3309a042695a8f"
ROOT = Path(__file__).resolve().parent
PLAN = "planning/LEGOAI-ROLE-MODEL-BINDINGS-DESIGN-REVIEW-1.md"
ADR = "adrs/ADR-029.md"
ALLOWED = frozenset(
    (PLAN, ADR, "adrs/ADR-INDEX.md", Path(__file__).name)
)
LABEL = (
    "LEGOAI-ROLE-MODEL-BINDINGS-DESIGN-REVIEW-1 LOCAL DOCUMENT CHECKS PASSED; "
    "ADR-029 PROPOSED; NO PRODUCTION CHANGE; NO IMPLEMENTATION AUTHORIZED"
)


def git(*arguments: str) -> str:
    environment = {
        key: value
        for key, value in os.environ.items()
        if not key.upper().startswith("GIT_")
    }
    environment["GIT_OPTIONAL_LOCKS"] = "0"
    result = subprocess.run(
        ["git", *arguments],
        cwd=ROOT,
        env=environment,
        check=True,
        capture_output=True,
        encoding="utf-8",
        timeout=30,
    )
    return result.stdout


def names(output: str) -> set[str]:
    return {item for item in output.split("\0") if item}


def scope() -> None:
    changed = names(git("diff", "--name-only", "--no-renames", "-z", BASE, "--"))
    changed |= names(
        git("diff", "--cached", "--name-only", "--no-renames", "-z", BASE, "--")
    )
    changed |= names(git("ls-files", "--others", "--exclude-standard", "-z"))
    unexpected = changed - ALLOWED
    if unexpected:
        raise ValueError(f"Out-of-scope paths: {sorted(unexpected)}")
    for path in ALLOWED:
        if not (ROOT / path).is_file():
            raise ValueError(f"Missing deliverable: {path}")


def preservation() -> None:
    historical = names(git("ls-tree", "-r", "--name-only", "-z", BASE, "--", "adrs"))
    current = names(git("ls-files", "-z", "--", "adrs"))
    preserved_adrs = sorted(
        path
        for path in historical | current
        if fnmatch.fnmatchcase(path, "adrs/ADR-0*.md") and path != ADR
    )
    paths = ["src", "packages", "examples", "scripts", "experiments", *preserved_adrs]
    git("diff", "--quiet", BASE, "--", *paths)
    git("diff", "--cached", "--quiet", BASE, "--", *paths)


def structure() -> None:
    text = (ROOT / PLAN).read_text(encoding="utf-8")
    required = (
        *(f"F{number}" for number in range(1, 9)),
        "Option A",
        "Option B",
        "Option C",
        *(f"D{number}" for number in range(1, 7)),
        "Recommendation",
    )
    for heading in required:
        if not re.search(r"^#{1,6}\s+" + re.escape(heading) + r"\b", text, re.MULTILINE):
            raise ValueError(f"Missing planning heading: {heading}")
    if not re.search(r"^#{1,6}\s+.*Follow-up slices", text, re.MULTILINE):
        raise ValueError("Missing follow-up slices heading")
    adr = (ROOT / ADR).read_text(encoding="utf-8")
    if not re.search(r"^Status: (?:Proposed\s*|Accepted(?: — [^\r\n]*)?)$", adr, re.MULTILINE):
        raise ValueError("ADR-029 must be Proposed or Accepted")
    if "ADR-014 §14.2" not in adr:
        raise ValueError("ADR-029 must reference ADR-014 §14.2")


def citations() -> None:
    text = (ROOT / PLAN).read_text(encoding="utf-8")
    pattern = re.compile(
        r"(?P<path>(?:[A-Za-z0-9_.-]+/)+[A-Za-z0-9_.-]+)"
        r"(?:::(?P<symbol>[A-Za-z_][A-Za-z0-9_.]*)|:(?P<line>[0-9]+))"
    )
    found = list(pattern.finditer(text))
    if not found:
        raise ValueError("Planning document has no source citations")
    for match in found:
        path = (ROOT / match["path"]).resolve()
        if not path.is_relative_to(ROOT) or not path.is_file():
            raise ValueError(f"Citation file missing or outside repository: {match[0]}")
        source = path.read_text(encoding="utf-8")
        if match["line"] is not None:
            if not 1 <= int(match["line"]) <= len(source.splitlines()):
                raise ValueError(f"Citation line out of range: {match[0]}")
        else:
            symbol = match["symbol"].rsplit(".", 1)[-1]
            if not re.search(r"\b" + re.escape(symbol) + r"\b", source):
                raise ValueError(f"Citation symbol absent: {match[0]}")
    print(f"Resolved {len(found)} source citations (existence, not semantic proof).")


def whitespace() -> None:
    git("diff", "--check")
    git("diff", "--cached", "--check")
    # git diff omits untracked deliverables; inspect their whitespace as well.
    untracked = names(git("ls-files", "--others", "--exclude-standard", "-z"))
    for name in sorted(ALLOWED & untracked):
        lines = (ROOT / name).read_text(encoding="utf-8").splitlines()
        for number, line in enumerate(lines, 1):
            if line.rstrip() != line:
                raise ValueError(f"Trailing whitespace: {name}:{number}")


def main() -> int:
    phase = "initialization"
    try:
        for phase, operation in (
            ("scope", scope),
            ("preservation", preservation),
            ("document structure", structure),
            ("citations", citations),
            ("whitespace", whitespace),
        ):
            print(f"[PHASE] {phase}", flush=True)
            operation()
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(f"FAIL [{phase}]: {error}; later phases NOT RUN", file=sys.stderr)
        return 1
    print(LABEL)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
