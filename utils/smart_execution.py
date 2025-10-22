"""
Smart Order Execution Module.

Implements TWAP, VWAP, and intelligent order routing.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from loguru import logger
import asyncio
import math


class SmartExecutor:
    """
    Smart order execution with TWAP/VWAP algorithms.
    
    Features:
    - TWAP (Time-Weighted Average Price)
    - VWAP (Volume-Weighted Average Price)
    - Iceberg orders
    - Adaptive execution
    - Slippage tracking
    """
    
    def __init__(self, alpaca_service):
        """
        Initialize smart executor.
        
        Args:
            alpaca_service: Alpaca service instance
        """
        self.alpaca = alpaca_service
        self.execution_history = []
        logger.info("✅ Smart Executor initialized")
    
    async def twap_execution(self, symbol: str, total_shares: int, 
                            duration_minutes: int, side: str = "buy") -> Dict[str, Any]:
        """
        Execute order using TWAP (Time-Weighted Average Price).
        
        Splits order into equal chunks over time.
        
        Args:
            symbol: Stock symbol
            total_shares: Total shares to trade
            duration_minutes: Duration to spread order over
            side: "buy" or "sell"
            
        Returns:
            Execution result
        """
        logger.info(f"🎯 TWAP Execution: {symbol} {total_shares} shares over {duration_minutes} min")
        
        # Calculate slices
        num_slices = min(duration_minutes, 10)  # Max 10 slices
        shares_per_slice = math.ceil(total_shares / num_slices)
        interval_seconds = (duration_minutes * 60) / num_slices
        
        executed_shares = 0
        total_cost = 0
        fills = []
        
        try:
            for i in range(num_slices):
                # Calculate shares for this slice
                remaining = total_shares - executed_shares
                slice_shares = min(shares_per_slice, remaining)
                
                if slice_shares <= 0:
                    break
                
                # Get current price
                quote = await self.alpaca.get_quote(symbol)
                current_price = quote['ask'] if side == "buy" else quote['bid']
                
                # Place limit order slightly better than market
                if side == "buy":
                    limit_price = current_price * 1.001  # 0.1% above ask
                else:
                    limit_price = current_price * 0.999  # 0.1% below bid
                
                # Submit order
                order = await self.alpaca.place_order(
                    symbol=symbol,
                    qty=slice_shares,
                    side=side,
                    order_type="limit",
                    limit_price=limit_price,
                    time_in_force="ioc"  # Immediate or cancel
                )
                
                # Wait for fill
                await asyncio.sleep(2)
                
                # Check order status
                order_status = await self.alpaca.get_order(order['id'])
                
                if order_status['status'] == 'filled':
                    filled_qty = int(order_status['filled_qty'])
                    filled_price = float(order_status['filled_avg_price'])
                    
                    executed_shares += filled_qty
                    total_cost += filled_qty * filled_price
                    
                    fills.append({
                        "slice": i + 1,
                        "shares": filled_qty,
                        "price": filled_price,
                        "time": datetime.now().isoformat()
                    })
                    
                    logger.info(f"TWAP slice {i+1}/{num_slices}: {filled_qty} @ ${filled_price:.2f}")
                
                # Wait for next slice (except last one)
                if i < num_slices - 1:
                    await asyncio.sleep(interval_seconds)
            
            # Calculate average price
            avg_price = total_cost / executed_shares if executed_shares > 0 else 0
            fill_rate = (executed_shares / total_shares * 100) if total_shares > 0 else 0
            
            result = {
                "algorithm": "TWAP",
                "symbol": symbol,
                "requested_shares": total_shares,
                "executed_shares": executed_shares,
                "fill_rate": fill_rate,
                "avg_price": avg_price,
                "total_cost": total_cost,
                "num_slices": len(fills),
                "fills": fills,
                "duration_minutes": duration_minutes
            }
            
            self.execution_history.append(result)
            
            logger.info(f"✅ TWAP Complete: {executed_shares}/{total_shares} @ ${avg_price:.2f} ({fill_rate:.1f}%)")
            
            return result
            
        except Exception as e:
            logger.error(f"TWAP execution error: {e}")
            return {"error": str(e)}
    
    async def vwap_execution(self, symbol: str, total_shares: int,
                            duration_minutes: int, side: str = "buy") -> Dict[str, Any]:
        """
        Execute order using VWAP (Volume-Weighted Average Price).
        
        Adjusts slice sizes based on historical volume patterns.
        
        Args:
            symbol: Stock symbol
            total_shares: Total shares to trade
            duration_minutes: Duration to spread order over
            side: "buy" or "sell"
            
        Returns:
            Execution result
        """
        logger.info(f"🎯 VWAP Execution: {symbol} {total_shares} shares over {duration_minutes} min")
        
        try:
            # Get historical volume profile
            bars = await self.alpaca.get_bars(
                symbol=symbol,
                timeframe="1Min",
                limit=duration_minutes
            )
            
            if not bars or len(bars) < 5:
                logger.warning("Insufficient volume data, falling back to TWAP")
                return await self.twap_execution(symbol, total_shares, duration_minutes, side)
            
            # Calculate volume weights
            total_volume = sum(bar['volume'] for bar in bars)
            volume_weights = [bar['volume'] / total_volume for bar in bars]
            
            # Calculate shares per slice based on volume
            num_slices = min(len(bars), 10)
            slice_shares = []
            
            for i in range(num_slices):
                weight = volume_weights[i] if i < len(volume_weights) else (1 / num_slices)
                shares = int(total_shares * weight)
                slice_shares.append(max(shares, 1))
            
            # Adjust to match total
            current_total = sum(slice_shares)
            if current_total < total_shares:
                slice_shares[-1] += (total_shares - current_total)
            
            # Execute slices
            executed_shares = 0
            total_cost = 0
            fills = []
            interval_seconds = (duration_minutes * 60) / num_slices
            
            for i, shares in enumerate(slice_shares):
                if executed_shares >= total_shares:
                    break
                
                # Get current price
                quote = await self.alpaca.get_quote(symbol)
                current_price = quote['ask'] if side == "buy" else quote['bid']
                
                # Place limit order
                if side == "buy":
                    limit_price = current_price * 1.001
                else:
                    limit_price = current_price * 0.999
                
                # Submit order
                order = await self.alpaca.place_order(
                    symbol=symbol,
                    qty=shares,
                    side=side,
                    order_type="limit",
                    limit_price=limit_price,
                    time_in_force="ioc"
                )
                
                await asyncio.sleep(2)
                
                # Check fill
                order_status = await self.alpaca.get_order(order['id'])
                
                if order_status['status'] == 'filled':
                    filled_qty = int(order_status['filled_qty'])
                    filled_price = float(order_status['filled_avg_price'])
                    
                    executed_shares += filled_qty
                    total_cost += filled_qty * filled_price
                    
                    fills.append({
                        "slice": i + 1,
                        "shares": filled_qty,
                        "price": filled_price,
                        "volume_weight": volume_weights[i] if i < len(volume_weights) else 0,
                        "time": datetime.now().isoformat()
                    })
                    
                    logger.info(f"VWAP slice {i+1}/{num_slices}: {filled_qty} @ ${filled_price:.2f}")
                
                if i < num_slices - 1:
                    await asyncio.sleep(interval_seconds)
            
            avg_price = total_cost / executed_shares if executed_shares > 0 else 0
            fill_rate = (executed_shares / total_shares * 100) if total_shares > 0 else 0
            
            result = {
                "algorithm": "VWAP",
                "symbol": symbol,
                "requested_shares": total_shares,
                "executed_shares": executed_shares,
                "fill_rate": fill_rate,
                "avg_price": avg_price,
                "total_cost": total_cost,
                "num_slices": len(fills),
                "fills": fills,
                "duration_minutes": duration_minutes
            }
            
            self.execution_history.append(result)
            
            logger.info(f"✅ VWAP Complete: {executed_shares}/{total_shares} @ ${avg_price:.2f} ({fill_rate:.1f}%)")
            
            return result
            
        except Exception as e:
            logger.error(f"VWAP execution error: {e}")
            return {"error": str(e)}
    
    async def iceberg_order(self, symbol: str, total_shares: int,
                           display_size: int, side: str = "buy") -> Dict[str, Any]:
        """
        Execute iceberg order (hide true order size).
        
        Args:
            symbol: Stock symbol
            total_shares: Total shares to trade
            display_size: Visible size per order
            side: "buy" or "sell"
            
        Returns:
            Execution result
        """
        logger.info(f"🧊 Iceberg Order: {symbol} {total_shares} shares (display: {display_size})")
        
        executed_shares = 0
        total_cost = 0
        fills = []
        
        try:
            while executed_shares < total_shares:
                remaining = total_shares - executed_shares
                order_size = min(display_size, remaining)
                
                # Get current price
                quote = await self.alpaca.get_quote(symbol)
                current_price = quote['ask'] if side == "buy" else quote['bid']
                
                # Place limit order at current market price
                limit_price = current_price
                
                order = await self.alpaca.place_order(
                    symbol=symbol,
                    qty=order_size,
                    side=side,
                    order_type="limit",
                    limit_price=limit_price,
                    time_in_force="day"
                )
                
                # Wait for fill
                await asyncio.sleep(5)
                
                order_status = await self.alpaca.get_order(order['id'])
                
                if order_status['status'] in ['filled', 'partially_filled']:
                    filled_qty = int(order_status['filled_qty'])
                    filled_price = float(order_status['filled_avg_price'])
                    
                    executed_shares += filled_qty
                    total_cost += filled_qty * filled_price
                    
                    fills.append({
                        "shares": filled_qty,
                        "price": filled_price,
                        "time": datetime.now().isoformat()
                    })
                    
                    logger.info(f"Iceberg fill: {filled_qty} @ ${filled_price:.2f}")
                
                # Cancel if not filled
                if order_status['status'] not in ['filled']:
                    await self.alpaca.cancel_order(order['id'])
                
                await asyncio.sleep(2)
            
            avg_price = total_cost / executed_shares if executed_shares > 0 else 0
            
            result = {
                "algorithm": "ICEBERG",
                "symbol": symbol,
                "requested_shares": total_shares,
                "executed_shares": executed_shares,
                "avg_price": avg_price,
                "total_cost": total_cost,
                "fills": fills
            }
            
            self.execution_history.append(result)
            
            logger.info(f"✅ Iceberg Complete: {executed_shares}/{total_shares} @ ${avg_price:.2f}")
            
            return result
            
        except Exception as e:
            logger.error(f"Iceberg execution error: {e}")
            return {"error": str(e)}
    
    def calculate_slippage(self, execution: Dict[str, Any], 
                          benchmark_price: float) -> Dict[str, Any]:
        """
        Calculate execution slippage.
        
        Args:
            execution: Execution result
            benchmark_price: Benchmark price (e.g., arrival price)
            
        Returns:
            Slippage metrics
        """
        avg_price = execution.get('avg_price', 0)
        executed_shares = execution.get('executed_shares', 0)
        
        if avg_price == 0 or executed_shares == 0:
            return {"error": "Invalid execution data"}
        
        # Calculate slippage
        slippage_per_share = avg_price - benchmark_price
        slippage_pct = (slippage_per_share / benchmark_price * 100) if benchmark_price > 0 else 0
        total_slippage = slippage_per_share * executed_shares
        
        return {
            "benchmark_price": benchmark_price,
            "avg_execution_price": avg_price,
            "slippage_per_share": slippage_per_share,
            "slippage_pct": slippage_pct,
            "total_slippage": total_slippage,
            "executed_shares": executed_shares
        }
    
    def get_execution_quality_metrics(self) -> Dict[str, Any]:
        """
        Get execution quality metrics across all executions.
        
        Returns:
            Quality metrics
        """
        if not self.execution_history:
            return {"message": "No execution history"}
        
        total_executions = len(self.execution_history)
        avg_fill_rate = sum(e.get('fill_rate', 0) for e in self.execution_history) / total_executions
        
        twap_count = sum(1 for e in self.execution_history if e.get('algorithm') == 'TWAP')
        vwap_count = sum(1 for e in self.execution_history if e.get('algorithm') == 'VWAP')
        iceberg_count = sum(1 for e in self.execution_history if e.get('algorithm') == 'ICEBERG')
        
        return {
            "total_executions": total_executions,
            "avg_fill_rate": avg_fill_rate,
            "algorithms_used": {
                "TWAP": twap_count,
                "VWAP": vwap_count,
                "ICEBERG": iceberg_count
            },
            "recent_executions": self.execution_history[-5:]
        }
