# Quick Setup Guide

## Step-by-Step Setup Instructions

### 1. Get Alpaca API Keys

1. Go to [Alpaca](https://alpaca.markets/)
2. Sign up for a free account
3. Navigate to "Paper Trading" section
4. Generate API keys (Key ID and Secret Key)
5. Save these keys - you'll need them for `.env`

### 2. Create Discord Bot

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Click "New Application"
3. Give it a name (e.g., "Trading Bot")
4. Go to "Bot" tab → "Add Bot"
5. Under "Token", click "Copy" to get your bot token
6. Enable these Privileged Gateway Intents:
   - ✅ Message Content Intent
   - ✅ Server Members Intent (optional)
7. Go to OAuth2 → URL Generator:
   - Scopes: `bot`, `applications.commands`
   - Bot Permissions: 
     - Send Messages
     - Read Messages/View Channels
     - Use Slash Commands
     - Embed Links
     - Add Reactions
8. Copy the generated URL and open it to invite bot to your server

### 3. Get Discord Channel ID

1. Open Discord
2. Go to User Settings → Advanced
3. Enable "Developer Mode"
4. Right-click on the channel where you want notifications
5. Click "Copy ID"
6. Save this ID - you'll need it for `.env`

### 4. Get OpenAI API Key

1. Go to [OpenAI Platform](https://platform.openai.com/)
2. Sign up or log in
3. Go to "API Keys" section
4. Create a new API key
5. Copy the key - you'll need it for `.env`

### 5. Install Python Dependencies

```bash
# Make sure you're in the project directory
cd options-AI-BOT

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
# venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 6. Configure Environment Variables

```bash
# Copy example env file
cp .env.example .env

# Edit .env with your favorite editor
nano .env  # or vim, code, etc.
```

Fill in your credentials:

```env
# Alpaca API (from Step 1)
ALPACA_API_KEY=PK...
ALPACA_SECRET_KEY=...
ALPACA_BASE_URL=https://paper-api.alpaca.markets

# Discord (from Steps 2 & 3)
DISCORD_BOT_TOKEN=...
DISCORD_CHANNEL_ID=123456789...

# OpenAI (from Step 4)
OPENAI_API_KEY=sk-...

# Trading Configuration (adjust as needed)
TRADING_MODE=paper
MAX_POSITION_SIZE=5000
MAX_DAILY_LOSS=1000
PROFIT_TARGET_PCT=0.50
STOP_LOSS_PCT=0.30
MAX_OPEN_POSITIONS=5
```

### 7. Create Required Directories

```bash
mkdir -p data logs
```

### 8. Test Configuration

```bash
# Test that all imports work
python -c "from config import settings; print('Config loaded successfully')"

# Verify environment variables
python -c "from config import settings; print(f'Trading Mode: {settings.trading_mode}')"
```

### 9. Start the System

```bash
python main.py
```

You should see:
```
============================================================
OPTIONS TRADING SYSTEM
============================================================
Trading Mode: PAPER
Max Position Size: $5,000.00
Max Daily Loss: $1,000.00
Profit Target: 50%
Stop Loss: 30%
Scan Interval: 5 minutes
============================================================
```

### 10. Test Discord Bot

- `/status` - Should show system status
- `/positions` - Should show open positions (likely empty at first)
- `/help` - Should show available commands
## Verification Checklist

- [ ] Alpaca API keys configured
- [ ] Discord bot created and invited to server
- [ ] Discord channel ID configured
- [ ] OpenAI API key configured
- [ ] `.env` file created with all credentials
- [ ] `data/` and `logs/` directories exist
- [ ] Discord bot responds to commands
- [ ] API accessible at http://localhost:8000/docs
## Common Issues

### "Module not found" errors
```bash
# Make sure virtual environment is activated
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Reinstall dependencies
pip install -r requirements.txt
```

### Discord bot not responding
- Check bot token is correct in `.env`
- Verify bot is online in Discord server
- Ensure bot has proper permissions
- Check channel ID is correct

### Alpaca API errors
- Verify API keys are correct
- Check you're using paper trading URL for paper mode
- Ensure Alpaca account is active

### Database errors
- Ensure `data/` directory exists and is writable
- Check disk space
- Try deleting `data/trading.db` to start fresh

## Next Steps

1. **Monitor the logs**: `tail -f logs/trading.log`
2. **Check the API**: Open http://localhost:8000/docs
3. **Watch Discord**: Notifications will appear in your configured channel
4. **Review positions**: Use `/status` and `/positions` commands
5. **Test manually**: Try `/sell <symbol>` or manual trades via API

## Safety Reminders

⚠️ **IMPORTANT**:
- System starts in PAPER trading mode by default
- Test thoroughly before switching to live trading
- Start with small position sizes
- Monitor regularly, especially during market hours
- Set conservative risk limits
- Never invest more than you can afford to lose

## Getting Help

If you encounter issues:
1. Check the logs in `logs/trading.log`
2. Review error messages carefully
3. Verify all configuration in `.env`
4. Check the troubleshooting section in README.md
5. Open an issue on GitHub with:
   - Error message
   - Relevant log entries
   - Steps to reproduce

---

**You're all set! Happy trading! 🚀**
