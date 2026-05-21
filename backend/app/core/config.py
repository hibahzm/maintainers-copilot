from pydantic import AliasChoices, BaseModel, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Maintainers Copilot API"
    vault_addr: str = "http://localhost:8200"
    vault_token: SecretStr = Field(
        default=SecretStr("dev-only-root-token"),
        validation_alias=AliasChoices("VAULT_TOKEN", "VAULT_DEV_ROOT_TOKEN_ID"),
    )
    vault_mount_point: str = "secret"
    vault_secret_path: str = "maintainers-copilot"
    model_server_url: str = "http://localhost:8001"
    database_url: str = "postgresql://copilot:copilot-dev-only@localhost:5432/copilot"
    redis_url: str = "redis://localhost:6379/0"
    conversation_ttl_seconds: int = 7200
    jwt_signing_key: SecretStr = SecretStr("dev-only-jwt-signing-key")
    access_token_ttl_minutes: int = 60
    openai_api_key: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("OPENAI_API_KEY", "LLM_API_KEY"),
    )
    chat_agent_model: str = "gpt-4o-mini"
    chat_agent_max_tool_rounds: int = 3
    cors_allowed_origins: list[str] = [
        "http://localhost:4173",
        "http://localhost:5173",
        "http://localhost:8080",
        "http://localhost:8501",
    ]
    widget_public_url: str = "http://localhost:4173"
    tracing_backend: str = "langfuse"
    tracing_host: str = "https://cloud.langfuse.com"
    eval_thresholds_path: str = "evals/eval_thresholds.yaml"


class RuntimeSecrets(BaseModel):
    """Secrets that must be loaded from Vault before the API can serve traffic."""

    database_password: SecretStr
    jwt_signing_key: SecretStr
    minio_access_key: SecretStr
    minio_secret_key: SecretStr
    llm_api_key: SecretStr
    tracing_api_key: SecretStr


settings = Settings()
