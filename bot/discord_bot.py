"""
Discord bot for controlling the trading system.
"""
import asyncio
from typing import Optional, Dict, Any
import discord
from discord import app_commands
from discord.ext import commands
from loguru import logger

from config import settings, update_trading_mode
from services import get_alpaca_service, get_database_service


class TradingBot(commands.Bot):
    """Discord bot for trading system control."""
    
    def __init__(self):
        """Initialize the bot."""
        intents = discord.Intents.default()
        intents.message_content = True
        
        super().__init__(command_prefix="/", intents=intents)
        
        self.notification_channel_id = int(settings.discord_channel_id)
        self.system_paused = False
        self.orchestrator = None  # Will be set by main
        
        # Track position threads for organized updates
        self.position_threads = {}  # {symbol: thread_id}
        
        logger.info("Discord bot initialized")
    
    async def setup_hook(self):
        """Setup hook called when bot is ready."""
        await self.tree.sync()
        logger.info("Command tree synced")
    
    async def on_ready(self):
        """Called when bot is ready."""
        logger.info(f"Bot logged in as {self.user}")
        await self.send_notification("🤖 Trading bot is online!")
    
    async def send_notification(self, message: str, embed: Optional[discord.Embed] = None, symbol: Optional[str] = None):
        """
        Send a notification to the configured channel or position thread.
        
        Args:
            message: Message text
            embed: Optional embed
            symbol: Optional symbol to send to position thread
        """
        try:
            channel = self.get_channel(self.notification_channel_id)
            if not channel:
                logger.warning(f"Notification channel not found: {self.notification_channel_id}")
                return
            
            # If symbol provided, try to send to position thread
            if symbol and symbol in self.position_threads:
                try:
                    thread = channel.get_thread(self.position_threads[symbol])
                    if thread:
                        if embed:
                            await thread.send(message, embed=embed)
                        else:
                            await thread.send(message)
                        return
                except:
                    pass  # Fall back to main channel
            
            # Send to main channel
            if embed:
                await channel.send(message, embed=embed)
            else:
                await channel.send(message)
                
        except Exception as e:
            logger.error(f"Error sending notification: {e}")
    
    async def create_position_thread(self, symbol: str, entry_price: float, quantity: int) -> Optional[int]:
        """
        Create a thread for tracking a specific position.
        
        Args:
            symbol: Stock symbol
            entry_price: Entry price
            quantity: Quantity
            
        Returns:
            Thread ID if created
        """
        try:
            channel = self.get_channel(self.notification_channel_id)
            if not channel:
                return None
            
            # Create thread
            thread_name = f"📈 {symbol} - ${entry_price:.2f} x {quantity}"
            message = await channel.send(f"🆕 New position opened: **{symbol}**")
            thread = await message.create_thread(name=thread_name, auto_archive_duration=1440)  # 24 hours
            
            # Store thread ID
            self.position_threads[symbol] = thread.id
            
            # Send initial message to thread
            embed = discord.Embed(
                title=f"Position: {symbol}",
                description=f"Tracking updates for {symbol}",
                color=discord.Color.blue()
            )
            embed.add_field(name="Entry Price", value=f"${entry_price:.2f}", inline=True)
            embed.add_field(name="Quantity", value=str(quantity), inline=True)
            embed.add_field(name="Cost Basis", value=f"${entry_price * quantity:.2f}", inline=True)
            
            await thread.send(embed=embed)
            
            logger.info(f"Created position thread for {symbol}: {thread.id}")
            return thread.id
            
        except Exception as e:
            logger.error(f"Error creating position thread: {e}")
            return None
    
    async def close_position_thread(self, symbol: str, final_pl: float):
        """
        Close/archive a position thread.
        
        Args:
            symbol: Stock symbol
            final_pl: Final profit/loss
        """
        try:
            if symbol not in self.position_threads:
                return
            
            channel = self.get_channel(self.notification_channel_id)
            if not channel:
                return
            
            thread = channel.get_thread(self.position_threads[symbol])
            if thread:
                # Send final message
                emoji = "🟢" if final_pl > 0 else "🔴"
                await thread.send(
                    f"{emoji} **Position Closed**\n"
                    f"Final P/L: ${final_pl:,.2f}\n"
                    f"Thread will be archived."
                )
                
                # Archive thread
                await thread.edit(archived=True)
            
            # Remove from tracking
            del self.position_threads[symbol]
            logger.info(f"Closed position thread for {symbol}")
            
        except Exception as e:
            logger.error(f"Error closing position thread: {e}")
    
    def set_orchestrator(self, orchestrator):
        """Set the orchestrator reference."""
        self.orchestrator = orchestrator


# Create bot instance
bot = TradingBot()


