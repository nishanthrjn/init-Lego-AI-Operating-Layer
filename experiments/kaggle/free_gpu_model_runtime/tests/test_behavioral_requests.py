"""1G request authority and prompt presentation regression contracts."""

from __future__ import annotations

import hashlib
import json
import platform
import shutil
import sys
from pathlib import Path

import pytest

from experiments.kaggle.free_gpu_model_runtime import notebook_support as notebook
from experiments.kaggle.free_gpu_model_runtime import runtime_probe as probe


@pytest.mark.parametrize("identity", ["ready", "json", "add"])
def test_fixed_case_payload(identity: str) -> None:
    case = next(case for case in probe.prompts() if case["id"] == identity)
    expected = {
        "model": probe.MODEL,
        "messages": [{"role": "user", "content": case["prompt"]}],
        "temperature": 0,
        "seed": 0,
        "max_tokens": 96,
        "n": 1,
        "stream": False,
    }
    if identity == "json":
        expected["response_format"] = {"type": "json_object"}
    assert probe.build_synthetic_request(case) == expected
    assert probe.build_synthetic_request(case) == probe.build_synthetic_request(case)


@pytest.mark.parametrize("mutation", ["unknown", "prompt", "extra"])
def test_no_arbitrary_request_customization(mutation: str) -> None:
    case = dict(probe.prompts()[1])
    if mutation == "unknown":
        case["id"] = "other"
    elif mutation == "prompt":
        case["prompt"] = "operator content"
    else:
        case["response_format"] = "arbitrary"
    with pytest.raises(probe.Stop):
        probe.build_synthetic_request(case)


def test_presentation_instructions_and_fixture_digest() -> None:
    ready, json_case, add = probe.prompts()
    assert ready["prompt"] == "Return exactly the word READY."
    assert 'only this exact JSON object: {"status":"ready"}' in json_case["prompt"]
    assert "Do not use Markdown or code fences" in json_case["prompt"]
    assert "exactly one function" in add["prompt"]
    assert "def add(a: int, b: int) -> int:\n    return a + b" in add["prompt"]
    assert all(
        len(case["prompt"]) <= probe.MAX_INPUT_CHARS for case in (ready, json_case, add)
    )
    raw = (
        (probe.SOURCE / "fixtures/synthetic_prompts.json")
        .read_bytes()
        .replace(b"\r\n", b"\n")
    )
    assert hashlib.sha256(raw).hexdigest() == probe.PROMPT_DIGEST


@pytest.mark.parametrize(
    "content",
    [
        '{"status":"READY"}',
        '{"status":"ready","extra":true}',
        '["ready"]',
        "status=ready",
        'Here is the JSON: {"status":"ready"}',
        '{"status":"ready","status":"ready"}',
        '```json\n{"status":"ready"}\n```',
    ],
)
def test_invalid_json_is_never_repaired(content: str) -> None:
    assert probe.output_matches("json", content) is False


@pytest.mark.parametrize(
    "content",
    [
        "```python\ndef add(a: int, b: int) -> int: return a + b\n```",
        "@decorator\ndef add(a: int, b: int) -> int: return a + b",
        "def add(a: int, b: int = 0) -> int: return a + b",
        "def add(a: int, b: int, *args) -> int: return a + b",
        "def add(a: int, b: int, **kwargs) -> int: return a + b",
        "def add(a: int, b: int) -> int: return a + b\ndef extra(): pass",
    ],
)
def test_add_remains_exact_ast(content: str) -> None:
    assert probe.output_matches("add", content) is False


def test_old_identity_cannot_qualify_as_1g(tmp_path: Path) -> None:
    source = tmp_path / "source"
    shutil.copytree(probe.SOURCE, source)
    manifest = source / "source-manifest.json"
    data = json.loads(manifest.read_text(encoding="utf-8"))
    data["experiment"] = "FREE-GPU-MODEL-RUNTIME-KAGGLE-1F"
    raw = json.dumps(data).encode()
    manifest.write_bytes(raw)
    with pytest.raises(RuntimeError, match="SOURCE_NOT_UNIQUE"):
        notebook.discover_source(tmp_path, hashlib.sha256(raw).hexdigest())


@pytest.mark.parametrize(
    ("mode", "outcome"),
    [("bootstrap", "KAGGLE_GPU_READY"), ("run", "MODEL_DOWNLOADED")],
)
def test_old_evidence_cannot_be_consumed(
    mode: str, outcome: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(probe, "WORK", tmp_path)
    monkeypatch.setattr(probe, "RESULT", tmp_path / "result.json")
    monkeypatch.setattr(platform, "system", lambda: "Linux")
    monkeypatch.setattr(platform, "machine", lambda: "x86_64")
    monkeypatch.setattr(Path, "is_dir", lambda path: True)
    monkeypatch.setattr(sys, "argv", ["probe", mode, "--confirm-free-session"])
    raw = json.dumps(
        {"experiment": "FREE-GPU-MODEL-RUNTIME-KAGGLE-1F", "outcome": outcome}
    ).encode()
    probe.RESULT.write_bytes(raw)
    assert probe.main() == 1
    assert probe.RESULT.read_bytes() == raw
