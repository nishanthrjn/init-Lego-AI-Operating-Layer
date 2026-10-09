"""REMOTE-ATTEMPT-CUSTODY-1 composition: attempts follow admitted disclosure.

Uses the disclosure-gate internal seam; REMOTE stays refused at open. No
network, transport, provider or Secret realization.
"""

import asyncio
from pathlib import Path
from typing import Any

import pytest

from legoai.capabilities.values import CapabilityId
from legoai.evidence.ports import EvidenceId
from legoai.governance.disclosure import DisclosureObservation, DisclosureRefusal
from legoai.kernel.identity import TenantId
from legoai.kernel.references import ReferenceScope
from legoai.reference._remote_attempts import (
    AttemptState,
    RemoteAttemptId,
    _RemoteAttemptStore,
)
from legoai.reference._secret_domain import _OrderingDomain
from legoai.reference.secret import _ProvisionedSecretSource
from legoai.runtime._composition.remote_attempt import prepare_attempt
from legoai.runtime.api import HostError, HostFailure, ModelPurpose
from legoai.runtime.local import open_local_host
from tests.integration.composition.test_local_host import (
    NOW,
    FakeModel,
    fake_binding,
    selection,
)
from tests.integration.composition.test_remote_disclosure import (
    configured,
    disclosure,
    remote_binding,
)
from tests.integration.composition.test_remote_disclosure_gate import (
    Seam,
    chat,
    disclosed,
)
from tests.unit.governance.test_disclosure import DAY
from tests.unit.governance.test_disclosure import NOW as AT

CHAT = CapabilityId("legoai.intelligence.model.chat")
# The credential's scope shares the host configuration's tenant.
SCOPE = ReferenceScope("secret-owner", TenantId("tenant-a"))


def store(tmp_path: Path) -> _RemoteAttemptStore:
    path = tmp_path / "attempts.db"
    _RemoteAttemptStore.provision(path)
    return _RemoteAttemptStore(path, _OrderingDomain(), lambda: AT)


def checked(seam: Seam, value: Any = None) -> tuple[Any, Any]:
    context = seam.mint(value=disclosed() if value is None else value)
    disclosure_value = seam.host._require(context, ModelPurpose.CHAT)  # type: ignore[attr-defined]
    check = seam.host._check(context, ModelPurpose.CHAT, disclosure_value)  # type: ignore[attr-defined]
    return check, check.decide()


def test_attempt_is_prepared_only_from_an_admitted_decision(tmp_path: Path) -> None:
    seam = Seam()
    check, decision = checked(seam)
    assert decision.admitted
    source = _ProvisionedSecretSource(_OrderingDomain(), SCOPE)
    secret = source.provision("bearer-key", "remote-model-bearer", "c", "token-value-1")
    attempt = prepare_attempt(
        check,
        decision,
        RemoteAttemptId("attempt-1"),
        seam.host._config.configuration,  # type: ignore[attr-defined]
        CHAT,
        secret.exact,
        AT,
    )
    assert attempt.execution_id == check.context.execution_id
    assert attempt.operation == check.context.operation
    assert (attempt.admission_id, attempt.admission_revision) == ("admission", "a1")
    assert (attempt.declaration_id, attempt.declaration_revision) == ("processor", "r1")
    assert attempt.binding_id == "remote" and attempt.model.value == "model-a"
    attempts = store(tmp_path)
    receipt = attempts.intend(attempt)
    assert attempts.claim_for_handoff(receipt) == attempt
    attempts.close()


def test_refused_decision_cannot_become_an_attempt(tmp_path: Path) -> None:
    seam = Seam(gate={"clock": lambda: AT + 2 * DAY})
    check, decision = checked(seam)
    assert decision.refusal is DisclosureRefusal.EXPIRED
    with pytest.raises(PermissionError):
        prepare_attempt(
            check,
            decision,
            RemoteAttemptId("attempt-1"),
            seam.host._config.configuration,  # type: ignore[attr-defined]
            CHAT,
            None,
            AT,
        )
    attempts = store(tmp_path)
    assert attempts.unsettled() == ()
    attempts.close()


