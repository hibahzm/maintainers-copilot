from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Maintainers Copilot API"
    vault_addr: str = "http://localhost:8200"
    model_server_url: str = "http://localhost:8001"


settings = Settings()
