"""
Telegram bot — primary mobile interface for TARA.

Commands
────────
/status       overview
/positions    open trades
/performance  P&L stats
/trades       last 10 trades
/auto_on      enable auto-execution
/auto_off     manual approval mode
/paper        paper trading
/live         live trading (requires confirmation)
/pause        pause scanning
/resume       resume scanning
/scan         trigger a scan immediately
/help         command list
"""

import uuid
from typing import Dict, Optional

from loguru import logger
from telegram import (
    BotCommand,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
)
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)

from config.settings import settings
from db.database import (
    get_all_time_pnl,
    get_open_trades,
    get_performance_stats,
    get_state,
    get_trade_history,
    get_weekly_pnl,
    get_weekly_trade_count,
    set_state,
)

# ── Globals ───────────────────────────────────────────────────────────────────

_app: Optional[Application] = None
_pending: Dict[str, Dict] = {}        # signal_id → signal dict
_manual_scan_flag: bool = False


# ── Auth ──────────────────────────────────────────────────────────────────────

def _authed(update: Update) -> bool:
    return str(update.effective_chat.id) == settings.telegram_chat_id


async def _deny(update: Update):
    await update.message.reply_text("Unauthorized.")


# ── Commands ──────────────────────────────────────────────────────────────────

async def cmd_start(update: Update, _ctx: ContextTypes.DEFAULT_TYPE):
    if not _authed(update):
        await _deny(update)
        return
    await _send_status(update)


async def cmd_status(update: Update, _ctx: ContextTypes.DEFAULT_TYPE):
    if not _authed(update):
        await _deny(update)
        return
    await _send_status(update)


async def _send_status(update: Update):
    mode    = get_state("trading_mode") or "paper"
    auto    = get_state("auto_trade") or "false"
    paused  = get_state("scanning_paused") or "false"
    weekly  = get_weekly_trade_count()
    wpnl    = get_weekly_pnl()

    text = (
        f"🤖 *TARA Options Bot*\n\n"
        f"Mode      : `{mode.upper()}`\n"
        f"Auto-trade: `{'ON ✅' if auto == 'true' else 'OFF ⏸'}`\n"
        f"Scanning  : `{'PAUSED ⛔' if paused == 'true' else 'ACTIVE 🟢'}`\n"
        f"This week : `{weekly}/3 trades` | `${wpnl:+.2f} P&L`\n\n"
        f"Use /help for all commands."
    )
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


async def cmd_help(update: Update, _ctx: ContextTypes.DEFAULT_TYPE):
    if not _authed(update):
        await _deny(update)
        return
    text = (
        "*Commands*\n"
        "/status — overview\n"
        "/positions — open trades\n"
        "/performance — P&L stats\n"
        "/trades — recent history\n\n"
        "*Controls*\n"
        "/auto\\_on — auto-execute signals\n"
        "/auto\\_off — approve each trade manually\n"
        "/paper — paper trading mode\n"
        "/live — live trading mode\n"
        "/pause — stop scanning\n"
        "/resume — resume scanning\n"
        "/scan — trigger scan now"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


async def cmd_positions(update: Update, _ctx: ContextTypes.DEFAULT_TYPE):
    if not _authed(update):
        await _deny(update)
        return
    trades = get_open_trades()
    if not trades:
        await update.message.reply_text("No open positions.")
        return
    lines = ["*Open Positions*\n"]
    for t in trades:
        lines.append(
            f"• `{t['symbol']}` {t['option_type'].upper()} ${t['strike']} exp {t['expiry']}\n"
            f"  Entry: `${t['entry_price']:.2f}` × {t['contracts']}ct  |  {t['entry_time'][:16]}"
        )
    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)


