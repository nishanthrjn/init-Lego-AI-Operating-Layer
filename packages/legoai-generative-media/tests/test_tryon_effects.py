"""Disclosure and job effect stay independent through deadlines, cancellation
and the governed path."""

import asyncio

import pytest
from legoai.execution.values import ExecutionState
from legoai.kernel.effects import EffectExtent
from media_support import FakeHTTP, FakeTime, tryon_adapter, tryon_request

from legoai_generative_media.composition import TRY_ON_OFFER, invoke_try_on
from legoai_generative_media.local_host import prepare_local
from legoai_generative_media.values import Cessation, GenerationCancelled, Outcome


def test_generation_deadline_after_complete_transfer() -> None:
    http, time = FakeHTTP(), FakeTime()
    http.time, http.ready_at = time, 10_000
    result = asyncio.run(tryon_adapter(http, time, wait=300).try_on(tryon_request()))
    assert result.outcome is Outcome.DEADLINE
    assert result.effect is EffectExtent.UNKNOWN
    assert result.input_disclosure is EffectExtent.COMPLETED
    assert result.cessation is Cessation.UNKNOWN
    assert result.job is not None and len(http.prompts()) == 1


@pytest.mark.parametrize(
    "stage,effect,disclosure,prompts",
    [
        ("/upload/image", EffectExtent.NONE, EffectExtent.UNKNOWN, 0),
        ("/history", EffectExtent.UNKNOWN, EffectExtent.COMPLETED, 1),
    ],
)
def test_cancellation_keeps_both_facts(
    stage: str, effect: EffectExtent, disclosure: EffectExtent, prompts: int
) -> None:
    async def scenario() -> None:
        http = FakeHTTP()
        http.wait_at = stage
        task = asyncio.create_task(tryon_adapter(http).try_on(tryon_request()))
        await http.entered.wait()
        task.cancel()
        with pytest.raises(GenerationCancelled) as caught:
            await task
        result = caught.value.result
        assert result.effect is effect and result.input_disclosure is disclosure
        assert len(http.prompts()) == prompts

    asyncio.run(scenario())


def test_governed_success_propagates_disclosure() -> None:
    async def scenario() -> None:
        http = FakeHTTP()
        adapter = tryon_adapter(http)
        session = await prepare_local(
            adapter, "r1", approved=adapter.workflow.reference, offer=TRY_ON_OFFER
        )
        execution, output = await invoke_try_on(
            session.execution,
            session.ready,
            session.context,
            session.contribution,
            session.contribution.revision,
            tryon_request(),
        )
        assert execution.final_state is ExecutionState.SUCCEEDED
        assert output.input_disclosure is EffectExtent.COMPLETED
        assert session.contribution.entry.offer == TRY_ON_OFFER
        assert await session.execution.close() == ()

    asyncio.run(scenario())


def test_governed_deadline_keeps_disclosure_receipt() -> None:
    async def scenario() -> None:
        http = FakeHTTP()
        http.wait_at = "/history"
        adapter = tryon_adapter(http)
        session = await prepare_local(
            adapter,
            "r1",
            approved=adapter.workflow.reference,
            offer=TRY_ON_OFFER,
            timeout=0.3,
        )
        execution, output = await invoke_try_on(
            session.execution,
            session.ready,
            session.context,
            session.contribution,
            session.contribution.revision,
            tryon_request(),
        )
        assert output.outcome is Outcome.DEADLINE
        assert output.effect is EffectExtent.UNKNOWN
        assert output.input_disclosure is EffectExtent.COMPLETED
        assert execution.final_state is ExecutionState.FAILED
        assert await session.execution.close() == ()

    asyncio.run(scenario())


def test_governed_remote_refusal_is_nothing_sent() -> None:
    async def scenario() -> None:
        http = FakeHTTP()
        adapter = tryon_adapter(http, local=False)
        session = await prepare_local(
            adapter, "r1", approved=adapter.workflow.reference, offer=TRY_ON_OFFER
        )
        _, output = await invoke_try_on(
            session.execution,
            session.ready,
            session.context,
            session.contribution,
            session.contribution.revision,
            tryon_request(),
        )
        assert output.effect is EffectExtent.NONE
        assert output.input_disclosure is EffectExtent.NONE
        assert http.calls == []
        assert await session.execution.close() == ()

    asyncio.run(scenario())
