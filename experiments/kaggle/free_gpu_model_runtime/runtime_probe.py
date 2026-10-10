"""Isolated operator-run Kaggle experiment; importing this module performs no I/O.

No LegoAI imports. No credentials. Public weight downloads are distinct from
inference: generation uses only the fixed notebook-local vLLM process.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import importlib
import importlib.metadata
import json
import os
import platform
import re
import signal
import socket
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

EXPERIMENT = "FREE-GPU-MODEL-RUNTIME-KAGGLE-1C"
RUNTIME_PYTHON_MAJOR = 3
RUNTIME_PYTHON_MINOR = 12
MANAGED_PYTHON = "3.12.12"
UV_VERSION = "0.9.5"
SYSTEM_UV = Path("/usr/local/bin/uv")
SYSTEM_PYTHONS = (Path("/usr/bin/python3.12"), Path("/usr/local/bin/python3.12"))
REASONS = frozenset(
    {
        "BASE_PLATFORM_UNSUPPORTED",
        "CUDA_UNAVAILABLE",
        "GPU_COUNT_UNSUPPORTED",
        "GPU_MODEL_UNSUPPORTED",
        "GPU_MEMORY_UNSUPPORTED",
        "GPU_CAPABILITY_UNSUPPORTED",
        "DRIVER_CUDA_UNSUPPORTED",
        "RUNTIME_PYTHON_NOT_FOUND",
        "RUNTIME_PYTHON_INVALID",
        "RUNTIME_ENV_CREATION_FAILED",
        "UV_PINNED_BOOTSTRAP_FAILED",
        "UV_TOOL_VERSION_UNACCEPTED",
        "RUNTIME_PYTHON_VERSION_MISMATCH",
        "RUNTIME_PACKAGE_VERSION_MISMATCH",
        "EXISTING_EVIDENCE",
        "INTERNAL_BOUNDED_FAILURE",
        "RUNTIME_ISOLATION_FAILED",
    }
)
MODEL = "Qwen/Qwen2.5-Coder-14B-Instruct-AWQ"
REVISION = "eb3172f06a6d6b3a15f08947b0668d782e4d2d2c"
SOURCE = Path(__file__).resolve().parent
WORK = Path("/kaggle/working")
SCRATCH = Path("/tmp/legoai-kaggle-runtime-1")
PYTHON = SCRATCH / "venv/bin/python"
MODEL_DIR = SCRATCH / "model"
RESULT = WORK / "kaggle_runtime_result.json"
HOST = "127.0.0.1"
PORT = 8765
MAX_GENERATIONS = 3
PROMPT_DIGEST = "8cc5101e5668bb803fb682bd276f47fdb4087ed99335a0f36506791b9b535015"
MAX_INPUT_CHARS = 512
MAX_INPUT_TOKENS = 256
MAX_OUTPUT_TOKENS = 96
MAX_RESPONSE_BYTES = 16384
START_TIMEOUT = 600
REQUEST_TIMEOUT = 90
DOWNLOAD_TIMEOUT = 1800
INSTALL_TIMEOUT = 1800
RUN_TIMEOUT = 960
FILES = (
    "config.json",
    "generation_config.json",
    "merges.txt",
    "vocab.json",
    "tokenizer.json",
    "tokenizer_config.json",
    "model.safetensors.index.json",
    "model-00001-of-00003.safetensors",
    "model-00002-of-00003.safetensors",
    "model-00003-of-00003.safetensors",
)
OUTCOMES = frozenset(
    {
        "KAGGLE_GPU_READY",
        "DEPENDENCIES_READY",
        "MODEL_DOWNLOADED",
        "LOCAL_PROTOCOL_READY",
        "SYNTHETIC_READY",
        "KAGGLE_RUNTIME_PASS",
        "MODEL_DOWNLOAD_FAILED",
        "MODEL_LOAD_FAILED",
        "RUNTIME_START_FAILED",
        "LOCAL_PROTOCOL_FAILED",
        "SYNTHETIC_INFERENCE_FAILED",
        "RESOURCE_EXHAUSTED",
        "RESULT_INCONCLUSIVE",
        "ZERO_COST_REQUIREMENT_VIOLATED",
    }
)


class Stop(Exception):
    """Closed diagnostic; arbitrary exception text is never serialized."""

    def __init__(self, outcome: str, reason: str = "INTERNAL_BOUNDED_FAILURE") -> None:
        if outcome not in OUTCOMES:
            raise ValueError("unknown outcome")
        if reason not in REASONS:
            raise ValueError("unknown reason")
        self.outcome = outcome
        self.reason = reason


def clean_environment() -> dict[str, str]:
    # Construct from constants, never inherit notebook credentials or proxy settings.
    return {
        "PATH": "/usr/local/nvidia/bin:/usr/local/cuda/bin:/usr/local/bin:/usr/bin:/bin",
        "HOME": str(SCRATCH / "home"),
        "TMPDIR": str(SCRATCH),
        "LANG": "C.UTF-8",
        "UV_PYTHON_INSTALL_DIR": str(SCRATCH / "pythons"),
        "UV_PYTHON_BIN_DIR": str(SCRATCH / "bin"),
        "UV_HTTP_RETRIES": "0",
        "UV_HTTP_TIMEOUT": "30",
        "PYTHONUNBUFFERED": "1",
        "HF_HUB_OFFLINE": "1",
        "TRANSFORMERS_OFFLINE": "1",
        "HF_HUB_DISABLE_TELEMETRY": "1",
        "VLLM_NO_USAGE_STATS": "1",
        "DO_NOT_TRACK": "1",
        "VLLM_USE_V1": "0",
        "VLLM_ATTENTION_BACKEND": "XFORMERS",
        "VLLM_HOST_IP": HOST,
        "GLOO_SOCKET_IFNAME": "lo",
        "NCCL_SOCKET_IFNAME": "lo",
        "NCCL_IB_DISABLE": "1",
        "VLLM_WORKER_MULTIPROC_METHOD": "spawn",
    }


def safe_version(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9.+_-]{1,96}", value):
        raise Stop("RESULT_INCONCLUSIVE")
    return value


def versions() -> dict[str, Any]:
    selected: dict[str, Any] = {"python": platform.python_version()}
    for name in ("torch", "transformers", "vllm"):
        try:
            selected[name] = safe_version(importlib.metadata.version(name))
        except importlib.metadata.PackageNotFoundError:
            selected[name] = None
    # Names and versions only: no pip freeze URLs, paths, credentials or environment.
    resolved = sorted(
        {
            (safe_version(d.metadata["Name"]), safe_version(d.version))
            for d in importlib.metadata.distributions()
        }
    )
    if len(resolved) > 512:
        raise Stop("RESULT_INCONCLUSIVE")
    selected["resolved"] = [{"name": n, "version": v} for n, v in resolved]
    return selected


def fresh_result() -> dict[str, Any]:
    return {
        "experiment": EXPERIMENT,
        "schema_version": 2,
        "runtime_python_source": "to_be_bootstrapped",
        "system_uv_version": None,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "model": {"id": MODEL, "revision": REVISION, "quantization": "awq-4bit"},
        "settings": {
            "temperature": 0,
            "seed": 0,
            "tensor_parallel_size": 2,
            "max_input_chars": MAX_INPUT_CHARS,
            "max_input_tokens": MAX_INPUT_TOKENS,
            "max_output_tokens": MAX_OUTPUT_TOKENS,
            "max_generations": MAX_GENERATIONS,
            "request_timeout_seconds": REQUEST_TIMEOUT,
        },
        "hardware": {},
        "base_versions": {},
        "runtime_versions": {},
        "phases": [],
        "assertions": [],
        "timings": {
            "download_seconds": None,
            "startup_including_load_seconds": None,
            "model_load_seconds": None,
            "first_token_seconds": None,
        },
        "gpu_memory": {"sampled_peak_used_mib": [], "sampling_complete": True},
        "outcome": "RESULT_INCONCLUSIVE",
    }


def save(result: dict[str, Any]) -> None:
    # All inserted evidence is explicitly projected; no raw exception/response paths.
    encoded = json.dumps(result, indent=2, allow_nan=False) + "\n"
    if len(encoded.encode()) > 131072:
        raise Stop("RESULT_INCONCLUSIVE")
    RESULT.write_text(encoded, encoding="utf-8")
    (WORK / "kaggle_runtime_report.md").write_text(
        f"# {EXPERIMENT}\n\nOutcome: **{result['outcome']}**\n\n"
        "Synthetic runtime feasibility only; no model-quality or ForgeAI claim.\n\n"
        "```json\n" + encoded + "```\n",
        encoding="utf-8",
    )


def phase(
    result: dict[str, Any], name: str, outcome: str, reason: str | None = None
) -> None:
    if outcome not in OUTCOMES:
        raise ValueError("unknown outcome")
    if reason is not None and reason not in REASONS:
        raise ValueError("unknown reason")
    result["phases"].append({"phase": name, "outcome": outcome, "reason": reason})
    result["outcome"] = outcome
    save(result)
    print(f"{name}: {outcome}" + (f" / {reason}" if reason else ""), flush=True)


def hardware() -> dict[str, Any]:
    torch = importlib.import_module("torch")
    available = bool(torch.cuda.is_available())
    count = int(torch.cuda.device_count())
    devices = []
    if count > 8:
        raise Stop("RESULT_INCONCLUSIVE")
    for index in range(count):
        prop = torch.cuda.get_device_properties(index)
        name = str(prop.name)
        if not re.fullmatch(r"[A-Za-z0-9 ()_-]{1,80}", name):
            raise Stop("RESULT_INCONCLUSIVE")
        devices.append(
            {
                "index": index,
                "name": name,
                "total_memory_bytes": int(prop.total_memory),
                "capability": list(torch.cuda.get_device_capability(index)),
            }
        )
    driver: list[str] = []
    banner = ""
    try:
        driver = (
            subprocess.run(
                ["nvidia-smi", "--query-gpu=driver_version", "--format=csv,noheader"],
                capture_output=True,
                text=True,
                check=True,
                timeout=10,
            )
            .stdout.strip()
            .splitlines()
        )
        banner = subprocess.run(
            ["nvidia-smi"], capture_output=True, text=True, check=True, timeout=10
        ).stdout
    except (OSError, subprocess.SubprocessError):
        # Preserve actual CUDA availability/count even when no driver utility
        # is available. Missing driver evidence fails the candidate gate.
        driver = []
    match = re.search(r"CUDA Version: (\d+\.\d+)", banner)
    return {
        "cuda_available": available,
        "device_count": count,
        "devices": devices,
        "torch_cuda_runtime": (
            safe_version(torch.version.cuda) if torch.version.cuda is not None else None
        ),
        "driver_versions": [safe_version(v.strip()) for v in driver[:8]],
        "driver_visible_cuda": match.group(1) if match else None,
    }


def require_hardware(observed: dict[str, Any]) -> None:
    if not observed["cuda_available"]:
        raise Stop("RESULT_INCONCLUSIVE", "CUDA_UNAVAILABLE")
    if observed["device_count"] != 2:
        raise Stop("RESULT_INCONCLUSIVE", "GPU_COUNT_UNSUPPORTED")
    for device in observed["devices"]:
        for valid, reason in (
            ("T4" in device["name"], "GPU_MODEL_UNSUPPORTED"),
            (device["capability"] == [7, 5], "GPU_CAPABILITY_UNSUPPORTED"),
            (
                14 * 2**30 <= device["total_memory_bytes"] <= 17 * 2**30,
                "GPU_MEMORY_UNSUPPORTED",
            ),
        ):
            if not valid:
                raise Stop("RESULT_INCONCLUSIVE", reason)
    visible = observed["driver_visible_cuda"]
    if visible is None or tuple(map(int, visible.split("."))) < (12, 8):
        raise Stop("RESULT_INCONCLUSIVE", "DRIVER_CUDA_UNSUPPORTED")


def stop_process(process: subprocess.Popen[bytes], *, group: bool = True) -> None:
    # Linux only. Outer workers own sessions; server descendants inherit them.
    try:
        if group:
            os.killpg(process.pid, signal.SIGTERM)
        else:
            process.terminate()
    except ProcessLookupError:
        return
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        if group:
            os.killpg(process.pid, signal.SIGKILL)
        else:
            process.kill()
        process.wait(timeout=10)
    finally:
        if group:
            # The leader can exit before its descendants; do not leave those
            # running just because wait() has reaped the leader successfully.
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass  # The owned process group has already disappeared.


def bounded_process(args: list[str], timeout: int) -> None:
    process = subprocess.Popen(
        args,
        env=clean_environment(),
        start_new_session=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        if process.wait(timeout=timeout) != 0:
            raise Stop("RESULT_INCONCLUSIVE")
    finally:
        stop_process(process)


class DownloadRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(
        self, req: Any, fp: Any, code: int, msg: str, headers: Any, newurl: str
    ) -> Any:
        parsed = urllib.parse.urlsplit(newurl)
        host = parsed.hostname or ""
        if (
            parsed.scheme != "https"
            or parsed.username
            or parsed.password
            or not (
                host == "huggingface.co"
                or host.endswith(".huggingface.co")
                or host.endswith(".hf.co")
            )
        ):
            raise Stop("MODEL_DOWNLOAD_FAILED")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def download() -> None:
    MODEL_DIR.mkdir(exist_ok=False)
    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({}), DownloadRedirect()
    )
    total = 0
    deadline = time.monotonic() + DOWNLOAD_TIMEOUT - 10
    for filename in FILES:
        url = f"https://huggingface.co/{MODEL}/resolve/{REVISION}/{filename}"
        # No auth handler, token lookup, Hub client retries or alternate model.
        with (
            opener.open(url, timeout=30) as response,
            (MODEL_DIR / filename).open("xb") as out,
        ):
            if response.status != 200:
                raise Stop("MODEL_DOWNLOAD_FAILED")
            size = 0
            limit = 5 * 2**30 if filename.endswith(".safetensors") else 16 * 2**20
            while True:
                if time.monotonic() >= deadline:
                    raise Stop("MODEL_DOWNLOAD_FAILED")
                block = response.read(1024 * 1024)
                if not block:
                    break
                size += len(block)
                total += len(block)
                if size > limit or total > 12 * 2**30:
                    raise Stop("RESOURCE_EXHAUSTED")
                out.write(block)
            length = response.headers.get("Content-Length")
            if size == 0 or (length is not None and size != int(length)):
                raise Stop("MODEL_DOWNLOAD_FAILED")


def prompts() -> list[dict[str, str]]:
    with (SOURCE / "fixtures/synthetic_prompts.json").open("rb") as source:
        raw = source.read(4097).replace(b"\r\n", b"\n")
    if len(raw) > 4096 or hashlib.sha256(raw).hexdigest() != PROMPT_DIGEST:
        raise Stop("RESULT_INCONCLUSIVE")
    values: Any = json.loads(raw)
    if not isinstance(values, list) or len(values) != MAX_GENERATIONS:
        raise Stop("RESULT_INCONCLUSIVE")
    for entry, identity in zip(values, ("ready", "json", "add"), strict=True):
        if (
            not isinstance(entry, dict)
            or set(entry) != {"id", "prompt"}
            or entry["id"] != identity
            or not isinstance(entry["prompt"], str)
            or not 1 <= len(entry["prompt"]) <= MAX_INPUT_CHARS
        ):
            raise Stop("RESULT_INCONCLUSIVE")
    return values


def output_matches(identity: str, content: str) -> bool:
    if len(content) > 4096:
        return False
    if identity == "ready":
        return content == "READY"
    if identity == "json":
        return content.strip() == '{"status":"ready"}'
    if identity == "add":
        try:
            actual = ast.dump(ast.parse(content), include_attributes=False)
            expected = ast.dump(
                ast.parse("def add(a: int, b: int) -> int:\n    return a + b\n"),
                include_attributes=False,
            )
            return actual == expected
        except (SyntaxError, ValueError, RecursionError):
            return False
    return False


def local_request(path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    if path not in ("/v1/models", "/v1/chat/completions"):
        raise Stop("LOCAL_PROTOCOL_FAILED")
    # HTTPConnection bypasses proxies and never follows redirects or retries.
    from http.client import HTTPConnection, HTTPException

    connection = HTTPConnection(HOST, PORT, timeout=REQUEST_TIMEOUT)
    try:
        connection.request(
            "GET" if payload is None else "POST",
            path,
            body=None if payload is None else json.dumps(payload),
            headers={"Content-Type": "application/json"},
        )
        response = connection.getresponse()
        body = response.read(MAX_RESPONSE_BYTES + 1)
        if response.status != 200 or len(body) > MAX_RESPONSE_BYTES:
            raise Stop("LOCAL_PROTOCOL_FAILED")
        decoded: Any = json.loads(body)
        if not isinstance(decoded, dict):
            raise Stop("LOCAL_PROTOCOL_FAILED")
        return decoded
    except (OSError, HTTPException, ValueError):
        raise Stop("LOCAL_PROTOCOL_FAILED") from None
    finally:
        connection.close()


def server_command() -> list[str]:
    return [
        str(PYTHON),
        "-m",
        "vllm.entrypoints.openai.api_server",
        "--model",
        str(MODEL_DIR),
        "--tokenizer",
        str(MODEL_DIR),
        "--served-model-name",
        MODEL,
        "--host",
        HOST,
        "--port",
        str(PORT),
        "--dtype",
        "half",
        "--quantization",
        "awq",
        "--tensor-parallel-size",
        "2",
        "--distributed-executor-backend",
        "mp",
        "--max-model-len",
        "512",
        "--max-num-seqs",
        "1",
        "--gpu-memory-utilization",
        "0.80",
        "--swap-space",
        "0",
        "--cpu-offload-gb",
        "0",
        "--seed",
        "0",
        "--enforce-eager",
        "--disable-custom-all-reduce",
        "--generation-config",
        "vllm",
        "--disable-log-requests",
        "--disable-log-stats",
    ]


def sample_memory(result: dict[str, Any]) -> None:
    try:
        lines = (
            subprocess.run(
                [
                    "nvidia-smi",
                    "--query-gpu=memory.used",
                    "--format=csv,noheader,nounits",
                ],
                capture_output=True,
                text=True,
                check=True,
                timeout=5,
            )
            .stdout.strip()
            .splitlines()
        )
        current = [int(v) for v in lines]
        if len(current) != 2 or any(v < 0 or v > 17408 for v in current):
            raise ValueError("memory observation")
        previous = result["gpu_memory"]["sampled_peak_used_mib"] or [0, 0]
        result["gpu_memory"]["sampled_peak_used_mib"] = [
            max(a, b) for a, b in zip(previous, current, strict=True)
        ]
    except (OSError, ValueError, subprocess.SubprocessError):
        result["gpu_memory"]["sampling_complete"] = False


def validate_chat(response: dict[str, Any], identity: str) -> dict[str, Any]:
    try:
        choices = response["choices"]
        usage = response["usage"]
        prompt_count, completion_count = (
            usage["prompt_tokens"],
            usage["completion_tokens"],
        )
        valid = (
            response["model"] == MODEL
            and len(choices) == 1
            and choices[0]["finish_reason"] == "stop"
            and choices[0]["message"]["role"] == "assistant"
            and type(prompt_count) is int
            and 0 < prompt_count <= MAX_INPUT_TOKENS
            and type(completion_count) is int
            and 0 < completion_count <= MAX_OUTPUT_TOKENS
        )
        content = choices[0]["message"]["content"]
        if not valid or not isinstance(content, str):
            raise Stop("LOCAL_PROTOCOL_FAILED")
        return {
            "id": identity,
            "passed": output_matches(identity, content),
            "prompt_tokens": prompt_count,
            "completion_tokens": completion_count,
        }
    except (KeyError, IndexError, TypeError):
        raise Stop("LOCAL_PROTOCOL_FAILED") from None


def serve_and_probe(result: dict[str, Any]) -> None:
    tokenizer = importlib.import_module("transformers").AutoTokenizer.from_pretrained(
        str(MODEL_DIR),
        local_files_only=True,
        trust_remote_code=False,
    )
    cases = prompts()
    for case in cases:
        encoded = tokenizer.apply_chat_template(
            [{"role": "user", "content": case["prompt"]}],
            tokenize=True,
            add_generation_prompt=True,
        )
        if len(encoded) > MAX_INPUT_TOKENS:
            raise Stop("SYNTHETIC_INFERENCE_FAILED")
    # Refuse an occupied port; never send prompts to an unrelated local server.
    with socket.socket() as check:
        check.bind((HOST, PORT))
    start = time.monotonic()
    # Inherit the worker process group so the outer watchdog also owns every
    # server descendant, including on timeout or notebook interruption.
    process = subprocess.Popen(
        server_command(),
        env=clean_environment(),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        for _ in range(300):
            if process.poll() is not None or time.monotonic() - start >= START_TIMEOUT:
                raise Stop("RUNTIME_START_FAILED")
            sample_memory(result)
            try:
                with socket.create_connection((HOST, PORT), timeout=1):
                    break
            except OSError:
                time.sleep(2)
        else:
            raise Stop("RUNTIME_START_FAILED")
        result["timings"]["startup_including_load_seconds"] = round(
            time.monotonic() - start, 3
        )
        catalog = local_request("/v1/models")
        if [item["id"] for item in catalog.get("data", [])] != [MODEL]:
            raise Stop("LOCAL_PROTOCOL_FAILED")
        phase(result, "local_protocol", "LOCAL_PROTOCOL_READY")
        for case in cases:
            start = time.monotonic()
            response = local_request(
                "/v1/chat/completions",
                {
                    "model": MODEL,
                    "messages": [{"role": "user", "content": case["prompt"]}],
                    "temperature": 0,
                    "seed": 0,
                    "max_tokens": MAX_OUTPUT_TOKENS,
                    "n": 1,
                    "stream": False,
                },
            )
            assertion = validate_chat(response, case["id"])
            assertion["total_seconds"] = round(time.monotonic() - start, 3)
            result["assertions"].append(assertion)
            sample_memory(result)
            save(result)
            if not assertion["passed"]:
                raise Stop("SYNTHETIC_INFERENCE_FAILED")
        phase(result, "synthetic", "SYNTHETIC_READY")
    finally:
        stop_process(process, group=False)


def inspect_interpreter(
    executable: Path, *, isolated: bool = False, pristine: bool = False
) -> str:
    script = (
        "import sys,json,site,importlib.util; print(json.dumps({"
        "'version':list(sys.version_info[:3]),'implementation':sys.implementation.name,"
        "'venv':sys.prefix != sys.base_prefix,'user_site':site.ENABLE_USER_SITE,"
        "'inherited':any(importlib.util.find_spec(n) is not None for n in ('torch','transformers'))}))"
    )
    try:
        completed = subprocess.run(
            [str(executable), "-I", "-c", script],
            env=clean_environment(),
            capture_output=True,
            text=True,
            check=True,
            timeout=15,
        )
        if len(completed.stdout) > 1024:
            raise ValueError("bounded observation")
        info = json.loads(completed.stdout)
        version = info["version"]
        if info["implementation"] != "cpython" or version[:2] != [
            RUNTIME_PYTHON_MAJOR,
            RUNTIME_PYTHON_MINOR,
        ]:
            raise Stop("RESULT_INCONCLUSIVE", "RUNTIME_PYTHON_VERSION_MISMATCH")
        if isolated:
            config = (executable.parent.parent / "pyvenv.cfg").read_text()
            if (
                not info["venv"]
                or info["user_site"] is not False
                or "include-system-site-packages = false" not in config.lower()
            ):
                raise Stop("RESULT_INCONCLUSIVE", "RUNTIME_ISOLATION_FAILED")
        if pristine and info.get("inherited") is not False:
            raise Stop("RESULT_INCONCLUSIVE", "RUNTIME_ISOLATION_FAILED")
        return safe_version(".".join(str(v) for v in version))
    except FileNotFoundError:
        reason = "RUNTIME_ISOLATION_FAILED" if isolated else "RUNTIME_PYTHON_NOT_FOUND"
        raise Stop("RESULT_INCONCLUSIVE", reason) from None
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError):
        raise Stop("RESULT_INCONCLUSIVE", "RUNTIME_PYTHON_INVALID") from None


def system_python() -> Path | None:
    for candidate in SYSTEM_PYTHONS:
        if candidate.is_file():
            inspect_interpreter(candidate)
            return candidate
    return None


def uv_version(executable: Path) -> str:
    try:
        result = subprocess.run(
            [str(executable), "--version"],
            env=clean_environment(),
            capture_output=True,
            text=True,
            check=True,
            timeout=15,
        )
    except (OSError, subprocess.SubprocessError):
        raise Stop("RESULT_INCONCLUSIVE", "UV_PINNED_BOOTSTRAP_FAILED") from None
    parts = result.stdout.split()
    if (
        len(result.stdout) > 128
        or len(parts) < 2
        or parts[0] != "uv"
        or re.fullmatch(r"[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}", parts[1]) is None
    ):
        raise Stop("RESULT_INCONCLUSIVE", "UV_TOOL_VERSION_UNACCEPTED")
    return parts[1]


def verify_uv(executable: Path) -> None:
    if uv_version(executable) != UV_VERSION:
        raise Stop("RESULT_INCONCLUSIVE", "UV_TOOL_VERSION_UNACCEPTED")


def resolve_uv(result: dict[str, Any]) -> Path:
    if SYSTEM_UV.is_file():
        # Bounded observation only; a different version grants no execution authority.
        result["system_uv_version"] = uv_version(SYSTEM_UV)
        if result["system_uv_version"] == UV_VERSION:
            return SYSTEM_UV
    tooling = SCRATCH / "tools"
    if tooling.exists() or tooling.is_symlink():
        raise Stop("RESULT_INCONCLUSIVE", "UV_PINNED_BOOTSTRAP_FAILED")
    try:
        bounded_process(
            [
                sys.executable,
                "-I",
                "-m",
                "pip",
                "--isolated",
                "install",
                "--no-input",
                "--target",
                str(tooling),
                "--index-url",
                "https://pypi.org/simple",
                "--only-binary=:all:",
                "--no-deps",
                "--retries",
                "0",
                "--timeout",
                "30",
                "--no-cache-dir",
                "--disable-pip-version-check",
                f"uv=={UV_VERSION}",
            ],
            180,
        )
        uv = tooling / "bin/uv"
        if (
            not uv.is_file()
            or uv.is_symlink()
            or not uv.resolve().is_relative_to(tooling.resolve())
        ):
            raise Stop("RESULT_INCONCLUSIVE", "UV_PINNED_BOOTSTRAP_FAILED")
        verify_uv(uv)
    except Stop as error:
        if error.reason == "UV_TOOL_VERSION_UNACCEPTED":
            raise
        raise Stop("RESULT_INCONCLUSIVE", "UV_PINNED_BOOTSTRAP_FAILED") from None
    except (OSError, subprocess.SubprocessError):
        raise Stop("RESULT_INCONCLUSIVE", "UV_PINNED_BOOTSTRAP_FAILED") from None
    return uv


def create_runtime(result: dict[str, Any]) -> None:
    target = SCRATCH / "venv"
    if target.exists() or target.is_symlink():
        raise Stop("RESULT_INCONCLUSIVE", "RUNTIME_ENV_CREATION_FAILED")
    interpreter = system_python()
    uv = resolve_uv(result)
    if interpreter is None:
        try:
            bounded_process(
                [
                    str(uv),
                    "--no-config",
                    "python",
                    "install",
                    f"cpython-{MANAGED_PYTHON}-linux-x86_64-gnu",
                ],
                300,
            )
        except (Stop, OSError, subprocess.SubprocessError):
            raise Stop("RESULT_INCONCLUSIVE", "RUNTIME_PYTHON_NOT_FOUND") from None
        interpreter = (
            SCRATCH
            / "pythons"
            / f"cpython-{MANAGED_PYTHON}-linux-x86_64-gnu/bin/python3.12"
        )
        result["runtime_python_source"] = "uv_managed"
    else:
        result["runtime_python_source"] = "system"
    inspect_interpreter(interpreter)
    try:
        bounded_process(
            [
                str(uv),
                "--no-config",
                "venv",
                "--python",
                str(interpreter),
                "--no-python-downloads",
                "--seed",
                "--index-url",
                "https://pypi.org/simple",
                str(target),
            ],
            180,
        )
    except (Stop, OSError, subprocess.SubprocessError):
        raise Stop("RESULT_INCONCLUSIVE", "RUNTIME_ENV_CREATION_FAILED") from None
    if not PYTHON.is_file():
        raise Stop("RESULT_INCONCLUSIVE", "RUNTIME_ENV_CREATION_FAILED")
    result["runtime_versions"] = {
        "python": inspect_interpreter(PYTHON, isolated=True, pristine=True)
    }
    save(result)


def require_packages(observed: dict[str, Any]) -> None:
    expected = {"vllm": "0.9.2", "torch": "2.7.0", "transformers": "4.51.3"}
    if any(
        not isinstance(observed.get(k), str) or observed[k].split("+")[0] != v
        for k, v in expected.items()
    ):
        raise Stop("RESULT_INCONCLUSIVE", "RUNTIME_PACKAGE_VERSION_MISMATCH")


def worker(result: dict[str, Any]) -> None:
    inspect_interpreter(PYTHON, isolated=True)
    result["runtime_versions"] = versions()
    require_packages(result["runtime_versions"])
    result["hardware"] = hardware()
    save(result)
    require_hardware(result["hardware"])
    serve_and_probe(result)
    phase(result, "qualification", "KAGGLE_RUNTIME_PASS")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "mode",
        choices=("inspect", "bootstrap", "run", "_inventory", "_download", "_worker"),
    )
    parser.add_argument("--confirm-free-session", action="store_true")
    args = parser.parse_args()
    if (
        platform.system() != "Linux"
        or platform.machine() != "x86_64"
        or not WORK.is_dir()
        or not Path("/kaggle/input").is_dir()
    ):
        print("RESULT_INCONCLUSIVE / BASE_PLATFORM_UNSUPPORTED")
        return 1
    if args.mode == "inspect" and RESULT.exists():
        print("RESULT_INCONCLUSIVE / EXISTING_EVIDENCE")
        return 1
    if args.mode in ("bootstrap", "run") and RESULT.exists():
        previous = json.loads(RESULT.read_text(encoding="utf-8"))
        required = (
            "KAGGLE_GPU_READY" if args.mode == "bootstrap" else "MODEL_DOWNLOADED"
        )
        if previous["outcome"] != required or (
            args.mode == "bootstrap"
            and ((SCRATCH / "venv").exists() or (SCRATCH / "venv").is_symlink())
        ):
            print("RESULT_INCONCLUSIVE / EXISTING_EVIDENCE")
            return 1
    result = fresh_result()
    active = args.mode
    if not args.confirm_free_session and RESULT.exists():
        print("ZERO_COST_REQUIREMENT_VIOLATED / EXISTING_EVIDENCE")
        return 1
    try:
        if not args.confirm_free_session:
            raise Stop("ZERO_COST_REQUIREMENT_VIOLATED")
        if args.mode != "inspect":
            SCRATCH.mkdir(exist_ok=True)
            (SCRATCH / "home").mkdir(exist_ok=True)
        if args.mode == "inspect":
            # Base inventory is deliberately limited; large Kaggle package sets
            # are not needed. Full resolved inventory is captured for the venv.
            result["base_versions"] = {"python": platform.python_version()}
            for name in ("torch", "transformers", "vllm"):
                try:
                    result["base_versions"][name] = safe_version(
                        importlib.metadata.version(name)
                    )
                except importlib.metadata.PackageNotFoundError:
                    result["base_versions"][name] = None
            result["hardware"] = hardware()
            save(result)
            require_hardware(result["hardware"])
            result["runtime_python_source"] = (
                "system" if system_python() is not None else "to_be_bootstrapped"
            )
            phase(result, active, "KAGGLE_GPU_READY")
        else:
            result = json.loads(RESULT.read_text(encoding="utf-8"))
            if args.mode == "bootstrap":
                if (
                    result["outcome"] != "KAGGLE_GPU_READY"
                    or (SCRATCH / "venv").exists()
                ):
                    raise Stop("RESULT_INCONCLUSIVE")
                create_runtime(result)
                bounded_process(
                    [
                        str(PYTHON),
                        "-m",
                        "pip",
                        "--isolated",
                        "install",
                        "--index-url",
                        "https://pypi.org/simple",
                        "--retries",
                        "0",
                        "--extra-index-url",
                        "https://download.pytorch.org/whl/cu128",
                        "--timeout",
                        "30",
                        "--no-cache-dir",
                        "--only-binary=:all:",
                        "--disable-pip-version-check",
                        "-r",
                        str(SOURCE / "requirements-kaggle.txt"),
                    ],
                    INSTALL_TIMEOUT,
                )
                phase(result, "dependencies", "DEPENDENCIES_READY")
                bounded_process(
                    [
                        str(PYTHON),
                        str(Path(__file__).resolve()),
                        "_inventory",
                        "--confirm-free-session",
                    ],
                    60,
                )
                result = json.loads(RESULT.read_text(encoding="utf-8"))
                active = "download"
                start = time.monotonic()
                bounded_process(
                    [
                        str(PYTHON),
                        str(Path(__file__).resolve()),
                        "_download",
                        "--confirm-free-session",
                    ],
                    DOWNLOAD_TIMEOUT,
                )
                result["timings"]["download_seconds"] = round(
                    time.monotonic() - start, 3
                )
                phase(result, active, "MODEL_DOWNLOADED")
            elif args.mode == "_inventory":
                result["runtime_versions"] = versions()
                require_packages(result["runtime_versions"])
                save(result)
            elif args.mode == "_download":
                download()
            elif args.mode == "run":
                if result["outcome"] != "MODEL_DOWNLOADED":
                    raise Stop("RESULT_INCONCLUSIVE")
                # Mark consumed before starting: no repeat generation on rerun.
                phase(result, "run", "RESULT_INCONCLUSIVE")
                bounded_process(
                    [
                        str(PYTHON),
                        str(Path(__file__).resolve()),
                        "_worker",
                        "--confirm-free-session",
                    ],
                    RUN_TIMEOUT,
                )
            elif args.mode == "_worker":
                worker(result)
        return 0
    except (Exception, KeyboardInterrupt) as error:
        if args.mode in ("run", "bootstrap") and RESULT.exists():
            result = json.loads(RESULT.read_text(encoding="utf-8"))
            last = result["phases"][-1] if result["phases"] else {}
            if (
                last.get("phase") in ("_worker", "_inventory", "_download")
                and last.get("reason") in REASONS
            ):
                print(
                    f"{last['phase']}: {last['outcome']} / {last['reason']}", flush=True
                )
                return 1
            if result["outcome"] in OUTCOMES - {
                "RESULT_INCONCLUSIVE",
                "KAGGLE_GPU_READY",
                "DEPENDENCIES_READY",
                "MODEL_DOWNLOADED",
                "LOCAL_PROTOCOL_READY",
                "SYNTHETIC_READY",
                "KAGGLE_RUNTIME_PASS",
            }:
                print(result["outcome"], flush=True)
                return 1
        outcome = error.outcome if isinstance(error, Stop) else "RESULT_INCONCLUSIVE"
        if active in ("download", "_download") and outcome == "RESULT_INCONCLUSIVE":
            outcome = "MODEL_DOWNLOAD_FAILED"
        reason = error.reason if isinstance(error, Stop) else "INTERNAL_BOUNDED_FAILURE"
        phase(result, active, outcome, reason)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
