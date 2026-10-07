"""Private Secret source owner. The acceptance COMMIT is the synthetic effect.

This persistence owner does not decide current authority. Private Stage-A
composition establishes current checks before this boundary; runtime hosts and
providers do not enable it. Durable qualification and ordering remain distinct.
"""

import hmac
import sqlite3
from datetime import datetime
from pathlib import Path

from legoai.evidence.custody import CustodyAccess, CustodyProfile, DurableCustodyReceipt
from legoai.governance.secret import (
    ApprovalObservation,
    SecretUseFact,
    SecretUseId,
    SecretUsePlan,
    SecretUseStatus,
    SourceDutyState,
    SourceEvent,
    UseRecoveryCategory,
    _time,
)
from legoai.reference import _custody_codec as codec
from legoai.reference._custody_sqlite import (
    _admit,
    _bind,
    _check,
    _commit,
    _Conflict,
    _connect,
    _provision,
    _ScopeDenied,
    _StorageGap,
)
from legoai.reference._durable_evidence import _ReceiptWitness
from legoai.reference._secret_domain import _OrderingDomain


def _schema() -> str:
    return """
CREATE TABLE incarnation(singleton INTEGER PRIMARY KEY CHECK(singleton=1),opened INTEGER NOT NULL CHECK(opened IN (0,1)));
INSERT INTO incarnation VALUES (1,0);
CREATE TABLE prepared(
 use_id TEXT PRIMARY KEY, plan TEXT NOT NULL CHECK(length(plan)<=32768),
 duty_id TEXT NOT NULL UNIQUE, pre_submission TEXT NOT NULL UNIQUE,
 post_submission TEXT NOT NULL UNIQUE
);
CREATE TABLE accepted(
 use_id TEXT PRIMARY KEY REFERENCES prepared(use_id),
 fact TEXT NOT NULL CHECK(length(fact)<=32768),
 pre_receipt TEXT NOT NULL CHECK(length(pre_receipt)<=32768),
 approval TEXT NOT NULL CHECK(approval IN ('consumed','not_applicable'))
);
CREATE TABLE duties(
 use_id TEXT PRIMARY KEY REFERENCES prepared(use_id),
 state TEXT NOT NULL CHECK(state IN ('pending','satisfied','requires_intervention')),
 revision INTEGER NOT NULL CHECK(revision>=1), receipt TEXT,
 disposition TEXT CHECK(disposition IS NULL OR length(disposition)<=32768),
 CHECK((state='satisfied')=(receipt IS NOT NULL))
);
CREATE TABLE history(
 use_id TEXT NOT NULL REFERENCES prepared(use_id), revision INTEGER NOT NULL,
 state TEXT NOT NULL, receipt TEXT, disposition TEXT,
 PRIMARY KEY(use_id,revision)
);
"""


