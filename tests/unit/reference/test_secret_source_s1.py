"""SECRET-SOURCE-S1: operator-provisioned immutable process-local material.

The canary is synthetic test data injected by trusted test code into the
protected source. Material may reach only the existing exact-use acceptance
(the Stage-A source ledger); every other surface is scanned for the canary.
No network, provider, transport or credential is used.
"""

import dataclasses
import logging
import os
import traceback
from collections.abc import Iterator
from dataclasses import replace
from pathlib import Path
from threading import Event, Thread
from typing import Any
from unittest.mock import patch

import pytest

from legoai.governance.ports import SecretAccessRequest
from legoai.governance.secret import (
    SecretRef,
    SecretRevisionRef,
    SourceEvent,
    UseRecoveryCategory,
)
from legoai.kernel.identity import TenantId
from legoai.kernel.references import ReferenceScope
from legoai.reference._secret_domain import _OrderingDomain
from legoai.reference._secret_ledger import _SecretLedger
from legoai.reference.secret import _ProvisionedSecretSource
from legoai.runtime._composition.secret import _provision_interactively
from tests.support.secret_ref_scenario import scenario

CANARY = "kisski-secret-CANARY-DO-NOT-LEAK-938427"
REPLACEMENT = "replacement-CANARY-DO-NOT-LEAK-551203"
SCOPE = ReferenceScope("secret-owner", TenantId("tenant"))


def source() -> _ProvisionedSecretSource:
    return _ProvisionedSecretSource(_OrderingDomain(), SCOPE)


def leaks(*values: object) -> bool:
    """Recursive scan of safe values, errors and their causal chains."""
    seen: set[int] = set()

    def text(value: object) -> Iterator[str]:
        if id(value) in seen:
            return
        seen.add(id(value))
        if isinstance(value, BaseException):
            yield from traceback.format_exception(value)
            for chained in (value.__cause__, value.__context__):
                if chained is not None:
                    yield from text(chained)
            return
        yield repr(value)
        yield str(value)
        if isinstance(value, (bytes, bytearray)):
            yield bytes(value).decode("latin-1")
        elif isinstance(value, (tuple, list, set, frozenset)):
            for item in value:
                yield from text(item)
        elif isinstance(value, dict):
            for key, item in value.items():
                yield from text(key)
                yield from text(item)
        elif dataclasses.is_dataclass(value) and not isinstance(value, type):
            for field in dataclasses.fields(value):
                yield from text(getattr(value, field.name))

    return any(
        canary in piece
        for value in values
        for piece in text(value)
        for canary in (CANARY, REPLACEMENT)
    )


def files_leak(directory: Path) -> bool:
    return any(
        CANARY.encode() in path.read_bytes()
        or REPLACEMENT.encode() in path.read_bytes()
        for path in directory.rglob("*")
        if path.is_file()
    )


class Spy:
    """Captures the material the protected realization hands to acceptance."""

    def __init__(self) -> None:
        self.seen: list[bytes] = []
        self.original = _SecretLedger.accept

    def __enter__(self) -> Spy:
        spy = self

        def accept(ledger: _SecretLedger, *args: Any, **kwargs: Any) -> Any:
            spy.seen.append(kwargs["material"])
            return spy.original(ledger, *args, **kwargs)

        self.patch = patch.object(_SecretLedger, "accept", accept)
        self.patch.start()
        return self

    def __exit__(self, *exc: object) -> None:
        self.patch.stop()


def mutate(s: Any, kind: str) -> None:
    """Existing local invalidators of the Stage-A owners (typed subset)."""
    p = s._request.plan
    if kind == "grant":
        s._authorization.grant_state.revoke(p.grant_id)
    elif kind == "policy":
        s._authorization.policy_currency.supersede(p.policy)
    elif kind == "catalog":
        e = s._entry
        s._catalog.withdraw(e.plugin_id, e.release, e.offer, e.tenant_context)
    elif kind == "revision":
        s._state.invalidate_revision()
    elif kind == "cancel":
        s._state.cancel()
    else:
        raise AssertionError(kind)


def material_source(s: Any) -> _ProvisionedSecretSource:
    source = s._state._source
    assert type(source) is _ProvisionedSecretSource
    return source


