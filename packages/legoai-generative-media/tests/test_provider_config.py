"""Provider configuration: data-driven, strict, secret references only."""

import dataclasses
from pathlib import Path
from typing import Any

import pytest
from media_support import write_workflow

from legoai_generative_media.comfyui import CompletionPolicy
from legoai_generative_media.config import (
    GenerationConfig,
    load_config,
    local_config,
    parse_config,
    resolve_secret,
)
from legoai_generative_media.values import TextToImageRequest

EXAMPLES = Path(__file__).resolve().parents[3] / "examples" / "generative-media-minimal"
CLOUD = "https://cloud.comfy.org"
SECRET = "sk-live-DO-NOT-LEAK-0123456789"


def base(tmp_path: Path, **provider: Any) -> dict[str, Any]:
    path, sha = write_workflow(tmp_path)
    return {
        "provider": {
            "type": "comfyui",
            "endpoint": "http://127.0.0.1:8188",
            **provider,
        },
        "workflow": {
            "path": str(path),
            "sha256": sha,
            "checkpoint": "test.safetensors",
        },
    }


def cloud(tmp_path: Path, **extra: Any) -> dict[str, Any]:
    data = base(
        tmp_path,
        endpoint=CLOUD,
        api_family="v2",
        deployment="remote",
        binding="comfyui-cloud",
        allowed_origins=[CLOUD],
        download_origins=["https://storage.googleapis.com"],
        auth={"type": "bearer", "secret_ref": "env:COMFY_API_KEY"},
    )
    data["provider"].update(extra)
    return data


def test_local_legacy_profile(tmp_path: Path) -> None:
    config = parse_config(base(tmp_path, api_family="legacy"), tmp_path)
    assert (
        config.provider.deployment == "local" and config.provider.api_family == "legacy"
    )
    assert config.provider.auth == "none" and config.provider.secret_ref is None
    assert config.provider.completion == CompletionPolicy()
    assert config.workflow.load().reference.sha256 == config.workflow.sha256


def test_v2_self_hosted_profile(tmp_path: Path) -> None:
    config = parse_config(
        base(tmp_path, endpoint="http://127.0.0.1:8189", api_family="v2"), tmp_path
    )
    assert (
        config.provider.api_family == "v2"
        and config.provider.origin == "http://127.0.0.1:8189"
    )


def test_cloud_profile(tmp_path: Path) -> None:
    config = parse_config(cloud(tmp_path), tmp_path)
    assert config.provider.deployment == "remote"
    assert config.provider.secret_ref == "env:COMFY_API_KEY"
    assert config.provider.download_origins == ("https://storage.googleapis.com",)


def test_completion_policy_from_one_setting(tmp_path: Path) -> None:
    data = base(tmp_path)
    data["completion"] = {"max_wait_seconds": 900}
    assert parse_config(data, tmp_path).provider.completion == CompletionPolicy(
        900, 1, 10
    )
    data["completion"] = {"max_wait_seconds": 900, "poll_interval_seconds": 2}
    assert parse_config(data, tmp_path).provider.completion == CompletionPolicy(
        900, 2, 10
    )


@pytest.mark.parametrize(
    "change",
    [
        {"type": "openai"},
        {"api_family": "v3"},
        {"deployment": "edge"},
        {"endpoint": "http://localhost:8188"},
        {"endpoint": "http://192.168.1.5:8188"},
        {"endpoint": "https://127.0.0.1:8188"},
        {"binding": "../x"},
        {"module": "os.system"},
        {"driver": "my_package.Driver"},
    ],
)
def test_invalid_provider_rejected(tmp_path: Path, change: dict[str, Any]) -> None:
    with pytest.raises((ValueError, TypeError)):
        parse_config(base(tmp_path, **change), tmp_path)


@pytest.mark.parametrize(
    "change",
    [
        {"endpoint": "http://cloud.comfy.org"},  # HTTPS required.
        {"endpoint": "https://user:pw@cloud.comfy.org"},  # No URL credentials.
        {"endpoint": "https://cloud.comfy.org/api?key=x"},
        {"allowed_origins": []},  # Operator must admit the origin.
        {"allowed_origins": ["https://evil.example"]},
        {"auth": {"type": "none"}},  # Remote requires bearer auth.
        {"download_origins": ["http://storage.googleapis.com"]},
    ],
)
def test_remote_rules(tmp_path: Path, change: dict[str, Any]) -> None:
    with pytest.raises(ValueError):
        parse_config(cloud(tmp_path, **change), tmp_path)


