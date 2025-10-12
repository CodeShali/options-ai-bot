# How Trading Works - Complete Explanation

## 🔄 Trading Cycle Overview

Your system runs **two main loops** continuously:

### 1. **Scan & Trade Loop** - Every 5 minutes
Finds opportunities and executes trades

### 2. **Monitor & Exit Loop** - Every 2 minutes  
Watches positions and exits when conditions are met

---

## 📊 Detailed: Scan & Trade (Every 5 Minutes)

### Step 1: Circuit Breaker Check
```
Check if daily loss > $1,000
├─ YES → Stop trading, send alert
└─ NO → Continue
```

### Step 2: Position Limits Check
```
Check available position slots
├─ Have slots? → Continue
└─ Max 5 reached? → Stop, wait for exits
```

### Step 3: Scan Watchlist
**What it does:**
- Fetches current quotes for all 10 symbols
- Gets last 20 bars (historical data)
- Calculates technical indicators:
  - **SMA 20 & 50** (Simple Moving Averages)
  - **RSI 14** (Relative Strength Index)
  - **Volume Ratio** (current vs average)
  - **Price Momentum** (recent price change)

**How it finds opportunities:**
```python
# Scoring system (0-100)
score = 0

# 1. Price above SMA20 (bullish)
if current_price > sma_20:
    score += 20

# 2. SMA20 above SMA50 (uptrend)
if sma_20 > sma_50:
    score += 15

# 3. RSI in sweet spot (30-70)
if 30 < rsi < 70:
    score += 20

# 4. Volume above average (interest)
if volume > avg_volume * 1.2:
    score += 15

# 5. Positive momentum (rising)
if momentum > 0:
    score += 15

# 6. Recent gain (0-5%)
if 0 < price_change < 5:
    score += 15

# Opportunity if score >= 60
```

**Example:**
```
AAPL:
├─ Price: $175.23 (above SMA20) → +20
├─ SMA20: $173.45 > SMA50: $170.12 → +15
├─ RSI: 55 (healthy) → +20
├─ Volume: 1.5x average → +15
├─ Momentum: +2.3% → +15
├─ Recent gain: +1.8% → +15
└─ Total Score: 100 → ✅ OPPORTUNITY!
```

### Step 4: AI Analysis (OpenAI GPT-4)
**What it analyzes:**
```
For each opportunity, GPT-4 evaluates:

Market Data:
├─ Current price
├─ Volume patterns
├─ Day high/low
├─ Previous close

Technical Indicators:
├─ SMA 20 & 50
├─ RSI
├─ Volatility
├─ Volume ratio
└─ Momentum

AI Considers:
├─ Is this a good entry point?
├─ What's the risk/reward ratio?
├─ Are conditions favorable?
├─ What's my confidence level?
└─ What could go wrong?

Output:
├─ Recommendation: BUY/HOLD/SELL
├─ Confidence: 0-100%
├─ Risk Level: LOW/MEDIUM/HIGH
├─ Reasoning: Detailed explanation
├─ Target Price: Optional
└─ Stop Loss: Optional
```

**Example AI Analysis:**
```
Symbol: AAPL
Recommendation: BUY
Confidence: 75%
Risk Level: LOW

Reasoning: "Strong upward momentum with RSI at 55 
indicates healthy buying pressure without being 
overbought. Price breaking above SMA20 with 
increasing volume suggests continuation. Recent 
earnings beat supports bullish thesis. Entry at 
current levels offers favorable risk/reward with 
support at $170."
```

### Step 5: Risk Validation
**What it checks:**
```
For each BUY signal:

1. Confidence >= 60%?
   ├─ YES → Continue
   └─ NO → Reject

2. Calculate position size:
   Base: $5,000 max
   ├─ High confidence (>80%) → $5,000
   ├─ Medium (60-80%) → $3,000-5,000
   └─ Low (<60%) → Reject

3. Check buying power:
   ├─ Sufficient? → Continue
   └─ Insufficient? → Reject

4. Circuit breaker OK?
   ├─ YES → Continue
   └─ NO → Reject

5. Position slots available?
   ├─ YES → APPROVE
   └─ NO → Reject
```

