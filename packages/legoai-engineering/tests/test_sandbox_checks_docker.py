"""CR-2a: real Docker qualification of the PYTHON_CHECKS image; never mocked away.

Without LEGOAI_SANDBOX_CHECKS_IMAGE these tests re-check the recorded qualified
image ID in `sandbox.docker._approved_image`. With it (set by
validate_consumer_readiness_cr2a.py after a build), they qualify that candidate,
bound only inside this test process; production accepts the recorded ID only.

The harness below is trusted qualification code. It runs the M5 check tools with
M5's fixed options and records whole-container cgroup memory evidence.
"""

import json
import os
import shutil
import time
from collections.abc import Iterator
from pathlib import Path

import pytest
from python_checks_project import project_files

import legoai_engineering.sandbox.docker as docker_module
from legoai_engineering.repository.values import RepositoryText
from legoai_engineering.sandbox._process import _Cli
from legoai_engineering.sandbox.docker import (
    DockerSandbox,
    DockerSandboxConfig,
    SandboxImage,
    _preflight,
)
from legoai_engineering.sandbox.errors import SandboxError, SandboxFailure
from legoai_engineering.sandbox.values import SandboxPolicy, SandboxRequest

pytestmark = pytest.mark.skipif(
    os.name != "nt", reason="Windows Desktop reference scope"
)

CANDIDATE_ENV = "LEGOAI_SANDBOX_CHECKS_IMAGE"
MEMORY_LIMIT = 134_217_728
EXPECTED_DISTRIBUTIONS = {
    "ast-serialize": "0.11.2",
    "iniconfig": "2.3.0",
    "librt": "0.15.0",
    "mypy": "2.3.1",
    "mypy-extensions": "1.1.0",
    "packaging": "26.3",
    "pathspec": "1.1.1",
    "pluggy": "1.6.0",
    "pygments": "2.21.0",
    "pytest": "9.1.1",
    "ruff": "0.16.8",
    "typing-extensions": "4.16.0",
}

HARNESS = r"""
import json, pathlib, subprocess, sys, time

SPEC = json.loads(__SPEC__)
COMMANDS = {
    "pytest": ["/usr/local/bin/pytest", "-q", "-o", "addopts=", "-p", "no:cacheprovider"],
    "ruff-check": ["/usr/local/bin/ruff", "check", "--no-fix", "--no-fix-only", "--no-cache"],
    "ruff-format": ["/usr/local/bin/ruff", "format", "--check", "--no-cache"],
    "mypy": ["/usr/local/bin/mypy", "--no-incremental", "--cache-dir", "/dev/null"],
}
argv = COMMANDS[SPEC["tool"]] + ["--", *("/work/" + t for t in SPEC["targets"])]
env = {
    "PATH": "/usr/local/bin:/usr/bin:/bin", "LANG": "C.UTF-8", "HOME": "/nonexistent",
    "TMPDIR": "/tmp", "PYTHONDONTWRITEBYTECODE": "1", "PYTHONUTF8": "1",
    "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1", "NO_COLOR": "1",
}
start = time.monotonic()
completed = subprocess.run(
    argv, cwd="/work", env=env, stdin=subprocess.DEVNULL,
    capture_output=True, timeout=SPEC["timeout"], shell=False,
)
elapsed = time.monotonic() - start
cgroup = pathlib.Path("/sys/fs/cgroup")


def read(name):
    try:
        return (cgroup / name).read_text()
    except OSError:
        return None


events = {}
for row in (read("memory.events") or "").splitlines():
    key, value = row.split()
    events[key] = int(value)
peak = read("memory.peak")
if SPEC["forward"]:
    sys.stdout.buffer.write(completed.stdout)
    sys.stdout.flush()
print(json.dumps({
    "returncode": completed.returncode,
    "elapsed": round(elapsed, 3),
    "peak": int(peak) if peak is not None else None,
    "limit": int(read("memory.max")),
    "oom_kill": events.get("oom_kill"),
    "stdout": completed.stdout[-4000:].decode("utf-8", "replace"),
    "stderr": completed.stderr[-4000:].decode("utf-8", "replace"),
}))
"""


def files(variant: str | None = None) -> tuple[RepositoryText, ...]:
    return project_files(variant)


def inventory(cli: _Cli) -> tuple[bytes, ...]:
    outputs = []
    for kind, extra, field in (
        ("container", ["--all"], "{{.Names}}"),
        ("volume", [], "{{.Name}}"),
    ):
        code, output, error = cli._run(
            [kind, "ls", *extra, "--filter", "label=legoai.m6=true", "--format", field],
            time.monotonic() + 15,
        )
        assert code == 0, error
        outputs.append(b"\n".join(sorted(output.splitlines())))
    return tuple(outputs)


