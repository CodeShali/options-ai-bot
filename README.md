# Options Trading AI Bot

A production-ready, multi-agent options trading system with AI-powered analysis, Discord bot control, and comprehensive risk management.

## 🏗️ Architecture

### Multi-Agent System
- **Orchestrator Agent**: Coordinates all agents and manages workflows
- **Data Pipeline Agent**: Fetches and processes market data
- **Strategy Agent**: AI-powered analysis using Claude for trading signals
- **Risk Manager Agent**: Validates trades and enforces risk limits
- **Execution Agent**: Executes trades through Alpaca API
- **Monitor Agent**: Monitors positions and generates exit signals

### Key Technologies
- **Trading API**: Alpaca (paper & live trading)
- **AI Analysis**: OpenAI GPT-4
- **Bot Interface**: Discord with slash commands
- **Database**: SQLite with async support
- **API**: FastAPI for internal communication
- **Scheduler**: APScheduler for periodic tasks

## 🚀 Features

### Trading Features
- ✅ Paper and live trading mode switching (with confirmation)
- ✅ Automated opportunity scanning every 5 minutes
- ✅ AI-powered market analysis with OpenAI GPT-4
- ✅ Intelligent position sizing based on confidence and risk
- ✅ Real-time position monitoring
- ✅ Automated exit signals (50% profit target, 30% stop loss)
- ✅ Circuit breakers for maximum daily loss protection
- ✅ Position limits and risk management

### Discord Commands
- `/status` - Get system status and portfolio overview
- `/positions` - List all open positions
- `/sell <symbol>` - Sell a specific position
- `/pause` - Pause the trading system
- `/resume` - Resume the trading system
- `/switch-mode <mode>` - Switch between paper and live trading
- `/trades [limit]` - View recent trades
- `/performance [days]` - View performance metrics

### Safety Features
- 🛡️ Circuit breaker for maximum daily loss
- 🛡️ Position size limits
- 🛡️ Maximum open positions limit
- 🛡️ Trade validation before execution
- 🛡️ Confirmation required for live trading mode
- 🛡️ Emergency stop functionality
- 🛡️ Comprehensive audit trail

## 📋 Prerequisites

- Python 3.9+
- Alpaca account (paper or live)
- Discord bot token
- OpenAI API key

## 🔧 Installation

1. **Clone the repository**
```bash
cd options-AI-BOT
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Configure environment variables**
```bash
cp .env.example .env
```

Edit `.env` with your credentials:
```env
# Alpaca API
ALPACA_API_KEY=your_alpaca_api_key
ALPACA_SECRET_KEY=your_alpaca_secret_key
ALPACA_BASE_URL=https://paper-api.alpaca.markets

# Discord
DISCORD_BOT_TOKEN=your_discord_bot_token
DISCORD_CHANNEL_ID=your_channel_id

# OpenAI
OPENAI_API_KEY=your_openai_api_key

# Trading Configuration
TRADING_MODE=paper
MAX_POSITION_SIZE=5000
MAX_DAILY_LOSS=1000
PROFIT_TARGET_PCT=0.50
STOP_LOSS_PCT=0.30
MAX_OPEN_POSITIONS=5
```

## 🎮 Usage

### Start the System
```bash
python main.py
```

The system will:
1. Initialize all agents
2. Start the Discord bot
4. Begin scheduled scanning and monitoring

### Discord Bot Setup

1. **Create Discord Bot**
   - Go to [Discord Developer Portal](https://discord.com/developers/applications)
   - Create a new application
   - Go to "Bot" section and create a bot
   - Copy the bot token to `.env`
   - Enable "Message Content Intent"

### OpenAI
- [OpenAI Docs](https://platform.openai.com/docs)
- [OpenAI API Reference](https://platform.openai.com/docs/api-reference)
2. **Invite Bot to Server**
   - Go to OAuth2 → URL Generator
   - Select scopes: `bot`, `applications.commands`
   - Select permissions: `Send Messages`, `Read Messages`, `Use Slash Commands`
   - Copy and open the generated URL

3. **Get Channel ID**
   - Enable Developer Mode in Discord (User Settings → Advanced)
   - Right-click your channel → Copy ID
   - Add to `.env`

### API Endpoints

Access the API documentation at: `http://localhost:8000/docs`

Key endpoints:
- `GET /status` - System status
- `GET /positions` - Open positions
- `GET /health` - Health check
- `POST /trade/manual` - Execute manual trade
- `POST /system/pause` - Pause system
- `POST /system/resume` - Resume system
- `POST /system/emergency-stop` - Emergency stop

## 📊 Trading Workflow

### Automated Scanning (Every 5 minutes)
1. **Scan**: Data Pipeline scans watchlist for opportunities
2. **Analyze**: Strategy Agent uses Claude AI to analyze opportunities
3. **Validate**: Risk Manager validates trades against limits
4. **Execute**: Execution Agent places orders via Alpaca
5. **Monitor**: Monitor Agent tracks positions continuously

