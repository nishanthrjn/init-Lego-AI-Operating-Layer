"""F7: pure Plugin-declaration-set analysis tests (PLUGIN-SPEC PLG-006,
PLG-017; "Namespace impersonation" risk row).
"""

from __future__ import annotations

import pytest

from legoai.kernel.versions import Version
from legoai.plugins.values import PluginDeclaration, PluginId
from legoai.reference.declarations import (
    DuplicateDeclaration,
    find_duplicate_identities,
    normalize_declarations,
)


def _declaration(namespace: str, local_id: str, release: Version) -> PluginDeclaration:
    return PluginDeclaration(PluginId(namespace, local_id), release)


class TestNormalizeDeclarations:
    def test_deterministic_ordering(self) -> None:
        a = _declaration("zzz", "a", Version(1, 0, 0))
        b = _declaration("aaa", "b", Version(1, 0, 0))
        assert normalize_declarations((a, b)) == (b, a)
        assert normalize_declarations((b, a)) == (b, a)

    def test_empty_input(self) -> None:
        assert normalize_declarations(()) == ()

    def test_wrong_type_rejected(self) -> None:
        with pytest.raises(TypeError):
            normalize_declarations([_declaration("a", "b", Version(1, 0, 0))])  # type: ignore[arg-type]

    def test_orders_by_release_when_identity_matches(self) -> None:
        older = _declaration("org", "p", Version(1, 0, 0))
        newer = _declaration("org", "p", Version(2, 0, 0))
        assert normalize_declarations((newer, older)) == (older, newer)


class TestFindDuplicateIdentities:
    def test_no_duplicates(self) -> None:
        a = _declaration("org.a", "p", Version(1, 0, 0))
        b = _declaration("org.b", "p", Version(1, 0, 0))
        assert find_duplicate_identities((a, b)) == ()

    def test_same_identity_and_release_flagged(self) -> None:
        a = _declaration("org", "p", Version(1, 0, 0))
        b = _declaration("org", "p", Version(1, 0, 0))
        duplicates = find_duplicate_identities((a, b))
        assert len(duplicates) == 1
        assert duplicates[0].occurrences == 2
        assert duplicates[0].plugin_id == a.plugin_id

    def test_same_identity_different_release_not_flagged(self) -> None:
        a = _declaration("org", "p", Version(1, 0, 0))
        b = _declaration("org", "p", Version(2, 0, 0))
        assert find_duplicate_identities((a, b)) == ()

    def test_wrong_type_rejected(self) -> None:
        with pytest.raises(TypeError):
            find_duplicate_identities([_declaration("a", "b", Version(1, 0, 0))])  # type: ignore[arg-type]

    def test_three_occurrences_counted_exactly(self) -> None:
        declarations = tuple(
            _declaration("org", "p", Version(1, 0, 0)) for _ in range(3)
        )
        duplicates = find_duplicate_identities(declarations)
        assert len(duplicates) == 1
        assert duplicates[0].occurrences == 3


class TestDuplicateDeclarationValue:
    def test_occurrences_below_two_rejected(self) -> None:
        with pytest.raises(ValueError):
            DuplicateDeclaration(PluginId("org", "p"), Version(1, 0, 0), 1)

    def test_wrong_type_plugin_id_rejected(self) -> None:
        with pytest.raises(TypeError):
            DuplicateDeclaration("not-a-plugin-id", Version(1, 0, 0), 2)  # type: ignore[arg-type]

    def test_wrong_type_release_rejected(self) -> None:
        with pytest.raises(TypeError):
            DuplicateDeclaration(PluginId("org", "p"), "1.0.0", 2)  # type: ignore[arg-type]
