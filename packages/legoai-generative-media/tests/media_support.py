import asyncio
import hashlib
import json
import re
import struct
import zlib
from pathlib import Path
from typing import Any

from legoai_generative_media.http import Headers, NotSent, Response
from legoai_generative_media.tryon import (
    ApprovedTryOnWorkflow,
    TryOnModels,
    tryon_template,
)
from legoai_generative_media.values import (
    ApprovedWorkflowRef,
    TextToImageRequest,
    UploadedImageRef,
)
from legoai_generative_media.workflow import ApprovedWorkflow, template

TRYON_MODELS = TryOnModels(
    "qwen_image_edit_2509_fp8_e4m3fn.safetensors",
    "qwen_2.5_vl_7b_fp8_scaled.safetensors",
    "qwen_image_vae.safetensors",
)
PERSON_REF = UploadedImageRef("11111111-1111-4111-8111-111111111111.png")
GARMENT_REF = UploadedImageRef("22222222-2222-4222-8222-222222222222.png")


def tryon_workflow(models: TryOnModels = TRYON_MODELS) -> ApprovedTryOnWorkflow:
    content = json.dumps(tryon_template(models)).encode()
    return ApprovedTryOnWorkflow(
        ApprovedWorkflowRef("tryon", "1", hashlib.sha256(content).hexdigest()),
        models,
        content,
    )


def tryon_graph(seed: int | None = 7) -> Any:
    return tryon_workflow().graph(PERSON_REF, GARMENT_REF, seed)


def write_tryon_workflow(directory: Path) -> tuple[Path, str]:
    approved = tryon_workflow()
    path = directory / "tryon_workflow.json"
    path.write_bytes(approved.content)
    return path, approved.reference.sha256


def workflow() -> ApprovedWorkflow:
    content = json.dumps(template("test.safetensors")).encode()
    return ApprovedWorkflow(
        ApprovedWorkflowRef("test", "1", hashlib.sha256(content).hexdigest()),
        "test.safetensors",
        content,
    )


def graph(prompt: str = "red mug", seed: int | None = 42) -> Any:
    return json.loads(workflow().bind(TextToImageRequest(prompt, seed)))["prompt"]


def chunk(kind: bytes, data: bytes) -> bytes:
    return (
        struct.pack(">I", len(data))
        + kind
        + data
        + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    )


def png() -> bytes:
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", 512, 512, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress((b"\0" + b"\x80" * (512 * 3)) * 512))
        + chunk(b"IEND", b"")
    )


Chunks = tuple[tuple[bytes, bytes], ...]


def make_png(
    width: int = 64,
    height: int = 64,
    *,
    color: int = 2,
    depth: int = 8,
    interlace: int = 0,
    before: Chunks = (),
    after: Chunks = (),
    idat_parts: int = 1,
    trailing: bytes = b"",
) -> bytes:
    """Synthetic PNG only: flat pixels, optional extra chunks around IDAT."""
    channels = 4 if color == 6 else 3
    compressed = zlib.compress((b"\0" + b"\x80" * (width * channels)) * height)
    step = -(-len(compressed) // idat_parts)
    idats = b"".join(
        chunk(b"IDAT", compressed[i : i + step])
        for i in range(0, len(compressed), step)
    )
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(
            b"IHDR",
            struct.pack(">IIBBBBB", width, height, depth, color, 0, 0, interlace),
        )
        + b"".join(chunk(k, d) for k, d in before)
        + idats
        + b"".join(chunk(k, d) for k, d in after)
        + chunk(b"IEND", b"")
        + trailing
    )


