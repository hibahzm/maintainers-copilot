"""Backend service for maintainer NLP tools hosted by the model server."""

from typing import Any

import httpx

from app.api.schemas.classifier import ClassifyIssueResponse
from app.infra.exceptions import ToolFailure


class MaintainerToolsService:
    """Proxy cheap/local and LLM-backed NLP tools through the model server."""

    def __init__(self, model_server_url: str, timeout_seconds: float = 30.0) -> None:
        self.model_server_url = model_server_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    async def classify_issue(self, *, title: str, body: str) -> ClassifyIssueResponse:
        data = await self._post("/classify", {"title": title, "body": body})
        return ClassifyIssueResponse.model_validate(data)

    async def extract_entities(self, *, title: str, body: str, text: str | None = None) -> dict[str, Any]:
        return await self._post("/ner", {"title": title, "body": body, "text": text})

    async def summarize_issue(self, *, title: str, body: str, text: str | None = None) -> dict[str, Any]:
        return await self._post("/summarize", {"title": title, "body": body, "text": text})

    async def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(f"{self.model_server_url}{path}", json=payload)
                response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            detail = exc.response.text if exc.response is not None else ""
            raise ToolFailure(f"Model server tool {path} failed: {detail}") from exc
        except httpx.HTTPError as exc:
            raise ToolFailure(f"Model server tool {path} request failed.") from exc

        data: dict[str, Any] = response.json()
        return data
