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

# A small typed package with tests: the bounded repository size ForgeAI-1 targets.
PROJECT = {
    "pyproject.toml": """[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]

[tool.mypy]
python_version = "3.14"
strict = true
mypy_path = "src"

[tool.ruff]
target-version = "py314"
src = ["src"]

[tool.ruff.lint]
select = ["E", "F", "I", "B", "UP"]
""",
    "src/orders/__init__.py": '"""Small order-processing package used as a fixture."""\n',
    "src/orders/models.py": '''"""Immutable order values."""

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum


class Status(Enum):
    OPEN = "open"
    PAID = "paid"
    CANCELLED = "cancelled"


@dataclass(frozen=True, slots=True)
class Line:
    sku: str
    quantity: int
    unit_price: Decimal


@dataclass(frozen=True, slots=True)
class Order:
    order_id: str
    customer: str
    lines: tuple[Line, ...] = field(default_factory=tuple)
    status: Status = Status.OPEN
''',
    "src/orders/validation.py": '''"""Input validation for orders."""

from decimal import Decimal

from orders.models import Line, Order


class ValidationError(ValueError):
    """Raised when an order or line is invalid."""


def validate_line(line: Line) -> Line:
    if not line.sku or not line.sku.isalnum():
        raise ValidationError("sku must be alphanumeric")
    if line.quantity <= 0:
        raise ValidationError("quantity must be positive")
    if line.unit_price < Decimal("0"):
        raise ValidationError("unit price must not be negative")
    return line


def validate_order(order: Order) -> Order:
    if not order.order_id:
        raise ValidationError("order id is required")
    if not order.customer.strip():
        raise ValidationError("customer is required")
    if not order.lines:
        raise ValidationError("an order needs at least one line")
    seen: set[str] = set()
    for line in order.lines:
        validate_line(line)
        if line.sku in seen:
            raise ValidationError(f"duplicate sku {line.sku}")
        seen.add(line.sku)
    return order
''',
    "src/orders/pricing.py": '''"""Deterministic pricing rules."""

from decimal import ROUND_HALF_UP, Decimal

from orders.models import Line, Order

TAX_RATE = Decimal("0.20")
BULK_THRESHOLD = 10
BULK_DISCOUNT = Decimal("0.05")
CENT = Decimal("0.01")


def line_total(line: Line) -> Decimal:
    total = line.unit_price * line.quantity
    if line.quantity >= BULK_THRESHOLD:
        total -= total * BULK_DISCOUNT
    return total.quantize(CENT, rounding=ROUND_HALF_UP)


def subtotal(order: Order) -> Decimal:
    return sum((line_total(line) for line in order.lines), Decimal("0.00"))


def tax(order: Order) -> Decimal:
    return (subtotal(order) * TAX_RATE).quantize(CENT, rounding=ROUND_HALF_UP)


def grand_total(order: Order) -> Decimal:
    return subtotal(order) + tax(order)
''',
    "src/orders/repository.py": '''"""Storage boundary and an in-memory realization."""

from typing import Protocol

from orders.models import Order


class OrderRepository(Protocol):
    def get(self, order_id: str) -> Order | None: ...

    def save(self, order: Order) -> None: ...


class InMemoryOrderRepository:
    def __init__(self) -> None:
        self._orders: dict[str, Order] = {}

    def get(self, order_id: str) -> Order | None:
        return self._orders.get(order_id)

    def save(self, order: Order) -> None:
        self._orders[order.order_id] = order

    def __len__(self) -> int:
        return len(self._orders)
''',
    "src/orders/service.py": '''"""Order lifecycle over an injected repository."""

from dataclasses import replace
from decimal import Decimal

from orders.models import Order, Status
from orders.pricing import grand_total
from orders.repository import OrderRepository
from orders.validation import ValidationError, validate_order


class OrderService:
    def __init__(self, repository: OrderRepository) -> None:
        self._repository = repository

    def place(self, order: Order) -> Decimal:
        validate_order(order)
        if self._repository.get(order.order_id) is not None:
            raise ValidationError("order already exists")
        self._repository.save(order)
        return grand_total(order)

    def pay(self, order_id: str) -> Order:
        order = self._require(order_id)
        if order.status is not Status.OPEN:
            raise ValidationError("only open orders can be paid")
        paid = replace(order, status=Status.PAID)
        self._repository.save(paid)
        return paid

    def cancel(self, order_id: str) -> Order:
        order = self._require(order_id)
        if order.status is Status.PAID:
            raise ValidationError("paid orders cannot be cancelled")
        cancelled = replace(order, status=Status.CANCELLED)
        self._repository.save(cancelled)
        return cancelled

    def _require(self, order_id: str) -> Order:
        order = self._repository.get(order_id)
        if order is None:
            raise ValidationError("unknown order")
        return order
''',
    "src/orders/formatting.py": '''"""Human-readable receipts."""

from orders.models import Order
from orders.pricing import grand_total, line_total, subtotal, tax


def receipt(order: Order) -> str:
    rows = [f"Order {order.order_id} for {order.customer}"]
    for line in order.lines:
        rows.append(f"{line.sku} x{line.quantity}: {line_total(line)}")
    rows.append(f"Subtotal: {subtotal(order)}")
    rows.append(f"Tax: {tax(order)}")
    rows.append(f"Total: {grand_total(order)}")
    return "\\n".join(rows)
''',
    "tests/test_validation.py": """from decimal import Decimal

import pytest

from orders.models import Line, Order
from orders.validation import ValidationError, validate_line, validate_order


def order(*lines: Line) -> Order:
    return Order("o-1", "Ada", lines)


def test_valid_line_is_returned() -> None:
    line = Line("sku1", 2, Decimal("3.50"))
    assert validate_line(line) is line


@pytest.mark.parametrize(
    "line",
    [
        Line("", 1, Decimal("1")),
        Line("bad-sku", 1, Decimal("1")),
        Line("sku1", 0, Decimal("1")),
        Line("sku1", 1, Decimal("-1")),
    ],
)
def test_invalid_lines_are_rejected(line: Line) -> None:
    with pytest.raises(ValidationError):
        validate_line(line)


def test_order_requires_lines_and_unique_skus() -> None:
    with pytest.raises(ValidationError):
        validate_order(order())
    line = Line("sku1", 1, Decimal("1"))
    with pytest.raises(ValidationError):
        validate_order(order(line, line))
    assert validate_order(order(line)).lines == (line,)
""",
    "tests/test_pricing.py": """from decimal import Decimal

from orders.formatting import receipt
from orders.models import Line, Order
from orders.pricing import grand_total, line_total, subtotal, tax


def test_bulk_discount_applies_at_threshold() -> None:
    assert line_total(Line("a", 9, Decimal("10.00"))) == Decimal("90.00")
    assert line_total(Line("a", 10, Decimal("10.00"))) == Decimal("95.00")


def test_totals_and_receipt() -> None:
    order = Order("o-2", "Grace", (Line("a", 2, Decimal("5.00")),))
    assert subtotal(order) == Decimal("10.00")
    assert tax(order) == Decimal("2.00")
    assert grand_total(order) == Decimal("12.00")
    assert receipt(order).endswith("Total: 12.00")
""",
    "tests/test_service.py": """from decimal import Decimal

import pytest

from orders.models import Line, Order, Status
from orders.repository import InMemoryOrderRepository
from orders.service import OrderService
from orders.validation import ValidationError


def service() -> tuple[OrderService, InMemoryOrderRepository]:
    repository = InMemoryOrderRepository()
    return OrderService(repository), repository


def test_place_pay_and_reject_duplicates() -> None:
    orders, repository = service()
    order = Order("o-3", "Linus", (Line("a", 1, Decimal("10.00")),))
    assert orders.place(order) == Decimal("12.00")
    assert len(repository) == 1
    with pytest.raises(ValidationError):
        orders.place(order)
    assert orders.pay("o-3").status is Status.PAID
    with pytest.raises(ValidationError):
        orders.cancel("o-3")


def test_unknown_order_is_rejected() -> None:
    orders, _ = service()
    with pytest.raises(ValidationError):
        orders.pay("missing")
""",
}

