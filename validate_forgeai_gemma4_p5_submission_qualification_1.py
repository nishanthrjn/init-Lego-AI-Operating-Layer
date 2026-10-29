"""P5 qualification configuration; reuses P3 orchestration and M2 algorithms."""
from pathlib import Path
import sys
from experiments.gemma4_competition import portable_p5 as p5

ROOT = Path(__file__).resolve().parent
BASE = "f65224bd1ced125ccf8de5016762ee882173d755"
PREFIX = "experiments/gemma4_competition/"
SCOPE = {
    "validate_forgeai_gemma4_p3_submission_qualification_1.py",
    "validate_forgeai_gemma4_p5_submission_qualification_1.py",
    PREFIX + "portable_p3.py", PREFIX + "portable_p5.py",
    PREFIX + "tests/test_p5_qualification.py",
    PREFIX + "kaggle_compiler/p5_compiler_only.ipynb",
    PREFIX + "submission_only/qualify_p3.py", PREFIX + "submission_only/qualify_p5.py",
    PREFIX + "submission_only/test_p5_submission.py",
    PREFIX + "submission_only/generate_self_contained.py",
    PREFIX + "submission_only/first_submission.ipynb",
    PREFIX + "README.md",
    PREFIX + "results/dev-16v-comparison.json", PREFIX + "results/dev-16v-comparison.md",
    PREFIX + "results/paper-evidence.json", PREFIX + "results/submissions.json",
}
GATE = p5.load_instance(ROOT / "validate_forgeai_gemma4_p3_submission_qualification_1.py", "_p5_qualification")
GATE.p3, GATE.BASE, GATE.SCOPE, GATE.CANDIDATE_NAME = p5, BASE, SCOPE, "p5"
_original_scope = GATE.scope_gate


def scope_gate():
    gate = _original_scope()
    original = gate.scope_checks

    def checked_scope():
        p5.require(gate.git("branch", "--show-current").decode().strip() == "br-ForgeAI-Gemma4",
                   "P5 requires br-ForgeAI-Gemma4")
        gate.git("merge-base", "--is-ancestor", BASE, "HEAD")
        original()
        # Inspect the index independently: a working-tree reversal cannot hide an edit.
        staged = set(gate.git("diff", "--cached", "--name-only", BASE).decode().splitlines())
        p5.require(staged <= SCOPE, "outside staged P5 scope")

    original_staged = gate.staged_checks

    def checked_staged():
        changed = set(gate.git("diff", "--name-only", BASE).decode().splitlines())
        changed.update(gate.git("ls-files", "--others", "--exclude-standard").decode().splitlines())
        staged = set(gate.git("diff", "--cached", "--name-only", BASE).decode().splitlines())
        p5.require(changed == staged, "P5 reviewed changes must all be staged")
        original_staged()

    gate.staged_checks = checked_staged
    gate.scope_checks = checked_scope
    return gate


GATE.scope_gate = scope_gate
reconcile = GATE.reconcile
main = GATE.main

if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print("FAIL: P5 qualification: " + (str(error) if type(error) is ValueError else type(error).__name__), file=sys.stderr)
        raise SystemExit(1) from None
