from pydantic import BaseModel, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Maintainers Copilot API"
    vault_addr: str = "http://localhost:8200"
    vault_token: SecretStr = Field(
        default=SecretStr("dev-only-root-token"),
        validation_alias="VAULT_DEV_ROOT_TOKEN_ID",
    )
    vault_mount_point: str = "secret"
    vault_secret_path: str = "maintainers-copilot"
    model_server_url: str = "http://localhost:8001"
    tracing_backend: str = "langfuse"
    tracing_host: str = "https://cloud.langfuse.com"


class RuntimeSecrets(BaseModel):
    """Secrets that must be loaded from Vault before the API can serve traffic."""

    database_password: SecretStr
    jwt_signing_key: SecretStr
    minio_access_key: SecretStr
    minio_secret_key: SecretStr
    llm_api_key: SecretStr
    tracing_api_key: SecretStr


settings = Settings()
