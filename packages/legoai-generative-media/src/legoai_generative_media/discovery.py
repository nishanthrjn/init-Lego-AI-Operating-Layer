"""Read-only API-family discovery and the closed driver registry.

Explicit families are trusted without probing. `auto` probes both families
read-only; exactly one must present positive, structured evidence. Version
strings are informational and never drive behaviour; capabilities do.
"""

from collections.abc import Callable, Mapping

from legoai.kernel.errors import ErrorCategory

from .drivers import legacy, v2
from .drivers.base import (
    Budget,
    ComfyDriver,
    ProviderError,
    Transport,
    TransportFactory,
)

FAMILIES = ("legacy", "v2")

DriverBuilder = Callable[
    [str | None, Transport, frozenset[str], TransportFactory], ComfyDriver
]


def _legacy(
    version: str | None,
    primary: Transport,
    download_origins: frozenset[str],
    transports: TransportFactory,
) -> ComfyDriver:
    return legacy.LegacyDriver(primary, version)


def _v2(
    version: str | None,
    primary: Transport,
    download_origins: frozenset[str],
    transports: TransportFactory,
) -> ComfyDriver:
    return v2.V2Driver(primary, download_origins=download_origins, downloads=transports)


# Closed map: configuration selects a key, never an import path or callable.
DRIVERS: Mapping[str, DriverBuilder] = {"legacy": _legacy, "v2": _v2}


async def discover(
    family: str,
    transport: Transport,
    *,
    request_timeout: float,
    clock: Callable[[], float],
) -> tuple[str, str | None]:
    """(family, observable version) or ProviderError; never submits or mutates."""
    if family in FAMILIES:
        return family, None
    if family != "auto":
        raise ValueError("unsupported API family")
    budget = Budget(clock() + 3 * request_timeout, clock, request_timeout, True)
    unreachable = 0
    evidence: list[str] = []
    try:
        is_v2, seen = await v2.probe(budget, transport)
        evidence.append(seen)
    except ProviderError:
        raise  # Authentication failures are explicit, not "unsupported".
    except OSError:
        is_v2, unreachable = False, unreachable + 1
        evidence.append("v2 probe: unreachable")
    version: str | None = None
    try:
        version, seen = await legacy.probe(budget, transport)
        evidence.append(seen)
    except OSError:
        unreachable += 1
        evidence.append("legacy probe: unreachable")
    is_legacy = version is not None
    if unreachable == 2:
        raise ProviderError(
            ErrorCategory.DEPENDENCY_FAILURE, "provider_unavailable", tuple(evidence)
        )
    if is_v2 == is_legacy:
        # Neither, or ambiguous: fail closed and require an explicit family.
        raise ProviderError(
            ErrorCategory.VERSION_MISMATCH, "unsupported_api", tuple(evidence)
        )
    return ("v2", None) if is_v2 else ("legacy", version)


async def confirm(
    family: str,
    transport: Transport,
    *,
    request_timeout: float,
    clock: Callable[[], float],
) -> str | None:
    """Read-only evidence for one explicit family; its version if observable."""
    budget = Budget(clock() + 2 * request_timeout, clock, request_timeout, True)
    try:
        if family == "legacy":
            version, seen = await legacy.probe(budget, transport)
            if version is not None:
                return version
        else:
            found, seen = await v2.probe(budget, transport)
            if found:
                return None
    except ProviderError:
        raise
    except OSError:
        raise ProviderError(
            ErrorCategory.DEPENDENCY_FAILURE, "provider_unavailable"
        ) from None
    raise ProviderError(ErrorCategory.VERSION_MISMATCH, "unsupported_api", (seen,))
