"""ADR-003/F2 contract vectors; no publication, credentials or live governance."""

from collections.abc import Callable
from dataclasses import FrozenInstanceError, fields, replace
from itertools import permutations
from typing import cast

import pytest

from legoai.application.values import (
    CapturedCandidate,
    ComposedConfiguration,
    EffectiveConfiguration,
    NormalizationMode,
    NormalizationPatch,
    SourceLayer,
    SourceProvenance,
)
from legoai.kernel.identity import ApplicationId, TenantId
from legoai.kernel.references import ApplicationRef, ConfigurationRef, ReferenceScope
from legoai.kernel.versions import Version
from legoai.reference.application.configuration import (
    capture_candidate,
    compose_configuration,
)


def target(tenant: str = "tenant") -> ConfigurationRef:
    return ConfigurationRef(
        ApplicationRef(
            ReferenceScope("composition", TenantId(tenant)), ApplicationId("app")
        ),
        "normalization",
    )


def provenance(source: str = "source") -> SourceProvenance:
    return SourceProvenance(
        "source-owner", source, "revision-1", Version(0, 1, 0), Version(0, 1, 0)
    )


def capture(raw: object, layer: SourceLayer = SourceLayer.BASE) -> CapturedCandidate:
    return capture_candidate(raw, target=target(), provenance=provenance(), layer=layer)


def compose(*sources: CapturedCandidate) -> ComposedConfiguration:
    return compose_configuration(
        target(),
        sources,
        contract_version=Version(0, 1, 0),
        interpretation_version=Version(0, 1, 0),
    )


def test_defaults_and_base() -> None:
    result = compose()
    assert result.effective == EffectiveConfiguration(
        Version(0, 1, 0),
        Version(0, 1, 0),
        4096,
        NormalizationMode.COLLAPSE,
        (" ", "\t", "\n", "\r", "\v", "\f"),
    )
    assert result.sources[0].layer is SourceLayer.DEFAULTS
    assert result.sources[0].provenance.source_id == "contract-defaults"
    base = capture({"max_input_length": 100, "normalization_mode": "trim"})
    changed = compose(base)
    assert changed.effective.max_input_length == 100
    assert changed.effective.normalization_mode is NormalizationMode.TRIM
    assert changed.sources == (result.sources[0], base)


def test_override_replaces_whole_collection_and_order_is_layer_defined() -> None:
    base = capture({"allowed_whitespace": [" ", "\t"], "max_input_length": 1024})
    override = capture(
        {"allowed_whitespace": [" "], "normalization_mode": "trim"},
        SourceLayer.TENANT_OVERRIDE,
    )
    for sources in permutations((base, override)):
        result = compose(*sources)
        assert result.effective.allowed_whitespace == (" ",)
        assert result.effective.max_input_length == 1024
        assert result.effective.normalization_mode is NormalizationMode.TRIM
        assert result.sources[1:] == (base, override)
        assert result == compose(base, override)
    assert compose(override).effective.allowed_whitespace == (" ",)
    assert (
        compose(capture({}, SourceLayer.TENANT_OVERRIDE)).effective
        == compose().effective
    )


@pytest.mark.parametrize("layer", [SourceLayer.BASE, SourceLayer.TENANT_OVERRIDE])
def test_duplicate_writers_fail_in_every_order(layer: SourceLayer) -> None:
    first = capture({"normalization_mode": "trim"}, layer)
    second = capture({"allowed_whitespace": []}, layer)
    for sources in permutations((first, second)):
        with pytest.raises(ValueError, match="duplicate"):
            compose(*sources)


def test_protected_field_and_defaults_cannot_be_overridden() -> None:
    for maximum in (1, 4096):
        with pytest.raises(ValueError, match="protected"):
            capture({"max_input_length": maximum}, SourceLayer.TENANT_OVERRIDE)
    with pytest.raises(ValueError, match="defaults"):
        capture({}, SourceLayer.DEFAULTS)
    with pytest.raises(ValueError, match="defaults"):
        compose(compose().sources[0])
    with pytest.raises(ValueError, match="at most"):
        compose(capture({}), capture({}), capture({}))


