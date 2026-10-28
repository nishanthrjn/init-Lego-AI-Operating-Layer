"""Separately frozen synthetic evaluation; eligibility is not admission."""

import sys
from pathlib import Path

# This operator tool runs from the root environment, which does not install the
# engineering package. Use the same repository sources pinned by frozen.py.
# Package initialization precedes pack imports for every v2 -m entry point.
ENGINEERING_SRC = (
    Path(__file__).resolve().parents[2] / "packages" / "legoai-engineering" / "src"
)
if str(ENGINEERING_SRC) not in sys.path:
    sys.path.insert(0, str(ENGINEERING_SRC))
