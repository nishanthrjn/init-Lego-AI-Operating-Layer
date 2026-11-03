"""P7A qualification configuration; reuses P3 orchestration and M2 algorithms."""
from pathlib import Path
import sys
from experiments.gemma4_competition import portable_p7a as p7a

ROOT = Path(__file__).resolve().parent
BASE = "1f1084d4cef7effe58eb8fbb1a4795376d5259a2"
PREFIX = "experiments/gemma4_competition/"
SCOPE = {
    "validate_forgeai_gemma4_p7a_submission_qualification_1.py",
    PREFIX + "portable_p7a.py",
    PREFIX + "tests/test_p7a_qualification.py",
    PREFIX + "kaggle_compiler/p7a_compiler_only.ipynb",
    PREFIX + "submission_only/qualify_p7a.py",
    PREFIX + "submission_only/test_p7a_submission.py",
    PREFIX + "submission_only/generate_self_contained.py",
    PREFIX + "submission_only/first_submission.ipynb",
    PREFIX + "README.md", PREFIX + "local_eval/README.md",
    PREFIX + "results/dev-16v-comparison.json", PREFIX + "results/dev-16v-comparison.md",
    PREFIX + "results/paper-evidence.json", PREFIX + "results/submissions.json",
}
GATE = p7a.load_instance(ROOT / "validate_forgeai_gemma4_p3_submission_qualification_1.py", "_p7a_qualification")
GATE.p3, GATE.BASE, GATE.SCOPE, GATE.CANDIDATE_NAME = p7a, BASE, SCOPE, "p7a"
_original_scope = GATE.scope_gate


def scope_gate():
    gate = _original_scope()
    original = gate.scope_checks

    def checked_scope():
        p7a.require(gate.git("branch", "--show-current").decode().strip() == "br-ForgeAI-Gemma4",
                   "P7A requires br-ForgeAI-Gemma4")
        gate.git("merge-base", "--is-ancestor", BASE, "HEAD")
        original()
        # Inspect the index independently: a working-tree reversal cannot hide an edit.
        staged = set(gate.git("diff", "--cached", "--name-only", BASE).decode().splitlines())
        p7a.require(staged <= SCOPE, "outside staged P7A scope")

    original_staged = gate.staged_checks

    def checked_staged():
        changed = set(gate.git("diff", "--name-only", BASE).decode().splitlines())
        changed.update(gate.git("ls-files", "--others", "--exclude-standard").decode().splitlines())
        staged = set(gate.git("diff", "--cached", "--name-only", BASE).decode().splitlines())
        p7a.require(changed == staged, "P7A reviewed changes must all be staged")
        original_staged()

    gate.staged_checks = checked_staged
    gate.scope_checks = checked_scope
    return gate


GATE.scope_gate = scope_gate
_development = p7a.load_instance(
    ROOT / PREFIX / "submission_only/qualify_p7a.py", "_p7a_development")
_original_reconcile = GATE.reconcile


def reconcile(receipt, remote):
    _development.require_confirmation_gate()
    return _original_reconcile(receipt, remote)


def main():
    # Block before scope commands, tests, installations, compilation or writes.
    _development.require_confirmation_gate()
    return GATE.main()


GATE.reconcile = reconcile

if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print("FAIL: P7A qualification: " + (str(error) if type(error) is ValueError else type(error).__name__), file=sys.stderr)
        raise SystemExit(1) from None
