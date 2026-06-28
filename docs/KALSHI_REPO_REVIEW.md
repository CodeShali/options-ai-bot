# Review: newyorkcompute/kalshi

**Repository:** https://github.com/newyorkcompute/kalshi  
**Review Date:** 2026-06-28  
**Reviewed By:** Claude (claude-sonnet-4-6)

---

## Overview

`newyorkcompute/kalshi` is a TypeScript monorepo providing AI-integrated tooling for trading on [Kalshi](https://kalshi.com), a CFTC-regulated prediction market exchange. The project targets AI agent developers, quantitative traders, and market makers who want programmatic access to Kalshi's prediction market data and order execution.

It is fundamentally different from `options-ai-bot` (which trades equity options on Alpaca) — Kalshi trades binary contracts on future event outcomes (elections, Fed rate decisions, Bitcoin prices, weather, etc.) rather than equity derivatives.

---

## Architecture

The project is organized as an NX monorepo with clear separation of concerns:

```
kalshi/
├── apps/
│   └── mm/                  # Market-maker daemon
├── packages/
│   ├── core/                # Shared SDK utilities, config, WebSocket client
│   ├── mcp/                 # MCP server exposing 14 tools
│   ├── tui/                 # Terminal UI dashboard
│   └── weather/             # NWS weather integration + probability models
└── skills/
    └── kalshi-trading/      # Claude Agent Skill definition + TypeScript client
```

**Toolchain:** TypeScript/ESM, NX, Vitest, ESLint, Node 22+.

The design favors composition: `packages/core` provides shared auth and API primitives consumed by both `packages/mcp` and `apps/mm`. This avoids duplication and keeps the auth layer in one place.

---

## Components

### `packages/mcp` — MCP Server (14 tools)

The crown jewel of the repo. Exposes Kalshi's full API surface as an MCP server consumable by any MCP-compatible AI client (Claude Desktop, Claude Code, Cursor).

**Market tools:**
| Tool | Description |
|------|-------------|
| `get_markets` | List/search markets with filters (status, ticker, series, event) |
| `get_market` | Full detail on a single market by ticker |
| `get_orderbook` | Market depth up to 100 price levels |
| `get_trades` | Recent trades with timestamp range and pagination |

**Event tools:**
| Tool | Description |
|------|-------------|
| `get_events` | List events with optional nested market data |
| `get_event` | Detailed info on a specific event |

**Portfolio tools:**
| Tool | Description |
|------|-------------|
| `get_balance` | Account balance and portfolio value |
| `get_positions` | Current positions, filterable by ticker/event |
| `get_fills` | Trade fill history (v0.5.0) |
| `get_settlements` | Settlement history with market outcomes (v0.5.0) |

**Order tools:**
| Tool | Description |
|------|-------------|
| `get_orders` | All orders with status/time filters |
| `create_order` | Place a trade — **executes real money** |
| `cancel_order` | Cancel a single order by ID |
| `batch_cancel_orders` | Cancel up to 20 orders in one call (v0.5.0) |

**Authentication:** Requires `KALSHI_API_KEY` (string) and `KALSHI_PRIVATE_KEY` (RSA PEM) as environment variables. The server validates both at startup and fails fast if either is missing.

**Versioning:** Currently at v0.5.0 with a well-maintained changelog.

---

### `apps/mm` — Automated Market Maker Daemon

A full market-making bot with five quoting strategies, risk controls, and a compliance layer for formal Kalshi MM programs.

**Strategies:**

| Strategy | Description |
|----------|-------------|
| **Symmetric** | Fixed spread (e.g., 4¢) with fixed contract size each side. Simple baseline. |
| **Adaptive** | Dynamic spreads that widen based on inventory imbalance and adverse selection score. Includes microprice calculation. |
| **Avellaneda-Stoikov** | Mathematically optimal quoting using stochastic control theory. Configurable risk aversion (`gamma`) and volatility estimate. |
| **Optimism-Tax** | Exploits the empirical finding that YES longshots below 15¢ are systematically overpriced by up to 64 percentage points. |
| **Weather-Informed** | Uses NWS forecast data to compute fair value for weather markets, then quotes around that. |

**Risk controls (all configurable):**
- Max contracts per market (default: 100)
- Max total cross-market exposure (default: 500 contracts)
- Daily loss circuit breaker (default: $50)
- Max contracts per order (default: 25)
- Stale order timeout (default: 30s)
- Minimum spread enforcement (default: 2¢)

**Adverse selection detection:** The daemon models order flow toxicity and widens quotes when it detects informed trading.

**Market scanner:** Automatically identifies markets meeting configurable filters (min volume, max orderbook depth, spread range, time-to-expiry, category). Avoids manual market selection.

**HTTP control plane:** Optional API on port 3001 for runtime inspection and control.

**WebSocket orderbook:** Real-time L2 orderbook streaming with reconnect logic (5s backoff).

**Compliance layer:** Tracks activity against formal MM program requirements (maker volume, spread requirements, uptime).

---

### `packages/weather` — Weather Intelligence

Integrates National Weather Service (NWS) forecast data to derive probability distributions for weather-related prediction markets (e.g., "Will it snow in NYC on January 15?"). Feeds into the weather-informed MM strategy.

This is a niche but clever feature — weather markets on Kalshi have relatively thin participation from sophisticated forecasters, making data-driven pricing a real edge.

---

### `packages/tui` — Terminal UI

A TUI dashboard built for monitoring active MM positions, live P&L, orderbook depth, and fill history. Targeted at operators running the MM bot in a terminal session.

---

### `skills/kalshi-trading` — Claude Agent Skill

A self-contained Claude skill that gives agents a TypeScript client and API documentation for writing and executing code against Kalshi directly — an alternative to the MCP server for code-first workflows where the agent writes the trading logic itself.

---

## Strengths

1. **Well-scoped MCP interface.** 14 tools cover read and write operations cleanly. Tool definitions appear to follow MCP best practices with clear parameter schemas.

2. **Multiple quoting strategies.** The Avellaneda-Stoikov and Optimism-Tax strategies show genuine quantitative thought, not just a toy bot.

3. **Fail-fast auth.** Validating credentials at server startup prevents silent failures mid-session when an agent tries to trade.

4. **Risk controls are first-class.** Position limits, daily loss limits, adverse selection detection, and minimum spread enforcement are built in rather than bolted on.

5. **Dual-interface design.** Offering both MCP server and Agent Skills is smart — different use cases (structured AI tool calls vs. code-generation agents) have different optimal integration paths.

6. **Changelog discipline.** Versioning is tracked cleanly with `CHANGELOG.md` files per package.

7. **Monorepo hygiene.** Shared core package, consistent TypeScript config, per-package test runners.

---

## Weaknesses / Areas of Concern

1. **`create_order` executes real trades.** There is no sandbox mode mentioned in the MCP server itself beyond using Kalshi's demo environment. Any agent with MCP access can place live orders. This warrants an explicit warning in Claude Desktop config and ideally a `dry_run` parameter.

2. **RSA private key in environment.** PEM keys in env vars are a common footgun — easy to accidentally log, include in crash dumps, or commit. A path-to-file pattern (`KALSHI_PRIVATE_KEY_PATH`) would be safer.

3. **No rate limiting in the MCP layer.** Kalshi's API has rate limits; rapid AI agent tool calls could hit them. The MCP server should handle 429 responses gracefully and surface them to the agent.

4. **Market maker default risk limits are small.** $50 daily loss limit is intentionally conservative for demos, but new users may copy config values without realizing they need tuning for their actual capital.

5. **Weather strategy is US-only.** NWS covers the US only; international weather markets on Kalshi (if any) would need a different data source.

6. **No paper trading within the MM bot itself.** The bot relies on Kalshi's demo environment rather than having an internal simulation layer, which limits backtesting.

7. **Node 22+ requirement.** Enforces a recent runtime; users on older Node installs need to upgrade.

---

## Integration Opportunities with `options-ai-bot`

The current `options-ai-bot` trades equity options via Alpaca and uses Claude for sentiment analysis. Kalshi prediction markets are a complementary (not competing) asset class.

### Option A: Add Kalshi as a data signal source

Kalshi markets on macro events (Fed decisions, CPI prints, elections) provide real-money probability estimates that can inform equity options positioning — e.g., if Kalshi's Fed rate market implies a 70% chance of a 25bps cut, that's a useful input to volatility/direction models.

**Implementation:** Add a `KalshiService` in Python using Kalshi's REST API (they have an official Python SDK) that the `strategy_agent.py` can query for event probabilities. No order execution required.

### Option B: Install the MCP server and expose it to the Claude agent

Add the `@newyorkcompute/kalshi-mcp` server to Claude Code's MCP config. This gives Claude direct tool-call access to Kalshi market data during analysis sessions without writing Python integration code.

**Implementation:** Add an MCP entry to `.mcp.json` with the npm package and env var credentials.

### Option C: Add a Kalshi prediction market trading module

Build a Python service (`services/kalshi_service.py`) that executes binary contract trades on Kalshi events that correlate with the existing equity signals.

**Implementation cost:** Medium. Requires Kalshi account, API credentials, and careful risk sizing since Kalshi contracts are binary (0 or $1) with different risk profiles than equity options.

### Recommended path

Start with **Option B** (MCP server) for immediate value during research and analysis, then evaluate **Option A** (Kalshi as signal source) if macro event probability data improves strategy returns.

---

## Summary

`newyorkcompute/kalshi` is a high-quality, well-structured project for anyone wanting to build on Kalshi's prediction market API. The MCP server is immediately useful for Claude-based trading research. The market maker is sophisticated enough for real-money deployment with appropriate configuration. The main gaps are around operational security (key handling, rate limiting) and simulation tooling.

For `options-ai-bot`, the most actionable near-term integration is installing the MCP package to give Claude direct access to Kalshi market data and probabilities during analysis sessions.
