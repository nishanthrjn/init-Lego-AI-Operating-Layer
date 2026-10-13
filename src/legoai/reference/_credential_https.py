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
from dataclasses import dataclass, field, fields, replace
from enum import Enum
from pathlib import Path

from legoai.governance.disclosure import endpoint_parts
from legoai.governance.provider_control import ProviderDiscoveryMethod


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


class ReceiveStage(Enum):
    CONNECT = "connect"
    TLS = "tls"
    SEND = "send"
    WAIT_FIRST_BYTE = "wait_first_byte"
    READ_HEADERS = "read_headers"
    READ_BODY = "read_body"
    COMPLETE = "complete"


class ResponseFraming(Enum):
    CONTENT_LENGTH = "content_length"
    CHUNKED = "chunked"
    CLOSE_DELIMITED = "close_delimited"
    CL_AND_TE = "cl_and_te"
    UNKNOWN = "unknown"


class HttpVersion(Enum):
    HTTP10 = "http_1_0"
    HTTP11 = "http_1_1"
    OTHER = "other"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True, repr=False)
class ReceiveDiagnostics:
    """Ephemeral observations only; never input to parsing or settlement."""

    receive_stage: ReceiveStage = ReceiveStage.CONNECT
    connected: bool = False
    tls_completed: bool = False
    request_fully_sent: bool = False
    first_byte_seen: bool = False
    headers_complete: bool = False
    protocol_version: HttpVersion = HttpVersion.UNKNOWN
    header_status_code: int | None = None
    content_length_present: bool | None = None
    transfer_encoding_present: bool | None = None
    framing: ResponseFraming = ResponseFraming.UNKNOWN
    content_length_declared: int | None = None
    body_bytes_observed: int = 0
    body_complete: bool = False
    eof_seen: bool = False
    parser_rejected: bool = False
    cap_reached: bool = False
    read_error: bool = False
    deadline_stage: ReceiveStage | None = None
    failure_category: TransportFailure | None = None
    send_to_first_byte_ms: int | None = None
    first_byte_to_headers_ms: int | None = None
    headers_to_body_complete_ms: int | None = None
    total_receive_ms: int | None = None
    chunks_observed: int | None = None
    decoded_body_bytes: int | None = None
    terminal_chunk_seen: bool | None = None
    trailer_present: bool | None = None

    def safe_items(self) -> tuple[tuple[str, str], ...]:
        """Closed projection; reject arbitrary values, including corrupt data."""
        result: list[tuple[str, str]] = []
        for item in fields(self):
            value = getattr(self, item.name)
            if value is None:
                text = "unknown"
            elif type(value) is bool:
                text = "true" if value else "false"
            elif type(value) is int and 0 <= value <= _max_response_body():
                if item.name == "chunks_observed" and value > 6552:
                    raise ValueError("invalid receive diagnostic")
                text = str(value)
            elif type(value) in (
                ReceiveStage,
                ResponseFraming,
                HttpVersion,
                TransportFailure,
            ):
                text = value.value
            else:
                raise ValueError("invalid receive diagnostic")
            result.append((item.name, text))
        return tuple(result)


