# Alert System Explained

## 🔔 What Are Alerts?

Alerts are automatic notifications sent by the **Monitor Agent** when it detects important changes in your positions. The system monitors your positions **every 2 minutes** and checks for specific conditions.

---

## 📊 Types of Alerts

### 1. **SIGNIFICANT_MOVE** 📊
**When**: Position moves more than 10% (up or down)

**What it means**: Your position has had a notable price change, but hasn't reached your profit target or stop loss yet.

**Example Message**:
```
📊 AAPL: UP 15.23%

Why? Position has moved UP by 15.23% (Entry: $150.00 → Current: $172.85). 
Profit target is 50% ($225.00). Need 34.77% more to hit target. 
Current profit: $2,285.00.
```

**What to do**: 
- **If UP**: Monitor closely - you're making money but haven't hit your target yet
- **If DOWN**: Watch carefully - you're losing money but haven't hit stop loss yet

---

### 2. **PROFIT_TARGET** 🎯
**When**: Position reaches 50% profit (configurable in `.env`)

**What it means**: Congratulations! Your position has hit your profit target.

**Example Message**:
```
🎯 AAPL: Profit target reached at 52.34%!

Why? Position entered at $150.00, now at $228.51. 
Target was 50% ($225.00). Current profit: $7,851.00. 
Consider taking profits!
```

**What to do**: 
- The system will automatically analyze if you should sell
- You can also manually sell using `/sell AAPL` in Discord
- Consider taking profits to lock in gains

---

### 3. **STOP_LOSS** ⚠️
**When**: Position loses 30% or more (configurable in `.env`)

**What it means**: Your position has hit the stop loss threshold to prevent larger losses.

**Example Message**:
```
⚠️ TSLA: Stop loss triggered at -31.45%!

Why? Position entered at $200.00, now at $137.10. 
Stop loss was 30% ($140.00). Current loss: -$6,290.00. 
Position should be closed to prevent further losses.
```

**What to do**: 
- The system will automatically analyze if you should exit
- Consider closing the position to prevent further losses
- Use `/sell TSLA` to manually close

---

## 🔍 Alert Components

Each alert includes:

### 1. **Message** (Short summary)
- Quick overview of what happened
- Example: `📊 AAPL: UP 15.23%`

### 2. **Reasoning** (Detailed explanation)
- **Entry price**: What you paid
- **Current price**: Current market price
- **Profit/Loss**: Dollar amount gained/lost
- **Distance to targets**: How far to profit target or stop loss
- **Recommendation**: What you should consider doing

### 3. **Position Details** (JSON data)
```json
{
  "symbol": "AAPL",
  "qty": 100,
  "entry_price": 150.00,
  "current_price": 172.85,
  "unrealized_pl": 2285.00,
  "unrealized_plpc": 15.23,
  "profit_target": 225.00,
  "stop_loss": 105.00
}
```

---

## ⚙️ Alert Settings

You can configure alert thresholds in your `.env` file:

```env
PROFIT_TARGET_PCT=0.50    # 50% profit target
STOP_LOSS_PCT=0.30        # 30% stop loss
```

### Current Settings:
- **Profit Target**: 50% gain
- **Stop Loss**: 30% loss
- **Significant Move**: 10% change (hardcoded)

---

## 📱 Where Alerts Appear

### 1. Discord Channel
- Real-time notifications
- Formatted with emojis and reasoning
- Channel ID: 1424598089074737242

### 2. Log File
- All alerts logged to `logs/trading.log`
- View with: `tail -f logs/trading.log`

### 3. Database
- Stored in `data/trading.db`
- Table: `positions` (updated with each alert)

---

## 🔄 Alert Frequency

### Position Monitoring
- **Runs**: Every 2 minutes
- **Checks**: All open positions
- **Triggers**: When conditions are met

### Why You Got Duplicate Alerts
You likely received the same alert twice because:
1. The position was still at >10% when the next monitoring cycle ran
2. The system checks every 2 minutes
3. If the price hasn't changed much, it will alert again

