# TARA Trading System - Operational Guide

**Last Updated:** October 21, 2025  
**Version:** 2.0  
**Status:** Production Ready

---

## 🚀 Quick Start

### Starting the System

```bash
cd /Users/shashank/Documents/options-AI-BOT
python3 main.py
```

**Expected Output:**
```
✅ Trading system started successfully
Mode: PAPER
API: http://0.0.0.0:8000
🌟 TARA logged in as Tara Assistant#7936
```

### Stopping the System

```bash
# Graceful shutdown
Ctrl+C

# Force kill (if needed)
kill $(lsof -ti:8000)
```

---

## 🎮 Discord Commands

### Trading Commands

| Command | Description | Example |
|---------|-------------|---------|
| `/buy` | Buy stock with AI analysis | `/buy AAPL 10` |
| `/buy-option` | Buy options with Greeks | `/buy-option AAPL call 1000` |
| `/sell` | Sell a position | `/sell AAPL` |
| `/scan` | Manual market scan | `/scan` |
| `/positions` | View all positions | `/positions` |
| `/account` | View account info | `/account` |

### System Commands

| Command | Description | Example |
|---------|-------------|---------|
| `/status` | System status | `/status` |
| `/pause` | Pause trading | `/pause` |
| `/resume` | Resume trading | `/resume` |
| `/limits` | View risk limits | `/limits` |
| `/api-status` | API usage stats | `/api-status` |

### Analysis Commands

| Command | Description | Example |
|---------|-------------|---------|
| `/quote` | Get stock quote | `/quote AAPL` |
| `/analyze` | Detailed analysis | `/analyze AAPL` |
| `/sentiment` | Sentiment analysis | `/sentiment AAPL` |
| `/performance` | Performance metrics | `/performance` |

### Watchlist Commands

| Command | Description | Example |
|---------|-------------|---------|
| `/watchlist` | View watchlist | `/watchlist` |
| `/watchlist-add` | Add symbol | `/watchlist-add AAPL` |
| `/watchlist-remove` | Remove symbol | `/watchlist-remove AAPL` |

---

## 💬 Natural Language Commands

### Buy Commands
```
"Buy 10 shares of AAPL"
"I want to buy TSLA"
"Purchase 5 NVDA shares"
"Find call options for AAPL"
"Show me put options for SPY under $1000"
```

### Sell Commands
```
"Sell my AAPL position"
"Close all positions"
"Sell half of my TSLA"
```

### Analysis Commands
```
"Should I buy AAPL?"
"What's the sentiment on TSLA?"
"Analyze NVDA for me"
"How are my positions doing?"
```

### Stop Loss Commands
```
"Set stop loss on AAPL at 5%"
"Set stop losses on all positions at 10%"
"Move my TSLA stop loss to 8%"
```

---

## ⚙️ Configuration

### Environment Variables

**Required:**
```bash
# Alpaca API
ALPACA_API_KEY=your_key_here
ALPACA_SECRET_KEY=your_secret_here
ALPACA_BASE_URL=https://paper-api.alpaca.markets  # Paper trading

# Discord
DISCORD_BOT_TOKEN=your_token_here
DISCORD_CHANNEL_ID=your_channel_id

# AI APIs
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_claude_key  # Optional, OpenAI is fallback
```

**Optional:**
```bash
# Trading Settings
AUTO_TRADING_ENABLED=false  # Manual approval required
MAX_DAILY_LOSS=1000  # Circuit breaker limit
MAX_POSITIONS=10  # Maximum concurrent positions

# Logging
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR
```

### Config Files

**`config/settings.py`** - Main configuration
```python
# Trading Mode
trading_mode = "PAPER"  # or "LIVE"

# Risk Management
max_daily_loss = 1000
max_positions = 10
position_size_pct = 0.05  # 5% of equity per trade

# Auto Trading
auto_trading_enabled = False  # Requires manual approval
```

---

## 📊 Monitoring

### System Health Checks

**1. Check if system is running:**
```bash
curl http://localhost:8000/health
```

**2. Check Discord bot status:**
- Bot should show as "Online" in Discord
- Try `/status` command

**3. Check logs:**
```bash
tail -f logs/tara_$(date +%Y%m%d).log
```

### Key Metrics to Monitor

**System Status:**
- ✅ System running
- ✅ Discord bot connected
- ✅ API calls within limits
- ✅ No circuit breaker triggered

**Trading Activity:**
- Scans per hour: 12 (every 5 min)
- Opportunities found: Varies
- Trades executed: Depends on signals
- Position count: < max_positions

**Performance:**
- Daily P&L
- Win rate
- Average trade duration
- Risk-adjusted returns

---

## 🔧 Troubleshooting

### Common Issues

#### 1. **Bot Not Responding**

**Symptoms:** Discord commands don't work

**Solutions:**
```bash
# Check if bot is running
ps aux | grep python

# Check Discord connection
# Look for "TARA logged in" in logs

# Restart bot
kill $(lsof -ti:8000)
python3 main.py
```

#### 2. **Claude API Errors**

**Symptoms:** "Credit balance too low" errors

**Solution:** System automatically falls back to OpenAI
```
✅ Automatic fallback configured
No action needed - OpenAI will be used
```

#### 3. **System Paused**

**Symptoms:** No scans or trades happening

**Solution:**
```
/resume  # In Discord
```

#### 4. **Circuit Breaker Triggered**

**Symptoms:** "Daily loss limit reached"

**Solution:**
```
# Wait until next day (auto-resets at 9:30 AM ET)
# Or manually reset (use with caution):
/reset-circuit-breaker
```

#### 5. **API Rate Limits**

**Symptoms:** "Rate limit exceeded" errors

**Solution:**
```
# Check current usage
/api-status

# System automatically throttles
# Wait a few minutes for limit to reset
```

