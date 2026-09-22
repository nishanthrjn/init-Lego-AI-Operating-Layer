"""DocuMind application layer: binds `DocuMindRuntime`'s governed
`governed_embed`/`governed_chat` callables to `legoai_document`'s
`ingest_document`/`answer_question` compositions, and maps a file path's
extension to `DocumentFormat` (task's own "app-specific code never inside
Core/Document Pack" boundary -- this mapping is DocuMind-CLI-specific, not
a general document-parsing concern)."""

from __future__ import annotations

from pathlib import Path

from legoai_document.answering.api import answer_question
from legoai_document.answering.values import AnsweringRequest, AnsweringResult
from legoai_document.ingestion.api import ingest_document
from legoai_document.ingestion.values import IngestionRequest, IngestionResult
from legoai_document.parsing.values import DocumentFormat
from legoai_document.retrieval.store import SQLiteRetrievalStore

from documind_app.composition import DocuMindRuntime

_EXTENSION_FORMATS: dict[str, DocumentFormat] = {
    ".txt": DocumentFormat.TEXT,
    ".text": DocumentFormat.TEXT,
    ".md": DocumentFormat.MARKDOWN,
    ".markdown": DocumentFormat.MARKDOWN,
    ".html": DocumentFormat.HTML,
    ".htm": DocumentFormat.HTML,
    ".pdf": DocumentFormat.PDF,
}


class UnrecognizedFileExtensionError(ValueError):
    """A file's extension does not map to any supported `DocumentFormat`."""


def format_for_path(path: Path) -> DocumentFormat:
    document_format = _EXTENSION_FORMATS.get(path.suffix.lower())
    if document_format is None:
        supported = ", ".join(sorted(_EXTENSION_FORMATS))
        raise UnrecognizedFileExtensionError(
            f"{path.name!r} has an unsupported extension {path.suffix!r} "
            f"(supported: {supported})"
        )
    return document_format


class DocuMindApplication:
    """One process-lifetime application instance: one governed runtime plus
    one local retrieval store."""

    def __init__(self, runtime: DocuMindRuntime) -> None:
        self.runtime = runtime
        self.runtime.config.index_path.parent.mkdir(parents=True, exist_ok=True)
        self.store = SQLiteRetrievalStore(runtime.config.index_path)

    async def ingest_path(self, path: Path) -> IngestionResult:
        document_format = format_for_path(path)
        content = path.read_bytes()
        request = IngestionRequest(
            self.runtime.config.tenant_id, str(path), content, document_format
        )
        return await ingest_document(request, self.runtime.governed_embed, self.store)

    async def ask(self, question: str) -> AnsweringResult:
        request = AnsweringRequest(self.runtime.config.tenant_id, question)
        return await answer_question(
            request, self.store, self.runtime.governed_embed, self.runtime.governed_chat
        )
