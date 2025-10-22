"""
Discord NLP Core
Lightweight intent detection and trading-related parsing for natural language chat.
"""
from typing import List, Dict
import re

TRADING_KEYWORDS = {
    'account','balance','equity','buying power','cash','portfolio','pnl','p&l','return','performance',
    'position','positions','trade','trades','order','orders','entry','exit','close','open','sell','buy',
    'risk','stop','target','limit','market','monitor','monitoring','scan','scanning','analyze','analysis',
    'strategy','strategies','signal','signals','alert','alerts','update','updates','report','reports',
    'greeks','delta','theta','gamma','vega','iv','sentiment','news','volume','momentum','breakout','price',
    'chart','technical','indicator','spy','qqq','iwm','vix','tara','bot','system','process','algorithm',
    'profit','loss','should','buy','sell','what','how','why','when','where','help','status','show','get',
    'my','me','i','stock','stocks','option','options','crypto','bitcoin','eth','market','markets'
}

SYMBOL_RE = re.compile(r"\b[A-Z]{1,5}\b")
DOLLAR_RE = re.compile(r"\$\d+(?:\.\d+)?")


def is_trading_related(text: str) -> bool:
    t = text.lower()
    if any(k in t for k in TRADING_KEYWORDS):
        return True
    if SYMBOL_RE.search(text):
        return True
    if DOLLAR_RE.search(text):
        return True
    return False


def extract_symbols(text: str) -> List[str]:
    syms = [m.group(0) for m in SYMBOL_RE.finditer(text)]
    # Filter common false positives
    bad = {"AND","THE","FOR","ARE","WITH","WHAT","WHEN","THIS","YOUR","HELP","OPEN","CLOSE"}
    return [s for s in syms if s.upper() not in bad]


def classify_intent(text: str) -> str:
    t = text.lower()
    # Order matters (more specific first)
    if any(k in t for k in ["why did you exit", "why exit", "why did we sell", "exited", "closed my"]):
        return "why_exit"
    if any(k in t for k in ["what are you monitoring", "what exactly do you monitor", "how do you monitor", "monitoring now"]):
        return "monitoring_explain"
    if any(k in t for k in ["what's my p&l", "pnl", "profit", "loss", "account status", "how's my account", "equity", "buying power"]):
        return "account_status"
    if any(k in t for k in ["show my positions", "my positions", "position status", "how is my", "what's happening with"]):
        return "position_status"
    if any(k in t for k in ["biggest risk", "risk right now", "portfolio risk", "concentration", "exposure"]):
        return "risk_overview"
    if any(k in t for k in ["today performance", "performance today", "day summary", "daily summary"]):
        return "performance_summary"
    if any(k in t for k in ["strategy", "how do you decide", "how do you buy", "trade plan", "entry rules"]):
        return "strategy_explain"
    if any(k in t for k in ["alerts", "notifications", "alert status", "smart alerts"]):
        return "alerts_status"
    return "general_trading"