# Provisioning


def test_provisioning_returns_only_a_reference() -> None:
    src = source()
    ref = src.provision("bearer-key", "remote-model-bearer", "model-adapter", CANARY)
    assert type(ref) is SecretRef
    assert ref.secret_class == "operator-provisioned"
    assert ref.use_requirement == "remote-model-bearer"
    assert ref.exact.identity == "bearer-key" and ref.exact.scope == SCOPE
    assert ref.exact.revision.startswith("s1-")
    assert src.status(ref.exact) is True
    assert not leaks(ref, ref.exact, src, str(src))
    # No public plaintext retrieval exists.
    public = {n for n in dir(src) if not n.startswith("_")}
    assert public == {"provision", "retire", "close", "status"}
    for name in ("reveal", "value", "token", "get_secret", "material", "secret"):
        assert not hasattr(src, name)


@pytest.mark.parametrize(
    ("material", "error"),
    [
        ("", ValueError),
        ("x" * 4097, ValueError),
        ("   ", ValueError),
        (" leading-space", ValueError),
        ("tab\tinside", ValueError),
        ("line\nbreak", ValueError),
        ("nul\x00", ValueError),
        ("café-key", ValueError),
        (CANARY.encode(), TypeError),
        (None, TypeError),
        (1234, TypeError),
    ],
    ids=[
        "empty",
        "oversized",
        "whitespace",
        "leading-space",
        "tab",
        "newline",
        "nul",
        "non-ascii",
        "bytes",
        "none",
        "int",
    ],
)
def test_invalid_material_is_rejected_without_echo(
    material: object, error: type
) -> None:
    src = source()
    with pytest.raises(error) as raised:
        src.provision("bearer-key", "purpose", "consumer", material)
    assert not leaks(raised.value)
    if isinstance(material, str) and len(material.strip()) >= 4:
        assert material not in "".join(traceback.format_exception(raised.value))


def test_bounds_admit_ordinary_bearer_keys() -> None:
    src = source()
    for value in ("a", "x" * 4096, "sk-" + "A1b2" * 12, "eyJhbGciOi.J9-_~+/=="):
        assert src.provision("id-" + str(len(value)), "p", "c", value).exact.revision


def test_replacement_is_a_new_revision_and_retires_the_old() -> None:
    src = source()
    first = src.provision("bearer-key", "purpose", "consumer", CANARY)
    second = src.provision("bearer-key", "purpose", "consumer", REPLACEMENT)
    assert first.exact.identity == second.exact.identity
    assert first.exact.revision != second.exact.revision
    assert first.exact.mapping_revision != second.exact.mapping_revision
    assert src.status(first.exact) is False and src.status(second.exact) is True
    # The old revision's buffer was overwritten, never rebound to new bytes.
    old = src._revisions[first.exact]
    assert bytes(old.material) == bytes(len(CANARY))
    assert old.reference == first


def test_other_identities_are_independent() -> None:
    src = source()
    a = src.provision("key-a", "purpose", "consumer", CANARY)
    b = src.provision("key-b", "purpose", "consumer", REPLACEMENT)
    assert src.status(a.exact) and src.status(b.exact)


# Protected realization through the existing exact-use mechanism


def test_authorized_exact_use_realizes_the_provisioned_revision(tmp_path: Path) -> None:
    with scenario(tmp_path, material=CANARY) as s, Spy() as spy:
        fact = s._accept(s._request)
        status = s.record_secret_use(s._request)
        assert fact.event is SourceEvent.ACCEPTED
        assert spy.seen == [CANARY.encode()]
        assert status.category is UseRecoveryCategory.ACCEPTED_ATTRIBUTED
        assert not leaks(fact, status, s._request, s._request.reference)
        assert s._state._material is None
    assert not files_leak(tmp_path)


def test_synthetic_stage_a_is_unchanged(tmp_path: Path) -> None:
    with scenario(tmp_path) as s, Spy() as spy:
        assert s._request.reference.secret_class == "synthetic"
        assert s._state._source is None
        s._accept(s._request)
        assert len(spy.seen) == 1 and len(spy.seen[0]) == 32


