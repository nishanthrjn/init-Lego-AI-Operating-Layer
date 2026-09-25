import asyncio

import pytest

from legoai_generative_media.http import Endpoint, LocalHTTP


@pytest.mark.parametrize(
    "response,valid",
    [
        (
            b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: 2\r\n\r\n{}",
            True,
        ),
        (
            b"HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\n\r\n2\r\n{}\r\n0\r\n\r\n",
            True,
        ),
        (
            b"HTTP/1.1 302 Found\r\nLocation: http://example.com/\r\nContent-Length: 0\r\n\r\n",
            False,
        ),
        (b"HTTP/1.1 200 OK\r\nContent-Length: 999999999\r\n\r\n", False),
        (b"HTTP/1.1 200 OK\r\nContent-Length: 3\r\n\r\nx", False),
        (b"HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\n\r\nfffffff\r\n", False),
    ],
)
def test_real_local_transport(
    response: bytes, valid: bool, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HTTP_PROXY", "http://192.0.2.1:9")
    monkeypatch.setenv("ALL_PROXY", "http://192.0.2.1:9")

    async def run() -> None:
        async def handler(
            reader: asyncio.StreamReader, writer: asyncio.StreamWriter
        ) -> None:
            await reader.readuntil(b"\r\n\r\n")
            writer.write(response)
            await writer.drain()
            writer.close()
            await writer.wait_closed()

        server = await asyncio.start_server(handler, "127.0.0.1", 0)
        async with server:
            port = server.sockets[0].getsockname()[1]
            http = LocalHTTP(Endpoint(f"http://127.0.0.1:{port}"))
            if valid:
                assert (await http.request("GET", "/test", limit=100)).body == b"{}"
            else:
                with pytest.raises((ValueError, asyncio.IncompleteReadError)):
                    await http.request("GET", "/test", limit=100)

    asyncio.run(run())
