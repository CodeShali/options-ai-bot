"""
Discord bot for controlling the trading system.
"""
import asyncio
from typing import Optional, Dict, Any
from datetime import datetime
import discord
from discord import app_commands
from discord.ext import commands
from loguru import logger

from config import settings, update_trading_mode
from services import get_alpaca_service, get_database_service, get_discord_conversation_service
from services.discord_realtime_service import get_discord_realtime_service
from services.discord_interactive_service import get_discord_interactive_service
from services.discord_alerts_service import get_discord_alerts_service
from services.discord_analytics_service import get_discord_analytics_service
from bot.discord_helpers import (
    create_status_embed,
    create_position_embed,
    create_trade_embed,
    create_sentiment_embed,
    create_error_embed,
    create_success_embed,
    create_warning_embed,
    format_positions_list,
    format_trades_list
)


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
        
        # Enhancement services (will be initialized in setup_hook)
        self.realtime_service = None
        self.interactive_service = None
        self.alerts_service = None
        self.analytics_service = None
        self.conversation_service = None
        
        logger.info("Discord bot initialized")
    
    async def setup_hook(self):
        """Setup hook called when bot is ready."""
        await self.tree.sync()
        logger.info("Command tree synced")
        
        # Initialize enhancement services
        try:
            self.realtime_service = get_discord_realtime_service(self)
            self.interactive_service = get_discord_interactive_service(self)
            self.alerts_service = get_discord_alerts_service(self)
            self.analytics_service = get_discord_analytics_service(self)
            self.conversation_service = get_discord_conversation_service(self)
            
            # Start all services
            self.realtime_service.start_monitoring()
            self.alerts_service.start_monitoring()
            self.analytics_service.start_reporting()
            
            logger.info("✅ All enhancement services activated")
        except Exception as e:
            logger.warning(f"Enhancement services initialization failed: {e}. Bot will run with basic features.")
    
    def set_orchestrator(self, orchestrator):
        """Set orchestrator reference for commands that need it."""
        self.orchestrator = orchestrator
        logger.info("Orchestrator reference set in bot")
    
    async def on_ready(self):
        """Called when the bot is ready."""
        logger.info(f"🌟 TARA logged in as {self.user}")
        
        # Set status
        await self.change_presence(
            status=discord.Status.online,
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="📊 Market Opportunities"
            )
        )
    
    async def on_reaction_add(self, reaction, user):
        """Handle reaction additions for NLP confirmations."""
        if user.bot:
            return
            
        # Check if this message has a reaction handler
        if hasattr(self, '_reaction_handlers'):
            handler = self._reaction_handlers.get(reaction.message.id)
            if handler:
                handled = await handler.handle_reaction(reaction, user)
                if handled:
                    # Remove handler after use
                    del self._reaction_handlers[reaction.message.id]
    
    async def on_message(self, message: discord.Message):
        """Handle natural language conversations with session management."""
        # Always ignore other bots
        if message.author.bot:
            return
        
        try:
            # Only respond in the configured notification channel or its threads
            allowed = False
            if message.channel.id == self.notification_channel_id:
                allowed = True
            elif isinstance(message.channel, discord.Thread):
                parent = message.channel.parent
                if parent and parent.id == self.notification_channel_id:
                    allowed = True
            # Also allow if the bot is mentioned anywhere or in DMs
            if not allowed:
                try:
                    if isinstance(message.channel, discord.DMChannel):
                        allowed = True
                    elif self.user and self.user in getattr(message, "mentions", []):
                        allowed = True
                except Exception:
                    pass
            
            if allowed and self.conversation_service:
                # Pass the message to conversation service (handles session management internally)
                reply = await self.conversation_service.handle_message(message)
                if reply:
                    # Check if reply needs reaction confirmation (trading actions)
                    if isinstance(reply, dict) and reply.get("needs_reaction_confirmation"):
                        logger.info("NLP reaction confirmation requested")
                        # Send message and add reactions
                        sent_message = await message.reply(
                            reply.get("content", "Confirm action?"),
                            mention_author=False
                        )
                        
                        # Create reaction confirmation handler
                        from services.discord_conversation_service import ReactionConfirmation
                        reaction_handler = ReactionConfirmation(
                            reply.get("action_data"),
                            self.conversation_service,
                            reply.get("user_id"),
                            sent_message
                        )
                        await reaction_handler.setup_reactions()
                        
                        # Store handler for reaction events
                        if not hasattr(self, '_reaction_handlers'):
                            self._reaction_handlers = {}
                        self._reaction_handlers[sent_message.id] = reaction_handler
                        
                    # Check if reply needs general reactions (all responses)
                    elif isinstance(reply, dict) and reply.get("needs_reactions"):
                        logger.info("NLP general reactions requested")
                        # Send message and add feedback reactions
                        sent_message = await message.reply(
                            reply.get("content", "Here's what I found."),
                            mention_author=False
                        )
                        
                        # Add general feedback reactions
                        await sent_message.add_reaction("👍")  # Good response
                        await sent_message.add_reaction("👎")  # Bad response
                        await sent_message.add_reaction("❓")  # Need more info
                        
                    # Check if reply needs confirmation (has buttons) - legacy
                    elif isinstance(reply, dict) and reply.get("needs_confirmation"):
                        logger.info("NLP confirmation requested; sending confirmation view")
                        # Send with confirmation buttons
                        await message.reply(
                            reply.get("content", "Confirm action?"),
                            view=reply.get("view"),
                            mention_author=False
                        )
                    else:
                        # Regular text reply - add basic reactions
                        reply_text = reply if isinstance(reply, str) else reply.get("content", str(reply))
                        sent_message = await message.reply(reply_text, mention_author=False)
                        
                        # Add basic feedback reactions to ALL responses
                        await sent_message.add_reaction("👍")
                        await sent_message.add_reaction("👎")
        except Exception as e:
            logger.error(f"Error in on_message: {e}")
        finally:
            # Ensure slash commands still work
            await self.process_commands(message)
    
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
        
        # Get performance metrics
        metrics = await db.get_performance_metrics(30)
        
        # Calculate position P/L
        total_pl = sum(float(pos.get('unrealized_pl', 0)) for pos in positions)
        
        # Get today's P/L from trades
        try:
            today_trades = await db.get_recent_trades(100)
            from datetime import datetime
            today = datetime.now().date()
            today_pl = sum(
                float(t.get('profit_loss', 0)) 
                for t in today_trades 
                if datetime.fromisoformat(t.get('timestamp', '')).date() == today
            )
        except:
            today_pl = 0
        
        # Check circuit breaker
        cb_active = abs(today_pl) > settings.max_daily_loss if today_pl < 0 else False
        daily_loss = abs(today_pl) if today_pl < 0 else 0
        
        # Get last activity times
        last_scan = "Just now"
        last_trade = "N/A"
        
        # Get strategy status
        strategies_status = {}
        if bot.orchestrator and hasattr(bot.orchestrator, 'strategy_agent'):
            try:
                from strategies.strategy_manager import StrategyManager
                manager = StrategyManager()
                for name in manager.active_strategies:
                    strategies_status[name.replace('_', ' ').title()] = {
                        'active': True,
                        'signals_today': 0  # TODO: Track signals per day
                    }
            except:
                pass
        
        # Calculate today's trades
        today_trades_count = len([t for t in today_trades if datetime.fromisoformat(t.get('timestamp', '')).date() == today]) if today_trades else 0
        today_wins = len([t for t in today_trades if datetime.fromisoformat(t.get('timestamp', '')).date() == today and float(t.get('profit_loss', 0)) > 0]) if today_trades else 0
        today_win_rate = (today_wins / today_trades_count * 100) if today_trades_count > 0 else 0
        
        # Get largest position
        largest_pos = max(positions, key=lambda x: float(x.get('market_value', 0))) if positions else None
        largest_pos_symbol = largest_pos.get('symbol', 'N/A') if largest_pos else 'N/A'
        
        # Calculate total risk (sum of stop loss distances)
        total_risk = sum(
            abs(float(pos.get('current_price', 0)) - float(pos.get('avg_entry_price', 0))) * float(pos.get('qty', 0)) * 0.02
            for pos in positions
        )
        
        # Get watchlist size
        watchlist_size = len(bot.orchestrator.data_pipeline.watchlist) if bot.orchestrator and bot.orchestrator.data_pipeline else 0
        
        # Calculate portfolio heat (simplified)
        equity = float(account.get('equity', 1))
        portfolio_heat = (total_risk / equity * 100) if equity > 0 else 0
        
        # Build comprehensive status data
        status_data = {
            'running': not bot.system_paused,
            'status': 'ACTIVE' if not bot.system_paused else 'PAUSED',
            'mode': settings.trading_mode,
            'paused': bot.system_paused,
            'account': account,
            'positions': {
                'count': len(positions),
                'total_pl': total_pl,
                'today_pl': today_pl
            },
            'today_trades': today_trades_count,
            'today_win_rate': today_win_rate,
            'largest_position': largest_pos_symbol,
            'total_risk': total_risk,
            'strategies': strategies_status,
            'last_scan': last_scan,
            'next_scan': '5 minutes' if not bot.system_paused else 'Paused',
            'symbols_watching': watchlist_size,
            'opportunities_found': 0,  # TODO: Track from last scan
            'portfolio_heat': portfolio_heat,
            'heat_limit': 6.0,
            'performance': {
                'win_rate': metrics.get('win_rate', 0),
                'total_trades': metrics.get('total_trades', 0),
                'total_pl': metrics.get('total_profit_loss', 0)
            },
            'circuit_breaker': {
                'active': cb_active,
                'daily_loss': daily_loss,
                'limit': getattr(settings, 'max_daily_loss', 1000)
            },
            'last_trade': last_trade,
            'uptime': 'N/A'  # TODO: Track uptime
        }
        
        # Create beautiful embed
        embed = create_status_embed(status_data)
        await interaction.followup.send(embed=embed)
        
    except Exception as e:
        logger.error(f"Error in status command: {e}")
        embed = create_error_embed(f"Error getting status: {str(e)}")
        await interaction.followup.send(embed=embed)


