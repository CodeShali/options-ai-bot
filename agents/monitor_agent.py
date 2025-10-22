"""
Monitor Agent - Monitors positions and generates exit signals.
"""
import asyncio
from typing import Dict, Any, List
from datetime import datetime
from loguru import logger

from agents.base_agent import BaseAgent
from services import get_alpaca_service, get_database_service
from services.smart_exit_manager import get_smart_exit_manager
from services.realtime_monitor_service import get_realtime_monitor_service
from services.options_greeks_monitor import get_options_greeks_monitor
from services.volume_momentum_analyzer import get_volume_momentum_analyzer
from services.news_monitor_service import get_news_monitor_service
from services.portfolio_risk_monitor import get_portfolio_risk_monitor
from config import settings


class MonitorAgent(BaseAgent):
    """Agent responsible for monitoring positions and generating alerts."""
    
    def __init__(self):
        """Initialize the monitor agent."""
        super().__init__("Monitor")
        self.alpaca = get_alpaca_service()
        self.db = get_database_service()
        self.exit_manager = get_smart_exit_manager()
        
        # 🚀 NEW: Enhanced monitoring services
        self.realtime_monitor = get_realtime_monitor_service()
        self.greeks_monitor = get_options_greeks_monitor()
        self.volume_analyzer = get_volume_momentum_analyzer()
        self.news_monitor = get_news_monitor_service()
        self.risk_monitor = get_portfolio_risk_monitor()
        
        self.alert_callbacks = []
        
        # Track last alert state for each position to avoid duplicates
        self.last_alert_state = {}  # {symbol: {"type": "SIGNIFICANT_MOVE", "threshold": 10}}
    
    def _should_send_alert(self, symbol: str, alert_type: str, current_plpc: float) -> bool:
        """
        Determine if an alert should be sent based on state changes.
        
        Args:
            symbol: Stock symbol
            alert_type: Type of alert (PROFIT_TARGET, STOP_LOSS, SIGNIFICANT_MOVE)
            current_plpc: Current profit/loss percentage (as decimal, e.g., 0.15 for 15%)
            
        Returns:
            True if alert should be sent
        """
        last_state = self.last_alert_state.get(symbol, {})
        last_type = last_state.get("type")
        last_plpc = last_state.get("plpc", 0)
        
        # Always send PROFIT_TARGET and STOP_LOSS alerts (critical)
        if alert_type in ["PROFIT_TARGET", "STOP_LOSS"]:
            # But only once per threshold crossing
            if last_type == alert_type:
                return False  # Already sent this alert
            return True
        
        # For SIGNIFICANT_MOVE alerts, use intelligent thresholds
        if alert_type == "SIGNIFICANT_MOVE":
            # Don't send if we just sent the same type
            if last_type == "SIGNIFICANT_MOVE":
                # Only send again if moved by another 5%
                plpc_change = abs(current_plpc - last_plpc)
                if plpc_change < 0.05:  # Less than 5% change since last alert
                    return False
            
            return True
        
        return True
    
    def _update_alert_state(self, symbol: str, alert_type: str, current_plpc: float):
        """Update the last alert state for a symbol."""
        self.last_alert_state[symbol] = {
            "type": alert_type,
            "plpc": current_plpc,
            "timestamp": datetime.now().isoformat()
        }
    
    def _clear_alert_state(self, symbol: str):
        """Clear alert state when position is closed."""
        if symbol in self.last_alert_state:
            del self.last_alert_state[symbol]
    
    async def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process monitoring request.
        
        Args:
            data: Request data with 'action'
            
        Returns:
            Monitoring result
        """
        action = data.get("action")
        
        if action == "monitor_positions":
            return await self.monitor_positions()
        elif action == "enhanced_monitor":
            return await self.enhanced_monitor_positions()
        elif action == "start_realtime":
            return await self.realtime_monitor.start_streaming()
        elif action == "stop_realtime":
            return await self.realtime_monitor.stop_streaming()
        elif action == "check_alerts":
            return await self.check_alerts()
        elif action == "get_position_status":
            symbol = data.get("symbol")
            return await self.get_position_status(symbol)
        elif action == "analyze_portfolio_risk":
            return await self.risk_monitor.analyze_portfolio_risk()
        elif action == "monitor_greeks":
            return await self.greeks_monitor.monitor_all_options_greeks()
        elif action == "analyze_volume_momentum":
            return await self.volume_analyzer.analyze_all_positions()
        elif action == "monitor_news":
            return await self.news_monitor.monitor_position_news()
        else:
            return {"error": f"Unknown action: {action}"}
    
    async def monitor_positions(self) -> Dict[str, Any]:
        """
        Monitor all open positions and check for exit signals.
        
        Returns:
            Monitoring result with alerts
        """
        try:
            logger.info("Monitoring positions...")
            
            # Get all positions
            positions = await self.alpaca.get_positions()
            
            # Clear alert states for positions that no longer exist
            current_symbols = {pos['symbol'] for pos in positions} if positions else set()
            closed_symbols = set(self.last_alert_state.keys()) - current_symbols
            for symbol in closed_symbols:
                self._clear_alert_state(symbol)
                logger.info(f"Cleared alert state for closed position: {symbol}")
            
            if not positions:
                return {
                    "positions_monitored": 0,
                    "alerts": [],
                    "timestamp": datetime.now().isoformat()
                }
            
            alerts = []
            
            for position in positions:
                symbol = position['symbol']
                entry_price = position['avg_entry_price']
                current_price = position['current_price']
                unrealized_plpc = position['unrealized_plpc']
                
                # 🚀 NEW: Use Smart Exit Manager instead of simple targets
                exit_decision = await self.exit_manager.check_exit_conditions(
                    symbol=symbol,
                    current_price=current_price
                )
                
                # Handle smart exit decisions
                if exit_decision["action"] == "partial_exit":
                    alerts.append({
                        "type": "SMART_PARTIAL_EXIT",
                        "symbol": symbol,
                        "message": f"🎯 {symbol}: {exit_decision['reason']}",
                        "reasoning": f"Smart exit triggered: {exit_decision.get('exit_type', 'target')} hit. "
                                   f"Selling {exit_decision['quantity']} shares at ${exit_decision['price']:.2f}. "
                                   f"Remaining position: {exit_decision.get('remaining', 0)} shares. "
                                   f"Profit on this exit: {exit_decision.get('profit_pct', 0):.1f}%",
                        "severity": "INFO",
                        "position": position,
                        "action_required": "PARTIAL_SELL",
                        "exit_decision": exit_decision
                    })
                    self._update_alert_state(symbol, "SMART_PARTIAL_EXIT", unrealized_plpc)
                
                elif exit_decision["action"] == "exit_all":
                    alerts.append({
                        "type": "SMART_FULL_EXIT",
                        "symbol": symbol,
                        "message": f"🚪 {symbol}: {exit_decision['reason']}",
                        "reasoning": f"Smart exit triggered: {exit_decision.get('exit_type', 'final')}. "
                                   f"Selling all {exit_decision['quantity']} shares at ${exit_decision['price']:.2f}. "
                                   f"Max profit seen: {exit_decision.get('max_profit_seen', 0):.1f}%",
                        "severity": "WARNING" if "stop" in exit_decision.get('exit_type', '') else "INFO",
                        "position": position,
                        "action_required": "FULL_SELL",
                        "exit_decision": exit_decision
                    })
                    self._update_alert_state(symbol, "SMART_FULL_EXIT", unrealized_plpc)
                
                # Fallback to legacy alerts if no smart exit position tracked
                elif symbol not in self.exit_manager.position_states:
                    # Calculate legacy targets
                    profit_target_price = entry_price * (1 + settings.profit_target_pct)
                    stop_loss_price = entry_price * (1 - settings.stop_loss_pct)
                    
                    # Check profit target (legacy)
                    if unrealized_plpc >= settings.profit_target_pct:
                        if self._should_send_alert(symbol, "PROFIT_TARGET", unrealized_plpc):
                            alerts.append({
                                "type": "PROFIT_TARGET",
                                "symbol": symbol,
                                "message": f"🎯 {symbol}: Legacy profit target at {unrealized_plpc*100:.2f}%",
                                "reasoning": f"Position not in smart exit system. Legacy target: {settings.profit_target_pct*100:.0f}%",
                                "severity": "INFO",
                                "position": position,
                                "action_required": "SELL"
                            })
                            self._update_alert_state(symbol, "PROFIT_TARGET", unrealized_plpc)
                    
                    # Check stop loss (legacy)
                    elif unrealized_plpc <= -settings.stop_loss_pct:
                        if self._should_send_alert(symbol, "STOP_LOSS", unrealized_plpc):
                            alerts.append({
                                "type": "STOP_LOSS",
                                "symbol": symbol,
                                "message": f"⚠️ {symbol}: Legacy stop loss at {unrealized_plpc*100:.2f}%",
                                "reasoning": f"Position not in smart exit system. Legacy stop: {settings.stop_loss_pct*100:.0f}%",
                                "severity": "WARNING",
                                "position": position,
                                "action_required": "SELL"
                            })
                            self._update_alert_state(symbol, "STOP_LOSS", unrealized_plpc)
                
                # Check for significant moves (>10% but not at target/stop yet)
                elif abs(unrealized_plpc) > 0.10:
                    if not self._should_send_alert(symbol, "SIGNIFICANT_MOVE", unrealized_plpc):
                        continue  # Skip this alert
                    move_direction = "UP" if unrealized_plpc > 0 else "DOWN"
                    move_pct = abs(unrealized_plpc * 100)
                    
                    # Calculate momentum metrics
                    price_change = current_price - entry_price
                    price_change_pct = (price_change / entry_price) * 100
                    
                    # Build detailed reasoning with momentum explanation
                    reasoning = f"📊 **Momentum Analysis:**\n"
                    reasoning += f"• Price Movement: ${entry_price:.2f} → ${current_price:.2f} ({price_change_pct:+.2f}%)\n"
                    reasoning += f"• Dollar Change: ${abs(price_change):.2f} {'gain' if price_change > 0 else 'loss'}\n"
                    reasoning += f"• Momentum Score: {move_pct:.2f}% calculated from price velocity\n"
                    
                    if unrealized_plpc > 0:
                        reasoning += f"• Interpretation: Strong {'bullish' if move_direction == 'UP' else 'bearish'} momentum\n"
                    else:
                        reasoning += f"• Interpretation: Significant {'selling' if move_direction == 'DOWN' else 'buying'} pressure\n"
                    
                    reasoning += f"\n💰 **Position Status:**\n"
                    
                    if unrealized_plpc > 0:
                        remaining_to_target = (settings.profit_target_pct - unrealized_plpc) * 100
                        reasoning += f"Profit target is {settings.profit_target_pct*100:.0f}% (${profit_target_price:.2f}). "
                        reasoning += f"Need {remaining_to_target:.1f}% more to hit target. "
                        reasoning += f"Current profit: ${position['unrealized_pl']:.2f}."
                    else:
                        remaining_to_stop = (settings.stop_loss_pct - abs(unrealized_plpc)) * 100
                        reasoning += f"Stop loss is at {settings.stop_loss_pct*100:.0f}% (${stop_loss_price:.2f}). "
                        reasoning += f"Will trigger at {remaining_to_stop:.1f}% more loss. "
                        reasoning += f"Current loss: ${position['unrealized_pl']:.2f}."
                    
                    alerts.append({
                        "type": "SIGNIFICANT_MOVE",
                        "symbol": symbol,
                        "message": f"📊 {symbol}: {move_direction} {move_pct:.2f}%",
                        "reasoning": reasoning,
                        "severity": "INFO",
                        "position": {
                            "symbol": symbol,
                            "qty": position['qty'],
                            "entry_price": entry_price,
                            "current_price": current_price,
                            "unrealized_pl": position['unrealized_pl'],
                            "unrealized_plpc": unrealized_plpc * 100,
                            "profit_target": profit_target_price,
                            "stop_loss": stop_loss_price
                        },
                        "action_required": "REVIEW"
                    })
                    self._update_alert_state(symbol, "SIGNIFICANT_MOVE", unrealized_plpc)
                
                # Update position in database
                await self.db.update_position(
                    symbol=symbol,
                    quantity=position['qty'],
                    avg_entry_price=entry_price,
                    current_price=current_price,
                    cost_basis=position['cost_basis'],
                    market_value=position['market_value'],
                    unrealized_pl=position['unrealized_pl'],
                    unrealized_plpc=unrealized_plpc
                )
            
            # Check options positions
            options_alerts = await self.monitor_options_positions()
            alerts.extend(options_alerts)
            
            # Trigger callbacks for alerts
            for alert in alerts:
                await self._trigger_alert_callbacks(alert)
            
            logger.info(
                f"Position monitoring complete: {len(positions)} positions, {len(alerts)} alerts"
            )
            
            return {
                "positions_monitored": len(positions),
                "alerts": alerts,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error monitoring positions: {e}")
            return {
                "error": str(e),
                "positions_monitored": 0,
                "alerts": []
            }
    
    async def _analyze_position_comprehensive(self, position: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze position with comprehensive metrics."""
        try:
            symbol = position.get("symbol")
            return {
                "trend": "BULLISH",  # This would be calculated from technical analysis
                "momentum": "STRONG",  # This would be calculated from momentum indicators
                "risk_level": "MODERATE",  # This would be calculated from volatility
                "recommendation": "HOLD"  # This would be AI-generated
            }
        except Exception as e:
            logger.error(f"Error analyzing position {symbol}: {e}")
            return {"trend": "UNKNOWN", "momentum": "UNKNOWN"}
    
    def _get_move_context(self, plpc: float, analysis: Dict[str, Any]) -> str:
        """Get context for significant moves."""
        if plpc > 0:
            return f"Strong upward movement with {analysis.get('momentum', 'unknown')} momentum"
        else:
            return f"Downward pressure with {analysis.get('trend', 'unknown')} trend"
    
    def _get_profit_recommendation(self, plpc: float, analysis: Dict[str, Any]) -> str:
        """Get profit-taking recommendation."""
        if plpc > 0.20:  # 20%+
            return "Consider taking partial profits - strong gains achieved"
        else:
            return "Monitor for further upside - good momentum"
    
    def _get_risk_assessment(self, plpc: float, analysis: Dict[str, Any]) -> str:
        """Get risk assessment for losses."""
        if plpc < -0.15:  # -15%
            return "HIGH RISK - Consider immediate exit to prevent further losses"
        else:
            return "MODERATE RISK - Monitor closely for reversal signals"
    
    async def check_alerts(self) -> Dict[str, Any]:
        """
        Check for system-level alerts.
        
        Returns:
            System alerts
        """
        try:
            alerts = []
            
            # Check account status
            account = await self.alpaca.get_account()
            
            # Check if account is blocked
            if account.get('trading_blocked') or account.get('account_blocked'):
                alerts.append({
                    "type": "ACCOUNT_BLOCKED",
                    "message": "Account is blocked from trading",
                    "severity": "CRITICAL",
                    "action_required": "CONTACT_SUPPORT"
                })
            
            # Check pattern day trader status
            if account.get('pattern_day_trader'):
                alerts.append({
                    "type": "PDT_STATUS",
                    "message": "Account is flagged as pattern day trader",
                    "severity": "INFO",
                    "action_required": "NONE"
                })
            
            # Check buying power
            if account['buying_power'] < 1000:
                alerts.append({
                    "type": "LOW_BUYING_POWER",
                    "message": f"Low buying power: ${account['buying_power']:.2f}",
                    "severity": "WARNING",
                    "action_required": "REVIEW"
                })
            
            # Check daily loss
            from agents.risk_manager_agent import RiskManagerAgent
            risk_manager = RiskManagerAgent()
            circuit_breaker = await risk_manager.check_circuit_breaker()
            
            if circuit_breaker.get('triggered'):
                alerts.append({
                    "type": "CIRCUIT_BREAKER",
                    "message": f"Circuit breaker triggered: ${circuit_breaker['daily_loss']:.2f} loss",
                    "severity": "CRITICAL",
                    "action_required": "STOP_TRADING"
                })
            
            return {
                "alerts": alerts,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error checking alerts: {e}")
            return {
                "error": str(e),
                "alerts": []
            }
    
    async def get_position_status(self, symbol: str) -> Dict[str, Any]:
        """
        Get detailed status for a specific position.
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Position status
        """
        try:
            position = await self.alpaca.get_position(symbol)
            
            if not position:
                return {
                    "error": f"No position found for {symbol}"
                }
            
            # Calculate metrics
            entry_price = position['avg_entry_price']
            current_price = position['current_price']
            unrealized_plpc = position['unrealized_plpc']
            
            # Calculate distance to targets
            profit_target_price = entry_price * (1 + settings.profit_target_pct)
            stop_loss_price = entry_price * (1 - settings.stop_loss_pct)
            
            distance_to_profit = ((profit_target_price - current_price) / current_price) * 100
            distance_to_stop = ((current_price - stop_loss_price) / current_price) * 100
            
            return {
                "symbol": symbol,
                "position": position,
                "entry_price": entry_price,
                "current_price": current_price,
                "unrealized_pl": position['unrealized_pl'],
                "unrealized_plpc": unrealized_plpc * 100,
                "profit_target_price": profit_target_price,
                "stop_loss_price": stop_loss_price,
                "distance_to_profit_pct": distance_to_profit,
                "distance_to_stop_pct": distance_to_stop,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting position status: {e}")
            return {
                "error": str(e),
                "symbol": symbol
            }
    
    async def monitor_options_positions(self) -> List[Dict[str, Any]]:
        """
        Monitor options positions for DTE and P/L.
        
        Returns:
            List of alerts
        """
        from config import settings
        
        try:
            # Get options positions
            options_positions = await self.alpaca.get_option_positions()
            
            if not options_positions:
                return []
            
            alerts = []
            
            for position in options_positions:
                symbol = position['symbol']
                underlying = position['underlying']
                dte = position['dte']
                unrealized_plpc = position['unrealized_plpc']
                
                # Calculate targets
                profit_target_price = position['avg_entry_price'] * (1 + settings.profit_target_pct)
                stop_loss_price = position['avg_entry_price'] * (1 - settings.stop_loss_pct)
                
                # Check DTE - close if approaching expiration
                if dte <= settings.options_close_dte:
                    alerts.append({
                        "type": "OPTIONS_EXPIRATION",
                        "symbol": underlying,
                        "option_symbol": symbol,
                        "message": f"⏰ {underlying} option expires in {dte} days!",
                        "reasoning": f"Option {position['option_type']} ${position['strike']} expires {position['expiration']}. "
                                   f"Only {dte} days remaining. Close to avoid theta decay and expiration risk. "
                                   f"Current P/L: ${position['unrealized_pl']:.2f} ({unrealized_plpc*100:.1f}%)",
                        "severity": "WARNING",
                        "action_required": "CLOSE",
                        "dte": dte,
                        "position": position
                    })
                
                # Check profit target
                elif unrealized_plpc >= settings.profit_target_pct:
                    alerts.append({
                        "type": "PROFIT_TARGET",
                        "symbol": underlying,
                        "option_symbol": symbol,
                        "message": f"🎯 {underlying} option: Profit target reached at {unrealized_plpc*100:.2f}%!",
                        "reasoning": f"Option entered at ${position['avg_entry_price']:.2f}, now at ${position['current_price']:.2f}. "
                                   f"Target was {settings.profit_target_pct*100:.0f}% (${profit_target_price:.2f}). "
                                   f"Current profit: ${position['unrealized_pl']:.2f}. Consider taking profits!",
                        "severity": "INFO",
                        "position": position,
                        "action_required": "SELL"
                    })
                
                # Check stop loss
                elif unrealized_plpc <= -settings.stop_loss_pct:
                    alerts.append({
                        "type": "STOP_LOSS",
                        "symbol": underlying,
                        "option_symbol": symbol,
                        "message": f"⚠️ {underlying} option: Stop loss triggered at {unrealized_plpc*100:.2f}%!",
                        "reasoning": f"Option entered at ${position['avg_entry_price']:.2f}, now at ${position['current_price']:.2f}. "
                                   f"Stop loss was {settings.stop_loss_pct*100:.0f}% (${stop_loss_price:.2f}). "
                                   f"Current loss: ${position['unrealized_pl']:.2f}. Close to prevent further losses.",
                        "severity": "WARNING",
                        "position": position,
                        "action_required": "SELL"
                    })
                
                # Check significant moves
                elif abs(unrealized_plpc) > 0.10:
                    if not self._should_send_alert(underlying, "SIGNIFICANT_MOVE", unrealized_plpc):
                        continue
                    
                    move_direction = "UP" if unrealized_plpc > 0 else "DOWN"
                    move_pct = abs(unrealized_plpc * 100)
                    
                    reasoning = f"Option has moved {move_direction} by {move_pct:.2f}% "
                    reasoning += f"(Entry: ${position['avg_entry_price']:.2f} → Current: ${position['current_price']:.2f}). "
                    reasoning += f"DTE: {dte} days. "
                    
                    if unrealized_plpc > 0:
                        remaining_to_target = (settings.profit_target_pct - unrealized_plpc) * 100
                        reasoning += f"Need {remaining_to_target:.1f}% more to hit {settings.profit_target_pct*100:.0f}% target. "
                    else:
                        remaining_to_stop = (settings.stop_loss_pct - abs(unrealized_plpc)) * 100
                        reasoning += f"Stop loss will trigger at {remaining_to_stop:.1f}% more loss. "
                    
                    reasoning += f"Current P/L: ${position['unrealized_pl']:.2f}."
                    
                    alerts.append({
                        "type": "SIGNIFICANT_MOVE",
                        "symbol": underlying,
                        "option_symbol": symbol,
                        "message": f"📊 {underlying} option: {move_direction} {move_pct:.2f}%",
                        "reasoning": reasoning,
                        "severity": "INFO",
                        "position": position,
                        "action_required": "REVIEW"
                    })
                    self._update_alert_state(underlying, "SIGNIFICANT_MOVE", unrealized_plpc)
            
            return alerts
            
        except Exception as e:
            logger.error(f"Error monitoring options positions: {e}")
            return []
    
    def register_alert_callback(self, callback):
        """
        Register a callback for alerts.
        
        Args:
            callback: Async function to call when alert is triggered
        """
        self.alert_callbacks.append(callback)
        logger.info(f"Alert callback registered: {callback.__name__}")
    
    async def _trigger_alert_callbacks(self, alert: Dict[str, Any]):
        """Trigger all registered alert callbacks."""
        for callback in self.alert_callbacks:
            try:
                await callback(alert)
            except Exception as e:
                logger.error(f"Error in alert callback: {e}")
    
    async def generate_dashboard_data(self) -> Dict[str, Any]:
        """
        Generate data for dashboard visualization.
        
        Returns:
            Dashboard data
        """
        try:
            # Get account info
            account = await self.alpaca.get_account()
            
            # Get positions
            positions = await self.alpaca.get_positions()
            
            # Get recent trades
            recent_trades = await self.db.get_recent_trades(20)
            
            # Get performance metrics
            metrics = await self.db.get_performance_metrics(30)
            
            # Calculate portfolio metrics
            total_pl = sum(pos['unrealized_pl'] for pos in positions)
            total_value = sum(pos['market_value'] for pos in positions)
            
            # Position breakdown
            position_breakdown = [
                {
                    "symbol": pos['symbol'],
                    "value": pos['market_value'],
                    "pl": pos['unrealized_pl'],
                    "pl_pct": pos['unrealized_plpc'] * 100
                }
                for pos in positions
            ]
            
            return {
                "account": {
                    "portfolio_value": account['portfolio_value'],
                    "cash": account['cash'],
                    "buying_power": account['buying_power']
                },
                "positions": {
                    "count": len(positions),
                    "total_value": total_value,
                    "total_pl": total_pl
                },
                "position_breakdown": position_breakdown,
                "performance": metrics,
                "recent_trades": recent_trades,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error generating dashboard data: {e}")
            return {"error": str(e)}
    
    async def run_premarket_analysis(self, watchlist: List[str]) -> Dict[str, Any]:
        """
        Run pre-market analysis 30-45 minutes before market open.
        Analyzes watchlist and provides actionable opportunities.
        
        Args:
            watchlist: List of symbols to analyze
            
        Returns:
            Pre-market analysis with opportunities
        """
        try:
            from services import get_llm_service
            from datetime import date
            
            logger.info("☀️ Starting pre-market analysis")
            
            llm = get_llm_service()
            opportunities = []
            
            # Use bulk snapshots for pre-market analysis - much faster!
            logger.info(f"📸 Getting pre-market snapshots for {len(watchlist[:10])} symbols...")
            snapshots = await self.alpaca.get_snapshots_bulk(watchlist[:10])
            
            for symbol, snapshot in snapshots.items():
                try:
                    # Use Alpaca's real data
                    current_price = snapshot['price']
                    prev_close = snapshot['prev_close']
                    premarket_change = snapshot['change_1d_pct']  # From Alpaca!
                    
                    # Determine bias
                    if premarket_change > 1.0:
                        bias = "bullish"
                        rationale = f"Up {premarket_change:.2f}% pre-market. Look for continuation above VWAP."
                    elif premarket_change < -1.0:
                        bias = "bearish"
                        rationale = f"Down {abs(premarket_change):.2f}% pre-market. Watch for support levels."
                    else:
                        bias = "neutral"
                        rationale = f"Flat pre-market ({premarket_change:+.2f}%). Wait for volume breakout."
                    
                    # Calculate entry/stop/target
                    entry = current_price
                    if bias == "bullish":
                        target = entry * 1.03  # 3% target
                        stop = entry * 0.98    # 2% stop
                    elif bias == "bearish":
                        target = entry * 0.97  # 3% target (short)
                        stop = entry * 1.02    # 2% stop
                    else:
                        target = entry * 1.02
                        stop = entry * 0.99
                    
                    opportunities.append({
                        'symbol': symbol,
                        'bias': bias,
                        'rationale': rationale,
                        'entry': entry,
                        'stop': stop,
                        'target': target,
                        'premarket_change': premarket_change
                    })
                    
                except Exception as e:
                    logger.warning(f"Error analyzing {symbol}: {e}")
                    continue
            
            # Sort by absolute pre-market change (most volatile first)
            opportunities.sort(key=lambda x: abs(x['premarket_change']), reverse=True)
            
            return {
                'status': 'success',
                'date': date.today().isoformat(),
                'opportunities': opportunities[:5],  # Top 5
                'analyzed_count': len(watchlist),
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error in pre-market analysis: {e}")
            return {
                'status': 'error',
                'error': str(e)
            }
    
    async def generate_aftermarket_summary(self) -> Dict[str, Any]:
        """
        Generate after-market summary using GPT-4-mini.
        Summarizes the day's trading activity and performance.
        
        Returns:
            After-market summary with P&L and observations
        """
        try:
            from services import get_llm_service
            from datetime import date
            import json
            
            logger.info("🌙 Generating after-market summary")
            
            # Get today's trades
            trades = await self.db.get_recent_trades(100)
            today = date.today().isoformat()
            today_trades = [t for t in trades if t['timestamp'].startswith(today)]
            
            # Get daily stats
            stats = await self.db.get_daily_stats(today)
            
            # Calculate metrics
            wins = sum(1 for t in today_trades if t.get('action') == 'sell' and float(t.get('total_value', 0)) > 0)
            losses = sum(1 for t in today_trades if t.get('action') == 'sell' and float(t.get('total_value', 0)) < 0)
            net_pnl = sum(float(t.get('total_value', 0)) for t in today_trades if t.get('action') == 'sell')
            
            # Get current positions
            positions = await self.alpaca.get_positions()
            open_positions = len(positions)
            
            # Prepare data for GPT-4-mini
            summary_data = {
                'date': today,
                'total_trades': len(today_trades),
                'wins': wins,
                'losses': losses,
                'net_pnl': net_pnl,
                'open_positions': open_positions,
                'trades': [
                    {
                        'symbol': t['symbol'],
                        'action': t['action'],
                        'quantity': t['quantity'],
                        'price': t['price'],
                        'value': t['total_value']
                    }
                    for t in today_trades[:10]  # Last 10 trades
                ]
            }
            
            # Generate AI summary with strategy comparison using GPT-4-mini
            llm = get_llm_service()
            prompt = f"""Analyze this trading day and provide a detailed summary with strategy comparison:

Date: {today}
Total Trades: {len(today_trades)}
Wins: {wins} | Losses: {losses}
Net P&L: ${net_pnl:.2f}
Open Positions: {open_positions}

Trades Today:
{json.dumps(summary_data['trades'], indent=2)}

For EACH trade, analyze:
1. What we did (entry/exit timing, hold duration)
2. Actual result (profit/loss %)
3. What optimal strategy would have been (better entry/exit points)
4. Missed opportunity or avoided loss (dollar amount)

Then provide:
- Overall execution quality (% optimal)
- Top improvement area
- One actionable insight for tomorrow

Format as:
TRADE ANALYSIS:
[Symbol]: What we did | Result | Optimal strategy | Impact

OVERALL:
Execution Quality: X% optimal
Key Improvement: [area]
Tomorrow's Focus: [insight]

Keep it professional and analyst-style."""
            
            try:
                # Use GPT-4-mini for cost efficiency (increased tokens for detailed analysis)
                response = await llm.generate_completion(
                    prompt=prompt,
                    model="gpt-4o-mini",
                    max_tokens=800
                )
                ai_summary = response.strip()
            except Exception as e:
                logger.warning(f"AI summary failed, using template: {e}")
                ai_summary = f"Completed {len(today_trades)} trades with {wins} wins and {losses} losses. Net P&L: ${net_pnl:.2f}. {open_positions} positions remain open."
            
            # Identify top observations
            notes = []
            if net_pnl > 100:
                notes.append("Strong profitable day")
            elif net_pnl < -100:
                notes.append("Review risk management")
            
            if wins > losses * 2:
                notes.append("Excellent win rate")
            elif losses > wins * 2:
                notes.append("Consider tightening entry criteria")
            
            if open_positions > 5:
                notes.append("High exposure - monitor closely")
            
            return {
                'status': 'success',
                'date': today,
                'summary': ai_summary,
                'trades': {
                    'total': len(today_trades),
                    'wins': wins,
                    'losses': losses,
                    'net_pnl': net_pnl
                },
                'notes': ' | '.join(notes) if notes else 'Standard trading day',
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error generating after-market summary: {e}")
            return {
                'status': 'error',
                'error': str(e)
            }
