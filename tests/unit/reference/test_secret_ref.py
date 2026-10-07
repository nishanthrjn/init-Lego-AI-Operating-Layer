"""SECRET-REF-1A requirements: deterministic acceptance/invalidation ordering."""

import json
import sqlite3
import traceback
from dataclasses import asdict, replace
from datetime import timedelta
from threading import Event, Thread
from unittest.mock import patch

import pytest

from legoai.governance.ports import SecretAccessPort
from legoai.governance.secret import SecretRef, SourceDutyState, SourceEvent
from legoai.governance.values import Principal
from legoai.kernel.identity import PrincipalId, TenantId
from legoai.kernel.references import PrincipalRef
from legoai.reference import _durable_evidence, _secret_ledger, secret
from legoai.reference._custody_sqlite import _commit, _StorageGap
from legoai.reference._durable_evidence import _ReceiptWitness
from legoai.reference._secret_domain import _OrderingDomain
from legoai.runtime._composition.secret import _SyntheticSecretAccess
from tests.support.secret_ref_scenario import scenario


def count(s):
    return s._approvals.current_use_state(s._request.context.approval).uses_recorded


def mutate(s, kind):
    p = s._request.plan
    if kind == "grant":
        s._authorization.grant_state.revoke(p.grant_id)
    elif kind == "policy":
        s._authorization.policy_currency.supersede(p.policy)
    elif kind == "catalog":
        e = s._entry
        s._catalog.withdraw(e.plugin_id, e.release, e.offer, e.tenant_context)
    elif kind == "mapping":
        s._state.invalidate_mapping()
    elif kind == "revision":
        s._state.invalidate_revision()
    elif kind == "cancel":
        s._state.cancel()
    elif kind == "expiry":
        s._clock.advance(p.expires_at)
    elif kind == "approval":
        s._approvals.consume(s._request.context.approval)
    else:
        raise AssertionError(kind)


def test_reference_only_operations(tmp_path):
    with scenario(tmp_path) as s:
        port: SecretAccessPort = s
        r = s._request
        assert port.resolve_secret_reference(r) == r.reference
        assert port.validate_secret_revision(r) == r.reference
        assert port.authorize_secret_use(r).considered_grant == r.plan.grant_id
        assert count(s) == 0
        with pytest.raises(PermissionError):
            port.record_secret_use(r)
        assert s._state._material is None
        assert not any(
            hasattr(port, n)
            for n in ("get_secret", "resolve_token", "raw_material", "credential_value")
        )


@pytest.mark.parametrize(
    "kind",
    [
        "grant",
        "policy",
        "catalog",
        "mapping",
        "revision",
        "cancel",
        "expiry",
        "approval",
    ],
)
@pytest.mark.parametrize("before", [True, False])
def test_invalidator_ordering(tmp_path, kind, before):
    with scenario(tmp_path) as s:
        # Mutation commits in another thread at the pre-use receipt seam. Events
        # make this deterministic; no polling/sleep and no production hook.
        ready, done = Event(), Event()
        errors = []

        def invalidator():
            try:
                assert ready.wait(5)
                mutate(s, kind)
            except BaseException as e:
                errors.append(e)
            finally:
                done.set()

        thread = Thread(target=invalidator)
        thread.start()
        original = s._custody.witness

        def witness(*args):
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
                    assert count(s) == (1 if kind == "approval" else 0)
                    assert s._inspect(s._request).accepted_fact is None
                else:
                    fact = s._accept(s._request)
                    ready.set()
                    assert done.wait(5)
                    # exhausted Approval mutation refuses instead of overusing
                    if kind == "approval":
                        assert len(errors) == 1 and isinstance(
                            errors.pop(), PermissionError
                        )
                    assert s._inspect(s._request).accepted_fact == fact
                    assert count(s) == 1
            assert not errors
            assert s._state._material is None
            with pytest.raises(PermissionError):
                s._accept(s._request)
        finally:
            ready.set()
            thread.join(5)
            assert not thread.is_alive()


