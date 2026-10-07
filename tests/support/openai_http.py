"""Process-local scripted HTTP transport; never contacts a real provider."""

import json
import socket
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


@dataclass
class Script:
    body: object
    status: int = 200
    mode: str = "complete"
    requests: list[tuple[str, dict[str, str], object]] = field(default_factory=list)
    release: threading.Event = field(default_factory=threading.Event)


@contextmanager
def server(script: Script) -> Iterator[str]:
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            raw = self.rfile.read(int(self.headers["Content-Length"]))
            script.requests.append((self.path, dict(self.headers), json.loads(raw)))
            if script.mode == "timeout":
                script.release.wait(2)
                return
            if script.mode == "reset":
                self.connection.shutdown(socket.SHUT_RDWR)
                self.connection.close()
                return
            payload = script.body
            if script.mode == "by-path":
                assert isinstance(payload, dict)
                payload = payload[self.path]
            body = (
                payload if isinstance(payload, bytes) else json.dumps(payload).encode()
            )
            self.send_response(script.status)
            self.send_header("Content-Type", "application/json")
            self.send_header(
                "Content-Length",
                str(len(body) + (10 if script.mode == "truncated" else 0)),
            )
            if script.status == 302:
                self.send_header("Location", "/must-not-follow")
            self.send_header("Retry-After", "0")
            self.end_headers()
            self.wfile.write(body)
            self.wfile.flush()
            self.close_connection = True

        def log_message(self, format: str, *args: object) -> None:
            pass

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(
        target=httpd.serve_forever, kwargs={"poll_interval": 0.01}
    )
    thread.start()
    try:
        yield f"http://127.0.0.1:{httpd.server_port}/v1"
    finally:
        script.release.set()
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=2)
        assert not thread.is_alive()


def chat_payload() -> dict[str, object]:
    return {
        "model": "chat-model",
        "choices": [
            {
                "message": {"role": "assistant", "content": "hello"},
                "finish_reason": "stop",
            }
        ],
    }


def embedding_payload() -> dict[str, object]:
    return {
        "model": "embed-model",
        "data": [{"index": 0, "embedding": [1, 0]}, {"index": 1, "embedding": [0, 1]}],
    }
