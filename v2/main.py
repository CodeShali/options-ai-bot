"""
TARA v2 — main entry point.

Starts three concurrent loops:
  1. APScheduler — scan for signals (morning + afternoon windows), monitor
     open positions every 2 min, force-close at 3:45 PM ET.
  2. Telegram bot — polling for commands and callbacks.
  3. Streamlit dashboard runs separately via `streamlit run dashboard/app.py`.
"""

import asyncio
import sys
from datetime import datetime, time as dtime
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from loguru import logger

from config.settings import settings
from core.indicators import compute_all
from core.market_data import (
    get_account,
    get_daily_bars,
    get_option_price,
    get_options_chain,
    get_snapshot,
)
from core.risk_manager import max_contracts, validate_trade
from core.signal_engine import analyze_opportunity
from core.trade_executor import check_exit_conditions, place_buy, place_sell
from db.database import (
    get_open_trades,
    get_state,
    get_weekly_trade_count,
    init_db,
    record_trade_close,
    record_trade_open,
    set_state,
)
from bot.telegram_bot import (
    consume_manual_scan,
    create_app,
    send_message,
    send_signal_alert,
)

ET = ZoneInfo("America/New_York")

# ── Market-hours helpers ──────────────────────────────────────────────────────

_MORNING_OPEN  = dtime(9, 35)
_MORNING_CLOSE = dtime(11, 30)
_AFTERNOON_OPEN  = dtime(13, 0)
_AFTERNOON_CLOSE = dtime(14, 30)
_FORCE_CLOSE_TIME = dtime(15, 45)


def _now_et() -> datetime:
    return datetime.now(ET)


def _in_scan_window() -> bool:
    t = _now_et().time()
    morning   = _MORNING_OPEN   <= t <= _MORNING_CLOSE
    afternoon = _AFTERNOON_OPEN <= t <= _AFTERNOON_CLOSE
    return morning or afternoon


def _market_open() -> bool:
    now = _now_et()
    if now.weekday() >= 5:      # Saturday / Sunday
        return False
    t = now.time()
    return dtime(9, 30) <= t <= dtime(16, 0)


# ── Signal scanning ───────────────────────────────────────────────────────────

async def _scan_symbol(symbol: str, account: dict, weekly_used: int) -> bool:
    """
    Fetch market data, pre-filter, ask Claude, validate risk, then trade or
    send alert. Returns True if a trade was initiated.
    """
    bars = get_daily_bars(symbol, days=60)
    if bars is None:
        return False

    indicators = compute_all(bars)

    # Cheap pre-filter — skip boring / low-conviction setups before calling Claude
    if indicators.get("volume_ratio", 0) < 1.2:
        logger.debug("{}: volume_ratio below threshold — skipping", symbol)
        return False
    if abs(indicators.get("price_change_1d_pct", 0)) < 0.5:
        logger.debug("{}: price change too small — skipping", symbol)
        return False

    snapshot = get_snapshot(symbol)
    if not snapshot:
        return False

    chain = get_options_chain(symbol, settings.min_dte, settings.max_dte)

    market_data = {
        "snapshot":      snapshot,
        "indicators":    indicators,
        "options_chain": chain,
        "news":          [],         # news enrichment can be added later
    }

    signal = analyze_opportunity(symbol, market_data, weekly_used)
    if signal is None:
        return False

    if not signal.get("trade"):
        logger.info("{}: Claude skipped — {}", symbol, signal.get("skip_reason"))
        return False

    ok, reason = validate_trade(signal, account)
    if not ok:
        logger.info("{}: risk check failed — {}", symbol, reason)
        await send_message(f"⚠️ Signal for `{symbol}` blocked: {reason}")
        return False

    # Determine contract count
    equity = account.get("equity", settings.account_size)
    entry  = signal.get("entry_price_estimate", 0)
    signal["contracts"] = max_contracts(entry, equity) if entry else 1

    auto = get_state("auto_trade") == "true"
    if auto:
        return await _execute_signal(signal)
    else:
        await send_signal_alert(signal)
        return False


async def _execute_signal(signal: dict) -> bool:
    """Place the order and log it in the DB."""
    symbol   = signal.get("symbol", "")
    action   = signal.get("action", "")
    strike   = signal.get("strike", 0)
    expiry   = signal.get("expiry", "")
    entry    = signal.get("entry_price_estimate", 0)
    contracts = signal.get("contracts", 1)

    # Build an Alpaca-style OCC option symbol (approximation for paper trades)
    # Real live trading will use the symbol from the options chain
    chain = get_options_chain(symbol, settings.min_dte, settings.max_dte)
    opt_type = "call" if action == "BUY_CALL" else "put"
    match = next(
        (c for c in chain if c["type"] == opt_type and c["strike"] == strike and c["expiry"] == expiry),
        None,
    )
    option_symbol = match["option_symbol"] if match else f"{symbol}_PAPER_{strike}{opt_type[0].upper()}"

    order_id = place_buy(option_symbol, contracts)
    if order_id is None:
        await send_message(f"❌ Order failed for `{symbol}` {action}")
        return False

    trade_id = record_trade_open(
        symbol=symbol,
        option_symbol=option_symbol,
        option_type=opt_type,
        strike=strike,
        expiry=expiry,
        entry_price=entry,
        contracts=contracts,
        order_id=order_id,
    )

    await send_message(
        f"✅ *Trade executed*\n"
        f"`{symbol}` {action} ${strike} exp {expiry}\n"
        f"Entry ~${entry:.2f} × {contracts}ct  |  DB id={trade_id}"
    )
    logger.info("Trade opened: id={} {} {} ${}", trade_id, symbol, action, strike)
    return True