@bot.tree.command(name="status", description="Get system status")
async def status_command(interaction: discord.Interaction):
    """Get system status."""
    await interaction.response.defer()
    
    try:
        alpaca = get_alpaca_service()
        db = get_database_service()
        
        # Get account info
        account = await alpaca.get_account()
        
        # Get positions
        positions = await alpaca.get_positions()
        
        # Get recent trades
        recent_trades = await db.get_recent_trades(5)
        
        # Get performance metrics
        metrics = await db.get_performance_metrics(30)
        
        # Create embed
        embed = discord.Embed(
            title="📊 Trading System Status",
            color=discord.Color.green() if not bot.system_paused else discord.Color.orange()
        )
        
        # System status
        status_text = "🟢 Active" if not bot.system_paused else "🟡 Paused"
        embed.add_field(
            name="System Status",
            value=f"{status_text}\nMode: {settings.trading_mode.upper()}",
            inline=True
        )
        
        # Account info
        embed.add_field(
            name="Account",
            value=f"Portfolio: ${account['portfolio_value']:,.2f}\n"
                  f"Cash: ${account['cash']:,.2f}\n"
                  f"Buying Power: ${account['buying_power']:,.2f}",
            inline=True
        )
        
        # Positions
        total_pl = sum(pos['unrealized_pl'] for pos in positions)
        embed.add_field(
            name="Positions",
            value=f"Open: {len(positions)}\n"
                  f"Unrealized P/L: ${total_pl:,.2f}",
            inline=True
        )
        
        # Performance
        embed.add_field(
            name="30-Day Performance",
            value=f"Trades: {metrics['total_trades']}\n"
                  f"Win Rate: {metrics['win_rate']:.1f}%\n"
                  f"Total P/L: ${metrics['total_profit_loss']:,.2f}",
            inline=False
        )
        
        # Recent positions
        if positions:
            pos_text = ""
            for pos in positions[:5]:
                pl_pct = pos['unrealized_plpc'] * 100
                emoji = "🟢" if pos['unrealized_pl'] > 0 else "🔴"
                pos_text += f"{emoji} {pos['symbol']}: ${pos['unrealized_pl']:,.2f} ({pl_pct:+.2f}%)\n"
            embed.add_field(name="Top Positions", value=pos_text, inline=False)
        
        await interaction.followup.send(embed=embed)
        
    except Exception as e:
        logger.error(f"Error in status command: {e}")
        await interaction.followup.send(f"❌ Error getting status: {str(e)}")


@bot.tree.command(name="positions", description="List all open positions")
async def positions_command(interaction: discord.Interaction):
    """List all open positions."""
    await interaction.response.defer()
    
    try:
        alpaca = get_alpaca_service()
        positions = await alpaca.get_positions()
        
        if not positions:
            await interaction.followup.send("📭 No open positions")
            return
        
        embed = discord.Embed(
            title="📈 Open Positions",
            color=discord.Color.blue()
        )
        
        for pos in positions:
            pl_pct = pos['unrealized_plpc'] * 100
            emoji = "🟢" if pos['unrealized_pl'] > 0 else "🔴"
            
            value = (
                f"Qty: {pos['qty']}\n"
                f"Entry: ${pos['avg_entry_price']:.2f}\n"
                f"Current: ${pos['current_price']:.2f}\n"
                f"P/L: ${pos['unrealized_pl']:,.2f} ({pl_pct:+.2f}%)"
            )
            
            embed.add_field(
                name=f"{emoji} {pos['symbol']}",
                value=value,
                inline=True
            )
        
        await interaction.followup.send(embed=embed)
        
    except Exception as e:
        logger.error(f"Error in positions command: {e}")
        await interaction.followup.send(f"❌ Error getting positions: {str(e)}")


@bot.tree.command(name="sell", description="Sell a position")
@app_commands.describe(symbol="Stock symbol to sell")
async def sell_command(interaction: discord.Interaction, symbol: str):
    """Sell a position."""
    await interaction.response.defer()
    
    try:
        symbol = symbol.upper()
        alpaca = get_alpaca_service()
        
        # Check if position exists
        position = await alpaca.get_position(symbol)
        if not position:
            await interaction.followup.send(f"❌ No position found for {symbol}")
            return
        
        # Close position
        success = await alpaca.close_position(symbol)
        
        if success:
            await interaction.followup.send(
                f"✅ Sell order placed for {symbol}\n"
                f"Quantity: {position['qty']}\n"
                f"P/L: ${position['unrealized_pl']:,.2f}"
            )
        else:
            await interaction.followup.send(f"❌ Failed to sell {symbol}")
        
    except Exception as e:
        logger.error(f"Error in sell command: {e}")
        await interaction.followup.send(f"❌ Error selling position: {str(e)}")


@bot.tree.command(name="pause", description="Pause the trading system")
async def pause_command(interaction: discord.Interaction):
    """Pause the trading system."""
    await interaction.response.defer()
    
    try:
        bot.system_paused = True
        
        if bot.orchestrator:
            bot.orchestrator.paused = True
        
        db = get_database_service()
        await db.set_system_state("paused", "true")
        
        await interaction.followup.send("⏸️ Trading system paused")
        logger.info("Trading system paused via Discord command")
        
    except Exception as e:
        logger.error(f"Error in pause command: {e}")
        await interaction.followup.send(f"❌ Error pausing system: {str(e)}")


