"""ADR-027 deferred: refuse material paths before any lookup or construction."""

import asyncio
import os
from collections.abc import Iterator, Mapping
from dataclasses import replace
from pathlib import Path
from unittest.mock import Mock

import pytest
from legoai.kernel.errors import ErrorCategory
from media_support import FakeHTTP, Transports, write_workflow

from legoai_generative_media import config as configuration
from legoai_generative_media import service
from legoai_generative_media.config import (
    GenerationConfig,
    ProviderConfig,
    TryOnConfig,
    TryOnWorkflowConfig,
    WorkflowConfig,
)
from legoai_generative_media.http import Endpoint, LocalHTTP, RemoteHTTPS
from legoai_generative_media.service import ProviderError

REASON = "credentialled_provider_unsupported"
LOCAL = "http://127.0.0.1:8188"
REMOTE = "https://media.example.org"


class ForbiddenMapping(Mapping[str, str]):
    def __getitem__(self, key: str) -> str:
        raise AssertionError("credential mapping read")

    def __iter__(self) -> Iterator[str]:
        raise AssertionError("credential mapping iterated")

    def __len__(self) -> int:
        raise AssertionError("credential mapping inspected")


def candidate(family: str, remote: bool) -> GenerationConfig:
    return GenerationConfig(
        ProviderConfig(
            REMOTE if remote else LOCAL,
            api_family=family,
            deployment="remote" if remote else "local",
            auth="bearer",
            secret_ref="env:SENSITIVE_REFERENCE_CANARY",
            allowed_origins=(REMOTE,) if remote else (),
        ),
        WorkflowConfig(Path("not-read.json"), "0" * 64, "test.safetensors"),
    )


def try_on(config: GenerationConfig) -> TryOnConfig:
    return TryOnConfig(
        config.provider,
        TryOnWorkflowConfig(
            Path("not-read.json"),
            "0" * 64,
            "d.safetensors",
            "t.safetensors",
            "v.safetensors",
        ),
    )


@pytest.mark.parametrize("family", ["auto", "legacy", "v2"])
@pytest.mark.parametrize("remote", [False, True])
@pytest.mark.parametrize("supplied", [False, True])
@pytest.mark.parametrize("injected", [False, True])
@pytest.mark.parametrize("operation", ["probe", "text", "transfer", "vto", "preflight"])
def test_refusal_precedes_all_material_and_provider_work(
    monkeypatch: pytest.MonkeyPatch,
    family: str,
    remote: bool,
    supplied: bool,
    injected: bool,
    operation: str,
) -> None:
    config = candidate(family, remote)
    spies: list[Mock] = []
    for owner, names in (
        (configuration, ("resolve_secret",)),
        (
            service,
            ("default_transports", "LocalHTTP", "RemoteHTTPS", "discover", "confirm"),
        ),
        (WorkflowConfig, ("load",)),
        (TryOnWorkflowConfig, ("load",)),
        (asyncio, ("open_connection",)),
    ):
        for name in names:
            spy = Mock(side_effect=AssertionError("forbidden downstream work"))
            monkeypatch.setattr(owner, name, spy)
            spies.append(spy)
    factory = Mock(side_effect=AssertionError("transport construction forbidden"))
    spies.append(factory)
    mapping = ForbiddenMapping()
    expected = (
        "remote_personal_images_forbidden" if remote and operation == "vto" else REASON
    )

    async def scenario() -> None:
        # Install only after the event loop exists; pytest itself needs its environment.
        with monkeypatch.context() as scoped:
            scoped.setattr(os, "environ", mapping)
            environment = mapping if supplied else None
            transport = factory if injected else None
            if operation == "preflight":
                report = await service.preflight_virtual_try_on(
                    try_on(config), environ=environment, transports=transport
                )
                assert not report.ok
                message = "remote personal images forbidden" if remote else REASON
                assert message in str(report.lines)
                return
            with pytest.raises(ProviderError) as caught:
                if operation == "probe":
                    await service.probe_provider(
                        config, environ=environment, transports=transport
                    )
                elif operation == "text":
                    await service.open_text_to_image(
                        config, environ=environment, transports=transport
                    )
                elif operation == "transfer":
                    await service.open_image_transfer(
                        config, environ=environment, transports=transport
                    )
                else:
                    await service.open_virtual_try_on(
                        try_on(config), environ=environment, transports=transport
                    )
            assert str(caught.value) == expected
            assert caught.value.category is ErrorCategory.POLICY_VIOLATION
            assert caught.value.evidence == ()
            assert caught.value.__cause__ is None and caught.value.__context__ is None

    asyncio.run(scenario())
    for spy in spies:
        spy.assert_not_called()


