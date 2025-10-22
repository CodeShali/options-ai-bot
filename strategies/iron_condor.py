"""
Iron Condor Options Strategy.

Entry: High IV, neutral outlook
- Sell OTM call spread
- Sell OTM put spread
- 30-45 DTE

Exit:
- 50% max profit
- 21 DTE
- Stop at 2x credit received
"""
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from loguru import logger


class IronCondorStrategy:
    """
    Iron Condor Options Strategy.
    
    Sells premium in neutral markets with high implied volatility.
    """
    
    def __init__(self):
        """Initialize strategy."""
        self.name = "Iron Condor"
        self.min_dte = 30
        self.max_dte = 45
        self.exit_dte = 21
        self.profit_target_pct = 0.50  # 50% of max profit
        self.stop_loss_multiplier = 2.0  # 2x credit received
        self.delta_target = 0.16  # ~84% probability of profit
        self.min_iv_rank = 50  # Minimum IV rank
        
        logger.info(f"✅ {self.name} strategy initialized")
    
    def analyze(self, symbol: str, current_price: float, iv_rank: float = None, 
                options_chain: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Analyze if stock meets iron condor criteria.
        
        Args:
            symbol: Stock symbol
            current_price: Current stock price
            iv_rank: Implied Volatility Rank (0-100)
            options_chain: Options chain data
            
        Returns:
            Signal dictionary with action and details
        """
        try:
            # Check IV Rank
            if iv_rank is None or iv_rank < self.min_iv_rank:
                return {
                    "action": "HOLD",
                    "reason": f"IV Rank too low: {iv_rank if iv_rank else 'N/A'} < {self.min_iv_rank}"
                }
            
            if not options_chain:
                return {
                    "action": "HOLD",
                    "reason": "No options chain data available"
                }
            
            # Find suitable expiration (30-45 DTE)
            target_date = datetime.now() + timedelta(days=self.min_dte)
            max_date = datetime.now() + timedelta(days=self.max_dte)
            
            suitable_expiration = None
            
            # This is a simplified version - in production, you'd parse actual options chain
            # For now, we'll create a theoretical iron condor
            
            # Calculate strikes based on delta
            # Sell call at ~0.16 delta (84% OTM)
            # Sell put at ~0.16 delta (84% OTM)
            # Buy further OTM for protection
            
            # Approximate strikes (simplified)
            # In production, use actual options data with Greeks
            call_sell_strike = current_price * 1.05  # ~5% OTM
            call_buy_strike = current_price * 1.10   # ~10% OTM
            put_sell_strike = current_price * 0.95   # ~5% OTM
            put_buy_strike = current_price * 0.90    # ~10% OTM
            
            # Estimate credit (simplified - in production, use actual option prices)
            spread_width = call_buy_strike - call_sell_strike
            estimated_credit = spread_width * 0.33  # ~33% of width
            
            max_loss = spread_width - estimated_credit
            
            return {
                "action": "OPEN_IRON_CONDOR",
                "strategy": self.name,
                "reason": f"High IV ({iv_rank:.0f}), neutral outlook, {self.min_dte}-{self.max_dte} DTE",
                "legs": {
                    "call_spread": {
                        "sell_strike": round(call_sell_strike, 2),
                        "buy_strike": round(call_buy_strike, 2),
                        "action": "SELL"
                    },
                    "put_spread": {
                        "sell_strike": round(put_sell_strike, 2),
                        "buy_strike": round(put_buy_strike, 2),
                        "action": "SELL"
                    }
                },
                "estimated_credit": round(estimated_credit, 2),
                "max_loss": round(max_loss, 2),
                "max_profit": round(estimated_credit, 2),
                "profit_target": round(estimated_credit * self.profit_target_pct, 2),
                "stop_loss": round(estimated_credit * self.stop_loss_multiplier, 2),
                "dte_range": f"{self.min_dte}-{self.max_dte}",
                "indicators": {
                    "iv_rank": iv_rank,
                    "current_price": current_price,
                    "delta_target": self.delta_target
                }
            }
            
        except Exception as e:
            logger.error(f"Error in {self.name} strategy for {symbol}: {e}")
            return {"action": "HOLD", "reason": f"Error: {str(e)}"}
    
    def check_exit(self, position: Dict[str, Any], current_price: float, 
                   dte: int, current_value: float) -> Dict[str, Any]:
        """
        Check if iron condor should be closed.
        
        Args:
            position: Current position details
            current_price: Current stock price
            dte: Days to expiration
            current_value: Current value of the iron condor
            
        Returns:
            Exit signal dictionary
        """
        try:
            credit_received = position.get('credit_received', 0)
            if credit_received == 0:
                return {"exit": False}
            
            # Calculate current P&L
            # For iron condor: profit when value decreases
            pnl = credit_received - current_value
            pnl_pct = (pnl / credit_received) * 100
            
            # Exit 1: 50% of max profit achieved
            profit_target = credit_received * self.profit_target_pct
            if pnl >= profit_target:
                return {
                    "exit": True,
                    "reason": f"Profit target hit: ${pnl:.2f} ({pnl_pct:.1f}% of credit)",
                    "type": "PROFIT_TARGET"
                }
            
            # Exit 2: 21 DTE (time-based exit)
            if dte <= self.exit_dte:
                return {
                    "exit": True,
                    "reason": f"Time exit: {dte} DTE <= {self.exit_dte} (P&L: ${pnl:.2f})",
                    "type": "TIME_EXIT"
                }
            
            # Exit 3: Stop loss at 2x credit received
            stop_loss = credit_received * self.stop_loss_multiplier
            if current_value >= stop_loss:
                return {
                    "exit": True,
                    "reason": f"Stop loss hit: ${current_value:.2f} >= ${stop_loss:.2f}",
                    "type": "STOP_LOSS"
                }
            
            # Exit 4: One side tested (price moved significantly)
            call_sell_strike = position.get('call_sell_strike', 0)
            put_sell_strike = position.get('put_sell_strike', 0)
            
            if call_sell_strike and current_price >= call_sell_strike:
                return {
                    "exit": True,
                    "reason": f"Call side tested: ${current_price:.2f} >= ${call_sell_strike:.2f}",
                    "type": "TESTED"
                }
            
            if put_sell_strike and current_price <= put_sell_strike:
                return {
                    "exit": True,
                    "reason": f"Put side tested: ${current_price:.2f} <= ${put_sell_strike:.2f}",
                    "type": "TESTED"
                }
            
            return {"exit": False}
            
        except Exception as e:
            logger.error(f"Error checking exit for {self.name}: {e}")
            return {"exit": False}
    
    def get_position_size(self, account_value: float, credit_per_contract: float, 
                         max_loss_per_contract: float) -> int:
        """
        Calculate number of iron condor contracts to trade.
        
        Args:
            account_value: Total account value
            credit_per_contract: Credit received per contract
            max_loss_per_contract: Maximum loss per contract
            
        Returns:
            Number of contracts
        """
        # Risk 2-3% of account per trade (iron condors are higher probability)
        risk_amount = account_value * 0.025  # 2.5%
        
        if max_loss_per_contract > 0:
            contracts = int(risk_amount / max_loss_per_contract)
            
            # Ensure position doesn't exceed 10% of account
            max_capital_at_risk = account_value * 0.10
            max_contracts = int(max_capital_at_risk / max_loss_per_contract)
            
            # At least 1 contract, max based on risk
            return max(1, min(contracts, max_contracts))
        
        return 1
    
    def adjust_position(self, position: Dict[str, Any], current_price: float, 
                       dte: int) -> Dict[str, Any]:
        """
        Determine if position needs adjustment.
        
        Args:
            position: Current position details
            current_price: Current stock price
            dte: Days to expiration
            
        Returns:
            Adjustment recommendation
        """
        try:
            call_sell_strike = position.get('call_sell_strike', 0)
            put_sell_strike = position.get('put_sell_strike', 0)
            
            # Check if one side is being tested
            call_distance = ((call_sell_strike - current_price) / current_price) * 100 if call_sell_strike else 100
            put_distance = ((current_price - put_sell_strike) / current_price) * 100 if put_sell_strike else 100
            
            # If price is within 2% of a short strike, consider adjustment
            if call_distance < 2:
                return {
                    "adjust": True,
                    "reason": f"Call side threatened: {call_distance:.1f}% away",
                    "action": "ROLL_CALLS_UP",
                    "side": "CALL"
                }
            
            if put_distance < 2:
                return {
                    "adjust": True,
                    "reason": f"Put side threatened: {put_distance:.1f}% away",
                    "action": "ROLL_PUTS_DOWN",
                    "side": "PUT"
                }
            
            return {"adjust": False}
            
        except Exception as e:
            logger.error(f"Error checking adjustment for {self.name}: {e}")
            return {"adjust": False}
