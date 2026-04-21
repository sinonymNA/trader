from __future__ import annotations

import os

import pytest


def reset_settings():
    import app.config as cfg
    cfg._settings = None


def test_safe_defaults() -> None:
    reset_settings()
    env_backup = {}
    keys = ["OANDA_API_KEY", "OANDA_ACCOUNT_ID", "TRADING_ENABLED", "DRY_RUN",
            "DATABASE_URL", "LOG_LEVEL", "INSTRUMENTS"]
    for k in keys:
        env_backup[k] = os.environ.pop(k, None)

    try:
        from app.config import Settings
        s = Settings()
        assert s.dry_run is True
        assert s.trading_enabled is False
        assert s.oanda_api_key == ""
        assert s.oanda_account_id == ""
        assert s.log_level == "INFO"
    finally:
        for k, v in env_backup.items():
            if v is not None:
                os.environ[k] = v
        reset_settings()


def test_instrument_list_parsing() -> None:
    reset_settings()
    from app.config import Settings
    s = Settings(instruments="EUR_USD, GBP_USD , USD_JPY")
    assert s.instrument_list() == ["EUR_USD", "GBP_USD", "USD_JPY"]


def test_validate_for_live_raises_without_credentials() -> None:
    reset_settings()
    from app.config import Settings
    s = Settings(dry_run=False, oanda_api_key="", oanda_account_id="")
    with pytest.raises(ValueError, match="OANDA_API_KEY"):
        s.validate_for_live()


def test_validate_for_live_passes_with_credentials() -> None:
    reset_settings()
    from app.config import Settings
    s = Settings(
        dry_run=False,
        oanda_api_key="my-key",
        oanda_account_id="my-account",
    )
    s.validate_for_live()  # should not raise


def test_invalid_log_level_raises() -> None:
    reset_settings()
    from app.config import Settings
    with pytest.raises(Exception):
        Settings(log_level="VERBOSE")
