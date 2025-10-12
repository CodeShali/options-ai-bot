# Intelligent Alert System

## 🧠 Smart Alert Logic

The system now includes **intelligent alert filtering** to prevent spam and only send meaningful notifications.

---

## 🎯 Alert Intelligence Rules

### 1. **PROFIT_TARGET Alerts** 🎯
**Trigger**: Position reaches 50% profit

**Intelligence**:
- ✅ Sent **once** when threshold is first crossed
- ❌ **Not sent again** even if price continues to rise
- ✅ Resets when position is closed

**Example**:
```
Position at 50% → Alert sent ✅
Position at 52% → No alert (already notified)
Position at 55% → No alert (already notified)
Position closed → State cleared
New position at 50% → Alert sent ✅
```

---

### 2. **STOP_LOSS Alerts** ⚠️
**Trigger**: Position loses 30%

**Intelligence**:
- ✅ Sent **once** when threshold is first crossed
- ❌ **Not sent again** even if loss increases
- ✅ Resets when position is closed

**Example**:
```
Position at -30% → Alert sent ✅
Position at -32% → No alert (already notified)
Position at -35% → No alert (already notified)
Position closed → State cleared
```

---

### 3. **SIGNIFICANT_MOVE Alerts** 📊
**Trigger**: Position moves >10% (up or down)

**Intelligence**:
- ✅ Sent when position **first** crosses 10%
- ❌ **Not sent again** unless position moves **another 5%**
- ✅ Resets when position is closed

**Example Scenario 1 (Gradual Rise)**:
```
Position at 10% → Alert sent ✅ (first time)
Position at 11% → No alert (< 5% change)
Position at 12% → No alert (< 5% change)
Position at 15% → Alert sent ✅ (5% change from last alert)
Position at 16% → No alert (< 5% change)
Position at 20% → Alert sent ✅ (5% change from last alert)
```

**Example Scenario 2 (Volatile)**:
```
Position at 10% → Alert sent ✅
Position at 8%  → No alert (below threshold)
Position at 12% → Alert sent ✅ (crossed 10% again)
Position at 17% → Alert sent ✅ (5% change)
```

---

## 🔄 State Management

### Alert State Tracking
The system tracks:
- **Last alert type** sent for each position
- **Last percentage** when alert was sent
- **Timestamp** of last alert

### State Clearing
Alert states are automatically cleared when:
- Position is closed
- Position is sold
- System detects position no longer exists

---

## 📊 Alert Frequency Comparison

### Before (Spam Mode) ❌
```
22:40 - AAPL: UP 10.5%
22:42 - AAPL: UP 10.6%  ← Duplicate!
22:44 - AAPL: UP 10.7%  ← Duplicate!
22:46 - AAPL: UP 10.8%  ← Duplicate!
22:48 - AAPL: UP 10.9%  ← Duplicate!
```
**Result**: 5 alerts in 8 minutes for minimal change

### After (Intelligent Mode) ✅
```
22:40 - AAPL: UP 10.5%
22:50 - AAPL: UP 15.8%  ← 5% change, meaningful update
23:05 - AAPL: UP 21.2%  ← 5% change, meaningful update
```
**Result**: 3 alerts for significant milestones

---

## 🎯 Why This Works

### Prevents Spam
- No duplicate alerts for same condition
- Only alerts on meaningful changes (5% increments)
- Reduces Discord notification fatigue

### Keeps You Informed
- Critical alerts (profit target, stop loss) always sent
- Significant moves tracked at meaningful intervals
- You won't miss important changes

### Smart Thresholds
- **10%**: Initial significant move threshold
- **5%**: Subsequent update threshold
- **50%**: Profit target (critical)
- **30%**: Stop loss (critical)

---

## 🔧 Configuration

### Current Settings
```python
# In monitor_agent.py

# Initial threshold for significant move
if abs(unrealized_plpc) > 0.10:  # 10%

# Subsequent update threshold
if plpc_change < 0.05:  # 5% change required
    return False  # Don't send
```