@pytest.fixture
def checks(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[DockerSandbox]:
    executable = shutil.which("docker")
    assert executable is not None, "CR-2a qualification requires Docker; no skip"
    approved = docker_module._approved_image(SandboxImage.PYTHON_CHECKS)
    candidate = os.environ.get(CANDIDATE_ENV)
    if candidate:
        # An explicit candidate (a new build) is what gets qualified, bound only
        # inside this test process. Production still accepts the recorded ID only.
        assert docker_module._immutable(candidate) and candidate.startswith("sha256:")
        if candidate != approved:
            print(f"\nCR2A-CANDIDATE {candidate} (recorded: {approved})")
        original = docker_module._approved_image

        def qualification_binding(image: SandboxImage) -> str | None:
            if image is SandboxImage.PYTHON_CHECKS:
                return candidate
            return original(image)

        monkeypatch.setattr(docker_module, "_approved_image", qualification_binding)
    else:
        assert approved is not None, f"set {CANDIDATE_ENV} to the built image ID"
    sandbox = DockerSandbox(
        DockerSandboxConfig(Path(executable), SandboxImage.PYTHON_CHECKS),
        SandboxPolicy(timeout_seconds=180),
    )
    cli = _Cli(sandbox.config.executable, tmp_path)
    _preflight(cli, sandbox.config.image, time.monotonic() + 30, None)
    before = inventory(cli)
    try:
        yield sandbox
    finally:
        assert inventory(cli) == before, "sandbox resources remain after execution"


def run_tool(
    sandbox: DockerSandbox,
    tool: str,
    targets: list[str],
    variant: str | None = None,
    *,
    forward: bool = False,
) -> dict[str, object]:
    spec = {"tool": tool, "targets": targets, "timeout": 170, "forward": forward}
    script = HARNESS.replace("__SPEC__", repr(json.dumps(spec)))
    result = sandbox.execute(SandboxRequest(script, files(variant)))
    assert result.exit_code == 0, result.stderr
    row: dict[str, object] = json.loads(result.stdout.decode().splitlines()[-1])
    print(
        f"\nCR2A-MEMORY tool={tool} fixture={variant or 'baseline'}"
        f" limit={row['limit']} exit={row['returncode']} oom_kill={row['oom_kill']}"
        f" peak_bytes={row['peak']} elapsed_s={row['elapsed']}"
    )
    return row


def test_toolchain_versions_and_contents(checks: DockerSandbox) -> None:
    script = """
import importlib.metadata, json, re, shutil, sys
names = {
    re.sub(r"[-_.]+", "-", d.metadata["Name"]).lower(): d.version
    for d in importlib.metadata.distributions()
}
print(json.dumps({
    "python": sys.version.split()[0],
    "distributions": names,
    "git": shutil.which("git"),
    "tools": [shutil.which(t) for t in ("pytest", "ruff", "mypy")],
}))
"""
    result = checks.execute(SandboxRequest(script))
    assert result.exit_code == 0, result.stderr
    found = json.loads(result.stdout)
    print(f"\nCR2A-TOOLCHAIN {json.dumps(found, sort_keys=True)}")
    distributions = dict(found["distributions"])
    distributions.pop("pip", None)
    assert distributions == EXPECTED_DISTRIBUTIONS
    assert found["python"].startswith("3.14.")
    assert found["git"] is None
    assert found["tools"] == [
        "/usr/local/bin/pytest",
        "/usr/local/bin/ruff",
        "/usr/local/bin/mypy",
    ]


def test_checks_image_keeps_m6_confinement(
    checks: DockerSandbox, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    canary = tmp_path / "host-canary.txt"
    canary.write_text("host-only-canary", encoding="utf-8")
    monkeypatch.setenv("LEGOAI_SANDBOX_SECRET", "synthetic-secret-value")
    drive = canary.drive.rstrip(":").lower()
    relative = "/".join(canary.parts[1:])
    host_paths = [
        f"/run/desktop/mnt/host/{drive}/{relative}",
        f"/host_mnt/{drive}/{relative}",
        f"/mnt/{drive}/{relative}",
    ]
    script = """
import errno, os, pathlib, socket
assert os.getuid() == os.getgid() == 65534
assert os.getpid() == 1
assert os.statvfs('/').f_flag & os.ST_RDONLY
assert 'LEGOAI_SANDBOX_SECRET' not in os.environ
status = pathlib.Path('/proc/self/status').read_text()
assert 'CapEff:\\t0000000000000000' in status
assert 'NoNewPrivs:\\t1' in status
assert not pathlib.Path('/var/run/docker.sock').exists()
for name in HOST_PATHS:
    try:
        pathlib.Path(name).read_bytes()
    except (OSError, ValueError):
        pass
    else:
        raise AssertionError('host file visible')
try:
    pathlib.Path('/usr/local/bin/legoai-test').write_text('escape')
except OSError as error:
    assert error.errno in (errno.EROFS, errno.EACCES)
else:
    raise AssertionError('image root writable')
assert os.listdir('/sys/class/net') == ['lo']
with socket.socket() as sock:
    sock.settimeout(1)
    assert sock.connect_ex(('192.0.2.1', 9)) == errno.ENETUNREACH
root = pathlib.Path('/sys/fs/cgroup')
assert (root / 'memory.max').read_text().strip() == '134217728'
assert (root / 'memory.swap.max').read_text().strip() == '0'
assert (root / 'pids.max').read_text().strip() == '32'
quota, period = map(int, (root / 'cpu.max').read_text().split())
assert quota == period
work = os.statvfs('/work')
assert work.f_blocks * work.f_frsize == 32 * 1048576
assert work.f_flag & os.ST_NOEXEC
print('confined')
""".replace("HOST_PATHS", repr(host_paths))
    result = checks.execute(SandboxRequest(script))
    assert result.exit_code == 0, result.stderr
    assert result.stdout == b"confined\n"
    assert canary.read_text("utf-8") == "host-only-canary"


@pytest.mark.parametrize(
    ("tool", "targets", "variant", "expected"),
    [
        ("pytest", ["tests"], None, 0),
        ("pytest", ["tests"], "failing-test", 1),
        ("pytest", ["tests"], "collection-error", 2),
        ("pytest", ["src"], None, 5),
        ("ruff-check", ["src", "tests"], None, 0),
        ("ruff-check", ["src", "tests"], "lint-finding", 1),
        ("ruff-format", ["src", "tests"], None, 0),
        ("ruff-format", ["src", "tests"], "unformatted", 1),
        ("mypy", ["src"], None, 0),
        ("mypy", ["src"], "type-error", 1),
    ],
    ids=[
        "pytest-pass",
        "pytest-fail",
        "pytest-collection-error",
        "pytest-no-tests",
        "ruff-clean",
        "ruff-finding",
        "ruff-format-clean",
        "ruff-format-finding",
        "mypy-clean",
        "mypy-finding",
    ],
)
def test_tool_outcomes_within_fixed_memory(
    checks: DockerSandbox,
    tool: str,
    targets: list[str],
    variant: str | None,
    expected: int,
) -> None:
    row = run_tool(checks, tool, targets, variant)
    assert row["returncode"] == expected, (row["stdout"], row["stderr"])
    assert row["limit"] == MEMORY_LIMIT
    assert row["oom_kill"] == 0
    peak = row["peak"]
    assert peak is None or (isinstance(peak, int) and peak <= MEMORY_LIMIT)


def test_timeout_is_enforced(checks: DockerSandbox) -> None:
    short = DockerSandbox(checks.config, SandboxPolicy(timeout_seconds=20))
    with pytest.raises(SandboxError) as caught:
        run_tool(short, "pytest", ["tests/test_slow.py"], "slow-test")
    assert caught.value.reason is SandboxFailure.TIMEOUT


def test_output_limit_is_enforced(checks: DockerSandbox) -> None:
    small = DockerSandbox(
        checks.config, SandboxPolicy(timeout_seconds=180, max_output_bytes=16_384)
    )
    with pytest.raises(SandboxError) as caught:
        run_tool(small, "pytest", ["tests/test_noisy.py"], "noisy-test", forward=True)
    assert caught.value.reason is SandboxFailure.OUTPUT_LIMIT


def test_pid_limit_applies_to_tool_processes(checks: DockerSandbox) -> None:
    row = run_tool(checks, "pytest", ["tests/test_processes.py"], "process-test")
    assert row["returncode"] == 0, (row["stdout"], row["stderr"])


def test_memory_limit_is_never_silent_success(checks: DockerSandbox) -> None:
    # Either Docker reports the OOM (RESOURCE_LIMIT) or the harness observes the
    # tool killed with a cgroup oom_kill event. A zero exit is never accepted.
    try:
        row = run_tool(checks, "pytest", ["tests/test_memory.py"], "memory-test")
    except SandboxError as error:
        assert error.reason is SandboxFailure.RESOURCE_LIMIT
        print("\nCR2A-MEMORY tool=pytest fixture=memory-test outcome=RESOURCE_LIMIT")
        return
    assert row["returncode"] != 0
    oom_kill = row["oom_kill"]
    assert isinstance(oom_kill, int) and oom_kill >= 1
