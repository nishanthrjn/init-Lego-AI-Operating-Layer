import asyncio
from dataclasses import replace

import pytest
from legoai.execution.values import ExecutionState
from legoai.kernel.effects import EffectExtent
from legoai.runtime.api import HostError, HostFailure
from media_support import FakeHTTP, workflow

from legoai_generative_media.comfyui import ComfyUIConfig, LocalComfyUIAdapter
from legoai_generative_media.composition import invoke
from legoai_generative_media.local_host import prepare_local
from legoai_generative_media.values import GenerationCancelled, Outcome, TextToImageRequest


def test_governed_success_and_replay() -> None:
    async def run() -> None:
        http = FakeHTTP()
        session = await prepare_local(
            LocalComfyUIAdapter(ComfyUIConfig(workflow()), http),
            "r1",
            approved=workflow().reference,
        )
        args = (
            session.execution,
            session.ready,
            session.context,
            session.contribution,
            session.contribution.revision,
            TextToImageRequest("x"),
        )
        execution, result = await invoke(*args)
        assert execution.final_state is ExecutionState.SUCCEEDED
        assert result.outcome is Outcome.SUCCESS
        with pytest.raises(HostError) as duplicate:
            await invoke(*args)
        assert duplicate.value.failure is HostFailure.DUPLICATE_CLAIM
        assert len([c for c in http.calls if c[0] == "POST"]) == 1
        assert await session.execution.close() == ()

    asyncio.run(run())


@pytest.mark.parametrize("case", ["foreign", "stale", "revoked", "retired"])
def test_public_claim_refuses_without_provider_effect(case: str) -> None:
    async def run() -> None:
        http = FakeHTTP()
        session = await prepare_local(
            LocalComfyUIAdapter(ComfyUIConfig(workflow()), http),
            "r1",
            approved=workflow().reference,
        )
        chosen = session.contribution
        revision = chosen.revision
        context = session.context
        if case == "foreign":
            context = replace(context)
        elif case == "stale":
            revision = replace(revision, revision="r2")
        elif case == "revoked":
            session.execution.revoke_authority()
        else:
            session.execution.retire_contribution()
        with pytest.raises(HostError) as refused:
            await invoke(
                session.execution,
                session.ready,
                context,
                chosen,
                revision,
                TextToImageRequest("x"),
            )
        assert refused.value.failure is {
            "foreign": HostFailure.FOREIGN_CONTEXT,
            "stale": HostFailure.STALE_CONFIGURATION,
            "revoked": HostFailure.UNAUTHORIZED,
            "retired": HostFailure.UNKNOWN_BINDING,
        }[case]
        assert http.calls == []
        assert await session.execution.close() == (session.context.execution_id,)

    asyncio.run(run())


def test_execution_deadline_retains_job() -> None:
    async def run() -> None:
        http = FakeHTTP()
        http.wait_at = "/history"
        session = await prepare_local(
            LocalComfyUIAdapter(ComfyUIConfig(workflow()), http),
            "r1",
            approved=workflow().reference,
            timeout=0.1,
        )
        execution, output = await invoke(
            session.execution,
            session.ready,
            session.context,
            session.contribution,
            session.contribution.revision,
            TextToImageRequest("x"),
        )
        assert output.outcome is Outcome.DEADLINE
        assert output.job is not None and output.effect is EffectExtent.UNKNOWN
        assert execution.final_state is ExecutionState.FAILED
        assert await session.execution.close() == ()

    asyncio.run(run())


def test_in_flight_replay_cannot_submit_again() -> None:
    async def run() -> None:
        http = FakeHTTP()
        http.wait_at = "/history"
        async with await prepare_local(
            LocalComfyUIAdapter(ComfyUIConfig(workflow()), http),
            "r1",
            approved=workflow().reference,
        ) as session:
            args = (
                session.execution,
                session.ready,
                session.context,
                session.contribution,
                session.contribution.revision,
                TextToImageRequest("x"),
            )
            first = asyncio.create_task(invoke(*args))
            await http.entered.wait()
            try:
                with pytest.raises(HostError) as duplicate:
                    await invoke(*args)
                assert duplicate.value.failure is HostFailure.DUPLICATE_CLAIM
                assert len(http.prompts()) == 1
            finally:
                first.cancel()
                with pytest.raises(GenerationCancelled) as cancelled:
                    await first
                assert cancelled.value.result.effect is EffectExtent.UNKNOWN
        assert await session.execution.close() == ()

    asyncio.run(run())
