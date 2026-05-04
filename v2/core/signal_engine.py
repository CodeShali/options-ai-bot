"""
Signal engine powered by Claude Opus 4.7.

Design:
- System prompt is marked cache_control=ephemeral so it is cached after the
  first request (saves ~90% of input-token cost on repeated scans).
- tool_choice forces the emit_signal tool so the response is always structured.
- Adaptive thinking lets Claude reason through multi-factor setups naturally.
- No temperature / top_p / top_k  (removed on Opus 4.7).
"""

from typing import Optional, Dict

import anthropic
from anthropic import Anthropic
from loguru import logger

from config.settings import settings

_client: Optional[Anthropic] = None


def _get_client() -> Anthropic:
    global _client
    if _client is None:
        _client = Anthropic(api_key=settings.anthropic_api_key)
    return _client


# ── System prompt (static — gets cached after first request) ──────────────────

_SYSTEM = """\
You are TARA, a disciplined options trading signal analyzer. You are precise, \
selective, and protect capital above everything else.

═══════════════════════════════════════════
TRADING PROFILE  (follow exactly)
═══════════════════════════════════════════
• Instruments : Options ONLY — BUY_CALL or BUY_PUT. No stock trades.
• Symbols     : SPY, QQQ, AAPL, NVDA, TSLA, MSFT — nothing else.
• Frequency   : At most 3 trades per week. Be highly selective.
• Hold time   : Intraday only — enter and exit the same day. NEVER overnight.
• Account     : $2,000 total. Max risk per trade: $150 (1 contract).
• Weekly goal : $200–$350 total (realistic). Do NOT gamble for more.

═══════════════════════════════════════════
STRIKE / EXPIRY SELECTION
═══════════════════════════════════════════
• Strike  : Slightly OTM — 1 to 2 strikes out from current price.
• DTE     : 5–14 days. Never 0-DTE. Never beyond 14 DTE for intraday plays.
• Premium : $0.50–$2.50 per contract (keeps max risk at $50–$250).

═══════════════════════════════════════════
A+ SETUP — NEED 4 OR MORE TO TRADE
═══════════════════════════════════════════
1. MOMENTUM      : Stock moved ≥1% today with above-average volume.
2. TECHNICALS    : RSI + MACD + Bollinger all agree on direction.
3. VOLUME        : Volume ≥1.5× the 20-day average (unusual conviction).
4. OPTIONS FLOW  : Open interest and volume on the target strike are healthy.
5. MARKET ALIGN  : SPY/QQQ trend supports the direction.
6. CATALYST      : Clear news, sector move, or earnings reaction driving move.

═══════════════════════════════════════════
MANDATORY SKIP CONDITIONS  (skip if ANY applies)
═══════════════════════════════════════════
• RSI >80 for calls  /  RSI <20 for puts     (extreme levels)
• Volume <1.2× average                        (no conviction)
• MACD and RSI disagree on direction          (conflicting signals)
• Price is near major resistance (for calls) / support (for puts)
• Fewer than 4 A+ confluences met             (not an A+ setup)
• Choppy / sideways market, no clear trend    (no edge)
• Only 1–2 confluences — skip without regret. Patience is an edge.

═══════════════════════════════════════════
EXIT RULES  (embed in every recommendation)
═══════════════════════════════════════════
• Profit target : Exit at +60–80% gain on premium paid.
• Stop loss     : Exit at –35% loss on premium paid — no exceptions.
• Time stop     : Must be closed by 3:45 PM ET — no overnight holds.
• Momentum flip : If the underlying reverses hard, exit immediately.

═══════════════════════════════════════════
POSITION SIZING
═══════════════════════════════════════════
• Always 1 contract for this $2,000 account.
• Max cost = min($150, 7.5% of $2,000).
• If the cheapest suitable contract costs >$1.50, pass on the trade.

═══════════════════════════════════════════
REASONING GUIDANCE
═══════════════════════════════════════════
Think carefully through every factor. A marginal setup is worth zero — there \
will be another trade tomorrow. Your job is to protect capital first, grow it \
second. Use the emit_signal tool to output your final decision in structured \
form. Keep the reasoning field concise (2–3 sentences max).
"""

# ── Tool definition ───────────────────────────────────────────────────────────

_SIGNAL_TOOL = {
    "name": "emit_signal",
    "description": (
        "Output a trading signal or a no-trade decision. "
        "Always call this tool — never reply in plain text."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "trade": {
                "type": "boolean",
                "description": "True = take the trade. False = skip.",
            },
            "skip_reason": {
                "type": "string",
                "description": "Why skipping (required when trade=false).",
            },
            "action": {
                "type": "string",
                "enum": ["BUY_CALL", "BUY_PUT"],
                "description": "Direction (required when trade=true).",
            },
            "symbol": {
                "type": "string",
                "description": "Underlying ticker (required when trade=true).",
            },
            "strike": {
                "type": "number",
                "description": "Option strike price.",
            },
            "expiry": {
                "type": "string",
                "description": "Expiry date YYYY-MM-DD.",
            },
            "contracts": {
                "type": "integer",
                "description": "Number of contracts — always 1 for this account.",
            },
            "entry_price_estimate": {
                "type": "number",
                "description": "Estimated premium per contract at entry.",
            },
            "profit_target": {
                "type": "number",
                "description": "Target exit premium (+60–80% of entry).",
            },
            "stop_loss_price": {
                "type": "number",
                "description": "Stop loss exit premium (–35% of entry).",
            },
            "confidence": {
                "type": "integer",
                "minimum": 0,
                "maximum": 100,
                "description": "Confidence score 0–100.",
            },
            "confluences_met": {
                "type": "array",
                "items": {"type": "string"},
                "description": "A+ conditions that are met for this setup.",
            },
            "reasoning": {
                "type": "string",
                "description": "2–3 sentence plain-English rationale.",
            },
            "risk_level": {
                "type": "string",
                "enum": ["LOW", "MEDIUM", "HIGH"],
                "description": "Overall risk assessment.",
            },
        },
        "required": ["trade", "confidence", "reasoning"],
    },
}


