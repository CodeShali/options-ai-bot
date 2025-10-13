# 🔍 How Scan and Monitor Work

**Your bot has two main automated processes running in the background**

---

## 📊 **1. SCAN (Data Pipeline Agent)**

### **What It Does:**
Scans your watchlist for trading opportunities automatically.

### **How Often:**
- **Every 30 minutes** (configurable via `SCAN_INTERVAL_MINUTES` in `.env`)
- Only during weekdays (skips weekends)

### **Current Watchlist:**
```python
[
    "AAPL", "MSFT", "GOOGL", "AMZN", "TSLA",
    "NVDA", "META", "SPY", "QQQ", "IWM"
]
```

### **What It Checks:**
For each symbol in the watchlist:

1. **Gets latest quote** - Current bid/ask price
2. **Gets 30 days of bars** - Historical price data
3. **Calculates indicators:**
   - 20-day SMA (Simple Moving Average)
   - Average volume (20-day)
   - Price change % (vs yesterday)
   - Volume ratio (current vs average)

4. **Looks for opportunities:**
   ```python
   IF:
   - Price up > 2% today
   - Volume > 1.5x average
   - Price above 20-day SMA
   
   THEN: Flag as opportunity
   ```

### **What Happens Next:**
If opportunities are found:
1. **Strategy Agent** analyzes them with AI
2. **Risk Manager** validates the trade
3. **Execution Agent** places the order (if approved)
4. **Discord notification** sent to you

---

## 👁️ **2. MONITOR (Monitor Agent)**

### **What It Does:**
Monitors all your open positions and sends alerts.

### **How Often:**
- **Every 2 minutes** - Constantly watching your positions

### **What It Monitors:**

#### **A. Profit Target** 🎯
```
Default: 20% profit
If position reaches +20%, sends alert:
"🎯 AAPL: Profit target reached at 20.5%!"
```

#### **B. Stop Loss** ⚠️
```
Default: 10% loss
If position drops to -10%, sends alert:
"⚠️ TSLA: Stop loss triggered at -10.2%!"
```

#### **C. Significant Moves** 📊
```
If position moves > 10% (but not at target/stop):
"📊 NVDA: UP 12.5%"
"📊 META: DOWN 11.3%"
```

#### **D. Options Expiration** ⏰
```
Checks days to expiration (DTE):
- DTE < 7 days: "⏰ Option expiring soon"
- DTE < 3 days: "🚨 Option expiring in 3 days!"
- DTE < 1 day: "⚠️ Option expires TODAY!"
```

### **Alert Logic:**
- **Profit/Stop alerts**: Sent once per threshold crossing
- **Significant move alerts**: Sent every 5% additional move
- **Expiration alerts**: Sent once per threshold

### **What It Does:**
1. **Tracks all positions** from Alpaca
2. **Calculates P&L** in real-time
3. **Checks thresholds** (profit target, stop loss)
4. **Sends Discord alerts** when triggered
5. **Updates database** with current position data
6. **Auto-closes** options near expiration (if configured)

---

## 🔄 **Complete Workflow**

### **Scan → Trade Flow:**
```
Every 30 minutes:
1. Scan watchlist (10 stocks)
2. Find opportunities (price up, volume high)
3. AI analyzes each opportunity
4. Risk manager validates
5. Execute trade (if approved)
6. Send Discord notification
```

### **Monitor → Alert Flow:**
```
Every 2 minutes:
1. Get all open positions
2. Calculate current P&L
3. Check profit target (20%)
4. Check stop loss (-10%)
5. Check significant moves (>10%)
6. Check options expiration
7. Send alerts to Discord
8. Update database
```

---

## ⚙️ **Configuration**

### **In `.env` file:**

```bash
# Scan frequency
SCAN_INTERVAL_MINUTES=30  # How often to scan

# Risk limits
PROFIT_TARGET_PCT=0.20    # 20% profit target
STOP_LOSS_PCT=0.10        # 10% stop loss
MAX_POSITION_SIZE=0.10    # 10% of portfolio per trade
MAX_DAILY_LOSS=0.05       # 5% max daily loss (circuit breaker)

# Trading mode
TRADING_MODE=paper        # paper or live
```

### **Current Settings:**
- ✅ Scan: Every 30 minutes
- ✅ Monitor: Every 2 minutes
- ✅ Profit Target: 20%
- ✅ Stop Loss: 10%
- ✅ Mode: Paper trading

---

## 📊 **What You See in Discord**

### **Scan Finds Opportunity:**
```
🔍 Opportunity Found: AAPL

📊 Analysis:
Price: $178.50 (+2.5%)
Volume: 1.8x average
Above 20-day SMA

🤖 AI Recommendation: BUY
Confidence: 75%

💰 Trade Plan:
Entry: $178.50
Target: $214.20 (+20%)
Stop: $160.65 (-10%)

✅ Trade executed: 10 shares @ $178.50
```

