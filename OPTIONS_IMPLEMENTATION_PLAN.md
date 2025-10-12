# Options Trading Implementation Plan

## 🎯 Goal
Build a hybrid system that trades **both stocks AND options** based on market signals.

---

## ✅ Configuration Added

I've added options configuration to the system:

```env
# Options Trading Configuration
ENABLE_OPTIONS_TRADING=true
ENABLE_STOCK_TRADING=true
OPTIONS_MAX_CONTRACTS=2
OPTIONS_MAX_PREMIUM=500
OPTIONS_MIN_DTE=30
OPTIONS_MAX_DTE=45
OPTIONS_CLOSE_DTE=7
OPTIONS_STRIKE_PREFERENCE=OTM
OPTIONS_OTM_STRIKES=1
```

---

## 🛠️ Implementation Required

### 1. Alpaca Options API Integration
**File**: `services/alpaca_service.py`

**Need to Add:**
```python
async def get_options_chain(self, symbol: str, expiration_date: str = None):
    """Get options chain for a symbol."""
    # Fetch available options contracts
    # Filter by expiration date range (30-45 DTE)
    # Return calls and puts with strikes

async def get_option_quote(self, symbol: str, strike: float, 
                          expiration: str, option_type: str):
    """Get quote for specific option contract."""
    # Fetch current premium
    # Get Greeks (Delta, Gamma, Theta, Vega)
    # Return bid/ask spread

async def place_option_order(self, symbol: str, quantity: int,
                            strike: float, expiration: str,
                            option_type: str, side: str):
    """Place options order (buy/sell call/put)."""
    # Format option symbol (e.g., AAPL251220C00180000)
    # Place market/limit order
    # Return order confirmation

async def get_option_positions(self):
    """Get all open options positions."""
    # Fetch options positions
    # Calculate P/L
    # Get days to expiration
    # Return formatted positions
```

---

### 2. Strategy Agent Updates
**File**: `agents/strategy_agent.py`

**Need to Add:**
```python
async def analyze_for_options(self, opportunity: Dict) -> Dict:
    """
    Determine if opportunity is better for stock or options.
    Decide call vs put, strike, expiration.
    """
    
    # Decision logic:
    if score >= 75:  # Strong bullish
        return {
            "instrument": "option",
            "type": "call",
            "strike_selection": "OTM",  # Slightly out of money
            "confidence": 80,
            "reasoning": "Strong bullish signal, buy call"
        }
    
    elif score <= 40:  # Strong bearish
        return {
            "instrument": "option",
            "type": "put",
            "strike_selection": "OTM",
            "confidence": 75,
            "reasoning": "Strong bearish signal, buy put"
        }
    
    elif 60 <= score < 75:  # Moderate bullish
        return {
            "instrument": "stock",  # Less risky
            "confidence": 65,
            "reasoning": "Moderate signal, buy stock"
        }
    
    else:  # Unclear
        return {
            "instrument": "none",
            "confidence": 0,
            "reasoning": "Signal not strong enough"
        }

async def select_option_strike(self, symbol: str, option_type: str,
                               current_price: float, chain: Dict) -> Dict:
    """
    Select optimal strike price based on preference.
    """
    
    if settings.options_strike_preference == "ATM":
        # Find strike closest to current price
        strike = find_nearest_strike(current_price, chain)
    
    elif settings.options_strike_preference == "OTM":
        # Find strike N strikes away
        if option_type == "call":
            strike = current_price + (settings.options_otm_strikes * strike_interval)
        else:  # put
            strike = current_price - (settings.options_otm_strikes * strike_interval)
    
    return {
        "strike": strike,
        "premium": get_premium(strike, chain),
        "delta": get_delta(strike, chain),
        "expiration": select_expiration(chain)
    }
```

---

### 3. Risk Manager Updates
**File**: `agents/risk_manager_agent.py`

