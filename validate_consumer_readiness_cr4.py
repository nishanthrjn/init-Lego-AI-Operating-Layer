"""CR-4 validation: consumer documentation and application assembly guide.

Run from the repository root:

    uv run python .\\validate_consumer_readiness_cr4.py

Documentation qualification only. No Docker, no model provider, no
heavyweight suites. Checks the new docs' structure, links, code-block
imports and catalog evidence; confirms stale active statements are gone,
historical records are preserved, and no production source changed. Stops at
the first failed phase and exits non-zero on failure.
"""

import ast
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ENGINEERING = ROOT / "packages" / "legoai-engineering"
CATALOG = ROOT / "docs" / "modules" / "MODULE-CATALOG.md"
ASSEMBLY = ROOT / "docs" / "ASSEMBLING-APPLICATIONS.md"
SELF = ROOT / "validate_consumer_readiness_cr4.py"
NEW_DOCS = (CATALOG, ASSEMBLY)
UPDATED_DOCS = (
    ROOT / "README.md",
    ENGINEERING / "README.md",
    ROOT / "planning" / "LEGOAI-CONSUMER-READINESS-PLAN.md",
    ROOT / "planning" / "PYTHON-FIRST-REUSABLE-AI-PLATFORM-PLAN.md",
)
LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
PRODUCTION = [
    "src/legoai",
    "packages/legoai-engineering/src",
    "packages/legoai-document/src",
    "packages/legoai-generative-media/src",
    "packages/legoai-collation/src",
    "packages/legoai-browser-hand-landmarks/src",
    "examples/forgeai/src",
    "examples/documind/src",
]


class Failure(Exception):
    pass


def text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def anchor(heading: str) -> str:
    slug = heading.strip().lower()
    slug = re.sub(r"[^\w\- ]", "", slug)
    return slug.replace(" ", "-")


def phase_exist() -> None:
    for path in NEW_DOCS:
        if not path.is_file() or not text(path).strip():
            raise Failure(f"missing documentation file: {path.relative_to(ROOT)}")


def phase_headings() -> None:
    catalog = text(CATALOG)
    for heading in (
        "# LegoAI Module Catalog",
        "## Maturity labels",
        "## Core runtime",
        "## Engineering",
        "## Other packs",
        "## Consumer applications",
        "## Deferred and planned",
        "## Per-module consumer documentation standard",
    ):
        if heading not in catalog:
            raise Failure(f"catalog heading missing: {heading}")
    columns = (
        "| Module | Real purpose | Supported public API | Typical uses | "
        "Configurable variation | Adapters / providers | Qualification | "
        "Important limitations | Consumer guide / evidence |"
    )
    if catalog.count(columns) != 3:
        raise Failure("catalog module tables must use the required columns")
    assembly = text(ASSEMBLY)
    numbered = [
        "## 1. Start with application intent",
        "## 2. Define application-owned inputs, outputs and effects",
        "## 3. Discover reusable modules",
        "## 4. REUSE > EXTEND > CREATE",
        "## 5. Separate task input, operator configuration and adapters",
        "## 6. Compose through public entry points",
        "## 7. Keep concrete adapters in the composition root",
        "## 8. Keep domain code on public Ports and values",
        "## 9. Add authorization at effect boundaries",
        "## 10. Test with fakes and replay before live providers",
        "## 11. Add clean-install and public-import architecture tests",
        "## 12. Record qualification honestly",
        "## 13. Promote patterns to LegoAI only with reuse evidence",
        "### A. DocuMind",
        "### B. Engineering consumer",
        "### C. ForgeAI",
    ]
    for heading in numbered:
        if heading not in assembly:
            raise Failure(f"assembly-guide heading missing: {heading}")
    for label in ("production-ready", "enterprise-ready", "battle-tested"):
        for path in NEW_DOCS:
            if label in text(path).lower():
                raise Failure(f"unsupported promotional label '{label}' in {path.name}")


