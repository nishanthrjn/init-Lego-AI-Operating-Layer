"""Offline documentary checks only; maintainer execution required."""

import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BASELINE = "c859f316bb4eff6a7a0cb86a5aabefe557e972c9"
SELF = "validate_forgeai_gemma4_official_artifact_reconciliation_1.py"
DIRECTORY = "experiments/gemma4_competition/"
REGISTER = DIRECTORY + "source-register.json"
CONTRACT = DIRECTORY + "OFFICIAL-CONTRACT-REGISTER.md"
DECISION = "M1_PARTIAL_ADDITIONAL_ARTIFACTS_REQUIRED"
PINS = {
    "experiments/gemma4_competition/source-register.json": "ef497200ff713028586a6d9c68ac1760a0b6ee1ade3680dc82f1e0fe6ad5d118",
    "experiments/gemma4_competition/OFFICIAL-CONTRACT-REGISTER.md": "372371668414bfdbaa7bc19b058db603ce1b331858ee3185036c9f8e6525e822",
    "planning/FORGEAI-GEMMA4-COMPETITION-READINESS-1.md": "283c75ba8e9e0577865e48b364b5b8a46e0918418d04c80ed8396c6609468b39",
    "planning/GEMMA4-COMPETITION-REQUIREMENTS.md": "7b3d0088f7042ada96d1c9a5a9e14f0f76b38e866434c810ff5d4fcf8f5f979e",
    "planning/GEMMA4-RESEARCH-PLAN.md": "e25d3d5ff24725c439dfe101ee5e370e16b066d04279dda22276a5399c1a5044",
    "planning/GEMMA4-IMPLEMENTATION-MILESTONES.md": "26e302fb1106055d7b263e1141c8f4e1dd02a33ff4c577309320421fbe099a9a"
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
    if len(register["official_files"]) != 24:
        raise ValueError("artifact inventory changed")
    acquisition = register["acquisition_review"]
    if (
        acquisition["task"] != "FORGEAI-GEMMA4-HARNESS-ARTIFACT-ACQUISITION-1"
        or acquisition["decision"] != DECISION
        or acquisition["new_artifacts_supplied"] is not True
        or acquisition["prior_reconciliation_validation"] != "MAINTAINER_REPORTED_PASS"
    ):
        raise ValueError("acquisition boundary changed")
    expected_inventory = [
        {key: entry[key] for key in ("path", "size_bytes", "sha256")}
        for entry in register["official_files"]
    ]
    if acquisition["observed_artifacts"] != expected_inventory:
        raise ValueError("observed inventory differs from preserved pins")
    contract = values[CONTRACT].decode("utf-8")
    for required in (
        DECISION, "M2 BLOCKED", "HARNESS_README", "C2", "NOT RUN",
        "NO IMPLEMENTATION, LIVE EXECUTION OR SUBMISSION AUTHORIZED.",
        *("| R" + str(i) + " |" for i in range(1, 8)),
    ):
        if required not in contract:
            raise ValueError("missing documentary boundary")


def artifact(data: bytes, entry: dict) -> None:
    if len(data) != entry["size_bytes"] or digest(data) != entry["sha256"]:
        raise ValueError("artifact bytes changed: " + entry["path"])


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
            DIRECTORY + "docs/HARNESS_README.md",
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
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as error:
        print(f"FAIL: {phase}: {error}; later phases NOT RUN")
        return 1
    print(
        "FORGEAI-GEMMA4-HARNESS-ARTIFACT-ACQUISITION-1 LOCAL DOCUMENT CHECKS PASSED; "
        "M1 PARTIAL; M2 BLOCKED; M1_PARTIAL_ADDITIONAL_ARTIFACTS_REQUIRED; "
        "NO IMPLEMENTATION, LIVE EXECUTION OR SUBMISSION AUTHORIZED"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
