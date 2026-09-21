"""F8b: one pure deterministic reference capability -- bounded ASCII
whitespace normalization (Gate-1 plan SS13's "internal walking skeleton").

This is not a generic capability SDK, provider framework, or runtime
registry. It is exactly the one small callable contract the plan names:
"a typed input string and a declared normalization mode produce a typed
normalized result." The function is pure: no I/O, no randomness, no wall
clock, no mutable global state, no network, no AI/model, no database.

The Capability/Plugin identity below is fixed and explicit (never generated
at import/runtime) so that ``legoai.runtime._composition.direct`` can
statically know which one declaration corresponds to this one
implementation (F8b task SS25/SS31-32: "a fixed local correspondence for
the one deterministic fixture is acceptable"). That correspondence is
represented in composition code, never by adding an executable field to
``PluginDeclaration``/``CapabilityOffer`` themselves -- those F7 values
remain exactly as inert as before this module exists.

Uses only the exact ``EffectiveConfiguration``/``NormalizationMode``
semantics F2 already defined (``legoai.application.values``): "trim edges"
or "also collapse runs to ASCII space," non-ASCII characters always
preserved, bounded maximum input length. F2 deliberately represented these
settings without executing them; this module is that execution, and
nothing more.
"""

from __future__ import annotations

from legoai.application.values import EffectiveConfiguration, NormalizationMode
from legoai.capabilities.values import CapabilityId, CapabilityOffer
from legoai.kernel.versions import Version
from legoai.plugins.values import PluginDeclaration, PluginId


def text_normalization_capability_id() -> CapabilityId:
    """The one fixed Capability identity this module's function realizes."""
    return CapabilityId("legoai.deterministic.text_normalization")


def text_normalization_plugin_id() -> PluginId:
    """The one fixed Plugin identity declaring the offer below."""
    return PluginId("legoai.reference", "deterministic-text-normalizer")


def text_normalization_release() -> Version:
    """The one fixed release version of that declaration."""
    return Version(1, 0, 0)


def text_normalization_offer() -> CapabilityOffer:
    return CapabilityOffer(
        text_normalization_capability_id(), text_normalization_release()
    )


def text_normalization_declaration() -> PluginDeclaration:
    """The inert Plugin declaration describing this module's realization.

    Constructing this performs no discovery, admission, activation, or
    binding of any kind (PLUGIN-SPEC PLG-021-024) -- it is the same kind of
    pure data every other ``PluginDeclaration`` is. Its "future owning
    Plugin/Provider/Adapter association" is recorded, per Gate-1 plan SS13,
    without claiming lifecycle activation.
    """
    return PluginDeclaration(
        text_normalization_plugin_id(),
        text_normalization_release(),
        (text_normalization_offer(),),
    )


def _trim(text: str, whitespace: frozenset[str]) -> str:
    start = 0
    end = len(text)
    while start < end and text[start] in whitespace:
        start += 1
    while end > start and text[end - 1] in whitespace:
        end -= 1
    return text[start:end]


def _collapse(text: str, whitespace: frozenset[str]) -> str:
    trimmed = _trim(text, whitespace)
    pieces: list[str] = []
    in_run = False
    for character in trimmed:
        if character in whitespace:
            if not in_run:
                pieces.append(" ")
                in_run = True
        else:
            pieces.append(character)
            in_run = False
    return "".join(pieces)


def normalize_text(text: str, effective: EffectiveConfiguration) -> str:
    """Bounded ASCII whitespace normalization (Gate-1 plan SS13).

    ``TRIM`` removes only leading/trailing characters found in
    ``effective.allowed_whitespace``; interior whitespace runs are left
    exactly as supplied. ``COLLAPSE`` additionally collapses each interior
    run of those characters to one ASCII space. An empty
    ``allowed_whitespace`` means no character is recognized as whitespace,
    so the text passes through unchanged (F2's own documented meaning).
    Non-ASCII characters are never inspected or altered by either mode.

    Pure and total for any input within the bound: same ``text`` and same
    ``effective`` always produce the same output, with no I/O, randomness,
    wall-clock read, or mutable state involved.

    Raises ``TypeError``/``ValueError`` for invalid input; never silently
    truncates or reinterprets oversize text.
    """
    if type(text) is not str:
        raise TypeError("normalize_text requires a built-in string")
    if type(effective) is not EffectiveConfiguration:
        raise TypeError("normalize_text requires EffectiveConfiguration")
    if len(text) > effective.max_input_length:
        raise ValueError("input exceeds the configured maximum length")
    whitespace = frozenset(effective.allowed_whitespace)
    if effective.normalization_mode is NormalizationMode.TRIM:
        return _trim(text, whitespace)
    return _collapse(text, whitespace)
