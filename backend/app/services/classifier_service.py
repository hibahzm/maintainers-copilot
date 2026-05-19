"""Backend service for proxying issue classification to the model server."""

from typing import Any

import httpx

from app.api.schemas.classifier import ClassifyIssueResponse
from app.infra.exceptions import ToolFailure


class ClassifierService:
    """Call the model server and normalize classification responses."""

    def __init__(self, model_server_url: str, timeout_seconds: float = 10.0) -> None:
        self.model_server_url = model_server_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    async def classify_issue(self, *, title: str, body: str) -> ClassifyIssueResponse:
        payload = {"title": title, "body": body}
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(f"{self.model_server_url}/classify", json=payload)
                response.raise_for_status()
        except httpx.HTTPError as exc:
            raise ToolFailure("Classifier model server request failed.") from exc

        data: dict[str, Any] = response.json()
        return ClassifyIssueResponse.model_validate(data)
