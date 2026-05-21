"""Upload project blob artifacts into MinIO.

This script makes the assignment's blob-storage contract explicit:
- classifier model evidence/manifest goes to the artifacts bucket
- eval reports go to the evals bucket
- RAG raw corpus + parent/child chunk files go to the rag bucket
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from minio import Minio
from minio.error import S3Error


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--endpoint", default=os.getenv("MINIO_ENDPOINT", "localhost:9000"))
    parser.add_argument("--access-key", default=os.getenv("MINIO_ACCESS_KEY", "minioadmin"))
    parser.add_argument("--secret-key", default=os.getenv("MINIO_SECRET_KEY", "minioadmin-dev-only"))
    parser.add_argument("--secure", action="store_true")
    parser.add_argument("--artifacts-bucket", default=os.getenv("MINIO_ARTIFACT_BUCKET", "artifacts"))
    parser.add_argument("--evals-bucket", default=os.getenv("MINIO_EVAL_BUCKET", "evals"))
    parser.add_argument("--rag-bucket", default=os.getenv("MINIO_RAG_BUCKET", "rag"))
    return parser.parse_args()


def ensure_bucket(client: Minio, bucket: str) -> None:
    if not client.bucket_exists(bucket):
        client.make_bucket(bucket)


def upload_file(client: Minio, *, bucket: str, object_name: str, path: Path) -> str:
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"Missing required blob source: {path}")
    client.fput_object(bucket, object_name, str(path))
    return f"s3://{bucket}/{object_name}"


def upload_optional_files(client: Minio, *, bucket: str, prefix: str, paths: list[Path]) -> list[str]:
    uploaded: list[str] = []
    for path in paths:
        if path.exists() and path.is_file():
            uploaded.append(upload_file(client, bucket=bucket, object_name=f"{prefix}/{path.name}", path=path))
    return uploaded


def main() -> None:
    args = parse_args()
    client = Minio(
        args.endpoint,
        access_key=args.access_key,
        secret_key=args.secret_key,
        secure=args.secure,
    )
    for bucket in (args.artifacts_bucket, args.evals_bucket, args.rag_bucket):
        ensure_bucket(client, bucket)

    uploaded: dict[str, list[str]] = {"artifacts": [], "evals": [], "rag": []}
    run_dir = Path("model_server/classifier/runs/first-distilbert-freeze4")
    uploaded["artifacts"].extend(
        upload_optional_files(
            client,
            bucket=args.artifacts_bucket,
            prefix="classifier/first-distilbert-freeze4",
            paths=[
                Path("model_server/classifier/model_card.md"),
                run_dir / "model_artifact_fingerprint.json",
                run_dir / "run_manifest.json",
                run_dir / "metrics.json",
                run_dir / "test_metrics.json",
                run_dir / "classification_report.json",
            ],
        )
    )

    eval_paths = sorted(Path("evals").glob("*.json")) + sorted(Path("evals").glob("*.yaml"))
    uploaded["evals"].extend(
        upload_optional_files(
            client,
            bucket=args.evals_bucket,
            prefix="ci/latest",
            paths=eval_paths,
        )
    )

    uploaded["rag"].extend(
        upload_optional_files(
            client,
            bucket=args.rag_bucket,
            prefix="dev-corpus",
            paths=[
                Path("data/rag/raw/dev_corpus.jsonl"),
                Path("data/rag/corpus_manifest.json"),
                Path("data/rag/dev_issue_sources.json"),
                Path("data/rag/chunks/parent_child_chunks.jsonl"),
                Path("data/rag/chunks/parent_child_chunks_manifest.json"),
            ],
        )
    )

    print(json.dumps(uploaded, indent=2, sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except S3Error as exc:
        raise SystemExit(f"MinIO upload failed: {exc}") from exc