def phase_links() -> None:
    for path in (*NEW_DOCS, *UPDATED_DOCS):
        body = text(path)
        headings = {
            anchor(line.lstrip("#"))
            for line in body.splitlines()
            if line.startswith("#")
        }
        for target in LINK.findall(body):
            if target.startswith(("http://", "https://", "mailto:")):
                continue
            file_part, _, fragment = target.partition("#")
            if not file_part:
                if fragment and fragment not in headings:
                    raise Failure(f"{path.name}: dangling anchor #{fragment}")
                continue
            resolved = (path.parent / file_part).resolve()
            if not resolved.exists():
                raise Failure(f"{path.name}: link target missing: {target}")


def phase_catalog_evidence() -> None:
    # Every module, application and deferred row must cite resolvable evidence
    # in its last cell; only the label and heading-standard tables are exempt.
    checked = 0
    for line in text(CATALOG).splitlines():
        if not line.startswith("| ") or set(line) <= set("|- "):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        first = cells[0]
        if first in {"Module", "Label", "Application", "Capability", "#"}:
            continue
        if first.isdigit() or first.startswith("**"):
            continue
        if len(cells) < 4:
            continue
        if not LINK.search(cells[-1]):
            raise Failure(f"catalog row without evidence link: {first}")
        checked += 1
    if checked < 20:
        raise Failure(f"too few catalog rows checked ({checked})")


def code_blocks(body: str) -> list[str]:
    return re.findall(r"```python\n(.*?)```", body, flags=re.DOTALL)


def private_imports(source: str) -> list[str]:
    found = []
    for node in ast.walk(ast.parse(source)):
        modules: list[str] = []
        names: list[str] = []
        if isinstance(node, ast.Import):
            modules = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules = [node.module]
            names = [alias.name for alias in node.names]
        for module in modules:
            if module.startswith(("legoai.reference", "legoai.runtime._composition")):
                found.append(module)
            elif module.startswith("legoai") and any(
                part.startswith("_") for part in module.split(".")
            ):
                found.append(module)
        if modules and modules[0].startswith("legoai"):
            found.extend(name for name in names if name.startswith("_"))
    return found


def phase_code_blocks() -> None:
    blocks = [(path, block) for path in NEW_DOCS for block in code_blocks(text(path))]
    if not blocks:
        raise Failure("assembly guide must include public-import code examples")
    for path, block in blocks:
        try:
            ast.parse(block)
        except SyntaxError as error:
            raise Failure(f"{path.name}: code block does not parse: {error}") from None


def phase_public_imports() -> None:
    for path in NEW_DOCS:
        for block in code_blocks(text(path)):
            found = private_imports(block)
            if found:
                raise Failure(f"{path.name}: private import in example: {found}")


def phase_stale_statuses() -> None:
    readme = text(ROOT / "README.md")
    for phrase in (
        "Workflows, Teams and ForgeAI remain planned",
        "public application-authoring facade remain future work",
        "M8.4 remains unstarted",
        "Git mutation and engineering Agents remain",
        "[Local validation is pending](planning/COMFYUI-TEXT-TO-IMAGE",
    ):
        if phrase in readme:
            raise Failure(f"stale active status in README.md: {phrase}")
    head = "\n".join(text(ENGINEERING / "README.md").splitlines()[:20])
    if "M8.4 is unstarted" in head:
        raise Failure("stale active M8.4 status in engineering README header")
    plan = text(ROOT / "planning" / "PYTHON-FIRST-REUSABLE-AI-PLATFORM-PLAN.md")
    if "M8.4 remains unstarted" in "\n".join(plan.splitlines()[:30]):
        raise Failure("stale active M8.4 status in platform plan header")
    if "Current note (2026-09-29, CR-4)" not in plan:
        raise Failure("platform roadmap ordering note missing")
    readiness = text(ROOT / "planning" / "LEGOAI-CONSUMER-READINESS-PLAN.md")
    if "nothing on the Core governed path is consumer-ready today" in readiness:
        raise Failure("stale readiness §17 statement")
    if "Superseded (2026-09-29, CR-4)" not in readiness:
        raise Failure("draft catalog not marked superseded")


def git(*arguments: str) -> subprocess.CompletedProcess[str]:
    executable = shutil.which("git")
    if executable is None:
        raise Failure("git is required")
    return subprocess.run(
        [executable, *arguments],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
        shell=False,
    )


