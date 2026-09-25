import asyncio
from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest
from legoai.capabilities.values import CapabilityRequirement, CapabilityVersionRange
from legoai.execution.ports import ExecutionTransitionError
from legoai.execution.values import ExecutionState
from legoai.kernel.effects import EffectExtent
from legoai.kernel.versions import Version
from legoai.plugins.ports import PluginLifecycleState
from media_support import FakeHTTP, workflow

from legoai_generative_media.comfyui import ComfyUIConfig, LocalComfyUIAdapter
from legoai_generative_media.composition import invoke, select
from legoai_generative_media.local_host import prepare_local
from legoai_generative_media.values import Outcome, TextToImageRequest


def test_governed_success_and_replay() -> None:
    async def run() -> None:
        http = FakeHTTP()
        session = await prepare_local(
            LocalComfyUIAdapter(ComfyUIConfig(workflow()), http),
            "r1",
            approved=workflow().reference,
        )
        args = (
            session.coordinator,
            session.ready,
            session.context,
            session.contribution,
            session.contribution.revision,
            TextToImageRequest("x"),
        )
        execution, result = await invoke(*args)
        assert execution.final_state is ExecutionState.SUCCEEDED
        assert result.outcome is Outcome.SUCCESS
        with pytest.raises(ExecutionTransitionError):
            await invoke(*args)
        assert len([c for c in http.calls if c[0] == "POST"]) == 1

    asyncio.run(run())


@pytest.mark.parametrize(
    "case", ["unknown", "stale", "disabled", "incompatible", "unpublished"]
)
def test_selection(case: str) -> None:
    async def run() -> None:
        http = FakeHTTP()
        session = await prepare_local(
            LocalComfyUIAdapter(ComfyUIConfig(workflow()), http),
            "r1",
            approved=workflow().reference,
        )
        chosen = session.contribution
        revision = chosen.revision
        requirement = session.requirement
        binding = chosen.binding
        catalog = session.catalog
        if case == "unknown":
            binding = "other"
        elif case == "stale":
            revision = replace(revision, revision="r2")
        elif case == "disabled":
            chosen = replace(
                chosen,
                activation=replace(
                    chosen.activation, state=PluginLifecycleState.STOPPED
                ),
            )
        elif case == "incompatible":
            requirement = CapabilityRequirement(
                requirement.capability, CapabilityVersionRange(Version(9, 0, 0))
            )
        else:
            from legoai.reference.catalog import InMemoryCatalog

            catalog = InMemoryCatalog()
        with pytest.raises(ValueError):
            select(
                requirement, binding, revision, (chosen,), catalog, datetime.now(UTC)
            )
        assert http.calls == []

    asyncio.run(run())


def test_execution_deadline_retains_job() -> None:
    async def run() -> None:
        http = FakeHTTP()
        http.wait_at = "/history"
        session = await prepare_local(
            LocalComfyUIAdapter(ComfyUIConfig(workflow()), http),
            "r1",
            approved=workflow().reference,
        )
        context = replace(
            session.context, deadline=datetime.now(UTC) + timedelta(seconds=0.1)
        )
        execution, output = await invoke(
            session.coordinator,
            session.ready,
            context,
            session.contribution,
            session.contribution.revision,
            TextToImageRequest("x"),
        )
        assert output.outcome is Outcome.DEADLINE
        assert output.job is not None and output.effect is EffectExtent.UNKNOWN
        assert execution.final_state is ExecutionState.FAILED

    asyncio.run(run())
