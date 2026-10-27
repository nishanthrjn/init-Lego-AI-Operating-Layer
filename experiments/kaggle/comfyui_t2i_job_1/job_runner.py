"""Single-session Kaggle batch job. No I/O occurs at import time."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import shutil
import signal
import struct
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import zlib
from collections.abc import Callable
from pathlib import Path
from typing import Any

# Direct script execution and namespace-package imports use the same checkout.
if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from experiments.kaggle.comfyui_t2i_job_1 import runtime_probe as runtime  # noqa: E402

EXPERIMENT = "KAGGLE-COMFYUI-T2I-JOB-1"
SOURCE = Path(__file__).resolve().parent
ROOT = SOURCE.parents[2]
SCRATCH = Path("/tmp/legoai-c1")
OUTPUT = Path("/kaggle/working/c1")
COMFY = SCRATCH / "ComfyUI"
STATE = SCRATCH / "state.json"
CONFIG = "examples/generative-media-minimal/configs/comfy-local.toml"
WORKFLOW = "comfyui-proof/workflow.json"
CHECKPOINT = "v1-5-pruned-emaonly.safetensors"
COMFY_REPO = "https://github.com/comfyanonymous/ComfyUI"
CHECKPOINT_URL = (
    "https://huggingface.co/stable-diffusion-v1-5/stable-diffusion-v1-5/"
    "resolve/main/" + CHECKPOINT
)
PHASES = ("inspect", "bootstrap", "start", "generate", "finish")
STATUSES = (
    "GENERATED",
    "NO_GPU",
    "PIN_MISSING",
    "BOOTSTRAP_FAILED",
    "DOWNLOAD_AUTH_REQUIRED",
    "CHECKPOINT_MISMATCH",
    "COMFYUI_NOT_READY",
    "GENERATION_FAILED",
    "FINISH_FAILED",
)
LIMITATIONS = [
    "single run; no quality claim",
    "Kaggle hardware varies by session",
    "not a hosted service",
]
NETWORK_ERRORS = (OSError, ValueError, urllib.error.URLError)
MAX_IMAGE = 16 * 1024 * 1024
LOG_LIMIT = 8192


class Stop(Exception):
    def __init__(self, status: str) -> None:
        if status not in STATUSES or status == "GENERATED":
            raise ValueError("unknown failure")
        self.status = status
        super().__init__(status)


def pin_errors(manifest: dict[str, Any]) -> list[str]:
    errors = []
    for key, size in (("comfyui_commit", 40), ("checkpoint_sha256", 64)):
        value = manifest.get(key)
        if not isinstance(value, str) or not re.fullmatch(
            rf"[0-9a-f]{{{size}}}", value
        ):
            errors.append(key)
    for key, value in (
        ("comfyui_repo", COMFY_REPO),
        ("checkpoint_url", CHECKPOINT_URL),
        ("uv_version", runtime.UV_VERSION),
        ("python_version", runtime.PYTHON_VERSION),
    ):
        if manifest.get(key) != value:
            errors.append(key)
    checkpoint_bytes = manifest.get("checkpoint_bytes")
    if type(checkpoint_bytes) is not int or not 1 <= checkpoint_bytes <= 10 * 1024**3:
        errors.append("checkpoint_bytes")
    prompt = manifest.get("prompt")
    if (
        not isinstance(prompt, str)
        or not prompt.strip()
        or len(prompt.encode("utf-8")) > 4096
        or any(ord(c) < 32 or ord(c) == 127 for c in prompt)
    ):
        errors.append("prompt")
    seed = manifest.get("seed")
    if type(seed) is not int or not 0 <= seed < 2**63:
        errors.append("seed")
    limit = manifest.get("max_job_seconds")
    if type(limit) is not int or not 1 <= limit <= 1800:
        errors.append("max_job_seconds")
    return errors


def config_workflow() -> dict[str, str]:
    # The unchanged operator config is TOML; these fixed string fields suffice
    # for a 3.10 launcher without adding a TOML dependency.
    text = (ROOT / CONFIG).read_text(encoding="utf-8")
    checkpoint = re.findall(r'^checkpoint = "([^"]+)"$', text, re.MULTILINE)
    digest = re.findall(r'^sha256 = "([0-9a-f]{64})"$', text, re.MULTILINE)
    path = re.findall(r'^path = "([^"]+)"$', text, re.MULTILINE)
    if checkpoint != [CHECKPOINT] or len(digest) != 1 or len(path) != 1:
        raise Stop("PIN_MISSING")
    if (ROOT / CONFIG).parent.joinpath(path[0]).resolve() != ROOT / WORKFLOW:
        raise Stop("PIN_MISSING")
    if hashlib.sha256((ROOT / WORKFLOW).read_bytes()).hexdigest() != digest[0]:
        raise Stop("PIN_MISSING")
    return {"path": WORKFLOW, "sha256": digest[0]}


def read_json(path: Path) -> dict[str, Any]:
    if path.stat().st_size > 131072:
        raise Stop("BOOTSTRAP_FAILED")
    value = json.loads(path.read_bytes())
    if not isinstance(value, dict):
        raise Stop("BOOTSTRAP_FAILED")
    return value


def save(path: Path, value: dict[str, Any]) -> None:
    raw = json.dumps(value, indent=2, allow_nan=False) + "\n"
    if len(raw.encode()) > 131072:
        raise Stop("FINISH_FAILED")
    temporary = path.with_suffix(".pending")
    temporary.write_text(raw, encoding="utf-8")
    temporary.replace(path)


def remaining(state: dict[str, Any], cap: float) -> float:
    value = min(cap, state["deadline"] - time.monotonic())
    if value <= 0:
        raise Stop("BOOTSTRAP_FAILED")
    return float(value)


def safe_log(text: str, kind: str = "closed") -> str:
    """Keep only a small typed projection, never raw third-party diagnostics."""
    accepted = []
    for line in text[-LOG_LIMIT:].splitlines():
        if kind == "freeze" and re.fullmatch(
            r"[A-Za-z0-9_.-]{1,96}==[A-Za-z0-9.+_-]{1,96}", line
        ):
            accepted.append(line)
        elif kind == "client" and re.fullmatch(
            r"PNG bytes: [0-9]{1,9} SHA-256: [0-9a-f]{64}", line
        ):
            accepted.append(line)
        elif line in STATUSES:
            accepted.append(line)
        else:
            accepted.append("REDACTED")
    return "\n".join(accepted)[-LOG_LIMIT:]


def log(name: str, text: str, kind: str = "closed") -> None:
    (OUTPUT / "logs" / name).write_text(safe_log(text, kind), encoding="utf-8")


def checked(argv: list[str], state: dict[str, Any], cwd: Path | None = None) -> str:
    result = runtime.command(argv, remaining(state, 600), cwd)
    if result.returncode:
        raise Stop("BOOTSTRAP_FAILED")
    return result.stdout


def git_argv(repo: str, commit: str) -> list[list[str]]:
    return [
        ["git", "init"],
        ["git", "remote", "add", "origin", repo],
        ["git", "fetch", "--depth", "1", "origin", commit],
        ["git", "checkout", "--detach", "FETCH_HEAD"],
        ["git", "rev-parse", "HEAD"],
    ]


def filter_requirements(text: str) -> str:
    kept = []
    for line in text.splitlines():
        name = re.match(r"\s*([A-Za-z0-9_.-]+)", line)
        if name and name[1].lower() in {"torch", "torchvision", "torchaudio"}:
            continue
        kept.append(line)
    return "\n".join(kept) + "\n"


def pip_argv(*args: str) -> list[str]:
    return [sys.executable, "-I", "-m", "pip", "--isolated", *args]


class PublicRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(
        self,
        req: urllib.request.Request,
        fp: Any,
        code: int,
        msg: str,
        headers: Any,
        newurl: str,
    ) -> urllib.request.Request | None:
        url = urllib.parse.urlsplit(newurl)
        if (
            url.scheme != "https"
            or url.username is not None
            or url.password is not None
            or not url.hostname
            or not (
                url.hostname == "huggingface.co"
                or url.hostname.endswith(".huggingface.co")
                or url.hostname.endswith(".hf.co")
            )
        ):
            raise Stop("BOOTSTRAP_FAILED")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def download(manifest: dict[str, Any], destination: Path, deadline: float) -> None:
    partial = destination.with_suffix(".partial")
    if destination.exists() or partial.exists():
        raise Stop("BOOTSTRAP_FAILED")
    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({}), PublicRedirect()
    )
    digest = hashlib.sha256()
    size = 0
    try:
        with opener.open(manifest["checkpoint_url"], timeout=30) as response:
            with partial.open("xb") as output:
                while True:
                    if time.monotonic() >= deadline:
                        raise Stop("BOOTSTRAP_FAILED")
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    size += len(chunk)
                    if size > manifest["checkpoint_bytes"]:
                        raise Stop("CHECKPOINT_MISMATCH")
                    digest.update(chunk)
                    output.write(chunk)
        if (
            size != manifest["checkpoint_bytes"]
            or digest.hexdigest() != manifest["checkpoint_sha256"]
        ):
            raise Stop("CHECKPOINT_MISMATCH")
        partial.rename(destination)
    except urllib.error.HTTPError as error:
        if error.code in (401, 403):
            raise Stop("DOWNLOAD_AUTH_REQUIRED") from None
        raise Stop("BOOTSTRAP_FAILED") from None
    finally:
        partial.unlink(missing_ok=True)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(
        self,
        req: urllib.request.Request,
        fp: Any,
        code: int,
        msg: str,
        headers: Any,
        newurl: str,
    ) -> None:
        raise ValueError("COMFYUI_NOT_READY")


def system_stats(timeout: float) -> dict[str, Any]:
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    with opener.open("http://127.0.0.1:8188/system_stats", timeout=timeout) as response:
        raw = response.read(65537)
    if len(raw) > 65536:
        raise ValueError("COMFYUI_NOT_READY")
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ValueError("COMFYUI_NOT_READY")
    return value


def ready(
    deadline: float,
    fetch: Callable[[float], dict[str, Any]] = system_stats,
    clock: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
) -> dict[str, Any]:
    while (left := deadline - clock()) > 0:
        try:
            result = fetch(min(5, left))
            if clock() < deadline and result.get("system") and result.get("devices"):
                return result
        except NETWORK_ERRORS:
            pass
        sleep(max(0, min(1, deadline - clock())))
    raise Stop("COMFYUI_NOT_READY")


def version(value: Any) -> str | None:
    if isinstance(value, str) and re.fullmatch(r"[0-9][A-Za-z0-9.+_-]{0,95}", value):
        return value
    return None


def comfy_argv() -> list[str]:
    return [
        sys.executable,
        "main.py",
        "--listen",
        "127.0.0.1",
        "--port",
        "8188",
        "--disable-all-custom-nodes",
    ]


def generate_argv(python: str, manifest: dict[str, Any]) -> list[str]:
    return [
        python,
        "examples/comfyui-text-to-image/generate.py",
        "--config",
        CONFIG,
        "--prompt",
        manifest["prompt"],
        "--seed",
        str(manifest["seed"]),
        "--output",
        str(OUTPUT / "image.png"),
    ]


def inspect(state: dict[str, Any], manifest: dict[str, Any]) -> None:
    tool = Path("/opt/bin/nvidia-smi")
    if (
        not tool.is_file()
        or tool.is_symlink()
        or tool.resolve() != tool
        or not os.access(tool, os.X_OK)
    ):
        raise Stop("NO_GPU")
    result = runtime.command(
        [str(tool), "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"],
        remaining(state, 10),
    )
    rows = result.stdout.strip().splitlines()
    if result.returncode or not 1 <= len(rows) <= 8:
        raise Stop("NO_GPU")
    devices = []
    for row in rows:
        match = re.fullmatch(r"((?:Tesla|NVIDIA) [A-Za-z0-9 -]{1,64}),\s*([0-9]+)", row)
        if not match or not 0 < int(match[2]) <= 1024 * 1024:
            raise Stop("NO_GPU")
        devices.append({"name": match[1], "memory_mib": int(match[2])})
    state["gpu"] = devices
    state["disk_free"] = {
        "tmp": shutil.disk_usage("/tmp").free,
        "working": shutil.disk_usage("/kaggle/working").free,
    }
    state["python_comfyui"] = platform.python_version()
    observation = checked(
        [
            sys.executable,
            "-I",
            "-c",
            "import json, torch; print(json.dumps({'available': "
            "torch.cuda.is_available(), 'torch': torch.__version__, "
            "'cuda': torch.version.cuda}))",
        ],
        state,
    )
    cuda = json.loads(observation)
    if cuda.get("available") is not True:
        raise Stop("NO_GPU")
    state["cuda"] = version(cuda.get("cuda"))
    state["torch"] = version(cuda.get("torch"))


def bootstrap(state: dict[str, Any], manifest: dict[str, Any]) -> None:
    uv = runtime.resolve_uv(state["deadline"])
    checked([str(uv), "--no-config", "python", "install", runtime.PYTHON_TARGET], state)
    python = checked(
        [
            str(uv),
            "--no-config",
            "python",
            "find",
            "--managed-python",
            runtime.PYTHON_TARGET,
        ],
        state,
    ).strip()
    if not Path(python).resolve().is_relative_to(SCRATCH / "pythons"):
        raise Stop("BOOTSTRAP_FAILED")
    observed = checked(
        [python, "-I", "-c", "import platform; print(platform.python_version())"], state
    )
    if observed.strip() != runtime.PYTHON_VERSION:
        raise Stop("BOOTSTRAP_FAILED")
    state["client_executable"] = python
    state["python_client"] = runtime.PYTHON_VERSION
    COMFY.mkdir()
    for argv in git_argv(COMFY_REPO, manifest["comfyui_commit"]):
        output = checked(argv, state, COMFY)
    if output.strip() != manifest["comfyui_commit"]:
        raise Stop("BOOTSTRAP_FAILED")
    before = checked(pip_argv("freeze"), state)
    log("freeze-before.txt", before, "freeze")
    filtered = SCRATCH / "comfy-requirements.txt"
    filtered.write_text(
        filter_requirements((COMFY / "requirements.txt").read_text(encoding="utf-8")),
        encoding="utf-8",
    )
    # Freeze installed CUDA distributions as constraints as well: transitive
    # requirements must fail resolution rather than replacing Kaggle's builds.
    constraints = SCRATCH / "cuda-constraints.txt"
    inventory = checked(
        [
            sys.executable,
            "-I",
            "-c",
            "from importlib.metadata import version; "
            "print('\\n'.join(n + '==' + version(n) "
            "for n in ('torch', 'torchvision', 'torchaudio')))",
        ],
        state,
    )
    cuda = [
        line
        for line in inventory.splitlines()
        if re.fullmatch(r"(?i)(torch|torchvision|torchaudio)==[A-Za-z0-9.+_-]+", line)
    ]
    if len(cuda) != 3:
        raise Stop("BOOTSTRAP_FAILED")
    constraints.write_text("\n".join(cuda) + "\n", encoding="utf-8")
    checked(
        pip_argv(
            "install",
            "--no-input",
            "--retries",
            "0",
            "--timeout",
            "30",
            "--no-cache-dir",
            "--disable-pip-version-check",
            "-c",
            str(constraints),
            "-r",
            str(filtered),
        ),
        state,
        COMFY,
    )
    after = checked(pip_argv("freeze"), state)
    log("freeze-after.txt", after, "freeze")
    after_cuda = checked(
        [
            sys.executable,
            "-I",
            "-c",
            "from importlib.metadata import version; "
            "print('\\n'.join(n + '==' + version(n) "
            "for n in ('torch', 'torchvision', 'torchaudio')))",
        ],
        state,
    )
    if after_cuda != inventory:
        raise Stop("BOOTSTRAP_FAILED")
    destination = COMFY / "models/checkpoints" / CHECKPOINT
    destination.parent.mkdir(parents=True, exist_ok=True)
    download(manifest, destination, state["deadline"])


def supervisor(deadline: float) -> int:
    """Own the server across notebook cells and stop it at the batch deadline."""
    process = subprocess.Popen(
        comfy_argv(),
        cwd=COMFY,
        env=runtime.environment(),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    assert process.stdout is not None
    tail = bytearray()
    reader = threading.Thread(
        target=runtime.drain, args=(process.stdout, tail), daemon=True
    )
    reader.start()

    def interrupted(signum: int, frame: Any) -> None:
        raise Stop("FINISH_FAILED")

    signal.signal(signal.SIGTERM, interrupted)
    try:
        (SCRATCH / "server-started").touch(exist_ok=False)
        while (
            process.poll() is None
            and time.monotonic() < deadline
            and not (SCRATCH / "server-stop").exists()
        ):
            time.sleep(0.2)
    finally:
        runtime.stop_process(process)
        reader.join(timeout=5)
        log("comfyui.txt", tail.decode("utf-8", errors="replace"))
        (SCRATCH / "server-stopped").touch(exist_ok=False)
    return 0


def stop_server() -> None:
    if not (SCRATCH / "server-requested").exists():
        return
    (SCRATCH / "server-stop").touch(exist_ok=True)
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        if (SCRATCH / "server-stopped").exists():
            return
        time.sleep(0.2)
    raise Stop("FINISH_FAILED")


def start(state: dict[str, Any], manifest: dict[str, Any]) -> None:
    # Refuse an already-listening service; do not submit to an unrelated runtime.
    try:
        system_stats(1)
    except NETWORK_ERRORS:
        pass
    else:
        raise Stop("COMFYUI_NOT_READY")
    (SCRATCH / "server-requested").touch(exist_ok=False)
    subprocess.Popen(
        [
            sys.executable,
            str(SOURCE / "job_runner.py"),
            "_serve",
            "--deadline",
            str(state["deadline"]),
        ],
        env=runtime.environment(),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    stats = ready(time.monotonic() + remaining(state, 300))
    if (
        not (SCRATCH / "server-started").exists()
        or (SCRATCH / "server-stopped").exists()
    ):
        raise Stop("COMFYUI_NOT_READY")
    state["comfyui_version"] = version(stats["system"].get("comfyui_version"))
    state["torch"] = version(stats["system"].get("pytorch_version"))
    devices = stats["devices"]
    if (
        not isinstance(devices, list)
        or not devices
        or any(d.get("type") != "cuda" for d in devices)
    ):
        raise Stop("NO_GPU")
    if state["comfyui_version"] is None or state["torch"] is None:
        raise Stop("COMFYUI_NOT_READY")
    state["cuda_devices"] = [
        {"type": "cuda", "index": int(d["index"]), "vram_total": int(d["vram_total"])}
        for d in devices[:8]
    ]


def generate(state: dict[str, Any], manifest: dict[str, Any]) -> None:
    if (OUTPUT / "image.png").exists() or (SCRATCH / "server-stopped").exists():
        raise Stop("GENERATION_FAILED")
    try:
        result = runtime.command(
            generate_argv(state["client_executable"], manifest),
            remaining(state, manifest["max_job_seconds"]),
            ROOT,
        )
    except runtime.PROCESS_ERRORS:
        raise Stop("GENERATION_FAILED") from None
    log("client-stdout.txt", result.stdout, "client")
    log("client-stderr.txt", result.stderr)
    if result.returncode:
        raise Stop("GENERATION_FAILED")


def image_info(raw: bytes) -> dict[str, Any]:
    if not 45 <= len(raw) <= MAX_IMAGE or raw[:8] != b"\x89PNG\r\n\x1a\n":
        raise Stop("FINISH_FAILED")
    offset = 8
    kinds: list[bytes] = []
    width = height = 0
    while offset < len(raw):
        if offset + 12 > len(raw):
            raise Stop("FINISH_FAILED")
        size = struct.unpack_from(">I", raw, offset)[0]
        end = offset + 12 + size
        if end > len(raw):
            raise Stop("FINISH_FAILED")
        kind = raw[offset + 4 : offset + 8]
        payload = raw[offset + 8 : end - 4]
        if zlib.crc32(kind + payload) != struct.unpack_from(">I", raw, end - 4)[0]:
            raise Stop("FINISH_FAILED")
        if not kinds:
            if kind != b"IHDR" or size != 13:
                raise Stop("FINISH_FAILED")
            width, height = struct.unpack_from(">II", payload)
            if width != 512 or height != 512:
                raise Stop("FINISH_FAILED")
        elif kind == b"IHDR":
            raise Stop("FINISH_FAILED")
        kinds.append(kind)
        offset = end
        if kind == b"IEND":
            if size != 0 or offset != len(raw):
                raise Stop("FINISH_FAILED")
            break
    if kinds[-1] != b"IEND" or b"IDAT" not in kinds:
        raise Stop("FINISH_FAILED")
    return {
        "sha256": hashlib.sha256(raw).hexdigest(),
        "bytes": len(raw),
        "width": width,
        "height": height,
    }


def finish(state: dict[str, Any], manifest: dict[str, Any]) -> None:
    stop_server()
    image = OUTPUT / "image.png"
    if image.stat().st_size > MAX_IMAGE:
        raise Stop("FINISH_FAILED")
    state["image"] = image_info(image.read_bytes())


def provenance(
    state: dict[str, Any], manifest: dict[str, Any], status: str
) -> dict[str, Any]:
    if status not in STATUSES:
        raise ValueError("unknown status")
    # Explicit projection: state includes internal paths and custody markers.
    result: dict[str, Any] = {
        "schema": 1,
        "experiment": EXPERIMENT,
        "status": status,
        "legoai_commit": state["legoai_commit"],
        "comfyui_commit": (
            manifest.get("comfyui_commit") if not pin_errors(manifest) else None
        ),
        "checkpoint": {
            "basename": CHECKPOINT,
            "sha256": (
                manifest.get("checkpoint_sha256") if not pin_errors(manifest) else None
            ),
            "bytes": (
                manifest.get("checkpoint_bytes") if not pin_errors(manifest) else None
            ),
            "license": "CreativeML OpenRAIL-M",
        },
        "workflow": state.get("workflow"),
        "prompt": manifest.get("prompt") if not pin_errors(manifest) else None,
        "seed": manifest.get("seed") if not pin_errors(manifest) else None,
        "image": state.get("image") if status == "GENERATED" else None,
        "phase_seconds": state.get("phase_seconds", {}),
        "log_tails": {},
        "limitations": LIMITATIONS,
    }
    for key in (
        "comfyui_version",
        "python_client",
        "python_comfyui",
        "torch",
        "cuda",
        "gpu",
        "disk_free",
        "cuda_devices",
    ):
        result[key] = state.get(key)
    for name, kind in (
        ("freeze-before.txt", "freeze"),
        ("freeze-after.txt", "freeze"),
        ("client-stdout.txt", "client"),
        ("client-stderr.txt", "closed"),
        ("comfyui.txt", "closed"),
    ):
        path = OUTPUT / "logs" / name
        if path.is_file():
            with path.open("rb") as file:
                file.seek(max(0, path.stat().st_size - LOG_LIMIT))
                result["log_tails"][name] = safe_log(
                    file.read(LOG_LIMIT).decode("utf-8", errors="replace"), kind
                )
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=EXPERIMENT)
    parser.add_argument("phase", choices=(*PHASES, "_serve"))
    parser.add_argument("--legoai-commit", default="")
    parser.add_argument("--internet-on", action="store_true")
    parser.add_argument("--deadline", type=float, default=0)
    args = parser.parse_args()
    if args.phase == "_serve":
        return supervisor(args.deadline)
    if not args.internet_on:
        print("BOOTSTRAP_FAILED: Internet ON required; no offline dataset path")
        return 1
    state: dict[str, Any] = {}
    manifest: dict[str, Any] = {}
    began = time.monotonic()
    claimed = False
    fallback = {
        "inspect": "NO_GPU",
        "bootstrap": "BOOTSTRAP_FAILED",
        "start": "COMFYUI_NOT_READY",
        "generate": "GENERATION_FAILED",
        "finish": "FINISH_FAILED",
    }[args.phase]
    try:
        if platform.system() != "Linux" or platform.machine() != "x86_64":
            raise Stop("BOOTSTRAP_FAILED")
        if not re.fullmatch(r"[0-9a-f]{40}", args.legoai_commit):
            raise Stop("PIN_MISSING")
        manifest = read_json(SOURCE / "job_manifest.json")
        if args.phase == "inspect":
            if STATE.exists() or OUTPUT.exists():
                raise Stop("BOOTSTRAP_FAILED")
            OUTPUT.mkdir(parents=True)
            (OUTPUT / "logs").mkdir()
            state = {
                "legoai_commit": args.legoai_commit,
                "phase_seconds": {},
                "deadline": began + 1800,
                "completed": [],
            }
        else:
            state = read_json(STATE)
            if (
                state.get("active")
                or state.get("failed")
                or state["completed"] != list(PHASES[: PHASES.index(args.phase)])
            ):
                raise Stop("BOOTSTRAP_FAILED")
            if state["legoai_commit"] != args.legoai_commit:
                raise Stop("BOOTSTRAP_FAILED")
        state["active"] = args.phase
        save(STATE, state)
        claimed = True
        if pin_errors(manifest):
            raise Stop("PIN_MISSING")
        if args.phase == "inspect":
            state["deadline"] = began + manifest["max_job_seconds"]
        raw_manifest = hashlib.sha256(
            (SOURCE / "job_manifest.json").read_bytes()
        ).hexdigest()
        if state.get("manifest_digest", raw_manifest) != raw_manifest:
            raise Stop("BOOTSTRAP_FAILED")
        state["manifest_digest"] = raw_manifest
        head = checked(["git", "rev-parse", "HEAD"], state, ROOT).strip()
        if head != args.legoai_commit or ROOT != SCRATCH / "legoai":
            raise Stop("BOOTSTRAP_FAILED")
        state["workflow"] = config_workflow()
        actions = {
            "inspect": inspect,
            "bootstrap": bootstrap,
            "start": start,
            "generate": generate,
            "finish": finish,
        }
        actions[args.phase](state, manifest)
        state["phase_seconds"][args.phase] = round(time.monotonic() - began, 3)
        state["completed"].append(args.phase)
        state["active"] = None
        save(STATE, state)
        if args.phase == "finish":
            save(OUTPUT / "provenance.json", provenance(state, manifest, "GENERATED"))
        print(args.phase + ": OK")
        return 0
    except Exception as error:
        status = error.status if isinstance(error, Stop) else fallback
        if claimed:
            try:
                stop_server()
            except Exception:
                status = "FINISH_FAILED"
            state["failed"] = status
            state["phase_seconds"][args.phase] = round(time.monotonic() - began, 3)
            try:
                save(STATE, state)
                save(OUTPUT / "provenance.json", provenance(state, manifest, status))
            except Exception:
                status = "FINISH_FAILED"
        print(status)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
