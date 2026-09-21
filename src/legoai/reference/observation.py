"""F8a: local reference Observation sink using stdlib ``logging`` only.

Importing this module has zero side effects: no ``logging.basicConfig()``
call, no handler attached, no root-logger mutation, no file/socket/
environment access. All effects occur only when a caller explicitly
constructs :class:`LocalLoggingObservationSink` and calls ``emit()``
(Gate-1 plan SS12.1's inert-import discipline; see
``tests/architecture/test_package_install.py``).

This is Gate-1's local diagnostic baseline, not the production
observability architecture Proposed ADR-013 will eventually settle: no
exporter, no OTLP, no metrics backend, no sampling/retention policy, no
distributed trace propagation, no central aggregation, no operational
alerting. Replacing this sink later requires only a new
``ObservationSinkPort`` realization; the semantic ``Observation`` value and
Port are unaffected.
"""

from __future__ import annotations

import json
import logging

from legoai.observability.values import Observation


class LocalLoggingObservationSink:
    """Reference ``ObservationSinkPort`` realization.

    Projects only ``Observation``'s own allowlisted fields into one
    structured JSON line per record -- never ``repr()``/``vars()``/
    ``dataclasses.asdict()`` of the value or of any nested reference, which
    could surface fields those types gain later for unrelated reasons.
    """

    def __init__(self, logger: logging.Logger | None = None) -> None:
        self._logger = (
            logger
            if logger is not None
            else logging.getLogger("legoai.reference.observation")
        )

    def emit(self, observation: Observation) -> None:
        if type(observation) is not Observation:
            raise TypeError("LocalLoggingObservationSink requires an Observation")
        payload = _project(observation)
        text = json.dumps(
            payload, sort_keys=True, separators=(",", ":"), allow_nan=False
        )
        self._logger.info(text)


def _project(observation: Observation) -> dict[str, object]:
    payload: dict[str, object] = {
        "schema_version": observation.schema_version,
        "event_code": observation.event_code.value,
        "owner": observation.owner,
    }
    if observation.correlation_id is not None:
        payload["correlation_id"] = observation.correlation_id.value
    if observation.trace_id is not None:
        payload["trace_id"] = observation.trace_id.value
    if observation.causation is not None:
        payload["causation_operation_id"] = observation.causation.operation_id.value
    if observation.operation is not None:
        payload["operation_id"] = observation.operation.operation_id.value
    if observation.tenant_id is not None:
        payload["tenant_id"] = observation.tenant_id.value
    if observation.configuration_revision is not None:
        payload["configuration_revision_id"] = (
            observation.configuration_revision.revision
        )
    if observation.error_category is not None:
        payload["error_category"] = observation.error_category.value
    if observation.safe_cause_reference is not None:
        payload["safe_cause_reference"] = observation.safe_cause_reference
    if observation.latency_ms is not None:
        payload["latency_ms"] = observation.latency_ms
    if observation.size_bytes is not None:
        payload["size_bytes"] = observation.size_bytes
    return payload
