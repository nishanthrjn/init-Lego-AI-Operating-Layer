"""Data-only diff/AST location extraction. Never execute repository source."""
import ast
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import tarfile

AUTHORIZATION = "AUTHORIZE FORGEAI GEMMA4 GOLD LOCATION METADATA EXPORT CPU"
HUNK = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")


def safe_path(value):
    if value == "/dev/null":
        return None
    value = value.split("\t", 1)[0]
    if value.startswith(("a/", "b/")):
        value = value[2:]
    if not re.fullmatch(r"[A-Za-z0-9_./-]+", value) or any(p in {"..", ".git"} for p in PurePosixPath(value).parts) or value.startswith("/"):
        raise ValueError("unsupported diff path")
    return value


def is_test(path):
    p = PurePosixPath(path)
    return (any(v.lower() in {"tests", "test", "testing"} for v in p.parts)
            or p.name.startswith("test_") or p.name.endswith("_test.py")
            or p.name in {"conftest.py", "pytest.ini", ".pytest.ini"})


def parse_diff(text):
    """Internal structure includes source; callers export only explicit projections."""
    files, current, hunk = [], None, None
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("diff --git "):
            current, hunk = None, None
        if hunk is None and line.startswith("--- ") and i + 1 < len(lines) and lines[i + 1].startswith("+++ "):
            current = {"old": safe_path(line[4:]), "new": safe_path(lines[i + 1][4:]), "hunks": []}
            files.append(current)
            hunk = None
            i += 2
            continue
        match = HUNK.match(line)
        if match and current is not None:
            hunk = {"old_start": int(match[1]), "old_count": int(match[2] or 1),
                    "new_start": int(match[3]), "new_count": int(match[4] or 1), "lines": []}
            current["hunks"].append(hunk)
        elif hunk is not None and line[:1] in {" ", "+", "-"}:
            hunk["lines"].append(line)
            old_n = sum(s[0] in " -" for s in hunk["lines"])
            new_n = sum(s[0] in " +" for s in hunk["lines"])
            if old_n == hunk["old_count"] and new_n == hunk["new_count"]:
                hunk = None
        i += 1
    if hunk is not None or (text.strip() and not files):
        raise ValueError("unsupported or incomplete diff")
    return files


def old_changed_lines(file):
    points = []
    for h in file["hunks"]:
        old = h["old_start"]
        for line in h["lines"]:
            if line.startswith("-"):
                points.append(old)
            elif line.startswith("+"):
                # Insertion anchor in original snapshot; never infer new function names.
                points.append(max(1, old))
            if not line.startswith("+"):
                old += 1
    return sorted(set(points))


def function_spans(source):
    tree = ast.parse(source)
    spans = []
    def visit(node, parents):
        scope = isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
        names = parents + [node.name] if scope else parents
        if scope:
            start = min([node.lineno] + [d.lineno for d in node.decorator_list])
            spans.append({"name": ".".join(names), "start": start, "end": node.end_lineno})
        for child in ast.iter_child_nodes(node):
            visit(child, names)
    visit(tree, [])
    return spans


def functions_at(source, points):
    try:
        spans = function_spans(source)
    except (SyntaxError, ValueError, TypeError, UnicodeError):
        return [{"name": "UNRESOLVED", "start": None, "end": None}]
    selected = []
    for point in points:
        matches = [s for s in spans if s["start"] <= point <= s["end"]]
        scope = min(matches, key=lambda s: s["end"] - s["start"]) if matches else {"name": "UNRESOLVED", "start": None, "end": None}
        if scope not in selected:
            selected.append(scope)
    return selected or [{"name": "UNRESOLVED", "start": None, "end": None}]


def archive_source(archive, path):
    with tarfile.open(archive, "r:*") as tar:
        matches = [m for m in tar if m.name.removeprefix("./") in {path, "workspace/" + path}]
        if len(matches) != 1 or not matches[0].isfile() or matches[0].size > 8 * 1024 * 1024:
            raise ValueError("snapshot source unavailable")
        return tar.extractfile(matches[0]).read().decode("utf-8")


def apply_text(source, change):
    old, result, position = source.splitlines(), [], 0
    for h in change["hunks"]:
        begin = h["old_start"] - 1 if h["old_count"] else h["old_start"]
        before = [s[1:] for s in h["lines"] if s[0] in " -"]
        after = [s[1:] for s in h["lines"] if s[0] in " +"]
        if begin < position or old[begin:begin + len(before)] != before:
            raise ValueError("snapshot delta mismatch")
        result.extend(old[position:begin])
        result.extend(after)
        position = begin + len(before)
    return "\n".join(result + old[position:]) + "\n"


