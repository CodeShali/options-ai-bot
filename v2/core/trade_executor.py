"""
Trade execution via Alpaca.

For paper trading the order placement is attempted; if Alpaca's paper
environment doesn't support a specific option symbol we fall back to
recording the trade in our DB at the estimated price (simulated fill).
"""

from typing import Optional, Dict

from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce
from loguru import logger

from config.settings import settings
from db.database import get_state


def _trading() -> TradingClient:
    return TradingClient(
        settings.alpaca_api_key,
        settings.alpaca_secret_key,
        paper=settings.alpaca_paper,
    )


def place_buy(option_symbol: str, contracts: int = 1) -> Optional[str]:
    """Place a market buy order. Returns order_id or None."""
    if get_state("trading_mode") == "paper":
        logger.info("[PAPER] Simulated buy: {} × {}", contracts, option_symbol)
        return f"PAPER-{option_symbol}"

    try:
        order = _trading().submit_order(
            MarketOrderRequest(
                symbol=option_symbol,
                qty=contracts,
                side=OrderSide.BUY,
                time_in_force=TimeInForce.DAY,
            )
        )
        logger.info("Buy order placed: {} × {} — id={}", contracts, option_symbol, order.id)
        return str(order.id)
    except Exception as exc:
        logger.error("place_buy {} failed: {}", option_symbol, exc)
        return None


def place_sell(option_symbol: str, contracts: int = 1) -> Optional[str]:
    """Place a market sell order to close a position."""
    if get_state("trading_mode") == "paper":
        logger.info("[PAPER] Simulated sell: {} × {}", contracts, option_symbol)
        return f"PAPER-SELL-{option_symbol}"

    try:
        order = _trading().submit_order(
            MarketOrderRequest(
                symbol=option_symbol,
                qty=contracts,
                side=OrderSide.SELL,
                time_in_force=TimeInForce.DAY,
            )
        )
        logger.info("Sell order placed: {} × {} — id={}", contracts, option_symbol, order.id)
        return str(order.id)
    except Exception as exc:
        logger.error("place_sell {} failed: {}", option_symbol, exc)
        return None


def check_exit_conditions(trade: Dict, current_price: float) -> Optional[str]:
    """
    Returns an exit reason string if the position should be closed, else None.
    """
    entry = trade.get("entry_price")
    if not entry or entry == 0:
        return None

    pnl_pct = (current_price - entry) / entry * 100

    if pnl_pct >= settings.profit_target_pct * 100:
        return f"PROFIT TARGET: +{pnl_pct:.1f}%"

    if pnl_pct <= -(settings.stop_loss_pct * 100):
        return f"STOP LOSS: {pnl_pct:.1f}%"

    return None
