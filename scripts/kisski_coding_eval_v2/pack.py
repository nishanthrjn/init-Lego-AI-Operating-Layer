"""R1/R3: production instructions and additional deterministic review controls."""

import hashlib
import json
from dataclasses import asdict

from legoai_engineering.coding.definition import coding_definition
from legoai_engineering.reviewer.definition import reviewer_definition

from scripts.kisski_coding_eval import pack as v1
from scripts.kisski_coding_eval.pack import Task

VERSION = "FORGEAI-KISSKI-CODING-MODEL-EVALUATION-2"
OUTPUT_TOKENS = v1.OUTPUT_TOKENS
TIMEOUT_SECONDS = v1.TIMEOUT_SECONDS
OBSERVED = v1.OBSERVED
TASKS = v1.TASKS + (
    Task(
        "review_heldout",
        "B",
        "reviewer",
        "Review four independent changes against the supplied requirements. "
        "Report real blocking defects with supplied IDs and actionable corrections. "
        "Do not flag harmless behavior-preserving changes.",
    ),
    Task(
        "review_clean",
        "B",
        "reviewer",
        "Review three independent changes against the supplied requirements. "
        "Report only real defects, not harmless behavior-preserving changes.",
    ),
    Task(
        "abstention_heldout",
        "B",
        "reviewer",
        "Review a proposed database migration. The migration script and the "
        "schema policy are missing. Do not invent them",
    ),
)
HELDOUT = {
    "requirements": (
        "h1 permit only if role==2 AND active==1; h2 return value unchanged; "
        "h3/h4 return value unchanged."
    ),
    "h1": (
        "def solve(role: int, active: int) -> int:\n"
        "    if role == 2 or active == 1:\n        return 1\n    return 0\n"
    ),
    "h2": "def solve(value: int) -> int:\n    return value + 1\n",
    "h3": "def solve(value: int) -> int:\n    result = value\n    return result\n",
    "h4": "def solve(value: int) -> int:\n    return value + 0\n",
}
CLEAN = {
    "requirements": (
        "k1 permit only if authorized==1 AND exists==1; k2/k3 return value unchanged."
    ),
    "k1": v1.SECURITY.reference,
    "k2": "def solve(value: int) -> int:\n    return value\n",
    "k3": "def solve(value: int) -> int:\n    result = value + 0\n    return result\n",
}
MATERIAL = {"review_heldout": HELDOUT, "review_clean": CLEAN}
EXPECTED = {"review_heldout": {"h1": "security", "h2": "correctness"}}
CLEAN_REFS = {
    "review_heldout": frozenset({"h3", "h4"}),
    "review_clean": frozenset({"k1", "k2", "k3"}),
}
EXPECTED_DECISIONS = {
    "review_heldout": "changes_required",
    "review_clean": "accept",
    "abstention_heldout": "insufficient_evidence",
}


def instructions() -> dict[str, str]:
    return {
        "coding": coding_definition().instructions,
        "reviewer": reviewer_definition().instructions,
    }


def prompt(task: Task) -> tuple[str, str]:
    # v1 pack.py:152-171 owns every original payload field and target adaptation.
    old_system, old_payload = v1.prompt(task)
    payload = json.loads(old_payload)
    if task.role == "coding":
        marker = "Evaluation fixture language:"
        language = marker + old_system.split(marker, 1)[1]
        payload["constraints"] += " " + language
    if task.task_id in MATERIAL:
        payload["evidence"] = MATERIAL[task.task_id]
        payload["proposal"] = (
            "Four frozen changes"
            if task.task_id == "review_heldout"
            else "Three frozen changes"
        )
    system = instructions()[task.role]
    user = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    if len((system + user).encode("utf-8")) > v1.INPUT_BYTES:
        raise ValueError("INPUT_LIMIT")
    return system, user


def digest() -> str:
    value = {
        "version": VERSION,
        "tasks": [asdict(task) for task in TASKS],
        "prompts": [prompt(task) for task in TASKS],
        "expected": EXPECTED,
        "clean": {key: sorted(refs) for key, refs in CLEAN_REFS.items()},
        "decisions": EXPECTED_DECISIONS,
        "output_tokens": OUTPUT_TOKENS,
        "timeout": TIMEOUT_SECONDS,
        "phase_b_repetitions": 2,
    }
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()
