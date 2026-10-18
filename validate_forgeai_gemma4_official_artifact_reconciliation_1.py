"""Offline documentary checks only; maintainer execution required."""

import base64
import csv
import hashlib
import io
import zipfile
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BASELINE = "52b09fb84e72dde5a5855822fb674772817976c9"
SELF = "validate_forgeai_gemma4_official_artifact_reconciliation_1.py"
DIRECTORY = "experiments/gemma4_competition/"
REGISTER = DIRECTORY + "source-register.json"
CONTRACT = DIRECTORY + "OFFICIAL-CONTRACT-REGISTER.md"
DECISION = "M1_PARTIAL_M2_BASELINE_CONDITIONALLY_UNBLOCKED"
HISTORICAL_DECISION = "M1_PARTIAL_ADDITIONAL_ARTIFACTS_REQUIRED"
PINS = {
    "experiments/gemma4_competition/source-register.json": "5672f8742ce26f1169b874fa3398fca3f80accc5f514eda06c62c4fe9e2b4caf",
    "experiments/gemma4_competition/OFFICIAL-CONTRACT-REGISTER.md": "37faae477bc39915db1b23c3a3c4c36e0cd7708560dcbae4785a0da89166e72a",
    "planning/FORGEAI-GEMMA4-COMPETITION-READINESS-1.md": "283c75ba8e9e0577865e48b364b5b8a46e0918418d04c80ed8396c6609468b39",
    "planning/GEMMA4-COMPETITION-REQUIREMENTS.md": "18edabe76bc58c0075b1dc200192c49cc7e5665691a332ac5694d7e132de906d",
    "planning/GEMMA4-RESEARCH-PLAN.md": "e25d3d5ff24725c439dfe101ee5e370e16b066d04279dda22276a5399c1a5044",
    "planning/GEMMA4-IMPLEMENTATION-MILESTONES.md": "d709be02106704e77c3a2a3ad063c87c0fefef930d46b8ffe3a4471ab32fcfbf"
}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def normalized(data: bytes) -> bytes:
    return data.replace(b"\r\n", b"\n")


def git(*args: str) -> bytes:
    return subprocess.run(
        ["git", *args], cwd=ROOT, check=True, capture_output=True, timeout=30
    ).stdout


def documents(values: dict[str, bytes]) -> None:
    for name, expected in PINS.items():
        data = normalized(values[name])
        if digest(data) != expected:
            raise ValueError("document content changed: " + name)
        text = data.decode("utf-8")
        if not text.endswith("\n") or text.endswith("\n\n"):
            raise ValueError("final newline: " + name)
        if any(line.rstrip() != line for line in text.splitlines()):
            raise ValueError("whitespace: " + name)
    register = json.loads(values[REGISTER])
    if register["decision"] != DECISION or register["m1_status"] != "PARTIAL":
        raise ValueError("unsupported M1 closure")
    if len(register["official_files"]) != 65:
        raise ValueError("artifact inventory changed")
    acquisition = register["acquisition_review"]
    if (
        acquisition["task"] != "FORGEAI-GEMMA4-HARNESS-ARTIFACT-ACQUISITION-1"
        or acquisition["decision"] != HISTORICAL_DECISION
        or acquisition["new_artifacts_supplied"] is not True
        or acquisition["prior_reconciliation_validation"] != "MAINTAINER_REPORTED_PASS"
    ):
        raise ValueError("acquisition boundary changed")
    expected_inventory = [
        {key: entry[key] for key in ("path", "size_bytes", "sha256")}
        for entry in register["official_files"]
        if not entry["path"].startswith("docs/archive/")
    ]
    if acquisition["observed_artifacts"] != expected_inventory:
        raise ValueError("observed inventory differs from preserved pins")
    review = register["implementation_review"]
    if (
        review["task"] != "FORGEAI-GEMMA4-VERSIONED-HARNESS-IMPLEMENTATION-1"
        or review["decision"] != HISTORICAL_DECISION
        or len(review["packages"]) != 41
    ):
        raise ValueError("implementation review boundary changed")
    entrypoint = register["scorer_entrypoint_review"]
    if (
        entrypoint["decision"] != DECISION
        or entrypoint["baseline_model"] != "gemma-4-31b-it-qat-w4a16-ct"
        or entrypoint["prior_implementation_validation"] != "MAINTAINER_REPORTED_PASS"
        or entrypoint["scope"] != "BASELINE_CONSTRUCTION_AND_OFFLINE_VALIDATION_ONLY; NO LIVE_EXECUTION_OR_SUBMISSION"
    ):
        raise ValueError("conditional baseline boundary changed")
    contract = values[CONTRACT].decode("utf-8")
    for required in (
        DECISION, "Root fields only:", "HARNESS_README", "C2", "NOT RUN",
        "NO IMPLEMENTATION, LIVE EXECUTION OR SUBMISSION AUTHORIZED.",
        *("| R" + str(i) + " |" for i in range(1, 8)),
    ):
        if required not in contract:
            raise ValueError(f"missing documentary boundary: {required!r}")


def artifact(data: bytes, entry: dict) -> None:
    if len(data) != entry["size_bytes"] or digest(data) != entry["sha256"]:
        raise ValueError("artifact bytes changed: " + entry["path"])


