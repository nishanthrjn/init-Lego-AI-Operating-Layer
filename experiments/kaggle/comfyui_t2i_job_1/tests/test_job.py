"""Offline contracts: no downloads, installs, server, subprocess or GPU workload."""

from __future__ import annotations

import ast
import hashlib
import io
import json
import platform
import re
import struct
import subprocess
import sys
import urllib.error
import urllib.request
import zlib
from email.message import Message
from pathlib import Path
from typing import Any

import pytest

from experiments.kaggle.comfyui_t2i_job_1 import job_runner as job
from experiments.kaggle.comfyui_t2i_job_1 import runtime_probe as runtime


@pytest.fixture
def manifest() -> dict[str, Any]:
    value = job.read_json(job.SOURCE / "job_manifest.json")
    value.update(
        comfyui_commit="a" * 40,
        checkpoint_sha256=hashlib.sha256(b"checkpoint").hexdigest(),
        checkpoint_bytes=10,
    )
    return value


def test_manifest_placeholders_are_refused() -> None:
    assert job.pin_errors(job.read_json(job.SOURCE / "job_manifest.json")) == [
        "comfyui_commit",
        "checkpoint_sha256",
        "checkpoint_bytes",
    ]


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("comfyui_commit", "a" * 39),
        ("comfyui_commit", "g" * 40),
        ("checkpoint_sha256", "z" * 64),
        ("checkpoint_bytes", True),
        ("checkpoint_bytes", 0),
        ("prompt", ""),
        ("prompt", "   "),
        ("prompt", "x\n"),
        ("prompt", "x\x7f"),
        ("prompt", "é" * 2049),
        ("seed", True),
        ("seed", -1),
        ("seed", 2**63),
        ("max_job_seconds", 0),
        ("uv_version", "0.9.5"),
        ("python_version", "3.14.0"),
        ("checkpoint_url", "https://example.com/a"),
    ],
)
def test_invalid_manifest(field: str, value: Any, manifest: dict[str, Any]) -> None:
    manifest[field] = value
    assert field in job.pin_errors(manifest)


