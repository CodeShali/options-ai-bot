# Complete Trading Workflow & Alerts

## 🔄 How Trading Decisions Are Made

Your system follows a **6-step automated workflow** that runs every 5 minutes during market hours.

---

## 📊 Complete Trading Workflow

```
┌─────────────────────────────────────────────────────────────┐
│  STEP 1: CIRCUIT BREAKER CHECK                              │
│  Risk Manager checks if daily loss limit reached            │
└─────────────┬───────────────────────────────────────────────┘
              │
              ▼
        [Triggered?]
         /        \
       YES        NO
        │          │
        ▼          ▼
   🚨 STOP    Continue
   Alert sent
        
┌─────────────────────────────────────────────────────────────┐
│  STEP 2: POSITION LIMITS CHECK                              │
│  Risk Manager checks available position slots               │
└─────────────┬───────────────────────────────────────────────┘
              │
              ▼
    [Slots Available?]
         /        \
       YES        NO
        │          │
        ▼          ▼
   Continue    Stop
              (Max 5 positions)

┌─────────────────────────────────────────────────────────────┐
│  STEP 3: SCAN FOR OPPORTUNITIES                             │
│  Data Pipeline scans watchlist (10 symbols)                 │
│  - Fetches current quotes                                   │
│  - Gets historical data                                     │
│  - Calculates technical indicators                          │
│  - Scores opportunities                                     │
└─────────────┬───────────────────────────────────────────────┘
              │
              ▼
    [Opportunities Found?]
         /        \
       YES        NO
        │          │
        ▼          ▼
   🔍 Alert    Stop
   "Found X    (Try again
   opportunities"  in 5 min)

┌─────────────────────────────────────────────────────────────┐
│  STEP 4: AI ANALYSIS                                        │
│  Strategy Agent analyzes top 5 opportunities with OpenAI    │
│  - Evaluates market conditions                              │
│  - Analyzes technical indicators                            │
│  - Calculates risk/reward                                   │
│  - Generates recommendation (BUY/HOLD/SELL)                 │
│  - Assigns confidence score (0-100%)                        │
└─────────────┬───────────────────────────────────────────────┘
              │
              ▼
    [BUY Signals with >60% confidence?]
         /        \
       YES        NO
        │          │
        ▼          ▼
   🤖 Alert    📊 Alert
   "X BUY      "No strong
   signals!"   buy signals"

┌─────────────────────────────────────────────────────────────┐
│  STEP 5: TRADE VALIDATION & EXECUTION                       │
│  For each BUY signal:                                       │
│  1. Risk Manager calculates position size                   │
│  2. Risk Manager validates trade                            │
│  3. Execution Agent places order                            │
└─────────────┬───────────────────────────────────────────────┘
              │
              ▼
    [Trade Approved?]
         /        \
       YES        NO
        │          │
        ▼          ▼
   ✅ Alert    ⛔ Alert
   "BUY        "Trade
   executed"   rejected"

┌─────────────────────────────────────────────────────────────┐
│  STEP 6: POSITION MONITORING (Every 2 minutes)              │
│  Monitor Agent checks all open positions                     │
│  - Checks profit targets (50%)                              │
│  - Checks stop losses (30%)                                 │
│  - Detects significant moves (>10%)                         │
│  - Triggers AI analysis for exits                           │
└─────────────┬───────────────────────────────────────────────┘
              │
              ▼
    [Exit Conditions Met?]
         /        \
       YES        NO
        │          │
        ▼          ▼
   🟢/🔴 Alert  Continue
   "SELL       monitoring
   executed"
```

---

## 🔔 All Alerts You'll Receive

### 1. **Scanning Phase** 🔍

#### Alert: Opportunities Found
```
🔍 Scan complete: Found 3 potential opportunities

Why? System scanned 10 symbols and found 3 with positive technical signals.

{
  "symbols": ["AAPL", "MSFT", "NVDA"],
  "analyzing": "Top 5 opportunities"
}
```

**When**: Every 5 minutes when scan finds opportunities
**Means**: System detected potential trades to analyze

---

### 2. **AI Analysis Phase** 🤖

#### Alert: Buy Signals Detected
```
🤖 AI Analysis: 2 BUY signal(s) detected!

{
  "signals": [
    {
      "symbol": "AAPL",
      "confidence": "75%",
      "risk": "LOW"
    },
    {
      "symbol": "MSFT",
      "confidence": "68%",
      "risk": "MEDIUM"
    }
  ]
}
```

**When**: After AI analyzes opportunities
**Means**: OpenAI GPT-4 recommends buying these stocks

#### Alert: No Buy Signals
```
📊 AI Analysis complete: No strong buy signals

{
  "analyzed": 3,
  "buy_signals": 0,
  "reason": "Confidence < 60% or HOLD/SELL recommendations"
}
```

**When**: AI doesn't find strong opportunities
**Means**: Market conditions not favorable, wait for next scan

