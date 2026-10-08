"""Required real Windows Docker Desktop Linux qualification, never mocked away."""

import os
import shutil
import time
from collections.abc import Iterator
from pathlib import Path
from threading import Event, Thread

import pytest

from legoai_engineering.repository.local import (
    LocalRepositoryWorkspace,
    LocalWorkspaceRoot,
)
from legoai_engineering.repository.values import RepositoryText
from legoai_engineering.repository.workspace import RepositoryPath, WorkspacePolicy
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


def inventory(cli: _Cli) -> tuple[bytes, bytes]:
    outputs = []
    for kind in ("container", "volume"):
        arguments = [
            kind,
            "ls",
            "--filter",
            "label=legoai.m6=true",
            "--format",
            "{{.Name}}",
        ]
        if kind == "container":
            arguments = [
                kind,
                "ls",
                "--all",
                "--filter",
                "label=legoai.m6=true",
                "--format",
                "{{.Names}}",
            ]
        code, output, error = cli._run(arguments, time.monotonic() + 15)
        assert code == 0, error
        outputs.append(b"\n".join(sorted(output.splitlines())))
    return outputs[0], outputs[1]


@pytest.fixture
def backend(tmp_path: Path) -> Iterator[DockerSandbox]:
    executable = shutil.which("docker")
    assert executable is not None, "M6 qualification requires Docker Desktop; no skip"
    sandbox = DockerSandbox(DockerSandboxConfig(Path(executable)))
    cli = _Cli(sandbox.config.executable, tmp_path)
    _preflight(cli, sandbox.config.image, time.monotonic() + 30, None)
    before = inventory(cli)
    try:
        yield sandbox
    finally:
        assert inventory(cli) == before, "sandbox resources remain after execution"


