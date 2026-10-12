"""Media owner integration with real public controls and fake provider I/O."""

import asyncio
import inspect
from dataclasses import fields
from pathlib import Path
from unittest.mock import AsyncMock, Mock

import pytest
from legoai.execution.values import ExecutionResult, ExecutionState
from legoai.kernel.effects import EffectExtent
from legoai.kernel.errors import ErrorCategory
from legoai.kernel.identity import PrincipalId
from legoai.kernel.references import PrincipalRef
from legoai.kernel.versions import Version
from legoai.plugins.values import PluginId
from legoai.runtime.api import GovernedExecutionConfig, HostError, HostFailure
from legoai.runtime.local import GovernedExecution, open_governed_execution
from media_support import (
    TRYON_MODELS,
    FakeHTTP,
    Transports,
    tryon_request,
    workflow,
    write_tryon_workflow,
    write_workflow,
)

from legoai_generative_media import local_host
from legoai_generative_media import service as media_service
from legoai_generative_media.comfyui import ComfyUIConfig, LocalComfyUIAdapter
from legoai_generative_media.composition import (
    OFFER,
    TRY_ON_OFFER,
    _SettlementFailure,
    invoke,
)
from legoai_generative_media.config import parse_config, parse_try_on_config
from legoai_generative_media.drivers.base import ProviderError
from legoai_generative_media.local_host import _UnsettledExecution, prepare_local
from legoai_generative_media.service import TextToImageService, TryOnService
from legoai_generative_media.values import (
    GenerationCancelled,
    GenerationResult,
    Outcome,
    TextToImageRequest,
    TryOnRequest,
)

LOCAL = "http://127.0.0.1:8188"


async def build(
    root: Path, http: FakeHTTP, try_on: bool
) -> TextToImageService | TryOnService:
    provider = {"type": "comfyui", "endpoint": LOCAL, "api_family": "legacy"}
    transports = Transports({LOCAL: http})
    if try_on:
        path, sha = write_tryon_workflow(root)
        http.use_tryon_job()
        config = parse_try_on_config(
            {
                "provider": provider,
                "try_on": {
                    "path": str(path),
                    "sha256": sha,
                    "diffusion_model": TRYON_MODELS.diffusion_model,
                    "text_encoder": TRYON_MODELS.text_encoder,
                    "vae": TRYON_MODELS.vae,
                },
            },
            root,
        )
        return await media_service.open_virtual_try_on(config, transports=transports)
    path, sha = write_workflow(root)
    text_config = parse_config(
        {
            "provider": provider,
            "workflow": {
                "path": str(path),
                "sha256": sha,
                "checkpoint": "test.safetensors",
            },
        },
        root,
    )
    return await media_service.open_text_to_image(text_config, transports=transports)


async def call(service: TextToImageService | TryOnService) -> GenerationResult:
    if isinstance(service, TryOnService):
        return await service.try_on(tryon_request())
    return await service.generate(TextToImageRequest("untrusted prompt", 7))


