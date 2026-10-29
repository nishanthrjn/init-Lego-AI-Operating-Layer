"""P5 configuration of the shared P3 adapter and M2 compiler/package engine."""
from pathlib import Path
import sys

AREA = Path(__file__).resolve().parent
# File-based loading also works inside the isolated Kaggle transfer bundle.
import importlib.util
spec = importlib.util.spec_from_file_location("_p5_adapter", AREA / "portable_p3.py")
adapter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adapter)
load_instance = adapter.load_instance
BUDGETS = dict(adapter.BUDGETS)
PROMPT_SHA256 = "020704784e5e0b95fb73095fea14fd7d8670cbe18e164f6d4a52cf1adcbaa7d9"
MEMBER_PINS = dict(adapter.MEMBER_PINS, **{"prompts/system.md": PROMPT_SHA256})
EXPERIMENTAL_ZIP_SHA256 = "6db4109a73cfea1c803c17e86f498406461141904dac58efe441f10cca1fe219"
EXPERIMENTAL_ZIP_SIZE = 6501
ENGINE = adapter.build_engine("p5", MEMBER_PINS, EXPERIMENTAL_ZIP_SHA256,
                              __file__, EXPERIMENTAL_ZIP_SIZE)


def __getattr__(name):
    return getattr(ENGINE, name)


if __name__ == "__main__":
    try:
        raise SystemExit(ENGINE.main())
    except Exception as error:
        print("FAIL: P5 portable compiler: " + type(error).__name__, file=sys.stderr)
        raise SystemExit(1) from None
