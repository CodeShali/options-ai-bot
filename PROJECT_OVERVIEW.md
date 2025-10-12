# Project Overview - Options Trading AI Bot

## 📁 Complete File Structure

```
options-AI-BOT/
├── agents/                          # Multi-agent system
│   ├── __init__.py
│   ├── base_agent.py               # Base class for all agents
│   ├── orchestrator_agent.py       # Main coordinator
│   ├── data_pipeline_agent.py      # Market data fetching
│   ├── strategy_agent.py           # AI-powered analysis
│   ├── risk_manager_agent.py       # Risk management & validation
│   ├── execution_agent.py          # Trade execution
│   └── monitor_agent.py            # Position monitoring
│
├── api/                             # FastAPI server
│   ├── __init__.py
│   └── server.py                   # REST API endpoints
│
├── bot/                             # Discord bot
│   ├── __init__.py
│   └── discord_bot.py              # Discord commands & notifications
│
├── config/                          # Configuration
│   ├── __init__.py
│   └── settings.py                 # Settings management
│
├── services/                        # Core services
│   ├── __init__.py
│   ├── alpaca_service.py           # Alpaca API integration
│   ├── llm_service.py              # Claude AI integration
│   └── database_service.py         # SQLite database
│
├── utils/                           # Utilities
│   ├── __init__.py
│   ├── logger.py                   # Logging configuration
│   └── scheduler.py                # Task scheduling
│
├── scripts/                         # Utility scripts
│   ├── __init__.py
│   ├── test_connection.py          # Test API connections
│   ├── manual_trade.py             # Execute manual trades
│   ├── view_positions.py           # View current positions
│   └── close_all.py                # Emergency close all positions
│
├── data/                            # Database (created at runtime)
│   └── trading.db
│
├── logs/                            # Log files (created at runtime)
│   └── trading.log
│
├── main.py                          # Main entry point
├── requirements.txt                 # Python dependencies
├── .env.example                     # Environment variables template
├── .env                            # Your environment variables (not in git)
├── .gitignore                      # Git ignore rules
├── Dockerfile                      # Docker container definition
├── docker-compose.yml              # Docker compose configuration
├── README.md                       # Main documentation
├── SETUP_GUIDE.md                  # Setup instructions
├── CONTRIBUTING.md                 # Contribution guidelines
├── CHANGELOG.md                    # Version history
├── LICENSE                         # MIT License
└── PROJECT_OVERVIEW.md             # This file
```

## 🎯 System Architecture

### Agent Communication Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    Orchestrator Agent                        │
│              (Coordinates all workflows)                     │
└────┬────────┬────────┬────────┬────────┬────────────────────┘
     │        │        │        │        │
     ▼        ▼        ▼        ▼        ▼
┌─────────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌────────┐
│  Data   │ │Strat │ │ Risk │ │Exec  │ │Monitor │
│Pipeline │ │ egy  │ │ Mgr  │ │ution │ │        │
└─────────┘ └──────┘ └──────┘ └──────┘ └────────┘
     │          │        │        │         │
     └──────────┴────────┴────────┴─────────┘
                      │
            ┌─────────┴─────────┐
            │                   │
         ┌──▼──┐           ┌───▼────┐
         │ API │           │Services│
         └─────┘           └────────┘
```

### Trading Workflow

```
1. SCAN PHASE (Every 5 minutes)
   ├─ Data Pipeline: Fetch market data for watchlist
   ├─ Strategy: Analyze opportunities with Claude AI
   ├─ Risk Manager: Validate against risk parameters
   ├─ Execution: Place orders for approved trades
   └─ Discord: Send notifications

2. MONITOR PHASE (Every 2 minutes)
   ├─ Monitor: Check all open positions
   ├─ Check profit targets (50%) and stop losses (30%)
   ├─ Strategy: Get AI confirmation for exits
   ├─ Execution: Close positions if conditions met
   └─ Discord: Send exit notifications

3. DAILY TASKS
   ├─ 9:30 AM ET: Reset circuit breaker
   └─ 4:00 PM ET: Generate daily summary
