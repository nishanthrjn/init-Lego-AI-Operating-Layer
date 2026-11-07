"""P10 configuration of the shared P3 adapter and M2 compiler/package engine."""
from pathlib import Path
import sys

AREA = Path(__file__).resolve().parent
# File-based loading also works inside the isolated Kaggle transfer bundle.
import importlib.util
spec = importlib.util.spec_from_file_location("_p10_adapter", AREA / "portable_p3.py")
adapter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adapter)
load_instance = adapter.load_instance
BUDGETS = dict(adapter.BUDGETS, max_time_minutes=8)
PROMPT_SHA256 = "020704784e5e0b95fb73095fea14fd7d8670cbe18e164f6d4a52cf1adcbaa7d9"
MEMBER_PINS = dict(adapter.MEMBER_PINS, **{"prompts/system.md": PROMPT_SHA256, "eval_config.yaml": "1643c1f28a19f6389943f909c7ad34f2534951073bde5f2923a40f398e378b13"})
EXPERIMENTAL_ZIP_SHA256 = "89a84bf709b52858b3a3ce39f33d713501dec1fe00e0fb04164f271158f333d6"
EXPERIMENTAL_ZIP_SIZE = 6501
ENGINE = adapter.build_engine("p10", MEMBER_PINS, EXPERIMENTAL_ZIP_SHA256,
                              __file__, EXPERIMENTAL_ZIP_SIZE, budgets=BUDGETS)


_original_transfer = ENGINE.transfer_paths
_original_verify = ENGINE.verify_local_receipt


def transfer_paths():
    prefix = 'experiments/gemma4_competition/'
    return sorted(set(_original_transfer()) | {
        prefix + 'qualification_pair.py',
        prefix + 'submission_only/qualify_p3.py',
        prefix + 'results/submissions.json',
        prefix + 'results/dev-16v-comparison.json',
        prefix + 'submission_only/qualify_p10.py',
        prefix + 'submission_only/generate_self_contained.py',
        prefix + 'submission_only/embedded_payload.py',
        prefix + 'local_eval/source-pins.json',
    })


def verify_local_receipt(path):
    receipt = _original_verify(path)
    guard = load_instance(AREA / 'submission_only/qualify_p10.py', '_p10_receipt_authority')
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
        print("FAIL: P10 portable compiler: " + type(error).__name__, file=sys.stderr)
        raise SystemExit(1) from None
