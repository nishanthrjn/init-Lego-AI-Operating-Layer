"""Immutable value types for the document.ingestion composition."""

from __future__ import annotations

from dataclasses import dataclass

from legoai_document.parsing.values import DocumentFormat


@dataclass(frozen=True, slots=True)
class IngestionRequest:
    """`tenant_id`/`document_id` are caller-supplied stable identities --
    re-ingesting the exact same pair replaces that document's prior chunks
    entirely (task SS27's idempotency requirement), never appends/
    duplicates."""

    tenant_id: str
    document_id: str
    content: bytes
    format: DocumentFormat
    chunk_size: int = 512
    overlap: int = 50


@dataclass(frozen=True, slots=True)
class IngestionResult:
    """Typed ingestion outcome -- no giant untyped result dict (task SS28).
    `model_identity`/`provider_identity` are `None` when `chunk_count == 0`
    (nothing was embedded, so there is no model/provider fact to report --
    never a fabricated value)."""

    document_id: str
    page_count: int
    chunk_count: int
    indexed_chunk_count: int
    model_identity: str | None
    provider_identity: str | None
