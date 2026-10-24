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
import random
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


def verification_outcome(official_resolved: bool, output: str, repo: str = "") -> dict:
    own = repo.rsplit("/", 1)[-1].lower()
    modules = re.findall(r"ModuleNotFoundError: No module named ['\"]([A-Za-z0-9_.-]+)['\"]", output)
    imports = re.findall(r"ImportError: cannot import name ['\"][^'\"]+['\"] from ['\"]([A-Za-z0-9_.-]+)['\"]", output)
    attrs = re.findall(r"AttributeError: module ['\"]([A-Za-z0-9_.-]+)['\"] has no attribute", output)
    # Classify the named failing module, not whichever repository appears in a traceback.
    own_error = own in REPOS and any(m.split('.')[0].lower() == own for m in modules + imports + attrs)
    external = any(m.split('.')[0].lower() not in REPOS | {"tests", "test", "conftest", "__main__"}
                   for m in modules + imports)
    collection = bool(re.search(r"ERROR collecting\b|errors? during collection\b|ImportError while loading conftest", output, re.I))
    if not official_resolved and external and (collection or imports or repo):
        return {"resolved": None, "official_resolved": False,
                "verification_status": "HARNESS_ENVIRONMENT_ERROR",
                "harness_errors": ["HARNESS_ENVIRONMENT_ERROR"]}
    if not official_resolved and own_error:
        return {"resolved": False, "official_resolved": False,
                "verification_status": "UNRESOLVED_INCOMPLETE_API", "harness_errors": []}
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
    if name == "dev-16v":
        if sha(path) != expected_sha or expected_sha != "5a91f0513a3cdddea3eb7a2a3f5208ebdd40a5ab41821f29f6a31a4f07585056":
            raise ValueError("derived subset hash mismatch")
        derived = json.loads(path.read_bytes())
        root = Path(__file__).parent
        parent, rows = load_subset(root / "subsets.json", derived["parent_sha256"], "dev-30")
        controls_path = root / "evidence/controls-05706c6a.json"
        if sha(controls_path) != derived["controls_sha256"]:
            raise ValueError("derived controls hash mismatch")
        ids = {r["task_id"] for r in json.loads(controls_path.read_bytes())["tasks"] if r["class"] == "VERIFIABLE"}
        expected = [r for r in rows if r["task_id"] in ids]
        if derived["tasks"] != expected or len(expected) != 16:
            raise ValueError("derived subset selection mismatch")
        return parent, expected
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
    official = {}
    official_file = path / "official/task_results.jsonl"
    if official_file.is_file():
        for raw in official_file.read_bytes().splitlines(keepends=True):
            if not raw.endswith(b"\n"):
                continue
            item = json.loads(raw)
            tid = item["instance_id"]
            if tid in official or meta["task_repos"].get(tid) != item["repo"]:
                raise ValueError("official task result identity mismatch")
            official[tid] = item
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
            outcome = verification_outcome(False, log.read_text(encoding="utf-8", errors="replace"), row["repo"])
            if outcome["verification_status"] in {"HARNESS_ENVIRONMENT_ERROR", "UNRESOLVED_INCOMPLETE_API"}:
                prior_errors = row["harness_errors"]
                if outcome["verification_status"] == "UNRESOLVED_INCOMPLETE_API":
                    prior_errors = [e for e in prior_errors if e != "VERIFICATION_ERROR_OR_INCOMPLETE"]
                row = dict(row, **outcome)
                row["harness_errors"] = sorted(set(prior_errors + outcome["harness_errors"]))
                row["classification_source"] = "RETAINED_OFFICIAL_VERIFICATION_LOG"
        agent_log = path / "official/logs" / (row["task_id"].replace("/", "__") + ".log")
        if not agent_log.resolve().is_relative_to((path / "official/logs").resolve()):
            raise ValueError("unsafe agent log identity")
        from continuation import project
        evidence = official.get(row["task_id"])
        if evidence is not None and evidence["resolved"] != row.get("official_resolved", row["resolved"]):
            raise ValueError("official outcome disagreement")
        row = project(row, error=(evidence.get("error") or "") if evidence else "",
                      log=agent_log.read_text(encoding="utf-8", errors="replace") if agent_log.is_file() else "")
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
    rng = random.Random(20261022)
    totals = sorted((startup + math.fsum(rng.choices(times, k=116))) / 3600 for _ in range(10000))
    upper = totals[math.ceil(0.95 * len(totals)) - 1]
    return {"gate": "FAIL" if upper > 11 else ("PASS" if complete else "INCONCLUSIVE"),
            "mean_hours": mean_hours, "p95_hours": p95_hours, "p95_task_seconds": p95,
            "bootstrap_upper95_hours": upper, "bootstrap_seed": 20261022, "bootstrap_replicates": 10000,
            "method": "Empirical bootstrap predictive total: 116 task times sampled with replacement plus fixed startup; one-sided 95th percentile. Assumes iid representative tasks; small-n and repo dependence limit coverage. p95*116 is informational, not a strict worst-case bound."}


