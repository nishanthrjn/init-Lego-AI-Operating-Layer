"""Maintainer-only P1 gate. Reuses M2 algorithms, with independent receipt/scope."""
import argparse
import contextlib
import io
from pathlib import Path
import subprocess
import sys
import tempfile

from experiments.gemma4_competition import portable_p1 as p1

ROOT = Path(__file__).resolve().parent
BASE = "bffc014cadea36c87770986a3a06afe17d503edd"
PREFIX = "experiments/gemma4_competition/"
SCOPE = {
    "validate_forgeai_gemma4_p1_procedure_prompt_1.py",
    PREFIX + "portable_p1.py", PREFIX + "tests/test_p1_candidate.py",
    PREFIX + "kaggle_compiler/p1_compiler_only.ipynb",
    PREFIX + "submission_only/first_submission.ipynb",
    PREFIX + "candidates/README.md", PREFIX + "PRIOR-ART.md",
    *(PREFIX + "candidates/p1/" + name for name in p1.MEMBERS),
}


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, stderr=subprocess.DEVNULL)


def scope_checks():
    changed = set(git("diff", "--name-only", BASE).decode().splitlines())
    changed.update(git("ls-files", "--others", "--exclude-standard").decode().splitlines())
    p1.require(changed <= SCOPE, "outside P1 scope: " + str(sorted(changed - SCOPE)))
    git("diff", "--check", BASE, "--", *sorted(SCOPE))
    p1.require("experiments/gemma4_competition/candidates/** text eol=lf"
               in (ROOT / ".gitattributes").read_text().splitlines(), "candidate LF rule missing")


def shared_gate():
    gate = p1.load_instance(ROOT / "validate_forgeai_gemma4_m2_minimal_baseline_1.py", "_p1_local_gate")
    gate.shared = p1.ENGINE
    gate.CANDIDATE = p1.CANDIDATE
    gate.static_candidate = p1.static_candidate
    return gate


def reconcile(receipt, remote):
    p1.require(receipt.is_file(), "missing receipt FILE: " + str(receipt))
    p1.require(remote.is_dir(), "missing results DIRECTORY: " + str(remote))
    p1.require(not receipt.resolve().is_relative_to(ROOT) and not remote.resolve().is_relative_to(ROOT),
               "preserve receipt/bundle/results outside repository")
    with contextlib.redirect_stdout(io.StringIO()):
        shared_gate().reconcile(receipt, remote)
    print("P1_OFFICIAL_COMPILER_VALIDATED; BYTE_IDENTITY_VERIFIED")
    print("P1_PACKAGE_VALIDATED; NO MODEL QUALITY OR SUBMISSION AUTHORIZATION")


class PhaseFailure(Exception):
    pass


def phase(label, action):
    print("[PHASE] " + label, flush=True)
    try:
        return action()
    except Exception as error:
        message = str(error) if type(error) is ValueError else type(error).__name__
        print("FAIL: " + label + ": " + message + "; later phases NOT RUN", file=sys.stderr)
        raise PhaseFailure from None


def local_checks():
    phase("exact P1 scope and working whitespace", scope_checks)
    phase("preserved wheel pins", p1.wheel_pins)
    phase("exact prompt/budgets; M2 and B2 preserved", lambda: p1.static_candidate(p1.CANDIDATE))
    for directory, pattern in (
        (PREFIX + "tests", "test_m2_minimal_baseline.py"),
        (PREFIX + "tests", "test_p1_candidate.py"),
        (PREFIX + "submission_only", "test_*.py"),
    ):
        phase("offline controls: " + pattern, lambda d=directory, p=pattern: subprocess.run(
            [sys.executable, "-B", "-m", "unittest", "discover", "-s", d, "-p", p], cwd=ROOT, check=True))
    phase("post-control scope preservation", scope_checks)
    return {"schema": 1, "state": "LOCAL_SCOPE_AND_STATIC_PASS", "candidate": "p1",
            "budgets": p1.BUDGETS, "prompt_sha256": p1.PROMPT_SHA256, "baseline": BASE,
            "git_head": git("rev-parse", "HEAD").decode().strip(), "inputs": p1.input_manifest()}


def staged_checks():
    staged = set(git("diff", "--cached", "--name-only", BASE).decode().splitlines())
    p1.require(staged <= SCOPE, "outside staged P1 scope: " + str(sorted(staged - SCOPE)))
    for name in staged:
        raw = (ROOT / name).read_bytes()
        indexed = git("show", ":" + name)
        if name.startswith(PREFIX + "candidates/p1/"):
            p1.require(raw == indexed, "candidate staged bytes differ: " + name)
        else:
            p1.require(p1.normalized(raw) == p1.normalized(indexed), "staged content differs: " + name)
    git("diff", "--cached", "--check", BASE, "--", *sorted(SCOPE))
    print("P1_PRE_COMMIT_STAGED_CONSISTENCY_PASSED")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--local-only", action="store_true")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--receipt", type=Path)
    parser.add_argument("--reconcile", type=Path)
    parser.add_argument("--pre-commit", action="store_true")
    args = parser.parse_args()
    if args.pre_commit:
        if not (args.receipt and args.reconcile):
            parser.error("--pre-commit needs --receipt and --reconcile")
        phase("exact P1 scope and working whitespace", scope_checks)
        phase("P1 evidence reconciliation", lambda: reconcile(args.receipt, args.reconcile))
        phase("separate pre-commit consistency", staged_checks)
        return 0
    if not args.local_only and not args.reconcile:
        parser.error("use --local-only or --receipt FILE --reconcile DIRECTORY")
    if args.reconcile and not args.receipt:
        parser.error("--reconcile requires --receipt FILE")
    receipt = local_checks()
    if args.reconcile:
        phase("P1 evidence reconciliation", lambda: reconcile(args.receipt, args.reconcile))
    else:
        output = args.output or Path(tempfile.mkdtemp(prefix="gemma-p1-transfer-parent-")) / "bundle"
        phase("external P1 transfer bundle", lambda: shared_gate().export_bundle(output, receipt))
        print("P1_LOCAL_SCOPE_AND_STATIC_PASS; PORTABLE COMPILATION REQUIRED")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except PhaseFailure:
        raise SystemExit(1) from None