@pytest.mark.parametrize("change", ["retire", "close", "replace"])
def test_ineligible_revision_never_yields_material(tmp_path: Path, change: str) -> None:
    with scenario(tmp_path, material=CANARY) as s, Spy() as spy:
        src = material_source(s)
        if change == "retire":
            src.retire(s._request.plan.secret)
        elif change == "close":
            src.close()
        else:
            src.provision(
                s._request.plan.secret.identity,
                s._request.plan.purpose,
                s._request.plan.consumer,
                REPLACEMENT,
            )
        with pytest.raises(PermissionError) as raised:
            s._accept(s._request)
        assert spy.seen == []
        assert not leaks(raised.value)
        # Refused at current authorization, before the use is even prepared.
        assert s._inspect(s._request) is None
    assert not files_leak(tmp_path)


def test_closed_source_refuses_new_provisioning() -> None:
    src = source()
    src.close()
    with pytest.raises(PermissionError) as raised:
        src.provision("bearer-key", "purpose", "consumer", CANARY)
    assert not leaks(raised.value)


@pytest.mark.parametrize("kind", ["grant", "policy", "catalog", "revision", "cancel"])
def test_unauthorized_use_never_receives_material(tmp_path: Path, kind: str) -> None:
    with scenario(tmp_path, material=CANARY) as s, Spy() as spy:
        mutate(s, kind)
        with pytest.raises(PermissionError) as raised:
            s._accept(s._request)
        assert spy.seen == []
        assert not leaks(raised.value)


def _request(s: Any, **changes: Any) -> SecretAccessRequest:
    plan = replace(s._request.plan, **changes.pop("plan", {}))
    reference = changes.pop(
        "reference", SecretRef(plan.secret, "operator-provisioned", plan.purpose)
    )
    return SecretAccessRequest(reference, plan, s._request.context)


def test_wrong_reference_purpose_or_consumer_is_ineligible(tmp_path: Path) -> None:
    with scenario(tmp_path, material=CANARY) as s:
        src = material_source(s)
        p = s._request.plan
        unknown = SecretRevisionRef(SCOPE, p.secret.identity, "s1-unknown", "s1-map-x")
        cases = [
            _request(s, plan={"secret": unknown}),
            _request(
                s,
                reference=SecretRef(p.secret, "operator-provisioned", "other-purpose"),
            ),
            _request(s, reference=SecretRef(p.secret, "synthetic", p.purpose)),
            _request(s, plan={"consumer": "other-consumer"}),
        ]
        with s._domain.enter():
            assert src._eligible(s._request)
            for request in cases:
                assert not src._eligible(request)
                with pytest.raises(PermissionError) as raised:
                    src._realize(request)
                assert not leaks(raised.value)


def test_wrong_class_or_foreign_domain_is_rejected_at_composition() -> None:
    from legoai.runtime._composition.secret import _SyntheticSecretAccess

    with pytest.raises(ValueError):
        _SyntheticSecretAccess(
            None,  # type: ignore[arg-type]
            None,  # type: ignore[arg-type]
            None,  # type: ignore[arg-type]
            None,  # type: ignore[arg-type]
            None,  # type: ignore[arg-type]
            None,  # type: ignore[arg-type]
            None,  # type: ignore[arg-type]
            None,  # type: ignore[arg-type]
            None,  # type: ignore[arg-type]
            None,  # type: ignore[arg-type]
            material_source=_ProvisionedSecretSource(_OrderingDomain(), SCOPE),
        )


@pytest.mark.parametrize("change", ["retire", "close"])
@pytest.mark.parametrize("before", [True, False])
def test_retirement_and_close_are_ordered_against_use(
    tmp_path: Path, change: str, before: bool
) -> None:
    with scenario(tmp_path, material=CANARY) as s, Spy() as spy:
        src = material_source(s)
        ready, done = Event(), Event()
        errors: list[BaseException] = []

        def invalidator() -> None:
            try:
                assert ready.wait(5)
                if change == "retire":
                    src.retire(s._request.plan.secret)
                else:
                    src.close()
            except BaseException as error:
                errors.append(error)
            finally:
                done.set()

        thread = Thread(target=invalidator)
        thread.start()
        original = s._custody.witness

        def witness(*args: Any) -> Any:
            result = original(*args)
            if before:
                ready.set()
                assert done.wait(5)
            return result

        try:
            with patch.object(s._custody, "witness", witness):
                if before:
                    with pytest.raises(PermissionError):
                        s._accept(s._request)
                    assert spy.seen == []
                else:
                    fact = s._accept(s._request)
                    ready.set()
                    assert done.wait(5)
                    assert fact.event is SourceEvent.ACCEPTED
                    assert spy.seen == [CANARY.encode()]
                    # Later invalidation cannot retract an accepted use.
                    inspected = s._inspect(s._request)
                    assert inspected is not None
                    assert inspected.accepted_fact == fact
        finally:
            ready.set()
            thread.join(5)
        assert not errors
        assert src.status(s._request.plan.secret) is False


