"""CONTENT-DISCOVERY-1Q-R3 operator entry point (run from examples/forgeai).

    uv run python evaluation/run_analyst_quality_1q_r3.py replay --output aq1q-r3-replay
    uv run python evaluation/run_analyst_quality_1q_r3.py live --model <name> \\
        --model-digest <sha256:...> --hardware "<real hardware description>" \\
        --expect-branch <branch> --expect-commit <sha> --output <new directory>
"""

import sys

from analyst_quality1q_r3.cli import main

if __name__ == "__main__":
    sys.exit(main())