### Position Monitoring (Every 2 minutes)
1. Check all open positions
2. Calculate profit/loss
3. Check exit conditions (profit target or stop loss)
4. Get AI confirmation for exits
5. Execute exit orders if conditions met
6. Send Discord notifications

## ⚙️ Configuration

### Risk Parameters
Edit in `.env`:
```env
MAX_POSITION_SIZE=5000      # Max $ per position
MAX_DAILY_LOSS=1000         # Circuit breaker threshold
PROFIT_TARGET_PCT=0.50      # 50% profit target
STOP_LOSS_PCT=0.30          # 30% stop loss
MAX_OPEN_POSITIONS=5        # Max concurrent positions
```

### Watchlist
Edit in `agents/data_pipeline_agent.py`:
```python
self.watchlist = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "TSLA",
    "NVDA", "META", "SPY", "QQQ", "IWM"
]
```

### Scan Interval
Edit in `.env`:
```env
SCAN_INTERVAL_MINUTES=5  # Scan every 5 minutes
```

## 🗂️ Project Structure

```
options-AI-BOT/
├── agents/                 # Multi-agent system
│   ├── base_agent.py
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
│   ├── llm_service.py
│   └── database_service.py
├── utils/                  # Utilities
│   ├── logger.py
│   └── scheduler.py
├── data/                   # Database (created at runtime)
├── logs/                   # Log files (created at runtime)
├── main.py                 # Entry point
├── requirements.txt
├── .env.example
└── README.md
```

## 🔒 Security Best Practices

1. **Never commit `.env` file** - Contains sensitive API keys
2. **Use paper trading first** - Test thoroughly before live trading
3. **Start with small position sizes** - Gradually increase as you gain confidence
4. **Monitor regularly** - Check Discord notifications and logs
5. **Set conservative limits** - Better safe than sorry
6. **Keep API keys secure** - Use environment variables only

## 📈 Monitoring

### Logs
Logs are stored in `logs/trading.log` with rotation:
- Max size: 10 MB per file
- Retention: 30 days
- Compression: ZIP

### Database
Trade history and system state stored in `data/trading.db`:
- All trades with timestamps
- Position history
- AI analysis results
- System state
- Daily statistics

### Discord Notifications
Real-time notifications for:
- Trade executions (buy/sell)
- Profit targets reached
- Stop losses triggered
- Circuit breaker alerts
- System status changes
- Daily summaries

## 🧪 Testing

### Paper Trading
Always test with paper trading first:
```env
TRADING_MODE=paper
ALPACA_BASE_URL=https://paper-api.alpaca.markets
```

### Manual Testing
Use Discord commands or API endpoints:
```bash
# Via API
curl -X POST "http://localhost:8000/trade/manual?symbol=AAPL"

# Via Discord
/status
/positions
```

## 🐛 Troubleshooting

### Bot Not Responding
- Check Discord bot token is correct
- Verify bot has proper permissions
- Check bot is online in Discord server
- Review logs for errors

### No Trades Executing
- Verify trading mode is correct
- Check circuit breaker status (`/status`)
- Ensure system is not paused
- Review risk limits in configuration
- Check market hours (system pauses on weekends)

### API Connection Errors
- Verify Alpaca API keys are correct
- Check API base URL matches trading mode
- Ensure internet connection is stable
- Review Alpaca account status

### Database Errors
- Ensure `data/` directory exists and is writable
- Check disk space
- Review database logs

## 📝 License

This project is for educational purposes. Use at your own risk. Trading involves substantial risk of loss.

## ⚠️ Disclaimer

**IMPORTANT**: This software is provided for educational purposes only. Trading stocks and options involves substantial risk of loss. Past performance is not indicative of future results. The authors and contributors are not responsible for any financial losses incurred through the use of this software.

Always:
- Start with paper trading
- Understand the risks
- Never invest more than you can afford to lose
- Consult with a financial advisor
- Comply with all applicable laws and regulations

## 🤝 Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📧 Support

For issues and questions:
- Open an issue on GitHub
- Check existing issues for solutions
- Review logs for error details

## 🔄 Updates

To update the system:
```bash
git pull origin main
pip install -r requirements.txt --upgrade
```

## 🎯 Roadmap

Future enhancements:
- [ ] Web dashboard with real-time charts
- [ ] Backtesting framework
- [ ] More technical indicators
- [ ] Multi-timeframe analysis
- [ ] Portfolio optimization
- [ ] Machine learning models
- [ ] Telegram bot support
- [ ] Email notifications
- [ ] Advanced order types
- [ ] Options strategies (spreads, straddles, etc.)

---

**Happy Trading! 🚀📈**
