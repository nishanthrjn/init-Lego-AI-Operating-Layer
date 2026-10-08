"""Explicit operator command; importing the harness never invokes a provider.

PREFLIGHT makes zero semantic calls but contacts the local provider for
metadata; DEVELOPMENT makes up to 22 calls. Both need a separate maintainer
authorization and an explicit approval reference; there is no default mode.
"""

import argparse
from pathlib import Path

from analyst_sufficiency_h2_development_live1.harness import run


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("PREFLIGHT", "DEVELOPMENT"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--approval-reference", required=True)
    args = parser.parse_args()
    report = run(args.mode, args.output, args.approval_reference)
    print(report["development_decision"]["label"] or report["stop_reason"] or "OK")


if __name__ == "__main__":
    main()
