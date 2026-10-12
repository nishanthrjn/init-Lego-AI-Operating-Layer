"""Configuration-only SAIA identity through existing ForgeAI REMOTE wiring.

All processor claims here describe a synthetic loopback fixture, never GWDG.
"""

import json
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

import pytest
from forgeai_support import REVIEW_ACCEPT, proposal
from legoai.intelligence.model.values import ProviderId
from legoai.runtime.api import ModelDeployment, OpenAICompatibleSettings
from test_remote_profile import (
    CANARY,
    body,
    configured,
    execute,
    policy_text,
    profile,
)
from tls_server import TlsServer

from forgeai.domain import TaskDisposition, TaskFailure
from forgeai.remote import RemoteProfile, load_profile


def saia_profile(port: int, model: str) -> RemoteProfile:
    value = profile(port, datetime.now(UTC))
    return replace(
        value,
        provider=ProviderId("kisski-saia"),
        model=model,
        policy=replace(
            value.policy,
            declarations=tuple(
                replace(item, provider_id="kisski-saia")
                for item in value.policy.declarations
            ),
            admissions=tuple(
                replace(item, provider_id="kisski-saia", models=frozenset({model}))
                for item in value.policy.admissions
            ),
        ),
    )


@pytest.mark.parametrize("model", ["synthetic-coder-a", "synthetic-coder-b"])
@pytest.mark.parametrize("valid", [False, True])
def test_existing_forgeai_proposal_parser_and_review_are_provider_neutral(
    tmp_path: Path, model: str, valid: bool
) -> None:
    with TlsServer(expected=CANARY) as remote:
        outputs = [proposal() if valid else "not JSON", REVIEW_ACCEPT]

        def respond() -> None:
            value = json.loads(body(outputs[remote.requests - 1]))
            value["model"] = model
            remote.responses["/v1/chat/completions"] = json.dumps(value).encode()

        remote.on_request = respond
        with configured(tmp_path, remote, policy=saia_profile(remote.port, model)) as (
            cfg,
            _,
        ):
            result, approvals, checks = execute(cfg)
            if valid:
                assert result.disposition is TaskDisposition.SUCCEEDED
                assert approvals == ["disclosure", "mutation"]
                assert checks.calls == 3 and remote.requests == 2
            else:
                assert result.failure is TaskFailure.PROPOSAL_INVALID
                assert approvals == ["disclosure"]
                assert checks.calls == 0 and remote.requests == 1
            assert all(remote.authorized)
            for raw in remote.bodies:
                request = json.loads(raw)
                assert request["model"] == model
                assert "response_format" not in request
                assert request["stream"] is False
                assert CANARY.encode() not in raw
            assert CANARY not in repr(cfg) + repr(result)


def test_nonsecret_configuration_selects_existing_adapter(tmp_path: Path) -> None:
    # No contact with this endpoint; parser/config construction is inert.
    text = (
        policy_text(443)
        .replace('provider = "remote-endpoint"', 'provider = "kisski-saia"')
        .replace("https://localhost:443/v1", "https://chat-ai.academiccloud.de/v1")
        .replace('model = "model-a"', 'model = "operator-pinned-synthetic-id"')
    )
    path = tmp_path / "policy.toml"
    path.write_text(text, encoding="utf-8")
    value = load_profile(path)
    settings = value.binding().provider
    assert type(settings) is OpenAICompatibleSettings
    assert settings.deployment is ModelDeployment.REMOTE
    assert settings.base_url == "https://chat-ai.academiccloud.de/v1"
    assert settings.chat_model == "operator-pinned-synthetic-id"
    assert settings.provider_id == ProviderId("kisski-saia")
    assert settings.bearer_credential is None
    assert CANARY not in text + repr(value) + repr(settings)


@pytest.mark.parametrize("key", ["api_key", "token", "KISSKI_API_KEY"])
def test_profile_never_accepts_secret_fields(tmp_path: Path, key: str) -> None:
    path = tmp_path / "policy.toml"
    path.write_text(policy_text(443) + f'{key} = "{CANARY}"\n', encoding="utf-8")
    with pytest.raises(ValueError) as error:
        load_profile(path)
    assert CANARY not in str(error.value)
