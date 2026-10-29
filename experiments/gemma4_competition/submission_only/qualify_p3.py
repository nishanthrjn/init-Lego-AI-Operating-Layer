"""Maintainer-only pin materialization after full reconciliation; no submission."""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def replace_entry(source, pins, candidate="p3"):
    tree = ast.parse(source)
    assignment = next(n for n in tree.body if isinstance(n, ast.Assign)
                      and any(isinstance(t, ast.Name) and t.id == "CANDIDATE_PINS" for t in n.targets))
    value = next(v for k, v in zip(assignment.value.keys, assignment.value.values)
                 if isinstance(k, ast.Constant) and k.value == candidate)
    lines = source.splitlines(keepends=True)
    start = sum(len(s) for s in lines[:value.lineno - 1]) + value.col_offset
    end = sum(len(s) for s in lines[:value.end_lineno - 1]) + value.end_col_offset
    return source[:start] + repr(pins) + source[end:]


def main(candidate="p3", guard=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--receipt", required=True, type=Path)
    parser.add_argument("--results", required=True, type=Path)
    parser.add_argument("--notebook", required=True, type=Path)
    args = parser.parse_args()
    if args.notebook.resolve().is_relative_to(ROOT) or args.notebook.exists():
        raise ValueError("fresh external notebook path required")
    sys.path.insert(0, str(ROOT))
    # Check development eligibility before reconciliation or any file mutation.
    evidence_pins = guard() if guard is not None else {}
    import importlib
    gate = importlib.import_module(f"validate_forgeai_gemma4_{candidate}_submission_qualification_1")
    gate.scope_gate().scope_checks()
    gate.reconcile(args.receipt, args.results)
    raw = (args.results / "manifest.json").read_bytes()
    manifest = json.loads(raw)
    receipt_hash = hashlib.sha256(args.receipt.read_bytes()).hexdigest()
    pins = {"manifest_sha256": hashlib.sha256(raw).hexdigest(),
            "zip_sha256": manifest["zip_sha256"], "zip_size": manifest["zip_size"],
            "receipt_sha256": receipt_hash,
            "authorization": "AUTHORIZE FORGEAI GEMMA4 SUBMISSION OF " + candidate.upper() + " PACKAGE " + receipt_hash[:8],
            "reconciled": True, "m2_result_understood": True}
    pins.update(evidence_pins)
    from generate_self_contained import build_notebook
    generated = build_notebook(candidate, pins, raw, (args.results / "submission.zip").read_bytes())
    target = HERE / "first_submission.ipynb"
    notebook = json.loads(target.read_bytes())
    cell = next(c for c in notebook["cells"] if c["id"] == "copy-helper")
    cell["source"] = replace_entry("".join(cell["source"]), pins, candidate).splitlines(keepends=True)
    with args.notebook.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(generated, indent=2) + "\n")
    target.write_text(json.dumps(notebook, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"candidate": candidate, "notebook": str(args.notebook), **pins}))
    print(candidate.upper() + "_SUBMISSION_PREPARATION_READY; PRE_COMMIT_CHECK_REQUIRED; NO_SUBMISSION_EXECUTED")


if __name__ == "__main__":
    main()
