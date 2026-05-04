from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Anthropic
    anthropic_api_key: str = ""

    # Alpaca
    alpaca_api_key: str = ""
    alpaca_secret_key: str = ""
    alpaca_paper: bool = True

    # Telegram
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    # Trading profile
    auto_trade: bool = False
    max_trades_per_week: int = 3
    max_risk_per_trade: float = 150.0   # max $ per trade
    profit_target_pct: float = 0.70     # 70% gain on premium
    stop_loss_pct: float = 0.35         # 35% loss on premium
    account_size: float = 2000.0

    # Symbols to scan
    watchlist: List[str] = ["SPY", "QQQ", "AAPL", "NVDA", "TSLA", "MSFT"]

    # Options
    min_dte: int = 5
    max_dte: int = 14

    # Scan windows (ET, 24h format)
    morning_scan_start_hour: int = 9
    morning_scan_start_min: int = 35
    morning_scan_end_hour: int = 11
    morning_scan_end_min: int = 30
    afternoon_scan_start_hour: int = 13
    afternoon_scan_end_hour: int = 14
    afternoon_scan_end_min: int = 30

    # Force-close time (ET)
    force_close_hour: int = 15
    force_close_min: int = 45

    scan_interval_minutes: int = 5
    monitor_interval_seconds: int = 120


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