```

## 🔧 Key Components

### 1. Orchestrator Agent
**Purpose**: Main coordinator that manages all trading workflows

**Key Methods**:
- `scan_and_trade()` - Main trading loop
- `monitor_and_exit()` - Position monitoring loop
- `manual_trade()` - Execute manual trades
- `emergency_stop()` - Emergency shutdown

### 2. Data Pipeline Agent
**Purpose**: Fetches and processes market data

**Key Methods**:
- `scan_opportunities()` - Scan watchlist for signals
- `get_market_data()` - Fetch data for symbols
- `get_quote()` - Get current quote

**Watchlist**: AAPL, MSFT, GOOGL, AMZN, TSLA, NVDA, META, SPY, QQQ, IWM

### 3. Strategy Agent
**Purpose**: AI-powered analysis using OpenAI

**Key Methods**:
- `analyze_opportunity()` - Analyze buy opportunities
- `analyze_exit()` - Analyze exit signals
- `batch_analyze()` - Analyze multiple opportunities

**Technical Indicators**:
- SMA (20, 50)
- RSI (14)
- Volatility
- Volume ratio
- Price momentum

### 4. Risk Manager Agent
**Purpose**: Validates trades and enforces risk limits

**Key Methods**:
- `validate_trade()` - Validate before execution
- `check_circuit_breaker()` - Check daily loss limit
- `calculate_position_size()` - Calculate optimal size
- `check_exit_conditions()` - Check if should exit

**Risk Parameters**:
- Max position size: $5,000
- Max daily loss: $1,000 (circuit breaker)
- Max open positions: 5
- Profit target: 50%
- Stop loss: 30%

### 5. Execution Agent
**Purpose**: Executes trades through Alpaca

**Key Methods**:
- `execute_buy()` - Place buy orders
- `execute_sell()` - Place sell orders
- `close_position()` - Close entire position
- `close_all_positions()` - Emergency close all

### 6. Monitor Agent
**Purpose**: Monitors positions and generates alerts

**Key Methods**:
- `monitor_positions()` - Check all positions
- `check_alerts()` - System-level alerts
- `get_position_status()` - Detailed position info
- `generate_dashboard_data()` - Dashboard metrics

## 🤖 Discord Bot Commands

| Command | Description | Example |
|---------|-------------|---------|
| `/status` | System and portfolio status | `/status` |
| `/positions` | List open positions | `/positions` |
| `/sell` | Sell a position | `/sell AAPL` |
| `/pause` | Pause trading | `/pause` |
| `/resume` | Resume trading | `/resume` |
| `/switch-mode` | Switch paper/live | `/switch-mode paper` |
| `/trades` | Recent trades | `/trades 10` |
| `/performance` | Performance metrics | `/performance 30` |

## 🔌 API Endpoints

### Status & Health
- `GET /` - API info
- `GET /health` - Health check
- `GET /status` - System status
- `GET /positions` - Open positions
- `GET /dashboard` - Dashboard data

### Trading
- `POST /trade/manual?symbol=AAPL` - Manual trade
- `POST /agent/execute` - Execute agent action

### System Control
- `POST /system/pause` - Pause system
- `POST /system/resume` - Resume system
- `POST /system/emergency-stop` - Emergency stop

## 📊 Database Schema

### Tables

**trades**
- Trade history with timestamps
- Columns: id, trade_id, symbol, action, quantity, price, total_value, timestamp, order_id, status, notes

**positions**
- Current and historical positions
- Columns: id, symbol, quantity, avg_entry_price, current_price, cost_basis, market_value, unrealized_pl, opened_at, closed_at, status

**analysis_history**
- AI analysis records
- Columns: id, symbol, analysis_type, recommendation, confidence, risk_level, reasoning, market_data, timestamp

**system_state**
- System configuration and state
- Columns: id, key, value, updated_at

**daily_stats**
- Daily performance metrics
- Columns: id, date, total_trades, winning_trades, losing_trades, total_profit_loss, portfolio_value

## 🔐 Environment Variables

### Required
```env
ALPACA_API_KEY=           # Alpaca API key
ALPACA_SECRET_KEY=        # Alpaca secret key
DISCORD_BOT_TOKEN=        # Discord bot token
DISCORD_CHANNEL_ID=       # Discord channel ID
OPENAI_API_KEY=           # OpenAI API key
```

### Optional (with defaults)
```env
TRADING_MODE=paper        # paper or live
MAX_POSITION_SIZE=5000    # Max $ per position
MAX_DAILY_LOSS=1000       # Circuit breaker
PROFIT_TARGET_PCT=0.50    # 50% profit target
STOP_LOSS_PCT=0.30        # 30% stop loss
MAX_OPEN_POSITIONS=5      # Max concurrent positions
SCAN_INTERVAL_MINUTES=5   # Scan frequency
```

## 🚀 Quick Start Commands

```bash
# Setup
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your credentials