def categories(row: dict) -> list[str]:
    if row.get("verification_status") == "HARNESS_ENVIRONMENT_ERROR":
        return ["harness_error", "HARNESS_ENVIRONMENT_ERROR"]
    result = list(row.get("failure_categories", []))
    if row["patch_bytes"] == 0:
        result.append("no_edit")
    if row["submit_patch_called"] is False:
        result.append("no_submit")
    if row["stop_reason"] in {"call_budget", "time_budget", "turn_budget", "wall_guard"}:
        result.append("budget_exhausted")
    if row["harness_errors"]:
        result.append("harness_error")
    if row.get("verification_status") in {"failed", "UNRESOLVED_INCOMPLETE_API"}:
        result.append("tests_fail")
    if row.get("verification_status") == "UNRESOLVED_INCOMPLETE_API":
        result.append("UNRESOLVED_INCOMPLETE_API")
    # Wrong-location and stray-file judgments require independent human evidence.
    return result


def summarize_observations(meta: dict, rows: list[dict]) -> dict:
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


def load_controls(path: Path, digest: str, meta: dict) -> dict:
    """Accept only pinned, complete, metadata-only controls for this frozen environment."""
    from controls import classify, safe_result, CLASSES
    if not re.fullmatch(r"[0-9a-f]{64}", digest) or sha(path) != digest:
        raise ValueError("controls SHA256 mismatch")
    doc = json.loads(path.read_bytes())
    fields = {"schema", "state", "subset_sha256", "official_tasks_sha256", "source_pins_sha256",
              "runtime_pins", "backend", "verification_timeout_seconds", "tasks"}
    if set(doc) != fields or doc["schema"] != 1 or doc["state"] != "COMPLETE":
        raise ValueError("complete metadata-only controls required")
    for key in ("subset_sha256", "official_tasks_sha256", "source_pins_sha256", "runtime_pins"):
        if key == "subset_sha256" and meta["subset"] == "dev-16v":
            _, selected = load_subset(Path(__file__).parent / "dev-16v.json", meta[key], "dev-16v")
            if meta["task_ids"] != [r["task_id"] for r in selected]:
                raise ValueError("derived run task identity mismatch")
            continue
        if doc[key] != meta[key]:
            raise ValueError("controls/run identity mismatch: " + key)
    if doc["backend"] != "subprocess" or doc["verification_timeout_seconds"] != 300:
        raise ValueError("unsupported controls verification contract")
    if meta.get("evaluation_config", {}).get("verification_timeout_seconds", 300) != 300:
        raise ValueError("agent/control verification timeout mismatch")
    freeze_path = Path(__file__).parent / "subsets.json"
    frozen, _ = load_subset(freeze_path, doc["subset_sha256"], "dev-30")
    expected = {r["task_id"]: r["repo"] for r in frozen["dev-30"] + frozen["confirm-20"]}
    seen = {}
    for row in doc["tasks"]:
        if set(row) != {"task_id", "repo", "class", "gold", "empty"} or row["class"] not in CLASSES:
            raise ValueError("unexpected control fields")
        if row["task_id"] in seen or expected.get(row["task_id"]) != row["repo"]:
            raise ValueError("control task identity mismatch")
        for mode in ("gold", "empty"):
            value = row[mode]
            if set(value) != {"passed", "error_category", "seconds"}:
                raise ValueError("control payload must contain only bounded metadata")
            safe_result(value["passed"], value["error_category"], value["seconds"])
            if value["passed"] != (value["error_category"] == "NONE"):
                raise ValueError("control outcome/category contradiction")
        if classify(row["gold"], row["empty"]) != row["class"]:
            raise ValueError("control classification mismatch")
        seen[row["task_id"]] = row
    if seen.keys() != expected.keys():
        raise ValueError("all 50 frozen controls required")
    return seen


