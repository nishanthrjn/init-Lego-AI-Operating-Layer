"""1F behavioral contracts and lifecycle regressions; no network or GPU."""

from __future__ import annotations

import json
import signal
import subprocess
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from experiments.kaggle.free_gpu_model_runtime import notebook_support as notebook
from experiments.kaggle.free_gpu_model_runtime import runtime_probe as probe
from experiments.kaggle.free_gpu_model_runtime.tests.test_runtime_probe import (
    validate_schema,
)


@pytest.mark.parametrize(
    ("identity", "content", "accepted"),
    [
        ("ready", "READY", True),
        ("ready", " READY\n", False),
        ("ready", "ready", False),
        ("json", '{ "status" : "ready" }', True),
        ("json", '\n{\n"status": "ready"\n}\n', True),
        ("json", '{"status":"ready","status":"ready"}', False),
        ("json", '{"status":"READY"}', False),
        ("json", '{"status":true}', False),
        ("json", '{"status":"ready","x":0}', False),
        ("json", '[{"status":"ready"}]', False),
        ("json", '"ready"', False),
        ("json", '```json\n{"status":"ready"}\n```', False),
        ("json", 'Here: {"status":"ready"}', False),
        ("json", '{"status":"ready"} done', False),
        ("json", '{"status":', False),
        ("json", "null", False),
        ("add", "def add(a:int,b:int)->int: return (a+b)\n", True),
        ("add", "def add(a,b): return a+b", False),
        ("add", "def sub(a:int,b:int)->int: return a+b", False),
        ("add", "def add(a:int,b:int)->int: return a-b", False),
        ("add", "def add(a:int,b:int)->int: return a+b\nprint(1)", False),
    ],
)
def test_output_contract_and_closed_diagnostics(
    identity: str, content: str, accepted: bool
) -> None:
    matched, facts = probe.output_diagnostics(identity, content)
    assert matched is accepted
    assert probe.output_matches(identity, content) is accepted
    schema = json.loads((probe.SOURCE / "result.schema.json").read_text())
    diagnostic_schema = schema["properties"]["assertions"]["items"]["properties"][
        "diagnostics"
    ]
    validate_schema(facts, diagnostic_schema, schema)
    assert "content" not in facts
    assert facts["content_length"] == len(content)


def test_diagnostics_distinguish_serialization_from_semantics() -> None:
    matched, facts = probe.output_diagnostics("json", '{ "status": "ready" }')
    assert matched and facts["semantic_match"] and not facts["exact_text_match"]
    matched, facts = probe.output_diagnostics("json", '{"status":"PRIVATE-CANARY"}')
    assert not matched and facts["parses_as_json"] and facts["status_is_string"]
    assert not facts["status_exact_match"] and "PRIVATE" not in json.dumps(facts)
    with pytest.raises(probe.Stop):
        probe.output_diagnostics("json", "x" * 4097)


def test_only_measurable_timings_remain() -> None:
    assert set(probe.fresh_result()["timings"]) == {
        "download_seconds",
        "startup_to_port_ready_seconds",
    }


@pytest.mark.parametrize("failure", ["timeout", "interrupt", "success"])
def test_notebook_terminates_launcher_on_cancellation(
    failure: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    events: list[str] = []

    class Process:
        returncode: int | None = None

        def communicate(self, timeout: int) -> tuple[str, str]:
            events.append("communicate")
            if len(events) == 1 and failure == "timeout":
                raise subprocess.TimeoutExpired("synthetic", timeout)
            if len(events) == 1 and failure == "interrupt":
                raise KeyboardInterrupt
            self.returncode = 0
            return "", ""

        def poll(self) -> int | None:
            return self.returncode

        def terminate(self) -> None:
            events.append("terminate")

        def kill(self) -> None:
            pytest.fail("graceful cleanup should finish")

    monkeypatch.setattr(subprocess, "Popen", lambda *a, **k: Process())
    if failure == "success":
        notebook.run_phase(Path("source"), "run", 1)
        assert events == ["communicate"]
    else:
        expected = RuntimeError if failure == "timeout" else KeyboardInterrupt
        with pytest.raises(expected):
            notebook.run_phase(Path("source"), "run", 1)
        assert events == ["communicate", "terminate", "communicate"]


@pytest.mark.parametrize("exited", [False, True])
def test_owned_group_descendants_killed_and_leader_reaped(
    exited: bool, monkeypatch: pytest.MonkeyPatch
) -> None:
    events: list[Any] = []

    def killpg(pid: int, sig: int) -> None:
        events.append((pid, sig))
        if exited and sig == 15:
            raise ProcessLookupError

    # Windows local tests model the Linux target API without invoking it.
    monkeypatch.setattr(probe, "os", SimpleNamespace(killpg=killpg))
    monkeypatch.setattr(probe, "signal", SimpleNamespace(SIGTERM=15, SIGKILL=9))

    class Process:
        pid = 123

        def wait(self, timeout: int) -> int:
            events.append("reap")
            return 0

    probe.stop_process(Process())  # type: ignore[arg-type]
    assert events == [(123, 15), "reap", (123, 9), "reap"]


def test_sigterm_unwinds_owned_children(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[Any] = []
    monkeypatch.setattr(signal, "signal", lambda *args: calls.append(args))
    with pytest.raises(KeyboardInterrupt):
        probe.interrupt_runtime(15, None)
    assert calls == [(signal.SIGTERM, signal.SIG_IGN)]


def test_optional_memory_failure_marks_incomplete(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def missing() -> str:
        raise probe.Stop("RESULT_INCONCLUSIVE", "DRIVER_OBSERVATION_UNAVAILABLE")

    monkeypatch.setattr(probe, "trusted_nvidia_smi", missing)
    result = probe.fresh_result()
    probe.sample_memory(result)
    assert result["gpu_memory"] == {
        "sampled_peak_used_mib": [],
        "sampling_complete": False,
    }
