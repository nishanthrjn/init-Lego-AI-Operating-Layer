"""Separate Evidence-owned SQLite custody. Trusted scoped composition only."""

import sqlite3
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from legoai.evidence.custody import CustodyAccess, DurableCustodyReceipt, SourceEvidence
from legoai.kernel.identity import RequestId
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
from legoai.reference._secret_domain import _OrderingDomain


def _schema() -> str:
    return """
CREATE TABLE custody(
 submission TEXT PRIMARY KEY, evidence TEXT NOT NULL CHECK(length(evidence)<=32768),
 receipt TEXT NOT NULL CHECK(length(receipt)<=32768),
 UNIQUE(evidence)
);
"""


class _ReceiptWitness:
    """Private evidence-owner output. Never accepted from an application boundary."""

    def __init__(self, receipt: DurableCustodyReceipt, domain: _OrderingDomain) -> None:
        self.receipt = receipt
        self.domain = domain


class _EvidenceStore:
    @staticmethod
    def provision(path: Path) -> None:
        _provision(path, "evidence-custody-v1", _schema())

    def __init__(
        self,
        path: Path,
        access: CustodyAccess,
        domain: _OrderingDomain,
        *,
        readonly: bool = False,
    ) -> None:
        if type(access) is not CustodyAccess or type(domain) is not _OrderingDomain:
            raise TypeError("trusted custody composition required")
        domain.outside()
        self._access, self._domain, self._readonly = access, domain, readonly
        self._admission = None if readonly else _admit(path, "evidence-custody-v1")
        try:
            self._conn = _connect(path, readonly=readonly)
            _check(self._conn, "evidence-custody-v1")
            _bind(self._conn, codec.encode(access), readonly=readonly)
            self._verify()
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

    def _authorize(self, access: CustodyAccess) -> None:
        self._domain.outside()
        if type(access) is not CustodyAccess or access != self._access:
            raise _ScopeDenied("custody scope unavailable")

    def _verify(self) -> None:
        try:
            rows = self._conn.execute(
                "SELECT submission,evidence,receipt FROM custody LIMIT 4097"
            ).fetchall()
            if len(rows) > 4096:
                raise ValueError("capacity")
            for submission, evidence, receipt in rows:
                e, r = codec.decode(evidence), codec.decode(receipt)
                if (
                    type(e) is not SourceEvidence
                    or type(r) is not DurableCustodyReceipt
                ):
                    raise ValueError("representation")
                if r.evidence != e or e.fact.submission.value != submission:
                    raise ValueError("link")
        except sqlite3.Error, ValueError, TypeError, KeyError, RecursionError:
            raise _StorageGap("custody history gap") from None

    def submission_status(
        self, submission: RequestId, access: CustodyAccess
    ) -> DurableCustodyReceipt | None:
        self._authorize(access)
        if type(submission) is not RequestId:
            raise TypeError("submission identity required")
        try:
            self._conn.execute("BEGIN")
            self._verify()
            row = self._conn.execute(
                "SELECT receipt FROM custody WHERE submission=?", (submission.value,)
            ).fetchone()
            if row is None:
                return None
            receipt = codec.decode(row[0])
            if type(receipt) is not DurableCustodyReceipt:
                raise _StorageGap("custody receipt gap")
            plan = receipt.evidence.fact.plan
            if plan.secret.scope != access.scope or plan.requester != access.requester:
                return None
            return receipt
        except sqlite3.Error:
            raise _StorageGap("custody status unavailable") from None
        finally:
            if self._conn.in_transaction:
                self._conn.execute("ROLLBACK")

    def witness(self, submission: RequestId, access: CustodyAccess) -> _ReceiptWitness:
        receipt = self.submission_status(submission, access)
        if receipt is None:
            raise _StorageGap("required custody unavailable")
        return _ReceiptWitness(receipt, self._domain)

    def acknowledge(
        self, evidence: SourceEvidence, access: CustodyAccess, *, recorded_at: datetime
    ) -> DurableCustodyReceipt:
        self._authorize(access)
        if self._readonly:
            raise _ScopeDenied("inspection cannot submit custody")
        if type(evidence) is not SourceEvidence:
            raise TypeError("typed source evidence required")
        plan = evidence.fact.plan
        if plan.secret.scope != access.scope or plan.requester != access.requester:
            raise _ScopeDenied("custody scope unavailable")
        previous = self.submission_status(evidence.fact.submission, access)
        if previous is not None:
            if previous.evidence != evidence:
                raise _Conflict("custody identity conflict")
            return previous
        receipt = DurableCustodyReceipt(
            str(uuid4()), "local-evidence-v1", evidence, recorded_at
        )
        encoded, result = codec.encode(evidence), codec.encode(receipt)
        try:
            self._conn.execute("BEGIN IMMEDIATE")
            if self._conn.execute("SELECT count(*) FROM custody").fetchone()[0] >= 4096:
                raise _StorageGap("custody capacity unavailable")
            self._conn.execute(
                "INSERT INTO custody VALUES (?,?,?)",
                (evidence.fact.submission.value, encoded, result),
            )
            _commit(self._conn)
        except sqlite3.IntegrityError:
            raise _Conflict("custody identity conflict") from None
        except sqlite3.Error:
            raise _StorageGap("custody commit outcome requires inspection") from None
        finally:
            if self._conn.in_transaction:
                self._conn.execute("ROLLBACK")
        return receipt
