"""Read-only API-family discovery and closed driver selection."""

import ast
import asyncio
from pathlib import Path
from typing import Any

import pytest
from legoai.kernel.errors import ErrorCategory
from media_support import (
    FakeHTTP,
    FakeTime,
    FakeV2,
    Transports,
    envelope,
    json_response,
    write_workflow,
)

from legoai_generative_media.config import parse_config
from legoai_generative_media.discovery import DRIVERS, confirm, discover
from legoai_generative_media.drivers.base import ProviderError
from legoai_generative_media.drivers.legacy import LegacyDriver
from legoai_generative_media.drivers.v2 import V2Driver
from legoai_generative_media.http import Headers, Response
from legoai_generative_media.service import open_text_to_image, probe_provider

LOCAL = "http://127.0.0.1:8188"


class Legacy(FakeHTTP):
    """Legacy server exposing /system_stats; unknown routes are plain 404."""

    async def request(
        self,
        method: str,
        path: str,
        body: bytes = b"",
        *,
        limit: int,
        headers: Headers = (),
    ) -> Response:
        if path == "/system_stats":
            self.calls.append((method, path, body))
            return json_response(
                200, {"system": {"comfyui_version": "0.37.0", "argv": ["x"]}}
            )
        if path.startswith("/api/v2/"):
            self.calls.append((method, path, body))
            return Response(404, "text/plain", b"404: Not Found")
        return await super().request(method, path, body, limit=limit)


class Html:
    """An unrelated web server: 200 HTML for everything."""

    def __init__(self) -> None:
        self.calls: list[str] = []

    async def request(
        self,
        method: str,
        path: str,
        body: bytes = b"",
        *,
        limit: int,
        headers: Headers = (),
    ) -> Response:
        self.calls.append(method)
        return Response(200, "text/html", b"<html>welcome</html>")


def run_discover(family: str, transport: Any) -> tuple[str, str | None]:
    return asyncio.run(
        discover(family, transport, request_timeout=5, clock=FakeTime().clock)
    )


def test_explicit_legacy_avoids_probing() -> None:
    http = Legacy()
    assert run_discover("legacy", http) == ("legacy", None)
    assert http.calls == []


def test_explicit_v2_avoids_probing_and_fallback() -> None:
    fake = FakeV2()
    assert run_discover("v2", fake) == ("v2", None)
    assert fake.calls == []


def test_auto_discovers_legacy_with_version() -> None:
    http = Legacy()
    assert run_discover("auto", http) == ("legacy", "0.37.0")
    assert http.posts() == 0


def test_auto_discovers_v2() -> None:
    fake = FakeV2()
    assert run_discover("auto", fake) == ("v2", None)
    assert fake.posts() == 0 and all(c[0] == "GET" for c in fake.calls)


@pytest.mark.parametrize("server", ["html", "empty-json", "unrelated-404-json"])
def test_unknown_api_fails_closed(server: str) -> None:
    class Odd(Html):
        async def request(
            self,
            method: str,
            path: str,
            body: bytes = b"",
            *,
            limit: int,
            headers: Headers = (),
        ) -> Response:
            self.calls.append(method)
            if server == "empty-json":
                return json_response(200, {})
            return envelope(404, "no_such_route")

    transport = Html() if server == "html" else Odd()
    with pytest.raises(ProviderError) as caught:
        run_discover("auto", transport)
    assert caught.value.reason == "unsupported_api"
    assert caught.value.category is ErrorCategory.VERSION_MISMATCH
    assert set(transport.calls) == {"GET"}


def test_ambiguous_surface_fails_closed() -> None:
    class Both(FakeV2):
        async def request(
            self,
            method: str,
            path: str,
            body: bytes = b"",
            *,
            limit: int,
            headers: Headers = (),
        ) -> Response:
            if path == "/system_stats":
                return json_response(200, {"system": {"comfyui_version": "1.0.0"}})
            return await super().request(method, path, body, limit=limit)

    with pytest.raises(ProviderError) as caught:
        run_discover("auto", Both())
    assert caught.value.reason == "unsupported_api"


def test_unreachable_provider_is_distinct() -> None:
    fake = FakeV2()
    fake.fail_at = "/"
    with pytest.raises(ProviderError) as caught:
        run_discover("auto", fake)
    assert caught.value.reason == "provider_unavailable"