def test_expired_before_authorization_and_boundary(tmp_path):
    with scenario(tmp_path) as s:
        s._clock.advance(s._request.plan.expires_at)
        with pytest.raises(PermissionError):
            s.authorize_secret_use(s._request)
        with pytest.raises(PermissionError):
            s._accept(s._request)
        assert count(s) == 0
        assert s._inspect(s._request) is None


def test_last_clock_tick_before_acceptance(tmp_path):
    with scenario(tmp_path) as s:
        s._clock.advance(s._request.plan.expires_at - timedelta(microseconds=1))
        fact = s._accept(s._request)
        s._clock.advance(s._request.plan.expires_at)
        assert s._inspect(s._request).accepted_fact == fact


@pytest.mark.parametrize(
    "field",
    [
        "requester",
        "actor",
        "purpose",
        "consumer",
        "consumer_version",
        "target_mapping",
        "configuration",
        "secret",
        "grant_id",
        "policy",
        "approval_id",
        "operation_id",
    ],
)
def test_exact_use_mismatch(tmp_path, field):
    with scenario(tmp_path) as s:
        p = s._request.plan
        old = getattr(p, field)
        if field in ("requester", "actor"):
            value = Principal(PrincipalRef("identity", PrincipalId("other")))
        elif isinstance(old, str):
            value = "other"
        elif field == "consumer_version":
            value = replace(old, patch=old.patch + 1)
        elif field == "configuration":
            value = replace(old, revision="other")
        elif field == "secret":
            value = replace(old, revision="other")
        elif field == "policy":
            value = replace(old, policy_id="other")
        else:
            value = replace(old, value="other")
        p = replace(p, **{field: value})
        r = replace(
            s._request, plan=p, reference=replace(s._request.reference, exact=p.secret)
        )
        with pytest.raises(PermissionError):
            s._accept(r)
        assert count(s) == 0
        assert s._inspect(s._request) is None
        # A wrong caller cannot burn another admitted use.
        assert s._accept(s._request).event is SourceEvent.ACCEPTED


def test_wrong_tenant_and_missing_authority(tmp_path):
    with scenario(tmp_path) as s:
        for context in (
            replace(s._request.context, grant=None),
            replace(s._request.context, resource_scope="other"),
        ):
            with pytest.raises(PermissionError):
                s.resolve_secret_reference(replace(s._request, context=context))
        p = s._request.plan
        scope = replace(p.secret.scope, tenant_id=TenantId("other"))
        app = replace(p.configuration.configuration.application, scope=scope)
        config = replace(
            p.configuration,
            configuration=replace(p.configuration.configuration, application=app),
        )
        p = replace(p, secret=replace(p.secret, scope=scope), configuration=config)
        r = replace(
            s._request, plan=p, reference=replace(s._request.reference, exact=p.secret)
        )
        with pytest.raises(PermissionError):
            s._accept(r)
        assert count(s) == 0


@pytest.mark.parametrize(
    "participant",
    ["grants", "policies", "approvals", "catalog", "source", "custody", "clock"],
)
def test_shared_domain_identity(tmp_path, participant):
    with scenario(tmp_path) as s:
        args = dict(
            request=s._request,
            entry=s._entry,
            domain=s._domain,
            grants=s._authorization.grant_state,
            policies=s._authorization.policy_currency,
            approvals=s._approvals,
            catalog=s._catalog,
            source=s._source,
            custody=s._custody,
            clock=s._clock,
        )
        owner = args[participant]
        with patch.object(owner, "_domain", _OrderingDomain()):
            with pytest.raises(ValueError, match="shared ordering"):
                _SyntheticSecretAccess(**args)


