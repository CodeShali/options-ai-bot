# TARA Trading System - Testing & Validation Guide

**Last Updated:** October 21, 2025  
**Version:** 2.0

---

## ✅ Pre-Deployment Checklist

### System Requirements

- [ ] Python 3.11+ installed
- [ ] All dependencies installed (`pip install -r requirements.txt`)
- [ ] Environment variables configured (`.env` file)
- [ ] API keys valid (Alpaca, OpenAI, Discord)
- [ ] Discord bot has proper permissions
- [ ] Port 8000 available

### Configuration Validation

```bash
# Test environment variables
python3 -c "from config import settings; print('✅ Config loaded')"

# Test API connections
python3 -c "from services import get_alpaca_service; import asyncio; asyncio.run(get_alpaca_service().get_account()); print('✅ Alpaca connected')"
```

---

## 🧪 Unit Testing

### Core Components

#### 1. Test Data Pipeline

```python
# Test market data fetching
python3 -c "
import asyncio
from agents.data_pipeline_agent import DataPipelineAgent

async def test():
    agent = DataPipelineAgent()
    result = await agent.process({'action': 'get_quote', 'symbol': 'AAPL'})
    assert 'price' in result
    print('✅ Data Pipeline OK')

asyncio.run(test())
"
```

#### 2. Test Risk Manager

```python
# Test position sizing
python3 -c "
import asyncio
from agents.risk_manager_agent import RiskManagerAgent

async def test():
    agent = RiskManagerAgent()
    size = await agent.calculate_position_size(
        symbol='AAPL',
        price=185.50,
        confidence=0.85
    )
    assert size > 0
    print(f'✅ Risk Manager OK - Size: {size}')

asyncio.run(test())
"
```

#### 3. Test Buy Assistant

```python
# Test stock buy analysis
python3 -c "
import asyncio
from services.buy_assistant_service import get_buy_assistant_service

async def test():
    service = get_buy_assistant_service()
    result = await service.analyze_buy_opportunity('AAPL')
    assert 'current_price' in result
    print('✅ Buy Assistant OK')

asyncio.run(test())
"
```

---

## 🎮 Integration Testing

### Discord Bot Tests

#### Test 1: Bot Connection
```
Expected: Bot shows as "Online" in Discord
Test: Check bot status in Discord server
Result: ✅ / ❌
```

#### Test 2: Basic Commands
```
Command: /status
Expected: System status embed with metrics
Result: ✅ / ❌

Command: /account
Expected: Account information display
Result: ✅ / ❌

Command: /positions
Expected: List of current positions (or "No positions")
Result: ✅ / ❌
```

#### Test 3: Buy Stock Command
```
Command: /buy AAPL 1
Expected: 
- Analysis of AAPL
- Confirmation dialog with price and cost
- Buttons: [✅ Confirm] [❌ Cancel]
Result: ✅ / ❌

Action: Click ✅ Confirm
Expected: Order execution confirmation
Result: ✅ / ❌
```

#### Test 4: Buy Options Command
```
Command: /buy-option AAPL call 1000
Expected:
- Top 3 options with Greeks
- Risk levels displayed
- Buttons: [Buy Option #1] [#2] [#3]
Result: ✅ / ❌

Action: Click Buy Option #1
Expected: Option order confirmation
Result: ✅ / ❌
```

#### Test 5: NLP Commands
```
Message: "Buy 10 shares of AAPL"
Expected:
- AI understands intent
- Shows analysis
- Asks for confirmation
Result: ✅ / ❌

Message: "Should I buy TSLA?"
Expected:
- AI provides analysis
- Gives recommendation
- Explains reasoning
Result: ✅ / ❌
```

### API Integration Tests

#### Test 6: Alpaca API
```bash
# Test account access
curl -X GET "https://paper-api.alpaca.markets/v2/account" \
  -H "APCA-API-KEY-ID: $ALPACA_API_KEY" \
  -H "APCA-API-SECRET-KEY: $ALPACA_SECRET_KEY"

Expected: Account JSON with equity, buying_power
Result: ✅ / ❌
```

#### Test 7: OpenAI API
```python
python3 -c "
import asyncio
from services.llm_service import get_llm_service

async def test():
    llm = get_llm_service()
    response = await llm.chat_completion(
        messages=[{'role': 'user', 'content': 'Test'}],
        model='gpt-4o-mini'
    )
    assert len(response) > 0
    print('✅ OpenAI API OK')

asyncio.run(test())
"
```

#### Test 8: Claude API Fallback
```python
# Test automatic fallback to OpenAI
python3 -c "
import asyncio
from services.claude_service import get_claude_service

async def test():
    service = get_claude_service()
    # This will use OpenAI if Claude is out of credits
    result = await service.analyze_stock([
        {'role': 'user', 'content': 'Analyze AAPL'}
    ])
    assert len(result) > 0
    print('✅ Claude/OpenAI Fallback OK')

asyncio.run(test())
"
```

---

## 🔄 End-to-End Testing

### Scenario 1: Complete Trading Cycle

**Setup:**
```
1. System running
2. Market hours (or test mode)
3. Watchlist has symbols
4. System unpaused
```

