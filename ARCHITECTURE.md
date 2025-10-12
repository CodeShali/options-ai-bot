# System Architecture Diagrams

## 🏗️ High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER INTERFACES                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────┐         ┌──────────────┐                      │
│  │   Discord    │         │   FastAPI    │                      │
│  │     Bot      │         │     API      │                      │
│  │  (Commands)  │         │  (REST API)  │                      │
│  └──────┬───────┘         └──────┬───────┘                      │
│         │                        │                               │
└─────────┼────────────────────────┼───────────────────────────────┘
          │                        │
          └────────┬───────────────┘
                   │
┌──────────────────▼──────────────────────────────────────────────┐
│                    ORCHESTRATOR AGENT                            │
│              (Main Coordinator & Workflow Manager)               │
└───┬────────┬────────┬────────┬────────┬────────────────────────┘
    │        │        │        │        │
    ▼        ▼        ▼        ▼        ▼
┌────────┐┌──────┐┌────────┐┌────────┐┌────────┐
│  Data  ││Strat ││  Risk  ││  Exec  ││Monitor │
│Pipeline││ egy  ││Manager ││ ution  ││        │
│ Agent  ││Agent ││ Agent  ││ Agent  ││ Agent  │
└───┬────┘└──┬───┘└───┬────┘└───┬────┘└───┬────┘
    │        │        │         │         │
    └────────┴────────┴─────────┴─────────┘
    ┌─────────────────┴─────────────────┐
    │                                    │
    ▼                                    ▼
┌─────────────────┐            ┌─────────────────┐
│  CORE SERVICES  │            │   DATA LAYER    │
├─────────────────────────────────────────────────────────────┤
│ • Alpaca API    │            │ • SQLite DB     │
│ • OpenAI GPT-4  │            │ • Trade History │
│ • Database      │            │ • Positions     │
│ • Scheduler     │            │ • Analytics     │
│ • Logger        │            │ • System State  │
└─────────────────┘            └─────────────────┘

---

## 🔄 Trading Workflow

### Scan & Trade Loop (Every 5 minutes)

```
START
  │
  ▼
┌─────────────────────────────────────┐
│ 1. CHECK CIRCUIT BREAKER            │
│    Risk Manager validates daily loss│
└───────────┬─────────────────────────┘
            │
            ▼ [OK]
┌─────────────────────────────────────┐
│ 2. CHECK POSITION LIMITS            │
│    Risk Manager checks available    │
│    position slots                   │
└───────────┬─────────────────────────┘
            │
            ▼ [Slots Available]
┌─────────────────────────────────────┐
│ 3. SCAN OPPORTUNITIES               │
│    Data Pipeline scans watchlist    │
│    • Fetch quotes                   │
│    • Get historical data            │
│    • Calculate indicators           │
│    • Score opportunities            │
└───────────┬─────────────────────────┘
            │
            ▼ [Opportunities Found]
┌─────────────────────────────────────┐
│ 4. AI ANALYSIS                      │
│    Strategy Agent analyzes with     │
│    OpenAI GPT-4                     │
│    • Market conditions              │
│    • Technical indicators           │
│    • Risk/reward ratio              │
│    • Confidence score               │
└───────────┬─────────────────────────┘
            │
            ▼ [BUY Signals]
┌─────────────────────────────────────┐
│ 5. CALCULATE POSITION SIZE          │
│    Risk Manager determines size     │
│    • Based on confidence            │
│    • Adjusted for risk level        │
│    • Within position limits         │
└───────────┬─────────────────────────┘
            │
            ▼
┌─────────────────────────────────────┐
│ 6. VALIDATE TRADE                   │
│    Risk Manager validates           │
│    • Position limits                │
│    • Buying power                   │
│    • Existing positions             │
│    • System state                   │
└───────────┬─────────────────────────┘
            │
            ▼ [Approved]
┌─────────────────────────────────────┐
│ 7. EXECUTE TRADE                    │
│    Execution Agent places order     │
│    • Market order via Alpaca        │
│    • Record in database             │
│    • Update positions               │
└───────────┬─────────────────────────┘
            │
            ▼
┌─────────────────────────────────────┐
│ 8. NOTIFY                           │
│    Send Discord notification        │
│    • Trade details                  │
│    • AI reasoning                   │
│    • Confidence level               │
└─────────────────────────────────────┘
  │
  ▼
END
```

### Monitor & Exit Loop (Every 2 minutes)

