# 📚 DISCORD COMMANDS - DETAILED EXPLANATION

**Last Updated:** October 12, 2025 14:10:00

---

## 📊 `/sentiment` COMMAND - DEEP DIVE

### What It Does
The `/sentiment` command performs **comprehensive AI-powered sentiment analysis** for any stock symbol using multiple data sources.

### Data Sources Used
1. **NewsAPI** - Fetches real news headlines (last 7 days)
2. **Alpaca Market Data** - Price action and technical indicators
3. **OpenAI GPT-4o** - AI analysis of news and market data

### Exact Flow

```
User: /sentiment AAPL

Step 1: Fetch News Headlines
├─ Calls NewsAPI for AAPL news (last 7 days)
├─ Gets up to 10 recent headlines
└─ Example: "Apple announces new iPhone", "AAPL beats earnings"

Step 2: AI News Sentiment Analysis (OpenAI GPT-4o)
├─ Sends headlines to OpenAI
├─ Prompt: "Analyze sentiment of these headlines..."
├─ AI returns:
│   ├─ Sentiment score (-1.0 to 1.0)
│   ├─ Sentiment label (POSITIVE/NEGATIVE/NEUTRAL)
│   ├─ Key themes (e.g., "product launch", "earnings beat")
│   ├─ Impact level (HIGH/MEDIUM/LOW)
│   └─ Reasoning (AI explanation)
└─ Cost: ~$0.001 per analysis

Step 3: Market Sentiment Analysis
├─ Fetches current price data from Alpaca
├─ Calculates technical indicators:
│   ├─ RSI (Relative Strength Index)
│   ├─ Price vs SMA (Simple Moving Average)
│   ├─ Volume trends
│   └─ Price momentum
└─ Generates market sentiment score

Step 4: Social Sentiment (Future Feature)
└─ Currently returns neutral (Phase 3 feature)

Step 5: AI Interpretation (OpenAI GPT-4o)
├─ Combines all sentiment data
├─ Sends to OpenAI for final interpretation
├─ AI provides overall analysis
└─ Cost: ~$0.001 per interpretation

Step 6: Display Results
└─ Shows beautiful Discord embed with all data
```

### OpenAI Usage
**YES, it calls OpenAI twice:**
1. **First call:** Analyze news headlines sentiment
2. **Second call:** Provide overall interpretation

**Total cost per `/sentiment` command:** ~$0.002 (very cheap!)

### Example Output

```
📊 Sentiment Analysis: AAPL

Overall Sentiment: BULLISH 🟢
Confidence Score: 0.75 (75%)

📰 News Sentiment: POSITIVE
  Score: 0.8
  Impact: HIGH
  Themes:
    • Product innovation
    • Strong earnings
    • Market leadership
  
  Recent Headlines:
    • Apple unveils groundbreaking AI features
    • AAPL stock surges on earnings beat
    • Analysts raise price targets

📈 Market Sentiment: POSITIVE
  Score: 0.7
  Indicators:
    • RSI: 65 (Bullish momentum)
    • Price vs SMA: +5.2% (Above trend)
    • Volume: 1.5x average (Strong interest)
  
  Reasoning: Strong upward momentum with
  healthy volume confirmation

🤖 AI Interpretation:
  "Apple shows strong bullish sentiment across
  all indicators. News catalysts are positive
  with product innovation and earnings strength.
  Market technicals confirm upward momentum.
  High confidence for continued strength."

💬 Social Sentiment: NEUTRAL
  (Phase 3 feature - coming soon)

⏰ Analysis Time: 2025-10-12 14:10:00
```

---

## 🎮 ALL DISCORD COMMANDS

### 1. `/status` - System Overview
**What it does:**
- Shows trading system status
- Account balance and equity
- Open positions count
- Performance metrics
- Circuit breaker status
- Last scan/trade times

**APIs called:**
- Alpaca API (account data)
- Database (performance metrics)

**OpenAI usage:** NO

**Example:**
```
/status

Response:
🤖 Trading System Status
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 System                    💼 Account
🟢 Status: Running          💵 Equity: $81,456.75
📄 Mode: PAPER              💰 Cash: $100,470.75
⏸️ Paused: No               ⚡ Buying Power: $402,337.50

📈 Positions                 🎯 Performance
📊 Open: 1                  ✅ Win Rate: 0.0%
💹 Total P/L: -$19,014.00   📊 Total Trades: 0
📉 Today P/L: $0.00         💰 Total P/L: $0.00

🛡️ Circuit Breaker          ⏰ Activity
🟢 Status: Normal           🔍 Last Scan: Just now
📉 Daily Loss: $0.00        📈 Last Trade: N/A
⚠️ Limit: $1,000.00         ⏱️ Uptime: 5 minutes
```

