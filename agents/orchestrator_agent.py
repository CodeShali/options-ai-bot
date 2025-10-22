"""
Orchestrator Agent - Coordinates all other agents and manages workflow.
"""
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
from loguru import logger

from agents.base_agent import BaseAgent
from agents.data_pipeline_agent import DataPipelineAgent
from agents.strategy_agent import StrategyAgent
from agents.risk_manager_agent import RiskManagerAgent
from agents.execution_agent import ExecutionAgent
from agents.monitor_agent import MonitorAgent
from services import get_database_service, get_cache_service, get_api_tracker
from config import settings
from bot.discord_helpers import (
    format_existing_position_message,
    format_order_submitted_message,
    format_order_accepted_message,
    format_order_filled_message,
)


class OrchestratorAgent(BaseAgent):
    """Main orchestrator that coordinates all trading agents."""
    
    def __init__(self):
        """Initialize the orchestrator agent."""
        super().__init__("Orchestrator")
        
        # Initialize all agents
        self.data_pipeline = DataPipelineAgent()
        self.strategy = StrategyAgent()
        self.risk_manager = RiskManagerAgent()
        self.execution = ExecutionAgent()
        self.monitor = MonitorAgent()
        
        # Initialize Tara services
        self.db = get_database_service()
        self.cache = get_cache_service()
        self.api_tracker = get_api_tracker()
        
        self.paused = False
        self.discord_bot = None  # Will be set by main
        
        logger.info("🌟 TARA Orchestrator initialized with all agents")
    
    async def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process orchestration request.
        
        Args:
            data: Request data with 'action'
            
        Returns:
            Processing result
        """
        action = data.get("action")
        
        if action == "scan_and_trade":
            return await self.scan_and_trade()
        elif action == "monitor_and_exit":
            return await self.monitor_and_exit()
        elif action == "manual_trade":
            symbol = data.get("symbol")
            return await self.manual_trade(symbol)
        elif action == "emergency_stop":
            return await self.emergency_stop()
        else:
            return {"error": f"Unknown action: {action}"}
    
    async def start(self):
        """Start the orchestrator and all agents."""
        await super().start()
        
        # Check pause state from database
        pause_state = await self.db.get_system_state("paused")
        self.paused = pause_state == "true"
        if self.paused:
            logger.warning("⚠️ System is PAUSED - trades will not execute")
        else:
            logger.info("✅ System is ACTIVE - ready to trade")
        
        # Start all agents
        await self.data_pipeline.start()
        await self.strategy.start()
        await self.risk_manager.start()
        await self.execution.start()
        await self.monitor.start()
        
        logger.info("All agents started")
    
    async def stop(self):
        """Stop the orchestrator and all agents."""
        await super().stop()
        
        # Stop all agents
        await self.data_pipeline.stop()
        await self.strategy.stop()
        await self.risk_manager.stop()
        await self.execution.stop()
        await self.monitor.stop()
        
        logger.info("All agents stopped")
    
    def _get_position_type(self, position: Dict) -> str:
        """
        Determine position type from position data.
        
        Returns:
            'stock', 'call', or 'put'
        """
        symbol = position.get('symbol', '')
        
        # Check if it's an option (has strike/expiry or option indicators)
        if 'strike' in position or 'option_type' in position:
            option_type = position.get('option_type', '').lower()
            if 'call' in option_type:
                return 'call'
            elif 'put' in option_type:
                return 'put'
        
        # Check symbol format (options have special format)
        if len(symbol) > 6:  # Options symbols are longer
            # Try to detect from symbol
            if 'C' in symbol[-9:]:  # Call indicator in option symbol
                return 'call'
            elif 'P' in symbol[-9:]:  # Put indicator in option symbol
                return 'put'
        
        # Default to stock
        return 'stock'
    
    async def should_skip_analysis(self, symbol: str, trade_type: str = 'stock') -> Dict[str, Any]:
        """
        Intelligent check if we should skip analyzing this symbol.
        
        Args:
            symbol: Stock symbol
            trade_type: 'stock', 'call', or 'put'
        
        Returns:
            {
                'skip': bool,
                'reason': str,
                'existing_position': dict or None,
                'suggestion': str
            }
        """
        try:
            # Check cache first
            cache_key = f"position_{symbol}"
            cached = self.cache.get(cache_key)
            
            if cached:
                position = cached
                logger.debug(f"🟢 Cache hit: Found position for {symbol}")
            else:
                # Check broker
                try:
                    from services import get_alpaca_service
                    alpaca = get_alpaca_service()
                    positions = await alpaca.get_positions()
                    
                    # Find position for this symbol
                    position = None
                    for pos in positions:
                        if pos['symbol'] == symbol:
                            position = pos
                            # Cache it
                            await self.cache.set(cache_key, position)
                            break
                except Exception as e:
                    logger.warning(f"Error checking positions: {e}")
                    position = None
            
            if not position:
                return {
                    'skip': False,
                    'reason': 'No existing position',
                    'existing_position': None,
                    'suggestion': 'New position opportunity'
                }
            
            # Check if position is FILLED (not pending)
            status = position.get('status', 'unknown').lower()
            if status not in ['filled', 'active']:
                return {
                    'skip': False,
                    'reason': f'Position status: {status} (not filled)',
                    'existing_position': None,
                    'suggestion': 'Position not yet active'
                }
            
            # Determine existing position type
            existing_type = self._get_position_type(position)
            
            # Apply intelligent rules
            if existing_type == trade_type:
                # Same type - check if we should scale in
                current_size = float(position.get('market_value', 0))
                max_size = settings.max_position_size
                
                if current_size >= max_size * 0.8:  # 80% of max
                    return {
                        'skip': True,
                        'reason': f'Already have {existing_type} position at {current_size/max_size*100:.0f}% of max size',
                        'existing_position': position,
                        'suggestion': 'Consider taking profits or wait for exit signal'
                    }
                else:
                    return {
                        'skip': False,
                        'reason': f'Can scale into existing {existing_type} position',
                        'existing_position': position,
                        'suggestion': f'Scale-in opportunity (current: {current_size/max_size*100:.0f}% of max)'
                    }
            
            # Different type - allow for hedging/spreads
            if existing_type == 'stock' and trade_type in ['put', 'call']:
                return {
                    'skip': False,
                    'reason': f'Allow options on existing stock position (hedging)',
                    'existing_position': position,
                    'suggestion': f'Options strategy on {symbol} stock position'
                }
            
            if existing_type in ['call', 'put'] and trade_type == 'stock':
                return {
                    'skip': False,
                    'reason': f'Allow stock on existing options position',
                    'existing_position': position,
                    'suggestion': f'Stock position with existing {existing_type}'
                }
            
            # Default: allow
            return {
                'skip': False,
                'reason': 'Different position type',
                'existing_position': position,
                'suggestion': 'Compatible with existing position'
            }
            
        except Exception as e:
            logger.error(f"Error in should_skip_analysis: {e}")
            return {
                'skip': False,
                'reason': f'Error checking: {str(e)}',
                'existing_position': None,
                'suggestion': 'Proceed with caution'
            }
    
    async def scan_and_trade(self) -> Dict[str, Any]:
        """
        Main trading workflow: scan for opportunities and execute trades.
        
        Returns:
            Workflow result
        """
        try:
            if self.paused:
                logger.info("System is paused, skipping scan")
                return {"status": "paused", "message": "System is paused"}
            
            logger.info("=== Starting scan and trade workflow ===")
            
            # Step 1: Check circuit breaker
            circuit_breaker = await self.risk_manager.process({
                "action": "check_circuit_breaker"
            })
            
            if circuit_breaker.get('triggered'):
                logger.warning("⚠️ Circuit breaker triggered, stopping workflow")
                
                # Use Tara's formatted circuit breaker message
                from bot.discord_helpers import format_circuit_breaker_message
                cb_message = format_circuit_breaker_message(
                    reason=circuit_breaker.get('reason', 'Daily loss limit exceeded'),
                    duration=circuit_breaker.get('duration', 'remainder of trading day'),
                    actions=circuit_breaker.get('actions', [])
                )
                
                await self._send_discord_alert(cb_message, {})
                return {
                    "status": "circuit_breaker",
                    "message": "Circuit breaker triggered",
                    "data": circuit_breaker
                }
            
            # Step 2: Check position limits
            position_limits = await self.risk_manager.process({
                "action": "check_position_limits"
            })
            
            if position_limits['positions_available'] <= 0:
                logger.info("No available position slots")
                return {
                    "status": "no_slots",
                    "message": "Maximum positions reached",
                    "data": position_limits
                }
            
            # Step 3: Scan for opportunities with detailed logging
            logger.info("🔍 Starting comprehensive market scan...")
            logger.info("📊 Scanning strategies: Momentum, Mean Reversion, Breakout, Volume Analysis")
            logger.info("🎯 Looking for: High-probability setups with 70%+ confidence")
            
            scan_result = await self.data_pipeline.process({
                "action": "scan_opportunities"
            })
            
            opportunities = scan_result.get('opportunities', [])
            symbols_scanned = scan_result.get('symbols_scanned', [])
            
            # Handle case where symbols_scanned might be an int or list
            if isinstance(symbols_scanned, int):
                num_symbols = symbols_scanned
            elif isinstance(symbols_scanned, list):
                num_symbols = len(symbols_scanned)
            else:
                num_symbols = 0
            
            # Detailed scan summary
            logger.info(f"📈 Scan completed: {num_symbols} symbols analyzed")
            logger.info(f"🎯 Opportunities found: {len(opportunities)} total")
            
            # Categorize opportunities by confidence
            high_conf = [o for o in opportunities if o.get('confidence', 0) >= 70]
            medium_conf = [o for o in opportunities if 50 <= o.get('confidence', 0) < 70]
            low_conf = [o for o in opportunities if o.get('confidence', 0) < 50]
            
            logger.info(f"   • High confidence (70%+): {len(high_conf)}")
            logger.info(f"   • Medium confidence (50-69%): {len(medium_conf)}")
            logger.info(f"   • Low confidence (<50%): {len(low_conf)}")
            
            if not opportunities:
                logger.info("❌ No opportunities found - Market conditions:")
                logger.info("   • Low volatility or unclear technical setups")
                logger.info("   • Waiting for stronger momentum signals")
                logger.info("   • All scanned symbols outside entry criteria")
                return {
                    "status": "no_opportunities",
                    "message": "No trading opportunities found",
                    "scan_details": {
                        "symbols_scanned": num_symbols,
                        "total_opportunities": 0,
                        "reasons": ["Low volatility", "No clear technical setups", "Waiting for momentum"]
                    }
                }
            
            logger.info(f"✅ Scan successful: {len(opportunities)} opportunities identified")
            
            # Only send notifications for high-confidence opportunities (70%+)
            high_confidence_opps = [
                opp for opp in opportunities 
                if opp.get('confidence', 0) >= 70 and opp.get('action') in ['BUY_STOCK', 'BUY_CALL', 'BUY_PUT']
            ]
            
            # Prevent duplicate alerts - check if we've already alerted about these symbols recently
            if not hasattr(self, '_recent_alerts'):
                self._recent_alerts = {}
            
            # Filter out symbols we've alerted about in the last 30 minutes
            from datetime import datetime, timedelta
            now = datetime.now()
            new_opps = []
            for opp in high_confidence_opps:
                symbol = opp['symbol']
                last_alert = self._recent_alerts.get(symbol)
                if not last_alert or (now - last_alert) > timedelta(minutes=30):
                    new_opps.append(opp)
                    self._recent_alerts[symbol] = now
            
            if new_opps:
                # Build concise message for NEW high-confidence opportunities only
                alert_message = f"🎯 **{len(new_opps)} New High-Confidence Trading Opportunity{'ies' if len(new_opps) > 1 else 'y'} Found**\n\n"
                
                for i, opp in enumerate(new_opps[:2], 1):  # Show top 2 only
                    alert_message += f"**{i}. {opp['symbol']}** - ${opp['current_price']:.2f}\n"
                    alert_message += f"   • **{opp['action']}** ({opp['confidence']}% confidence)\n"
                    
                    # Add AI reasoning (shortened)
                    reasoning = opp.get('reasoning', 'Strong technical setup detected')
                    alert_message += f"   • 🤖 **AI:** {reasoning[:150]}{'...' if len(reasoning) > 150 else ''}\n\n"
                
                alert_message += "💡 *Ask me: 'Should I buy AAPL?' or 'Set stop loss on my positions' for personalized advice*"
                
                await self._send_discord_alert(alert_message, {})
            
            # Intelligent scanner already has Claude's analysis, so use those recommendations directly
            # Filter for high confidence BUY signals from intelligent scanner
            buy_signals = [
                opp for opp in opportunities
                if opp['action'] in ['BUY_STOCK', 'BUY_CALL', 'BUY_PUT'] and opp['confidence'] >= 70
            ]
            
            if not buy_signals:
                logger.info("No strong buy signals from intelligent scanner")
                return {
                    "status": "no_signals",
                    "message": "No strong buy signals found (confidence < 70%)",
                    "opportunities": opportunities
                }
            
            logger.info(f"Found {len(buy_signals)} buy signals")
            
            # Send notification about buy signals
            auto_trading_status = "ENABLED ✅" if settings.auto_trading_enabled else "DISABLED ⏸️"
            await self._send_discord_alert(
                f"🤖 AI Analysis: {len(buy_signals)} BUY signal(s) detected!\n"
                f"Auto-Trading: {auto_trading_status}",
                {
                    "signals": [
                        {
                            "symbol": sig['symbol'],
                            "confidence": f"{sig['confidence']}%",
                            "risk": sig.get('risk_level', 'MEDIUM')
                        }
                        for sig in buy_signals
                    ]
                }
            )
            
            # Step 5: Execute trades for approved signals (only if auto-trading enabled)
            executed_trades = []
            
            if not settings.auto_trading_enabled:
                logger.info("Auto-trading disabled - sending alerts only")
                return {
                    "status": "alerts_only",
                    "message": f"Found {len(buy_signals)} signals but auto-trading is disabled",
                    "signals": buy_signals
                }
            
            for analysis in buy_signals[:position_limits['positions_available']]:
                symbol = analysis['symbol']
                action = analysis['action']
                
                # Determine trade type from action
                trade_type = 'stock'
                if 'CALL' in action:
                    trade_type = 'call'
                elif 'PUT' in action:
                    trade_type = 'put'
                
                # Intelligent duplicate check
                skip_check = await self.should_skip_analysis(symbol, trade_type)
                
                if skip_check['skip']:
                    logger.info(f"⏭️ Skipping {symbol} {trade_type}: {skip_check['reason']}")
                    
                    # Send notification to Discord
                    if self.discord_bot:
                        message = (
                            f"⏭️ **Skipped Trade: {symbol}**\n"
                            f"**Type:** {trade_type.upper()}\n"
                            f"**Reason:** {skip_check['reason']}\n"
                            f"**Suggestion:** {skip_check['suggestion']}"
                        )
                        await self._send_discord_alert(message, {}, symbol=symbol)
                    
                    continue
                
                # If we have existing position but not skipping, note it
                if skip_check['existing_position']:
                    logger.info(f"📊 {symbol}: {skip_check['reason']} - {skip_check['suggestion']}")
                    
                    # Notify about scale-in or hedging opportunity
                    if self.discord_bot and not skip_check['skip']:
                        message = (
                            f"📊 **Position Update: {symbol}**\n"
                            f"**Strategy:** {skip_check['suggestion']}\n"
                            f"**Note:** {skip_check['reason']}"
                        )
                        await self._send_discord_alert(message, {}, symbol=symbol)
                
                # Decide instrument type (stock vs options)
                # The analysis IS the opportunity from intelligent scanner
                instrument_decision = await self.strategy.decide_instrument_type(
                    analysis, 
                    analysis  # Pass the full analysis as the opportunity
                )
                
                if instrument_decision['instrument'] == 'none':
                    logger.info(f"Skipping {analysis['symbol']}: {instrument_decision['reasoning']}")
                    continue
                
                # Handle options trading
                if instrument_decision['instrument'] == 'option':
                    # Select options contract
                    contract = await self.strategy.select_options_contract(
                        symbol=analysis['symbol'],
                        option_type=instrument_decision['option_type'],
                        current_price=analysis.get('current_price', analysis.get('price', 0))
                    )
                    
                    if 'error' in contract:
                        logger.error(f"Error selecting options contract: {contract['error']}")
                        continue
                    
                    # Calculate contracts
                    position_size = await self.risk_manager.calculate_options_position_size(
                        analysis,
                        contract['premium']
                    )
                    
                    if position_size['contracts'] == 0:
                        logger.info(f"No contracts for {analysis['symbol']}: {position_size.get('reason')}")
                        continue
                    
                    # Prepare options trade
                    trade = {
                        "underlying": analysis['symbol'],
                        "option_type": contract['option_type'],
                        "strike": contract['strike'],
                        "expiration": contract['expiration'],
                        "premium": contract['premium'],
                        "contracts": position_size['contracts'],
                        "dte": contract['dte']
                    }
                    
                    # Validate options trade
                    validation = await self.risk_manager.validate_options_trade(trade)
                    
                    if not validation['approved']:
                        logger.warning(f"Options trade not approved: {validation['reason']}")
                        await self._send_discord_alert(
                            f"⛔ Options trade rejected: {trade['underlying']}",
                            {"reason": validation['reason']}
                        )
                        continue
                    
                    # Execute options trade
                    execution_result = await self.execution.execute_options_buy(trade)
                    
                    if execution_result['success']:
                        executed_trades.append(execution_result)
                        logger.info(f"🌟 TARA executed options trade: {trade['underlying']}")
                        
                        # Create thread
                        if self.discord_bot:
                            try:
                                await self.discord_bot.create_position_thread(
                                    symbol=f"{trade['underlying']} {trade['option_type'].upper()} ${trade['strike']}",
                                    entry_price=trade['premium'],
                                    quantity=trade['contracts']
                                )
                            except Exception as e:
                                logger.error(f"Error creating thread: {e}")
                        
                        # Send detailed options notification
                        option_details = (
                            f"🌟 **TARA EXECUTED OPTIONS TRADE**\n\n"
                            f"**Symbol:** {trade['underlying']}\n"
                            f"**Action:** BUY {trade['option_type'].upper()}\n"
                            f"**Strike:** ${trade['strike']:.2f}\n"
                            f"**Expiration:** {trade['expiration']}\n"
                            f"**DTE:** {trade['dte']} days\n"
                            f"**Contracts:** {trade['contracts']}\n"
                            f"**Premium:** ${trade['premium']:.2f} per contract\n"
                            f"**Total Cost:** ${validation['total_cost']:.2f}\n"
                            f"**Confidence:** {analysis['confidence']}%\n\n"
                            f"**🤖 AI Insight:** {analysis.get('reasoning', 'N/A')[:200]}...\n\n"
                            f"**Target:** ${analysis.get('target_price', 0):.2f}\n"
                            f"**Stop Loss:** ${analysis.get('stop_loss', 0):.2f}\n"
                            f"**Risk Level:** {analysis.get('risk_level', 'MEDIUM')}"
                        )
                        
                        await self._send_discord_alert(
                            option_details,
                            {},
                            symbol=trade['underlying']
                        )
                    else:
                        logger.error(f"Options execution failed: {execution_result.get('error')}")
                    
                    continue
                
                # Handle stock trading (existing code)
                position_size = await self.risk_manager.process({
                    "action": "calculate_position_size",
                    "analysis": analysis
                })
                
                if position_size.get('error'):
                    logger.error(f"Error calculating position size: {position_size['error']}")
                    continue
                
                # Prepare trade
                trade = {
                    "symbol": analysis['symbol'],
                    "action": "buy",
                    "quantity": position_size['quantity'],
                    "price": position_size['price'],
                    "notes": f"AI Analysis - Confidence: {analysis['confidence']}%"
                }
                
                # Validate trade
                validation = await self.risk_manager.process({
                    "action": "validate_trade",
                    "trade": trade
                })
                
                if not validation['approved']:
                    logger.warning(
                        f"Trade not approved for {trade['symbol']}: {validation['reason']}"
                    )
                    # Notify about rejected trade
                    await self._send_discord_alert(
                        f"⛔ Trade rejected: {trade['symbol']}",
                        {
                            "reason": validation['reason'],
                            "symbol": trade['symbol'],
                            "quantity": trade['quantity']
                        }
                    )
                    continue
                
                # Execute trade
                execution_result = await self.execution.process({
                    "action": "execute_buy",
                    "trade": trade
                })
                
                if execution_result['success']:
                    executed_trades.append(execution_result)
                    logger.info(f"🌟 TARA executed trade: {trade['symbol']}")
                    
                    # Create position thread in Discord
                    if self.discord_bot:
                        try:
                            await self.discord_bot.create_position_thread(
                                symbol=trade['symbol'],
                                entry_price=trade['price'],
                                quantity=trade['quantity']
                            )
                        except Exception as e:
                            logger.error(f"Error creating position thread: {e}")
                    
                    # Send detailed Discord notification
                    trade_details = (
                        f"🌟 **TARA EXECUTED TRADE**\n\n"
                        f"**Symbol:** {trade['symbol']}\n"
                        f"**Action:** BUY STOCK\n"
                        f"**Quantity:** {trade['quantity']} shares\n"
                        f"**Price:** ${trade['price']:.2f}\n"
                        f"**Total:** ${trade['quantity'] * trade['price']:.2f}\n"
                        f"**Confidence:** {analysis['confidence']}%\n\n"
                        f"**🤖 AI Insight:** {analysis.get('reasoning', 'N/A')[:200]}...\n\n"
                        f"**Target:** ${analysis.get('target_price', 0):.2f}\n"
                        f"**Stop Loss:** ${analysis.get('stop_loss', 0):.2f}\n"
                        f"**Risk Level:** {analysis.get('risk_level', 'MEDIUM')}"
                    )
                    
                    await self._send_discord_alert(
                        trade_details,
                        {},
                        symbol=trade['symbol']  # Send to position thread
                    )
                else:
                    logger.error(
                        f"Trade execution failed for {trade['symbol']}: "
                        f"{execution_result.get('error')}"
                    )
            
            logger.info(f"=== Workflow complete: {len(executed_trades)} trades executed ===")
            
            # Send summary if trades were executed
            if executed_trades:
                summary = (
                    f"🌟 **TARA SCAN COMPLETE**\n\n"
                    f"**Opportunities Found:** {len(opportunities)}\n"
                    f"**Signals Generated:** {len(buy_signals)}\n"
                    f"**Trades Executed:** {len(executed_trades)}\n\n"
                    f"✅ All trades executed successfully!\n"
                    f"Monitor will track positions every 2 minutes."
                )
                await self._send_discord_alert(summary, {})
            
            return {
                "status": "success",
                "opportunities_found": len(opportunities),
                "signals_generated": len(buy_signals),
                "trades_executed": len(executed_trades),
                "executed_trades": executed_trades
            }
            
        except Exception as e:
            logger.error(f"Error in scan and trade workflow: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def monitor_and_exit(self) -> Dict[str, Any]:
        """
        Monitor positions and execute exits when needed.
        
        NOTE: This runs INDEPENDENTLY of auto_trading_enabled.
        Position monitoring and exits ALWAYS work, even if auto-trading is disabled.
        Only NEW trade entries are affected by auto_trading_enabled.
        
        Returns:
            Workflow result
        """
        try:
            if self.paused:
                return {"status": "paused", "message": "System is paused"}
            
            logger.info("=== Starting monitor and exit workflow ===")
            
            # Step 1: Monitor all positions
            monitor_result = await self.monitor.process({
                "action": "monitor_positions"
            })
            
            alerts = monitor_result.get('alerts', [])
            
            if not alerts:
                logger.info("No alerts generated")
                return {
                    "status": "no_alerts",
                    "positions_monitored": monitor_result['positions_monitored']
                }
            
            logger.info(f"Generated {len(alerts)} alerts")
            
            # Step 2: Process alerts that require action
            exits_executed = []
            
            for alert in alerts:
                if alert['action_required'] not in ['SELL', 'CLOSE']:
                    continue
                
                symbol = alert['symbol']
                position = alert['position']
                
                # Handle options expiration (force close)
                if alert['type'] == 'OPTIONS_EXPIRATION':
                    option_symbol = alert['option_symbol']
                    execution_result = await self.execution.close_options_position(
                        option_symbol,
                        reason=f"Expiration in {alert['dte']} days"
                    )
                    
                    if execution_result['success']:
                        exits_executed.append(execution_result)
                        logger.info(f"Options position closed due to expiration: {option_symbol}")
                        
                        # Notify
                        await self._send_discord_alert(
                            f"⏰ OPTIONS CLOSED: {symbol} (expiration approaching)",
                            {"reason": alert['reasoning']},
                            symbol=symbol
                        )
                        
                        # Close thread
                        if self.discord_bot:
                            try:
                                await self.discord_bot.close_position_thread(
                                    symbol,
                                    position.get('unrealized_pl', 0)
                                )
                            except Exception as e:
                                logger.error(f"Error closing thread: {e}")
                    
                    continue
                
                # Get current market data
                quote = await self.data_pipeline.process({
                    "action": "get_quote",
                    "symbol": symbol
                })
                
                market_data = {
                    "current_price": quote.get('ask_price', position.get('current_price', 0)),
                    "bid_price": quote.get('bid_price'),
                    "ask_price": quote.get('ask_price')
                }
                
                # Get AI analysis for exit
                exit_analysis = await self.strategy.process({
                    "action": "analyze_exit",
                    "position": position,
                    "market_data": market_data
                })
                
                # If AI confirms exit or it's a stop loss, execute
                should_exit = (
                    exit_analysis['action'] == 'EXIT' or
                    alert['type'] == 'STOP_LOSS'
                )
                
                if should_exit:
                    # Check if it's an options position
                    if 'option_symbol' in alert:
                        # Close options position
                        execution_result = await self.execution.close_options_position(
                            alert['option_symbol'],
                            reason=alert['message']
                        )
                    else:
                        # Close stock position
                        execution_result = await self.execution.process({
                            "action": "close_position",
                            "symbol": symbol,
                            "reason": alert['message']
                        })
                    
                    if execution_result['success']:
                        exits_executed.append(execution_result)
                        logger.info(f"Exit executed: {symbol}")
                        
                        # Send Discord notification to thread
                        pl = execution_result['profit_loss']
                        emoji = "🟢" if pl > 0 else "🔴"
                        await self._send_discord_alert(
                            f"{emoji} SELL executed: {symbol} - P/L: ${pl:.2f}",
                            {"reason": alert['message']},
                            symbol=symbol  # Send to position thread
                        )
                        
                        # Close position thread
                        if self.discord_bot:
                            try:
                                await self.discord_bot.close_position_thread(symbol, pl)
                            except Exception as e:
                                logger.error(f"Error closing position thread: {e}")
                    else:
                        logger.error(
                            f"Exit execution failed for {symbol}: "
                            f"{execution_result.get('error')}"
                        )
            
            logger.info(f"=== Monitoring complete: {len(exits_executed)} exits executed ===")
            
            return {
                "status": "success",
                "alerts_generated": len(alerts),
                "exits_executed": len(exits_executed),
                "executed_exits": exits_executed
            }
            
        except Exception as e:
            logger.error(f"Error in monitor and exit workflow: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def manual_trade(self, symbol: str) -> Dict[str, Any]:
        """
        Execute a manual trade for a specific symbol.
        
        Args:
            symbol: Stock symbol to trade
            
        Returns:
            Trade result
        """
        try:
            logger.info(f"Processing manual trade for {symbol}")
            
            # Get market data
            quote = await self.data_pipeline.process({
                "action": "get_quote",
                "symbol": symbol
            })
            
            if quote.get('error'):
                return {
                    "status": "error",
                    "error": f"Could not get quote for {symbol}"
                }
            
            # Create opportunity
            opportunity = {
                "symbol": symbol,
                "current_price": quote['ask_price'],
                "quote": quote,
                "bars": [],
                "price_change_pct": 0,
                "volume_ratio": 1.0,
                "sma_20": quote['ask_price'],
                "score": 0
            }
            
            # Analyze
            analysis = await self.strategy.process({
                "action": "analyze_opportunity",
                "opportunity": opportunity
            })
            
            if analysis['recommendation'] != 'BUY':
                return {
                    "status": "not_recommended",
                    "message": f"AI does not recommend buying {symbol}",
                    "analysis": analysis
                }
            
            # Calculate position size
            position_size = await self.risk_manager.process({
                "action": "calculate_position_size",
                "analysis": analysis
            })
            
            # Prepare and validate trade
            trade = {
                "symbol": symbol,
                "action": "buy",
                "quantity": position_size['quantity'],
                "price": position_size['price'],
                "notes": "Manual trade"
            }
            
            validation = await self.risk_manager.process({
                "action": "validate_trade",
                "trade": trade
            })
            
            if not validation['approved']:
                return {
                    "status": "not_approved",
                    "message": validation['reason'],
                    "trade": trade
                }
            
            # Execute
            execution_result = await self.execution.process({
                "action": "execute_buy",
                "trade": trade
            })
            
            return {
                "status": "success" if execution_result['success'] else "failed",
                "execution": execution_result,
                "analysis": analysis
            }
            
        except Exception as e:
            logger.error(f"Error in manual trade: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def emergency_stop(self) -> Dict[str, Any]:
        """
        Emergency stop: close all positions and pause system.
        
        Returns:
            Emergency stop result
        """
        try:
            logger.warning("=== EMERGENCY STOP INITIATED ===")
            
            # Pause system
            self.paused = True
            await self.db.set_system_state("paused", "true")
            
            # Close all positions
            close_result = await self.execution.process({
                "action": "close_all_positions",
                "reason": "Emergency stop"
            })
            
            # Send Discord notification
            await self._send_discord_alert(
                "🚨 EMERGENCY STOP: All positions closed, system paused",
                close_result
            )
            
            logger.warning("=== Emergency stop complete ===")
            
            return {
                "status": "success",
                "message": "Emergency stop executed",
                "close_result": close_result
            }
            
        except Exception as e:
            logger.error(f"Error in emergency stop: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def set_discord_bot(self, bot):
        """Set the Discord bot reference."""
        self.discord_bot = bot
        
        # Register monitor alert callback
        async def alert_callback(alert):
            # Build alert message with reasoning
            alert_data = {
                "type": alert['type'],
                "severity": alert.get('severity', 'INFO'),
                "action_required": alert.get('action_required', 'NONE')
            }
            
            # Add reasoning if available
            if 'reasoning' in alert:
                alert_data['reasoning'] = alert['reasoning']
            
            # Add position details if available
            if 'position' in alert:
                pos = alert['position']
                if isinstance(pos, dict):
                    alert_data['position'] = {
                        'symbol': pos.get('symbol'),
                        'qty': pos.get('qty'),
                        'entry_price': pos.get('entry_price') or pos.get('avg_entry_price'),
                        'current_price': pos.get('current_price'),
                        'unrealized_pl': pos.get('unrealized_pl'),
                        'unrealized_plpc': pos.get('unrealized_plpc')
                    }
            
            # Extract symbol for thread routing
            symbol = alert.get('symbol')
            await self._send_discord_alert(alert['message'], alert_data, symbol=symbol)
        
        self.monitor.register_alert_callback(alert_callback)
    
    async def _send_discord_alert(self, message: str, data: Optional[Dict[str, Any]] = None, symbol: Optional[str] = None):
        """Send alert to Discord."""
        if self.discord_bot:
            try:
                full_message = message
                
                if data:
                    # Format reasoning separately for better readability
                    if 'reasoning' in data:
                        full_message += f"\n\n**Why?** {data['reasoning']}"
                        # Remove reasoning from the JSON to avoid duplication
                        data_copy = {k: v for k, v in data.items() if k != 'reasoning'}
                    else:
                        data_copy = data
                    
                    # Only add JSON if there's additional data
                    if data_copy:
                        import json
                        full_message += f"\n```json\n{json.dumps(data_copy, indent=2)}\n```"
                
                await self.discord_bot.send_notification(full_message, symbol=symbol)
            except Exception as e:
                logger.error(f"Error sending Discord alert: {e}")
