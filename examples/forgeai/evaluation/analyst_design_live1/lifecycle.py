"""Execution custody partition, distinct from frozen semantic opportunities."""

import json
from enum import StrEnum
from pathlib import Path
from typing import Any


class AttemptState(StrEnum):
    NEVER_ATTEMPTED = "NEVER_ATTEMPTED"
    ATTEMPTED_NO_RESULT = "ATTEMPTED_NO_RESULT"
    COMPLETED_RESULT = "COMPLETED_RESULT"


def key(value: dict[str, Any]) -> str:
    return "/".join(value[k] for k in ("case", "variant", "phase"))


def partition(path: Path, planned: list[dict[str, Any]]) -> dict[str, Any]:
    starts: dict[str, dict[str, Any]] = {}
    finishes: dict[str, dict[str, Any]] = {}
    for file in sorted(path.glob("call-*-started.json")):
        start = json.loads(file.read_text(encoding="utf-8"))
        identity = key(start)
        if identity in starts:
            raise ValueError("duplicate lifecycle start")
        starts[identity] = start
        finish_path = file.with_name(file.name.replace("-started", "-finished"))
        if finish_path.exists():
            finish = json.loads(finish_path.read_text(encoding="utf-8"))
            if key(finish) != identity:
                raise ValueError("lifecycle finish identity")
            finishes[identity] = finish
    if len(list(path.glob("call-*-finished.json"))) != len(finishes):
        raise ValueError("orphan lifecycle finish")
    completed = set()
    for file in sorted(path.glob("observation-*.json")):
        row = json.loads(file.read_text(encoding="utf-8"))
        for attempt in row["attempts"]:
            completed.add(f"{row['case']}/{row['variant']}/{attempt['phase']}")
    identities = {key(s) for s in planned}
    if len(identities) != len(planned) or not starts.keys() <= identities:
        raise ValueError("lifecycle membership")
    if not (completed & identities) <= starts.keys():
        raise ValueError("completed model result without started call")
    slots = []
    for slot in planned:
        identity = key(slot)
        state = (
            AttemptState.COMPLETED_RESULT
            if identity in completed
            else AttemptState.ATTEMPTED_NO_RESULT
            if identity in starts
            else AttemptState.NEVER_ATTEMPTED
        )
        finish = finishes.get(identity)
        slots.append(
            {
                "identity": identity,
                "attempt_state": state.value,
                "finish_recorded": finish is not None,
                "finish_failure": finish.get("failure") if finish else None,
            }
        )
    groups = {
        s.name.lower(): [x["identity"] for x in slots if x["attempt_state"] == s.value]
        for s in AttemptState
    }
    result = {
        "scope": "MODEL_CALL_OPPORTUNITIES",
        "planned": len(planned),
        "attempted": len(starts),
        "completed": len(groups["completed_result"]),
        "slots": slots,
        **groups,
    }
    validate_partition(result)
    return result


def validate_partition(value: dict[str, Any]) -> None:
    groups = [value[s.name.lower()] for s in AttemptState]
    flat = [x for group in groups for x in group]
    slots = value["slots"]
    if (
        value["scope"] != "MODEL_CALL_OPPORTUNITIES"
        or len(flat) != len(set(flat))
        or value["planned"] != len(flat)
        or value["attempted"] != len(groups[1]) + len(groups[2])
        or value["completed"] != len(groups[2])
        or len(slots) != len(flat)
        or {s["identity"] for s in slots} != set(flat)
    ):
        raise ValueError("lifecycle accounting invariant")
    for state in AttemptState:
        if {s["identity"] for s in slots if s["attempt_state"] == state.value} != set(
            value[state.name.lower()]
        ):
            raise ValueError("lifecycle state invariant")
