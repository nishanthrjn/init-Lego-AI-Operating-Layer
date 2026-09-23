"""Semantic known-check boundary, independent of runtime governance."""

from typing import Protocol

from legoai_engineering.checks.values import CheckRequest, CheckResult


class EngineeringCheckPort(Protocol):
    def check(self, request: CheckRequest) -> CheckResult:
        """Run one known check with finite capture/time limits; never retry.

        Nonzero completion is a result. Infrastructure faults raise CheckError;
        invalid workspace targets reuse WorkspaceError. No arbitrary argv, shell,
        installation, authorization or isolation is provided. Synchronous calls
        have no cooperative cancellation API; interruption triggers child cleanup.
        """
        ...
