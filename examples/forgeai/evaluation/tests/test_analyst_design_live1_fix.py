"""HARNESS-RUNTIME-FIX-1: fenced composition, durable accounting and spawn."""

import asyncio
import hashlib
import json
import multiprocessing
import os
import re
import socket
import subprocess
from pathlib import Path
from typing import Any
from urllib.request import OpenerDirector

import pytest
from analyst_design_live1 import harness, runtime
from analyst_design_live1.diagnostics import (
    SAFE_CLASSES,
    ChildStage,
    FailureCategory,
    IPCStatus,
    classify,
    safe_class,
)
from analyst_design_live1.lifecycle import AttemptState, partition, validate_partition
from analyst_design_live1.storage import Store
from legoai_engineering.analyst.sufficiency_agent import EvidenceSufficiencyAgent
from test_analyst_design_live1 import manifest, output

from legoai.runtime.local import open_local_host


class PreDispatchStop(Exception):
    pass


async def fenced_composition(
    m: Any, expected: Any, timeout: float, *, missing: bool, mark: Any
) -> Any:
    # Executed inside an already initialized loop: Windows' stdlib self-pipe
    # setup is not mistaken for provider traffic. No bypass exists in production.
    with pytest.MonkeyPatch.context() as patch:
        original = open_local_host
        patch.delenv("FORGEAI_LIVE1_OFFLINE", raising=False)

        def forbidden(*args: Any, **kwargs: Any) -> Any:
            pytest.fail("network boundary entered")

        for name in ("getaddrinfo", "gethostbyname", "gethostbyname_ex"):
            patch.setattr(socket, name, forbidden)
        for name in ("connect", "connect_ex", "send", "sendall", "sendto"):
            patch.setattr(socket.socket, name, forbidden)
        patch.setattr(OpenerDirector, "open", forbidden)

        def host(config: Any, selection: Any, **kwargs: Any) -> Any:
            assert selection == {"revision": "live1", "binding": "ollama"}
            if missing:
                selection = {"revision": selection["revision"]}
            return original(config, selection, **kwargs)

        async def agent(*args: Any, **kwargs: Any) -> Any:
            assert not missing, "Agent must not enter on composition failure"
            raise PreDispatchStop("SENSITIVE_SENTINEL_MUST_NOT_BE_PERSISTED")

        patch.setattr(runtime, "open_local_host", host)
        patch.setattr(EvidenceSufficiencyAgent, "assess", agent)
        return await runtime.governed(m, expected, timeout, mark=mark)


def composition_child(
    pipe: Any, m: Any, expected: Any, timeout: float, output: str | None
) -> None:
    # Test-only spawn target reuses production child/envelope handling, replacing
    # just its coroutine with the fenced actual composition (not Replay).
    original = runtime.governed

    async def run(
        m: Any, expected: Any, timeout: float, output: Any, *, mark: Any
    ) -> Any:
        runtime.governed = original
        return await fenced_composition(
            m, expected, timeout, missing=output == "missing", mark=mark
        )

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(runtime, "governed", run)
        runtime.child(pipe, m, expected, timeout, output)


def broken_child(
    pipe: Any, m: Any, expected: Any, timeout: float, output: str | None
) -> None:
    if output == "abnormal":
        os._exit(7)
    if output == "invalid":
        pipe.send(("SENSITIVE_SENTINEL_MUST_NOT_BE_PERSISTED",))
    elif output == "invalid_result":
        pipe.send(("result", object(), None))
    elif output == "unknown_class":
        pipe.send(("failure", FailureCategory.UNKNOWN_CHILD_FAILURE, "SECRET_CLASS"))
    pipe.close()


def context_with(patch: pytest.MonkeyPatch, target: Any) -> None:
    context = multiprocessing.get_context("spawn")

    class Context:
        Pipe = staticmethod(context.Pipe)

        @staticmethod
        def Process(*, target: Any, args: Any) -> Any:
            return context.Process(target=selected, args=args)

    selected = target
    patch.setattr(multiprocessing, "get_context", lambda method: Context())


