"""`SQLiteRetrievalStore` -- the v0.1 self-contained local retrieval
backend (`planning/V0.1-DOCUMIND-IMPLEMENTATION-PLAN.md` SS L's storage
decision). stdlib `sqlite3` only: no Postgres/pgvector, no vector-database
dependency. Vector similarity is a pure-Python brute-force cosine scan over
stored embeddings (JSON-encoded, never a binary/NumPy format, to keep this
store dependency-free and trivially portable); lexical scoring is a
deterministic word-overlap heuristic (see `legoai_document.retrieval.api`'s
own docstring) rather than SQLite's FTS5 extension, since FTS5 availability
is not guaranteed across every stdlib `sqlite3` build -- this store must
work identically everywhere Python 3.14 runs.

Correctness over scale: a brute-force scan is appropriate for the small,
single-user local document sets this v0.1 slice targets (task SS20); it is
not a claim of production-scale retrieval performance.
"""

from __future__ import annotations

import json
import math
import sqlite3
from pathlib import Path

from legoai_document.retrieval.errors import RetrievalStoreError
from legoai_document.retrieval.values import IndexedChunk, RetrievalScope

_SCHEMA = """
CREATE TABLE IF NOT EXISTS chunks (
    tenant_id TEXT NOT NULL,
    document_id TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    text TEXT NOT NULL,
    embedding TEXT NOT NULL,
    PRIMARY KEY (tenant_id, document_id, chunk_index)
)
"""


class SQLiteRetrievalStore:
    """Owns exactly one SQLite connection to `path`. Constructing this
    creates the schema if absent -- construction-time schema creation, not
    a capability invocation, mirrors `SQLiteConfigurationStore`'s own
    established Gate-1 pattern."""

    def __init__(self, path: str | Path) -> None:
        self._path = str(path)
        try:
            self._connection = sqlite3.connect(self._path)
            self._connection.execute(_SCHEMA)
            self._connection.commit()
        except sqlite3.DatabaseError as exc:
            raise RetrievalStoreError(
                f"could not open or initialize retrieval store at {path!r}: {exc}"
            ) from exc

    def close(self) -> None:
        self._connection.close()

    def index_chunk(self, chunk: IndexedChunk) -> None:
        """Idempotent: re-indexing the exact same
        `(tenant_id, document_id, chunk_index)` replaces the prior row."""
        try:
            self._connection.execute(
                "INSERT OR REPLACE INTO chunks "
                "(tenant_id, document_id, chunk_index, text, embedding) "
                "VALUES (?, ?, ?, ?, ?)",
                (
                    chunk.tenant_id,
                    chunk.document_id,
                    chunk.chunk_index,
                    chunk.text,
                    json.dumps(chunk.embedding),
                ),
            )
            self._connection.commit()
        except sqlite3.DatabaseError as exc:
            raise RetrievalStoreError(f"could not index chunk: {exc}") from exc

    def delete_document(self, tenant_id: str, document_id: str) -> None:
        """Remove every chunk for one document -- used before re-ingesting a
        document whose new chunk count is smaller than its previous one, so
        stale trailing chunks from the earlier ingestion cannot linger."""
        try:
            self._connection.execute(
                "DELETE FROM chunks WHERE tenant_id = ? AND document_id = ?",
                (tenant_id, document_id),
            )
            self._connection.commit()
        except sqlite3.DatabaseError as exc:
            raise RetrievalStoreError(
                f"could not delete document chunks: {exc}"
            ) from exc

    def _scoped_rows(
        self, scope: RetrievalScope
    ) -> list[tuple[str, int, str, list[float]]]:
        try:
            if scope.document_ids is None:
                cursor = self._connection.execute(
                    "SELECT document_id, chunk_index, text, embedding FROM chunks "
                    "WHERE tenant_id = ?",
                    (scope.tenant_id,),
                )
            else:
                placeholders = ",".join("?" for _ in scope.document_ids)
                cursor = self._connection.execute(
                    "SELECT document_id, chunk_index, text, embedding FROM chunks "
                    f"WHERE tenant_id = ? AND document_id IN ({placeholders})",
                    (scope.tenant_id, *scope.document_ids),
                )
            return [
                (document_id, chunk_index, text, json.loads(embedding))
                for document_id, chunk_index, text, embedding in cursor.fetchall()
            ]
        except sqlite3.DatabaseError as exc:
            raise RetrievalStoreError(f"could not read retrieval store: {exc}") from exc

    def search_vector(
        self, scope: RetrievalScope, embedding: tuple[float, ...], top_k: int
    ) -> list[tuple[str, int, str, float]]:
        """Brute-force cosine similarity, scoped, sorted descending,
        truncated to `top_k`. Returns `(document_id, chunk_index, text, score)`."""
        rows = self._scoped_rows(scope)
        scored = [
            (document_id, chunk_index, text, _cosine_similarity(embedding, vector))
            for document_id, chunk_index, text, vector in rows
        ]
        scored.sort(key=lambda row: row[3], reverse=True)
        return scored[:top_k]

    def search_text(
        self, scope: RetrievalScope, query_text: str, top_k: int
    ) -> list[tuple[str, int, str, float]]:
        """Deterministic lexical word-overlap score, scoped, sorted
        descending, truncated to `top_k`. See
        `legoai_document.retrieval.api`'s module docstring for the exact
        scoring rule."""
        rows = self._scoped_rows(scope)
        query_words = _words(query_text)
        scored = [
            (document_id, chunk_index, text, _lexical_overlap_score(query_words, text))
            for document_id, chunk_index, text, _vector in rows
        ]
        scored = [row for row in scored if row[3] > 0.0]
        scored.sort(key=lambda row: row[3], reverse=True)
        return scored[:top_k]


def _words(text: str) -> frozenset[str]:
    return frozenset(word for word in text.lower().split() if word)


def _lexical_overlap_score(query_words: frozenset[str], text: str) -> float:
    """`|query_words ∩ chunk_words| / |query_words|` -- a deliberately
    simple, deterministic overlap ratio, not a production-grade BM25/TF-IDF
    implementation (task SS22: document the rule, do not overclaim
    quality)."""
    if not query_words:
        return 0.0
    chunk_words = _words(text)
    return len(query_words & chunk_words) / len(query_words)


def _cosine_similarity(a: tuple[float, ...], b: list[float]) -> float:
    if len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)