@pytest.mark.parametrize(
    "auth",
    [
        {"type": "bearer", "secret_ref": SECRET},  # Raw value instead of a reference.
        {"type": "bearer", "secret_ref": "file:/etc/key"},
        {"type": "bearer", "token": SECRET},
        {"type": "bearer", "api_key": SECRET},
        {"type": "bearer"},
        {"type": "none", "secret_ref": "env:COMFY_API_KEY"},
    ],
)
def test_raw_credentials_rejected_without_echo(
    tmp_path: Path, auth: dict[str, Any]
) -> None:
    with pytest.raises(ValueError) as caught:
        parse_config(cloud(tmp_path, auth=auth), tmp_path)
    assert SECRET not in str(caught.value)


@pytest.mark.parametrize("key", ["api_key", "token", "password"])
def test_credentials_in_other_tables_rejected(tmp_path: Path, key: str) -> None:
    data = cloud(tmp_path)
    data["provider"][key] = SECRET
    with pytest.raises(ValueError) as caught:
        parse_config(data, tmp_path)
    assert SECRET not in str(caught.value)
    data = cloud(tmp_path)
    data["workflow"][key] = SECRET
    with pytest.raises(ValueError):
        parse_config(data, tmp_path)


def test_secret_resolved_only_from_named_env_reference() -> None:
    assert resolve_secret("env:COMFY_API_KEY", {"COMFY_API_KEY": SECRET}) == SECRET
    assert resolve_secret(None, {"COMFY_API_KEY": SECRET}) is None
    with pytest.raises(ValueError) as caught:
        resolve_secret("env:COMFY_API_KEY", {"OTHER": SECRET})
    assert "COMFY_API_KEY" in str(caught.value) and SECRET not in str(caught.value)
    for ref in ("COMFY_API_KEY", "env:lower", "env:A B", "vault:x"):
        with pytest.raises(ValueError):
            resolve_secret(ref, {"COMFY_API_KEY": SECRET})


def test_digest_binds_settings_not_secret_values(tmp_path: Path) -> None:
    first = parse_config(cloud(tmp_path), tmp_path)
    assert SECRET not in repr(first)
    other = cloud(tmp_path)
    other["provider"]["allowed_origins"] = [CLOUD, "https://other.run.comfy.app"]
    assert parse_config(other, tmp_path).digest != first.digest
    assert first.digest == parse_config(cloud(tmp_path), tmp_path).digest


def test_unknown_required_capability_rejected(tmp_path: Path) -> None:
    data = base(tmp_path)
    data["workflow"]["requires"] = ["gpu"]
    with pytest.raises(ValueError):
        parse_config(data, tmp_path)
    data["workflow"]["requires"] = ["node_preflight"]
    assert parse_config(data, tmp_path).workflow.requires == frozenset(
        {"node_preflight"}
    )


def test_application_request_unchanged() -> None:
    assert [f.name for f in dataclasses.fields(TextToImageRequest)] == [
        "prompt",
        "seed",
    ]
    assert [f.name for f in dataclasses.fields(GenerationConfig)] == [
        "provider",
        "workflow",
    ]


def test_local_config_matches_cli_profile(tmp_path: Path) -> None:
    path, sha = write_workflow(tmp_path)
    config = local_config(path, sha, "test.safetensors", "http://127.0.0.1:8188", 900)
    assert config.provider.api_family == "legacy"
    assert config.provider.completion == CompletionPolicy(900, 1, 10)


@pytest.mark.parametrize(
    "name", ["comfy-local.toml", "comfy-cloud.toml", "comfy-v2-selfhosted.toml"]
)
def test_shipped_examples_parse_without_credentials(name: str) -> None:
    path = EXAMPLES / "configs" / name
    text = path.read_text(encoding="utf-8")
    assert "Bearer" not in text and "sk-" not in text
    config = load_config(path)
    assert config.provider.secret_ref in (None, "env:COMFY_API_KEY")
