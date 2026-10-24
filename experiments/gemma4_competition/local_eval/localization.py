"""CPU retrieval experiment. Gold is passed only to scoring, never retrieval."""
import argparse
import ast
import hashlib
import json
import logging
import re
import subprocess
import sys
import tarfile
import time
from pathlib import Path
from types import SimpleNamespace

from location_metadata import safe_path, is_test, parse_diff, apply_text, function_spans

HERE = Path(__file__).resolve().parent
AUTH = "AUTHORIZE FORGEAI GEMMA4 LOCALIZATION STUDY CPU"
GOLD_SHA = "c366076d5d2862d6a3c07c5db6f977c06bdcef8f94657f3f6591501826290c54"
FAILURES = {"rich_4076", "rich_4079", "fastapi_5077", "rich_3934", "rich_3471", "fastapi_15800"}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def check_graph_sources():
    import importlib.metadata
    pins = json.loads((HERE / "localization-source-pins.json").read_bytes())
    dist = importlib.metadata.distribution("swegemma")
    if dist.version != "0.2.11":
        raise ValueError("graph package version mismatch")
    for member, expected in pins.items():
        if digest(dist.locate_file(member)) != expected:
            raise ValueError("graph implementation mismatch")
    return pins


def tokens(text):
    # Fixed lexical rule; no tuning against gold. Quoted terms are included naturally.
    return set(re.findall(r"[A-Za-z_][A-Za-z_0-9]{2,}", text.lower()))


def index_sources(sources):
    index = []
    for path, source in sorted(sources.items()):
        module = path.removesuffix(".py").replace("/", ".").removeprefix("src.")
        if module.endswith(".__init__"):
            module = module[:-9]
        index.append({"file": path, "function": None, "symbol": module, "text": source})
        try:
            spans = function_spans(source)
        except (SyntaxError, ValueError):
            continue
        lines = source.splitlines()
        for scope in spans:
            index.append({"file": path, "function": scope["name"],
                          "symbol": module + "." + scope["name"],
                          "text": "\n".join(lines[scope["start"] - 1:scope["end"]])})
    return index


def lexical(issue, index):
    query = tokens(issue)
    scored = []
    for row in index:
        words = re.findall(r"[A-Za-z_][A-Za-z_0-9]*", row["text"].lower())
        hits = sum(w in query for w in words)
        if hits:
            scored.append((hits / max(1, len(words)), row))
    return [r[1]["symbol"] for r in sorted(scored, key=lambda r: (-r[0], r[1]["symbol"]))[:100]]


def fuse(*rankings):
    scores = {}
    for ranking in rankings:
        for i, name in enumerate(dict.fromkeys(ranking), 1):
            scores[name] = scores.get(name, 0) + 1 / (60 + i)
    return sorted(scores, key=lambda n: (-scores[n], n))


def names_only(names, index):
    """Whitelist against snapshot AST, not gold; unknown nodes retain rank but no text."""
    result = []
    for name in dict.fromkeys(names):
        bare = name.split(";", 1)[-1]
        matches = [r for r in index if r["symbol"] == bare]
        if not matches:
            matches = [r for r in index if r["symbol"].endswith("." + bare)]
        if len(matches) == 1:
            row = matches[0]
            result.append({"name": row["symbol"], "file": row["file"], "function": row["function"]})
        else:
            result.append({"name": "UNRESOLVED", "file": None, "function": None})
    return result


def metrics(ranked, gold):
    files = list(dict.fromkeys(r["file"] for r in ranked))
    funcs = list(dict.fromkeys((r["file"], r["function"]) for r in ranked))
    gf = set(gold["gold_files"])
    gs = {(r["file"], r["name"]) for r in gold["gold_functions"] if r["name"] != "UNRESOLVED"}
    result = {"file_recall@" + str(k): len(gf & set(files[:k])) / len(gf) if gf else None for k in (1, 3, 5, 10)}
    result.update({"function_recall@" + str(k): len(gs & set(funcs[:k])) / len(gs) if gs else None for k in (5, 10)})
    result["file_mrr"] = next((1 / i for i, f in enumerate(files, 1) if f in gf), 0.0) if gf else None
    result["unmapped_nodes"] = sum(r["file"] is None for r in ranked)
    return result


