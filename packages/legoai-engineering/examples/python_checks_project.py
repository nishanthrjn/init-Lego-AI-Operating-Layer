"""A small typed Python project used to qualify and exercise sandboxed checks.

Seven modules and three test files (about 7.9 KB): the bounded repository size
ForgeAI-1 targets. VARIANTS add single files that produce known check outcomes.
This is fixture data only; nothing here is executed on import.
"""

from legoai_engineering.repository.values import RepositoryText

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
    "network-test": {
        "tests/test_network.py": """import errno
import os
import socket


def test_network_is_unavailable() -> None:
    assert os.listdir("/sys/class/net") == ["lo"]
    with socket.socket() as sock:
        sock.settimeout(1)
        assert sock.connect_ex(("192.0.2.1", 9)) == errno.ENETUNREACH
""",
    },
}


def project_files(variant: str | None = None) -> tuple[RepositoryText, ...]:
    project = dict(PROJECT)
    if variant is not None:
        project.update(VARIANTS[variant])
    return tuple(RepositoryText(path, text) for path, text in sorted(project.items()))
