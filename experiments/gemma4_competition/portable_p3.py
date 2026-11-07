"""P3 configuration of the existing M2 compiler, install and packaging engine."""
import importlib.util
from pathlib import Path
import sys

AREA = Path(__file__).resolve().parent
BUDGETS = {"timeout_seconds": 180, "max_tool_calls": 28, "max_time_minutes": 6, "max_turns": 80}
PROMPT_SHA256 = "65ee3fd052e92b455e7bb29908fd75a45116d84c94b47b11ecc9950d43aec45d"
MEMBER_PINS = {
    "agent.yaml": "83a97b8a3e9a8d71efa692423ace1d0187ba65ca84655c94679b03b3eab4c3c6",
    "eval_config.yaml": "2c8a983a1926aadfeca826bc90936ebc00329f6440e44a41369d01eed909d1a8",
    "configs/sampling.yaml": "571a934e89911734927533f1d36cbcc7b8d493592febe63b217e911cf7ed4926",
    "prompts/system.md": PROMPT_SHA256,
}
EXPERIMENTAL_ZIP_SHA256 = "19b4e77257004e5440e23520f05e83ab755257fd6ff43c71d38539b9d62c676f"


def load_instance(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ValueError("source unavailable: " + str(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def build_engine(candidate="p3", member_pins=MEMBER_PINS, zip_sha256=EXPERIMENTAL_ZIP_SHA256, entry=None, zip_size=None, budgets=None):
    receipt_budgets = dict(BUDGETS if budgets is None else budgets)
    engine = load_instance(AREA / "portable_m2.py", "_" + candidate + "_shared_engine")
    original_static = engine.static_candidate
    original_transfer = engine.transfer_paths
    original_verify = engine.verify_local_receipt
    engine.CANDIDATE = AREA / "candidates" / candidate
    engine.EXPECTED_OUTPUT_TOKENS = 8192
    engine.INSTALL_AUTHORIZATION = "AUTHORIZE FORGEAI GEMMA4 " + candidate.upper() + " KAGGLE CPU SCOPED INSTALL AND COMPILER ONLY"
    engine.__file__ = str(Path(entry or __file__).resolve())

    def expected_files():
        files = {n: (engine.CANDIDATE / n).read_bytes() for n in engine.MEMBERS}
        engine.require({n: engine.sha(v) for n, v in files.items()} == member_pins,
                       candidate.upper() + " differs from frozen experimental package members")
        return files

    def static_candidate(directory):
        files = original_static(directory)
        blob = engine.zip_bytes(files)
        engine.require(engine.sha(blob) == zip_sha256 and (zip_size is None or len(blob) == zip_size),
                       candidate.upper() + " deterministic ZIP differs from retained experimental run")
        return files

    def transfer_paths():
        prefix = "experiments/gemma4_competition/"
        return sorted((set(original_transfer()) - {prefix + "kaggle_compiler/compiler_only.ipynb"}) | {
            "validate_forgeai_gemma4_p3_submission_qualification_1.py",
            f"validate_forgeai_gemma4_{candidate}_submission_qualification_1.py",
            "validate_forgeai_gemma4_p1_procedure_prompt_1.py",
            prefix + "portable_p1.py", prefix + "portable_p3.py", prefix + f"portable_{candidate}.py",
            prefix + "tests/test_p3_qualification.py", prefix + f"tests/test_{candidate}_qualification.py",
            prefix + "local_eval/paper_evidence.py", prefix + "local_eval/analysis.py",
            prefix + "local_eval/compare_runs.py",
            prefix + f"kaggle_compiler/{candidate}_compiler_only.ipynb",
            *(prefix + f"candidates/{candidate}/" + n for n in engine.MEMBERS),
        })

    def verify_local_receipt(path):
        receipt = original_verify(path)
        engine.require(receipt.get("candidate") == candidate and receipt.get("budgets") == receipt_budgets
                       and receipt.get("experimental_zip_sha256") == zip_sha256,
                       candidate.upper() + " receipt identity mismatch")
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
        print("FAIL: P3 portable compiler: " + type(error).__name__, file=sys.stderr)
        raise SystemExit(1) from None
