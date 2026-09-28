"""Legacy temp upload over the existing bounded transport (no live ComfyUI)."""

import asyncio
import json
import re
import socket
from collections.abc import Callable

from legoai.kernel.effects import EffectExtent
from legoai.kernel.errors import ErrorCategory
from media_support import FakeHTTP, FakeTime, make_png

from legoai_generative_media.comfyui import CompletionPolicy
from legoai_generative_media.drivers.base import Transport
from legoai_generative_media.drivers.legacy import LegacyDriver
from legoai_generative_media.http import Endpoint, LocalHTTP
from legoai_generative_media.transfer import ImageTransfer
from legoai_generative_media.values import ImageInput, InputTransfer

SECRET = b"owner=Alice gps=51.5N"
PERSON = ImageInput(make_png(before=((b"tEXt", b"Author\0" + SECRET),)))


def transfer(transport: Transport) -> ImageTransfer:
    return ImageTransfer(
        LegacyDriver(transport),
        local=True,
        completion=CompletionPolicy(30, 1, 2),
        clock=FakeTime().clock,
    )


def test_multipart_request_shape() -> None:
    http = FakeHTTP()
    result = asyncio.run(transfer(http).upload((PERSON,)))
    assert result.ok
    ((key, value),) = http.upload_headers[0]
    assert key == "Content-Type"
    match = re.fullmatch(r"multipart/form-data; boundary=(legoai-[0-9a-f]{32})", value)
    assert match is not None
    boundary = match.group(1).encode()
    body = http.uploaded[0]
    name = result.uploaded[0].provider_name.encode()
    assert body.startswith(b"--" + boundary + b"\r\n")
    assert body.endswith(b"--" + boundary + b"--\r\n")
    assert b'name="image"; filename="' + name + b'"' in body
    assert b"Content-Type: image/png\r\n\r\n" + PERSON.content + b"\r\n" in body
    assert b'name="type"\r\n\r\ntemp\r\n' in body
    assert b'name="overwrite"\r\n\r\nfalse\r\n' in body
    assert b"subfolder" not in body
    assert SECRET not in body  # Stripped bytes only.
    # Upload is the only write; nothing deletes or touches asset records.
    assert [(c[0], c[1]) for c in http.calls] == [("POST", "/upload/image")]


Reply = Callable[[bytes], bytes]


def field(pattern: bytes, data: bytes) -> bytes:
    match = re.search(pattern, data)
    assert match is not None
    return match.group(1)


async def start(reply_for: Reply, seen: list[bytes]) -> tuple[asyncio.Server, int]:
    async def handler(
        reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        head = await reader.readuntil(b"\r\n\r\n")
        body = await reader.readexactly(int(field(rb"Content-Length: (\d+)", head)))
        seen.append(head + body)
        writer.write(reply_for(body))
        await writer.drain()
        writer.close()

    server = await asyncio.start_server(handler, "127.0.0.1", 0)
    return server, server.sockets[0].getsockname()[1]


def echo(body: bytes) -> bytes:
    name = field(rb'filename="([^"]+)"', body).decode()
    data = json.dumps({"name": name, "subfolder": "", "type": "temp"}).encode()
    return (
        b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n"
        + f"Content-Length: {len(data)}\r\n\r\n".encode()
        + data
    )


def over_real_transport(reply_for: Reply) -> tuple[InputTransfer, list[bytes]]:
    seen: list[bytes] = []

    async def scenario() -> InputTransfer:
        server, port = await start(reply_for, seen)
        async with server:
            http = LocalHTTP(Endpoint(f"http://127.0.0.1:{port}"), 5)
            return await transfer(http).upload((PERSON,))

    return asyncio.run(scenario()), seen


def test_real_local_transport_sends_one_multipart_type() -> None:
    result, seen = over_real_transport(echo)
    assert result.ok and result.disclosure is EffectExtent.COMPLETED
    head = seen[0].split(b"\r\n\r\n", 1)[0].lower()
    assert head.count(b"content-type:") == 1
    assert b"content-type: multipart/form-data; boundary=legoai-" in head
    assert b"application/json" not in head
    assert SECRET not in seen[0]


def test_redirect_after_send_is_unknown_disclosure() -> None:
    def redirect(body: bytes) -> bytes:
        return b"HTTP/1.1 302 Found\r\nLocation: http://127.0.0.1:1/x\r\nContent-Length: 0\r\n\r\n"

    result, seen = over_real_transport(redirect)
    assert len(seen) == 1  # Not followed, not retried.
    assert result.disclosure is EffectExtent.UNKNOWN
    assert result.error is ErrorCategory.VALIDATION_ERROR


def test_connection_refused_is_no_disclosure() -> None:
    probe = socket.socket()
    probe.bind(("127.0.0.1", 0))
    port = probe.getsockname()[1]
    probe.close()  # Nothing listens here now.
    http = LocalHTTP(Endpoint(f"http://127.0.0.1:{port}"), 2)
    result = asyncio.run(transfer(http).upload((PERSON,)))
    assert result.disclosure is EffectExtent.NONE
    assert result.error is ErrorCategory.DEPENDENCY_FAILURE and result.uploaded == ()
