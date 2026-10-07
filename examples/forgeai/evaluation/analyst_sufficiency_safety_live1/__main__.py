"""Explicit operator command; importing the harness never invokes a provider."""

import argparse
from pathlib import Path

from analyst_sufficiency_safety_live1.harness import run


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("PREFLIGHT", "BASELINE"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--approval-reference", required=True)
    args = parser.parse_args()
    report = run(args.mode, args.output, args.approval_reference)
    print(report["decision"]["code"] or report["stop_reason"] or report["mode"])


if __name__ == "__main__":
    main()
