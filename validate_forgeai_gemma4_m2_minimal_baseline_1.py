"""Local repository gate and reconciliation for the shared portable M2 compiler.

Maintainer execution only. Staged consistency is a distinct --pre-commit phase.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from experiments.gemma4_competition import portable_m2 as shared
# Existing policy tests continue exercising the same shared implementation.
from experiments.gemma4_competition.portable_m2 import (
    CANDIDATE, MEMBERS, MODEL, OfflineViolation, deny_effects, environment_preflight,
    inspect_zip, metadata, normalized, require, sha, static_candidate, zip_bytes,
)

ROOT = Path(__file__).resolve().parent
# Parent of the scoped-install slice; preserves the maintainer's committed
# wheel-untracking, ignore policy and historical transfer evidence.
BASE = "0bfa26c9d6f6678f6b1b6048a596a5f130273599"
SCOPE = {
    ".gitattributes",
    "validate_forgeai_gemma4_m2_minimal_baseline_1.py",
    "experiments/gemma4_competition/portable_m2.py",
    "experiments/gemma4_competition/tests/test_m2_minimal_baseline.py",
    "experiments/gemma4_competition/kaggle_compiler/README.md",
    "experiments/gemma4_competition/kaggle_compiler/compiler_only.ipynb",
}

# Existing maintainer evidence is immutable and is not part of this edit scope.
PRESERVED_EVIDENCE = {
    "experiments/gemma4_competition/evidence/gemma-m2-transfer-parent-4eyj8s5t/bundle.zip": "446620fd4d75bfb8388f134cc0501850ea5fa0e39f7568a4a6387fc15d2a5fd2",
    "experiments/gemma4_competition/evidence/m2-bundle-a7956ced/bundle.zip": "660a64ffb4a14595136eefb01ba75da03732b9ef520ab3165c6f108e23de9a17"
}


def git(*args: str) -> bytes:
    return subprocess.check_output(["git", *args], cwd=ROOT, stderr=subprocess.DEVNULL)


def scope_checks() -> None:
    changed = set(git("diff", "--name-only", BASE).decode().splitlines())
    changed.update(git("ls-files", "--others", "--exclude-standard").decode().splitlines())
    for name, digest in PRESERVED_EVIDENCE.items():
        require(sha((ROOT / name).read_bytes()) == digest, "preserved evidence changed: " + name)
    require(changed - PRESERVED_EVIDENCE.keys() <= SCOPE, "outside approved portable factoring scope: " + str(sorted(changed - SCOPE)))
    git("diff", "--check", BASE, "--", *sorted(SCOPE))
    for name in SCOPE:
        data = normalized((ROOT / name).read_bytes())
        require(data.endswith(b"\n"), "missing final newline: " + name)
        require(all(line.rstrip(b" \t") == line for line in data.splitlines()), "trailing whitespace: " + name)
    # Candidate/evidence/environment specifications are not in the mutation scope.
    require((ROOT / ".gitattributes").read_text().strip()
            == "experiments/gemma4_competition/baseline/** text eol=lf", "LF attribute policy")


def staged_checks() -> None:
    staged = set(git("diff", "--cached", "--name-only", BASE).decode().splitlines())
    require(staged - PRESERVED_EVIDENCE.keys() <= SCOPE, "outside staged scope")
    for name in staged & PRESERVED_EVIDENCE.keys():
        require(sha(git("show", ":" + name)) == PRESERVED_EVIDENCE[name], "staged preserved evidence changed")
    for name in staged & SCOPE:
        require(normalized(git("show", ":" + name)) == normalized((ROOT / name).read_bytes()),
                "staged content differs: " + name)
    for name in MEMBERS:
        relative = "experiments/gemma4_competition/baseline/" + name
        require(git("show", ":" + relative) == (ROOT / relative).read_bytes(), "candidate index bytes differ")
    git("diff", "--cached", "--check", BASE, "--", *sorted(SCOPE))
    print("M2_PRE_COMMIT_STAGED_CONSISTENCY_PASSED")


def local_checks() -> dict:
    print("[PHASE] exact local scope and working whitespace", flush=True)
    scope_checks()
    print("[PHASE] preserved wheel pins and exact candidate bytes", flush=True)
    shared.wheel_pins()
    static_candidate(CANDIDATE)
    print("[PHASE] offline policy, scoped-install and packaging controls", flush=True)
    subprocess.run([sys.executable, "-B", "-m", "unittest", "discover", "-s",
                    "experiments/gemma4_competition/tests", "-p", "test_m2_minimal_baseline.py"],
                   cwd=ROOT, check=True)
    print("[PHASE] post-control scope preservation", flush=True)
    scope_checks()
    print("M2_BASELINE_LOCAL_STATIC_CHECKS_PASSED")
    return {"schema": 1, "state": "LOCAL_SCOPE_AND_STATIC_PASS", "baseline": BASE,
            "git_head": git("rev-parse", "HEAD").decode().strip(), "inputs": shared.input_manifest()}


def export_bundle(output: Path, receipt: dict) -> Path:
    require(not output.resolve().is_relative_to(ROOT), "transfer output must be outside repository")
    output.mkdir(parents=True, exist_ok=False)
    for name in shared.transfer_paths():
        destination = output / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, destination)
        require(sha(destination.read_bytes()) == receipt["inputs"][name]["sha256"], "copy changed bytes")
    path = output / "local-receipt.json"
    path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("transfer bundle: " + str(output))
    print("local receipt SHA256: " + sha(path.read_bytes()))
    return path


def reconcile(receipt: Path, remote: Path) -> None:
    shared.verify_local_receipt(receipt)
    install_path = remote / "install-evidence.json"
    install = shared.verify_install_evidence(install_path, sha(receipt.read_bytes()))
    manifest = json.loads((remote / "manifest.json").read_text(encoding="utf-8"))
    require(manifest.get("install_evidence") == install
            and manifest.get("install_evidence_sha256") == sha(install_path.read_bytes()),
            "install evidence manifest mismatch")
    require(manifest.get("official_environment_deviations") == install["pip_check"]["findings"],
            "manifest deviations differ from re-derived findings")
    compiler = json.loads((remote / "compiler-output.json").read_text(encoding="utf-8"))
    require(manifest.get("state") == "PORTABLE_COMPILE_AND_PACKAGE_PASS"
            and compiler.get("state") == "compiler_validated", "portable pass missing")
    require(manifest.get("local_receipt_sha256") == sha(receipt.read_bytes()), "receipt mismatch")
    require(manifest.get("inputs") == shared.input_manifest(), "returned evidence bound to other inputs")
    require(manifest.get("environment") == compiler.get("versions"), "package version evidence mismatch")
    data = static_candidate(CANDIDATE)
    require(manifest.get("members") == [{"path": n, "sha256": sha(data[n]), "size": len(data[n])}
                                       for n in sorted(data)], "member manifest mismatch")
    blob = (remote / "submission.zip").read_bytes()
    inspect_zip(blob, data)
    require(blob == zip_bytes(data) and manifest.get("zip_sha256") == sha(blob)
            and manifest.get("zip_size") == len(blob), "returned ZIP mismatch")
    require(manifest.get("wheel_sha256") == {n: sha(p.read_bytes()) for n, p in shared.wheel_pins().items()},
            "returned wheel evidence mismatch")
    print("M2_BASELINE_OFFICIAL_COMPILER_VALIDATED; LOCAL_SCOPE_PASS + PORTABLE_COMPILE_PASS; BYTE_IDENTITY_VERIFIED")
    print("M2_BASELINE_PACKAGE_VALIDATED; NO MODEL QUALITY OR KAGGLE ACCEPTANCE CLAIMED")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--local-only", action="store_true")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--receipt", type=Path)
    parser.add_argument("--reconcile", type=Path)
    parser.add_argument("--pre-commit", action="store_true")
    args = parser.parse_args()
    if args.pre_commit:
        require(args.receipt is not None and args.reconcile is not None,
                "pre-commit requires completed portable evidence and receipt")
        scope_checks()
        reconcile(args.receipt, args.reconcile)
        staged_checks()
        return 0
    receipt = local_checks()
    if args.reconcile:
        require(args.receipt is not None, "original local receipt required")
        reconcile(args.receipt, args.reconcile)
        return 0
    output = args.output or Path(tempfile.mkdtemp(prefix="gemma-m2-transfer-parent-")) / "bundle"
    receipt_path = export_bundle(output, receipt)
    if args.local_only:
        print("LOCAL_SCOPE_AND_STATIC_PASS; PORTABLE COMPILATION STILL REQUIRED")
        return 0
    result = shared.run_portable(receipt_path, output / "compiler-results")
    if result == 0:
        reconcile(receipt_path, output / "compiler-results")
    return result


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print("FAIL: " + type(error).__name__ + "; later phases NOT RUN", file=sys.stderr)
        raise SystemExit(1) from None
