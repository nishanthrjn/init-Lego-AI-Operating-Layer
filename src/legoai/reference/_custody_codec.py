"""Closed safe-value codec for the two custody owners; no executable decoding."""

import json
from collections.abc import Callable
from dataclasses import fields, is_dataclass
from datetime import datetime
from enum import Enum
from typing import cast

from legoai.evidence.custody import (
    CustodyAccess,
    CustodyProfile,
    DurableCustodyReceipt,
    SourceEvidence,
)
from legoai.governance.secret import (
    SecretRevisionRef,
    SecretUseFact,
    SecretUseId,
    SecretUsePlan,
    SourceEvent,
)
from legoai.governance.values import ApprovalId, GrantId, PolicyRef, Principal
from legoai.kernel.identity import (
    ApplicationId,
    OperationId,
    PrincipalId,
    RequestId,
    TenantId,
)
from legoai.kernel.references import (
    ApplicationRef,
    ConfigurationRef,
    ConfigurationRevisionRef,
    PrincipalRef,
    ReferenceScope,
)
from legoai.kernel.versions import Version


def _types() -> tuple[type, ...]:
    return (
        SecretRevisionRef,
        SecretUseFact,
        SecretUseId,
        SecretUsePlan,
        ApprovalId,
        GrantId,
        PolicyRef,
        Principal,
        ApplicationId,
        OperationId,
        PrincipalId,
        RequestId,
        TenantId,
        ApplicationRef,
        ConfigurationRef,
        ConfigurationRevisionRef,
        PrincipalRef,
        ReferenceScope,
        Version,
        SourceEvidence,
        DurableCustodyReceipt,
        CustodyAccess,
    )


def _enums() -> tuple[type[Enum], ...]:
    return (SourceEvent, CustodyProfile)


def _encode(value: object) -> object:
    if value is None or type(value) in (str, int):
        return value
    if type(value) is datetime:
        return {"type": "datetime", "value": value.isoformat()}
    if type(value) in _enums() and isinstance(value, Enum):
        return {"type": type(value).__name__, "value": value.value}
    if type(value) in _types() and is_dataclass(value) and not isinstance(value, type):
        return {
            "type": type(value).__name__,
            "fields": {f.name: _encode(getattr(value, f.name)) for f in fields(value)},
        }
    raise ValueError("unsupported custody representation")


def _decode(value: object, depth: int = 0) -> object:
    if depth > 16:
        raise ValueError("custody nesting bound")
    if value is None or type(value) in (str, int):
        return value
    if not isinstance(value, dict):
        raise ValueError("invalid custody representation")
    name = value.get("type")
    if set(value) == {"type", "value"}:
        if name == "datetime" and type(value["value"]) is str:
            return datetime.fromisoformat(value["value"])
        for enum in _enums():
            if name == enum.__name__:
                return enum(value["value"])
    if set(value) == {"type", "fields"} and isinstance(value["fields"], dict):
        for kind in _types():
            if name == kind.__name__:
                args = value["fields"]
                if set(args) != {f.name for f in fields(kind)}:
                    break
                # Closed registry only; each constructor validates decoded input.
                construct = cast(Callable[..., object], kind)
                return construct(
                    **{key: _decode(item, depth + 1) for key, item in args.items()}
                )
    raise ValueError("unknown custody representation")


def _pairs(items: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in items:
        if key in result:
            raise ValueError("duplicate custody key")
        result[key] = value
    return result


def encode(value: object) -> str:
    result = json.dumps(
        _encode(value), ensure_ascii=True, sort_keys=True, separators=(",", ":")
    )
    if len(result.encode()) > 32768:
        raise ValueError("custody record bound")
    return result


def decode(text: str) -> object:
    if type(text) is not str or len(text.encode()) > 32768:
        raise ValueError("custody record bound")
    return _decode(json.loads(text, object_pairs_hook=_pairs))
