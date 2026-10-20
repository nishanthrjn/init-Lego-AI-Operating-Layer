"""Maintainer-only B2 local gate; shared M2 compilation and reconciliation."""
import argparse
import contextlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile

from experiments.gemma4_competition import portable_b2 as b2

ROOT = Path(__file__).resolve().parent
BASE = "b319b8c76615a1705623fddbeb73d52b51605cdd"
PREFIX = "experiments/gemma4_competition/"
SCOPE = {
    ".gitattributes", "validate_forgeai_gemma4_b2_candidate_1.py",
    PREFIX + "portable_b2.py", PREFIX + "tests/test_b2_candidate.py",
    PREFIX + "candidates/README.md", PREFIX + "results/submissions.json",
    PREFIX + "kaggle_compiler/b2_compiler_only.ipynb",
    PREFIX + "submission_only/first_submission.ipynb",
    PREFIX + "submission_only/README.md",
    PREFIX + "submission_only/test_candidate_selection.py",
    *(PREFIX + "candidates/b2/" + name for name in b2.MEMBERS),
}


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT)


def scope_checks():
    changed = set(git("diff", "--name-only", BASE).decode().splitlines())
    changed.update(git("ls-files", "--others", "--exclude-standard").decode().splitlines())
    b2.require(changed <= SCOPE, "outside B2 scope: " + str(sorted(changed - SCOPE)))
    git("diff", "--check", BASE, "--", *sorted(SCOPE))
    b2.require((ROOT / ".gitattributes").read_text().splitlines() == [
        "experiments/gemma4_competition/baseline/** text eol=lf",
        "experiments/gemma4_competition/candidates/** text eol=lf",
    ], "LF policy changed")


def shared_gate():
    gate = b2.load_instance(ROOT / "validate_forgeai_gemma4_m2_minimal_baseline_1.py", "_b2_local_gate")
    gate.shared = b2.ENGINE
    gate.CANDIDATE = b2.CANDIDATE
    gate.static_candidate = b2.static_candidate
    return gate


def reconcile(receipt, remote):
    # Reuse every M2 evidence/ZIP/identity/deviation check; only the success label
    # differs. Do not allow the shared historical M2 label to escape for B2.
    with contextlib.redirect_stdout(io.StringIO()):
        shared_gate().reconcile(receipt, remote)
    print("B2_OFFICIAL_COMPILER_VALIDATED; BYTE_IDENTITY_VERIFIED")
    print("B2_PACKAGE_VALIDATED; NO MODEL QUALITY OR SUBMISSION AUTHORIZATION")


def local_checks():
    scope_checks()
    b2.wheel_pins()
    b2.static_candidate(b2.CANDIDATE)
    for directory, pattern in (
        (PREFIX + "tests", "test_m2_minimal_baseline.py"),
        (PREFIX + "tests", "test_b2_candidate.py"),
        (PREFIX + "submission_only", "test_*.py"),
    ):
        subprocess.run([sys.executable, "-B", "-m", "unittest", "discover", "-s", directory,
                        "-p", pattern], cwd=ROOT, check=True)
    scope_checks()
    return {"schema": 1, "state": "LOCAL_SCOPE_AND_STATIC_PASS", "candidate": "b2",
            "budgets": b2.BUDGETS, "baseline": BASE, "git_head": git("rev-parse", "HEAD").decode().strip(),
            "inputs": b2.input_manifest()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--local-only", action="store_true")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--receipt", type=Path)
    parser.add_argument("--reconcile", type=Path)
    parser.add_argument("--pre-commit", action="store_true")
    args = parser.parse_args()
    if args.pre_commit:
        b2.require(args.receipt and args.reconcile, "pre-commit requires receipt and results")
        scope_checks()
        reconcile(args.receipt, args.reconcile)
        staged = set(git("diff", "--cached", "--name-only", BASE).decode().splitlines())
        b2.require(staged <= SCOPE, "outside staged B2 scope")
        for name in staged:
            raw = (ROOT / name).read_bytes()
            indexed = git("show", ":" + name)
            if name.startswith(PREFIX + "candidates/b2/"):
                b2.require(raw == indexed, "candidate index bytes mismatch")
            else:
                b2.require(b2.normalized(raw) == b2.normalized(indexed), "staged content differs: " + name)
        git("diff", "--cached", "--check", BASE, "--", *sorted(SCOPE))
        print("B2_PRE_COMMIT_STAGED_CONSISTENCY_PASSED")
        return 0
    receipt = local_checks()
    if args.reconcile:
        b2.require(args.receipt is not None, "original B2 receipt required")
        reconcile(args.receipt, args.reconcile)
    else:
        b2.require(args.local_only, "use --local-only or --reconcile; no implicit compiler run")
        output = args.output or Path(tempfile.mkdtemp(prefix="gemma-b2-transfer-parent-")) / "bundle"
        shared_gate().export_bundle(output, receipt)
        print("B2_LOCAL_SCOPE_AND_STATIC_PASS; PORTABLE COMPILATION REQUIRED")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print("FAIL: " + type(error).__name__ + "; later phases NOT RUN", file=sys.stderr)
        raise SystemExit(1) from None
