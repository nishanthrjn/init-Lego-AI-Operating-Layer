"""Shared owner-neutral duty-obligation anchors (ADR-004 SS9, ADR-009).

Narrow anchors only: identifying one outstanding owner duty and its open,
owner-declared category. No custody behavior, no evidence-fact identity (no
evidence has been submitted at duty-creation time -- only a requirement for
it), no retention/repair mechanics, and no storage belong here. Owner-specific
duty *content* (which subject, which principal, what is required) lives in
each owning owner's own values module (e.g. `legoai.application.values`),
composed from these anchors plus existing Kernel references.
"""

from dataclasses import dataclass, field

from legoai.kernel.identity import _validate


@dataclass(frozen=True, slots=True)
class DutyId:
    """Opaque identity of one outstanding owner duty/obligation.

    Not a custody receipt and not proof any obligation was accepted or
    resolved; construction alone establishes no authority or completion.
    """

    value: str = field(repr=False)

    def __post_init__(self) -> None:
        _validate(self.value)


@dataclass(frozen=True, slots=True)
class DutyKind:
    """Open, owner-declared obligation category.

    Deliberately not a closed enum: no accepted document enumerates a fixed
    obligation-kind set, and future owners (evidence repair, catalog
    publication, external-effect reconciliation, resource settlement, Plugin
    cleanup, ...) must be able to declare new kinds without a Kernel or
    Application code change. Distinct kind values with identical text are
    still the same opaque text; callers distinguish kinds by agreed value,
    not by Python type beyond this wrapper.
    """

    value: str = field(repr=False)

    def __post_init__(self) -> None:
        _validate(self.value)
