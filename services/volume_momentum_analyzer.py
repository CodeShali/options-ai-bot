"""
Volume & Momentum Analyzer - Track volume spikes, momentum shifts, and breakout patterns.
"""
import asyncio
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from loguru import logger
import statistics
import math

from services import get_alpaca_service, get_database_service
from config import settings


class VolumeMomentumAnalyzer:
    """Analyze volume patterns and momentum for better exit timing."""
    
    def __init__(self):
        """Initialize volume momentum analyzer."""
        self.alpaca = get_alpaca_service()
        self.db = get_database_service()
        
        # Analysis parameters
        self.lookback_periods = {
            "short": 5,    # 5 minutes for short-term momentum
            "medium": 15,  # 15 minutes for medium-term
            "long": 60     # 1 hour for long-term trend
        }
        
        # Volume thresholds
        self.volume_thresholds = {
            "spike_multiplier": 2.5,      # 2.5x average volume = spike
            "massive_spike": 5.0,         # 5x average = massive spike
            "low_volume": 0.5,            # 0.5x average = low volume
            "breakout_volume": 1.8        # 1.8x average for breakout confirmation
        }
        
        # Momentum thresholds
        self.momentum_thresholds = {
            "acceleration": 1.5,          # 1.5x momentum = acceleration
            "deceleration": 0.6,          # 0.6x momentum = deceleration
            "reversal": -0.5,             # Negative momentum = reversal
            "strong_momentum": 2.0        # 2x momentum = very strong
        }
        
        # Store recent analysis for trend detection
        self.analysis_history = {}  # {symbol: [analysis_results]}
    
    async def analyze_all_positions(self) -> Dict[str, Any]:
        """Analyze volume and momentum for all positions."""
        try:
            logger.info("📊 Analyzing volume & momentum for positions...")
            
            # Get current positions
            positions = await self.alpaca.get_positions()
            
            if not positions:
                return {
                    "positions_analyzed": 0,
                    "alerts": [],
                    "timestamp": datetime.now().isoformat()
                }
            
            alerts = []
            analysis_summary = []
            
            for position in positions:
                try:
                    symbol = position['symbol']
                    
                    # Analyze volume and momentum
                    analysis = await self.analyze_symbol(symbol)
                    
                    if analysis["success"]:
                        # Generate alerts based on analysis
                        symbol_alerts = self._generate_alerts(symbol, analysis, position)
                        alerts.extend(symbol_alerts)
                        
                        # Store for summary
                        analysis_summary.append({
                            "symbol": symbol,
                            "analysis": analysis,
                            "alerts_count": len(symbol_alerts)
                        })
                        
                        # Store in history
                        self._store_analysis_history(symbol, analysis)
                    
                except Exception as e:
                    logger.error(f"Error analyzing {position.get('symbol', 'unknown')}: {e}")
                    continue
            
            logger.info(f"📊 Volume/momentum analysis complete: {len(positions)} positions, {len(alerts)} alerts")
            
            return {
                "positions_analyzed": len(positions),
                "alerts": alerts,
                "analysis_summary": analysis_summary,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error in volume/momentum analysis: {e}")
            return {
                "error": str(e),
                "positions_analyzed": 0,
                "alerts": []
            }
    
    async def analyze_symbol(self, symbol: str) -> Dict[str, Any]:
        """Analyze volume and momentum for a specific symbol."""
        try:
            # Get recent bars (1-minute bars for detailed analysis)
            bars = await self.alpaca.get_bars(
                symbol=symbol,
                timeframe="1Min",
                limit=120,  # 2 hours of data
                asof=datetime.now()
            )
            
            if not bars or len(bars) < 20:
                return {"success": False, "error": "Insufficient data"}
            
            # Volume analysis
            volume_analysis = self._analyze_volume(bars)
            
            # Momentum analysis
            momentum_analysis = self._analyze_momentum(bars)
            
            # Pattern detection
            patterns = self._detect_patterns(bars)
            
            # Price action analysis
            price_action = self._analyze_price_action(bars)
            
            # Combine all analyses
            analysis = {
                "success": True,
                "symbol": symbol,
                "timestamp": datetime.now().isoformat(),
                "current_price": bars[-1]['close'],
                "volume": volume_analysis,
                "momentum": momentum_analysis,
                "patterns": patterns,
                "price_action": price_action,
                "overall_signal": self._calculate_overall_signal(
                    volume_analysis, momentum_analysis, patterns, price_action
                )
            }
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing {symbol}: {e}")
            return {"success": False, "error": str(e)}
    
    def _analyze_volume(self, bars: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze volume patterns."""
        try:
            volumes = [bar['volume'] for bar in bars]
            current_volume = volumes[-1]
            
            # Calculate average volumes for different periods
            avg_volume_20 = statistics.mean(volumes[-20:]) if len(volumes) >= 20 else current_volume
            avg_volume_60 = statistics.mean(volumes[-60:]) if len(volumes) >= 60 else avg_volume_20
            
            # Volume ratios
            volume_ratio_20 = current_volume / avg_volume_20 if avg_volume_20 > 0 else 1
            volume_ratio_60 = current_volume / avg_volume_60 if avg_volume_60 > 0 else 1
            
            # Volume trend (last 5 bars vs previous 5 bars)
            recent_avg = statistics.mean(volumes[-5:]) if len(volumes) >= 10 else current_volume
            previous_avg = statistics.mean(volumes[-10:-5]) if len(volumes) >= 10 else recent_avg
            volume_trend = (recent_avg / previous_avg - 1) * 100 if previous_avg > 0 else 0
            
            # Classify volume
            if volume_ratio_20 >= self.volume_thresholds["massive_spike"]:
                volume_signal = "MASSIVE_SPIKE"
            elif volume_ratio_20 >= self.volume_thresholds["spike_multiplier"]:
                volume_signal = "SPIKE"
            elif volume_ratio_20 <= self.volume_thresholds["low_volume"]:
                volume_signal = "LOW"
            else:
                volume_signal = "NORMAL"
            
            return {
                "current_volume": current_volume,
                "avg_volume_20": avg_volume_20,
                "avg_volume_60": avg_volume_60,
                "volume_ratio_20": volume_ratio_20,
                "volume_ratio_60": volume_ratio_60,
                "volume_trend_pct": volume_trend,
                "volume_signal": volume_signal,
                "is_above_average": volume_ratio_20 > 1.0
            }
            
        except Exception as e:
            logger.error(f"Error analyzing volume: {e}")
            return {}
    
    def _analyze_momentum(self, bars: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze price momentum."""
        try:
            prices = [bar['close'] for bar in bars]
            
            if len(prices) < 15:
                return {}
            
            # Calculate momentum for different periods
            momentum_5min = self._calculate_momentum(prices[-5:])
            momentum_15min = self._calculate_momentum(prices[-15:])
            momentum_60min = self._calculate_momentum(prices[-60:]) if len(prices) >= 60 else momentum_15min
            
            # Momentum acceleration/deceleration
            momentum_acceleration = momentum_5min / momentum_15min if momentum_15min != 0 else 1
            
            # Price velocity (rate of change)
            velocity_5min = (prices[-1] - prices[-5]) / prices[-5] * 100 if len(prices) >= 5 else 0
            velocity_15min = (prices[-1] - prices[-15]) / prices[-15] * 100 if len(prices) >= 15 else 0
            
            # Momentum classification
            if momentum_acceleration >= self.momentum_thresholds["strong_momentum"]:
                momentum_signal = "STRONG_ACCELERATION"
            elif momentum_acceleration >= self.momentum_thresholds["acceleration"]:
                momentum_signal = "ACCELERATION"
            elif momentum_acceleration <= self.momentum_thresholds["deceleration"]:
                momentum_signal = "DECELERATION"
            elif momentum_5min < 0 and momentum_15min > 0:
                momentum_signal = "REVERSAL"
            else:
                momentum_signal = "STABLE"
            
            return {
                "momentum_5min": momentum_5min,
                "momentum_15min": momentum_15min,
                "momentum_60min": momentum_60min,
                "momentum_acceleration": momentum_acceleration,
                "velocity_5min": velocity_5min,
                "velocity_15min": velocity_15min,
                "momentum_signal": momentum_signal,
                "is_accelerating": momentum_acceleration > 1.2
            }
            
        except Exception as e:
            logger.error(f"Error analyzing momentum: {e}")
            return {}
    
    def _calculate_momentum(self, prices: List[float]) -> float:
        """Calculate momentum score for a price series."""
        if len(prices) < 2:
            return 0
        
        # Simple momentum: (current - start) / start
        return (prices[-1] - prices[0]) / prices[0] if prices[0] != 0 else 0
    
    def _detect_patterns(self, bars: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Detect chart patterns and breakouts."""
        try:
            if len(bars) < 20:
                return {}
            
            highs = [bar['high'] for bar in bars]
            lows = [bar['low'] for bar in bars]
            closes = [bar['close'] for bar in bars]
            volumes = [bar['volume'] for bar in bars]
            
            patterns = []
            
            # Breakout detection
            recent_high = max(highs[-5:])
            resistance_level = max(highs[-20:-5]) if len(highs) >= 20 else recent_high
            
            recent_low = min(lows[-5:])
            support_level = min(lows[-20:-5]) if len(lows) >= 20 else recent_low
            
            current_price = closes[-1]
            avg_volume = statistics.mean(volumes[-20:])
            current_volume = volumes[-1]
            
            # Breakout above resistance
            if (current_price > resistance_level and 
                current_volume > avg_volume * self.volume_thresholds["breakout_volume"]):
                patterns.append("BREAKOUT_ABOVE_RESISTANCE")
            
            # Breakdown below support
            if (current_price < support_level and 
                current_volume > avg_volume * self.volume_thresholds["breakout_volume"]):
                patterns.append("BREAKDOWN_BELOW_SUPPORT")
            
            # Consolidation pattern
            price_range = (max(highs[-10:]) - min(lows[-10:])) / current_price
            if price_range < 0.02:  # Less than 2% range
                patterns.append("CONSOLIDATION")
            
            # Volume breakout without price breakout (accumulation/distribution)
            if (current_volume > avg_volume * 2.0 and 
                abs(current_price - closes[-5]) / closes[-5] < 0.01):
                patterns.append("VOLUME_BREAKOUT_NO_PRICE")
            
            return {
                "patterns_detected": patterns,
                "resistance_level": resistance_level,
                "support_level": support_level,
                "price_range_pct": price_range * 100,
                "breakout_volume_ratio": current_volume / avg_volume if avg_volume > 0 else 1
            }
            
        except Exception as e:
            logger.error(f"Error detecting patterns: {e}")
            return {}
    
    def _analyze_price_action(self, bars: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze price action characteristics."""
        try:
            if len(bars) < 10:
                return {}
            
            # Recent price action
            recent_bars = bars[-10:]
            
            # Count bullish/bearish bars
            bullish_bars = sum(1 for bar in recent_bars if bar['close'] > bar['open'])
            bearish_bars = sum(1 for bar in recent_bars if bar['close'] < bar['open'])
            
            # Average body size (close - open)
            body_sizes = [abs(bar['close'] - bar['open']) / bar['open'] for bar in recent_bars if bar['open'] > 0]
            avg_body_size = statistics.mean(body_sizes) if body_sizes else 0
            
            # Average wick sizes
            upper_wicks = [(bar['high'] - max(bar['open'], bar['close'])) / bar['open'] 
                          for bar in recent_bars if bar['open'] > 0]
            lower_wicks = [(min(bar['open'], bar['close']) - bar['low']) / bar['open'] 
                          for bar in recent_bars if bar['open'] > 0]
            
            avg_upper_wick = statistics.mean(upper_wicks) if upper_wicks else 0
            avg_lower_wick = statistics.mean(lower_wicks) if lower_wicks else 0
            
            # Price action signal
            if bullish_bars >= 7:
                price_action_signal = "STRONG_BULLISH"
            elif bullish_bars >= 6:
                price_action_signal = "BULLISH"
            elif bearish_bars >= 7:
                price_action_signal = "STRONG_BEARISH"
            elif bearish_bars >= 6:
                price_action_signal = "BEARISH"
            else:
                price_action_signal = "NEUTRAL"
            
            return {
                "bullish_bars": bullish_bars,
                "bearish_bars": bearish_bars,
                "avg_body_size_pct": avg_body_size * 100,
                "avg_upper_wick_pct": avg_upper_wick * 100,
                "avg_lower_wick_pct": avg_lower_wick * 100,
                "price_action_signal": price_action_signal,
                "is_trending": abs(bullish_bars - bearish_bars) >= 4
            }
            
        except Exception as e:
            logger.error(f"Error analyzing price action: {e}")
            return {}
    
    def _calculate_overall_signal(self, volume_analysis: Dict, momentum_analysis: Dict, 
                                patterns: Dict, price_action: Dict) -> str:
        """Calculate overall signal from all analyses."""
        try:
            signals = []
            
            # Volume signals
            volume_signal = volume_analysis.get("volume_signal", "NORMAL")
            if volume_signal in ["SPIKE", "MASSIVE_SPIKE"]:
                signals.append("BULLISH")
            elif volume_signal == "LOW":
                signals.append("BEARISH")
            
            # Momentum signals
            momentum_signal = momentum_analysis.get("momentum_signal", "STABLE")
            if momentum_signal in ["ACCELERATION", "STRONG_ACCELERATION"]:
                signals.append("BULLISH")
            elif momentum_signal in ["DECELERATION", "REVERSAL"]:
                signals.append("BEARISH")
            
            # Pattern signals
            detected_patterns = patterns.get("patterns_detected", [])
            if "BREAKOUT_ABOVE_RESISTANCE" in detected_patterns:
                signals.append("BULLISH")
            elif "BREAKDOWN_BELOW_SUPPORT" in detected_patterns:
                signals.append("BEARISH")
            
            # Price action signals
            pa_signal = price_action.get("price_action_signal", "NEUTRAL")
            if "BULLISH" in pa_signal:
                signals.append("BULLISH")
            elif "BEARISH" in pa_signal:
                signals.append("BEARISH")
            
            # Determine overall signal
            bullish_count = signals.count("BULLISH")
            bearish_count = signals.count("BEARISH")
            
            if bullish_count >= 3:
                return "STRONG_BULLISH"
            elif bullish_count >= 2:
                return "BULLISH"
            elif bearish_count >= 3:
                return "STRONG_BEARISH"
            elif bearish_count >= 2:
                return "BEARISH"
            else:
                return "NEUTRAL"
            
        except Exception as e:
            logger.error(f"Error calculating overall signal: {e}")
            return "UNKNOWN"
    
    def _generate_alerts(self, symbol: str, analysis: Dict[str, Any], position: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate alerts based on analysis."""
        alerts = []
        
        try:
            volume_analysis = analysis.get("volume", {})
            momentum_analysis = analysis.get("momentum", {})
            patterns = analysis.get("patterns", {})
            overall_signal = analysis.get("overall_signal", "NEUTRAL")
            
            # Volume spike alerts
            volume_signal = volume_analysis.get("volume_signal")
            if volume_signal == "MASSIVE_SPIKE":
                alerts.append({
                    "type": "MASSIVE_VOLUME_SPIKE",
                    "symbol": symbol,
                    "message": f"🚀 {symbol}: Massive volume spike - {volume_analysis.get('volume_ratio_20', 0):.1f}x average",
                    "reasoning": f"Volume is {volume_analysis.get('volume_ratio_20', 0):.1f}x the 20-period average. "
                               f"Indicates strong institutional interest or news impact. Monitor for continuation.",
                    "severity": "HIGH",
                    "volume_ratio": volume_analysis.get("volume_ratio_20", 0),
                    "action_required": "MONITOR_CLOSELY"
                })
            
            elif volume_signal == "SPIKE":
                alerts.append({
                    "type": "VOLUME_SPIKE",
                    "symbol": symbol,
                    "message": f"📈 {symbol}: Volume spike - {volume_analysis.get('volume_ratio_20', 0):.1f}x average",
                    "reasoning": f"Above-average volume ({volume_analysis.get('volume_ratio_20', 0):.1f}x) suggests increased interest.",
                    "severity": "MEDIUM",
                    "volume_ratio": volume_analysis.get("volume_ratio_20", 0),
                    "action_required": "MONITOR"
                })
            
            # Momentum alerts
            momentum_signal = momentum_analysis.get("momentum_signal")
            if momentum_signal == "STRONG_ACCELERATION":
                alerts.append({
                    "type": "STRONG_MOMENTUM_ACCELERATION",
                    "symbol": symbol,
                    "message": f"⚡ {symbol}: Strong momentum acceleration",
                    "reasoning": f"Momentum accelerating strongly ({momentum_analysis.get('momentum_acceleration', 0):.1f}x). "
                               f"Consider letting winners run or taking partial profits.",
                    "severity": "HIGH",
                    "momentum_acceleration": momentum_analysis.get("momentum_acceleration", 0),
                    "action_required": "LET_RUN_OR_PARTIAL_PROFITS"
                })
            
            elif momentum_signal == "DECELERATION":
                alerts.append({
                    "type": "MOMENTUM_DECELERATION",
                    "symbol": symbol,
                    "message": f"⚠️ {symbol}: Momentum decelerating",
                    "reasoning": f"Momentum slowing down. Consider taking profits or tightening stops.",
                    "severity": "MEDIUM",
                    "momentum_acceleration": momentum_analysis.get("momentum_acceleration", 0),
                    "action_required": "CONSIDER_PROFITS"
                })
            
            # Pattern alerts
            detected_patterns = patterns.get("patterns_detected", [])
            if "BREAKOUT_ABOVE_RESISTANCE" in detected_patterns:
                alerts.append({
                    "type": "BREAKOUT_DETECTED",
                    "symbol": symbol,
                    "message": f"📈 {symbol}: Breakout above resistance",
                    "reasoning": f"Price broke above resistance level with volume confirmation. "
                               f"Bullish signal - consider holding or adding to position.",
                    "severity": "HIGH",
                    "resistance_level": patterns.get("resistance_level", 0),
                    "action_required": "HOLD_OR_ADD"
                })
            
            elif "BREAKDOWN_BELOW_SUPPORT" in detected_patterns:
                alerts.append({
                    "type": "BREAKDOWN_DETECTED",
                    "symbol": symbol,
                    "message": f"📉 {symbol}: Breakdown below support",
                    "reasoning": f"Price broke below support level with volume. "
                               f"Bearish signal - consider exiting or reducing position.",
                    "severity": "HIGH",
                    "support_level": patterns.get("support_level", 0),
                    "action_required": "CONSIDER_EXIT"
                })
            
            # Overall signal alerts
            if overall_signal == "STRONG_BULLISH" and position.get('unrealized_plpc', 0) > 0:
                alerts.append({
                    "type": "STRONG_BULLISH_SIGNAL",
                    "symbol": symbol,
                    "message": f"🔥 {symbol}: Strong bullish signals aligned",
                    "reasoning": f"Multiple bullish indicators: volume, momentum, and price action all positive. "
                               f"Consider letting position run or scaling in.",
                    "severity": "HIGH",
                    "overall_signal": overall_signal,
                    "action_required": "LET_RUN"
                })
            
            elif overall_signal == "STRONG_BEARISH":
                alerts.append({
                    "type": "STRONG_BEARISH_SIGNAL",
                    "symbol": symbol,
                    "message": f"🔴 {symbol}: Strong bearish signals",
                    "reasoning": f"Multiple bearish indicators aligned. Consider reducing exposure or exiting.",
                    "severity": "HIGH",
                    "overall_signal": overall_signal,
                    "action_required": "REDUCE_OR_EXIT"
                })
            
        except Exception as e:
            logger.error(f"Error generating alerts for {symbol}: {e}")
        
        return alerts
    
    def _store_analysis_history(self, symbol: str, analysis: Dict[str, Any]):
        """Store analysis history for trend detection."""
        try:
            if symbol not in self.analysis_history:
                self.analysis_history[symbol] = []
            
            # Add current analysis
            self.analysis_history[symbol].append({
                "timestamp": datetime.now(),
                "analysis": analysis.copy()
            })
            
            # Keep only last 4 hours of data
            cutoff = datetime.now() - timedelta(hours=4)
            self.analysis_history[symbol] = [
                entry for entry in self.analysis_history[symbol]
                if entry["timestamp"] > cutoff
            ]
            
        except Exception as e:
            logger.error(f"Error storing analysis history: {e}")
    
    def get_analysis_summary(self, symbol: str) -> Dict[str, Any]:
        """Get analysis summary for a specific symbol."""
        try:
            if symbol not in self.analysis_history or not self.analysis_history[symbol]:
                return {"error": "No analysis history found"}
            
            latest = self.analysis_history[symbol][-1]
            history = self.analysis_history[symbol]
            
            return {
                "symbol": symbol,
                "latest_analysis": latest["analysis"],
                "last_updated": latest["timestamp"].isoformat(),
                "history_points": len(history),
                "trend": self._calculate_trend(history)
            }
            
        except Exception as e:
            logger.error(f"Error getting analysis summary: {e}")
            return {"error": str(e)}
    
    def _calculate_trend(self, history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate trends from analysis history."""
        try:
            if len(history) < 2:
                return {}
            
            # Get volume trend
            volume_ratios = [
                entry["analysis"].get("volume", {}).get("volume_ratio_20", 1)
                for entry in history
            ]
            
            # Get momentum trend
            momentum_values = [
                entry["analysis"].get("momentum", {}).get("momentum_5min", 0)
                for entry in history
            ]
            
            return {
                "volume_trend": "increasing" if volume_ratios[-1] > volume_ratios[0] else "decreasing",
                "momentum_trend": "increasing" if momentum_values[-1] > momentum_values[0] else "decreasing",
                "volume_avg": statistics.mean(volume_ratios),
                "momentum_avg": statistics.mean(momentum_values)
            }
            
        except Exception as e:
            logger.error(f"Error calculating trend: {e}")
            return {}


# Singleton instance
_volume_momentum_analyzer = None

def get_volume_momentum_analyzer():
    """Get or create volume momentum analyzer."""
    global _volume_momentum_analyzer
    if _volume_momentum_analyzer is None:
        _volume_momentum_analyzer = VolumeMomentumAnalyzer()
    return _volume_momentum_analyzer
