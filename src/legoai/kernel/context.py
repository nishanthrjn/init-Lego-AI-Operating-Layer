"""Neutral explicit scope anchors; no ambient context or admission behavior."""

from dataclasses import dataclass

from legoai.kernel.identity import TenantId


@dataclass(frozen=True, slots=True)
class TenantContext:
    """Exactly one asserted tenant, requiring external verification before use."""

    tenant_id: TenantId

    def __post_init__(self) -> None:
        if type(self.tenant_id) is not TenantId:
            raise TypeError("tenant context requires explicit TenantId")
