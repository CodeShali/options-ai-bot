"""
Execution Agent - Executes trades through Alpaca API.
"""
import asyncio
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime
from loguru import logger

from agents.base_agent import BaseAgent
from services import get_alpaca_service, get_database_service


class ExecutionAgent(BaseAgent):
    """Agent responsible for trade execution."""
    
    def __init__(self):
        """Initialize the execution agent."""
        super().__init__("Execution")
        self.alpaca = get_alpaca_service()
        self.db = get_database_service()
    
    async def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process execution request.
        
        Args:
            data: Request data with 'action' and trade details
            
        Returns:
            Execution result
        """
        action = data.get("action")
        
        if action == "execute_buy":
            trade = data.get("trade")
            return await self.execute_buy(trade)
        elif action == "execute_sell":
            symbol = data.get("symbol")
            quantity = data.get("quantity")
            reason = data.get("reason", "Manual sell")
            return await self.execute_sell(symbol, quantity, reason)
        elif action == "close_position":
            symbol = data.get("symbol")
            reason = data.get("reason", "Position close")
            return await self.close_position(symbol, reason)
        elif action == "close_all_positions":
            reason = data.get("reason", "Close all")
            return await self.close_all_positions(reason)
        else:
            return {"error": f"Unknown action: {action}"}
    
    async def execute_buy(self, trade: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a buy order with enhanced execution.
        
        Args:
            trade: Trade details with symbol, quantity, price, etc.
            
        Returns:
            Execution result
        """
        try:
            from services.enhanced_execution_service import get_enhanced_execution_service
            from services.execution_cost_analyzer import get_execution_cost_analyzer
            from services.smart_exit_manager import get_smart_exit_manager
            from services.retry_handler import get_retry_handler
            
            symbol = trade['symbol']
            quantity = trade['quantity']
            expected_price = trade.get('price', 0)
            
            logger.info(f"🚀 Enhanced BUY execution: {quantity} {symbol} @ ${expected_price:.2f}")
            
            # Use enhanced execution service
            execution_service = get_enhanced_execution_service()
            retry_handler = get_retry_handler()
            
            # Execute with retry logic
            result = await retry_handler.retry_order_execution(
                execution_service.execute_intelligent_order,
                symbol=symbol,
                quantity=quantity,
                side="buy",
                expected_price=expected_price,
                order_type="auto"
            )
            
            if not result["success"]:
                return {
                    "success": False,
                    "error": result.get("error", "Unknown error"),
                    "symbol": symbol,
                    "attempts": result.get("attempts", 1)
                }
            
            # Extract execution details
            execution_result = result["result"]
            fill_price = execution_result.get("fill_price", expected_price)
            filled_qty = execution_result.get("filled_qty", quantity)
            
            # Generate trade ID
            trade_id = str(uuid.uuid4())
            
            # Record trade in database
            await self.db.record_trade(
                trade_id=trade_id,
                symbol=symbol,
                action="buy",
                quantity=filled_qty,
                price=fill_price,
                order_id=execution_result.get("order_id", ""),
                status="filled",
                notes=f"Enhanced execution - {execution_result.get('order_type_used', 'auto')}"
            )
            
            # Analyze execution cost
            cost_analyzer = get_execution_cost_analyzer()
            if expected_price > 0:
                await cost_analyzer.analyze_execution_cost(
                    symbol=symbol,
                    side="buy",
                    quantity=filled_qty,
                    expected_price=expected_price,
                    actual_price=fill_price,
                    order_type=execution_result.get("order_type_used", "market"),
                    spread=execution_result.get("spread_pct", 0) / 100 * expected_price
                )
            
            # Setup smart exits
            exit_manager = get_smart_exit_manager()
            position_type = trade.get('position_type', 'stock')
            await exit_manager.setup_smart_exits(
                symbol=symbol,
                entry_price=fill_price,
                quantity=filled_qty,
                position_type=position_type,
                strategy="multi_target"
            )
            
            logger.info(f"✅ Enhanced BUY completed: {symbol} - {filled_qty} @ ${fill_price:.2f}")
            
            return {
                "success": True,
                "trade_id": trade_id,
                "order_id": execution_result.get("order_id"),
                "symbol": symbol,
                "quantity": filled_qty,
                "fill_price": fill_price,
                "action": "buy",
                "execution_type": "enhanced",
                "order_type_used": execution_result.get("order_type_used"),
                "spread_pct": execution_result.get("spread_pct", 0),
                "attempts": result.get("attempts", 1)
            }
            
        except Exception as e:
            logger.error(f"Error in enhanced buy execution: {e}")
            return {
                "success": False,
                "error": str(e),
                "symbol": trade.get('symbol', 'UNKNOWN'),
                "execution_type": "enhanced"
            }
    
    async def execute_sell(
        self,
        symbol: str,
        quantity: Optional[int] = None,
        reason: str = "Manual sell"
    ) -> Dict[str, Any]:
        """
        Execute a sell order for a position.
        
        Args:
            symbol: Stock symbol
            quantity: Number of shares to sell (None = sell all)
            reason: Reason for selling
            
        Returns:
            Execution result
        """
        try:
            # Get current position
            position = await self.alpaca.get_position(symbol)
            if not position:
                return {
                    "success": False,
                    "error": f"No position found for {symbol}",
                    "symbol": symbol
                }
            
            current_qty = int(float(position.get("qty", 0)))
            if current_qty <= 0:
                return {
                    "success": False,
                    "error": f"No shares to sell for {symbol}",
                    "symbol": symbol
                }
            
            # Check for open orders that might be holding shares
            try:
                open_orders = await self.alpaca.get_orders(status="open", limit=50)
                held_qty = 0
                for order in open_orders:
                    if order.get("symbol") == symbol and order.get("side") == "sell":
                        held_qty += int(float(order.get("qty", 0)))
                
                available_qty = abs(current_qty) - held_qty
                if available_qty <= 0:
                    return {
                        "success": False,
                        "error": f"All {symbol} shares are held by open orders. Cancel existing sell orders first.",
                        "symbol": symbol,
                        "held_by_orders": held_qty
                    }
            except Exception as e:
                logger.warning(f"Could not check open orders for {symbol}: {e}")
                available_qty = abs(current_qty)
            
            # Determine quantity to sell
            sell_qty = quantity if quantity is not None else available_qty
            sell_qty = min(sell_qty, available_qty)  # Don't oversell available
            
            if sell_qty <= 0:
                return {
                    "success": False,
                    "error": f"No available shares to sell for {symbol} (all held by orders)",
                    "symbol": symbol
                }
            
            logger.info(f"Executing SELL order: {sell_qty} {symbol} (Available: {available_qty}, Reason: {reason})")
            
            # Place market sell order
            order = await self.alpaca.place_market_order(
                symbol=symbol,
                qty=sell_qty,
                side="sell"
            )
            
            # Record the trade
            await self.db.record_trade({
                "symbol": symbol,
                "action": "SELL",
                "quantity": sell_qty,
                "price": float(position.get("current_price", 0)),
                "timestamp": datetime.now(),
                "reason": reason,
                "order_id": order.get("id")
            })
            
            logger.info(f"✅ Sell order placed: {sell_qty} {symbol} - Order ID: {order.get('id')}")
            
            return {
                "success": True,
                "symbol": symbol,
                "quantity": sell_qty,
                "order_id": order.get("id"),
                "message": f"Sold {sell_qty} shares of {symbol}"
            }
            
        except Exception as e:
            logger.error(f"Error executing sell order: {e}")
            return {
                "success": False,
                "error": str(e),
                "symbol": symbol
            }
    
    async def set_stop_losses(self, symbols: List[str], pct: float) -> Dict[str, Any]:
        """Place stop-loss orders as a percentage below current price for given symbols."""
        results: List[str] = []
        for symbol in symbols:
            try:
                position = await self.alpaca.get_position(symbol)
                if not position:
                    results.append(f"{symbol}: No position found")
                    continue
                current_price = float(position.get("current_price", 0))
                qty = int(abs(float(position.get("qty", 0))))
                stop_price = round(current_price * (1 - pct / 100), 2)
                await self.alpaca.place_order(
                    symbol=symbol,
                    qty=qty,
                    side="sell",
                    order_type="stop",
                    stop_price=stop_price,
                    time_in_force="gtc",
                )
                results.append(f"✅ {symbol}: Stop-loss set at ${stop_price:.2f}")
            except Exception as e:
                results.append(f"❌ {symbol}: Error - {str(e)}")
        return {"success": True, "results": results}

    async def set_take_profits(self, symbols: List[str], pct: float) -> Dict[str, Any]:
        """Place take-profit limit orders as a percentage above current price for given symbols."""
        results: List[str] = []
        for symbol in symbols:
            try:
                position = await self.alpaca.get_position(symbol)
                if not position:
                    results.append(f"{symbol}: No position found")
                    continue
                current_price = float(position.get("current_price", 0))
                qty = int(abs(float(position.get("qty", 0))))
                limit_price = round(current_price * (1 + pct / 100), 2)
                await self.alpaca.place_order(
                    symbol=symbol,
                    qty=qty,
                    side="sell",
                    order_type="limit",
                    limit_price=limit_price,
                    time_in_force="gtc",
                )
                results.append(f"✅ {symbol}: Take-profit at ${limit_price:.2f}")
            except Exception as e:
                results.append(f"❌ {symbol}: Error - {str(e)}")
        return {"success": True, "results": results}

    async def cancel_open_orders_for_symbol(self, symbol: str, order_type: Optional[str] = None) -> Dict[str, Any]:
        """Cancel open orders for a symbol, optionally filtered by type."""
        try:
            orders = await self.alpaca.get_orders(status="open", limit=200)
            cancelled = 0
            for o in orders:
                if o.get("symbol") != symbol:
                    continue
                if order_type and (o.get("type") != order_type):
                    continue
                try:
                    if await self.alpaca.cancel_order(o.get("id")):
                        cancelled += 1
                except Exception:
                    continue
            return {"success": True, "cancelled": cancelled}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def close_position(self, symbol: str, reason: str = "Position close") -> Dict[str, Any]:
        """
        Close an entire position.
        
        Args:
            symbol: Stock symbol
            reason: Reason for closing
            
        Returns:
            Execution result
        """
        try:
            logger.info(f"Closing position: {symbol} (Reason: {reason})")
            
            # Get position details before closing
            position = await self.alpaca.get_position(symbol)
            if not position:
                return {
                    "success": False,
                    "error": f"No position found for {symbol}"
                }
            
            # Close position via Alpaca
            success = await self.alpaca.close_position(symbol)
            
            if success:
                # Generate trade ID
                trade_id = str(uuid.uuid4())
                
                # Record trade
                await self.db.record_trade(
                    trade_id=trade_id,
                    symbol=symbol,
                    action="sell",
                    quantity=position['qty'],
                    price=position['current_price'],
                    status="submitted",
                    notes=reason
                )
                
                # Mark position as closed
                await self.db.close_position(symbol)
                
                logger.info(f"Position closed: {symbol}")
                
                return {
                    "success": True,
                    "trade_id": trade_id,
                    "symbol": symbol,
                    "quantity": position['qty'],
                    "profit_loss": position['unrealized_pl'],
                    "reason": reason
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to close position",
                    "symbol": symbol
                }
            
        except Exception as e:
            logger.error(f"Error closing position: {e}")
            return {
                "success": False,
                "error": str(e),
                "symbol": symbol
            }
    
    async def close_all_positions(self, reason: str = "Close all") -> Dict[str, Any]:
        """
        Close all open positions.
        
        Args:
            reason: Reason for closing all positions
            
        Returns:
            Execution result
        """
        try:
            logger.info(f"Closing all positions (Reason: {reason})")
            
            # Get all positions
            positions = await self.alpaca.get_positions()
            
            if not positions:
                return {
                    "success": True,
                    "message": "No positions to close",
                    "closed_count": 0
                }
            
            # Close each position
            results = []
            for position in positions:
                result = await self.close_position(position['symbol'], reason)
                results.append(result)
            
            successful = sum(1 for r in results if r.get('success'))
            
            logger.info(f"Closed {successful}/{len(positions)} positions")
            
            return {
                "success": True,
                "closed_count": successful,
                "total_count": len(positions),
                "results": results
            }
            
        except Exception as e:
            logger.error(f"Error closing all positions: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """
        Get the status of an order.
        
        Args:
            order_id: Order ID
            
        Returns:
            Order status
        """
        try:
            orders = await self.alpaca.get_orders(status="all", limit=100)
            
            for order in orders:
                if order['id'] == order_id:
                    return order
            
            return {"error": "Order not found"}
            
        except Exception as e:
            logger.error(f"Error getting order status: {e}")
            return {"error": str(e)}
    
    async def execute_options_buy(self, trade: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute an options buy order.
        
        Args:
            trade: Options trade details
            
        Returns:
            Execution result
        """
        try:
            logger.info(
                f"Executing options buy: {trade['contracts']} {trade['underlying']} "
                f"{trade['option_type']} ${trade['strike']} exp {trade['expiration']}"
            )
            
            # Place options order via Alpaca
            result = await self.alpaca.place_option_order(
                underlying=trade['underlying'],
                quantity=trade['contracts'],
                strike=trade['strike'],
                expiration=trade['expiration'],
                option_type=trade['option_type'],
                side='buy'
            )
            
            if not result['success']:
                return {
                    "success": False,
                    "error": result.get('error', 'Unknown error')
                }
            
            # Generate trade ID
            trade_id = str(uuid.uuid4())
            
            # Record trade in database
            await self.db.record_trade(
                trade_id=trade_id,
                symbol=trade['underlying'],
                action="buy",
                quantity=trade['contracts'],
                price=trade['premium'],
                status="submitted",
                notes=f"Options: {trade['option_type']} ${trade['strike']} exp {trade['expiration']}"
            )
            
            logger.info(f"Options order placed: {result['order_id']}")
            
            return {
                "success": True,
                "trade_id": trade_id,
                "order_id": result['order_id'],
                "symbol": result['symbol'],
                "underlying": trade['underlying'],
                "option_type": trade['option_type'],
                "strike": trade['strike'],
                "expiration": trade['expiration'],
                "contracts": trade['contracts'],
                "premium": trade['premium'],
                "total_cost": trade['premium'] * 100 * trade['contracts']
            }
            
        except Exception as e:
            logger.error(f"Error executing options buy: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def close_options_position(self, option_symbol: str, reason: str = "Exit signal") -> Dict[str, Any]:
        """
        Close an options position.
        
        Args:
            option_symbol: Option symbol to close
            reason: Reason for closing
            
        Returns:
            Execution result
        """
        try:
            logger.info(f"Closing options position: {option_symbol} (Reason: {reason})")
            
            # Close via Alpaca
            success = await self.alpaca.close_option_position(option_symbol)
            
            if success:
                # Parse option symbol to get underlying
                parsed = self.alpaca.parse_option_symbol(option_symbol)
                
                # Mark as closed in database
                await self.db.close_position(parsed['underlying'])
                
                logger.info(f"Options position closed: {option_symbol}")
                
                return {
                    "success": True,
                    "symbol": option_symbol,
                    "underlying": parsed['underlying'],
                    "reason": reason
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to close position"
                }
                
        except Exception as e:
            logger.error(f"Error closing options position: {e}")
            return {
                "success": False,
                "error": str(e)
            }