def test_competing_exact_uses_and_foreign_thread_fail_closed(tmp_path):
    with scenario(tmp_path) as s:
        ready, done = Event(), Event()
        errors = []

        def competitor():
            assert ready.wait(5)
            try:
                s._accept(s._request)
            except PermissionError:
                errors.append("denied")
            finally:
                done.set()

        thread = Thread(target=competitor)
        thread.start()
        ready.set()
        fact = s._accept(s._request)
        assert done.wait(5)
        thread.join(5)
        assert errors == ["denied"]
        with pytest.raises(PermissionError):
            s._accept(s._request)
        assert count(s) == 1 and s._inspect(s._request).accepted_fact == fact


def test_pre_use_custody_failure(tmp_path):
    with scenario(tmp_path) as s:
        with patch.object(
            s._custody, "acknowledge", side_effect=_StorageGap("custody unavailable")
        ):
            with pytest.raises(_StorageGap):
                s._accept(s._request)
        assert count(s) == 0
        assert s._inspect(s._request).accepted_fact is None
        assert s._state._material is None
        with pytest.raises(PermissionError):
            s._accept(s._request)


@pytest.mark.parametrize("wrong", ["public", "domain", "subject"])
def test_wrong_pre_use_receipt(tmp_path, wrong):
    with scenario(tmp_path) as s:
        original = s._custody.witness

        def corrupt(*args):
            w = original(*args)
            if wrong == "public":
                return w.receipt
            if wrong == "domain":
                return _ReceiptWitness(w.receipt, _OrderingDomain())
            fact = replace(
                w.receipt.evidence.fact,
                plan=replace(w.receipt.evidence.fact.plan, purpose="other"),
            )
            return _ReceiptWitness(
                replace(w.receipt, evidence=replace(w.receipt.evidence, fact=fact)),
                s._domain,
            )

        with patch.object(s._custody, "witness", corrupt):
            with pytest.raises(PermissionError):
                s._accept(s._request)
        assert count(s) == 0
        assert s._inspect(s._request).accepted_fact is None


def test_post_use_failure_repair_no_repeat_no_refund(tmp_path):
    with scenario(tmp_path) as s:
        fact = s._accept(s._request)
        with patch.object(
            s._custody, "acknowledge", side_effect=_StorageGap("custody unavailable")
        ):
            with pytest.raises(_StorageGap):
                s.record_secret_use(s._request)
        status = s._inspect(s._request)
        assert status.accepted_fact == fact and status.duty is SourceDutyState.PENDING
        assert count(s) == 1
        s._state.cancel()
        s._authorization.grant_state.revoke(s._request.plan.grant_id)
        with patch.object(
            s._source, "accept", side_effect=AssertionError("repair repeated use")
        ):
            repaired = s.record_secret_use(s._request)
            assert repaired.duty is SourceDutyState.SATISFIED
            assert s.record_secret_use(s._request) == repaired
        assert count(s) == 1


def test_lost_acknowledgment_and_restart(tmp_path):
    with scenario(tmp_path) as s:

        def lost(conn):
            _commit(conn)
            raise sqlite3.OperationalError("lost acknowledgment")

        original = s._source.accept

        def accept(*args, **kwargs):
            with patch.object(_secret_ledger, "_commit", lost):
                return original(*args, **kwargs)

        with patch.object(s._source, "accept", accept):
            with pytest.raises(_StorageGap):
                s._accept(s._request)
        fact = s._inspect(s._request).accepted_fact
        assert fact is not None and count(s) == 1
        with pytest.raises(PermissionError):
            s._accept(s._request)
    with scenario(tmp_path, reopen=True) as s:
        assert s._inspect(s._request).accepted_fact == fact
        assert not s._source._new_work
        assert s._state._material is None and not s._source._live
        with pytest.raises(PermissionError):
            s.authorize_secret_use(s._request)
        with pytest.raises(PermissionError):
            s._accept(s._request)
        assert count(s) == 0  # new registry is empty, not restored/refunded from DB
        with patch.object(s._source, "accept", side_effect=AssertionError("replay")):
            assert s.record_secret_use(s._request).duty is SourceDutyState.SATISFIED
        assert s._inspect(s._request).approval.value == "consumed"


