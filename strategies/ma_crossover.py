"""
Moving Average Crossover Strategy.

Entry:
- 50-day SMA crosses above 200-day SMA (Golden Cross)
- Volume confirmation

Exit:
- 50-day SMA crosses below 200-day SMA (Death Cross)
- OR 3% stop loss
"""
from typing import Dict, Any, Optional, List
from loguru import logger
from utils.technical_indicators import TechnicalIndicators


class MACrossoverStrategy:
    """
    Moving Average Crossover Trading Strategy.
    
    Trades based on golden cross and death cross signals.
    """
    
    def __init__(self):
        """Initialize strategy."""
        self.name = "MA Crossover"
        self.fast_period = 50
        self.slow_period = 200
        self.volume_confirmation = True
        self.stop_loss_pct = 0.03  # 3%
        
        logger.info(f"✅ {self.name} strategy initialized")
    
    def analyze(self, symbol: str, bars: List[Dict[str, Any]], current_price: float) -> Dict[str, Any]:
        """
        Analyze if stock meets MA crossover criteria.
        
        Args:
            symbol: Stock symbol
            bars: Historical bars (OHLCV)
            current_price: Current price
            
        Returns:
            Signal dictionary with action and details
        """
        try:
            if len(bars) < self.slow_period + 5:
                return {"action": "HOLD", "reason": f"Insufficient data (need {self.slow_period + 5} bars)"}
            
            # Extract data
            closes = [bar['close'] for bar in bars]
            volumes = [bar['volume'] for bar in bars]
            
            # Calculate moving averages
            sma_50 = TechnicalIndicators.calculate_sma(closes, period=self.fast_period)
            sma_200 = TechnicalIndicators.calculate_sma(closes, period=self.slow_period)
            
            if not sma_50 or not sma_200:
                return {"action": "HOLD", "reason": "MA calculation failed"}
            
            current_sma_50 = sma_50[-1]
            current_sma_200 = sma_200[-1]
            prev_sma_50 = sma_50[-2]
            prev_sma_200 = sma_200[-2]
            
            if None in [current_sma_50, current_sma_200, prev_sma_50, prev_sma_200]:
                return {"action": "HOLD", "reason": "Invalid MA values"}
            
            # Calculate average volume
            avg_volume = sum(volumes[-20:]) / 20
            current_volume = volumes[-1]
            volume_confirmed = current_volume > avg_volume
            
            # Golden Cross: 50 SMA crosses above 200 SMA
            if TechnicalIndicators.is_golden_cross(sma_50, sma_200, len(sma_50) - 1):
                if self.volume_confirmation and not volume_confirmed:
                    return {
                        "action": "HOLD",
                        "reason": f"Golden Cross but low volume: {current_volume/avg_volume:.1f}x",
                        "indicators": {
                            "sma_50": current_sma_50,
                            "sma_200": current_sma_200,
                            "volume_ratio": current_volume / avg_volume
                        }
                    }
                
                return {
                    "action": "BUY",
                    "strategy": self.name,
                    "reason": f"Golden Cross: 50 SMA ${current_sma_50:.2f} > 200 SMA ${current_sma_200:.2f}",
                    "entry_price": current_price,
                    "stop_loss": current_price * (1 - self.stop_loss_pct),
                    "indicators": {
                        "sma_50": current_sma_50,
                        "sma_200": current_sma_200,
                        "volume_ratio": current_volume / avg_volume,
                        "crossover": "GOLDEN"
                    }
                }
            
            # Death Cross: 50 SMA crosses below 200 SMA
            if TechnicalIndicators.is_death_cross(sma_50, sma_200, len(sma_50) - 1):
                return {
                    "action": "SELL",
                    "strategy": self.name,
                    "reason": f"Death Cross: 50 SMA ${current_sma_50:.2f} < 200 SMA ${current_sma_200:.2f}",
                    "indicators": {
                        "sma_50": current_sma_50,
                        "sma_200": current_sma_200,
                        "crossover": "DEATH"
                    }
                }
            
            # Check current trend and distance
            distance_pct = ((current_sma_50 - current_sma_200) / current_sma_200) * 100
            
            if current_sma_50 > current_sma_200:
                trend = "BULLISH"
                trend_desc = f"50 SMA above 200 SMA by {distance_pct:.2f}%"
            elif current_sma_50 < current_sma_200:
                trend = "BEARISH"
                trend_desc = f"50 SMA below 200 SMA by {abs(distance_pct):.2f}%"
            else:
                trend = "NEUTRAL"
                trend_desc = "50 SMA equal to 200 SMA"
            
            # Determine what's needed for next signal
            vol_ratio = current_volume / avg_volume if avg_volume > 0 else 0
            
            if trend == "BULLISH":
                next_signal = "Death Cross (50 SMA crosses below 200 SMA)"
                conditions_needed = [f"Waiting for trend reversal or {next_signal}"]
            elif trend == "BEARISH":
                next_signal = "Golden Cross (50 SMA crosses above 200 SMA)"
                conditions_needed = [f"Waiting for trend reversal or {next_signal}"]
            else:
                next_signal = "Any crossover"
                conditions_needed = ["Waiting for 50 SMA to cross 200 SMA"]
            
            # Hold - Provide detailed explanation
            reason = f"No crossover: {trend_desc}. {conditions_needed[0]}"
            
            return {
                "action": "HOLD",
                "strategy": self.name,
                "reason": reason,
                "conditions_met": [],
                "conditions_needed": conditions_needed,
                "next_check": next_signal,
                "indicators": {
                    "sma_50": current_sma_50,
                    "sma_200": current_sma_200,
                    "trend": trend,
                    "distance_pct": distance_pct,
                    "volume_ratio": vol_ratio
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
            if entry_price == 0:
                return {"exit": False}
            
            # Calculate P&L
            pnl_pct = ((current_price - entry_price) / entry_price) * 100
            
            # Stop Loss: 3% below entry
            if pnl_pct <= -self.stop_loss_pct * 100:
                return {
                    "exit": True,
                    "reason": f"Stop loss hit: {pnl_pct:.2f}%",
                    "type": "STOP_LOSS"
                }
            
            # Check for death cross
            if len(bars) >= self.slow_period + 5:
                closes = [bar['close'] for bar in bars]
                sma_50 = TechnicalIndicators.calculate_sma(closes, period=self.fast_period)
                sma_200 = TechnicalIndicators.calculate_sma(closes, period=self.slow_period)
                
                if sma_50 and sma_200:
                    # Death Cross: Exit signal
                    if TechnicalIndicators.is_death_cross(sma_50, sma_200, len(sma_50) - 1):
                        return {
                            "exit": True,
                            "reason": f"Death Cross detected (P&L: {pnl_pct:.2f}%)",
                            "type": "DEATH_CROSS"
                        }
            
            return {"exit": False}
            
        except Exception as e:
            logger.error(f"Error checking exit for {self.name}: {e}")
            return {"exit": False}
    
    def get_position_size(self, account_value: float, current_price: float, atr: float = None) -> int:
        """
        Calculate position size based on risk.
        
        Args:
            account_value: Total account value
            current_price: Current stock price
            atr: Average True Range (optional)
            
        Returns:
            Number of shares to buy
        """
        # Risk 1% of account per trade
        risk_amount = account_value * 0.01
        
        # Stop loss is 3% below entry
        risk_per_share = current_price * self.stop_loss_pct
        
        if risk_per_share > 0:
            shares = int(risk_amount / risk_per_share)
            
            # Ensure position doesn't exceed 10% of account
            max_position = account_value * 0.10
            max_shares = int(max_position / current_price)
            
            return min(shares, max_shares)
        
        return 0