@pytest.mark.parametrize("missing", [False, True])
def test_actual_composition_network_fenced(missing: bool) -> None:
    f, m = manifest()
    stages: list[ChildStage] = []
    expected = runtime.projection(m, f, "initial", "initial")
    from legoai.runtime.api import HostError

    with pytest.raises(HostError if missing else PreDispatchStop) as caught:
        asyncio.run(
            fenced_composition(m, expected, 10, missing=missing, mark=stages.append)
        )
    if missing:
        assert safe_class(caught.value) == "HostError"
        assert stages == [ChildStage.HOST_COMPOSITION_STARTED]
        assert classify(stages[-1]) == FailureCategory.COMPOSITION_FAILURE
    else:
        assert stages == [
            ChildStage.HOST_COMPOSITION_STARTED,
            ChildStage.HOST_COMPOSITION_COMPLETED,
            ChildStage.AGENT_CALL_STARTED,
        ]


@pytest.mark.parametrize("missing", [True, False])
def test_spawn_composition_failure_custody(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, missing: bool
) -> None:
    context_with(monkeypatch, composition_child)
    observed: list[dict[str, Any]] = []

    def call(m: Any, expected: Any, timeout: float) -> Any:
        return runtime.supervised(
            m,
            expected,
            10,
            output="missing" if missing else None,
            observe=observed.append,
        )

    report = asyncio.run(
        harness.execute("SMOKE", Store(tmp_path / "run"), {}, "offline", call=call)
    )
    life = report["execution_lifecycle"]
    assert life["attempted"] == 1 and life["completed"] == 0
    assert life["attempted_no_result"] == ["d01/initial/initial"]
    assert len(life["never_attempted"]) == 5
    assert "d01/initial" not in report["not_run"]
    diagnostic = report["timings"][0]["child_diagnostics"]
    assert diagnostic == observed[-1]
    assert diagnostic["child_failure_category"] == (
        "COMPOSITION_FAILURE" if missing else "PRE_DISPATCH_AGENT_FAILURE"
    )
    assert diagnostic["child_stage"] == (
        "HOST_COMPOSITION_STARTED" if missing else "AGENT_CALL_STARTED"
    )
    assert diagnostic["exception_class"] == (
        "HostError" if missing else "OtherException"
    )
    assert diagnostic["ipc_status"] == "ENVELOPE_RECEIVED"
    assert diagnostic["child_exit_code"] == 0
    assert (
        diagnostic["process_exit_observed"] and diagnostic["cleanup_action"] == "NONE"
    )
    assert diagnostic["model_dispatch"] == diagnostic["http_request"] == "NOT_OBSERVED"
    assert diagnostic["provider_acceptance"] == "UNKNOWN"
    assert report["in_flight_disposition"] == "SERVER_EFFECT_UNKNOWN"
    assert "SENSITIVE_SENTINEL" not in json.dumps(report)
    assert (
        json.loads((tmp_path / "run/call-001-finished.json").read_text())[
            "child_diagnostics"
        ]
        == diagnostic
    )


@pytest.mark.parametrize(
    "mode,ipc,category",
    [
        ("eof", "EOF_BEFORE_ENVELOPE", "CHILD_PROTOCOL_FAILURE"),
        ("abnormal", "EOF_BEFORE_ENVELOPE", "CHILD_ABNORMAL_EXIT"),
        ("invalid", "INVALID_ENVELOPE", "CHILD_PROTOCOL_FAILURE"),
        ("invalid_result", "ENVELOPE_RECEIVED", "INVALID_RESULT"),
        ("unknown_class", "INVALID_ENVELOPE", "CHILD_PROTOCOL_FAILURE"),
    ],
)
def test_spawn_protocol_custody(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mode: str, ipc: str, category: str
) -> None:
    context_with(monkeypatch, broken_child)

    def call(m: Any, expected: Any, timeout: float) -> Any:
        return runtime.supervised(m, expected, 10, output=mode)

    report = asyncio.run(
        harness.execute("SMOKE", Store(tmp_path / mode), {}, "offline", call=call)
    )
    diagnostic = report["timings"][0]["child_diagnostics"]
    assert diagnostic["ipc_status"] == ipc
    assert diagnostic["child_failure_category"] == category
    assert report["execution_lifecycle"]["attempted_no_result"] == [
        "d01/initial/initial"
    ]
    assert diagnostic["child_exit_code"] == (7 if mode == "abnormal" else 0)
    assert "SENSITIVE_SENTINEL" not in json.dumps(report)
    assert "SECRET_CLASS" not in json.dumps(report)