async def run_scan():
    """Called by scheduler — scans all watchlist symbols if conditions allow."""
    manual = consume_manual_scan()

    if not manual and not _in_scan_window():
        return
    if not manual and not _market_open():
        return
    if get_state("scanning_paused") == "true":
        return

    weekly = get_weekly_trade_count()
    if weekly >= settings.max_trades_per_week:
        logger.info("Weekly trade limit reached ({}/{})", weekly, settings.max_trades_per_week)
        return

    if get_open_trades():
        logger.debug("Open position exists — skipping scan")
        return

    account = get_account()
    logger.info("Scanning {} symbols…", len(settings.watchlist))

    for symbol in settings.watchlist:
        weekly = get_weekly_trade_count()
        if weekly >= settings.max_trades_per_week:
            break
        traded = await _scan_symbol(symbol, account, weekly)
        if traded:
            break   # one position at a time


# ── Position monitoring ───────────────────────────────────────────────────────

async def monitor_positions():
    """Check open positions against profit target and stop loss."""
    if not _market_open():
        return

    open_trades = get_open_trades()
    if not open_trades:
        return

    for trade in open_trades:
        current = get_option_price(trade["option_symbol"])
        if current is None:
            continue

        reason = check_exit_conditions(trade, current)
        if reason:
            await _close_position(trade, current, reason)


async def force_close_all():
    """3:45 PM ET — close everything, no overnight holds."""
    open_trades = get_open_trades()
    if not open_trades:
        return

    logger.warning("Force-close triggered at 3:45 PM ET")
    await send_message("⏰ *3:45 PM ET — force-closing all positions.*")

    for trade in open_trades:
        current = get_option_price(trade["option_symbol"]) or trade["entry_price"]
        await _close_position(trade, current, "TIME STOP 3:45 PM")


async def _close_position(trade: dict, exit_price: float, reason: str):
    order_id = place_sell(trade["option_symbol"], trade["contracts"])
    if order_id is None:
        logger.error("Sell order failed for {}", trade["option_symbol"])
        return

    pnl, pnl_pct = record_trade_close(trade["id"], exit_price)

    icon = "✅" if pnl >= 0 else "❌"
    await send_message(
        f"{icon} *Position closed*\n"
        f"`{trade['symbol']}` {trade['option_type'].upper()} ${trade['strike']}\n"
        f"Exit: ${exit_price:.2f}  |  P&L: `${pnl:+.2f}` ({pnl_pct:+.1f}%)\n"
        f"Reason: {reason}"
    )
    logger.info(
        "Trade closed: id={} pnl={:+.2f} ({:+.1f}%) reason={}",
        trade["id"], pnl, pnl_pct, reason,
    )


# ── Approved-signal watcher ───────────────────────────────────────────────────

async def check_approved_signals(app):
    """
    Poll bot_data for manually approved signals and execute them.
    The Telegram callback handler sets bot_data['approved_signal'].
    """
    sig = app.bot_data.pop("approved_signal", None)
    if sig:
        account = get_account()
        ok, reason = validate_trade(sig, account)
        if ok:
            await _execute_signal(sig)
        else:
            await send_message(f"⚠️ Approved signal now invalid: {reason}")


# ── Entry point ───────────────────────────────────────────────────────────────

async def main():
    logger.remove()
    logger.add(sys.stderr, level="INFO", colorize=True,
               format="<green>{time:HH:mm:ss}</green> | <level>{level:<8}</level> | {message}")
    logger.add("logs/tara.log", rotation="1 day", retention="14 days", level="DEBUG")

    init_db()

    # Default state on first run
    if get_state("trading_mode") is None:
        set_state("trading_mode", "paper")
    if get_state("auto_trade") is None:
        set_state("auto_trade", "false")
    if get_state("scanning_paused") is None:
        set_state("scanning_paused", "false")

    tg_app = create_app()

    scheduler = AsyncIOScheduler(timezone=ET)

    # Scan every 5 minutes
    scheduler.add_job(run_scan, "interval", minutes=5, id="scan")

    # Monitor positions every 2 minutes
    scheduler.add_job(monitor_positions, "interval", minutes=2, id="monitor")

    # Approved-signal check every 10 seconds
    scheduler.add_job(
        lambda: asyncio.create_task(check_approved_signals(tg_app)),
        "interval", seconds=10, id="approved_check",
    )

    # Force-close at 3:45 PM ET on weekdays
    scheduler.add_job(
        force_close_all, "cron",
        day_of_week="mon-fri", hour=15, minute=45,
        id="force_close",
    )

    scheduler.start()
    logger.info("TARA v2 started — paper={} auto={}", settings.alpaca_paper, get_state("auto_trade"))
    await send_message("🤖 *TARA v2 online.* Use /status for current state.")

    async with tg_app:
        await tg_app.initialize()
        await tg_app.start()
        await tg_app.updater.start_polling(drop_pending_updates=True)

        try:
            await asyncio.Event().wait()    # run forever
        finally:
            await tg_app.updater.stop()
            await tg_app.stop()
            await tg_app.shutdown()
            scheduler.shutdown()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Shutting down.")
