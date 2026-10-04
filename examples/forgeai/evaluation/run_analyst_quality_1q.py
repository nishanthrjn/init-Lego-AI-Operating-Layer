"""CONTENT-DISCOVERY-1Q operator entry point (run from examples/forgeai).

    uv run python evaluation/run_analyst_quality_1q.py replay --output aq1q-replay
    uv run python evaluation/run_analyst_quality_1q.py live --model <name> \\
        --model-digest <sha256:...> --hardware "<class>" \\
        --expect-branch <branch> --expect-commit <sha> --output <new directory>
"""

import sys

from analyst_quality1q.cli import main

if __name__ == "__main__":
    sys.exit(main())
