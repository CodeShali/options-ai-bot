"""
Entry Strategy Manager - Smart position entry with scaling and timing strategies.
"""
import asyncio
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from loguru import logger
import math

from services import get_alpaca_service
from services.enhanced_execution_service import get_enhanced_execution_service
from config import settings


class EntryStrategyManager:
    """Manage intelligent entry strategies for positions."""
    
    def __init__(self):
        """Initialize entry strategy manager."""
        self.alpaca = get_alpaca_service()
        self.execution_service = get_enhanced_execution_service()
        self.active_entries = {}  # Track active entry strategies
        
    async def execute_smart_entry(
        self,
        symbol: str,
        total_quantity: int,
        side: str,
        entry_price: float,
        strategy: str = "scale_in",  # scale_in, time_weighted, breakout_confirmation
        confidence: float = 75.0,
        volatility: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Execute smart entry strategy.
        
        Args:
            symbol: Stock symbol
            total_quantity: Total desired position size
            side: 'buy' or 'sell'
            entry_price: Target entry price
            strategy: Entry strategy type
            confidence: Signal confidence (0-100)
            volatility: Stock volatility (ATR %)
            
        Returns:
            Entry execution plan and results
        """
        try:
            logger.info(f"🎯 Smart entry: {strategy} for {total_quantity} {symbol} @ ${entry_price:.2f}")
            
            # Create entry plan based on strategy
            if strategy == "scale_in":
                plan = self._create_scale_in_plan(
                    symbol, total_quantity, side, entry_price, confidence, volatility
                )
            elif strategy == "time_weighted":
                plan = self._create_time_weighted_plan(
                    symbol, total_quantity, side, entry_price, confidence
                )
            elif strategy == "breakout_confirmation":
                plan = self._create_breakout_confirmation_plan(
                    symbol, total_quantity, side, entry_price, confidence
                )
            else:
                # Default: immediate full entry
                plan = self._create_immediate_entry_plan(
                    symbol, total_quantity, side, entry_price
                )
            
            # Store active entry
            entry_id = f"{symbol}_{side}_{datetime.now().timestamp()}"
            self.active_entries[entry_id] = {
                "symbol": symbol,
                "strategy": strategy,
                "plan": plan,
                "total_quantity": total_quantity,
                "filled_quantity": 0,
                "remaining_quantity": total_quantity,
                "start_time": datetime.now(),
                "status": "active",
                "executions": []
            }
            
            # Execute first entry
            first_result = await self._execute_entry_step(entry_id, 0)
            
            return {
                "success": True,
                "entry_id": entry_id,
                "strategy": strategy,
                "plan": plan,
                "first_execution": first_result
            }
            
        except Exception as e:
            logger.error(f"Error executing smart entry: {e}")
            return {"success": False, "error": str(e)}
    
    def _create_scale_in_plan(
        self,
        symbol: str,
        total_quantity: int,
        side: str,
        entry_price: float,
        confidence: float,
        volatility: Optional[float]
    ) -> List[Dict[str, Any]]:
        """Create scale-in entry plan."""
        
        # Determine number of entries based on confidence and volatility
        if confidence >= 85:
            # High confidence - fewer entries, larger initial size
            entries = 2
            initial_pct = 0.7  # 70% immediately
        elif confidence >= 70:
            # Medium confidence - moderate scaling
            entries = 3
            initial_pct = 0.5  # 50% immediately
        else:
            # Lower confidence - more cautious scaling
            entries = 4
            initial_pct = 0.3  # 30% immediately
        
        # Adjust for volatility
        if volatility and volatility > 0.03:  # High volatility (>3% ATR)
            entries += 1  # More entries for volatile stocks
            initial_pct *= 0.8  # Smaller initial size
        
        # Calculate entry sizes
        remaining_pct = 1.0 - initial_pct
        subsequent_pct = remaining_pct / (entries - 1) if entries > 1 else 0
        
        plan = []
        
        # Entry 1: Immediate
        plan.append({
            "step": 1,
            "quantity": int(total_quantity * initial_pct),
            "price_target": entry_price,
            "price_tolerance": 0.002,  # 0.2% tolerance
            "timing": "immediate",
            "order_type": "limit",
            "timeout_seconds": 30
        })
        
        # Subsequent entries
        for i in range(1, entries):
            # Scale-in on pullbacks (for buys) or bounces (for sells)
            if side.lower() == "buy":
                # Buy more on pullbacks
                price_target = entry_price * (1 - 0.01 * i)  # 1% lower each step
            else:
                # Sell more on bounces
                price_target = entry_price * (1 + 0.01 * i)  # 1% higher each step
            
            plan.append({
                "step": i + 1,
                "quantity": int(total_quantity * subsequent_pct),
                "price_target": price_target,
                "price_tolerance": 0.005,  # 0.5% tolerance for scale-ins
                "timing": "conditional",
                "condition": "pullback" if side.lower() == "buy" else "bounce",
                "order_type": "limit",
                "timeout_seconds": 300,  # 5 minutes
                "max_wait_minutes": 30
            })
        
        return plan
    
    def _create_time_weighted_plan(
        self,
        symbol: str,
        total_quantity: int,
        side: str,
        entry_price: float,
        confidence: float
    ) -> List[Dict[str, Any]]:
        """Create time-weighted entry plan (TWAP-style)."""
        
        # Determine time window based on confidence
        if confidence >= 80:
            time_window_minutes = 15  # Quick entry for high confidence
            entries = 3
        else:
            time_window_minutes = 30  # Slower entry for lower confidence
            entries = 5
        
        interval_minutes = time_window_minutes / entries
        quantity_per_entry = total_quantity // entries
        remainder = total_quantity % entries
        
        plan = []
        current_time = datetime.now()
        
        for i in range(entries):
            quantity = quantity_per_entry
            if i == entries - 1:  # Last entry gets remainder
                quantity += remainder
            
            plan.append({
                "step": i + 1,
                "quantity": quantity,
                "price_target": entry_price,
                "price_tolerance": 0.003,  # 0.3% tolerance
                "timing": "scheduled",
                "scheduled_time": current_time + timedelta(minutes=i * interval_minutes),
                "order_type": "limit",
                "timeout_seconds": 60
            })
        
        return plan
    
    def _create_breakout_confirmation_plan(
        self,
        symbol: str,
        total_quantity: int,
        side: str,
        entry_price: float,
        confidence: float
    ) -> List[Dict[str, Any]]:
        """Create breakout confirmation entry plan."""
        
        plan = []
        
        # Entry 1: Small position on initial signal
        plan.append({
            "step": 1,
            "quantity": int(total_quantity * 0.25),  # 25% initial
            "price_target": entry_price,
            "price_tolerance": 0.002,
            "timing": "immediate",
            "order_type": "limit",
            "timeout_seconds": 30
        })
        
        # Entry 2: Larger position on confirmation
        if side.lower() == "buy":
            confirmation_price = entry_price * 1.005  # 0.5% above entry
        else:
            confirmation_price = entry_price * 0.995  # 0.5% below entry
        
        plan.append({
            "step": 2,
            "quantity": int(total_quantity * 0.5),  # 50% on confirmation
            "price_target": confirmation_price,
            "price_tolerance": 0.003,
            "timing": "conditional",
            "condition": "breakout_confirmation",
            "order_type": "market",  # Market order for momentum
            "max_wait_minutes": 15
        })
        
        # Entry 3: Final position on strong momentum
        if side.lower() == "buy":
            momentum_price = entry_price * 1.01  # 1% above entry
        else:
            momentum_price = entry_price * 0.99  # 1% below entry
        
        plan.append({
            "step": 3,
            "quantity": int(total_quantity * 0.25),  # Remaining 25%
            "price_target": momentum_price,
            "price_tolerance": 0.005,
            "timing": "conditional",
            "condition": "strong_momentum",
            "order_type": "market",
            "max_wait_minutes": 10
        })
        
        return plan
    
    def _create_immediate_entry_plan(
        self,
        symbol: str,
        total_quantity: int,
        side: str,
        entry_price: float
    ) -> List[Dict[str, Any]]:
        """Create immediate full entry plan."""
        
        return [{
            "step": 1,
            "quantity": total_quantity,
            "price_target": entry_price,
            "price_tolerance": 0.002,
            "timing": "immediate",
            "order_type": "auto",  # Let execution service decide
            "timeout_seconds": 30
        }]
    
    async def _execute_entry_step(self, entry_id: str, step_index: int) -> Dict[str, Any]:
        """Execute a specific entry step."""
        try:
            if entry_id not in self.active_entries:
                return {"success": False, "error": "Entry not found"}
            
            entry = self.active_entries[entry_id]
            plan = entry["plan"]
            
            if step_index >= len(plan):
                return {"success": False, "error": "Step index out of range"}
            
            step = plan[step_index]
            symbol = entry["symbol"]
            
            logger.info(f"📊 Executing entry step {step['step']} for {symbol}")
            
            # Check timing conditions
            if step["timing"] == "scheduled":
                scheduled_time = step["scheduled_time"]
                if datetime.now() < scheduled_time:
                    # Schedule for later
                    delay = (scheduled_time - datetime.now()).total_seconds()
                    asyncio.create_task(self._delayed_execution(entry_id, step_index, delay))
                    return {"success": True, "status": "scheduled", "delay_seconds": delay}
            
            elif step["timing"] == "conditional":
                # Check if condition is met
                condition_met = await self._check_entry_condition(entry_id, step)
                if not condition_met:
                    return {"success": True, "status": "waiting_for_condition"}
            
            # Execute the order
            result = await self.execution_service.execute_intelligent_order(
                symbol=symbol,
                quantity=step["quantity"],
                side="buy",  # Assuming buy for now
                expected_price=step["price_target"],
                order_type=step["order_type"],
                timeout_seconds=step.get("timeout_seconds", 30)
            )
            
            # Update entry tracking
            if result["success"]:
                filled_qty = result.get("filled_qty", step["quantity"])
                entry["filled_quantity"] += filled_qty
                entry["remaining_quantity"] -= filled_qty
                
                execution_record = {
                    "step": step["step"],
                    "quantity": filled_qty,
                    "price": result.get("fill_price", step["price_target"]),
                    "timestamp": datetime.now(),
                    "order_id": result.get("order_id")
                }
                entry["executions"].append(execution_record)
                
                logger.info(f"✅ Entry step {step['step']} completed: {filled_qty} shares @ ${result.get('fill_price', 0):.2f}")
                
                # Check if entry is complete
                if entry["remaining_quantity"] <= 0:
                    entry["status"] = "completed"
                    logger.info(f"🎉 Entry strategy completed for {symbol}")
                else:
                    # Schedule next step if applicable
                    next_step_index = step_index + 1
                    if next_step_index < len(plan):
                        asyncio.create_task(self._execute_next_step(entry_id, next_step_index))
            
            return result
            
        except Exception as e:
            logger.error(f"Error executing entry step: {e}")
            return {"success": False, "error": str(e)}
    
    async def _delayed_execution(self, entry_id: str, step_index: int, delay_seconds: float):
        """Execute entry step after delay."""
        await asyncio.sleep(delay_seconds)
        await self._execute_entry_step(entry_id, step_index)
    
    async def _execute_next_step(self, entry_id: str, step_index: int):
        """Execute next entry step with appropriate delay."""
        # Small delay to avoid rapid-fire orders
        await asyncio.sleep(2)
        await self._execute_entry_step(entry_id, step_index)
    
    async def _check_entry_condition(self, entry_id: str, step: Dict[str, Any]) -> bool:
        """Check if entry condition is met."""
        try:
            entry = self.active_entries[entry_id]
            symbol = entry["symbol"]
            condition = step["condition"]
            
            # Get current price
            quote = await self.alpaca.get_latest_quote(symbol)
            if not quote:
                return False
            
            current_price = quote["price"]
            target_price = step["price_target"]
            
            if condition == "pullback":
                # For buys: price pulled back to or below target
                return current_price <= target_price * (1 + step.get("price_tolerance", 0.005))
            
            elif condition == "bounce":
                # For sells: price bounced to or above target
                return current_price >= target_price * (1 - step.get("price_tolerance", 0.005))
            
            elif condition == "breakout_confirmation":
                # Price moved in favorable direction
                return current_price >= target_price
            
            elif condition == "strong_momentum":
                # Strong price movement (simplified)
                return current_price >= target_price
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking entry condition: {e}")
            return False
    
    def get_entry_status(self, entry_id: str) -> Dict[str, Any]:
        """Get status of entry strategy."""
        if entry_id not in self.active_entries:
            return {"found": False}
        
        entry = self.active_entries[entry_id]
        
        # Calculate progress
        total_qty = entry["total_quantity"]
        filled_qty = entry["filled_quantity"]
        progress_pct = (filled_qty / total_qty * 100) if total_qty > 0 else 0
        
        # Calculate average fill price
        executions = entry["executions"]
        if executions:
            total_value = sum(ex["quantity"] * ex["price"] for ex in executions)
            total_shares = sum(ex["quantity"] for ex in executions)
            avg_price = total_value / total_shares if total_shares > 0 else 0
        else:
            avg_price = 0
        
        return {
            "found": True,
            "entry_id": entry_id,
            "symbol": entry["symbol"],
            "strategy": entry["strategy"],
            "status": entry["status"],
            "progress_pct": progress_pct,
            "total_quantity": total_qty,
            "filled_quantity": filled_qty,
            "remaining_quantity": entry["remaining_quantity"],
            "avg_fill_price": avg_price,
            "executions_count": len(executions),
            "time_elapsed": str(datetime.now() - entry["start_time"]).split(".")[0],
            "executions": executions
        }
    
    def get_all_active_entries(self) -> List[Dict[str, Any]]:
        """Get all active entry strategies."""
        return [
            self.get_entry_status(entry_id)
            for entry_id in self.active_entries
            if self.active_entries[entry_id]["status"] == "active"
        ]
    
    async def cancel_entry_strategy(self, entry_id: str) -> Dict[str, Any]:
        """Cancel an active entry strategy."""
        try:
            if entry_id not in self.active_entries:
                return {"success": False, "error": "Entry not found"}
            
            entry = self.active_entries[entry_id]
            entry["status"] = "cancelled"
            
            logger.info(f"🚫 Entry strategy cancelled: {entry_id}")
            
            return {
                "success": True,
                "entry_id": entry_id,
                "filled_quantity": entry["filled_quantity"],
                "cancelled_quantity": entry["remaining_quantity"]
            }
            
        except Exception as e:
            logger.error(f"Error cancelling entry strategy: {e}")
            return {"success": False, "error": str(e)}


# Singleton instance
_entry_strategy_manager = None

def get_entry_strategy_manager():
    """Get or create entry strategy manager."""
    global _entry_strategy_manager
    if _entry_strategy_manager is None:
        _entry_strategy_manager = EntryStrategyManager()
    return _entry_strategy_manager