def test_prompt_utf8_boundary_and_config(
    manifest: dict[str, Any], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest["prompt"] = "é" * 2048
    assert job.pin_errors(manifest) == []
    config = (job.ROOT / job.CONFIG).read_text(encoding="utf-8")
    assert f'checkpoint = "{job.CHECKPOINT}"' in config
    assert manifest["checkpoint_url"].endswith("/" + job.CHECKPOINT)
    # Model the fresh LF Kaggle checkout in a temporary fixture. Windows Git
    # expands this tracked LF file to CRLF; production must not normalize it.
    raw = (job.ROOT / job.WORKFLOW).read_bytes().replace(b"\r\n", b"\n")
    config_path = tmp_path / job.CONFIG
    workflow_path = tmp_path / job.WORKFLOW
    config_path.parent.mkdir(parents=True)
    workflow_path.parent.mkdir(parents=True)
    config_path.write_bytes(config.encode("utf-8"))
    workflow_path.write_bytes(raw)
    monkeypatch.setattr(job, "ROOT", tmp_path)
    workflow = job.config_workflow()
    assert (
        workflow["sha256"]
        == hashlib.sha256((job.ROOT / workflow["path"]).read_bytes()).hexdigest()
    )


@pytest.mark.parametrize("change", ["crlf", "content"])
def test_workflow_exact_bytes_remain_required(
    change: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = (job.ROOT / job.CONFIG).read_bytes()
    raw = (job.ROOT / job.WORKFLOW).read_bytes().replace(b"\r\n", b"\n")
    config_path = tmp_path / job.CONFIG
    workflow_path = tmp_path / job.WORKFLOW
    config_path.parent.mkdir(parents=True)
    workflow_path.parent.mkdir(parents=True)
    config_path.write_bytes(config)
    workflow_path.write_bytes(raw)
    monkeypatch.setattr(job, "ROOT", tmp_path)
    job.config_workflow()
    altered = raw.replace(b"\n", b"\r\n") if change == "crlf" else raw + b" "
    assert altered != raw
    workflow_path.write_bytes(altered)
    with pytest.raises(job.Stop, match="PIN_MISSING"):
        job.config_workflow()


def test_exact_argv(manifest: dict[str, Any]) -> None:
    assert job.comfy_argv() == [
        sys.executable,
        "main.py",
        "--listen",
        "127.0.0.1",
        "--port",
        "8188",
        "--disable-all-custom-nodes",
    ]
    assert job.generate_argv("/python", manifest) == [
        "/python",
        "examples/comfyui-text-to-image/generate.py",
        "--config",
        job.CONFIG,
        "--prompt",
        manifest["prompt"],
        "--seed",
        "42",
        "--output",
        str(job.OUTPUT / "image.png"),
    ]
    assert job.git_argv(job.COMFY_REPO, "a" * 40) == [
        ["git", "init"],
        ["git", "remote", "add", "origin", job.COMFY_REPO],
        ["git", "fetch", "--depth", "1", "origin", "a" * 40],
        ["git", "checkout", "--detach", "FETCH_HEAD"],
        ["git", "rev-parse", "HEAD"],
    ]
    assert runtime.pip_uv_argv(Path("req"), Path("tools")) == [
        sys.executable,
        "-I",
        "-m",
        "pip",
        "--isolated",
        "install",
        "--no-input",
        "--target",
        "tools",
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
        "--require-hashes",
        "-r",
        "req",
    ]
    assert job.pip_argv("freeze") == [
        sys.executable,
        "-I",
        "-m",
        "pip",
        "--isolated",
        "freeze",
    ]


def test_requirements_filter() -> None:
    source = "torch>=2\n TorchVision ==0.2\ntorchaudio; python_version>'3'\nTORCH\ntorch-sde==1\nsafetensors\n# torch\n"
    assert job.filter_requirements(source) == "torch-sde==1\nsafetensors\n# torch\n"


@pytest.mark.parametrize("mismatch", [None, "hash", "short", "long", "401", "403"])
def test_streaming_checkpoint(
    mismatch: str | None,
    manifest: dict[str, Any],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Opener:
        def open(self, url: str, timeout: float) -> io.BytesIO:
            assert url == job.CHECKPOINT_URL and timeout == 30
            if mismatch in ("401", "403"):
                raise urllib.error.HTTPError(
                    url, int(mismatch), "PRIVATE", Message(), None
                )
            return io.BytesIO(b"checkpoint")

    monkeypatch.setattr(urllib.request, "build_opener", lambda *args: Opener())
    if mismatch == "hash":
        manifest["checkpoint_sha256"] = "0" * 64
    if mismatch in ("short", "long"):
        manifest["checkpoint_bytes"] = 9 if mismatch == "long" else 11
    path = tmp_path / job.CHECKPOINT
    if mismatch is None:
        job.download(manifest, path, float("inf"))
        assert path.read_bytes() == b"checkpoint"
    else:
        with pytest.raises(job.Stop) as error:
            job.download(manifest, path, float("inf"))
        assert error.value.status == (
            "DOWNLOAD_AUTH_REQUIRED"
            if mismatch in ("401", "403")
            else "CHECKPOINT_MISMATCH"
        )
        assert not path.exists()
    assert not path.with_suffix(".partial").exists()


def test_readiness_deadline() -> None:
    now = 0.0
    calls = []

    def fetch(timeout: float) -> dict[str, Any]:
        calls.append(timeout)
        raise OSError("PRIVATE")

    def sleep(delay: float) -> None:
        nonlocal now
        now += delay

    with pytest.raises(job.Stop, match="COMFYUI_NOT_READY"):
        job.ready(3, fetch, lambda: now, sleep)
    assert now == 3 and calls == [3, 2, 1]


def test_generate_failure_has_one_attempt(
    manifest: dict[str, Any], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(job, "OUTPUT", tmp_path)
    monkeypatch.setattr(job, "SCRATCH", tmp_path)
    (tmp_path / "logs").mkdir()
    calls = []

    def command(argv: list[str], timeout: float, cwd: Path | None = None) -> Any:
        calls.append(argv)
        assert cwd == job.ROOT
        return subprocess.CompletedProcess(argv, 1, "PRIVATE", "PRIVATE")

    monkeypatch.setattr(runtime, "command", command)
    state = {"client_executable": "/python", "deadline": float("inf")}
    with pytest.raises(job.Stop, match="GENERATION_FAILED"):
        job.generate(state, manifest)
    assert calls == [job.generate_argv("/python", manifest)]
    assert "PRIVATE" not in (tmp_path / "logs/client-stderr.txt").read_text()


def png() -> bytes:
    def chunk(kind: bytes, value: bytes) -> bytes:
        return (
            struct.pack(">I", len(value))
            + kind
            + value
            + struct.pack(">I", zlib.crc32(kind + value))
        )

    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", 512, 512, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(b"\0" * (512 * 3 + 1) * 512))
        + chunk(b"IEND", b"")
    )


def test_png_metadata_and_corruption() -> None:
    raw = png()
    assert job.image_info(raw) == {
        "sha256": hashlib.sha256(raw).hexdigest(),
        "bytes": len(raw),
        "width": 512,
        "height": 512,
    }
    for corrupt in (b"", raw[:-1], raw + b"x", raw[:16] + b"x" + raw[17:]):
        with pytest.raises(job.Stop, match="FINISH_FAILED"):
            job.image_info(corrupt)


def validate_schema(value: Any, schema: dict[str, Any]) -> None:
    """Interpret the closed subset used by this schema without new dependencies."""
    kinds: dict[str, Any] = {
        "null": type(None),
        "object": dict,
        "array": list,
        "string": str,
        "integer": int,
        "number": (int, float),
    }
    if "type" in schema:
        names = schema["type"] if isinstance(schema["type"], list) else [schema["type"]]
        assert any(
            isinstance(value, kinds[name])
            and (name not in ("integer", "number") or type(value) is not bool)
            for name in names
        )
    if "const" in schema:
        assert value == schema["const"]
    if "enum" in schema:
        assert value in schema["enum"]
    if isinstance(value, dict):
        assert set(schema.get("required", [])) <= value.keys()
        properties = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            assert value.keys() <= properties.keys()
        for key, item in value.items():
            validate_schema(item, properties[key])
    if isinstance(value, list):
        assert (
            schema.get("minItems", 0)
            <= len(value)
            <= schema.get("maxItems", float("inf"))
        )
        for item in value:
            validate_schema(item, schema.get("items", {}))
    if isinstance(value, str):
        assert (
            schema.get("minLength", 0)
            <= len(value)
            <= schema.get("maxLength", float("inf"))
        )
        if "pattern" in schema:
            assert re.search(schema["pattern"], value)
    if type(value) in (int, float):
        assert (
            schema.get("minimum", -float("inf"))
            <= value
            <= schema.get("maximum", float("inf"))
        )


@pytest.mark.parametrize("status", job.STATUSES)
def test_provenance(
    status: str,
    manifest: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("PRIVATE_TEST", "PRIVATE-CANARY")
    monkeypatch.setattr(job, "OUTPUT", tmp_path)
    (tmp_path / "logs").mkdir()
    job.log("client-stderr.txt", "PRIVATE-CANARY" * 2000)
    state = {
        "legoai_commit": "a" * 40,
        "environment": {"SECRET": "PRIVATE-CANARY"},
        "image": job.image_info(png()),
    }
    result = job.provenance(state, manifest, status)
    validate_schema(result, job.read_json(job.SOURCE / "provenance.schema.json"))
    assert "PRIVATE-CANARY" not in json.dumps(result)
    assert all(len(t.encode()) <= job.LOG_LIMIT for t in result["log_tails"].values())
    assert (result["image"] is not None) == (status == "GENERATED")
    with pytest.raises(ValueError):
        job.provenance(state, manifest, "UNKNOWN")


def test_schema_rejects_unknown_status(manifest: dict[str, Any]) -> None:
    record = job.provenance({"legoai_commit": "a" * 40}, manifest, "NO_GPU")
    record["status"] = "UNKNOWN"
    with pytest.raises(AssertionError):
        validate_schema(record, job.read_json(job.SOURCE / "provenance.schema.json"))


def test_notebook_and_grammar() -> None:
    raw = (job.SOURCE / "kaggle_job.ipynb").read_text(encoding="utf-8")
    for token in (
        "0.0.0.0",
        "ngrok",
        "cloudflared",
        "localtunnel",
        "HF_TOKEN",
        "KAGGLE_KEY",
        "UserSecretsClient",
    ):
        assert token not in raw
    notebook = json.loads(raw)
    assert notebook["nbformat"] == 4
    code = [c for c in notebook["cells"] if c["cell_type"] == "code"]
    assert [c["id"] for c in code] == [
        "parameters",
        "checkout",
        *job.PHASES,
        "artifacts",
    ]
    for cell in code:
        assert cell["outputs"] == [] and cell["execution_count"] is None
        ast.parse("".join(cell["source"]), feature_version=(3, 10))
    for name in ("job_runner.py", "runtime_probe.py"):
        tree = ast.parse((job.SOURCE / name).read_text(), feature_version=(3, 10))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                assert not any(
                    k.arg == "shell"
                    and isinstance(k.value, ast.Constant)
                    and k.value.value is True
                    for k in node.keywords
                )


def test_uv_exact_version_and_hash(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(runtime, "SCRATCH", tmp_path)
    monkeypatch.setattr(runtime, "SYSTEM_UV", tmp_path / "missing")
    calls = []

    def command(argv: list[str], timeout: float, cwd: Path | None = None) -> Any:
        calls.append(argv)
        if "install" in argv:
            uv = tmp_path / "tools/bin/uv"
            uv.parent.mkdir(parents=True)
            uv.touch()
            assert (
                f"--hash=sha256:{runtime.UV_SHA256}"
                in (tmp_path / "uv-requirements.txt").read_text()
            )
        return subprocess.CompletedProcess(argv, 0, "uv 0.11.13\n", "")

    monkeypatch.setattr(runtime, "command", command)
    assert runtime.resolve_uv() == tmp_path / "tools/bin/uv"
    assert calls == [
        runtime.pip_uv_argv(tmp_path / "uv-requirements.txt", tmp_path / "tools"),
        [str(tmp_path / "tools/bin/uv"), "--version"],
    ]
    monkeypatch.setattr(runtime, "uv_version", lambda path, timeout=15: "0.9.5")
    with pytest.raises(ValueError, match="BOOTSTRAP_FAILED"):
        runtime.verify_uv(tmp_path / "tools/bin/uv")


def test_internet_off_stops_before_io(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "argv", ["job_runner.py", "inspect"])
    monkeypatch.setattr(job, "read_json", lambda path: pytest.fail("no I/O allowed"))
    assert job.main() == 1


def test_phases_are_ordered_and_never_repeated(
    manifest: dict[str, Any], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "job_manifest.json").write_text(json.dumps(manifest))
    monkeypatch.setattr(job, "SOURCE", source)
    monkeypatch.setattr(job, "SCRATCH", tmp_path)
    monkeypatch.setattr(job, "STATE", tmp_path / "state.json")
    monkeypatch.setattr(job, "OUTPUT", tmp_path / "output")
    monkeypatch.setattr(job, "ROOT", tmp_path / "legoai")
    monkeypatch.setattr(platform, "system", lambda: "Linux")
    monkeypatch.setattr(platform, "machine", lambda: "x86_64")
    monkeypatch.setattr(job, "checked", lambda *args: "a" * 40)
    monkeypatch.setattr(job, "config_workflow", lambda: {})
    calls = []

    def action(state: dict[str, Any], selected: dict[str, Any]) -> None:
        calls.append(state["active"])

    for phase in job.PHASES:
        monkeypatch.setattr(job, phase, action)
    for phase in job.PHASES:
        monkeypatch.setattr(
            sys,
            "argv",
            ["job_runner.py", phase, "--legoai-commit", "a" * 40, "--internet-on"],
        )
        assert job.main() == 0
        before = job.STATE.read_bytes()
        assert job.main() == 1
        assert job.STATE.read_bytes() == before
    assert calls == list(job.PHASES)


def test_bootstrap_commands_preserve_system_torch(
    manifest: dict[str, Any], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(job, "SCRATCH", tmp_path)
    monkeypatch.setattr(job, "COMFY", tmp_path / "ComfyUI")
    monkeypatch.setattr(job, "OUTPUT", tmp_path)
    (tmp_path / "logs").mkdir()
    uv = tmp_path / "uv"
    monkeypatch.setattr(runtime, "resolve_uv", lambda deadline: uv)
    monkeypatch.setattr(job, "download", lambda *args: None)
    python = str(tmp_path / "pythons/bin/python")
    inventory = "torch==2.0+cu128\ntorchvision==0.1\ntorchaudio==0.1\n"
    calls = []

    def checked(argv: list[str], state: Any, cwd: Path | None = None) -> str:
        calls.append(argv)
        if argv[:4] == [str(uv), "--no-config", "python", "find"]:
            return python
        if argv[:3] == [python, "-I", "-c"]:
            return "3.14.5"
        if argv == ["git", "rev-parse", "HEAD"]:
            (job.COMFY / "requirements.txt").write_text("torch>=2\nsafetensors\n")
            return str(manifest["comfyui_commit"])
        return inventory

    monkeypatch.setattr(job, "checked", checked)
    state: dict[str, Any] = {"deadline": float("inf")}
    job.bootstrap(state, manifest)
    assert calls[:2] == [
        [
            str(uv),
            "--no-config",
            "python",
            "install",
            "cpython-3.14.5-linux-x86_64-gnu",
        ],
        [
            str(uv),
            "--no-config",
            "python",
            "find",
            "--managed-python",
            "cpython-3.14.5-linux-x86_64-gnu",
        ],
    ]
    assert (
        job.pip_argv(
            "install",
            "--no-input",
            "--retries",
            "0",
            "--timeout",
            "30",
            "--no-cache-dir",
            "--disable-pip-version-check",
            "-c",
            str(tmp_path / "cuda-constraints.txt"),
            "-r",
            str(tmp_path / "comfy-requirements.txt"),
        )
        in calls
    )
    assert (tmp_path / "comfy-requirements.txt").read_text() == "safetensors\n"
    assert (tmp_path / "cuda-constraints.txt").read_text() == inventory
    assert state["client_executable"] == python


def test_bounded_pipe_tail() -> None:
    tail = bytearray()
    runtime.drain(io.BytesIO(b"x" * 100000 + b"last"), tail)
    assert len(tail) == runtime.TAIL_BYTES
    assert tail.endswith(b"last")


def test_loopback_redirect_is_refused() -> None:
    with pytest.raises(ValueError, match="COMFYUI_NOT_READY"):
        job.NoRedirect().redirect_request(
            urllib.request.Request("http://127.0.0.1:8188/system_stats"),
            None,
            302,
            "",
            {},
            "https://example.com",
        )