@bot.tree.command(name="resume", description="Resume the trading system")
async def resume_command(interaction: discord.Interaction):
    """Resume the trading system."""
    await interaction.response.defer()
    
    try:
        bot.system_paused = False
        
        if bot.orchestrator:
            bot.orchestrator.paused = False
        
        db = get_database_service()
        await db.set_system_state("paused", "false")
        
        await interaction.followup.send("▶️ Trading system resumed")
        logger.info("Trading system resumed via Discord command")
        
    except Exception as e:
        logger.error(f"Error in resume command: {e}")
        await interaction.followup.send(f"❌ Error resuming system: {str(e)}")


@bot.tree.command(name="switch-mode", description="Switch between paper and live trading")
@app_commands.describe(mode="Trading mode (paper or live)")
@app_commands.choices(mode=[
    app_commands.Choice(name="Paper Trading", value="paper"),
    app_commands.Choice(name="Live Trading", value="live")
])
async def switch_mode_command(interaction: discord.Interaction, mode: app_commands.Choice[str]):
    """Switch trading mode."""
    await interaction.response.defer()
    
    try:
        new_mode = mode.value
        
        # Confirmation for live trading
        if new_mode == "live":
            embed = discord.Embed(
                title="⚠️ WARNING: Switching to Live Trading",
                description=(
                    "You are about to switch to **LIVE TRADING** mode.\n\n"
                    "This will use real money. Are you sure?\n\n"
                    "React with ✅ to confirm or ❌ to cancel."
                ),
                color=discord.Color.red()
            )
            
            msg = await interaction.followup.send(embed=embed)
            await msg.add_reaction("✅")
            await msg.add_reaction("❌")
            
            def check(reaction, user):
                return (
                    user == interaction.user and
                    str(reaction.emoji) in ["✅", "❌"] and
                    reaction.message.id == msg.id
                )
            
            try:
                reaction, user = await bot.wait_for("reaction_add", timeout=30.0, check=check)
                
                if str(reaction.emoji) == "❌":
                    await interaction.followup.send("❌ Mode switch cancelled")
                    return
                
            except asyncio.TimeoutError:
                await interaction.followup.send("⏱️ Confirmation timeout - mode switch cancelled")
                return
        
        # Update mode
        update_trading_mode(new_mode)
        
        # Reinitialize Alpaca service
        from services.alpaca_service import _alpaca_service
        global _alpaca_service
        _alpaca_service = None
        
        db = get_database_service()
        await db.set_system_state("trading_mode", new_mode)
        
        embed = discord.Embed(
            title="✅ Trading Mode Switched",
            description=f"Now in **{new_mode.upper()}** trading mode",
            color=discord.Color.green()
        )
        
        await interaction.followup.send(embed=embed)
        logger.info(f"Trading mode switched to {new_mode} via Discord command")
        
    except Exception as e:
        logger.error(f"Error in switch-mode command: {e}")
        await interaction.followup.send(f"❌ Error switching mode: {str(e)}")


@bot.tree.command(name="trades", description="View recent trades")
@app_commands.describe(limit="Number of trades to show (default: 10)")
async def trades_command(interaction: discord.Interaction, limit: int = 10):
    """View recent trades."""
    await interaction.response.defer()
    
    try:
        db = get_database_service()
        trades = await db.get_recent_trades(limit)
        
        if not trades:
            await interaction.followup.send("📭 No recent trades")
            return
        
        embed = discord.Embed(
            title=f"📜 Recent Trades (Last {len(trades)})",
            color=discord.Color.blue()
        )
        
        for trade in trades:
            timestamp = trade['timestamp']
            action_emoji = "🟢" if trade['action'].lower() == 'buy' else "🔴"
            
            value = (
                f"Action: {action_emoji} {trade['action'].upper()}\n"
                f"Qty: {trade['quantity']}\n"
                f"Price: ${trade['price']:.2f}\n"
                f"Total: ${trade['total_value']:,.2f}\n"
                f"Time: {timestamp}"
            )
            
            embed.add_field(
                name=trade['symbol'],
                value=value,
                inline=True
            )
        
        await interaction.followup.send(embed=embed)
        
    except Exception as e:
        logger.error(f"Error in trades command: {e}")
        await interaction.followup.send(f"❌ Error getting trades: {str(e)}")