@dataclass(frozen=True, slots=True)
class HttpsTarget:
    """Exact recipient: the admitted https origin, API root and request path."""

    host: str = field(repr=False)
    port: int
    api_root: str = field(repr=False)
    path: str = field(repr=False)
    discovery_method: ProviderDiscoveryMethod | None = None

    def __post_init__(self) -> None:
        if self.path == "/models":
            if self.discovery_method is None:
                object.__setattr__(
                    self, "discovery_method", ProviderDiscoveryMethod.POST_EMPTY
                )
            elif type(self.discovery_method) is not ProviderDiscoveryMethod:
                raise TransportError(TransportFailure.PROTOCOL)
        elif self.discovery_method is not None:
            raise TransportError(TransportFailure.PROTOCOL)

    @staticmethod
    def for_endpoint(
        origin: str,
        api_root: str,
        path: str,
        *,
        discovery_method: ProviderDiscoveryMethod | None = None,
    ) -> HttpsTarget:
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
        return HttpsTarget(
            host, int(port) if port else 443, api_root, path, discovery_method
        )

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
    failure: TransportFailure | None = None
    diagnostics: ReceiveDiagnostics | None = field(
        default=None, repr=False, compare=False
    )


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
        if target.path == "/models" and body:
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
        self._failure: TransportFailure | None = None
        self._time_violation = False
        self._diagnostics: ReceiveDiagnostics | None = ReceiveDiagnostics()
        self._sent_at: float | None = None
        self._first_at: float | None = None
        self._headers_at: float | None = None

    def _note(self, event: str, data: bytes | bytearray = b"") -> None:
        # Observability is optional: failure discards it, never changes the
        # exchange, deadline, failure category, custody or retry behavior.
        if self._diagnostics is None:
            return
        try:
            self._update_diagnostics(event, data)
        except Exception:
            self._diagnostics = None

    def _update_diagnostics(self, event: str, data: bytes | bytearray) -> None:
        current = self._diagnostics
        assert current is not None
        now = time.monotonic()

        def elapsed(start: float | None) -> int | None:
            if start is None:
                return None
            return min(3_600_000, max(0, int((now - start) * 1000)))

        if event == "connected":
            current = replace(current, connected=True, receive_stage=ReceiveStage.TLS)
        elif event == "tls":
            current = replace(
                current, tls_completed=True, receive_stage=ReceiveStage.SEND
            )
        elif event == "sent":
            self._sent_at = now
            current = replace(
                current,
                request_fully_sent=True,
                receive_stage=ReceiveStage.WAIT_FIRST_BYTE,
            )
        elif event == "data":
            if not current.first_byte_seen:
                self._first_at = now
                current = replace(
                    current,
                    first_byte_seen=True,
                    receive_stage=ReceiveStage.READ_HEADERS,
                    send_to_first_byte_ms=elapsed(self._sent_at),
                )
            end = data.find(b"\r\n\r\n")
            if end >= 0:
                if not current.headers_complete:
                    current = replace(
                        current,
                        headers_complete=True,
                        receive_stage=ReceiveStage.READ_BODY,
                        first_byte_to_headers_ms=elapsed(self._first_at),
                    )
                    self._headers_at = now
                    # Bounded metadata scan only; the original parser remains
                    # the sole authority. Never retain any raw header value.
                    if end <= _max_header_bytes():
                        lines = bytes(data[:end]).split(b"\r\n")
                        status = lines[0].split(b" ", 2)
                        version = {
                            b"HTTP/1.0": HttpVersion.HTTP10,
                            b"HTTP/1.1": HttpVersion.HTTP11,
                        }.get(status[0], HttpVersion.OTHER)
                        code = (
                            int(status[1])
                            if len(status) > 1
                            and len(status[1]) == 3
                            and status[1].isdigit()
                            else None
                        )
                        current = replace(
                            current,
                            protocol_version=version,
                            header_status_code=(
                                code
                                if code is not None and 100 <= code <= 599
                                else None
                            ),
                        )
                        lengths: list[bytes] = []
                        transfers: list[bytes] = []
                        malformed = False
                        for line in lines[1:]:
                            name, separator, value = line.partition(b":")
                            if not separator or not name or name != name.strip():
                                malformed = True
                            if separator and name.lower() == b"content-length":
                                lengths.append(value.strip())
                            if separator and name.lower() == b"transfer-encoding":
                                transfers.append(value.strip().lower())
                        length = None
                        over = False
                        if len(lengths) == 1 and lengths[0].isdigit():
                            digits = lengths[0].lstrip(b"0") or b"0"
                            over = len(digits) > 7 or int(digits) > _max_response_body()
                            if not over:
                                length = int(digits)
                        framing = ResponseFraming.UNKNOWN
                        if lengths and transfers:
                            framing = ResponseFraming.CL_AND_TE
                        elif transfers == [b"chunked"]:
                            framing = ResponseFraming.CHUNKED
                        elif not lengths and not transfers:
                            framing = ResponseFraming.CLOSE_DELIMITED
                        elif length is not None and not transfers:
                            framing = ResponseFraming.CONTENT_LENGTH
                        if malformed:
                            framing = ResponseFraming.UNKNOWN
                        current = replace(
                            current,
                            content_length_present=bool(lengths),
                            transfer_encoding_present=bool(transfers),
                            framing=framing,
                            content_length_declared=length,
                            cap_reached=over,
                        )
                count = len(data) - end - 4
                current = replace(
                    current,
                    body_bytes_observed=min(count, _max_response_body()),
                    cap_reached=current.cap_reached or count > _max_response_body(),
                )
            current = replace(
                current,
                cap_reached=current.cap_reached
                or (end < 0 and len(data) > _max_header_bytes())
                or (end >= 0 and end + 4 > _max_header_bytes())
                or len(data) > _max_header_bytes() + _max_response_body(),
            )
        elif event == "complete":
            current = replace(
                current,
                receive_stage=ReceiveStage.COMPLETE,
                body_complete=True,
                headers_to_body_complete_ms=elapsed(self._headers_at),
            )
        elif event == "eof":
            current = replace(current, eof_seen=True)
        elif event == "read_error":
            current = replace(current, read_error=True)
        elif event == "failure":
            current = replace(
                current,
                parser_rejected=self._failure is TransportFailure.PROTOCOL,
                deadline_stage=(
                    current.receive_stage
                    if self._failure is TransportFailure.TIMEOUT
                    else None
                ),
            )
        elif event in {"connect_timeout", "connect_error", "tls_error"}:
            category = {
                "connect_timeout": TransportFailure.TIMEOUT,
                "connect_error": TransportFailure.CONNECT,
                "tls_error": TransportFailure.TLS,
            }[event]
            current = replace(
                current,
                failure_category=category,
                deadline_stage=(
                    current.receive_stage
                    if category is TransportFailure.TIMEOUT
                    else None
                ),
            )
        current = replace(
            current,
            total_receive_ms=elapsed(self._sent_at),
            failure_category=self._failure or current.failure_category,
        )
        self._diagnostics = current

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
            self._note("connect_timeout")
            raise TransportError(TransportFailure.TIMEOUT) from None
        except OSError:
            self._note("connect_error")
            raise TransportError(TransportFailure.CONNECT) from None
        self._sock = sock
        self._note("connected")
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
            self._note("tls")
        except ssl.SSLError:
            self._note("tls_error")
            raise TransportError(TransportFailure.TLS) from None
        except OSError:
            self._note("connect_error")
            raise TransportError(TransportFailure.CONNECT) from None

    def _remaining(self) -> float:
        remaining = self._deadline - time.monotonic()
        if remaining <= 0:
            self._failure = TransportFailure.TIMEOUT
            self._note("failure")
            raise TransportError(TransportFailure.TIMEOUT)
        return remaining

    def _wait(self, events: int) -> None:
        assert self._sock is not None and self._selector is not None
        key = self._selector.register(self._sock, events)
        try:
            if not self._selector.select(self._remaining()):
                self._failure = TransportFailure.TIMEOUT
                self._note("failure")
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
            is_get = self.target.discovery_method is ProviderDiscoveryMethod.GET
            request += (
                f"{'GET' if is_get else 'POST'} {self.target.request_path} HTTP/1.1\r\n"
                f"Host: {self.target.origin.removeprefix('https://')}\r\n"
            ).encode("ascii")
            if not is_get:
                request += b"Content-Type: application/json\r\n"
            request += b"Accept: application/json\r\n"
            request += b"Authorization: Bearer " + material + b"\r\n"
            if not is_get:
                request += f"Content-Length: {len(self._body)}\r\n".encode("ascii")
            request += b"Connection: close\r\n\r\n"
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
        if self._accepted >= self._total:
            self._note("sent")

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
        """One bounded ordinary response; no partial delivery or streaming."""
        if self.progress() is not SendProgress.ALL or self._tls is None:
            return None
        plaintext = bytearray()
        decoder: _Chunked | None = None
        status = 0
        try:
            while True:
                try:
                    self._remaining()
                    data = self._tls.read(65_536)
                    if not data:
                        self._note("eof")
                        break
                    if decoder is None:
                        plaintext += data
                        self._note("data", plaintext)
                        head = _response_head(plaintext)
                        if head is not None and head[1] is None:
                            status, _, offset = head
                            decoder = _Chunked(self._deadline)
                            data = bytes(plaintext[offset:])
                            plaintext.clear()
                    if decoder is not None:
                        try:
                            complete = decoder.feed(data)
                        finally:
                            self._note_chunked(decoder)
                        response = (
                            HttpResponse(status, bytes(decoder.body))
                            if complete
                            else None
                        )
                    else:
                        if len(plaintext) > _max_header_bytes() + _max_response_body():
                            raise TransportError(TransportFailure.PROTOCOL)
                        response = _parse(bytes(plaintext))
                    if response is not None:
                        self._note("complete")
                        return response
                except ssl.SSLWantReadError:
                    self._receive_some()
                except ssl.SSLZeroReturnError:
                    self._note("eof")
                    break
                except ssl.SSLEOFError:
                    self._note("eof")
                    break
        except TransportError as error:
            self._failure = error.failure
            self._note("failure")
            return None
        except ssl.SSLError, OSError:
            self._note("read_error")
            return None
        if decoder is not None:
            self._failure = TransportFailure.PROTOCOL
            self._note("failure")
            return None
        return _parse(bytes(plaintext))

    def _note_chunked(self, decoder: _Chunked) -> None:
        """Copy bounded observations only; parser never reads diagnostic state."""
        if self._diagnostics is None:
            return
        try:
            self._diagnostics = replace(
                self._diagnostics,
                chunks_observed=min(decoder.chunks, 6552),
                decoded_body_bytes=len(decoder.body),
                terminal_chunk_seen=decoder.terminal,
                trailer_present=decoder.trailer,
                body_bytes_observed=min(decoder.wire, _max_response_body()),
                cap_reached=decoder.cap_reached,
            )
        except Exception:
            self._diagnostics = None

    def observe(self, response: HttpResponse | None) -> HandoffObservation:
        self._note("observed")
        return HandoffObservation(
            self.progress(),
            response,
            self._time_violation,
            self._stopped,
            self._failure,
            self._diagnostics,
        )

    def close(self) -> None:
        self._stop()
        if self._selector is not None:
            self._selector.close()
            self._selector = None
        if self._sock is not None:
            self._sock.close()
            self._sock = None


