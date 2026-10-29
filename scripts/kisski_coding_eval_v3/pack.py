"""R1'/R3': v2 payloads plus two new deterministic reviewer controls."""

import hashlib
import json
from dataclasses import asdict

from scripts.kisski_coding_eval.pack import INPUT_BYTES, Task
from scripts.kisski_coding_eval_v2 import pack as v2
from scripts.kisski_coding_eval_v2.pack import OBSERVED as OBSERVED
from scripts.kisski_coding_eval_v2.pack import OUTPUT_TOKENS as OUTPUT_TOKENS
from scripts.kisski_coding_eval_v2.pack import TIMEOUT_SECONDS as TIMEOUT_SECONDS
from scripts.kisski_coding_eval_v2.pack import instructions as instructions

VERSION = "FORGEAI-KISSKI-CODING-MODEL-EVALUATION-3"
TASKS = v2.TASKS + (
    Task(
        "review_heldout2",
        "B",
        "reviewer",
        "Review four independent changes against the supplied requirements. "
        "Report real blocking defects with supplied IDs and actionable corrections. "
        "Do not flag harmless behavior-preserving changes.",
    ),
    Task(
        "review_clean2",
        "B",
        "reviewer",
        "Review three independent changes against the supplied requirements. "
        "Report only real defects, not harmless behavior-preserving changes.",
    ),
)
HELDOUT = {
    "requirements": (
        "s1 permit only if token_valid==1 AND expired==0; "
        "s2 return 0 for negative values, else the value; "
        "s3/s4 return value unchanged."
    ),
    "s1": (
        "def solve(token_valid: int, expired: int) -> int:\n"
        "    if token_valid == 1:\n        return 1\n    return 0\n"
    ),
    "s2": "def solve(value: int) -> int:\n    return value\n",
    "s3": "def solve(value: int) -> int:\n    result = value\n    return result\n",
    "s4": "def solve(value: int) -> int:\n    return value + 0\n",
}
CLEAN = {
    "requirements": (
        "c1 permit only if token_valid==1 AND expired==0; c2/c3 return value unchanged."
    ),
    "c1": (
        "def solve(token_valid: int, expired: int) -> int:\n"
        "    if token_valid == 1 and expired == 0:\n"
        "        return 1\n    return 0\n"
    ),
    "c2": "def solve(value: int) -> int:\n    return value\n",
    "c3": "def solve(value: int) -> int:\n    result = value + 0\n    return result\n",
}
MATERIAL = {"review_heldout2": HELDOUT, "review_clean2": CLEAN}
EXPECTED = {"review_heldout2": {"s1": "security", "s2": "correctness"}}
CLEAN_REFS = {
    "review_heldout2": frozenset({"s3", "s4"}),
    "review_clean2": frozenset({"c1", "c2", "c3"}),
}
EXPECTED_DECISIONS = {
    "review_heldout2": "changes_required",
    "review_clean2": "accept",
}


def prompt(task: Task) -> tuple[str, str]:
    # V2 pack.prompt owns production instructions and unchanged original payloads.
    system, user = v2.prompt(task)
    if task.task_id not in MATERIAL:
        return system, user
    payload = json.loads(user)
    payload["evidence"] = MATERIAL[task.task_id]
    payload["proposal"] = (
        "Four frozen changes"
        if task.task_id == "review_heldout2"
        else "Three frozen changes"
    )
    user = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    if len((system + user).encode("utf-8")) > INPUT_BYTES:
        raise ValueError("INPUT_LIMIT")
    return system, user


def digest() -> str:
    # V2 pack.digest, with v3 identity and the additional expected maps.
    value = {
        "version": VERSION,
        "tasks": [asdict(task) for task in TASKS],
        "prompts": [prompt(task) for task in TASKS],
        "expected": {**v2.EXPECTED, **EXPECTED},
        "clean": {
            key: sorted(refs) for key, refs in (v2.CLEAN_REFS | CLEAN_REFS).items()
        },
        "decisions": v2.EXPECTED_DECISIONS | EXPECTED_DECISIONS,
        "output_tokens": OUTPUT_TOKENS,
        "timeout": TIMEOUT_SECONDS,
        "phase_b_repetitions": 2,
    }
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()
