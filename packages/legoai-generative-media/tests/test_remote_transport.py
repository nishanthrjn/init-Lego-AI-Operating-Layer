"""Secret-free HTTPS mechanics; credential construction is unsupported."""

import asyncio
import ssl

import pytest

from legoai_generative_media.http import Endpoint, LocalHTTP, RemoteHTTPS, https_origin

SECRET = "sk-live-DO-NOT-LEAK-0123456789"


@pytest.mark.parametrize(
    "origin",
    [
        "http://cloud.comfy.org",
        "https://user:pw@cloud.comfy.org",
        "https://cloud.comfy.org/api",
        "https://cloud.comfy.org?x=1",
        "https://cloud.comfy.org#f",
        "ftp://cloud.comfy.org",
        "https://",
        "https://clo ud.comfy.org",
    ],
)
def test_https_origin_required(origin: str) -> None:
    with pytest.raises(ValueError):
        RemoteHTTPS(origin)


def test_origin_canonicalization() -> None:
    assert https_origin("https://Cloud.Comfy.org:443/") == "https://cloud.comfy.org"
    assert (
        https_origin("https://x.run.comfy.app:8443") == "https://x.run.comfy.app:8443"
    )
    with pytest.raises(ValueError):
        RemoteHTTPS("https://Cloud.Comfy.org")  # Configuration must be canonical.


def test_tls_verification_enabled() -> None:
    transport = RemoteHTTPS("https://cloud.comfy.org")
    assert transport._tls.verify_mode is ssl.CERT_REQUIRED
    assert transport._tls.check_hostname is True


@pytest.mark.parametrize("token", ["", "has space", "line\r\nX-Evil: 1", "x" * 4097])
def test_malformed_credentials_rejected_without_echo(token: str) -> None:
    with pytest.raises(ValueError) as caught:
        RemoteHTTPS("https://cloud.comfy.org", token=token)
    assert token not in str(caught.value) or not token


def test_credentials_never_in_repr() -> None:
    for factory in (
        lambda: RemoteHTTPS("https://cloud.comfy.org", token=SECRET),
        lambda: LocalHTTP(Endpoint(), token=SECRET),
    ):
        with pytest.raises(ValueError) as caught:
            factory()
        assert str(caught.value) == "credentialled_provider_unsupported"
        assert SECRET not in str(caught.value)


@pytest.mark.parametrize(
    "headers",
    [
        (("Authorization", "Bearer x"),),
        (("Host", "evil.example"),),
        (("X-A", "b\r\nInjected: 1"),),
        (("Bad:Name", "v"),),
    ],
)
def test_per_request_headers_cannot_override_security(
    headers: tuple[tuple[str, str], ...],
) -> None:
    with pytest.raises(ValueError):
        asyncio.run(
            RemoteHTTPS("https://cloud.comfy.org").request(
                "GET", "/api/v2/jobs", limit=100, headers=headers
            )
        )


def test_bearer_refuses_before_network(monkeypatch: pytest.MonkeyPatch) -> None:
    from unittest.mock import Mock

    network = Mock(side_effect=AssertionError("network forbidden"))
    monkeypatch.setattr(asyncio, "open_connection", network)
    with pytest.raises(ValueError, match="credentialled_provider_unsupported"):
        LocalHTTP(Endpoint(), token=SECRET)
    network.assert_not_called()