def chunks_of(data: bytes) -> list[tuple[bytes, bytes]]:
    """(type, whole chunk bytes) in order, for structural assertions."""
    out, offset = [], 8
    while offset < len(data):
        size = struct.unpack_from(">I", data, offset)[0]
        end = offset + 12 + size
        out.append((data[offset + 4 : offset + 8], data[offset:end]))
        offset = end
    return out


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
        self.upload_modes: list[str] = []
        self.uploaded: list[bytes] = []
        self.upload_headers: list[Headers] = []
        # object_info model lists per loader input; missing node classes.
        self.models: dict[str, tuple[str, ...]] = {
            "ckpt_name": ("test.safetensors",),
            "unet_name": (TRYON_MODELS.diffusion_model,),
            "clip_name": (TRYON_MODELS.text_encoder,),
            "vae_name": (TRYON_MODELS.vae,),
        }
        self.missing_nodes: set[str] = set()
        self.running_graph: Any = None  # Graph recorded for a running job.

    def prompts(self) -> list[Any]:
        """Submitted API graphs, in order."""
        return [
            json.loads(c[2])["prompt"]
            for c in self.calls
            if c[:2] == ("POST", "/prompt")
        ]

    def uploads(self) -> int:
        return len([c for c in self.calls if c[:2] == ("POST", "/upload/image")])

    def use_tryon_job(self, seed: int = 7) -> None:
        """History for job-1 recorded as an approved try-on graph."""
        self.history["job-1"]["prompt"][2] = tryon_graph(seed)
        self.running_graph = tryon_graph(seed)
        self.image = make_png(768, 1024)

    def running(self) -> bool:
        return self.time is not None and self.time.now < self.ready_at

    def posts(self) -> int:
        return len([c for c in self.calls if c[0] == "POST"])

    async def request(
        self,
        method: str,
        path: str,
        body: bytes = b"",
        *,
        limit: int,
        headers: Headers = (),
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
            required = {field: [list(files)] for field, files in self.models.items()}
            data = (
                {}
                if self.missing or node in self.missing_nodes
                else {node: {"input": {"required": required}}}
            )
        elif path == "/prompt":
            data = self.submission
        elif path.startswith("/history/"):
            data = {} if self.running() else self.history
        elif path == "/queue":
            data = (
                {
                    "queue_running": [
                        [
                            1,
                            "job-1",
                            graph()
                            if self.running_graph is None
                            else self.running_graph,
                            {},
                            ["9"],
                        ]
                    ],
                    "queue_pending": [],
                }
                if self.running()
                else self.queue
            )
        elif path.startswith("/view?"):
            return Response(200, "image/png", self.image)
        elif path == "/upload/image" and method == "POST":
            return self.upload(body, headers)
        elif path == "/system_stats":
            data = {"system": {"comfyui_version": "0.37.0"}}
        else:
            raise AssertionError("unexpected route " + path)
        return Response(200, "application/json", json.dumps(data).encode())

    def upload(self, body: bytes, headers: Headers) -> Response:
        """Scripted /upload/image: one mode per call, 'ok' when unscripted."""
        mode = self.upload_modes.pop(0) if self.upload_modes else "ok"
        if mode == "not_sent":
            raise NotSent("fixture: connection refused")
        self.uploaded.append(body)
        self.upload_headers.append(headers)
        if mode == "lost":
            raise OSError("fixture: reset after send")
        match = re.search(rb'filename="([^"]+)"', body)
        assert match is not None
        name = match.group(1).decode("ascii")
        if mode == "status500":
            return Response(500, "application/json", b'{"error": {"code": "boom"}}')
        if mode == "oversized":
            return Response(200, "application/json", b" " * (70 * 1024))
        data: Any = {"name": name, "subfolder": "", "type": "temp"}
        if mode == "malformed":
            data = {"name": name}
        elif mode == "rename":
            data = {**data, "name": name[:-4] + " (1).png"}
        return Response(200, "application/json", json.dumps(data).encode())


def write_workflow(directory: Path) -> tuple[Path, str]:
    approved = workflow()
    path = directory / "workflow.json"
    path.write_bytes(approved.content)
    return path, approved.reference.sha256


def json_response(status: int, data: Any) -> Response:
    return Response(status, "application/json", json.dumps(data).encode())


def envelope(status: int, code: str) -> Response:
    return json_response(status, {"error": {"code": code, "message": "provider text"}})


V2_JOB = "7f3d2c1b-9a8e-4d6f-b012-3c4d5e6f7a8b"
V2_ASSET = "11111111-2222-4333-8444-555555555555"
SIGNED = "https://storage.googleapis.com/comfy-assets/x.png?X-Goog-Signature=abc"


class FakeV2:
    """Deterministic Comfy API v2 surface (docs.comfy.org/api-reference/v2)."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str, bytes, Headers]] = []
        self.status = "succeeded"
        self.submit: Response | None = None  # Override the 201 acknowledgement.
        self.recorded: Any = graph()
        self.format = "api"
        self.image = png()
        self.redirect: str | None = None
        self.known = True
        self.not_found_code = "not_found"  # Spec code; live Cloud: job_not_found.
        self.fail_at = ""
        self.outputs: Any = None
        self.time: FakeTime | None = None
        self.ready_at = 0.0

    def posts(self) -> int:
        return len([c for c in self.calls if c[0] == "POST"])

    def job(self) -> dict[str, Any]:
        running = self.time is not None and self.time.now < self.ready_at
        status = "running" if running else self.status
        outputs = [
            {
                "node_id": "9",
                "name": "images",
                "type": "output",
                "content_type": "image/png",
                "size_bytes": len(self.image),
                "id": V2_ASSET,
                "url": SIGNED,
                "url_expires_at": "2026-09-28T12:00:00Z",
            }
        ]
        return {
            "id": V2_JOB,
            "status": status,
            "outputs": (self.outputs if self.outputs is not None else outputs)
            if status == "succeeded"
            else [],
            "error": None,
        }

    async def request(
        self,
        method: str,
        path: str,
        body: bytes = b"",
        *,
        limit: int,
        headers: Headers = (),
    ) -> Response:
        self.calls.append((method, path, body, headers))
        if self.fail_at and path.startswith(self.fail_at):
            raise OSError("fixture failure")
        if method == "POST" and path == "/api/v2/jobs":
            if self.submit is not None:
                return self.submit
            self.recorded = json.loads(body)["workflow"]
            return json_response(201, {**self.job(), "status": "queued", "outputs": []})
        if method != "GET":
            raise AssertionError("unexpected write " + path)
        if path == f"/api/v2/jobs/{V2_JOB}" and self.known:
            return json_response(200, self.job())
        if path == f"/api/v2/jobs/{V2_JOB}/workflow" and self.known:
            return json_response(
                200, {"format": self.format, "workflow": self.recorded}
            )
        if path.startswith("/api/v2/jobs/"):
            return envelope(404, self.not_found_code)
        if path == f"/api/v2/assets/{V2_ASSET}/content":
            if self.redirect is not None:
                return Response(302, "", b"", self.redirect)
            return Response(200, "image/png", self.image)
        return Response(404, "text/plain", b"404: Not Found")


class FakeStorage:
    """Signed-URL object store: no credentials expected."""

    def __init__(self, image: bytes) -> None:
        self.calls: list[tuple[str, str]] = []
        self.image = image

    async def request(
        self,
        method: str,
        path: str,
        body: bytes = b"",
        *,
        limit: int,
        headers: Headers = (),
    ) -> Response:
        self.calls.append((method, path))
        return Response(200, "application/octet-stream", self.image)


class Transports:
    """Test TransportFactory: records (origin, token) and routes by origin."""

    def __init__(self, routes: dict[str, Any]) -> None:
        self.routes = routes
        self.opened: list[tuple[str, str | None]] = []

    def __call__(self, origin: str, token: str | None) -> Any:
        self.opened.append((origin, token))
        if origin not in self.routes:
            raise AssertionError("unexpected origin " + origin)
        return self.routes[origin]


def tryon_request(seed: int | None = 7) -> Any:
    """Synthetic person/garment PNGs only (ADR-020: no real photos in tests)."""
    from legoai_generative_media.values import ImageInput, TryOnRequest

    return TryOnRequest(
        ImageInput(make_png(96, 128)), ImageInput(make_png(80, 80, color=6)), seed
    )


def tryon_adapter(
    http: Any,
    time: FakeTime | None = None,
    *,
    local: bool = True,
    driver: Any = None,
    wait: float = 300,
) -> Any:
    """The try-on engine over a fake legacy provider, with fake time."""
    from legoai_generative_media.comfyui import CompletionPolicy
    from legoai_generative_media.drivers.legacy import LegacyDriver
    from legoai_generative_media.virtual_try_on import ComfyVirtualTryOnAdapter

    time = time or FakeTime()
    if hasattr(http, "use_tryon_job") and http.image == png():
        # Default fake output becomes the approved try-on geometry; tests of
        # other sizes must set http.image after constructing the adapter.
        http.image = make_png(768, 1024)
    return ComfyVirtualTryOnAdapter(
        tryon_workflow(),
        driver or LegacyDriver(http),
        completion=CompletionPolicy(wait, 1, 10),
        clock=time.clock,
        sleep=time.sleep,
        local=local,
    )
