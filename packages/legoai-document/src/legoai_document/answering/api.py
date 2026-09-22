"""document.answering v1 -- direct governed answering with citations.

    question
      -> embed query (governed model.embedding)
      -> retrieve (document.retrieval, local, no Model call)
      -> rerank (document.rerank; identity/truncation by default)
      -> build a bounded context
      -> chat (governed model.chat)
      -> answer + citations

No Agent (task SS29/SS50 -- `DOCUMIND-EXTRACTION-ASSESSMENT.md` SS16.5
already established this: SK's own evidence proves a direct capability
invocation is sufficient; MAF's "Agent" wrapper around the identical logic
is not evidence that one is required). This is a plain async function
composing already-independent capabilities, exactly like
`legoai_document.ingestion`.

**No supporting context is an explicitly declared outcome, not a silent
fallback (task SS25):** if retrieval finds nothing in scope, this function
returns a fixed, deterministic "no supporting context" answer with zero
citations and never calls the chat model at all -- avoiding both a wasted
governed invocation and any risk of an ungrounded answer.

**Context bounding (task SS32):** a plain character-count budget, not real
LLM tokenization (no tokenizer dependency is added for v0.1) -- an
explicitly documented deterministic approximation. At least the top-ranked
candidate is always included even if it alone exceeds the budget; nothing
beyond it is added once the budget is exceeded.

**Prompting (task SS33):** one small, stable system instruction. No prompt
framework, no few-shot library.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from legoai.intelligence.model.values import (
    ChatMessage,
    ChatRequest,
    ChatResult,
    ChatRole,
    EmbeddingRequest,
)

from legoai_document.answering.values import (
    AnsweringRequest,
    AnsweringResult,
    AnswerProvenance,
    Citation,
)
from legoai_document.embedding.api import GovernedEmbed
from legoai_document.rerank.api import Reranker, identity_rerank
from legoai_document.rerank.values import (
    RerankCandidate,
    RerankedCandidate,
    RerankRequest,
)
from legoai_document.retrieval.api import hybrid_search
from legoai_document.retrieval.store import SQLiteRetrievalStore
from legoai_document.retrieval.values import RetrievalQuery, RetrievalScope

GovernedChat = Callable[[ChatRequest], Awaitable[ChatResult]]

_SYSTEM_PROMPT = (
    "You are a careful assistant that answers strictly from the provided "
    "context. If the context does not contain enough information to "
    "answer the question, say so explicitly instead of guessing. When you "
    "use information from a context block, cite it using its exact [n] "
    "marker."
)

_NO_CONTEXT_ANSWER = "No supporting context was found for this question."


async def answer_question(
    request: AnsweringRequest,
    store: SQLiteRetrievalStore,
    governed_embed: GovernedEmbed,
    governed_chat: GovernedChat,
    reranker: Reranker = identity_rerank,
) -> AnsweringResult:
    embedding_result = await governed_embed(EmbeddingRequest((request.question,)))
    query_embedding = embedding_result.vectors[0]

    retrieval_result = hybrid_search(
        store,
        RetrievalQuery(
            RetrievalScope(request.tenant_id),
            request.question,
            query_embedding,
            top_k=request.top_k,
        ),
    )

    if not retrieval_result.candidates:
        return AnsweringResult(
            _NO_CONTEXT_ANSWER,
            (),
            AnswerProvenance(
                embedding_result.model_identity.value,
                embedding_result.provider_identity.value,
                "none",
                0,
            ),
        )

    rerank_request = RerankRequest(
        request.question,
        tuple(
            RerankCandidate(c.document_id, c.chunk_index, c.text, c.score)
            for c in retrieval_result.candidates
        ),
        top_n=request.rerank_top_n,
    )
    rerank_result = reranker(rerank_request)

    citations = _build_citations(
        rerank_result.candidates, request.max_context_characters
    )

    if not citations:
        return AnsweringResult(
            _NO_CONTEXT_ANSWER,
            (),
            AnswerProvenance(
                embedding_result.model_identity.value,
                embedding_result.provider_identity.value,
                rerank_result.reranker,
                len(retrieval_result.candidates),
            ),
        )

    context_text = "\n\n".join(
        f"[{citation.index}] {citation.text}" for citation in citations
    )
    chat_request = ChatRequest(
        (
            ChatMessage(ChatRole.SYSTEM, _SYSTEM_PROMPT),
            ChatMessage(
                ChatRole.USER,
                f"Context:\n{context_text}\n\nQuestion: {request.question}",
            ),
        )
    )
    chat_result = await governed_chat(chat_request)

    return AnsweringResult(
        chat_result.content,
        citations,
        AnswerProvenance(
            chat_result.model_identity.value,
            chat_result.provider_identity.value,
            rerank_result.reranker,
            len(retrieval_result.candidates),
        ),
    )


def _build_citations(
    candidates: tuple[RerankedCandidate, ...], max_characters: int
) -> tuple[Citation, ...]:
    citations: list[Citation] = []
    used = 0
    for index, candidate in enumerate(candidates, start=1):
        block_length = len(candidate.text) + len(f"[{index}] ")
        if citations and used + block_length > max_characters:
            break
        citations.append(
            Citation(
                index, candidate.document_id, candidate.chunk_index, candidate.text
            )
        )
        used += block_length
    return tuple(citations)