---

### 3. **Trade Validation Phase** ⛔

#### Alert: Trade Rejected
```
⛔ Trade rejected: AAPL

Why? Insufficient buying power

{
  "reason": "Insufficient buying power",
  "symbol": "AAPL",
  "quantity": 10
}
```

**When**: Risk manager rejects a trade
**Means**: Trade didn't pass risk validation
**Common Reasons**:
- Insufficient buying power
- Position size too large
- Max positions reached
- Circuit breaker active

---

### 4. **Trade Execution Phase** ✅

#### Alert: Buy Executed
```
✅ BUY executed: 10 AAPL @ $150.25

Why? Position entered at $150.25, now at $150.25. 
AI confidence: 75%. Risk level: LOW.

{
  "confidence": 75,
  "reasoning": "Strong upward momentum with RSI at 45..."
}
```

**When**: Trade successfully executed
**Means**: You now own this position
**Includes**: Quantity, price, AI reasoning

---

### 5. **Position Monitoring Phase** 📊

#### Alert: Significant Move
```
📊 AAPL: UP 12.45%

Why? Position has moved UP by 12.45% (Entry: $150.00 → Current: $168.68). 
Profit target is 50% ($225.00). Need 37.55% more to hit target. 
Current profit: $1,868.00.

{
  "type": "SIGNIFICANT_MOVE",
  "severity": "INFO",
  "action_required": "REVIEW",
  "position": {...}
}
```

**When**: Position moves >10% (then every 5% after)
**Means**: Your position is moving significantly

#### Alert: Profit Target Reached
```
🎯 AAPL: Profit target reached at 52.34%!

Why? Position entered at $150.00, now at $228.51. 
Target was 50% ($225.00). Current profit: $7,851.00. 
Consider taking profits!

{
  "type": "PROFIT_TARGET",
  "severity": "INFO",
  "action_required": "SELL"
}
```

**When**: Position reaches 50% profit
**Means**: Your profit target hit, system will analyze exit

#### Alert: Stop Loss Triggered
```
⚠️ TSLA: Stop loss triggered at -31.45%!

Why? Position entered at $200.00, now at $137.10. 
Stop loss was 30% ($140.00). Current loss: -$6,290.00. 
Position should be closed to prevent further losses.

{
  "type": "STOP_LOSS",
  "severity": "WARNING",
  "action_required": "SELL"
}
```

**When**: Position loses 30%
**Means**: Stop loss triggered, system will analyze exit

---

### 6. **Exit Execution Phase** 🟢🔴

#### Alert: Sell Executed (Profit)
```
🟢 SELL executed: AAPL - P/L: $7,851.00

Why? Profit target reached at 52.34%!

{
  "reason": "Profit target reached"
}
```

**When**: Position sold for profit
**Means**: Trade closed with profit

#### Alert: Sell Executed (Loss)
```
🔴 SELL executed: TSLA - P/L: -$6,290.00

Why? Stop loss triggered at -31.45%!

{
  "reason": "Stop loss triggered"
}
```

**When**: Position sold for loss
**Means**: Trade closed to prevent further losses

---

### 7. **System Alerts** 🚨

#### Alert: Circuit Breaker
```
🚨 Circuit breaker triggered! Trading stopped.

{
  "daily_loss": -1050.00,
  "max_loss": -1000.00,
  "triggered": true
}
```

**When**: Daily loss exceeds $1,000
**Means**: Trading halted to prevent further losses

#### Alert: Emergency Stop
```
🚨 EMERGENCY STOP: All positions closed, system paused

{
  "positions_closed": 3,
  "total_pl": -450.00
}
```

**When**: You trigger emergency stop
**Means**: All positions forcibly closed

---

## 🎯 Decision-Making Process

### How Buy Decisions Are Made

```
1. TECHNICAL SCREENING (Data Pipeline)
   ├─ Price momentum > threshold
   ├─ Volume > average
   ├─ RSI in favorable range
   └─ Moving average crossovers
        │
        ▼
2. AI ANALYSIS (OpenAI GPT-4)
   ├─ Evaluates all technical data
   ├─ Considers market conditions
   ├─ Calculates risk/reward
   └─ Generates recommendation + confidence
        │
        ▼
3. RISK VALIDATION (Risk Manager)
   ├─ Confidence >= 60%?
   ├─ Position size within limits?
   ├─ Buying power sufficient?
   ├─ Circuit breaker OK?
   └─ Max positions not reached?
        │
        ▼
4. EXECUTION (If all checks pass)
   └─ Place market order via Alpaca
```

### How Sell Decisions Are Made