def phase_history_preserved() -> None:
    historical = [
        "planning/M8.1-REPOSITORY-ANALYST-PLAN.md",
        "planning/M8.2-INDEPENDENT-REVIEWER-PLAN.md",
        "planning/M8.3-BOUNDED-CODING-PLAN.md",
        "planning/FORGEAI-REUSE-GAP-ASSESSMENT.md",
        "planning/FORGEAI-4-AND-M8.4-DIRECTION.md",
        "adrs",
    ]
    result = git("diff", "--quiet", "HEAD", "--", *historical)
    if result.returncode != 0:
        raise Failure("historical planning records or ADRs were modified")
    engineering = text(ENGINEERING / "README.md")
    if (
        "M8.3 Coding and M8.4 Test/Validation Agents remain unstarted."
        not in engineering
    ):
        raise Failure("historical engineering milestone text was rewritten")
    plan = text(ROOT / "planning" / "PYTHON-FIRST-REUSABLE-AI-PLATFORM-PLAN.md")
    if "memory, Workflow or Team. M8.4 remains unstarted." not in plan:
        raise Failure("historical platform-plan closure text was rewritten")


def phase_no_production_diff() -> None:
    tracked = git("diff", "--quiet", "HEAD", "--", *PRODUCTION)
    if tracked.returncode != 0:
        raise Failure("production source changed")
    untracked = git("status", "--porcelain", "--untracked-files=all", "--", *PRODUCTION)
    if untracked.stdout.strip():
        raise Failure(f"untracked production files:\n{untracked.stdout}")


def main() -> int:
    phases = [
        ("1 documentation files exist", phase_exist),
        ("2 expected headings and labels", phase_headings),
        ("3 internal links and anchors resolve", phase_links),
        ("4 Module Catalog rows cite evidence", phase_catalog_evidence),
        ("5 code blocks parse", phase_code_blocks),
        ("6 no private imports in doc examples", phase_public_imports),
        ("7 stale active statuses corrected", phase_stale_statuses),
        ("8 historical records preserved", phase_history_preserved),
        ("9 no production source change", phase_no_production_diff),
    ]
    completed: list[str] = []
    for name, check in phases:
        print(f"\n[PHASE] {name}", flush=True)
        try:
            check()
        except Failure as error:
            for item in completed:
                print("PASS " + item)
            print(f"FAIL {name}: {error}")
            return 1
        completed.append(name)
    uv = shutil.which("uv")
    if uv is None:
        print("FAIL 10: uv is required on PATH")
        return 1
    environment = os.environ.copy()
    environment.pop("VIRTUAL_ENV", None)
    commands = [
        (
            "10 engineering consumer-guide / architecture tests",
            [
                uv,
                "run",
                "--locked",
                "--no-sync",
                "python",
                "-m",
                "pytest",
                "-p",
                "no:cacheprovider",
                "-q",
                "tests/test_architecture.py",
            ],
            ENGINEERING,
        ),
        (
            "11 validator typing and lint",
            [sys.executable, "-m", "mypy", str(SELF)],
            ROOT,
        ),
        (
            "11b validator lint",
            [sys.executable, "-m", "ruff", "check", str(SELF)],
            ROOT,
        ),
        (
            "11c validator format",
            [sys.executable, "-m", "ruff", "format", "--check", str(SELF)],
            ROOT,
        ),
        (
            "12 git diff --check",
            [shutil.which("git") or "git", "diff", "--check"],
            ROOT,
        ),
    ]
    with tempfile.TemporaryDirectory(prefix="legoai-cr4-") as temporary:
        for name, command, cwd in commands:
            if "pytest" in command:
                command = [
                    *command[:-1],
                    "--basetemp",
                    str(Path(temporary) / "bt"),
                    command[-1],
                ]
            print(f"\n[PHASE] {name}", flush=True)
            print(subprocess.list2cmdline(command), flush=True)
            result = subprocess.run(
                command, cwd=cwd, env=environment, check=False, shell=False
            )
            if result.returncode != 0:
                for item in completed:
                    print("PASS " + item)
                print(f"FAIL {name}; later phases NOT RUN")
                return result.returncode if result.returncode > 0 else 1
            completed.append(name)
    for item in completed:
        print("PASS " + item)
    print("CR-4 DOCUMENTATION VALIDATION PASSED - docs only; no production change")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
