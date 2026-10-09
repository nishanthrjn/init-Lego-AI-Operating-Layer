"""CREDENTIAL-HTTPS-T2: private SRCP-1 credential-bearing HTTPS transport.

One connection per attempt: DNS/TCP connect and a verified TLS handshake
complete before any credential exists. TLS runs over `ssl.SSLObject` and
`MemoryBIO`, so HTTP plaintext, TLS records and socket bytes are separate.
The credential-bearing request is encrypted into the outgoing BIO and handed to
the OS only by single nonblocking `send` calls (ADR-007 §18). This module
never decides authority or disclosure, never touches attempt custody, never
retries, redirects, pools or uses a proxy, and reads no environment.

Acceptance boundary (ADR-023 §7.3): H is the OS accepting ciphertext of the
credential-bearing request flight. Encryption into the BIO is preparation.
Every credential-flight send happens inside the Secret owner's ordering domain
(the caller's responsibility); handshake bytes and response reads never do.
"""

import selectors
import socket
import ssl
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from legoai.governance.disclosure import endpoint_parts


def _max_request_body() -> int:
    return 1_048_576


def _max_response_body() -> int:
    return 4_194_304


def _max_header_bytes() -> int:
    return 32_768


def _max_headers() -> int:
    return 64


def _max_write() -> int:
    """Upper bound on ciphertext offered to one nonblocking send call."""
    return 16_384


class TransportFailure(Enum):
    """Safe categories only; never a peer address, certificate text or body."""

    ORIGIN = "origin"
    CONNECT = "connect"
    TLS = "tls"
    TIMEOUT = "timeout"
    PROTOCOL = "protocol"


class TransportError(Exception):
    def __init__(self, failure: TransportFailure) -> None:
        super().__init__(f"credential transport failure: {failure.value}")
        self.failure = failure


class SendProgress(Enum):
    """Credential-flight bytes accepted by the OS (ADR-023 §9 categories)."""

    NONE = "none"
    PARTIAL = "partial"
    ALL = "all"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class HttpsTarget:
    """Exact recipient: the admitted https origin, API root and request path."""

    host: str = field(repr=False)
    port: int
    api_root: str = field(repr=False)
    path: str = field(repr=False)

    @staticmethod
    def for_endpoint(origin: str, api_root: str, path: str) -> HttpsTarget:
        parts = endpoint_parts(origin + ("" if api_root == "/" else api_root))
        # The two Model operations and the one provider-control operation
        # (PROVIDER-MODEL-DISCOVERY-1, ADR-024 §22). Never an arbitrary path.
        if parts != (origin, api_root) or path not in (
            "/chat/completions",
            "/embeddings",
            "/models",
        ):
            raise TransportError(TransportFailure.ORIGIN)
        host_port = origin.removeprefix("https://")
        host, _, port = host_port.partition(":")
        return HttpsTarget(host, int(port) if port else 443, api_root, path)

    @property
    def origin(self) -> str:
        return "https://" + self.host + ("" if self.port == 443 else f":{self.port}")

    @property
    def request_path(self) -> str:
        return ("" if self.api_root == "/" else self.api_root) + self.path


@dataclass(frozen=True, slots=True)
class HttpResponse:
    """A complete, bounded HTTP/1.1 response; the body is never rendered."""

    status: int
    body: bytes = field(repr=False)


@dataclass(frozen=True, slots=True)
class HandoffObservation:
    """What the transport observed; the invocation owner maps it to custody."""

    progress: SendProgress
    response: HttpResponse | None = field(repr=False)
    time_violation: bool
    stopped: bool  # a later gate refused, timed out or failed: no more bytes


def tls_context(trust_anchor: Path | None = None) -> ssl.SSLContext:
    """Verified TLS client context, built explicitly (no ambient key logging).

    Production uses the system trust store. A test trust anchor is passed by
    trusted test composition; verification is never disabled.
    """
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.check_hostname = True
    context.verify_mode = ssl.CERT_REQUIRED
    context.keylog_filename = None  # type: ignore[assignment]
    if trust_anchor is None:
        context.load_default_certs(ssl.Purpose.SERVER_AUTH)
    else:
        context.load_verify_locations(cafile=str(trust_anchor))
    return context


