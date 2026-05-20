"""RAG query service backed by model-server embeddings and pgvector retrieval."""

from typing import Any

import httpx

from app.api.schemas.rag import RagQueryResponse, RagRetrievedChunk
from app.domain.rag import RetrievedChunk
from app.infra.exceptions import ToolFailure
from app.repositories.rag_repo import RagRepository


class RagService:
    """Embed a user query, retrieve chunks from pgvector, and shape citations.

    Answer generation with an LLM is intentionally the next layer; this service
    currently returns retrieval-grounded context so the pgvector path can be
    tested before adding another model call.
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
    ) -> RagQueryResponse:
        embedding_payload = await self._embed_query(question)
        embedding = embedding_payload["embedding"]
        embedding_model = embedding_payload["model_name"]
        chunks = await self.repository.search_hybrid(
            query_text=question,
            query_embedding=embedding,
            embedding_model=embedding_model,
            top_k=top_k,
            source_type=source_type,
        )
        citations = self._citations(chunks)
        return RagQueryResponse(
            answer=self._retrieval_answer(chunks),
            citations=citations,
            chunks=[self._chunk_schema(chunk) for chunk in chunks],
            retrieval_mode="pgvector_hybrid_dense_sparse_e5",
            embedding_model=embedding_model,
        )

    async def _embed_query(self, question: str) -> dict[str, Any]:
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