def _response_head(data: bytes | bytearray) -> tuple[int, int | None, int] | None:
    """Validated status, length (None for chunked), body offset; no body copies."""
    end = data.find(b"\r\n\r\n")
    if end < 0:
        if len(data) > _max_header_bytes():
            raise TransportError(TransportFailure.PROTOCOL)
        return None
    if end + 4 > _max_header_bytes():
        raise TransportError(TransportFailure.PROTOCOL)
    head = data[:end].decode("latin-1")
    lines = head.split("\r\n")
    status = lines[0].split(" ", 2)
    if (
        len(lines) > _max_headers() + 1
        or len(status) < 2
        or status[0] not in ("HTTP/1.1", "HTTP/1.0")
        or not status[1].isascii()
        or not status[1].isdigit()
        or len(status[1]) != 3
        or not 200 <= int(status[1]) <= 599
    ):
        raise TransportError(TransportFailure.PROTOCOL)
    length: int | None = None
    transfers: list[str] = []
    for line in lines[1:]:
        name, separator, value = line.partition(":")
        if not separator or not name or name != name.strip():
            raise TransportError(TransportFailure.PROTOCOL)
        lowered = name.lower()
        if lowered == "transfer-encoding":
            transfers.append(value.strip(" \t").lower())
        if (
            lowered == "content-type"
            and value.split(";", 1)[0].strip().lower() == "text/event-stream"
        ):
            raise TransportError(TransportFailure.PROTOCOL)
        if lowered == "content-length":
            value = value.strip()
            if length is not None or not value.isdigit():
                raise TransportError(TransportFailure.PROTOCOL)
            digits = value.lstrip("0") or "0"
            if len(digits) > 7:
                raise TransportError(TransportFailure.PROTOCOL)
            try:
                length = int(digits)
            except ValueError:
                raise TransportError(TransportFailure.PROTOCOL) from None
    if transfers:
        if length is not None or transfers != ["chunked"] or status[0] != "HTTP/1.1":
            raise TransportError(TransportFailure.PROTOCOL)
        return int(status[1]), None, end + 4
    if length is None or length > _max_response_body():
        raise TransportError(TransportFailure.PROTOCOL)
    return int(status[1]), length, end + 4


