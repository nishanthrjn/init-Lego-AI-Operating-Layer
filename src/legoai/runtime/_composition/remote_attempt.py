"""Model-invocation-plane construction of one exact remote attempt.

An attempt can be prepared only from an ADMITTED disclosure decision of the
gate bound to that same execution; the attempt store records responsibility
and never decides disclosure. No Secret is realized here: a credentialed
binding contributes only its SecretRevisionRef. No transport exists yet, and
the public host constructs nothing here while REMOTE is refused at open.
"""

from datetime import datetime

from legoai.capabilities.values import CapabilityId
from legoai.governance.disclosure import DisclosureDecision
from legoai.governance.secret import SecretRevisionRef
from legoai.intelligence.model.values import ModelId, ProviderId
from legoai.kernel.references import ConfigurationRevisionRef
from legoai.reference._remote_attempts import RemoteAttempt, RemoteAttemptId
from legoai.runtime._composition.disclosure import DisclosureCheck


def prepare_attempt(
    check: DisclosureCheck,
    decision: DisclosureDecision,
    attempt_id: RemoteAttemptId,
    configuration: ConfigurationRevisionRef,
    capability: CapabilityId,
    secret: SecretRevisionRef | None,
    created_at: datetime,
) -> RemoteAttempt:
    """Bind the admitted disclosure, endpoint and credential identities."""
    if type(check) is not DisclosureCheck or type(decision) is not DisclosureDecision:
        raise TypeError("an admitted disclosure check is required")
    if not decision.admitted:
        raise PermissionError("remote attempt requires admitted disclosure")
    admission = next(
        (a for a in check.gate.admissions if a.admission_id == decision.admission_id),
        None,
    )
    endpoint = check.gate.endpoint
    model = endpoint.model_for(check.purpose)
    if (
        admission is None
        or decision.admission_revision != admission.revision
        or decision.declaration_revision != admission.declaration_revision
        or model is None
    ):
        raise PermissionError("remote attempt requires admitted disclosure")
    assert decision.admission_id is not None
    assert decision.admission_revision is not None
    assert decision.declaration_revision is not None
    return RemoteAttempt(
        attempt_id,
        check.context.execution_id,
        check.context.operation,
        configuration,
        decision.admission_id,
        decision.admission_revision,
        admission.declaration_id,
        decision.declaration_revision,
        endpoint.binding_id,
        ProviderId(endpoint.provider_id),
        endpoint.endpoint_origin,
        endpoint.api_root,
        ModelId(model),
        capability,
        secret,
        created_at,
    )
