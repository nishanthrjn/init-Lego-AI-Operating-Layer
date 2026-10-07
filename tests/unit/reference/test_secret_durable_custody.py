"""Contract, corruption, crash and disclosure tests for the durable prerequisite."""

import os
import sqlite3
import subprocess
import sys
from dataclasses import fields, replace

import pytest

from legoai.governance.secret import (
    ApprovalObservation,
    SecretUseFact,
    SecretUseId,
    SourceDutyState,
    SourceEvent,
    UseRecoveryCategory,
)
from legoai.governance.values import Principal
from legoai.kernel.identity import PrincipalId, RequestId, TenantId
from legoai.kernel.references import PrincipalRef, ReferenceScope
from legoai.reference import _custody_codec, _durable_evidence, _secret_ledger
from legoai.reference._custody_sqlite import _Conflict, _ScopeDenied, _StorageGap
from legoai.reference._durable_evidence import _EvidenceStore
from legoai.reference._secret_domain import _OrderingDomain
from legoai.reference._secret_ledger import _inspect_source, _SecretLedger
from tests.support.custody_scenario import NOW, access, evidence, plan


@pytest.fixture
def stores(tmp_path):
    s, e = tmp_path / "source.db", tmp_path / "evidence.db"
    _SecretLedger.provision(s)
    _EvidenceStore.provision(e)
    d = _OrderingDomain()
    source, custody = _SecretLedger(s, access(), d), _EvidenceStore(e, access(), d)
    try:
        yield source, custody, d
    finally:
        source.close()
        custody.close()


def prepare(source, custody):
    p, a = plan(), access()
    source.prepare(p, a)
    fact = SecretUseFact(p, SourceEvent.PREPARED, NOW)
    receipt = custody.acknowledge(evidence(fact), a, recorded_at=NOW)
    return custody.witness(p.pre_submission, a), receipt


def accept(source, custody, domain, *, material=None):
    witness, _ = prepare(source, custody)
    value = os.urandom(32) if material is None else material
    with domain.enter():
        return source.accept(
            plan(),
            witness,
            access(),
            material=value,
            expected_material=value,
            now=NOW,
            approval=ApprovalObservation.CONSUMED,
        )


def test_source_atomic_acceptance(stores):
    source, custody, domain = stores
    fact = accept(*stores)
    status = source.status(plan().use_id, access())
    assert status.category is UseRecoveryCategory.ACCEPTED_ATTRIBUTION_OUTSTANDING
    assert status.duty is SourceDutyState.PENDING
    assert status.approval is ApprovalObservation.CONSUMED
    assert status.revision == 2
    assert status.accepted_fact == fact
    # Duplicate is retained truth; it must not validate a fresh material value.
    witness = custody.witness(plan().pre_submission, access())
    with domain.enter():
        result = source.accept(
            plan(),
            witness,
            access(),
            material=b"",
            expected_material=b"",
            now=NOW,
            approval=ApprovalObservation.CONSUMED,
        )
    assert result == fact
    assert source._conn.execute("SELECT count(*) FROM accepted").fetchone() == (1,)


def test_receipt_and_repair(stores):
    source, custody, domain = stores
    fact = accept(*stores)
    receipt = custody.acknowledge(evidence(fact), access(), recorded_at=NOW)
    assert custody.acknowledge(evidence(fact), access(), recorded_at=NOW) == receipt
    witness = custody.witness(plan().post_submission, access())
    done = source.finish(plan().use_id, witness, access(), expected_revision=2)
    assert done.category is UseRecoveryCategory.ACCEPTED_ATTRIBUTED
    assert source.finish(plan().use_id, witness, access(), expected_revision=2) == done
    assert custody.submission_status(plan().post_submission, access()) == receipt
    with pytest.raises(_Conflict):
        source.intervene(
            plan().use_id, access(), expected_revision=3, disposition="must-not-erase"
        )