```
1. MONITORING (Every 2 minutes)
   ├─ Check profit target (50%)
   ├─ Check stop loss (30%)
   └─ Check significant moves (>10%)
        │
        ▼
2. AI EXIT ANALYSIS (If conditions met)
   ├─ Evaluate current position
   ├─ Consider market conditions
   ├─ Recommend: EXIT, HOLD, or PARTIAL_EXIT
   └─ Provide confidence score
        │
        ▼
3. RISK CONFIRMATION (Risk Manager)
   ├─ Verify exit conditions
   └─ Approve exit
        │
        ▼
4. EXECUTION (If approved)
   └─ Place sell order via Alpaca
```

---

## 📈 Example Complete Trade Cycle

### Minute 0: Scan
```
🔍 Scan complete: Found 3 potential opportunities
Symbols: AAPL, MSFT, NVDA
```

### Minute 1: Analysis
```
🤖 AI Analysis: 1 BUY signal(s) detected!
AAPL - Confidence: 75%, Risk: LOW
```

### Minute 2: Execution
```
✅ BUY executed: 10 AAPL @ $150.00
AI reasoning: "Strong upward momentum..."
```

### Minute 10: Monitoring (8 minutes later)
```
📊 AAPL: UP 10.5%
Entry: $150.00 → Current: $165.75
Profit: $1,575.00
```

### Minute 25: Monitoring (15 minutes later)
```
📊 AAPL: UP 15.8%
Entry: $150.00 → Current: $173.70
Profit: $2,370.00
```

### Minute 45: Profit Target (20 minutes later)
```
🎯 AAPL: Profit target reached at 50.2%!
Entry: $150.00 → Current: $225.30
Profit: $7,530.00
```

### Minute 46: AI Exit Analysis
```
AI recommends: EXIT
Confidence: 85%
Reasoning: "Profit target reached, momentum slowing..."
```

### Minute 47: Exit Execution
```
🟢 SELL executed: AAPL - P/L: $7,530.00
Reason: Profit target reached
```

**Total Time**: 47 minutes from scan to profit!

---

## ⚙️ Configuration

### Alert Frequency
- **Scanning**: Every 5 minutes
- **Monitoring**: Every 2 minutes
- **Significant Move**: Initial + every 5% change
- **Profit/Loss Targets**: Once when reached

### Thresholds (Configurable in `.env`)
```env
PROFIT_TARGET_PCT=0.50    # 50% profit target
STOP_LOSS_PCT=0.30        # 30% stop loss
MAX_POSITION_SIZE=5000    # Max $ per position
MAX_OPEN_POSITIONS=5      # Max concurrent positions
SCAN_INTERVAL_MINUTES=5   # Scan frequency
```

### AI Confidence Threshold
- **Minimum**: 60% confidence required
- **Location**: `orchestrator_agent.py` line 170
- **Adjustable**: Change `>= 60` to higher/lower

---

## 🎓 Understanding the Alerts

### Alert Priority Levels

**🚨 CRITICAL** (Immediate action)
- Circuit breaker triggered
- Emergency stop
- System errors

**⚠️ WARNING** (Review soon)
- Stop loss triggered
- Trade rejected
- Low buying power

**📊 INFO** (Informational)
- Opportunities found
- Buy signals detected
- Significant moves
- Profit targets

**✅ SUCCESS** (Confirmation)
- Trade executed
- Position closed

---

## 💡 Pro Tips

### Reduce Alert Noise
1. Increase confidence threshold (60% → 70%)
2. Increase scan interval (5 min → 10 min)
3. Increase significant move threshold (10% → 15%)

### Get More Alerts
1. Decrease confidence threshold (60% → 50%)
2. Decrease scan interval (5 min → 3 min)
3. Add more symbols to watchlist

### Understand AI Decisions
- Check `reasoning` field in alerts
- Review logs: `tail -f logs/trading.log`
- Use `/trades` command to see history

---

## 🔍 Monitoring Your System

### Discord Commands
```
/status      - Current system state
/positions   - All open positions
/trades      - Recent trade history
/performance - Performance metrics
```

### Log Files
```bash
# Watch live
tail -f logs/trading.log

# Search for specific alerts
grep "BUY executed" logs/trading.log
grep "SELL executed" logs/trading.log
grep "Alert" logs/trading.log
```

### Database Queries
```bash
# View all trades
sqlite3 data/trading.db "SELECT * FROM trades ORDER BY timestamp DESC LIMIT 10;"

# View analysis history
sqlite3 data/trading.db "SELECT * FROM analysis_history ORDER BY timestamp DESC LIMIT 10;"
```

---

## 🎯 Summary

Your system will send alerts for:

✅ **Opportunities found** (every scan)
✅ **AI analysis results** (buy signals or no signals)
✅ **Trade rejections** (with reasons)
✅ **Trade executions** (buys and sells)
✅ **Position movements** (>10%, then every 5%)
✅ **Profit targets** (50% gain)
✅ **Stop losses** (30% loss)
✅ **System events** (circuit breaker, errors)

**You'll never miss a trading decision or important event!** 🎉

---

*Last Updated: 2025-10-11*