@pytest.mark.parametrize(
    "field", ["max_input_length", "normalization_mode", "allowed_whitespace"]
)
def test_missing_is_not_null_or_empty_string(field: str) -> None:
    assert compose(capture({})).effective == compose().effective
    for value in (None, ""):
        with pytest.raises((TypeError, ValueError)):
            capture({field: value})


def test_empty_collection_is_not_missing() -> None:
    base = capture({"allowed_whitespace": [" ", "\t"]})
    override = capture({"allowed_whitespace": []}, SourceLayer.TENANT_OVERRIDE)
    assert override.values.allowed_whitespace == ()
    assert compose(base, override).effective.allowed_whitespace == ()
    assert compose(capture({})).effective.allowed_whitespace != ()


@pytest.mark.parametrize(
    "raw",
    [
        {"max_input_length": True},
        {"max_input_length": 0},
        {"max_input_length": -1},
        {"max_input_length": 65537},
        {"max_input_length": "1"},
        {"max_input_length": 1.0},
        {"normalization_mode": "unknown"},
        {"normalization_mode": False},
        {"allowed_whitespace": ["x"]},
        {"allowed_whitespace": ["\u00a0"]},
        {"allowed_whitespace": [" ", " "]},
        {"allowed_whitespace": [" "] * 7},
        {"allowed_whitespace": [""]},
        {"allowed_whitespace": ["  "]},
        {"allowed_whitespace": [1]},
        {"allowed_whitespace": {" "}},
        {"allowed_whitespace": {"nested": []}},
        {"allowed_whitespace": [[" "]]},
        {"normalization_mode.child": "trim"},
        {"extensions": {"required": "unknown"}},
        {"max_input_lenght": 10},
        {1: "value"},
        [],
        None,
    ],
)
def test_invalid_closed_inputs(raw: object) -> None:
    with pytest.raises((TypeError, ValueError)):
        capture(raw)


def test_bounds_and_input_order() -> None:
    for maximum in (1, 65536):
        assert (
            compose(capture({"max_input_length": maximum})).effective.max_input_length
            == maximum
        )
    assert capture(
        {"normalization_mode": "trim", "allowed_whitespace": [" "]}
    ) == capture({"allowed_whitespace": (" ",), "normalization_mode": "trim"})
    with pytest.raises(ValueError, match="bound"):
        capture({"a": 1, "b": 2, "c": 3, "d": 4})


def test_capture_freezes_nested_input_and_preserves_provenance() -> None:
    whitespace = [" ", "\t"]
    raw: dict[str, object] = {"allowed_whitespace": whitespace, "max_input_length": 15}
    candidate = capture(raw)
    result = compose(candidate)
    whitespace.clear()
    raw.clear()
    assert candidate.values.allowed_whitespace == (" ", "\t")
    assert result == compose(candidate)
    assert result.effective.max_input_length == 15
    assert candidate.provenance == provenance()
    assert candidate.target == target()
    assert candidate.provenance.source_revision == "revision-1"
    assert candidate.provenance.contract_version == Version(0, 1, 0)
    assert candidate.provenance.interpretation_version == Version(0, 1, 0)
    for item in (
        candidate,
        candidate.provenance,
        candidate.values,
        result,
        result.effective,
    ):
        original_hash = hash(item)
        for attribute in fields(item):
            with pytest.raises(FrozenInstanceError):
                setattr(item, attribute.name, None)
        assert hash(item) == original_hash
        assert not hasattr(item, "__dict__")


def test_semantic_equality_separate_from_provenance() -> None:
    first = capture({"normalization_mode": "trim"})
    second = replace(first, provenance=provenance("different-source"))
    assert compose(first).effective == compose(second).effective
    assert compose(first) != compose(second)
    for _ in range(10):
        assert compose(first) == compose(first)
    later = capture({"normalization_mode": "collapse"})
    assert compose(first).effective.normalization_mode is NormalizationMode.TRIM
    assert compose(later).effective != compose(first).effective


