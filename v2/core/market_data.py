from datetime import datetime, date, timedelta
from typing import Optional, Dict, List

import pandas as pd
from alpaca.data.historical import StockHistoricalDataClient, OptionHistoricalDataClient
from alpaca.data.requests import (
    StockBarsRequest,
    StockSnapshotRequest,
    OptionChainRequest,
)
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit
from alpaca.trading.client import TradingClient
from loguru import logger

from config.settings import settings

# Lazy-initialised clients (avoids import-time errors when keys aren't set yet)
_stock: Optional[StockHistoricalDataClient] = None
_option: Optional[OptionHistoricalDataClient] = None
_trading: Optional[TradingClient] = None


def _get_stock() -> StockHistoricalDataClient:
    global _stock
    if _stock is None:
        _stock = StockHistoricalDataClient(settings.alpaca_api_key, settings.alpaca_secret_key)
    return _stock


def _get_option() -> OptionHistoricalDataClient:
    global _option
    if _option is None:
        _option = OptionHistoricalDataClient(settings.alpaca_api_key, settings.alpaca_secret_key)
    return _option


def _get_trading() -> TradingClient:
    global _trading
    if _trading is None:
        _trading = TradingClient(
            settings.alpaca_api_key,
            settings.alpaca_secret_key,
            paper=settings.alpaca_paper,
        )
    return _trading


# ── Price data ────────────────────────────────────────────────────────────────

def get_daily_bars(symbol: str, days: int = 60) -> Optional[pd.DataFrame]:
    """Daily OHLCV bars, most-recent last."""
    try:
        end = datetime.now()
        start = end - timedelta(days=days + 10)  # buffer for weekends/holidays
        req = StockBarsRequest(
            symbol_or_symbols=symbol,
            timeframe=TimeFrame.Day,
            start=start,
            end=end,
            feed="iex",
        )
        bars = _get_stock().get_stock_bars(req)
        df = bars.df
        if isinstance(df.index, pd.MultiIndex):
            df = df.xs(symbol, level=0)
        df = df.sort_index()
        return df if len(df) >= 20 else None
    except Exception as e:
        logger.error("daily_bars {}: {}", symbol, e)
        return None


def get_snapshot(symbol: str) -> Optional[Dict]:
    """Latest quote + day stats for a symbol."""
    try:
        req = StockSnapshotRequest(symbol_or_symbols=symbol, feed="iex")
        snaps = _get_stock().get_stock_snapshot(req)
        s = snaps.get(symbol)
        if not s:
            return None

        price = float(s.latest_trade.price) if s.latest_trade else None
        prev_close = float(s.prev_daily_bar.close) if s.prev_daily_bar else None
        change_pct = (
            (price - prev_close) / prev_close * 100
            if price and prev_close
            else None
        )
        return {
            "symbol": symbol,
            "price": price,
            "prev_close": prev_close,
            "change_pct": round(change_pct, 2) if change_pct is not None else None,
            "open": float(s.daily_bar.open) if s.daily_bar else None,
            "high": float(s.daily_bar.high) if s.daily_bar else None,
            "low": float(s.daily_bar.low) if s.daily_bar else None,
            "volume": int(s.daily_bar.volume) if s.daily_bar else None,
            "bid": float(s.latest_quote.bid_price) if s.latest_quote else None,
            "ask": float(s.latest_quote.ask_price) if s.latest_quote else None,
        }
    except Exception as e:
        logger.error("snapshot {}: {}", symbol, e)
        return None


# ── Options chain ─────────────────────────────────────────────────────────────

def get_options_chain(symbol: str, min_dte: int, max_dte: int) -> List[Dict]:
    """Filtered options chain around current price."""
    try:
        exp_start = date.today() + timedelta(days=min_dte)
        exp_end = date.today() + timedelta(days=max_dte)
        req = OptionChainRequest(
            underlying_symbol=symbol,
            expiration_date_gte=exp_start,
            expiration_date_lte=exp_end,
        )
        chain = _get_option().get_option_chain(req)
        contracts = []
        for sym_key, c in chain.items():
            opt_type = getattr(c, "type", None)
            opt_type_str = opt_type.value if hasattr(opt_type, "value") else str(opt_type)
            exp_date = getattr(c, "expiration_date", None)
            dte = (exp_date - date.today()).days if exp_date else 0
            contracts.append({
                "option_symbol": sym_key,
                "type": opt_type_str.lower(),
                "strike": float(c.strike_price),
                "expiry": str(exp_date),
                "dte": dte,
                "open_interest": getattr(c, "open_interest", 0) or 0,
                "implied_volatility": getattr(c, "implied_volatility", None),
            })
        return sorted(contracts, key=lambda x: (x["expiry"], x["strike"]))
    except Exception as e:
        logger.warning("options_chain {}: {} (non-fatal)", symbol, e)
        return []


# ── Account / Positions ───────────────────────────────────────────────────────

def get_account() -> Dict:
    try:
        a = _get_trading().get_account()
        return {
            "equity": float(a.equity),
            "cash": float(a.cash),
            "buying_power": float(a.buying_power),
            "day_trade_count": int(a.daytrade_count),
            "pdt_flagged": bool(a.pattern_day_trader),
        }
    except Exception as e:
        logger.error("get_account: {}", e)
        return {"equity": 0, "cash": 0, "buying_power": 0, "day_trade_count": 0, "pdt_flagged": False}


def get_positions() -> List[Dict]:
    try:
        return [
            {
                "symbol": p.symbol,
                "qty": float(p.qty),
                "entry_price": float(p.avg_entry_price),
                "current_price": float(p.current_price) if p.current_price else None,
                "market_value": float(p.market_value) if p.market_value else None,
                "unrealized_pl": float(p.unrealized_pl) if p.unrealized_pl else None,
                "unrealized_plpc": float(p.unrealized_plpc) if p.unrealized_plpc else None,
            }
            for p in _get_trading().get_all_positions()
        ]
    except Exception as e:
        logger.error("get_positions: {}", e)
        return []


def get_option_price(option_symbol: str) -> Optional[float]:
    """Current market price for an open option position."""
    try:
        for p in _get_trading().get_all_positions():
            if p.symbol == option_symbol and p.current_price:
                return float(p.current_price)
        return None
    except Exception as e:
        logger.error("get_option_price {}: {}", option_symbol, e)
        return None
