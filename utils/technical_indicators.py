"""
Technical Indicators for Quantitative Trading Strategies.

Implements all major technical indicators:
- RSI, MACD, Bollinger Bands
- Moving Averages (SMA, EMA)
- ADX, ATR
- Volume indicators
"""
from typing import List, Dict, Any, Tuple
import numpy as np
from loguru import logger


class TechnicalIndicators:
    """Calculate technical indicators for trading strategies."""
    
    @staticmethod
    def calculate_sma(prices: List[float], period: int) -> List[float]:
        """
        Calculate Simple Moving Average.
        
        Args:
            prices: List of prices
            period: SMA period
            
        Returns:
            List of SMA values
        """
        if len(prices) < period:
            return []
        
        sma = []
        for i in range(len(prices)):
            if i < period - 1:
                sma.append(None)
            else:
                sma.append(sum(prices[i-period+1:i+1]) / period)
        
        return sma
    
    @staticmethod
    def calculate_ema(prices: List[float], period: int) -> List[float]:
        """
        Calculate Exponential Moving Average.
        
        Args:
            prices: List of prices
            period: EMA period
            
        Returns:
            List of EMA values
        """
        if len(prices) < period:
            return []
        
        multiplier = 2 / (period + 1)
        ema = [sum(prices[:period]) / period]  # Start with SMA
        
        for price in prices[period:]:
            ema.append((price - ema[-1]) * multiplier + ema[-1])
        
        # Pad with None for initial values
        return [None] * (period - 1) + ema
    
    @staticmethod
    def calculate_rsi(prices: List[float], period: int = 14) -> List[float]:
        """
        Calculate Relative Strength Index.
        
        Args:
            prices: List of prices
            period: RSI period (default 14)
            
        Returns:
            List of RSI values (0-100)
        """
        if len(prices) < period + 1:
            return []
        
        # Calculate price changes
        deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
        
        # Separate gains and losses
        gains = [d if d > 0 else 0 for d in deltas]
        losses = [-d if d < 0 else 0 for d in deltas]
        
        # Calculate initial average gain/loss
        avg_gain = sum(gains[:period]) / period
        avg_loss = sum(losses[:period]) / period
        
        rsi = [None] * period
        
        # Calculate RSI
        for i in range(period, len(gains)):
            if avg_loss == 0:
                rsi.append(100)
            else:
                rs = avg_gain / avg_loss
                rsi.append(100 - (100 / (1 + rs)))
            
            # Update averages (Wilder's smoothing)
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        
        return rsi
    
    @staticmethod
    def calculate_macd(prices: List[float], fast: int = 12, slow: int = 26, signal: int = 9) -> Dict[str, List[float]]:
        """
        Calculate MACD (Moving Average Convergence Divergence).
        
        Args:
            prices: List of prices
            fast: Fast EMA period (default 12)
            slow: Slow EMA period (default 26)
            signal: Signal line period (default 9)
            
        Returns:
            Dictionary with macd, signal, and histogram
        """
        if len(prices) < slow:
            return {"macd": [], "signal": [], "histogram": []}
        
        # Calculate EMAs
        ema_fast = TechnicalIndicators.calculate_ema(prices, fast)
        ema_slow = TechnicalIndicators.calculate_ema(prices, slow)
        
        # Calculate MACD line
        macd_line = []
        for i in range(len(prices)):
            if ema_fast[i] is not None and ema_slow[i] is not None:
                macd_line.append(ema_fast[i] - ema_slow[i])
            else:
                macd_line.append(None)
        
        # Calculate signal line (EMA of MACD)
        macd_values = [m for m in macd_line if m is not None]
        if len(macd_values) < signal:
            return {"macd": macd_line, "signal": [None] * len(macd_line), "histogram": [None] * len(macd_line)}
        
        signal_line = TechnicalIndicators.calculate_ema(macd_values, signal)
        
        # Pad signal line
        signal_padded = [None] * (len(macd_line) - len(signal_line)) + signal_line
        
        # Calculate histogram
        histogram = []
        for i in range(len(macd_line)):
            if macd_line[i] is not None and signal_padded[i] is not None:
                histogram.append(macd_line[i] - signal_padded[i])
            else:
                histogram.append(None)
        
        return {
            "macd": macd_line,
            "signal": signal_padded,
            "histogram": histogram
        }
    
    @staticmethod
    def calculate_bollinger_bands(prices: List[float], period: int = 20, std_dev: float = 2.0) -> Dict[str, List[float]]:
        """
        Calculate Bollinger Bands.
        
        Args:
            prices: List of prices
            period: Period for SMA (default 20)
            std_dev: Number of standard deviations (default 2)
            
        Returns:
            Dictionary with upper, middle, and lower bands
        """
        if len(prices) < period:
            return {"upper": [], "middle": [], "lower": []}
        
        sma = TechnicalIndicators.calculate_sma(prices, period)
        
        upper = []
        lower = []
        
        for i in range(len(prices)):
            if i < period - 1:
                upper.append(None)
                lower.append(None)
            else:
                std = np.std(prices[i-period+1:i+1])
                upper.append(sma[i] + (std_dev * std))
                lower.append(sma[i] - (std_dev * std))
        
        return {
            "upper": upper,
            "middle": sma,
            "lower": lower
        }
    
    @staticmethod
    def calculate_atr(highs: List[float], lows: List[float], closes: List[float], period: int = 14) -> List[float]:
        """
        Calculate Average True Range.
        
        Args:
            highs: List of high prices
            lows: List of low prices
            closes: List of close prices
            period: ATR period (default 14)
            
        Returns:
            List of ATR values
        """
        if len(highs) < period + 1:
            return []
        
        # Calculate True Range
        tr = [highs[0] - lows[0]]  # First TR
        
        for i in range(1, len(highs)):
            high_low = highs[i] - lows[i]
            high_close = abs(highs[i] - closes[i-1])
            low_close = abs(lows[i] - closes[i-1])
            tr.append(max(high_low, high_close, low_close))
        
        # Calculate ATR (Wilder's smoothing)
        atr = [None] * period
        atr.append(sum(tr[:period]) / period)
        
        for i in range(period, len(tr)):
            atr.append((atr[-1] * (period - 1) + tr[i]) / period)
        
        return atr
    
    @staticmethod
    def calculate_adx(highs: List[float], lows: List[float], closes: List[float], period: int = 14) -> Dict[str, List[float]]:
        """
        Calculate ADX (Average Directional Index).
        
        Args:
            highs: List of high prices
            lows: List of low prices
            closes: List of close prices
            period: ADX period (default 14)
            
        Returns:
            Dictionary with adx, plus_di, and minus_di
        """
        if len(highs) < period + 1:
            return {"adx": [], "plus_di": [], "minus_di": []}
        
        # Calculate +DM and -DM
        plus_dm = []
        minus_dm = []
        
        for i in range(1, len(highs)):
            high_diff = highs[i] - highs[i-1]
            low_diff = lows[i-1] - lows[i]
            
            if high_diff > low_diff and high_diff > 0:
                plus_dm.append(high_diff)
            else:
                plus_dm.append(0)
            
            if low_diff > high_diff and low_diff > 0:
                minus_dm.append(low_diff)
            else:
                minus_dm.append(0)
        
        # Calculate ATR
        atr = TechnicalIndicators.calculate_atr(highs, lows, closes, period)
        
        # Calculate +DI and -DI
        plus_di = [None] * (period + 1)
        minus_di = [None] * (period + 1)
        
        # Smooth DM
        smooth_plus_dm = sum(plus_dm[:period])
        smooth_minus_dm = sum(minus_dm[:period])
        
        for i in range(period, len(plus_dm)):
            smooth_plus_dm = smooth_plus_dm - (smooth_plus_dm / period) + plus_dm[i]
            smooth_minus_dm = smooth_minus_dm - (smooth_minus_dm / period) + minus_dm[i]
            
            if atr[i+1] is not None and atr[i+1] > 0:
                plus_di.append((smooth_plus_dm / atr[i+1]) * 100)
                minus_di.append((smooth_minus_dm / atr[i+1]) * 100)
            else:
                plus_di.append(None)
                minus_di.append(None)
        
        # Calculate DX and ADX
        dx = []
        for i in range(len(plus_di)):
            if plus_di[i] is not None and minus_di[i] is not None:
                di_sum = plus_di[i] + minus_di[i]
                if di_sum > 0:
                    dx.append(abs(plus_di[i] - minus_di[i]) / di_sum * 100)
                else:
                    dx.append(0)
            else:
                dx.append(None)
        
        # Calculate ADX (smoothed DX)
        adx = [None] * (period * 2)
        dx_values = [d for d in dx if d is not None]
        
        if len(dx_values) >= period:
            adx.append(sum(dx_values[:period]) / period)
            
            for i in range(period, len(dx_values)):
                adx.append((adx[-1] * (period - 1) + dx_values[i]) / period)
        
        return {
            "adx": adx,
            "plus_di": plus_di,
            "minus_di": minus_di
        }
    
    @staticmethod
    def calculate_volume_sma(volumes: List[int], period: int = 20) -> List[float]:
        """Calculate volume SMA."""
        return TechnicalIndicators.calculate_sma([float(v) for v in volumes], period)
    
    @staticmethod
    def is_golden_cross(sma_50: List[float], sma_200: List[float], index: int) -> bool:
        """
        Check if golden cross occurred (50 SMA crosses above 200 SMA).
        
        Args:
            sma_50: 50-day SMA values
            sma_200: 200-day SMA values
            index: Current index
            
        Returns:
            True if golden cross occurred
        """
        if index < 1 or len(sma_50) <= index or len(sma_200) <= index:
            return False
        
        if sma_50[index] is None or sma_200[index] is None:
            return False
        if sma_50[index-1] is None or sma_200[index-1] is None:
            return False
        
        # Cross from below to above
        return sma_50[index-1] <= sma_200[index-1] and sma_50[index] > sma_200[index]
    
    @staticmethod
    def is_death_cross(sma_50: List[float], sma_200: List[float], index: int) -> bool:
        """
        Check if death cross occurred (50 SMA crosses below 200 SMA).
        
        Args:
            sma_50: 50-day SMA values
            sma_200: 200-day SMA values
            index: Current index
            
        Returns:
            True if death cross occurred
        """
        if index < 1 or len(sma_50) <= index or len(sma_200) <= index:
            return False
        
        if sma_50[index] is None or sma_200[index] is None:
            return False
        if sma_50[index-1] is None or sma_200[index-1] is None:
            return False
        
        # Cross from above to below
        return sma_50[index-1] >= sma_200[index-1] and sma_50[index] < sma_200[index]
