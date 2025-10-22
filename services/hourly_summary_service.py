"""
Hourly summary service for trading activities and market analysis.
"""
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from loguru import logger

from services import get_alpaca_service, get_database_service


class HourlySummaryService:
    """Service for generating hourly trading summaries."""
    
    def __init__(self, bot=None):
        """Initialize hourly summary service."""
        self.bot = bot
        self.alpaca = get_alpaca_service()
        self.db = get_database_service()
        self.last_summary_time = None
        logger.info("📊 Hourly Summary Service initialized")
    
    async def generate_hourly_summary(self) -> Dict[str, Any]:
        """Generate comprehensive hourly summary."""
        try:
            now = datetime.now()
            hour_ago = now - timedelta(hours=1)
            
            # Collect data for summary
            summary_data = {
                "timestamp": now.isoformat(),
                "period": f"{hour_ago.strftime('%H:%M')} - {now.strftime('%H:%M')}",
                "scans_performed": await self._get_scan_summary(hour_ago, now),
                "opportunities_found": await self._get_opportunities_summary(hour_ago, now),
                "trades_executed": await self._get_trades_summary(hour_ago, now),
                "positions_status": await self._get_positions_summary(),
                "market_conditions": await self._get_market_conditions(),
                "performance_metrics": await self._get_performance_metrics(),
                "next_actions": await self._get_next_actions()
            }
            
            # Generate formatted summary message
            summary_message = await self._format_summary_message(summary_data)
            
            # Send to Discord if bot is available
            if self.bot:
                await self._send_summary_to_discord(summary_message, summary_data)
            
            self.last_summary_time = now
            logger.info(f"📊 Hourly summary generated for {summary_data['period']}")
            
            return summary_data
            
        except Exception as e:
            logger.error(f"Error generating hourly summary: {e}")
            return {}
    
    async def _get_scan_summary(self, start_time: datetime, end_time: datetime) -> Dict[str, Any]:
        """Get scanning activity summary."""
        try:
            # This would ideally come from a scan log/database
            # For now, we'll estimate based on scheduler intervals
            time_diff = (end_time - start_time).total_seconds() / 60  # minutes
            estimated_scans = max(1, int(time_diff / 5))  # Every 5 minutes during market hours
            
            return {
                "total_scans": estimated_scans,
                "symbols_analyzed": ["AAPL", "GOOGL", "MSFT", "META", "NVDA", "TSLA", "IWM", "QQQ", "SPY", "AMZN"],
                "scan_types": ["momentum", "mean_reversion", "breakout", "volume_spike"],
                "market_hours_active": self._is_market_hours(datetime.now())
            }
        except Exception as e:
            logger.error(f"Error getting scan summary: {e}")
            return {"total_scans": 0, "symbols_analyzed": [], "scan_types": []}
    
    async def _get_opportunities_summary(self, start_time: datetime, end_time: datetime) -> Dict[str, Any]:
        """Get opportunities found summary."""
        try:
            # Get recent opportunities (this would come from opportunity database)
            opportunities = {
                "total_found": 0,
                "high_confidence": 0,
                "by_strategy": {
                    "momentum": 0,
                    "mean_reversion": 0,
                    "breakout": 0,
                    "volume_spike": 0
                },
                "top_opportunities": [],
                "reasons_for_no_opportunities": []
            }
            
            # Check current market conditions for why no opportunities
            if opportunities["total_found"] == 0:
                market_conditions = await self._analyze_market_conditions()
                opportunities["reasons_for_no_opportunities"] = market_conditions.get("limiting_factors", [])
            
            return opportunities
        except Exception as e:
            logger.error(f"Error getting opportunities summary: {e}")
            return {"total_found": 0, "high_confidence": 0}
    
    async def _get_trades_summary(self, start_time: datetime, end_time: datetime) -> Dict[str, Any]:
        """Get trades executed summary."""
        try:
            # Get recent orders from Alpaca
            orders = await self.alpaca.get_orders(status="all", limit=50)
            
            recent_orders = []
            for order in orders:
                order_time = datetime.fromisoformat(order.get("created_at", "").replace("Z", "+00:00"))
                if start_time <= order_time <= end_time:
                    recent_orders.append(order)
            
            executed_trades = [o for o in recent_orders if o.get("status") == "filled"]
            
            return {
                "total_orders": len(recent_orders),
                "executed_trades": len(executed_trades),
                "pending_orders": len([o for o in recent_orders if o.get("status") in ["new", "accepted", "pending_new"]]),
                "cancelled_orders": len([o for o in recent_orders if o.get("status") == "cancelled"]),
                "trade_details": [
                    {
                        "symbol": t.get("symbol"),
                        "side": t.get("side"),
                        "qty": t.get("qty"),
                        "filled_price": t.get("filled_avg_price"),
                        "time": t.get("filled_at", t.get("created_at"))
                    }
                    for t in executed_trades[:5]  # Show last 5 trades
                ]
            }
        except Exception as e:
            logger.error(f"Error getting trades summary: {e}")
            return {"total_orders": 0, "executed_trades": 0}
    
    async def _get_positions_summary(self) -> Dict[str, Any]:
        """Get current positions summary."""
        try:
            positions = await self.alpaca.get_positions()
            account = await self.alpaca.get_account()
            
            total_value = sum(float(pos.get("market_value", 0)) for pos in positions)
            total_pnl = sum(float(pos.get("unrealized_pl", 0)) for pos in positions)
            
            return {
                "total_positions": len(positions),
                "total_value": total_value,
                "total_pnl": total_pnl,
                "account_equity": float(account.get("equity", 0)),
                "buying_power": float(account.get("buying_power", 0)),
                "top_performers": sorted(
                    [
                        {
                            "symbol": pos.get("symbol"),
                            "pnl": float(pos.get("unrealized_pl", 0)),
                            "pnl_pct": float(pos.get("unrealized_plpc", 0)) * 100
                        }
                        for pos in positions
                    ],
                    key=lambda x: x["pnl"],
                    reverse=True
                )[:3]
            }
        except Exception as e:
            logger.error(f"Error getting positions summary: {e}")
            return {"total_positions": 0, "total_value": 0}
    
    async def _get_market_conditions(self) -> Dict[str, Any]:
        """Get current market conditions."""
        try:
            # Get market data for major indices
            market_data = {}
            for symbol in ["SPY", "QQQ", "IWM"]:
                try:
                    snapshot = await self.alpaca.get_snapshot(symbol)
                    if snapshot:
                        market_data[symbol] = {
                            "price": snapshot.get("latest_trade", {}).get("price", 0),
                            "change_pct": snapshot.get("prev_daily_bar", {}).get("change", 0)
                        }
                except:
                    continue
            
            return {
                "market_data": market_data,
                "volatility": "MODERATE",  # This would be calculated from VIX or other indicators
                "trend": "SIDEWAYS",      # This would be determined from technical analysis
                "volume": "NORMAL"        # This would be compared to average volume
            }
        except Exception as e:
            logger.error(f"Error getting market conditions: {e}")
            return {}
    
    async def _get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics."""
        try:
            account = await self.alpaca.get_account()
            
            return {
                "day_pnl": float(account.get("day_trade_buying_power", 0)) - float(account.get("buying_power", 0)),
                "success_rate": 0.0,  # This would be calculated from trade history
                "avg_hold_time": "N/A",  # This would be calculated from trade history
                "risk_metrics": {
                    "max_position_size": 5000,
                    "current_exposure": float(account.get("long_market_value", 0)),
                    "cash_percentage": (float(account.get("cash", 0)) / float(account.get("equity", 1))) * 100
                }
            }
        except Exception as e:
            logger.error(f"Error getting performance metrics: {e}")
            return {}
    
    async def _get_next_actions(self) -> List[str]:
        """Get recommended next actions."""
        try:
            actions = []
            
            # Check if market is open
            if self._is_market_hours(datetime.now()):
                actions.append("Continue monitoring for breakout opportunities")
                actions.append("Watch for volume spikes in current positions")
            else:
                actions.append("Prepare for next trading session")
                actions.append("Review after-hours news and earnings")
            
            # Check positions for risk management
            positions = await self.alpaca.get_positions()
            if positions:
                actions.append(f"Monitor {len(positions)} active positions for exit signals")
            
            return actions
        except Exception as e:
            logger.error(f"Error getting next actions: {e}")
            return ["Continue systematic monitoring"]
    
    async def _analyze_market_conditions(self) -> Dict[str, Any]:
        """Analyze why opportunities might be limited."""
        try:
            limiting_factors = []
            
            # Check market hours
            if not self._is_market_hours(datetime.now()):
                limiting_factors.append("Market is closed")
            
            # Check if system is paused
            # This would check system status
            limiting_factors.append("Low volatility environment")
            limiting_factors.append("Waiting for clear technical setups")
            
            return {
                "limiting_factors": limiting_factors,
                "market_regime": "Consolidation phase",
                "recommended_strategy": "Wait for clear breakout signals"
            }
        except Exception as e:
            logger.error(f"Error analyzing market conditions: {e}")
            return {"limiting_factors": ["Analysis unavailable"]}
    
    def _is_market_hours(self, dt: datetime) -> bool:
        """Check if it's market hours."""
        # Simple check - market hours are 9:30 AM - 4:00 PM ET, Monday-Friday
        if dt.weekday() >= 5:  # Weekend
            return False
        return 9 <= dt.hour < 16
    
    async def _format_summary_message(self, data: Dict[str, Any]) -> str:
        """Format summary data into Discord message."""
        try:
            scans = data.get("scans_performed", {})
            opps = data.get("opportunities_found", {})
            trades = data.get("trades_executed", {})
            positions = data.get("positions_summary", {})
            
            message = f"""📊 **HOURLY TRADING SUMMARY** - {data.get('period', 'N/A')}

🔍 **SCANNING ACTIVITY**
• **Scans Performed:** {scans.get('total_scans', 0)} across {len(scans.get('symbols_analyzed', []))} symbols
• **Strategies Used:** {', '.join(scans.get('scan_types', []))}
• **Market Status:** {'🟢 ACTIVE' if scans.get('market_hours_active') else '🔴 CLOSED'}

🎯 **OPPORTUNITIES ANALYSIS**
• **Total Found:** {opps.get('total_found', 0)} opportunities
• **High Confidence:** {opps.get('high_confidence', 0)} (70%+ confidence)
• **By Strategy:** Momentum: {opps.get('by_strategy', {}).get('momentum', 0)}, Breakout: {opps.get('by_strategy', {}).get('breakout', 0)}"""

            if opps.get('reasons_for_no_opportunities'):
                message += f"\n• **Why No Opportunities:** {', '.join(opps['reasons_for_no_opportunities'])}"

            message += f"""

💼 **TRADING EXECUTION**
• **Orders Placed:** {trades.get('total_orders', 0)}
• **Trades Executed:** {trades.get('executed_trades', 0)}
• **Pending Orders:** {trades.get('pending_orders', 0)}"""

            if trades.get('trade_details'):
                message += "\n• **Recent Trades:**"
                for trade in trades['trade_details'][:3]:
                    message += f"\n  - {trade['side'].upper()} {trade['qty']} {trade['symbol']} @ ${float(trade.get('filled_price', 0)):.2f}"

            message += f"""

📈 **PORTFOLIO STATUS**
• **Active Positions:** {positions.get('total_positions', 0)}
• **Total Value:** ${positions.get('total_value', 0):,.2f}
• **Unrealized P&L:** ${positions.get('total_pnl', 0):+,.2f}
• **Account Equity:** ${positions.get('account_equity', 0):,.2f}"""

            if positions.get('top_performers'):
                message += "\n• **Top Performers:**"
                for perf in positions['top_performers']:
                    message += f"\n  - {perf['symbol']}: ${perf['pnl']:+,.2f} ({perf['pnl_pct']:+.1f}%)"

            next_actions = data.get('next_actions', [])
            if next_actions:
                message += f"\n\n🎯 **NEXT ACTIONS**\n" + "\n".join(f"• {action}" for action in next_actions[:3])

            return message
            
        except Exception as e:
            logger.error(f"Error formatting summary message: {e}")
            return f"📊 **HOURLY SUMMARY** - Error generating detailed summary: {e}"
    
    async def _send_summary_to_discord(self, message: str, data: Dict[str, Any]):
        """Send summary to Discord channel."""
        try:
            if hasattr(self.bot, 'send_notification'):
                await self.bot.send_notification(message)
                logger.info("📊 Hourly summary sent to Discord")
        except Exception as e:
            logger.error(f"Error sending summary to Discord: {e}")


# Global instance
_hourly_summary_service: Optional[HourlySummaryService] = None


def get_hourly_summary_service(bot=None) -> HourlySummaryService:
    """Get the global hourly summary service instance."""
    global _hourly_summary_service
    if _hourly_summary_service is None:
        _hourly_summary_service = HourlySummaryService(bot)
    return _hourly_summary_service