@bot.tree.command(name="performance", description="View performance metrics")
@app_commands.describe(days="Number of days to analyze (default: 30)")
async def performance_command(interaction: discord.Interaction, days: int = 30):
    """View performance metrics."""
    await interaction.response.defer()
    
    try:
        db = get_database_service()
        metrics = await db.get_performance_metrics(days)
        
        embed = discord.Embed(
            title=f"📊 Performance Metrics ({days} Days)",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="Trading Activity",
            value=(
                f"Total Trades: {metrics['total_trades']}\n"
                f"Winning Trades: {metrics['winning_trades']}\n"
                f"Losing Trades: {metrics['losing_trades']}"
            ),
            inline=True
        )
        
        embed.add_field(
            name="Performance",
            value=(
                f"Win Rate: {metrics['win_rate']:.1f}%\n"
                f"Total P/L: ${metrics['total_profit_loss']:,.2f}"
            ),
            inline=True
        )
        
        await interaction.followup.send(embed=embed)
        
    except Exception as e:
        logger.error(f"Error in performance command: {e}")
        await interaction.followup.send(f"❌ Error getting performance: {str(e)}")


@bot.tree.command(name="account", description="View account details")
async def account_command(interaction: discord.Interaction):
    """View detailed account information."""
    await interaction.response.defer()
    
    try:
        alpaca = get_alpaca_service()
        account = await alpaca.get_account()
        
        embed = discord.Embed(
            title="💰 Account Details",
            color=discord.Color.gold()
        )
        
        embed.add_field(
            name="Balance",
            value=(
                f"Portfolio Value: ${account['equity']:,.2f}\n"
                f"Cash: ${account['cash']:,.2f}\n"
                f"Buying Power: ${account['buying_power']:,.2f}"
            ),
            inline=False
        )
        
        embed.add_field(
            name="Day Trading",
            value=(
                f"Day Trades: {account.get('daytrade_count', 0)}\n"
                f"PDT: {'Yes' if account.get('pattern_day_trader') else 'No'}"
            ),
            inline=True
        )
        
        embed.add_field(
            name="Status",
            value=(
                f"Trading Blocked: {'Yes' if account.get('trading_blocked') else 'No'}\n"
                f"Account Blocked: {'Yes' if account.get('account_blocked') else 'No'}"
            ),
            inline=True
        )
        
        await interaction.followup.send(embed=embed)
        
    except Exception as e:
        logger.error(f"Error in account command: {e}")
        await interaction.followup.send(f"❌ Error getting account: {str(e)}")


@bot.tree.command(name="watchlist", description="View current watchlist")
async def watchlist_command(interaction: discord.Interaction):
    """View the current watchlist."""
    await interaction.response.defer()
    
    try:
        # Get watchlist from data pipeline agent
        from agents.data_pipeline_agent import DataPipelineAgent
        data_pipeline = DataPipelineAgent()
        
        watchlist = data_pipeline.watchlist
        
        embed = discord.Embed(
            title="👀 Watchlist",
            description=f"Monitoring {len(watchlist)} symbols",
            color=discord.Color.purple()
        )
        
        # Get current prices
        alpaca = get_alpaca_service()
        symbols_text = ""
        
        for symbol in watchlist:
            try:
                quote = await alpaca.get_quote(symbol)
                if quote:
                    symbols_text += f"**{symbol}**: ${quote['price']:.2f}\n"
                else:
                    symbols_text += f"**{symbol}**: N/A\n"
            except:
                symbols_text += f"**{symbol}**: N/A\n"
        
        embed.add_field(name="Symbols", value=symbols_text or "No symbols", inline=False)
        
        await interaction.followup.send(embed=embed)
        
    except Exception as e:
        logger.error(f"Error in watchlist command: {e}")
        await interaction.followup.send(f"❌ Error getting watchlist: {str(e)}")


@bot.tree.command(name="quote", description="Get quote for a symbol")
@app_commands.describe(symbol="Stock symbol")
async def quote_command(interaction: discord.Interaction, symbol: str):
    """Get current quote for a symbol."""
    await interaction.response.defer()
    
    try:
        symbol = symbol.upper()
        alpaca = get_alpaca_service()
        quote = await alpaca.get_quote(symbol)
        
        if not quote:
            await interaction.followup.send(f"❌ No quote found for {symbol}")
            return
        
        embed = discord.Embed(
            title=f"💹 {symbol} Quote",
            color=discord.Color.blue()
        )
        
        embed.add_field(name="Price", value=f"${quote['price']:.2f}", inline=True)
        embed.add_field(name="Bid", value=f"${quote.get('bid', 0):.2f}", inline=True)
        embed.add_field(name="Ask", value=f"${quote.get('ask', 0):.2f}", inline=True)
        
        if 'volume' in quote:
            embed.add_field(name="Volume", value=f"{quote['volume']:,}", inline=True)
        
        await interaction.followup.send(embed=embed)
        
    except Exception as e:
        logger.error(f"Error in quote command: {e}")
        await interaction.followup.send(f"❌ Error getting quote: {str(e)}")


