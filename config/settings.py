"""
Configuration management for the options trading system.
"""
import os
from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, validator


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # Alpaca API Configuration
    alpaca_api_key: str = Field(..., description="Alpaca API key")
    alpaca_secret_key: str = Field(..., description="Alpaca secret key")
    alpaca_base_url: str = Field(
        default="https://paper-api.alpaca.markets",
        description="Alpaca API base URL"
    )
    alpaca_data_feed: Literal["iex", "sip"] = Field(
        default="iex",
        description="Market data feed: 'iex' (free) or 'sip' (paid, full volume)"
    )
    
    # Discord Bot Configuration
    discord_bot_token: str = Field(..., description="Discord bot token")
    discord_channel_id: str = Field(..., description="Discord channel ID for notifications")
    
    # OpenAI Configuration
    openai_api_key: str = Field(..., description="OpenAI API key")
    
    # Claude API Configuration (for sentiment analysis)
    anthropic_api_key: str = Field(default="", description="Anthropic Claude API key for sentiment")
    
    # News API Configuration (Optional)
    news_api_key: str = Field(default="", description="NewsAPI key (optional)")
    news_api_enabled: bool = Field(default=False, description="Enable real news API")
    
    # Trading Configuration
    trading_mode: Literal["paper", "live"] = Field(
        default="paper",
        description="Trading mode: paper or live"
    )
    max_position_size: float = Field(
        default=5000.0,
        description="Maximum position size in USD"
    )
    max_daily_loss: float = Field(
        default=1000.0,
        description="Maximum daily loss in USD (circuit breaker)"
    )
    profit_target_pct: float = Field(
        default=0.50,
        description="Profit target percentage (0.50 = 50%)"
    )
    stop_loss_pct: float = Field(
        default=0.30,
        description="Stop loss percentage (0.30 = 30%)"
    )
    max_open_positions: int = Field(
        default=5,
        description="Maximum number of concurrent positions"
    )
    
    # Options Trading Configuration
    enable_options_trading: bool = Field(
        default=True,
        description="Enable options trading alongside stocks"
    )
    enable_stock_trading: bool = Field(
        default=True,
        description="Enable stock trading alongside options"
    )
    options_max_contracts: int = Field(
        default=2,
        description="Maximum number of option contracts per trade"
    )
    options_max_premium: float = Field(
        default=500.0,
        description="Maximum premium to pay per option contract"
    )
    options_min_dte: int = Field(
        default=30,
        description="Minimum days to expiration for options"
    )
    options_max_dte: int = Field(
        default=45,
        description="Maximum days to expiration for options"
    )
    options_close_dte: int = Field(
        default=7,
        description="Close options when this many days to expiration"
    )
    options_strike_preference: Literal["ATM", "OTM", "ITM"] = Field(
        default="OTM",
        description="Strike price preference: ATM, OTM (Out of The Money), or ITM (In The Money)"
    )
    options_otm_strikes: int = Field(
        default=1,
        description="Number of strikes away from current price for OTM options"
    )
    
    # Database Configuration
    database_path: str = Field(
        default="./data/trading.db",
        description="Path to SQLite database"
    )
    
    # Logging Configuration
    log_level: str = Field(default="INFO", description="Logging level")
    log_file: str = Field(
        default="./logs/trading.log",
        description="Path to log file"
    )
    
    # Scheduler Configuration
    scan_interval_minutes: int = Field(
        default=5,
        description="How often to scan for opportunities (in minutes)"
    )
    scan_interval: int = Field(
        default=300,
        description="Scan interval in seconds (300 = 5 min, 60 = 1 min for aggressive mode)"
    )
    
    # Aggressive Trading Mode Settings
    aggressive_mode: bool = Field(
        default=False,
        description="Enable aggressive trading mode (1-minute scanning, day trading)"
    )
    scalp_target_pct: float = Field(
        default=0.015,
        description="Profit target for scalp trades (1.5%)"
    )
    tight_stop_pct: float = Field(
        default=0.01,
        description="Stop loss for scalp trades (1%)"
    )
    scalp_hold_time_minutes: int = Field(
        default=30,
        description="Maximum hold time for scalp trades"
    )
    target_profit_pct: float = Field(
        default=0.03,
        description="Profit target for day trades (3%)"
    )
    stop_loss_pct_day: float = Field(
        default=0.015,
        description="Stop loss for day trades (1.5%)"
    )
    max_hold_time_minutes: int = Field(
        default=120,
        description="Maximum hold time for day trades"
    )
    
    # FastAPI Configuration
    api_host: str = Field(default="0.0.0.0", description="FastAPI host")
    api_port: int = Field(default=8000, description="FastAPI port")
    
    @validator("trading_mode")
    def validate_trading_mode(cls, v):
        """Validate trading mode."""
        if v not in ["paper", "live"]:
            raise ValueError("trading_mode must be 'paper' or 'live'")
        return v
    
    @validator("profit_target_pct", "stop_loss_pct")
    def validate_percentages(cls, v):
        """Validate percentage values."""
        if not 0 < v < 1:
            raise ValueError("Percentage must be between 0 and 1")
        return v
    
    @property
    def is_live_trading(self) -> bool:
        """Check if live trading is enabled."""
        return self.trading_mode == "live"
    
    @property
    def is_paper_trading(self) -> bool:
        """Check if paper trading is enabled."""
        return self.trading_mode == "paper"


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get the global settings instance."""
    return settings


def update_trading_mode(mode: Literal["paper", "live"]) -> None:
    """
    Update the trading mode.
    
    Args:
        mode: New trading mode ('paper' or 'live')
    """
    global settings
    settings.trading_mode = mode
    # Update the Alpaca base URL based on mode
    if mode == "live":
        settings.alpaca_base_url = "https://api.alpaca.markets"
    else:
        settings.alpaca_base_url = "https://paper-api.alpaca.markets"


def enable_aggressive_mode() -> None:
    """
    Enable aggressive trading mode with 1-minute scanning.
    Updates scan interval and trading parameters for day trading/scalping.
    """
    global settings
    settings.aggressive_mode = True
    settings.scan_interval = 60  # 1 minute
    settings.scan_interval_minutes = 1
    settings.max_daily_loss = 500  # Tighter circuit breaker
    settings.max_open_positions = 5
    settings.max_position_size = 2000
    
    # Update options for scalping
    settings.options_min_dte = 0  # Allow 0 DTE
    settings.options_max_dte = 7  # Max 1 week
    settings.options_max_premium = 500
    settings.options_max_contracts = 2


def disable_aggressive_mode() -> None:
    """
    Disable aggressive mode and return to conservative swing trading.
    """
    global settings
    settings.aggressive_mode = False
    settings.scan_interval = 300  # 5 minutes
    settings.scan_interval_minutes = 5
    settings.max_daily_loss = 1000
    settings.max_open_positions = 5
    settings.max_position_size = 5000
    
    # Reset options to swing trading
    settings.options_min_dte = 30
    settings.options_max_dte = 45
    settings.options_max_premium = 500
    settings.options_max_contracts = 2
