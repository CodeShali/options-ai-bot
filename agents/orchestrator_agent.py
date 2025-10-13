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
from services import get_database_service


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
        
        self.db = get_database_service()
        self.paused = False
        self.discord_bot = None  # Will be set by main
        
        logger.info("Orchestrator initialized with all agents")
    
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
                logger.warning("Circuit breaker triggered, stopping workflow")
                await self._send_discord_alert(
                    "🚨 Circuit breaker triggered! Trading stopped.",
                    circuit_breaker
                )
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
            
            # Step 3: Scan for opportunities
            scan_result = await self.data_pipeline.process({
                "action": "scan_opportunities"
            })
            
            opportunities = scan_result.get('opportunities', [])
            
            if not opportunities:
                logger.info("No opportunities found")
                return {
                    "status": "no_opportunities",
                    "message": "No trading opportunities found"
                }
            
            logger.info(f"Found {len(opportunities)} opportunities")
            
            # Send detailed notification about opportunities found with Claude's reasoning
            if opportunities:
                # Build detailed message with Claude's analysis
                alert_message = f"🔍 **Scan Complete: {len(opportunities)} Opportunities Found**\n\n"
                
                for i, opp in enumerate(opportunities[:3], 1):  # Show top 3
                    rec = opp.get('recommendation', {})
                    alert_message += f"**{i}. {opp['symbol']}** - ${opp['current_price']:.2f}\n"
                    alert_message += f"   • Action: **{opp['action']}** ({opp['confidence']}% confidence)\n"
                    alert_message += f"   • Score: {opp['score']:.0f}/100\n"
                    
                    # Add momentum info
                    momentum = rec.get('momentum', {})
                    if momentum:
                        alert_message += f"   • Momentum: {momentum.get('direction', 'N/A')} {momentum.get('move_pct', 0):+.2f}% (15min)\n"
                        alert_message += f"   • Volume: {momentum.get('volume_ratio_5min', 0):.2f}x average\n"
                    
                    # Add Claude's reasoning
                    reasoning = opp.get('reasoning', 'No reasoning provided')
                    alert_message += f"   • **Claude's Analysis:** {reasoning[:200]}...\n"
                    
                    # Add entry/exit if available
                    if 'entry_strategy' in rec:
                        alert_message += f"   • Entry: {rec.get('entry_strategy', 'N/A')[:100]}\n"
                        alert_message += f"   • Target: ${rec.get('target_price', 0):.2f} | Stop: ${rec.get('stop_loss', 0):.2f}\n"
                        alert_message += f"   • Risk: {rec.get('risk_level', 'N/A')}\n"
                    
                    alert_message += "\n"
                
                alert_message += "📊 **Next Steps:**\n"
                alert_message += "• Review Claude's reasoning above\n"
                alert_message += "• Verify analysis aligns with market conditions\n"
                alert_message += "• Check if entry/exit makes sense\n"
                alert_message += "• Execute if confident\n"
                
                await self._send_discord_alert(alert_message, {})
            
            # Step 4: Analyze top opportunities
            top_opportunities = opportunities[:5]  # Analyze top 5
            
            analysis_result = await self.strategy.process({
                "action": "batch_analyze",
                "opportunities": top_opportunities
            })
            
            analyses = analysis_result.get('analyses', [])
            
            # Filter for BUY recommendations with high confidence
            buy_signals = [
                a for a in analyses
                if a['recommendation'] == 'BUY' and a['confidence'] >= 60
            ]
            
            if not buy_signals:
                logger.info("No strong buy signals")
                # Notify about analysis results
                await self._send_discord_alert(
                    "📊 AI Analysis complete: No strong buy signals",
                    {
                        "analyzed": len(analyses),
                        "buy_signals": 0,
                        "reason": "Confidence < 60% or HOLD/SELL recommendations"
                    }
                )
                return {
                    "status": "no_signals",
                    "message": "No strong buy signals found",
                    "analyses": analyses
                }
            
            logger.info(f"Found {len(buy_signals)} buy signals")
            
            # Send notification about buy signals
            await self._send_discord_alert(
                f"🤖 AI Analysis: {len(buy_signals)} BUY signal(s) detected!",
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
            
            # Step 5: Execute trades for approved signals
            executed_trades = []
            
            for analysis in buy_signals[:position_limits['positions_available']]:
                # Decide instrument type (stock vs options)
                instrument_decision = await self.strategy.decide_instrument_type(
                    analysis, 
                    analysis['opportunity']
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
                        current_price=analysis['opportunity']['current_price']
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
                        logger.info(f"Options trade executed: {trade['underlying']}")
                        
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
                        
                        # Notify
                        await self._send_discord_alert(
                            f"✅ OPTIONS BUY: {trade['contracts']} {trade['underlying']} "
                            f"{trade['option_type']} ${trade['strike']} exp {trade['expiration']} @ ${trade['premium']:.2f}",
                            {
                                "type": "options",
                                "confidence": analysis['confidence'],
                                "dte": trade['dte'],
                                "total_cost": validation['total_cost']
                            },
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
                    logger.info(f"Trade executed: {trade['symbol']}")
                    
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
                    
                    # Send Discord notification to thread
                    await self._send_discord_alert(
                        f"✅ BUY executed: {trade['quantity']} {trade['symbol']} @ ${trade['price']:.2f}",
                        {
                            "confidence": analysis['confidence'],
                            "reasoning": analysis['reasoning'][:200]
                        },
                        symbol=trade['symbol']  # Send to position thread
                    )
                else:
                    logger.error(
                        f"Trade execution failed for {trade['symbol']}: "
                        f"{execution_result.get('error')}"
                    )
            
            logger.info(f"=== Workflow complete: {len(executed_trades)} trades executed ===")
            
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
        Monitor positions and execute exits when conditions are met.
        
        Returns:
            Monitoring result
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