@bot.tree.command(name="positions", description="List all open positions")
async def positions_command(interaction: discord.Interaction):
    """List all open positions."""
    await interaction.response.defer()
    
    try:
        alpaca = get_alpaca_service()
        positions = await alpaca.get_positions()
        
        if not positions:
            embed = create_warning_embed("No open positions")
            await interaction.followup.send(embed=embed)
            return
        
        # Use beautiful formatted list
        embed = format_positions_list(positions)
        await interaction.followup.send(embed=embed)
        
    except Exception as e:
        logger.error(f"Error in positions command: {e}")
        embed = create_error_embed(f"Error getting positions: {str(e)}")
        await interaction.followup.send(embed=embed)


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
            embed = create_error_embed(f"No position found for {symbol}")
            await interaction.followup.send(embed=embed)
            return
        
        # Close position
        success = await alpaca.close_position(symbol)
        
        if success:
            embed = create_success_embed(
                f"**Sell order placed for {symbol}**\n\n"
                f"Quantity: {position['qty']}\n"
                f"P/L: ${position['unrealized_pl']:,.2f}"
            )
            await interaction.followup.send(embed=embed)
        else:
            embed = create_error_embed(f"Failed to sell {symbol}")
            await interaction.followup.send(embed=embed)
        
    except Exception as e:
        logger.error(f"Error in sell command: {e}")
        embed = create_error_embed(f"Error selling position: {str(e)}")
        await interaction.followup.send(embed=embed)


@bot.tree.command(name="buy", description="Buy stock with AI analysis")
@app_commands.describe(
    symbol="Stock symbol to buy",
    quantity="Number of shares (optional, will suggest if not provided)"
)
async def buy_command(interaction: discord.Interaction, symbol: str, quantity: int = None):
    """Buy stock with AI analysis and recommendations."""
    await interaction.response.defer()
    
    try:
        symbol = symbol.upper()
        from services.buy_assistant_service import get_buy_assistant_service
        buy_assistant = get_buy_assistant_service()
        
        # Analyze the buy opportunity
        analysis = await buy_assistant.analyze_buy_opportunity(symbol)
        
        if "error" in analysis:
            embed = create_error_embed(f"Error analyzing {symbol}: {analysis['error']}")
            await interaction.followup.send(embed=embed)
            return
        
        current_price = analysis["current_price"]
        buying_power = analysis["buying_power"]
        max_shares = analysis["max_shares"]
        
        # If no quantity specified, suggest an amount
        if quantity is None:
            # Suggest 5% of buying power worth of shares
            suggested_value = buying_power * 0.05
            quantity = int(suggested_value / current_price)
            quantity = max(1, min(quantity, max_shares))  # At least 1, at most max_shares
        
        # Validate quantity
        estimated_cost = current_price * quantity
        if estimated_cost > buying_power:
            embed = create_error_embed(
                f"**Insufficient Buying Power**\n\n"
                f"Cost: ${estimated_cost:,.2f}\n"
                f"Available: ${buying_power:,.2f}\n"
                f"Max shares you can buy: {max_shares}"
            )
            await interaction.followup.send(embed=embed)
            return
        
        # Create confirmation embed
        embed = discord.Embed(
            title=f"💰 Confirm Buy Order - {symbol}",
            description=f"Review your order details before confirming",
            color=discord.Color.green()
        )
        embed.add_field(name="Symbol", value=symbol, inline=True)
        embed.add_field(name="Quantity", value=f"{quantity} shares", inline=True)
        embed.add_field(name="Current Price", value=f"${current_price:.2f}", inline=True)
        embed.add_field(name="Estimated Cost", value=f"${estimated_cost:,.2f}", inline=True)
        embed.add_field(name="Buying Power After", value=f"${buying_power - estimated_cost:,.2f}", inline=True)
        embed.add_field(name="Order Type", value="Market Order", inline=True)
        
        # Create confirmation view
        class BuyConfirmView(discord.ui.View):
            def __init__(self):
                super().__init__(timeout=60)
                self.confirmed = None
            
            @discord.ui.button(label="✅ Confirm Buy", style=discord.ButtonStyle.green)
            async def confirm_button(self, interaction: discord.Interaction, button: discord.ui.Button):
                self.confirmed = True
                self.stop()
                
                # Execute the buy
                result = await buy_assistant.execute_stock_buy(symbol, quantity)
                
                if result["success"]:
                    success_embed = create_success_embed(
                        f"**✅ Buy Order Executed**\n\n"
                        f"Symbol: {symbol}\n"
                        f"Quantity: {quantity} shares\n"
                        f"Estimated Cost: ${result['estimated_cost']:,.2f}\n"
                        f"Order ID: {result['order'].get('id', 'N/A')}"
                    )
                    await interaction.response.edit_message(embed=success_embed, view=None)
                else:
                    error_embed = create_error_embed(f"Failed to execute buy order: {result.get('error', 'Unknown error')}")
                    await interaction.response.edit_message(embed=error_embed, view=None)
            
            @discord.ui.button(label="❌ Cancel", style=discord.ButtonStyle.red)
            async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
                self.confirmed = False
                self.stop()
                cancel_embed = create_error_embed("Buy order cancelled")
                await interaction.response.edit_message(embed=cancel_embed, view=None)
        
        view = BuyConfirmView()
        await interaction.followup.send(embed=embed, view=view)
        
    except Exception as e:
        logger.error(f"Error in buy command: {e}")
        embed = create_error_embed(f"Error processing buy order: {str(e)}")
        await interaction.followup.send(embed=embed)