def wheel_evidence(register: dict) -> None:
    # Standard-library ZIP/CSV inspection only; never import wheel members.
    for package in register["implementation_review"]["packages"]:
        path = ROOT / DIRECTORY / package["path"]
        with zipfile.ZipFile(path) as archive:
            names = archive.namelist()
            if len(set(names)) != len(names):
                raise ValueError("duplicate wheel members")
            for member in package["members"]:
                data = archive.read(member["path"])
                if len(data) != member["size_bytes"] or digest(data) != member["sha256"]:
                    raise ValueError("wheel member pin mismatch")
            if package["name"].replace("-", "_") not in {
                "adk_submission", "adk_eval_core", "swegemma"
            }:
                continue
            record = next(n for n in names if n.endswith(".dist-info/RECORD"))
            rows = list(csv.reader(io.StringIO(archive.read(record).decode("utf-8"))))
            recorded = set()
            for name, encoded_hash, size in rows:
                if name in recorded or name not in names:
                    raise ValueError("invalid RECORD member")
                recorded.add(name)
                data = archive.read(name)
                if name == record and not encoded_hash and not size:
                    continue
                algorithm, expected = encoded_hash.split("=", 1)
                if algorithm != "sha256" or int(size) != len(data):
                    raise ValueError("unsupported RECORD hash or size mismatch")
                actual = base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b"=").decode()
                if actual != expected:
                    raise ValueError("RECORD digest mismatch")
            if recorded != {n for n in names if not n.endswith("/")}:
                raise ValueError("RECORD inventory mismatch")


def main() -> int:
    phase = "document and artifact scope; production preserved"
    try:
        print("[PHASE] " + phase, flush=True)
        values = {name: (ROOT / name).read_bytes() for name in PINS}
        documents(values)
        entries = json.loads(values[REGISTER])["official_files"]
        artifacts = {DIRECTORY + entry["path"]: entry for entry in entries}
        allowed = {
            REGISTER, CONTRACT, SELF,

            "planning/GEMMA4-COMPETITION-REQUIREMENTS.md",
            "planning/GEMMA4-IMPLEMENTATION-MILESTONES.md",
        }
        changed = set(git("diff", "--name-only", "--no-renames", BASELINE).decode().splitlines())
        staged = set(git("diff", "--cached", "--name-only", "--no-renames", BASELINE).decode().splitlines())
        changed |= staged
        changed |= set(git("ls-files", "--others", "--exclude-standard").decode().splitlines())
        if changed - allowed:
            raise ValueError("outside reconciliation scope: " + repr(changed - allowed))
        for name in set(PINS) | set(artifacts) | {SELF}:
            path = ROOT / name
            if not path.is_file() or any(part.is_symlink() for part in (path, *path.parents)):
                raise ValueError("missing or symlinked file: " + name)
        found = {
            p.relative_to(ROOT).as_posix()
            for p in (ROOT / DIRECTORY / "docs").rglob("*") if p.is_file()
        }
        if found != set(artifacts):
            raise ValueError("unregistered or missing artifact")
        phase = "raw byte pins and documentary positive/negative controls"
        print("\n[PHASE] " + phase, flush=True)
        for name, entry in artifacts.items():
            data = (ROOT / name).read_bytes()
            artifact(data, entry)
            try:
                artifact(data + b"CHANGED", entry)
            except ValueError:
                pass
            else:
                raise ValueError("altered artifact accepted")
        wheel_evidence(json.loads(values[REGISTER]))
        for name in PINS:
            bad = dict(values)
            bad[name] = bad[name] + b"UNSUPPORTED CLOSURE"
            try:
                documents(bad)
            except ValueError:
                pass
            else:
                raise ValueError("altered document accepted")
        phase = "staged content consistency and whitespace"
        print("\n[PHASE] " + phase, flush=True)
        indexed = dict(values)
        for name in staged & set(PINS):
            indexed[name] = git("show", ":" + name)
        documents(indexed)
        for name in staged & set(artifacts):
            artifact(git("show", ":" + name), artifacts[name])
        if SELF in staged and normalized(git("show", ":" + SELF)) != normalized((ROOT / SELF).read_bytes()):
            raise ValueError("staged validator differs")
        # Supplied official text is immutable, including its original whitespace.
        git("diff", "--check", BASELINE, "--", *PINS, SELF)
        git("diff", "--cached", "--check", BASELINE, "--", *PINS, SELF)
    except (OSError, ValueError, KeyError, TypeError, zipfile.BadZipFile, subprocess.SubprocessError) as error:
        print(f"FAIL: {phase}: {error}; later phases NOT RUN")
        return 1
    print(
        "FORGEAI-GEMMA4-SCORER-ENTRYPOINT-RECONCILIATION-1 LOCAL DOCUMENT CHECKS PASSED; "
        "M1_PARTIAL_M2_BASELINE_CONDITIONALLY_UNBLOCKED; "
        "BASELINE CONSTRUCTION AND OFFLINE VALIDATION ONLY; NO LIVE EXECUTION OR SUBMISSION AUTHORIZED"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