# Test connections
python scripts/test_connection.py

# Start system
python main.py

# Utility scripts
python scripts/view_positions.py
python scripts/manual_trade.py AAPL
python scripts/close_all.py
```

## 🐳 Docker Deployment

```bash
# Build and run
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

## 📈 Performance Monitoring

### Logs
- Location: `logs/trading.log`
- Rotation: 10 MB per file
- Retention: 30 days
- Format: Timestamp, level, module, message

### Metrics
- Win rate
- Total P/L
- Average trade duration
- Position count
- Daily statistics

### Alerts
- Profit targets reached
- Stop losses triggered
- Circuit breaker activated
- System errors
- Position updates

## 🛡️ Safety Features

1. **Circuit Breaker**: Stops trading at max daily loss
2. **Position Limits**: Max 5 concurrent positions
3. **Size Limits**: Max $5,000 per position
4. **Trade Validation**: All trades validated before execution
5. **Live Trading Confirmation**: Requires explicit confirmation
6. **Emergency Stop**: Can close all positions instantly
7. **Audit Trail**: All trades logged to database
8. **Paper Trading Default**: Starts in safe mode

## 🔄 Scheduled Tasks

| Task | Frequency | Description |
|------|-----------|-------------|
| Scan & Trade | 5 minutes | Scan for opportunities |
| Monitor Positions | 2 minutes | Check exit conditions |
| Reset Circuit Breaker | Daily 9:30 AM ET | New trading day |
| Daily Summary | Daily 4:00 PM ET | Performance report |

## 📚 Additional Resources

- **README.md**: Main documentation
- **SETUP_GUIDE.md**: Detailed setup instructions
- **CONTRIBUTING.md**: How to contribute
- **API Docs**: http://localhost:8000/docs (when running)

## 🎓 Learning Resources

### Alpaca API
- [Alpaca Docs](https://alpaca.markets/docs/)
- [Paper Trading](https://alpaca.markets/docs/trading/paper-trading/)

### Discord Bot
- [Discord.py Docs](https://discordpy.readthedocs.io/)
- [Discord Developer Portal](https://discord.com/developers/docs)

### AI Analysis
- [OpenAI GPT-4 Docs](https://docs.anthropic.com/)
- [Claude API Reference](https://docs.anthropic.com/claude/reference)

## ⚠️ Important Notes

1. **Always start with paper trading**
{{ ... }}
3. **Monitor regularly during market hours**
4. **Set conservative risk limits initially**
5. **Never invest more than you can afford to lose**
6. **This is educational software - use at your own risk**

## 🐛 Common Issues & Solutions

### Issue: Bot not responding
**Solution**: Check bot token, permissions, and channel ID

### Issue: No trades executing
**Solution**: Check circuit breaker, system pause status, risk limits

### Issue: API connection errors
**Solution**: Verify API keys, check internet connection, review Alpaca status

### Issue: Database errors
**Solution**: Ensure data/ directory exists and is writable

## 📞 Support

- Check logs: `tail -f logs/trading.log`
- Review API docs: http://localhost:8000/docs
- Test connections: `python scripts/test_connection.py`
- Check positions: `python scripts/view_positions.py`

---

**Built with ❤️ for algorithmic trading education**
