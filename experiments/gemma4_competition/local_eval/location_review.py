"""Offline location-only evaluation. Never supply these records to an agent."""
import argparse
from collections import Counter
import json
from pathlib import Path
import re
from analysis import canonical, read_run, load_controls, sha
from location_metadata import parse_diff, old_changed_lines


def classify(row, gold, patch):
    result = {"category": "TOOL_FORMAT/OTHER", "file_hit": None, "function_hit": None,
              "agent_files": [], "agent_functions": [], "extra_files": [], "reason": "UNKNOWN"}
    if row.get("completed_result") is False or row["resolved"] is None or row["harness_errors"]:
        return dict(result, reason="INCOMPLETE_OR_ENVIRONMENT")
    if row["resolved"]:
        return dict(result, category="RESOLVED", reason="OFFICIAL_RESULT")
    if "TOOL_CALL_FORMAT_FAILURE" in row.get("failure_categories", []):
        return dict(result, reason="TOOL_CALL_FORMAT_FAILURE")
    if row.get("patch_bytes") == 0:
        return dict(result, category="NO_EDIT", reason="EMPTY_RETAINED_PATCH")
    if patch is None:
        return dict(result, reason="PATCH_UNAVAILABLE")
    try:
        changes = parse_diff(patch)
    except ValueError:
        return dict(result, reason="PATCH_FORMAT_UNSUPPORTED")
    files = sorted({f["old"] or f["new"] for f in changes})
    overlap = set(files) & set(gold["gold_files"])
    result.update(agent_files=files, file_hit=bool(overlap), extra_files=sorted(set(files) - set(gold["gold_files"])))
    if gold["location_status"] == "UNRESOLVED" or not gold["gold_files"]:
        return dict(result, reason="GOLD_LOCATION_UNRESOLVED")
    if not overlap:
        return dict(result, category="WRONG_LOCATION", reason="NO_GOLD_FILE_OVERLAP")
    hit, unknown = False, False
    for change in changes:
        path = change["old"] or change["new"]
        points = old_changed_lines(change)
        scopes = [f for f in gold["gold_functions"] if f["file"] == path and f["name"] != "UNRESOLVED"]
        matched = [f["name"] for f in scopes if any(f["start"] <= p <= f["end"] for p in points)]
        hit = hit or bool(matched)
        result["agent_functions"].append({"file": path, "names": sorted(set(matched)) or ["UNRESOLVED"],
                                          "basis": "agent old-line overlap with exported snapshot scopes only"})
        if path in overlap and (not points or any(f["name"] == "UNRESOLVED" for f in gold["gold_functions"] if f["file"] == path)):
            unknown = True
    result["function_hit"] = True if hit else (None if unknown else False)
    if hit:
        return dict(result, category="RIGHT_LOCATION_WRONG_FIX", reason="GOLD_SCOPE_OVERLAP_BUT_UNRESOLVED")
    if not unknown and gold["location_status"] == "RESOLVED":
        return dict(result, category="WRONG_LOCATION", reason="FILE_HIT_WITHOUT_GOLD_SCOPE_OVERLAP")
    return dict(result, reason="FUNCTION_LOCATION_UNRESOLVED")


def validate_metadata(doc):
    if set(doc) != {"schema", "official_tasks_sha256", "coordinate_system", "tasks"} or doc["schema"] != 1 or len(doc["tasks"]) != 129:
        raise ValueError("expected metadata-only 129-task export")
    seen = set()
    for row in doc["tasks"]:
        if set(row) != {"task_id", "repo", "gold_files", "gold_functions", "hunk_count", "lines_changed_count", "location_status"}:
            raise ValueError("unexpected metadata fields")
        if row["task_id"] in seen or not re.fullmatch(r"[A-Za-z0-9_.-]+", row["task_id"]):
            raise ValueError("invalid task identity")
        if row["repo"] not in {"fastapi/fastapi", "Textualize/rich", "psf/requests", "encode/httpx"} or row["location_status"] not in {"RESOLVED", "PARTIAL", "UNRESOLVED"}:
            raise ValueError("invalid repository/resolution metadata")
        for field in ("hunk_count", "lines_changed_count"):
            if row[field] is not None and (type(row[field]) is not int or row[field] < 0):
                raise ValueError("invalid location count")
        seen.add(row["task_id"])
        from location_metadata import safe_path, is_test
        for path in row["gold_files"]:
            if safe_path(path) != path or is_test(path):
                raise ValueError("unsafe/nonproduction gold location")
        for f in row["gold_functions"]:
            if set(f) != {"file", "name", "start", "end"} or f["file"] not in row["gold_files"] or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)*", f["name"]):
                raise ValueError("invalid function metadata")
            if f["name"] != "UNRESOLVED" and (type(f["start"]) is not int or type(f["end"]) is not int or not 1 <= f["start"] <= f["end"]):
                raise ValueError("invalid source span")
            if f["name"] == "UNRESOLVED" and (f["start"] is not None or f["end"] is not None):
                raise ValueError("unresolved span must be null")