### Step 6: Execute Trade
```
If approved:
├─ Place market order via Alpaca
├─ Record in database
├─ Create Discord thread
├─ Send notification
└─ Update positions
```

---

## 📈 Detailed: Monitor & Exit (Every 2 Minutes)

### Step 1: Get All Positions
```
Fetch from Alpaca:
├─ Entry price
├─ Current price
├─ Quantity
├─ Unrealized P/L
└─ Unrealized P/L %
```

### Step 2: Check Exit Conditions
**For each position:**

#### Condition 1: Profit Target (50%)
```
If unrealized_plpc >= 50%:
├─ Generate PROFIT_TARGET alert
├─ Trigger AI exit analysis
└─ Execute if AI confirms
```

#### Condition 2: Stop Loss (30%)
```
If unrealized_plpc <= -30%:
├─ Generate STOP_LOSS alert
├─ Trigger AI exit analysis
└─ Execute if AI confirms
```

#### Condition 3: Significant Move (>10%)
```
If abs(unrealized_plpc) > 10%:
├─ Generate SIGNIFICANT_MOVE alert
├─ Send to Discord thread
└─ Continue monitoring
```

### Step 3: AI Exit Analysis
**When triggered:**
```
GPT-4 evaluates:

Position Status:
├─ Entry price vs current
├─ Profit/loss amount
├─ Time in position
└─ Current market conditions

Market Data:
├─ Current price
├─ Volume
├─ Price action
└─ Momentum

Decision Factors:
├─ Should I take profits now?
├─ Is momentum reversing?
├─ Could it go higher?
├─ Is risk increasing?
└─ What's the smart move?

Output:
├─ Action: EXIT/HOLD/PARTIAL_EXIT
├─ Confidence: 0-100%
└─ Reasoning: Why this decision
```

### Step 4: Execute Exit
```
If AI recommends EXIT:
├─ Place sell order via Alpaca
├─ Record in database
├─ Send to Discord thread
├─ Close thread
└─ Update statistics
```

---

## ⏰ Timing & Frequency

### Automated Scans
```
Market Hours (9:30 AM - 4:00 PM ET):
├─ Scan: Every 5 minutes (12 scans/hour)
├─ Monitor: Every 2 minutes (30 checks/hour)
└─ Total: ~96 scans + 240 checks per day
```

### Why These Intervals?

**5 Minutes for Scanning:**
- ✅ Catches opportunities quickly
- ✅ Not too frequent (avoids overtrading)
- ✅ Allows time for AI analysis
- ✅ Reduces API costs

**2 Minutes for Monitoring:**
- ✅ Quick response to profit targets
- ✅ Fast stop loss execution
- ✅ Catches significant moves
- ✅ Protects your positions

---

## 🎯 Example Complete Trade

### Minute 0: Scan Starts
```
Scanning watchlist...
├─ AAPL: Score 85 ✅
├─ MSFT: Score 45 ❌
├─ GOOGL: Score 72 ✅
└─ Found 2 opportunities
```

### Minute 1: AI Analysis
```
Analyzing AAPL...
├─ Confidence: 75%
├─ Risk: LOW
└─ Recommendation: BUY ✅

Analyzing GOOGL...
├─ Confidence: 55%
├─ Risk: MEDIUM
└─ Recommendation: HOLD ❌
```

### Minute 2: Risk Check & Execute
```
AAPL Trade:
├─ Confidence 75% ✅
├─ Position size: $4,000
├─ Buying power: $127,351 ✅
├─ Slots available: 4/5 ✅
└─ APPROVED → Execute

BUY: 22 shares AAPL @ $175.23
Total: $3,855.06
```

### Minute 4-10: Monitoring Begins
```
Every 2 minutes:
├─ Check AAPL position
├─ Current: $176.45 (+0.7%)
└─ No action needed
```