class _CredentialFlight:
    """One verified TLS connection and its single credential-bearing request.

    `open` connects and handshakes before any credential exists. `_begin`,
    `_send_once` are called only by the Secret owner inside its ordering
    domain; `_wait_writable` and `receive` only outside it.
    """

    def __init__(
        self,
        target: HttpsTarget,
        context: ssl.SSLContext,
        body: bytes,
        *,
        timeout: float,
    ) -> None:
        if type(target) is not HttpsTarget or type(context) is not ssl.SSLContext:
            raise TypeError("trusted transport composition required")
        if not context.check_hostname or context.verify_mode is not ssl.CERT_REQUIRED:
            raise TransportError(TransportFailure.TLS)
        if type(body) is not bytes or len(body) > _max_request_body():
            raise TransportError(TransportFailure.PROTOCOL)
        if type(timeout) not in (int, float) or not 0 < timeout <= 3600:
            raise ValueError("bounded timeout required")
        self.target, self._body, self._timeout = target, body, float(timeout)
        self._context = context
        self._deadline = time.monotonic() + self._timeout
        self._sock: socket.socket | None = None
        self._selector: selectors.BaseSelector | None = None
        self._incoming = ssl.MemoryBIO()
        self._outgoing = ssl.MemoryBIO()
        self._tls: ssl.SSLObject | None = None
        self._pending = bytearray()
        self._begun = False
        self._total = 0
        self._accepted = 0
        self._send_failed = False
        self._stopped = False
        self._time_violation = False

    def __repr__(self) -> str:
        return f"_CredentialFlight(accepted={self._accepted}, total={self._total})"

    # Connection and TLS, before any credential (never inside the domain).

    def open(self) -> None:
        try:
            # DNS resolution and TCP connect; the resolved address never
            # replaces the configured host used for certificate verification.
            sock = socket.create_connection(
                (self.target.host, self.target.port), timeout=self._remaining()
            )
        except TimeoutError:
            raise TransportError(TransportFailure.TIMEOUT) from None
        except OSError:
            raise TransportError(TransportFailure.CONNECT) from None
        self._sock = sock
        sock.setblocking(False)
        self._selector = selectors.DefaultSelector()
        self._tls = self._context.wrap_bio(
            self._incoming, self._outgoing, server_hostname=self.target.host
        )
        try:
            while True:
                try:
                    self._tls.do_handshake()
                    break
                except ssl.SSLWantReadError:
                    self._flush_plain()
                    self._receive_some()
                except ssl.SSLWantWriteError:
                    self._flush_plain()
            self._flush_plain()
        except ssl.SSLError:
            raise TransportError(TransportFailure.TLS) from None
        except OSError:
            raise TransportError(TransportFailure.CONNECT) from None

    def _remaining(self) -> float:
        remaining = self._deadline - time.monotonic()
        if remaining <= 0:
            raise TransportError(TransportFailure.TIMEOUT)
        return remaining

    def _wait(self, events: int) -> None:
        assert self._sock is not None and self._selector is not None
        key = self._selector.register(self._sock, events)
        try:
            if not self._selector.select(self._remaining()):
                raise TransportError(TransportFailure.TIMEOUT)
        finally:
            self._selector.unregister(key.fileobj)

    def _flush_plain(self) -> None:
        """Send non-credential TLS bytes (handshake/alerts); outside the domain."""
        assert self._sock is not None
        data = self._outgoing.read()
        while data:
            try:
                sent = self._sock.send(data)
                data = data[sent:]
            except BlockingIOError:
                self._wait(selectors.EVENT_WRITE)

    def _receive_some(self) -> None:
        assert self._sock is not None
        while True:
            try:
                chunk = self._sock.recv(65_536)
                break
            except BlockingIOError:
                self._wait(selectors.EVENT_READ)
        if chunk:
            self._incoming.write(chunk)
        else:
            self._incoming.write_eof()

    # The credential flight: called by the Secret owner inside its domain.

    def _begin(self, material: bytes) -> None:
        """Encrypt the one request into the outgoing BIO (private preparation).

        The plaintext request buffer is overwritten afterwards (best effort).
        """
        if self._begun or self._tls is None:
            raise TransportError(TransportFailure.PROTOCOL)
        self._begun = True
        request = bytearray()
        try:
            request += (
                f"POST {self.target.request_path} HTTP/1.1\r\n"
                f"Host: {self.target.origin.removeprefix('https://')}\r\n"
                "Content-Type: application/json\r\n"
                "Accept: application/json\r\n"
            ).encode("ascii")
            request += b"Authorization: Bearer " + material + b"\r\n"
            request += (
                f"Content-Length: {len(self._body)}\r\nConnection: close\r\n\r\n"
            ).encode("ascii")
            request += self._body
            view = memoryview(request)
            written = 0
            while written < len(request):
                written += self._tls.write(view[written:])
            view.release()
            self._pending = bytearray(self._outgoing.read())
            self._total = len(self._pending)
        finally:
            for index in range(len(request)):
                request[index] = 0

    def _send_some(self, data: bytes) -> int:
        assert self._sock is not None
        return self._sock.send(data)

    def _send_once(self) -> None:
        """One nonblocking OS acceptance step of credential-flight ciphertext."""
        if not self._pending or self._send_failed:
            return
        try:
            sent = self._send_some(bytes(self._pending[: _max_write()]))
        except BlockingIOError:
            sent = 0
        except OSError:
            # This call accepted nothing; earlier accepted bytes stay counted.
            self._send_failed = True
            self._stopped = True
            return
        del self._pending[:sent]
        self._accepted += sent

    @property
    def _flight_pending(self) -> bool:
        return bool(self._pending) and not self._send_failed

    def _wait_writable(self) -> None:
        """Readiness wait between continuation writes; outside the domain."""
        try:
            self._wait(selectors.EVENT_WRITE)
        except TransportError:
            self._stopped = True
            raise

    def _stop(self) -> None:
        self._stopped = True
        for index in range(len(self._pending)):
            self._pending[index] = 0
        self._pending.clear()

    def _note_time_violation(self) -> None:
        self._time_violation = True

    # Response and observation, outside the domain.

    def progress(self) -> SendProgress:
        if not self._begun or self._accepted == 0:
            return SendProgress.NONE
        if self._accepted >= self._total:
            return SendProgress.ALL
        return SendProgress.PARTIAL

    def receive(self) -> HttpResponse | None:
        """Bounded HTTP/1.1 framing (Content-Length only); None if incomplete."""
        if self.progress() is not SendProgress.ALL or self._tls is None:
            return None
        plaintext = bytearray()
        try:
            while True:
                try:
                    data = self._tls.read(65_536)
                    if not data:
                        break
                    plaintext += data
                    if len(plaintext) > _max_header_bytes() + _max_response_body():
                        raise TransportError(TransportFailure.PROTOCOL)
                    response = _parse(bytes(plaintext))
                    if response is not None:
                        return response
                except ssl.SSLWantReadError:
                    self._receive_some()
                except ssl.SSLZeroReturnError:
                    break
                except ssl.SSLEOFError:
                    break
        except TransportError, ssl.SSLError, OSError:
            return None
        return _parse(bytes(plaintext))

    def observe(self, response: HttpResponse | None) -> HandoffObservation:
        return HandoffObservation(
            self.progress(), response, self._time_violation, self._stopped
        )

    def close(self) -> None:
        self._stop()
        if self._selector is not None:
            self._selector.close()
            self._selector = None
        if self._sock is not None:
            self._sock.close()
            self._sock = None


