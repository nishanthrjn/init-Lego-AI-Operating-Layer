"""Test-only ObservationSinkPort realizations. Never shipped as production
fallbacks (F8a task SS19-20; Gate-1 plan SS9.1's own fake-placement rule).
"""

from __future__ import annotations

from legoai.observability.values import Observation


class CapturingObservationSink:
    """Deterministic in-memory sink for assertions."""

    def __init__(self) -> None:
        self.observations: list[Observation] = []

    def emit(self, observation: Observation) -> None:
        self.observations.append(observation)


class FailingObservationSink:
    """Deliberately failing sink for failure-containment tests."""

    def emit(self, observation: Observation) -> None:
        raise RuntimeError("injected observation sink failure")