def test_environment_never_read(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LEGOAI_MAX_INPUT_LENGTH", "10")
    candidate = capture({})
    first = compose(candidate)
    monkeypatch.setenv("LEGOAI_MAX_INPUT_LENGTH", "999")
    assert compose(candidate) == first
    assert compose(capture({})).effective == first.effective


def test_wrong_target_scope() -> None:
    original = target()
    app = original.application
    wrong_targets = (
        target("other"),
        replace(original, instance="other"),
        replace(
            original, application=replace(app, application_id=ApplicationId("other"))
        ),
        replace(
            original, application=replace(app, scope=replace(app.scope, owner="other"))
        ),
    )
    for wrong in wrong_targets:
        for layer in (SourceLayer.BASE, SourceLayer.TENANT_OVERRIDE):
            source = capture_candidate(
                {}, target=wrong, provenance=provenance(), layer=layer
            )
            with pytest.raises(ValueError, match="mismatch"):
                compose(source)


@pytest.mark.parametrize("field", ["contract_version", "interpretation_version"])
def test_unsupported_interpretation(field: str) -> None:
    with pytest.raises(ValueError, match="unsupported"):
        cast(Callable[..., object], replace)(provenance(), **{field: Version(0, 2, 0)})
    arguments = {
        "contract_version": Version(0, 1, 0),
        "interpretation_version": Version(0, 1, 0),
    }
    arguments[field] = Version(0, 2, 0)
    with pytest.raises(ValueError, match="unsupported"):
        compose_configuration(target(), (), **arguments)


def test_safe_errors_no_credentials_or_authority() -> None:
    for key in (
        "api_key",
        "token",
        "password",
        "credentials",
        "secret",
        "authorized",
        "skip_policy",
    ):
        with pytest.raises(ValueError) as failure:
            capture({key: "sensitive-canary"})
        assert "sensitive-canary" not in str(failure.value)
        assert key not in str(failure.value)
    result = compose(capture({}))
    for value in (result, result.effective, result.sources[0]):
        assert not any(
            hasattr(value, name)
            for name in (
                "revision",
                "owner_revision",
                "activate",
                "authorize",
                "resolve_secret",
                "current",
                "publish",
            )
        )
    assert "sensitive-canary" not in repr(
        replace(provenance(), source_id="sensitive-canary")
    )


def test_constructor_boundaries() -> None:
    patch = NormalizationPatch(1, NormalizationMode.TRIM, ())
    candidate = capture({})
    result = compose(candidate)
    # Intentional runtime-boundary violations, not unchecked production calls.
    for value in (provenance(), candidate, result, result.effective):
        for attribute in fields(value):
            with pytest.raises(TypeError):
                cast(Callable[..., object], replace)(value, **{attribute.name: []})
    for attribute in fields(patch):
        with pytest.raises(TypeError):
            cast(Callable[..., object], replace)(patch, **{attribute.name: []})
    with pytest.raises(TypeError):
        compose_configuration(
            cast(ConfigurationRef, Version(0, 1, 0)),
            (),
            contract_version=Version(0, 1, 0),
            interpretation_version=Version(0, 1, 0),
        )
    with pytest.raises(TypeError):
        compose_configuration(
            target(),
            cast(tuple[CapturedCandidate, ...], [candidate]),
            contract_version=Version(0, 1, 0),
            interpretation_version=Version(0, 1, 0),
        )
    with pytest.raises(TypeError):
        capture_candidate(
            {},
            target=target(),
            provenance=provenance(),
            layer=cast(SourceLayer, "base"),
        )
    with pytest.raises(ValueError):
        replace(result, sources=())
    with pytest.raises(ValueError):
        replace(result, target=target("other"))


def test_no_custom_container_callbacks() -> None:
    class Input(dict[str, object]):
        def __getitem__(self, key: str) -> object:  # deliberately never invoked
            raise AssertionError("untrusted callback")

    with pytest.raises(TypeError):
        capture(Input())


def test_internal_values_enforce_same_collection_and_layer_contract() -> None:
    for invalid in ((" ",) * 7, (1,)):
        with pytest.raises((TypeError, ValueError)):
            NormalizationPatch(allowed_whitespace=cast(tuple[str, ...], invalid))
    result = compose(capture({}))
    with pytest.raises(ValueError):
        replace(result, sources=(result.sources[1],))
    with pytest.raises(ValueError):
        replace(result, sources=result.sources * 2)
    with pytest.raises(TypeError):
        replace(result, sources=cast(tuple[CapturedCandidate, ...], (None,)))
    with pytest.raises(TypeError):
        compose(cast(CapturedCandidate, {}))
