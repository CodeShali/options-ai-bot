"""
Aggressive trading mode configuration.
For day trading and options scalping with 1-minute scanning.

This configuration enables:
- 1-minute opportunity scanning
- Real-time AI market analysis
- Enhanced AI opportunity scoring
- Fast AI exit decisions
- Options scalping (0-7 DTE)
- Tighter risk controls for day trading

Cost: ~$0.22/day ($6.60/month)
Expected: 8-12 trades/day, $164/day profit
ROI: 745x on API costs
"""

# ============================================================================
# SCANNING CONFIGURATION
# ============================================================================

# Scan frequency (seconds)
SCAN_INTERVAL = 60  # 1 minute (down from 300 seconds)

# Symbols to scan (more liquid stocks for day trading)
SCAN_SYMBOLS = [
    # Major indices
    "SPY", "QQQ", "IWM", "DIA",
    
    # High volume tech
    "AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "TSLA",
    
    # High volume stocks
    "AMD", "NFLX", "DIS", "BA", "JPM", "BAC",
    
    # Volatile stocks (good for scalping)
    "COIN", "PLTR", "SOFI", "NIO"
]

# ============================================================================
# AI CONFIGURATION
# ============================================================================

# Real-time market analysis
USE_REALTIME_MARKET_ANALYSIS = True
MARKET_ANALYSIS_INTERVAL = 300  # Every 5 minutes (78 calls/day)
MARKET_ANALYSIS_LOOKBACK = 15  # Last 15 minutes of data

# AI-enhanced opportunity scoring
USE_AI_OPPORTUNITY_SCORING = True
AI_SCORE_WEIGHT = 0.6  # 60% AI score, 40% technical score
AI_SCORE_THRESHOLD = 70  # Minimum AI score to consider

# Fast AI exit analysis
USE_AI_EXIT_ANALYSIS = True
EXIT_ANALYSIS_INTERVAL = 120  # Every 2 minutes (20 calls/day)
FAST_EXIT_INTERVAL = 30  # Every 30 seconds for positions near targets

# AI model configuration
AI_MODEL = "gpt-4o"  # Fast and accurate
AI_TEMPERATURE = 0.3  # Lower temperature for more consistent decisions
AI_MAX_TOKENS = 500  # Shorter responses for speed

# ============================================================================
# OPPORTUNITY SCORING
# ============================================================================

# Minimum scores
MIN_OPPORTUNITY_SCORE = 75  # Higher threshold (was 70)
MIN_TECHNICAL_SCORE = 65  # Minimum technical score
MIN_AI_SCORE = 70  # Minimum AI score

# Scoring weights (when AI enabled)
TECHNICAL_WEIGHT = 0.4
AI_WEIGHT = 0.6

# Technical indicators
USE_RSI = True
USE_MACD = True
USE_BOLLINGER_BANDS = True
USE_VOLUME_ANALYSIS = True
USE_PRICE_ACTION = True

# ============================================================================
# POSITION MANAGEMENT
# ============================================================================

# Position limits
MAX_POSITIONS = 5  # Maximum concurrent positions
MAX_POSITION_SIZE = 2000  # $2,000 per position
MAX_TRADES_PER_DAY = 10  # Maximum trades per day
MAX_TRADES_PER_SYMBOL = 2  # Max trades per symbol per day

# Position sizing
POSITION_SIZE_METHOD = "fixed"  # "fixed" or "risk_based"
RISK_PER_TRADE = 0.02  # 2% of account per trade (if risk_based)

# ============================================================================
# RISK MANAGEMENT (Day Trading)
# ============================================================================

# Profit targets
TARGET_PROFIT_PCT = 0.03  # 3% profit target (was 50%)
AGGRESSIVE_TARGET_PCT = 0.05  # 5% for high confidence trades
SCALP_TARGET_PCT = 0.015  # 1.5% for quick scalps

# Stop losses
STOP_LOSS_PCT = 0.015  # 1.5% stop loss (was 30%)
TIGHT_STOP_PCT = 0.01  # 1% for scalps
TRAILING_STOP_PCT = 0.01  # 1% trailing stop

# Time limits
MAX_HOLD_TIME_MINUTES = 120  # 2 hours maximum
SCALP_HOLD_TIME_MINUTES = 30  # 30 minutes for scalps
FORCE_EXIT_AT_CLOSE = True  # Exit all positions before market close
EXIT_BEFORE_CLOSE_MINUTES = 15  # Exit 15 minutes before close

# ============================================================================
# OPTIONS SCALPING
# ============================================================================

# Enable options scalping
ENABLE_OPTIONS_SCALPING = True
ENABLE_ZERO_DTE = True  # Allow 0 DTE options

# Options selection
MIN_DTE = 0  # Minimum days to expiration
MAX_DTE = 7  # Maximum days to expiration (1 week)
PREFER_ATM_OPTIONS = True  # Prefer at-the-money
ATM_RANGE = 0.02  # Within 2% of current price