async def cmd_performance(update: Update, _ctx: ContextTypes.DEFAULT_TYPE):
    if not _authed(update):
        await _deny(update)
        return
    stats  = get_performance_stats()
    wpnl   = get_weekly_pnl()
    total  = get_all_time_pnl()
    weekly = get_weekly_trade_count()
    wr     = (stats["wins"] / stats["total"] * 100) if stats["total"] > 0 else 0
    rr     = abs(stats["avg_win"] / stats["avg_loss"]) if stats["avg_loss"] != 0 else 0

    text = (
        f"*Performance*\n\n"
        f"This week : `${wpnl:+.2f}` ({weekly}/3 trades)\n"
        f"All-time  : `${total:+.2f}`\n\n"
        f"Trades    : {stats['total']}\n"
        f"Win rate  : {wr:.0f}%\n"
        f"Avg win   : `${stats['avg_win']:.2f}`\n"
        f"Avg loss  : `${stats['avg_loss']:.2f}`\n"
        f"R/R ratio : `{rr:.2f}x`"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


async def cmd_trades(update: Update, _ctx: ContextTypes.DEFAULT_TYPE):
    if not _authed(update):
        await _deny(update)
        return
    trades = get_trade_history(limit=10)
    if not trades:
        await update.message.reply_text("No trade history yet.")
        return
    lines = ["*Last 10 Trades*\n"]
    for t in trades:
        if t["status"] == "open":
            icon, pnl_str = "⏳", "open"
        elif (t.get("pnl") or 0) > 0:
            icon, pnl_str = "✅", f"${t['pnl']:+.2f}"
        else:
            icon, pnl_str = "❌", f"${t['pnl']:+.2f}"
        lines.append(
            f"{icon} `{t['symbol']}` {t['option_type'].upper()} "
            f"${t['strike']} | {pnl_str}"
        )
    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)


async def cmd_auto_on(update: Update, _ctx: ContextTypes.DEFAULT_TYPE):
    if not _authed(update):
        await _deny(update)
        return
    set_state("auto_trade", "true")
    await update.message.reply_text(
        "✅ *Auto-trade ON* — Claude will execute qualifying signals automatically.",
        parse_mode=ParseMode.MARKDOWN,
    )


async def cmd_auto_off(update: Update, _ctx: ContextTypes.DEFAULT_TYPE):
    if not _authed(update):
        await _deny(update)
        return
    set_state("auto_trade", "false")
    await update.message.reply_text(
        "⏸ *Auto-trade OFF* — you'll approve each signal before execution.",
        parse_mode=ParseMode.MARKDOWN,
    )


async def cmd_paper(update: Update, _ctx: ContextTypes.DEFAULT_TYPE):
    if not _authed(update):
        await _deny(update)
        return
    set_state("trading_mode", "paper")
    await update.message.reply_text("📝 Switched to *paper* trading.", parse_mode=ParseMode.MARKDOWN)


async def cmd_live(update: Update, _ctx: ContextTypes.DEFAULT_TYPE):
    if not _authed(update):
        await _deny(update)
        return
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Yes, go LIVE", callback_data="confirm_live"),
        InlineKeyboardButton("❌ Cancel",       callback_data="cancel_live"),
    ]])
    await update.message.reply_text(
        "⚠️ Switch to *LIVE* trading with real money?",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=kb,
    )


async def cmd_pause(update: Update, _ctx: ContextTypes.DEFAULT_TYPE):
    if not _authed(update):
        await _deny(update)
        return
    set_state("scanning_paused", "true")
    await update.message.reply_text("⛔ Scanning *paused*. Use /resume to restart.", parse_mode=ParseMode.MARKDOWN)


async def cmd_resume(update: Update, _ctx: ContextTypes.DEFAULT_TYPE):
    if not _authed(update):
        await _deny(update)
        return
    set_state("scanning_paused", "false")
    await update.message.reply_text("🟢 Scanning *resumed*.", parse_mode=ParseMode.MARKDOWN)


async def cmd_scan(update: Update, _ctx: ContextTypes.DEFAULT_TYPE):
    if not _authed(update):
        await _deny(update)
        return
    global _manual_scan_flag
    _manual_scan_flag = True
    await update.message.reply_text("🔍 Manual scan triggered — results coming shortly…")


# ── Callback handler ──────────────────────────────────────────────────────────

