"""Virtual try-on over the shared engine (ADR-020): fail before disclosure.

Order per invocation:

1. request checked;
2. local deployment and `input_upload` capability checked;
3. node/model preflight (legacy object_info);
4. person upload, then garment upload, each once;
5. the approved TRY_ON template is patched;
6. exactly one submission;
7. bounded wait, then one validated PNG.

Anything that fails before step 6 never submits. Disclosure is reported
separately from job effect, as a named effect.
"""

from dataclasses import dataclass
from typing import Any

from legoai.kernel.effects import EffectExtent
from legoai.kernel.errors import ErrorCategory

from .comfyui import ComfyEngine, Refused, RunState
from .drivers.base import Budget
from .transfer import ImageTransfer
from .tryon import ApprovedTryOnWorkflow
from .values import GenerationResult, Outcome, TryOnRequest


@dataclass(frozen=True)
class ComfyVirtualTryOnAdapter(ComfyEngine[ApprovedTryOnWorkflow]):
    """VirtualTryOnPort over any admitted driver; local providers only."""

    # From configuration (deployment = "local"); remote personal images refused.
    local: bool = False

    def __post_init__(self) -> None:
        if type(self.workflow) is not ApprovedTryOnWorkflow:
            raise TypeError("approved try-on workflow required")
        super().__post_init__()

    async def try_on(self, request: TryOnRequest) -> GenerationResult:
        if type(request) is not TryOnRequest:
            raise TypeError("TryOnRequest required")

        async def prepare(budget: Budget, run: RunState) -> tuple[dict[str, Any], int]:
            if not self.local:
                raise Refused(
                    GenerationResult(
                        Outcome.FAILED,
                        EffectExtent.NONE,
                        error=ErrorCategory.POLICY_VIOLATION,
                        reason="remote_personal_images_forbidden",
                    )
                )
            if not self.profile.capabilities.input_upload:
                raise Refused(
                    GenerationResult(
                        Outcome.FAILED,
                        EffectExtent.NONE,
                        error=ErrorCategory.VERSION_MISMATCH,
                        reason="capability_missing",
                    )
                )
            # Privacy: prove nodes and model files exist before any disclosure.
            await self._preflight(budget)
            # Conservative while bytes may be in flight (deadline/cancellation).
            run.disclosure = EffectExtent.UNKNOWN
            transfer = await ImageTransfer(
                self.driver, self.local, self.completion, self.clock
            ).upload((request.person, request.garment), budget=budget)
            run.disclosure = transfer.disclosure
            if not transfer.ok:
                raise Refused(
                    GenerationResult(
                        Outcome.FAILED,
                        EffectExtent.NONE,
                        error=transfer.error,
                        reason=transfer.reason,
                        evidence=transfer.evidence,
                        input_disclosure=transfer.disclosure,
                    )
                )
            run.category = ErrorCategory.VALIDATION_ERROR
            person, garment = transfer.uploaded
            graph = self.workflow.graph(person, garment, request.seed)
            run.category = ErrorCategory.DEPENDENCY_FAILURE
            return graph, request.seed if request.seed is not None else 0

        return await self._execute(prepare)


# No retry, re-upload, delete, record-delete or remote transfer.
