"""B2 composition over the unchanged, receipt-bound M2 implementation.

This module owns an isolated module instance, never mutates an imported M2
singleton, and delegates all compiler/install/package algorithms unchanged.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

AREA = Path(__file__).resolve().parent
BUDGETS = {"timeout_seconds": 90, "max_tool_calls": 40, "max_time_minutes": 4, "max_turns": 100}
EVALUATION = """evaluation:
  timeout_seconds: 90
  max_tool_calls: 40
  max_time_minutes: 4
  max_turns: 100
"""


def load_instance(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ValueError("implementation source unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def build_engine():
    engine = load_instance(AREA / "portable_m2.py", "_b2_shared_engine")
    original_transfer = engine.transfer_paths
    original_expected = engine.expected_files
    original_static = engine.static_candidate
    original_verify = engine.verify_local_receipt
    baseline_expected = original_expected()
    engine.CANDIDATE = AREA / "candidates/b2"
    engine.EVALUATION = EVALUATION
    engine.INSTALL_AUTHORIZATION = "AUTHORIZE FORGEAI GEMMA4 B2 KAGGLE CPU SCOPED INSTALL AND COMPILER ONLY"
    # run_portable launches __file__ for its worker: dispatch through this same
    # composition in the child, so it cannot silently compile baseline instead.
    engine.__file__ = str(Path(__file__).resolve())

    def expected_files():
        return {**baseline_expected, "eval_config.yaml": EVALUATION.encode()}

    def static_candidate(directory):
        data = original_static(directory)
        for name in engine.MEMBERS:
            baseline = (AREA / "baseline" / name).read_bytes()
            engine.require(baseline == baseline_expected[name], "M2 baseline bytes changed")
            if name != "eval_config.yaml":
                engine.require(data[name] == baseline, "B2 changed a non-budget file")
        return data

    def transfer_paths():
        prefix = "experiments/gemma4_competition/"
        return sorted(set(original_transfer()) | {
            "validate_forgeai_gemma4_b2_candidate_1.py",
            prefix + "portable_b2.py",
            prefix + "kaggle_compiler/b2_compiler_only.ipynb",
            prefix + "tests/test_b2_candidate.py",
            *(prefix + "candidates/b2/" + name for name in engine.MEMBERS),
        })

    def verify_local_receipt(path):
        receipt = original_verify(path)
        engine.require(receipt.get("candidate") == "b2" and receipt.get("budgets") == BUDGETS,
                       "B2 receipt identity mismatch")
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
        print("FAIL: " + type(error).__name__ + "; later phases NOT RUN", file=sys.stderr)
        raise SystemExit(1) from None
