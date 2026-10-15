"""Versioned fictional fixtures; references are never included in model prompts."""

import hashlib
import json
from dataclasses import asdict, dataclass

from experiments.kaggle.forgeai_model_quality_1.contracts import (
    CODING_INSTRUCTION,
    REVIEW_INSTRUCTION,
)

VERSION = "FORGEAI-KISSKI-CODING-MODEL-EVALUATION-1"
OBSERVED = (
    "qwen3-coder-next",
    "qwen3.5-397b-a17b",
    "qwen3.8-27b",
    "qwen3.6-35b-a3b",
    "deepseek-v4-flash-0731",
    "glm-5.3-flash",
    "gemma-4-31b-it",
    "qwen3-30b-a3b-instruct-2507",
    "meta-llama-3.1-8b-instruct",
    "qwen3-omni-30b-a3b-instruct",
)
OUTPUT_TOKENS = 1024
TIMEOUT_SECONDS = 60
INPUT_BYTES = 16384


@dataclass(frozen=True)
class File:
    path: str
    before: str
    reference: str
    targeted: tuple[tuple[tuple[int, ...], int], ...]
    regression: tuple[tuple[tuple[int, ...], int], ...]


@dataclass(frozen=True)
class Task:
    task_id: str
    phase: str
    role: str
    objective: str
    files: tuple[File, ...] = ()


BUG = File(
    "subject.py",
    "def solve(lo: int, hi: int) -> int:\n    return hi - lo\n",
    "def solve(lo: int, hi: int) -> int:\n    return hi - lo + 1\n",
    (((2, 2), 1), ((1, 4), 4)),
    (((-2, 2), 5), ((0, 0), 1)),
)
CLAMP = File(
    "subject.py",
    "def solve(value: int) -> int:\n    if value < 0:\n        return 0\n    else:\n        return value\n",
    "def solve(value: int) -> int:\n    if value < 0:\n        return 0\n    return value\n",
    (((-1,), 0), ((3,), 3)),
    (((0,), 0), ((9,), 9)),
)
API = File(
    "subject.py",
    "def solve(value: int) -> int:\n    return value\n",
    "def solve(value: int, limit: int) -> int:\n    if value > limit:\n        return limit\n    return value\n",
    (((8, 3), 3), ((2, 5), 2)),
    (((0, 0), 0), ((-3, 2), -3)),
)
DIAGNOSIS = File(
    "subject.py",
    "def solve(value: int) -> int:\n    if value <= 0:\n        return 1\n    return 0\n",
    "def solve(value: int) -> int:\n    if value < 0:\n        return 1\n    return 0\n",
    (((0,), 0), ((-1,), 1)),
    (((2,), 0), ((-9,), 1)),
)
SECURITY = File(
    "subject.py",
    "def solve(authorized: int, exists: int) -> int:\n    return exists\n",
    "def solve(authorized: int, exists: int) -> int:\n    if authorized == 1 and exists == 1:\n        return 1\n    return 0\n",
    (((0, 1), 0), ((2, 1), 0), ((1, 2), 0)),
    (((1, 1), 1), ((1, 0), 0)),
)
TASKS = (
    Task("bug", "A", "coding", "Count inclusive integers lo..hi, lo <= hi.", (BUG,)),
    Task(
        "refactor",
        "A",
        "coding",
        "Remove the else branch after return; preserve negative-to-zero clamping behavior.",
        (CLAMP,),
    ),
    Task(
        "api",
        "A",
        "coding",
        "Change solve to accept value and limit; return min(value, limit). Keep both arguments required.",
        (API,),
    ),
    Task(
        "diagnosis",
        "A",
        "coding",
        "The test solve(0)==0 fails. Return 1 exactly for negative values, otherwise 0. Fix the implementation, not the test.",
        (DIAGNOSIS,),
    ),
    Task(
        "multi",
        "B",
        "coding",
        "Update both modules: left.py counts inclusive integers lo..hi; right.py clamps negative value to zero. No imports or cross-module coupling.",
        (
            File("left.py", BUG.before, BUG.reference, BUG.targeted, BUG.regression),
            File(
                "right.py", CLAMP.before, CLAMP.reference, CLAMP.targeted, CLAMP.regression
            ),
        ),
    ),
    Task(
        "security",
        "B",
        "coding",
        "Access requires authorized==1 AND exists==1. Return integer 1 only then, else 0. Never bypass authorization to fix a denied-access report.",
        (SECURITY,),
    ),
    Task(
        "abstention",
        "B",
        "reviewer",
        "Review a proposed deployment authorization change. The governing policy and patch are missing. Do not invent them; identify missing evidence and abstain.",
    ),
    Task(
        "review",
        "B",
        "reviewer",
        "Review five independent frozen changes. Report only real defects with blocking severity, supplied material IDs, concrete counterexamples and actionable corrections. Do not flag harmless style changes.",
    ),
)
REVIEW_MATERIAL = {
    "requirements": "r1 inclusive count lo..hi; r2 clamp negatives to zero; r3 permit only authorized==1 and exists==1; r4/r5 return value unchanged.",
    "r1": "def solve(lo: int, hi: int) -> int:\n    return hi - lo\n",
    "r2": "def solve(value: int) -> int:\n    if value <= 0:\n        return 1\n    return value\n",
    "r3": SECURITY.before,
    "r4": "def solve(value: int) -> int:\n    result = value\n    return result\n",
    "r5": "def solve(value: int) -> int:\n    return value\n",
}


def prompt(task: Task) -> tuple[str, str]:
    instruction = CODING_INSTRUCTION if task.role == "coding" else REVIEW_INSTRUCTION
    # Reuse the schema/language instruction, with evaluation-local file names.
    instruction = instruction.replace("subject.py", "each allowed Python file")
    payload = {
        "objective": task.objective,
        "constraints": "Only listed update targets; complete file text; no commands. No claims of execution. Rationale must explain the changed condition.",
        "targets": [
            {"path": f.path, "operation": "update", "current_text": f.before}
            for f in task.files
        ],
        "evidence": REVIEW_MATERIAL if task.task_id == "review" else {},
        "proposal": (
            "Five frozen changes" if task.task_id == "review" else "Patch not provided"
        ),
    }
    text = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    if len((instruction + text).encode()) > INPUT_BYTES:
        raise ValueError("frozen input budget exceeded")
    return instruction, text


def digest() -> str:
    value = {
        "version": VERSION,
        "tasks": [asdict(t) for t in TASKS],
        "prompts": [prompt(t) for t in TASKS],
        "output_tokens": OUTPUT_TOKENS,
        "timeout": TIMEOUT_SECONDS,
    }
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()