def test_decision_from_another_admission_is_refused() -> None:
    seam = Seam()
    check, decision = checked(seam)
    from dataclasses import replace

    forged = replace(decision, admission_revision="a2")
    with pytest.raises(PermissionError):
        prepare_attempt(
            check,
            forged,
            RemoteAttemptId("attempt-1"),
            seam.host._config.configuration,  # type: ignore[attr-defined]
            CHAT,
            None,
            AT,
        )


def test_attempt_history_authorizes_neither_disclosure_nor_secret_use(
    tmp_path: Path,
) -> None:
    seam = Seam()
    check, decision = checked(seam)
    source = _ProvisionedSecretSource(_OrderingDomain(), SCOPE)
    secret = source.provision("bearer-key", "remote-model-bearer", "c", "token-value-1")
    attempts = store(tmp_path)
    receipt = attempts.intend(
        prepare_attempt(
            check,
            decision,
            RemoteAttemptId("attempt-1"),
            seam.host._config.configuration,  # type: ignore[attr-defined]
            CHAT,
            secret.exact,
            AT,
        )
    )
    attempts.settle(receipt, AttemptState.UNKNOWN, frozenset())
    # A later invocation is decided by the gate alone, never by history.
    seam.host._gate = __import__("dataclasses").replace(  # type: ignore[attr-defined]
        seam.host._gate,  # type: ignore[attr-defined]
        clock=lambda: AT + 2 * DAY,
    )
    _, later = checked(seam)
    assert later.refusal is DisclosureRefusal.EXPIRED
    # A retired credential stays retired, whatever the attempt recorded.
    source.retire(secret.exact)
    assert source.status(secret.exact) is False
    public = {n for n in dir(attempts) if not n.startswith("_")}
    assert public == {
        "provision",
        "close",
        "intend",
        "claim_for_handoff",
        "settle",
        "reconcile_unknown",
        "inspect",
        "unsettled",
    }
    attempts.close()


def test_disclosure_evidence_and_attempt_custody_stay_separate(tmp_path: Path) -> None:
    seam = Seam()
    attempts = store(tmp_path)

    async def work() -> Any:
        return await seam.host.governed_chat(seam.mint(value=disclosed()), chat())

    result = asyncio.run(work())
    record = seam.custody.read(
        EvidenceId(f"disclosure-{result.execution.execution_id.value}"), seam.tenant
    )
    assert record is not None and type(record.subject) is DisclosureObservation
    # The gate recorded disclosure Evidence; it created no attempt.
    assert attempts.unsettled() == ()
    assert not hasattr(record.subject, "attempt_id")
    attempts.close()


def test_local_invocations_create_no_attempt_rows(tmp_path: Path) -> None:
    attempts = store(tmp_path)
    model = FakeModel()
    config = configured(
        fake_binding(model), remote_binding(), disclosure_config=disclosure()
    )
    host = open_local_host(config, selection("fake"), clock=lambda: NOW)

    async def work() -> Any:
        return await host.governed_chat(host.model_execution(ModelPurpose.CHAT), chat())

    result = asyncio.run(work())
    assert model.chat_calls == 1 and result.response is not None
    assert attempts.unsettled() == ()
    conn = __import__("sqlite3").connect(tmp_path / "attempts.db")
    assert conn.execute("SELECT count(*) FROM attempts").fetchone() == (0,)
    conn.close()
    attempts.close()


def test_remote_remains_refused_with_disclosure_secret_and_store(
    tmp_path: Path,
) -> None:
    attempts = store(tmp_path)
    source = _ProvisionedSecretSource(_OrderingDomain(), SCOPE)
    source.provision("bearer-key", "remote-model-bearer", "c", "token-value-1")
    config = configured(remote_binding(), disclosure_config=disclosure())
    with pytest.raises(HostError) as error:
        open_local_host(config, selection("remote"), clock=lambda: NOW)
    assert error.value.failure is HostFailure.UNSUPPORTED_COMPOSITION
    assert attempts.unsettled() == ()
    attempts.close()