**Need to Add:**
```python
async def validate_options_trade(self, trade: Dict) -> Dict:
    """
    Validate options trade with additional checks.
    """
    
    # Check 1: Premium within limit
    premium_cost = trade['premium'] * 100 * trade['contracts']
    if premium_cost > settings.options_max_premium * trade['contracts']:
        return {"approved": False, "reason": "Premium too expensive"}
    
    # Check 2: Days to expiration
    dte = calculate_dte(trade['expiration'])
    if dte < settings.options_min_dte or dte > settings.options_max_dte:
        return {"approved": False, "reason": "Expiration outside range"}
    
    # Check 3: Max contracts
    if trade['contracts'] > settings.options_max_contracts:
        return {"approved": False, "reason": "Too many contracts"}
    
    # Check 4: Greeks analysis
    if abs(trade['delta']) < 0.30:  # Too far OTM
        return {"approved": False, "reason": "Delta too low"}
    
    # Check 5: Buying power
    if premium_cost > account['buying_power']:
        return {"approved": False, "reason": "Insufficient buying power"}
    
    return {"approved": True, "reason": "All checks passed"}

async def calculate_options_position_size(self, analysis: Dict) -> Dict:
    """
    Calculate number of contracts based on confidence and risk.
    """
    
    confidence = analysis['confidence']
    premium = analysis['premium']
    
    # High confidence: 2 contracts
    if confidence >= 80:
        contracts = min(2, settings.options_max_contracts)
    # Medium confidence: 1 contract
    elif confidence >= 70:
        contracts = 1
    else:
        contracts = 0
    
    # Ensure premium within limits
    total_cost = premium * 100 * contracts
    if total_cost > settings.options_max_premium * contracts:
        contracts = int(settings.options_max_premium / (premium * 100))
    
    return {
        "contracts": contracts,
        "premium": premium,
        "total_cost": total_cost
    }
```

---

### 4. Execution Agent Updates
**File**: `agents/execution_agent.py`

**Need to Add:**
```python
async def execute_options_buy(self, trade: Dict) -> Dict:
    """
    Execute options buy order.
    """
    
    try:
        # Format option symbol
        option_symbol = format_option_symbol(
            trade['symbol'],
            trade['expiration'],
            trade['option_type'],
            trade['strike']
        )
        
        # Place order
        order = await self.alpaca.place_option_order(
            symbol=trade['symbol'],
            quantity=trade['contracts'],
            strike=trade['strike'],
            expiration=trade['expiration'],
            option_type=trade['option_type'],
            side='buy'
        )
        
        # Record in database
        await self.db.record_trade({
            "symbol": trade['symbol'],
            "instrument": "option",
            "option_type": trade['option_type'],
            "strike": trade['strike'],
            "expiration": trade['expiration'],
            "action": "buy",
            "quantity": trade['contracts'],
            "price": trade['premium'],
            "total_value": trade['premium'] * 100 * trade['contracts']
        })
        
        return {
            "success": True,
            "order_id": order['id'],
            "contracts": trade['contracts'],
            "premium": trade['premium']
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}
```

---

### 5. Monitor Agent Updates
**File**: `agents/monitor_agent.py`

**Need to Add:**
```python
async def monitor_options_positions(self) -> Dict:
    """
    Monitor options positions with additional checks.
    """
    
    positions = await self.alpaca.get_option_positions()
    alerts = []
    
    for position in positions:
        # Calculate P/L
        entry_premium = position['avg_entry_price']
        current_premium = position['current_price']
        unrealized_plpc = (current_premium - entry_premium) / entry_premium
        
        # Check profit target (50%)
        if unrealized_plpc >= settings.profit_target_pct:
            alerts.append({
                "type": "PROFIT_TARGET",
                "symbol": position['symbol'],
                "option_type": position['option_type'],
                "strike": position['strike'],
                "expiration": position['expiration']
            })
        
        # Check stop loss (30%)
        elif unrealized_plpc <= -settings.stop_loss_pct:
            alerts.append({
                "type": "STOP_LOSS",
                "symbol": position['symbol']
            })
        
        # Check days to expiration
        dte = calculate_dte(position['expiration'])
        if dte <= settings.options_close_dte:
            alerts.append({
                "type": "EXPIRATION_WARNING",
                "symbol": position['symbol'],
                "dte": dte,
                "message": f"Only {dte} days to expiration"
            })
        
        # Check theta decay (time decay accelerating)
        if dte <= 14 and unrealized_plpc < 0:
            alerts.append({
                "type": "THETA_DECAY",
                "symbol": position['symbol'],
                "message": "Time decay accelerating, consider closing"
            })
    
    return {"alerts": alerts}
```

