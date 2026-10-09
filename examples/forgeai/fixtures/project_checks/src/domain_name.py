"""Normalize a Unicode hostname for a network protocol without making a request."""

import idna


def ascii_hostname(value: str) -> str:
    return idna.encode(value).decode("ascii")