def snapshot_sources(data, task):
    from swegemma.deduplication import resolve_task_snapshot_paths
    snapshot, base, delta = resolve_task_snapshot_paths(data / "snapshots", task.instance_id, task.repo)
    sources = {}
    # Static reads only: never import or execute snapshot code, never apply the reference patch.
    with tarfile.open(base or snapshot) as archive:
        for member in archive:
            if not member.isfile() or member.size > 8 * 1024 * 1024:
                continue
            name = member.name.removeprefix("./").removeprefix("workspace/")
            try:
                path = safe_path(name)
            except ValueError:
                continue
            if path and path.endswith(".py") and not is_test(path):
                if path in sources:
                    raise ValueError("duplicate snapshot member")
                sources[path] = archive.extractfile(member).read().decode("utf-8")
    if base and delta:
        for change in parse_diff(Path(delta).read_text(encoding="utf-8")):
            old, new = change["old"], change["new"]
            if new and new.endswith(".py") and not is_test(new):
                sources[new] = apply_text(sources.get(old, ""), change)
            if old and old != new:
                sources.pop(old, None)
    return sources


def retrieve(data, task):
    from swegemma.context import SwegemmaContext
    from swegemma.tools.graph import search_similar_code, get_code_neighbors, get_code_subgraph
    from swegemma.graph.embedding_utils import resolve_local_file_path
    # Deliberately exclude patch/test_patch, even from the tool context object.
    public = SimpleNamespace(instance_id=task.instance_id, repo=task.repo, base_commit=task.base_commit,
                             problem_statement=task.problem_statement, hints_text="")
    input_pins = {}
    for directory, extension in (("graphs", ".json"), ("embeddings", ".npz")):
        artifact = Path(resolve_local_file_path(str(data / directory), public.repo, extension, public.base_commit))
        input_pins[directory] = digest(artifact) if artifact.is_file() else None
    inputs_available = all(input_pins.values())
    index_start = time.process_time()
    index = index_sources(snapshot_sources(data, public))
    setup_cpu = time.process_time() - index_start
    ctx = SwegemmaContext(task=public, repo=public.repo, graph_dir=str(data / "graphs"),
                          embeddings_dir=str(data / "embeddings"), max_tool_calls=4,
                          max_time_minutes=5, max_stdout_chars=5000)
    calls = []

    def call(tool, *args, **kwargs):
        cpu, wall = time.process_time(), time.perf_counter()
        raw = tool(ctx, *args, **kwargs)
        payload = json.loads(raw)
        calls.append({"tool": tool.__name__, "chars": len(raw), "cpu_seconds": time.process_time() - cpu,
                      "wall_seconds": time.perf_counter() - wall, "status": "OK" if payload.get("status") == "ok" else "UNAVAILABLE"})
        return payload if payload.get("status") == "ok" else {}

    found = call(search_similar_code, public.problem_statement, k=10)
    t1 = [r["node_name"] for r in found.get("results", [])]
    t2 = []
    for node in t1[:2]:
        t2.append(node)
        t2.extend(call(get_code_neighbors, node, max_neighbors=10).get("neighbors", []))
    t2.extend(t1[2:])
    # Fourth call characterizes the actual subgraph interface; not another tuned method.
    if t1:
        call(get_code_subgraph, t1[:2])
    start = time.process_time()
    lex = lexical(public.problem_statement, index)
    lex_cpu = time.process_time() - start
    canonical_t1 = [r["name"] for r in names_only(t1, index) if r["name"] != "UNRESOLVED"]
    rankings = {"T1": t1, "T2": list(dict.fromkeys(t2)), "L": lex, "L+T1": fuse(lex, canonical_t1)}
    t1_ok = inputs_available and calls[0]["status"] == "OK"
    t2_ok = t1_ok and all(c["status"] == "OK" for c in calls if c["tool"] == "get_code_neighbors")
    return {"task_id": task.instance_id, "repo": task.repo, "calls": calls, "snapshot_index_cpu_seconds": setup_cpu,
            "input_sha256": input_pins,
            "retrieval_state": "OK" if inputs_available and all(c["status"] == "OK" for c in calls) else "PARTIAL_UNAVAILABLE",
            "method_available": {"T1": t1_ok, "T2": t2_ok, "L": True, "L+T1": t1_ok},
            "lexical_cpu_seconds": lex_cpu,
            "rankings": {m: names_only(r, index) for m, r in rankings.items()}}


def summarize(rows):
    groups = {"overall": rows, "diagnosed_failures": [r for r in rows if r["task_id"] in FAILURES]}
    groups.update({repo: [r for r in rows if r["repo"] == repo] for repo in sorted({r["repo"] for r in rows})})
    result = {}
    for group, items in groups.items():
        result[group] = {"tasks": len(items), "unavailable": sum("metrics" not in r for r in items), "methods": {}}
        calls = [call for row in items for call in row.get("calls", [])]
        result[group]["tools"] = {}
        for tool in sorted({c["tool"] for c in calls}):
            selected = [c for c in calls if c["tool"] == tool]
            result[group]["tools"][tool] = {"calls": len(selected), **{
                "mean_" + key: sum(c[key] for c in selected) / len(selected)
                for key in ("chars", "cpu_seconds", "wall_seconds")}}
        for key in ("snapshot_index_cpu_seconds", "lexical_cpu_seconds"):
            times = [r[key] for r in items if key in r]
            result[group]["mean_" + key] = sum(times) / len(times) if times else None
        for method in ("T1", "T2", "L", "L+T1"):
            values = [r["metrics"][method] for r in items if "metrics" in r and r["metrics"][method] is not None]
            keys = sorted({k for v in values for k in v})
            result[group]["methods"][method] = {k: {"n": sum(v[k] is not None for v in values),
                "mean": sum(v[k] for v in values if v[k] is not None) / sum(v[k] is not None for v in values)
                if any(v[k] is not None for v in values) else None} for k in keys}
            result[group]["methods"][method]["unavailable_tasks"] = len(items) - len(values)
    return result


