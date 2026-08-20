from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "development"
    port: int = 8000
    cors_origins: str = "http://localhost:5173"
    execution_mode: Literal["local", "azure"] = "local"
    azure_batch_account_url: str = ""
    azure_batch_autoscale_pool_id: str = "finance-hpc-pool"
    azure_batch_always_on_pool_id: str = "finance-hpc-warm-pool"
    batch_task_delay_seconds: int = Field(default=180, ge=0, le=3600)

    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    def azure_batch_missing_settings(self) -> list[str]:
        required = {
            "AZURE_BATCH_ACCOUNT_URL": self.azure_batch_account_url,
            "AZURE_BATCH_AUTOSCALE_POOL_ID": self.azure_batch_autoscale_pool_id,
            "AZURE_BATCH_ALWAYS_ON_POOL_ID": self.azure_batch_always_on_pool_id,
        }
        return [name for name, value in required.items() if not value]


@lru_cache
def get_settings() -> Settings:
    return Settings()
