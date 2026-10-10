"""Maintainer-only local document checks; no tests, installs or service calls."""

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BASELINE = "c7e6070f0675fdaed95f246fc778275863779080"
DOCUMENT = "planning/KAGGLE-FORGEAI-INTEGRATION-OPTIONS-1.md"
VALIDATOR = "validate_kaggle_forgeai_integration_options_1.py"
ALLOWED = frozenset({DOCUMENT, VALIDATOR})
SECTIONS = (
    "Decision and scope",
    "Current evidence and repository boundary",
    "Official source ledger",
    "Candidate comparison",
    "Zero-cost and service-use assessment",
    "Authentication and privacy",
    "Conceptual request contract",
    "Conceptual response contract",
    "Lifecycle, races and failures",
    "ModelPort and integration placement",
    "Future ComfyUI and VTO applicability",
    "Evidence gates and implementation sequence",
    "Qualification plan and stop conditions",
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
    # Baseline-to-index and baseline-to-worktree separately catch staged changes
    # that were reversed only in the working copy. No rename folding hides paths.
    changed = git_paths(["diff", "--name-only", "--no-renames", "-z", BASELINE, "--"])
    changed |= git_paths(
        ["diff", "--cached", "--name-only", "--no-renames", "-z", BASELINE, "--"]
    )
    changed |= git_paths(["ls-files", "--others", "--exclude-standard", "-z"])
    unexpected = sorted(changed - ALLOWED)
    if unexpected:
        raise ValueError(f"changes outside the two-file slice: {unexpected!r}")
    for name in ALLOWED:
        path = ROOT / name
        if path.is_symlink() or not path.is_file():
            raise ValueError(f"missing or symlinked slice file: {name}")


def check_document() -> None:
    path = ROOT / DOCUMENT
    if path.stat().st_size > 100_000:
        raise ValueError("document exceeds local review bound")
    source = path.read_text(encoding="utf-8")
    for index, title in enumerate(SECTIONS, 1):
        if f"## {index}. {title}\n" not in source:
            raise ValueError(f"missing required section: {title}")
    recommendations = re.findall(r"^RECOMMENDATION:\s*\n    ([A-Z_]+)$", source, re.M)
    if recommendations != ["NEED_MORE_EVIDENCE"] or not source.rstrip().endswith(
        "RECOMMENDATION:\n    NEED_MORE_EVIDENCE"
    ):
        raise ValueError("expected exactly one final evidence-gated recommendation")
    required = (
        "2026-10-11",
        BASELINE,
        "ZERO_COST_REQUIREMENT_VIOLATED",
        "No REPOSITORY_CONTENT, TASK_TEXT, DERIVED_DIAGNOSTIC",
        "No automatic repository mutation.",
        "No ModelPort signature change",
        "No live probe is authorized",
        "KAGGLE-JOB-BRIDGE-CONTRACT-REVIEW-1",
        "request_sha256",
        "OUTPUT_IDENTITY_MISMATCH",
        "SUBMISSION_UNCERTAIN",
        "4096 bytes",
        "8192 bytes",
        "SUPPORTED",
        "PARTIAL",
        "UNSUPPORTED",
        "UNKNOWN",
        "https://www.kaggle.com/docs/notebooks",
        "https://github.com/Kaggle/kaggle-cli/blob/main/CHANGELOG.md",
        "https://www.kaggle.com/terms",
        "https://www.kaggle.com/privacy",
    )
    for declaration in required:
        if declaration not in source:
            raise ValueError(f"missing design declaration: {declaration}")
    # Executable examples are restricted to the exact local handoff. Prose and
    # Mermaid still require maintainer semantic review; this is not a proof.
    fences = re.findall(r"^```([^\n]*)\n(.*?)^```\s*$", source, re.M | re.S)
    handoff = (
        "uv run --locked --offline --no-sync python "
        ".\\validate_kaggle_forgeai_integration_options_1.py\n"
        "if ($LASTEXITCODE -ne 0) { throw 'Kaggle integration options validation failed' }"
    )
    examples = [body.strip() for language, body in fences if language == "powershell"]
    if examples != [handoff]:
        raise ValueError("local handoff commands changed")
    if any(language not in {"mermaid", "powershell"} for language, _ in fences):
        raise ValueError("unexpected executable example fence")
    if any(line.rstrip() != line for line in source.splitlines()):
        raise ValueError("document has trailing whitespace")
    if not source.endswith("\n"):
        raise ValueError("document lacks final newline")


def main() -> int:
    phase = "two-file scope; production and dependencies unchanged"
    try:
        print(f"[PHASE] {phase}", flush=True)
        check_scope()
        phase = "document structure and explicit boundaries"
        print(f"\n[PHASE] {phase}", flush=True)
        check_document()
        checks = (
            ("typing", [sys.executable, "-m", "mypy", VALIDATOR]),
            ("lint", [sys.executable, "-m", "ruff", "check", VALIDATOR]),
            ("format", [sys.executable, "-m", "ruff", "format", "--check", VALIDATOR]),
            ("working whitespace", ["git", "diff", "--check", BASELINE, "--"]),
            (
                "staged whitespace",
                ["git", "diff", "--cached", "--check", BASELINE, "--"],
            ),
        )
        for phase, command in checks:
            print(f"\n[PHASE] {phase}", flush=True)
            subprocess.run(command, cwd=ROOT, check=True, timeout=120)
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        print(f"FAIL: {phase}: {exc}; later phases NOT RUN")
        return 1
    print(
        "KAGGLE-FORGEAI-INTEGRATION-OPTIONS-1 LOCAL DOCUMENT CHECKS PASSED; "
        "NO CONNECTIVITY QUALIFIED; NO LIVE EXECUTION AUTHORIZED"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
