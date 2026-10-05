"""ANALYST-MODEL-COMPARE-1 operator entry point (run from examples/forgeai).

    uv run python evaluation/run_analyst_model_compare_1.py smoke --model <name> \\
        --model-digest <pinned sha256:...> --hardware "<real hardware description>" \\
        --expect-branch <branch> --expect-commit <sha> --output <new directory>
    uv run python evaluation/run_analyst_model_compare_1.py live ... (same flags)
    uv run python evaluation/run_analyst_model_compare_1.py compare \\
        --control <R3 report.json> --candidate <report.json> [--smoke <smoke.json>] \\
        --output <new directory>
"""

import sys

from analyst_model_compare1.cli import main

if __name__ == "__main__":
    sys.exit(main())
