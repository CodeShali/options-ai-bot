# TARA Trading System - Workflow Guide

**Last Updated:** October 21, 2025  
**Version:** 2.0

---

## 📋 Table of Contents

1. [Automated Trading Workflow](#automated-trading-workflow)
2. [Manual Trading Workflows](#manual-trading-workflows)
3. [Monitoring Workflows](#monitoring-workflows)
4. [Risk Management Workflows](#risk-management-workflows)
5. [Data Flow Diagrams](#data-flow-diagrams)

---

## 🤖 Automated Trading Workflow

### Complete Scan-to-Trade Cycle

```
┌─────────────────────────────────────────────────────────┐
│ PHASE 1: MARKET SCAN (Every 5 minutes)                 │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
        ┌─────────────────────────────────┐
        │ 1. Data Pipeline Agent          │
        │    • Fetch watchlist symbols    │
        │    • Get real-time quotes       │
        │    • Get historical bars        │
        │    • Cache market data          │
        └────────────┬────────────────────┘
                     │
                     ▼
        ┌─────────────────────────────────┐
        │ 2. Intelligent Scanner          │
        │    • Technical analysis         │
        │    • Multi-timeframe analysis   │
        │    • Strategy signals           │
        │    • Pattern recognition        │
        └────────────┬────────────────────┘
                     │
                     ▼
        ┌─────────────────────────────────┐
        │ 3. AI Analysis (Claude/OpenAI)  │
        │    • Analyze technical setup    │
        │    • Review news sentiment      │
        │    • Generate reasoning         │
        │    • Assign confidence score    │
        └────────────┬────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│ PHASE 2: OPPORTUNITY FILTERING                         │
└─────────────────────────────────────────────────────────┘
                     │
                     ▼
        ┌─────────────────────────────────┐
        │ 4. Filter Opportunities         │
        │    • Confidence >= 70%          │
        │    • Action: BUY signals only   │
        │    • Remove duplicates          │
        │    • Check recent alerts        │
        └────────────┬────────────────────┘
                     │
                     ▼
        ┌─────────────────────────────────┐
        │ 5. Discord Notification         │
        │    • Show top 2 opportunities   │
        │    • Display AI reasoning       │
        │    • Add ✅/❌ reactions        │
        │    • Wait for user response     │
        └────────────┬────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│ PHASE 3: RISK VALIDATION                               │
└─────────────────────────────────────────────────────────┘
                     │
                     ▼
        ┌─────────────────────────────────┐
        │ 6. Risk Manager Validation      │
        │    • Check circuit breaker      │
        │    • Verify position limits     │
        │    • Calculate position size    │
        │    • Check portfolio heat       │
        └────────────┬────────────────────┘
                     │
                     ▼
        ┌─────────────────────────────────┐
        │ 7. Pre-Trade Checks             │
        │    • Buying power sufficient?   │
        │    • Symbol not in positions?   │
        │    • Market hours active?       │
        │    • No pending orders?         │
        └────────────┬────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│ PHASE 4: EXECUTION                                      │
└─────────────────────────────────────────────────────────┘
                     │
                     ▼
        ┌─────────────────────────────────┐
        │ 8. Execution Agent              │
        │    • Place market order         │
        │    • Track order status         │
        │    • Confirm fill               │
        │    • Update database            │
        └────────────┬────────────────────┘
                     │
                     ▼
        ┌─────────────────────────────────┐
        │ 9. Post-Execution               │
        │    • Set stop loss order        │
        │    • Set take profit (optional) │
        │    • Send Discord confirmation  │
        │    • Start position monitoring  │
        └────────────┬────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│ PHASE 5: MONITORING (Every 2 minutes)                  │
└─────────────────────────────────────────────────────────┘
                     │
                     ▼
        ┌─────────────────────────────────┐
        │ 10. Monitor Agent               │
        │    • Track P&L                  │
        │    • Check stop loss            │
        │    • Check take profit          │
        │    • Generate alerts            │
        └────────────┬────────────────────┘
                     │
                     ▼
        ┌─────────────────────────────────┐
        │ 11. Exit Detection              │
        │    • Stop loss hit?             │
        │    • Take profit reached?       │
        │    • Strategy exit signal?      │
        │    • Time-based exit?           │
        └────────────┬────────────────────┘
                     │
                     ▼
        ┌─────────────────────────────────┐
        │ 12. Position Close              │
        │    • Place sell order           │
        │    • Confirm execution          │
        │    • Record performance         │
        │    • Send Discord update        │
        └─────────────────────────────────┘
```

---

## 🛒 Manual Trading Workflows

### Workflow A: Manual Stock Buy

**User Action:** `/buy AAPL 10`

```
Step 1: Command Received
├─ Discord bot receives command
├─ Extracts symbol (AAPL) and quantity (10)
└─ Calls Buy Assistant Service

Step 2: Analysis Phase
├─ Get current quote from Alpaca
├─ Get account buying power
├─ Calculate estimated cost
├─ Validate sufficient funds
└─ Prepare confirmation dialog

Step 3: User Confirmation
├─ Display confirmation embed:
│   • Symbol: AAPL
│   • Quantity: 10 shares
│   • Price: $185.50
│   • Cost: $1,855.00
│   • Buying Power After: $23,145.00
├─ Show buttons: [✅ Confirm] [❌ Cancel]
└─ Wait for user response

Step 4: Execution (if confirmed)
├─ Place market buy order
├─ Track order status
├─ Confirm fill
├─ Update database
└─ Send success notification

Step 5: Post-Execution
├─ Position now monitored automatically
├─ Stop loss can be set
└─ Appears in /positions
```

### Workflow B: Manual Options Buy

**User Action:** `/buy-option AAPL call 1000`

```
Step 1: Command Received
├─ Extract symbol (AAPL)
├─ Extract strategy (call)
├─ Extract max risk ($1000)
└─ Call Buy Assistant Service

Step 2: Options Chain Analysis
├─ Fetch options chain from Alpaca
├─ Filter by strategy (calls only)
├─ Get Greeks for each contract:
│   • Delta (Δ)
│   • Theta (Θ)
│   • Gamma (Γ)
│   • Vega (V)
└─ Filter by max risk ($1000)

Step 3: Scoring & Ranking
├─ Calculate quality score (0-100):
│   • Delta score (30 points)
│   • Theta score (20 points)
│   • Moneyness score (30 points)
│   • Time to expiration score (20 points)
│   • Liquidity score (5 points)
├─ Assess risk level (LOW/MODERATE/HIGH)
├─ Generate recommendation text
└─ Sort by score (highest first)

Step 4: Display Recommendations
├─ Show top 3 options:
│   #1 - Strike, Expiration, Cost, Greeks, Score
│   #2 - Strike, Expiration, Cost, Greeks, Score
│   #3 - Strike, Expiration, Cost, Greeks, Score
├─ Add buttons: [Buy #1] [Buy #2] [Buy #3]
└─ Wait for user selection

Step 5: Execution (on selection)
├─ Place limit order at ask price
├─ Track order status
├─ Confirm fill
├─ Update database
└─ Send success notification
```

### Workflow C: NLP Buy

**User Message:** "Buy 10 shares of AAPL"

```
Step 1: NLP Processing
├─ Conversation service receives message
├─ Extract user intent: "buy_stock"
├─ Extract parameters:
│   • Symbol: AAPL
│   • Quantity: 10
└─ Call buy_stock function

Step 2: AI Function Call
├─ LLM detects buy intent
├─ Calls buy_stock function with args
├─ Function analyzes opportunity
└─ Returns analysis to AI

Step 3: AI Response
├─ AI formats friendly response:
│   "I can help you buy AAPL! 📊
│    Current Price: $185.50
│    Cost for 10 shares: $1,855.00
│    Ready to proceed?"
├─ Add ✅/❌ reactions
└─ Wait for user confirmation

Step 4: Execution (if ✅)
├─ Place market buy order
├─ Track and confirm
├─ AI sends confirmation:
│   "✅ Bought 10 shares of AAPL at $185.50"
└─ Position now monitored
```

---

## 📊 Monitoring Workflows

### Workflow D: Position Monitoring

**Frequency:** Every 2 minutes

```
Step 1: Get All Positions
├─ Fetch from Alpaca API
├─ Update cache
└─ For each position:

Step 2: Calculate Metrics
├─ Current price
├─ Unrealized P&L ($)
├─ Unrealized P&L (%)
├─ Entry price
├─ Quantity
└─ Market value

Step 3: Check Alert Conditions
├─ Profit Target (15%+)
│   └─ Send: "🎯 AAPL up 15.2% - Consider taking profits"
├─ Stop Loss (10%-)
│   └─ Send: "⚠️ AAPL down 10.5% - Stop loss triggered"
├─ Significant Move (10%+)
│   └─ Send: "📈 AAPL moved 12.3% - Review position"
└─ Exit Signal
    └─ Send: "🚨 Exit signal for AAPL - Strategy recommends closing"

Step 4: Duplicate Prevention
├─ Check last alert time for symbol
├─ Only send if > 30 min since last alert
└─ Update alert timestamp

Step 5: Discord Notification
├─ Format alert message
├─ Include position details
├─ Add action buttons if needed
└─ Send to Discord channel
```

### Workflow E: Hourly Summary

**Frequency:** Top of every hour during market hours

```
Step 1: Data Collection
├─ Scan activity (last hour)
├─ Opportunities found
├─ Trades executed
├─ Current positions
├─ Account metrics
└─ Market conditions

Step 2: Analysis
├─ Calculate hourly P&L
├─ Identify top performers
├─ Identify worst performers
├─ Assess market trend
└─ Generate recommendations

Step 3: Format Summary
├─ 🔍 SCANNING ACTIVITY
│   • Scans performed: 12
│   • Symbols analyzed: 10
│   • Strategies used: 4
├─ 🎯 OPPORTUNITIES
│   • Total found: 3
│   • High confidence: 1
│   • Reasons for no more: Low volatility
├─ 💼 TRADING EXECUTION
│   • Orders placed: 1
│   • Trades executed: 1
│   • Pending orders: 0
├─ 📈 PORTFOLIO STATUS
│   • Active positions: 5
│   • Total value: $42,500
│   • Unrealized P&L: +$1,234.56
└─ 🎯 NEXT ACTIONS
    • Continue monitoring
    • Watch for breakouts

Step 4: Send to Discord
├─ Post formatted summary
├─ Include charts (if available)
└─ Add timestamp
```

---

## 🛡️ Risk Management Workflows

### Workflow F: Circuit Breaker

**Trigger:** Daily loss exceeds limit

```
Step 1: Loss Detection
├─ Calculate daily P&L
├─ Compare to max_daily_loss ($1000)
└─ If exceeded:

Step 2: Emergency Actions
├─ Set circuit_breaker = True
├─ Pause all trading
├─ Cancel pending orders
├─ Keep existing positions (don't force close)
└─ Log event

Step 3: Notification
├─ Send Discord alert:
│   "🚨 CIRCUIT BREAKER TRIGGERED
│    Daily Loss: -$1,050
│    Limit: $1,000
│    Trading paused until tomorrow"
└─ Require manual review

Step 4: Reset (Next Day)
├─ Auto-reset at 9:30 AM ET
├─ Clear circuit breaker flag
├─ Resume normal operations
└─ Send notification:
    "✅ Circuit breaker reset - Trading resumed"
```

### Workflow G: Position Sizing

**Trigger:** Before every trade

```
Step 1: Get Account Info
├─ Total equity
├─ Buying power
├─ Current positions count
└─ Portfolio heat

Step 2: Calculate Size
├─ Base size = equity × position_size_pct (5%)
├─ Adjust for confidence:
│   • 70-79%: 80% of base
│   • 80-89%: 100% of base
│   • 90-100%: 120% of base
├─ Cap at buying_power
└─ Round to whole shares

Step 3: Validate
├─ Size > 0?
├─ Cost < buying_power?
├─ Won't exceed max_positions?
├─ Won't exceed portfolio_heat?
└─ If all pass: Approve

Step 4: Return Decision
├─ Approved: Return quantity
├─ Rejected: Return error with reason
└─ Log decision
```

---

## 📈 Data Flow Diagrams

### Real-Time Data Flow

```
Market Data Sources
        │
        ├─ Alpaca WebSocket ────┐
        ├─ Alpaca REST API ─────┤
        └─ News APIs ───────────┤
                                │
                                ▼
                        ┌───────────────┐
                        │  Data Cache   │
                        │  (15-60s TTL) │
                        └───────┬───────┘
                                │
                ┌───────────────┼───────────────┐
                │               │               │
                ▼               ▼               ▼
        ┌──────────┐    ┌──────────┐    ┌──────────┐
        │ Scanner  │    │ Monitor  │    │ Discord  │
        │  Agent   │    │  Agent   │    │   Bot    │
        └──────────┘    └──────────┘    └──────────┘
```

### Order Execution Flow

```
User Command/Signal
        │
        ▼
┌───────────────┐
│ Risk Manager  │ ──── Validate ───┐
└───────────────┘                   │
        │                           │
        ▼                           │
┌───────────────┐                   │
│ Execution     │ ◄─── Approved ────┘
│ Agent         │
└───────┬───────┘
        │
        ▼
┌───────────────┐
│ Alpaca API    │
│ Place Order   │
└───────┬───────┘
        │
        ▼
┌───────────────┐
│ Order Status  │
│ Tracking      │
└───────┬───────┘
        │
        ├─ Filled ──────► Update DB ──► Discord Notification
        ├─ Rejected ────► Log Error ──► Discord Alert
        └─ Pending ─────► Continue Tracking
```

---

## 🔄 State Transitions

### Position Lifecycle

```
NO POSITION
    │
    ▼ (Buy Signal + Approval)
PENDING ORDER
    │
    ├─► FILLED ────────────► OPEN POSITION
    │                              │
    └─► REJECTED ──────────► NO POSITION
                                   │
                                   ▼ (Monitoring)
                            OPEN POSITION
                                   │
                    ┌──────────────┼──────────────┐
                    │              │              │
                    ▼              ▼              ▼
            PROFIT TARGET    STOP LOSS      EXIT SIGNAL
                    │              │              │
                    └──────────────┴──────────────┘
                                   │
                                   ▼ (Sell Order)
                            PENDING CLOSE
                                   │
                                   ▼ (Filled)
                            CLOSED POSITION
                                   │
                                   ▼
                            PERFORMANCE RECORDED
```

---

## ⏱️ Timing & Schedules

### Scheduled Jobs

| Job | Frequency | Time | Purpose |
|-----|-----------|------|---------|
| Market Scan | 5 minutes | During market hours | Find opportunities |
| Position Monitor | 2 minutes | Always | Track P&L, alerts |
| Hourly Summary | 1 hour | Top of hour (9 AM-4 PM) | Activity report |
| Circuit Breaker Reset | Daily | 9:30 AM ET | Reset loss limits |
| News Monitor | 5 minutes | During market hours | Check news alerts |
| Greeks Monitor | 1 minute | During market hours | Options Greeks |

### Market Hours

- **Regular Hours:** 9:30 AM - 4:00 PM ET
- **Pre-Market:** 4:00 AM - 9:30 AM ET (monitoring only)
- **After-Hours:** 4:00 PM - 8:00 PM ET (monitoring only)
- **Weekend:** No trading, monitoring paused

---

*For architecture details, see SYSTEM_ARCHITECTURE.md*  
*For operational procedures, see OPERATIONAL_GUIDE.md*  
*For testing procedures, see TESTING_VALIDATION.md*
