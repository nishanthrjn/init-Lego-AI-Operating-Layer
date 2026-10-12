"""Maintainer-run documentary checks; never import or execute ForgeAI."""

import hashlib
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BASELINE = "593fcbc42c976003af0942af1bfccefea55eff04"
DOCUMENT = "planning/FORGEAI-V0.2-REPOSITORY-ENGINEER-READINESS-1.md"
SELF = "validate_forgeai_v0_2_repository_engineer_readiness_1.py"
ALLOWED = frozenset({DOCUMENT, SELF})
# Unrelated maintainer edits present on resumption; not edited by this slice.
# Normalize CRLF only, so Git staging does not change their identity.
PRESERVED = {
    "AGENTS.md": "effa1b2ae09e62857b5a7690d0d975c384a07079a51393a72449dc74290bc0ee",
    "CLAUDE.md": "f530c2fd05f0c55d0b992f724ed2a9ecfeb531884c79d6577b2e1382b8753b28",
}
DECISION = "FORGEAI_V0_2_IMPLEMENTATION_READY"
NEXT = "FORGEAI-REPOSITORY-CONTEXT-PREFLIGHT-1"
STATUSES = frozenset(
    {
        "IMPLEMENTED_AND_QUALIFIED",
        "IMPLEMENTED_BUT_NOT_QUALIFIED",
        "PARTIAL",
        "ABSENT",
        "NOT_REQUIRED_FOR_V0_2",
    }
)
GAPS = frozenset(
    {
        "ARCHITECTURE_GAP",
        "IMPLEMENTATION_GAP",
        "MODEL_QUALITY_GAP",
        "PROVIDER_LIMITATION",
        "ENVIRONMENT_LIMITATION",
        "EVALUATION_GAP",
    }
)
MARKERS = {
    "examples/forgeai/src/forgeai/domain.py": (
        "class TaskRequest:",
        "MAX_ATTEMPTS = 2",
    ),
    "examples/forgeai/src/forgeai/composition.py": (
        "def prepare_run(",
        "def local_profile(",
    ),
    "examples/forgeai/src/forgeai/worker.py": (
        "async def _attempt(",
        "async def _rework(",
        "async def _review(",
    ),
    "examples/forgeai/src/forgeai/review.py": ("def check_rework_constraints(",),
    "examples/forgeai/src/forgeai/cli.py": ("def terminal_approver(",),
    "packages/legoai-engineering/src/legoai_engineering/repository/ports.py": (
        "class RepositoryWorkspacePort(Protocol):",
    ),
    "packages/legoai-engineering/src/legoai_engineering/git/ports.py": (
        "class GitRepositoryPort(Protocol):",
    ),
    "packages/legoai-engineering/src/legoai_engineering/coding/values.py": (
        "MAX_REFERENCE_TOTAL_BYTES = 16384",
    ),
    "examples/forgeai/tests/test_v01_context.py": (
        "def test_instruction_text_in_context_stays_repository_data(",
    ),
    "examples/forgeai/tests/test_v01_check_rework.py": (
        "def test_21_no_third_attempt_is_representable(",
    ),
}
REQUIRED = (
    "repository guidance is data, never host authority",
    "Model output is data, never authority",
    "mutation requires exact proposal approval",
    "no automatic reset, rollback, commit or push",
    "no generic workflow engine",
    "vector database",
    "knowledge graph",
    "no PlannerAgent",
    "no step adds an unlimited loop",
    "CONTEXT_INCOMPLETE",
    "no new Port",
    "ADR-027 remains Deferred",
    "NOT RUN — Awaiting user execution",
    "no production, dependencies or ADRs change",
    "the whole v0.2 product remains unimplemented and unqualified",
    "root-file inventory",
    "REPOSITORY_STRUCTURE_ACTION",
    "same model binding",
    "six false-sufficients",
    "no validator was run internally",
)


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=True,
        capture_output=True,
        timeout=30,
    ).stdout.decode("utf-8")


def paths(*args: str) -> set[str]:
    return {part for part in git(*args).split("\0") if part}


def digest(text: str) -> str:
    return hashlib.sha256(text.replace("\r\n", "\n").encode("utf-8")).hexdigest()


def scope(changed: set[str]) -> None:
    if changed - ALLOWED - PRESERVED.keys():
        raise ValueError("changes outside review and pinned pre-existing edits")


def preserved() -> None:
    for name, expected in PRESERVED.items():
        path = ROOT / name
        if path.is_symlink() or digest(path.read_text(encoding="utf-8")) != expected:
            raise ValueError(f"pre-existing instruction edit changed: {name}")
        staged = digest(git("show", f":{name}"))
        original = digest(git("show", f"{BASELINE}:{name}"))
        if staged not in (original, expected):
            raise ValueError(f"unexpected staged instruction edit: {name}")


def whitespace(text: str, label: str) -> None:
    if not text.endswith("\n") or text.endswith("\n\n"):
        raise ValueError(f"final newline violation: {label}")
    if any(line != line.rstrip(" \t") for line in text.splitlines()):
        raise ValueError(f"trailing whitespace: {label}")


def rows(text: str, pattern: str) -> list[list[str]]:
    return [
        [cell.strip() for cell in line.strip("|").split("|")]
        for line in text.splitlines()
        if re.match(pattern, line)
    ]


