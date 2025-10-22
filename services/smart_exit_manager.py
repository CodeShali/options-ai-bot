"""
Smart Exit Manager - Advanced exit strategies with scaling, trailing stops, and time-based exits.
"""
import asyncio
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from loguru import logger
import math

from services import get_alpaca_service, get_database_service
from config import settings


class SmartExitManager:
    """Manage intelligent exit strategies for positions."""
    
    def __init__(self):
        """Initialize the smart exit manager."""
        self.alpaca = get_alpaca_service()
        self.db = get_database_service()
        self.position_states = {}  # Track position exit states
        
    async def setup_smart_exits(
        self,
        symbol: str,
        entry_price: float,
        quantity: int,
        position_type: str,  # 'stock', 'call', 'put'
        strategy: str = "multi_target"  # multi_target, trailing, time_based
    ) -> Dict[str, Any]:
        """
        Setup smart exit strategy for a position.
        
        Args:
            symbol: Stock/option symbol
            entry_price: Entry price
            quantity: Position size
            position_type: Type of position
            strategy: Exit strategy type
            
        Returns:
            Exit setup details
        """
        try:
            logger.info(f"🎯 Setting up smart exits for {symbol} ({position_type})")
            
            # Calculate exit levels based on position type
            exit_levels = self._calculate_exit_levels(
                entry_price, position_type, strategy
            )
            
            # Initialize position state
            self.position_states[symbol] = {
                "entry_price": entry_price,
                "quantity": quantity,
                "remaining_quantity": quantity,
                "position_type": position_type,
                "strategy": strategy,
                "exit_levels": exit_levels,
                "exits_executed": [],
                "trailing_stop": None,
                "breakeven_moved": False,
                "entry_time": datetime.now(),
                "last_price": entry_price,
                "max_profit_seen": 0,
                "max_price_seen": entry_price
            }
            
            logger.info(f"✅ Smart exits configured: {exit_levels}")
            return {
                "success": True,
                "symbol": symbol,
                "strategy": strategy,
                "exit_levels": exit_levels
            }
            
        except Exception as e:
            logger.error(f"Error setting up smart exits: {e}")
            return {"success": False, "error": str(e)}
    
    def _calculate_exit_levels(
        self,
        entry_price: float,
        position_type: str,
        strategy: str
    ) -> Dict[str, Any]:
        """Calculate exit levels based on position type and strategy."""
        
        if position_type == "stock":
            return self._calculate_stock_exits(entry_price, strategy)
        elif position_type in ["call", "put"]:
            return self._calculate_options_exits(entry_price, position_type, strategy)
        else:
            # Default exits
            return {
                "target1": entry_price * 1.05,  # 5% gain
                "target2": entry_price * 1.10,  # 10% gain
                "target3": entry_price * 1.20,  # 20% gain
                "stop_loss": entry_price * 0.95,  # 5% loss
                "time_exit_hours": 4
            }
    
    def _calculate_stock_exits(self, entry_price: float, strategy: str) -> Dict[str, Any]:
        """Calculate exit levels for stock positions."""
        
        if strategy == "multi_target":
            return {
                "target1": entry_price * 1.03,    # 3% - Take 1/3 off
                "target1_size": 0.33,
                "target2": entry_price * 1.06,    # 6% - Take another 1/3
                "target2_size": 0.33,
                "target3": entry_price * 1.12,    # 12% - Exit remaining
                "target3_size": 1.0,
                "stop_loss": entry_price * 0.97,  # 3% stop
                "trailing_stop_pct": 0.02,        # 2% trailing
                "time_exit_hours": 6,
                "breakeven_trigger": 1.015         # Move stop to BE at 1.5% profit
            }
        elif strategy == "trailing":
            return {
                "trailing_stop_pct": 0.03,        # 3% trailing stop
                "initial_stop": entry_price * 0.95, # 5% initial stop
                "time_exit_hours": 8
            }
        else:  # time_based
            return {
                "target": entry_price * 1.05,     # 5% target
                "stop_loss": entry_price * 0.97,  # 3% stop
                "time_exit_hours": 2,              # Quick exit
                "profit_threshold": 0.02           # 2% minimum profit to hold
            }
    
    def _calculate_options_exits(
        self,
        entry_price: float,
        position_type: str,
        strategy: str
    ) -> Dict[str, Any]:
        """Calculate exit levels for options positions."""
        
        # Options are more volatile, use wider targets
        if strategy == "multi_target":
            return {
                "target1": entry_price * 1.25,    # 25% - Take 1/2 off
                "target1_size": 0.5,
                "target2": entry_price * 1.50,    # 50% - Take 1/4 off
                "target2_size": 0.25,
                "target3": entry_price * 2.00,    # 100% - Exit remaining
                "target3_size": 1.0,
                "stop_loss": entry_price * 0.70,  # 30% stop (options decay)
                "trailing_stop_pct": 0.15,        # 15% trailing
                "time_exit_hours": 4,              # Shorter hold for options
                "breakeven_trigger": 1.10,        # Move stop to BE at 10% profit
                "dte_exit": 7                      # Exit if DTE < 7 days
            }
        elif strategy == "trailing":
            return {
                "trailing_stop_pct": 0.20,        # 20% trailing stop
                "initial_stop": entry_price * 0.75, # 25% initial stop
                "time_exit_hours": 6,
                "dte_exit": 10
            }
        else:  # time_based
            return {
                "target": entry_price * 1.30,     # 30% target
                "stop_loss": entry_price * 0.80,  # 20% stop
                "time_exit_hours": 2,              # Very quick for options
                "profit_threshold": 0.10,          # 10% minimum profit
                "dte_exit": 14
            }
    
    async def check_exit_conditions(self, symbol: str, current_price: float) -> Dict[str, Any]:
        """
        Check if any exit conditions are met.
        
        Args:
            symbol: Position symbol
            current_price: Current market price
            
        Returns:
            Exit decision and details
        """
        try:
            if symbol not in self.position_states:
                return {"action": "none", "reason": "Position not tracked"}
            
            state = self.position_states[symbol]
            entry_price = state["entry_price"]
            remaining_qty = state["remaining_quantity"]
            exit_levels = state["exit_levels"]
            strategy = state["strategy"]
            
            # Update position state
            state["last_price"] = current_price
            profit_pct = (current_price - entry_price) / entry_price
            
            # Track max profit/price for trailing stops
            if profit_pct > state["max_profit_seen"]:
                state["max_profit_seen"] = profit_pct
                state["max_price_seen"] = current_price
            
            # Check exit conditions based on strategy
            if strategy == "multi_target":
                return await self._check_multi_target_exits(symbol, current_price, state)
            elif strategy == "trailing":
                return await self._check_trailing_stop_exits(symbol, current_price, state)
            elif strategy == "time_based":
                return await self._check_time_based_exits(symbol, current_price, state)
            
            return {"action": "none", "reason": "No exit conditions met"}
            
        except Exception as e:
            logger.error(f"Error checking exit conditions: {e}")
            return {"action": "none", "error": str(e)}
    
    async def _check_multi_target_exits(
        self,
        symbol: str,
        current_price: float,
        state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Check multi-target exit strategy."""
        
        entry_price = state["entry_price"]
        remaining_qty = state["remaining_quantity"]
        exit_levels = state["exit_levels"]
        exits_executed = state["exits_executed"]
        
        # Check stop loss first
        if current_price <= exit_levels["stop_loss"]:
            return {
                "action": "exit_all",
                "reason": "Stop loss triggered",
                "price": current_price,
                "quantity": remaining_qty,
                "exit_type": "stop_loss"
            }
        
        # Check time-based exit
        time_exit = await self._check_time_exit(state)
        if time_exit["action"] != "none":
            return time_exit
        
        # Check DTE exit for options
        if state["position_type"] in ["call", "put"]:
            dte_exit = await self._check_dte_exit(symbol, state)
            if dte_exit["action"] != "none":
                return dte_exit
        
        # Move stop to breakeven if profitable
        if not state["breakeven_moved"] and current_price >= entry_price * exit_levels.get("breakeven_trigger", 1.05):
            state["breakeven_moved"] = True
            exit_levels["stop_loss"] = entry_price * 1.001  # Just above breakeven
            logger.info(f"📊 {symbol}: Stop moved to breakeven at ${entry_price:.2f}")
        
        # Check profit targets
        if "target1" not in exits_executed and current_price >= exit_levels["target1"]:
            exit_qty = int(state["quantity"] * exit_levels["target1_size"])
            exits_executed.append("target1")
            state["remaining_quantity"] -= exit_qty
            
            # Update trailing stop
            if "trailing_stop_pct" in exit_levels:
                state["trailing_stop"] = current_price * (1 - exit_levels["trailing_stop_pct"])
            
            return {
                "action": "partial_exit",
                "reason": "Target 1 hit - taking partial profits",
                "price": current_price,
                "quantity": exit_qty,
                "remaining": state["remaining_quantity"],
                "exit_type": "target1",
                "profit_pct": (current_price - entry_price) / entry_price * 100
            }
        
        if "target2" not in exits_executed and current_price >= exit_levels["target2"]:
            exit_qty = int(state["quantity"] * exit_levels["target2_size"])
            exits_executed.append("target2")
            state["remaining_quantity"] -= exit_qty
            
            # Tighten trailing stop
            if "trailing_stop_pct" in exit_levels:
                state["trailing_stop"] = current_price * (1 - exit_levels["trailing_stop_pct"] * 0.7)
            
            return {
                "action": "partial_exit",
                "reason": "Target 2 hit - taking more profits",
                "price": current_price,
                "quantity": exit_qty,
                "remaining": state["remaining_quantity"],
                "exit_type": "target2",
                "profit_pct": (current_price - entry_price) / entry_price * 100
            }
        
        if "target3" not in exits_executed and current_price >= exit_levels["target3"]:
            exits_executed.append("target3")
            
            return {
                "action": "exit_all",
                "reason": "Target 3 hit - full exit",
                "price": current_price,
                "quantity": remaining_qty,
                "exit_type": "target3",
                "profit_pct": (current_price - entry_price) / entry_price * 100
            }
        
        # Check trailing stop
        if state["trailing_stop"] and current_price <= state["trailing_stop"]:
            return {
                "action": "exit_all",
                "reason": "Trailing stop triggered",
                "price": current_price,
                "quantity": remaining_qty,
                "exit_type": "trailing_stop",
                "max_profit_seen": state["max_profit_seen"] * 100
            }
        
        # Update trailing stop if in profit
        if state["trailing_stop"] and current_price > state["max_price_seen"]:
            new_trailing = current_price * (1 - exit_levels.get("trailing_stop_pct", 0.05))
            if new_trailing > state["trailing_stop"]:
                state["trailing_stop"] = new_trailing
                logger.debug(f"📊 {symbol}: Trailing stop updated to ${new_trailing:.2f}")
        
        return {"action": "none", "reason": "No exit conditions met"}
    
    async def _check_trailing_stop_exits(
        self,
        symbol: str,
        current_price: float,
        state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Check trailing stop exit strategy."""
        
        exit_levels = state["exit_levels"]
        remaining_qty = state["remaining_quantity"]
        
        # Initialize trailing stop if not set
        if not state["trailing_stop"]:
            if current_price > state["entry_price"]:
                # In profit - start trailing
                state["trailing_stop"] = current_price * (1 - exit_levels["trailing_stop_pct"])
            else:
                # Use initial stop
                state["trailing_stop"] = exit_levels.get("initial_stop", state["entry_price"] * 0.95)
        
        # Check if trailing stop hit
        if current_price <= state["trailing_stop"]:
            return {
                "action": "exit_all",
                "reason": "Trailing stop triggered",
                "price": current_price,
                "quantity": remaining_qty,
                "exit_type": "trailing_stop"
            }
        
        # Update trailing stop if price moved up
        if current_price > state["max_price_seen"]:
            new_trailing = current_price * (1 - exit_levels["trailing_stop_pct"])
            state["trailing_stop"] = max(state["trailing_stop"], new_trailing)
        
        # Check time exit
        return await self._check_time_exit(state)
    
    async def _check_time_based_exits(
        self,
        symbol: str,
        current_price: float,
        state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Check time-based exit strategy."""
        
        entry_price = state["entry_price"]
        remaining_qty = state["remaining_quantity"]
        exit_levels = state["exit_levels"]
        
        # Check stop loss
        if current_price <= exit_levels["stop_loss"]:
            return {
                "action": "exit_all",
                "reason": "Stop loss triggered",
                "price": current_price,
                "quantity": remaining_qty,
                "exit_type": "stop_loss"
            }
        
        # Check profit target
        if current_price >= exit_levels["target"]:
            return {
                "action": "exit_all",
                "reason": "Profit target hit",
                "price": current_price,
                "quantity": remaining_qty,
                "exit_type": "target"
            }
        
        # Check time exit
        return await self._check_time_exit(state)
    
    async def _check_time_exit(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Check if time-based exit should trigger."""
        
        entry_time = state["entry_time"]
        time_limit = timedelta(hours=state["exit_levels"].get("time_exit_hours", 4))
        current_time = datetime.now()
        
        if current_time - entry_time >= time_limit:
            profit_pct = (state["last_price"] - state["entry_price"]) / state["entry_price"]
            min_profit = state["exit_levels"].get("profit_threshold", 0.02)
            
            # Only exit on time if not profitable enough
            if profit_pct < min_profit:
                return {
                    "action": "exit_all",
                    "reason": f"Time exit - held for {time_limit.total_seconds()/3600:.1f}h with {profit_pct*100:.1f}% profit",
                    "price": state["last_price"],
                    "quantity": state["remaining_quantity"],
                    "exit_type": "time_exit"
                }
        
        return {"action": "none"}
    
    async def _check_dte_exit(self, symbol: str, state: Dict[str, Any]) -> Dict[str, Any]:
        """Check if DTE-based exit should trigger for options."""
        
        if state["position_type"] not in ["call", "put"]:
            return {"action": "none"}
        
        dte_threshold = state["exit_levels"].get("dte_exit", 7)
        
        try:
            # Parse option symbol to get expiration (simplified)
            # In real implementation, would parse actual option symbol
            # For now, assume we track DTE separately
            
            # Placeholder - would need actual DTE calculation
            current_dte = 10  # Would get from option symbol parsing
            
            if current_dte <= dte_threshold:
                return {
                    "action": "exit_all",
                    "reason": f"DTE exit - {current_dte} days to expiration",
                    "price": state["last_price"],
                    "quantity": state["remaining_quantity"],
                    "exit_type": "dte_exit"
                }
        
        except Exception as e:
            logger.error(f"Error checking DTE: {e}")
        
        return {"action": "none"}
    
    async def execute_exit(self, exit_decision: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the exit decision."""
        try:
            if exit_decision["action"] == "none":
                return {"success": True, "message": "No exit needed"}
            
            symbol = exit_decision.get("symbol", "")
            quantity = exit_decision["quantity"]
            price = exit_decision["price"]
            reason = exit_decision["reason"]
            
            logger.info(f"🚪 Executing exit: {symbol} - {reason}")
            
            # Execute sell order through enhanced execution service
            from services.enhanced_execution_service import get_enhanced_execution_service
            execution_service = get_enhanced_execution_service()
            
            result = await execution_service.execute_intelligent_order(
                symbol=symbol,
                quantity=quantity,
                side="sell",
                expected_price=price,
                order_type="auto"
            )
            
            if result["success"]:
                # Update position state
                if exit_decision["action"] == "exit_all":
                    # Remove from tracking
                    if symbol in self.position_states:
                        del self.position_states[symbol]
                
                logger.info(f"✅ Exit executed: {symbol} - {reason}")
                
                return {
                    "success": True,
                    "exit_type": exit_decision.get("exit_type", "unknown"),
                    "reason": reason,
                    "quantity": quantity,
                    "price": result.get("fill_price", price),
                    "order_id": result.get("order_id")
                }
            else:
                logger.error(f"❌ Exit failed: {result.get('error')}")
                return {"success": False, "error": result.get("error")}
            
        except Exception as e:
            logger.error(f"Error executing exit: {e}")
            return {"success": False, "error": str(e)}
    
    def get_position_status(self, symbol: str) -> Dict[str, Any]:
        """Get current status of position exits."""
        if symbol not in self.position_states:
            return {"tracked": False}
        
        state = self.position_states[symbol]
        entry_price = state["entry_price"]
        current_price = state["last_price"]
        profit_pct = (current_price - entry_price) / entry_price * 100
        
        return {
            "tracked": True,
            "symbol": symbol,
            "strategy": state["strategy"],
            "entry_price": entry_price,
            "current_price": current_price,
            "profit_pct": profit_pct,
            "remaining_quantity": state["remaining_quantity"],
            "exits_executed": state["exits_executed"],
            "trailing_stop": state.get("trailing_stop"),
            "max_profit_seen": state["max_profit_seen"] * 100,
            "time_held": str(datetime.now() - state["entry_time"]).split(".")[0]
        }


# Singleton instance
_smart_exit_manager = None

def get_smart_exit_manager():
    """Get or create smart exit manager."""
    global _smart_exit_manager
    if _smart_exit_manager is None:
        _smart_exit_manager = SmartExitManager()
    return _smart_exit_manager