def test_spawn_replay_success_and_durable_diagnostics(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = runtime.supervised
    f, _ = manifest()

    def replay(m: Any, expected: Any, timeout: float, *, observe: Any) -> Any:
        return original(
            m, expected, 10, output=output(m, f, "initial", "initial"), observe=observe
        )

    monkeypatch.setattr(harness, "supervised", replay)
    # Explicit callable matches harness supervised identity: same custody path.
    report = asyncio.run(
        harness.execute(
            "SMOKE",
            Store(tmp_path / "success"),
            {},
            "offline",
            call=replay,
            before_call=lambda: None,
        )
    )
    assert report["execution_lifecycle"]["completed_result"][0] == "d01/initial/initial"
    files = sorted((tmp_path / "success").glob("call-001-diagnostic-*.json"))
    assert len(files) == len(ChildStage) + 1
    records = [json.loads(p.read_text()) for p in files]
    assert [r["child_stage"] for r in records[:-1]] == list(ChildStage)
    assert records[-1]["ipc_status"] == "ENVELOPE_RECEIVED"
    assert records[-1]["child_exit_code"] == 0
    assert records[-1]["cleanup_action"] == "NONE"
    assert records[-1]["provider_acceptance"] == "UNKNOWN"


def test_timeout_lifecycle(tmp_path: Path) -> None:
    f, _ = manifest()

    def call(m: Any, expected: Any, timeout: float) -> Any:
        return runtime.supervised(
            m, expected, 0.0001, output=output(m, f, "initial", "initial")
        )

    report = asyncio.run(
        harness.execute("SMOKE", Store(tmp_path / "timeout"), {}, "offline", call=call)
    )
    diagnostic = report["timings"][0]["child_diagnostics"]
    assert diagnostic["child_failure_category"] == "TIMEOUT"
    assert diagnostic["cleanup_action"] in {"TERMINATE", "KILL"}
    assert diagnostic["process_exit_observed"]
    assert diagnostic["provider_acceptance"] == "UNKNOWN"
    assert report["execution_lifecycle"]["attempted_no_result"] == [
        "d01/initial/initial"
    ]
    assert report["in_flight_disposition"] == "SERVER_EFFECT_UNKNOWN"


def test_never_attempted_partition(tmp_path: Path) -> None:
    store = Store(tmp_path / "empty")
    planned = [{"case": "d01", "variant": "initial", "phase": "initial"}]
    value = partition(store.path, planned)
    assert value["attempted"] == value["completed"] == 0
    assert value["never_attempted"] == ["d01/initial/initial"]
    assert set(AttemptState) == {
        "NEVER_ATTEMPTED",
        "ATTEMPTED_NO_RESULT",
        "COMPLETED_RESULT",
    }
    store.write("call-001-started.json", planned[0])
    value = partition(store.path, planned)
    assert value["slots"][0]["finish_recorded"] is False
    assert value["attempted_no_result"] == ["d01/initial/initial"]
    for field in ("planned", "attempted", "completed"):
        bad = {**value, field: 99}
        with pytest.raises(ValueError, match="invariant"):
            validate_partition(bad)


def test_closed_diagnostics() -> None:
    assert len(ChildStage) == 8 and len(FailureCategory) == 10
    assert len(IPCStatus) == 5
    assert safe_class(ValueError("SECRET")) == "ValueError"
    assert safe_class(PreDispatchStop("SECRET")) == "OtherException"
    assert "HostError" in SAFE_CLASSES and "ModelCompositionError" in SAFE_CLASSES
    assert classify(ChildStage.GOVERNED_RUNTIME_ENTERED) == "UNKNOWN_CHILD_FAILURE"
    assert classify(None) == "UNKNOWN_CHILD_FAILURE"


def test_historical_artifacts_unchanged() -> None:
    from analyst_design_live1.identity import ROOT

    text = (
        ROOT / "planning/FORGEAI-ANALYST-DESIGN-LIVE-1-CHILD-FAILURE-DIAGNOSTIC.md"
    ).read_text(encoding="utf-8")
    inventory = re.findall(
        r"\| ((?:preflight|smoke)-[^ |]+) \| ([^ |]+) \| `([a-f0-9]{64})` \|", text
    )
    original = subprocess.check_output(
        [
            "git",
            "show",
            "3bfdd9235fb915b07d3a759f9b731dee5670e33f:planning/FORGEAI-ANALYST-DESIGN-LIVE-1-CHILD-FAILURE-DIAGNOSTIC.md",
        ],
        cwd=ROOT,
    ).decode("utf-8")
    assert inventory == re.findall(
        r"\| ((?:preflight|smoke)-[^ |]+) \| ([^ |]+) \| `([a-f0-9]{64})` \|", original
    )
    assert len(inventory) == 8
    for directory, name, digest in inventory:
        path = ROOT / "examples/forgeai" / ("live1-" + directory) / name
        assert hashlib.sha256(path.read_bytes()).hexdigest() == digest
    report = json.loads(
        (ROOT / "examples/forgeai/live1-smoke-d59e9c3f030b/report.json").read_text()
    )
    assert report["in_flight_disposition"] == "SERVER_EFFECT_UNKNOWN"
    assert report["smoke_status"] == "SMOKE_RUNTIME_FAILURE"
    assert report["sufficiency_profile_outcome"] == "SUFFICIENCY_PROFILE_RUNTIME_FAILED"


def test_process_launch_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    from multiprocessing.process import BaseProcess

    def fail(self: Any) -> Any:
        raise OSError("SENSITIVE_SENTINEL")

    monkeypatch.setattr(BaseProcess, "start", fail)
    f, m = manifest()
    observed: list[dict[str, Any]] = []
    with pytest.raises(runtime.CallStopped) as caught:
        runtime.supervised(m, {}, 1, output="offline", observe=observed.append)
    d = caught.value.diagnostics.record()
    assert d["child_failure_category"] == "PROCESS_LAUNCH_FAILURE"
    assert d["child_exit_code"] is None and not d["process_exit_observed"]
    assert d["ipc_status"] == "NO_ENVELOPE" and d["cleanup_action"] == "NONE"
    assert "SENSITIVE_SENTINEL" not in json.dumps(d)
    assert observed == [d]


def test_semantic_failure_remains_result() -> None:
    from legoai_engineering.analyst.sufficiency import SufficiencyFailure

    f, m = manifest()
    observed: list[dict[str, Any]] = []
    result, digest = runtime.supervised(
        m,
        runtime.projection(m, f, "initial", "initial"),
        10,
        output="not json",
        observe=observed.append,
    )
    assert result.failure == SufficiencyFailure.INVALID_OUTPUT
    assert observed[-1]["child_failure_category"] is None
    assert observed[-1]["child_stage"] == "RESULT_COMPLETED"
    assert observed[-1]["ipc_status"] == "ENVELOPE_RECEIVED"


def test_orphan_finish_rejected(tmp_path: Path) -> None:
    store = Store(tmp_path / "orphan")
    store.write(
        "call-001-finished.json",
        {"case": "d01", "variant": "initial", "phase": "initial"},
    )
    with pytest.raises(ValueError, match="orphan"):
        partition(store.path, [])


@pytest.mark.parametrize(
    "mode,category",
    [("eof", "CHILD_PROTOCOL_FAILURE"), ("abnormal", "CHILD_ABNORMAL_EXIT")],
)
def test_exit_without_ready_pipe(
    monkeypatch: pytest.MonkeyPatch, mode: str, category: str
) -> None:
    context_with(monkeypatch, broken_child)
    # Exercise the supervisor's independent process-status path, with no ready
    # envelope. Normal exit without a result is not an abnormal process exit.
    reader, writer = multiprocessing.get_context("spawn").Pipe(duplex=False)
    connection_type = type(reader)
    reader.close()
    writer.close()
    monkeypatch.setattr(connection_type, "poll", lambda self, timeout=0: False)
    f, m = manifest()
    with pytest.raises(runtime.CallStopped) as caught:
        runtime.supervised(m, {}, 10, output=mode)
    record = caught.value.diagnostics.record()
    assert caught.value.reason == "child_exit"
    assert record["child_failure_category"] == category
    assert record["child_exit_code"] == (0 if mode == "eof" else 7)
    assert record["ipc_status"] == "NO_ENVELOPE"
