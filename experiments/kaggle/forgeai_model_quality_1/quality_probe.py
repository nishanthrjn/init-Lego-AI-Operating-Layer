"""Explicitly authorized, manual-transfer runner; no transport to Kaggle."""

from __future__ import annotations

import argparse
import json
import os
import queue
import signal
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import Any

from .contracts import (
    CALL_LIMIT,
    CALL_SECONDS,
    GENERATION_SETTINGS,
    MODEL,
    OUTPUT_BYTES,
    REVISION,
    RUNTIME_FAILURE_CODES,
    THRESHOLDS,
    VERSION,
    Rejected,
)
from .evaluator import artifacts, classification, score_coding, score_review
from .package import SOURCE, identity
from .scenarios import CASES, digest, prompt


def environment(home: Path) -> dict[str, str]:
    values = {
        "PATH": "/usr/local/nvidia/bin:/usr/local/cuda/bin:/usr/local/bin:/usr/bin:/bin",
        "HOME": str(home),
        "TMPDIR": "/tmp",
        "LANG": "C.UTF-8",
        "HF_HUB_OFFLINE": "1",
        "TRANSFORMERS_OFFLINE": "1",
        "HF_HUB_DISABLE_TELEMETRY": "1",
        "VLLM_NO_USAGE_STATS": "1",
        "DO_NOT_TRACK": "1",
        "VLLM_USE_V1": "0",
        "VLLM_ATTENTION_BACKEND": "XFORMERS",
        "VLLM_HOST_IP": "127.0.0.1",
        "GLOO_SOCKET_IFNAME": "lo",
        "NCCL_SOCKET_IFNAME": "lo",
        "NCCL_IB_DISABLE": "1",
        "VLLM_WORKER_MULTIPROC_METHOD": "spawn",
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    libraries = os.environ.get("LD_LIBRARY_PATH")
    if libraries is not None:
        if len(libraries) > 512 or len(libraries.split(":")) > 8:
            raise Rejected("RUNTIME_ENVIRONMENT_INVALID")
        if any(
            part not in {"/usr/local/nvidia/lib64", "/usr/local/cuda/lib64"}
            for part in libraries.split(":")
        ):
            raise Rejected("RUNTIME_ENVIRONMENT_INVALID")
        values["LD_LIBRARY_PATH"] = libraries
    return values


class Worker:
    def __init__(self) -> None:
        self.process: subprocess.Popen[bytes] | None = None
        self.calls = 0
        self.runtime: dict[str, Any] = {}
        self.reader: threading.Thread | None = None
        self.home: tempfile.TemporaryDirectory[str] | None = None

    def start(self) -> None:
        if sys.platform != "linux":
            raise Rejected("RUNTIME_IDENTITY_MISMATCH")
        self.home = tempfile.TemporaryDirectory(prefix="quality-worker-home-")
        self.process = subprocess.Popen(
            [sys.executable, "-m", "forgeai_model_quality_1.runtime_worker"],
            cwd=SOURCE.parent,
            env=environment(Path(self.home.name)),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        ready = self.read(900)
        if set(ready) != {"ready"} or not isinstance(ready["ready"], dict):
            raise Rejected("MODEL_LOAD_FAILED")
        self.runtime = ready["ready"]

    def read(self, seconds: int, payload: bytes | None = None) -> dict[str, Any]:
        process = self.process
        if process is None or process.stdout is None:
            raise Rejected("RUNTIME_FAILURE")
        channel: queue.Queue[bytes] = queue.Queue(maxsize=1)

        def receive() -> None:
            assert process.stdout is not None
            try:
                if payload is not None:
                    assert process.stdin is not None
                    process.stdin.write(payload)
                    process.stdin.flush()
                channel.put(process.stdout.readline(OUTPUT_BYTES * 8 + 1))
            except OSError:
                channel.put(b"")

        thread = threading.Thread(target=receive, daemon=True)
        self.reader = thread
        thread.start()
        try:
            line = channel.get(timeout=seconds)
        except queue.Empty:
            raise Rejected("RUNTIME_TIMEOUT") from None
        if not line.endswith(b"\n") or len(line) > OUTPUT_BYTES * 8:
            raise Rejected("RUNTIME_PROTOCOL_INVALID")
        try:
            value = json.loads(line)
        except (ValueError, RecursionError):
            raise Rejected("RUNTIME_PROTOCOL_INVALID") from None
        if not isinstance(value, dict):
            raise Rejected("RUNTIME_FAILURE")
        if "error" in value:
            reason = value["error"]
            if (
                set(value) == {"error"}
                and isinstance(reason, str)
                and reason in RUNTIME_FAILURE_CODES
            ):
                raise Rejected(reason)
            raise Rejected("RUNTIME_PROTOCOL_INVALID")
        return value

    def generate(self, content: str) -> str:
        process = self.process
        if self.calls >= CALL_LIMIT or process is None or process.stdin is None:
            raise Rejected("CALL_LIMIT")
        self.calls += 1  # Conservative: consumed before sending, including failures.
        payload = (json.dumps({"prompt": content}) + "\n").encode()
        value = self.read(CALL_SECONDS, payload)
        if set(value) != {"text"} or not isinstance(value["text"], str):
            raise Rejected("RUNTIME_PROTOCOL_INVALID")
        if len(value["text"].encode()) > OUTPUT_BYTES:
            raise Rejected("OUTPUT_LIMIT")
        return str(value["text"])

    def close(self) -> None:
        if self.process is not None:
            # Include tensor-parallel children even if the leader has exited.
            try:
                os.killpg(self.process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            self.process.wait(timeout=15)
            if self.reader is not None:
                self.reader.join(timeout=5)
                if self.reader.is_alive():
                    raise Rejected("CLEANUP_FAILED")
            for stream in (self.process.stdin, self.process.stdout):
                if stream is not None:
                    stream.close()
        if self.home is not None:
            self.home.cleanup()


def run(destination: Path) -> dict[str, Any]:
    package_digest = identity()
    if destination.exists():
        raise Rejected("EXISTING_RESULT")
    destination.mkdir(parents=True)  # Single-use run even after an interruption.
    worker = Worker()
    plan = [
        {
            "scenario": case.name,
            "role": "reviewer" if case.review_kind else "coding",
            "initial_prompt_digest": digest(prompt(case)),
            "max_calls": 2 if case.rework else 1,
        }
        for case in CASES
    ]
    rows: list[dict[str, Any]] = []
    failure: str | None = None
    started = time.monotonic()
    try:
        worker.start()
        for case in CASES:
            content = prompt(case)
            before = time.monotonic()
            raw = worker.generate(content)
            attempt = {
                "prompt_digest": digest(content),
                "output_digest": digest(raw),
                "seconds": round(time.monotonic() - before, 3),
            }
            if case.review_kind:
                row = score_review(case, raw)
            else:
                row, files = score_coding(case, raw)
            row["attempts"] = [attempt]
            rows.append(row)
            if "TOOL_TIMEOUT" in row["failures"]:
                raise Rejected("TOOL_TIMEOUT")
            if "TOOL_FAILURE" in row["failures"]:
                raise Rejected("TOOL_FAILURE")
            if case.rework:
                findings = set(row["failures"])
                eligible = findings and findings <= {
                    "ORACLE_FAILED",
                    "RUFF_FINDING",
                    "MYPY_FINDING",
                }
                if not eligible:
                    row["failures"].append("REWORK_NOT_EXERCISED")
                    continue
                feedback = (
                    "Completed deterministic checks reported: "
                    + ", ".join(sorted(findings))
                    + ". Ruff checks E4,E7,E9,F,B; mypy checks strict typing. "
                    + "Required oracle cases: "
                    + json.dumps(case.oracle)
                )
                content = prompt(case, files, feedback)
                before = time.monotonic()
                raw = worker.generate(content)
                second, _ = score_coding(case, raw, rework=True)
                second["attempts"] = [
                    *row["attempts"],
                    {
                        "prompt_digest": digest(content),
                        "output_digest": digest(raw),
                        "seconds": round(time.monotonic() - before, 3),
                        "first_dimensions": row["dimensions"],
                        "first_failures": row["failures"],
                    },
                ]
                second["dimensions"]["REWORK_QUALITY"] = (
                    "PASS" if not second["failures"] else "FAIL"
                )
                rows[-1] = second
    except Rejected as exc:
        failure = str(exc)
    except (OSError, ValueError, subprocess.SubprocessError, KeyboardInterrupt):
        failure = "RUNTIME_INTERRUPTED_OR_FAILED"
    finally:
        try:
            worker.close()
        except (OSError, Rejected, subprocess.SubprocessError):
            failure = "CLEANUP_FAILED"
    result = {
        "evaluation_version": VERSION,
        "package_digest": package_digest,
        "model_id": MODEL,
        "model_revision": REVISION,
        "runtime": worker.runtime,
        "generation_settings": GENERATION_SETTINGS,
        "plan": plan,
        "scenarios": rows,
        "total_model_calls": worker.calls,
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "failure": failure,
        "thresholds": THRESHOLDS,
        "classification": classification(rows, failure),
    }
    artifacts(result, destination)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--authorized-synthetic-run", action="store_true")
    args = parser.parse_args()
    if not args.authorized_synthetic_run:
        print(f"{VERSION}: plan only; 10 scenarios; <=11 calls; live not authorized")
        return 0
    try:
        result = run(Path("/kaggle/working/forgeai-quality-result"))
    except (OSError, ValueError):
        print("RESULT_INCONCLUSIVE: PRECONDITION_FAILED")
        return 1
    print(result["classification"])
    return 0 if result["classification"] == "MODEL_QUALITY_PROMISING" else 1


if __name__ == "__main__":
    raise SystemExit(main())