def test_direct_resolver_never_reads_mapping() -> None:
    assert configuration.resolve_secret(None, ForbiddenMapping()) is None
    with pytest.raises(ProviderError, match=REASON):
        configuration.resolve_secret(
            "env:SENSITIVE_REFERENCE_CANARY", ForbiddenMapping()
        )


@pytest.mark.parametrize("token", ["", "synthetic-canary", "not valid\r\n"])
def test_direct_transports_refuse_before_tls_or_material_processing(
    monkeypatch: pytest.MonkeyPatch, token: str
) -> None:
    import ssl

    tls = Mock(side_effect=AssertionError("TLS construction forbidden"))
    monkeypatch.setattr(ssl, "create_default_context", tls)
    for make in (
        lambda: LocalHTTP(Endpoint(), token=token),
        lambda: RemoteHTTPS(REMOTE, token=token),
    ):
        with pytest.raises(ValueError) as caught:
            make()
        assert str(caught.value) == REASON
    tls.assert_not_called()


def test_default_factory_rejects_config_and_direct_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    factory = service.default_transports(ProviderConfig(LOCAL))
    constructor = Mock(side_effect=AssertionError("HTTP construction forbidden"))
    monkeypatch.setattr(service, "LocalHTTP", constructor)
    with pytest.raises(ProviderError, match=REASON):
        service.default_transports(candidate("legacy", False).provider)
    with pytest.raises(ProviderError, match=REASON):
        factory(LOCAL, "synthetic-canary")
    constructor.assert_not_called()


def test_exchange_cannot_serialize_authorization() -> None:
    from legoai_generative_media.http import _exchange

    reader = Mock(side_effect=AssertionError("response read forbidden"))
    writer = Mock()
    writer.write.side_effect = AssertionError("send forbidden")
    with pytest.raises(ValueError, match=REASON):
        asyncio.run(
            _exchange(reader, writer, "127.0.0.1", "GET", "/", b"", 100, (), "canary")
        )
    assert reader.mock_calls == [] and writer.mock_calls == []


def test_existing_driver_headers_remain_supported() -> None:
    from legoai_generative_media.http import _check

    _check(
        "POST",
        "/upload/image",
        b"synthetic",
        100,
        (("Content-Type", "multipart/form-data; boundary=test"),),
    )
    _check("POST", "/api/v2/jobs", b"{}", 100, (("Idempotency-Key", "synthetic"),))


@pytest.mark.parametrize(
    "header", ["Authorization", "X-API-Key", "Cookie", "X-Credential"]
)
def test_header_material_refused_before_connect(
    monkeypatch: pytest.MonkeyPatch, header: str
) -> None:
    network = Mock(side_effect=AssertionError("network forbidden"))
    monkeypatch.setattr(asyncio, "open_connection", network)
    with pytest.raises(ValueError, match="forbidden header"):
        asyncio.run(
            LocalHTTP(Endpoint()).request(
                "GET", "/", limit=100, headers=((header, "canary"),)
            )
        )
    network.assert_not_called()


def test_secret_free_diagnostic_ignores_even_supplied_mapping(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path, sha = write_workflow(tmp_path)
    config = replace(
        candidate("legacy", False),
        provider=ProviderConfig(LOCAL, api_family="legacy"),
        workflow=WorkflowConfig(path, sha, "test.safetensors"),
    )
    fake = FakeHTTP()
    transports = Transports({LOCAL: fake})

    async def scenario() -> None:
        with monkeypatch.context() as scoped:
            scoped.setattr(os, "environ", ForbiddenMapping())
            profile = await service.probe_provider(
                config, environ=ForbiddenMapping(), transports=transports
            )
        assert profile.family == "legacy"

    asyncio.run(scenario())
    assert transports.opened == [(LOCAL, None)]
    assert fake.calls and all(call[0] == "GET" for call in fake.calls)
