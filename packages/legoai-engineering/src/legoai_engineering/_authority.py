"""Private ADR-018 current-authorization check shared by engineering wiring.

One definition for authorized reads, mutation and checks. Not middleware, not
a policy engine and never a permission issuer: the operator binds one workspace
reference and one fixed action; existing Governance decides per call.
"""

from collections.abc import Callable
from dataclasses import replace
from datetime import datetime

from legoai.governance.ports import (
    AuthorizationDecision,
    AuthorizationOutcome,
    AuthorizationPort,
    SecurityContext,
)
from legoai.kernel.references import ConfigurationRef

from legoai_engineering.authorization import (
    EffectAuthorizationError,
    EffectAuthorizationFailure,
)


def _bind(workspace_reference: object, security_context: object, action: str) -> None:
    """Refuse at composition any context not bound to this workspace and action.

    Approval-bearing contexts are unsupported: no dispatch owner consumes them.
    """
    if type(workspace_reference) is not ConfigurationRef:
        raise TypeError("engineering authorization requires workspace ConfigurationRef")
    if type(security_context) is not SecurityContext:
        raise TypeError("engineering authorization requires SecurityContext")
    if (
        security_context.operation.subject != workspace_reference
        or security_context.action != action
        or security_context.resource_scope != workspace_reference.instance
        or security_context.approval is not None
    ):
        raise ValueError(f"unsupported {action} authorization scope")


def _evaluate(
    security_context: SecurityContext,
    authorization: AuthorizationPort,
    clock: Callable[[], datetime],
) -> AuthorizationOutcome:
    """Evaluate current authority now; never cached, never an implicit allow."""
    if security_context.approval is not None:
        return AuthorizationOutcome.DENIED
    context = replace(security_context, established_at=clock())
    decision = authorization.evaluate(context)
    if type(decision) is not AuthorizationDecision:
        raise TypeError("authorization must return AuthorizationDecision")
    if (
        decision.operation != context.operation
        or decision.evaluated_at != context.established_at
    ):
        return AuthorizationOutcome.DENIED
    return decision.outcome


def _require(
    security_context: SecurityContext,
    authorization: AuthorizationPort,
    clock: Callable[[], datetime],
) -> None:
    """Raise before an effect unless current authority is ALLOWED."""
    outcome = _evaluate(security_context, authorization, clock)
    if outcome is AuthorizationOutcome.UNAVAILABLE:
        raise EffectAuthorizationError(EffectAuthorizationFailure.UNAVAILABLE)
    if outcome is not AuthorizationOutcome.ALLOWED:
        raise EffectAuthorizationError(EffectAuthorizationFailure.DENIED)
