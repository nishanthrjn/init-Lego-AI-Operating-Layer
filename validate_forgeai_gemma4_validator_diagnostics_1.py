"""Read-only diagnostics for already qualified M2/B2 evidence; maintainer execution only.

The original validators remain receipt-bound. Reconciliation executes their exact
preserved source, never a changed current compiler notebook or relaxed hash check.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path, PurePosixPath
import subprocess
import sys
import tempfile
from types import ModuleType

ROOT = Path(__file__).resolve().parent
PREFIX = "experiments/gemma4_competition/"
PARENT = "b319b8c76615a1705623fddbeb73d52b51605cdd"
SLICE = "c636bac7c3dd7ff23f41f104f26f7c3b77c44fae"
README = PREFIX + "candidates/README.md"
SLICE_FILES = {
    ".gitattributes", "validate_forgeai_gemma4_b2_candidate_1.py",
    PREFIX + "portable_b2.py", PREFIX + "tests/test_b2_candidate.py",
    README, PREFIX + "results/submissions.json",
    PREFIX + "kaggle_compiler/b2_compiler_only.ipynb",
    PREFIX + "submission_only/first_submission.ipynb",
    PREFIX + "submission_only/README.md",
    PREFIX + "submission_only/test_candidate_selection.py",
    *(PREFIX + "candidates/b2/" + name for name in (
        "agent.yaml", "eval_config.yaml", "prompts/system.md", "configs/sampling.yaml")),
}
DIAGNOSTIC_FILES = {
    "validate_forgeai_gemma4_validator_diagnostics_1.py",
    PREFIX + "tests/test_validator_diagnostics.py", README,
}
RECEIPTS = {
    "m2": "ca6a05b46844c86369c7aaef3d989b542c5f3c5f63fcc91c7fce5997742893d9",
    "b2": "d7195f13fc0f4da056e003317d72c6d46f5b5acb0521742515721684d01f383f",
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, stderr=subprocess.DEVNULL)


def names(*args):
    return set(git(*args).decode().splitlines())


def scope_checks():
    require(git("rev-parse", SLICE + "^").decode().strip() == PARENT,
            "B2 parent commit differs from pinned parent")
    require(git("merge-base", SLICE, "HEAD").decode().strip() == SLICE,
            "HEAD does not contain the pinned B2 slice")
    original = names("diff", "--name-only", PARENT, SLICE)
    require(original == SLICE_FILES, "pinned B2 slice file set differs")
    # Later unrelated commits are not part of the original B2 slice. They cannot
    # change any of its implementation files. README is this task's sole doc exception.
    changed = names("diff", "--name-only", SLICE, "HEAD", "--", *sorted(SLICE_FILES - {README}))
    require(not changed, "committed B2 slice changed: " + str(sorted(changed)))
    dirty = names("diff", "--name-only", "HEAD")
    dirty |= names("ls-files", "--others", "--exclude-standard")
    require(dirty <= DIAGNOSTIC_FILES,
            "outside diagnostic edit scope: " + str(sorted(dirty - DIAGNOSTIC_FILES)))
    # Do not allow the documentation exception to rewrite the historical note.
    before = git("show", SLICE + ":" + README).replace(b"\r\n", b"\n")
    current = (ROOT / README).read_bytes().replace(b"\r\n", b"\n")
    require(current.startswith(before), "historical B2 README changed; append only")


def external_path(path, description, directory=False):
    require(not path.resolve().is_relative_to(ROOT.resolve()),
            description + " must be outside the repository")
    require(path.is_dir() if directory else path.is_file(),
            "missing " + description + ": " + str(path))


def preserved_bundle(candidate, receipt, results):
    external_path(receipt, "receipt file")
    external_path(results, "results directory", directory=True)
    for name in ("install-evidence.json", "compiler-output.json", "manifest.json", "submission.zip"):
        require((results / name).is_file(), "missing results file: " + str(results / name))
    raw = receipt.read_bytes()
    require(digest(raw) == RECEIPTS[candidate], "receipt SHA256 differs for " + candidate)
    data = json.loads(raw)
    root = receipt.parent.resolve()
    for name, pin in data["inputs"].items():
        relative = PurePosixPath(name)
        require(not relative.is_absolute() and ".." not in relative.parts and "\\" not in name,
                "unsafe receipt input path")
        path = root.joinpath(*relative.parts)
        require(path.resolve().is_relative_to(root) and path.is_file(),
                "missing or unsafe preserved input: " + name)
        blob = path.read_bytes()
        require(len(blob) == pin["size"] and digest(blob) == pin["sha256"],
                "preserved input SHA256/size mismatch: " + name)
    # Candidate bytes in today's checkout must still be the qualified bytes.
    directory = "baseline/" if candidate == "m2" else "candidates/b2/"
    for name in ("agent.yaml", "eval_config.yaml", "prompts/system.md", "configs/sampling.yaml"):
        relative = PREFIX + directory + name
        require((ROOT / relative).is_file(), "missing current candidate: " + relative)
        require((ROOT / relative).read_bytes() == (root / relative).read_bytes(),
                "current candidate bytes changed: " + relative)
    return root


def historical_reconcile(candidate, bundle, receipt, results):
    raw = receipt.read_bytes()
    require(digest(raw) == RECEIPTS[candidate], "receipt changed before reconciliation")
    with tempfile.TemporaryDirectory(prefix="gemma-preserved-validator-") as temporary:
        snapshot = Path(temporary)
        for name, pin in json.loads(raw)["inputs"].items():
            blob = (bundle / name).read_bytes()
            require(digest(blob) == pin["sha256"] and len(blob) == pin["size"],
                    "preserved input changed before reconciliation: " + name)
            target = snapshot / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(blob)
        copied_receipt = snapshot / "local-receipt.json"
        copied_receipt.write_bytes(raw)
        # A fresh snapshot excludes unpinned __pycache__/package initializer files.
        load_and_reconcile(candidate, snapshot, copied_receipt, results)


def load_and_reconcile(candidate, bundle, receipt, results):
    # Only hash-authenticated local source is loaded. No compile, install, model,
    # tests or live calls: invoke the preserved reconciliation function directly.
    target = ("validate_forgeai_gemma4_m2_minimal_baseline_1.py" if candidate == "m2"
              else "validate_forgeai_gemma4_b2_candidate_1.py")
    require(target in json.loads(receipt.read_bytes())["inputs"], "validator absent from receipt")
    require(not any(n == "experiments" or n.startswith("experiments.") for n in sys.modules),
            "historical reconciliation requires a fresh interpreter")
    # Explicit namespace paths prevent an unpinned __init__.py or a package in
    # today's checkout from replacing the authenticated historical modules.
    for name, relative in (("experiments", "experiments"),
                           ("experiments.gemma4_competition", "experiments/gemma4_competition")):
        package = ModuleType(name)
        package.__path__ = [str(bundle / relative)]
        sys.modules[name] = package
    try:
        spec = importlib.util.spec_from_file_location("_preserved_validator", bundle / target)
        require(spec is not None and spec.loader is not None, "preserved validator loader unavailable")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.reconcile(receipt, results)
    finally:
        for name in list(sys.modules):
            if name == "experiments" or name.startswith("experiments."):
                del sys.modules[name]


class ReportedFailure(Exception):
    pass


def phase(label, action):
    print("[PHASE] " + label, flush=True)
    try:
        return action()
    except Exception as error:
        # Only our/plain contract ValueErrors are printable. Other exception
        # subclasses may contain payloads; never dump tracebacks or environment.
        detail = str(error) if type(error) is ValueError else type(error).__name__
        print("FAIL: " + label + ": " + detail + "; later phases NOT RUN", file=sys.stderr)
        raise ReportedFailure from None


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", choices=tuple(RECEIPTS), required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--reconcile", type=Path, required=True)
    args = parser.parse_args(argv)
    sys.dont_write_bytecode = True
    phase("exact committed B2 scope and diagnostic working scope", scope_checks)
    bundle = phase("preserved receipt, source pins and exact candidate bytes",
                   lambda: preserved_bundle(args.candidate, args.receipt, args.reconcile))
    phase("historical " + args.candidate.upper() + " evidence reconciliation",
          lambda: historical_reconcile(args.candidate, bundle, args.receipt, args.reconcile))
    print("HISTORICAL_PACKAGE_RECONCILED; CURRENT_CHECKOUT_COMPILER_NOT_QUALIFIED")
    return 0


def cli(argv=None):
    try:
        return main(argv)
    except ReportedFailure:
        return 1


if __name__ == "__main__":
    raise SystemExit(cli())
