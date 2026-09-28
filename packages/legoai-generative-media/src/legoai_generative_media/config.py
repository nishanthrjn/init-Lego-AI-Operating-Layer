"""Operator provider configuration: strict TOML, secret references only.

Precedence: the configuration file is the only source of settings. The
environment is consulted solely to resolve an explicit `env:NAME` secret
reference. There are no other environment overrides. This is an
adapter-local reference resolver, not a secret-management system.
"""

import hashlib
import json
import re
import tomllib
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .comfyui import CompletionPolicy
from .drivers.base import Capabilities
from .http import Endpoint, https_origin
from .values import ApprovedWorkflowRef, identifier
from .workflow import ApprovedWorkflow

MAX_CONFIG_BYTES = 64 * 1024
SECRET_REF = re.compile(r"env:[A-Z_][A-Z0-9_]{0,127}")
_KEYS = {
    "": {"provider", "completion", "workflow"},
    "provider": {
        "type",
        "endpoint",
        "api_family",
        "deployment",
        "binding",
        "allowed_origins",
        "download_origins",
        "auth",
    },
    "provider.auth": {"type", "secret_ref"},
    "completion": {
        "max_wait_seconds",
        "poll_interval_seconds",
        "request_timeout_seconds",
    },
    "workflow": {"path", "sha256", "checkpoint", "identity", "version", "requires"},
}


def _table(data: object, name: str) -> dict[str, Any]:
    if type(data) is not dict:
        raise ValueError(f"table required: {name or 'root'}")
    unknown = set(data) - _KEYS[name]
    if unknown:
        # Key names only; values (which could be pasted credentials) never echo.
        raise ValueError(f"unknown key(s) in {name or 'root'}: {sorted(unknown)}")
    return data


def _text(table: dict[str, Any], key: str, default: str | None = None) -> str:
    value = table.get(key, default)
    if type(value) is not str or not value:
        raise ValueError(f"string required: {key}")
    return value


def _origins(table: dict[str, Any], key: str) -> tuple[str, ...]:
    values = table.get(key, [])
    if type(values) is not list or len(values) > 8:
        raise ValueError(f"bounded list required: {key}")
    return tuple(sorted({https_origin(v) for v in values}))


@dataclass(frozen=True, slots=True)
class ProviderConfig:
    endpoint: str
    api_family: str = "auto"
    deployment: str = "local"
    binding: str = "comfyui-local"
    auth: str = "none"
    secret_ref: str | None = None
    allowed_origins: tuple[str, ...] = ()
    download_origins: tuple[str, ...] = ()
    completion: CompletionPolicy = CompletionPolicy()

    def __post_init__(self) -> None:
        if self.api_family not in ("auto", "legacy", "v2"):
            raise ValueError("api_family must be auto, legacy or v2")
        if self.deployment not in ("local", "remote"):
            raise ValueError("deployment must be local or remote")
        if self.auth not in ("none", "bearer"):
            raise ValueError("auth type must be none or bearer")
        identifier(self.binding)
        if (self.auth == "none") != (self.secret_ref is None):
            raise ValueError("bearer auth requires secret_ref; none forbids it")
        if self.secret_ref is not None and not SECRET_REF.fullmatch(self.secret_ref):
            raise ValueError("secret_ref must be env:NAME")
        if type(self.completion) is not CompletionPolicy:
            raise TypeError("completion policy required")
        if self.deployment == "local":
            Endpoint(self.endpoint)  # Literal loopback, explicit port, no extras.
            if self.allowed_origins or self.download_origins:
                raise ValueError("origin lists apply to remote deployments only")
        else:
            if self.auth != "bearer":
                raise ValueError("remote deployments require bearer auth")
            if self.endpoint.rstrip("/") != https_origin(self.endpoint):
                raise ValueError("canonical HTTPS origin required")
            if self.origin not in self.allowed_origins:
                # Operator authorization: a URL alone never admits a host.
                raise ValueError("remote endpoint not in allowed_origins")

    @property
    def origin(self) -> str:
        return self.endpoint.rstrip("/")