---

### 2. `/positions` - View All Positions
**What it does:**
- Lists all open positions
- Shows entry price, current price
- Unrealized P/L for each
- Color-coded (green=profit, red=loss)

**APIs called:**
- Alpaca API (positions data)

**OpenAI usage:** NO

**Example:**
```
/positions

Response:
📊 Open Positions (1)

🔴 TSLA
  Quantity: 300 shares
  Entry: $326.38
  Current: $263.04
  P/L: -$19,014.00 (-23.7%)
  Value: $78,912.00
```

---

### 3. `/sentiment <symbol>` - Sentiment Analysis
**What it does:**
- Multi-source sentiment analysis
- News sentiment with AI
- Market technical sentiment
- Social sentiment (future)
- Overall AI interpretation

**APIs called:**
- NewsAPI (headlines)
- Alpaca API (market data)
- OpenAI GPT-4o (2 calls)

**OpenAI usage:** YES (2 calls, ~$0.002 cost)

**See detailed explanation above**

---

### 4. `/api-status` - API Connection Status
**What it does:**
- Checks all API connections
- Shows trading mode
- Displays configuration
- Estimated daily costs
- API call counts

**APIs called:**
- Alpaca API (test connection)
- NewsAPI (test connection)

**OpenAI usage:** NO

**Example:**
```
/api-status

Response:
🔌 API Status

Alpaca API: ✅ Connected
  Mode: Paper Trading
  Latency: 45ms

OpenAI API: ✅ Connected
  Model: GPT-4o
  Calls Today: 15

NewsAPI: ✅ Connected
  Articles Fetched: 42

Discord Bot: ✅ Connected
  Uptime: 2 hours

⚙️ Configuration
  Scan Interval: 5 minutes
  Max Position: $5,000
  Circuit Breaker: $1,000/day
  
💰 Estimated Costs
  Today: $0.03
  Monthly: $0.90
```

---

### 5. `/aggressive-mode <enable/disable>` - Toggle Trading Mode
**What it does:**
- Switches between conservative and aggressive
- Updates scan interval (5 min → 1 min)
- Adjusts position sizes
- Changes circuit breaker
- Enables scalping/day trading

**APIs called:** None

**OpenAI usage:** NO

**Example:**
```
/aggressive-mode enable

Response:
🚀 Aggressive Mode ENABLED

Settings Updated:
• Scan Interval: 1 minute (was 5 min)
• Trade Types: Scalp + Day + Swing
• Max Positions: 5
• Position Size: $2,000 (was $5,000)
• Circuit Breaker: $500/day (was $1,000)
• Options: 0-7 DTE allowed

Expected Changes:
• Trades/day: 8-12 (was 2-3)
• AI calls/day: 138 (was 11)
• Daily cost: $0.22 (was $0.02)
• More opportunities detected
```

---

### 6. `/circuit-breaker-set <amount>` - Adjust Risk Limit
**What it does:**
- Sets maximum daily loss limit
- Updates circuit breaker threshold
- Validates amount ($100-$10,000)

**APIs called:** None

**OpenAI usage:** NO

**Example:**
```
/circuit-breaker-set 500

Response:
🛡️ Circuit Breaker Updated

New Limit: $500.00
Previous: $1,000.00

Current Status:
• Daily Loss: $0.00
• Remaining: $500.00
• Status: Normal 🟢

The bot will stop trading if daily
losses exceed $500.00
```

---

### 7. `/trades` - Recent Trade History
**What it does:**
- Shows recent trades
- Entry/exit prices
- Profit/loss per trade
- Timestamps
- Color-coded results

**APIs called:**
- Database (trade history)

**OpenAI usage:** NO

**Example:**
```
/trades

Response:
📊 Recent Trades (Last 10)

🟢 AAPL - BUY
  Date: 2025-10-12 10:30
  Entry: $180.50
  Exit: $183.21
  P/L: +$135.00 (+1.5%)

🔴 MSFT - SELL
  Date: 2025-10-12 09:15
  Entry: $350.00
  Exit: $345.25
  P/L: -$237.50 (-1.4%)
```

---

