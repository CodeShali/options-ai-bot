# 📋 Watchlist & Intelligent Scanning

**Complete guide to managing your watchlist and scanning for opportunities**

---

## 🎯 **Overview**

The bot now has TWO ways to scan for opportunities:

1. **Automatic Scan** - Scans default watchlist every 30 minutes
2. **Manual Scan** - Scan any symbols you want, anytime

**Both use the NEW Intelligent Scanner!** 🚀

---

## 📋 **Watchlist Management**

### **Default Watchlist:**
```
AAPL, MSFT, GOOGL, AMZN, TSLA,
NVDA, META, SPY, QQQ, IWM
```

### **Discord Commands:**

#### **View Watchlist:**
```
/watchlist view
```
Shows all symbols currently being monitored.

#### **Add Symbol:**
```
/watchlist add NVDA
```
Adds NVDA to the watchlist. Will be included in automatic scans.

#### **Remove Symbol:**
```
/watchlist remove TSLA
```
Removes TSLA from the watchlist.

---

## 🔍 **Scanning Commands**

### **1. Scan Default Watchlist**
```
/scan
```
Runs intelligent scan on all watchlist symbols.

**Output:**
```
🔍 Market Scan Results

📊 Scan Statistics:
- Symbols Scanned: 10
- Movers Detected: 3
- Opportunities Found: 2
- Duration: 15.3s

🎯 TOP OPPORTUNITIES:

1. NVDA - $485.50
   Action: BUY_CALL (85% confidence)
   Score: 85/100
   Strong upward momentum (+1.8% in 15min) with 2.5x volume...

2. AAPL - $178.50
   Action: BUY_STOCK (72% confidence)
   Score: 72/100
   Moderate momentum (+1.2%) with volume confirmation...
```

### **2. Scan Specific Symbols**
```
/scan NVDA, AAPL, TSLA
```
Scans only the symbols you specify (comma-separated).

**Use cases:**
- Check specific stocks you're interested in
- Scan stocks not in watchlist
- Quick analysis of multiple symbols

### **3. Deep Analysis of One Symbol**
```
/analyze NVDA
```
Performs comprehensive analysis on a single symbol.

**Output:**
```
📈 Deep Analysis: NVDA
Current Price: $485.50

🎯 Recommendation:
Action: BUY_CALL
Confidence: 85%
Score: 85/100

💡 Analysis:
Strong upward momentum (+1.8% in 15min) with 2.5x volume.
RSI at 65 (not overbought), above all MAs. Recent positive
news on chip demand.

🚀 Momentum:
Direction: UP
Move: +1.8%
Volume: 2.5x

📊 Technicals:
RSI: 65.0
vs SMA20: ABOVE
Volume: INCREASING

📍 Entry/Exit:
Entry: Enter ATM call on pullback
Target: $495.00
Stop: $478.00
```

---

## 🤖 **What the Intelligent Scanner Does**

For EVERY symbol (watchlist or custom):

### **1. Momentum Detection** 🚀
- Analyzes 5-minute candles (last 100 minutes)
- Detects moves in last 15 minutes
- Identifies volume spikes
- Tracks trend strength

### **2. Technical Analysis** 📊
- Calculates 15+ indicators
- Moving averages (SMA 10, 20, 50)
- RSI (overbought/oversold)
- Support/Resistance levels
- Volume trends

### **3. Options Analysis** 📈
- Checks options availability
- ATM call/put Greeks
- Implied volatility
- Premium costs

### **4. News Sentiment** 📰
- Gets recent headlines
- Sentiment analysis
- Impact assessment

### **5. Comprehensive Scoring** 🎯
- Momentum score (0-100)
- Weighted across 5 categories
- Price momentum: 30 pts
- Volume confirmation: 20 pts
- Technical alignment: 25 pts
- Trend strength: 15 pts
- Volume trend: 10 pts

### **6. AI Recommendation** 🤖
- Claude analyzes everything
- Recommends: BUY_STOCK / BUY_CALL / BUY_PUT / WAIT
- Provides confidence, entry, target, stop, risk, sizing

---

## 🔄 **Automatic vs Manual Scanning**

### **Automatic Scan (Every 30 minutes):**
```
✅ Scans default watchlist
✅ Runs in background
✅ Sends Discord notifications
✅ Can execute trades (if confidence > 70%)
✅ Happens automatically
```

**Example:**
```
10:00 AM - Auto scan runs
10:00 AM - Finds NVDA opportunity
10:01 AM - AI analyzes: BUY_CALL (85%)
10:02 AM - Discord notification sent
10:02 AM - Trade executed (if enabled)
```

### **Manual Scan (On-demand):**
```
✅ Scan anytime you want
✅ Scan any symbols
✅ Get immediate results
✅ No automatic trading
✅ Full control
```

**Example:**
```
You: /scan NVDA, AAPL
Bot: Scanning 2 symbols...
Bot: Found 1 opportunity (NVDA)
Bot: Full analysis provided
You: Review and decide
```

---

## 📊 **Use Cases**