def test_v2_authentication_failure_is_explicit() -> None:
    class Denied(Html):
        async def request(
            self,
            method: str,
            path: str,
            body: bytes = b"",
            *,
            limit: int,
            headers: Headers = (),
        ) -> Response:
            self.calls.append(method)
            return envelope(401, "unauthorized")

    with pytest.raises(ProviderError) as caught:
        run_discover("auto", Denied())
    assert caught.value.reason == "authentication_failed"


def test_confirm_explicit_family() -> None:
    clock = FakeTime().clock
    assert (
        asyncio.run(confirm("legacy", Legacy(), request_timeout=5, clock=clock))
        == "0.37.0"
    )
    assert asyncio.run(confirm("v2", FakeV2(), request_timeout=5, clock=clock)) is None
    with pytest.raises(ProviderError):
        asyncio.run(confirm("v2", Legacy(), request_timeout=5, clock=clock))


def test_registry_is_closed() -> None:
    assert set(DRIVERS) == {"legacy", "v2"}
    fake = FakeV2()
    assert isinstance(
        DRIVERS["legacy"](None, fake, frozenset(), Transports({})), LegacyDriver
    )
    assert isinstance(DRIVERS["v2"](None, fake, frozenset(), Transports({})), V2Driver)


def test_config_resolves_driver(tmp_path: Path) -> None:
    path, sha = write_workflow(tmp_path)

    def config(family: str, endpoint: str = LOCAL) -> Any:
        return parse_config(
            {
                "provider": {
                    "type": "comfyui",
                    "endpoint": endpoint,
                    "api_family": family,
                },
                "workflow": {
                    "path": str(path),
                    "sha256": sha,
                    "checkpoint": "test.safetensors",
                },
            },
            tmp_path,
        )

    legacy = asyncio.run(
        open_text_to_image(config("auto"), transports=Transports({LOCAL: Legacy()}))
    )
    assert legacy.profile.family == "legacy" and legacy.profile.version == "0.37.0"
    assert legacy.profile.capabilities.node_preflight
    v2 = asyncio.run(
        open_text_to_image(
            config("auto", "http://127.0.0.1:8189"),
            transports=Transports({"http://127.0.0.1:8189": FakeV2()}),
        )
    )
    assert v2.profile.family == "v2" and v2.profile.capabilities.idempotent_submission
    profile = asyncio.run(
        probe_provider(config("legacy"), transports=Transports({LOCAL: Legacy()}))
    )
    assert profile.version == "0.37.0"


def test_no_dynamic_imports_or_config_driven_code() -> None:
    root = Path(__file__).resolve().parents[1] / "src" / "legoai_generative_media"
    for path in (root / "discovery.py", root / "config.py", root / "service.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                assert all(a.name not in ("importlib", "pkgutil") for a in node.names)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                assert node.func.id not in ("eval", "exec", "__import__", "getattr")


class Fixed(Html):
    """Answers every request with one canned response."""

    def __init__(self, response: Response) -> None:
        super().__init__()
        self.response = response

    async def request(
        self,
        method: str,
        path: str,
        body: bytes = b"",
        *,
        limit: int,
        headers: Headers = (),
    ) -> Response:
        self.calls.append(method)
        return self.response


@pytest.mark.parametrize("status", [401, 403])
def test_any_auth_rejection_is_explicit(status: int) -> None:
    bare = Fixed(Response(status, "text/plain", b"denied"))
    with pytest.raises(ProviderError) as caught:
        run_discover("auto", bare)
    assert caught.value.category is ErrorCategory.AUTHORIZATION_DENIED
    assert caught.value.evidence == (
        f"v2 probe: status={status} type=text/plain code=-",
    )
    with pytest.raises(ProviderError):
        asyncio.run(confirm("v2", bare, request_timeout=5, clock=FakeTime().clock))


def test_evidence_is_sanitized_and_never_echoes_bodies() -> None:
    leak = "sk-live-DO-NOT-LEAK provider message with details"
    response = json_response(404, {"error": {"code": "job_missing", "message": leak}})
    with pytest.raises(ProviderError) as caught:
        asyncio.run(
            confirm("v2", Fixed(response), request_timeout=5, clock=FakeTime().clock)
        )
    assert caught.value.reason == "unsupported_api"
    assert caught.value.evidence == (
        "v2 probe: status=404 type=application/json code=job_missing",
    )
    odd = json_response(404, {"error": {"code": "has spaces " + leak}})
    with pytest.raises(ProviderError) as caught:
        run_discover("auto", Fixed(odd))
    joined = " ".join(caught.value.evidence)
    assert leak not in joined and "code=-" in joined
    assert "legacy probe: status=404" in joined