@bot.tree.command(name="limits", description="View current risk limits")
async def limits_command(interaction: discord.Interaction):
    """View current risk limits and settings."""
    await interaction.response.defer()
    
    try:
        from config import settings
        
        embed = discord.Embed(
            title="🛡️ Risk Limits",
            color=discord.Color.orange()
        )
        
        embed.add_field(
            name="Position Limits",
            value=(
                f"Max Position Size: ${settings.max_position_size:,.2f}\n"
                f"Max Open Positions: {settings.max_open_positions}\n"
                f"Max Daily Loss: ${settings.max_daily_loss:,.2f}"
            ),
            inline=False
        )
        
        embed.add_field(
            name="Exit Thresholds",
            value=(
                f"Profit Target: {settings.profit_target_pct*100:.0f}%\n"
                f"Stop Loss: {settings.stop_loss_pct*100:.0f}%"
            ),
            inline=True
        )
        
        embed.add_field(
            name="Scanning",
            value=f"Interval: {settings.scan_interval_minutes} minutes",
            inline=True
        )
        
        await interaction.followup.send(embed=embed)
        
    except Exception as e:
        logger.error(f"Error in limits command: {e}")
        await interaction.followup.send(f"❌ Error getting limits: {str(e)}")


@bot.tree.command(name="circuit-breaker", description="Check circuit breaker status")
async def circuit_breaker_command(interaction: discord.Interaction):
    """Check circuit breaker status."""
    await interaction.response.defer()
    
    try:
        from agents.risk_manager_agent import RiskManagerAgent
        risk_manager = RiskManagerAgent()
        
        result = await risk_manager.check_circuit_breaker()
        
        if result['triggered']:
            embed = discord.Embed(
                title="🚨 Circuit Breaker TRIGGERED",
                description="Trading is currently halted due to daily loss limit",
                color=discord.Color.red()
            )
        else:
            embed = discord.Embed(
                title="✅ Circuit Breaker OK",
                description="Trading is active",
                color=discord.Color.green()
            )
        
        embed.add_field(
            name="Daily Loss",
            value=f"${result['daily_loss']:,.2f}",
            inline=True
        )
        
        embed.add_field(
            name="Max Loss",
            value=f"${result['max_loss']:,.2f}",
            inline=True
        )
        
        remaining = result['max_loss'] - abs(result['daily_loss'])
        embed.add_field(
            name="Remaining",
            value=f"${remaining:,.2f}",
            inline=True
        )
        
        await interaction.followup.send(embed=embed)
        
    except Exception as e:
        logger.error(f"Error in circuit-breaker command: {e}")
        await interaction.followup.send(f"❌ Error checking circuit breaker: {str(e)}")


@bot.tree.command(name="scan-now", description="Trigger an immediate opportunity scan")
async def scan_now_command(interaction: discord.Interaction):
    """Trigger an immediate scan for opportunities."""
    await interaction.response.defer()
    
    try:
        if not bot.orchestrator:
            await interaction.followup.send("❌ Orchestrator not available")
            return
        
        await interaction.followup.send("🔍 Starting scan...")
        
        # Trigger scan and trade workflow
        result = await bot.orchestrator.scan_and_trade()
        
        status = result.get('status', 'unknown')
        
        if status == 'success':
            await interaction.followup.send(
                f"✅ Scan complete!\n"
                f"Opportunities: {result.get('opportunities_found', 0)}\n"
                f"Signals: {result.get('signals_generated', 0)}\n"
                f"Trades: {result.get('trades_executed', 0)}"
            )
        else:
            await interaction.followup.send(f"📊 Scan complete: {result.get('message', 'No action taken')}")
        
    except Exception as e:
        logger.error(f"Error in scan-now command: {e}")
        await interaction.followup.send(f"❌ Error running scan: {str(e)}")


@bot.tree.command(name="close-all", description="⚠️ Close all positions (EMERGENCY)")
async def close_all_command(interaction: discord.Interaction):
    """Emergency close all positions."""
    await interaction.response.defer()
    
    try:
        # Confirmation
        embed = discord.Embed(
            title="⚠️ WARNING: Close All Positions",
            description=(
                "You are about to close **ALL OPEN POSITIONS**.\n\n"
                "This action cannot be undone.\n\n"
                "React with ✅ to confirm or ❌ to cancel."
            ),
            color=discord.Color.red()
        )
        
        msg = await interaction.followup.send(embed=embed)
        await msg.add_reaction("✅")
        await msg.add_reaction("❌")
        
        def check(reaction, user):
            return (
                user == interaction.user and
                str(reaction.emoji) in ["✅", "❌"] and
                reaction.message.id == msg.id
            )
        
        try:
            reaction, user = await bot.wait_for("reaction_add", timeout=30.0, check=check)
            
            if str(reaction.emoji) == "❌":
                await interaction.followup.send("❌ Close all cancelled")
                return
            
            # Close all positions
            if bot.orchestrator:
                result = await bot.orchestrator.emergency_stop()
                await interaction.followup.send(
                    f"🚨 All positions closed\n"
                    f"Positions: {result.get('positions_closed', 0)}\n"
                    f"Total P/L: ${result.get('total_pl', 0):,.2f}"
                )
            else:
                await interaction.followup.send("❌ Orchestrator not available")
                
        except asyncio.TimeoutError:
            await interaction.followup.send("⏱️ Confirmation timeout - cancelled")
        
    except Exception as e:
        logger.error(f"Error in close-all command: {e}")
        await interaction.followup.send(f"❌ Error closing positions: {str(e)}")


