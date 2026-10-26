"""Control-filtered per-task Markdown comparison; no model or evaluator calls."""
import argparse
from pathlib import Path
import re
from analysis import read_run, load_controls, sha, same_config_agreement


def agreement_section(runs, controls, pair):
    a, separator, b = pair.partition("=")
    if not separator or a not in runs or b not in runs or a == b:
        raise ValueError("same-config requires two distinct existing labels: A=B")
    report = same_config_agreement(*runs[a], *runs[b], controls)
    lines = [f"Same-config {a} vs {b}: {report['agreement_count']}/{report['tasks']} agree; "
             f"observed noise floor = {report['flip_count']} task flips.",
             "", "| Task | First resolved | Second resolved | Flipped |", "|---|---|---|---|"]
    lines.extend(f"| {row['task_id']} | {row['a_resolved']} | {row['b_resolved']} | {row['flipped']} |"
                 for row in report["per_task"])
    return "\n".join(lines) + "\n\n" + report["caveat"] + "\n"


def table(runs, controls):
    if not runs:
        raise ValueError("at least one run required")
    first = next(iter(runs.values()))[0]
    identities = {}
    for label, (meta, rows) in runs.items():
        if not re.fullmatch(r"[A-Za-z0-9_-]+", label):
            raise ValueError("unsafe comparison label")
        for key in ("official_tasks_sha256", "runtime_pins", "source_pins_sha256"):
            if meta[key] != first[key]:
                raise ValueError("comparison contract mismatch: " + key)
        for tid, repo in meta["task_repos"].items():
            if tid in identities and identities[tid] != repo:
                raise ValueError("task repository mismatch")
            identities[tid] = repo
        ids = [r["task_id"] for r in rows]
        if len(ids) != len(set(ids)) or not set(ids) <= set(meta["task_ids"]):
            raise ValueError("duplicate/unplanned results")
    labels = list(runs)
    lines = ["| Task | Control | " + " | ".join(labels) + " |",
             "|---|---|" + "---|" * len(labels)]
    def escape(value):
        return str(value).replace("|", "\\|").replace("\n", " ").replace("\r", " ")
    for tid in sorted(identities):
        cls = controls.get(tid, {}).get("class", "UNASSESSED")
        cells = []
        for label in labels:
            meta, rows = runs[label]
            row = next((r for r in rows if r["task_id"] == tid), None)
            if tid not in meta["task_ids"]:
                value = "NOT_PLANNED"
            elif cls != "VERIFIABLE":
                value = "EXCLUDED"
            elif row is None:
                value = "MISSING"
            elif row.get("completed_result") is False or row["resolved"] is None or row["harness_errors"]:
                value = "UNKNOWN"
            else:
                value = "RESOLVED" if row["resolved"] else "UNRESOLVED"
            if row and row.get("attempt_id"):
                value += " (attempt " + escape(row["attempt_id"]) + ")"
            cells.append(value)
        lines.append("| " + escape(tid) + " | " + cls + " | " + " | ".join(cells) + " |")
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", action="append", required=True, metavar="LABEL=FOLDER")
    parser.add_argument("--controls", type=Path, required=True)
    parser.add_argument("--controls-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--same-config", action="append", default=[], metavar="A=B")
    args = parser.parse_args()
    output = args.output.resolve()
    if output.is_relative_to(Path(__file__).resolve().parents[3]) or any((p / ".git").exists() for p in output.parents):
        raise ValueError("comparison outputs must remain outside repositories")
    runs, provenance = {}, []
    controls = None
    for item in args.run:
        label, separator, folder = item.partition("=")
        if not separator or label in runs:
            raise ValueError("unique LABEL=FOLDER arguments required")
        path = Path(folder)
        meta, rows = read_run(path)
        controls = load_controls(args.controls, args.controls_sha256, meta)
        runs[label] = (meta, rows)
        provenance.append(f"{label}: run SHA256 {sha(path / 'run.json')}; tasks SHA256 {sha(path / 'tasks.jsonl')}; state {meta['completion_state']}")
    rendered = table(runs, controls)
    for pair in args.same_config:
        rendered += "\n" + agreement_section(runs, controls, pair)
    header = "Controls SHA256: " + args.controls_sha256 + "\n\n" + "\n\n".join(provenance)
    with output.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(header + "\n\n" + rendered + "\nTask union shown; NOT_PLANNED is not failure. UNKNOWN/MISSING are not unresolved verdicts. No significance or improvement claim.\n")


if __name__ == "__main__":
    main()
