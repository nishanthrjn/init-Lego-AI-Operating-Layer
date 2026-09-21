"""ADR-003 pure capture/composition for the closed F2 normalization fixture.

No I/O, runtime authority, publication or normalization execution. Caller inputs
must remain stable during this synchronous capture; no atomic multi-source read
or isolation against hostile in-process mutation is claimed.
"""

from typing import cast

from legoai.application.values import (
    CapturedCandidate,
    ComposedConfiguration,
    EffectiveConfiguration,
    NormalizationMode,
    NormalizationPatch,
    SourceLayer,
    SourceProvenance,
    _versions,
)
from legoai.kernel.references import ConfigurationRef
from legoai.kernel.versions import Version


def capture_candidate(
    raw: object,
    *,
    target: ConfigurationRef,
    provenance: SourceProvenance,
    layer: SourceLayer,
) -> CapturedCandidate:
    """Capture a built-in dictionary exactly once, copying its bounded collection.

    Keys are the three fixture field names. Mode input is exact text; whitespace
    input is a built-in list/tuple. Unknown keys/null/coercion are rejected with
    value-free errors. Missing keys alone become internal absence.
    """
    if type(raw) is not dict:
        raise TypeError("candidate input must be a built-in dictionary")
    if type(layer) is not SourceLayer:
        raise TypeError("candidate requires SourceLayer")
    if layer is SourceLayer.DEFAULTS:
        raise ValueError("defaults are supplied by the configuration contract")
    entries = cast(dict[object, object], raw)
    if len(entries) > 3:
        raise ValueError("candidate exceeds the closed field bound")
    captured = tuple(entries.items())
    maximum: int | None = None
    mode: NormalizationMode | None = None
    whitespace: tuple[str, ...] | None = None
    for name, value in captured:
        if type(name) is not str:
            raise TypeError("candidate field names must be text")
        if name == "max_input_length":
            if type(value) is not int:
                raise TypeError("maximum input length must be an integer")
            maximum = value
        elif name == "normalization_mode":
            if type(value) is not str:
                raise TypeError("normalization mode input must be text")
            if value not in ("trim", "collapse"):
                raise ValueError("unsupported normalization mode")
            mode = NormalizationMode(value)
        elif name == "allowed_whitespace":
            if type(value) not in (list, tuple):
                raise TypeError("whitespace input must be a built-in list or tuple")
            sequence = cast(list[object] | tuple[object, ...], value)
            if len(sequence) > 6:
                raise ValueError("whitespace collection exceeds six characters")
            items = tuple(sequence)
            if any(type(item) is not str for item in items):
                raise TypeError("whitespace elements must be text")
            whitespace = cast(tuple[str, ...], items)
        else:
            raise ValueError("unknown configuration field or extension")
    return CapturedCandidate(
        target, provenance, layer, NormalizationPatch(maximum, mode, whitespace)
    )


def compose_configuration(
    target: ConfigurationRef,
    candidates: tuple[CapturedCandidate, ...],
    *,
    contract_version: Version,
    interpretation_version: Version,
) -> ComposedConfiguration:
    """Defaults → unique base → optional tenant layer, replacing whole fields.

    Layer legality is not live authorization. Realization/deployment fields and
    extensions are absent from this fixture; they have no implicit override rank.
    """
    _versions(contract_version, interpretation_version)
    if type(target) is not ConfigurationRef:
        raise TypeError("composition requires ConfigurationRef")
    if type(candidates) is not tuple:
        raise TypeError("composition requires an immutable captured candidate tuple")
    if len(candidates) > 2:
        raise ValueError("at most one base and one tenant layer are supported")
    if any(type(candidate) is not CapturedCandidate for candidate in candidates):
        raise TypeError("composition requires captured candidates")
    base: CapturedCandidate | None = None
    override: CapturedCandidate | None = None
    for candidate in candidates:
        if candidate.target != target:
            raise ValueError(
                "candidate owner, tenant, Application or instance mismatch"
            )
        if candidate.layer is SourceLayer.BASE and base is None:
            base = candidate
        elif candidate.layer is SourceLayer.TENANT_OVERRIDE and override is None:
            override = candidate
        else:
            raise ValueError("duplicate layer or caller-supplied defaults")
    default_values = EffectiveConfiguration(
        contract_version,
        interpretation_version,
        4096,
        NormalizationMode.COLLAPSE,
        (" ", "\t", "\n", "\r", "\v", "\f"),
    )
    defaults = CapturedCandidate(
        target,
        SourceProvenance(
            "legoai.normalization-fixture",
            "contract-defaults",
            "0.1.0",
            contract_version,
            interpretation_version,
        ),
        SourceLayer.DEFAULTS,
        NormalizationPatch(
            default_values.max_input_length,
            default_values.normalization_mode,
            default_values.allowed_whitespace,
        ),
    )
    sources = (defaults,) + tuple(
        source for source in (base, override) if source is not None
    )
    maximum = default_values.max_input_length
    mode = default_values.normalization_mode
    whitespace = default_values.allowed_whitespace
    for source in sources[1:]:
        patch = source.values
        if patch.max_input_length is not None:
            maximum = patch.max_input_length
        if patch.normalization_mode is not None:
            mode = patch.normalization_mode
        if patch.allowed_whitespace is not None:
            whitespace = patch.allowed_whitespace
    return ComposedConfiguration(
        target,
        EffectiveConfiguration(
            contract_version, interpretation_version, maximum, mode, whitespace
        ),
        sources,
    )
