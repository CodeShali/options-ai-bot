"""
Multi-Timeframe Analysis Module.

Analyzes stocks across multiple timeframes to confirm trends and signals.
"""
from typing import Dict, Any, List, Optional
from loguru import logger
from utils.technical_indicators import TechnicalIndicators


class MultiTimeframeAnalyzer:
    """
    Analyze stocks across multiple timeframes.
    
    Provides trend confirmation and signal validation.
    """
    
    def __init__(self):
        """Initialize multi-timeframe analyzer."""
        self.timeframes = {
            "short": {"period": 20, "name": "Short-term (20 days)"},
            "medium": {"period": 50, "name": "Medium-term (50 days)"},
            "long": {"period": 200, "name": "Long-term (200 days)"}
        }
        logger.info("✅ Multi-timeframe analyzer initialized")
    
    def analyze(self, bars: List[Dict[str, Any]], current_price: float) -> Dict[str, Any]:
        """
        Analyze stock across multiple timeframes.
        
        Args:
            bars: Historical bars (need at least 200)
            current_price: Current price
            
        Returns:
            Multi-timeframe analysis result
        """
        if len(bars) < 200:
            return {
                "available": False,
                "reason": f"Insufficient data (need 200 bars, have {len(bars)})"
            }
        
        closes = [bar['close'] for bar in bars]
        highs = [bar['high'] for bar in bars]
        lows = [bar['low'] for bar in bars]
        volumes = [bar['volume'] for bar in bars]
        
        # Calculate indicators for each timeframe
        sma_20 = TechnicalIndicators.calculate_sma(closes, 20)
        sma_50 = TechnicalIndicators.calculate_sma(closes, 50)
        sma_200 = TechnicalIndicators.calculate_sma(closes, 200)
        
        rsi = TechnicalIndicators.calculate_rsi(closes, 14)
        macd = TechnicalIndicators.calculate_macd(closes)
        atr = TechnicalIndicators.calculate_atr(highs, lows, closes, 14)
        
        # Determine trend for each timeframe
        short_term = self._analyze_timeframe(current_price, sma_20, "short")
        medium_term = self._analyze_timeframe(current_price, sma_50, "medium")
        long_term = self._analyze_timeframe(current_price, sma_200, "long")
        
        # Overall trend alignment
        alignment = self._check_alignment(short_term, medium_term, long_term)
        
        # Momentum indicators
        momentum = {
            "rsi": rsi[-1] if rsi else None,
            "macd": macd['macd'][-1] if macd['macd'] else None,
            "macd_signal": macd['signal'][-1] if macd['signal'] else None,
            "macd_histogram": macd['histogram'][-1] if macd['histogram'] else None
        }
        
        # Volatility
        current_atr = atr[-1] if atr else 0
        volatility_pct = (current_atr / current_price * 100) if current_price > 0 else 0
        
        # Generate recommendation
        recommendation = self._generate_recommendation(
            alignment, momentum, short_term, medium_term, long_term
        )
        
        return {
            "available": True,
            "timeframes": {
                "short": short_term,
                "medium": medium_term,
                "long": long_term
            },
            "alignment": alignment,
            "momentum": momentum,
            "volatility": {
                "atr": current_atr,
                "volatility_pct": volatility_pct
            },
            "recommendation": recommendation,
            "current_price": current_price,
            "sma_values": {
                "sma_20": sma_20[-1] if sma_20 else None,
                "sma_50": sma_50[-1] if sma_50 else None,
                "sma_200": sma_200[-1] if sma_200 else None
            }
        }
    
    def _analyze_timeframe(self, current_price: float, sma: List[float], 
                          timeframe: str) -> Dict[str, Any]:
        """
        Analyze single timeframe.
        
        Args:
            current_price: Current price
            sma: SMA values
            timeframe: Timeframe name
            
        Returns:
            Timeframe analysis
        """
        if not sma or sma[-1] is None:
            return {
                "trend": "UNKNOWN",
                "strength": 0,
                "distance": 0
            }
        
        current_sma = sma[-1]
        distance = ((current_price - current_sma) / current_sma) * 100
        
        # Determine trend
        if distance > 2:
            trend = "STRONG_BULLISH"
            strength = min(100, abs(distance) * 10)
        elif distance > 0:
            trend = "BULLISH"
            strength = abs(distance) * 10
        elif distance < -2:
            trend = "STRONG_BEARISH"
            strength = min(100, abs(distance) * 10)
        elif distance < 0:
            trend = "BEARISH"
            strength = abs(distance) * 10
        else:
            trend = "NEUTRAL"
            strength = 0
        
        return {
            "trend": trend,
            "strength": strength,
            "distance": distance,
            "sma": current_sma
        }
    
    def _check_alignment(self, short: Dict, medium: Dict, long: Dict) -> Dict[str, Any]:
        """
        Check if timeframes are aligned.
        
        Args:
            short: Short-term analysis
            medium: Medium-term analysis
            long: Long-term analysis
            
        Returns:
            Alignment analysis
        """
        trends = [short['trend'], medium['trend'], long['trend']]
        
        # Check for bullish alignment
        bullish_trends = ['BULLISH', 'STRONG_BULLISH']
        bearish_trends = ['BEARISH', 'STRONG_BEARISH']
        
        bullish_count = sum(1 for t in trends if t in bullish_trends)
        bearish_count = sum(1 for t in trends if t in bearish_trends)
        
        if bullish_count == 3:
            alignment = "FULLY_ALIGNED_BULLISH"
            score = 100
        elif bullish_count == 2:
            alignment = "MOSTLY_BULLISH"
            score = 70
        elif bearish_count == 3:
            alignment = "FULLY_ALIGNED_BEARISH"
            score = 100
        elif bearish_count == 2:
            alignment = "MOSTLY_BEARISH"
            score = 70
        else:
            alignment = "MIXED"
            score = 30
        
        return {
            "alignment": alignment,
            "score": score,
            "bullish_count": bullish_count,
            "bearish_count": bearish_count,
            "description": self._get_alignment_description(alignment)
        }
    
    def _get_alignment_description(self, alignment: str) -> str:
        """Get human-readable alignment description."""
        descriptions = {
            "FULLY_ALIGNED_BULLISH": "All timeframes bullish - strong uptrend",
            "MOSTLY_BULLISH": "Majority bullish - uptrend likely",
            "FULLY_ALIGNED_BEARISH": "All timeframes bearish - strong downtrend",
            "MOSTLY_BEARISH": "Majority bearish - downtrend likely",
            "MIXED": "Mixed signals - no clear trend"
        }
        return descriptions.get(alignment, "Unknown")
    
    def _generate_recommendation(self, alignment: Dict, momentum: Dict,
                                 short: Dict, medium: Dict, long: Dict) -> Dict[str, Any]:
        """
        Generate trading recommendation based on multi-timeframe analysis.
        
        Args:
            alignment: Timeframe alignment
            momentum: Momentum indicators
            short: Short-term analysis
            medium: Medium-term analysis
            long: Long-term analysis
            
        Returns:
            Trading recommendation
        """
        score = alignment['score']
        rsi = momentum.get('rsi')
        macd_histogram = momentum.get('macd_histogram')
        
        # Strong bullish alignment
        if alignment['alignment'] == "FULLY_ALIGNED_BULLISH":
            if rsi and rsi < 70:  # Not overbought
                return {
                    "action": "BUY",
                    "confidence": 0.85,
                    "reason": "All timeframes bullish, RSI not overbought",
                    "risk": "LOW"
                }
            else:
                return {
                    "action": "HOLD",
                    "confidence": 0.60,
                    "reason": "Bullish but overbought (RSI > 70)",
                    "risk": "MEDIUM"
                }
        
        # Strong bearish alignment
        elif alignment['alignment'] == "FULLY_ALIGNED_BEARISH":
            return {
                "action": "AVOID",
                "confidence": 0.80,
                "reason": "All timeframes bearish - strong downtrend",
                "risk": "HIGH"
            }
        
        # Mostly bullish
        elif alignment['alignment'] == "MOSTLY_BULLISH":
            if rsi and rsi < 60:
                return {
                    "action": "BUY",
                    "confidence": 0.70,
                    "reason": "Majority bullish, RSI healthy",
                    "risk": "MEDIUM"
                }
            else:
                return {
                    "action": "HOLD",
                    "confidence": 0.50,
                    "reason": "Mostly bullish but RSI elevated",
                    "risk": "MEDIUM"
                }
        
        # Mixed signals
        else:
            return {
                "action": "HOLD",
                "confidence": 0.40,
                "reason": "Mixed timeframe signals - wait for clarity",
                "risk": "HIGH"
            }
    
    def should_boost_signal(self, signal: str, mtf_analysis: Dict[str, Any]) -> tuple[bool, str]:
        """
        Check if multi-timeframe analysis supports the signal.
        
        Args:
            signal: Trading signal (BUY/SELL)
            mtf_analysis: Multi-timeframe analysis result
            
        Returns:
            (should_boost, reason)
        """
        if not mtf_analysis.get('available'):
            return False, "MTF not available"
        
        alignment = mtf_analysis['alignment']['alignment']
        
        # BUY signal
        if signal == "BUY":
            if alignment in ["FULLY_ALIGNED_BULLISH", "MOSTLY_BULLISH"]:
                return True, f"MTF confirms: {alignment}"
            else:
                return False, f"MTF conflicts: {alignment}"
        
        # SELL signal
        elif signal == "SELL":
            if alignment in ["FULLY_ALIGNED_BEARISH", "MOSTLY_BEARISH"]:
                return True, f"MTF confirms: {alignment}"
            else:
                return False, f"MTF conflicts: {alignment}"
        
        return False, "No MTF confirmation"