VARIANTS = {
    "failing-test": {
        "tests/test_regression.py": """from decimal import Decimal

from orders.models import Line
from orders.pricing import line_total


def test_expected_regression() -> None:
    assert line_total(Line("a", 10, Decimal("10.00"))) == Decimal("100.00")
""",
    },
    "collection-error": {
        "tests/test_broken.py": "import orders.missing_module  # noqa: F401\n",
    },
    "lint-finding": {"src/orders/unused.py": "import os\n"},
    "unformatted": {"src/orders/ugly.py": "value=1\n"},
    "type-error": {
        "src/orders/broken_types.py": 'def total() -> int:\n    return "not an int"\n',
    },
    "slow-test": {
        "tests/test_slow.py": "import time\n\n\ndef test_slow() -> None:\n"
        "    time.sleep(120)\n",
    },
    "noisy-test": {
        "tests/test_noisy.py": 'def test_noisy() -> None:\n    print("x" * 200_000)\n'
        "    raise AssertionError\n",
    },
    "process-test": {
        "tests/test_processes.py": """import errno
import os
import signal


def test_pid_limit_reached() -> None:
    children = []
    try:
        for _ in range(40):
            try:
                child = os.fork()
            except OSError as error:
                assert error.errno == errno.EAGAIN
                break
            if child == 0:
                try:
                    while True:
                        signal.pause()
                finally:
                    os._exit(0)
            children.append(child)
        else:
            raise AssertionError("PID limit not enforced")
    finally:
        for child in children:
            os.kill(child, signal.SIGKILL)
        for child in children:
            os.waitpid(child, 0)
    assert 1 <= len(children) < 32
""",
    },
    "memory-test": {
        "tests/test_memory.py": """def test_allocates_beyond_limit() -> None:
    blocks = []
    for _ in range(512):
        blocks.append(bytearray(1_048_576))
""",
    },
}


def files(variant: str | None = None) -> tuple[RepositoryText, ...]:
    project = dict(PROJECT)
    if variant is not None:
        project.update(VARIANTS[variant])
    return tuple(RepositoryText(path, text) for path, text in sorted(project.items()))


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
