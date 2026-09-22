"""Errors for the document.rerank capability."""

from __future__ import annotations


class RerankValidationError(Exception):
    """`top_n <= 0` or another malformed request -- a caller precondition
    violation."""