@bot.tree.command(name="watchlist-add", description="Add symbol to watchlist")
@app_commands.describe(symbol="Stock symbol to add")
async def watchlist_add_command(interaction: discord.Interaction, symbol: str):
    """Add a symbol to the watchlist."""
    await interaction.response.defer()
    
    try:
        symbol = symbol.upper()
        
        # Get data pipeline agent
        if not bot.orchestrator:
            await interaction.followup.send("❌ System not ready")
            return
        
        data_pipeline = bot.orchestrator.data_pipeline
        
        if symbol in data_pipeline.watchlist:
            await interaction.followup.send(f"ℹ️ {symbol} is already in watchlist")
            return
        
        # Add to watchlist
        data_pipeline.watchlist.append(symbol)
        
        # Get current quote
        alpaca = get_alpaca_service()
        quote = await alpaca.get_quote(symbol)
        
        price_info = f"${quote['price']:.2f}" if quote else "N/A"
        
        await interaction.followup.send(
            f"✅ Added {symbol} to watchlist\n"
            f"Current Price: {price_info}\n"
            f"Total Symbols: {len(data_pipeline.watchlist)}"
        )
        
        logger.info(f"Added {symbol} to watchlist via Discord")
        
    except Exception as e:
        logger.error(f"Error in watchlist-add command: {e}")
        await interaction.followup.send(f"❌ Error adding symbol: {str(e)}")


@bot.tree.command(name="watchlist-remove", description="Remove symbol from watchlist")
@app_commands.describe(symbol="Stock symbol to remove")
async def watchlist_remove_command(interaction: discord.Interaction, symbol: str):
    """Remove a symbol from the watchlist."""
    await interaction.response.defer()
    
    try:
        symbol = symbol.upper()
        
        # Get data pipeline agent
        if not bot.orchestrator:
            await interaction.followup.send("❌ System not ready")
            return
        
        data_pipeline = bot.orchestrator.data_pipeline
        
        if symbol not in data_pipeline.watchlist:
            await interaction.followup.send(f"ℹ️ {symbol} is not in watchlist")
            return
        
        # Remove from watchlist
        data_pipeline.watchlist.remove(symbol)
        
        await interaction.followup.send(
            f"✅ Removed {symbol} from watchlist\n"
            f"Remaining Symbols: {len(data_pipeline.watchlist)}"
        )
        
        logger.info(f"Removed {symbol} from watchlist via Discord")
        
    except Exception as e:
        logger.error(f"Error in watchlist-remove command: {e}")
        await interaction.followup.send(f"❌ Error removing symbol: {str(e)}")


@bot.tree.command(name="simulate", description="🧪 Run full system simulation")
async def simulate_command(interaction: discord.Interaction):
    """Run complete system simulation."""
    await interaction.response.defer()
    
    try:
        if not bot.orchestrator:
            await interaction.followup.send("❌ System not ready")
            return
        
        # Import simulation service
        from services.simulation_service import get_simulation_service
        
        sim_service = get_simulation_service(bot.orchestrator)
        
        # Send initial message
        await interaction.followup.send("🧪 **Starting Full System Simulation...**\nThis will test all trading scenarios.\n\n⏳ Please wait...")
        
        # Run simulation
        results = await sim_service.run_full_simulation()
        
        # Create results embed
        embed = discord.Embed(
            title="🧪 System Simulation Results",
            description=f"Completed {results['total_tests']} tests in {results['duration_seconds']:.1f}s",
            color=discord.Color.green() if results['success_rate'] >= 80 else discord.Color.orange()
        )
        
        # Summary
        embed.add_field(
            name="📊 Summary",
            value=(
                f"✅ Passed: {results['passed']}\n"
                f"❌ Failed: {results['failed']}\n"
                f"📈 Success Rate: {results['success_rate']:.1f}%"
            ),
            inline=False
        )
        
        # Show each test result
        for i, test in enumerate(results['results'][:10], 1):  # Show first 10
            status_emoji = "✅" if test['status'] == 'PASSED' else "❌"
            details = test.get('details', test.get('error', 'No details'))
            
            embed.add_field(
                name=f"{status_emoji} Test {i}: {test['test']}",
                value=f"{details[:100]}...",
                inline=False
            )
        
        if len(results['results']) > 10:
            embed.add_field(
                name="ℹ️ Note",
                value=f"Showing 10 of {len(results['results'])} tests. Check logs for full results.",
                inline=False
            )
        
        embed.set_footer(text=f"Simulation completed at {results['timestamp']}")
        
        await interaction.followup.send(embed=embed)
        
        logger.info(f"Simulation completed via Discord: {results['passed']}/{results['total_tests']} passed")
        
    except Exception as e:
        logger.error(f"Error in simulate command: {e}")
        await interaction.followup.send(f"❌ Simulation error: {str(e)}")