def retained_patch(folder, row, sources, meta):
    """Follow hash-identified attempt ancestry; never use a different candidate's patch."""
    seen = set()
    while row.get("inherited_from_run_sha256"):
        pin = row["inherited_from_run_sha256"]
        if pin in seen:
            raise ValueError("cyclic attempt provenance")
        seen.add(pin)
        folder = sources.get(pin)
        if folder is None:
            return None
        prior, rows = read_run(folder)
        for key in ("candidate", "package_sha256", "official_tasks_sha256"):
            if prior.get(key) != meta.get(key):
                raise ValueError("inherited patch identity mismatch")
        row = next((r for r in rows if r["task_id"] == row["task_id"]), None)
        if row is None:
            return None
    return folder / "official/patches" / (row["task_id"] + ".patch")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", action="append", required=True, metavar="LABEL=FOLDER")
    parser.add_argument("--attempt", action="append", default=[], type=Path, help="Prior attempt folder for inherited patches")
    parser.add_argument("--gold", type=Path, required=True)
    parser.add_argument("--gold-sha256", required=True)
    parser.add_argument("--controls", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if sha(args.gold) != args.gold_sha256:
        raise ValueError("gold metadata pin mismatch")
    doc = json.loads(args.gold.read_bytes())
    validate_metadata(doc)
    gold = {r["task_id"]: r for r in doc["tasks"]}
    output = args.output.resolve()
    if output.is_relative_to(Path(__file__).resolve().parents[3]) or any((p / ".git").exists() for p in output.parents):
        raise ValueError("analysis outputs must remain outside repositories")
    folders = {}
    for item in args.run:
        label, sep, folder = item.partition("=")
        if not sep or not re.fullmatch(r"[A-Za-z0-9_-]+", label) or label in folders:
            raise ValueError("unique safe LABEL=FOLDER required")
        folders[label] = Path(folder)
    sources = {sha(p / "run.json"): p for p in list(folders.values()) + args.attempt}
    rows, counts = [], {}
    for label, folder in folders.items():
        meta, records = read_run(folder)
        controls = load_controls(args.controls, "05706c6a948a67bfaf991ed0282d11308aac79865a614a68c6c582fe01f67033", meta)
        if meta["official_tasks_sha256"] != doc["official_tasks_sha256"]:
            raise ValueError("task inventory differs from gold metadata")
        counts[label] = Counter()
        by_id = {r["task_id"]: r for r in records}
        for tid in meta["task_ids"]:
            if controls[tid]["class"] != "VERIFIABLE":
                continue
            if gold[tid]["repo"] != meta["task_repos"][tid]:
                raise ValueError("gold repository mismatch")
            row = by_id.get(tid)
            if row is None:
                assessment = {"category": "TOOL_FORMAT/OTHER", "reason": "MISSING_RESULT"}
                patch_pin = None
            else:
                path = retained_patch(folder, row, sources, meta)
                patch = path.read_text(encoding="utf-8") if path and path.is_file() else None
                patch_pin = sha(path) if patch is not None else None
                assessment = classify(row, gold[tid], patch)
            counts[label][assessment["category"]] += 1
            rows.append({"run": label, "task_id": tid, "patch_sha256": patch_pin, **assessment})
    output.mkdir(parents=True, exist_ok=False)
    (output / "locations.json").write_bytes(canonical({"gold_sha256": args.gold_sha256, "counts": counts, "tasks": rows}))
    table = ["| Task | " + " | ".join(folders) + " |", "|---|" + "---|" * len(folders)]
    for tid in sorted({r["task_id"] for r in rows}):
        table.append("| " + tid + " | " + " | ".join(next((r["category"] for r in rows if r["task_id"] == tid and r["run"] == label), "NOT_PLANNED") for label in folders) + " |")
    (output / "locations.md").write_text("\n".join(table) + "\n\nCounts:\n\n" + json.dumps(counts, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
