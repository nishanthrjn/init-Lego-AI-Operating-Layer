"""Errors for the document.retrieval capability."""

from __future__ import annotations


class RetrievalValidationError(Exception):
    """Malformed query (empty scope, non-positive `top_k`, mismatched/empty
    embedding) -- a caller precondition violation."""


class RetrievalStoreError(Exception):
    """The local store could not be read or written (corrupt file,
    filesystem failure, schema mismatch) -- distinct from "no match found",
    which is not an error at all (an empty `RetrievalResult`)."""
