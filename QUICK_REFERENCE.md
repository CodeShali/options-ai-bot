# 🚀 QUICK REFERENCE GUIDE

## 📱 **DISCORD COMMANDS**

### **Daily Admin Workflow**
```
Morning Routine:
1. /simulate              → Test system health
2. /sentiment SPY         → Check market sentiment
3. /status                → Verify system status
4. /account               → Check buying power
5. /positions             → Review open positions
```

### **All Commands**

#### **📊 Information**
| Command | Description | Example |
|---------|-------------|---------|
| `/status` | System overview | `/status` |
| `/account` | Account details | `/account` |
| `/positions` | Open positions | `/positions` |
| `/quote <symbol>` | Stock quote | `/quote AAPL` |
| `/sentiment <symbol>` | 📊 Sentiment analysis | `/sentiment TSLA` |
| `/watchlist` | View watchlist | `/watchlist` |
| `/watchlist-add <symbol>` | Add symbol | `/watchlist-add MSFT` |
| `/watchlist-remove <symbol>` | Remove symbol | `/watchlist-remove SPY` |
| `/trades [limit]` | Recent trades | `/trades 10` |
| `/performance [days]` | Performance metrics | `/performance 7` |

#### **⚙️ Control**
| Command | Description | Example |
|---------|-------------|---------|
| `/pause` | Pause trading | `/pause` |
| `/resume` | Resume trading | `/resume` |
| `/scan-now` | Trigger scan | `/scan-now` |
| `/simulate` | 🧪 Run system test | `/simulate` |
| `/switch-mode <mode>` | Switch paper/live | `/switch-mode paper` |

#### **💼 Trading**
| Command | Description | Example |
|---------|-------------|---------|
| `/sell <symbol>` | Sell position | `/sell AAPL` |
| `/close-all` | ⚠️ Close all | `/close-all` |

#### **🛡️ Risk**
| Command | Description | Example |
|---------|-------------|---------|
| `/limits` | View limits | `/limits` |
| `/update-limit <type> <value>` | ⚙️ Update limit | `/update-limit profit_target 60` |
| `/circuit-breaker` | Check breaker | `/circuit-breaker` |

#### **ℹ️ Help**
| Command | Description | Example |
|---------|-------------|---------|
| `/help` | Show all commands | `/help` |

---

## 🎯 **UPDATE LIMIT OPTIONS**

### **Available Limit Types**
```
1. max_position_size      → $100 - $50,000
2. max_daily_loss         → $100 - $10,000
3. profit_target          → 5% - 200%
4. stop_loss              → 5% - 50%
5. max_positions          → 1 - 20
6. options_max_contracts  → 1 - 10
7. options_max_premium    → $50 - $2,000
```

### **Examples**
```
/update-limit profit_target 60
/update-limit stop_loss 25
/update-limit max_daily_loss 1500
/update-limit options_max_contracts 3
/update-limit max_position_size 7500
```

---

## 📊 **SENTIMENT SCORES**

### **Score Interpretation**
```
+0.5 to +1.0  = STRONG POSITIVE → +5% confidence
+0.3 to +0.5  = POSITIVE        → +3% confidence
-0.3 to +0.3  = NEUTRAL         → No change
-0.5 to -0.3  = NEGATIVE        → -5% confidence
-1.0 to -0.5  = STRONG NEGATIVE → -10% confidence
```

### **Confidence Thresholds**
```
Original Thresholds:
- 75%+ confidence → Call option
- 60-74% confidence → Stock
- <60% confidence → Skip

With Sentiment Adjustment:
- Can push 70%+ to 75%+ → Options
- Can reduce 75%+ to <75% → Stock
- Can reduce 60%+ to <60% → Skip
```

---

## 🧪 **SIMULATION TESTS**

### **10 Tests Run**
1. ✅ Stock Buy (Moderate Signal)
2. ✅ Call Option Buy (Strong Signal)
3. ✅ Put Option Buy (Phase 2)
4. ✅ Profit Target Exit (50%)
5. ✅ Stop Loss Exit (30%)
6. ✅ Options Expiration (7 DTE)
7. ✅ Circuit Breaker ($1000)
8. ✅ Position Limits (Max 5)
9. ✅ Risk Validation
10. ✅ Sentiment Analysis