def test_close_preserves_historical_attribution(tmp_path: Path) -> None:
    with scenario(tmp_path, material=CANARY) as s:
        fact = s._accept(s._request)
        attributed = s.record_secret_use(s._request)
        material_source(s).close()
        status = s._inspect(s._request)
        assert status is not None
        assert status.accepted_fact == fact
        assert status.category is attributed.category
        assert not leaks(status)
    assert not files_leak(tmp_path)


# Leak containment, persistence, environment


def test_no_material_in_logs(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.DEBUG)
    with scenario(tmp_path, material=CANARY) as s:
        s._accept(s._request)
        s.record_secret_use(s._request)
        material_source(s).close()
    assert CANARY not in caplog.text


def test_no_ambient_environment_source(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    for name in ("KISSKI_API_KEY", "OPENAI_API_KEY", "LEGOAI_TOKEN"):
        monkeypatch.setenv(name, REPLACEMENT)
    with scenario(tmp_path, material=CANARY) as s, Spy() as spy:
        s._accept(s._request)
    # Only the operator-provisioned bytes are used; the environment is ignored.
    assert spy.seen == [CANARY.encode()]
    assert os.environ["KISSKI_API_KEY"] == REPLACEMENT


def test_provisioning_creates_no_files(tmp_path: Path) -> None:
    before = set(tmp_path.rglob("*"))
    src = _ProvisionedSecretSource(_OrderingDomain(), SCOPE)
    src.provision("bearer-key", "purpose", "consumer", CANARY)
    src.close()
    assert set(tmp_path.rglob("*")) == before


def test_close_overwrites_owned_buffers_best_effort() -> None:
    src = source()
    ref = src.provision("bearer-key", "purpose", "consumer", CANARY)
    src.close()
    assert bytes(src._revisions[ref.exact].material) == bytes(len(CANARY))
    assert src.status(ref.exact) is False
    assert not leaks(src, repr(src._revisions[ref.exact]))


# Hidden interactive bootstrap


def test_hidden_input_provisions_directly_into_the_source() -> None:
    src = source()
    prompts: list[str] = []

    def read(prompt: str) -> str:
        prompts.append(prompt)
        return CANARY

    ref = _provision_interactively(
        src, "bearer-key", "purpose", "consumer", read=read, interactive=lambda: True
    )
    assert type(ref) is SecretRef and src.status(ref.exact)
    assert prompts and CANARY not in prompts[0]
    assert not leaks(ref)


def test_hidden_input_refuses_without_an_interactive_terminal() -> None:
    src = source()
    calls: list[str] = []

    def read(prompt: str) -> str:
        calls.append(prompt)
        return CANARY

    with pytest.raises(PermissionError):
        _provision_interactively(
            src,
            "bearer-key",
            "purpose",
            "consumer",
            read=read,
            interactive=lambda: False,
        )
    assert calls == []
    # The default check uses the real stdin, which pytest does not attach to
    # a terminal: refused before any read.
    with pytest.raises(PermissionError):
        _provision_interactively(
            src, "bearer-key", "purpose", "consumer", read=lambda p: CANARY
        )


def test_hidden_input_rejection_does_not_echo() -> None:
    with pytest.raises(ValueError) as raised:
        _provision_interactively(
            source(),
            "bearer-key",
            "purpose",
            "consumer",
            read=lambda prompt: CANARY + " with space",
            interactive=lambda: True,
        )
    assert not leaks(raised.value)
