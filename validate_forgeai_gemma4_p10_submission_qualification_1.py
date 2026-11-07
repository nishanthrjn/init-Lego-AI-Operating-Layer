"""P10 qualification configuration; reuses P3 orchestration and M2 algorithms."""
from pathlib import Path
import sys
from experiments.gemma4_competition import portable_p10 as p10

ROOT = Path(__file__).resolve().parent
from experiments.gemma4_competition import qualification_pair as pair
BASE = pair.BASE
PREFIX = "experiments/gemma4_competition/"
SCOPE = pair.SCOPE
GATE = p10.load_instance(ROOT / "validate_forgeai_gemma4_p3_submission_qualification_1.py", "_p10_qualification")
GATE.p3, GATE.BASE, GATE.SCOPE, GATE.CANDIDATE_NAME = p10, BASE, SCOPE, "p10"
_original_scope = GATE.scope_gate


def scope_gate():
    gate = _original_scope()
    original = gate.scope_checks

    def checked_scope():
        p10.require(gate.git("branch", "--show-current").decode().strip() == "br-ForgeAI-Gemma4",
                   "P10 requires br-ForgeAI-Gemma4")
        gate.git("merge-base", "--is-ancestor", BASE, "HEAD")
        original()
        # Inspect the index independently: a working-tree reversal cannot hide an edit.
        staged = set(gate.git("diff", "--cached", "--name-only", BASE).decode().splitlines())
        p10.require(staged <= SCOPE, "outside staged P10 scope")

    original_staged = gate.staged_checks

    def checked_staged():
        changed = set(gate.git("diff", "--name-only", BASE).decode().splitlines())
        changed.update(gate.git("ls-files", "--others", "--exclude-standard").decode().splitlines())
        staged = set(gate.git("diff", "--cached", "--name-only", BASE).decode().splitlines())
        p10.require(changed == staged, "P10 reviewed changes must all be staged")
        original_staged()

    gate.staged_checks = checked_staged
    gate.scope_checks = checked_scope
    return gate


GATE.scope_gate = scope_gate
_development = p10.load_instance(
    ROOT / PREFIX / "submission_only/qualify_p10.py", "_p10_development")
_original_reconcile = GATE.reconcile


def reconcile(receipt, remote):
    pair.require_frozen(receipt)
    _development.require_qualification_gate()
    return _original_reconcile(receipt, remote)


def main():
    # Block before scope commands, tests, installations, compilation or writes.
    _development.require_qualification_gate()
    pair.require_frozen()
    return GATE.main()


GATE.reconcile = reconcile

if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print("FAIL: P10 qualification: " + (str(error) if type(error) is ValueError else type(error).__name__), file=sys.stderr)
        raise SystemExit(1) from None
