"""
Enhanced Execution Service - Intelligent order routing with limit orders, slippage tracking, and smart exits.
"""
import asyncio
import uuid
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
from loguru import logger
import math

from services import get_alpaca_service, get_database_service
from config import settings


class EnhancedExecutionService:
    """Advanced execution service with intelligent order routing."""
    
    def __init__(self):
        """Initialize the enhanced execution service."""
        self.alpaca = get_alpaca_service()
        self.db = get_database_service()
        self.execution_stats = {}  # Track execution quality
        
    async def execute_intelligent_order(
        self,
        symbol: str,
        quantity: int,
        side: str,
        expected_price: Optional[float] = None,
        order_type: str = "auto",  # auto, market, limit
        timeout_seconds: int = 30,
        extended_hours: bool = False
    ) -> Dict[str, Any]:
        """
        Execute order with intelligent routing.
        
        Args:
            symbol: Stock symbol
            quantity: Quantity to trade
            side: 'buy' or 'sell'
            expected_price: Expected price for slippage calculation
            order_type: 'auto', 'market', or 'limit'
            timeout_seconds: Timeout for limit orders
            extended_hours: Enable extended hours trading
            
        Returns:
            Execution result with fill details
        """
        try:
            logger.info(f"🎯 Intelligent execution: {side} {quantity} {symbol}")
            
            # Get current quote
            quote = await self.alpaca.get_latest_quote(symbol)
            if not quote:
                return {"success": False, "error": "No quote available"}
            
            bid = quote['bid']
            ask = quote['ask']
            mid_price = (bid + ask) / 2 if bid > 0 and ask > 0 else quote['price']
            spread = ask - bid if bid > 0 and ask > 0 else 0
            spread_pct = (spread / mid_price * 100) if mid_price > 0 else 0
            
            # Determine order type if auto
            if order_type == "auto":
                order_type = self._determine_order_type(spread_pct, quantity, symbol)
            
            # Execute based on determined type
            if order_type == "limit":
                result = await self._execute_limit_order(
                    symbol, quantity, side, bid, ask, mid_price, 
                    timeout_seconds, extended_hours
                )
            else:
                result = await self._execute_market_order(
                    symbol, quantity, side, extended_hours
                )
            
            # Track execution quality
            if result['success'] and expected_price:
                await self._track_execution_quality(
                    symbol, side, expected_price, result.get('fill_price', 0),
                    spread_pct, order_type
                )
            
            # Add execution metadata
            result.update({
                "spread_pct": spread_pct,
                "order_type_used": order_type,
                "mid_price": mid_price,
                "extended_hours": extended_hours
            })
            
            return result
            
        except Exception as e:
            logger.error(f"Error in intelligent execution: {e}")
            return {"success": False, "error": str(e)}
    
    def _determine_order_type(self, spread_pct: float, quantity: int, symbol: str) -> str:
        """
        Determine optimal order type based on market conditions.
        
        Args:
            spread_pct: Bid-ask spread percentage
            quantity: Order quantity
            symbol: Stock symbol
            
        Returns:
            'limit' or 'market'
        """
        # Use limit orders for:
        # 1. Wide spreads (>0.5%)
        # 2. Large orders (>$10k)
        # 3. Illiquid stocks
        # 4. Options (always use limit)
        
        if spread_pct > 0.5:
            logger.info(f"📊 Wide spread ({spread_pct:.2f}%) - using LIMIT order")
            return "limit"
        
        # Estimate order value (rough)
        if quantity > 100:  # Large order
            logger.info(f"📊 Large order ({quantity} shares) - using LIMIT order")
            return "limit"
        
        # Check if it's an option symbol
        if len(symbol) > 10:  # Options symbols are longer
            logger.info(f"📊 Options trade - using LIMIT order")
            return "limit"
        
        # Default to market for liquid stocks with tight spreads
        logger.info(f"📊 Tight spread ({spread_pct:.2f}%) - using MARKET order")
        return "market"
    
    async def _execute_limit_order(
        self,
        symbol: str,
        quantity: int,
        side: str,
        bid: float,
        ask: float,
        mid_price: float,
        timeout_seconds: int,
        extended_hours: bool
    ) -> Dict[str, Any]:
        """Execute limit order with intelligent pricing."""
        try:
            # Calculate intelligent limit price
            spread = ask - bid
            
            if side.lower() == "buy":
                # For buys: Start at mid + 30% of spread (aggressive but not market)
                limit_price = mid_price + (spread * 0.3)
                limit_price = min(limit_price, ask)  # Don't exceed ask
            else:
                # For sells: Start at mid - 30% of spread
                limit_price = mid_price - (spread * 0.3)
                limit_price = max(limit_price, bid)  # Don't go below bid
            
            logger.info(f"💰 Limit order: {side} {quantity} {symbol} @ ${limit_price:.2f} (mid: ${mid_price:.2f})")
            
            # Place limit order
            time_in_force = "gtc" if extended_hours else "day"
            order = await self.alpaca.place_limit_order(
                symbol=symbol,
                qty=quantity,
                side=side,
                limit_price=limit_price,
                time_in_force=time_in_force
            )
            
            # Wait for fill with timeout
            fill_result = await self._wait_for_fill(order['id'], timeout_seconds)
            
            if fill_result['filled']:
                return {
                    "success": True,
                    "order_id": order['id'],
                    "fill_price": fill_result['avg_price'],
                    "filled_qty": fill_result['filled_qty'],
                    "order_type": "limit",
                    "limit_price": limit_price
                }
            else:
                # Timeout - cancel and try market order
                logger.warning(f"⏰ Limit order timeout - canceling and using market")
                await self.alpaca.cancel_order(order['id'])
                
                # Fallback to market order
                return await self._execute_market_order(symbol, quantity, side, extended_hours)
                
        except Exception as e:
            logger.error(f"Error executing limit order: {e}")
            # Fallback to market order
            return await self._execute_market_order(symbol, quantity, side, extended_hours)
    
    async def _execute_market_order(
        self,
        symbol: str,
        quantity: int,
        side: str,
        extended_hours: bool
    ) -> Dict[str, Any]:
        """Execute market order."""
        try:
            logger.info(f"🚀 Market order: {side} {quantity} {symbol}")
            
            # Place market order
            time_in_force = "day"  # Market orders are always day
            order = await self.alpaca.place_market_order(
                symbol=symbol,
                qty=quantity,
                side=side,
                time_in_force=time_in_force
            )
            
            # Wait for fill (market orders usually fill quickly)
            fill_result = await self._wait_for_fill(order['id'], 10)  # 10 second timeout
            
            return {
                "success": True,
                "order_id": order['id'],
                "fill_price": fill_result['avg_price'],
                "filled_qty": fill_result['filled_qty'],
                "order_type": "market"
            }
            
        except Exception as e:
            logger.error(f"Error executing market order: {e}")
            return {"success": False, "error": str(e)}
    
    async def _wait_for_fill(self, order_id: str, timeout_seconds: int) -> Dict[str, Any]:
        """
        Wait for order to fill with partial fill handling.
        
        Args:
            order_id: Order ID to monitor
            timeout_seconds: Maximum time to wait
            
        Returns:
            Fill result with partial fill details
        """
        start_time = datetime.now()
        timeout = timedelta(seconds=timeout_seconds)
        last_filled_qty = 0
        partial_fill_timeout = 10  # Seconds to wait for more fills after partial
        
        while datetime.now() - start_time < timeout:
            try:
                order = await self.alpaca.get_order(order_id)
                status = order['status'].lower()
                filled_qty = int(order.get('filled_qty', 0))
                total_qty = int(order['qty'])
                
                if status == 'filled':
                    return {
                        "filled": True,
                        "partial": False,
                        "avg_price": float(order['filled_avg_price']),
                        "filled_qty": filled_qty,
                        "remaining_qty": 0
                    }
                elif status in ['canceled', 'rejected', 'expired']:
                    return {
                        "filled": filled_qty > 0,
                        "partial": filled_qty > 0 and filled_qty < total_qty,
                        "status": status,
                        "filled_qty": filled_qty,
                        "remaining_qty": total_qty - filled_qty,
                        "avg_price": float(order.get('filled_avg_price', 0)) if filled_qty > 0 else 0
                    }
                
                # Handle partial fills
                if filled_qty > 0 and filled_qty < total_qty:
                    if filled_qty > last_filled_qty:
                        # New partial fill
                        last_filled_qty = filled_qty
                        logger.info(f"📊 Partial fill: {filled_qty}/{total_qty} shares ({filled_qty/total_qty*100:.1f}%)")
                        
                        # Wait a bit longer for more fills
                        partial_timeout = datetime.now() + timedelta(seconds=partial_fill_timeout)
                        
                        # Check if we should accept partial fill
                        fill_percentage = filled_qty / total_qty
                        if fill_percentage >= 0.8:  # 80% filled
                            logger.info(f"✅ Accepting partial fill: {fill_percentage*100:.1f}% filled")
                            # Cancel remaining and return partial fill
                            await self.alpaca.cancel_order(order_id)
                            return {
                                "filled": True,
                                "partial": True,
                                "avg_price": float(order['filled_avg_price']),
                                "filled_qty": filled_qty,
                                "remaining_qty": total_qty - filled_qty,
                                "fill_percentage": fill_percentage * 100
                            }
                    
                    # Check if partial fill timeout exceeded
                    if datetime.now() > partial_timeout:
                        fill_percentage = filled_qty / total_qty
                        if fill_percentage >= 0.5:  # At least 50% filled
                            logger.info(f"⏰ Partial fill timeout - accepting {fill_percentage*100:.1f}%")
                            await self.alpaca.cancel_order(order_id)
                            return {
                                "filled": True,
                                "partial": True,
                                "avg_price": float(order['filled_avg_price']),
                                "filled_qty": filled_qty,
                                "remaining_qty": total_qty - filled_qty,
                                "fill_percentage": fill_percentage * 100
                            }
                
                await asyncio.sleep(1)  # Check every second
                
            except Exception as e:
                logger.error(f"Error checking order status: {e}")
                await asyncio.sleep(2)
        
        # Final timeout check
        try:
            order = await self.alpaca.get_order(order_id)
            filled_qty = int(order.get('filled_qty', 0))
            total_qty = int(order['qty'])
            
            if filled_qty > 0:
                # Got partial fill during timeout
                fill_percentage = filled_qty / total_qty
                logger.warning(f"⏰ Order timeout with partial fill: {fill_percentage*100:.1f}%")
                await self.alpaca.cancel_order(order_id)
                return {
                    "filled": True,
                    "partial": True,
                    "status": "timeout_partial",
                    "avg_price": float(order.get('filled_avg_price', 0)),
                    "filled_qty": filled_qty,
                    "remaining_qty": total_qty - filled_qty,
                    "fill_percentage": fill_percentage * 100
                }
        except Exception as e:
            logger.error(f"Error in final timeout check: {e}")
        
        # Complete timeout with no fills
        return {"filled": False, "partial": False, "status": "timeout", "filled_qty": 0, "remaining_qty": 0}
    
    async def handle_partial_fill(
        self,
        symbol: str,
        original_quantity: int,
        filled_quantity: int,
        remaining_quantity: int,
        side: str,
        reason: str = "partial_fill"
    ) -> Dict[str, Any]:
        """
        Handle partial fill by deciding what to do with remaining quantity.
        
        Args:
            symbol: Stock symbol
            original_quantity: Original order quantity
            filled_quantity: Quantity that was filled
            remaining_quantity: Quantity remaining
            side: 'buy' or 'sell'
            reason: Reason for partial fill
            
        Returns:
            Action decision for remaining quantity
        """
        try:
            fill_percentage = filled_quantity / original_quantity * 100
            
            logger.info(f"🔄 Handling partial fill: {symbol} - {filled_quantity}/{original_quantity} ({fill_percentage:.1f}%)")
            
            # Decision logic for remaining quantity
            if fill_percentage >= 90:
                # 90%+ filled - don't bother with remainder
                decision = "accept_partial"
                action = "none"
                
            elif fill_percentage >= 70:
                # 70-90% filled - try to fill remainder with market order
                decision = "fill_remainder_market"
                action = "market_order"
                
            elif fill_percentage >= 50:
                # 50-70% filled - try to fill remainder with limit order
                decision = "fill_remainder_limit"
                action = "limit_order"
                
            elif fill_percentage >= 25:
                # 25-50% filled - reassess position size
                decision = "reassess_position"
                action = "recalculate"
                
            else:
                # <25% filled - likely cancel and retry
                decision = "cancel_and_retry"
                action = "retry"
            
            # Execute decision
            result = {"decision": decision, "action": action, "fill_percentage": fill_percentage}
            
            if action == "market_order":
                # Submit market order for remainder
                market_result = await self.execute_intelligent_order(
                    symbol=symbol,
                    quantity=remaining_quantity,
                    side=side,
                    order_type="market"
                )
                result["market_order_result"] = market_result
                
            elif action == "limit_order":
                # Submit limit order for remainder
                limit_result = await self.execute_intelligent_order(
                    symbol=symbol,
                    quantity=remaining_quantity,
                    side=side,
                    order_type="limit",
                    timeout_seconds=60
                )
                result["limit_order_result"] = limit_result
                
            elif action == "recalculate":
                # Adjust position size based on what we got
                result["suggested_adjustment"] = f"Reduce position size expectations by {100-fill_percentage:.1f}%"
                
            elif action == "retry":
                # Would retry original order (implementation depends on strategy)
                result["retry_recommended"] = True
            
            logger.info(f"📋 Partial fill decision: {decision} for {symbol}")
            return result
            
        except Exception as e:
            logger.error(f"Error handling partial fill: {e}")
            return {"decision": "error", "error": str(e)}
    
    async def _track_execution_quality(
        self,
        symbol: str,
        side: str,
        expected_price: float,
        actual_price: float,
        spread_pct: float,
        order_type: str
    ):
        """Track execution quality metrics."""
        try:
            slippage = actual_price - expected_price if side == "buy" else expected_price - actual_price
            slippage_pct = (slippage / expected_price * 100) if expected_price > 0 else 0
            
            # Store in execution stats
            if symbol not in self.execution_stats:
                self.execution_stats[symbol] = {
                    "trades": 0,
                    "total_slippage": 0,
                    "total_slippage_pct": 0,
                    "limit_orders": 0,
                    "market_orders": 0
                }
            
            stats = self.execution_stats[symbol]
            stats["trades"] += 1
            stats["total_slippage"] += abs(slippage)
            stats["total_slippage_pct"] += abs(slippage_pct)
            
            if order_type == "limit":
                stats["limit_orders"] += 1
            else:
                stats["market_orders"] += 1
            
            # Log execution quality
            logger.info(
                f"📊 Execution: {symbol} {side} - "
                f"Expected: ${expected_price:.2f}, Actual: ${actual_price:.2f}, "
                f"Slippage: {slippage:+.2f} ({slippage_pct:+.2f}%), "
                f"Spread: {spread_pct:.2f}%, Type: {order_type}"
            )
            
            # Alert on high slippage
            if abs(slippage_pct) > 1.0:
                logger.warning(f"⚠️ High slippage detected: {slippage_pct:.2f}% on {symbol}")
            
        except Exception as e:
            logger.error(f"Error tracking execution quality: {e}")
    
    async def get_execution_stats(self, symbol: Optional[str] = None) -> Dict[str, Any]:
        """Get execution quality statistics."""
        if symbol:
            stats = self.execution_stats.get(symbol, {})
            if stats and stats["trades"] > 0:
                return {
                    "symbol": symbol,
                    "trades": stats["trades"],
                    "avg_slippage": stats["total_slippage"] / stats["trades"],
                    "avg_slippage_pct": stats["total_slippage_pct"] / stats["trades"],
                    "limit_order_pct": (stats["limit_orders"] / stats["trades"] * 100),
                    "market_order_pct": (stats["market_orders"] / stats["trades"] * 100)
                }
            return {"symbol": symbol, "trades": 0}
        
        # Overall stats
        total_trades = sum(s["trades"] for s in self.execution_stats.values())
        if total_trades == 0:
            return {"total_trades": 0}
        
        total_slippage = sum(s["total_slippage"] for s in self.execution_stats.values())
        total_slippage_pct = sum(s["total_slippage_pct"] for s in self.execution_stats.values())
        total_limit = sum(s["limit_orders"] for s in self.execution_stats.values())
        
        return {
            "total_trades": total_trades,
            "avg_slippage": total_slippage / total_trades,
            "avg_slippage_pct": total_slippage_pct / total_trades,
            "limit_order_pct": (total_limit / total_trades * 100),
            "symbols_traded": len(self.execution_stats)
        }


# Singleton instance
_enhanced_execution_service = None

def get_enhanced_execution_service():
    """Get or create enhanced execution service."""
    global _enhanced_execution_service
    if _enhanced_execution_service is None:
        _enhanced_execution_service = EnhancedExecutionService()
    return _enhanced_execution_service
