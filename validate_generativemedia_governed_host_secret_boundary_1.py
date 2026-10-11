"""Maintainer-run document/scope checks; no runtime imports or provider execution."""

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BASELINE = "5840eef3baadfada97740af51cef0630be1a7612"
DOCUMENT = "planning/GENERATIVE-MEDIA-GOVERNED-HOST-SECRET-BOUNDARY-1.md"
VALIDATOR = "validate_generativemedia_governed_host_secret_boundary_1.py"
ALLOWED = frozenset({DOCUMENT, VALIDATOR})
DECISION = "ADR_REQUIRED_BEFORE_IMPLEMENTATION"
SECTIONS = (
    "Current problem statement",
    "H-01 evidence",
    "M-01 evidence",
    "Relationship to M-04",
    "Accepted security/architecture requirements",
    "Current Model Secret-use flow",
    "Current Media credential flow",
    "Generic vs Model-specific Secret semantics",
    "Media effect-boundary matrix",
    "Alternative architecture comparison",
    "SOLID / DRY / KISS / YAGNI / SoC / LoD comparison",
    "Cross-consumer evidence",
    "Preferred architecture",
    "Exact public/private ownership proposal",
    "Secret-use sequence diagram",
    "Media operation/effect sequence diagram",
    "Migration outline",
    "Compatibility impact",
    "Required ADR status",
    "Exact next implementation slice if approved",
)
HANDOFF = (
    "uv run --locked --offline --no-sync python "
    ".\\validate_generativemedia_governed_host_secret_boundary_1.py\n"
    "if ($LASTEXITCODE -ne 0) { throw 'Generative Media boundary review validation failed' }"
)


def git(args: list[str]) -> bytes:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=True,
        capture_output=True,
        timeout=30,
    ).stdout


def git_paths(args: list[str]) -> set[str]:
    return {
        entry.decode("utf-8", errors="strict")
        for entry in git(args).split(b"\0")
        if entry
    }


def check_scope() -> None:
    # Compare both index and working tree with the reviewed parent. A staged
    # production change remains disallowed even if undone in the working tree.
    changed = git_paths(["diff", "--name-only", "--no-renames", "-z", BASELINE, "--"])
    changed |= git_paths(
        ["diff", "--cached", "--name-only", "--no-renames", "-z", BASELINE, "--"]
    )
    changed |= git_paths(["ls-files", "--others", "--exclude-standard", "-z"])
    unexpected = sorted(changed - ALLOWED)
    if unexpected:
        raise ValueError(f"changes outside two-file decision slice: {unexpected!r}")
    for name in sorted(ALLOWED):
        path = ROOT / name
        if path.is_symlink() or not path.is_file():
            raise ValueError(f"missing or symlinked slice file: {name}")
        if path.stat().st_size > 100_000:
            raise ValueError(f"slice file exceeds review bound: {name}")


