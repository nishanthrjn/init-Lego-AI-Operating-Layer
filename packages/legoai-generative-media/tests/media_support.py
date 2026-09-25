import asyncio
import hashlib
import json
import struct
import zlib
from typing import Any

from legoai_generative_media.http import Response
from legoai_generative_media.values import ApprovedWorkflowRef
from legoai_generative_media.workflow import ApprovedWorkflow, template


def workflow() -> ApprovedWorkflow:
    content = json.dumps(template("test.safetensors")).encode()
    return ApprovedWorkflow(
        ApprovedWorkflowRef("test", "1", hashlib.sha256(content).hexdigest()),
        "test.safetensors",
        content,
    )


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


class FakeHTTP:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, bytes]] = []
        self.history: Any = {
            "job-1": {
                "status": {"completed": True, "status_str": "success"},
                "outputs": {
                    "9": {
                        "images": [
                            {"filename": "image.png", "subfolder": "", "type": "output"}
                        ]
                    }
                },
            }
        }
        self.submission: Any = {"prompt_id": "job-1", "node_errors": {}}
        self.image = png()
        self.missing = False
        self.fail_at = ""
        self.wait_at = ""
        self.entered = asyncio.Event()

    async def request(
        self, method: str, path: str, body: bytes = b"", *, limit: int
    ) -> Response:
        self.calls.append((method, path, body))
        if path.startswith(self.fail_at) and self.fail_at:
            raise OSError("fixture failure")
        if path.startswith(self.wait_at) and self.wait_at:
            self.entered.set()
            await asyncio.Event().wait()
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
            data = self.history
        else:
            return Response(200, "image/png", self.image)
        return Response(200, "application/json", json.dumps(data).encode())