def run(config):
    from runtime import official_cells, install_official_environment, check_environment, clean_env
    from location_review import validate_metadata
    if (config.get("authorization") != AUTH or config.get("cpu_only_confirmed") is not True
            or config.get("internet_off_confirmed") is not True or Path("/dev/nvidia0").exists()
            or sys.platform != "linux"):
        raise ValueError("CPU authorization and Internet Off required")
    data = Path(config["data"])
    if data != Path("/kaggle/input/competitions/gemma-4-developer-agent"):
        raise ValueError("public competition input required")
    gold_path = HERE / "evidence/gold-locations.json"
    if digest(gold_path) != GOLD_SHA:
        raise ValueError("gold metadata pin mismatch")
    gold = json.loads(gold_path.read_bytes())
    validate_metadata(gold)
    if digest(data / "tasks.jsonl") != gold["official_tasks_sha256"]:
        raise ValueError("public inventory mismatch")
    if any(not (data / d).is_dir() for d in ("snapshots", "graphs", "embeddings")):
        raise ValueError("official retrieval inputs unavailable")
    output = Path(config["output"])
    if output.parent != Path("/kaggle/working") or output.exists():
        raise ValueError("fresh external output required")
    if not Path("/kaggle/input/datasets/metric/gemma-4-developer-agent-wheelhouse").is_dir():
        raise ValueError("official wheelhouse missing")
    official_cells()
    output.mkdir()
    install_official_environment(config, output)  # pinned cell 2 only, never cell 8
    check_environment()
    source_pins = check_graph_sources()
    rows = []
    started = time.monotonic()
    for task in gold["tasks"]:
        if time.monotonic() - started > 10800:
            break
        dest = output / (task["task_id"] + ".json")
        try:
            subprocess.run([sys.executable, "-B", str(Path(__file__).resolve()), "--worker", task["task_id"],
                            "--data", str(data), "--output", str(dest), "--config", str(config["config_path"])], env=clean_env(),
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=300, check=True)
            row = json.loads(dest.read_bytes())
            row["metrics"] = {m: metrics(r, task) if row["method_available"][m] else None for m, r in row["rankings"].items()}
        except (subprocess.SubprocessError, OSError, ValueError):
            row = {"task_id": task["task_id"], "repo": task["repo"], "state": "UNAVAILABLE"}
        rows.append(row)
        with (output / "study.jsonl").open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(row, sort_keys=True) + "\n")
    report = {"state": "COMPLETED" if len(rows) == 129 else "PARTIAL", "gold_sha256": GOLD_SHA,
              "graph_source_sha256": source_pins,
              "official_tasks_sha256": gold["official_tasks_sha256"], "summary": summarize(rows)}
    (output / "summary.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    pins = {p.name: digest(p) for p in output.iterdir() if p.is_file()}
    (output / "hashes.json").write_text(json.dumps(pins, indent=2), encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path)
    parser.add_argument("--worker")
    parser.add_argument("--data", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    logging.disable(logging.CRITICAL)
    try:
        if args.worker:
            approval = json.loads(args.config.read_bytes())
            if (approval.get("authorization") != AUTH or approval.get("cpu_only_confirmed") is not True
                    or approval.get("internet_off_confirmed") is not True or sys.platform != "linux"
                    or Path("/dev/nvidia0").exists()
                    or args.data != Path("/kaggle/input/competitions/gemma-4-developer-agent")
                    or args.output.parent != Path(approval["output"])):
                raise ValueError("worker approval mismatch")
            from swegemma.models import load_tasks
            check_graph_sources()
            task = next(t for t in load_tasks(args.data / "tasks.jsonl") if t.instance_id == args.worker)
            args.output.write_text(json.dumps(retrieve(args.data, task)), encoding="utf-8")
        else:
            config = json.loads(args.config.read_bytes())
            config["config_path"] = str(args.config.resolve())
            run(config)
    except Exception:
        raise SystemExit("LOCALIZATION_STUDY_BLOCKED; source text withheld") from None
