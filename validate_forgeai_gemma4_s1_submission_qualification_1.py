"""S1 qualification configuration; reuses P3 orchestration and M2 algorithms."""
from pathlib import Path
import sys
from experiments.gemma4_competition import portable_s1 as s1

ROOT = Path(__file__).resolve().parent
BASE = "a46674ce4e77eed7ef2c315185a8a3f53df5fb15"
PREFIX = "experiments/gemma4_competition/"
SCOPE = {
    "validate_forgeai_gemma4_s1_submission_qualification_1.py",
    PREFIX + "portable_s1.py",
    PREFIX + "tests/test_s1_qualification.py",
    PREFIX + "kaggle_compiler/s1_compiler_only.ipynb",
    PREFIX + "submission_only/qualify_s1.py",
    PREFIX + "submission_only/test_s1_submission.py",
    PREFIX + "submission_only/generate_self_contained.py",
    PREFIX + "submission_only/first_submission.ipynb",
    PREFIX + "README.md", PREFIX + "local_eval/README.md",
    PREFIX + "results/dev-16v-comparison.json", PREFIX + "results/dev-16v-comparison.md",
    PREFIX + "results/paper-evidence.json", PREFIX + "results/submissions.json",
}
GATE = s1.load_instance(ROOT / "validate_forgeai_gemma4_p3_submission_qualification_1.py", "_s1_qualification")
GATE.p3, GATE.BASE, GATE.SCOPE, GATE.CANDIDATE_NAME = s1, BASE, SCOPE, "s1"
_original_scope = GATE.scope_gate


def scope_gate():
    gate = _original_scope()
    original = gate.scope_checks

    def checked_scope():
        s1.require(gate.git("branch", "--show-current").decode().strip() == "br-ForgeAI-Gemma4",
                   "S1 requires br-ForgeAI-Gemma4")
        gate.git("merge-base", "--is-ancestor", BASE, "HEAD")
        original()
        # Inspect the index independently: a working-tree reversal cannot hide an edit.
        staged = set(gate.git("diff", "--cached", "--name-only", BASE).decode().splitlines())
        s1.require(staged <= SCOPE, "outside staged S1 scope")

    original_staged = gate.staged_checks

    def checked_staged():
        changed = set(gate.git("diff", "--name-only", BASE).decode().splitlines())
        changed.update(gate.git("ls-files", "--others", "--exclude-standard").decode().splitlines())
        staged = set(gate.git("diff", "--cached", "--name-only", BASE).decode().splitlines())
        s1.require(changed == staged, "S1 reviewed changes must all be staged")
        original_staged()

    gate.staged_checks = checked_staged
    gate.scope_checks = checked_scope
    return gate


GATE.scope_gate = scope_gate
_development = s1.load_instance(
    ROOT / PREFIX / "submission_only/qualify_s1.py", "_s1_development")
_original_reconcile = GATE.reconcile


def reconcile(receipt, remote):
    _development.require_qualification_gate()
    return _original_reconcile(receipt, remote)


def main():
    # Block before scope commands, tests, installations, compilation or writes.
    _development.require_qualification_gate()
    return GATE.main()


GATE.reconcile = reconcile

if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print("FAIL: S1 qualification: " + (str(error) if type(error) is ValueError else type(error).__name__), file=sys.stderr)
        raise SystemExit(1) from None