def check_document(source: str) -> None:
    headings = re.findall(r"^## (.+)$", source, re.M)
    expected = [f"{index}. {title}" for index, title in enumerate(SECTIONS, 1)]
    if headings != expected:
        raise ValueError("expected all 20 review sections exactly once, in order")
    decisions = re.findall(r"^DECISION:\n    ([A-Z_]+)$", source, re.M)
    if decisions != [DECISION] or source.count("DECISION:") != 1:
        raise ValueError("expected exactly one primary decision")
    if not source.rstrip().endswith(f"DECISION:\n    {DECISION}"):
        raise ValueError("primary decision must end the document")
    statuses = re.findall(r"^Required ADR status: ([A-Z_]+)\.$", source, re.M)
    if statuses != ["NEW_ADR_REQUIRED"]:
        raise ValueError("expected explicit new-ADR gate")
    required = (
        BASELINE,
        "LOCAL VALIDATION PENDING",
        "H-01",
        "M-01",
        "M-04",
        "REUSE > EXTEND > CREATE",
        "Approval != Permission",
        "Unknown effect != no effect",
        "SecretAccessPort",
        "SecretUsePlan",
        "TenantContext",
        "Principal",
        "ADR-010",
        "ADR-020",
        "ADR-023",
        "Model",
        "ForgeAI",
        "DocuMind",
        "No production source, public API, dependency manifest or existing ADR changes.",
        "No live execution authorized.",
        "SRP",
        "OCP",
        "LSP",
        "ISP",
        "DIP",
        "GENERATIVE-MEDIA-CONSTRUCTION-ADMISSION-1",
    )
    prose = " ".join(source.split())
    for declaration in required:
        if declaration not in prose:
            raise ValueError(f"missing review declaration: {declaration}")
    for label in "ABCDEF":
        if f"| {label}:" not in source:
            raise ValueError(f"missing alternative/effect label: {label}")

    fences = re.findall(r"^```([^\n]*)\n(.*?)^```[ \t]*$", source, re.M | re.S)
    if source.count("```") != 2 * len(fences):
        raise ValueError("unbalanced or unsupported code fences")
    examples = [body.strip() for language, body in fences if language == "powershell"]
    if examples != [HANDOFF]:
        raise ValueError("only the exact offline maintainer command is allowed")
    diagrams = [body.strip() for language, body in fences if language == "mermaid"]
    if len(diagrams) != 2 or not (
        diagrams[0].startswith("sequenceDiagram\n")
        and diagrams[1].startswith("flowchart TD\n")
    ):
        raise ValueError("expected Secret-use and media-effect diagrams")
    if any(language not in {"mermaid", "powershell"} for language, _ in fences):
        raise ValueError("unexpected executable example fence")
    # These are document hygiene checks, not a shell interpreter or proof of
    # architectural correctness. Scope prevents production/API implementation.
    if re.search(r"https?://|--live\b|\b(?:curl|wget|Invoke-WebRequest)\b", source, re.I):
        raise ValueError("live endpoint or provider-command example is not allowed")
    without_handoff = source.replace(HANDOFF, "")
    if re.search(
        r"(?:^|[`>])\s*(?:uv\s+run|python(?:3)?\s|docker\s|pip\s)",
        without_handoff,
        re.M | re.I,
    ):
        raise ValueError("unexpected command outside the local validation handoff")
    for link in re.findall(r"\]\(([^)]+)\)", source):
        if not link.startswith("../"):
            raise ValueError(f"expected a repository evidence link: {link}")
        target = ((ROOT / DOCUMENT).parent / link).resolve()
        if not target.is_relative_to(ROOT) or not target.is_file():
            raise ValueError(f"missing or out-of-repository evidence link: {link}")


def check_whitespace(name: str, source: str) -> None:
    if not source.endswith("\n"):
        raise ValueError(f"missing final newline: {name}")
    if any(line.rstrip() != line for line in source.splitlines()):
        raise ValueError(f"trailing whitespace: {name}")


def main() -> int:
    phase = "two-file scope; production, public API and dependencies unchanged"
    try:
        print(f"[PHASE] {phase}", flush=True)
        check_scope()
        phase = "document structure, ownership, decision and diagrams"
        print(f"\n[PHASE] {phase}", flush=True)
        check_document((ROOT / DOCUMENT).read_text(encoding="utf-8"))
        phase = "local and staged document whitespace"
        print(f"\n[PHASE] {phase}", flush=True)
        tracked = git_paths(["ls-files", "-z", "--", *sorted(ALLOWED)])
        for name in sorted(ALLOWED):
            check_whitespace(name, (ROOT / name).read_text(encoding="utf-8"))
            if name in tracked:
                staged = git(["show", f":{name}"]).decode("utf-8", errors="strict")
                staged = staged.replace("\r\n", "\n")
                check_whitespace(f"index:{name}", staged)
                if name == DOCUMENT:
                    check_document(staged)
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
        "GENERATIVE-MEDIA-GOVERNED-HOST-SECRET-BOUNDARY-1 "
        "LOCAL DOCUMENT CHECKS PASSED; ADR REQUIRED BEFORE IMPLEMENTATION; "
        "NO LIVE EXECUTION AUTHORIZED"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