---

## 📊 Trading Logic Flow

### Entry Decision
```
Scan finds opportunity (score 85)
├─ Strong bullish signal
├─ AI confidence: 80%
└─ Decision: BUY CALL OPTION

Select Contract:
├─ Current price: $175
├─ Strike: $180 (1 strike OTM)
├─ Expiration: 35 DTE
├─ Premium: $3.50
├─ Contracts: 2
└─ Total cost: $700

Risk Validation:
├─ Premium OK? ($700 < $1,000) ✅
├─ DTE OK? (35 days, 30-45 range) ✅
├─ Contracts OK? (2 <= 2 max) ✅
├─ Delta OK? (0.45 > 0.30) ✅
└─ Buying power OK? ✅

Execute:
└─ BUY 2 AAPL Call $180 12/20 @ $3.50
```

### Monitoring
```
Every 2 minutes:
├─ Check P/L (target: 50%, stop: 30%)
├─ Check DTE (close at 7 days)
├─ Check theta decay
└─ Generate alerts
```

### Exit Decision
```
Option reaches 50% profit:
├─ Entry: $3.50
├─ Current: $5.25
├─ Profit: 50%
└─ AI confirms exit

OR

7 days to expiration:
├─ DTE: 7 days
├─ Current P/L: +20%
└─ Close to avoid theta decay

Execute:
└─ SELL 2 AAPL Call $180 12/20 @ $5.25
```

---

## 🎯 Hybrid Strategy

### When to Use Options
```
Strong Signals (score >= 75 or <= 40):
├─ Bullish → Buy Call
├─ Bearish → Buy Put
└─ Higher leverage, higher risk/reward
```

### When to Use Stocks
```
Moderate Signals (60 <= score < 75):
├─ Buy stock
└─ Lower risk, steady gains
```

---

## ⚠️ Important Notes

### Alpaca Options Requirements
1. **Account approval** needed for options trading
2. **Options agreement** must be signed
3. **Minimum account balance** may be required
4. **Paper trading** supports options (test first!)

### Options Risks
- **Time decay** (Theta) - options lose value over time
- **Volatility** - can work for or against you
- **Expiration** - can expire worthless
- **Leverage** - amplifies both gains and losses

### Recommended Approach
1. **Test in paper trading first**
2. **Start with 1 contract** per trade
3. **Use longer DTE** (30-45 days)
4. **Close before expiration** (7 days)
5. **Monitor closely** (every 2 minutes)

---

## 📋 Implementation Checklist

- [x] Add options configuration to settings
- [x] Update .env.example with options settings
- [ ] Extend Alpaca service for options API
- [ ] Update strategy agent for options analysis
- [ ] Modify risk manager for options validation
- [ ] Update execution agent for options orders
- [ ] Add options monitoring logic
- [ ] Update database schema for options
- [ ] Add Discord commands for options
- [ ] Update documentation
- [ ] Test in paper trading
- [ ] Verify options approval with Alpaca

---

## 🚀 Next Steps

This is a **significant implementation** that requires:
- **~4-6 hours** of development time
- **Alpaca options API** integration
- **Extensive testing** in paper mode
- **Options trading approval** from Alpaca

**Recommendation**: 
1. First, verify your Alpaca account has **options trading enabled**
2. Test the current stock trading system thoroughly
3. Then we can implement full options support

Would you like me to:
1. **Continue with full implementation now** (~4-6 hours)
2. **Implement in phases** (start with basic options, add features later)
3. **Focus on stock trading first**, add options later

Let me know and I'll proceed accordingly!

---

*Created: 2025-10-11*
