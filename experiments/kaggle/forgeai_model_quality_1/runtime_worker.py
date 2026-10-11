"""Private child: fixed local snapshot, one model, no download or HTTP client."""

from __future__ import annotations

import hashlib
import importlib
import importlib.metadata
import json
import os
import platform
import sys
from pathlib import Path
from typing import Any

from .contracts import (
    CALL_LIMIT,
    INPUT_BYTES,
    INPUT_TOKENS,
    MODEL,
    OUTPUT_BYTES,
    OUTPUT_TOKENS,
    REVISION,
    RUNTIME_FAILURE_CODES,
    Rejected,
)

MODEL_DIRECTORY = Path("/tmp/legoai-kaggle-runtime-1/model")
INVENTORY = Path("/kaggle/working/reviewed_model_inventory.json")
RUNTIME = {
    "python": "3.12.3",
    "torch": "2.7.0+cu128",
    "transformers": "4.51.3",
    "vllm": "0.9.2",
    "pytest": "9.1.1",
    "mypy": "2.3.1",
    "ruff": "0.16.8",
}
WEIGHT_FILES = (
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


def runtime_identity() -> dict[str, Any]:
    if platform.system() != "Linux" or platform.python_version() != RUNTIME["python"]:
        raise Rejected("RUNTIME_IDENTITY_MISMATCH")
    for name, version in RUNTIME.items():
        if name != "python" and importlib.metadata.version(name) != version:
            raise Rejected("RUNTIME_IDENTITY_MISMATCH")
    torch = importlib.import_module("torch")
    if not torch.cuda.is_available() or torch.cuda.device_count() != 2:
        raise Rejected("RUNTIME_IDENTITY_MISMATCH")
    if any(torch.cuda.get_device_name(index) != "Tesla T4" for index in range(2)):
        raise Rejected("RUNTIME_IDENTITY_MISMATCH")
    if INVENTORY.is_symlink() or INVENTORY.stat().st_size > 4096:
        raise Rejected("MODEL_IDENTITY_MISMATCH")
    inventory = json.loads(INVENTORY.read_text(encoding="utf-8"))
    if set(inventory) != {"model_id", "model_revision", "files"}:
        raise Rejected("MODEL_IDENTITY_MISMATCH")
    if (
        inventory["model_id"] != MODEL
        or inventory["model_revision"] != REVISION
        or MODEL_DIRECTORY.is_symlink()
    ):
        raise Rejected("MODEL_IDENTITY_MISMATCH")
    if set(inventory["files"]) != set(WEIGHT_FILES):
        raise Rejected("MODEL_IDENTITY_MISMATCH")
    hashes: dict[str, str] = {}
    total = 0
    for name in WEIGHT_FILES:
        path = MODEL_DIRECTORY / name
        maximum = 5 * 2**30 if name.endswith(".safetensors") else 16 * 2**20
        if path.is_symlink() or not path.is_file() or path.stat().st_size > maximum:
            raise Rejected("MODEL_IDENTITY_MISMATCH")
        total += path.stat().st_size
        if total > 12 * 2**30:
            raise Rejected("MODEL_IDENTITY_MISMATCH")
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            while block := stream.read(1024 * 1024):
                digest.update(block)
        hashes[name] = digest.hexdigest()
        if hashes[name] != inventory["files"][name]:
            raise Rejected("MODEL_IDENTITY_MISMATCH")
    return {
        **RUNTIME,
        "gpu": ["Tesla T4", "Tesla T4"],
        "tensor_parallel_size": 2,
        "quantization": "awq-4bit",
        "max_model_len": 4096,
        "model_inventory_digest": hashlib.sha256(
            json.dumps(hashes, sort_keys=True).encode()
        ).hexdigest(),
        "transport": "in-process-vllm",
    }


def main() -> int:
    # Redirect native/library logs before importing GPU libraries. Keep only a
    # private bounded JSON line channel; stdout/stderr never reach the artifact.
    protocol = os.fdopen(os.dup(sys.stdout.fileno()), "w", encoding="utf-8")
    with open(os.devnull, "w", encoding="utf-8") as sink:
        os.dup2(sink.fileno(), 1)
        os.dup2(sink.fileno(), 2)
    try:
        observed = runtime_identity()
        vllm = importlib.import_module("vllm")
        engine = vllm.LLM(
            model=str(MODEL_DIRECTORY),
            tokenizer=str(MODEL_DIRECTORY),
            trust_remote_code=False,
            hf_token=False,
            dtype="half",
            quantization="awq",
            tensor_parallel_size=2,
            distributed_executor_backend="mp",
            max_model_len=4096,
            max_num_seqs=1,
            gpu_memory_utilization=0.80,
            swap_space=0,
            cpu_offload_gb=0,
            seed=0,
            enforce_eager=True,
            disable_custom_all_reduce=True,
            disable_log_stats=True,
            generation_config="vllm",
        )
        tokenizer = engine.get_tokenizer()
        protocol.write(json.dumps({"ready": observed}) + "\n")
        protocol.flush()
        for _ in range(CALL_LIMIT):
            line = sys.stdin.buffer.readline(INPUT_BYTES * 8 + 1)
            if not line:
                return 0
            if len(line) > INPUT_BYTES * 8 or not line.endswith(b"\n"):
                raise Rejected("INPUT_LIMIT")
            request = json.loads(line)
            if not isinstance(request, dict) or set(request) != {"prompt"}:
                raise Rejected("INPUT_LIMIT")
            prompt = request["prompt"]
            if not isinstance(prompt, str) or len(prompt.encode()) > INPUT_BYTES:
                raise Rejected("INPUT_LIMIT")
            token_ids = tokenizer.apply_chat_template(
                [{"role": "user", "content": prompt}],
                tokenize=True,
                add_generation_prompt=True,
            )
            if len(token_ids) > INPUT_TOKENS:
                raise Rejected("INPUT_LIMIT")
            sampling = vllm.SamplingParams(
                temperature=0,
                seed=0,
                max_tokens=OUTPUT_TOKENS,
                n=1,
            )
            outputs = engine.generate(
                [{"prompt_token_ids": token_ids}],
                sampling_params=sampling,
                use_tqdm=False,
            )
            if len(outputs) != 1 or len(outputs[0].outputs) != 1:
                raise Rejected("GENERATION_INVALID")
            output = outputs[0].outputs[0]
            if len(output.text.encode()) > OUTPUT_BYTES:
                raise Rejected("OUTPUT_LIMIT")
            if output.finish_reason != "stop":
                raise Rejected("OUTPUT_LIMIT")
            protocol.write(json.dumps({"text": output.text}) + "\n")
            protocol.flush()
        return 0
    except Exception as exc:
        reason = (
            str(exc)
            if isinstance(exc, Rejected) and str(exc) in RUNTIME_FAILURE_CODES
            else "RUNTIME_FAILURE"
        )
        protocol.write(json.dumps({"error": reason}) + "\n")
        protocol.flush()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