### Minute 12: Significant Move
```
AAPL Update:
├─ Entry: $175.23
├─ Current: $193.50 (+10.4%)
├─ Profit: $402.94
└─ Alert sent to thread 📊
```

### Minute 20: More Movement
```
AAPL Update:
├─ Current: $203.15 (+15.9%)
├─ Profit: $615.24
└─ Alert sent (5% change) 📊
```

### Minute 45: Profit Target!
```
AAPL Alert:
├─ Current: $263.85 (+50.6%)
├─ Profit: $1,949.64
└─ PROFIT TARGET REACHED! 🎯

AI Exit Analysis:
├─ Recommendation: EXIT
├─ Confidence: 85%
└─ Reasoning: "Target reached, momentum slowing"

SELL: 22 shares @ $263.85
Profit: $1,949.64 🟢
```

**Total Time**: 45 minutes from entry to profit!

---

## 📊 Opportunity Scoring Breakdown

### What Makes a Good Opportunity?

**Technical Strength (60 points)**
```
Price Action (35 points):
├─ Above SMA20: 20 pts
├─ SMA20 > SMA50: 15 pts

Momentum (25 points):
├─ Positive momentum: 15 pts
├─ Recent gain 0-5%: 15 pts (scaled)
```

**Market Confirmation (40 points)**
```
Volume (15 points):
└─ Above average: 15 pts

RSI (20 points):
├─ 30-70 range: 20 pts
├─ 20-30 or 70-80: 10 pts
└─ <20 or >80: 0 pts
```

**Minimum Score: 60** (out of 100)

### Example Scores

**Strong Opportunity (Score: 95)**
```
NVDA:
├─ Price above SMA20: ✅ 20
├─ SMA20 > SMA50: ✅ 15
├─ RSI 58: ✅ 20
├─ Volume 2.1x: ✅ 15
├─ Momentum +3.2%: ✅ 15
├─ Recent gain +2.1%: ✅ 10
└─ Total: 95 → Excellent!
```

**Weak Opportunity (Score: 45)**
```
XYZ:
├─ Price below SMA20: ❌ 0
├─ SMA20 < SMA50: ❌ 0
├─ RSI 82: ❌ 0
├─ Volume 0.8x: ❌ 0
├─ Momentum -1.5%: ❌ 0
├─ Recent loss -2%: ❌ 0
└─ Total: 45 → Skip
```

---

## 🎓 Key Takeaways

### How Often It Checks
- **Scans**: Every 5 minutes (looking for new trades)
- **Monitors**: Every 2 minutes (watching your positions)
- **Total**: ~336 automated checks per trading day

### How It Finds Opportunities
1. **Technical screening** (score >= 60)
2. **AI analysis** (confidence >= 60%)
3. **Risk validation** (all checks pass)
4. **Execution** (if approved)

### What It Monitors
- **Profit targets** (50% gain)
- **Stop losses** (30% loss)
- **Significant moves** (>10% change)
- **AI exit signals** (when conditions met)

### Why It Works
- ✅ **Systematic** - No emotions
- ✅ **Fast** - Catches opportunities quickly
- ✅ **Smart** - AI-powered decisions
- ✅ **Protected** - Multiple safety checks
- ✅ **Automated** - Runs 24/7 (during market hours)

---

## 💡 Customization

### Change Scan Frequency
Edit `.env`:
```env
SCAN_INTERVAL_MINUTES=5  # Change to 3, 10, etc.
```

### Adjust Thresholds
Edit `.env`:
```env
PROFIT_TARGET_PCT=0.50  # 50% → Change to 0.30 (30%)
STOP_LOSS_PCT=0.30      # 30% → Change to 0.20 (20%)
```

### Modify Watchlist
Use Discord:
```
/watchlist-add TSLA
/watchlist-remove SPY
/watchlist
```

### Change Opportunity Score
Edit `agents/data_pipeline_agent.py` line ~100:
```python
if score >= 60:  # Change to 70 for stricter
```

---

**Your system is constantly working to find and execute profitable trades! 🚀**

*Last Updated: 2025-10-11*
