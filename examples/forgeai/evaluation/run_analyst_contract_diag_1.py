"""ANALYST-CONTRACT-DIAG-1 operator entry point (run from examples/forgeai).

    uv run python evaluation/run_analyst_contract_diag_1.py live --model <name> \\
        --model-digest <sha256:...> --hardware "<class>" \\
        --expect-branch <branch> --expect-commit <sha> --output <new directory>
"""

import sys

from analyst_contract_diag1.cli import main

if __name__ == "__main__":
    sys.exit(main())
