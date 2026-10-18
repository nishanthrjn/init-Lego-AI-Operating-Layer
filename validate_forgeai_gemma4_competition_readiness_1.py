"""Maintainer-run documentary checks only; no network or harness execution."""

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BASELINE = "fd9ce282249067a0c68187d2ff56447d8fd29108"
SELF = "validate_forgeai_gemma4_competition_readiness_1.py"
PRESERVED = "validate_forgeai_kisski_glm53_phase_a_qualification_1.py"
WORKING_BLOB = "120cd167f51df68152c652500ccaab323bd03e3c"
INDEX_BLOB = "2f3a3b458703df13cd0887055fe93654daa46f69"
DOCUMENTS = {
    "FORGEAI-GEMMA4-COMPETITION-READINESS-1.md": (
        "M1 PARTIAL; M2 BLOCKED ON OFFICIAL HARNESS CONTRACTS",
        "REUSE",
        "ADAPT",
        "CREATE",
        "EXCLUDE",
        "Pilot ADMISSIONS remains empty.",
        "FORGEAI-GEMMA4-OFFICIAL-HARNESS-CONTRACT-1",
    ),
    "GEMMA4-COMPETITION-REQUIREMENTS.md": (
        "M1 PARTIAL",
        "R1",
        "R7",
        "No HARNESS_README or starter code has been verified in this slice.",
        "https://www.kaggle.com/competitions/gemma-4-developer-agent/rules",
        "https://www.kaggle.com/competitions/gemma-4-developer-agent-paper/rules",
    ),
    "GEMMA4-RESEARCH-PLAN.md": (
        "NO NOVELTY OR IMPROVEMENT CLAIMED",
        "locked evaluation",
        "H1",
        "H7",
        "Matched experiment arms",
    ),
    "GEMMA4-IMPLEMENTATION-MILESTONES.md": (
        *(f"| M{i} " for i in range(1, 10)),
        "Acceptance and tests",
        "Evidence, risk and maintainer gate",
    ),
}


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    ).stdout


def document(name: str, content: str) -> None:
    required = (*DOCUMENTS[name], "NO LIVE EXECUTION OR SUBMISSION AUTHORIZED.")
    if any(item not in content for item in required):
        raise ValueError("document boundary missing: " + name)
    if not content.endswith("\n") or content.endswith("\n\n"):
        raise ValueError("final newline: " + name)
    if any(line.rstrip() != line for line in content.splitlines()):
        raise ValueError("trailing whitespace: " + name)


def main() -> int:
    phase = "five-file planning scope; unrelated GLM edit pinned"
    try:
        print("[PHASE] " + phase, flush=True)
        allowed = {SELF, *("planning/" + name for name in DOCUMENTS)}
        changed = set(git("diff", "--name-only", "--no-renames", BASELINE).splitlines())
        staged = set(
            git("diff", "--cached", "--name-only", "--no-renames", BASELINE).splitlines()
        )
        changed.update(staged)
        changed.update(git("ls-files", "--others", "--exclude-standard").splitlines())
        if (ROOT / PRESERVED).is_symlink():
            raise ValueError("preserved file became symlink")
        if git("hash-object", "--", PRESERVED).strip() != WORKING_BLOB:
            raise ValueError("unrelated GLM working edit changed")
        if git("rev-parse", ":" + PRESERVED).strip() not in {
            INDEX_BLOB,
            WORKING_BLOB,
        }:
            raise ValueError("unrelated GLM index changed")
        if changed - allowed - {PRESERVED}:
            raise ValueError("outside planning scope")
        for name in allowed:
            if (ROOT / name).is_symlink() or not (ROOT / name).is_file():
                raise ValueError("missing or symlinked slice file")
        phase = "requirements, boundaries, milestones and negative controls"
        print("\n[PHASE] " + phase, flush=True)
        for name, requirements in DOCUMENTS.items():
            path = "planning/" + name
            content = (ROOT / path).read_text(encoding="utf-8")
            document(name, content)
            required = (*requirements, "NO LIVE EXECUTION OR SUBMISSION AUTHORIZED.")
            for requirement in required:
                try:
                    document(name, content.replace(requirement, "REMOVED"))
                except ValueError:
                    continue
                raise ValueError("negative documentary control accepted")
            if path in staged:
                document(name, git("show", ":" + path))
        phase = "working and staged slice whitespace"
        print("\n[PHASE] " + phase, flush=True)
        git("diff", "--check", BASELINE, "--", *sorted(allowed))
        git("diff", "--cached", "--check", BASELINE, "--", *sorted(allowed))
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(f"FAIL: {phase}: {error}; later phases NOT RUN")
        return 1
    print(
        "FORGEAI-GEMMA4-COMPETITION-READINESS-1 LOCAL DOCUMENT CHECKS PASSED; "
        "M1 PARTIAL; OFFICIAL HARNESS AND RULES REVIEW REQUIRED; "
        "NO IMPLEMENTATION, LIVE EXECUTION OR SUBMISSION AUTHORIZED"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