**Test Steps:**

```
Step 1: Trigger Scan
Command: /scan
Expected: "🔍 Starting market scan..."
Result: ✅ / ❌

Step 2: Wait for Opportunities
Expected: Discord notification with opportunities
Time: < 30 seconds
Result: ✅ / ❌

Step 3: Review Opportunity
Expected:
- Symbol, price, confidence
- AI reasoning
- ✅/❌ reactions
Result: ✅ / ❌

Step 4: Approve Trade
Action: Click ✅
Expected: "Validating trade..."
Result: ✅ / ❌

Step 5: Order Execution
Expected: "✅ Buy order executed"
Time: < 5 seconds
Result: ✅ / ❌

Step 6: Position Appears
Command: /positions
Expected: New position listed
Result: ✅ / ❌

Step 7: Monitoring Starts
Wait: 2 minutes
Expected: Position being monitored (check logs)
Result: ✅ / ❌

Step 8: Close Position
Command: /sell AAPL
Expected: Position closed, P&L recorded
Result: ✅ / ❌
```

### Scenario 2: Manual Buy Flow

**Test Steps:**

```
Step 1: Manual Buy
Command: /buy AAPL 5
Expected: Confirmation dialog
Result: ✅ / ❌

Step 2: Confirm
Action: Click ✅ Confirm
Expected: Order placed
Result: ✅ / ❌

Step 3: Verify Position
Command: /positions
Expected: AAPL position with 5 shares
Result: ✅ / ❌

Step 4: Set Stop Loss
Message: "Set stop loss on AAPL at 10%"
Expected: Stop loss order placed
Result: ✅ / ❌

Step 5: Close Position
Command: /sell AAPL
Expected: Position closed
Result: ✅ / ❌
```

### Scenario 3: Options Trading

**Test Steps:**

```
Step 1: Find Options
Command: /buy-option AAPL call 1000
Expected: Top 3 options displayed
Result: ✅ / ❌

Step 2: Review Greeks
Expected:
- Delta, Theta, Gamma, Vega shown
- Risk level (LOW/MODERATE/HIGH)
- Quality score (0-100)
Result: ✅ / ❌

Step 3: Select Option
Action: Click "Buy Option #1"
Expected: Order placed
Result: ✅ / ❌

Step 4: Verify Position
Command: /positions
Expected: Option contract in positions
Result: ✅ / ❌
```

---

## 🛡️ Risk Management Testing

### Test 9: Circuit Breaker

**Setup:**
```python
# Temporarily lower circuit breaker limit for testing
# In config/settings.py:
max_daily_loss = 100  # Lower limit for testing
```

**Test Steps:**

```
Step 1: Check Current Loss
Command: /limits
Expected: Shows daily loss and limit
Result: ✅ / ❌

Step 2: Trigger Circuit Breaker
# Make trades that lose > $100
Expected: "🚨 Circuit breaker triggered"
Result: ✅ / ❌

Step 3: Verify Trading Stopped
Command: /scan
Expected: "Trading paused - circuit breaker active"
Result: ✅ / ❌

Step 4: Try to Trade
Command: /buy AAPL 1
Expected: "Cannot trade - circuit breaker active"
Result: ✅ / ❌

Step 5: Reset (Next Day)
# Wait for 9:30 AM ET or manually reset
Expected: "✅ Circuit breaker reset"
Result: ✅ / ❌
```

### Test 10: Position Limits

```
Step 1: Check Limit
Command: /limits
Expected: Shows max_positions (default: 10)
Result: ✅ / ❌

Step 2: Fill to Limit
# Open 10 positions
Expected: All positions opened
Result: ✅ / ❌

Step 3: Try to Exceed
Command: /buy TSLA 1
Expected: "Maximum positions reached"
Result: ✅ / ❌

Step 4: Close One Position
Command: /sell AAPL
Expected: Position closed
Result: ✅ / ❌

Step 5: Try Again
Command: /buy TSLA 1
Expected: Order placed successfully
Result: ✅ / ❌
```

---

## 📊 Performance Testing

### Test 11: Scan Performance

```bash
# Measure scan time
time python3 -c "
import asyncio
from agents.orchestrator_agent import OrchestratorAgent

async def test():
    agent = OrchestratorAgent()
    await agent.start()
    result = await agent.scan_and_trade()
    print(f'Scan result: {result}')

asyncio.run(test())
"

Expected: < 10 seconds
Result: ✅ / ❌
```

### Test 12: Order Execution Speed

```
Step 1: Place Order
Command: /buy AAPL 1
Time Start: [Record time]

Step 2: Confirm
Action: Click ✅

Step 3: Order Filled
Time End: [Record time]

Expected: < 2 seconds
Actual: ___ seconds
Result: ✅ / ❌
```

### Test 13: Concurrent Operations

```
Test: Multiple commands simultaneously
Commands:
- /positions
- /account
- /quote AAPL
- /quote TSLA
- /status

Expected: All respond within 5 seconds
Result: ✅ / ❌
```

---

## 🔍 Monitoring & Alerts Testing

