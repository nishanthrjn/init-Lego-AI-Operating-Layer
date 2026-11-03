"""P7A configuration of the shared P3 adapter and M2 compiler/package engine."""
from pathlib import Path
import sys

AREA = Path(__file__).resolve().parent
# File-based loading also works inside the isolated Kaggle transfer bundle.
import importlib.util
spec = importlib.util.spec_from_file_location("_p7a_adapter", AREA / "portable_p3.py")
adapter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adapter)
load_instance = adapter.load_instance
BUDGETS = dict(adapter.BUDGETS)
PROMPT_SHA256 = "622ef9503338228212386f7ef967844c601d1ce06c35d6dccf3c36ba1c43fa31"
MEMBER_PINS = dict(adapter.MEMBER_PINS, **{"prompts/system.md": PROMPT_SHA256})
EXPERIMENTAL_ZIP_SHA256 = "68f685853161c0a3c0653e6c2a42655f53fc03b9f3ed8702b80c681390ef0c34"
EXPERIMENTAL_ZIP_SIZE = 7359
ENGINE = adapter.build_engine("p7a", MEMBER_PINS, EXPERIMENTAL_ZIP_SHA256,
                              __file__, EXPERIMENTAL_ZIP_SIZE)


def __getattr__(name):
    return getattr(ENGINE, name)


if __name__ == "__main__":
    try:
        raise SystemExit(ENGINE.main())
    except Exception as error:
        print("FAIL: P7A portable compiler: " + type(error).__name__, file=sys.stderr)
        raise SystemExit(1) from None
