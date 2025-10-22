"""
Order Batch Manager - Queue and batch orders for efficient execution.
"""
import asyncio
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from loguru import logger
import uuid

from services.enhanced_execution_service import get_enhanced_execution_service


class OrderBatchManager:
    """Manage order batching and queuing for efficient execution."""
    
    def __init__(self):
        """Initialize order batch manager."""
        self.execution_service = get_enhanced_execution_service()
        self.order_queue = []
        self.batch_config = {
            "max_batch_size": 5,
            "batch_timeout_seconds": 10,
            "min_batch_size": 2
        }
        self.processing = False
        self.batch_stats = {
            "batches_processed": 0,
            "orders_processed": 0,
            "avg_batch_size": 0,
            "last_batch_time": None
        }
        
        # Start batch processor
        asyncio.create_task(self._batch_processor())
    
    async def queue_order(
        self,
        symbol: str,
        quantity: int,
        side: str,
        order_type: str = "auto",
        expected_price: Optional[float] = None,
        priority: str = "normal",  # high, normal, low
        max_wait_seconds: int = 60,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Queue an order for batch execution.
        
        Args:
            symbol: Stock symbol
            quantity: Order quantity
            side: 'buy' or 'sell'
            order_type: Order type
            expected_price: Expected price
            priority: Order priority
            max_wait_seconds: Maximum time to wait in queue
            metadata: Additional order metadata
            
        Returns:
            Queue result with order ID
        """
        try:
            order_id = str(uuid.uuid4())
            
            order = {
                "order_id": order_id,
                "symbol": symbol,
                "quantity": quantity,
                "side": side,
                "order_type": order_type,
                "expected_price": expected_price,
                "priority": priority,
                "max_wait_seconds": max_wait_seconds,
                "metadata": metadata or {},
                "queued_time": datetime.now(),
                "status": "queued"
            }
            
            # Insert based on priority
            if priority == "high":
                self.order_queue.insert(0, order)  # Front of queue
            else:
                self.order_queue.append(order)  # Back of queue
            
            logger.info(f"📋 Order queued: {order_id} - {side} {quantity} {symbol} (priority: {priority})")
            
            return {
                "success": True,
                "order_id": order_id,
                "queue_position": len(self.order_queue),
                "estimated_wait_seconds": self._estimate_wait_time()
            }
            
        except Exception as e:
            logger.error(f"Error queuing order: {e}")
            return {"success": False, "error": str(e)}
    
    async def _batch_processor(self):
        """Main batch processing loop."""
        while True:
            try:
                if not self.processing and self.order_queue:
                    await self._process_batch()
                
                await asyncio.sleep(1)  # Check every second
                
            except Exception as e:
                logger.error(f"Error in batch processor: {e}")
                await asyncio.sleep(5)  # Wait before retrying
    
    async def _process_batch(self):
        """Process a batch of orders."""
        if self.processing or not self.order_queue:
            return
        
        self.processing = True
        
        try:
            # Remove expired orders
            await self._remove_expired_orders()
            
            if not self.order_queue:
                self.processing = False
                return
            
            # Determine batch size
            batch_size = min(
                len(self.order_queue),
                self.batch_config["max_batch_size"]
            )
            
            # Wait for minimum batch size or timeout
            if batch_size < self.batch_config["min_batch_size"]:
                oldest_order = min(self.order_queue, key=lambda x: x["queued_time"])
                wait_time = (datetime.now() - oldest_order["queued_time"]).total_seconds()
                
                if wait_time < self.batch_config["batch_timeout_seconds"]:
                    self.processing = False
                    return  # Wait for more orders or timeout
            
            # Extract batch
            batch = self.order_queue[:batch_size]
            self.order_queue = self.order_queue[batch_size:]
            
            logger.info(f"🚀 Processing batch of {len(batch)} orders")
            
            # Group orders by symbol for better execution
            symbol_groups = self._group_orders_by_symbol(batch)
            
            # Execute batches
            batch_results = []
            for symbol, orders in symbol_groups.items():
                group_results = await self._execute_symbol_group(symbol, orders)
                batch_results.extend(group_results)
            
            # Update statistics
            self._update_batch_stats(len(batch))
            
            logger.info(f"✅ Batch completed: {len(batch)} orders processed")
            
        except Exception as e:
            logger.error(f"Error processing batch: {e}")
            # Return orders to queue on error
            for order in batch:
                order["status"] = "error"
                self.order_queue.insert(0, order)
        
        finally:
            self.processing = False
    
    def _group_orders_by_symbol(self, orders: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Group orders by symbol for efficient execution."""
        groups = {}
        
        for order in orders:
            symbol = order["symbol"]
            if symbol not in groups:
                groups[symbol] = []
            groups[symbol].append(order)
        
        return groups
    
    async def _execute_symbol_group(self, symbol: str, orders: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Execute a group of orders for the same symbol."""
        results = []
        
        # Sort by priority and side for optimal execution
        orders.sort(key=lambda x: (
            0 if x["priority"] == "high" else 1 if x["priority"] == "normal" else 2,
            0 if x["side"] == "buy" else 1
        ))
        
        logger.info(f"📊 Executing {len(orders)} orders for {symbol}")
        
        # Check if we can net orders (buy vs sell)
        net_result = self._calculate_net_position(orders)
        
        if net_result["can_net"] and len(orders) > 1:
            # Execute net position
            result = await self._execute_net_orders(symbol, orders, net_result)
            results.append(result)
        else:
            # Execute orders individually but in quick succession
            for order in orders:
                result = await self._execute_single_order(order)
                results.append(result)
                
                # Small delay between orders to avoid overwhelming the system
                await asyncio.sleep(0.1)
        
        return results
    
    def _calculate_net_position(self, orders: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate net position from a group of orders."""
        buy_quantity = sum(o["quantity"] for o in orders if o["side"] == "buy")
        sell_quantity = sum(o["quantity"] for o in orders if o["side"] == "sell")
        
        net_quantity = buy_quantity - sell_quantity
        net_side = "buy" if net_quantity > 0 else "sell"
        net_quantity = abs(net_quantity)
        
        # Only net if we have both buys and sells and the net is significant
        can_net = (buy_quantity > 0 and sell_quantity > 0 and 
                  net_quantity < min(buy_quantity, sell_quantity) * 0.8)
        
        return {
            "can_net": can_net,
            "net_quantity": net_quantity,
            "net_side": net_side,
            "buy_quantity": buy_quantity,
            "sell_quantity": sell_quantity
        }
    
    async def _execute_net_orders(
        self,
        symbol: str,
        orders: List[Dict[str, Any]],
        net_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute netted orders."""
        try:
            logger.info(f"🔄 Netting {len(orders)} orders for {symbol}: {net_result['net_quantity']} {net_result['net_side']}")
            
            if net_result["net_quantity"] == 0:
                # Perfect net - no execution needed
                return {
                    "success": True,
                    "type": "netted_zero",
                    "orders_netted": len(orders),
                    "message": "Orders perfectly netted - no execution needed"
                }
            
            # Execute net position
            avg_price = sum(o.get("expected_price", 0) for o in orders) / len(orders)
            
            result = await self.execution_service.execute_intelligent_order(
                symbol=symbol,
                quantity=net_result["net_quantity"],
                side=net_result["net_side"],
                expected_price=avg_price,
                order_type="auto"
            )
            
            result.update({
                "type": "netted_execution",
                "orders_netted": len(orders),
                "original_buy_qty": net_result["buy_quantity"],
                "original_sell_qty": net_result["sell_quantity"]
            })
            
            return result
            
        except Exception as e:
            logger.error(f"Error executing net orders: {e}")
            return {"success": False, "error": str(e), "type": "netted_execution"}
    
    async def _execute_single_order(self, order: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single order."""
        try:
            order["status"] = "executing"
            
            result = await self.execution_service.execute_intelligent_order(
                symbol=order["symbol"],
                quantity=order["quantity"],
                side=order["side"],
                expected_price=order.get("expected_price"),
                order_type=order["order_type"]
            )
            
            result.update({
                "order_id": order["order_id"],
                "type": "individual_execution",
                "queue_time_seconds": (datetime.now() - order["queued_time"]).total_seconds()
            })
            
            order["status"] = "completed" if result["success"] else "failed"
            
            return result
            
        except Exception as e:
            logger.error(f"Error executing single order: {e}")
            order["status"] = "failed"
            return {
                "success": False,
                "error": str(e),
                "order_id": order["order_id"],
                "type": "individual_execution"
            }
    
    async def _remove_expired_orders(self):
        """Remove orders that have exceeded their max wait time."""
        current_time = datetime.now()
        expired_orders = []
        
        for i, order in enumerate(self.order_queue):
            wait_time = (current_time - order["queued_time"]).total_seconds()
            if wait_time > order["max_wait_seconds"]:
                expired_orders.append(i)
        
        # Remove expired orders (in reverse order to maintain indices)
        for i in reversed(expired_orders):
            expired_order = self.order_queue.pop(i)
            logger.warning(f"⏰ Order expired: {expired_order['order_id']} - waited {wait_time:.1f}s")
    
    def _estimate_wait_time(self) -> int:
        """Estimate wait time for new orders."""
        if not self.order_queue:
            return 0
        
        # Simple estimation based on queue size and batch processing rate
        queue_size = len(self.order_queue)
        batch_size = self.batch_config["max_batch_size"]
        batch_interval = self.batch_config["batch_timeout_seconds"]
        
        estimated_batches = (queue_size + batch_size - 1) // batch_size  # Ceiling division
        estimated_wait = estimated_batches * batch_interval
        
        return min(estimated_wait, 60)  # Cap at 60 seconds
    
    def _update_batch_stats(self, batch_size: int):
        """Update batch processing statistics."""
        self.batch_stats["batches_processed"] += 1
        self.batch_stats["orders_processed"] += batch_size
        self.batch_stats["avg_batch_size"] = (
            self.batch_stats["orders_processed"] / self.batch_stats["batches_processed"]
        )
        self.batch_stats["last_batch_time"] = datetime.now()
    
    def get_queue_status(self) -> Dict[str, Any]:
        """Get current queue status."""
        return {
            "queue_length": len(self.order_queue),
            "processing": self.processing,
            "estimated_wait_seconds": self._estimate_wait_time(),
            "batch_config": self.batch_config,
            "stats": self.batch_stats,
            "orders_by_priority": {
                "high": sum(1 for o in self.order_queue if o["priority"] == "high"),
                "normal": sum(1 for o in self.order_queue if o["priority"] == "normal"),
                "low": sum(1 for o in self.order_queue if o["priority"] == "low")
            },
            "orders_by_symbol": self._get_symbol_breakdown()
        }
    
    def _get_symbol_breakdown(self) -> Dict[str, int]:
        """Get breakdown of orders by symbol."""
        symbol_counts = {}
        for order in self.order_queue:
            symbol = order["symbol"]
            symbol_counts[symbol] = symbol_counts.get(symbol, 0) + 1
        return symbol_counts
    
    async def cancel_queued_order(self, order_id: str) -> Dict[str, Any]:
        """Cancel a queued order."""
        try:
            for i, order in enumerate(self.order_queue):
                if order["order_id"] == order_id:
                    cancelled_order = self.order_queue.pop(i)
                    logger.info(f"🚫 Cancelled queued order: {order_id}")
                    return {
                        "success": True,
                        "order_id": order_id,
                        "was_queued": True,
                        "queue_time": (datetime.now() - cancelled_order["queued_time"]).total_seconds()
                    }
            
            return {"success": False, "error": "Order not found in queue"}
            
        except Exception as e:
            logger.error(f"Error cancelling queued order: {e}")
            return {"success": False, "error": str(e)}
    
    def configure_batching(
        self,
        max_batch_size: Optional[int] = None,
        batch_timeout_seconds: Optional[int] = None,
        min_batch_size: Optional[int] = None
    ) -> Dict[str, Any]:
        """Configure batch processing parameters."""
        if max_batch_size is not None:
            self.batch_config["max_batch_size"] = max_batch_size
        if batch_timeout_seconds is not None:
            self.batch_config["batch_timeout_seconds"] = batch_timeout_seconds
        if min_batch_size is not None:
            self.batch_config["min_batch_size"] = min_batch_size
        
        logger.info(f"📋 Batch configuration updated: {self.batch_config}")
        
        return {
            "success": True,
            "config": self.batch_config
        }


# Singleton instance
_order_batch_manager = None

def get_order_batch_manager():
    """Get or create order batch manager."""
    global _order_batch_manager
    if _order_batch_manager is None:
        _order_batch_manager = OrderBatchManager()
    return _order_batch_manager