@bot.tree.command(name="update-limit", description="⚙️ Update trading limits")
@app_commands.describe(
    limit_type="Type of limit to update",
    value="New value"
)
@app_commands.choices(limit_type=[
    app_commands.Choice(name="Max Position Size ($)", value="max_position_size"),
    app_commands.Choice(name="Max Daily Loss ($)", value="max_daily_loss"),
    app_commands.Choice(name="Profit Target (%)", value="profit_target"),
    app_commands.Choice(name="Stop Loss (%)", value="stop_loss"),
    app_commands.Choice(name="Max Open Positions", value="max_positions"),
    app_commands.Choice(name="Options Max Contracts", value="options_max_contracts"),
    app_commands.Choice(name="Options Max Premium ($)", value="options_max_premium"),
])
async def update_limit_command(interaction: discord.Interaction, limit_type: str, value: float):
    """Update trading limits dynamically."""
    await interaction.response.defer()
    
    try:
        from config import settings
        
        # Validate and update based on type
        if limit_type == "max_position_size":
            if value < 100 or value > 50000:
                await interaction.followup.send("❌ Position size must be between $100 and $50,000")
                return
            settings.max_position_size = value
            msg = f"✅ Max position size updated to ${value:,.2f}"
        
        elif limit_type == "max_daily_loss":
            if value < 100 or value > 10000:
                await interaction.followup.send("❌ Daily loss must be between $100 and $10,000")
                return
            settings.max_daily_loss = value
            msg = f"✅ Max daily loss updated to ${value:,.2f}"
        
        elif limit_type == "profit_target":
            if value < 5 or value > 200:
                await interaction.followup.send("❌ Profit target must be between 5% and 200%")
                return
            settings.profit_target_pct = value / 100
            msg = f"✅ Profit target updated to {value}%"
        
        elif limit_type == "stop_loss":
            if value < 5 or value > 50:
                await interaction.followup.send("❌ Stop loss must be between 5% and 50%")
                return
            settings.stop_loss_pct = value / 100
            msg = f"✅ Stop loss updated to {value}%"
        
        elif limit_type == "max_positions":
            if value < 1 or value > 20:
                await interaction.followup.send("❌ Max positions must be between 1 and 20")
                return
            settings.max_open_positions = int(value)
            msg = f"✅ Max open positions updated to {int(value)}"
        
        elif limit_type == "options_max_contracts":
            if value < 1 or value > 10:
                await interaction.followup.send("❌ Max contracts must be between 1 and 10")
                return
            settings.options_max_contracts = int(value)
            msg = f"✅ Options max contracts updated to {int(value)}"
        
        elif limit_type == "options_max_premium":
            if value < 50 or value > 2000:
                await interaction.followup.send("❌ Max premium must be between $50 and $2,000")
                return
            settings.options_max_premium = value
            msg = f"✅ Options max premium updated to ${value:,.2f}"
        
        else:
            await interaction.followup.send("❌ Unknown limit type")
            return
        
        # Show updated limits
        embed = discord.Embed(
            title="⚙️ Limit Updated",
            description=msg,
            color=discord.Color.green()
        )
        
        embed.add_field(
            name="📊 Current Limits",
            value=(
                f"Max Position Size: ${settings.max_position_size:,.2f}\n"
                f"Max Daily Loss: ${settings.max_daily_loss:,.2f}\n"
                f"Profit Target: {settings.profit_target_pct*100:.0f}%\n"
                f"Stop Loss: {settings.stop_loss_pct*100:.0f}%\n"
                f"Max Positions: {settings.max_open_positions}\n"
                f"Options Max Contracts: {settings.options_max_contracts}\n"
                f"Options Max Premium: ${settings.options_max_premium:,.2f}"
            ),
            inline=False
        )
        
        embed.set_footer(text="⚠️ Changes are temporary and will reset on restart")
        
        await interaction.followup.send(embed=embed)
        
        logger.info(f"Limit updated via Discord: {limit_type} = {value}")
        
    except Exception as e:
        logger.error(f"Error in update-limit command: {e}")
        await interaction.followup.send(f"❌ Error updating limit: {str(e)}")