def test_failed_commit_keeps_approval_consumed(tmp_path):
    with scenario(tmp_path) as s:
        original = s._source.accept

        def fail(*args, **kwargs):
            with patch.object(
                _secret_ledger,
                "_commit",
                side_effect=sqlite3.OperationalError("commit unavailable"),
            ):
                return original(*args, **kwargs)

        with patch.object(s._source, "accept", fail):
            with pytest.raises(_StorageGap):
                s._accept(s._request)
        assert count(s) == 1 and s._inspect(s._request).accepted_fact is None
        with pytest.raises(PermissionError):
            s._accept(s._request)


def test_canary_non_leakage(tmp_path, caplog, capsys):
    canary = b"STAGE_A_PRIVATE_MATERIAL_CANARY_9182"
    sql = []
    with scenario(tmp_path) as s:
        s._source._conn.set_trace_callback(sql.append)
        s._custody._conn.set_trace_callback(sql.append)
        with patch.object(secret, "token_bytes", return_value=canary):
            fact = s._accept(s._request)
        status = s.record_secret_use(s._request)
        with pytest.raises(PermissionError) as exc:
            s._accept(s._request)
        report = json.dumps(asdict(status), default=str)
        values = [
            repr(s),
            repr(s._state),
            repr(s._request),
            repr(fact),
            report,
            repr(asdict(s._request.plan.configuration)),
            "".join(traceback.format_exception(exc.value)),
            caplog.text,
            repr(capsys.readouterr()),
            "".join(sql),
        ]
        assert s._state._material is None
        assert all(canary.decode() not in value for value in values)
        # Inspect live databases, rollback journals (if present), and writer files.
        for path in tmp_path.iterdir():
            if path.is_file():
                assert canary not in path.read_bytes()
    for path in tmp_path.iterdir():
        if path.is_file():
            assert canary not in path.read_bytes()


@pytest.mark.parametrize("bad", [None, "current", {}, 42])
def test_secret_ref_exact_invariants(bad):
    with pytest.raises(TypeError):
        SecretRef(bad, "synthetic", "purpose")


def test_no_alias_or_environment_interpretation(tmp_path):
    with scenario(tmp_path) as s:
        for revision in ("current", "latest", "alias", "$API_KEY"):
            exact = replace(s._request.plan.secret, revision=revision)
            request = replace(
                s._request,
                reference=replace(s._request.reference, exact=exact),
                plan=replace(s._request.plan, secret=exact),
            )
            with pytest.raises(PermissionError):
                s.resolve_secret_reference(request)


@pytest.mark.parametrize(
    "kind",
    [
        "grant",
        "policy",
        "catalog",
        "mapping",
        "revision",
        "cancel",
        "expiry",
        "approval",
    ],
)
def test_mutation_waiting_at_source_commit(tmp_path, kind):
    from contextlib import contextmanager

    with scenario(tmp_path) as s:
        ready, attempting, done = Event(), Event(), Event()
        original_enter = s._domain.enter

        @contextmanager
        def enter():
            if ready.is_set():
                attempting.set()
            with original_enter():
                yield

        errors = []

        def invalidate():
            assert ready.wait(5)
            try:
                mutate(s, kind)
            except PermissionError as e:
                errors.append(e)
            finally:
                done.set()

        thread = Thread(target=invalidate)
        thread.start()
        original_accept = s._source.accept

        def commit(conn):
            s._domain.held()
            ready.set()
            assert attempting.wait(5)
            assert not done.is_set()
            _commit(conn)

        def accept(*args, **kwargs):
            with (
                patch.object(s._domain, "enter", enter),
                patch.object(_secret_ledger, "_commit", commit),
            ):
                return original_accept(*args, **kwargs)

        try:
            with patch.object(s._source, "accept", accept):
                fact = s._accept(s._request)
            assert done.wait(5)
            assert len(errors) == (1 if kind == "approval" else 0)
            assert count(s) == 1
            assert s._inspect(s._request).accepted_fact == fact
        finally:
            ready.set()
            thread.join(5)
            assert not thread.is_alive()


