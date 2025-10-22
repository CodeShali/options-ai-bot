# TARA Trading System - Architecture Documentation

**Last Updated:** October 21, 2025  
**Version:** 2.0  
**Status:** Production Ready

---

## 🏗️ System Architecture Overview

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Discord Interface                       │
│  (Commands, NLP, Interactive Buttons, Real-time Updates)    │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│                  Orchestrator Agent                          │
│         (Coordinates all agents and workflows)               │
└──┬──────┬──────┬──────┬──────┬──────┬──────┬──────┬────────┘
   │      │      │      │      │      │      │      │
   ▼      ▼      ▼      ▼      ▼      ▼      ▼      ▼
┌──────┐┌──────┐┌──────┐┌──────┐┌──────┐┌──────┐┌──────┐┌──────┐
│Data  ││Intel ││Strat ││Risk  ││Exec  ││Monit ││Buy   ││News  │
│Pipe  ││Scan  ││egy   ││Mgr   ││ution ││or    ││Asst  ││Monit │
└──┬───┘└──┬───┘└──┬───┘└──┬───┘└──┬───┘└──┬───┘└──┬───┘└──┬───┘
   │       │       │       │       │       │       │       │
   └───────┴───────┴───────┴───────┴───────┴───────┴───────┘
                            │
                ┌───────────▼───────────┐
                │   External Services   │
                ├───────────────────────┤
                │ • Alpaca Trading API  │
                │ • OpenAI GPT-4        │
                │ • Claude (fallback)   │
                │ • News APIs           │
                │ • Market Data         │
                └───────────────────────┘
```

---

## 🧩 Core Components

### 1. **Orchestrator Agent** (`agents/orchestrator_agent.py`)
**Purpose:** Central coordinator for all trading operations

**Responsibilities:**
- Workflow coordination (scan → analyze → risk check → execute)
- Agent lifecycle management
- System state management (pause/resume)
- Error handling and recovery

**Key Methods:**
- `scan_and_trade()` - Main trading workflow
- `monitor_and_exit()` - Position monitoring workflow
- `emergency_stop()` - Emergency shutdown

---

### 2. **Data Pipeline Agent** (`agents/data_pipeline_agent.py`)
**Purpose:** Data collection and preprocessing

**Responsibilities:**
- Market data fetching (quotes, bars, snapshots)
- Watchlist management
- Data caching and optimization
- Symbol validation

**Key Methods:**
- `scan_opportunities()` - Scan watchlist for opportunities
- `get_market_data()` - Fetch real-time data
- `add_to_watchlist()` - Manage watchlist

---

### 3. **Intelligent Scanner** (`agents/intelligent_scanner.py`)
**Purpose:** AI-powered opportunity detection

**Responsibilities:**
- Technical analysis (RSI, MACD, Bollinger Bands)
- Multi-timeframe analysis
- Strategy signal generation
- AI-powered analysis (Claude/OpenAI)

**Key Methods:**
- `scan_with_full_analysis()` - Comprehensive scan
- `_full_technical_analysis()` - Technical indicators
- `_get_ai_analysis()` - AI reasoning

**Strategies:**
- Momentum Breakout
- Mean Reversion
- Volume Spike
- Pattern Recognition

---

### 4. **Strategy Agent** (`agents/strategy_agent.py`)
**Purpose:** Quantitative strategy execution

**Responsibilities:**
- Strategy signal generation
- Backtesting
- Performance tracking
- Strategy selection

**Available Strategies:**
- Momentum Breakout
- MA Crossover
- Mean Reversion
- Iron Condor (options)

---

### 5. **Risk Manager Agent** (`agents/risk_manager_agent.py`)
**Purpose:** Risk control and validation

**Responsibilities:**
- Position sizing
- Circuit breaker (daily loss limits)
- Portfolio heat management
- Trade validation

**Key Methods:**
- `validate_trade()` - Pre-trade risk check
- `check_circuit_breaker()` - Loss limit check
- `calculate_position_size()` - Size determination

**Risk Limits:**
- Max daily loss: $1,000 (configurable)
- Max positions: 10
- Max portfolio heat: 6.0
- Position size: 2-5% of equity

---

### 6. **Execution Agent** (`agents/execution_agent.py`)
**Purpose:** Order execution and management

**Responsibilities:**
- Order placement (market, limit, stop)
- Order tracking and updates
- Position management
- Stop loss / take profit orders

**Key Methods:**
- `execute_buy()` - Execute buy orders
- `execute_sell()` - Execute sell orders
- `set_stop_losses()` - Set protective stops
- `set_take_profits()` - Set profit targets

---

### 7. **Monitor Agent** (`agents/monitor_agent.py`)
**Purpose:** Position monitoring and alerts

**Responsibilities:**
- Real-time position monitoring
- P&L tracking
- Alert generation
- Exit signal detection

**Key Methods:**
- `monitor_positions()` - Monitor all positions
- `check_alerts()` - System-level alerts
- `get_position_status()` - Detailed position info

**Alert Types:**
- Profit target reached (15%+)
- Stop loss triggered (10%-)
- Significant moves (10%+)
- Exit signals

---

### 8. **Buy Assistant Service** (`services/buy_assistant_service.py`)
**Purpose:** Intelligent buy order assistance

**Responsibilities:**
- Stock buy analysis
- Options Greeks analysis
- Risk assessment
- Order execution

**Key Methods:**
- `analyze_buy_opportunity()` - Analyze stock buy
- `find_best_options()` - Find optimal options
- `execute_stock_buy()` - Execute stock order
- `execute_option_buy()` - Execute option order

**Greeks Analysis:**
- Delta (Δ) - Price sensitivity
- Theta (Θ) - Time decay
- Gamma (Γ) - Delta change rate
- Vega (V) - Volatility sensitivity

---

## 🔄 Data Flow

### Trading Workflow

```
1. SCAN PHASE
   ├─ Data Pipeline fetches market data
   ├─ Intelligent Scanner analyzes symbols
   ├─ Strategy Agent generates signals
   └─ AI provides reasoning (Claude/OpenAI)

