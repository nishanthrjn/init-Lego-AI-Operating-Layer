"""F8a: minimal Observation sink boundary (Gate-1 plan SS6, SS17).

Narrow by design: this Port is responsible only for accepting one already
validated ``Observation``. It owns no format policy, retention, sampling,
network delivery, authorization, or Evidence storage -- those remain out of
scope for Gate-1's local diagnostic baseline and, where they eventually
matter, belong to Proposed ADR-013's later production observability
architecture, not this Port. This module settles none of ADR-013's open
questions (export protocols, sampling, retention, distributed trace
propagation, metrics backend, central aggregation, operational alerting).
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from legoai.observability.values import Observation


@runtime_checkable
class ObservationSinkPort(Protocol):
    """Synchronous diagnostic sink boundary. No async API in Gate 1."""

    def emit(self, observation: Observation) -> None:
        """Accept one validated ``Observation``.

        May raise if the sink itself fails (a real local I/O/logging
        failure) -- that is a diagnostic-path failure only. Nothing in
        Gate-1's semantic model reads this method's return value, catches
        its exceptions to decide operation success, or otherwise treats
        Observation emission as authoritative. No caller-facing
        best-effort/swallowing wrapper is introduced in this batch; a
        future real consumer decides its own failure-containment policy
        around this narrow Port.
        """
        ...
