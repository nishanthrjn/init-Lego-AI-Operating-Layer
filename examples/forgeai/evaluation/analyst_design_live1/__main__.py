"""Explicit operator command; importing the harness never invokes a provider."""

import argparse
from pathlib import Path

from analyst_design_live1.harness import run


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("PREFLIGHT", "SMOKE", "FULL"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--approval-reference", required=True)
    parser.add_argument("--smoke-report", type=Path)
    args = parser.parse_args()
    report = run(
        args.mode, args.output, args.approval_reference, smoke_report=args.smoke_report
    )
    print(report.get("smoke_status") or report["sufficiency_profile_outcome"])


if __name__ == "__main__":
    main()
