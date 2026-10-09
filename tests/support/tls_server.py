"""Process-local synthetic TLS server for CREDENTIAL-HTTPS-T2 qualification.

Test-only certificates (tests/support/tls): a test CA, a `localhost` leaf, a
`wrong.invalid` leaf and an untrusted self-signed `localhost`. The server
compares the received Bearer value with the expected synthetic token and
keeps only the boolean result; it never prints or stores the token.
"""

import hmac
import socket
import ssl
import threading
from pathlib import Path

TLS = Path(__file__).resolve().parent / "tls"
TEST_CA = TLS / "test-ca.pem"


class TlsServer:
    """One-connection-at-a-time TLS server; `mode` selects the response."""

    def __init__(
        self, mode: str = "ok", *, cert: str = "localhost.pem", expected: str = ""
    ) -> None:
        self.mode, self.expected = mode, expected.encode()
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

    def _read_request(self, conn: ssl.SSLSocket) -> bool:
        data = b""
        while b"\r\n\r\n" not in data:
            chunk = conn.recv(65_536)
            if not chunk:
                return False
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
        self.bodies.append(body)
        # Compare and discard: only the boolean outcome is retained.
        self.authorized.append(
            len(bearer) == 1
            and hmac.compare_digest(bearer[0], b"Bearer " + self.expected)
        )
        del bearer
        return True

    def _handle(self, conn: ssl.SSLSocket) -> None:
        if self.mode == "close-before-request":
            return
        if not self._read_request(conn):
            return
        if self.mode == "timeout":
            self._stop.wait(10)
            return
        body = b'{"ok":true}'
        responses = {
            "ok": b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: %d\r\n\r\n%s",
            "401": b"HTTP/1.1 401 Unauthorized\r\nContent-Length: %d\r\n\r\n%s",
            "403": b"HTTP/1.1 403 Forbidden\r\nContent-Length: %d\r\n\r\n%s",
            "429": b"HTTP/1.1 429 Too Many Requests\r\nContent-Length: %d\r\n\r\n%s",
            "500": b"HTTP/1.1 500 Internal Server Error\r\nContent-Length: %d\r\n\r\n%s",
            "302": b"HTTP/1.1 302 Found\r\nLocation: https://elsewhere.invalid/\r\nContent-Length: %d\r\n\r\n%s",
        }
        if self.mode in responses:
            conn.sendall(responses[self.mode] % (len(body), body))
        elif self.mode == "truncated":
            conn.sendall(b"HTTP/1.1 200 OK\r\nContent-Length: 100\r\n\r\n" + body)
        elif self.mode == "malformed":
            conn.sendall(b"NOT-HTTP garbage\r\n\r\n")
        elif self.mode == "chunked":
            conn.sendall(
                b"HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\n\r\n5\r\nhello\r\n0\r\n\r\n"
            )
        elif self.mode == "oversized":
            conn.sendall(b"HTTP/1.1 200 OK\r\nContent-Length: 999999999\r\n\r\n")
