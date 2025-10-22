"""
Risk Manager Agent - Manages risk and validates trades.
"""
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, date
from loguru import logger

from agents.base_agent import BaseAgent
from services import get_alpaca_service, get_database_service
from config import settings


class RiskManagerAgent(BaseAgent):
    """Agent responsible for risk management and trade validation."""
    
    def __init__(self):
        """Initialize the risk manager agent."""
        super().__init__("RiskManager")
        self.alpaca = get_alpaca_service()
        self.db = get_database_service()
        self.daily_loss = 0.0
        self.circuit_breaker_triggered = False
    
    async def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process risk management request.
        
        Args:
            data: Request data with 'action' and trade data
            
        Returns:
            Risk assessment result
        """
        action = data.get("action")
        
        if action == "validate_trade":
            trade = data.get("trade")
            return await self.validate_trade(trade)
        elif action == "check_position_limits":
            return await self.check_position_limits()
        elif action == "check_circuit_breaker":
            return await self.check_circuit_breaker()
        elif action == "calculate_position_size":
            analysis = data.get("analysis")
            return await self.calculate_position_size(analysis)
        elif action == "check_exit_conditions":
            position = data.get("position")
            return await self.check_exit_conditions(position)
        else:
            return {"error": f"Unknown action: {action}"}
    
    async def validate_trade(self, trade: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate a trade against risk parameters.
        
        Args:
            trade: Trade data with symbol, action, quantity, price
            
        Returns:
            Validation result
        """
        try:
            symbol = trade['symbol']
            action = trade['action']
            quantity = trade['quantity']
            price = trade['price']
            
            logger.info(f"Validating trade: {action} {quantity} {symbol} @ ${price}")
            
            # Check circuit breaker
            if self.circuit_breaker_triggered:
                return {
                    "approved": False,
                    "reason": "Circuit breaker triggered - max daily loss exceeded"
                }
            
            # Check if system is paused
            paused = await self.db.get_system_state("paused")
            if paused == "true":
                return {
                    "approved": False,
                    "reason": "System is paused"
                }
            
            # For buy orders, check additional constraints
            if action.lower() == "buy":
                # Check position limits
                positions = await self.alpaca.get_positions()
                if len(positions) >= settings.max_open_positions:
                    return {
                        "approved": False,
                        "reason": f"Maximum open positions reached ({settings.max_open_positions})"
                    }
                
                # Check position size
                position_value = quantity * price
                if position_value > settings.max_position_size:
                    return {
                        "approved": False,
                        "reason": f"Position size ${position_value:.2f} exceeds maximum ${settings.max_position_size}"
                    }
                
                # Check buying power
                account = await self.alpaca.get_account()
                if position_value > account['buying_power']:
                    return {
                        "approved": False,
                        "reason": f"Insufficient buying power (need ${position_value:.2f}, have ${account['buying_power']:.2f})"
                    }
                
                # Check if already have position in this symbol
                existing_position = await self.alpaca.get_position(symbol)
                if existing_position:
                    return {
                        "approved": False,
                        "reason": f"Already have open position in {symbol}"
                    }
            
            # For sell orders, verify position exists
            elif action.lower() == "sell":
                position = await self.alpaca.get_position(symbol)
                if not position:
                    return {
                        "approved": False,
                        "reason": f"No position found for {symbol}"
                    }
                
                if quantity > position['qty']:
                    return {
                        "approved": False,
                        "reason": f"Sell quantity {quantity} exceeds position size {position['qty']}"
                    }
            
            # All checks passed
            return {
                "approved": True,
                "reason": "Trade validated successfully"
            }
            
        except Exception as e:
            logger.error(f"Error validating trade: {e}")
            return {
                "approved": False,
                "reason": f"Validation error: {str(e)}"
            }
    
    async def check_position_limits(self) -> Dict[str, Any]:
        """
        Check current position limits.
        
        Returns:
            Position limits status
        """
        try:
            positions = await self.alpaca.get_positions()
            account = await self.alpaca.get_account()
            
            total_exposure = sum(pos['market_value'] for pos in positions)
            
            return {
                "open_positions": len(positions),
                "max_positions": settings.max_open_positions,
                "positions_available": settings.max_open_positions - len(positions),
                "total_exposure": total_exposure,
                "buying_power": account['buying_power'],
                "portfolio_value": account['portfolio_value']
            }
            
        except Exception as e:
            logger.error(f"Error checking position limits: {e}")
            return {"error": str(e)}
    
    async def check_circuit_breaker(self) -> Dict[str, Any]:
        """
        Check circuit breaker status.
        
        Returns:
            Circuit breaker status
        """
        try:
            # Calculate daily P/L - ONLY from CLOSED positions (realized P&L)
            today = date.today().isoformat()
            
            # Ensure database is initialized
            await self.db.initialize()
            
            import aiosqlite
            async with aiosqlite.connect(self.db.db_path) as db:
                # Get all trades today grouped by symbol to calculate realized P&L
                cursor = await db.execute("""
                    SELECT symbol,
                           SUM(CASE WHEN action = 'buy' THEN -total_value ELSE 0 END) as total_cost,
                           SUM(CASE WHEN action = 'sell' THEN total_value ELSE 0 END) as total_revenue
                    FROM trades 
                    WHERE DATE(timestamp) = ?
                    GROUP BY symbol
                """, (today,))
                rows = await cursor.fetchall()
                
                # Calculate realized P&L (only for closed positions where we have both buy and sell)
                daily_pl = 0.0
                for row in rows:
                    symbol, total_cost, total_revenue = row
                    # Only count if we have sells (realized P&L)
                    if total_revenue > 0:
                        realized_pl = total_revenue + total_cost  # cost is negative
                        daily_pl += realized_pl
            
            # Only count losses (negative P&L)
            self.daily_loss = -daily_pl if daily_pl < 0 else 0.0
            
            # Check if circuit breaker should trigger
            if self.daily_loss >= settings.max_daily_loss:
                self.circuit_breaker_triggered = True
                logger.warning(
                    f"⚠️ Circuit breaker triggered! Daily loss: ${self.daily_loss:.2f}"
                )
                
                # Generate detailed explanation for Tara
                reason = f"Daily loss of ${self.daily_loss:.2f} exceeded limit of ${settings.max_daily_loss:.2f}"
                duration = "remainder of trading day"
                actions = [
                    "Review today's trades to identify patterns",
                    "Check if stop-losses are properly set",
                    "Consider reducing position sizes tomorrow",
                    "Wait for automatic reset at market open",
                    "Contact administrator for manual override if needed"
                ]
                
                return {
                    "triggered": True,
                    "daily_loss": self.daily_loss,
                    "max_loss": settings.max_daily_loss,
                    "remaining": 0,
                    "reason": reason,
                    "duration": duration,
                    "actions": actions,
                    "explanation": f"Circuit breaker activated to protect capital. {reason}. Trading will resume automatically tomorrow."
                }
            
            return {
                "triggered": False,
                "daily_loss": self.daily_loss,
                "max_loss": settings.max_daily_loss,
                "remaining": settings.max_daily_loss - self.daily_loss,
                "reason": None,
                "duration": None,
                "actions": [],
                "explanation": f"Circuit breaker status: Normal. ${settings.max_daily_loss - self.daily_loss:.2f} remaining before activation."
            }
            
        except Exception as e:
            logger.error(f"Error checking circuit breaker: {e}")
            return {
                "triggered": False,
                "daily_loss": 0.0,
                "max_loss": settings.max_daily_loss,
                "remaining": settings.max_daily_loss,
                "error": str(e)
            }
    
    async def calculate_position_size(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate appropriate position size based on risk.
        
        Args:
            analysis: Strategy analysis result
            
        Returns:
            Position sizing recommendation
        """
        try:
            symbol = analysis['symbol']
            confidence = analysis['confidence']
            risk_level = analysis.get('risk_level', 'MEDIUM')  # Default to MEDIUM if not provided
            current_price = analysis.get('current_price', analysis.get('price', 0))  # Get from analysis directly
            
            # Base position size
            base_size = settings.max_position_size
            
            # Adjust based on confidence
            confidence_factor = confidence / 100.0
            
            # Adjust based on risk level
            risk_factors = {
                "LOW": 1.0,
                "MEDIUM": 0.7,
                "HIGH": 0.4
            }
            risk_factor = risk_factors.get(risk_level, 0.5)
            
            # Calculate position value
            position_value = base_size * confidence_factor * risk_factor
            
            # Calculate quantity
            quantity = int(position_value / current_price)
            
            # Ensure minimum quantity
            if quantity < 1:
                quantity = 1
            
            actual_value = quantity * current_price
            
            # Calculate stop loss and take profit
            stop_loss_price = current_price * (1 - settings.stop_loss_pct)
            take_profit_price = current_price * (1 + settings.profit_target_pct)
            
            return {
                "symbol": symbol,
                "quantity": quantity,
                "position_value": actual_value,
                "price": current_price,
                "stop_loss": stop_loss_price,
                "take_profit": take_profit_price,
                "confidence_factor": confidence_factor,
                "risk_factor": risk_factor
            }
            
        except Exception as e:
            logger.error(f"Error calculating position size: {e}")
            return {"error": str(e)}
    
    async def check_exit_conditions(self, position: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check if exit conditions are met for a position.
        
        Args:
            position: Position data
            
        Returns:
            Exit conditions status
        """
        try:
            symbol = position['symbol']
            entry_price = position['avg_entry_price']
            current_price = position['current_price']
            unrealized_plpc = position['unrealized_plpc']
            
            # Calculate thresholds
            profit_target = settings.profit_target_pct
            stop_loss = -settings.stop_loss_pct
            
            should_exit = False
            reason = None
            
            # Check profit target
            if unrealized_plpc >= profit_target:
                should_exit = True
                reason = f"Profit target reached: {unrealized_plpc*100:.2f}% >= {profit_target*100:.2f}%"
            
            # Check stop loss
            elif unrealized_plpc <= stop_loss:
                should_exit = True
                reason = f"Stop loss triggered: {unrealized_plpc*100:.2f}% <= {stop_loss*100:.2f}%"
            
            return {
                "symbol": symbol,
                "should_exit": should_exit,
                "reason": reason,
                "current_pl_pct": unrealized_plpc * 100,
                "profit_target_pct": profit_target * 100,
                "stop_loss_pct": stop_loss * 100,
                "entry_price": entry_price,
                "current_price": current_price
            }
            
        except Exception as e:
            logger.error(f"Error checking exit conditions: {e}")
            return {"error": str(e)}
    
    async def validate_options_trade(self, trade: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate an options trade with specific checks.
        
        Args:
            trade: Options trade details
            
        Returns:
            Validation result
        """
        from config import settings
        
        try:
            # Check 1: Premium within limit
            premium = trade['premium']
            contracts = trade['contracts']
            total_cost = premium * 100 * contracts  # Premium is per share, 100 shares per contract
            
            max_cost = settings.options_max_premium * contracts
            if total_cost > max_cost:
                return {
                    "approved": False,
                    "reason": f"Premium too expensive: ${total_cost:.2f} > ${max_cost:.2f}"
                }
            
            # Check 2: Days to expiration
            dte = trade['dte']
            if dte < settings.options_min_dte:
                return {
                    "approved": False,
                    "reason": f"Expiration too soon: {dte} days < {settings.options_min_dte} min"
                }
            if dte > settings.options_max_dte:
                return {
                    "approved": False,
                    "reason": f"Expiration too far: {dte} days > {settings.options_max_dte} max"
                }
            
            # Check 3: Max contracts
            if contracts > settings.options_max_contracts:
                return {
                    "approved": False,
                    "reason": f"Too many contracts: {contracts} > {settings.options_max_contracts} max"
                }
            
            # Check 4: Buying power
            account = await self.alpaca.get_account()
            if total_cost > account['buying_power']:
                return {
                    "approved": False,
                    "reason": f"Insufficient buying power: ${total_cost:.2f} > ${account['buying_power']:.2f}"
                }
            
            # Check 5: Circuit breaker
            circuit_breaker = await self.check_circuit_breaker()
            if circuit_breaker.get('triggered'):
                return {
                    "approved": False,
                    "reason": "Circuit breaker triggered"
                }
            
            # Check 6: Position limits
            position_limits = await self.check_position_limits()
            if position_limits['positions_available'] <= 0:
                return {
                    "approved": False,
                    "reason": "Maximum positions reached"
                }
            
            logger.info(
                f"Options trade validated: {contracts} {trade['underlying']} "
                f"{trade['option_type']} ${trade['strike']} @ ${premium:.2f}"
            )
            
            return {
                "approved": True,
                "reason": "All checks passed",
                "total_cost": total_cost
            }
            
        except Exception as e:
            logger.error(f"Error validating options trade: {e}")
            return {
                "approved": False,
                "reason": f"Validation error: {str(e)}"
            }
    
    async def calculate_options_position_size(self, analysis: Dict[str, Any], 
                                             premium: float) -> Dict[str, Any]:
        """
        Calculate number of option contracts based on confidence and risk.
        
        Args:
            analysis: Strategy analysis result
            premium: Option premium per share
            
        Returns:
            Position sizing recommendation
        """
        from config import settings
        
        try:
            confidence = analysis['confidence']
            
            # Base contracts on confidence
            if confidence >= 80:
                contracts = min(2, settings.options_max_contracts)
            elif confidence >= 70:
                contracts = 1
            else:
                contracts = 0
            
            # Calculate total cost
            total_cost = premium * 100 * contracts
            
            # Ensure within premium limit
            max_cost = settings.options_max_premium * contracts
            if total_cost > max_cost and contracts > 0:
                # Reduce to 1 contract if 2 is too expensive
                contracts = 1
                total_cost = premium * 100
                
                # If still too expensive, reject
                if total_cost > settings.options_max_premium:
                    return {
                        "contracts": 0,
                        "reason": f"Premium too expensive even for 1 contract: ${total_cost:.2f}"
                    }
            
            return {
                "contracts": contracts,
                "total_cost": total_cost,
                "premium_per_share": premium,
                "reason": f"Confidence {confidence}% → {contracts} contract(s)"
            }
            
        except Exception as e:
            logger.error(f"Error calculating options position size: {e}")
            return {
                "contracts": 0,
                "reason": f"Error: {str(e)}"
            }
    
    async def reset_circuit_breaker(self):
        """Reset the circuit breaker (typically at start of new day)."""
        self.circuit_breaker_triggered = False
        self.daily_loss = 0.0
        logger.info("Circuit breaker reset")
