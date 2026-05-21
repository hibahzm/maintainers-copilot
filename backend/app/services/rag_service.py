"""RAG query service backed by model-server embeddings and pgvector retrieval."""

from typing import Any

import httpx

from app.api.schemas.rag import RagQueryResponse, RagRetrievedChunk
from app.domain.rag import RetrievedChunk
from app.infra.exceptions import ToolFailure
from app.infra.tracing import trace_event, trace_span
from app.repositories.rag_repo import RagRepository


class RagService:
    """Embed a user query, retrieve chunks from pgvector, and optionally answer.

    Retrieval is the primary contract. If LLM answer generation is unavailable
    because a key is missing or the provider is down, the service still returns
    grounded chunks/citations for the caller.
    """

    def __init__(
        self,
        *,
        model_server_url: str,
        database_url: str,
        repository: RagRepository | None = None,
        timeout_seconds: float = 20.0,
    ) -> None:
        self.model_server_url = model_server_url.rstrip("/")
        self.repository = repository or RagRepository(database_url=database_url)
        self.timeout_seconds = timeout_seconds

    async def query(
        self,
        *,
        question: str,
        top_k: int,
        source_type: str | None = None,
        generate_answer: bool = True,
    ) -> RagQueryResponse:
        with trace_span(
            "rag.query",
            top_k=top_k,
            source_type=source_type or "any",
            generate_answer=generate_answer,
            question_chars=len(question),
        ):
            embedding_payload = await self._embed_query(question)
            embedding = embedding_payload["embedding"]
            embedding_model = embedding_payload["model_name"]
            with trace_span("rag.retrieve", top_k=top_k, embedding_model=embedding_model):
                chunks = await self.repository.search_hybrid(
                    query_text=question,
                    query_embedding=embedding,
                    embedding_model=embedding_model,
                    top_k=top_k,
                    source_type=source_type,
                )
            citations = self._citations(chunks)
            trace_event("rag.retrieved", chunks=len(chunks), citations=len(citations))
            answer_payload = (
                await self._generate_answer(question=question, chunks=chunks)
                if generate_answer and chunks
                else None
            )
            return RagQueryResponse(
                answer=answer_payload["answer"] if answer_payload else self._retrieval_answer(chunks),
                citations=answer_payload["citations"] if answer_payload else citations,
                chunks=[self._chunk_schema(chunk) for chunk in chunks],
                retrieval_mode="pgvector_hybrid_dense_sparse_e5",
                embedding_model=embedding_model,
                answer_provider=answer_payload["provider"] if answer_payload else "retrieval-only",
                answer_model=answer_payload.get("model_name") if answer_payload else None,
                answer_response_id=answer_payload.get("response_id") if answer_payload else None,
            )

    async def _embed_query(self, question: str) -> dict[str, Any]:
        with trace_span("rag.embed", question_chars=len(question)):
            try:
                async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                    response = await client.post(
                        f"{self.model_server_url}/embed",
                        json={"texts": [question], "input_type": "query"},
                    )
                    response.raise_for_status()
            except httpx.HTTPError as exc:
                raise ToolFailure("Embedding model server request failed.") from exc

        data = response.json()
        embeddings = data.get("embeddings") or []
        if len(embeddings) != 1:
            raise ToolFailure("Embedding model server returned an invalid embedding payload.")
        return {"embedding": embeddings[0], "model_name": data.get("model_name")}

    async def _generate_answer(self, *, question: str, chunks: list[RetrievedChunk]) -> dict[str, Any] | None:
        payload = {
            "question": question,
            "chunks": [
                {
                    "source_id": chunk.source_id,
                    "title": chunk.title,
                    "parent_title": chunk.parent_title,
                    "text": chunk.text,
                    "score": chunk.score,
                }
                for chunk in chunks[:5]
            ],
        }
        with trace_span("rag.answer", chunks=len(chunks[:5]), question_chars=len(question)):
            try:
                async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                    response = await client.post(f"{self.model_server_url}/rag-answer", json=payload)
                    response.raise_for_status()
            except httpx.HTTPError:
                trace_event("rag.answer.skipped", reason="model_server_error")
                return None
        data: dict[str, Any] = response.json()
        return data

    def _retrieval_answer(self, chunks: list[RetrievedChunk]) -> str:
        if not chunks:
            return "I could not find matching project context yet."
        return "I found relevant project context. Use the returned citations/chunks for the grounded answer."

    def _citations(self, chunks: list[RetrievedChunk]) -> list[str]:
        citations: list[str] = []
        for chunk in chunks:
            if chunk.source_id not in citations:
                citations.append(chunk.source_id)
        return citations

    def _chunk_schema(self, chunk: RetrievedChunk) -> RagRetrievedChunk:
        return RagRetrievedChunk(
            chunk_id=chunk.chunk_id,
            source_id=chunk.source_id,
            title=chunk.title,
            parent_title=chunk.parent_title,
            source_type=chunk.source_type,
            score=chunk.score,
            dense_score=chunk.dense_score,
            sparse_score=chunk.sparse_score,
            text_preview=chunk.text[:500],
            metadata=chunk.metadata,
        )