### **Success Rate**
- **90%+** = Excellent ✅
- **80-89%** = Good ⚠️
- **<80%** = Issues ❌

---

## 🎯 **TRADING DECISION FLOW**

### **Complete Flow with Sentiment**
```
1. Scan finds opportunity (score 85)
   ↓
2. AI analyzes (72% BUY confidence)
   ↓
3. Sentiment analysis (automatic):
   - News: +0.7 (POSITIVE)
   - Market: +0.5 (POSITIVE)
   - Social: +0.4 (POSITIVE)
   - Overall: +0.58
   ↓
4. Confidence adjusted: 72% → 77%
   ↓
5. Decision: 77% = CALL OPTION
   ↓
6. Select contract:
   - Strike: $180 (1 OTM)
   - Expiration: 35 DTE
   - Premium: $3.50
   ↓
7. Risk validation (6 checks):
   - Premium: $700 < $1,000 ✅
   - DTE: 35 days ✅
   - Contracts: 2 ✅
   - Buying power: OK ✅
   - Circuit breaker: OK ✅
   - Position limits: OK ✅
   ↓
8. Execute: BUY 2 contracts
   ↓
9. Discord: Thread + notification
```

---

## 📈 **MONITORING FLOW**

### **Every 2 Minutes**
```
Check all positions:

Stock Positions:
├─ Profit >= 50%? → Alert + AI exit
├─ Loss >= 30%? → Alert + AI exit
└─ Move > 10%? → Info alert

Options Positions:
├─ DTE <= 7 days? → FORCE CLOSE
├─ Profit >= 50%? → Alert + AI exit
├─ Loss >= 30%? → Alert + AI exit
└─ Move > 10%? → Info alert
```

---

## 🔧 **SYSTEM FILES**

### **Configuration**
```
.env                      → Environment variables
config/settings.py        → System settings
```

### **Services**
```
services/alpaca_service.py      → Alpaca API
services/llm_service.py         → OpenAI GPT
services/database_service.py    → SQLite DB
services/sentiment_service.py   → Sentiment analysis
services/simulation_service.py  → System testing
```

### **Agents**
```
agents/orchestrator_agent.py    → Main coordinator
agents/strategy_agent.py        → AI analysis + sentiment
agents/risk_manager_agent.py    → Risk validation
agents/execution_agent.py       → Order execution
agents/monitor_agent.py         → Position monitoring
agents/data_pipeline_agent.py   → Data fetching
```

### **Discord**
```
bot/discord_bot.py        → Discord commands
```

### **Logs**
```
logs/trading.log          → All system logs
```

---

## 🚨 **TROUBLESHOOTING**

### **Check System Status**
```bash
# View logs
tail -f logs/trading.log

# Check if running
lsof -ti:8000

# Check API
curl http://localhost:8000/
```

### **Common Issues**

#### **Simulation Fails**
```
Issue: /simulate returns error
Fix: Check orchestrator is initialized
     Verify all agents started
```

#### **Limits Not Updating**
```
Issue: /update-limit doesn't work
Fix: Check value is in valid range
     Verify settings module imported
```

#### **Sentiment Errors**
```
Issue: Sentiment analysis fails
Fix: Check LLM service is running
     Verify OpenAI API key set
```

#### **No Options Trades**
```
Issue: System only trades stocks
Fix: Signals not strong enough (need 75%+)
     Check sentiment isn't reducing confidence
     Verify options trading enabled in .env
```

---

## 📊 **CURRENT SETTINGS**

### **Default Values**
```
Trading:
- Max Position Size: $5,000
- Max Daily Loss: $1,000
- Profit Target: 50%
- Stop Loss: 30%
- Max Positions: 5

Options:
- Max Contracts: 2
- Max Premium: $500
- Min DTE: 30 days
- Max DTE: 45 days
- Close DTE: 7 days
- Strike Preference: OTM
- OTM Strikes: 1

Scanning:
- Interval: 5 minutes
- Watchlist: 10 symbols
```

---

## 🎯 **QUICK TIPS**