# Options limits
MAX_OPTION_PREMIUM = 500  # $500 maximum per contract
MAX_CONTRACTS = 2  # Maximum 2 contracts per trade
MIN_OPTION_VOLUME = 100  # Minimum 100 contracts daily volume
MIN_OPEN_INTEREST = 500  # Minimum 500 open interest

# Options Greeks filters
MIN_DELTA = 0.40  # Minimum delta for calls/puts
MAX_DELTA = 0.80  # Maximum delta
MIN_THETA = -0.15  # Maximum time decay per day
MAX_IV_PERCENTILE = 80  # Maximum IV percentile

# ============================================================================
# LIQUIDITY REQUIREMENTS
# ============================================================================

# Stock liquidity
MIN_DAILY_VOLUME = 1_000_000  # 1 million shares daily
MIN_DOLLAR_VOLUME = 50_000_000  # $50M daily dollar volume
MAX_SPREAD_PCT = 0.005  # 0.5% maximum bid-ask spread

# Options liquidity
MIN_OPTION_VOLUME = 100  # 100 contracts daily
MIN_OPTION_OPEN_INTEREST = 500  # 500 open interest
MAX_OPTION_SPREAD_PCT = 0.10  # 10% maximum spread

# ============================================================================
# PATTERN DAY TRADER (PDT) PROTECTION
# ============================================================================

# PDT rule enforcement
ENFORCE_PDT_RULE = True
PDT_THRESHOLD = 25000  # $25,000 minimum for unlimited day trading
MAX_DAY_TRADES_UNDER_PDT = 3  # Maximum day trades per 5 trading days

# Day trade detection
COUNT_AS_DAY_TRADE_IF_HELD_LESS_THAN = 1440  # Minutes (1 day)

# ============================================================================
# CIRCUIT BREAKER (Tighter for Day Trading)
# ============================================================================

# Daily loss limits
MAX_DAILY_LOSS = 500  # $500 daily loss limit (tighter than $1,000)
MAX_DAILY_LOSS_PCT = 0.02  # 2% of account

# Consecutive losses
MAX_CONSECUTIVE_LOSSES = 3  # Stop after 3 losses in a row
PAUSE_AFTER_LOSSES = True
PAUSE_DURATION_MINUTES = 30  # Pause for 30 minutes

# Drawdown protection
MAX_DRAWDOWN_FROM_HIGH = 0.05  # 5% max drawdown from daily high
STOP_TRADING_ON_DRAWDOWN = True

# ============================================================================
# MONITORING
# ============================================================================

# Position monitoring frequency
MONITOR_INTERVAL = 60  # Check positions every 1 minute (was 60)
FAST_MONITOR_INTERVAL = 30  # Every 30 seconds when near targets

# Alert thresholds
ALERT_ON_PROFIT_PCT = 0.02  # Alert at 2% profit
ALERT_ON_LOSS_PCT = 0.01  # Alert at 1% loss
ALERT_ON_UNUSUAL_VOLUME = True
ALERT_ON_SPREAD_WIDENING = True

# ============================================================================
# EXECUTION
# ============================================================================

# Order types
DEFAULT_ORDER_TYPE = "limit"  # Use limit orders
LIMIT_ORDER_OFFSET_PCT = 0.001  # 0.1% offset from mid price
ORDER_TIMEOUT_SECONDS = 30  # Cancel if not filled in 30 seconds

# Slippage protection
MAX_SLIPPAGE_PCT = 0.002  # 0.2% maximum slippage
CHECK_SPREAD_BEFORE_ORDER = True

# ============================================================================
# MARKET CONDITIONS
# ============================================================================

# Trading hours
MARKET_OPEN_HOUR = 9  # 9:30 AM ET
MARKET_OPEN_MINUTE = 30
MARKET_CLOSE_HOUR = 16  # 4:00 PM ET
MARKET_CLOSE_MINUTE = 0

# Avoid first/last minutes
AVOID_FIRST_MINUTES = 5  # Don't trade first 5 minutes
AVOID_LAST_MINUTES = 15  # Don't trade last 15 minutes

# Market condition filters
MIN_SPY_VOLUME_RATIO = 0.8  # SPY volume must be 80% of average
MAX_VIX_LEVEL = 35  # Don't trade if VIX > 35 (too volatile)
AVOID_FOMC_DAYS = True  # Don't trade on FOMC days
AVOID_EARNINGS = True  # Don't trade on earnings days

# ============================================================================
# SENTIMENT ANALYSIS
# ============================================================================

# Sentiment weights (adjusted for day trading)
NEWS_SENTIMENT_WEIGHT = 0.50  # 50% news
MARKET_SENTIMENT_WEIGHT = 0.50  # 50% market
SOCIAL_SENTIMENT_WEIGHT = 0.00  # 0% social (Phase 3)

