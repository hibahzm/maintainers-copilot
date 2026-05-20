# RAG Data Layout

This directory is the local development workspace for Step 3 advanced RAG.

The repository tracks only small manifests and documentation. Raw corpora, chunks, indexes, and embeddings are intentionally ignored because they can grow large and may contain user-provided issue text.

## Local development layout

```text
data/rag/
  README.md                 tracked
  corpus_manifest.json       tracked, small evidence only
  dev_issue_sources.json      tracked public issue IDs for reproducible dev-corpus rebuilds
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
- otherwise, public GitHub issue records fetched from tracked IDs in `data/rag/dev_issue_sources.json`

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


## Embedding model comparison

Compare at least two dense embedding candidates on the same parent-child chunks and RAG golden set:

```bash
pip install -q sentence-transformers

python -m scripts.rag.evaluate_embedding_models \
  --chunks-path data/rag/chunks/parent_child_chunks.jsonl \
  --golden-path evals/golden_rag.json \
  --output-path evals/rag_embedding_model_comparison_results.json \
  --embedding-models sentence-transformers/all-MiniLM-L6-v2 intfloat/e5-small-v2 \
  --device auto \
  --batch-size 64 \
  --no-metadata-filter
```

Bring this file back into the repo after Colab finishes:

```text
evals/rag_embedding_model_comparison_results.json
```

The comparison is dense-only cosine retrieval with metadata filters disabled so the embedding choice is measured directly, not hidden by BM25 or label filters. If the corpus is missing any golden-set source IDs, the evaluator fails instead of writing misleading metrics. A lightweight helper notebook is available at `notebooks/rag_embedding_model_comparison_colab.ipynb`.

Committed result: `intfloat/e5-small-v2` is the selected first RAG embedding model with recall@10 `1.0000`, MRR@10 `1.0000`, and nDCG@10 `0.9636`, beating `all-MiniLM-L6-v2` on ranking quality.


## pgvector indexing

After the database migration runs, index the generated parent-child chunks into PostgreSQL/pgvector with the selected embedding model:

```bash
scripts/rag/ingest_pgvector.sh
```

The ingest wrapper uses `uv`, CPU-only PyTorch wheels, `sentence-transformers`, and `asyncpg` without adding those heavy packages to the committed service dependencies. Override defaults with environment variables if needed:

```bash
DEVICE=cpu BATCH_SIZE=32 DATABASE_URL=postgresql://copilot:copilot-dev-only@localhost:5432/copilot \
  scripts/rag/ingest_pgvector.sh
```

Smoke-test dense pgvector search:

```bash
python -m scripts.rag.query_pgvector \
  "What model was selected for issue classification and why?" \
  --database-url postgresql://copilot:copilot-dev-only@localhost:5432/copilot \
  --top-k 5
```

The indexing script writes `rag_sources` and `rag_chunks`; it does not commit raw chunk rows or embeddings to Git. Query-time embeddings use the E5 `query:` prefix, while stored chunk embeddings use the E5 `passage:` prefix.

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

## Metadata filtering

Evaluate the same hybrid grid with golden-set metadata filters enabled:

```bash
python -m scripts.rag.evaluate_hybrid_retrieval \
  --use-metadata-filter \
  --output-path evals/rag_hybrid_metadata_filter_results.json
```

Tracked evidence:

```text
evals/rag_hybrid_metadata_filter_results.json
```

On the current dev corpus, reliable metadata filters are neutral versus the unfiltered tuned hybrid: they preserve recall@10 `1.0000` and MRR@10 `0.9533` for the best true hybrid.

## Query transformation

Evaluate deterministic issue-query expansion on top of the tuned parent-child hybrid retriever:

```bash
python -m scripts.rag.evaluate_query_transform

python -m scripts.rag.evaluate_query_transform \
  --no-metadata-filter \
  --output-path evals/rag_query_transform_unfiltered_results.json
```

Tracked evidence:

```text
evals/rag_query_transform_results.json
evals/rag_query_transform_unfiltered_results.json
```

The transform expands maintainer-shaped queries with issue numbers, code symbols, project-service terms, and common pandas API terms. On the current dev corpus, it changes 17 of 25 golden queries and preserves recall@10 `1.0000`, but its MRR@10 `0.9400` is slightly below the untransformed best hybrid MRR@10 `0.9533`. Treat this as an optional/gated query rewrite, not the default path.

## Cross-encoder reranking

The cross-encoder is an experiment dependency, not a model-server dependency. Run it in Colab or another experiment runtime after the parent-child chunks exist:

```bash
pip install -q torch transformers

python -m scripts.rag.evaluate_cross_encoder_rerank \
  --chunks-path data/rag/chunks/parent_child_chunks.jsonl \
  --golden-path evals/golden_rag.json \
  --output-path evals/rag_cross_encoder_rerank_results.json \
  --reranker-model cross-encoder/ms-marco-MiniLM-L-6-v2 \
  --candidate-k 25 \
  --top-k 10
```

Bring this file back into the repo after Colab finishes:

```text
evals/rag_cross_encoder_rerank_results.json
```

The script reranks the top 25 candidates from the tuned hybrid retriever using a true query-document cross-encoder, then reports the same recall@k, MRR@10, and nDCG@10 metrics as the earlier retrieval experiments. The committed Colab result uses `cross-encoder/ms-marco-MiniLM-L-6-v2` and reaches recall@10 `1.0000`, MRR@10 `0.9533`, and nDCG@10 `0.9471`.

A lightweight helper notebook is also available at `notebooks/rag_cross_encoder_rerank_colab.ipynb`.

