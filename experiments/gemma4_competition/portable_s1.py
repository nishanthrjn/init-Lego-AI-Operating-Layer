"""S1 configuration of the shared P3 adapter and M2 compiler/package engine."""
from pathlib import Path
import sys

AREA = Path(__file__).resolve().parent
# File-based loading also works inside the isolated Kaggle transfer bundle.
import importlib.util
spec = importlib.util.spec_from_file_location("_s1_adapter", AREA / "portable_p3.py")
adapter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adapter)
load_instance = adapter.load_instance
BUDGETS = dict(adapter.BUDGETS)
PROMPT_SHA256 = "020704784e5e0b95fb73095fea14fd7d8670cbe18e164f6d4a52cf1adcbaa7d9"
MEMBER_PINS = dict(adapter.MEMBER_PINS, **{"prompts/system.md": PROMPT_SHA256,
    "agent.yaml": "b060349f8d6780ed21f2efbe40ac4b09dba0ecc352ac164dc6b395f7eea9c544"})
EXPERIMENTAL_ZIP_SHA256 = "6f38e73cbd441b9c55a5c04e25d2350fdf1deb3fccbd8b1631fcbee7af4ca36a"
EXPERIMENTAL_ZIP_SIZE = 6501
ENGINE = adapter.build_engine("s1", MEMBER_PINS, EXPERIMENTAL_ZIP_SHA256,
                              __file__, EXPERIMENTAL_ZIP_SIZE)


MODEL = "gemma-4-e4b-it-qat-w4a16-ct"
ENGINE.MODEL = MODEL  # Configure only this isolated compiler engine; preserve other candidates.

_original_transfer = ENGINE.transfer_paths
_original_verify = ENGINE.verify_local_receipt


def transfer_paths():
    prefix = 'experiments/gemma4_competition/'
    return sorted(set(_original_transfer()) | {
        prefix + 'qualification_pair.py',
        prefix + 'submission_only/qualify_p3.py',
        prefix + 'results/submissions.json',
        prefix + 'results/dev-16v-comparison.json',
        prefix + 'submission_only/qualify_s1.py',
        prefix + 'submission_only/generate_self_contained.py',
        prefix + 'submission_only/embedded_payload.py',
        prefix + 'local_eval/source-pins.json',
    })


def verify_local_receipt(path):
    receipt = _original_verify(path)
    guard = load_instance(AREA / 'submission_only/qualify_s1.py', '_s1_receipt_authority')
    guard.require_qualification_gate()
    return receipt


ENGINE.transfer_paths = transfer_paths
ENGINE.verify_local_receipt = verify_local_receipt

def __getattr__(name):
    return getattr(ENGINE, name)


if __name__ == "__main__":
    try:
        raise SystemExit(ENGINE.main())
    except Exception as error:
        print("FAIL: S1 portable compiler: " + type(error).__name__, file=sys.stderr)
        raise SystemExit(1) from None
