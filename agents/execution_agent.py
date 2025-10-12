"""
Execution Agent - Executes trades through Alpaca API.
"""
import asyncio
import uuid
from typing import Dict, Any, Optional
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
        Execute a buy order.
        
        Args:
            trade: Trade details with symbol, quantity, price, etc.
            
        Returns:
            Execution result
        """
        try:
            symbol = trade['symbol']
            quantity = trade['quantity']
            
            logger.info(f"Executing BUY order: {quantity} {symbol}")
            
            # Place market order
            order = await self.alpaca.place_market_order(
                symbol=symbol,
                qty=quantity,
                side="buy",
                time_in_force="day"
            )
            
            # Generate trade ID
            trade_id = str(uuid.uuid4())
            
            # Record trade in database
            await self.db.record_trade(
                trade_id=trade_id,
                symbol=symbol,
                action="buy",
                quantity=quantity,
                price=trade.get('price', 0),
                order_id=order['id'],
                status="submitted",
                notes=trade.get('notes', '')
            )
            
            logger.info(f"BUY order executed: {symbol} (Order ID: {order['id']})")
            
            return {
                "success": True,
                "trade_id": trade_id,
                "order": order,
                "symbol": symbol,
                "quantity": quantity,
                "action": "buy"
            }
            
        except Exception as e:
            logger.error(f"Error executing buy order: {e}")
            return {
                "success": False,
                "error": str(e),
                "symbol": trade.get('symbol', 'UNKNOWN')
            }
    
    async def execute_sell(
        self,
        symbol: str,
        quantity: Optional[int] = None,
        reason: str = "Manual sell"
    ) -> Dict[str, Any]:
        """
        Execute a sell order.
        
        Args:
            symbol: Stock symbol
            quantity: Quantity to sell (None = sell all)
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
                    "error": f"No position found for {symbol}"
                }
            
            # Determine quantity
            if quantity is None:
                quantity = int(position['qty'])
            else:
                quantity = min(quantity, int(position['qty']))
            
            logger.info(f"Executing SELL order: {quantity} {symbol} (Reason: {reason})")
            
            # Place market order
            order = await self.alpaca.place_market_order(
                symbol=symbol,
                qty=quantity,
                side="sell",
                time_in_force="day"
            )
            
            # Generate trade ID
            trade_id = str(uuid.uuid4())
            
            # Get current price for recording
            quote = await self.alpaca.get_latest_quote(symbol)
            current_price = quote['bid_price'] if quote else position['current_price']
            
            # Record trade in database
            await self.db.record_trade(
                trade_id=trade_id,
                symbol=symbol,
                action="sell",
                quantity=quantity,
                price=current_price,
                order_id=order['id'],
                status="submitted",
                notes=reason
            )
            
            # If selling entire position, mark as closed
            if quantity >= position['qty']:
                await self.db.close_position(symbol)
            
            logger.info(f"SELL order executed: {symbol} (Order ID: {order['id']})")
            
            return {
                "success": True,
                "trade_id": trade_id,
                "order": order,
                "symbol": symbol,
                "quantity": quantity,
                "action": "sell",
                "reason": reason,
                "profit_loss": position['unrealized_pl']
            }
            
        except Exception as e:
            logger.error(f"Error executing sell order: {e}")
            return {
                "success": False,
                "error": str(e),
                "symbol": symbol
            }
    
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