**Solution**: The alert will stop once:
- The position moves below 10%
- The position hits profit target or stop loss
- The position is closed

---

## 🎯 What Each Alert Tells You

### SIGNIFICANT_MOVE Alert Breakdown

**Before Update** (What you saw):
```
Alert: Significant move
{
  "type": "SIGNIFICANT_MOVE",
  "symbol": "AAPL",
  "position": {...}
}
```

**After Update** (What you'll see now):
```
📊 AAPL: UP 15.23%

Why? Position has moved UP by 15.23% (Entry: $150.00 → Current: $172.85). 
Profit target is 50% ($225.00). Need 34.77% more to hit target. 
Current profit: $2,285.00.

{
  "type": "SIGNIFICANT_MOVE",
  "severity": "INFO",
  "action_required": "REVIEW",
  "position": {
    "symbol": "AAPL",
    "qty": 100,
    "entry_price": 150.00,
    "current_price": 172.85,
    "unrealized_pl": 2285.00,
    "unrealized_plpc": 15.23
  }
}
```

---

## 🛠️ Managing Alerts

### View Current Positions
```bash
source venv/bin/activate
python scripts/view_positions.py
```

### Check Position Status in Discord
```
/positions
```

### Manually Close a Position
```
/sell SYMBOL
```

### Check System Status
```
/status
```

---

## 📊 Alert Action Guide

| Alert Type | Severity | Action Required | What to Do |
|------------|----------|-----------------|------------|
| SIGNIFICANT_MOVE | INFO | REVIEW | Monitor the position |
| PROFIT_TARGET | INFO | SELL | Consider taking profits |
| STOP_LOSS | WARNING | SELL | Consider cutting losses |
| CIRCUIT_BREAKER | CRITICAL | STOP_TRADING | Trading halted |
| LOW_BUYING_POWER | WARNING | REVIEW | Check account balance |

---

## 🤖 Automated Actions

The system will automatically:

1. **Monitor** all positions every 2 minutes
2. **Alert** you when conditions are met
3. **Analyze** with OpenAI whether to exit
4. **Execute** exits if AI confirms and risk manager approves
5. **Notify** you of all actions taken

---

## 💡 Pro Tips

### Reduce Alert Noise
If you're getting too many alerts:
1. Increase the significant move threshold (edit `monitor_agent.py` line 107)
2. Adjust your profit target/stop loss in `.env`
3. Close positions that are hovering around 10%

### Understand Your Positions
- **Green (UP)**: Making money, watch for profit target
- **Red (DOWN)**: Losing money, watch for stop loss
- **~10%**: Will trigger significant move alerts

### Take Action
- Don't ignore STOP_LOSS alerts - they protect you
- Consider taking profits at PROFIT_TARGET
- Review SIGNIFICANT_MOVE alerts to understand trends

---

## 📞 Need Help?

### Check Logs
```bash
tail -f logs/trading.log
```

### View Position Details
```bash
python scripts/view_positions.py
```

### Discord Commands
```
/status      - System overview
/positions   - All open positions
/trades      - Recent trades
/performance - Performance metrics
```

---

## 🎓 Example Scenarios

### Scenario 1: Winning Position
```
1. Buy AAPL at $150 (100 shares)
2. Price moves to $165 → Alert: "📊 AAPL: UP 10.00%"
3. Price moves to $172 → Alert: "📊 AAPL: UP 14.67%"
4. Price moves to $225 → Alert: "🎯 AAPL: Profit target reached at 50.00%!"
5. System analyzes and may auto-sell
```

### Scenario 2: Losing Position
```
1. Buy TSLA at $200 (50 shares)
2. Price drops to $178 → Alert: "📊 TSLA: DOWN 11.00%"
3. Price drops to $160 → Alert: "📊 TSLA: DOWN 20.00%"
4. Price drops to $140 → Alert: "⚠️ TSLA: Stop loss triggered at -30.00%!"
5. System analyzes and may auto-sell to prevent further losses
```

---

**Your alerts now include detailed reasoning to help you understand what's happening with your positions!** 🎉

*Last Updated: 2025-10-11*
