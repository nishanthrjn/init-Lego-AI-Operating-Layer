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
# Admitted by FORGEAI-ANALYST-SUFFICIENCY-SAFETY-LIVE-2-PREFLIGHT-CUSTODY-1.
PREFLIGHT2 = {
    "directory": "safety2-preflight-300452037205",
    "run_id": "8b147424-5231-4758-9e0f-05730f6174bc",
    "git_head": "dff9cc045a635d4c8437ea78d8ce86c0ec7c3e4b",
    "committed_in": "72cb346",
    "tree": "5f5f49375b83b9fca58873ea9f15e3f9b409840b",
}
MODEL_DIGEST = "sha256:9ec8897f747e246e970bc5cfdda85d22f1123dc2e3d34978a010a75968716849"
ARTIFACTS = {
    "live1-smoke-d59e9c3f030b": "8cef1bea232463de78afca2a01cb11056ec85913",
    "live1-smoke-227bdd3cec0b": "a19b5c191da4b63c298f22e71ca0ae418ae84df7",
    "live1-smoke-bf448d5a12b3": "54494f60b828102452257c1010f19f4688dfb8f9",
    "live1-preflight-411899d3f557": "89f79532512b954c8ae3b2630a06a9e5eef18b7d",
    "live1-preflight-9bdb9f5867b6": "164fd09c88848877c81bd12e339d94e1cab5f2d4",
    "live1-preflight-a9e59b9f3773": "bf9c71dc7f2b406d9c027cdd2d84688917945a49",
    REFUSAL["directory"]: REFUSAL["tree"],
    PREFLIGHT2["directory"]: PREFLIGHT2["tree"],
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
    preflight(
        json.loads(
            repository("show", f"HEAD:{FORGE}/{PREFLIGHT2['directory']}/report.json")
        )
    )
    return {"directories": sorted(found), "refusal": REFUSAL, "preflight": PREFLIGHT2}


def preflight(report: dict[str, Any]) -> None:
    """The admitted live/2 PREFLIGHT: passed, zero calls, exact identities."""
    p = report["provenance"]
    observed = p["observed"]
    if (
        report["run_id"] != PREFLIGHT2["run_id"]
        or report["condition"] != "forgeai-analyst-sufficiency-safety-live/2"
        or report["report_identity"]
        != "forgeai-analyst-sufficiency-safety-live-report/2"
        or report["mode"] != "PREFLIGHT"
        or report["decision"] != {"code": None, "label": "PREFLIGHT - NO MEASUREMENT"}
        or report["stop_reason"] is not None
        or report["git_head"] != PREFLIGHT2["git_head"]
        or p["commit"] != PREFLIGHT2["git_head"]
        or report["clean_tracked_tree"] is not True
        or (report["calls"], report["attempted"], report["completed"]) != (0, 0, 0)
        or report["records"]
        or report["timings"]
        or p["model"] != observed["model"]
        or p["model"] != "qwen2.5-coder:14b"
        or p["model_digest"] != observed["digest"]
        or p["model_digest"] != MODEL_DIGEST
        or p["ollama_version"] != observed["ollama"]
        or p["ollama_version"] != "0.40.0"
        or p["credentials"] != "NONE"
        or p["payload_leakage_preflight"] != "PASSED"
        or report["membership"] != [f"s{i:02}" for i in range(1, 23)]
        or (report["call_ceiling"], report["call_seconds"], report["total_seconds"])
        != (22, 600, 3600)
        or report["historical_non_gating"]["cases"] != ["d21", "d22"]
    ):
        raise ValueError("PREFLIGHT2_ARTIFACT_MISMATCH")
