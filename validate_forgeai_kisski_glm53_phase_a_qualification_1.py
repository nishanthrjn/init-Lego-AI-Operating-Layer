"""Offline documentary readiness checks; run only by the maintainer."""

import subprocess
from pathlib import Path

from scripts.kisski_coding_eval.frozen import verify
from validate_forgeai_kisski_coding_model_evaluation_1 import git

ROOT = Path(__file__).resolve().parent
BASELINE = "12de226b1549eedd8f983dd7b96345344b942aea"
MANIFEST = "3cd0e5a14f6ff9d2beba5cb1af9bcc6ac214637a7b3858ad3282bd0e51691ef6"
SELF = "validate_forgeai_kisski_glm53_phase_a_qualification_1.py"
DOCUMENT = "planning/FORGEAI-KISSKI-GLM53-PHASE-A-QUALIFICATION-1.md"
REQUIRED = (
    "Status: MAINTAINER VALIDATION PENDING; PRIOR GLM PROTOCOL FAILURES RECORDED.",
    "Model: `glm-5.3-flash`.",
    "Tasks: `bug`, `refactor`, `api`, `diagnosis`.",
    "Bounds: one discovery; four chats; 1024 output tokens; 60 seconds per chat.",
    'Acceptance: only `finish_reason == "stop"`; LENGTH remains rejected.',
    "No retry, fallback, model reselection, resume or historical record merging.",
    "DeepSeek: `NO_MODEL_QUALIFIED`; `MODEL_NOT_QUALIFIED`.",
    "Pilot: `ADMISSIONS` remains empty.",
    "NO LIVE EXECUTION AUTHORIZED; NO PHASE B AUTHORIZED.",
    "Existing GLM evidence is inconclusive; provider failures are not quality scores.",
)


def document(content: str) -> None:
    if any(content.count(line) != 1 for line in REQUIRED):
        raise ValueError("missing or duplicated disposition/boundary statement")
    if BASELINE not in content or MANIFEST not in content:
        raise ValueError("baseline identity missing")


def main() -> int:
    phase = "exact two-file scope; all existing source and records preserved"
    try:
        print("[PHASE] " + phase, flush=True)
        allowed = {SELF, DOCUMENT}
        changed = set(git("diff", "--name-only", "--no-renames", BASELINE).splitlines())
        changed.update(
            git("diff", "--cached", "--name-only", "--no-renames", BASELINE).splitlines()
        )
        changed.update(git("ls-files", "--others", "--exclude-standard").splitlines())
        if changed - allowed:
            raise ValueError("outside documentary scope: " + repr(changed - allowed))
        for name in allowed:
            path = ROOT / name
            if path.is_symlink() or not path.is_file():
                raise ValueError("missing or symlinked slice file")
            content = path.read_text(encoding="utf-8")
            if not content.endswith("\n") or content.endswith("\n\n"):
                raise ValueError("final newline violation")
            if any(line.rstrip() != line for line in content.splitlines()):
                raise ValueError("trailing whitespace")
        phase = "frozen source manifest and canonical contract pins"
        print("\n[PHASE] " + phase, flush=True)
        if verify(ROOT) != MANIFEST:
            raise ValueError("unexpected frozen source manifest")
        phase = "document boundaries; positive and negative controls"
        print("\n[PHASE] " + phase, flush=True)
        content = (ROOT / DOCUMENT).read_text(encoding="utf-8")
        document(content)
        for line in REQUIRED:
            try:
                document(content.replace(line, "REMOVED", 1))
            except ValueError:
                continue
            raise ValueError("negative documentary control accepted")
        indexed = git("ls-files", "--", DOCUMENT).splitlines()
        if indexed:
            document(git("show", ":" + DOCUMENT))
        phase = "working and staged whitespace"
        print("\n[PHASE] " + phase, flush=True)
        git("diff", "--check", BASELINE)
        git("diff", "--cached", "--check", BASELINE)
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(f"FAIL: {phase}: {error}; later phases NOT RUN")
        return 1
    print(
        "FORGEAI-KISSKI-GLM53-PHASE-A-QUALIFICATION-1 LOCAL DOCUMENT CHECKS PASSED; "
        "FROZEN INTEGRITY VERIFIED; PRIOR GLM PROTOCOL FAILURES PRESERVED; "
        "NO MODEL QUALITY QUALIFIED; NO LIVE EXECUTION AUTHORIZED"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