```
START
  │
  ▼
┌─────────────────────────────────────┐
│ 1. GET ALL POSITIONS                │
│    Monitor Agent fetches positions  │
│    from Alpaca                      │
└───────────┬─────────────────────────┘
            │
            ▼ [For Each Position]
┌─────────────────────────────────────┐
│ 2. CHECK EXIT CONDITIONS            │
│    Monitor Agent evaluates:         │
│    • Profit target (50%)            │
│    • Stop loss (30%)                │
│    • Significant moves (>10%)       │
└───────────┬─────────────────────────┘
            │
            ▼ [Alert Generated]
┌─────────────────────────────────────┐
│ 3. GET CURRENT MARKET DATA          │
│    Data Pipeline fetches quote      │
└───────────┬─────────────────────────┘
            │
            ▼
┌─────────────────────────────────────┐
│ 4. AI EXIT ANALYSIS                 │
│    Strategy Agent analyzes with     │
│    Claude AI                        │
│    • Current position status        │
│    • Market conditions              │
│    • Exit recommendation            │
└───────────┬─────────────────────────┘
            │
            ▼ [EXIT Recommended]
┌─────────────────────────────────────┐
│ 5. EXECUTE EXIT                     │
│    Execution Agent closes position  │
│    • Sell order via Alpaca          │
│    • Record in database             │
│    • Mark position closed           │
└───────────┬─────────────────────────┘
            │
            ▼
┌─────────────────────────────────────┐
│ 6. NOTIFY                           │
│    Send Discord notification        │
│    • Exit reason                    │
│    • Profit/Loss                    │
│    • Performance                    │
└─────────────────────────────────────┘
  │
  ▼
END
```

---

## 🎯 Agent Responsibilities

```
┌─────────────────────────────────────────────────────────────┐
│                    ORCHESTRATOR AGENT                        │
├─────────────────────────────────────────────────────────────┤
│ • Coordinates all agents                                     │
│ • Manages trading workflows                                  │
│ • Handles Discord integration                                │
│ • Emergency stop functionality                               │
│ • Error handling and recovery                                │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                   DATA PIPELINE AGENT                        │
├─────────────────────────────────────────────────────────────┤
│ • Scans watchlist for opportunities                          │
│ • Fetches market data (quotes, bars)                         │
│ • Calculates basic indicators                                │
│ • Scores opportunities                                       │
│ • Manages watchlist                                          │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                     STRATEGY AGENT                           │
├─────────────────────────────────────────────────────────────┤
│ • AI-powered analysis with OpenAI                            │
│ • Opportunity evaluation                                     │
│ • Exit signal analysis                                       │
│ • Technical indicator calculation                            │
│ • Batch analysis support                                     │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                   RISK MANAGER AGENT                         │
├─────────────────────────────────────────────────────────────┤
│ • Trade validation                                           │
│ • Position size calculation                                  │
│ • Circuit breaker monitoring                                 │
│ • Position limit enforcement                                 │
│ • Exit condition checking                                    │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    EXECUTION AGENT                           │
├─────────────────────────────────────────────────────────────┤
│ • Buy order execution                                        │
│ • Sell order execution                                       │
│ • Position closing                                           │
│ • Order status tracking                                      │
│ • Database recording                                         │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                     MONITOR AGENT                            │
├─────────────────────────────────────────────────────────────┤
│ • Real-time position monitoring                              │
│ • Alert generation                                           │
│ • Exit signal detection                                      │
│ • Dashboard data generation                                  │
│ • Position status tracking                                   │
└─────────────────────────────────────────────────────────────┘
```

---

## 📊 Data Flow

```
┌──────────────┐
│   Alpaca     │ ◄─── Market Data ─────┐
│     API      │                        │
└──────┬───────┘                        │
       │                                │
       │ Positions, Orders,             │
       │ Account Info                   │
       │                                │
       ▼                                │
┌──────────────┐                        │
│   Services   │                        │
│   Layer      │                        │
└──────┬───────┘                        │
       │                                │
       │ Processed Data                 │
       │                                │
       ▼                                │
┌──────────────┐     Analysis      ┌───┴────────┐
│    Agents    │ ◄────────────────►│ OpenAI API │
│    Layer     │     Requests      └────────────┘
└──────┬───────┘
       │
       │ Trade Decisions,
       │ Alerts, Updates
       │
       ▼
┌──────────────┐
│   Database   │
│   (SQLite)   │
└──────┬───────┘
       │
       │ Historical Data,
       │ Analytics
       │
       ▼
┌──────────────┐
│   Discord    │
│     Bot      │
└──────────────┘
```

---