### Customize Thresholds
Edit `/Users/shashank/Documents/options-AI-BOT/agents/monitor_agent.py`:

**Line 159**: Change initial threshold
```python
elif abs(unrealized_plpc) > 0.10:  # Change 0.10 to 0.15 for 15%
```

**Line 56**: Change update threshold
```python
if plpc_change < 0.05:  # Change 0.05 to 0.10 for 10% updates
```

---

## 📱 What You'll See Now

### First Alert (Position crosses 10%)
```
📊 AAPL: UP 10.23%

Why? Position has moved UP by 10.23% (Entry: $150.00 → Current: $165.35). 
Profit target is 50% ($225.00). Need 39.77% more to hit target. 
Current profit: $1,535.00.
```

### Next Alert (Position moves another 5%)
```
📊 AAPL: UP 15.67%

Why? Position has moved UP by 15.67% (Entry: $150.00 → Current: $173.51). 
Profit target is 50% ($225.00). Need 34.33% more to hit target. 
Current profit: $2,351.00.
```

### No More Alerts Until...
- Position moves another 5% (to ~20%)
- Position hits profit target (50%)
- Position hits stop loss (-30%)

---

## 🎓 Alert Logic Flow

```
┌─────────────────────────────────────┐
│  Position Monitoring (Every 2 min)  │
└─────────────┬───────────────────────┘
              │
              ▼
┌─────────────────────────────────────┐
│  Check Position P/L Percentage      │
└─────────────┬───────────────────────┘
              │
              ▼
        ┌─────┴─────┐
        │           │
        ▼           ▼
   >= 50%?      <= -30%?
   (Profit)     (Loss)
        │           │
        ▼           ▼
   Check if     Check if
   already      already
   alerted      alerted
        │           │
        ▼           ▼
   Send once    Send once
   only         only
        │           │
        └─────┬─────┘
              │
              ▼
        > 10% move?
        (Significant)
              │
              ▼
        Check last
        alert state
              │
              ▼
        ┌─────┴─────┐
        │           │
        ▼           ▼
   First time?  Changed 5%?
        │           │
        ▼           ▼
   Send alert   Send alert
        │           │
        └─────┬─────┘
              │
              ▼
        Update state
        (type, %, time)
```

---

## 💡 Pro Tips

### Monitor Alert Patterns
Watch your Discord for:
- **Frequent updates** (every 5%) = Volatile position
- **No updates** = Stable position
- **Critical alerts** = Action needed

### Adjust Based on Trading Style
**Day Trader**:
- Lower thresholds (7% initial, 3% updates)
- More frequent alerts

**Swing Trader**:
- Higher thresholds (15% initial, 7% updates)
- Fewer, more significant alerts

**Long-term Holder**:
- Much higher thresholds (20% initial, 10% updates)
- Only major moves

---

## 🔍 Debugging Alert State

### View Current Alert States
The system tracks states in memory. To see them, add this to your code:

```python
# In monitor_agent.py, add logging
logger.info(f"Current alert states: {self.last_alert_state}")
```

### Check Logs
```bash
tail -f logs/trading.log | grep "alert state"
```

You'll see:
```
Cleared alert state for closed position: AAPL
Updated alert state: TSLA -> SIGNIFICANT_MOVE at 12.5%
```

---

## 🎯 Summary

### What Changed
- ✅ **PROFIT_TARGET**: Once per threshold
- ✅ **STOP_LOSS**: Once per threshold
- ✅ **SIGNIFICANT_MOVE**: Initial + every 5% change
- ✅ **State tracking**: Per position
- ✅ **Auto-cleanup**: When positions close

### Benefits
- 📉 **90% fewer duplicate alerts**
- 🎯 **Only meaningful updates**
- 🧠 **Smart threshold tracking**
- 🔄 **Automatic state management**

### No More Spam!
Your Discord will now only show:
- Critical alerts (profit/loss targets)
- Meaningful position updates (5% increments)
- Important state changes

---

**Enjoy your intelligent, spam-free alert system! 🎉**

*Last Updated: 2025-10-11*