def document(text: str) -> None:
    whitespace(text, DOCUMENT)
    headings = re.findall(r"^## (\d+)\. ", text, re.MULTILINE)
    if headings != [str(i) for i in range(1, 23)]:
        raise ValueError("22 ordered review sections required")
    choices = re.findall(r"^FORGEAI_V0_2_[A-Z_]+$", text, re.MULTILINE)
    if choices != [DECISION] or text.rstrip().splitlines()[-1] != DECISION:
        raise ValueError("one final readiness decision required")
    selected = re.findall(r"^Selected next slice: `([^`]+)`\.$", text, re.MULTILINE)
    if selected != [NEXT]:
        raise ValueError("exactly one next slice required")
    normalized = " ".join(text.casefold().split())
    for required in REQUIRED:
        if required.casefold() not in normalized:
            raise ValueError(f"missing boundary/evidence: {required}")
    capability = rows(text, r"^\| [A-S] \|")
    if [row[0] for row in capability] != list("ABCDEFGHIJKLMNOPQRS"):
        raise ValueError("complete ordered A-S matrix required")
    for row in capability:
        if len(row) != 4 or row[2] not in STATUSES or not re.search(r"S\d{2}", row[3]):
            raise ValueError("capability classification and source required")
    gaps = rows(text, r"^\| G\d{2} \|")
    if [row[0] for row in gaps] != [f"G{i:02}" for i in range(1, 11)]:
        raise ValueError("ranked G01-G10 gap matrix required")
    for row in gaps:
        if (
            len(row) != 11
            or row[3] not in GAPS
            or row[5] not in {"REUSE", "EXTEND", "CREATE"}
            or any(not cell for cell in row)
        ):
            raise ValueError("complete classified gap row required")
    for classification in GAPS:
        if classification not in text:
            raise ValueError("model/system/environment distinctions missing")
    sources = rows(text, r"^\| S\d{2} \|")
    if [row[0] for row in sources] != [f"S{i:02}" for i in range(1, 19)]:
        raise ValueError("source/test register incomplete")
    if not all(len(row) == 3 and "test_" in row[2] for row in sources[:14]):
        raise ValueError("focused tests required for production capability claims")


def source_links(text: str) -> None:
    for target in re.findall(r"\]\(([^)]+)\)", text):
        path = (ROOT / DOCUMENT).parent / target.split("#", 1)[0]
        resolved = path.resolve()
        if not resolved.is_relative_to(ROOT) or path.is_symlink() or not path.is_file():
            raise ValueError(f"missing or out-of-repository source link: {target}")
    for name, tokens in MARKERS.items():
        source = (ROOT / name).read_text(encoding="utf-8")
        if any(token not in source for token in tokens):
            raise ValueError(f"review source identity changed: {name}")


def controls(text: str) -> None:
    document(text)
    mutants = (
        text.replace("| A | Establish", "| Z | Establish", 1),
        text.replace("| ABSENT |", "| UNKNOWN |", 1),
        text.replace("| G01 |", "| G99 |", 1),
        text.replace("| EXTEND |", "| INVENT |", 1),
        text.replace("Model output is data, never authority", "Model grants authority"),
        text.replace("No step adds\nan unlimited loop", "Allow unlimited loops"),
        text.replace("Selected next slice:", "Unselected slice:", 1),
        text + f"\nSelected next slice: `{NEXT}`.\n",
        text + "FORGEAI_V0_2_BLOCKED\n",
        text.replace("| S01 |", "| S99 |", 1),
    )
    for mutant in mutants:
        if mutant == text:
            raise ValueError("negative control did not alter its target")
        try:
            document(mutant)
        except ValueError:
            continue
        raise ValueError("negative documentary control was accepted")
    scope(set(ALLOWED))
    for forbidden in ("src/legoai/runtime/local.py", "uv.lock", "adrs/ADR-027.md"):
        try:
            scope({forbidden})
        except ValueError:
            continue
        raise ValueError("scope negative control was accepted")


def main() -> int:
    phase = "two-file review scope; unrelated instruction edits pinned and preserved"
    try:
        print(f"[PHASE] {phase}", flush=True)
        changed = paths("diff", "--name-only", "--no-renames", "-z", BASELINE)
        staged = paths(
            "diff", "--cached", "--name-only", "--no-renames", "-z", BASELINE
        )
        changed |= staged | paths("ls-files", "--others", "--exclude-standard", "-z")
        scope(changed)
        preserved()
        for name in ALLOWED:
            if (ROOT / name).is_symlink() or not (ROOT / name).is_file():
                raise ValueError(f"missing or symlinked review file: {name}")
        phase = "source references, A-S coverage, gaps and singular decision"
        print(f"\n[PHASE] {phase}", flush=True)
        text = (ROOT / DOCUMENT).read_text(encoding="utf-8")
        document(text)
        source_links(text)
        whitespace((ROOT / SELF).read_text(encoding="utf-8"), SELF)
        phase = "positive and negative document controls"
        print(f"\n[PHASE] {phase}", flush=True)
        controls(text)
        phase = "staged document consistency"
        print(f"\n[PHASE] {phase}", flush=True)
        review_staged = staged & ALLOWED
        if review_staged:
            if review_staged != ALLOWED:
                raise ValueError("stage both review files or leave both unstaged")
            staged_document = git("show", f":{DOCUMENT}")
            document(staged_document)
            source_links(staged_document)
            whitespace(git("show", f":{SELF}"), SELF)
        for label, args in (
            ("working whitespace", ("diff", "--check", BASELINE, "--")),
            ("staged whitespace", ("diff", "--cached", "--check", BASELINE, "--")),
        ):
            phase = label
            print(f"\n[PHASE] {phase}", flush=True)
            git(*args)
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(f"FAIL: {phase}: {error}; later phases NOT RUN")
        return 1
    print(
        "FORGEAI-V0.2-REPOSITORY-ENGINEER-READINESS-1 LOCAL DOCUMENT CHECKS PASSED; "
        f"{DECISION}; NEXT: {NEXT}; "
        "V0.2 NOT QUALIFIED; NO IMPLEMENTATION OR LIVE EXECUTION AUTHORIZED"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