### Test 14: Position Monitoring

```
Step 1: Open Position
Command: /buy AAPL 1

Step 2: Wait for Monitoring
Time: 2 minutes
Expected: Position monitored (check logs)
Result: ✅ / ❌

Step 3: Simulate Price Move
# Wait for real price movement or use test mode
Expected: Alert if move > 10%
Result: ✅ / ❌
```

### Test 15: Hourly Summary

```
Step 1: Wait for Top of Hour
Time: e.g., 10:00 AM, 11:00 AM
Expected: Hourly summary posted to Discord
Result: ✅ / ❌

Step 2: Verify Content
Expected:
- Scan activity
- Opportunities found
- Trades executed
- Portfolio status
Result: ✅ / ❌
```

---

## 🐛 Error Handling Testing

### Test 16: API Failures

```
Test: Disconnect internet briefly
Expected: 
- Graceful error messages
- Automatic retry
- No crashes
Result: ✅ / ❌
```

### Test 17: Invalid Commands

```
Command: /buy INVALID_SYMBOL
Expected: "Symbol not found" error
Result: ✅ / ❌

Command: /buy AAPL -5
Expected: "Invalid quantity" error
Result: ✅ / ❌

Command: /buy AAPL 1000000
Expected: "Insufficient buying power" error
Result: ✅ / ❌
```

### Test 18: Rate Limiting

```
Test: Send 100 commands rapidly
Expected:
- Rate limiting kicks in
- "Please wait" messages
- No crashes
Result: ✅ / ❌
```

---

## 📝 Validation Checklist

### Pre-Production Validation

**System Health:**
- [ ] All agents initialize successfully
- [ ] Discord bot connects
- [ ] API keys valid
- [ ] Database accessible
- [ ] Logs writing correctly

**Core Functionality:**
- [ ] Market scans complete
- [ ] Opportunities detected
- [ ] Orders execute
- [ ] Positions monitored
- [ ] Alerts sent

**Risk Management:**
- [ ] Circuit breaker works
- [ ] Position limits enforced
- [ ] Position sizing correct
- [ ] Stop losses set

**User Interface:**
- [ ] All Discord commands work
- [ ] NLP understands intents
- [ ] Confirmations display
- [ ] Notifications sent

**Performance:**
- [ ] Scans < 10s
- [ ] Orders < 2s
- [ ] Alerts < 5s
- [ ] No memory leaks

**Error Handling:**
- [ ] API failures handled
- [ ] Invalid inputs rejected
- [ ] Rate limiting works
- [ ] Logs errors properly

---

## 🚀 Production Readiness

### Final Checks Before Going Live

```
✅ All tests passed
✅ Paper trading successful for 1 week
✅ No critical bugs in logs
✅ Performance metrics acceptable
✅ Risk limits configured correctly
✅ Emergency procedures documented
✅ Backup and recovery tested
✅ Monitoring alerts working
✅ Team trained on operations
✅ Rollback plan ready
```

### Go-Live Procedure

```
1. [ ] Switch to LIVE mode in config
2. [ ] Verify LIVE API keys
3. [ ] Start with small position sizes
4. [ ] Monitor closely for first day
5. [ ] Gradually increase limits
6. [ ] Document any issues
7. [ ] Review daily performance
```

---

## 📊 Test Results Template

```
Test Date: ___________
Tester: ___________
Environment: Paper / Live

UNIT TESTS
- Data Pipeline: ✅ / ❌
- Risk Manager: ✅ / ❌
- Buy Assistant: ✅ / ❌

INTEGRATION TESTS
- Discord Bot: ✅ / ❌
- Alpaca API: ✅ / ❌
- OpenAI API: ✅ / ❌

E2E TESTS
- Trading Cycle: ✅ / ❌
- Manual Buy: ✅ / ❌
- Options Trading: ✅ / ❌

RISK TESTS
- Circuit Breaker: ✅ / ❌
- Position Limits: ✅ / ❌

PERFORMANCE TESTS
- Scan Speed: ___ seconds
- Order Speed: ___ seconds
- Concurrent Ops: ✅ / ❌

ISSUES FOUND:
1. _______________
2. _______________
3. _______________

OVERALL STATUS: PASS / FAIL

NOTES:
_________________
_________________
```

---

## 🔧 Debugging Guide

### Common Issues & Solutions

**Issue: Bot not responding**
```bash
# Check if running
ps aux | grep python

# Check logs
tail -50 logs/tara_$(date +%Y%m%d).log

# Restart
python3 main.py
```

**Issue: Orders not executing**
```
1. Check /status - is system paused?
2. Check /limits - circuit breaker triggered?
3. Check logs for errors
4. Verify API keys
5. Check buying power
```

**Issue: Scans not finding opportunities**
```
1. Check watchlist - /watchlist
2. Check market hours
3. Review scan logs
4. Adjust confidence thresholds
5. Verify data sources
```

---

*For architecture details, see SYSTEM_ARCHITECTURE.md*  
*For operational procedures, see OPERATIONAL_GUIDE.md*  
*For workflow details, see WORKFLOW_GUIDE.md*