### **For Best Results**
1. ✅ Run `/simulate` every morning
2. ✅ Check `/sentiment SPY` for market
3. ✅ Monitor Discord notifications
4. ✅ Review logs regularly
5. ✅ Adjust limits as needed

### **Red Flags**
1. ⚠️ Simulation success rate < 80%
2. ⚠️ Strong negative sentiment
3. ⚠️ Circuit breaker triggered
4. ⚠️ Multiple failed validations
5. ⚠️ Errors in logs

### **Good Practices**
1. ✅ Start with conservative limits
2. ✅ Test in paper mode first
3. ✅ Monitor closely initially
4. ✅ Document what works
5. ✅ Adjust gradually

---

## 📱 **NOTIFICATION EXAMPLES**

### **Options Buy**
```
✅ OPTIONS BUY: 2 AAPL call $180 exp 2025-12-20 @ $3.50
Type: options
Confidence: 77% (adjusted from 72% by sentiment)
DTE: 35 days
Total cost: $700.00
Sentiment: POSITIVE (+0.58)
```

### **Stock Buy**
```
✅ BUY executed: 28 MSFT @ $175.23
Confidence: 68%
Reasoning: Moderate bullish signal | Sentiment: Neutral sentiment, no adjustment
```

### **Profit Target**
```
🎯 AAPL option: Profit target reached at 52%!
Entry: $3.50 → Current: $5.32
Profit: $364.00
DTE: 28 days
Action: Consider taking profits
```

### **Stop Loss**
```
⚠️ TSLA option: Stop loss triggered at -31%!
Entry: $4.20 → Current: $2.90
Loss: -$260.00
DTE: 22 days
Action: Close to prevent further losses
```

### **Expiration**
```
⏰ AAPL option expires in 7 days!
Option: Call $180 exp 2025-12-20
Only 7 days remaining. Close to avoid theta decay.
Current P/L: $180.00 (25.7%)
Action: FORCE CLOSE
```

---

## 🎓 **LEARNING RESOURCES**

### **Documentation**
- `HOW_TRADING_WORKS.md` - Complete system explanation
- `OPTIONS_IMPLEMENTATION_PLAN.md` - Options details
- `PHASE1_COMPLETE.md` - Phase 1 summary
- `NEW_FEATURES_COMPLETE.md` - New features guide
- `FINAL_STATUS.md` - Current status
- `QUICK_REFERENCE.md` - This guide

### **Key Concepts**
- **DTE** - Days To Expiration
- **OTM** - Out of The Money
- **Premium** - Option price per share
- **Contracts** - 1 contract = 100 shares
- **Sentiment** - Market/news/social mood
- **Confidence** - AI certainty (0-100%)

---

## 🚀 **GETTING STARTED**

### **First Time Setup**
1. ✅ System already running
2. ✅ Discord bot connected
3. ✅ All features enabled

### **First Commands to Try**
```
1. /help              → See all commands
2. /status            → Check system
3. /simulate          → Test everything
4. /sentiment SPY     → Check market
5. /watchlist         → View symbols
```

### **Daily Routine**
```
Morning (8:00 AM):
- /simulate
- /sentiment SPY
- /status
- /account

During Market (9:30 AM - 4:00 PM):
- Monitor Discord notifications
- Check position threads
- Review alerts

Evening (After 4:00 PM):
- /performance 1
- /positions
- Review logs
```

---

## 📞 **SUPPORT**

### **Check Logs**
```bash
tail -f logs/trading.log
```

### **Check System**
```bash
lsof -ti:8000  # Should return PID
```

### **Restart System**
```bash
lsof -ti:8000 | xargs kill -9
source venv/bin/activate && python main.py
```

---

## ✅ **SYSTEM STATUS**

```
✅ Trading System: RUNNING
✅ Discord Bot: CONNECTED
✅ Options Trading: ENABLED
✅ Stock Trading: ENABLED
✅ Sentiment Analysis: ENABLED
✅ Simulation: READY
✅ Dynamic Limits: READY
✅ Mode: PAPER
✅ All Features: OPERATIONAL
```

---

**Everything is ready to use!** 🎯📈

*Last Updated: 2025-10-12 12:14 AM*
