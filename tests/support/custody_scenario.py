"""Offline deterministic process-death driver. Failpoints never enter production."""

import os
import sqlite3
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from legoai.evidence.custody import CustodyAccess, CustodyProfile, SourceEvidence
from legoai.governance.secret import (
    ApprovalObservation,
    SecretRevisionRef,
    SecretUseFact,
    SecretUseId,
    SecretUsePlan,
    SourceEvent,
)
from legoai.governance.values import Approval, ApprovalId, GrantId, PolicyRef, Principal
from legoai.kernel.context import TenantContext
from legoai.kernel.identity import (
    ApplicationId,
    OperationId,
    PrincipalId,
    RequestId,
    TenantId,
)
from legoai.kernel.references import (
    ApplicationRef,
    ConfigurationRef,
    ConfigurationRevisionRef,
    OperationRef,
    PrincipalRef,
    ReferenceScope,
)
from legoai.kernel.versions import Version
from legoai.reference import _durable_evidence, _secret_ledger
from legoai.reference._custody_sqlite import _commit
from legoai.reference._durable_evidence import _EvidenceStore
from legoai.reference._secret_domain import _OrderingDomain
from legoai.reference._secret_ledger import _SecretLedger

NOW = datetime(2026, 10, 7, tzinfo=UTC)


def plan() -> SecretUsePlan:
    scope = ReferenceScope("secret-owner", TenantId("tenant"))
    principal = Principal(PrincipalRef("identity", PrincipalId("operator")))
    return SecretUsePlan(
        SecretUseId("use"),
        OperationId("operation"),
        SecretRevisionRef(scope, "synthetic-reference", "1", "mapping-1"),
        principal,
        principal,
        ConfigurationRevisionRef(
            ConfigurationRef(ApplicationRef(scope, ApplicationId("app")), "config"),
            "1",
            Version(1, 0, 0),
        ),
        "synthetic-use",
        "private-synthetic-consumer",
        Version(1, 0, 0),
        "synthetic-target",
        GrantId("grant"),
        PolicyRef("policy-owner", "policy", Version(1, 0, 0)),
        ApprovalId("approval"),
        "attribution-duty",
        RequestId("prepared-submission"),
        RequestId("accepted-submission"),
        NOW,
        NOW + timedelta(hours=1),
        NOW + timedelta(days=1),
    )


def access() -> CustodyAccess:
    p = plan()
    return CustodyAccess(p.secret.scope, p.requester)


def evidence(fact: SecretUseFact) -> SourceEvidence:
    return SourceEvidence(fact, fact.plan.actor, CustodyProfile.INTACT_LOCAL_V1)


def die(point: int) -> None:
    print(f"FAILPOINT {point}", flush=True)
    os._exit(73)


def crash_scenario(directory: Path, point: int) -> None:
    """Actual abrupt child termination, at explicit semantic/SQL boundaries."""
    domain = _OrderingDomain()
    p, a = plan(), access()
    source = _SecretLedger(directory / "source.db", a, domain)
    custody = _EvidenceStore(directory / "evidence.db", a, domain)
    source.prepare(p, a)
    if point == 1:
        die(point)
    custody.acknowledge(
        evidence(SecretUseFact(p, SourceEvent.PREPARED, NOW)), a, recorded_at=NOW
    )
    if point == 2:
        die(point)
    witness = custody.witness(p.pre_submission, a)
    material = os.urandom(32)
    with domain.enter():
        if point == 3:
            die(point)
        from legoai.reference.governance import InMemoryApprovalRegistry

        approvals = InMemoryApprovalRegistry()
        assert p.approval_id is not None
        approval = Approval(
            p.approval_id,
            OperationRef(
                p.configuration.configuration, p.operation_id, "synthetic-use"
            ),
            TenantContext(p.secret.scope.tenant_id),
            p.requester,
            p.actor,
            1,
            NOW,
            p.expires_at,
        )
        approvals.consume(approval)
        if point == 4:
            die(point)
        if point == 5:
            die(point)

        def source_commit(conn: sqlite3.Connection) -> None:
            if point == 6:
                die(point)
            _commit(conn)
            if point == 7:
                die(point)

        source_patch = patch.object(_secret_ledger, "_commit", source_commit)
        source_patch.start()
        fact = source.accept(
            p,
            witness,
            a,
            material=material,
            expected_material=material,
            now=NOW,
            approval=ApprovalObservation.CONSUMED,
        )
    source_patch.stop()
    if point in (8, 12):
        die(point)

    def evidence_commit(conn: sqlite3.Connection) -> None:
        if point == 9:
            die(point)
        _commit(conn)
        if point == 10:
            die(point)

    patch.object(_durable_evidence, "_commit", evidence_commit).start()
    custody.acknowledge(evidence(fact), a, recorded_at=NOW)

    def finish_commit(conn: sqlite3.Connection) -> None:
        if point == 11:
            die(point)
        _commit(conn)
        if point == 13:
            die(point)

    patch.object(_secret_ledger, "_commit", finish_commit).start()
    source.finish(
        p.use_id, custody.witness(p.post_submission, a), a, expected_revision=2
    )
    raise AssertionError("unknown failpoint")


if __name__ == "__main__":
    crash_scenario(Path(sys.argv[1]), int(sys.argv[2]))