@bot.tree.command(name="sentiment", description="📊 Check sentiment for a symbol")
@app_commands.describe(symbol="Stock symbol to analyze")
async def sentiment_command(interaction: discord.Interaction, symbol: str):
    """Check sentiment analysis for a symbol."""
    await interaction.response.defer()
    
    try:
        symbol = symbol.upper()
        
        # Import sentiment service
        from services.sentiment_service import get_sentiment_service
        
        sentiment_service = get_sentiment_service()
        
        # Set LLM if available
        if bot.orchestrator:
            from services import get_llm_service
            sentiment_service.set_llm(get_llm_service())
        
        await interaction.followup.send(f"🔍 Analyzing sentiment for {symbol}...\n⏳ This may take a moment...")
        
        # Get sentiment
        sentiment = await sentiment_service.analyze_symbol_sentiment(symbol)
        
        # Create embed
        if sentiment.get('overall_sentiment') == 'POSITIVE':
            color = discord.Color.green()
            emoji = "📈"
        elif sentiment.get('overall_sentiment') == 'NEGATIVE':
            color = discord.Color.red()
            emoji = "📉"
        else:
            color = discord.Color.blue()
            emoji = "➡️"
        
        embed = discord.Embed(
            title=f"{emoji} Sentiment Analysis: {symbol}",
            description=sentiment.get('interpretation', 'No interpretation available'),
            color=color
        )
        
        # Overall sentiment
        embed.add_field(
            name="📊 Overall Sentiment",
            value=(
                f"**{sentiment['overall_sentiment']}**\n"
                f"Score: {sentiment['overall_score']:.2f} (-1 to 1)"
            ),
            inline=False
        )
        
        # News sentiment
        news = sentiment.get('news_sentiment', {})
        embed.add_field(
            name="📰 News Sentiment",
            value=(
                f"**{news.get('sentiment', 'N/A')}**\n"
                f"Score: {news.get('score', 0):.2f}\n"
                f"{news.get('reasoning', 'N/A')}"
            ),
            inline=True
        )
        
        # Market sentiment
        market = sentiment.get('market_sentiment', {})
        embed.add_field(
            name="📈 Market Sentiment",
            value=(
                f"**{market.get('sentiment', 'N/A')}**\n"
                f"Score: {market.get('score', 0):.2f}\n"
                f"{market.get('reasoning', 'N/A')}"
            ),
            inline=True
        )
        
        # Social sentiment
        social = sentiment.get('social_sentiment', {})
        embed.add_field(
            name="💬 Social Sentiment",
            value=(
                f"**{social.get('sentiment', 'N/A')}**\n"
                f"Score: {social.get('score', 0):.2f}\n"
                f"Mentions: {social.get('mentions', 0):,}"
            ),
            inline=True
        )
        
        embed.set_footer(text=f"Analysis timestamp: {sentiment.get('timestamp', 'N/A')}")
        
        await interaction.followup.send(embed=embed)
        
        logger.info(f"Sentiment analysis for {symbol}: {sentiment['overall_sentiment']}")
        
    except Exception as e:
        logger.error(f"Error in sentiment command: {e}")
        await interaction.followup.send(f"❌ Error analyzing sentiment: {str(e)}")


@bot.tree.command(name="help", description="Show all available commands")
async def help_command(interaction: discord.Interaction):
    """Show help information."""
    await interaction.response.defer()
    
    embed = discord.Embed(
        title="🤖 Trading Bot Commands",
        description="Complete list of available commands",
        color=discord.Color.blue()
    )
    
    embed.add_field(
        name="📊 Information",
        value=(
            "`/status` - System status overview\n"
            "`/account` - Account details\n"
            "`/positions` - Open positions\n"
            "`/trades [limit]` - Recent trades\n"
            "`/performance [days]` - Performance metrics\n"
            "`/quote <symbol>` - Get stock quote\n"
            "`/sentiment <symbol>` - 📊 Sentiment analysis\n"
            "`/watchlist` - View watchlist\n"
            "`/watchlist-add <symbol>` - Add to watchlist\n"
            "`/watchlist-remove <symbol>` - Remove from watchlist"
        ),
        inline=False
    )
    
    embed.add_field(
        name="⚙️ Control",
        value=(
            "`/pause` - Pause trading\n"
            "`/resume` - Resume trading\n"
            "`/scan-now` - Trigger immediate scan\n"
            "`/switch-mode <mode>` - Switch paper/live\n"
            "`/simulate` - 🧪 Run full system test"
        ),
        inline=False
    )
    
    embed.add_field(
        name="💼 Trading",
        value=(
            "`/sell <symbol>` - Sell a position\n"
            "`/close-all` - ⚠️ Close all positions"
        ),
        inline=False
    )
    
    embed.add_field(
        name="🛡️ Risk",
        value=(
            "`/limits` - View risk limits\n"
            "`/update-limit <type> <value>` - ⚙️ Update limits\n"
            "`/circuit-breaker` - Check circuit breaker"
        ),
        inline=False
    )
    
    embed.add_field(
        name="ℹ️ Help",
        value="`/help` - Show this message",
        inline=False
    )
    
    await interaction.followup.send(embed=embed)


def get_bot() -> TradingBot:
    """Get the bot instance."""
    return bot


async def start_bot():
    """Start the Discord bot."""
    try:
        await bot.start(settings.discord_bot_token)
    except Exception as e:
        logger.error(f"Error starting Discord bot: {e}")
        raise
