"""
Real-Time Monitor Service - Stream prices and monitor positions in real-time.
"""
import asyncio
from typing import Dict, Any, List, Set, Optional
from datetime import datetime, timedelta
from loguru import logger
import json

from services import get_alpaca_service, get_database_service
from services.smart_exit_manager import get_smart_exit_manager
from services.market_hours_service import get_market_hours_service
from config import settings


class RealTimeMonitorService:
    """Real-time position monitoring with websocket streaming."""
    
    def __init__(self):
        """Initialize real-time monitor."""
        self.alpaca = get_alpaca_service()
        self.db = get_database_service()
        self.exit_manager = get_smart_exit_manager()
        self.market_hours = get_market_hours_service()
        
        # Streaming state
        self.is_streaming = False
        self.position_symbols: Set[str] = set()
        self.last_prices: Dict[str, float] = {}
        self.price_alerts: List[Dict[str, Any]] = []
        
        # Alert callbacks
        self.alert_callbacks = []
        
        # Performance tracking
        self.stream_stats = {
            "messages_received": 0,
            "alerts_generated": 0,
            "exits_triggered": 0,
            "start_time": None,
            "last_update": None
        }
    
    async def start_streaming(self) -> Dict[str, Any]:
        """Start real-time price streaming for positions."""
        try:
            if self.is_streaming:
                return {"success": False, "error": "Already streaming"}
            
            # Check market hours
            market_status = self.market_hours.get_current_market_status()
            if not market_status["can_trade"]:
                logger.info(f"📴 Not starting stream - {market_status['session_description']}")
                return {
                    "success": False,
                    "error": f"Market closed - {market_status['session_description']}"
                }
            
            # Get current positions
            await self._update_position_symbols()
            
            if not self.position_symbols:
                logger.info("📭 No positions to monitor")
                return {"success": False, "error": "No positions to monitor"}
            
            logger.info(f"🚀 Starting real-time stream for {len(self.position_symbols)} symbols")
            
            # Start streaming task
            self.is_streaming = True
            self.stream_stats["start_time"] = datetime.now()
            
            # Start the streaming loop
            asyncio.create_task(self._stream_loop())
            
            return {
                "success": True,
                "symbols": list(self.position_symbols),
                "market_session": market_status["session"],
                "start_time": self.stream_stats["start_time"].isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error starting real-time stream: {e}")
            return {"success": False, "error": str(e)}
    
    async def stop_streaming(self) -> Dict[str, Any]:
        """Stop real-time streaming."""
        try:
            if not self.is_streaming:
                return {"success": False, "error": "Not streaming"}
            
            self.is_streaming = False
            
            # Calculate stats
            duration = datetime.now() - self.stream_stats["start_time"]
            
            logger.info(f"📴 Stopped real-time stream after {duration}")
            
            return {
                "success": True,
                "duration_seconds": duration.total_seconds(),
                "stats": self.stream_stats
            }
            
        except Exception as e:
            logger.error(f"Error stopping stream: {e}")
            return {"success": False, "error": str(e)}
    
    async def _stream_loop(self):
        """Main streaming loop."""
        try:
            while self.is_streaming:
                # Check if market is still open
                market_status = self.market_hours.get_current_market_status()
                if not market_status["can_trade"]:
                    logger.info("📴 Market closed - stopping stream")
                    break
                
                # Update position symbols periodically
                if self.stream_stats["messages_received"] % 100 == 0:
                    await self._update_position_symbols()
                
                # Stream prices for current positions
                if self.position_symbols:
                    await self._stream_position_prices()
                
                # Small delay to prevent overwhelming
                await asyncio.sleep(0.1)
            
        except Exception as e:
            logger.error(f"Error in streaming loop: {e}")
        finally:
            self.is_streaming = False
    
    async def _update_position_symbols(self):
        """Update the list of symbols to monitor."""
        try:
            positions = await self.alpaca.get_positions()
            new_symbols = {pos['symbol'] for pos in positions} if positions else set()
            
            # Log changes
            added = new_symbols - self.position_symbols
            removed = self.position_symbols - new_symbols
            
            if added:
                logger.info(f"📈 Added to stream: {added}")
            if removed:
                logger.info(f"📉 Removed from stream: {removed}")
            
            self.position_symbols = new_symbols
            
        except Exception as e:
            logger.error(f"Error updating position symbols: {e}")
    
    async def _stream_position_prices(self):
        """Stream real-time prices for positions."""
        try:
            # Get latest quotes for all positions
            quotes = await self.alpaca.get_latest_quotes(list(self.position_symbols))
            
            for symbol, quote in quotes.items():
                if not quote:
                    continue
                
                current_price = quote.get('price', quote.get('ask', 0))
                if current_price <= 0:
                    continue
                
                # Track price updates
                self.stream_stats["messages_received"] += 1
                self.stream_stats["last_update"] = datetime.now()
                
                # Store last price
                last_price = self.last_prices.get(symbol, current_price)
                self.last_prices[symbol] = current_price
                
                # Check for significant price moves
                if last_price > 0:
                    price_change_pct = (current_price - last_price) / last_price
                    
                    # Alert on rapid moves (>1% in one update)
                    if abs(price_change_pct) > 0.01:
                        await self._handle_rapid_price_move(symbol, current_price, price_change_pct)
                
                # Check smart exit conditions
                await self._check_realtime_exits(symbol, current_price)
            
        except Exception as e:
            logger.error(f"Error streaming prices: {e}")
    
    async def _handle_rapid_price_move(self, symbol: str, price: float, change_pct: float):
        """Handle rapid price movements."""
        try:
            direction = "UP" if change_pct > 0 else "DOWN"
            
            alert = {
                "type": "RAPID_PRICE_MOVE",
                "symbol": symbol,
                "message": f"⚡ {symbol}: Rapid move {direction} {abs(change_pct)*100:.1f}%",
                "price": price,
                "change_pct": change_pct * 100,
                "timestamp": datetime.now().isoformat(),
                "severity": "HIGH" if abs(change_pct) > 0.02 else "MEDIUM"
            }
            
            self.price_alerts.append(alert)
            self.stream_stats["alerts_generated"] += 1
            
            # Trigger callbacks
            await self._trigger_alert_callbacks(alert)
            
            logger.info(f"⚡ {symbol}: Rapid {direction} move {abs(change_pct)*100:.1f}% to ${price:.2f}")
            
        except Exception as e:
            logger.error(f"Error handling rapid price move: {e}")
    
    async def _check_realtime_exits(self, symbol: str, current_price: float):
        """Check for real-time exit conditions."""
        try:
            # Check smart exit conditions
            exit_decision = await self.exit_manager.check_exit_conditions(symbol, current_price)
            
            if exit_decision["action"] != "none":
                # Generate exit alert
                alert = {
                    "type": "REALTIME_EXIT",
                    "symbol": symbol,
                    "message": f"🚪 {symbol}: {exit_decision['reason']}",
                    "exit_decision": exit_decision,
                    "price": current_price,
                    "timestamp": datetime.now().isoformat(),
                    "severity": "CRITICAL"
                }
                
                self.price_alerts.append(alert)
                self.stream_stats["exits_triggered"] += 1
                
                # Trigger callbacks immediately
                await self._trigger_alert_callbacks(alert)
                
                logger.warning(f"🚪 REALTIME EXIT: {symbol} - {exit_decision['reason']}")
                
                # Optional: Auto-execute exit (if enabled)
                if settings.auto_trading_enabled and exit_decision.get("auto_execute", False):
                    await self._auto_execute_exit(symbol, exit_decision)
            
        except Exception as e:
            logger.error(f"Error checking realtime exits for {symbol}: {e}")
    
    async def _auto_execute_exit(self, symbol: str, exit_decision: Dict[str, Any]):
        """Auto-execute exit if enabled."""
        try:
            logger.info(f"🤖 Auto-executing exit for {symbol}")
            
            result = await self.exit_manager.execute_exit(exit_decision)
            
            if result["success"]:
                logger.info(f"✅ Auto-exit executed: {symbol}")
                
                # Alert about execution
                alert = {
                    "type": "AUTO_EXIT_EXECUTED",
                    "symbol": symbol,
                    "message": f"🤖 {symbol}: Auto-exit executed",
                    "execution_result": result,
                    "timestamp": datetime.now().isoformat(),
                    "severity": "INFO"
                }
                
                await self._trigger_alert_callbacks(alert)
            else:
                logger.error(f"❌ Auto-exit failed: {symbol} - {result.get('error')}")
            
        except Exception as e:
            logger.error(f"Error auto-executing exit: {e}")
    
    def register_alert_callback(self, callback):
        """Register callback for real-time alerts."""
        self.alert_callbacks.append(callback)
        logger.info(f"📡 Real-time alert callback registered: {callback.__name__}")
    
    async def _trigger_alert_callbacks(self, alert: Dict[str, Any]):
        """Trigger all alert callbacks."""
        for callback in self.alert_callbacks:
            try:
                await callback(alert)
            except Exception as e:
                logger.error(f"Error in real-time alert callback: {e}")
    
    def get_stream_status(self) -> Dict[str, Any]:
        """Get current streaming status."""
        return {
            "is_streaming": self.is_streaming,
            "symbols_monitored": list(self.position_symbols),
            "symbols_count": len(self.position_symbols),
            "stats": self.stream_stats,
            "recent_alerts": self.price_alerts[-10:],  # Last 10 alerts
            "last_prices": self.last_prices
        }
    
    def get_recent_alerts(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent real-time alerts."""
        return self.price_alerts[-limit:]
    
    def clear_alerts(self):
        """Clear alert history."""
        cleared_count = len(self.price_alerts)
        self.price_alerts.clear()
        logger.info(f"🧹 Cleared {cleared_count} real-time alerts")
        return {"cleared": cleared_count}


# Singleton instance
_realtime_monitor = None

def get_realtime_monitor_service():
    """Get or create real-time monitor service."""
    global _realtime_monitor
    if _realtime_monitor is None:
        _realtime_monitor = RealTimeMonitorService()
    return _realtime_monitor