### **Use Case 1: Monitor Your Favorites**
```
/watchlist add NVDA
/watchlist add AMD
/watchlist add INTC

Now these 3 are scanned every 30 minutes automatically!
```

### **Use Case 2: Quick Check**
```
/scan TSLA

Quick scan of just TSLA to see if there's an opportunity.
```

### **Use Case 3: Compare Multiple**
```
/scan NVDA, AMD, INTC

Compare all chip stocks at once.
```

### **Use Case 4: Deep Dive**
```
/analyze AAPL

Get full technical + momentum + news analysis for AAPL.
```

### **Use Case 5: Custom Watchlist**
```
/watchlist remove SPY
/watchlist remove QQQ
/watchlist add COIN
/watchlist add MSTR

Now monitoring crypto-related stocks instead of indices.
```

---

## 🎯 **Workflow Examples**

### **Morning Routine:**
```
1. /watchlist view
   - Check what's being monitored

2. /scan
   - See overnight opportunities

3. /analyze NVDA
   - Deep dive on interesting stocks

4. Review and trade
```

### **During Market Hours:**
```
1. Auto scans run every 30 min
2. Discord notifications for opportunities
3. /analyze [symbol] for details
4. Execute trades
```

### **Custom Research:**
```
1. Hear about a stock (e.g., news)
2. /analyze STOCK
3. Get full analysis instantly
4. Decide to trade or not
```

---

## ⚙️ **Configuration**

### **Change Scan Frequency:**
```bash
# In .env
SCAN_INTERVAL_MINUTES=15  # Scan every 15 minutes
```

### **Modify Default Watchlist:**
```python
# In agents/data_pipeline_agent.py
self.watchlist = [
    "AAPL", "MSFT", "GOOGL",  # Your custom list
    "NVDA", "AMD", "INTC"
]
```

Or use Discord:
```
/watchlist add SYMBOL
/watchlist remove SYMBOL
```

---

## 📈 **What You Get**

### **For Watchlist Symbols:**
- ✅ Automatic scanning every 30 min
- ✅ Discord notifications
- ✅ Auto-trading (if enabled)
- ✅ Continuous monitoring

### **For Manual Scans:**
- ✅ Instant analysis
- ✅ Any symbols you want
- ✅ Full intelligent scan
- ✅ No auto-trading
- ✅ Review before action

---

## 🚀 **Key Features**

### **1. Flexible**
```
Scan watchlist OR custom symbols
Add/remove symbols anytime
```

### **2. Intelligent**
```
Uses NEW intelligent scanner
15+ technical indicators
AI-powered recommendations
```

### **3. Actionable**
```
Clear buy/sell/wait signals
Entry/exit strategies
Risk assessment
Position sizing
```

### **4. Real-Time**
```
5-minute candle analysis
Detects momentum early
Volume confirmation
```

### **5. Comprehensive**
```
Technicals + News + Greeks
Multi-factor scoring
Full reasoning provided
```

---

## 💡 **Pro Tips**

### **Tip 1: Keep Watchlist Focused**
```
Don't add too many symbols (10-20 max)
Focus on sectors you understand
Remove symbols you're not interested in
```

### **Tip 2: Use Manual Scans for Research**
```
Hear about a stock? /analyze it immediately
Comparing stocks? /scan them together
```

### **Tip 3: Combine Both Methods**
```
Watchlist: Your core holdings
Manual scans: New opportunities
```

### **Tip 4: Review Before Trading**
```
Auto-scan finds opportunities
You review the analysis
You decide to trade or not
```

---

## 📊 **Summary**

**Watchlist:**
- Default 10 symbols
- Add/remove anytime
- Scanned automatically every 30 min

**Scanning:**
- `/scan` - Scan watchlist
- `/scan SYMBOLS` - Scan specific stocks
- `/analyze SYMBOL` - Deep dive one stock

**Intelligent Scanner:**
- Momentum detection (5-min candles)
- 15+ technical indicators
- Options + Greeks analysis
- News sentiment
- AI recommendations
- Comprehensive scoring

**Result:**
- Find opportunities early
- Get actionable recommendations
- Make informed decisions
- Trade with confidence

---

## 🎉 **Examples**

### **Example 1: Add to Watchlist**
```
You: /watchlist add NVDA
Bot: ✅ Added NVDA to watchlist

(Now NVDA is scanned every 30 minutes)
```

### **Example 2: Quick Scan**
```
You: /scan TSLA, NVDA
Bot: 🔍 Scanning 2 symbols...
Bot: Found 1 opportunity: NVDA (BUY_CALL, 85%)
```

### **Example 3: Deep Analysis**
```
You: /analyze AAPL
Bot: 📈 Full analysis with momentum, technicals, news
Bot: Recommendation: BUY_STOCK (72% confidence)
Bot: Entry: $177, Target: $185, Stop: $175
```

---

**Your bot now scans intelligently, whether automatically or on-demand!** 🚀📊

Use the watchlist for continuous monitoring and manual scans for quick research!
