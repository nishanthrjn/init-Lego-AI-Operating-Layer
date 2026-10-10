"""Offline contracts: never import torch/vLLM or contact a network/GPU."""

from __future__ import annotations

import ast
import json
import subprocess
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from experiments.kaggle.free_gpu_model_runtime import runtime_probe as probe


def hardware(count: int = 2) -> dict[str, Any]:
    return {
        "cuda_available": True,
        "device_count": count,
        "devices": [
            {"name": "Tesla T4", "capability": [7, 5], "total_memory_bytes": 15 * 2**30}
            for _ in range(count)
        ],
        "driver_visible_cuda": "12.8",
    }


@pytest.mark.parametrize("count", [0, 1, 3])
def test_wrong_gpu_count_stops(count: int) -> None:
    with pytest.raises(probe.Stop):
        probe.require_hardware(hardware(count))


@pytest.mark.parametrize("change", ["name", "memory", "capability", "cuda", "driver"])
def test_hardware_fail_closed(change: str) -> None:
    observed = hardware()
    if change == "name":
        observed["devices"][0]["name"] = "NVIDIA P100"
    elif change == "memory":
        observed["devices"][0]["total_memory_bytes"] = 8 * 2**30
    elif change == "capability":
        observed["devices"][0]["capability"] = [7, 0]
    elif change == "cuda":
        observed["cuda_available"] = False
    else:
        observed["driver_visible_cuda"] = "12.4"
    with pytest.raises(probe.Stop):
        probe.require_hardware(observed)


def test_actual_t4_memory_not_aggregate() -> None:
    probe.require_hardware(hardware())


def test_cpu_assignment_is_recorded_without_driver_utility(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = SimpleNamespace(
        cuda=SimpleNamespace(is_available=lambda: False, device_count=lambda: 0),
        version=SimpleNamespace(cuda=None),
    )
    monkeypatch.setattr(
        probe, "importlib", SimpleNamespace(import_module=lambda name: fake)
    )

    def unavailable(*args: Any, **kwargs: Any) -> Any:
        raise FileNotFoundError("PRIVATE-CANARY")

    monkeypatch.setattr(subprocess, "run", unavailable)
    observed = probe.hardware()
    assert observed["cuda_available"] is False
    assert observed["device_count"] == 0
    assert observed["driver_visible_cuda"] is None
    assert observed["torch_cuda_runtime"] is None
    assert "PRIVATE-CANARY" not in json.dumps(observed)


@pytest.mark.parametrize(
    ("identity", "content", "expected"),
    [
        ("ready", "READY", True),
        ("ready", "READY!", False),
        ("json", '{"status":"ready"}', True),
        ("json", '{"status":"ready","extra":1}', False),
        ("add", "def add(a: int, b: int) -> int:\n    return a + b", True),
        ("add", "def add(a: int, b: int) -> int:\n    return a - b", False),
        ("add", "import os\ndef add(a: int, b: int) -> int:\n    return a + b", False),
        ("add", "```python\ndef add(a,b): return a+b\n```", False),
    ],
)
def test_contracts_never_execute_generated_code(
    identity: str, content: str, expected: bool
) -> None:
    assert probe.output_matches(identity, content) is expected


def response() -> dict[str, Any]:
    return {
        "model": probe.MODEL,
        "choices": [
            {
                "finish_reason": "stop",
                "message": {"role": "assistant", "content": "READY"},
            }
        ],
        "usage": {"prompt_tokens": 16, "completion_tokens": 1},
    }


@pytest.mark.parametrize("mutation", ["model", "length", "usage", "boolean", "shape"])
def test_http_success_is_not_contract_success(mutation: str) -> None:
    value = response()
    if mutation == "model":
        value["model"] = "another-model"
    elif mutation == "length":
        value["choices"][0]["finish_reason"] = "length"
    elif mutation == "usage":
        value["usage"]["completion_tokens"] = 97
    elif mutation == "boolean":
        value["usage"]["prompt_tokens"] = True
    else:
        value["choices"] = None
    with pytest.raises(probe.Stop):
        probe.validate_chat(value, "ready")


def test_safe_projection_drops_canary() -> None:
    value = response()
    value["choices"][0]["message"]["content"] = "PRIVATE-CANARY"
    value["error"] = {"body": "PRIVATE-CANARY"}
    projected = probe.validate_chat(value, "ready")
    assert projected["passed"] is False
    assert "PRIVATE-CANARY" not in json.dumps(projected)


def test_prompts_and_closed_server_configuration() -> None:
    assert len(probe.prompts()) == probe.MAX_GENERATIONS == 3
    command = probe.server_command()
    assert command[command.index("--host") + 1] == "127.0.0.1"
    assert command[command.index("--served-model-name") + 1] == probe.MODEL
    assert command[command.index("--tensor-parallel-size") + 1] == "2"
    assert "--trust-remote-code" not in command
    assert "--enforce-eager" in command
    assert "--disable-log-requests" in command


def test_modified_fixture_is_not_admitted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "fixtures").mkdir()
    (tmp_path / "fixtures/synthetic_prompts.json").write_text(
        json.dumps([{"id": "ready", "prompt": "private input"}])
    )
    monkeypatch.setattr(probe, "SOURCE", tmp_path)
    with pytest.raises(probe.Stop):
        probe.prompts()