def summarize(meta: dict, rows: list[dict], controls: dict | None = None) -> dict:
    observations = summarize_observations(meta, rows)
    classes = {tid: controls[tid]["class"] if controls and tid in controls else "UNASSESSED"
               for tid in meta["task_ids"]}
    eligible = [r for r in rows if classes[r["task_id"]] == "VERIFIABLE"]
    expected = [tid for tid, cls in classes.items() if cls == "VERIFIABLE"]
    clean = [r for r in eligible if r["resolved"] is not None and not r["harness_errors"]]
    complete = bool(expected) and len(clean) == len(expected)
    passed = sum(r["resolved"] is True for r in clean)
    repos = {}
    for repo in sorted(set(meta["task_repos"].values())):
        rr = [r for r in clean if r["repo"] == repo]
        planned = sum(meta["task_repos"][tid] == repo for tid in expected)
        repos[repo] = {"verifiable": planned, "scored": len(rr),
                       "passed": sum(r["resolved"] is True for r in rr),
                       "pass_rate": sum(r["resolved"] is True for r in rr) / planned if planned and len(rr) == planned else None}
    macro_values = [r["pass_rate"] for r in repos.values() if r["pass_rate"] is not None]
    for row in observations["per_task"]:
        row["control_class"] = classes[row["task_id"]]
        row["agent_verdict"] = ("RESOLVED" if row["resolved"] else "UNRESOLVED") if (
            row["control_class"] == "VERIFIABLE" and row["resolved"] is not None and not row["harness_errors"]
        ) else "EXCLUDED_OR_UNKNOWN"
    return {"controls_status": "PINNED_CONTROLS_APPLIED" if controls else "CONTROLS_REQUIRED",
            "planned": len(meta["task_ids"]), "observed": len(rows), "verifiable": len(expected),
            "excluded_counts": dict(Counter(c for c in classes.values() if c != "VERIFIABLE")),
            "passed": passed, "unresolved": len(clean) - passed, "complete": complete,
            "pass_rate": passed / len(expected) if complete else None,
            "repo_macro_pass_rate": statistics.mean(macro_values) if complete and macro_values else None,
            "by_repo": repos, "macro_excluded_repos": [k for k, v in repos.items() if not v["verifiable"]],
            "time_fit": projection([r["wall_seconds"] for r in rows], meta.get("startup_seconds"),
                                   complete and len(rows) == len(meta["task_ids"]) and not any(r["harness_errors"] for r in rows)
                                   and meta.get("completion_state") == "COMPLETED"),
            "per_task": observations.pop("per_task"),
            "descriptive_observations_not_control_qualified": observations,
            "caveat": "Agent verdicts require VERIFIABLE controls. Raw observed rates are descriptive only; exclusions change the population."}


def paired(a_meta: dict, a: list[dict], b_meta: dict, b: list[dict], controls: dict | None = None) -> dict:
    if not controls:
        raise ValueError("paired agent verdicts require pinned controls")
    for key in ("subset_sha256", "subset", "source_sha256", "official_tasks_sha256", "task_ids", "task_repos", "runtime_pins", "source_pins_sha256"):
        if a_meta[key] != b_meta[key]:
            raise ValueError("unpaired run contract: " + key)
    if len(a) != len(a_meta["task_ids"]) or len(b) != len(b_meta["task_ids"]):
        raise ValueError("paired comparison requires two complete subsets")
    a = [r for r in a if controls[r["task_id"]]["class"] == "VERIFIABLE"]
    b = [r for r in b if controls[r["task_id"]]["class"] == "VERIFIABLE"]
    if not a:
        raise ValueError("no VERIFIABLE paired tasks")
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
    a.add_argument("--controls", type=Path)
    a.add_argument("--controls-sha256")
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
        if bool(args.controls) != bool(args.controls_sha256):
            raise ValueError("supply controls file and independently retained SHA256 together")
        controls = load_controls(args.controls, args.controls_sha256, meta) if args.controls else None
        report = summarize(meta, rows, controls)
        report["controls_sha256"] = args.controls_sha256
        if args.compare:
            other_meta, other = read_run(args.compare)
            if args.controls:
                load_controls(args.controls, args.controls_sha256, other_meta)
            report["comparison"] = paired(meta, rows, other_meta, other, controls)
        print(json.dumps(report, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