def test_prepared_intervention_and_no_replay(stores, tmp_path):
    source, custody, domain = stores
    prepare(source, custody)
    status = source.status(plan().use_id, access())
    assert status.category is UseRecoveryCategory.PREPARED_ONLY
    assert status.approval is ApprovalObservation.POSSIBLY_CONSUMED
    result = source.intervene(
        plan().use_id, access(), expected_revision=1, disposition="entitled-review-1"
    )
    assert result.category is UseRecoveryCategory.RECONCILED_REQUIRES_INTERVENTION
    recovered = _inspect_source(tmp_path / "source.db", access())
    assert recovered == (result,)


def test_source_duplicate_conflict(stores):
    source, custody, domain = stores
    first = source.prepare(plan(), access())
    assert source.prepare(plan(), access()) == first
    for changed in (
        replace(plan(), purpose="different"),
        replace(plan(), secret=replace(plan().secret, revision="2")),
        replace(plan(), consumer="different"),
    ):
        with pytest.raises(_Conflict):
            source.prepare(changed, access())


def test_evidence_conflict(stores):
    source, custody, domain = stores
    prepare(source, custody)
    other = SecretUseFact(
        replace(plan(), purpose="different"), SourceEvent.PREPARED, NOW
    )
    with pytest.raises(_Conflict):
        custody.acknowledge(evidence(other), access(), recorded_at=NOW)


@pytest.mark.parametrize("kind", ["tenant", "requester", "owner"])
def test_disclosure_scope(stores, kind):
    source, custody, domain = stores
    prepare(source, custody)
    a = access()
    if kind == "tenant":
        wrong = replace(a, scope=ReferenceScope(a.scope.owner, TenantId("other")))
    elif kind == "owner":
        wrong = replace(a, scope=ReferenceScope("other", a.scope.tenant_id))
    else:
        wrong = replace(
            a, requester=Principal(PrincipalRef("identity", PrincipalId("other")))
        )
    for operation in (
        lambda: source.status(plan().use_id, wrong),
        lambda: source.inspect(wrong),
        lambda: custody.submission_status(plan().pre_submission, wrong),
    ):
        with pytest.raises(_ScopeDenied, match="scope unavailable"):
            operation()
    assert source.status(SecretUseId("unknown"), a) is None
    assert custody.submission_status(RequestId("unknown"), a) is None


def test_preuse_refusal_and_domain(stores):
    source, custody, domain = stores
    source.prepare(plan(), access())
    with pytest.raises(_StorageGap):
        custody.witness(plan().pre_submission, access())
    with pytest.raises(RuntimeError):
        source.accept(
            plan(),
            None,
            access(),
            material=b"x",
            expected_material=b"x",
            now=NOW,
            approval=ApprovalObservation.CONSUMED,
        )
    with domain.enter():
        with pytest.raises(RuntimeError):
            custody.acknowledge(
                evidence(SecretUseFact(plan(), SourceEvent.PREPARED, NOW)),
                access(),
                recorded_at=NOW,
            )
        with pytest.raises(RuntimeError):
            with domain.enter():
                pass
    assert (
        source.status(plan().use_id, access()).category
        is UseRecoveryCategory.PREPARED_ONLY
    )


@pytest.mark.parametrize(
    "reason", ["expired", "material", "approval", "subject", "domain"]
)
def test_invalid_acceptance(stores, reason):
    source, custody, domain = stores
    witness, _ = prepare(source, custody)
    now, material, observation = NOW, b"x", ApprovalObservation.CONSUMED
    if reason == "expired":
        now = plan().expires_at
    if reason == "material":
        material = b"wrong"
    if reason == "approval":
        observation = ApprovalObservation.POSSIBLY_CONSUMED
    if reason == "domain":
        witness.domain = _OrderingDomain()
    if reason == "subject":
        witness.receipt = replace(
            witness.receipt,
            evidence=evidence(
                SecretUseFact(
                    replace(plan(), purpose="other"), SourceEvent.PREPARED, NOW
                )
            ),
        )
    with domain.enter(), pytest.raises((_ScopeDenied, ValueError)):
        source.accept(
            plan(),
            witness,
            access(),
            material=material,
            expected_material=b"x",
            now=now,
            approval=observation,
        )
    assert (
        source.status(plan().use_id, access()).category
        is UseRecoveryCategory.PREPARED_ONLY
    )


