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
    minio_endpoint: str = "localhost:9000"
    minio_secure: bool = False
    minio_artifact_bucket: str = "artifacts"
    minio_eval_bucket: str = "evals"
    minio_rag_bucket: str = "rag"
    minio_conversation_bucket: str = "conversation-snapshots"
    conversation_snapshot_retention: int = 25
    jwt_signing_key: SecretStr = SecretStr("dev-only-jwt-signing-key")
    access_token_ttl_minutes: int = 60
    openai_api_key: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("OPENAI_API_KEY", "LLM_API_KEY"),
    )
    chat_agent_model: str = "gpt-4o-mini"
    chat_agent_max_tool_rounds: int = 3
    bootstrap_dev_data: bool = True
    bootstrap_rag_index: bool = True
    rag_bootstrap_chunks_path: str = "data/rag/chunks/parent_child_chunks.jsonl"
    rag_bootstrap_batch_size: int = 16
    rag_bootstrap_timeout_seconds: float = 180.0
    dev_admin_email: str = "admin@maintainers.local"
    dev_admin_password: SecretStr = SecretStr("admin-password")
    default_widget_id: str = "maintainers-copilot"
    cors_allowed_origins: list[str] = [
        "http://localhost:4173",
        "http://localhost:5173",
        "http://localhost:8080",
        "http://localhost:8501",
    ]
    widget_public_url: str = "http://localhost:4173"
    tracing_backend: str = "langfuse"
    tracing_host: str = Field(
        default="https://cloud.langfuse.com",
        validation_alias=AliasChoices("TRACING_HOST", "LANGFUSE_BASE_URL"),
    )
    eval_thresholds_path: str = "evals/eval_thresholds.yaml"


class RuntimeSecrets(BaseModel):
    """Secrets that must be loaded from Vault before the API can serve traffic."""

    database_password: SecretStr
    jwt_signing_key: SecretStr
    minio_access_key: SecretStr
    minio_secret_key: SecretStr
    llm_api_key: SecretStr
    tracing_api_key: SecretStr
    langfuse_public_key: SecretStr
    langfuse_secret_key: SecretStr


settings = Settings()
