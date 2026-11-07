"""One committed, clean baseline for the S1/P10 qualification pair."""
import json
import os
import re
import subprocess
from pathlib import Path

AREA = Path(__file__).resolve().parent
ROOT = AREA.parents[1]
BASE = os.environ.get("FORGEAI_GEMMA4_QUALIFICATION_BASELINE", "")
PREFIX = "experiments/gemma4_competition/"
# Reviewed implementation scope; execution additionally requires a clean committed tree.
SCOPE = {
    *(f"validate_forgeai_gemma4_{c}_submission_qualification_1.py" for c in ("s1", "p10")),
    *(PREFIX + f"portable_{c}.py" for c in ("s1", "p10")),
    *(PREFIX + f"tests/test_{c}_qualification.py" for c in ("s1", "p10")),
    *(PREFIX + f"kaggle_compiler/{c}_compiler_only.ipynb" for c in ("s1", "p10")),
    *(PREFIX + f"submission_only/qualify_{c}.py" for c in ("s1", "p10")),
    *(PREFIX + f"submission_only/test_{c}_submission.py" for c in ("s1", "p10")),
    *(PREFIX + n for n in (
        "qualification_pair.py", "portable_p3.py", "README.md",
        "submission_only/qualify_p3.py", "submission_only/generate_self_contained.py",
        "submission_only/test_joint_qualification.py", "tests/test_qualification_pair.py",
        "results/submissions.json", "results/dev-16v-comparison.json",
        "results/dev-16v-comparison.md", "results/paper-evidence.json")),
}


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, stderr=subprocess.DEVNULL)


def require_frozen(receipt=None):
    if not re.fullmatch(r"[0-9a-f]{40}", BASE):
        raise ValueError("Set FORGEAI_GEMMA4_QUALIFICATION_BASELINE to the committed pair SHA")
    if git("branch", "--show-current").decode().strip() != "br-ForgeAI-Gemma4":
        raise ValueError("Qualification pair requires br-ForgeAI-Gemma4")
    if git("rev-parse", "HEAD").decode().strip() != BASE:
        raise ValueError("Both candidates require the same committed HEAD baseline")
    if git("status", "--porcelain", "--untracked-files=all").strip():
        raise ValueError("Commit the reviewed slice before export; keep repository clean through both submissions")
    if receipt is not None:
        doc = json.loads(Path(receipt).read_bytes())
        if doc.get("baseline") != BASE or doc.get("git_head") != BASE:
            raise ValueError("Receipt does not match common committed baseline")
    return BASE
