"""Current authorization immediately before a known check runs (ADR-018 CR-3)."""

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime

from legoai.governance.ports import AuthorizationPort, SecurityContext
from legoai.kernel.references import ConfigurationRef

from legoai_engineering._authority import _bind, _require
from legoai_engineering.checks.ports import EngineeringCheckPort
from legoai_engineering.checks.values import CheckRequest, CheckResult

ENGINEERING_CHECK_ACTION = "run-engineering-check"


@dataclass(frozen=True, slots=True)
class AuthorizedEngineeringChecks:
    """EngineeringCheckPort decorator over local or sandboxed checks.

    Running a check executes repository-controlled code, so every check
    evaluates current Governance for run-engineering-check on the bound
    workspace, then calls the inner adapter exactly once. Denial raises
    EffectAuthorizationError before any process or sandbox starts. Results,
    CheckError and WorkspaceError pass through unchanged. Authorization is
    permission to run, not result integrity or isolation; there is no retry
    and no fallback between adapters.
    """

    workspace_reference: ConfigurationRef
    checks: EngineeringCheckPort = field(repr=False)
    security_context: SecurityContext = field(repr=False)
    authorization: AuthorizationPort = field(repr=False)
    clock: Callable[[], datetime] = field(repr=False)

    def __post_init__(self) -> None:
        _bind(
            self.workspace_reference,
            self.security_context,
            ENGINEERING_CHECK_ACTION,
        )
        if not callable(getattr(self.checks, "check", None)):
            raise TypeError("authorized checks require EngineeringCheckPort")
        if not callable(getattr(self.authorization, "evaluate", None)):
            raise TypeError("authorized checks require AuthorizationPort")
        if not callable(self.clock):
            raise TypeError("authorized checks require a clock")

    def check(self, request: CheckRequest) -> CheckResult:
        if type(request) is not CheckRequest:
            raise TypeError("authorized checks require CheckRequest")
        _require(self.security_context, self.authorization, self.clock)
        return self.checks.check(request)
