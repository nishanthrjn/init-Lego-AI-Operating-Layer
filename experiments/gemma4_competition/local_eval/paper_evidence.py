"""Offline, metadata-only evidence export. Maintainer execution required."""
import argparse
import json
from pathlib import Path

from analysis import load_controls, read_run, sha, summarize
from compare_runs import table


def project(meta, rows, ids):
    """Restrict a development run without converting missing results to failures."""
    selected = dict(meta)
    selected["task_ids"] = [tid for tid in meta["task_ids"] if tid in ids]
    selected["task_repos"] = {tid: repo for tid, repo in meta["task_repos"].items() if tid in ids}
    return selected, [row for row in rows if row["task_id"] in ids]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", action="append", required=True, metavar="CANDIDATE=FOLDER")
    parser.add_argument("--controls", required=True, type=Path)
    parser.add_argument("--controls-sha256", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[3]
    if args.output.resolve().is_relative_to(root):
        raise ValueError("derived run outputs must remain outside repository")
    supplied = {}
    for item in args.run:
        name, separator, folder = item.partition("=")
        if not separator or name in supplied:
            raise ValueError("unique CANDIDATE=FOLDER required")
        supplied[name] = Path(folder)
    if set(supplied) not in ({"p1", "p1b", "p1c", "p2", "p3", "p3g"}, {"p1", "p1b", "p1c", "p2", "p3", "p3g", "p3att2", "p4"}):
        raise ValueError("exact six historical or eight comparable runs required")
    loaded = {name: read_run(path) for name, path in supplied.items()}
    ids = set(loaded["p3"][0]["task_ids"])
    if len(ids) != 16:
        raise ValueError("P3 must contain the frozen 16-task development subset")
    runs, records = {}, {}
    controls = None
    for name, (meta, rows) in loaded.items():
        controls = load_controls(args.controls, args.controls_sha256, meta)
        if any(controls.get(tid, {}).get("class") != "VERIFIABLE" for tid in ids):
            raise ValueError("comparison task is not VERIFIABLE")
        if not ids <= set(meta["task_ids"]):
            raise ValueError("run lacks comparison tasks")
        runs[name] = project(meta, rows, ids)
        path = supplied[name]
        records[name] = {
            "sources": [{"file": str(path / part), "sha256": sha(path / part)}
                        for part in ("run.json", "tasks.jsonl", "completion.json", "official/task_results.jsonl")
                        if (path / part).is_file()],
            "summary": summarize(*runs[name], controls),
        }
    rendered = table(runs, controls)
    rendered += "\n\n## Tool argument rejections\n\n"
    rendered += "| Run | Rejected edit/write | Edit/write rate | Rejected all tools | All-tool rate | Nonempty patch share |\n|---|---:|---:|---:|---:|---:|\n"
    for name, record in records.items():
        summary = record["summary"]["descriptive_observations_not_control_qualified"]
        metric = summary["tool_argument_rejections"]
        rendered += (f"| {name} | {metric['edit_write_rejected']}/{metric['edit_write_attempted']} | "
                     f"{metric['rejection_rate']} | {metric['all_tool_rejected']}/{metric['all_tool_attempted']} | "
                     f"{metric['all_tool_rejection_rate']} | {summary['patch_production']['share']} |\n")
    rendered += "\nNull means unknown/incomplete or zero denominator, never zero rejections. Per-task tool counts, resend streaks, source-edit marker counts and trace hashes are in the JSON.\n"
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output / "dev-16v-comparison.md").write_text(rendered, encoding="utf-8")
    (args.output / ("eight-run-analysis.json" if len(records) == 8 else "six-run-analysis.json")).write_text(json.dumps({
        "controls_sha256": args.controls_sha256, "runs": records,
        "limitations": "Development evidence; P1 restricted, P1b merged once, P3 repeats separate; missing traces/patch telemetry stay unknown; no superiority claim."
    }, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