## 🔐 Security Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     ENVIRONMENT LAYER                        │
│                   (.env file - not in git)                   │
├─────────────────────────────────────────────────────────────┤
│ • API Keys (Alpaca, Discord, Anthropic)                      │
│ • Trading Configuration                                      │
│ • Risk Parameters                                            │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                   CONFIGURATION LAYER                        │
│                  (Pydantic Settings)                         │
├─────────────────────────────────────────────────────────────┤
│ • Validates environment variables                            │
│ • Type checking                                              │
│ • Default values                                             │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                   APPLICATION LAYER                          │
├─────────────────────────────────────────────────────────────┤
│ • Services use validated config                              │
│ • No hardcoded credentials                                   │
│ • Secure API communication                                   │
└─────────────────────────────────────────────────────────────┘

VALIDATION LAYERS:
┌─────────────────────────────────────────────────────────────┐
│ 1. Trade Validation (Risk Manager)                          │
│    ├─ Position limits                                        │
│    ├─ Size limits                                            │
│    ├─ Circuit breaker                                        │
│    └─ System state                                           │
│                                                              │
│ 2. Mode Confirmation (Discord Bot)                          │
│    └─ Explicit confirmation for live trading                │
│                                                              │
│ 3. Database Audit Trail                                     │
│    └─ All trades logged with timestamps                     │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔄 State Management

```
┌─────────────────────────────────────────────────────────────┐
│                      SYSTEM STATE                            │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐ │
│  │   Trading    │    │   Circuit    │    │   Position   │ │
│  │     Mode     │    │   Breaker    │    │    Limits    │ │
│  │ (paper/live) │    │   Status     │    │   (5 max)    │ │
│  └──────────────┘    └──────────────┘    └──────────────┘ │
│                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐ │
│  │   Paused     │    │    Daily     │    │   Active     │ │
│  │    State     │    │     Loss     │    │  Positions   │ │
│  │  (yes/no)    │    │   Tracker    │    │   (0-5)      │ │
│  └──────────────┘    └──────────────┘    └──────────────┘ │
│                                                              │
└───────────────────────┬──────────────────────────────────────┘
                        │
                        ▼
            ┌───────────────────────┐
            │   Persisted in DB     │
            │   (system_state)      │
            └───────────────────────┘
```

---

## 📡 Communication Patterns

### Async Message Flow

```
Discord Command
    │
    ▼
┌─────────────┐
│ Discord Bot │
└──────┬──────┘
       │ async call
       ▼
┌─────────────┐
│Orchestrator │
└──────┬──────┘
       │ async call
       ▼
┌─────────────┐
│   Agent     │
└──────┬──────┘
       │ async call
       ▼
┌─────────────┐
│   Service   │
└──────┬──────┘
       │ async call
       ▼
┌─────────────┐
│ External API│
└──────┬──────┘
       │ response
       ▼
    (bubbles back up)
       │
       ▼
Discord Notification
```

### Scheduled Task Flow

```
APScheduler
    │
    ▼
┌─────────────┐
│  Scheduler  │
└──────┬──────┘
       │ triggers
       ▼
┌─────────────┐
│Orchestrator │
└──────┬──────┘
       │ coordinates
       ▼
┌─────────────┐
│   Agents    │ ◄─┐
└──────┬──────┘   │
       │          │
       │ process  │ loop
       │          │
       └──────────┘
```

---

## 🎯 Decision Flow

### Buy Decision

```
Opportunity Detected
    │
    ▼
┌─────────────────────┐
│ Technical Analysis  │
│ (Data Pipeline)     │
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│ AI Analysis         │ ◄─── Claude AI
│ (Strategy Agent)    │
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│ Risk Validation     │
│ (Risk Manager)      │
└──────┬──────────────┘
       │
       ▼
    [Approved?]
       │
       ├─ Yes ──► Execute Trade
       │
       └─ No ───► Skip
```

### Sell Decision

```
Position Monitored
    │
    ▼
┌─────────────────────┐
│ Check Conditions    │
│ • Profit Target     │
│ • Stop Loss         │
│ • Significant Move  │
└──────┬──────────────┘
       │
       ▼
    [Alert?]
       │
       ├─ Yes ──► AI Exit Analysis ◄─── OpenAI GPT-4
       │              │
       │              ▼
       │          [EXIT?]
       │              │
       │              ├─ Yes ──► Execute Exit
       │              │
       │              └─ No ───► Hold
       │
       └─ No ───► Continue Monitoring
```

---

This architecture ensures:
- ✅ **Separation of Concerns**: Each agent has specific responsibilities
- ✅ **Scalability**: Easy to add new agents or features
- ✅ **Reliability**: Multiple validation layers
- ✅ **Observability**: Comprehensive logging and monitoring
- ✅ **Security**: Environment-based configuration
- ✅ **Flexibility**: Configurable parameters
