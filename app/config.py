from __future__ import annotations

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # OANDA
    oanda_api_key: str = ""
    oanda_account_id: str = ""
    oanda_base_url: str = "https://api-fxpractice.oanda.com"

    # Safety
    trading_enabled: bool = False
    dry_run: bool = True

    # App
    log_level: str = "INFO"
    timezone: str = "America/New_York"
    database_url: str = "sqlite+aiosqlite:///./trader.db"
    worker_interval_seconds: int = 15

    # Trading parameters
    instruments: str = "EUR_USD,GBP_USD,USD_JPY"
    max_position_units: int = 1000
    daily_loss_limit_usd: float = 50.0
    stop_loss_pips: float = 20.0
    take_profit_pips: float = 40.0

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        valid = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        upper = v.upper()
        if upper not in valid:
            raise ValueError(f"log_level must be one of {valid}")
        return upper

    def instrument_list(self) -> list[str]:
        return [i.strip() for i in self.instruments.split(",") if i.strip()]

    def validate_for_live(self) -> None:
        if not self.oanda_api_key:
            raise ValueError("OANDA_API_KEY is required when DRY_RUN=false")
        if not self.oanda_account_id:
            raise ValueError("OANDA_ACCOUNT_ID is required when DRY_RUN=false")


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