def test_no_inherited_credentials_or_proxy(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HF_TOKEN", "CANARY")
    monkeypatch.setenv("HTTPS_PROXY", "CANARY")
    monkeypatch.setenv("CUSTOM_SECRET", "CANARY")
    clean = probe.clean_environment()
    assert "CANARY" not in json.dumps(clean)
    assert "HF_TOKEN" not in clean
    assert clean["VLLM_HOST_IP"] == "127.0.0.1"
    assert clean["HF_HUB_OFFLINE"] == "1"
    assert clean["VLLM_NO_USAGE_STATS"] == "1"


def test_one_http_attempt_no_redirect_or_raw_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import http.client

    calls: list[str] = []

    class Connection:
        def __init__(self, host: str, port: int, timeout: int) -> None:
            assert (host, port, timeout) == (
                probe.HOST,
                probe.PORT,
                probe.REQUEST_TIMEOUT,
            )

        def request(self, *args: Any, **kwargs: Any) -> None:
            calls.append("request")

        def getresponse(self) -> Any:
            return self

        status = 302

        def read(self, size: int) -> bytes:
            assert size == probe.MAX_RESPONSE_BYTES + 1
            return b"PRIVATE-CANARY"

        def close(self) -> None:
            calls.append("close")

    monkeypatch.setattr(http.client, "HTTPConnection", Connection)
    with pytest.raises(probe.Stop) as caught:
        probe.local_request("/v1/models")
    assert caught.value.outcome == "LOCAL_PROTOCOL_FAILED"
    assert calls == ["request", "close"]
    assert "PRIVATE-CANARY" not in str(caught.value)


def test_watchdog_always_cleans_owned_group(monkeypatch: pytest.MonkeyPatch) -> None:
    events: list[str] = []

    class Process:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            assert kwargs["start_new_session"] is True
            assert kwargs["stderr"] == subprocess.DEVNULL
            events.append("start")

        def wait(self, timeout: int) -> int:
            raise subprocess.TimeoutExpired("synthetic", timeout)

    def stop(process: Any) -> None:
        events.append("stop")

    monkeypatch.setattr(subprocess, "Popen", Process)
    monkeypatch.setattr(probe, "stop_process", stop)
    with pytest.raises(subprocess.TimeoutExpired):
        probe.bounded_process(["synthetic"], 1)
    assert events == ["start", "stop"]


@pytest.mark.parametrize(
    "failure", ["none", "startup", "http", "contract", "json_fenced"]
)
def test_generation_ceiling_and_failure_cleanup(
    monkeypatch: pytest.MonkeyPatch, failure: str
) -> None:
    calls: list[str] = []
    stopped: list[bool] = []

    class Tokenizer:
        def apply_chat_template(self, *args: Any, **kwargs: Any) -> list[int]:
            return [1, 2]

        def from_pretrained(self, *args: Any, **kwargs: Any) -> Tokenizer:
            assert kwargs == {"local_files_only": True, "trust_remote_code": False}
            return self

    class Socket:
        def __enter__(self) -> Socket:
            return self

        def __exit__(self, *args: Any) -> None:
            return None

        def bind(self, address: tuple[str, int]) -> None:
            assert address == (probe.HOST, probe.PORT)

    class Process:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            assert "start_new_session" not in kwargs

        def poll(self) -> int | None:
            return 1 if failure == "startup" else None

    def request(path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        calls.append(path)
        if payload is None:
            return {"data": [{"id": probe.MODEL}]}
        assert payload["model"] == probe.MODEL and payload["n"] == 1
        assert payload["temperature"] == 0 and payload["max_tokens"] == 96
        if failure == "http":
            raise probe.Stop("LOCAL_PROTOCOL_FAILED")
        result = response()
        content = [
            "READY",
            '{"status":"ready"}',
            "def add(a: int, b: int) -> int:\n    return a + b",
        ][len(calls) - 2]
        result["choices"][0]["message"]["content"] = (
            "CANARY" if failure == "contract" else content
        )
        if failure == "json_fenced" and len(calls) == 3:
            result["choices"][0]["message"]["content"] = (
                '```json\n{"status":"ready"}\n```'
            )
        if len(calls) == 3:
            assert payload["response_format"] == {"type": "json_object"}
        else:
            assert "response_format" not in payload
        return result

    def stop(process: Any, *, group: bool) -> None:
        stopped.append(group)

    def record(result: dict[str, Any], phase: str, outcome: str) -> None:
        result["outcome"] = outcome

    monkeypatch.setattr(
        probe,
        "importlib",
        SimpleNamespace(
            import_module=lambda name: SimpleNamespace(AutoTokenizer=Tokenizer())
        ),
    )
    monkeypatch.setattr(
        probe,
        "socket",
        SimpleNamespace(socket=Socket, create_connection=lambda *a, **k: Socket()),
    )
    monkeypatch.setattr(subprocess, "Popen", Process)
    monkeypatch.setattr(probe, "stop_process", stop)
    monkeypatch.setattr(probe, "sample_memory", lambda result: None)
    monkeypatch.setattr(probe, "save", lambda result: None)
    monkeypatch.setattr(probe, "phase", record)
    monkeypatch.setattr(probe, "local_request", request)
    result = probe.fresh_result()
    if failure == "none":
        monkeypatch.setattr(probe, "inspect_interpreter", lambda *a, **k: "3.12.3")
        monkeypatch.setattr(
            probe,
            "versions",
            lambda: {"torch": "2.7.0+cu128", "vllm": "0.9.2", "transformers": "4.51.3"},
        )
        monkeypatch.setattr(probe, "hardware", hardware)
        probe.worker(result)
        assert len(result["assertions"]) == 3
        assert result["outcome"] == "KAGGLE_RUNTIME_PASS"
        assert [a["id"] for a in result["assertions"]] == ["ready", "json", "add"]
        assert all(a["passed"] for a in result["assertions"])
        assert len(calls) == 4
    else:
        with pytest.raises(probe.Stop) as error:
            probe.serve_and_probe(result)
        if failure in ("contract", "json_fenced"):
            assert error.value.reason == "SYNTHETIC_OUTPUT_MISMATCH"
            assert error.value.outcome == "SYNTHETIC_INFERENCE_FAILED"
        assert len(calls) == (
            0 if failure == "startup" else 3 if failure == "json_fenced" else 2
        )
        if failure == "json_fenced":
            facts = result["assertions"][-1]["diagnostics"]
            assert facts["has_markdown_fence"] is True
            assert facts["parses_as_json"] is False
            assert facts["semantic_match"] is False
    assert stopped == [False]
    assert "CANARY" not in json.dumps(result)


@pytest.mark.parametrize(
    "url",
    [
        "http://huggingface.co/a",
        "https://evil.example/a",
        "https://user:secret@huggingface.co/a",
    ],
)
def test_download_redirect_boundary(url: str) -> None:
    with pytest.raises(probe.Stop):
        probe.DownloadRedirect().redirect_request(None, None, 302, "", {}, url)


def validate_schema(value: Any, schema: dict[str, Any], root: dict[str, Any]) -> None:
    """Validate the bounded subset used by this experiment's closed JSON schema."""
    if "oneOf" in schema:
        matches = 0
        for variant in schema["oneOf"]:
            try:
                validate_schema(value, variant, root)
            except AssertionError:
                continue
            matches += 1
        assert matches == 1
        return
    if "$ref" in schema:
        schema = root["$defs"][schema["$ref"].rsplit("/", 1)[1]]
    if "const" in schema:
        assert value == schema["const"]
    if "enum" in schema:
        assert value in schema["enum"]
    kind = schema.get("type")
    if isinstance(kind, list):
        if value is None and "null" in kind:
            return
        kind = next(k for k in kind if k != "null")
    if kind == "object":
        assert isinstance(value, dict)
        assert set(schema.get("required", [])) <= set(value)
        assert set(value) <= set(schema["properties"])
        for key, item in value.items():
            validate_schema(item, schema["properties"][key], root)
    elif kind == "array":
        assert isinstance(value, list) and len(value) <= schema["maxItems"]
        for item in value:
            validate_schema(item, schema["items"], root)
    elif kind == "string":
        assert isinstance(value, str) and len(value) <= schema.get("maxLength", 256)
    elif kind == "boolean":
        assert type(value) is bool
    elif kind == "integer":
        assert type(value) is int
    elif kind == "number":
        assert type(value) in (int, float) and value >= 0
    if kind in ("integer", "number"):
        if "minimum" in schema:
            assert value >= schema["minimum"]
        if "maximum" in schema:
            assert value <= schema["maximum"]


def test_artifact_schema_and_no_raw_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(probe, "WORK", tmp_path)
    monkeypatch.setattr(probe, "RESULT", tmp_path / "kaggle_runtime_result.json")
    result = probe.fresh_result()
    result["assertions"] = [
        dict(probe.validate_chat(response(), "ready"), total_seconds=1.0)
    ]
    probe.phase(result, "synthetic", "SYNTHETIC_READY")
    schema = json.loads((probe.SOURCE / "result.schema.json").read_text())
    validate_schema(json.loads(probe.RESULT.read_text()), schema, schema)
    assert '"content":' not in probe.RESULT.read_text()
    assert "traceback" not in probe.RESULT.read_text()
    with pytest.raises(ValueError):
        probe.phase(result, "test", "raw private exception")


def test_notebook_is_thin_and_unexecuted() -> None:
    notebook = json.loads((probe.SOURCE / "kaggle_runtime.ipynb").read_text())
    code = [cell for cell in notebook["cells"] if cell["cell_type"] == "code"]
    assert len(code) == 4
    for cell in code:
        assert cell["outputs"] == [] and cell["execution_count"] is None
        ast.parse("".join(cell["source"]))
    text = "\n".join("".join(c["source"]) for c in code)
    for mode in ("inspect", "bootstrap", "run"):
        assert f'"{mode}"' in text
    assert "runtime_probe.py" in text
    assert "--confirm-free-session" in text
    assert "vllm" not in text and "torch" not in text


def test_experiment_has_no_product_imports_or_exposure() -> None:
    source = (probe.SOURCE / "runtime_probe.py").read_text()
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            assert not (node.module or "").startswith(
                ("legoai", "forgeai", "examples", "packages")
            )
    for forbidden in (
        "ngrok",
        "cloudflared",
        "localtunnel",
        "0.0.0.0",
        "router.huggingface.co",
        "api.openai.com",
        "getenv",
    ):
        assert forbidden not in source
    parents = {
        child: parent
        for parent in ast.walk(tree)
        for child in ast.iter_child_nodes(parent)
    }
    environment_reads = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Attribute)
        and isinstance(node.value, ast.Name)
        and node.value.id == "os"
        and node.attr == "environ"
    ]
    assert len(environment_reads) == 1
    environment = environment_reads[0]
    access = parents[environment]
    call = parents[access]
    assert isinstance(call, ast.Call)
    assert ast.unparse(call) == "os.environ.get('LD_LIBRARY_PATH')"
    clean = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "clean_environment"
    )
    assert environment in set(ast.walk(clean))
    assert len(probe.REVISION) == 40
    assert all(".." not in name and "/" not in name for name in probe.FILES)
    assert (probe.SOURCE / "requirements-kaggle.txt").is_file()