def test_matching_receipt_and_revision(stores):
    source, custody, domain = stores
    fact = accept(*stores)
    with pytest.raises(_Conflict):
        source.finish(
            plan().use_id,
            custody.witness(plan().pre_submission, access()),
            access(),
            expected_revision=2,
        )
    custody.acknowledge(evidence(fact), access(), recorded_at=NOW)
    with pytest.raises(_Conflict):
        source.finish(
            plan().use_id,
            custody.witness(plan().post_submission, access()),
            access(),
            expected_revision=1,
        )
    assert source.status(plan().use_id, access()).duty is SourceDutyState.PENDING


@pytest.mark.parametrize("store", [_SecretLedger, _EvidenceStore])
def test_storage_profile_and_one_writer(tmp_path, store):
    path = tmp_path / "owner.db"
    store.provision(path)
    first = store(path, access(), _OrderingDomain())
    try:
        assert first._conn.execute("PRAGMA synchronous").fetchone() == (3,)
        assert first._conn.execute("PRAGMA journal_mode").fetchone() == ("delete",)
        assert first._conn.execute("PRAGMA busy_timeout").fetchone() == (0,)
        assert first._conn.execute("PRAGMA foreign_keys").fetchone() == (1,)
        with pytest.raises(_StorageGap):
            store(path, access(), _OrderingDomain())
        with pytest.raises(FileExistsError):
            store.provision(path)
    finally:
        first.close()
    reopened = store(path, access(), _OrderingDomain())
    reopened.close()


@pytest.mark.parametrize(
    "damage",
    [
        "missing",
        "schema",
        "truncated",
        "integrity",
        "missing-duty",
        "unreadable",
        "missing-admission",
    ],
)
def test_corruption_is_gap(tmp_path, damage):
    path = tmp_path / "source.db"
    if damage == "missing":
        assert _inspect_source(path, access()) is UseRecoveryCategory.UNKNOWN_GAP
        assert not path.exists()
        return
    if damage == "unreadable":
        path.mkdir()
        assert _inspect_source(path, access()) is UseRecoveryCategory.UNKNOWN_GAP
        return
    _SecretLedger.provision(path)
    s = _SecretLedger(path, access(), _OrderingDomain())
    s.prepare(plan(), access())
    s.close()
    if damage == "truncated":
        path.write_bytes(b"not-a-database")
    elif damage == "missing-admission":
        path.with_suffix(".db.writer").unlink()
        with pytest.raises(_StorageGap):
            _SecretLedger(path, access(), _OrderingDomain())
        return
    else:
        with sqlite3.connect(path) as conn:
            if damage == "schema":
                conn.execute("UPDATE metadata SET version=99")
            elif damage == "missing-duty":
                conn.execute("DELETE FROM duties")
            else:
                conn.execute("UPDATE prepared SET plan='{}'")
    assert _inspect_source(path, access()) is UseRecoveryCategory.UNKNOWN_GAP
    with pytest.raises(_StorageGap):
        _SecretLedger(path, access(), _OrderingDomain())


def test_owners_separate(tmp_path):
    source = tmp_path / "source.db"
    custody = tmp_path / "evidence.db"
    _SecretLedger.provision(source)
    _EvidenceStore.provision(custody)
    with pytest.raises(_StorageGap):
        _EvidenceStore(source, access(), _OrderingDomain())
    with pytest.raises(_StorageGap):
        _SecretLedger(custody, access(), _OrderingDomain())
    with sqlite3.connect(source) as c:
        assert (
            c.execute(
                "SELECT name FROM sqlite_master WHERE name LIKE 'config_%'"
            ).fetchall()
            == []
        )


