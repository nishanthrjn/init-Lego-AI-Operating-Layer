"""Forbid external sockets while allowing Windows asyncio's internal socketpair."""

import socket
import threading
from collections.abc import Callable, Iterator
from typing import cast
from unittest.mock import patch

import pytest


@pytest.fixture(autouse=True)
def no_external_network() -> Iterator[None]:
    original_pair = socket.socketpair
    original_connect = cast(
        Callable[[socket.socket, object], None], socket.socket.connect
    )
    local = threading.local()

    def connect(sock: socket.socket, address: object) -> None:
        if not getattr(local, "creating_pair", False):
            raise AssertionError("Network forbidden")
        original_connect(sock, address)

    def socketpair() -> tuple[socket.socket, socket.socket]:
        local.creating_pair = True
        try:
            return original_pair()
        finally:
            local.creating_pair = False

    with (
        patch.object(socket.socket, "connect", connect),
        patch("socket.socketpair", socketpair),
        patch(
            "socket.create_connection", side_effect=AssertionError("Network forbidden")
        ),
    ):
        yield
