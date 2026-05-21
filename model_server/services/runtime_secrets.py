"""Runtime secret helpers for model-server endpoints.

Environment variables still win for notebooks and one-off local experiments.
Docker/local-stack runtime can fetch the same values from Vault after vault-init
has seeded the development KV bundle.
"""

from __future__ import annotations

import json
import os
from functools import lru_cache
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


@lru_cache(maxsize=16)
def runtime_secret_value(key: str) -> str | None:
    vault_addr = os.getenv("VAULT_ADDR")
    vault_token = os.getenv("VAULT_TOKEN") or os.getenv("VAULT_DEV_ROOT_TOKEN_ID")
    mount_point = os.getenv("VAULT_MOUNT_POINT", "secret")
    secret_path = os.getenv("VAULT_SECRET_PATH", "maintainers-copilot")
    if not vault_addr or not vault_token:
        return None

    url = f"{vault_addr.rstrip('/')}/v1/{mount_point}/data/{secret_path}"
    request = Request(url, headers={"X-Vault-Token": vault_token}, method="GET")
    try:
        with urlopen(request, timeout=5) as response:
            payload = json.load(response)
    except (HTTPError, URLError, TimeoutError, ValueError):
        return None

    value = payload.get("data", {}).get("data", {}).get(key)
    if not isinstance(value, str) or not value:
        return None
    return value