@pytest.mark.parametrize("try_on", [False, True])
@pytest.mark.parametrize(
    "failure,effect",
    [
        (None, EffectExtent.COMPLETED),
        ("/prompt", EffectExtent.UNKNOWN),
        ("/object_info", EffectExtent.NONE),
    ],
)
def test_services_use_public_claim_and_settlement_once(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    try_on: bool,
    failure: str | None,
    effect: EffectExtent,
) -> None:
    captured: list[GovernedExecutionConfig] = []
    handles: list[GovernedExecution] = []
    spies: list[tuple[AsyncMock, AsyncMock, AsyncMock]] = []

    def open_spy(config: GovernedExecutionConfig) -> GovernedExecution:
        captured.append(config)
        execution = open_governed_execution(config)
        handles.append(execution)
        claim = AsyncMock(wraps=execution.claim)
        settle = AsyncMock(wraps=execution.settle)
        close = AsyncMock(wraps=execution.close)
        monkeypatch.setattr(execution, "claim", claim)
        monkeypatch.setattr(execution, "settle", settle)
        monkeypatch.setattr(execution, "close", close)
        spies.append((claim, settle, close))
        return execution

    monkeypatch.setattr(local_host, "open_governed_execution", open_spy)

    async def scenario() -> None:
        http = FakeHTTP()
        service = await build(tmp_path, http, try_on)
        assert captured == []  # Construction/diagnostics is not invocation.
        secret = Mock(side_effect=AssertionError("no invocation credential lookup"))
        monkeypatch.setattr(media_service, "resolve_secret", secret)
        http.fail_at = failure or ""
        result = await call(service)
        assert result.effect is effect
        assert result.outcome is (Outcome.SUCCESS if failure is None else Outcome.FAILED)
        sent = failure != "/object_info"
        assert len(http.prompts()) == int(sent)
        assert http.uploads() == (2 if try_on and sent else 0)
        assert result.input_disclosure is (
            EffectExtent.COMPLETED if try_on and sent else EffectExtent.NONE
        )
        assert len(captured) == len(spies) == 1
        config = captured[0]
        assert config.offer == (TRY_ON_OFFER if try_on else OFFER)
        assert config.declaration.plugin_id == PluginId("legoai", "local-comfyui")
        assert config.declaration.release == Version(1, 0, 0)
        assert config.declaration.offers == (config.offer,)
        assert config.principal == PrincipalRef("local-host", PrincipalId("operator"))
        assert config.configuration.revision == service.config.digest
        assert config.grant.action == "invoke-capability"
        assert config.grant.resource_scope == config.offer.capability.value
        assert config.max_executions == 1
        claim, settle, close = spies[0]
        assert claim.await_count == settle.await_count == close.await_count == 1
        assert settle.call_args is not None
        observed = settle.call_args.args[1]
        assert type(observed) is ExecutionResult
        assert observed.effect is effect
        assert observed.final_state is (
            ExecutionState.SUCCEEDED if failure is None else ExecutionState.FAILED
        )
        assert await handles[0].close() == ()
        secret.assert_not_called()

    asyncio.run(scenario())


@pytest.mark.parametrize(
    "failure,category",
    [
        (HostFailure.UNAUTHORIZED, ErrorCategory.POLICY_VIOLATION),
        (HostFailure.DEADLINE_EXCEEDED, ErrorCategory.DEADLINE_EXCEEDED),
        (HostFailure.STALE_CONFIGURATION, ErrorCategory.CONFLICT),
    ],
)
def test_facade_open_refusal_is_a_sanitized_media_error(
    monkeypatch: pytest.MonkeyPatch,
    failure: HostFailure,
    category: ErrorCategory,
) -> None:
    factory = Mock(side_effect=HostError(failure))
    monkeypatch.setattr(local_host, "open_governed_execution", factory)
    http = FakeHTTP()
    with pytest.raises(ProviderError) as caught:
        asyncio.run(
            prepare_local(
                LocalComfyUIAdapter(ComfyUIConfig(workflow()), http),
                "r1",
                approved=workflow().reference,
            )
        )
    assert caught.value.category is category
    assert str(caught.value) == "media_execution_refused"
    assert caught.value.__cause__ is None and caught.value.evidence == ()
    assert http.calls == []


@pytest.mark.parametrize("try_on", [False, True])
def test_completed_generation_survives_retrieval_failure(
    tmp_path: Path, try_on: bool
) -> None:
    async def scenario() -> None:
        http = FakeHTTP()
        service = await build(tmp_path, http, try_on)
        http.fail_at = "/view"
        result = await call(service)
        assert result.outcome is Outcome.FAILED
        assert result.effect is EffectExtent.COMPLETED
        assert result.error is ErrorCategory.DEPENDENCY_FAILURE
        assert len(http.prompts()) == 1

    asyncio.run(scenario())


@pytest.mark.parametrize("try_on", [False, True])
def test_reconciliation_and_diagnostics_do_not_open_execution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, try_on: bool
) -> None:
    facade = Mock(side_effect=AssertionError("diagnostics cannot invoke"))
    monkeypatch.setattr(local_host, "open_governed_execution", facade)

    async def scenario() -> None:
        http = FakeHTTP()
        service = await build(tmp_path, http, try_on)
        result = await service.reconcile(service.job("job-1"))
        assert result.image is not None
        if isinstance(service, TextToImageService):
            profile = await media_service.probe_provider(
                service.config, transports=Transports({LOCAL: http})
            )
            assert profile.family == "legacy"
        assert all(method == "GET" for method, _, _ in http.calls)
        facade.assert_not_called()

    asyncio.run(scenario())


