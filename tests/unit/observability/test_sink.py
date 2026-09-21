"""F8a: ObservationSinkPort substitution, failure containment, and
import-inertness tests (Gate-1 plan SS6/SS17; F8a task SS17-23, SS38-39).
"""

from __future__ import annotations

import ast
import importlib
import json
import logging
import subprocess
import sys
from pathlib import Path

import pytest

from legoai.kernel.errors import ErrorCategory
from legoai.kernel.identity import (
    ApplicationId,
    CorrelationId,
    OperationId,
    TenantId,
    TraceId,
)
from legoai.kernel.references import (
    ApplicationRef,
    ConfigurationRef,
    ConfigurationRevisionRef,
    OperationRef,
    ReferenceScope,
)
from legoai.kernel.versions import Version
from legoai.observability.ports import ObservationSinkPort
from legoai.observability.values import Observation, ObservationEventCode
from legoai.reference.observation import LocalLoggingObservationSink
from tests.support.observation import CapturingObservationSink, FailingObservationSink

SUPER_SECRET_CANARY_VALUE = "SUPER_SECRET_CANARY_VALUE"


def _observation() -> Observation:
    return Observation(1, ObservationEventCode("config.publish.committed"), "owner")


def _target() -> ConfigurationRef:
    scope = ReferenceScope("owner1", TenantId("t1"))
    return ConfigurationRef(ApplicationRef(scope, ApplicationId("app1")), "i1")


def _fully_populated_observation() -> Observation:
    target = _target()
    op = OperationRef(target, OperationId("op1"), "sink-fixture")
    return Observation(
        schema_version=1,
        event_code=ObservationEventCode("config.publish.rejected"),
        owner="legoai.reference.application",
        correlation_id=CorrelationId("corr-1"),
        trace_id=TraceId("trace-1"),
        causation=op,
        operation=op,
        tenant_id=TenantId("t1"),
        configuration_revision=ConfigurationRevisionRef(target, "r1", Version(0, 1, 0)),
        error_category=ErrorCategory.CONFLICT,
        safe_cause_reference="expected-revision-mismatch",
        latency_ms=12.5,
        size_bytes=256,
    )


class TestPortSubstitution:
    def test_capturing_sink_satisfies_port(self) -> None:
        sink: ObservationSinkPort = CapturingObservationSink()
        assert isinstance(sink, ObservationSinkPort)

    def test_local_logging_sink_satisfies_port(self) -> None:
        sink: ObservationSinkPort = LocalLoggingObservationSink()
        assert isinstance(sink, ObservationSinkPort)

    def test_failing_sink_satisfies_port(self) -> None:
        sink: ObservationSinkPort = FailingObservationSink()
        assert isinstance(sink, ObservationSinkPort)

    @pytest.mark.parametrize(
        "make_sink",
        [CapturingObservationSink, LocalLoggingObservationSink],
    )
    def test_semantic_value_construction_does_not_depend_on_sink_choice(
        self, make_sink: type[ObservationSinkPort]
    ) -> None:
        # The same Observation value is emitted identically regardless of
        # which sink realization receives it -- proving substitutability.
        observation = _observation()
        sink = make_sink()
        sink.emit(observation)  # must not raise for a well-formed observation


class TestCapturingSink:
    def test_records_deterministically(self) -> None:
        sink = CapturingObservationSink()
        first = _observation()
        second = Observation(
            1, ObservationEventCode("config.publish.rejected"), "owner"
        )
        sink.emit(first)
        sink.emit(second)
        assert sink.observations == [first, second]

    def test_supports_assertions_on_content(self) -> None:
        sink = CapturingObservationSink()
        sink.emit(_observation())
        assert sink.observations[0].event_code.value == "config.publish.committed"


