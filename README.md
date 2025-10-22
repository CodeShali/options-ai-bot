# 🌟 TARA - AI Trading System

**Trade by Light, Guided by Intelligence**

*Automated trading system with Discord bot control, Claude AI analysis, and comprehensive risk management*

[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
> **⚠️ DISCLAIMER**: This software is for educational purposes only. Trading involves substantial risk of loss. Use at your own risk.

---

## 📋 Table of Contents

- [Features](#-features)
- [Quick Start](#-quick-start)
- [Discord Commands](#-discord-commands)
- [Architecture](#-architecture)
- [Configuration](#-configuration)
- [Testing](#-testing)
- [Documentation](#-documentation)
- [Support](#-support)

---

## ✨ Features

### 🤖 AI-Powered Analysis
- **Claude Sonnet 4** for superior stock & options analysis
- **GPT-4o** fallback for reliability
- Real-time market data from Alpaca
- Technical indicators & pattern recognition
- Sentiment analysis from news sources

### 💬 Discord Bot Control
- **24 slash commands** for complete control
- Real-time notifications & alerts
- Position management & monitoring
- Interactive watchlist management
- Performance tracking & reporting

### 🛡️ Risk Management
- Position size limits
- Daily loss circuit breakers
- Trade validation & approval
- Stop-loss & profit targets
- Portfolio risk analysis

### 📊 Trading Features
- Paper & live trading modes
- Automated opportunity scanning
- Multi-timeframe analysis
- Options Greeks calculation
- Trade execution & monitoring

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- API Keys:
  - [Alpaca](https://alpaca.markets/) (Trading)
  - [Discord](https://discord.com/developers) (Bot)
  - [OpenAI](https://platform.openai.com/) (AI Analysis)
  - [Anthropic](https://console.anthropic.com/) (Claude AI - optional)
  - [NewsAPI](https://newsapi.org/) (News Data - optional)

### Installation

```bash
# 1. Clone repository
git clone https://github.com/your-username/options-AI-BOT.git
cd options-AI-BOT

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env with your API keys

# 5. Run the bot
python main.py
```

---

## 💬 Discord Commands

### Trading Commands
```
/sentiment <symbol>     - AI analysis with Claude
/quote <symbol>         - Real-time quote
/options <symbol>       - Options chain data
/trade <symbol>         - Generate trade opportunity
```

### Portfolio Management
```
/positions              - View open positions
/account                - Account summary
/performance [days]     - Performance metrics
/trades [limit]         - Recent trades
```

### Watchlist
```
/watchlist              - View watchlist
/add-watchlist <symbol> - Add to watchlist
/remove-watchlist <sym> - Remove from watchlist
```

### System Control
```
/status                 - System status
/scan-now               - Trigger immediate scan
/pause                  - Pause trading
/resume                 - Resume trading
/switch-mode <mode>     - Switch paper/live
```

### Advanced
```
/simulate               - Run system tests
/close-all              - Emergency close all
/help                   - Show all commands
```

---

## 🏗️ Architecture

### Multi-Agent System

```
┌─────────────────────────────────────────────────────────┐
│                   Orchestrator Agent                     │
│              (Coordinates all workflows)                 │
└─────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
┌───────▼────────┐  ┌──────▼──────┐  ┌────────▼────────┐
│ Data Pipeline  │  │  Strategy   │  │  Risk Manager   │
│     Agent      │  │    Agent    │  │      Agent      │
│                │  │             │  │                 │
│ • Market data  │  │ • AI        │  │ • Validation    │
│ • Scanning     │  │   analysis  │  │ • Limits        │
│ • Watchlist    │  │ • Signals   │  │ • Approval      │
└────────────────┘  └─────────────┘  └─────────────────┘
        │                   │                   │
        └───────────────────┼───────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
┌───────▼────────┐  ┌──────▼──────┐
│   Execution    │  │   Monitor   │
│     Agent      │  │    Agent    │
│                │  │             │
│ • Trade exec   │  │ • Position  │
│ • Orders       │  │   tracking  │
│ • Fills        │  │ • Alerts    │
└────────────────┘  └─────────────┘
```

### Technology Stack

- **Trading**: Alpaca API (paper & live)
- **AI Analysis**: Claude Sonnet 4, GPT-4o
- **Bot**: Discord.py with slash commands
- **API**: FastAPI for internal communication
- **Database**: SQLite with async support
- **Scheduler**: APScheduler for automation
- **Logging**: Loguru with rotation
- **Containerization**: Docker & Docker Compose

---

## ⚙️ Configuration

### Environment Variables

Create `.env` from `.env.example`:

```env
# Trading API
ALPACA_API_KEY=your_alpaca_api_key
ALPACA_SECRET_KEY=your_alpaca_secret_key
ALPACA_BASE_URL=https://paper-api.alpaca.markets

# Discord Bot
DISCORD_BOT_TOKEN=your_discord_bot_token
DISCORD_CHANNEL_ID=your_channel_id

# AI Services
OPENAI_API_KEY=your_openai_api_key
ANTHROPIC_API_KEY=your_anthropic_api_key
NEWS_API_KEY=your_news_api_key

# Trading Configuration
TRADING_MODE=paper
MAX_POSITION_SIZE=5000
MAX_DAILY_LOSS=1000
PROFIT_TARGET_PCT=0.50
STOP_LOSS_PCT=0.30
MAX_OPEN_POSITIONS=5
```

### Risk Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `MAX_POSITION_SIZE` | $5,000 | Maximum $ per position |
| `MAX_DAILY_LOSS` | $1,000 | Circuit breaker threshold |
| `PROFIT_TARGET_PCT` | 50% | Profit target |
| `STOP_LOSS_PCT` | 30% | Stop loss |
| `MAX_OPEN_POSITIONS` | 5 | Max concurrent positions |

### Watchlist

Edit in `agents/data_pipeline_agent.py`:

```python
self.watchlist = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "TSLA",
    "NVDA", "META", "SPY", "QQQ", "IWM"
]
```

---

## 📁 Project Structure

```
options-AI-BOT/
├── agents/                 # Multi-agent system
│   ├── orchestrator_agent.py
│   ├── data_pipeline_agent.py
│   ├── strategy_agent.py
│   ├── risk_manager_agent.py
│   ├── execution_agent.py
│   └── monitor_agent.py
├── api/                    # FastAPI server
│   └── server.py
├── bot/                    # Discord bot
│   └── discord_bot.py
├── config/                 # Configuration
│   └── settings.py
├── services/               # Core services
│   ├── alpaca_service.py
│   ├── claude_service.py
│   ├── llm_service.py
│   ├── news_service.py
│   └── database_service.py
├── utils/                  # Utilities
│   ├── logger.py
│   └── scheduler.py
├── docs/                   # Documentation
│   ├── deployment/
│   ├── guides/
│   └── archive/
├── tests/                  # All test scripts
├── data/                   # Database (runtime)
├── logs/                   # Log files (runtime)
├── main.py                 # Entry point
├── requirements.txt
├── .env.example
├── README.md
└── START_HERE.md           # Quick start guide
```

---

## 📚 Documentation

### Essential Guides
- **[START_HERE.md](START_HERE.md)** - Quick start guide
- **[SYSTEM_READINESS_REPORT.md](SYSTEM_READINESS_REPORT.md)** - System status & gaps
- **[Operational Guide](docs/OPERATIONAL_GUIDE.md)** - Daily operations
- **[System Architecture](docs/SYSTEM_ARCHITECTURE.md)** - Technical details
- **[Workflow Guide](docs/WORKFLOW_GUIDE.md)** - Step-by-step workflows
- **[Testing & Validation](docs/TESTING_VALIDATION.md)** - Testing procedures

### Testing
- Test scripts in `tests/` directory
- Run tests: `python tests/test_claude_api.py`

---

## 🔒 Security

### Best Practices
1. ✅ Never commit `.env` file
2. ✅ Use paper trading first
3. ✅ Start with small position sizes
4. ✅ Monitor regularly
5. ✅ Set conservative limits
6. ✅ Keep API keys secure

### API Key Security
- Store in `.env` (gitignored)
- Use Secret Manager in production
- Rotate keys regularly
- Limit API permissions

---

## 📊 Monitoring

### Logs
- Location: `logs/bot.log`
- Rotation: 10 MB per file
- Retention: 30 days
- Format: JSON structured logging

### Database
- Location: `data/trading.db`
- Tables: positions, trades, signals, stats
- Backup: Recommended daily

### Discord Notifications
Real-time alerts for:
- Trade executions
- Profit/loss updates
- Circuit breaker triggers
- System status changes
- Daily summaries

---

## 🧪 Testing

### Paper Trading
Always test first:
```env
TRADING_MODE=paper
ALPACA_BASE_URL=https://paper-api.alpaca.markets
```

### System Tests
```bash
# Test Claude API
python tests/test_claude_api.py

# Test Discord commands
python tests/test_discord_commands.py

# Run full simulation
/simulate  # In Discord
```

---

## 🐛 Troubleshooting

### Bot Not Responding
```bash
# Check logs
tail -f logs/bot.log

# Verify Discord token
grep DISCORD_BOT_TOKEN .env

# Check bot permissions in Discord
```

### No Trades Executing
```bash
# Check trading mode
/status

# Verify market hours
# System pauses on weekends

# Check circuit breaker
/account
```

### API Errors
```bash
# Test Alpaca connection
python tests/check_prices.py

# Verify API keys
grep ALPACA .env
```

---

## 💰 Cost Breakdown

### AI API Costs (per 1000 analyses)
- Claude Sonnet 4: ~$0.30
- GPT-4o-mini: ~$0.10
- NewsAPI: Free (100 req/day)

### Hosting
- Run locally on your machine (free)
- Or deploy to your preferred cloud platform

---

## 🤝 Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

---

## 📧 Support

- **Issues**: [GitHub Issues](https://github.com/your-username/options-AI-BOT/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-username/options-AI-BOT/discussions)
- **Documentation**: See `docs/` directory

---

## 🔄 Updates

```bash
# Pull latest changes
git pull origin main

# Update dependencies
pip install -r requirements.txt --upgrade

# Restart bot
docker-compose restart  # Docker
# OR
python main.py  # Local
```

---

## 🎯 Roadmap

- [ ] Web dashboard with real-time charts
- [ ] Backtesting framework
- [ ] More technical indicators
- [ ] Multi-timeframe analysis
- [ ] Portfolio optimization
- [ ] Machine learning models
- [ ] Telegram bot support
- [ ] Email notifications
- [ ] Advanced order types
- [ ] Options strategies (spreads, straddles)

---

## ⚠️ Disclaimer

**IMPORTANT**: This software is provided for educational purposes only. Trading stocks and options involves substantial risk of loss. Past performance is not indicative of future results. The authors and contributors are not responsible for any financial losses incurred through the use of this software.

Always:
- ✅ Start with paper trading
- ✅ Understand the risks
- ✅ Never invest more than you can afford to lose
- ✅ Consult with a financial advisor
- ✅ Comply with all applicable laws and regulations

---

## 📝 License

MIT License - see [LICENSE](LICENSE) file for details.

---

## 🌟 Acknowledgments

- [Alpaca](https://alpaca.markets/) for trading API
- [Discord.py](https://discordpy.readthedocs.io/) for bot framework
- [Anthropic](https://www.anthropic.com/) for Claude AI
- [OpenAI](https://openai.com/) for GPT models

---

**Happy Trading! 🚀📈**

*Built with ❤️ for algorithmic traders*