async def _callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    data: str = q.data

    if data.startswith("approve_"):
        sid = data[8:]
        sig = _pending.pop(sid, None)
        if sig:
            await q.edit_message_text(
                f"✅ *Approved* — executing…\n`{sig.get('symbol')} {sig.get('action')} ${sig.get('strike')}`",
                parse_mode=ParseMode.MARKDOWN,
            )
            ctx.bot_data["approved_signal"] = sig
        else:
            await q.edit_message_text("⚠️ Signal expired.")

    elif data.startswith("skip_"):
        sid = data[5:]
        _pending.pop(sid, None)
        await q.edit_message_text("❌ *Skipped.*", parse_mode=ParseMode.MARKDOWN)

    elif data == "confirm_live":
        set_state("trading_mode", "live")
        await q.edit_message_text("🔴 *LIVE* trading mode active. Real money is at stake.", parse_mode=ParseMode.MARKDOWN)

    elif data == "cancel_live":
        await q.edit_message_text("Cancelled — still on paper trading.")


# ── Outbound alerts ───────────────────────────────────────────────────────────

async def send_signal_alert(signal: Dict, signal_id: Optional[str] = None):
    """Push a signal to Telegram with Approve / Skip buttons."""
    if _app is None:
        logger.warning("Telegram app not ready — can't send signal alert")
        return

    sid = signal_id or uuid.uuid4().hex[:8]
    _pending[sid] = signal

    conf = signal.get("confidence", 0)
    stars = "⭐" * max(1, conf // 20)
    confs = "\n".join(f"  ✓ {c}" for c in signal.get("confluences_met", []))
    entry = signal.get("entry_price_estimate", 0)

    text = (
        f"📊 *SIGNAL FOUND*\n\n"
        f"Symbol   : `{signal.get('symbol')}`\n"
        f"Action   : `{signal.get('action')}`\n"
        f"Strike   : `${signal.get('strike')}`  exp `{signal.get('expiry')}`\n"
        f"Entry    : `~${entry:.2f}` per contract\n"
        f"Target   : `${signal.get('profit_target', 0):.2f}` (+{settings.profit_target_pct*100:.0f}%)\n"
        f"Stop     : `${signal.get('stop_loss_price', 0):.2f}` (–{settings.stop_loss_pct*100:.0f}%)\n"
        f"Max risk : `${entry*100:.0f}`\n"
        f"Confidence: {stars} `{conf}%`\n\n"
        f"Confluences met:\n{confs}\n\n"
        f"_{signal.get('reasoning', '')}_"
    )
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ APPROVE", callback_data=f"approve_{sid}"),
        InlineKeyboardButton("❌ SKIP",    callback_data=f"skip_{sid}"),
    ]])
    try:
        await _app.bot.send_message(
            chat_id=settings.telegram_chat_id,
            text=text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=kb,
        )
    except Exception as exc:
        logger.error("send_signal_alert: {}", exc)


async def send_message(text: str):
    """Send a plain Markdown message."""
    if _app is None:
        return
    try:
        await _app.bot.send_message(
            chat_id=settings.telegram_chat_id,
            text=text,
            parse_mode=ParseMode.MARKDOWN,
        )
    except Exception as exc:
        logger.error("send_message: {}", exc)


# ── Manual-scan flag ──────────────────────────────────────────────────────────

def consume_manual_scan() -> bool:
    """Returns True (and resets flag) if a manual scan was requested."""
    global _manual_scan_flag
    if _manual_scan_flag:
        _manual_scan_flag = False
        return True
    return False


# ── App factory ───────────────────────────────────────────────────────────────

def create_app() -> Application:
    global _app
    _app = Application.builder().token(settings.telegram_bot_token).build()

    handlers = [
        ("start",       cmd_start),
        ("status",      cmd_status),
        ("help",        cmd_help),
        ("positions",   cmd_positions),
        ("performance", cmd_performance),
        ("trades",      cmd_trades),
        ("auto_on",     cmd_auto_on),
        ("auto_off",    cmd_auto_off),
        ("paper",       cmd_paper),
        ("live",        cmd_live),
        ("pause",       cmd_pause),
        ("resume",      cmd_resume),
        ("scan",        cmd_scan),
    ]
    for name, fn in handlers:
        _app.add_handler(CommandHandler(name, fn))

    _app.add_handler(CallbackQueryHandler(_callback))
    return _app
