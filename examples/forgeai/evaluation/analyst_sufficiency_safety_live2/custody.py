"""Exact custody of committed live run directories (no arbitrary artifacts).

Each approved directory is pinned by its Git tree id at HEAD. Any other run
directory (committed or untracked) is refused, as is any change to a pinned
one. A new run directory needs an explicit, separately reviewed entry here.
"""

import json
import re
from collections.abc import Callable
from typing import Any

FORGE = "examples/forgeai"
RUN_DIRECTORY = re.compile(r"-(smoke|preflight|baseline)-[0-9a-f]{12}$")
REFUSAL = {
    "directory": "safety1-preflight-c80435f8dadc",
    "run_id": "6c557182-67a9-4851-9260-058c36e896be",
    "stop_reason": "RUNTIME_IDENTITY_REVIEW_REQUIRED",
    "committed_in": "ecbdf24",
    "tree": "be52fc954ed30e980ab85db7ea83692389581899",
}
ARTIFACTS = {
    "live1-smoke-d59e9c3f030b": "8cef1bea232463de78afca2a01cb11056ec85913",
    "live1-smoke-227bdd3cec0b": "a19b5c191da4b63c298f22e71ca0ae418ae84df7",
    "live1-smoke-bf448d5a12b3": "54494f60b828102452257c1010f19f4688dfb8f9",
    "live1-preflight-411899d3f557": "89f79532512b954c8ae3b2630a06a9e5eef18b7d",
    "live1-preflight-9bdb9f5867b6": "164fd09c88848877c81bd12e339d94e1cab5f2d4",
    "live1-preflight-a9e59b9f3773": "bf9c71dc7f2b406d9c027cdd2d84688917945a49",
    REFUSAL["directory"]: REFUSAL["tree"],
}


def run_directories(repository: Callable[..., str]) -> set[str]:
    tracked = repository("ls-tree", "-d", "--name-only", "HEAD", FORGE + "/")
    untracked = repository(
        "ls-files", "--others", "--exclude-standard", "--directory", FORGE + "/"
    )
    names = {
        line.rstrip("/").split("/")[2]
        for line in (*tracked.splitlines(), *untracked.splitlines())
        if line.count("/") >= 2
    }
    return {n for n in names if RUN_DIRECTORY.search(n)}


def verify(repository: Callable[..., str]) -> dict[str, Any]:
    found = run_directories(repository)
    if found != set(ARTIFACTS):
        raise ValueError(
            "UNRECOGNIZED_OR_MISSING_RUN_DIRECTORY: "
            + repr(sorted(found ^ set(ARTIFACTS)))
        )
    for name, tree in ARTIFACTS.items():
        path = f"{FORGE}/{name}"
        if repository("rev-parse", f"HEAD:{path}") != tree:
            raise ValueError("RUN_DIRECTORY_CHANGED: " + name)
        if repository("status", "--porcelain", "--", path):
            raise ValueError("RUN_DIRECTORY_MODIFIED: " + name)
    report = json.loads(
        repository("show", f"HEAD:{FORGE}/{REFUSAL['directory']}/report.json")
    )
    if (
        report["run_id"] != REFUSAL["run_id"]
        or report["stop_reason"] != REFUSAL["stop_reason"]
        or report["mode"] != "PREFLIGHT"
        or report["calls"] != 0
        or report["records"]
        or report["condition"] != "forgeai-analyst-sufficiency-safety-live/1"
    ):
        raise ValueError("REFUSAL_ARTIFACT_MISMATCH")
    return {"directories": sorted(found), "refusal": REFUSAL}
