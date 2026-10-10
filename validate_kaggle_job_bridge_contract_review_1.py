"""Maintainer-run local document checks; no service clients or test execution."""

import re
import subprocess
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent
BASELINE = "a71461fe1a3cbc94b9da3fc7d6556684e36090e6"
DOCUMENT = "planning/KAGGLE-JOB-BRIDGE-CONTRACT-REVIEW-1.md"
VALIDATOR = "validate_kaggle_job_bridge_contract_review_1.py"
ALLOWED = frozenset({DOCUMENT, VALIDATOR})
DECISION = "CONTRACT_BLOCKED_SECURITY_GAP"
SECTIONS = (
    "Executive decision",
    "Evidence and selected stable release",
    "Stable versus development capability matrix",
    "Tagged call-chain analysis",
    "Submission acknowledgement",
    "Status identity and output identity",
    "File inventory before download",
    "Bounded download analysis",
    "Log-free retrieval analysis",
    "Retries, resume and observation budgets",
    "Push effects and local custody",
    "Resource, version, session and cancellation",
    "Private-scope verification and unique resources",
    "Authentication contract and recommendation",
    "Zero-cost and service-use assessment",
    "Privacy evidence and existing governance minimum",
    "Request and response identity acceptance",
    "Release blockers and exact next decision",
    "Sources and retrieval ledger",
    "Maintainer validation handoff",
)


def git_paths(args: list[str]) -> set[str]:
    result = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=True,
        capture_output=True,
        timeout=30,
    )
    return {
        entry.decode("utf-8", errors="strict")
        for entry in result.stdout.split(b"\0")
        if entry
    }


def check_scope() -> None:
    changed = git_paths(["diff", "--name-only", "--no-renames", "-z", BASELINE, "--"])
    changed |= git_paths(
        ["diff", "--cached", "--name-only", "--no-renames", "-z", BASELINE, "--"]
    )
    changed |= git_paths(["ls-files", "--others", "--exclude-standard", "-z"])
    unexpected = sorted(changed - ALLOWED)
    if unexpected:
        raise ValueError(f"changes outside documentation slice: {unexpected!r}")
    for name in ALLOWED:
        path = ROOT / name
        if path.is_symlink() or not path.is_file():
            raise ValueError(f"missing or symlinked slice file: {name}")
        if path.stat().st_size > 100_000:
            raise ValueError(f"slice file exceeds review bound: {name}")


def check_document() -> None:
    source = (ROOT / DOCUMENT).read_text(encoding="utf-8")
    for index, title in enumerate(SECTIONS, 1):
        if source.count(f"## {index}. {title}\n") != 1:
            raise ValueError(f"required section missing or repeated: {title}")
    if re.findall(r"^DECISION:\s*\n    ([A-Z_]+)$", source, re.M) != [DECISION]:
        raise ValueError("expected one explicit final decision")
    if not source.rstrip().endswith(f"DECISION:\n    {DECISION}"):
        raise ValueError("decision must end the document")
    required = (
        BASELINE,
        "2026-10-11",
        "kaggle==2.2.4",
        "kagglesdk==0.1.37",
        "f0afa32699d28c97f82691728ada3ed8c16c5abf",
        "ae99c895ac3d5cfb80436be8e426c0bc658c5892",
        "RELEASED",
        "UNRELEASED",
        "ABSENT",
        "UNKNOWN",
        "No live command is authorized.",
        "No repository disclosure is authorized.",
        "No production code or dependency manifest changes.",
        "No synthetic prototype implementation.",
        "No public endpoint or tunnel instructions.",
        "No new Core or job abstraction.",
        "SUBMISSION_UNCERTAIN",
        "version_label",
        "response_processor",
        "8192",
        "SUPPORTED_BY_TEXT",
        "NOT_SUPPORTED_BY_TEXT",
        "AMBIGUOUS",
        "ZERO_COST_REQUIREMENT_VIOLATED",
    )
    prose = " ".join(source.split())
    for declaration in required:
        if declaration not in prose:
            raise ValueError(f"missing review declaration: {declaration}")
    fences = re.findall(r"^```([^\n]*)\n(.*?)^```\s*$", source, re.M | re.S)
    handoff = (
        "uv run --locked --offline --no-sync python "
        ".\\validate_kaggle_job_bridge_contract_review_1.py\n"
        "if ($LASTEXITCODE -ne 0) { throw 'Kaggle job bridge contract review validation failed' }"
    )
    examples = [body.strip() for language, body in fences if language == "powershell"]
    if examples != [handoff]:
        raise ValueError("only the exact local maintainer command is allowed")
    if any(language not in {"mermaid", "powershell"} for language, _ in fences):
        raise ValueError("unexpected executable example fence")
    if sum(language == "mermaid" for language, _ in fences) != 2:
        raise ValueError("expected two lifecycle/identity diagrams")
    for url in re.findall(r"https?://[^\s<>\])`]+", source):
        parts = urlsplit(url)
        official = (
            parts.scheme == "https"
            and not parts.username
            and not parts.password
            and not parts.query
            and parts.port is None
            and (
                (parts.netloc == "github.com" and parts.path.startswith("/Kaggle/"))
                or (
                    parts.netloc == "pypi.org"
                    and parts.path.startswith(("/project/kaggle/", "/project/kagglesdk/"))
                )
                or (
                    parts.netloc == "www.kaggle.com"
                    and parts.path
                    in {
                        "/docs/efficient-gpu-usage",
                        "/product-announcements/735239",
                        "/terms",
                        "/aup",
                        "/privacy",
                    }
                )
                or (
                    parts.netloc == "requests.readthedocs.io"
                    and parts.path.startswith("/en/latest/_modules/requests/")
                )
            )
        )
        if not official:
            raise ValueError("non-allowlisted documentation URL or service endpoint")


def check_local_whitespace() -> None:
    # Git does not check untracked files; cover both new files explicitly too.
    for name in ALLOWED:
        source = (ROOT / name).read_text(encoding="utf-8")
        if not source.endswith("\n"):
            raise ValueError(f"missing final newline: {name}")
        if any(line.rstrip() != line for line in source.splitlines()):
            raise ValueError(f"trailing whitespace: {name}")


def main() -> int:
    phase = "two-file scope; product and dependency boundary"
    try:
        print(f"[PHASE] {phase}", flush=True)
        check_scope()
        phase = "document structure, decision and source boundaries"
        print(f"\n[PHASE] {phase}", flush=True)
        check_document()
        phase = "local file whitespace"
        print(f"\n[PHASE] {phase}", flush=True)
        check_local_whitespace()
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
        "KAGGLE-JOB-BRIDGE-CONTRACT-REVIEW-1 LOCAL DOCUMENT CHECKS PASSED; "
        "CONTRACT BLOCKED SECURITY GAP; NO LIVE EXECUTION AUTHORIZED"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