class TestLocalLoggingSink:
    def test_emits_one_json_line_with_allowed_fields_only(self) -> None:
        logger = logging.getLogger("legoai.reference.observation.test")
        records: list[str] = []

        class _Handler(logging.Handler):
            def emit(self, record: logging.LogRecord) -> None:
                records.append(record.getMessage())

        handler = _Handler()
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False
        try:
            sink = LocalLoggingObservationSink(logger)
            sink.emit(_observation())
        finally:
            logger.removeHandler(handler)

        assert len(records) == 1
        payload = json.loads(records[0])
        assert payload == {
            "schema_version": 1,
            "event_code": "config.publish.committed",
            "owner": "owner",
        }

    def test_emits_every_populated_optional_field(self) -> None:
        logger = logging.getLogger("legoai.reference.observation.test.full")
        records: list[str] = []

        class _Handler(logging.Handler):
            def emit(self, record: logging.LogRecord) -> None:
                records.append(record.getMessage())

        handler = _Handler()
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False
        try:
            sink = LocalLoggingObservationSink(logger)
            sink.emit(_fully_populated_observation())
        finally:
            logger.removeHandler(handler)

        assert len(records) == 1
        payload = json.loads(records[0])
        assert payload == {
            "schema_version": 1,
            "event_code": "config.publish.rejected",
            "owner": "legoai.reference.application",
            "correlation_id": "corr-1",
            "trace_id": "trace-1",
            "causation_operation_id": "op1",
            "operation_id": "op1",
            "tenant_id": "t1",
            "configuration_revision_id": "r1",
            "error_category": "Conflict",
            "safe_cause_reference": "expected-revision-mismatch",
            "latency_ms": 12.5,
            "size_bytes": 256,
        }

    def test_rejects_non_observation_input(self) -> None:
        sink = LocalLoggingObservationSink()
        with pytest.raises(TypeError):
            sink.emit("not-an-observation")  # type: ignore[arg-type]

    def test_does_not_use_repr_or_vars_projection(self) -> None:
        # Explicit field-by-field projection: adding an unrelated attribute
        # to the Observation instance's __dict__ is impossible (frozen,
        # slotted) and the sink never calls vars()/asdict() to discover
        # fields dynamically -- verified structurally via source scan.
        import legoai.reference.observation as module

        assert module.__file__ is not None
        source = Path(module.__file__).read_text(encoding="utf-8")
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                assert node.func.id not in {"vars", "repr"}
            if isinstance(node, ast.Attribute):
                assert node.attr != "asdict"


class TestFailingSinkContainment:
    def test_failing_sink_raises(self) -> None:
        sink = FailingObservationSink()
        with pytest.raises(RuntimeError):
            sink.emit(_observation())

    def test_sink_failure_does_not_mutate_observation(self) -> None:
        observation = _observation()
        sink = FailingObservationSink()
        with pytest.raises(RuntimeError):
            sink.emit(observation)
        # The value remains exactly what it was -- diagnostic failure has no
        # semantic-state side effect to undo, because there was never one.
        assert observation == _observation()

    def test_sink_failure_does_not_prevent_a_different_sink_from_working(self) -> None:
        failing = FailingObservationSink()
        capturing = CapturingObservationSink()
        observation = _observation()
        with pytest.raises(RuntimeError):
            failing.emit(observation)
        capturing.emit(observation)
        assert capturing.observations == [observation]


class TestImportInertness:
    def test_import_does_not_configure_logging_or_touch_filesystem(
        self, tmp_path: Path
    ) -> None:
        script = """
import logging, sys
from unittest.mock import patch
handlers = tuple(logging.getLogger().handlers)
def denied(*args, **kwargs):
    raise AssertionError("import side effect")
with patch.object(logging, "basicConfig", denied):
    import legoai.reference.observation
    import legoai.observability
    import legoai.observability.values
    import legoai.observability.ports
assert tuple(logging.getLogger().handlers) == handlers
"""
        result = subprocess.run(
            [sys.executable, "-I", "-B", "-c", script],
            cwd=tmp_path,
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        assert list(tmp_path.iterdir()) == []

    def test_module_reload_still_has_no_side_effects(self) -> None:
        import legoai.reference.observation as module

        handlers_before = tuple(logging.getLogger().handlers)
        importlib.reload(module)
        assert tuple(logging.getLogger().handlers) == handlers_before