def test_real_filesystem_environment_network_and_privilege(
    backend: DockerSandbox, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "source with spaces ü"
    source.mkdir()
    (source / "sample ü.txt").write_text("original", encoding="utf-8")
    canary = tmp_path / "host-canary.txt"
    canary.write_text("host-only-canary", encoding="utf-8")
    monkeypatch.setenv("LEGOAI_SANDBOX_SECRET", "synthetic-secret-value")
    workspace = LocalRepositoryWorkspace(
        LocalWorkspaceRoot(source),
        WorkspacePolicy(1024, 1024, 10, 8, (".git", ".venv")),
    )
    host_paths: list[str] = []
    # Windows C:\ spelling is merely a relative filename on Linux. Probe the
    # actual Desktop/WSL host-drive spellings instead.
    for path in (canary, source / "sample ü.txt"):
        drive = path.drive.rstrip(":").lower()
        relative = "/".join(path.parts[1:])
        host_paths.extend(
            [
                f"/run/desktop/mnt/host/{drive}/{relative}",
                f"/host_mnt/{drive}/{relative}",
                f"/mnt/{drive}/{relative}",
            ]
        )
    script = """
import errno, json, os, pathlib, socket
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
        pathlib.Path(name).write_text('escape')
    except (OSError, ValueError):
        pass
    else:
        raise AssertionError('host path writable')
try:
    pathlib.Path('/etc/legoai-test').write_text('escape')
except OSError as error:
    assert error.errno in (errno.EROFS, errno.EACCES)
else:
    raise AssertionError('root writable')
assert os.listdir('/sys/class/net') == ['lo']
with socket.socket() as sock:
    sock.settimeout(1)
    assert sock.connect_ex(('192.0.2.1', 9)) == errno.ENETUNREACH
pathlib.Path('sample ü.txt').write_text('sandbox-only')
pathlib.Path('result ü.txt').write_text('safe result')
pathlib.Path('not-requested.txt').write_text('not returned')
print('isolated')
""".replace("HOST_PATHS", repr(host_paths))
    result = backend.execute(
        SandboxRequest(
            script,
            (workspace.read_text(RepositoryPath("sample ü.txt")),),
            (RepositoryPath("result ü.txt"),),
        )
    )
    assert result.exit_code == 0, result.stderr
    assert result.stdout == b"isolated\n"
    assert len(result.artifacts) == 1
    assert result.artifacts[0].content == b"safe result"
    assert (source / "sample ü.txt").read_text("utf-8") == "original"
    assert sorted(path.name for path in source.iterdir()) == ["sample ü.txt"]
    assert canary.read_text("utf-8") == "host-only-canary"


def test_nonzero_is_completed_workload(backend: DockerSandbox) -> None:
    result = backend.execute(SandboxRequest("import sys; print('failed'); sys.exit(7)"))
    assert result.exit_code == 7
    assert result.stdout == b"failed\n"


@pytest.mark.parametrize("stream", [1, 2])
def test_output_overflow_terminates_container(
    backend: DockerSandbox, stream: int
) -> None:
    sandbox = DockerSandbox(backend.config, SandboxPolicy(max_output_bytes=128))
    with pytest.raises(SandboxError) as caught:
        sandbox.execute(SandboxRequest(f"import os; os.write({stream}, b'x' * 65536)"))
    assert caught.value.reason is SandboxFailure.OUTPUT_LIMIT


@pytest.mark.parametrize("mode", ["timeout", "cancel"])
def test_lifetime_terminates_descendants(
    backend: DockerSandbox, mode: str, tmp_path: Path
) -> None:
    signal = Event()
    done = Event()
    observed = Event()
    observer_errors: list[BaseException] = []
    cli = _Cli(backend.config.executable, tmp_path)
    baseline = inventory(cli)[0].splitlines()
    sandbox = DockerSandbox(
        backend.config, SandboxPolicy(timeout_seconds=20 if mode == "timeout" else 60)
    )

    def observe() -> None:
        deadline = time.monotonic() + 18
        try:
            while not done.wait(0.1) and time.monotonic() < deadline:
                for name in inventory(cli)[0].splitlines():
                    if name in baseline or not name.endswith(b"-w"):
                        continue
                    code, output, _ = cli._run(
                        ["top", name.decode("ascii"), "-eo", "pid"], deadline
                    )
                    if code == 0 and len(output.splitlines()) >= 3:
                        observed.set()
                        if mode == "cancel":
                            signal.set()
                        return
        except BaseException as error:
            observer_errors.append(error)

    thread = Thread(target=observe)
    thread.start()
    started = time.monotonic()
    script = """
import subprocess, sys, time
subprocess.Popen([sys.executable, '-I', '-B', '-c', 'import time; time.sleep(120)'],
                 start_new_session=True)
print('descendant started', flush=True)
time.sleep(120)
"""
    try:
        with pytest.raises(SandboxError) as caught:
            sandbox.execute(SandboxRequest(script), signal)
        assert caught.value.reason is (
            SandboxFailure.TIMEOUT if mode == "timeout" else SandboxFailure.CANCELLED
        )
        assert time.monotonic() - started < 85
    finally:
        done.set()
        thread.join(timeout=20)
        assert not thread.is_alive()
    assert not observer_errors
    assert observed.is_set(), "real descendant must be observed before termination"
    # Fixture checks Docker confirms both container namespaces and volume removed.


def test_descendant_writer_dead_before_collection(backend: DockerSandbox) -> None:
    script = """
import pathlib, subprocess, sys, time
pathlib.Path('result').write_bytes(b'parent')
subprocess.Popen([sys.executable, '-I', '-B', '-c',
    "import pathlib,time; pathlib.Path('ready').touch(); time.sleep(2); pathlib.Path('result').write_bytes(b'child')"],
    start_new_session=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
while not pathlib.Path('ready').exists():
    time.sleep(0.01)
"""
    result = backend.execute(
        SandboxRequest(script, artifacts=(RepositoryPath("result"),))
    )
    assert result.exit_code == 0
    assert result.artifacts[0].content == b"parent"


@pytest.mark.parametrize(
    "script,path",
    [
        ("import os; os.symlink('/etc/passwd', 'out')", "out"),
        ("import os; os.symlink('/etc', 'out')", "out/passwd"),
        ("import os; os.mkfifo('out')", "out"),
        (
            "import pathlib,os; pathlib.Path('out').write_text('x'); os.link('out','alias')",
            "out",
        ),
        ("import pathlib; pathlib.Path('out').mkdir()", "out"),
        ("pass", "missing"),
        ("import pathlib; pathlib.Path('out').write_bytes(b'x'*129)", "out"),
    ],
)
def test_artifacts_reject_unsafe_or_oversized_files(
    backend: DockerSandbox, script: str, path: str
) -> None:
    sandbox = DockerSandbox(backend.config, SandboxPolicy(max_artifact_bytes=128))
    with pytest.raises(SandboxError) as caught:
        sandbox.execute(SandboxRequest(script, artifacts=(RepositoryPath(path),)))
    assert caught.value.reason is SandboxFailure.ARTIFACT


def test_artifact_aggregate_bound(backend: DockerSandbox) -> None:
    sandbox = DockerSandbox(
        backend.config,
        SandboxPolicy(max_artifact_bytes=128, max_total_artifact_bytes=128),
    )
    with pytest.raises(SandboxError) as caught:
        sandbox.execute(
            SandboxRequest(
                "import pathlib; pathlib.Path('a').write_bytes(b'x'*100); pathlib.Path('b').write_bytes(b'x'*100)",
                artifacts=(RepositoryPath("a"), RepositoryPath("b")),
            )
        )
    assert caught.value.reason is SandboxFailure.ARTIFACT


def test_cpu_memory_pid_and_storage_controls(backend: DockerSandbox) -> None:
    script = """
import errno, os, pathlib, signal
root = pathlib.Path('/sys/fs/cgroup')
assert (root/'memory.max').read_text().strip() == '134217728'
assert (root/'memory.swap.max').read_text().strip() == '0'
assert (root/'pids.max').read_text().strip() == '32'
quota, period = map(int, (root/'cpu.max').read_text().split())
assert quota == period
for path, size, inodes in (('/work', 32*1048576, 4096), ('/tmp', 8*1048576, 1024)):
    filesystem = os.statvfs(path)
    assert filesystem.f_blocks * filesystem.f_frsize == size
    assert filesystem.f_files == inodes
    assert filesystem.f_flag & os.ST_NOEXEC
    assert filesystem.f_flag & os.ST_NOSUID
    assert filesystem.f_flag & os.ST_NODEV
shared = os.statvfs('/dev/shm')
assert shared.f_blocks * shared.f_frsize == 8*1048576
children = []
# Exercise PID exhaustion without starting dozens of independent interpreters
# whose memory demand can trigger the separate 128 MiB limit first.
try:
    for _ in range(40):
        try:
            child = os.fork()
        except OSError as error:
            assert error.errno == errno.EAGAIN
            assert (root/'pids.current').read_text().strip() == '32'
            break
        if child == 0:
            # Stay idle with copy-on-write memory until the parent kills us.
            # Never enter the parent's cleanup or storage assertions.
            try:
                while True:
                    signal.pause()
            finally:
                os._exit(0)
        children.append(child)
    else:
        raise AssertionError('PID limit not enforced')
finally:
    for child in children:
        os.kill(child, signal.SIGKILL)
    for child in children:
        waited, status = os.waitpid(child, 0)
        assert waited == child and os.WIFSIGNALED(status)
        assert os.WTERMSIG(status) == signal.SIGKILL
assert 1 <= len(children) < 32
try:
    with open('full', 'wb', buffering=0) as stream:
        for _ in range(40):
            stream.write(b'x' * 1048576)
except OSError as error:
    assert error.errno == errno.ENOSPC
else:
    raise AssertionError('workspace limit not enforced')
print('resource controls applied')
"""
    result = backend.execute(SandboxRequest(script))
    assert result.exit_code == 0, result.stderr
    assert result.stdout == b"resource controls applied\n"


def test_memory_oom_is_not_an_ordinary_nonzero_exit(backend: DockerSandbox) -> None:
    with pytest.raises(SandboxError) as caught:
        backend.execute(
            SandboxRequest("blocks = []\nwhile True: blocks.append(bytearray(1048576))")
        )
    assert caught.value.reason is SandboxFailure.RESOURCE_LIMIT


def test_missing_runtime_is_explicit(tmp_path: Path) -> None:
    sandbox = DockerSandbox(DockerSandboxConfig(tmp_path / "missing" / "docker.exe"))
    with pytest.raises(SandboxError) as caught:
        sandbox.execute(SandboxRequest("pass"))
    assert caught.value.reason is SandboxFailure.RUNTIME_UNAVAILABLE


def test_missing_image_is_not_pulled(backend: DockerSandbox, tmp_path: Path) -> None:
    cli = _Cli(backend.config.executable, tmp_path)
    with pytest.raises(SandboxError) as caught:
        _preflight(cli, "python@sha256:" + "0" * 64, time.monotonic() + 20, None)
    assert caught.value.reason is SandboxFailure.ENVIRONMENT_UNAVAILABLE


def test_input_control_characters_and_empty_artifact(backend: DockerSandbox) -> None:
    result = backend.execute(
        SandboxRequest(
            "import pathlib,sys; assert sys.stdin.buffer.read()==b''; assert pathlib.Path('input').read_bytes()==bytes([1,10,13]); pathlib.Path('out').write_bytes(b'')",
            (RepositoryText("input", "\x01\n\r"),),
            (RepositoryPath("out"),),
        )
    )
    assert result.exit_code == 0, result.stderr
    assert result.artifacts[0].content == b""


def test_real_checks_environment_is_ready() -> None:
    """Startup readiness on the qualified Desktop engine: metadata only."""
    executable = shutil.which("docker")
    assert executable is not None, "requires Docker Desktop; no skip"
    for profile in (SandboxImage.PYTHON_CHECKS, SandboxImage.PYTHON_STDLIB):
        DockerSandbox(DockerSandboxConfig(Path(executable), profile)).verify_ready()
