"""CONTENT-DISCOVERY-1Q-R2 operator entry point (run from examples/forgeai).

    uv run python evaluation/run_analyst_quality_1q_r2.py replay --output aq1q-r2-replay
    uv run python evaluation/run_analyst_quality_1q_r2.py live --model <name> \\
        --model-digest <sha256:...> --hardware "<class>" \\
        --expect-branch <branch> --expect-commit <sha> --output <new directory>
"""

import sys

from analyst_quality1q_r2.cli import main

if __name__ == "__main__":
    sys.exit(main())
