import pandas as pd
import numpy as np
from typing import Dict


def _rsi(prices: pd.Series, period: int = 14) -> float:
    delta = prices.diff()
    gain = delta.where(delta > 0, 0.0).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0.0)).rolling(period).mean()
    rs = gain / loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    val = rsi.iloc[-1]
    return float(val) if not pd.isna(val) else 50.0


def _macd(prices: pd.Series) -> Dict:
    ema12 = prices.ewm(span=12, adjust=False).mean()
    ema26 = prices.ewm(span=26, adjust=False).mean()
    line = ema12 - ema26
    signal = line.ewm(span=9, adjust=False).mean()
    hist = line - signal
    bull_cross = bool(
        len(line) > 1
        and line.iloc[-1] > signal.iloc[-1]
        and line.iloc[-2] <= signal.iloc[-2]
    )
    bear_cross = bool(
        len(line) > 1
        and line.iloc[-1] < signal.iloc[-1]
        and line.iloc[-2] >= signal.iloc[-2]
    )
    return {
        "macd": float(line.iloc[-1]),
        "signal": float(signal.iloc[-1]),
        "histogram": float(hist.iloc[-1]),
        "bullish_crossover": bull_cross,
        "bearish_crossover": bear_cross,
    }


def _bollinger(prices: pd.Series, period: int = 20, n_std: float = 2.0) -> Dict:
    sma = prices.rolling(period).mean()
    std = prices.rolling(period).std()
    upper = sma + std * n_std
    lower = sma - std * n_std
    cur = float(prices.iloc[-1])
    band_width = float(upper.iloc[-1] - lower.iloc[-1])
    position = (
        (cur - float(lower.iloc[-1])) / band_width if band_width > 0 else 0.5
    )
    return {
        "upper": float(upper.iloc[-1]),
        "middle": float(sma.iloc[-1]),
        "lower": float(lower.iloc[-1]),
        "bandwidth": round(band_width / float(sma.iloc[-1]), 4) if float(sma.iloc[-1]) != 0 else 0,
        "position": round(position, 3),  # 0=lower band, 1=upper band
    }


def _volume_ratio(volumes: pd.Series, period: int = 20) -> float:
    avg = float(volumes.iloc[:-1].rolling(period).mean().iloc[-1])
    cur = float(volumes.iloc[-1])
    return round(cur / avg, 2) if avg > 0 else 1.0


def _price_change_pct(prices: pd.Series, n: int) -> float:
    if len(prices) < n + 1:
        return 0.0
    return round(float((prices.iloc[-1] - prices.iloc[-(n + 1)]) / prices.iloc[-(n + 1)] * 100), 2)


def _support_resistance(prices: pd.Series, window: int = 20) -> Dict:
    recent = prices.tail(window)
    cur = float(prices.iloc[-1])
    high = float(recent.max())
    low = float(recent.min())
    return {
        "resistance": high,
        "support": low,
        "near_resistance": cur >= high * 0.98,
        "near_support": cur <= low * 1.02,
    }


def compute_all(df: pd.DataFrame) -> Dict:
    """Compute all indicators from a daily OHLCV DataFrame."""
    closes = df["close"]
    volumes = df["volume"]

    rsi_val = _rsi(closes)
    macd_d = _macd(closes)
    bb = _bollinger(closes)
    vol_r = _volume_ratio(volumes)
    sr = _support_resistance(closes)

    return {
        "rsi": round(rsi_val, 2),
        "macd": round(macd_d["macd"], 4),
        "macd_signal": round(macd_d["signal"], 4),
        "macd_histogram": round(macd_d["histogram"], 4),
        "macd_bullish_crossover": macd_d["bullish_crossover"],
        "macd_bearish_crossover": macd_d["bearish_crossover"],
        "bb_upper": round(bb["upper"], 2),
        "bb_middle": round(bb["middle"], 2),
        "bb_lower": round(bb["lower"], 2),
        "bb_bandwidth": bb["bandwidth"],
        "bb_position": bb["position"],
        "volume_ratio": vol_r,
        "price_change_1d_pct": _price_change_pct(closes, 1),
        "price_change_5d_pct": _price_change_pct(closes, 5),
        "resistance": sr["resistance"],
        "support": sr["support"],
        "near_resistance": sr["near_resistance"],
        "near_support": sr["near_support"],
    }