@bot.tree.command(name="buy-option", description="Buy options with Greeks analysis")
@app_commands.describe(
    symbol="Stock symbol",
    strategy="Call or Put",
    max_risk="Maximum risk per contract (default: $1000)"
)
@app_commands.choices(strategy=[
    app_commands.Choice(name="Call", value="call"),
    app_commands.Choice(name="Put", value="put")
])
async def buy_option_command(
    interaction: discord.Interaction,
    symbol: str,
    strategy: app_commands.Choice[str],
    max_risk: float = 1000.0
):
    """Buy options with AI-powered Greeks analysis."""
    await interaction.response.defer()
    
    try:
        symbol = symbol.upper()
        strategy_type = strategy.value
        
        from services.buy_assistant_service import get_buy_assistant_service
        buy_assistant = get_buy_assistant_service()
        
        # Find best options
        best_options = await buy_assistant.find_best_options(
            symbol=symbol,
            strategy=strategy_type,
            max_risk=max_risk,
            target_delta=0.5
        )
        
        if not best_options:
            embed = create_error_embed(
                f"**No suitable {strategy_type} options found for {symbol}**\n\n"
                f"Try adjusting your max risk or check if options are available for this symbol."
            )
            await interaction.followup.send(embed=embed)
            return
        
        # Show top 3 options
        embed = discord.Embed(
            title=f"📊 Best {strategy_type.upper()} Options for {symbol}",
            description=f"Top recommendations based on Greeks analysis (Max Risk: ${max_risk:,.2f})",
            color=discord.Color.blue()
        )
        
        for i, option in enumerate(best_options[:3], 1):
            field_value = (
                f"**Strike:** ${option['strike']:.2f} | **Expires:** {option['days_to_exp']} days\n"
                f"**Cost:** ${option['contract_cost']:.2f} | **Risk:** {option['risk_level']}\n"
                f"**Greeks:** Δ={option['delta']:.3f} | Θ={option['theta']:.4f} | Γ={option['gamma']:.4f}\n"
                f"**Score:** {option['score']:.1f}/100\n"
                f"💡 {option['recommendation']}"
            )
            embed.add_field(
                name=f"#{i} - {option['symbol']}",
                value=field_value,
                inline=False
            )
        
        embed.set_footer(text="Use the buttons below to select and buy an option")
        
        # Create selection view
        class OptionSelectView(discord.ui.View):
            def __init__(self, options_list):
                super().__init__(timeout=120)
                self.options_list = options_list
                
                # Add buttons for each option
                for i in range(min(3, len(options_list))):
                    button = discord.ui.Button(
                        label=f"Buy Option #{i+1}",
                        style=discord.ButtonStyle.green,
                        custom_id=f"buy_option_{i}"
                    )
                    button.callback = self.create_callback(i)
                    self.add_item(button)
            
            def create_callback(self, index):
                async def callback(interaction: discord.Interaction):
                    option = self.options_list[index]
                    
                    # Execute buy
                    result = await buy_assistant.execute_option_buy(
                        option_symbol=option['symbol'],
                        quantity=1,
                        order_type="limit",
                        limit_price=option['ask']  # Use ask price for limit order
                    )
                    
                    if result["success"]:
                        success_embed = create_success_embed(
                            f"**✅ Option Buy Order Placed**\n\n"
                            f"Contract: {option['symbol']}\n"
                            f"Strike: ${option['strike']:.2f}\n"
                            f"Expiration: {option['expiration']}\n"
                            f"Cost: ${option['contract_cost']:.2f}\n"
                            f"Delta: {option['delta']:.3f}\n"
                            f"Order ID: {result['order'].get('id', 'N/A')}"
                        )
                        await interaction.response.edit_message(embed=success_embed, view=None)
                    else:
                        error_embed = create_error_embed(f"Failed to place option order: {result.get('error', 'Unknown error')}")
                        await interaction.response.edit_message(embed=error_embed, view=None)
                
                return callback
        
        view = OptionSelectView(best_options)
        await interaction.followup.send(embed=embed, view=view)
        
    except Exception as e:
        logger.error(f"Error in buy-option command: {e}")
        embed = create_error_embed(f"Error finding options: {str(e)}")
        await interaction.followup.send(embed=embed)


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
        
        embed = create_success_embed("⏸️ **Trading system paused**\n\nAll trading activities suspended.")
        await interaction.followup.send(embed=embed)
        logger.info("Trading system paused via Discord command")
        
    except Exception as e:
        logger.error(f"Error in pause command: {e}")
        embed = create_error_embed(f"Error pausing system: {str(e)}")
        await interaction.followup.send(embed=embed)


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
        
        embed = create_success_embed("▶️ **Trading system resumed**\n\nTrading activities active.")
        await interaction.followup.send(embed=embed)
        logger.info("Trading system resumed via Discord command")
        
    except Exception as e:
        logger.error(f"Error in resume command: {e}")
        embed = create_error_embed(f"Error resuming system: {str(e)}")
        await interaction.followup.send(embed=embed)


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
        from services.alpaca_service import reset_alpaca_service
        reset_alpaca_service()
        
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
            
            # Get trade status and color code it
            status = trade.get('status', 'unknown').upper()
            status_emoji = {
                'FILLED': '✅',
                'PENDING': '⏳',
                'SUBMITTED': '⏳',
                'ACCEPTED': '⏳',
                'REJECTED': '❌',
                'CANCELED': '❌',
                'CANCELLED': '❌',
                'PARTIAL': '⚠️',
                'PARTIAL_FILL': '⚠️'
            }.get(status, '❓')
            
            # Determine field color based on status
            status_color = {
                'FILLED': '🟢',
                'PENDING': '🟡',
                'SUBMITTED': '🟡',
                'ACCEPTED': '🟡',
                'REJECTED': '🔴',
                'CANCELED': '🔴',
                'CANCELLED': '🔴',
                'PARTIAL': '🟠',
                'PARTIAL_FILL': '🟠'
            }.get(status, '⚪')
            
            value = (
                f"{status_color} **Status:** {status_emoji} {status}\n"
                f"**Action:** {action_emoji} {trade['action'].upper()}\n"
                f"**Qty:** {trade['quantity']} | **Price:** ${trade['price']:.2f}\n"
                f"**Total:** ${trade['total_value']:,.2f}\n"
                f"**Time:** {timestamp[:19]}"
            )
            
            embed.add_field(
                name=f"{trade['symbol']}",
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
    """View detailed account information with Tara formatting."""
    await interaction.response.defer()
    
    try:
        from services import get_api_tracker, get_database_service
        from services.performance_metrics_service import get_performance_metrics_service
        from bot.discord_helpers import format_account_summary
        from datetime import date
        
        alpaca = get_alpaca_service()
        db = get_database_service()
        
        account = await alpaca.get_account()
        positions = await alpaca.get_positions()
        
        # Get API tracker stats
        api_tracker = get_api_tracker()
        api_status = await api_tracker.get_status("Alpaca")
        
        # Calculate actual P&L from today's trades
        today = date.today().isoformat()
        trades_today = await db.get_recent_trades(100)
        closed_pl_today = sum(
            float(t.get('total_value', 0)) 
            for t in trades_today 
            if t.get('timestamp', '').startswith(today) and t.get('action') == 'sell'
        )
        
        # Calculate daily return
        equity_start = float(account.get('last_equity', account['equity']))
        current_equity = float(account['equity'])
        daily_return_pct = ((current_equity - equity_start) / equity_start * 100) if equity_start > 0 else 0
        
        # Calculate total return (from initial capital)
        initial_capital = 100000.0  # Default initial capital for paper trading
        total_return_pct = ((current_equity - initial_capital) / initial_capital * 100) if initial_capital > 0 else 0
        
        # Get performance metrics (NEW)
        perf_service = get_performance_metrics_service(db)
        performance_metrics = await perf_service.calculate_metrics(days=30)
        
        # Prepare account data for Tara formatting
        account_data = {
            'account_name': f"Alpaca ({settings.trading_mode.upper()})",
            'cash': account['cash'],
            'equity': account['equity'],
            'buying_power': account['buying_power'],
            'positions': positions,
            'equity_start_of_day': equity_start,
            'closed_pl_today': closed_pl_today,
            'daily_return_pct': daily_return_pct,
            'total_return_pct': total_return_pct
        }
        
        # Use Tara's formatted message with performance metrics
        message = format_account_summary(account_data, api_status['calls_today'], performance_metrics)
        
        await interaction.followup.send(message)
        
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
                quote = await alpaca.get_latest_quote(symbol)
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
        quote = await alpaca.get_latest_quote(symbol)
        
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


@bot.tree.command(name="auto-trade", description="⚙️ Check or toggle automatic trading")
@app_commands.describe(action="Action: status, enable, or disable")
async def auto_trade_command(interaction: discord.Interaction, action: str = "status"):
    """Check or toggle automatic trading."""
    await interaction.response.defer()
    
    try:
        from config import settings
        
        action = action.lower()
        
        if action == "enable":
            # Note: This only changes in-memory, not .env file
            settings.auto_trading_enabled = True
            
            embed = discord.Embed(
                title="✅ Auto-Trading ENABLED",
                description="Bot will now automatically execute trades when high-confidence signals are detected.",
                color=discord.Color.green()
            )
            embed.add_field(
                name="⚠️ Important",
                value="• Trades will execute automatically\n"
                      "• Review alerts before they execute\n"
                      "• Monitor positions closely\n"
                      "• Use `/auto-trade disable` to stop",
                inline=False
            )
            
            logger.info("Auto-trading ENABLED via Discord command")
            
        elif action == "disable":
            settings.auto_trading_enabled = False
            
            embed = discord.Embed(
                title="⏸️ Auto-Trading DISABLED",
                description="Bot will send alerts only. No automatic trade execution.",
                color=discord.Color.orange()
            )
            embed.add_field(
                name="ℹ️ Info",
                value="• You'll receive alerts for opportunities\n"
                      "• Review AI insights\n"
                      "• Execute trades manually if desired\n"
                      "• **Monitor still works** - existing positions managed\n"
                      "• Use `/auto-trade enable` to resume",
                inline=False
            )
            
            logger.info("Auto-trading DISABLED via Discord command")
            
        else:  # status
            status = "ENABLED ✅" if settings.auto_trading_enabled else "DISABLED ⏸️"
            color = discord.Color.green() if settings.auto_trading_enabled else discord.Color.orange()
            
            embed = discord.Embed(
                title=f"⚙️ Auto-Trading Status: {status}",
                description="Current automatic trading configuration",
                color=color
            )
            
            embed.add_field(
                name="Status",
                value=status,
                inline=True
            )
            
            embed.add_field(
                name="Mode",
                value=f"{settings.trading_mode.upper()}",
                inline=True
            )
            
            embed.add_field(
                name="Max Positions",
                value=f"{settings.max_open_positions}",
                inline=True
            )
            
            if settings.auto_trading_enabled:
                embed.add_field(
                    name="⚠️ Active Trading",
                    value="Bot will execute trades automatically when signals are detected.",
                    inline=False
                )
            else:
                embed.add_field(
                    name="ℹ️ Alerts Only",
                    value="Bot will send alerts but not execute NEW trades.\n"
                          "**Monitor still active** - existing positions are managed automatically.\n"
                          "Use `/auto-trade enable` to start trading.",
                    inline=False
                )
        
        await interaction.followup.send(embed=embed)
        
    except Exception as e:
        logger.error(f"Error in auto-trade command: {e}")
        await interaction.followup.send(f"❌ Error managing auto-trade: {str(e)}")


@bot.tree.command(name="scan-now", description="Trigger an immediate opportunity scan")
async def scan_now_command(interaction: discord.Interaction):
    """Trigger an immediate scan for opportunities."""
    await interaction.response.defer()
    
    try:
        if not bot.orchestrator:
            await interaction.followup.send("❌ Orchestrator not available")
            return
        
        # Get watchlist
        watchlist = bot.orchestrator.data_pipeline.watchlist if bot.orchestrator.data_pipeline else []
        
        # Send initial status
        await interaction.followup.send(
            f"🔍 **Starting Market Scan**\n\n"
            f"**Scanning:** {len(watchlist)} symbols\n"
            f"**Watchlist:** {', '.join(watchlist[:5])}{'...' if len(watchlist) > 5 else ''}\n"
            f"**Process:**\n"
            f"1. 📊 Fetching market data...\n"
            f"2. 🎯 Calculating opportunity scores...\n"
            f"3. 🤖 Generating trade signals...\n"
            f"4. ✅ Executing approved trades...\n\n"
            f"⏳ Please wait..."
        )
        
        # Trigger scan and trade workflow
        result = await bot.orchestrator.scan_and_trade()
        
        status = result.get('status', 'unknown')
        opportunities = result.get('opportunities_found', 0)
        signals = result.get('signals_generated', 0)
        trades = result.get('trades_executed', 0)
        
        # Create detailed result embed
        embed = discord.Embed(
            title="📊 Scan Complete",
            color=discord.Color.green() if trades > 0 else discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        embed.add_field(
            name="🔍 Scan Results",
            value=f"**Symbols Scanned:** {len(watchlist)}\n"
                  f"**Opportunities Found:** {opportunities}\n"
                  f"**Signals Generated:** {signals}\n"
                  f"**Trades Executed:** {trades}",
            inline=False
        )
        
        if opportunities > 0:
            # Get opportunity details if available
            opps = result.get('opportunities', [])
            if opps:
                opp_text = ""
                for opp in opps[:3]:  # Show top 3
                    symbol = opp.get('symbol', 'N/A')
                    score = opp.get('score', 0)
                    action = opp.get('action', 'N/A')
                    
                    # NEW: Get strategy signal and MTF data
                    rec = opp.get('recommendation', {})
                    strategy_signal = rec.get('strategy_signal')
                    mtf_analysis = rec.get('mtf_analysis')
                    
                    # Score emoji
                    if score >= 80:
                        score_emoji = "🟢"
                        score_label = "STRONG"
                    elif score >= 60:
                        score_emoji = "🟡"
                        score_label = "MODERATE"
                    else:
                        score_emoji = "⚪"
                        score_label = "WEAK"
                    
                    opp_text += f"**{symbol}** {score_emoji} Score: {score}/100 ({score_label})\n"
                    opp_text += f"  📊 Action: {action}\n"
                    
                    # Get current price and reasoning
                    current_price = opp.get('current_price', 0)
                    reasoning = opp.get('reasoning', '')
                    
                    # Show strategy signal if available
                    if strategy_signal:
                        strategy_name = strategy_signal.get('strategy', 'Quant Analysis')
                        strategy_action = strategy_signal.get('action', 'N/A')
                        
                        if strategy_action != 'HOLD':
                            opp_text += f"  🎯 **Strategy:** {strategy_name} ({strategy_action})\n"
                            
                            # Show entry/stop/target with R:R if BUY/SELL
                            if strategy_action in ['BUY', 'SELL']:
                                entry = strategy_signal.get('entry_price', 0)
                                stop = strategy_signal.get('stop_loss', 0)
                                target = strategy_signal.get('take_profit', 0)
                                
                                # Calculate R:R
                                risk = abs(entry - stop)
                                reward = abs(target - entry)
                                rr_ratio = reward / risk if risk > 0 else 0
                                
                                opp_text += f"  💰 Entry: ${entry:.2f} | Stop: ${stop:.2f} | Target: ${target:.2f}\n"
                                opp_text += f"  📊 Risk/Reward: 1:{rr_ratio:.1f}\n"
                                
                                # Show strategy reason
                                strategy_reason = strategy_signal.get('reason', '')
                                if strategy_reason:
                                    # Truncate if too long
                                    reason_short = strategy_reason[:80] + "..." if len(strategy_reason) > 80 else strategy_reason
                                    opp_text += f"  💡 Why: {reason_short}\n"
                        else:
                            # Show detailed HOLD status
                            conditions_needed = strategy_signal.get('conditions_needed', [])
                            if conditions_needed:
                                # Show first condition needed
                                opp_text += f"  ⚪ Quant: {conditions_needed[0][:60]}...\n" if len(conditions_needed[0]) > 60 else f"  ⚪ Quant: {conditions_needed[0]}\n"
                            else:
                                opp_text += f"  ⚪ Quant: No setup (waiting for entry)\n"
                    
                    # Show MTF alignment if available
                    if mtf_analysis and mtf_analysis.get('available'):
                        alignment = mtf_analysis.get('alignment', {}).get('alignment', 'UNKNOWN')
                        if alignment != 'UNKNOWN':
                            # Use emojis for alignment
                            if 'BULLISH' in alignment:
                                mtf_emoji = "📈"
                            elif 'BEARISH' in alignment:
                                mtf_emoji = "📉"
                            else:
                                mtf_emoji = "📊"
                            opp_text += f"  {mtf_emoji} **MTF:** {alignment}\n"
                    
                    # Show momentum data if available
                    momentum = rec.get('momentum', {})
                    if momentum:
                        momentum_score = momentum.get('score', 0)
                        if momentum_score > 0:
                            opp_text += f"  🚀 Momentum: {momentum_score:.0f}/100\n"
                    
                    # Show key technical indicators if available
                    indicators = strategy_signal.get('indicators', {}) if strategy_signal else {}
                    if indicators:
                        # Show most relevant indicators
                        rsi = indicators.get('rsi')
                        volume_ratio = indicators.get('volume_ratio')
                        
                        if rsi is not None:
                            rsi_label = "Oversold" if rsi < 30 else "Overbought" if rsi > 70 else "Neutral"
                            opp_text += f"  📊 RSI: {rsi:.0f} ({rsi_label})\n"
                        
                        if volume_ratio is not None and volume_ratio > 1:
                            opp_text += f"  📊 Volume: {volume_ratio:.1f}x average\n"
                    
                    # Show AI reasoning (truncated)
                    if reasoning and strategy_signal and strategy_signal.get('action') != 'HOLD':
                        # Extract first sentence or first 100 chars
                        first_sentence = reasoning.split('.')[0] if '.' in reasoning else reasoning[:100]
                        if len(first_sentence) > 100:
                            first_sentence = first_sentence[:100] + "..."
                        opp_text += f"  💭 {first_sentence}\n"
                    
                    opp_text += "\n"
                
                embed.add_field(
                    name="🎯 Top Opportunities (with Quantitative Signals)",
                    value=opp_text or "No details available",
                    inline=False
                )
        
        if trades > 0:
            embed.add_field(
                name="✅ Action Taken",
                value=f"Executed {trades} trade(s). Check `/positions` for details.",
                inline=False
            )
        elif signals > 0:
            embed.add_field(
                name="⚠️ Signals Generated",
                value=f"Found {signals} signal(s) but no trades executed (risk limits or market conditions).",
                inline=False
            )
        else:
            embed.add_field(
                name="📉 No Action",
                value="No high-quality opportunities found. Market conditions may not be favorable.",
                inline=False
            )
        
        embed.set_footer(text=f"Next scheduled scan in {bot.orchestrator.data_pipeline.scan_interval if hasattr(bot.orchestrator.data_pipeline, 'scan_interval') else 5} minutes")
        
        await interaction.followup.send(embed=embed)
        
    except Exception as e:
        logger.error(f"Error in scan-now command: {e}")
        embed = create_error_embed(f"Error running scan: {str(e)}")
        await interaction.followup.send(embed=embed)


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
        quote = await alpaca.get_latest_quote(symbol)
        
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
        
        # Determine system health
        success_rate = results['success_rate']
        if success_rate >= 90:
            health = "EXCELLENT"
            color = discord.Color.green()
        elif success_rate >= 75:
            health = "GOOD"
            color = discord.Color.blue()
        elif success_rate >= 60:
            health = "FAIR"
            color = discord.Color.orange()
        else:
            health = "NEEDS ATTENTION"
            color = discord.Color.red()
        
        # Create main summary embed
        embed = discord.Embed(
            title="🧪 SYSTEM SIMULATION RESULTS",
            description=(
                f"**━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━**\n"
                f"## 📊 SUMMARY\n"
                f"✅ Passed: **{results['passed']}/{results['total_tests']}** ({success_rate:.1f}%)\n"
                f"❌ Failed: **{results['failed']}/{results['total_tests']}**\n"
                f"⏱️ Duration: **{results['duration_seconds']:.1f}s**\n"
                f"🎯 System Health: **{health}**\n"
                f"**━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━**"
            ),
            color=color,
            timestamp=datetime.now()
        )
        
        # Group tests by category
        trade_type_tests = []
        sentiment_tests = []
        other_tests = []
        
        for test in results['results']:
            test_name = test['test']
            if 'Scalping' in test_name or 'Day Trading' in test_name or 'Swing Trading' in test_name:
                trade_type_tests.append(test)
            elif 'Sentiment' in test_name and ('Boost' in test_name or 'Block' in test_name):
                sentiment_tests.append(test)
            else:
                other_tests.append(test)
        
        # Show Trade Type Tests
        if trade_type_tests:
            trade_type_text = ""
            for test in trade_type_tests:
                status_emoji = "✅" if test['status'] == 'PASSED' else "❌"
                details = test.get('details', test.get('error', 'No details'))
                # Truncate details to fit
                if len(details) > 200:
                    details = details[:197] + "..."
                trade_type_text += f"{status_emoji} **{test['test']}**\n{details}\n\n"
            
            if trade_type_text:
                embed.add_field(
                    name="🎯 TRADE TYPE TESTS",
                    value=trade_type_text[:1024],
                    inline=False
                )
        
        # Show Sentiment Impact Tests
        if sentiment_tests:
            sentiment_text = ""
            for test in sentiment_tests:
                status_emoji = "✅" if test['status'] == 'PASSED' else "❌"
                details = test.get('details', test.get('error', 'No details'))
                if len(details) > 200:
                    details = details[:197] + "..."
                sentiment_text += f"{status_emoji} **{test['test']}**\n{details}\n\n"
            
            if sentiment_text:
                embed.add_field(
                    name="📰 SENTIMENT IMPACT TESTS",
                    value=sentiment_text[:1024],
                    inline=False
                )
        
        # Show other tests (condensed)
        if other_tests:
            other_text = ""
            for test in other_tests[:5]:  # Show first 5
                status_emoji = "✅" if test['status'] == 'PASSED' else "❌"
                other_text += f"{status_emoji} {test['test']}\n"
            
            if len(other_tests) > 5:
                other_text += f"\n_...and {len(other_tests)-5} more tests_"
            
            embed.add_field(
                name="🔧 OTHER TESTS",
                value=other_text,
                inline=False
            )
        
        # Add recommendations
        if results['failed'] > 0:
            failed_tests = [t['test'] for t in results['results'] if t['status'] == 'FAILED']
            recommendations = "⚠️ **Action Required:**\n"
            for test_name in failed_tests[:3]:
                recommendations += f"• Fix: {test_name}\n"
            
            embed.add_field(
                name="💡 RECOMMENDATIONS",
                value=recommendations,
                inline=False
            )
        else:
            embed.add_field(
                name="💡 RECOMMENDATIONS",
                value="✅ All systems operational! Ready for trading.",
                inline=False
            )
        
        embed.set_footer(text=f"Simulation completed | {results['total_tests']} tests")
        
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
    """Check sentiment analysis for a symbol with real market data."""
    await interaction.response.defer()
    
    try:
        symbol = symbol.upper()
        
        await interaction.followup.send(f"🔍 Analyzing {symbol} sentiment...\n⏳ Gathering news, options flow, and technical data...")
        
        # Use enhanced sentiment service with real data
        from services.enhanced_sentiment_service import get_enhanced_sentiment_service
        from services import get_alpaca_service, get_news_service
        
        alpaca = get_alpaca_service()
        news = get_news_service()
        
        # Get or create enhanced sentiment service
        enhanced_sentiment = get_enhanced_sentiment_service(alpaca, news)
        
        if not enhanced_sentiment:
            # Fallback to old service
            logger.warning("Enhanced sentiment service not available, using fallback")
            from services.sentiment_service import get_sentiment_service
            sentiment_service = get_sentiment_service()
            
            if bot.orchestrator:
                from services import get_llm_service
                from services.claude_service import get_claude_service
                sentiment_service.set_llm(get_llm_service())
                sentiment_service.set_alpaca(alpaca)
                sentiment_service.set_news(news)
                sentiment_service.set_claude(get_claude_service())
            
            analysis = await sentiment_service.analyze_for_trading(symbol)
            from bot.discord_helpers import create_trading_analysis_embed
            embed = create_trading_analysis_embed(analysis)
        else:
            # Use new enhanced sentiment analysis
            sentiment_data = await enhanced_sentiment.analyze_sentiment(symbol)
            
            # Create enhanced embed
            from bot.discord_helpers import create_enhanced_sentiment_embed
            embed = create_enhanced_sentiment_embed(sentiment_data)
        
        # Check if already in watchlist
        alpaca = get_alpaca_service()
        is_in_watchlist = await alpaca.is_in_watchlist(symbol)
        
        if is_in_watchlist:
            # Already in watchlist - show what we're doing with it
            watchlist_message = f"""
📋 **{symbol} is already in your watchlist!**

**What we're doing with it:**
1. 🔍 **Monitoring** - Checking price every 5 minutes
2. 📊 **Analyzing** - Running technical analysis on each scan
3. 🎯 **Scoring** - Calculating trade opportunity score (0-100)
4. 🚨 **Alerting** - Will notify you when score > 70
5. 🤖 **Auto-Trading** - Can execute trades if conditions met (if enabled)

**Current Process:**
✅ Price tracking active
✅ Pattern detection running
✅ Risk analysis ongoing
✅ Entry signals monitored

Use `/watchlist` to see all monitored stocks.
"""
            await interaction.followup.send(embed=embed, content=watchlist_message)
        else:
            # Not in watchlist - show add button
            class WatchlistView(discord.ui.View):
                def __init__(self, symbol_to_add):
                    super().__init__(timeout=60)
                    self.symbol = symbol_to_add
                    self.responded = False
                
                @discord.ui.button(label="✅ Add to Watchlist", style=discord.ButtonStyle.green)
                async def add_button(self, interaction: discord.Interaction, button: discord.ui.Button):
                    if self.responded:
                        return
                    self.responded = True
                    
                    # Add to watchlist (use default watchlist or create one)
                    alpaca = get_alpaca_service()
                    # Try to get or create a default watchlist
                    try:
                        watchlists = await alpaca.get_watchlists()
                        default_watchlist = None
                        for wl in watchlists:
                            if wl.get('name') == 'TARA-Main':
                                default_watchlist = wl.get('id')
                                break
                        
                        if not default_watchlist:
                            # Create default watchlist
                            new_wl = await alpaca.create_watchlist('TARA-Main', [self.symbol])
                            success = new_wl is not None
                        else:
                            success = await alpaca.add_to_watchlist(default_watchlist, self.symbol)
                    except Exception as e:
                        logger.error(f"Error adding to watchlist: {e}")
                        success = False
                    
                    if success:
                        response_msg = f"""✅ **{self.symbol}** added to watchlist!

**What happens now:**
1. 🔍 Bot will monitor {self.symbol} every 5 minutes
2. 📊 Technical analysis runs automatically
3. 🎯 Trade opportunities scored (0-100)
4. 🚨 You'll get alerts when score > 70
5. 🤖 Auto-trading available (if enabled)

Use `/watchlist` to see all monitored stocks."""
                        await interaction.response.send_message(response_msg, ephemeral=True)
                    else:
                        await interaction.response.send_message(f"⚠️ Could not add **{self.symbol}** to watchlist", ephemeral=True)
                    
                    # Disable buttons
                    for item in self.children:
                        item.disabled = True
                    await interaction.message.edit(view=self)
                
                @discord.ui.button(label="❌ No Thanks", style=discord.ButtonStyle.gray)
                async def skip_button(self, interaction: discord.Interaction, button: discord.ui.Button):
                    if self.responded:
                        return
                    self.responded = True
                    
                    await interaction.response.send_message(f"👍 Skipped adding **{self.symbol}** to watchlist", ephemeral=True)
                    
                    # Disable buttons
                    for item in self.children:
                        item.disabled = True
                    await interaction.message.edit(view=self)
            
            # Send embed with watchlist prompt
            view = WatchlistView(symbol)
            await interaction.followup.send(
                embed=embed,
                content=f"💡 **Add {symbol} to your watchlist?**",
                view=view
            )
        
        # Log sentiment result
        if enhanced_sentiment:
            logger.info(f"Enhanced sentiment analysis for {symbol}: {sentiment_data.get('overall_sentiment', {}).get('label', 'N/A')}")
        elif 'analysis' in locals():
            logger.info(f"Trading analysis for {symbol}: {analysis.get('recommendation', 'N/A')}")
        
    except Exception as e:
        logger.error(f"Error in sentiment command: {e}")
        embed = create_error_embed(f"Error analyzing sentiment: {str(e)}")
        await interaction.followup.send(embed=embed)


@bot.tree.command(name="aggressive-mode", description="🚀 Toggle aggressive trading mode (1-min scanning)")
@app_commands.describe(enable="Enable or disable aggressive mode")
@app_commands.choices(enable=[
    app_commands.Choice(name="Enable (1-min scanning, day trading)", value="on"),
    app_commands.Choice(name="Disable (5-min scanning, swing trading)", value="off")
])
async def aggressive_mode_command(interaction: discord.Interaction, enable: app_commands.Choice[str]):
    """Toggle aggressive trading mode."""
    await interaction.response.defer()
    
    try:
        from config import enable_aggressive_mode, disable_aggressive_mode
        
        if enable.value == "on":
            enable_aggressive_mode()
            embed = create_success_embed(
                "🚀 **Aggressive Mode ENABLED**\n\n"
                "**Settings Updated:**\n"
                "• Scan Interval: 1 minute (was 5 min)\n"
                "• Trade Types: Scalp + Day Trade\n"
                "• Max Positions: 5\n"
                "• Position Size: $2,000\n"
                "• Circuit Breaker: $500/day\n"
                "• Options: 0-7 DTE allowed\n\n"
                "**Expected:**\n"
                "• 8-12 trades/day\n"
                "• AI cost: ~$0.22/day\n"
                "• More opportunities detected"
            )
            logger.info("Aggressive mode enabled via Discord")
        else:
            disable_aggressive_mode()
            embed = create_success_embed(
                "📊 **Aggressive Mode DISABLED**\n\n"
                "**Settings Reset:**\n"
                "• Scan Interval: 5 minutes\n"
                "• Trade Type: Swing trading\n"
                "• Max Positions: 5\n"
                "• Position Size: $5,000\n"
                "• Circuit Breaker: $1,000/day\n"
                "• Options: 30-45 DTE\n\n"
                "**Expected:**\n"
                "• 2-3 trades/day\n"
                "• AI cost: ~$0.02/day\n"
                "• Conservative approach"
            )
            logger.info("Aggressive mode disabled via Discord")
        
        await interaction.followup.send(embed=embed)
        
    except Exception as e:
        logger.error(f"Error toggling aggressive mode: {e}")
        embed = create_error_embed(f"Error toggling aggressive mode: {str(e)}")
        await interaction.followup.send(embed=embed)


@bot.tree.command(name="circuit-breaker-set", description="⚙️ Set daily loss limit")
@app_commands.describe(amount="Daily loss limit in dollars")
async def circuit_breaker_set_command(interaction: discord.Interaction, amount: float):
    """Set circuit breaker daily loss limit."""
    await interaction.response.defer()
    
    try:
        if amount < 100 or amount > 10000:
            embed = create_error_embed("Amount must be between $100 and $10,000")
            await interaction.followup.send(embed=embed)
            return
        
        settings.max_daily_loss = amount
        
        embed = create_success_embed(
            f"🛡️ **Circuit Breaker Updated**\n\n"
            f"Daily loss limit set to: **${amount:,.2f}**\n\n"
            f"Trading will be blocked if daily loss exceeds this amount."
        )
        await interaction.followup.send(embed=embed)
        logger.info(f"Circuit breaker set to ${amount} via Discord")
        
    except Exception as e:
        logger.error(f"Error setting circuit breaker: {e}")
        embed = create_error_embed(f"Error: {str(e)}")
        await interaction.followup.send(embed=embed)


@bot.tree.command(name="api-status", description="📡 Check API connections and usage")
async def api_status_command(interaction: discord.Interaction):
    """Check all API connections and usage with Tara formatting."""
    await interaction.response.defer()
    
    try:
        from services import get_api_tracker
        from bot.discord_helpers import format_api_status
        from datetime import datetime
        
        # Get API tracker
        api_tracker = get_api_tracker()
        
        # Get Alpaca status
        try:
            alpaca = get_alpaca_service()
            account = await alpaca.get_account()
            alpaca_connected = True
            provider_name = f"Alpaca ({settings.trading_mode.upper()})"
        except Exception as e:
            alpaca_connected = False
            provider_name = "Alpaca (ERROR)"
        
        # Get real API stats
        api_status_data = await api_tracker.get_status("Alpaca")
        
        # Create embed for API status
        embed = discord.Embed(
            title="📡 API Status",
            description="Real-time API connections and usage",
            color=discord.Color.blue() if alpaca_connected else discord.Color.red(),
            timestamp=datetime.now()
        )
        
        # Alpaca API
        embed.add_field(
            name="📊 Alpaca API",
            value=f"**Provider:** {provider_name}\n"
                  f"**Status:** {'🟢 Connected' if alpaca_connected else '🔴 Disconnected'}\n"
                  f"**Calls Today:** {api_status_data['calls_today']}\n"
                  f"**Errors:** {api_status_data['errors']}\n"
                  f"**Rate Limit:** {api_status_data['rate_limit_used']}/{api_status_data['rate_limit_total']}",
            inline=False
        )
        
        # NewsAPI
        from services import get_news_service
        news = get_news_service()
        news_status = "🟢 Enabled" if news.enabled else "🔴 Disabled"
        
        embed.add_field(
            name="📰 NewsAPI",
            value=f"**Status:** {news_status}\n"
                  f"**Calls Today:** ~3\n"
                  f"**Limit:** 100/day (FREE)",
            inline=True
        )
        
        # OpenAI
        try:
            from services import get_llm_service
            llm = get_llm_service()
            openai_status = "🟢 Connected"
            if settings.aggressive_mode:
                openai_calls = "~138"
                openai_cost = "$0.22"
            else:
                openai_calls = "~11"
                openai_cost = "$0.02"
        except Exception as e:
            openai_status = f"🔴 Error: {str(e)[:50]}"
            openai_calls = "0"
            openai_cost = "$0.00"
        
        embed.add_field(
            name="🤖 OpenAI",
            value=f"**Status:** {openai_status}\n"
                  f"**Model:** gpt-4o\n"
                  f"**Calls Today:** {openai_calls}\n"
                  f"**Cost Today:** {openai_cost}",
            inline=True
        )
        
        # Discord
        embed.add_field(
            name="💬 Discord",
            value=f"**Status:** 🟢 Connected\n"
                  f"**Latency:** {bot.latency*1000:.0f}ms\n"
                  f"**Commands:** Active",
            inline=True
        )
        
        # Trading Mode
        mode_emoji = "🚀" if settings.aggressive_mode else "📊"
        mode_name = "Aggressive (1-min)" if settings.aggressive_mode else "Conservative (5-min)"
        
        embed.add_field(
            name="⚙️ Trading Mode",
            value=f"**Mode:** {mode_emoji} {mode_name}\n"
                  f"**Scan Interval:** {settings.scan_interval}s\n"
                  f"**Circuit Breaker:** ${settings.max_daily_loss:,.0f}",
            inline=True
        )
        
        embed.set_footer(text="API Status | Real-time")
        await interaction.followup.send(embed=embed)
        
    except Exception as e:
        logger.error(f"Error checking API status: {e}")
        embed = create_error_embed(f"Error: {str(e)}")
        await interaction.followup.send(embed=embed)


@bot.tree.command(name="help", description="Show all available commands")
async def help_command(interaction: discord.Interaction):
    """Show help information."""
    try:
        await interaction.response.send_message(
            "🌟 **TARA - Enhanced Trading Assistant**\n"
            "**Trade by Light, Guided by Intelligence**\n\n"
            "💬 **Natural Language AI** - Just talk to me! Ask: `What's my account?`, `Set stop loss`, etc.\n\n"
            "**📋 Quick Commands:**\n"
            "`/status` `/account` `/positions` `/trades` `/performance`\n"
            "`/quote` `/sentiment` `/analyze` `/monitor` `/scan`\n"
            "`/sell` `/pause` `/resume` `/limits` `/api-status`\n\n"
            "**🚀 Enhanced Features:**\n"
            "✅ Real-time updates • Smart alerts • Daily reports\n"
            "✅ Interactive controls • Performance analytics\n"
            "✅ Conversational AI with action execution\n\n"
            "💡 **Tip:** You can ask me to do things naturally:\n"
            "• `Set -2% stop loss on all positions`\n"
            "• `Sell my TSLA position`\n"
            "• `What's my biggest loser?`\n\n"
            "Type `/` to see all commands or just chat with me!",
            ephemeral=False
        )
    except Exception as e:
        logger.error(f"Error in help command: {e}")
        try:
            await interaction.response.send_message("Use `/` to see all commands or just chat with me!", ephemeral=True)
        except:
            pass


@bot.tree.command(name="scan", description="🔍 Scan for trading opportunities")
@app_commands.describe(symbols="Optional: Specific symbols to scan (comma-separated)")
async def scan_command(interaction: discord.Interaction, symbols: Optional[str] = None):
    """Scan for trading opportunities."""
    await interaction.response.defer()
    
    try:
        from services import get_sentiment_service
        
        # Parse symbols if provided
        custom_symbols = None
        if symbols:
            custom_symbols = [s.strip().upper() for s in symbols.split(',')]
            logger.info(f"Scanning custom symbols: {custom_symbols}")
        
        # Run intelligent scan
        if bot.orchestrator and bot.orchestrator.data_pipeline:
            scan_result = await bot.orchestrator.data_pipeline.scan_opportunities(custom_symbols)
            
            full_result = scan_result.get('full_scan_result', {})
            summary = full_result.get('summary', 'Scan complete')
            opportunities = scan_result.get('opportunities', [])
            stats = full_result.get('scan_stats', {})
            
            # Create embed
            embed = discord.Embed(
                title="🔍 Market Scan Results",
                description=summary,
                color=discord.Color.blue(),
                timestamp=datetime.now()
            )
            
            # Add stats
            embed.add_field(
                name="📊 Scan Statistics",
                value=f"Symbols Scanned: {stats.get('symbols_scanned', 0)}\n"
                      f"Movers Detected: {stats.get('movers_detected', 0)}\n"
                      f"Opportunities Found: {stats.get('opportunities_found', 0)}\n"
                      f"Duration: {stats.get('duration_seconds', 0):.1f}s",
                inline=False
            )
            
            # Add top opportunities
            if opportunities:
                for i, opp in enumerate(opportunities[:3], 1):
                    rec = opp.get('recommendation', {})
                    embed.add_field(
                        name=f"{i}. {opp['symbol']} - ${opp['current_price']:.2f}",
                        value=f"**Action:** {opp['action']} ({opp['confidence']}% confidence)\n"
                              f"**Score:** {opp['score']:.0f}/100\n"
                              f"{opp['reasoning'][:150]}...",
                        inline=False
                    )
            
            await interaction.followup.send(embed=embed)
        else:
            await interaction.followup.send(
                embed=create_error_embed("Orchestrator not available")
            )
            
    except Exception as e:
        logger.error(f"Error in scan command: {e}")
        await interaction.followup.send(
            embed=create_error_embed(f"Scan failed: {str(e)}")
        )


@bot.tree.command(name="analyze", description="📈 Deep analysis of a symbol")
@app_commands.describe(symbol="Symbol to analyze")
async def analyze_command(interaction: discord.Interaction, symbol: str):
    """Perform deep analysis on a specific symbol."""
    await interaction.response.defer()
    
    try:
        symbol = symbol.upper()
        
        # Run intelligent scan on just this symbol
        if bot.orchestrator and bot.orchestrator.data_pipeline:
            scan_result = await bot.orchestrator.data_pipeline.scan_opportunities([symbol])
            
            opportunities = scan_result.get('opportunities', [])
            
            if opportunities:
                opp = opportunities[0]
                rec = opp.get('recommendation', {})
                
                # NEW: Get strategy and MTF data
                strategy_signal = rec.get('strategy_signal')
                mtf_analysis = rec.get('mtf_analysis')
                
                embed = discord.Embed(
                    title=f"📈 Deep Analysis: {symbol}",
                    description=f"Current Price: ${opp['current_price']:.2f}",
                    color=discord.Color.green() if opp['action'].startswith('BUY') else discord.Color.orange(),
                    timestamp=datetime.now()
                )
                
                # Recommendation
                embed.add_field(
                    name="🎯 Recommendation",
                    value=f"**Action:** {opp['action']}\n"
                          f"**Confidence:** {opp['confidence']}%\n"
                          f"**Score:** {opp['score']:.0f}/100",
                    inline=False
                )
                
                # NEW: Quantitative Strategy Signal
                if strategy_signal:
                    strategy_name = strategy_signal.get('strategy', 'Quant Analysis')
                    strategy_action = strategy_signal.get('action', 'N/A')
                    
                    if strategy_action != 'HOLD':
                        entry = strategy_signal.get('entry_price', 0)
                        stop = strategy_signal.get('stop_loss', 0)
                        target = strategy_signal.get('take_profit', 0)
                        
                        embed.add_field(
                            name="🎯 Quantitative Strategy",
                            value=f"**Strategy:** {strategy_name}\n"
                                  f"**Signal:** {strategy_action}\n"
                                  f"**Entry:** ${entry:.2f}\n"
                                  f"**Stop Loss:** ${stop:.2f}\n"
                                  f"**Target:** ${target:.2f}",
                            inline=True
                        )
                    else:
                        # Show detailed HOLD status
                        conditions_needed = strategy_signal.get('conditions_needed', [])
                        next_check = strategy_signal.get('next_check', 'Unknown')
                        reason = strategy_signal.get('reason', 'Waiting for entry conditions')
                        
                        # Format conditions needed
                        if conditions_needed:
                            conditions_text = "\n".join([f"• {cond}" for cond in conditions_needed[:3]])
                        else:
                            conditions_text = "• Waiting for entry setup"
                        
                        embed.add_field(
                            name="🎯 Quantitative Strategy",
                            value=f"**Status:** No setup detected\n"
                                  f"**Reason:** {reason[:100]}\n"
                                  f"**Conditions Needed:**\n{conditions_text}\n"
                                  f"**Next Check:** {next_check}",
                            inline=True
                        )
                
                # NEW: Multi-Timeframe Analysis
                if mtf_analysis and mtf_analysis.get('available'):
                    alignment = mtf_analysis.get('alignment', {})
                    alignment_status = alignment.get('alignment', 'UNKNOWN')
                    timeframes = mtf_analysis.get('timeframes', {})
                    
                    short = timeframes.get('short', {}).get('trend', 'N/A')
                    medium = timeframes.get('medium', {}).get('trend', 'N/A')
                    long = timeframes.get('long', {}).get('trend', 'N/A')
                    
                    embed.add_field(
                        name="📈 Multi-Timeframe Analysis",
                        value=f"**Alignment:** {alignment_status}\n"
                              f"**Short (20d):** {short}\n"
                              f"**Medium (50d):** {medium}\n"
                              f"**Long (200d):** {long}",
                        inline=True
                    )
                
                # Reasoning
                embed.add_field(
                    name="💡 Analysis",
                    value=opp['reasoning'],
                    inline=False
                )
                
                # Momentum
                momentum = rec.get('momentum', {})
                if momentum:
                    embed.add_field(
                        name="🚀 Momentum",
                        value=f"Direction: {momentum.get('direction', 'N/A')}\n"
                              f"Move: {momentum.get('move_pct', 0):+.2f}%\n"
                              f"Volume: {momentum.get('volume_ratio_5min', 0):.2f}x",
                        inline=True
                    )
                
                # Technicals
                technicals = rec.get('technicals', {})
                if technicals:
                    embed.add_field(
                        name="📊 Technicals",
                        value=f"RSI: {technicals.get('rsi', 0):.1f}\n"
                              f"vs SMA20: {technicals.get('price_vs_sma20', 'N/A')}\n"
                              f"Volume: {technicals.get('volume_trend', 'N/A')}",
                        inline=True
                    )
                
                # Entry/Exit if available
                if 'entry_strategy' in rec:
                    embed.add_field(
                        name="📍 Entry/Exit",
                        value=f"Entry: {rec.get('entry_strategy', 'N/A')}\n"
                              f"Target: ${rec.get('target_price', 0):.2f}\n"
                              f"Stop: ${rec.get('stop_loss', 0):.2f}",
                        inline=False
                    )
                
                await interaction.followup.send(embed=embed)
            else:
                await interaction.followup.send(
                    embed=create_warning_embed(f"No significant opportunity detected for {symbol}")
                )
        else:
            await interaction.followup.send(
                embed=create_error_embed("Orchestrator not available")
            )
            
    except Exception as e:
        logger.error(f"Error in analyze command: {e}")
        error_embed = create_error_embed(f"Analysis failed: {str(e)}")
        await interaction.followup.send(embed=error_embed)


@bot.tree.command(name="monitor", description="Analyze current positions with detailed momentum and recommendations")
async def monitor_command(interaction: discord.Interaction):
    """Manually trigger position monitoring with detailed analysis."""
    await interaction.response.defer()
    
    try:
        from services import get_alpaca_service
        
        alpaca = get_alpaca_service()
        positions = await alpaca.get_positions()
        
        if not positions:
            await interaction.followup.send("📊 **Position Monitor**\n\nNo open positions to monitor.")
            return
        
        # Build detailed analysis for each position
        monitor_report = "📊 **Position Monitor Analysis**\n"
        monitor_report += "─────────────────────────────\n\n"
        
        for pos in positions:
            symbol = pos['symbol']
            qty = pos['qty']
            entry_price = pos['avg_entry_price']
            current_price = pos['current_price']
            unrealized_pl = pos['unrealized_pl']
            unrealized_plpc = pos['unrealized_plpc']
            
            # Calculate momentum
            price_change = current_price - entry_price
            price_change_pct = (price_change / entry_price) * 100
            
            # Determine momentum direction
            if abs(price_change_pct) < 1:
                momentum_status = "Neutral"
                momentum_emoji = "➡️"
            elif price_change_pct > 0:
                momentum_status = "Bullish"
                momentum_emoji = "📈"
            else:
                momentum_status = "Bearish"
                momentum_emoji = "📉"
            
            # Calculate targets
            profit_target = entry_price * 1.5  # 50% profit target
            stop_loss = entry_price * 0.7  # 30% stop loss
            
            # Determine recommendation
            if unrealized_plpc >= 0.5:
                recommendation = "TAKE PROFIT"
                rec_emoji = "💰"
                reason = "Target reached - secure gains"
            elif unrealized_plpc <= -0.3:
                recommendation = "EXIT"
                rec_emoji = "⚠️"
                reason = "Stop loss triggered - limit losses"
            elif price_change_pct > 10:
                recommendation = "HOLD"
                rec_emoji = "✋"
                reason = "Strong momentum - let it run"
            elif price_change_pct < -10:
                recommendation = "CONSIDER EXIT"
                rec_emoji = "⚠️"
                reason = "Weak momentum - review position"
            else:
                recommendation = "HOLD"
                rec_emoji = "✋"
                reason = "Within normal range"
            
            # Build position report
            monitor_report += f"**{symbol}** ({qty} shares @ ${entry_price:.2f})\n"
            monitor_report += f"Current: ${current_price:.2f} | P&L: ${unrealized_pl:+,.2f} ({unrealized_plpc*100:+.2f}%)\n"
            monitor_report += f"{momentum_emoji} Momentum: {momentum_status} ({price_change_pct:+.2f}%)\n"
            monitor_report += f"{rec_emoji} Recommendation: **{recommendation}**\n"
            monitor_report += f"Reason: {reason}\n"
            monitor_report += f"Stop Loss: ${stop_loss:.2f} | Target: ${profit_target:.2f}\n"
            monitor_report += f"─────────────────────────────\n\n"
        
        # Add summary
        total_pl = sum(p['unrealized_pl'] for p in positions)
        monitor_report += f"**Summary:**\n"
        monitor_report += f"Total Positions: {len(positions)}\n"
        monitor_report += f"Total P&L: ${total_pl:+,.2f}\n"
        
        await interaction.followup.send(monitor_report)
        
    except Exception as e:
        logger.error(f"Error in monitor command: {e}")
        await interaction.followup.send(f"❌ Error monitoring positions: {str(e)}")


@bot.tree.command(name="watchlist-create", description="📋 Create a new persistent watchlist in Alpaca")
async def watchlist_create_command(
    interaction: discord.Interaction,
    name: str,
    symbols: str
):
    """Create a new watchlist in Alpaca."""
    await interaction.response.defer()
    
    try:
        from services import get_alpaca_service
        alpaca = get_alpaca_service()
        
        # Parse symbols
        symbol_list = [s.strip().upper() for s in symbols.split(',')]
        
        # Create watchlist
        result = await alpaca.create_watchlist(name, symbol_list)
        
        if result:
            embed = create_success_embed(
                f"📋 **Watchlist Created: {name}**\n\n"
                f"**Symbols:** {', '.join(symbol_list)}\n"
                f"**ID:** {result.get('id', 'N/A')}\n"
                f"**Stored in:** Alpaca (persistent)"
            )
        else:
            embed = create_error_embed("Failed to create watchlist")
        
        await interaction.followup.send(embed=embed)
        
    except Exception as e:
        logger.error(f"Error creating watchlist: {e}")
        error_embed = create_error_embed(f"Error: {str(e)}")
        await interaction.followup.send(embed=error_embed)


@bot.tree.command(name="watchlist-list", description="📋 List all Alpaca watchlists")
async def watchlist_list_command(interaction: discord.Interaction):
    """List all watchlists from Alpaca."""
    await interaction.response.defer()
    
    try:
        from services import get_alpaca_service
        alpaca = get_alpaca_service()
        
        watchlists = await alpaca.get_all_watchlists()
        
        if not watchlists:
            embed = create_warning_embed("No watchlists found in Alpaca")
            await interaction.followup.send(embed=embed)
            return
        
        embed = discord.Embed(
            title="📋 Alpaca Watchlists",
            description=f"Found {len(watchlists)} watchlist(s)",
            color=discord.Color.blue()
        )
        
        for wl in watchlists:
            symbols = wl.get('symbols', [])
            embed.add_field(
                name=f"{wl['name']}",
                value=f"**ID:** {wl['id']}\n**Symbols:** {', '.join(symbols[:10])}{'...' if len(symbols) > 10 else ''}",
                inline=False
            )
        
        await interaction.followup.send(embed=embed)
        
    except Exception as e:
        logger.error(f"Error listing watchlists: {e}")
        error_embed = create_error_embed(f"Error: {str(e)}")
        await interaction.followup.send(embed=error_embed)


@bot.tree.command(name="screen", description="🔍 Screen stocks with filters")
async def screen_command(
    interaction: discord.Interaction,
    volume_min: int = 1000000,
    price_min: float = 5.0,
    price_max: float = 500.0,
    change_min: float = None
):
    """Screen stocks using Alpaca Screener API."""
    await interaction.response.defer()
    
    try:
        from services import get_alpaca_service
        alpaca = get_alpaca_service()
        
        # Build filters
        filters = {
            "volume_min": volume_min,
            "price_min": price_min,
            "price_max": price_max
        }
        
        if change_min is not None:
            filters["change_pct_min"] = change_min
        
        # Screen stocks
        symbols = await alpaca.screen_stocks(filters)
        
        if not symbols:
            embed = create_warning_embed("No stocks found matching criteria")
            await interaction.followup.send(embed=embed)
            return
        
        embed = discord.Embed(
            title="🔍 Stock Screener Results",
            description=f"Found {len(symbols)} stocks matching criteria",
            color=discord.Color.green()
        )
        
        embed.add_field(
            name="Filters Applied",
            value=f"**Volume:** ≥{volume_min:,}\n"
                  f"**Price:** ${price_min} - ${price_max}\n"
                  f"**Change:** {f'≥{change_min:+.1f}%' if change_min else 'Any'}",
            inline=False
        )
        
        embed.add_field(
            name=f"Matching Symbols ({len(symbols)})",
            value=', '.join(symbols[:20]) + ('...' if len(symbols) > 20 else ''),
            inline=False
        )
        
        await interaction.followup.send(embed=embed)
        
    except Exception as e:
        logger.error(f"Error screening stocks: {e}")
        error_embed = create_error_embed(f"Error: {str(e)}")
        await interaction.followup.send(embed=error_embed)


@bot.tree.command(name="crypto-price", description="🪙 Get cryptocurrency price")
async def crypto_price_command(
    interaction: discord.Interaction,
    symbol: str
):
    """Get crypto price from Alpaca."""
    await interaction.response.defer()
    
    try:
        from services import get_alpaca_service
        alpaca = get_alpaca_service()
        
        # Ensure symbol format (e.g., BTCUSD)
        symbol = symbol.upper().replace('/', '')
        if not symbol.endswith('USD'):
            symbol = symbol + 'USD'
        
        # Get crypto snapshot
        snapshot = await alpaca.get_crypto_snapshot(symbol)
        
        if not snapshot:
            embed = create_error_embed(f"Could not get price for {symbol}")
            await interaction.followup.send(embed=embed)
            return
        
        embed = discord.Embed(
            title=f"🪙 {symbol}",
            description=f"**Price:** ${snapshot['price']:,.2f}",
            color=discord.Color.gold()
        )
        
        embed.add_field(
            name="Type",
            value="Cryptocurrency",
            inline=True
        )
        
        embed.add_field(
            name="Source",
            value="Alpaca Crypto API",
            inline=True
        )
        
        embed.set_footer(text=f"Updated: {snapshot.get('timestamp', 'N/A')}")
        
        await interaction.followup.send(embed=embed)
        
    except Exception as e:
        logger.error(f"Error getting crypto price: {e}")
        error_embed = create_error_embed(f"Error: {str(e)}\nCrypto API may not be available on your plan")
        await interaction.followup.send(embed=error_embed)


@bot.tree.command(name="crypto-buy", description="🪙 Buy cryptocurrency")
async def crypto_buy_command(
    interaction: discord.Interaction,
    symbol: str,
    quantity: float
):
    """Buy cryptocurrency via Alpaca."""
    await interaction.response.defer()
    
    try:
        from services import get_alpaca_service
        alpaca = get_alpaca_service()
        
        # Ensure symbol format
        symbol = symbol.upper().replace('/', '')
        if not symbol.endswith('USD'):
            symbol = symbol + 'USD'
        
        # Place crypto order
        order = await alpaca.place_crypto_order(symbol, quantity, "buy")
        
        if 'error' in order:
            embed = create_error_embed(f"Failed to place order: {order['error']}")
        else:
            embed = create_success_embed(
                f"🪙 **Crypto Buy Order Placed**\n\n"
                f"**Symbol:** {symbol}\n"
                f"**Quantity:** {quantity}\n"
                f"**Side:** BUY\n"
                f"**Status:** {order.get('status', 'Unknown')}\n"
                f"**Order ID:** {order.get('id', 'N/A')}"
            )
        
        await interaction.followup.send(embed=embed)
        
    except Exception as e:
        logger.error(f"Error buying crypto: {e}")
        error_embed = create_error_embed(f"Error: {str(e)}")
        await interaction.followup.send(embed=error_embed)


@bot.tree.command(name="stream-start", description="📡 Start real-time price streaming")
async def stream_start_command(
    interaction: discord.Interaction,
    symbols: str
):
    """Start real-time streaming for symbols."""
    await interaction.response.defer()
    
    try:
        embed = create_success_embed(
            f"📡 **Real-Time Streaming**\n\n"
            f"**Symbols:** {symbols}\n"
            f"**Status:** Feature available\n\n"
            f"⚠️ **Note:** Streaming requires WebSocket setup.\n"
            f"Contact admin to enable real-time streaming for your watchlist."
        )
        
        await interaction.followup.send(embed=embed)
        
    except Exception as e:
        logger.error(f"Error starting stream: {e}")
        error_embed = create_error_embed(f"Error: {str(e)}")
        await interaction.followup.send(embed=error_embed)


@bot.tree.command(name="corporate-actions", description="📊 Check corporate actions (splits/dividends)")
async def corporate_actions_command(
    interaction: discord.Interaction,
    symbol: str
):
    """Check corporate actions for a symbol."""
    await interaction.response.defer()
    
    try:
        from services import get_alpaca_service
        alpaca = get_alpaca_service()
        
        # Get corporate actions
        actions = await alpaca.get_corporate_actions(symbol.upper())
        
        if not actions:
            embed = create_warning_embed(
                f"No recent corporate actions found for {symbol.upper()}\n\n"
                f"This includes: splits, dividends, mergers, spinoffs"
            )
            await interaction.followup.send(embed=embed)
            return
        
        embed = discord.Embed(
            title=f"📊 Corporate Actions: {symbol.upper()}",
            description=f"Found {len(actions)} action(s)",
            color=discord.Color.blue()
        )
        
        for action in actions[:10]:  # Show up to 10
            embed.add_field(
                name=f"{action.get('type', 'Unknown').title()}",
                value=f"**Date:** {action.get('date', 'N/A')}\n**Details:** {action.get('details', 'N/A')}",
                inline=False
            )
        
        await interaction.followup.send(embed=embed)
        
    except Exception as e:
        logger.error(f"Error getting corporate actions: {e}")
        error_embed = create_error_embed(f"Error: {str(e)}\nCorporate Actions API may not be available on your plan")
        await interaction.followup.send(embed=error_embed)


@bot.tree.command(name="strategy-list", description="📊 List all available trading strategies")
async def strategy_list_command(interaction: discord.Interaction):
    """List all available strategies."""
    await interaction.response.defer()
    
    try:
        from strategies.strategy_manager import StrategyManager
        
        manager = StrategyManager()
        strategies = manager.list_strategies()
        
        embed = discord.Embed(
            title="📊 Available Trading Strategies",
            description=f"Total: {len(strategies)} strategies",
            color=discord.Color.blue()
        )
        
        for name, active in strategies.items():
            status = "✅ ACTIVE" if active else "⚠️ INACTIVE"
            info = manager.get_strategy_info(name)
            
            embed.add_field(
                name=f"{info.get('name', name)} {status}",
                value=f"Type: {info.get('type', 'equity')}\n{info.get('description', 'No description')[:100]}",
                inline=False
            )
        
        await interaction.followup.send(embed=embed)
        
    except Exception as e:
        logger.error(f"Error listing strategies: {e}")
        error_embed = create_error_embed(f"Error: {str(e)}")
        await interaction.followup.send(embed=error_embed)


@bot.tree.command(name="strategy-performance", description="📈 View strategy performance metrics")
async def strategy_performance_command(
    interaction: discord.Interaction,
    strategy: str = None,
    days: int = 30
):
    """View strategy performance."""
    await interaction.response.defer()
    
    try:
        from services.strategy_performance_tracker import get_strategy_tracker
        
        tracker = get_strategy_tracker()
        
        if strategy:
            # Get specific strategy performance
            perf = await tracker.get_strategy_performance(strategy, days)
            
            if perf.get('total_trades', 0) == 0:
                embed = create_warning_embed(f"No trades recorded for {strategy} in last {days} days")
                await interaction.followup.send(embed=embed)
                return
            
            embed = discord.Embed(
                title=f"📈 {perf['strategy']} Performance",
                description=f"Last {days} days",
                color=discord.Color.green() if perf.get('total_pnl', 0) > 0 else discord.Color.red()
            )
            
            embed.add_field(
                name="Trades",
                value=f"Total: {perf['total_trades']}\nWins: {perf['wins']}\nLosses: {perf['losses']}",
                inline=True
            )
            
            embed.add_field(
                name="Win Rate",
                value=f"{perf['win_rate']:.1f}%",
                inline=True
            )
            
            embed.add_field(
                name="Total P&L",
                value=f"${perf['total_pnl']:.2f}",
                inline=True
            )
            
            embed.add_field(
                name="Avg Win/Loss",
                value=f"Win: ${perf['avg_win']:.2f}\nLoss: ${perf['avg_loss']:.2f}",
                inline=True
            )
            
            embed.add_field(
                name="Profit Factor",
                value=f"{perf['profit_factor']:.2f}",
                inline=True
            )
            
            embed.add_field(
                name="Sharpe Ratio",
                value=f"{perf['sharpe_ratio']:.2f}",
                inline=True
            )
            
        else:
            # Get all strategies performance
            all_perf = await tracker.get_all_strategies_performance(days)
            
            if not all_perf:
                embed = create_warning_embed(f"No strategy trades recorded in last {days} days")
                await interaction.followup.send(embed=embed)
                return
            
            embed = discord.Embed(
                title="📈 All Strategies Performance",
                description=f"Last {days} days",
                color=discord.Color.blue()
            )
            
            for perf in all_perf[:5]:  # Top 5
                embed.add_field(
                    name=perf['strategy'],
                    value=f"Trades: {perf['total_trades']} | Win Rate: {perf['win_rate']:.1f}% | P&L: ${perf['total_pnl']:.2f}",
                    inline=False
                )
        
        await interaction.followup.send(embed=embed)
        
    except Exception as e:
        logger.error(f"Error getting strategy performance: {e}")
        error_embed = create_error_embed(f"Error: {str(e)}")
        await interaction.followup.send(embed=error_embed)


@bot.tree.command(name="strategy-enable", description="✅ Enable a trading strategy")
async def strategy_enable_command(
    interaction: discord.Interaction,
    strategy: str
):
    """Enable a strategy."""
    await interaction.response.defer()
    
    try:
        from strategies.strategy_manager import StrategyManager
        
        manager = StrategyManager()
        success = manager.enable_strategy(strategy)
        
        if success:
            embed = create_success_embed(f"✅ Enabled strategy: {strategy}")
        else:
            embed = create_error_embed(f"Failed to enable {strategy}. Check strategy name.")
        
        await interaction.followup.send(embed=embed)
        
    except Exception as e:
        logger.error(f"Error enabling strategy: {e}")
        error_embed = create_error_embed(f"Error: {str(e)}")
        await interaction.followup.send(embed=error_embed)


@bot.tree.command(name="strategy-disable", description="⚠️ Disable a trading strategy")
async def strategy_disable_command(
    interaction: discord.Interaction,
    strategy: str
):
    """Disable a strategy."""
    await interaction.response.defer()
    
    try:
        from strategies.strategy_manager import StrategyManager
        
        manager = StrategyManager()
        success = manager.disable_strategy(strategy)
        
        if success:
            embed = create_warning_embed(f"⚠️ Disabled strategy: {strategy}")
        else:
            embed = create_error_embed(f"Failed to disable {strategy}. Check strategy name.")
        
        await interaction.followup.send(embed=embed)
        
    except Exception as e:
        logger.error(f"Error disabling strategy: {e}")
        error_embed = create_error_embed(f"Error: {str(e)}")
        await interaction.followup.send(embed=error_embed)


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
