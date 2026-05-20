# RAG Data Layout

This directory is the local development workspace for Step 3 advanced RAG.

The repository tracks only small manifests and documentation. Raw corpora, chunks, indexes, and embeddings are intentionally ignored because they can grow large and may contain user-provided issue text.

## Local development layout

```text
data/rag/
  README.md                 tracked
  corpus_manifest.json       tracked, small evidence only
  raw/                       ignored local raw corpus files
  chunks/                    ignored local chunk files; small chunk manifests tracked
  indexes/                   ignored local BM25/vector/rerank scratch files
```

## Final architecture

The local folders are a temporary development surface. The production-shaped flow should become:

```text
pandas docs + resolved issues
        ↓
raw source snapshots in MinIO
        ↓
chunking pipeline
        ↓
parent/child chunks + metadata
        ↓
PostgreSQL/pgvector for dense vectors and metadata
        ↓
BM25 + dense hybrid retrieval
        ↓
cross-encoder reranking
        ↓
RAG answer with citations
```

## Dev corpus

Build a small ignored dev corpus from already-local files:

```bash
python -m scripts.rag.build_dev_corpus
```

Default outputs:

```text
data/rag/raw/dev_corpus.jsonl
 data/rag/corpus_manifest.json
```

The dev corpus currently uses:

- local project Markdown docs from `docs/*.md`
- held-out issue records from `data/test_200_balanced.jsonl` if that ignored file is present locally

The full RAG corpus later needs resolved issues with maintainer answers/comments; this first dev corpus is only for building and testing the pipeline shape without requiring a large download.

## Baseline retrieval

Build naive fixed-size chunks:

```bash
python -m scripts.rag.chunk_corpus
```

Run the baseline dense-only evaluator:

```bash
python -m scripts.rag.evaluate_retrieval
```

Tracked baseline evidence:

```text
data/rag/chunks/naive_fixed_chunks_manifest.json
evals/rag_naive_dense_baseline_results.json
```

The generated chunk rows stay ignored:

```text
data/rag/chunks/naive_fixed_chunks.jsonl
```

## Parent-child chunking

Build non-naive parent-child chunks:

```bash
python -m scripts.rag.chunk_parent_child
```

Evaluate them with the same dense-only evaluator:

```bash
python -m scripts.rag.evaluate_retrieval \
  --chunks-path data/rag/chunks/parent_child_chunks.jsonl \
  --output-path evals/rag_parent_child_dense_results.json
```

Tracked evidence:

```text
data/rag/chunks/parent_child_chunks_manifest.json
evals/rag_parent_child_dense_results.json
```

## BM25 + hybrid tuning

Evaluate sparse BM25, dense, and hybrid sparse+dense weights over the parent-child chunks:

```bash
python -m scripts.rag.evaluate_hybrid_retrieval
```

Tracked evidence:

```text
evals/rag_hybrid_tuning_results.json
```

The tuning output records both `best_overall` and `best_hybrid`. On the current dev corpus, pure BM25 is strongest overall, while the best true hybrid uses dense weight `0.25` and sparse weight `0.75`.
