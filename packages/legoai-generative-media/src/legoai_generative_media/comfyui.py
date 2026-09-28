"""Provider-neutral ComfyUI text-to-image engine; no runtime management.

Deadlines, effect truth, attribution and PNG validation live here once. The
selected driver translates one API family's routes and wire formats.
"""

import asyncio
import math
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from legoai.kernel.effects import EffectExtent
from legoai.kernel.errors import ErrorCategory

from .drivers.base import (
    Budget,
    Capabilities,
    ComfyDriver,
    InvalidOutput,
    ProviderError,
    ProviderProfile,
    ReadOnlyTransport,
    RequestTimeout,
    SubmissionRejected,
    Transport,
)
from .drivers.legacy import LegacyDriver, object_response, safe_location
from .http import Endpoint, LocalHTTP
from .values import (
    Cessation,
    GeneratedImage,
    GenerationCancelled,
    GenerationResult,
    InputTransferCancelled,
    Outcome,
    ProviderJobRef,
    ReconciliationResult,
    ReconciliationStatus,
    TextToImageRequest,
    identifier,
)
from .workflow import ApprovedTemplate, ApprovedWorkflow

__all__ = [
    "HARD_MAX_WAIT_SECONDS",
    "ComfyEngine",
    "ComfyTextToImageAdapter",
    "ComfyUIConfig",
    "CompletionPolicy",
    "LocalComfyUIAdapter",
    "ReadOnlyTransport",
    "RequestTimeout",
    "Transport",
    "object_response",
    "safe_location",
]

# Observed fixed-workflow CPU run: ~640 s. 1800 s admits ~2.8x that variance
# (throttling, concurrent load) while keeping every wait finite.
HARD_MAX_WAIT_SECONDS = 1800
MAX_POLL_INTERVAL_SECONDS = 30
MAX_REQUEST_TIMEOUT_SECONDS = 60

FAILURES = (
    OSError,
    ValueError,
    TypeError,
    KeyError,
    IndexError,
    RecursionError,
    asyncio.IncompleteReadError,
    asyncio.LimitOverrunError,
)


def _bounded(value: float, lower: float, upper: float, name: str) -> None:
    if (
        type(value) not in (float, int)
        or not math.isfinite(value)
        or not lower <= value <= upper
    ):
        raise ValueError(f"invalid {name}")


