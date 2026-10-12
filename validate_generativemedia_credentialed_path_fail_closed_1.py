"""Maintainer-only, offline H-01 scope correction qualification; no live providers."""

import os
import subprocess
import sys
import tempfile
import venv
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BASELINE = "a61590446b34586a0f30fa8da50020a801ee5cd5"
PACKAGE = "packages/legoai-generative-media"
SELF = "validate_generativemedia_credentialed_path_fail_closed_1.py"
PRODUCTION = [
    f"{PACKAGE}/src/legoai_generative_media/{name}.py"
    for name in ("config", "service", "http", "values")
]
TESTS = [
    f"{PACKAGE}/tests/{name}.py"
    for name in (
        "test_credential_scope",
        "test_architecture",
        "test_provider_config",
        "test_driver_v2",
        "test_tryon_reuse",
        "test_input_policy",
        "test_public_execution",
        "test_remote_transport",
    )
]
TARGETS = [*PRODUCTION, *TESTS, SELF]
ALLOWED = frozenset(
    TARGETS
    + [
        f"{PACKAGE}/README.md",
        "docs/modules/MODULE-CATALOG.md",
        "planning/LEGOAI-ARCHITECTURE-DESIGN-CONFORMANCE-AUDIT-1.md",
        "planning/GENERATIVE-MEDIA-CREDENTIALED-PATH-FAIL-CLOSED-1.md",
    ]
)
WHEEL_SMOKE = """
from legoai_generative_media.config import ProviderConfig, resolve_secret
from legoai_generative_media.service import ProviderError, default_transports
from legoai_generative_media.http import Endpoint, LocalHTTP, RemoteHTTPS
from legoai_generative_media.values import REASONS
reason = "credentialled_provider_unsupported"
assert reason in REASONS
class Forbidden(dict):
    def get(self, *args):
        raise AssertionError("material lookup")
for operation in (
    lambda: resolve_secret("env:SYNTHETIC", Forbidden()),
    lambda: default_transports(ProviderConfig(
        "http://127.0.0.1:8188", auth="bearer", secret_ref="env:SYNTHETIC")),
    lambda: LocalHTTP(Endpoint(), token="synthetic"),
    lambda: RemoteHTTPS("https://media.example.org", token="synthetic"),
):
    try:
        operation()
    except (ProviderError, ValueError) as error:
        assert str(error) == reason
    else:
        raise AssertionError("credential path admitted")
assert resolve_secret(None, Forbidden()) is None
default_transports(ProviderConfig("http://127.0.0.1:8188"))
"""


def paths(args: list[str]) -> set[str]:
    output = subprocess.run(
        ["git", *args], cwd=ROOT, check=True, capture_output=True, timeout=30
    ).stdout
    return {part.decode("utf-8") for part in output.split(b"\0") if part}


def check_scope() -> None:
    changed = paths(["diff", "--name-only", "--no-renames", "-z", BASELINE])
    changed |= paths(
        ["diff", "--cached", "--name-only", "--no-renames", "-z", BASELINE]
    )
    changed |= paths(["ls-files", "--others", "--exclude-standard", "-z"])
    if changed - ALLOWED:
        raise ValueError(f"outside media correction scope: {sorted(changed - ALLOWED)}")
    for name in ALLOWED:
        if not (ROOT / name).is_file() or (ROOT / name).is_symlink():
            raise ValueError(f"missing or symlinked slice file: {name}")
    # Scope excludes every ADR, Core/Model file and dependency manifest/lock.
    adr = (ROOT / "adrs/ADR-027.md").read_text(encoding="utf-8")
    if "Status: Deferred" not in adr or "B-02 remains STILL_BLOCKED" not in adr:
        raise ValueError("deferral baseline changed")


