"""
Momentum Breakout Strategy.

Entry:
- Price breaks above 20-day high
- Volume > 1.5x average
- ADX > 25 (strong trend)

Exit:
- Price breaks below 10-day low
- OR trailing stop (2 ATR)

Position Size: Based on ATR (volatility)
"""
from typing import Dict, Any, Optional, List
from loguru import logger
from utils.technical_indicators import TechnicalIndicators


class MomentumBreakoutStrategy:
    """
    Momentum Breakout Trading Strategy.
    
    Buys breakouts with strong volume and trend confirmation.
    """
    
    def __init__(self):
        """Initialize strategy."""
        self.name = "Momentum Breakout"
        self.breakout_period = 20  # 20-day high
        self.exit_period = 10  # 10-day low
        self.volume_multiplier = 1.5
        self.adx_threshold = 25
        self.trailing_stop_atr = 2.0
        
        logger.info(f"✅ {self.name} strategy initialized")
    
    def analyze(self, symbol: str, bars: List[Dict[str, Any]], current_price: float) -> Dict[str, Any]:
        """
        Analyze if stock meets momentum breakout criteria.
        
        Args:
            symbol: Stock symbol
            bars: Historical bars (OHLCV)
            current_price: Current price
            
        Returns:
            Signal dictionary with action and details
        """
        try:
            if len(bars) < 30:
                return {"action": "HOLD", "reason": "Insufficient data"}
            
            # Extract data
            closes = [bar['close'] for bar in bars]
            highs = [bar['high'] for bar in bars]
            lows = [bar['low'] for bar in bars]
            volumes = [bar['volume'] for bar in bars]
            
            # Calculate 20-day high
            high_20 = max(highs[-self.breakout_period-1:-1])  # Exclude current bar
            
            # Calculate average volume
            avg_volume = sum(volumes[-20:]) / 20
            current_volume = volumes[-1]
            
            # Calculate ADX
            adx_data = TechnicalIndicators.calculate_adx(highs, lows, closes, period=14)
            
            if not adx_data['adx']:
                return {"action": "HOLD", "reason": "ADX calculation failed"}
            
            current_adx = adx_data['adx'][-1]
            
            if current_adx is None:
                return {"action": "HOLD", "reason": "Invalid ADX value"}
            
            # Calculate ATR for stop loss
            atr = TechnicalIndicators.calculate_atr(highs, lows, closes, period=14)
            current_atr = atr[-1] if atr else 0
            
            # Entry Signal: Price breaks above 20-day high + Volume > 1.5x + ADX > 25
            if (current_price > high_20 and 
                current_volume > avg_volume * self.volume_multiplier and 
                current_adx > self.adx_threshold):
                
                stop_loss = current_price - (self.trailing_stop_atr * current_atr) if current_atr else current_price * 0.95
                
                return {
                    "action": "BUY",
                    "strategy": self.name,
                    "reason": f"Breakout: Price ${current_price:.2f} > 20D High ${high_20:.2f}, Vol {current_volume/avg_volume:.1f}x, ADX {current_adx:.1f}",
                    "entry_price": current_price,
                    "stop_loss": stop_loss,
                    "trailing_stop": True,
                    "trailing_stop_distance": self.trailing_stop_atr * current_atr if current_atr else current_price * 0.05,
                    "indicators": {
                        "high_20": high_20,
                        "volume_ratio": current_volume / avg_volume,
                        "adx": current_adx,
                        "atr": current_atr
                    }
                }
            
            # Exit Signal: Price breaks below 10-day low
            if len(lows) >= self.exit_period:
                low_10 = min(lows[-self.exit_period:])
                
                if current_price < low_10:
                    return {
                        "action": "SELL",
                        "strategy": self.name,
                        "reason": f"Exit: Price ${current_price:.2f} < 10D Low ${low_10:.2f}",
                        "indicators": {
                            "low_10": low_10
                        }
                    }
            
            # Hold - Provide detailed explanation
            vol_ratio = current_volume / avg_volume
            price_to_breakout = ((high_20 - current_price) / current_price) * 100
            
            # Determine what's missing for entry
            conditions_met = []
            conditions_needed = []
            
            if current_price > high_20:
                conditions_met.append(f"Price above 20D high (${current_price:.2f} > ${high_20:.2f})")
            else:
                conditions_needed.append(f"Price needs to break ${high_20:.2f} (currently ${current_price:.2f}, {price_to_breakout:.2f}% away)")
            
            if vol_ratio > self.volume_multiplier:
                conditions_met.append(f"Volume strong ({vol_ratio:.1f}x > {self.volume_multiplier}x)")
            else:
                conditions_needed.append(f"Volume needs {self.volume_multiplier}x average (currently {vol_ratio:.1f}x)")
            
            if current_adx > self.adx_threshold:
                conditions_met.append(f"Trend strong (ADX {current_adx:.1f} > {self.adx_threshold})")
            else:
                conditions_needed.append(f"ADX needs to reach {self.adx_threshold} (currently {current_adx:.1f})")
            
            # Build detailed reason
            if conditions_met:
                reason = f"Partial setup: {', '.join(conditions_met)}. Still need: {', '.join(conditions_needed)}"
            else:
                reason = f"No setup: {', '.join(conditions_needed)}"
            
            return {
                "action": "HOLD",
                "strategy": self.name,
                "reason": reason,
                "conditions_met": conditions_met,
                "conditions_needed": conditions_needed,
                "next_check": f"Wait for breakout above ${high_20:.2f} with volume",
                "indicators": {
                    "high_20": high_20,
                    "price": current_price,
                    "price_to_breakout_pct": price_to_breakout,
                    "adx": current_adx,
                    "adx_target": self.adx_threshold,
                    "volume_ratio": vol_ratio,
                    "volume_target": self.volume_multiplier
                }
            }
            
        except Exception as e:
            logger.error(f"Error in {self.name} strategy for {symbol}: {e}")
            return {"action": "HOLD", "reason": f"Error: {str(e)}"}
    
    def check_exit(self, position: Dict[str, Any], current_price: float, bars: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Check if position should be exited.
        
        Args:
            position: Current position details
            current_price: Current price
            bars: Historical bars
            
        Returns:
            Exit signal dictionary
        """
        try:
            entry_price = position.get('entry_price', 0)
            highest_price = position.get('highest_price', entry_price)
            
            if entry_price == 0:
                return {"exit": False}
            
            # Update highest price
            if current_price > highest_price:
                highest_price = current_price
            
            # Extract data
            lows = [bar['low'] for bar in bars]
            highs = [bar['high'] for bar in bars]
            closes = [bar['close'] for bar in bars]
            
            # Calculate ATR for trailing stop
            atr = TechnicalIndicators.calculate_atr(highs, lows, closes, period=14)
            current_atr = atr[-1] if atr else 0
            
            # Trailing Stop: 2 ATR from highest price
            if current_atr:
                trailing_stop = highest_price - (self.trailing_stop_atr * current_atr)
                
                if current_price < trailing_stop:
                    pnl_pct = ((current_price - entry_price) / entry_price) * 100
                    return {
                        "exit": True,
                        "reason": f"Trailing stop hit: ${current_price:.2f} < ${trailing_stop:.2f} (P&L: {pnl_pct:.2f}%)",
                        "type": "TRAILING_STOP",
                        "highest_price": highest_price
                    }
            
            # Exit if price breaks below 10-day low
            if len(lows) >= self.exit_period:
                low_10 = min(lows[-self.exit_period:])
                
                if current_price < low_10:
                    pnl_pct = ((current_price - entry_price) / entry_price) * 100
                    return {
                        "exit": True,
                        "reason": f"Price broke 10D low: ${current_price:.2f} < ${low_10:.2f} (P&L: {pnl_pct:.2f}%)",
                        "type": "TECHNICAL"
                    }
            
            return {
                "exit": False,
                "highest_price": highest_price  # Update for next check
            }
            
        except Exception as e:
            logger.error(f"Error checking exit for {self.name}: {e}")
            return {"exit": False}
    
    def get_position_size(self, account_value: float, current_price: float, atr: float = None) -> int:
        """
        Calculate position size based on volatility (ATR).
        
        Args:
            account_value: Total account value
            current_price: Current stock price
            atr: Average True Range
            
        Returns:
            Number of shares to buy
        """
        # Risk 1% of account per trade
        risk_amount = account_value * 0.01
        
        if atr and atr > 0:
            # Risk per share is 2 ATR (trailing stop distance)
            risk_per_share = self.trailing_stop_atr * atr
        else:
            # Fallback: 5% stop loss
            risk_per_share = current_price * 0.05
        
        if risk_per_share > 0:
            shares = int(risk_amount / risk_per_share)
            
            # Ensure position doesn't exceed 10% of account
            max_position = account_value * 0.10
            max_shares = int(max_position / current_price)
            
            return min(shares, max_shares)
        
        return 0