@dataclass(frozen=True, slots=True)
class CompletionPolicy:
    """Operator-side waiting bounds; never part of the application request.

    max_wait bounds one call from start to result. request_timeout bounds each
    HTTP exchange separately, so no single call can consume the whole wait.
    The poll count is derived, never coordinated by hand.
    """

    max_wait_seconds: float = 300
    poll_interval_seconds: float = 1
    request_timeout_seconds: float = 10

    def __post_init__(self) -> None:
        _bounded(self.max_wait_seconds, 0.5, HARD_MAX_WAIT_SECONDS, "total wait")
        _bounded(
            self.poll_interval_seconds,
            0.05,
            min(MAX_POLL_INTERVAL_SECONDS, self.max_wait_seconds / 10),
            "poll interval",
        )
        _bounded(
            self.request_timeout_seconds,
            0.01,
            min(MAX_REQUEST_TIMEOUT_SECONDS, self.max_wait_seconds),
            "request timeout",
        )

    @classmethod
    def for_wait(cls, max_wait_seconds: float) -> CompletionPolicy:
        """One operator setting; interval and request bounds are derived."""
        _bounded(max_wait_seconds, 0.5, HARD_MAX_WAIT_SECONDS, "total wait")
        return cls(
            max_wait_seconds,
            min(1, max_wait_seconds / 10),
            min(10, max_wait_seconds),
        )

    @property
    def max_polls(self) -> int:
        # Termination backstop even if an injected clock never advances.
        return int(self.max_wait_seconds // self.poll_interval_seconds) + 1


class Refused(Exception):
    """A complete pre-submission result (for example a failed input transfer)."""

    def __init__(self, result: GenerationResult) -> None:
        super().__init__("refused before submission")
        self.result = result


@dataclass
class RunState:
    """Per-invocation facts a capability's preparation step may update."""

    disclosure: EffectExtent = EffectExtent.NONE
    category: ErrorCategory = ErrorCategory.DEPENDENCY_FAILURE


Prepare = Callable[[Budget, RunState], Awaitable[tuple[dict[str, Any], int]]]


@dataclass(frozen=True)
class ComfyEngine[W: ApprovedTemplate]:
    """Deadline, single submission, effect truth, attribution and PNG checks.

    Capabilities supply only a preparation step returning the bound graph and
    seed. Everything from submission onwards is shared and identical.
    """

    workflow: W
    driver: ComfyDriver = field(repr=False)
    binding: str = "comfyui-local"
    completion: CompletionPolicy = CompletionPolicy()
    # Workflow-declared provider capabilities; checked before any submission.
    requires: frozenset[str] = frozenset()
    # Monotonic clock/sleep are injectable so long jobs are testable without waiting.
    clock: Callable[[], float] = field(default=time.monotonic, repr=False)
    sleep: Callable[[float], Awaitable[None]] = field(default=asyncio.sleep, repr=False)
    _busy: bool = field(default=False, init=False, repr=False)

    def __post_init__(self) -> None:
        if type(self.completion) is not CompletionPolicy:
            raise TypeError("completion policy required")
        identifier(self.binding)
        if type(self.requires) is not frozenset or not (
            self.requires <= Capabilities.names()
        ):
            raise ValueError("unknown required capability")

    @property
    def profile(self) -> ProviderProfile:
        return self.driver.profile

    def _budget(self, *, read_only: bool) -> Budget:
        return Budget(
            self.clock() + self.completion.max_wait_seconds,
            self.clock,
            self.completion.request_timeout_seconds,
            read_only,
        )

    async def _pause(self, budget: Budget) -> None:
        remaining = budget.deadline - self.clock()
        if remaining <= 0:
            raise TimeoutError
        await self.sleep(min(self.completion.poll_interval_seconds, remaining))

    async def _preflight(self, budget: Budget) -> None:
        capabilities = self.profile.capabilities
        if not all(capabilities.supports(name) for name in self.requires):
            # Workflow portability: fail closed before anything is dispatched.
            raise ProviderError(ErrorCategory.VERSION_MISMATCH, "capability_missing")
        if capabilities.node_preflight:
            await self.driver.preflight(budget, self.workflow)

    async def _execute(self, prepare: Prepare) -> GenerationResult:
        if self._busy:
            return GenerationResult(
                Outcome.FAILED, EffectExtent.NONE, error=ErrorCategory.CONFLICT
            )
        object.__setattr__(self, "_busy", True)
        run = RunState()
        effect = EffectExtent.NONE
        job: ProviderJobRef | None = None
        reason: str | None = None
        policy = self.completion
        budget = self._budget(read_only=False)
        width, height = self.workflow.geometry

        def result(outcome: Outcome, **values: Any) -> GenerationResult:
            return GenerationResult(
                outcome, effect, job, input_disclosure=run.disclosure, **values
            )

        try:
            # Real-time backstop even if an injected clock misbehaves.
            async with asyncio.timeout(policy.max_wait_seconds):
                graph, seed = await prepare(budget, run)
                # Conservative from the instant dispatch might occur: never resubmit.
                effect = EffectExtent.UNKNOWN
                try:
                    submission = await self.driver.submit(budget, graph)
                except SubmissionRejected:
                    # The provider documents that this rejection created no job.
                    effect = EffectExtent.NONE
                    raise
                job = ProviderJobRef("comfyui", self.binding, submission.job_id)
                if submission.problem:
                    raise ValueError("submission node errors")
                for attempt in range(policy.max_polls):
                    if attempt:
                        await self._pause(budget)
                    observed = await self.driver.observe(budget, job, thorough=False)
                    if observed.status in (
                        ReconciliationStatus.PENDING,
                        ReconciliationStatus.NOT_FOUND,
                    ):
                        continue
                    if observed.status is ReconciliationStatus.FAILED:
                        run.category = ErrorCategory.EXECUTION_FAILURE
                        reason = observed.reason
                        raise ValueError("generation failed")
                    effect = EffectExtent.COMPLETED
                    run.category = ErrorCategory.VALIDATION_ERROR
                    output = self.driver.output(observed)
                    run.category = ErrorCategory.DEPENDENCY_FAILURE
                    content = await self.driver.fetch(budget, output)
                    run.category = ErrorCategory.VALIDATION_ERROR
                    generated = GeneratedImage(
                        content,
                        job,
                        self.workflow.reference,
                        seed,
                        width=width,
                        height=height,
                    )
                    return result(Outcome.SUCCESS, image=generated)
                raise TimeoutError("poll bound exceeded")
        except Refused as refused:
            return refused.result
        except InputTransferCancelled as cancelled:
            run.disclosure = cancelled.transfer.disclosure
            raise GenerationCancelled(
                result(Outcome.CANCELLED, cessation=Cessation.UNKNOWN)
            ) from None
        except asyncio.CancelledError:
            raise GenerationCancelled(
                result(Outcome.CANCELLED, cessation=Cessation.UNKNOWN)
            ) from None
        except TimeoutError:
            return result(
                Outcome.DEADLINE,
                error=ErrorCategory.DEADLINE_EXCEEDED,
                cessation=Cessation.UNKNOWN,
            )
        except ProviderError as error:
            return result(
                Outcome.FAILED,
                error=error.category,
                reason=error.reason,
                evidence=error.evidence,
            )
        except InvalidOutput:
            return result(Outcome.FAILED, error=ErrorCategory.VALIDATION_ERROR)
        except FAILURES:
            return result(Outcome.FAILED, error=run.category, reason=reason)
        finally:
            object.__setattr__(self, "_busy", False)

    async def reconcile(self, job: ProviderJobRef) -> ReconciliationResult:
        """Inspect one existing job; never submits, retries, interrupts or deletes.

        All I/O goes through a read-only budget that refuses any POST.
        Cancellation propagates unchanged: reconciliation has no effect to retain.
        """
        if type(job) is not ProviderJobRef:
            raise TypeError("ProviderJobRef required")
        if job.provider != "comfyui" or job.binding != self.binding:
            raise ValueError("job not owned by this binding")
        budget = self._budget(read_only=True)
        completed = False
        category = ErrorCategory.DEPENDENCY_FAILURE
        reason: str | None = None
        evidence: tuple[str, ...] = ()
        try:
            async with asyncio.timeout(self.completion.max_wait_seconds):
                observed = await self.driver.observe(budget, job, thorough=True)
                if observed.status is ReconciliationStatus.NOT_FOUND:
                    # Absence is not evidence of non-execution or failure.
                    return ReconciliationResult(job, ReconciliationStatus.NOT_FOUND)
                category = ErrorCategory.VALIDATION_ERROR
                graph = await self.driver.recorded_graph(budget, job, observed)
                seed = self.workflow.seed_of(graph)
                if observed.status is ReconciliationStatus.PENDING:
                    return ReconciliationResult(job, ReconciliationStatus.PENDING)
                if observed.status is ReconciliationStatus.FAILED:
                    return ReconciliationResult(
                        job,
                        ReconciliationStatus.FAILED,
                        error=ErrorCategory.EXECUTION_FAILURE,
                        reason=observed.reason,
                    )
                # Completion is now established; later faults cannot retract it.
                completed = True
                output = self.driver.output(observed)
                category = ErrorCategory.DEPENDENCY_FAILURE
                content = await self.driver.fetch(budget, output)
                category = ErrorCategory.VALIDATION_ERROR
                width, height = self.workflow.geometry
                image = GeneratedImage(
                    content,
                    job,
                    self.workflow.reference,
                    seed,
                    width=width,
                    height=height,
                )
                return ReconciliationResult(
                    job, ReconciliationStatus.COMPLETED, image=image
                )
        except TimeoutError:
            category = ErrorCategory.DEADLINE_EXCEEDED
        except ProviderError as error:
            category, reason, evidence = error.category, error.reason, error.evidence
        except InvalidOutput:
            category = ErrorCategory.VALIDATION_ERROR
        except OSError:
            category = ErrorCategory.DEPENDENCY_FAILURE
        except FAILURES:
            pass
        return ReconciliationResult(
            job,
            ReconciliationStatus.COMPLETED
            if completed
            else ReconciliationStatus.UNRESOLVED,
            error=category,
            reason=reason,
            evidence=evidence,
        )


@dataclass(frozen=True)
class ComfyTextToImageAdapter(ComfyEngine[ApprovedWorkflow]):
    """TextToImagePort + JobReconciliationPort over any admitted driver."""

    def __post_init__(self) -> None:
        if type(self.workflow) is not ApprovedWorkflow:
            raise TypeError("validated workflow and policy required")
        super().__post_init__()

    async def generate(self, request: TextToImageRequest) -> GenerationResult:
        if type(request) is not TextToImageRequest:
            raise TypeError("TextToImageRequest required")

        async def prepare(budget: Budget, run: RunState) -> tuple[dict[str, Any], int]:
            graph = self.workflow.graph(request)
            await self._preflight(budget)
            return graph, request.seed if request.seed is not None else 0

        return await self._execute(prepare)


@dataclass(frozen=True, slots=True)
class ComfyUIConfig:
    """Loopback legacy profile; configuration files use config.load_config."""

    workflow: ApprovedWorkflow
    endpoint: Endpoint = Endpoint()
    binding: str = "comfyui-local"
    completion: CompletionPolicy = CompletionPolicy()

    def __post_init__(self) -> None:
        if (
            type(self.workflow) is not ApprovedWorkflow
            or type(self.endpoint) is not Endpoint
            or type(self.completion) is not CompletionPolicy
        ):
            raise TypeError("validated workflow, endpoint and policy required")
        identifier(self.binding)


@dataclass(frozen=True)
class LocalComfyUIAdapter:
    """Legacy driver over loopback HTTP; the validated local profile."""

    config: ComfyUIConfig
    transport: Transport | None = field(default=None, repr=False)
    clock: Callable[[], float] = field(default=time.monotonic, repr=False)
    sleep: Callable[[float], Awaitable[None]] = field(default=asyncio.sleep, repr=False)
    _engine: ComfyTextToImageAdapter = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if type(self.config) is not ComfyUIConfig:
            raise TypeError("ComfyUIConfig required")
        engine = ComfyTextToImageAdapter(
            self.config.workflow,
            LegacyDriver(self._http()),
            self.config.binding,
            self.config.completion,
            clock=self.clock,
            sleep=self.sleep,
        )
        object.__setattr__(self, "_engine", engine)

    def _http(self) -> Transport:
        if self.transport is not None:
            return self.transport
        return LocalHTTP(
            self.config.endpoint, self.config.completion.request_timeout_seconds
        )

    async def generate(self, request: TextToImageRequest) -> GenerationResult:
        return await self._engine.generate(request)

    async def reconcile(self, job: ProviderJobRef) -> ReconciliationResult:
        return await self._engine.reconcile(job)


# No global interrupt, queue clear, deletion, retry or output-directory access.