def test_unclaimed_close_is_explicit_and_retains_custody() -> None:
    async def scenario() -> None:
        http = FakeHTTP()
        session = await prepare_local(
            LocalComfyUIAdapter(ComfyUIConfig(workflow()), http),
            "r1",
            approved=workflow().reference,
        )
        with pytest.raises(_UnsettledExecution) as caught:
            async with session:
                session.execution.revoke_authority()
                await invoke(
                    session.execution,
                    session.ready,
                    session.context,
                    session.contribution,
                    session.contribution.revision,
                    TextToImageRequest("x"),
                )
        assert isinstance(caught.value, ProviderError)
        assert str(caught.value) == "media_execution_unsettled"
        assert caught.value.evidence == () and caught.value.__cause__ is None
        assert caught.value._execution is session.execution
        assert caught.value._unresolved == (session.context.execution_id,)
        assert isinstance(caught.value._owner_failure, HostError)
        assert http.calls == []
        with pytest.raises(HostError) as closed:
            session.execution.establish()
        assert closed.value.failure is HostFailure.CLOSED

    asyncio.run(scenario())


def test_failed_settlement_keeps_completed_owner_receipt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def scenario() -> None:
        http = FakeHTTP()
        session = await prepare_local(
            LocalComfyUIAdapter(ComfyUIConfig(workflow()), http),
            "r1",
            approved=workflow().reference,
        )
        settle = AsyncMock(side_effect=HostError(HostFailure.WRONG_EXECUTION_STATE))
        monkeypatch.setattr(session.execution, "settle", settle)
        with pytest.raises(_UnsettledExecution) as caught:
            async with session:
                await invoke(
                    session.execution,
                    session.ready,
                    session.context,
                    session.contribution,
                    session.contribution.revision,
                    TextToImageRequest("x"),
                )
        receipt = caught.value._owner_failure
        assert isinstance(receipt, _SettlementFailure)
        assert receipt._observed.effect is EffectExtent.COMPLETED
        assert receipt._result.effect is EffectExtent.COMPLETED
        assert receipt._result.image is not None
        assert len(http.prompts()) == settle.await_count == 1

    asyncio.run(scenario())


def test_failed_close_never_reports_empty_obligations(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def scenario() -> None:
        session = await prepare_local(
            LocalComfyUIAdapter(ComfyUIConfig(workflow()), FakeHTTP()),
            "r1",
            approved=workflow().reference,
        )
        real_close = session.execution.close
        fault = RuntimeError("restricted close detail")
        monkeypatch.setattr(session.execution, "close", AsyncMock(side_effect=fault))
        with pytest.raises(_UnsettledExecution) as caught:
            async with session:
                pass
        assert caught.value._unresolved is None  # Unknown, never an empty receipt.
        assert caught.value._close_failure is fault
        assert "restricted" not in str(caught.value)
        assert caught.value._execution is session.execution
        assert await real_close() == (session.context.execution_id,)

    asyncio.run(scenario())


@pytest.mark.parametrize("stage", ["/upload/image", "/history"])
def test_service_cancellation_settles_and_closes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, stage: str
) -> None:
    captured: list[GovernedExecution] = []

    def factory(config: GovernedExecutionConfig) -> GovernedExecution:
        execution = open_governed_execution(config)
        captured.append(execution)
        return execution

    monkeypatch.setattr(local_host, "open_governed_execution", factory)

    async def scenario() -> None:
        http = FakeHTTP()
        service = await build(tmp_path, http, True)
        http.wait_at = stage
        task = asyncio.create_task(call(service))
        await http.entered.wait()
        task.cancel()
        with pytest.raises(GenerationCancelled) as caught:
            await task
        result = caught.value.result
        assert result.effect is (
            EffectExtent.NONE if stage == "/upload/image" else EffectExtent.UNKNOWN
        )
        assert result.input_disclosure is (
            EffectExtent.UNKNOWN if stage == "/upload/image" else EffectExtent.COMPLETED
        )
        assert await captured[0].close() == ()
        with pytest.raises(HostError) as closed:
            captured[0].establish()
        assert closed.value.failure is HostFailure.CLOSED

    asyncio.run(scenario())


def test_public_request_result_and_service_shapes() -> None:
    assert tuple(f.name for f in fields(TextToImageRequest)) == ("prompt", "seed")
    assert tuple(f.name for f in fields(TryOnRequest)) == ("person", "garment", "seed")
    assert tuple(f.name for f in fields(GenerationResult)) == (
        "outcome",
        "effect",
        "job",
        "image",
        "error",
        "cessation",
        "reason",
        "evidence",
        "input_disclosure",
    )
    for method in (TextToImageService.generate, TryOnService.try_on):
        assert tuple(inspect.signature(method).parameters) == ("self", "request")
    for method in (TextToImageService.reconcile, TryOnService.reconcile):
        assert tuple(inspect.signature(method).parameters) == ("self", "job")