@dataclass(frozen=True, slots=True)
class WorkflowConfig:
    path: Path
    sha256: str
    checkpoint: str
    identity: str = "local-txt2img"
    version: str = "1"
    requires: frozenset[str] = frozenset()

    def __post_init__(self) -> None:
        ApprovedWorkflowRef(self.identity, self.version, self.sha256)
        if not self.requires <= Capabilities.names():
            raise ValueError("unknown required capability")

    def load(self) -> ApprovedWorkflow:
        return ApprovedWorkflow.load(
            self.path,
            ApprovedWorkflowRef(self.identity, self.version, self.sha256),
            self.checkpoint,
        )


@dataclass(frozen=True, slots=True)
class GenerationConfig:
    provider: ProviderConfig
    workflow: WorkflowConfig

    @property
    def digest(self) -> str:
        """Configuration revision: every non-secret setting; never secret values."""
        p, w, c = self.provider, self.workflow, self.provider.completion
        canonical = {
            "provider": [
                p.endpoint,
                p.api_family,
                p.deployment,
                p.binding,
                p.auth,
                p.secret_ref,
                list(p.allowed_origins),
                list(p.download_origins),
            ],
            "completion": [
                c.max_wait_seconds,
                c.poll_interval_seconds,
                c.request_timeout_seconds,
            ],
            "workflow": [
                w.sha256,
                w.checkpoint,
                w.identity,
                w.version,
                sorted(w.requires),
            ],
        }
        return hashlib.sha256(
            json.dumps(canonical, sort_keys=True).encode()
        ).hexdigest()


def _completion(table: dict[str, Any]) -> CompletionPolicy:
    derived = CompletionPolicy.for_wait(table.get("max_wait_seconds", 300))
    return CompletionPolicy(
        derived.max_wait_seconds,
        table.get("poll_interval_seconds", derived.poll_interval_seconds),
        table.get("request_timeout_seconds", derived.request_timeout_seconds),
    )


def parse_config(data: object, base: Path) -> GenerationConfig:
    root = _table(data, "")
    provider = _table(root.get("provider"), "provider")
    if provider.get("type") != "comfyui":
        raise ValueError("provider.type must be comfyui")
    auth = _table(provider.get("auth", {"type": "none"}), "provider.auth")
    completion = _completion(_table(root.get("completion", {}), "completion"))
    workflow = _table(root.get("workflow"), "workflow")
    requires = workflow.get("requires", [])
    if type(requires) is not list or any(type(r) is not str for r in requires):
        raise ValueError("workflow.requires must be a list of capability names")
    secret_ref = auth.get("secret_ref")
    if secret_ref is not None and type(secret_ref) is not str:
        raise ValueError("secret_ref must be env:NAME")
    return GenerationConfig(
        ProviderConfig(
            _text(provider, "endpoint"),
            _text(provider, "api_family", "auto"),
            _text(provider, "deployment", "local"),
            _text(provider, "binding", "comfyui-local"),
            _text(auth, "type", "none"),
            secret_ref,
            _origins(provider, "allowed_origins"),
            _origins(provider, "download_origins"),
            completion,
        ),
        WorkflowConfig(
            # Relative workflow paths resolve against the configuration file.
            (base / _text(workflow, "path")).resolve(),
            _text(workflow, "sha256"),
            _text(workflow, "checkpoint"),
            _text(workflow, "identity", "local-txt2img"),
            _text(workflow, "version", "1"),
            frozenset(requires),
        ),
    )


def load_config(path: Path) -> GenerationConfig:
    with path.open("rb") as source:
        content = source.read(MAX_CONFIG_BYTES + 1)
    if len(content) > MAX_CONFIG_BYTES:
        raise ValueError("configuration oversized")
    return parse_config(tomllib.loads(content.decode("utf-8")), path.resolve().parent)


def local_config(
    workflow: Path, sha256: str, checkpoint: str, endpoint: str, max_wait: float
) -> GenerationConfig:
    """The validated loopback legacy profile, expressed as configuration."""
    return GenerationConfig(
        ProviderConfig(
            endpoint, "legacy", completion=CompletionPolicy.for_wait(max_wait)
        ),
        WorkflowConfig(workflow.resolve(), sha256, checkpoint),
    )


def resolve_secret(ref: str | None, environ: Mapping[str, str]) -> str | None:
    """Resolve env:NAME; the error names the variable, never any value."""
    if ref is None:
        return None
    if not SECRET_REF.fullmatch(ref):
        raise ValueError("secret_ref must be env:NAME")
    value = environ.get(ref[4:])
    if not value:
        raise ValueError(f"secret reference unresolved: {ref}")
    return value