@pytest.mark.parametrize("invalidation", ["mapping", "revision", "cancel", "accepted"])
def test_second_composition_cannot_reuse_slot(tmp_path, invalidation):
    with scenario(tmp_path) as s:
        if invalidation == "accepted":
            s._accept(s._request)
        else:
            mutate(s, invalidation)
        with pytest.raises(PermissionError, match="binding already established"):
            _SyntheticSecretAccess(
                s._request,
                s._entry,
                s._domain,
                s._authorization.grant_state,
                s._authorization.policy_currency,
                s._approvals,
                s._catalog,
                s._source,
                s._custody,
                s._clock,
            )
        assert count(s) == (1 if invalidation == "accepted" else 0)


def test_public_approval_mutation_cannot_bypass_gate(tmp_path):
    with scenario(tmp_path) as s:
        with pytest.raises(RuntimeError):
            s._approvals._consume(s._request.context.approval)
        with s._domain.enter():
            for mutation in (
                lambda: s._approvals.consume(s._request.context.approval),
                lambda: s._authorization.grant_state.revoke(s._request.plan.grant_id),
                lambda: s._authorization.policy_currency.supersede(
                    s._request.plan.policy
                ),
                lambda: s._catalog.publish(
                    None, None, None, established_at=s._request.plan.prepared_at
                ),
                s._state.cancel,
                s._state.invalidate_mapping,
                s._state.invalidate_revision,
                lambda: s._catalog.withdraw(
                    s._entry.plugin_id,
                    s._entry.release,
                    s._entry.offer,
                    s._entry.tenant_context,
                ),
            ):
                with pytest.raises(RuntimeError):
                    mutation()
        assert count(s) == 0
        assert s._accept(s._request).event is SourceEvent.ACCEPTED


def test_canary_absent_during_rollback_journal_commit(tmp_path):
    canary = b"STAGE_A_PRIVATE_MATERIAL_CANARY_9182"
    observations = []
    with scenario(tmp_path) as s:

        def inspect_commit(conn):
            files = [p for p in tmp_path.iterdir() if p.is_file()]
            observations.extend(p.name for p in files if p.name.endswith("-journal"))
            assert all(canary not in p.read_bytes() for p in files)
            _commit(conn)

        with (
            patch.object(secret, "token_bytes", return_value=canary),
            patch.object(_secret_ledger, "_commit", inspect_commit),
            patch.object(_durable_evidence, "_commit", inspect_commit),
        ):
            s._accept(s._request)
            s.record_secret_use(s._request)
        assert "source.db-journal" in observations
        assert "evidence.db-journal" in observations


def test_optional_approval_and_strict_public_request(tmp_path):
    with scenario(tmp_path, with_approval=False) as service:
        request = service._request

        class EqualitySpoof:
            def __eq__(self, other):
                return True

        with pytest.raises(PermissionError):
            service._accept(EqualitySpoof())
        assert service._accept(request).plan.approval_id is None
        assert service.record_secret_use(request).approval.value == "not_applicable"


def test_approval_failure_discards_material_before_error_leaves_boundary(tmp_path):
    with scenario(tmp_path) as s:
        with patch.object(
            s._approvals, "_consume", side_effect=PermissionError("owner refusal")
        ):
            with pytest.raises(PermissionError) as error:
                s._accept(s._request)
        assert s._state._material is None
        assert count(s) == 0
        assert s._inspect(s._request).accepted_fact is None
        trace = error.value.__traceback__
        while trace is not None:
            if trace.tb_frame.f_code.co_name == "_accept":
                assert "material" not in trace.tb_frame.f_locals
            trace = trace.tb_next
        with pytest.raises(PermissionError):
            s._accept(s._request)
