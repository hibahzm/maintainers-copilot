"""MinIO blob storage helpers."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from io import BytesIO
from typing import Any

from minio import Minio
from minio.error import S3Error
from pydantic import SecretStr

from app.infra.exceptions import ToolFailure


class MinioBlobStore:
    """Small adapter for project blob storage responsibilities."""

    def __init__(
        self,
        *,
        endpoint: str,
        access_key: SecretStr,
        secret_key: SecretStr,
        secure: bool,
    ) -> None:
        self.client = Minio(
            endpoint,
            access_key=access_key.get_secret_value(),
            secret_key=secret_key.get_secret_value(),
            secure=secure,
        )

    def ensure_bucket(self, bucket: str) -> None:
        try:
            if not self.client.bucket_exists(bucket):
                self.client.make_bucket(bucket)
        except S3Error as exc:
            raise ToolFailure(f"MinIO bucket check failed for {bucket}.") from exc

    def put_json(self, *, bucket: str, object_name: str, payload: dict[str, Any]) -> str:
        self.ensure_bucket(bucket)
        body = json.dumps(payload, indent=2, sort_keys=True, default=str).encode("utf-8")
        try:
            self.client.put_object(
                bucket,
                object_name,
                BytesIO(body),
                length=len(body),
                content_type="application/json",
            )
        except S3Error as exc:
            raise ToolFailure(f"MinIO JSON upload failed for {bucket}/{object_name}.") from exc
        return f"s3://{bucket}/{object_name}"

    def prune_prefix(self, *, bucket: str, prefix: str, keep: int) -> None:
        if keep <= 0:
            return
        self.ensure_bucket(bucket)
        try:
            objects = sorted(
                self.client.list_objects(bucket, prefix=prefix, recursive=True),
                key=lambda item: item.last_modified or datetime.now(UTC),
                reverse=True,
            )
            for old_object in objects[keep:]:
                self.client.remove_object(bucket, old_object.object_name)
        except S3Error as exc:
            raise ToolFailure(f"MinIO prune failed for {bucket}/{prefix}.") from exc