@pytest.mark.parametrize("store", [_SecretLedger, _EvidenceStore])
@pytest.mark.parametrize("changed", ["tenant", "owner", "requester"])
def test_reopen_scope_cannot_be_rebound(tmp_path, store, changed):
    path = tmp_path / "scoped.db"
    store.provision(path)
    first = store(path, access(), _OrderingDomain())
    first.close()
    original = access()
    if changed == "requester":
        wrong = replace(
            original,
            requester=Principal(PrincipalRef("identity", PrincipalId("other"))),
        )
    elif changed == "tenant":
        wrong = replace(
            original, scope=ReferenceScope(original.scope.owner, TenantId("other"))
        )
    else:
        wrong = replace(
            original, scope=ReferenceScope("other", original.scope.tenant_id)
        )
    for readonly in (False, True):
        with pytest.raises(_ScopeDenied, match="scope unavailable"):
            store(path, wrong, _OrderingDomain(), readonly=readonly)
    admitted = store(path, original, _OrderingDomain(), readonly=True)
    admitted.close()


@pytest.mark.parametrize("point", range(1, 14))
def test_crash_matrix(tmp_path, point):
    _SecretLedger.provision(tmp_path / "source.db")
    _EvidenceStore.provision(tmp_path / "evidence.db")
    completed = subprocess.run(
        [
            sys.executable,
            "-B",
            "-m",
            "tests.support.custody_scenario",
            str(tmp_path),
            str(point),
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert completed.returncode == 73, completed.stderr
    assert completed.stdout.strip() == f"FAILPOINT {point}"
    domain = _OrderingDomain()
    source = _SecretLedger(tmp_path / "source.db", access(), domain)
    custody = _EvidenceStore(tmp_path / "evidence.db", access(), domain)
    try:
        result = source.status(plan().use_id, access())
        expected = (
            UseRecoveryCategory.PREPARED_ONLY
            if point <= 6
            else (
                UseRecoveryCategory.ACCEPTED_ATTRIBUTED
                if point == 13
                else UseRecoveryCategory.ACCEPTED_ATTRIBUTION_OUTSTANDING
            )
        )
        assert result.category is expected
        assert result.duty is (
            SourceDutyState.SATISFIED if point == 13 else SourceDutyState.PENDING
        )
        assert (
            custody.submission_status(plan().pre_submission, access()) is not None
            if point > 1
            else custody.submission_status(plan().pre_submission, access()) is None
        )
        assert (
            custody.submission_status(plan().post_submission, access()) is not None
        ) == (point in (10, 11, 13))
        # Repeating prepare never admits this recovered identity for acceptance.
        source.prepare(plan(), access())
        if point <= 6 and point > 1:
            witness = custody.witness(plan().pre_submission, access())
            with domain.enter(), pytest.raises(_ScopeDenied):
                source.accept(
                    plan(),
                    witness,
                    access(),
                    material=b"x",
                    expected_material=b"x",
                    now=NOW,
                    approval=ApprovalObservation.CONSUMED,
                )
        assert source.status(plan().use_id, access()) == result
    finally:
        source.close()
        custody.close()


def test_material_canary(stores, tmp_path, capsys, caplog, monkeypatch):
    value = os.urandom(40).hex().encode()
    source, custody, domain = stores
    sql = []
    source._conn.set_trace_callback(sql.append)
    custody._conn.set_trace_callback(sql.append)
    from legoai.reference._custody_sqlite import _commit

    scanned_journals = []

    def scan_files():
        for path in tmp_path.iterdir():
            if path.is_file():
                if path.name.endswith(("-journal", "-wal")):
                    scanned_journals.append(path.name)
                if value in path.read_bytes():
                    pytest.fail("canary persisted", pytrace=False)

    def guarded_commit(conn):
        scan_files()  # active rollback journals, not merely files left after COMMIT
        _commit(conn)

    monkeypatch.setattr(_secret_ledger, "_commit", guarded_commit)
    monkeypatch.setattr(_durable_evidence, "_commit", guarded_commit)
    fact = accept(*stores, material=value)
    custody.acknowledge(evidence(fact), access(), recorded_at=NOW)
    source.finish(
        plan().use_id,
        custody.witness(plan().post_submission, access()),
        access(),
        expected_revision=2,
    )
    captured = capsys.readouterr()
    reports = (
        repr(source.inspect(access()))
        + str(fact)
        + _custody_codec.encode(fact)
        + caplog.text
        + captured.out
        + captured.err
        + "".join(sql)
    )
    if value in reports.encode():
        pytest.fail("canary disclosure", pytrace=False)
    scan_files()
    assert scanned_journals
    assert not tuple(tmp_path.glob("*-wal"))  # DELETE profile, WAL unsupported


def test_safe_contracts_and_codec():
    p = plan()
    assert _custody_codec.decode(_custody_codec.encode(p)) == p
    assert not {"material", "callback", "transaction", "header", "token"} & {
        f.name for f in fields(p)
    }
    with pytest.raises(ValueError):
        _custody_codec.decode('{"type":"datetime","type":"other","value":"x"}')
    with pytest.raises(ValueError):
        _custody_codec.decode('{"type":"eval","fields":{}}')
    for altered in (
        {"purpose": ""},
        {"expires_at": NOW},
        {"pre_submission": p.post_submission},
    ):
        with pytest.raises((TypeError, ValueError)):
            replace(p, **altered)


def test_readonly_inspection_cannot_mutate(stores, tmp_path):
    source, custody, domain = stores
    prepare(source, custody)
    reader = _SecretLedger(
        tmp_path / "source.db", access(), _OrderingDomain(), readonly=True
    )
    try:
        assert reader.inspect(access())[0].category is UseRecoveryCategory.PREPARED_ONLY
        with pytest.raises(_ScopeDenied):
            reader.prepare(plan(), access())
        with pytest.raises(_ScopeDenied):
            reader.intervene(
                plan().use_id, access(), expected_revision=1, disposition="review"
            )
    finally:
        reader.close()


def test_reopen_is_repair_only(tmp_path):
    path = tmp_path / "source.db"
    _SecretLedger.provision(path)
    first = _SecretLedger(path, access(), _OrderingDomain())
    first.close()
    reopened = _SecretLedger(path, access(), _OrderingDomain())
    try:
        with pytest.raises(_ScopeDenied, match="repair only"):
            reopened.prepare(plan(), access())
        assert reopened.inspect(access()) == ()
    finally:
        reopened.close()


def test_deleted_acceptance_is_unknown(stores, tmp_path):
    source, custody, domain = stores
    accept(*stores)
    source._conn.execute("DELETE FROM accepted")
    assert (
        _inspect_source(tmp_path / "source.db", access())
        is UseRecoveryCategory.UNKNOWN_GAP
    )


@pytest.mark.parametrize("damage", ["schema", "receipt", "truncated", "missing"])
def test_evidence_corruption(tmp_path, damage):
    path = tmp_path / "evidence.db"
    if damage != "missing":
        _EvidenceStore.provision(path)
        custody = _EvidenceStore(path, access(), _OrderingDomain())
        custody.acknowledge(
            evidence(SecretUseFact(plan(), SourceEvent.PREPARED, NOW)),
            access(),
            recorded_at=NOW,
        )
        custody.close()
        if damage == "truncated":
            path.write_bytes(b"broken")
        else:
            with sqlite3.connect(path) as conn:
                conn.execute(
                    "UPDATE metadata SET version=99"
                    if damage == "schema"
                    else "UPDATE custody SET receipt='{}'"
                )
    with pytest.raises(_StorageGap):
        _EvidenceStore(path, access(), _OrderingDomain())


def test_evidence_failure_preserves_accepted_duty(stores, monkeypatch):
    source, custody, domain = stores
    fact = accept(*stores)

    def failed_commit(conn):
        raise sqlite3.OperationalError("injected local failure")

    monkeypatch.setattr(_durable_evidence, "_commit", failed_commit)
    with pytest.raises(_StorageGap):
        custody.acknowledge(evidence(fact), access(), recorded_at=NOW)
    assert custody.submission_status(plan().post_submission, access()) is None
    assert (
        source.status(plan().use_id, access()).category
        is UseRecoveryCategory.ACCEPTED_ATTRIBUTION_OUTSTANDING
    )
    assert source._conn.execute("SELECT count(*) FROM accepted").fetchone() == (1,)