class _SecretLedger:
    @staticmethod
    def provision(path: Path) -> None:
        _provision(path, "secret-source-v1", _schema())

    def __init__(
        self,
        path: Path,
        access: CustodyAccess,
        domain: _OrderingDomain,
        *,
        readonly: bool = False,
    ) -> None:
        if type(access) is not CustodyAccess or type(domain) is not _OrderingDomain:
            raise TypeError("trusted source composition required")
        domain.outside()
        self._access, self._domain, self._readonly = access, domain, readonly
        self._owner_thread = domain.thread_identity()
        self._stage_a_claimed = False
        self._live: set[str] = set()
        self._new_work = False
        self._admission = None if readonly else _admit(path, "secret-source-v1")
        try:
            self._conn = _connect(path, readonly=readonly)
            _check(self._conn, "secret-source-v1")
            _bind(self._conn, codec.encode(access), readonly=readonly)
            self._verify()
            if not readonly:
                # First admitted incarnation only. Reopen is repair/inspection,
                # even for a new identity: this slice has no restart admission.
                self._conn.execute("BEGIN IMMEDIATE")
                changed = self._conn.execute(
                    "UPDATE incarnation SET opened=1 WHERE singleton=1 AND opened=0"
                )
                self._new_work = changed.rowcount == 1
                _commit(self._conn)
        except BaseException:
            if hasattr(self, "_conn"):
                self._conn.close()
            if self._admission is not None:
                self._admission.close()
            raise

    def close(self) -> None:
        self._domain.outside()
        self._conn.close()
        if self._admission is not None:
            self._admission.close()
        self._live.clear()

    def _authorize(self, access: CustodyAccess) -> None:
        if type(access) is not CustodyAccess or access != self._access:
            raise _ScopeDenied("source scope unavailable")

    def _plan(self, use_id: SecretUseId, access: CustodyAccess) -> SecretUsePlan | None:
        self._authorize(access)
        if type(use_id) is not SecretUseId:
            raise TypeError("exact source identity required")
        row = self._conn.execute(
            "SELECT plan FROM prepared WHERE use_id=?", (use_id.value,)
        ).fetchone()
        if row is None:
            return None
        plan = codec.decode(row[0])
        if type(plan) is not SecretUsePlan:
            raise _StorageGap("source representation gap")
        if plan.secret.scope != access.scope or plan.requester != access.requester:
            return None
        return plan

    def _verify(self) -> None:
        try:
            _check(self._conn, "secret-source-v1")
            if self._conn.execute(
                "SELECT singleton,opened FROM incarnation"
            ).fetchall() not in ([(1, 0)], [(1, 1)]):
                raise ValueError("incarnation gap")
            rows = self._conn.execute(
                "SELECT use_id,plan,duty_id,pre_submission,post_submission FROM prepared LIMIT 4097"
            ).fetchall()
            if len(rows) > 4096:
                raise ValueError("capacity")
            for key, encoded, duty_id, pre, post in rows:
                plan = codec.decode(encoded)
                if type(plan) is not SecretUsePlan or (key, duty_id, pre, post) != (
                    plan.use_id.value,
                    plan.duty_id,
                    plan.pre_submission.value,
                    plan.post_submission.value,
                ):
                    raise ValueError("source identity")
                duty = self._conn.execute(
                    "SELECT state,revision,receipt,disposition FROM duties WHERE use_id=?",
                    (key,),
                ).fetchone()
                if duty is None:
                    raise ValueError("missing duty")
                state, revision, receipt, disposition = duty
                history = self._conn.execute(
                    "SELECT revision,state,receipt,disposition FROM history WHERE use_id=? ORDER BY revision",
                    (key,),
                ).fetchall()
                if (
                    len(history) != revision
                    or [r[0] for r in history] != list(range(1, revision + 1))
                    or history[-1] != (revision, state, receipt, disposition)
                ):
                    raise ValueError("duty history gap")
                accepted = self._conn.execute(
                    "SELECT fact,approval,pre_receipt FROM accepted WHERE use_id=?",
                    (key,),
                ).fetchone()
                acceptance_marker = len(history) >= 2 and history[1] == (
                    2,
                    "pending",
                    None,
                    None,
                )
                if acceptance_marker != (accepted is not None):
                    raise ValueError("acceptance/duty atomic set gap")
                if accepted is not None:
                    fact = codec.decode(accepted[0])
                    if (
                        type(fact) is not SecretUseFact
                        or fact.plan != plan
                        or fact.event is not SourceEvent.ACCEPTED
                    ):
                        raise ValueError("acceptance gap")
                    expected = (
                        "not_applicable" if plan.approval_id is None else "consumed"
                    )
                    if accepted[1] != expected:
                        raise ValueError("approval observation gap")
                    pre = codec.decode(accepted[2])
                    if (
                        type(pre) is not DurableCustodyReceipt
                        or pre.evidence.fact
                        != SecretUseFact(plan, SourceEvent.PREPARED, plan.prepared_at)
                        or pre.committed_at > fact.occurred_at
                    ):
                        raise ValueError("pre-use custody gap")
                if state == "satisfied":
                    r = codec.decode(receipt)
                    if (
                        type(r) is not DurableCustodyReceipt
                        or accepted is None
                        or r.evidence.fact != codec.decode(accepted[0])
                    ):
                        raise ValueError("receipt mismatch")
        except sqlite3.Error, ValueError, TypeError, KeyError, RecursionError:
            raise _StorageGap("source history gap") from None

    def prepare(self, plan: SecretUsePlan, access: CustodyAccess) -> SecretUseStatus:
        self._domain.outside()
        self._authorize(access)
        if self._readonly:
            raise _ScopeDenied("inspection cannot prepare")
        if type(plan) is not SecretUsePlan:
            raise TypeError("typed use plan required")
        if plan.secret.scope != access.scope or plan.requester != access.requester:
            raise _ScopeDenied("source scope unavailable")
        self._verify()
        previous = self._plan(plan.use_id, access)
        if previous is not None:
            if previous != plan:
                raise _Conflict("source identity conflict")
            result = self.status(plan.use_id, access)
            assert result is not None
            return result
        if not self._new_work:
            raise _ScopeDenied("reopened source permits repair only")
        try:
            self._conn.execute("BEGIN IMMEDIATE")
            if (
                self._conn.execute("SELECT count(*) FROM prepared").fetchone()[0]
                >= 4096
            ):
                raise _StorageGap("source capacity unavailable")
            self._conn.execute(
                "INSERT INTO prepared VALUES (?,?,?,?,?)",
                (
                    plan.use_id.value,
                    codec.encode(plan),
                    plan.duty_id,
                    plan.pre_submission.value,
                    plan.post_submission.value,
                ),
            )
            self._conn.execute(
                "INSERT INTO duties VALUES (?,'pending',1,NULL,NULL)",
                (plan.use_id.value,),
            )
            self._conn.execute(
                "INSERT INTO history VALUES (?,1,'pending',NULL,NULL)",
                (plan.use_id.value,),
            )
            _commit(self._conn)
        except sqlite3.IntegrityError:
            raise _Conflict("source identity conflict") from None
        except sqlite3.Error:
            raise _StorageGap("source prepare requires inspection") from None
        finally:
            if self._conn.in_transaction:
                self._conn.execute("ROLLBACK")
        self._live.add(plan.use_id.value)
        result = self.status(plan.use_id, access)
        assert result is not None
        return result

    def status(
        self, use_id: SecretUseId, access: CustodyAccess
    ) -> SecretUseStatus | None:
        self._domain.outside()
        self._authorize(access)
        try:
            self._conn.execute("BEGIN")
            self._verify()
            return self._status(use_id, access)
        except sqlite3.Error:
            raise _StorageGap("source status unavailable") from None
        finally:
            if self._conn.in_transaction:
                self._conn.execute("ROLLBACK")

    def _status(
        self, use_id: SecretUseId, access: CustodyAccess
    ) -> SecretUseStatus | None:
        plan = self._plan(use_id, access)
        if plan is None:
            return None
        state, revision = self._conn.execute(
            "SELECT state,revision FROM duties WHERE use_id=?", (use_id.value,)
        ).fetchone()
        accepted = self._conn.execute(
            "SELECT approval,fact FROM accepted WHERE use_id=?", (use_id.value,)
        ).fetchone()
        category = UseRecoveryCategory.PREPARED_ONLY
        approval = (
            ApprovalObservation.NOT_APPLICABLE
            if plan.approval_id is None
            else ApprovalObservation.POSSIBLY_CONSUMED
        )
        fact = None
        if accepted is not None:
            category = UseRecoveryCategory.ACCEPTED_ATTRIBUTION_OUTSTANDING
            approval = ApprovalObservation(accepted[0])
            retained = codec.decode(accepted[1])
            if type(retained) is not SecretUseFact:
                raise _StorageGap("retained source result gap")
            fact = retained
        if state == "satisfied":
            category = UseRecoveryCategory.ACCEPTED_ATTRIBUTED
        elif state == "requires_intervention":
            category = UseRecoveryCategory.RECONCILED_REQUIRES_INTERVENTION
        return SecretUseStatus(
            use_id, category, SourceDutyState(state), revision, approval, fact
        )

    def _claim_stage_a(self) -> None:
        """One Stage-A binding per admitted owner incarnation, never reset.

        Reconstructing a facade cannot reset cancellation or Secret invalidation.
        Reopened incarnations still permit only inspection/repair, not new use.
        """
        if self._domain.thread_identity() != self._owner_thread:
            raise _ScopeDenied("source owner thread required")
        with self._domain.enter():
            if self._stage_a_claimed:
                raise _ScopeDenied("source Stage-A binding already established")
            self._stage_a_claimed = True

    def _ready(
        self, plan: SecretUsePlan, witness: _ReceiptWitness, now: datetime
    ) -> None:
        """Stage-A pre-consumption check, under the same acceptance domain."""
        self._domain.held()
        if (
            self._readonly
            or not self._new_work
            or plan.use_id.value not in self._live
            or self._plan(plan.use_id, self._access) != plan
            or type(witness) is not _ReceiptWitness
            or witness.domain is not self._domain
        ):
            raise _ScopeDenied("Secret use unavailable")
        receipt = witness.receipt
        if (
            receipt.evidence.fact
            != SecretUseFact(plan, SourceEvent.PREPARED, plan.prepared_at)
            or receipt.evidence.profile is not CustodyProfile.INTACT_LOCAL_V1
            or not receipt.committed_at <= now < plan.expires_at
        ):
            raise _ScopeDenied("Secret use unavailable")

    def _discard(self, use_id: SecretUseId) -> None:
        self._domain.held()
        self._live.discard(use_id.value)

    def accept(
        self,
        plan: SecretUsePlan,
        witness: _ReceiptWitness,
        access: CustodyAccess,
        *,
        material: bytes,
        expected_material: bytes,
        now: datetime,
        approval: ApprovalObservation,
    ) -> SecretUseFact:
        """Private persistence boundary; caller already holds the exact domain.

        Current owner checks are the private Stage-A composition's responsibility.
        No callbacks, Evidence DB transaction or invocation happens here.
        """
        self._domain.held()
        self._authorize(access)
        if self._readonly:
            raise _ScopeDenied("inspection cannot accept")
        if type(plan) is not SecretUsePlan or self._plan(plan.use_id, access) != plan:
            raise _Conflict("source identity unavailable")
        row = self._conn.execute(
            "SELECT fact FROM accepted WHERE use_id=?", (plan.use_id.value,)
        ).fetchone()
        if row is not None:
            fact = codec.decode(row[0])
            if type(fact) is not SecretUseFact:
                raise _StorageGap("acceptance history gap")
            return fact
        if plan.use_id.value not in self._live:
            raise _ScopeDenied("recovered use cannot be accepted")
        # Any failed/uncertain attempt requires inspection, never another use.
        self._live.remove(plan.use_id.value)
        _time(now)
        if type(witness) is not _ReceiptWitness or witness.domain is not self._domain:
            raise _ScopeDenied("required custody witness unavailable")
        receipt = witness.receipt
        prepared = SecretUseFact(plan, SourceEvent.PREPARED, plan.prepared_at)
        if (
            receipt.evidence.fact != prepared
            or receipt.evidence.profile is not CustodyProfile.INTACT_LOCAL_V1
            or not receipt.committed_at <= now < plan.expires_at
        ):
            raise _ScopeDenied("required custody does not match")
        if (
            type(material) is not bytes
            or type(expected_material) is not bytes
            or not 1 <= len(material) <= 4096
            or not 1 <= len(expected_material) <= 4096
            or not hmac.compare_digest(material, expected_material)
        ):
            raise _ScopeDenied("synthetic validation failed")
        required = (
            ApprovalObservation.NOT_APPLICABLE
            if plan.approval_id is None
            else ApprovalObservation.CONSUMED
        )
        if approval is not required:
            raise _ScopeDenied("approval observation unavailable")
        fact = SecretUseFact(plan, SourceEvent.ACCEPTED, now)
        try:
            self._conn.execute("BEGIN IMMEDIATE")
            self._conn.execute(
                "INSERT INTO accepted VALUES (?,?,?,?)",
                (
                    plan.use_id.value,
                    codec.encode(fact),
                    codec.encode(receipt),
                    approval.value,
                ),
            )
            # Acceptance revision and outstanding attribution are committed together.
            updated = self._conn.execute(
                "UPDATE duties SET revision=2 WHERE use_id=? AND revision=1 AND state='pending'",
                (plan.use_id.value,),
            )
            if updated.rowcount != 1:
                raise _Conflict("source duty precondition")
            self._conn.execute(
                "INSERT INTO history VALUES (?,2,'pending',NULL,NULL)",
                (plan.use_id.value,),
            )
            _commit(self._conn)
        except sqlite3.Error:
            raise _StorageGap("acceptance outcome requires inspection") from None
        finally:
            if self._conn.in_transaction:
                self._conn.execute("ROLLBACK")
        return fact

    def finish(
        self,
        use_id: SecretUseId,
        witness: _ReceiptWitness,
        access: CustodyAccess,
        *,
        expected_revision: int,
    ) -> SecretUseStatus:
        self._domain.outside()
        self._authorize(access)
        self._verify()
        plan = self._plan(use_id, access)
        if (
            plan is None
            or type(witness) is not _ReceiptWitness
            or witness.domain is not self._domain
        ):
            raise _ScopeDenied("source receipt unavailable")
        row = self._conn.execute(
            "SELECT fact FROM accepted WHERE use_id=?", (use_id.value,)
        ).fetchone()
        if row is None or witness.receipt.evidence.fact != codec.decode(row[0]):
            raise _Conflict("source receipt mismatch")
        return self._update(
            use_id,
            access,
            expected_revision,
            "satisfied",
            codec.encode(witness.receipt),
            None,
        )

    def intervene(
        self,
        use_id: SecretUseId,
        access: CustodyAccess,
        *,
        expected_revision: int,
        disposition: str,
    ) -> SecretUseStatus:
        """Trusted entitled disposition reference, not arbitrary repair text."""
        from legoai.kernel.identity import _validate

        self._domain.outside()
        self._authorize(access)
        _validate(disposition)
        self._verify()
        if self._plan(use_id, access) is None:
            raise _ScopeDenied("source scope unavailable")
        return self._update(
            use_id,
            access,
            expected_revision,
            "requires_intervention",
            None,
            disposition,
        )

    def _update(
        self,
        use_id: SecretUseId,
        access: CustodyAccess,
        revision: int,
        state: str,
        receipt: str | None,
        disposition: str | None,
    ) -> SecretUseStatus:
        if type(revision) is not int or revision < 1:
            raise ValueError("exact positive duty revision required")
        if self._readonly:
            raise _ScopeDenied("inspection cannot repair")
        old = self._conn.execute(
            "SELECT state,receipt,disposition FROM duties WHERE use_id=?",
            (use_id.value,),
        ).fetchone()
        if old != (state, receipt, disposition):
            if old[0] == "satisfied":
                raise _Conflict("completed attribution is immutable")
            try:
                self._conn.execute("BEGIN IMMEDIATE")
                row = self._conn.execute(
                    "UPDATE duties SET state=?,revision=revision+1,receipt=?,disposition=? WHERE use_id=? AND revision=?",
                    (state, receipt, disposition, use_id.value, revision),
                )
                if row.rowcount != 1:
                    raise _Conflict("source duty revision conflict")
                self._conn.execute(
                    "INSERT INTO history VALUES (?,?,?,?,?)",
                    (use_id.value, revision + 1, state, receipt, disposition),
                )
                _commit(self._conn)
            except sqlite3.Error:
                raise _StorageGap("duty completion requires inspection") from None
            finally:
                if self._conn.in_transaction:
                    self._conn.execute("ROLLBACK")
        result = self._status(use_id, access)
        assert result is not None
        return result

    def inspect(self, access: CustodyAccess) -> tuple[SecretUseStatus, ...]:
        """Bounded privileged enumeration, no material/acquisition/submission."""
        self._domain.outside()
        self._authorize(access)
        try:
            self._conn.execute("BEGIN")
            self._verify()
            results = []
            for (key,) in self._conn.execute(
                "SELECT use_id FROM prepared ORDER BY use_id"
            ):
                status = self._status(SecretUseId(key), access)
                if status is not None:
                    results.append(status)
            return tuple(results)
        except sqlite3.Error:
            raise _StorageGap("source inspection unavailable") from None
        finally:
            if self._conn.in_transaction:
                self._conn.execute("ROLLBACK")


def _inspect_source(
    path: Path, access: CustodyAccess
) -> tuple[SecretUseStatus, ...] | UseRecoveryCategory:
    """Read-only inspection. Missing/invalid history never means an empty store."""
    try:
        ledger = _SecretLedger(path, access, _OrderingDomain(), readonly=True)
        try:
            return ledger.inspect(access)
        finally:
            ledger.close()
    except _StorageGap, sqlite3.Error, OSError:
        return UseRecoveryCategory.UNKNOWN_GAP
