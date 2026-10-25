"""P3 qualification orchestration; shared M2 compiler/reconciliation and P1 scope guards."""
import argparse
import contextlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile

from experiments.gemma4_competition import portable_p3 as p3

ROOT = Path(__file__).resolve().parent
BASE = "fd801cf5ef6fe1732f2ce2b23530676c153d2cae"
PREFIX = "experiments/gemma4_competition/"
SCOPE = {
    PREFIX + "portable_m2.py",
    "validate_forgeai_gemma4_p3_submission_qualification_1.py",
    PREFIX + "portable_p3.py", PREFIX + "tests/test_p3_qualification.py",
    PREFIX + "kaggle_compiler/p3_compiler_only.ipynb",
    PREFIX + "submission_only/first_submission.ipynb",
    PREFIX + "submission_only/qualify_p3.py",
    PREFIX + "submission_only/test_p3_submission.py",
    PREFIX + "local_eval/README.md", PREFIX + "local_eval/paper_evidence.py",
    PREFIX + "results/dev-16v-comparison.json", PREFIX + "results/paper-evidence.json",
    PREFIX + "results/dev-16v-comparison.md", PREFIX + "results/submissions.json",
}


def shared_gate():
    gate = p3.load_instance(ROOT / "validate_forgeai_gemma4_m2_minimal_baseline_1.py", "_p3_m2_gate")
    gate.shared = p3.ENGINE
    gate.CANDIDATE = p3.CANDIDATE
    gate.static_candidate = p3.static_candidate
    return gate


def scope_gate():
    gate = p3.load_instance(ROOT / "validate_forgeai_gemma4_p1_procedure_prompt_1.py", "_p3_scope_gate")
    gate.BASE, gate.SCOPE, gate.p1 = BASE, SCOPE, p3
    return gate


def reconcile(receipt, remote):
    p3.require(receipt.is_file() and remote.is_dir(), "receipt FILE and result DIRECTORY required")
    p3.require(not receipt.resolve().is_relative_to(ROOT) and not remote.resolve().is_relative_to(ROOT),
               "compiler evidence must remain outside repository")
    with contextlib.redirect_stdout(io.StringIO()):
        shared_gate().reconcile(receipt, remote)
    print("P3_OFFICIAL_COMPILER_VALIDATED; BYTE_IDENTITY_VERIFIED")
    print("P3_PACKAGE_VALIDATED; NO MODEL QUALITY OR SUBMISSION AUTHORIZATION")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--local-only", action="store_true")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--receipt", type=Path)
    parser.add_argument("--reconcile", type=Path)
    parser.add_argument("--pre-commit", action="store_true")
    args = parser.parse_args()
    if args.local_only == bool(args.reconcile) or (args.reconcile and not args.receipt):
        parser.error("choose --local-only OR --receipt FILE --reconcile DIRECTORY")
    if args.pre_commit and not args.reconcile:
        parser.error("--pre-commit requires reconciliation")
    scope = scope_gate()
    scope.phase("exact P3 qualification scope", scope.scope_checks)
    scope.phase("experimental P3 member and ZIP identity", lambda: p3.static_candidate(p3.CANDIDATE))
    if not args.pre_commit:
        scope.phase("preserved wheel pins", p3.wheel_pins)
        for directory, pattern in (("tests", "test_m2_minimal_baseline.py"),
                                   ("tests", "test_p3_qualification.py"), ("submission_only", "test_*.py")):
            scope.phase("offline controls: " + pattern, lambda d=directory, p=pattern: subprocess.run(
                [sys.executable, "-B", "-m", "unittest", "discover", "-s", PREFIX + d, "-p", p],
                cwd=ROOT, check=True))
        scope.phase("post-control scope preservation", scope.scope_checks)
    if args.reconcile:
        scope.phase("P3 evidence reconciliation", lambda: reconcile(args.receipt, args.reconcile))
        if args.pre_commit:
            with contextlib.redirect_stdout(io.StringIO()):
                scope.staged_checks()
            print("P3_PRE_COMMIT_STAGED_CONSISTENCY_PASSED")
    else:
        receipt = {"schema": 1, "state": "LOCAL_SCOPE_AND_STATIC_PASS", "candidate": "p3",
                   "budgets": p3.BUDGETS, "prompt_sha256": p3.PROMPT_SHA256,
                   "experimental_zip_sha256": p3.EXPERIMENTAL_ZIP_SHA256, "baseline": BASE,
                   "git_head": scope.git("rev-parse", "HEAD").decode().strip(), "inputs": p3.input_manifest()}
        output = args.output or Path(tempfile.mkdtemp(prefix="gemma-p3-transfer-parent-")) / "bundle"
        scope.phase("external P3 transfer bundle", lambda: shared_gate().export_bundle(output, receipt))
        print("P3_LOCAL_SCOPE_AND_STATIC_PASS; PORTABLE COMPILATION REQUIRED")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print("FAIL: P3 qualification: " + (str(error) if type(error) is ValueError else type(error).__name__), file=sys.stderr)
        raise SystemExit(1) from None
