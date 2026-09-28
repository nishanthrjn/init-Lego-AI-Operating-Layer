import asyncio
import hashlib
import json
import struct
import zlib
from typing import Any

from legoai_generative_media.http import Response
from legoai_generative_media.values import ApprovedWorkflowRef, TextToImageRequest
from legoai_generative_media.workflow import ApprovedWorkflow, template


def workflow() -> ApprovedWorkflow:
    content = json.dumps(template("test.safetensors")).encode()
    return ApprovedWorkflow(
        ApprovedWorkflowRef("test", "1", hashlib.sha256(content).hexdigest()),
        "test.safetensors",
        content,
    )


def graph(prompt: str = "red mug", seed: int | None = 42) -> Any:
    return json.loads(workflow().bind(TextToImageRequest(prompt, seed)))["prompt"]


def png() -> bytes:
    def chunk(kind: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + kind
            + data
            + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
        )

    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", 512, 512, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress((b"\0" + b"\x80" * (512 * 3)) * 512))
        + chunk(b"IEND", b"")
    )


class FakeTime:
    """Injected monotonic clock; sleeping advances time without waiting."""

    def __init__(self) -> None:
        self.now = 0.0

    def clock(self) -> float:
        return self.now

    async def sleep(self, seconds: float) -> None:
        self.now += seconds
        await asyncio.sleep(0)


class FakeHTTP:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, bytes]] = []
        self.history: Any = {
            "job-1": {
                # Provider queue tuple: number, id, graph, extra_data, outputs.
                "prompt": [1, "job-1", graph(), {"create_time": 1}, ["9"]],
                "status": {"completed": True, "status_str": "success", "messages": []},
                "outputs": {
                    "9": {
                        "images": [
                            {"filename": "image.png", "subfolder": "", "type": "output"}
                        ]
                    }
                },
            }
        }
        self.queue: Any = {"queue_running": [], "queue_pending": []}
        self.submission: Any = {"prompt_id": "job-1", "node_errors": {}}
        self.image = png()
        self.missing = False
        self.fail_at = ""
        self.wait_at = ""
        self.entered = asyncio.Event()
        # Simulated long job: queued/running until time.now reaches ready_at.
        self.time: FakeTime | None = None
        self.ready_at = 0.0

    def running(self) -> bool:
        return self.time is not None and self.time.now < self.ready_at

    def posts(self) -> int:
        return len([c for c in self.calls if c[0] == "POST"])

    async def request(
        self, method: str, path: str, body: bytes = b"", *, limit: int
    ) -> Response:
        self.calls.append((method, path, body))
        if path.startswith(self.fail_at) and self.fail_at:
            raise OSError("fixture failure")
        if path.startswith(self.wait_at) and self.wait_at:
            self.entered.set()
            await asyncio.Event().wait()
        data: Any
        if path.startswith("/object_info/"):
            node = path.rsplit("/", 1)[-1]
            data = (
                {}
                if self.missing
                else {
                    node: {"input": {"required": {"ckpt_name": [["test.safetensors"]]}}}
                }
            )
        elif path == "/prompt":
            data = self.submission
        elif path.startswith("/history/"):
            data = {} if self.running() else self.history
        elif path == "/queue":
            data = (
                {
                    "queue_running": [[1, "job-1", graph(), {}, ["9"]]],
                    "queue_pending": [],
                }
                if self.running()
                else self.queue
            )
        elif path.startswith("/view?"):
            return Response(200, "image/png", self.image)
        else:
            raise AssertionError("unexpected route " + path)
        return Response(200, "application/json", json.dumps(data).encode())
