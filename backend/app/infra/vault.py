"""Vault client and startup secret-loading helpers."""

from collections.abc import Mapping
from typing import Any

import httpx
from pydantic import ValidationError

from app.core.config import RuntimeSecrets, Settings


class VaultStartupError(RuntimeError):
    """Raised when startup cannot safely continue because Vault is unavailable or incomplete."""


class VaultClient:
    """Small async Vault adapter for startup-time secret resolution."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = httpx.AsyncClient(
            base_url=settings.vault_addr.rstrip("/"),
            headers={"X-Vault-Token": settings.vault_token.get_secret_value()},
            timeout=5.0,
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    async def assert_reachable(self) -> None:
        try:
            response = await self._client.get("/v1/sys/health")
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise VaultStartupError("Vault is unreachable during API startup.") from exc

    async def load_runtime_secrets(self) -> RuntimeSecrets:
        """Load the required application secret bundle from a KV v2 mount."""
        path = (
            f"/v1/{self._settings.vault_mount_point}/data/"
            f"{self._settings.vault_secret_path}"
        )

        try:
            response = await self._client.get(path)
            response.raise_for_status()
            payload = response.json()
        except httpx.HTTPError as exc:
            raise VaultStartupError("Vault secret bundle could not be loaded.") from exc
        except ValueError as exc:
            raise VaultStartupError("Vault returned an invalid JSON response.") from exc

        secret_data = _extract_kv_v2_data(payload)

        try:
            return RuntimeSecrets.model_validate(secret_data)
        except ValidationError as exc:
            raise VaultStartupError(
                "Vault secret bundle is missing one or more required runtime secrets."
            ) from exc


def _extract_kv_v2_data(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    """Return the nested secret dictionary from Vault's KV v2 response shape."""
    try:
        data = payload["data"]["data"]
    except (KeyError, TypeError) as exc:
        raise VaultStartupError("Vault returned an unexpected KV v2 response shape.") from exc

    if not isinstance(data, Mapping):
        raise VaultStartupError("Vault returned a non-object secret payload.")

    return data
