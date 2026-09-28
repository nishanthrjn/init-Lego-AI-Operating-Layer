"""Upload -> single submission composition: order, patching, attempt limits."""

import asyncio
import re
from typing import Any

import pytest
from legoai.kernel.effects import EffectExtent
from legoai.kernel.errors import ErrorCategory
from media_support import TRYON_MODELS, FakeHTTP, tryon_adapter, tryon_request

from legoai_generative_media.drivers.base import Budget, Submission, SubmissionRejected
from legoai_generative_media.drivers.legacy import LegacyDriver
from legoai_generative_media.tryon import INSTRUCTION, ApprovedTryOnWorkflow
from legoai_generative_media.values import GenerationResult, Outcome

REQUEST = tryon_request(seed=7)


def run(http: FakeHTTP, *modes: str, driver: Any = None) -> GenerationResult:
    http.upload_modes = list(modes)
    result: GenerationResult = asyncio.run(
        tryon_adapter(http, driver=driver).try_on(REQUEST)
    )
    return result


def names(http: FakeHTTP) -> list[str]:
    out = []
    for body in http.uploaded:
        match = re.search(rb'filename="([^"]+)"', body)
        assert match is not None
        out.append(match.group(1).decode())
    return out


def test_success_uploads_twice_then_submits_once() -> None:
    http = FakeHTTP()
    result = run(http)
    assert result.outcome is Outcome.SUCCESS
    assert result.effect is EffectExtent.COMPLETED
    assert result.input_disclosure is EffectExtent.COMPLETED
    assert http.uploads() == 2 and len(http.prompts()) == 1
    # Person first, garment second.
    assert REQUEST.person.content in http.uploaded[0]
    assert REQUEST.garment.content in http.uploaded[1]
    graph = http.prompts()[0]
    person, garment = names(http)
    assert graph["6"]["inputs"]["image"] == f"{person} [temp]"
    assert graph["7"]["inputs"]["image"] == f"{garment} [temp]"
    assert graph["13"]["inputs"]["seed"] == 7
    assert graph["11"]["inputs"]["prompt"] == INSTRUCTION
    assert graph["1"]["inputs"]["unet_name"] == TRYON_MODELS.diffusion_model
    assert graph["2"]["inputs"]["clip_name"] == TRYON_MODELS.text_encoder
    assert graph["3"]["inputs"]["vae_name"] == TRYON_MODELS.vae
    assert (graph["8"]["inputs"]["width"], graph["8"]["inputs"]["height"]) == (
        768,
        1024,
    )
    assert result.image is not None
    assert (result.image.width, result.image.height) == (768, 1024)
    assert result.image.seed == 7
    assert len([c for c in http.calls if c[1].startswith("/view")]) == 1
    order = [c[1] for c in http.calls if c[0] == "POST"]
    assert order == ["/upload/image", "/upload/image", "/prompt"]


@pytest.mark.parametrize(
    "modes,disclosure,attempts",
    [
        (("not_sent",), EffectExtent.NONE, 1),
        (("lost",), EffectExtent.UNKNOWN, 1),
        (("rename",), EffectExtent.PARTIAL, 1),
        (("ok", "not_sent"), EffectExtent.PARTIAL, 2),
        (("ok", "lost"), EffectExtent.UNKNOWN, 2),
        (("ok", "status500"), EffectExtent.UNKNOWN, 2),
    ],
)
def test_transfer_failure_never_submits(
    modes: tuple[str, ...], disclosure: EffectExtent, attempts: int
) -> None:
    http = FakeHTTP()
    result = run(http, *modes)
    assert result.outcome is Outcome.FAILED
    assert result.effect is EffectExtent.NONE
    assert result.input_disclosure is disclosure
    assert http.uploads() == attempts  # Each upload at most once.
    assert http.prompts() == []  # POST /prompt count = 0.


def test_workflow_patch_failure_never_submits(monkeypatch: pytest.MonkeyPatch) -> None:
    def broken(*args: object) -> None:
        raise ValueError("patch failure")

    monkeypatch.setattr(ApprovedTryOnWorkflow, "graph", broken)
    http = FakeHTTP()
    result = run(http)
    assert result.effect is EffectExtent.NONE
    assert result.input_disclosure is EffectExtent.COMPLETED
    assert result.error is ErrorCategory.VALIDATION_ERROR
    assert http.uploads() == 2 and http.prompts() == []


def test_definite_submission_rejection_is_no_job_effect() -> None:
    class Rejecting(LegacyDriver):
        async def submit(self, budget: Budget, graph: dict[str, Any]) -> Submission:
            raise SubmissionRejected(ErrorCategory.VALIDATION_ERROR, "invalid_workflow")

    http = FakeHTTP()
    result = run(http, driver=Rejecting(http))
    assert result.effect is EffectExtent.NONE
    assert result.input_disclosure is EffectExtent.COMPLETED
    assert result.reason == "invalid_workflow" and result.job is None


def test_lost_submission_acknowledgement_is_unknown_and_not_retried() -> None:
    http = FakeHTTP()
    http.fail_at = "/prompt"
    result = run(http)
    assert result.effect is EffectExtent.UNKNOWN
    assert result.input_disclosure is EffectExtent.COMPLETED
    assert len([c for c in http.calls if c[:2] == ("POST", "/prompt")]) == 1
    assert http.uploads() == 2


def test_retrieval_failure_keeps_completed_generation() -> None:
    http = FakeHTTP()
    http.fail_at = "/view"
    result = run(http)
    assert result.outcome is Outcome.FAILED
    assert result.effect is EffectExtent.COMPLETED
    assert result.error is ErrorCategory.DEPENDENCY_FAILURE
    assert result.input_disclosure is EffectExtent.COMPLETED
    assert len(http.prompts()) == 1


def test_node_errors_after_submission_are_unknown() -> None:
    http = FakeHTTP()
    http.submission = {"prompt_id": "job-1", "node_errors": {"8": "bad"}}
    result = run(http)
    assert result.effect is EffectExtent.UNKNOWN and len(http.prompts()) == 1
