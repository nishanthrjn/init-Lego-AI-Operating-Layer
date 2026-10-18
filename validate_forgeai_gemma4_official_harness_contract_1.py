"""Offline documentary gate; cannot qualify inaccessible official artifacts."""

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BASELINE = "461f01036390d00dcce1069adb6a804937dc4ff9"
DIRECTORY = "experiments/gemma4_competition/"
REGISTER = DIRECTORY + "source-register.json"
CONTRACT = DIRECTORY + "OFFICIAL-CONTRACT-REGISTER.md"
SELF = "validate_forgeai_gemma4_official_harness_contract_1.py"
DOCUMENTS = (
    "planning/FORGEAI-GEMMA4-COMPETITION-READINESS-1.md",
    "planning/GEMMA4-COMPETITION-REQUIREMENTS.md",
    "planning/GEMMA4-RESEARCH-PLAN.md",
    "planning/GEMMA4-IMPLEMENTATION-MILESTONES.md",
)
MODELS = tuple(
    "gemma-4-" + size + "-it-qat-w4a16-ct"
    for size in ("31b", "12b", "e4b", "e2b")
)
TOOLS = (
    "run_command", "submit_patch", "get_status", "read_file", "edit_file",
    "write_file", "get_code_neighbors", "search_similar_code", "get_code_subgraph",
    "run_skill_script", "load_skill_resource",
)
REQUIRED = (
    "Status: M1 PARTIAL; M2 BLOCKED.",
    "No official local files were obtained.",
    "Mixed variants within one submission are not supported.",
    "No runnable YAML/JSON agent configuration examples are included.",
    "NO IMPLEMENTATION, LIVE EXECUTION OR SUBMISSION AUTHORIZED.",
    *("| R" + str(i) + " |" for i in range(1, 8)),
    *MODELS,
    *TOOLS,
)


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, check=True, capture_output=True,
        text=True, timeout=30,
    ).stdout


def document(content: str) -> None:
    if any(item not in content for item in REQUIRED):
        raise ValueError("missing contract boundary or inventory")
    if any(marker in content for marker in ("```yaml", "```json", "M1 COMPLETE")):
        raise ValueError("unsupported configuration or closure claim")


def register(content: str) -> None:
    value = json.loads(content)
    if value["m1_status"] != "PARTIAL" or value["official_files"] != []:
        raise ValueError("new artifacts/closure require a separate verified slice")
    if value["observed_date"] != "2026-10-18" or value["model_evidence"] != "S6":
        raise ValueError("source observation identity changed")
    if value["announced_models"] != list(MODELS):
        raise ValueError("model announcement mismatch")
    if value["mixed_variants_supported"] is not False:
        raise ValueError("mixed variant restriction missing")
    expected = {
        "S1": "competitions/gemma-4-developer-agent/overview",
        "S2": "competitions/gemma-4-developer-agent-paper/overview/submission-requirements",
        "S3": "code/ryanholbrook/getting-started-gemma-4-developer-agent/input",
        "S4_MAIN": "competitions/gemma-4-developer-agent/rules",
        "S4_PAPER": "competitions/gemma-4-developer-agent-paper/rules",
        "S5_DATA": "competitions/gemma-4-developer-agent/data",
        "S5_STARTER": "code/ryanholbrook/getting-started-gemma-4-developer-agent",
        "S6": "competitions/gemma-4-developer-agent/discussion/748287",
        "S7_WHEELHOUSE": "datasets/metric/gemma-4-developer-agent-wheelhouse",
    }
    sources = value["sources"]
    if len(sources) != len(expected) or {s["id"] for s in sources} != set(expected):
        raise ValueError("source inventory mismatch")
    for source in sources:
        if source["url"] != "https://www.kaggle.com/" + expected[source["id"]]:
            raise ValueError("source provenance changed")
        status = (
            "INDEXED_STAFF_ANNOUNCEMENT" if source["id"] == "S6"
            else "INDEXED_OFFICIAL_PARTIAL" if source["id"] in {"S1", "S2", "S3"}
            else "UNVERIFIED"
        )
        if source["status"] != status:
            raise ValueError("unsupported source verification claim")
        if source["sha256"] is not None or source["version"] is not None:
            raise ValueError("unobtained artifact cannot have a verified pin")


def main() -> int:
    phase = "seven-file documentary scope; production and frozen evidence preserved"
    try:
        print("[PHASE] " + phase, flush=True)
        allowed = {SELF, REGISTER, CONTRACT, *DOCUMENTS}
        changed = set(git("diff", "--name-only", "--no-renames", BASELINE).splitlines())
        staged = set(git("diff", "--cached", "--name-only", BASELINE).splitlines())
        changed.update(staged)
        changed.update(git("ls-files", "--others", "--exclude-standard").splitlines())
        if changed - allowed:
            raise ValueError("outside contract-document scope")
        for name in allowed:
            path = ROOT / name
            if path.is_symlink() or not path.is_file():
                raise ValueError("missing or symlinked contract file")
            content = path.read_text(encoding="utf-8")
            if not content.endswith("\n") or content.endswith("\n\n"):
                raise ValueError("final newline violation: " + name)
            if any(line.rstrip() != line for line in content.splitlines()):
                raise ValueError("trailing whitespace: " + name)
        phase = "provenance, unavailable pins and partial contract controls"
        print("\n[PHASE] " + phase, flush=True)
        content = (ROOT / CONTRACT).read_text(encoding="utf-8")
        document(content)
        register((ROOT / REGISTER).read_text(encoding="utf-8"))
        for token in REQUIRED:
            try:
                document(content.replace(token, "REMOVED"))
            except ValueError:
                continue
            raise ValueError("negative document control accepted")
        for name, check in ((CONTRACT, document), (REGISTER, register)):
            if name in staged:
                check(git("show", ":" + name))
        for name in DOCUMENTS:
            content = (ROOT / name).read_text(encoding="utf-8")
            if name.endswith("RESEARCH-PLAN.md"):
                if "Controlled model-variant experiment" not in content:
                    raise ValueError("variant comparison missing")
            elif "OFFICIAL-CONTRACT-REGISTER.md" not in content:
                raise ValueError("contract cross-reference missing")
        phase = "working and staged whitespace"
        print("\n[PHASE] " + phase, flush=True)
        git("diff", "--check", BASELINE)
        git("diff", "--cached", "--check", BASELINE)
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as error:
        print(f"FAIL: {phase}: {error}; later phases NOT RUN")
        return 1
    print(
        "FORGEAI-GEMMA4-OFFICIAL-HARNESS-CONTRACT-1 LOCAL DOCUMENT CHECKS PASSED; "
        "M1 PARTIAL; OFFICIAL FILE HASHES UNAVAILABLE; M2 BLOCKED; "
        "NO LIVE EXECUTION OR SUBMISSION AUTHORIZED"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
