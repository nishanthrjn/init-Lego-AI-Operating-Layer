"""MODEL-STRUCTURED-OUTPUT-1-LIVE-PROBE: exact custody of the one admitted run.

The run directory is pinned by its Git tree id; the probe source by the digest
recorded at execution. Any other entry under runs/ (committed, untracked or
ignored) is refused until separately reviewed and pinned here. Checks verify
recorded historical facts; they never re-run the probe.
"""

import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROBE_DIR = "examples/model-structured-output-probe"
RUN = "probe-d54d022d-9928-4f5d-a9b8-8745929e97f5"
TREE = "8027518e16ff282ce5950514f3c4173ee5173e68"  # committed in d5c5b39
PROBE_SOURCE_SHA256 = "3fdaf87179f512b9ca0ddc1bf9e8f209cf4954f1969f2f2c360eb74898cff532"
SCHEMA_DIGEST = "dd522666abf2ef6cb884ab37fb25da4e56f123febc5ee1f7064cbb570aeab4e2"
MODEL_DIGEST = "sha256:9ec8897f747e246e970bc5cfdda85d22f1123dc2e3d34978a010a75968716849"


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout.strip()


def _load(name: str) -> dict[str, object]:
    data: dict[str, object] = json.loads(
        (ROOT / PROBE_DIR / "runs" / RUN / name).read_text(encoding="utf-8")
    )
    return data


def test_only_the_admitted_run_exists() -> None:
    entries = sorted(p.name for p in (ROOT / PROBE_DIR / "runs").iterdir())
    assert entries == [RUN]


def test_run_directory_matches_pinned_tree() -> None:
    assert _git("rev-parse", f"HEAD:{PROBE_DIR}/runs/{RUN}") == TREE
    assert _git("status", "--porcelain", "--ignored", "--", f"{PROBE_DIR}/runs") == ""


def test_probe_source_matches_execution_digest() -> None:
    raw = (ROOT / PROBE_DIR / "probe.py").read_bytes().replace(b"\r\n", b"\n")
    assert hashlib.sha256(raw).hexdigest() == PROBE_SOURCE_SHA256
    assert _git("ls-files", "--", f"{PROBE_DIR}/probe.py") == f"{PROBE_DIR}/probe.py"


def test_recorded_execution_facts() -> None:
    run, report = _load("run.json"), _load("report.json")
    repository = run["repository"]
    runtime = run["runtime"]
    identity = run["request_identity"]
    assert isinstance(repository, dict) and isinstance(runtime, dict)
    assert isinstance(identity, dict)
    assert run["probe_id"] == report["probe_id"] == RUN.removeprefix("probe-")
    assert repository["git_head"] == "d9645d0f05d8beff61ed4fd7febe2f142fcc1b6d"
    assert repository["probe_source_sha256"] == PROBE_SOURCE_SHA256
    assert repository["probe_source_tracked"] is False  # historical fact
    assert runtime["endpoint_class"] == "loopback"
    assert runtime["ollama_version_observed"] == "0.40.0"
    assert runtime["model_tag_observed"] == "qwen2.5-coder:14b"
    assert runtime["model_digest_observed"] == MODEL_DIGEST
    assert identity["schema_digest"] == SCHEMA_DIGEST
    assert run["retry"] is False and run["fallback"] is False
    result = report["result"]
    assert isinstance(result, dict)
    assert result["semantic_calls"] == 1
    assert result["effect"] == "COMPLETED"
    assert result["json_parse"] == "SUCCESS"
    assert all(result["checks"].values())
    assert report["verdict"] == "PASSED" and report["failures"] == []


def test_no_ignore_rule_hides_probe_evidence() -> None:
    for path in (
        f"{PROBE_DIR}/runs/{RUN}/run.json",
        f"{PROBE_DIR}/runs/probe-future/run.json",
        f"{PROBE_DIR}/probe.py",
    ):
        checked = subprocess.run(
            ["git", "check-ignore", "--no-index", "-q", path], cwd=ROOT, check=False
        )
        assert checked.returncode == 1, path
