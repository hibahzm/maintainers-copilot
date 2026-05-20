from app.domain.rag import RetrievedChunk
from app.repositories.rag_repo import merge_hybrid_candidates


def chunk(chunk_id: str, *, dense: float = 0.0, sparse: float = 0.0) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=chunk_id,
        source_id=f"source:{chunk_id}",
        title="title",
        parent_title=None,
        text="text",
        source_type="project_doc",
        score=max(dense, sparse),
        dense_score=dense,
        sparse_score=sparse,
    )


def test_merge_hybrid_candidates_prefers_tuned_sparse_weight():
    dense = [chunk("a", dense=0.9), chunk("b", dense=0.2)]
    sparse = [chunk("b", sparse=1.0), chunk("a", sparse=0.1)]

    results = merge_hybrid_candidates(
        dense_candidates=dense,
        sparse_candidates=sparse,
        top_k=2,
        dense_weight=0.25,
    )

    assert [result.chunk_id for result in results] == ["b", "a"]
    assert results[0].sparse_score == 1.0
    assert results[0].dense_score == 0.2
