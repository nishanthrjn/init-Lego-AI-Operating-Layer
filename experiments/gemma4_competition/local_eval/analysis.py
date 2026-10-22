"""Offline public-development evidence contracts. Standard library only; no models."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import re
import statistics
import zipfile

SEED = 20261021
REPOS = {"fastapi", "requests", "rich", "httpx"}
ALLOCATIONS = {
    "dev-30": {"fastapi": 12, "requests": 6, "rich": 11, "httpx": 1},
    "smoke-5": {"fastapi": 2, "requests": 1, "rich": 1, "httpx": 1},
    "confirm-20": {"fastapi": 8, "requests": 4, "rich": 8, "httpx": 0},
}
STOPS = {"submitted", "call_budget", "time_budget", "turn_budget", "error", "unknown", "wall_guard"}


def missing_collection_dependency(output: str) -> bool:
    """Only explicit verifier collection/import errors, not arbitrary tool failures."""
    missing = re.search(r"ModuleNotFoundError: No module named ['\"][A-Za-z0-9_.-]+['\"]", output)
    collection = re.search(r"ERROR collecting\b|errors? during collection\b|ImportError while loading conftest", output, re.I)
    return bool(missing and collection)


def verification_outcome(official_resolved: bool, output: str) -> dict:
    if not official_resolved and missing_collection_dependency(output):
        return {"resolved": None, "official_resolved": False,
                "verification_status": "HARNESS_ENVIRONMENT_ERROR",
                "harness_errors": ["HARNESS_ENVIRONMENT_ERROR"]}
    return {"resolved": official_resolved, "official_resolved": official_resolved,
            "verification_status": "passed" if official_resolved else ("failed" if output.startswith("STDOUT:\n") else "unknown"),
            "harness_errors": []}


def sha(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def canonical(value) -> bytes:
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()


def freeze(rows: list[dict], source_sha256: str, label_field: str | None = None) -> dict:
    """Read only identity/explicit labels; never infer types from issue/test/patch text."""
    groups = defaultdict(list)
    seen = set()
    for row in rows:
        allowed = {"instance_id", "repo", "base_commit", "created_at"} | ({label_field} if label_field else set())
        if set(row) - allowed:
            raise ValueError("metadata-only input required; unexpected fields refused")
        tid, repo = row["instance_id"], row["repo"]
        if not isinstance(tid, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,200}", tid) or tid in seen:
            raise ValueError("missing or duplicate task identity")
        if not isinstance(repo, str) or repo.lower().split("/")[-1] not in REPOS:
            raise ValueError("unexpected public repository")
        seen.add(tid)
        label = row.get(label_field) if label_field else None
        if label is not None and label not in ("bug", "feature"):
            raise ValueError("label must be explicit bug/feature or null; no inferred labels")
        groups[repo].append({"task_id": tid, "repo": repo, "label": label})
    if len(groups) != 4 or len(rows) != 129:
        raise ValueError("expected the pinned 129-task public development inventory across four repositories")
    ranked_repos = sorted(groups, key=lambda r: hashlib.sha256(f"{SEED}:{r}".encode()).hexdigest())
    ordered_by_repo = {}
    for repo in ranked_repos:
        strata = defaultdict(list)
        for item in groups[repo]:
            strata[item["label"] or "unknown"].append(item)
        for bucket in strata.values():
            bucket.sort(key=lambda x: hashlib.sha256(f"{SEED}:{x['task_id']}".encode()).hexdigest())
        ordered = []
        while any(strata.values()):
            for label in sorted(strata):
                if strata[label]:
                    ordered.append(strata[label].pop(0))
        ordered_by_repo[repo] = ordered
    subsets = {}
    for name, quotas in ALLOCATIONS.items():
        picked = {}
        for repo in ranked_repos:
            short = repo.lower().split("/")[-1]
            offset = ALLOCATIONS["dev-30"][short] if name == "confirm-20" else 0
            picked[repo] = ordered_by_repo[repo][offset:offset + quotas[short]]
            if len(picked[repo]) != quotas[short]:
                raise ValueError("insufficient tasks for approved repository allocation")
        subsets[name] = [picked[r][i] for i in range(max(quotas.values())) for r in ranked_repos if i < len(picked[r])]
    return {"schema": 1, "seed": SEED, "source_sha256": source_sha256,
            "label_field": label_field, "inventory_size": len(rows), **subsets}


def load_subset(path: Path, expected_sha: str, name: str) -> tuple[dict, list[dict]]:
    if sha(path) != expected_sha or name not in ALLOCATIONS:
        raise ValueError("subset hash/name mismatch")
    doc = json.loads(path.read_bytes())
    if set(doc) != {"schema", "seed", "source_sha256", "label_field", "inventory_size", *ALLOCATIONS}:
        raise ValueError("unexpected frozen metadata fields")
    if doc["seed"] != SEED or doc["schema"] != 1 or doc["inventory_size"] != 129:
        raise ValueError("subset inventory/seed mismatch")
    identities = {}
    for subset_name, quotas in ALLOCATIONS.items():
        rows = doc[subset_name]
        if any(set(r) != {"task_id", "repo", "label"} or r["label"] not in (None, "bug", "feature") for r in rows):
            raise ValueError("unexpected subset task fields")
        if len({r["task_id"] for r in rows}) != len(rows):
            raise ValueError("duplicate subset task")
        counts = Counter(r["repo"].lower().split("/")[-1] for r in rows)
        if dict(counts) != {k: v for k, v in quotas.items() if v}:
            raise ValueError("approved repository allocation mismatch")
        identities[subset_name] = {r["task_id"] for r in rows}
    if not identities["smoke-5"] <= identities["dev-30"]:
        raise ValueError("smoke must be nested in frozen dev-30")
    if identities["confirm-20"] & identities["dev-30"]:
        raise ValueError("confirmation holdout overlaps development tasks")
    return doc, doc[name]


def verify_package(package: Path, manifest: Path, manifest_sha: str, receipt_sha: str) -> dict:
    if sha(manifest) != manifest_sha:
        raise ValueError("manifest raw-byte SHA256 mismatch")
    m = json.loads(manifest.read_bytes())
    if m["state"] != "PORTABLE_COMPILE_AND_PACKAGE_PASS" or m["local_receipt_sha256"] != receipt_sha:
        raise ValueError("package qualification/receipt mismatch")
    if package.stat().st_size != m["zip_size"] or sha(package) != m["zip_sha256"]:
        raise ValueError("package byte identity mismatch")
    return m


def extract_package(package: Path, target: Path) -> None:
    """Preflight every member before writing; official directory validation follows."""
    with zipfile.ZipFile(package) as archive:
        infos = archive.infolist()
        names = set()
        if len(infos) > 10000 or sum(i.file_size for i in infos) > 3 * 1024**3:
            raise ValueError("archive limits exceeded")
        for info in infos:
            p = PurePosixPath(info.filename)
            if (not info.filename or p.is_absolute() or ".." in p.parts
                    or "\\" in info.filename or ":" in info.filename
                    or info.filename in names or (info.external_attr >> 16) & 0o170000 == 0o120000):
                raise ValueError("unsafe archive member")
            names.add(info.filename)
        target.mkdir(parents=True, exist_ok=False)
        archive.extractall(target)


def validate_record(r: dict) -> None:
    required = {"schema", "task_id", "repo", "resolved", "wall_seconds", "agent_seconds",
                "model_turns", "tool_calls", "tokens", "submit_patch_called", "patch_bytes",
                "files_changed", "test_files_touched", "stray_files", "stop_reason",
                "last_tool_error", "harness_errors", "seconds_per_model_turn"}
    if not required <= r.keys() or r["schema"] != 1 or r["stop_reason"] not in STOPS:
        raise ValueError("invalid task record schema")
    if not isinstance(r["task_id"], str) or not r["task_id"] or not isinstance(r["repo"], str):
        raise ValueError("invalid task identity")
    for key in ("resolved", "submit_patch_called", "test_files_touched"):
        if r[key] is not None and type(r[key]) is not bool:
            raise ValueError("invalid tri-state boolean: " + key)
    for key in ("wall_seconds", "agent_seconds", "seconds_per_model_turn"):
        value = r[key]
        if value is None and key != "wall_seconds":
            continue
        if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
            raise ValueError("invalid duration: " + key)
    for key in ("model_turns", "tokens", "patch_bytes"):
        if r[key] is not None and (type(r[key]) is not int or r[key] < 0):
            raise ValueError("invalid count: " + key)
    if r["tool_calls"] is not None:
        if not isinstance(r["tool_calls"], dict) or any(not isinstance(k, str) or type(v) is not int or v < 0 for k, v in r["tool_calls"].items()):
            raise ValueError("invalid tool counts")
    for key in ("files_changed", "stray_files", "harness_errors"):
        if r[key] is not None and (not isinstance(r[key], list) or any(not isinstance(v, str) for v in r[key])):
            raise ValueError("invalid list: " + key)


def read_run(path: Path) -> tuple[dict, list[dict]]:
    meta = json.loads((path / "run.json").read_bytes())
    completion = path / "completion.json"
    meta["completion_state"] = json.loads(completion.read_bytes())["state"] if completion.is_file() else "INCOMPLETE"
    if not meta["task_ids"] or len(set(meta["task_ids"])) != len(meta["task_ids"]):
        raise ValueError("invalid planned task identity")
    rows = []
    lines = (path / "tasks.jsonl").read_bytes().splitlines(keepends=True)
    for i, raw in enumerate(lines):
        # An unterminated final line is a torn write, not completed evidence.
        if i == len(lines) - 1 and not raw.endswith(b"\n"):
            break
        row = json.loads(raw)
        validate_record(row)
        if meta["task_repos"].get(row["task_id"]) != row["repo"]:
            raise ValueError("task/repository identity mismatch")
        # Derive corrections from retained official verification logs, never rewrite history.
        log_root = (path / "official" / "test_outputs").resolve()
        log = log_root / (row["task_id"].replace("/", "__") + ".log")
        if not log.resolve().is_relative_to(log_root):
            raise ValueError("unsafe verification log identity")
        if row["resolved"] is False and log.is_file():
            outcome = verification_outcome(False, log.read_text(encoding="utf-8", errors="replace"))
            if outcome["verification_status"] == "HARNESS_ENVIRONMENT_ERROR":
                prior_errors = row["harness_errors"]
                row = dict(row, **outcome)
                row["harness_errors"] = sorted(set(prior_errors + outcome["harness_errors"]))
                row["classification_source"] = "RETAINED_OFFICIAL_VERIFICATION_LOG"
        rows.append(row)
    ids = [r["task_id"] for r in rows]
    if len(set(ids)) != len(ids) or not set(ids) <= set(meta["task_ids"]):
        raise ValueError("duplicate or unexpected task result")
    return meta, rows


def projection(times: list[float], startup: float | None, complete: bool) -> dict:
    if any(type(t) not in (float, int) or not math.isfinite(t) or t < 0 for t in times):
        raise ValueError("invalid projection duration")
    if startup is not None and (type(startup) not in (float, int) or not math.isfinite(startup) or startup < 0):
        raise ValueError("invalid startup duration")
    if not times or startup is None:
        return {"gate": "INCONCLUSIVE", "mean_hours": None, "p95_hours": None}
    p95 = sorted(times)[math.ceil(0.95 * len(times)) - 1]
    mean_hours = (startup + 116 * statistics.mean(times)) / 3600
    p95_hours = (startup + 116 * p95) / 3600
    return {"gate": "FAIL" if max(mean_hours, p95_hours) > 11 else ("PASS" if complete else "INCONCLUSIVE"),
            "mean_hours": mean_hours, "p95_hours": p95_hours, "p95_task_seconds": p95,
            "method": "116 sequential tasks; nearest-rank sample p95, not a confidence bound"}


def categories(row: dict) -> list[str]:
    if row.get("verification_status") == "HARNESS_ENVIRONMENT_ERROR":
        return ["harness_error", "HARNESS_ENVIRONMENT_ERROR"]
    result = []
    if row["patch_bytes"] == 0:
        result.append("no_edit")
    if row["submit_patch_called"] is False:
        result.append("no_submit")
    if row["stop_reason"] in {"call_budget", "time_budget", "turn_budget", "wall_guard"}:
        result.append("budget_exhausted")
    if row["harness_errors"]:
        result.append("harness_error")
    if row.get("verification_status") == "failed":
        result.append("tests_fail")
    # Wrong-location and stray-file judgments require independent human evidence.
    return result


def summarize(meta: dict, rows: list[dict]) -> dict:
    n = len(meta["task_ids"])
    complete = len(rows) == n and all(r["resolved"] is not None for r in rows)
    time_complete = complete and meta.get("completion_state") == "COMPLETED" and not any(r["harness_errors"] or r["stop_reason"] == "wall_guard" for r in rows)
    passed = sum(r["resolved"] is True for r in rows)
    tools, failures = Counter(), Counter()
    repos = {}
    for repo in sorted(set(meta["task_repos"].values())):
        rr = [r for r in rows if r["repo"] == repo]
        planned = sum(v == repo for v in meta["task_repos"].values())
        repos[repo] = {"passed": sum(r["resolved"] is True for r in rr), "planned": planned,
                       "scorable": sum(r["resolved"] is not None for r in rr),
                       "harness_environment_errors": sum(r.get("verification_status") == "HARNESS_ENVIRONMENT_ERROR" for r in rr),
                       "observed": len(rr), "pass_rate_lower_bound": sum(r["resolved"] is True for r in rr) / planned,
                       "caveat": "ANECDOTAL n=1" if repo.lower().endswith("/httpx") else "small n"}
    for r in rows:
        tools.update(r["tool_calls"] or {})
        failures.update(categories(r))
    return {"planned": n, "observed": len(rows), "passed": passed,
            "unresolved": sum(r["resolved"] is False for r in rows),
            "harness_environment_errors": sum(r.get("verification_status") == "HARNESS_ENVIRONMENT_ERROR" for r in rows),
            "scorable_tasks": sum(r["resolved"] is not None for r in rows),
            "scorable_pass_rate": passed / sum(r["resolved"] is not None for r in rows) if any(r["resolved"] is not None for r in rows) else None,
            "pass_rate": passed / n if complete else None, "pass_rate_lower_bound": passed / n,
            "repo_macro_pass_rate": statistics.mean(r["pass_rate_lower_bound"] for r in repos.values()) if complete else None,
            "repo_macro_lower_bound": statistics.mean(r["pass_rate_lower_bound"] for r in repos.values()),
            "scorable_repo_macro_pass_rate": statistics.mean(r["passed"] / r["scorable"] for r in repos.values() if r["scorable"]) if any(r["scorable"] for r in repos.values()) else None,
            "scorable_macro_excluded_repos": [repo for repo, r in repos.items() if not r["scorable"]],
            "complete": complete, "by_repo": repos, "tool_usage": dict(tools),
            "stop_reasons": dict(Counter(r["stop_reason"] for r in rows)),
            "tool_call_limit_hits": sum(r["stop_reason"] == "call_budget" for r in rows),
            "observed_tokens": sum(r["tokens"] or 0 for r in rows),
            "tokens_unknown_tasks": sum(r["tokens"] is None for r in rows),
            "per_task": [{k: r.get(k) for k in ("task_id", "repo", "resolved", "official_resolved", "verification_status", "wall_seconds", "stop_reason", "model_turns", "tool_calls", "tokens", "harness_errors")} for r in rows],
            "tool_telemetry_unknown_tasks": sum(r["tool_calls"] is None for r in rows),
            "failure_categories_nonexclusive": dict(failures), "wrong_location": "UNKNOWN: human review required",
            "time_fit": projection([r["wall_seconds"] for r in rows], meta.get("startup_seconds"), time_complete),
            "caveat": "Public development evidence only; small n; task count/hidden concurrency unverified."}


def paired(a_meta: dict, a: list[dict], b_meta: dict, b: list[dict]) -> dict:
    for key in ("subset_sha256", "subset", "source_sha256", "official_tasks_sha256", "task_ids", "task_repos", "runtime_pins", "source_pins_sha256"):
        if a_meta[key] != b_meta[key]:
            raise ValueError("unpaired run contract: " + key)
    if len(a) != len(a_meta["task_ids"]) or len(b) != len(b_meta["task_ids"]):
        raise ValueError("paired comparison requires two complete subsets")
    aa, bb = {r["task_id"]: r for r in a}, {r["task_id"]: r for r in b}
    if aa.keys() != bb.keys() or any(r["resolved"] is None or r["harness_errors"] for r in a + b):
        raise ValueError("paired comparison has unknown outcomes")
    wins = [k for k in aa if bb[k]["resolved"] and not aa[k]["resolved"]]
    losses = [k for k in aa if aa[k]["resolved"] and not bb[k]["resolved"]]
    n = len(wins) + len(losses)
    p = min(1.0, 2 * sum(math.comb(n, i) for i in range(min(len(wins), len(losses)) + 1)) / 2**n) if n else 1.0
    return {"b_wins": wins, "b_losses": losses, "ties": len(a) - n, "discordant": n,
            "exact_two_sided_sign_test_p": p, "caveat": "Small n; stochastic runs, shared repos and dev-set tuning limit inference; no causal improvement claim."}


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    f = sub.add_parser("freeze")
    f.add_argument("tasks", type=Path)
    f.add_argument("output", type=Path)
    f.add_argument("--label-field")
    a = sub.add_parser("analyze", aliases=["summary"])
    a.add_argument("run", type=Path)
    a.add_argument("--compare", type=Path)
    args = parser.parse_args()
    if args.command == "freeze":
        if any((p / ".git").exists() for p in args.tasks.resolve().parents):
            raise ValueError("metadata source must remain outside the repository")
        rows = [json.loads(s) for s in args.tasks.read_text(encoding="utf-8").splitlines() if s.strip()]
        doc = freeze(rows, sha(args.tasks), args.label_field)
        with args.output.open("xb") as stream:
            stream.write(canonical(doc))
        print("SUBSET_SHA256=" + sha(args.output))
        print("REVIEW_AND_FREEZE_BEFORE_GPU_EXECUTION")
    else:
        meta, rows = read_run(args.run)
        report = summarize(meta, rows)
        if args.compare:
            other_meta, other = read_run(args.compare)
            report["comparison"] = paired(meta, rows, other_meta, other)
        print(json.dumps(report, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