### 8. `/performance` - Trading Metrics
**What it does:**
- Shows win rate
- Total P/L
- Average profit/loss
- Best/worst trades
- Performance chart

**APIs called:**
- Database (performance data)

**OpenAI usage:** NO

**Example:**
```
/performance

Response:
📊 Trading Performance (Last 30 days)

📈 Overview
  Total Trades: 45
  Winning: 29 (64.4%)
  Losing: 16 (35.6%)
  
💰 Profit & Loss
  Total P/L: +$2,450.00
  Avg Win: +$185.50
  Avg Loss: -$95.25
  Best Trade: +$450.00 (NVDA)
  Worst Trade: -$280.00 (TSLA)
  
🎯 Metrics
  Win Rate: 64.4%
  Profit Factor: 2.1
  Sharpe Ratio: 1.8
  Max Drawdown: -$380.00
```

---

### 9. `/pause` - Pause Trading
**What it does:**
- Stops scanning for new opportunities
- Continues monitoring existing positions
- Prevents new trades

**APIs called:** None

**OpenAI usage:** NO

---

### 10. `/resume` - Resume Trading
**What it does:**
- Resumes scanning
- Allows new trades
- Restarts automated trading

**APIs called:** None

**OpenAI usage:** NO

---

### 11. `/sell <symbol>` - Manual Exit
**What it does:**
- Manually closes a position
- Sells all shares/contracts
- Records trade in database

**APIs called:**
- Alpaca API (sell order)
- Database (record trade)

**OpenAI usage:** NO

---

## 💰 COST BREAKDOWN

### Commands That Use OpenAI

| Command | OpenAI Calls | Cost per Use | Notes |
|---------|--------------|--------------|-------|
| `/sentiment` | 2 | ~$0.002 | News analysis + interpretation |

### Commands That Don't Use OpenAI

| Command | Cost | APIs Used |
|---------|------|-----------|
| `/status` | Free | Alpaca, Database |
| `/positions` | Free | Alpaca |
| `/api-status` | Free | All APIs (test only) |
| `/aggressive-mode` | Free | None |
| `/circuit-breaker-set` | Free | None |
| `/trades` | Free | Database |
| `/performance` | Free | Database |
| `/pause` | Free | None |
| `/resume` | Free | None |
| `/sell` | Free | Alpaca, Database |

---

## 🤖 AUTOMATED AI USAGE

### When Trading Bot Uses OpenAI

**1. Opportunity Analysis (Automatic)**
- Triggered when: Score > 70
- Frequency: Every opportunity found
- Calls: 1 per opportunity
- Cost: ~$0.002 per analysis
- Conservative mode: ~11 calls/day = $0.02/day
- Aggressive mode: ~138 calls/day = $0.22/day

**2. Exit Signal Analysis (Automatic)**
- Triggered when: Position needs exit decision
- Frequency: As needed
- Calls: 1 per exit decision
- Cost: ~$0.002 per analysis

**3. Sentiment Analysis (Manual)**
- Triggered when: User runs `/sentiment`
- Frequency: On demand
- Calls: 2 per command
- Cost: ~$0.002 per command

---

## 📊 TOTAL DAILY COSTS

### Conservative Mode (5-min scanning)
```
Opportunity Analysis: $0.02
Exit Analysis: $0.01
User Commands: $0.00 (unless you use /sentiment)
─────────────────────
Total: ~$0.03/day
Monthly: ~$0.90
Yearly: ~$10.80
```

### Aggressive Mode (1-min scanning)
```
Opportunity Analysis: $0.22
Exit Analysis: $0.05
User Commands: $0.00 (unless you use /sentiment)
─────────────────────
Total: ~$0.27/day
Monthly: ~$8.10
Yearly: ~$97.20
```

**Still extremely cheap!**

---

## 🎯 SUMMARY

### Commands Using AI (OpenAI GPT-4o)
- ✅ `/sentiment` - 2 calls per use

### Commands NOT Using AI
- ❌ `/status`
- ❌ `/positions`
- ❌ `/api-status`
- ❌ `/aggressive-mode`
- ❌ `/circuit-breaker-set`
- ❌ `/trades`
- ❌ `/performance`
- ❌ `/pause`
- ❌ `/resume`
- ❌ `/sell`

### Automated AI Usage
- ✅ Opportunity analysis (when scanning finds opportunities)
- ✅ Exit signal analysis (when positions need exit decisions)
- ✅ Sentiment boosting (part of opportunity analysis)

---

**Last Updated:** October 12, 2025 14:10:00