def snapshot_source(snapshots, tid, repo, path):
    fallback = snapshots / "fallbacks" / (tid + ".tgz")
    if fallback.is_file():
        return archive_source(fallback, path)
    clean = re.sub(r"[/\\-]+", "_", repo.strip()).strip("_")
    base = next((p for p in (snapshots / "base_snapshots" / f"base_{clean}.tgz", snapshots / f"base_{clean}.tgz") if p.is_file()), None)
    delta = next((p for p in (snapshots / "patches" / (tid + ".patch"), snapshots / (tid + ".patch")) if p.is_file()), None)
    if base is not None and delta is not None:
        changes = parse_diff(delta.read_text(encoding="utf-8"))
        change = next((c for c in changes if c["new"] == path or c["old"] == path), None)
        if change is None:
            return archive_source(base, path)
        source = archive_source(base, change["old"]) if change["old"] else ""
        return apply_text(source, change)
    direct = next((snapshots / (tid + ext) for ext in (".tgz", ".tar.gz") if (snapshots / (tid + ext)).is_file()), None)
    return archive_source(direct, path)


def locations(task, source_reader):
    try:
        files = [f for f in parse_diff(task["patch"]) if not any(is_test(p) for p in (f["old"], f["new"]) if p)]
    except ValueError:
        return {"task_id": task["instance_id"], "repo": task["repo"], "gold_files": [],
                "gold_functions": [], "hunk_count": None, "lines_changed_count": None,
                "location_status": "UNRESOLVED"}
    functions = []
    for file in files:
        path = file["old"] or file["new"]
        try:
            source = source_reader(path) if file["old"] and path.endswith(".py") else None
        except (OSError, ValueError, TypeError, UnicodeError, tarfile.TarError):
            source = None
        scopes = functions_at(source, old_changed_lines(file))
        functions.extend({"file": path, **scope} for scope in scopes)
    return {"task_id": task["instance_id"], "repo": task["repo"],
            "gold_files": sorted({f["old"] or f["new"] for f in files}),
            "gold_functions": functions, "location_status": "PARTIAL" if any(f["name"] == "UNRESOLVED" for f in functions) else "RESOLVED",
            "hunk_count": sum(len(f["hunks"]) for f in files),
            "lines_changed_count": sum(line[0] in "+-" for f in files for h in f["hunks"] for line in h["lines"])}


def export(data, output, authorization, cpu_confirmed, internet_off):
    if authorization != AUTHORIZATION or cpu_confirmed is not True or internet_off is not True:
        raise ValueError("exact CPU export authorization required")
    import sys
    if sys.platform != "linux" or Path("/dev/nvidia0").exists():
        raise ValueError("CPU Kaggle session required")
    if output != Path("/kaggle/working/gold-locations.json") or output.exists() or output.with_suffix(".sha256").exists():
        raise ValueError("fresh metadata output required")
    raw = (data / "tasks.jsonl").read_bytes()
    tasks = [json.loads(line) for line in raw.splitlines() if line.strip()]
    if len(tasks) != 129 or len({t["instance_id"] for t in tasks}) != 129:
        raise ValueError("expected 129 unique public tasks")
    rows = []
    for task in tasks:
        tid, repo = task["instance_id"], task["repo"]
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", tid) or repo not in {"fastapi/fastapi", "Textualize/rich", "psf/requests", "encode/httpx"}:
            raise ValueError("unexpected public identity")
        # Never read test_patch or pass any task content to an agent.
        rows.append(locations(task, lambda p: snapshot_source(data / "snapshots", tid, repo, p)))
    doc = {"schema": 1, "official_tasks_sha256": hashlib.sha256(raw).hexdigest(),
           "coordinate_system": "pre-change snapshot; insertion anchors; deepest enclosing AST scope",
           "tasks": rows}
    payload = (json.dumps(doc, indent=2, sort_keys=True) + "\n").encode()
    with output.open("xb") as stream:
        stream.write(payload)
    digest = hashlib.sha256(payload).hexdigest()
    with output.with_suffix(".sha256").open("x") as stream:
        stream.write(digest + "  gold-locations.json\n")
    print("GOLD_LOCATIONS_SHA256=" + digest)
