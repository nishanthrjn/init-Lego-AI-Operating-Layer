"""F2's closed normalization configuration fixture, not a configuration language.

Strings identifying sources use F1's 1-256 code-point bound. Input size is in
Unicode code points, bounded locally to 1-65536. Whitespace is an ordered tuple
of at most six distinct ASCII whitespace characters; empty means recognize no
whitespace. No Unicode normalization or non-ASCII transformation is implied.
"""

from dataclasses import dataclass, field
from enum import Enum

from legoai.kernel.identity import _validate
from legoai.kernel.references import ConfigurationRef
from legoai.kernel.versions import Version


class SourceLayer(Enum):
    DEFAULTS = "defaults"
    BASE = "base"
    TENANT_OVERRIDE = "tenant override"


class NormalizationMode(Enum):
    """Future fixture behavior: trim edges or also collapse runs to ASCII space.

    F2 only represents these settings; it does not execute normalization.
    Non-ASCII characters are always preserved by this fixture contract.
    """

    TRIM = "trim"
    COLLAPSE = "collapse"


def _versions(contract: Version, interpretation: Version) -> None:
    if type(contract) is not Version or type(interpretation) is not Version:
        raise TypeError("configuration versions must be Version values")
    if contract != Version(0, 1, 0) or interpretation != Version(0, 1, 0):
        raise ValueError("unsupported normalization contract or interpretation version")


def _maximum(value: int) -> None:
    if type(value) is not int:
        raise TypeError("maximum input length must be an integer")
    if not 1 <= value <= 65536:
        raise ValueError("maximum input length must be within 1-65536 code points")


def _whitespace(value: tuple[str, ...]) -> None:
    if type(value) is not tuple:
        raise TypeError("whitespace must be an immutable tuple")
    if len(value) > 6:
        raise ValueError("whitespace collection exceeds six characters")
    for character in value:
        if type(character) is not str:
            raise TypeError("whitespace elements must be text")
        if len(character) != 1 or character not in " \t\n\r\v\f":
            raise ValueError("unsupported whitespace character")
    if len(set(value)) != len(value):
        raise ValueError("duplicate whitespace character")


@dataclass(frozen=True, slots=True)
class SourceProvenance:
    """Claimed source attribution, neither verified provenance nor custody."""

    owner: str = field(repr=False)
    source_id: str = field(repr=False)
    source_revision: str = field(repr=False)
    contract_version: Version
    interpretation_version: Version

    def __post_init__(self) -> None:
        _validate(self.owner)
        _validate(self.source_id)
        _validate(self.source_revision)
        _versions(self.contract_version, self.interpretation_version)


@dataclass(frozen=True, slots=True)
class NormalizationPatch:
    """Internal captured fields. None denotes missing, never explicit input null.

    The capture boundary rejects supplied null before constructing this record.
    A supplied empty tuple is distinct from a missing whitespace field.
    """

    max_input_length: int | None = None
    normalization_mode: NormalizationMode | None = None
    allowed_whitespace: tuple[str, ...] | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        if self.max_input_length is not None:
            _maximum(self.max_input_length)
        if (
            self.normalization_mode is not None
            and type(self.normalization_mode) is not NormalizationMode
        ):
            raise TypeError("normalization mode must be NormalizationMode")
        if self.allowed_whitespace is not None:
            _whitespace(self.allowed_whitespace)


@dataclass(frozen=True, slots=True)
class CapturedCandidate:
    target: ConfigurationRef
    provenance: SourceProvenance
    layer: SourceLayer
    values: NormalizationPatch

    def __post_init__(self) -> None:
        if type(self.target) is not ConfigurationRef:
            raise TypeError("candidate requires ConfigurationRef")
        if type(self.provenance) is not SourceProvenance:
            raise TypeError("candidate requires SourceProvenance")
        if type(self.layer) is not SourceLayer:
            raise TypeError("candidate requires SourceLayer")
        if type(self.values) is not NormalizationPatch:
            raise TypeError("candidate requires immutable NormalizationPatch")
        if (
            self.layer is SourceLayer.TENANT_OVERRIDE
            and self.values.max_input_length is not None
        ):
            raise ValueError(
                "tenant layer cannot replace protected maximum input length"
            )


@dataclass(frozen=True, slots=True)
class EffectiveConfiguration:
    """Fully materialized semantic value; source identities are a separate axis.

    Equality includes interpretation versions and ordered fixture field values,
    not source provenance, capture time, target scope or object identity.
    """

    contract_version: Version
    interpretation_version: Version
    max_input_length: int
    normalization_mode: NormalizationMode
    allowed_whitespace: tuple[str, ...] = field(repr=False)

    def __post_init__(self) -> None:
        _versions(self.contract_version, self.interpretation_version)
        _maximum(self.max_input_length)
        if type(self.normalization_mode) is not NormalizationMode:
            raise TypeError("effective normalization mode must be NormalizationMode")
        _whitespace(self.allowed_whitespace)


@dataclass(frozen=True, slots=True)
class ComposedConfiguration:
    """Unpublished candidate plus retained capture inputs in semantic layer order.

    This is not a publication receipt. Equality of this full record includes
    target/provenance; compare .effective for semantic configuration equality.
    """

    target: ConfigurationRef
    effective: EffectiveConfiguration
    sources: tuple[CapturedCandidate, ...]

    def __post_init__(self) -> None:
        if (
            type(self.target) is not ConfigurationRef
            or type(self.effective) is not EffectiveConfiguration
        ):
            raise TypeError(
                "composition requires typed target and effective configuration"
            )
        if type(self.sources) is not tuple:
            raise TypeError("composition sources must be an immutable captured tuple")
        if not 1 <= len(self.sources) <= 3:
            raise ValueError("composition requires one to three source records")
        if any(type(source) is not CapturedCandidate for source in self.sources):
            raise TypeError("composition sources must contain CapturedCandidate")
        layers = tuple(source.layer for source in self.sources)
        if layers not in (
            (SourceLayer.DEFAULTS,),
            (SourceLayer.DEFAULTS, SourceLayer.BASE),
            (SourceLayer.DEFAULTS, SourceLayer.TENANT_OVERRIDE),
            (SourceLayer.DEFAULTS, SourceLayer.BASE, SourceLayer.TENANT_OVERRIDE),
        ):
            raise ValueError("composition requires defaults and unique ordered layers")
        for source in self.sources:
            if source.target != self.target:
                raise ValueError("composition source scope mismatch")