2. VALIDATION PHASE
   ├─ Risk Manager validates trade
   ├─ Position limits checked
   ├─ Circuit breaker checked
   └─ Portfolio heat calculated

3. EXECUTION PHASE
   ├─ Execution Agent places order
   ├─ Order tracking initiated
   ├─ Database updated
   └─ Discord notification sent

4. MONITORING PHASE
   ├─ Monitor Agent tracks position
   ├─ P&L calculated continuously
   ├─ Alerts generated on thresholds
   └─ Exit signals detected

5. EXIT PHASE
   ├─ Exit signal validated
   ├─ Sell order placed
   ├─ Position closed
   └─ Performance recorded
```

---

## 🗄️ Database Schema

### Key Collections/Tables

**1. Positions**
```python
{
    "symbol": str,
    "qty": int,
    "entry_price": float,
    "current_price": float,
    "unrealized_pl": float,
    "unrealized_plpc": float,
    "timestamp": datetime
}
```

**2. Trades**
```python
{
    "symbol": str,
    "action": str,  # BUY/SELL
    "quantity": int,
    "price": float,
    "timestamp": datetime,
    "strategy": str,
    "confidence": float
}
```

**3. System State**
```python
{
    "paused": bool,
    "circuit_breaker": bool,
    "daily_loss": float,
    "last_reset": datetime
}
```

**4. Cache**
```python
{
    "key": str,
    "value": Any,
    "ttl": int,  # seconds
    "timestamp": datetime
}
```

---

## 🔌 External Integrations

### 1. **Alpaca Trading API**
**Purpose:** Brokerage and market data
**Endpoints Used:**
- `/v2/account` - Account info
- `/v2/positions` - Current positions
- `/v2/orders` - Order management
- `/v2/stocks/{symbol}/quotes/latest` - Real-time quotes
- `/v2/stocks/{symbol}/bars` - Historical data
- `/v2/options/contracts` - Options chain

### 2. **OpenAI API**
**Purpose:** AI analysis and NLP
**Models Used:**
- GPT-4o - Primary analysis
- GPT-4o-mini - Conversations

**Usage:**
- Stock analysis
- Opportunity reasoning
- NLP command processing
- Conversation management

### 3. **Claude API (Anthropic)**
**Purpose:** Advanced AI analysis
**Model:** Claude Sonnet 4
**Fallback:** Automatically switches to OpenAI if credits low

### 4. **News APIs**
**Purpose:** Real-time news monitoring
**Sources:**
- Alpaca News API
- Financial news aggregators

---

## 🔐 Security Architecture

### API Key Management
- Environment variables only
- Never hardcoded
- Separate keys for dev/prod

### Rate Limiting
- API call tracking (200/min limit)
- Automatic throttling
- Queue management

### Error Handling
- Graceful degradation
- Automatic retries
- Fallback mechanisms

---

## 📊 Performance Optimization

### Caching Strategy
- Account data: 60s TTL
- Positions: 30s TTL
- Market data: 15s TTL
- News: 5min TTL

### Parallel Processing
- Concurrent API calls
- Async/await throughout
- Non-blocking operations

### Resource Management
- Connection pooling
- Memory optimization
- Garbage collection

---

## 🔄 Scalability

### Current Capacity
- 10 concurrent positions
- 200 API calls/minute
- 100+ symbols in watchlist
- Real-time monitoring

### Scaling Options
- Increase position limits
- Add more strategies
- Multi-account support
- Distributed processing

---

## 🛠️ Technology Stack

**Core:**
- Python 3.11+
- AsyncIO for concurrency
- Discord.py for bot
- FastAPI for API server

**AI/ML:**
- OpenAI GPT-4
- Claude Sonnet 4
- Custom technical indicators

**Data:**
- Alpaca API
- Real-time WebSockets
- Historical data APIs

**Infrastructure:**
- APScheduler for jobs
- Loguru for logging
- Pydantic for validation

---

## 📈 System Metrics

**Performance Targets:**
- Scan latency: < 10s
- Order execution: < 2s
- Alert latency: < 5s
- Uptime: 99.9%

**Resource Usage:**
- Memory: ~500MB
- CPU: 10-20% average
- Network: ~1MB/min

---

*For operational procedures, see OPERATIONAL_GUIDE.md*  
*For testing procedures, see TESTING_VALIDATION.md*  
*For workflow details, see WORKFLOW_GUIDE.md*