### **Monitor Sends Alert:**
```
🎯 AAPL: Profit target reached at 20.5%!

Position Details:
Entry: $178.50
Current: $215.00
Profit: $365.00 (+20.5%)

💡 Recommendation: Consider taking profits!
```

---

## 🎯 **Current Status**

### **Scan Agent:**
```
Status: ✅ Running
Frequency: Every 30 minutes
Watchlist: 10 stocks
Last scan: [check logs]
Opportunities found: [check logs]
```

### **Monitor Agent:**
```
Status: ✅ Running
Frequency: Every 2 minutes
Positions monitored: [your open positions]
Active alerts: [any current alerts]
```

---

## 🔍 **How to Check What's Happening**

### **View Recent Scans:**
```bash
tail -100 logs/bot.log | grep -i "scan"

# Look for:
"Scanning for opportunities..."
"Found 2 opportunities"
"Scan and trade job completed"
```

### **View Monitor Activity:**
```bash
tail -100 logs/bot.log | grep -i "monitor"

# Look for:
"Monitoring positions..."
"Position monitoring complete: 3 positions, 1 alerts"
"Profit target reached"
```

### **View All Scheduled Jobs:**
```bash
tail -100 logs/bot.log | grep -i "scheduled"

# Look for:
"Scheduled jobs configured"
"Running scheduled scan and trade job"
"Running scheduled monitor positions job"
```

---

## 📈 **Example: Full Day Timeline**

```
9:30 AM  - Market opens
9:30 AM  - Circuit breaker reset
9:32 AM  - Monitor checks positions (every 2 min)
9:34 AM  - Monitor checks positions
10:00 AM - Scan runs (finds AAPL opportunity)
10:01 AM - AI analyzes AAPL
10:02 AM - Trade executed: Buy 10 AAPL @ $178.50
10:02 AM - Discord notification sent
10:04 AM - Monitor checks positions (now includes AAPL)
10:30 AM - Scan runs (no opportunities)
10:32 AM - Monitor checks positions
11:00 AM - Scan runs (finds TSLA opportunity)
...
2:00 PM  - AAPL hits profit target (+20%)
2:00 PM  - Discord alert: "🎯 Profit target reached!"
2:02 PM  - Monitor checks (AAPL still at target)
...
4:00 PM  - Market closes
4:00 PM  - Daily summary generated
4:01 PM  - Discord: "📊 Daily Summary: 2 trades, +$450 profit"
```

---

## 🛠️ **Customization**

### **Change Scan Frequency:**
```bash
# In .env
SCAN_INTERVAL_MINUTES=15  # Scan every 15 minutes
```

### **Change Profit/Stop Levels:**
```bash
# In .env
PROFIT_TARGET_PCT=0.15    # 15% profit target
STOP_LOSS_PCT=0.05        # 5% stop loss
```

### **Modify Watchlist:**
```python
# In agents/data_pipeline_agent.py
self.watchlist = [
    "AAPL", "MSFT", "GOOGL",  # Your custom list
    "NVDA", "AMD", "INTC"
]
```

---

## 🚨 **Important Notes**

### **Scan Agent:**
- ✅ Runs automatically every 30 minutes
- ✅ Only scans during weekdays
- ✅ Requires market data (IEX/SIP)
- ✅ Uses AI for analysis
- ⚠️ Can execute trades (if risk approved)

### **Monitor Agent:**
- ✅ Runs every 2 minutes
- ✅ Monitors ALL positions (stocks + options)
- ✅ Sends Discord alerts
- ✅ Updates database
- ⚠️ Can auto-close positions (if configured)

### **Safety Features:**
- ✅ Circuit breaker (max daily loss)
- ✅ Position size limits
- ✅ Risk manager validation
- ✅ Paper trading mode (default)
- ✅ All trades logged

---

## 📊 **Summary**

**Scan Agent:**
- **Purpose**: Find trading opportunities
- **Frequency**: Every 30 minutes
- **Action**: Analyzes → Trades → Notifies

**Monitor Agent:**
- **Purpose**: Watch open positions
- **Frequency**: Every 2 minutes
- **Action**: Checks P&L → Sends alerts → Updates DB

**Together they:**
- 🔍 Automatically find opportunities
- 💰 Execute trades (with risk management)
- 👁️ Monitor all positions
- 🚨 Send timely alerts
- 📊 Keep you informed

---

**Your bot is actively scanning and monitoring 24/7!** 🤖📊

Check Discord for notifications or logs for detailed activity.
