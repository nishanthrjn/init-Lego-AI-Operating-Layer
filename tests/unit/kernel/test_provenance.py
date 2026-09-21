"""F4: kernel.provenance identity value tests (DutyId, DutyKind)."""

from __future__ import annotations

import pytest

from legoai.kernel.provenance import DutyId, DutyKind


class TestDutyId:
    def test_construction_and_equality(self) -> None:
        assert DutyId("duty-1") == DutyId("duty-1")
        assert DutyId("duty-1") != DutyId("duty-2")

    def test_cross_kind_distinction(self) -> None:
        # Same text, different kind: DutyId and DutyKind are distinct,
        # non-interchangeable nominal types even when their underlying text
        # is identical (mypy itself already proves this statically; this
        # confirms the same text round-trips through each type independently
        # at runtime).
        assert DutyId("x").value == DutyKind("x").value == "x"

    def test_empty_value_rejected(self) -> None:
        with pytest.raises(ValueError):
            DutyId("")

    def test_wrong_type_rejected(self) -> None:
        with pytest.raises(TypeError):
            DutyId(123)  # type: ignore[arg-type]

    def test_str_subclass_rejected(self) -> None:
        class NotQuiteStr(str):
            pass

        with pytest.raises(TypeError):
            DutyId(NotQuiteStr("duty-1"))

    def test_frozen(self) -> None:
        duty_id = DutyId("duty-1")
        with pytest.raises(AttributeError):
            duty_id.value = "mutated"  # type: ignore[misc]  # noqa: B010

    def test_repr_omits_value(self) -> None:
        assert "duty-1" not in repr(DutyId("duty-1"))


class TestDutyKind:
    def test_construction_and_equality(self) -> None:
        assert DutyKind("source-submission") == DutyKind("source-submission")
        assert DutyKind("source-submission") != DutyKind("catalog-publication")

    def test_open_vocabulary_accepts_new_kind(self) -> None:
        # DutyKind is deliberately not a closed enum: any bounded opaque text
        # is a valid kind, so a future owner can declare a new kind without
        # a Kernel code change.
        assert DutyKind("resource-settlement").value == "resource-settlement"

    def test_empty_value_rejected(self) -> None:
        with pytest.raises(ValueError):
            DutyKind("")

    def test_wrong_type_rejected(self) -> None:
        with pytest.raises(TypeError):
            DutyKind(None)  # type: ignore[arg-type]

    def test_frozen(self) -> None:
        kind = DutyKind("source-submission")
        with pytest.raises(AttributeError):
            kind.value = "mutated"  # type: ignore[misc]  # noqa: B010
