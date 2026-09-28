# ruff: noqa: E402
"""Read-only provider probe: reachability, API family, capabilities.

Never submits a workflow, mutates provider state or prints credentials.
"""

import argparse
import asyncio
import sys
from pathlib import Path

# Repository example bootstrap only; wheel consumers import the installed package.
ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [
    str(ROOT / "packages" / "legoai-generative-media" / "src"),
    str(ROOT / "src"),
]

from legoai_generative_media.config import load_config
from legoai_generative_media.service import ProviderError, probe_provider


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, type=Path)
    args = parser.parse_args()
    try:
        config = load_config(args.config)
    except ValueError as error:
        parser.error(str(error))
    print("mode: read-only probe")
    print("origin:", config.provider.origin, "deployment:", config.provider.deployment)
    print("configured api_family:", config.provider.api_family)
    try:
        profile = asyncio.run(probe_provider(config))
    except ProviderError as error:
        print("submission performed: NO")
        print("provider:", error.reason, "category:", error.category.value)
        for line in error.evidence:
            print("evidence", line)
        return 1
    except ValueError, OSError:
        print("submission performed: NO")
        print("provider unreachable or configuration invalid")
        return 1
    print("submission performed: NO")
    print("provider reachable: YES")
    print("api_family:", profile.family)
    print("version:", profile.version or "not observable")
    capabilities = profile.capabilities
    for name in sorted(capabilities.names()):
        print(f"capability {name}:", "yes" if capabilities.supports(name) else "no")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