def _parse(data: bytes) -> HttpResponse | None:
    """Complete response or None (need more); malformed raises PROTOCOL."""
    end = data.find(b"\r\n\r\n")
    if end < 0:
        if len(data) > _max_header_bytes():
            raise TransportError(TransportFailure.PROTOCOL)
        return None
    head = data[:end].decode("latin-1")
    lines = head.split("\r\n")
    status = lines[0].split(" ", 2)
    if (
        len(lines) > _max_headers() + 1
        or len(status) < 2
        or status[0] not in ("HTTP/1.1", "HTTP/1.0")
        or not status[1].isdigit()
        or len(status[1]) != 3
        or not 200 <= int(status[1]) <= 599
    ):
        raise TransportError(TransportFailure.PROTOCOL)
    length: int | None = None
    for line in lines[1:]:
        name, separator, value = line.partition(":")
        if not separator or not name or name != name.strip():
            raise TransportError(TransportFailure.PROTOCOL)
        lowered = name.lower()
        if lowered == "transfer-encoding":
            raise TransportError(TransportFailure.PROTOCOL)
        if lowered == "content-length":
            value = value.strip()
            if length is not None or not value.isdigit():
                raise TransportError(TransportFailure.PROTOCOL)
            length = int(value)
    if length is None or length > _max_response_body():
        raise TransportError(TransportFailure.PROTOCOL)
    body = data[end + 4 :]
    if len(body) < length:
        return None
    if len(body) > length:
        raise TransportError(TransportFailure.PROTOCOL)
    return HttpResponse(int(status[1]), body)