def main() -> int:
    phase = "media-only scope; Core, Model, ADRs and dependencies unchanged"
    try:
        print(f"[PHASE] {phase}", flush=True)
        check_scope()
        # Copy only platform/process settings, never enumerate credential variables.
        environment = {
            key: os.environ[key]
            for key in (
                "PATH",
                "SystemRoot",
                "WINDIR",
                "TEMP",
                "TMP",
                "TMPDIR",
                "LOCALAPPDATA",
                "APPDATA",
                "USERPROFILE",
                "HOME",
            )
            if key in os.environ
        }
        search = [ROOT / PACKAGE / "src", ROOT / "src", ROOT / PACKAGE / "tests", ROOT]
        environment.update(
            PYTHONPATH=os.pathsep.join(map(str, search)),
            MYPYPATH=os.pathsep.join(map(str, search)),
            PYTHONDONTWRITEBYTECODE="1",
            PYTEST_DISABLE_PLUGIN_AUTOLOAD="1",
            UV_OFFLINE="1",
            UV_PYTHON=sys.executable,
        )
        with tempfile.TemporaryDirectory(prefix="media-h01-") as temporary:
            scratch = Path(temporary)

            def run(label: str, args: list[str], cwd: Path = ROOT) -> None:
                nonlocal phase
                phase = label
                print(f"\n[PHASE] {phase}", flush=True)
                subprocess.run(args, cwd=cwd, env=environment, check=True, timeout=600)

            def tests(label: str, files: list[str]) -> None:
                run(
                    label,
                    [
                        sys.executable,
                        "-m",
                        "pytest",
                        "-q",
                        "-p",
                        "no:cacheprovider",
                        *files,
                    ],
                )

            def media(label: str, names: tuple[str, ...]) -> None:
                tests(label, [f"{PACKAGE}/tests/{name}.py" for name in names])

            media(
                "credential refusal and transport ordering",
                ("test_credential_scope", "test_remote_transport"),
            )
            media(
                "probe and discovery",
                ("test_provider_config", "test_discovery", "test_driver_v2"),
            )
            media(
                "text and facade regressions",
                (
                    "test_adapter",
                    "test_contracts",
                    "test_effects",
                    "test_policy",
                    "test_reconcile",
                    "test_reuse",
                    "test_public_execution",
                    "test_composition",
                ),
            )
            media(
                "VTO and M-04 regressions",
                (
                    "test_tryon_reuse",
                    "test_tryon_contract",
                    "test_tryon_preflight",
                    "test_tryon_workflow",
                    "test_tryon_geometry",
                    "test_tryon_effects",
                    "test_tryon_composition",
                    "test_tryon_reconcile",
                    "test_tryon_live_tooling",
                    "test_input_policy",
                    "test_input_disclosure",
                ),
            )
            tests(
                "architecture",
                [
                    f"{PACKAGE}/tests/test_architecture.py",
                    "tests/architecture/test_consumer_private_boundaries.py",
                    "tests/architecture/test_governed_execution.py",
                ],
            )
            tests(
                "Model Secret isolation; synthetic material only",
                [
                    "tests/integration/composition/test_secret_uses.py",
                    "tests/unit/reference/test_secret_source_s1.py",
                ],
            )
            artifacts = scratch / "wheels"
            for project in (ROOT, ROOT / PACKAGE):
                run(
                    "offline wheel build " + project.name,
                    [
                        "uv",
                        "build",
                        "--offline",
                        "--no-build-isolation",
                        "--wheel",
                        "--out-dir",
                        str(artifacts),
                        str(project),
                    ],
                )
            isolated = scratch / "isolated"
            phase = "fresh isolated environment"
            print(f"\n[PHASE] {phase}", flush=True)
            venv.EnvBuilder(with_pip=False).create(isolated)
            python = isolated / (
                "Scripts/python.exe" if os.name == "nt" else "bin/python"
            )
            wheels = sorted(artifacts.glob("*.whl"))
            if len(wheels) != 2:
                raise ValueError("exact Core and media wheels required")
            run(
                "offline wheel installation",
                [
                    "uv",
                    "pip",
                    "install",
                    "--offline",
                    "--no-deps",
                    "--python",
                    str(python),
                    *map(str, wheels),
                ],
            )
            run(
                "installed credential refusal contracts",
                [str(python), "-I", "-c", WHEEL_SMOKE],
                scratch,
            )
            run(
                "typing",
                [
                    sys.executable,
                    "-m",
                    "mypy",
                    "--config-file",
                    f"{PACKAGE}/pyproject.toml",
                    "--cache-dir",
                    str(scratch / "mypy"),
                    *TARGETS,
                ],
            )
            run("lint", [sys.executable, "-m", "ruff", "check", "--no-cache", *TARGETS])
            run(
                "format",
                [
                    sys.executable,
                    "-m",
                    "ruff",
                    "format",
                    "--check",
                    "--no-cache",
                    *TARGETS,
                ],
            )
            run("working whitespace", ["git", "diff", "--check", BASELINE, "--"])
            run(
                "staged whitespace",
                ["git", "diff", "--cached", "--check", BASELINE, "--"],
            )
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        print(f"FAIL: {phase}: {exc}; later phases NOT RUN")
        return 1
    print(
        "GENERATIVE-MEDIA-CREDENTIALED-PATH-FAIL-CLOSED-1 LOCALLY QUALIFIED; "
        "H-01 CLOSED FOR SUPPORTED SCOPE; ADR-027 DEFERRED; B-02 STILL_BLOCKED; "
        "CREDENTIALED MEDIA UNSUPPORTED/UNQUALIFIED; REMOTE VTO UNSUPPORTED; "
        "NO LIVE OR GLOBAL SECURITY QUALIFICATION"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