---

## 🔄 Daily Operations

### Morning Routine (Before Market Open)

**1. Start System (if not running):**
```bash
python3 main.py
```

**2. Check System Status:**
```
/status  # In Discord
```

**3. Review Watchlist:**
```
/watchlist
```

**4. Check Account:**
```
/account
```

**5. Ensure System is Unpaused:**
```
/resume  # If needed
```

### During Market Hours

**Monitor:**
- Discord notifications for opportunities
- Position P&L updates
- Alert messages

**Actions:**
- Approve/reject trade recommendations
- Adjust stop losses if needed
- Monitor risk limits

### End of Day

**1. Review Performance:**
```
/performance
```

**2. Check Positions:**
```
/positions
```

**3. Review Trades:**
```
/trades
```

**4. Optional - Pause System:**
```
/pause  # If you want to stop overnight
```

---

## 📈 Trading Workflows

### Workflow 1: Automated Scanning

**Frequency:** Every 5 minutes during market hours

**Process:**
1. System scans watchlist
2. Identifies opportunities
3. Sends Discord notification
4. Waits for approval (if auto-trading disabled)
5. Executes trade on approval
6. Monitors position

**User Action Required:**
- Review opportunity notification
- Click ✅ to approve or ❌ to reject

### Workflow 2: Manual Buy (Stock)

**Command:** `/buy AAPL 10`

**Process:**
1. System analyzes AAPL
2. Shows current price, cost, buying power
3. Displays confirmation dialog
4. User clicks ✅ Confirm or ❌ Cancel
5. Order executes on confirmation

### Workflow 3: Manual Buy (Options)

**Command:** `/buy-option AAPL call 1000`

**Process:**
1. System analyzes options chain
2. Calculates Greeks for all contracts
3. Ranks by quality score
4. Shows top 3 recommendations
5. User selects option to buy
6. Order executes

### Workflow 4: Position Monitoring

**Frequency:** Every 2 minutes

**Process:**
1. System checks all positions
2. Calculates P&L
3. Checks for alerts:
   - Profit target (15%+)
   - Stop loss (10%-)
   - Significant moves (10%+)
4. Sends alerts to Discord
5. Suggests actions if needed

### Workflow 5: Exit Management

**Triggers:**
- Stop loss hit
- Take profit target reached
- Strategy exit signal
- Manual sell command

**Process:**
1. Exit signal detected
2. Validation checks
3. Sell order placed
4. Position closed
5. Performance recorded
6. Discord notification sent

---

## 🎯 Best Practices

### Risk Management

**1. Start Small:**
- Begin with paper trading
- Test strategies thoroughly
- Gradually increase position sizes

**2. Use Stop Losses:**
```
"Set stop losses on all positions at 10%"
```

**3. Monitor Daily Loss:**
```
/limits  # Check circuit breaker status
```

**4. Diversify:**
- Don't put all capital in one position
- Use 2-5% position sizing
- Spread across sectors

### Trading Discipline

**1. Follow the System:**
- Trust the AI analysis
- Don't override without good reason
- Review performance regularly

**2. Avoid Emotional Trading:**
- Let the system make decisions
- Don't chase losses
- Take profits when targets hit

**3. Regular Reviews:**
- Daily performance check
- Weekly strategy review
- Monthly optimization

### System Maintenance

**1. Keep System Updated:**
```bash
git pull  # Get latest updates
pip install -r requirements.txt  # Update dependencies
```

**2. Monitor Logs:**
```bash
tail -f logs/tara_$(date +%Y%m%d).log
```

**3. Backup Configuration:**
```bash
cp .env .env.backup
cp config/settings.py config/settings.py.backup
```

---

## 🚨 Emergency Procedures

### Emergency Stop

**When to Use:**
- Unexpected market conditions
- System malfunction
- Need immediate halt

**How:**
```
/pause  # In Discord

# Or emergency stop:
/emergency-stop  # Closes all positions and pauses
```

### Recovery Procedures

**1. System Crash:**
```bash
# Restart system
python3 main.py

# Check positions
/positions

# Resume if needed
/resume
```

**2. Runaway Losses:**
```bash
# Emergency stop
/emergency-stop

# Review what happened
/trades
/performance

# Adjust risk limits before resuming
```

**3. API Issues:**
```bash
# Check API status
/api-status

# Wait for rate limits to reset
# System will auto-retry
```

---

## 📞 Support

### Getting Help

**1. Check Logs:**
```bash
tail -100 logs/tara_$(date +%Y%m%d).log
```

**2. Review Documentation:**
- SYSTEM_ARCHITECTURE.md
- WORKFLOW_GUIDE.md
- TESTING_VALIDATION.md

**3. Common Solutions:**
- Restart system
- Check environment variables
- Verify API keys
- Check internet connection

---

## ✅ Pre-Market Checklist

- [ ] System is running
- [ ] Discord bot is online
- [ ] System is unpaused (`/resume`)
- [ ] Watchlist is updated
- [ ] Risk limits are appropriate
- [ ] Account has buying power
- [ ] No circuit breaker triggered
- [ ] API keys are valid
- [ ] Logs are clean (no errors)

---

## 📝 Daily Log Template

```
Date: ___________
Market: Open/Closed
System Status: Running/Paused

Scans Performed: ___
Opportunities Found: ___
Trades Executed: ___
Positions Opened: ___
Positions Closed: ___

Daily P&L: $___
Win Rate: ___%
Largest Winner: $___
Largest Loser: $___

Notes:
_________________
_________________
```

---

*For architecture details, see SYSTEM_ARCHITECTURE.md*  
*For testing procedures, see TESTING_VALIDATION.md*  
*For workflow details, see WORKFLOW_GUIDE.md*
