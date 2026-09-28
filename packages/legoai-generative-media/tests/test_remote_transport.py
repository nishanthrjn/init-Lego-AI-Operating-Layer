"""Remote HTTPS boundary: explicit origin, verified TLS, credentials by reference."""

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
    assert SECRET not in repr(RemoteHTTPS("https://cloud.comfy.org", token=SECRET))
    assert SECRET not in repr(LocalHTTP(Endpoint(), token=SECRET))


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


def test_bearer_header_sent_and_redirect_returned_not_followed() -> None:
    """Shared HTTP/1.1 exchange, exercised over a loopback server."""
    seen: list[bytes] = []

    async def run() -> None:
        async def handler(
            reader: asyncio.StreamReader, writer: asyncio.StreamWriter
        ) -> None:
            seen.append(await reader.readuntil(b"\r\n\r\n"))
            writer.write(
                b"HTTP/1.1 302 Found\r\nLocation: https://evil.example/x\r\n"
                b"Content-Length: 0\r\n\r\n"
            )
            await writer.drain()
            writer.close()

        server = await asyncio.start_server(handler, "127.0.0.1", 0)
        async with server:
            port = server.sockets[0].getsockname()[1]
            http = LocalHTTP(Endpoint(f"http://127.0.0.1:{port}"), token=SECRET)
            with pytest.raises(ValueError) as caught:
                await http.request("GET", "/x", limit=100)
            assert SECRET not in str(caught.value)

    asyncio.run(run())
    assert b"Authorization: Bearer " + SECRET.encode() in seen[0]
    assert b"evil.example" not in seen[0]
