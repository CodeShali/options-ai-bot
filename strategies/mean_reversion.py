"""
Mean Reversion Strategy.

Entry: RSI < 30 (oversold) + Price < 20-day SMA
Exit: RSI > 70 (overbought) OR Price > 20-day SMA
Stop: 2% below entry
Target: 5% above entry
"""
from typing import Dict, Any, Optional, List
from loguru import logger
from utils.technical_indicators import TechnicalIndicators


class MeanReversionStrategy:
    """
    Mean Reversion Trading Strategy.
    
    Buys oversold stocks and sells when they revert to mean.
    """
    
    def __init__(self):
        """Initialize strategy."""
        self.name = "Mean Reversion"
        self.rsi_oversold = 30
        self.rsi_overbought = 70
        self.sma_period = 20
        self.stop_loss_pct = 0.02  # 2%
        self.take_profit_pct = 0.05  # 5%
        
        logger.info(f"✅ {self.name} strategy initialized")
    
    def analyze(self, symbol: str, bars: List[Dict[str, Any]], current_price: float) -> Dict[str, Any]:
        """
        Analyze if stock meets mean reversion criteria.
        
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
            
            # Calculate indicators
            rsi = TechnicalIndicators.calculate_rsi(closes, period=14)
            sma_20 = TechnicalIndicators.calculate_sma(closes, period=self.sma_period)
            
            if not rsi or not sma_20:
                return {"action": "HOLD", "reason": "Indicator calculation failed"}
            
            current_rsi = rsi[-1]
            current_sma = sma_20[-1]
            
            if current_rsi is None or current_sma is None:
                return {"action": "HOLD", "reason": "Invalid indicator values"}
            
            # Entry Signal: RSI < 30 AND Price < 20-day SMA
            if current_rsi < self.rsi_oversold and current_price < current_sma:
                return {
                    "action": "BUY",
                    "strategy": self.name,
                    "reason": f"Oversold: RSI={current_rsi:.1f} < {self.rsi_oversold}, Price ${current_price:.2f} < SMA ${current_sma:.2f}",
                    "entry_price": current_price,
                    "stop_loss": current_price * (1 - self.stop_loss_pct),
                    "take_profit": current_price * (1 + self.take_profit_pct),
                    "indicators": {
                        "rsi": current_rsi,
                        "sma_20": current_sma,
                        "price_vs_sma": ((current_price - current_sma) / current_sma) * 100
                    }
                }
            
            # Exit Signal: RSI > 70 OR Price > 20-day SMA
            if current_rsi > self.rsi_overbought or current_price > current_sma:
                return {
                    "action": "SELL",
                    "strategy": self.name,
                    "reason": f"Exit: RSI={current_rsi:.1f} or Price ${current_price:.2f} > SMA ${current_sma:.2f}",
                    "indicators": {
                        "rsi": current_rsi,
                        "sma_20": current_sma
                    }
                }
            
            # Hold - Provide detailed explanation
            price_vs_sma_pct = ((current_price - current_sma) / current_sma) * 100
            
            # Determine what's missing for entry
            conditions_met = []
            conditions_needed = []
            
            if current_rsi < self.rsi_oversold:
                conditions_met.append(f"RSI oversold ({current_rsi:.1f} < {self.rsi_oversold})")
            else:
                conditions_needed.append(f"RSI needs to drop to {self.rsi_oversold} (currently {current_rsi:.1f})")
            
            if current_price < current_sma:
                conditions_met.append(f"Price below SMA (${current_price:.2f} < ${current_sma:.2f})")
            else:
                conditions_needed.append(f"Price needs to drop to ${current_sma:.2f} (currently ${current_price:.2f}, {price_vs_sma_pct:+.2f}%)")
            
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
                "next_check": "Wait for RSI < 30 AND Price < 20-day SMA",
                "indicators": {
                    "rsi": current_rsi,
                    "rsi_target": self.rsi_oversold,
                    "sma_20": current_sma,
                    "price": current_price,
                    "price_vs_sma_pct": price_vs_sma_pct
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
            
            # Stop Loss: 2% below entry
            if pnl_pct <= -self.stop_loss_pct * 100:
                return {
                    "exit": True,
                    "reason": f"Stop loss hit: {pnl_pct:.2f}%",
                    "type": "STOP_LOSS"
                }
            
            # Take Profit: 5% above entry
            if pnl_pct >= self.take_profit_pct * 100:
                return {
                    "exit": True,
                    "reason": f"Take profit hit: {pnl_pct:.2f}%",
                    "type": "TAKE_PROFIT"
                }
            
            # Check technical exit
            if len(bars) >= 30:
                closes = [bar['close'] for bar in bars]
                rsi = TechnicalIndicators.calculate_rsi(closes, period=14)
                sma_20 = TechnicalIndicators.calculate_sma(closes, period=self.sma_period)
                
                if rsi and sma_20:
                    current_rsi = rsi[-1]
                    current_sma = sma_20[-1]
                    
                    # Exit if RSI > 70 (overbought) or price > SMA
                    if current_rsi is not None and current_rsi > self.rsi_overbought:
                        return {
                            "exit": True,
                            "reason": f"Overbought: RSI={current_rsi:.1f}",
                            "type": "TECHNICAL"
                        }
                    
                    if current_sma is not None and current_price > current_sma:
                        return {
                            "exit": True,
                            "reason": f"Price above SMA: ${current_price:.2f} > ${current_sma:.2f}",
                            "type": "TECHNICAL"
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
        
        # Stop loss is 2% below entry
        risk_per_share = current_price * self.stop_loss_pct
        
        if risk_per_share > 0:
            shares = int(risk_amount / risk_per_share)
            
            # Ensure position doesn't exceed 10% of account
            max_position = account_value * 0.10
            max_shares = int(max_position / current_price)
            
            return min(shares, max_shares)
        
        return 0
