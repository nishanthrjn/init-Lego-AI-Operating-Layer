"""Process-local synthetic TLS server for credential-bearing HTTPS qualification.

Test-only certificates (tests/support/tls): a test CA, a `localhost` leaf, a
`wrong.invalid` leaf and an untrusted self-signed `localhost`. The server
compares the received Bearer value with the expected synthetic token and
keeps only the boolean result; it never prints or stores the token.

`responses` maps a request path to the complete response body, so the server can
emulate the OpenAI-compatible contract (OPENAI-COMPATIBLE-REMOTE-1); any other
path answers the fixed `{"ok":true}`. A numeric `mode` answers that status.
`on_request` runs after a request was fully read, before any response.
"""

import hmac
import socket
import ssl
import threading
from collections.abc import Callable
from pathlib import Path

TLS = Path(__file__).resolve().parent / "tls"
TEST_CA = TLS / "test-ca.pem"


class TlsServer:
    """One-connection-at-a-time TLS server; `mode` selects the response."""

    def __init__(
        self,
        mode: str = "ok",
        *,
        cert: str = "localhost.pem",
        expected: str = "",
        responses: dict[str, bytes] | None = None,
        on_request: Callable[[], None] | None = None,
        methods: dict[str, str] | None = None,
    ) -> None:
        self.mode, self.expected = mode, expected.encode()
        self.responses = dict(responses or {})
        self.on_request = on_request
        self.methods = dict(methods or {})
        self.context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        self.context.load_cert_chain(TLS / cert)
        # Listen on the first loopback address `localhost` resolves to (often
        # ::1 on Windows), so clients never wait on a refused address first.
        family, _, _, _, address = socket.getaddrinfo(
            "localhost", 0, type=socket.SOCK_STREAM
        )[0]
        self.listener = socket.create_server((address[0], 0), family=family)
        self.port = self.listener.getsockname()[1]
        self.connections = 0
        self.requests = 0
        self.authorized: list[bool] = []
        self.header_lines: list[int] = []
        self.header_names: list[tuple[str, ...]] = []
        self.paths: list[str] = []
        self.hosts: list[str] = []
        self.bodies: list[bytes] = []
        self._stop = threading.Event()
        self.thread = threading.Thread(target=self._serve, daemon=True)
        self.thread.start()

    def __enter__(self) -> TlsServer:
        return self

    def __exit__(self, *exc: object) -> None:
        self._stop.set()
        self.listener.close()
        self.thread.join(5)

    def _serve(self) -> None:
        self.listener.settimeout(0.2)
        while not self._stop.is_set():
            try:
                raw, _ = self.listener.accept()
            except TimeoutError, OSError:
                continue
            self.connections += 1
            raw.settimeout(10)
            try:
                conn = self.context.wrap_socket(raw, server_side=True)
            except ssl.SSLError, OSError:
                raw.close()
                continue
            try:
                self._handle(conn)
            except ssl.SSLError, OSError:
                pass
            finally:
                try:
                    conn.close()
                except OSError:
                    pass

    def _read_request(self, conn: ssl.SSLSocket) -> str | None:
        data = b""
        while b"\r\n\r\n" not in data:
            chunk = conn.recv(65_536)
            if not chunk:
                return None
            data += chunk
        head, _, body = data.partition(b"\r\n\r\n")
        lines = head.split(b"\r\n")
        method, path, _ = lines[0].split(b" ", 2)
        length = 0
        bearer: list[bytes] = []
        for line in lines[1:]:
            name, _, value = line.partition(b":")
            if name.lower() == b"content-length":
                length = int(value.strip())
            if name.lower() == b"host":
                self.hosts.append(value.strip().decode())
            if name.lower() == b"authorization":
                bearer.append(value.strip())
        while len(body) < length:
            chunk = conn.recv(65_536)
            if not chunk:
                break
            body += chunk
        self.requests += 1
        self.paths.append(f"{method.decode()} {path.decode()}")
        self.header_lines.append(len(lines) - 1)
        self.header_names.append(
            tuple(line.partition(b":")[0].decode().lower() for line in lines[1:])
        )
        self.bodies.append(body)
        # Compare and discard: only the boolean outcome is retained.
        self.authorized.append(
            len(bearer) == 1
            and hmac.compare_digest(bearer[0], b"Bearer " + self.expected)
        )
        del bearer
        return path.decode()

    def _handle(self, conn: ssl.SSLSocket) -> None:
        if self.mode == "close-before-request":
            return
        path = self._read_request(conn)
        if path is None:
            return
        if path in self.methods and self.paths[-1] != f"{self.methods[path]} {path}":
            conn.sendall(
                b"HTTP/1.1 405 Method Not Allowed\r\nContent-Length: 0\r\n\r\n"
            )
            return
        if self.on_request is not None:
            self.on_request()
        if self.mode == "timeout":
            self._stop.wait(10)
            return
        body = self.responses.get(path, b'{"ok":true}')
        if self.mode == "ok" or self.mode.isdigit():
            status = 200 if self.mode == "ok" else int(self.mode)
            location = (
                b"Location: https://elsewhere.invalid/\r\n" if status == 302 else b""
            )
            conn.sendall(
                b"HTTP/1.1 %d Status\r\nContent-Type: application/json\r\n%s"
                b"Content-Length: %d\r\n\r\n%s" % (status, location, len(body), body)
            )
        elif self.mode == "truncated":
            conn.sendall(
                b"HTTP/1.1 200 OK\r\nContent-Length: %d\r\n\r\n%s"
                % (len(body) + 100, body)
            )
        elif self.mode == "malformed":
            conn.sendall(b"NOT-HTTP garbage\r\n\r\n")
        elif self.mode == "chunked":
            conn.sendall(
                b"HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\n\r\n5\r\nhello\r\n0\r\n\r\n"
            )
        elif self.mode == "malformed-chunk":
            conn.sendall(
                b"HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\n\r\nZ\r\n"
            )
        elif self.mode == "oversized":
            conn.sendall(b"HTTP/1.1 200 OK\r\nContent-Length: 999999999\r\n\r\n")