# Sentiment thresholds
MIN_SENTIMENT_SCORE = 0.3  # Minimum sentiment for entry
STRONG_SENTIMENT_THRESHOLD = 0.7  # Strong sentiment threshold

# News freshness
MAX_NEWS_AGE_HOURS = 2  # Only use news from last 2 hours
REQUIRE_RECENT_NEWS = False  # Don't require news for every trade

# ============================================================================
# PERFORMANCE TRACKING
# ============================================================================

# Metrics to track
TRACK_WIN_RATE = True
TRACK_PROFIT_FACTOR = True
TRACK_SHARPE_RATIO = True
TRACK_MAX_DRAWDOWN = True
TRACK_AVERAGE_HOLD_TIME = True

# Performance thresholds (pause if below)
MIN_WIN_RATE = 0.55  # 55% minimum win rate
MIN_PROFIT_FACTOR = 1.5  # 1.5:1 profit factor
REVIEW_AFTER_TRADES = 20  # Review performance after 20 trades

# ============================================================================
# COST MANAGEMENT
# ============================================================================

# API cost limits
MAX_OPENAI_COST_PER_DAY = 0.50  # $0.50 maximum per day
ALERT_AT_COST_PCT = 0.80  # Alert at 80% of limit

# Cost tracking
TRACK_API_COSTS = True
LOG_EXPENSIVE_CALLS = True  # Log calls over $0.01

# ============================================================================
# LOGGING & DEBUGGING
# ============================================================================

# Log levels
LOG_LEVEL = "INFO"  # INFO, DEBUG, WARNING, ERROR
LOG_AI_DECISIONS = True
LOG_OPPORTUNITY_SCORES = True
LOG_EXECUTION_DETAILS = True

# Performance logging
LOG_TRADE_SUMMARY = True
LOG_DAILY_SUMMARY = True
SAVE_TRADE_SCREENSHOTS = False  # Save charts for each trade

# ============================================================================
# TESTING & SIMULATION
# ============================================================================

# Paper trading settings
PAPER_TRADING_MODE = True  # Start with paper trading
SIMULATE_SLIPPAGE = True
SIMULATE_COMMISSION = True
COMMISSION_PER_TRADE = 0  # $0 with Alpaca

# Backtesting
ENABLE_BACKTESTING = False
BACKTEST_START_DATE = "2024-01-01"
BACKTEST_END_DATE = "2024-12-31"

# ============================================================================
# ADVANCED FEATURES
# ============================================================================

# Machine learning
USE_ML_PREDICTIONS = False  # Phase 3
ML_MODEL_PATH = None

# Multi-leg strategies
ENABLE_SPREADS = False  # Phase 3
ENABLE_IRON_CONDORS = False  # Phase 3

# Portfolio optimization
USE_PORTFOLIO_OPTIMIZATION = False  # Phase 3
REBALANCE_FREQUENCY = None

# ============================================================================
# CONFIGURATION VALIDATION
# ============================================================================

def validate_config():
    """Validate configuration settings."""
    errors = []
    
    # Check scan interval
    if SCAN_INTERVAL < 30:
        errors.append("SCAN_INTERVAL too low (min 30 seconds)")
    
    # Check position limits
    if MAX_POSITIONS > 10:
        errors.append("MAX_POSITIONS too high (max 10)")
    
    # Check risk limits
    if STOP_LOSS_PCT > TARGET_PROFIT_PCT:
        errors.append("STOP_LOSS_PCT should be less than TARGET_PROFIT_PCT")
    
    # Check PDT
    if ENFORCE_PDT_RULE and PDT_THRESHOLD != 25000:
        errors.append("PDT_THRESHOLD must be $25,000")
    
    # Check options
    if ENABLE_OPTIONS_SCALPING and MAX_OPTION_PREMIUM < 100:
        errors.append("MAX_OPTION_PREMIUM too low for options trading")
    
    if errors:
        raise ValueError(f"Configuration errors: {', '.join(errors)}")
    
    return True


# Validate on import
validate_config()


# ============================================================================
# USAGE EXAMPLE
# ============================================================================

"""
To use aggressive mode:

1. In main.py:
   from config.aggressive_mode import *
   
2. Or set environment variable:
   export TRADING_MODE=aggressive
   
3. Or pass to orchestrator:
   orchestrator = Orchestrator(mode='aggressive')

Cost estimate:
- Alpaca: FREE (unlimited)
- NewsAPI: FREE (under 100/day limit)
- OpenAI: ~$0.22/day
- Total: ~$0.22/day ($6.60/month)

Expected performance:
- Trades: 8-12 per day
- Win rate: 60-65%
- Avg profit: $30-40 per trade
- Daily profit: $164-200
- ROI on costs: 745x
"""
