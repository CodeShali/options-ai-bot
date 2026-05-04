from typing import Dict, Tuple

from loguru import logger

from config.settings import settings
from db.database import get_state, get_weekly_trade_count, get_open_trades


def validate_trade(signal: Dict, account: Dict) -> Tuple[bool, str]:
    """
    Run every pre-trade risk check.
    Returns (approved, reason_string).
    """
    if get_state("scanning_paused") == "true":
        return False, "Scanning is paused"

    weekly = get_weekly_trade_count()
    if weekly >= settings.max_trades_per_week:
        return False, f"Weekly limit reached ({weekly}/{settings.max_trades_per_week})"

    open_trades = get_open_trades()
    if open_trades:
        return False, f"{len(open_trades)} position(s) already open — one at a time"

    confidence = signal.get("confidence", 0)
    if confidence < 65:
        return False, f"Confidence too low: {confidence}% (min 65%)"

    if signal.get("risk_level") == "HIGH":
        return False, "Signal flagged HIGH risk — skip"

    confluences = signal.get("confluences_met", [])
    if len(confluences) < 3:
        return False, f"Only {len(confluences)} confluences (need ≥3)"

    entry = signal.get("entry_price_estimate", 0)
    contracts = signal.get("contracts", 1)
    cost = entry * contracts * 100
    if cost > settings.max_risk_per_trade:
        return False, f"Cost ${cost:.0f} exceeds max risk ${settings.max_risk_per_trade:.0f}"

    buying_power = account.get("buying_power", 0)
    if cost > buying_power * 0.15:
        return False, "Insufficient buying power"

    return True, "Approved"


def max_contracts(entry_price: float, account_equity: float) -> int:
    """How many contracts can we buy within risk limits."""
    budget = min(settings.max_risk_per_trade, account_equity * 0.075)
    n = int(budget / (entry_price * 100))
    return max(1, min(n, 2))
