"""P1 configuration of the unchanged M2 compiler, install and package functions."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

AREA = Path(__file__).resolve().parent
PROMPT_SHA256 = "8f8e4108b1ce5796ffe50ecd1cb9419c6214879a088466874664e6d8d19b0e7b"
BUDGETS = {"timeout_seconds": 180, "max_tool_calls": 28, "max_time_minutes": 6, "max_turns": 80}
EVALUATION = """evaluation:
  timeout_seconds: 180
  max_tool_calls: 28
  max_time_minutes: 6
  max_turns: 80
"""
B2_EVALUATION = """evaluation:
  timeout_seconds: 90
  max_tool_calls: 40
  max_time_minutes: 4
  max_turns: 100
"""


def load_instance(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ValueError("implementation source unavailable: " + str(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def build_engine():
    engine = load_instance(AREA / "portable_m2.py", "_p1_shared_engine")
    original_expected = engine.expected_files()
    original_static = engine.static_candidate
    original_transfer = engine.transfer_paths
    original_verify = engine.verify_local_receipt
    engine.CANDIDATE = AREA / "candidates/p1"
    engine.EVALUATION = EVALUATION
    engine.INSTALL_AUTHORIZATION = "AUTHORIZE FORGEAI GEMMA4 P1 KAGGLE CPU SCOPED INSTALL AND COMPILER ONLY"
    engine.__file__ = str(Path(__file__).resolve())

    def expected_files():
        prompt = (engine.CANDIDATE / "prompts/system.md").read_bytes()
        engine.require(engine.sha(prompt) == PROMPT_SHA256, "P1 prompt SHA256 changed")
        return {**original_expected, "prompts/system.md": prompt, "eval_config.yaml": EVALUATION.encode()}

    def static_candidate(directory):
        data = original_static(directory)
        for name in engine.MEMBERS:
            baseline = (AREA / "baseline" / name).read_bytes()
            engine.require(baseline == original_expected[name], "M2 candidate changed: " + name)
            prior = (AREA / "candidates/b2" / name).read_bytes()
            expected = B2_EVALUATION.encode() if name == "eval_config.yaml" else baseline
            engine.require(prior == expected, "B2 candidate changed: " + name)
            if name not in {"prompts/system.md", "eval_config.yaml"}:
                engine.require(data[name] == prior, "P1 changed model/tools/sampling: " + name)
            else:
                engine.require(data[name] != prior, "P1 must differ from B2: " + name)
        return data

    def transfer_paths():
        prefix = "experiments/gemma4_competition/"
        return sorted((set(original_transfer()) - {prefix + "kaggle_compiler/compiler_only.ipynb"}) | {
            "validate_forgeai_gemma4_p1_procedure_prompt_1.py",
            prefix + "portable_p1.py", prefix + "tests/test_p1_candidate.py",
            prefix + "kaggle_compiler/p1_compiler_only.ipynb",
            *(prefix + "candidates/" + candidate + "/" + name
              for candidate in ("b2", "p1") for name in engine.MEMBERS),
        })

    def verify_local_receipt(path):
        receipt = original_verify(path)
        engine.require(receipt.get("candidate") == "p1" and receipt.get("budgets") == BUDGETS
                       and receipt.get("prompt_sha256") == PROMPT_SHA256, "P1 receipt identity mismatch")
        return receipt

    engine.expected_files = expected_files
    engine.static_candidate = static_candidate
    engine.transfer_paths = transfer_paths
    engine.verify_local_receipt = verify_local_receipt
    return engine


ENGINE = build_engine()


def __getattr__(name):
    return getattr(ENGINE, name)


if __name__ == "__main__":
    try:
        raise SystemExit(ENGINE.main())
    except Exception as error:
        print("FAIL: P1 portable compiler: " + type(error).__name__ + "; later phases NOT RUN", file=sys.stderr)
        raise SystemExit(1) from None
