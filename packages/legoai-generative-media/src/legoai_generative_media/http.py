"""Bounded loopback HTTP/1.1, no redirects, DNS hosts, proxies or retries."""

import asyncio
import ipaddress
from dataclasses import dataclass
from urllib.parse import urlsplit


@dataclass(frozen=True, slots=True)
class Endpoint:
    value: str = "http://127.0.0.1:8188"

    def __post_init__(self) -> None:
        parsed = urlsplit(self.value)
        if parsed.scheme != "http" or parsed.path not in ("", "/"):
            raise ValueError("loopback HTTP origin required")
        if parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError("URL extras forbidden")
        if "?" in self.value or "#" in self.value or "@" in self.value:
            raise ValueError("URL extras forbidden")
        if not parsed.hostname or not ipaddress.ip_address(parsed.hostname).is_loopback:
            raise ValueError("literal loopback IP required")
        if parsed.port is None or not 1 <= parsed.port <= 65535:
            raise ValueError("explicit port required")
        if any(ord(c) <= 32 or ord(c) >= 127 for c in self.value):
            raise ValueError("invalid endpoint characters")


@dataclass(frozen=True, slots=True)
class Response:
    status: int
    content_type: str
    body: bytes


class LocalHTTP:
    def __init__(self, endpoint: Endpoint, timeout: float = 10) -> None:
        if type(endpoint) is not Endpoint:
            raise TypeError("validated endpoint required")
        if type(timeout) not in (float, int) or not 0 < timeout <= 60:
            raise ValueError("invalid request timeout")
        self.endpoint = endpoint
        self.timeout = timeout

    async def request(
        self, method: str, path: str, body: bytes = b"", *, limit: int
    ) -> Response:
        if method not in ("GET", "POST") or not path.startswith("/"):
            raise ValueError("invalid request")
        if any(ord(c) <= 32 or ord(c) >= 127 for c in path) or path.startswith("//"):
            raise ValueError("invalid request path")
        if len(body) > 256 * 1024 or not 0 < limit <= 16 * 1024 * 1024:
            raise ValueError("invalid HTTP bound")
        parsed = urlsplit(self.endpoint.value)
        writer: asyncio.StreamWriter | None = None
        # Each exchange has its own ceiling within the enclosing generation deadline.
        async with asyncio.timeout(self.timeout):
            try:
                reader, writer = await asyncio.wait_for(
                    asyncio.open_connection(parsed.hostname, parsed.port, limit=65536),
                    min(3, self.timeout),
                )
                assert writer is not None  # Successful connection owns a writer.
                headers = (
                    f"{method} {path} HTTP/1.1\r\nHost: {parsed.netloc}\r\n"
                    f"Connection: close\r\nAccept-Encoding: identity\r\n"
                    f"Content-Type: application/json\r\nContent-Length: {len(body)}\r\n\r\n"
                ).encode("ascii")
                writer.write(headers + body)
                await writer.drain()
                head = await reader.readuntil(b"\r\n\r\n")
                if len(head) > 65536:
                    raise ValueError("headers oversized")
                lines = head.decode("ascii").split("\r\n")
                version, code, *_ = lines[0].split(" ")
                if version not in ("HTTP/1.0", "HTTP/1.1"):
                    raise ValueError("invalid HTTP version")
                status = int(code)
                fields: dict[str, str] = {}
                for line in lines[1:]:
                    if not line:
                        continue
                    key, value = line.split(":", 1)
                    key = key.lower()
                    if key in fields:
                        raise ValueError("duplicate header")
                    fields[key] = value.strip()
                if 300 <= status < 400:
                    raise ValueError("redirect forbidden")
                if fields.get("content-encoding", "identity") != "identity":
                    raise ValueError("encoded response forbidden")
                data = bytearray()
                if "transfer-encoding" in fields:
                    if (
                        fields["transfer-encoding"].lower() != "chunked"
                        or "content-length" in fields
                    ):
                        raise ValueError("ambiguous framing")
                    for _ in range(65536):
                        chunk_header = await reader.readuntil(b"\r\n")
                        if len(chunk_header) > 128 or b";" in chunk_header:
                            raise ValueError("invalid chunk header")
                        size = int(chunk_header.strip(), 16)
                        if size < 0 or len(data) + size > limit:
                            raise ValueError("response oversized")
                        if size == 0:
                            if await reader.readexactly(2) != b"\r\n":
                                raise ValueError("trailers unsupported")
                            break
                        data.extend(await reader.readexactly(size))
                        if await reader.readexactly(2) != b"\r\n":
                            raise ValueError("invalid chunk")
                    else:
                        raise ValueError("too many chunks")
                elif "content-length" in fields:
                    size = int(fields["content-length"])
                    if not 0 <= size <= limit:
                        raise ValueError("response oversized")
                    data.extend(await reader.readexactly(size))
                else:
                    while True:
                        chunk = await reader.read(min(65536, limit + 1 - len(data)))
                        if not chunk:
                            break
                        data.extend(chunk)
                        if len(data) > limit:
                            raise ValueError("response oversized")
                return Response(status, fields.get("content-type", ""), bytes(data))
            finally:
                if writer is not None:
                    writer.close()
                    # No worker thread or unbounded close wait survives cancellation.
