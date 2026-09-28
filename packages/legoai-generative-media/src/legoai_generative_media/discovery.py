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
    try:
        is_v2 = await v2.probe(budget, transport)
    except ProviderError:
        raise  # Authentication failures are explicit, not "unsupported".
    except OSError:
        is_v2, unreachable = False, unreachable + 1
    except ValueError:
        is_v2 = False
    version: str | None = None
    try:
        version = await legacy.probe_version(budget, transport)
        is_legacy = True
    except OSError:
        is_legacy, unreachable = False, unreachable + 1
    except ValueError, KeyError, TypeError:
        is_legacy = False
    if unreachable == 2:
        raise ProviderError(ErrorCategory.DEPENDENCY_FAILURE, "provider_unavailable")
    if is_v2 == is_legacy:
        # Neither, or ambiguous: fail closed and require an explicit family.
        raise ProviderError(ErrorCategory.VERSION_MISMATCH, "unsupported_api")
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
            return await legacy.probe_version(budget, transport)
        if family == "v2" and await v2.probe(budget, transport):
            return None
    except ProviderError:
        raise
    except OSError:
        raise ProviderError(
            ErrorCategory.DEPENDENCY_FAILURE, "provider_unavailable"
        ) from None
    except ValueError, KeyError, TypeError:
        pass
    raise ProviderError(ErrorCategory.VERSION_MISMATCH, "unsupported_api")