# ── Public API ────────────────────────────────────────────────────────────────

def analyze_opportunity(
    symbol: str,
    market_data: Dict,
    weekly_trades_used: int,
) -> Optional[Dict]:
    """
    Ask Claude to analyze one trading opportunity.

    Returns the emit_signal tool input dict, or None on API failure.
    The caller decides whether to trade based on signal["trade"].
    """
    prompt = _build_prompt(symbol, market_data, weekly_trades_used)

    try:
        response = _get_client().messages.create(
            model="claude-opus-4-7",
            max_tokens=2048,
            thinking={"type": "adaptive"},
            output_config={"effort": "high"},
            # Cache the large static system prompt — saves cost on repeated scans
            system=[
                {
                    "type": "text",
                    "text": _SYSTEM,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            tools=[_SIGNAL_TOOL],
            tool_choice={"type": "tool", "name": "emit_signal"},
            messages=[{"role": "user", "content": prompt}],
        )

        usage = response.usage
        cached = getattr(usage, "cache_read_input_tokens", 0)
        logger.debug(
            "Claude {} | input={} cached={} output={}",
            symbol,
            usage.input_tokens,
            cached,
            usage.output_tokens,
        )

        for block in response.content:
            if block.type == "tool_use" and block.name == "emit_signal":
                return block.input

        logger.warning("No emit_signal block in Claude response for {}", symbol)
        return None

    except anthropic.RateLimitError:
        logger.warning("Claude rate-limited — skipping {}", symbol)
        return None
    except anthropic.APIError as exc:
        logger.error("Claude API error for {}: {}", symbol, exc)
        return None


# ── Prompt builder ────────────────────────────────────────────────────────────

def _build_prompt(symbol: str, data: Dict, weekly_trades_used: int) -> str:
    snap = data.get("snapshot", {})
    ind = data.get("indicators", {})
    chain: list = data.get("options_chain", [])
    news: list = data.get("news", [])

    # Summarise nearby option strikes
    calls = [c for c in chain if c.get("type") == "call"][:4]
    puts = [c for c in chain if c.get("type") == "put"][:4]
    chain_lines = []
    if calls:
        chain_lines.append("Nearby CALLS: " + " | ".join(
            f"${c['strike']} {c['expiry']} ({c['dte']}DTE)"
            for c in calls
        ))
    if puts:
        chain_lines.append("Nearby PUTS: " + " | ".join(
            f"${c['strike']} {c['expiry']} ({c['dte']}DTE)"
            for c in puts
        ))
    chain_text = "\n".join(chain_lines) if chain_lines else "Options chain unavailable."

    news_text = ""
    if news:
        news_text = "Recent news:\n" + "\n".join(f"  • {n}" for n in news[:3])

    price = snap.get("price", "N/A")
    change = snap.get("change_pct", 0) or 0

    return f"""\
Analyse this potential trade and call emit_signal with your decision.

━━━ MARKET DATA ━━━
Symbol        : {symbol}
Current price : ${price}
Day change    : {change:+.2f}%
Volume ratio  : {ind.get('volume_ratio', 1):.2f}× average

━━━ TECHNICALS ━━━
RSI (14)      : {ind.get('rsi', 50):.1f}
MACD line     : {ind.get('macd', 0):.4f}
MACD signal   : {ind.get('macd_signal', 0):.4f}
MACD hist     : {ind.get('macd_histogram', 0):.4f}
Bullish cross : {ind.get('macd_bullish_crossover', False)}
Bearish cross : {ind.get('macd_bearish_crossover', False)}
BB position   : {ind.get('bb_position', 0.5):.2f}  (0=lower, 1=upper band)
BB bandwidth  : {ind.get('bb_bandwidth', 0):.4f}
1-day change  : {ind.get('price_change_1d_pct', 0):+.2f}%
5-day change  : {ind.get('price_change_5d_pct', 0):+.2f}%
Near resist.  : {ind.get('near_resistance', False)}
Near support  : {ind.get('near_support', False)}

━━━ OPTIONS ━━━
{chain_text}

{news_text}

━━━ CONSTRAINTS ━━━
Trades used this week : {weekly_trades_used} / 3
Max risk this trade   : $150 (1 contract)
Account size          : $2,000

Apply A+ setup criteria strictly. If fewer than 4 confluences are met, \
set trade=false. Call emit_signal now."""
