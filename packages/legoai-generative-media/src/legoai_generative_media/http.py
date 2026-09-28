"""Bounded HTTP/1.1 transports: loopback HTTP and allowlisted remote HTTPS.

No redirects are followed, no proxies are consulted and nothing is retried.
"""

import asyncio
import ipaddress
import ssl
from dataclasses import dataclass
from urllib.parse import urlsplit

Headers = tuple[tuple[str, str], ...]
# One bounded input image (16 MiB) plus multipart framing; JSON bodies are
# bounded far lower by their producers (256 KiB workflows).
MAX_REQUEST_BODY = 16 * 1024 * 1024 + 64 * 1024


class NotSent(OSError):
    """Failure established before any request byte left this process."""


# Connect is bounded by at most half the exchange timeout, so a failed connect
# is classified here (NotSent) before any enclosing request deadline of the
# same length fires and can only report the outcome as unknown.


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


def https_origin(value: str) -> str:
    """Canonical 'https://host[:port]' or ValueError; no path, query or userinfo."""
    if type(value) is not str or any(ord(c) <= 32 or ord(c) >= 127 for c in value):
        raise ValueError("invalid origin")
    parsed = urlsplit(value)
    if parsed.scheme != "https" or parsed.path not in ("", "/"):
        raise ValueError("HTTPS origin required")
    if "@" in value or "?" in value or "#" in value or not parsed.hostname:
        raise ValueError("URL extras forbidden")
    port = parsed.port
    host = parsed.hostname.lower()
    return "https://" + host + ("" if port in (None, 443) else f":{port}")


@dataclass(frozen=True, slots=True)
class Response:
    status: int
    content_type: str
    body: bytes
    location: str | None = None


def _authorization(value: str | None) -> str | None:
    if value is None:
        return None
    if type(value) is not str or not 1 <= len(value) <= 4096:
        raise ValueError("invalid credential")
    if any(not 0x21 <= ord(c) <= 0x7E for c in value):
        raise ValueError("invalid credential")
    return "Bearer " + value


def _check(method: str, path: str, body: bytes, limit: int, headers: Headers) -> None:
    if method not in ("GET", "POST") or not path.startswith("/"):
        raise ValueError("invalid request")
    if any(ord(c) <= 32 or ord(c) >= 127 for c in path) or path.startswith("//"):
        raise ValueError("invalid request path")
    if len(path) > 8192:
        raise ValueError("request path oversized")
    if len(body) > MAX_REQUEST_BODY or not 0 < limit <= 16 * 1024 * 1024:
        raise ValueError("invalid HTTP bound")
    for key, value in headers:
        if key.lower() in ("authorization", "host", "content-length") or any(
            not 0x20 <= ord(c) <= 0x7E or c == ":" for c in key
        ):
            raise ValueError("forbidden header")
        if any(not 0x20 <= ord(c) <= 0x7E for c in value):
            raise ValueError("invalid header value")


async def _exchange(
    reader: asyncio.StreamReader,
    writer: asyncio.StreamWriter,
    host: str,
    method: str,
    path: str,
    body: bytes,
    limit: int,
    headers: Headers,
    authorization: str | None,
) -> Response:
    extra = "".join(f"{k}: {v}\r\n" for k, v in headers)
    if not any(k.lower() == "content-type" for k, _ in headers):
        extra = "Content-Type: application/json\r\n" + extra
    if authorization is not None:
        extra += f"Authorization: {authorization}\r\n"
    head_out = (
        f"{method} {path} HTTP/1.1\r\nHost: {host}\r\n"
        f"Connection: close\r\nAccept-Encoding: identity\r\n"
        f"Content-Length: {len(body)}\r\n"
        f"{extra}\r\n"
    ).encode("ascii")
    writer.write(head_out + body)
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
        # Returned, never followed; only a caller with an origin policy may act.
        return Response(status, "", b"", fields.get("location"))
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


class LocalHTTP:
    def __init__(
        self, endpoint: Endpoint, timeout: float = 10, *, token: str | None = None
    ) -> None:
        if type(endpoint) is not Endpoint:
            raise TypeError("validated endpoint required")
        if type(timeout) not in (float, int) or not 0 < timeout <= 60:
            raise ValueError("invalid request timeout")
        self.endpoint = endpoint
        self.timeout = timeout
        self._authorization = _authorization(token)

    def __repr__(self) -> str:
        return f"LocalHTTP({self.endpoint.value!r})"

    async def request(
        self,
        method: str,
        path: str,
        body: bytes = b"",
        *,
        limit: int,
        headers: Headers = (),
    ) -> Response:
        _check(method, path, body, limit, headers)
        parsed = urlsplit(self.endpoint.value)
        writer: asyncio.StreamWriter | None = None
        # Each exchange has its own ceiling within the enclosing generation deadline.
        async with asyncio.timeout(self.timeout):
            try:
                try:
                    reader, writer = await asyncio.wait_for(
                        asyncio.open_connection(
                            parsed.hostname, parsed.port, limit=65536
                        ),
                        min(3, self.timeout / 2),
                    )
                except OSError as error:  # Includes connect timeouts.
                    raise NotSent("connection not established") from error
                assert writer is not None  # Successful connection owns a writer.
                response = await _exchange(
                    reader,
                    writer,
                    parsed.netloc,
                    method,
                    path,
                    body,
                    limit,
                    headers,
                    self._authorization,
                )
                if response.location is not None or 300 <= response.status < 400:
                    raise ValueError("redirect forbidden")
                return response
            finally:
                if writer is not None:
                    writer.close()
                    # No worker thread or unbounded close wait survives cancellation.


class RemoteHTTPS:
    """One allowlisted HTTPS origin; TLS verified; redirects returned, not followed."""

    def __init__(
        self, origin: str, timeout: float = 10, *, token: str | None = None
    ) -> None:
        self.origin = https_origin(origin)
        if origin.rstrip("/") != self.origin:
            raise ValueError("canonical origin required")
        if type(timeout) not in (float, int) or not 0 < timeout <= 60:
            raise ValueError("invalid request timeout")
        self.timeout = timeout
        self._authorization = _authorization(token)
        # Default context: certificate and hostname verification enabled.
        self._tls = ssl.create_default_context()

    def __repr__(self) -> str:
        return f"RemoteHTTPS({self.origin!r})"

    async def request(
        self,
        method: str,
        path: str,
        body: bytes = b"",
        *,
        limit: int,
        headers: Headers = (),
    ) -> Response:
        _check(method, path, body, limit, headers)
        parsed = urlsplit(self.origin)
        host = parsed.hostname
        assert host is not None  # Guaranteed by https_origin.
        port = parsed.port or 443
        writer: asyncio.StreamWriter | None = None
        async with asyncio.timeout(self.timeout):
            try:
                try:
                    reader, writer = await asyncio.wait_for(
                        asyncio.open_connection(
                            host, port, ssl=self._tls, server_hostname=host, limit=65536
                        ),
                        min(5, self.timeout / 2),
                    )
                except OSError as error:  # Includes connect/TLS timeouts.
                    raise NotSent("connection not established") from error
                assert writer is not None
                return await _exchange(
                    reader,
                    writer,
                    parsed.netloc,
                    method,
                    path,
                    body,
                    limit,
                    headers,
                    self._authorization,
                )
            finally:
                if writer is not None:
                    writer.close()
