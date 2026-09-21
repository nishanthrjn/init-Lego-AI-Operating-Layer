"""F7: pure Plugin-declaration-set analysis (PLUGIN-SPEC PLG-006, PLG-017,
"Namespace impersonation" risk row; Gate-1 plan SS14/SS32).

Structural validity of one ``PluginDeclaration`` is already enforced by its
own constructor (``legoai.plugins.values``, e.g. rejecting a duplicate
offer within that one declaration). This module analyzes facts that only
exist *across* an independently supplied sequence of declarations -- pure
input-values-in, analysis-values-out, no filesystem/package/entry-point
discovery, no global registry, no mutation.
"""

from dataclasses import dataclass

from legoai.kernel.versions import Version
from legoai.plugins.values import PluginDeclaration, PluginId


def _declaration_sort_key(
    declaration: PluginDeclaration,
) -> tuple[str, str, int, int, int]:
    return (
        declaration.plugin_id.namespace,
        declaration.plugin_id.local_id,
        declaration.release.major,
        declaration.release.minor,
        declaration.release.patch,
    )


def normalize_declarations(
    declarations: tuple[PluginDeclaration, ...],
) -> tuple[PluginDeclaration, ...]:
    """Deterministically order an independently supplied declaration set.

    Ordering here carries no preference/priority meaning -- it exists only
    so downstream analysis is reproducible rather than depending on
    caller-supplied sequence, dict, or set iteration order.
    """
    if type(declarations) is not tuple or any(
        type(declaration) is not PluginDeclaration for declaration in declarations
    ):
        raise TypeError(
            "normalize_declarations requires an immutable tuple of PluginDeclaration"
        )
    return tuple(sorted(declarations, key=_declaration_sort_key))


@dataclass(frozen=True, slots=True)
class DuplicateDeclaration:
    """One ``(PluginId, release)`` pair that appears more than once among
    independently supplied declarations -- a namespace/identity collision
    fact (PLUGIN-SPEC's "Namespace impersonation" risk row), not itself a
    security verdict. This module only surfaces the fact; attributing or
    resolving the collision is Security/Governance's later decision."""

    plugin_id: PluginId
    release: Version
    occurrences: int

    def __post_init__(self) -> None:
        if type(self.plugin_id) is not PluginId:
            raise TypeError("duplicate declaration requires PluginId")
        if type(self.release) is not Version:
            raise TypeError("duplicate declaration requires a release Version")
        if type(self.occurrences) is not int or self.occurrences < 2:
            raise ValueError("occurrences must be an integer of 2 or more")


def find_duplicate_identities(
    declarations: tuple[PluginDeclaration, ...],
) -> tuple[DuplicateDeclaration, ...]:
    """Find every ``(PluginId, release)`` pair declared more than once in
    ``declarations``. Two independent declaration objects claiming the
    identical Plugin identity and release is a genuine collision worth
    surfacing without any admission/loading machinery."""
    if type(declarations) is not tuple or any(
        type(declaration) is not PluginDeclaration for declaration in declarations
    ):
        raise TypeError(
            "find_duplicate_identities requires an immutable tuple of PluginDeclaration"
        )
    counts: dict[tuple[PluginId, Version], int] = {}
    for declaration in declarations:
        key = (declaration.plugin_id, declaration.release)
        counts[key] = counts.get(key, 0) + 1
    duplicates = [
        DuplicateDeclaration(plugin_id, release, count)
        for (plugin_id, release), count in counts.items()
        if count > 1
    ]
    duplicates.sort(
        key=lambda d: (
            d.plugin_id.namespace,
            d.plugin_id.local_id,
            d.release.major,
            d.release.minor,
            d.release.patch,
        )
    )
    return tuple(duplicates)