def _parse(data: bytes) -> HttpResponse | None:
    """Existing fixed-length completion contract; headers share one authority."""
    head = _response_head(data)
    if head is None:
        return None
    status, length, offset = head
    if length is None:
        raise TransportError(TransportFailure.PROTOCOL)
    body = data[offset:]
    if len(body) < length:
        return None
    if len(body) > length:
        raise TransportError(TransportFailure.PROTOCOL)
    return HttpResponse(status, body)


class _Chunked:
    """Private bounded response state; raw data is never rendered or published."""

    def __init__(self, deadline: float) -> None:
        self.deadline = deadline
        self.state = "size"
        self.line = bytearray()
        self.body = bytearray()
        self.remaining = 0
        self.framing = 0
        self.chunks = 0
        self.wire = 0
        self.terminal = False
        self.trailer = False
        self.cap_reached = False

    def _refuse(self, *, cap: bool = False) -> None:
        self.cap_reached = cap
        raise TransportError(TransportFailure.PROTOCOL)

    def feed(self, data: bytes) -> bool:
        self.wire += len(data)
        position = 0
        while position < len(data):
            if time.monotonic() >= self.deadline:
                raise TransportError(TransportFailure.TIMEOUT)
            if self.state == "complete":
                self._refuse()
            if self.state == "data":
                count = min(self.remaining, len(data) - position)
                self.body.extend(data[position : position + count])
                position += count
                self.remaining -= count
                if not self.remaining:
                    self.state = "data_crlf"
                continue
            self.framing += 1
            if self.framing > 32768:
                self._refuse(cap=True)
            value = data[position]
            position += 1
            if self.state == "size" and len(self.line) >= 8:
                self._refuse(cap=True)
            self.line.append(value)
            if self.state == "size":
                if value != 10:
                    if value not in b"0123456789abcdefABCDEF\r":
                        self._refuse()
                    continue
                if not self.line.endswith(b"\r\n"):
                    self._refuse()
                digits = self.line[:-2]
                if not 1 <= len(digits) <= 6 or any(
                    digit not in b"0123456789abcdefABCDEF" for digit in digits
                ):
                    self._refuse()
                size = int(digits, 16)
                self.line.clear()
                if size == 0:
                    self.terminal = True
                    self.state = "trailer_end"
                else:
                    if self.chunks >= 6552 or size > _max_response_body() - len(
                        self.body
                    ):
                        self._refuse(cap=True)
                    self.chunks += 1
                    self.remaining = size
                    self.state = "data"
            else:
                if value != (13 if len(self.line) == 1 else 10):
                    self.trailer = self.state == "trailer_end"
                    self._refuse()
                if len(self.line) == 2:
                    self.line.clear()
                    self.state = "complete" if self.state == "trailer_end" else "size"
        if time.monotonic() >= self.deadline:
            raise TransportError(TransportFailure.TIMEOUT)
        return self.state == "complete"
