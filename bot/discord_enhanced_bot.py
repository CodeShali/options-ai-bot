"""
Enhanced Discord Bot - Main Integration
Integrates all Discord enhancement services into a single powerful bot.
"""
import asyncio
import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional, Dict, Any
from datetime import datetime
from loguru import logger

from config import settings
from services import get_alpaca_service, get_database_service, get_discord_conversation_service
from services.discord_realtime_service import get_discord_realtime_service
from services.discord_interactive_service import get_discord_interactive_service
from services.discord_alerts_service import get_discord_alerts_service
from services.discord_analytics_service import get_discord_analytics_service
from bot.discord_helpers import (
    create_status_embed,
    create_error_embed,
    create_success_embed,
    format_positions_list
)


class EnhancedTradingBot(commands.Bot):
    """Enhanced Discord bot with all professional features."""
    
    def __init__(self):
        """Initialize enhanced bot."""
        intents = discord.Intents.default()
        intents.message_content = True
        
        super().__init__(command_prefix="/", intents=intents)
        
        self.notification_channel_id = int(settings.discord_channel_id)
        self.system_paused = False
        self.orchestrator = None
        
        # Initialize all enhancement services
        self.realtime_service = None
        self.interactive_service = None
        self.alerts_service = None
        self.analytics_service = None
        self.conversation_service = None
        
        logger.info("🚀 Enhanced Discord bot initialized")
    
    async def setup_hook(self):
        """Setup hook with all enhancements."""
        await self.tree.sync()
        
        # Initialize services
        self.realtime_service = get_discord_realtime_service(self)
        self.interactive_service = get_discord_interactive_service(self)
        self.alerts_service = get_discord_alerts_service(self)
        self.analytics_service = get_discord_analytics_service(self)
        self.conversation_service = get_discord_conversation_service(self)
        
        # Start all services
        self.realtime_service.start_monitoring()
        self.alerts_service.start_monitoring()
        self.analytics_service.start_reporting()
        
        logger.info("✅ All enhanced features activated")
    
    async def on_ready(self):
        """Enhanced bot ready message."""
        logger.info(f"🌟 TARA Enhanced Edition is online!")
        
        embed = discord.Embed(
            title="🌟 TARA Trading System - Enhanced Edition",
            description="Professional-grade algorithmic trading with real-time intelligence",
            color=discord.Color.gold(),
            timestamp=datetime.now()
        )
        
        embed.add_field(
            name="✅ Enhanced Features Active",
            value=(
                "• Real-time position updates (30s intervals)\n"
                "• Interactive button controls\n"
                "• Smart alert system (volume, breakouts, Greeks, news)\n"
                "• Daily automated summaries (4:10 PM)\n"
                "• Performance analytics & charts\n"
                "• Position management panel\n"
                "• Risk calculators\n"
                "• Voice channel integration"
            ),
            inline=False
        )
        
        await self.send_notification(embed=embed)
    
    async def on_message(self, message: discord.Message):
        """Natural language chat within the trading channel and its threads."""
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
            
            if allowed and self.conversation_service:
                reply = await self.conversation_service.handle_message(message)
                if reply:
                    # Reply to keep the conversation contextual; avoid pinging the user
                    await message.reply(reply, mention_author=False)
        finally:
            # Ensure slash commands still work when on_message is overridden
            await self.process_commands(message)
    
    async def send_notification(self, message: str = None, embed: Optional[discord.Embed] = None, symbol: Optional[str] = None):
        """Enhanced notification system."""
        try:
            channel = self.get_channel(self.notification_channel_id)
            if not channel:
                return
            
            # Send to position thread if symbol provided
            if symbol and self.realtime_service and symbol in self.realtime_service.position_threads:
                try:
                    thread = channel.get_thread(self.realtime_service.position_threads[symbol])
                    if thread:
                        if embed:
                            await thread.send(message, embed=embed)
                        else:
                            await thread.send(message)
                        return
                except:
                    pass
            
            # Send to main channel
            if embed:
                await channel.send(message, embed=embed)
            else:
                await channel.send(message)
                
        except Exception as e:
            logger.error(f"Error sending notification: {e}")
    
    def set_orchestrator(self, orchestrator):
        """Set orchestrator reference."""
        self.orchestrator = orchestrator


# Create enhanced bot instance
enhanced_bot = EnhancedTradingBot()


# ==================== ENHANCED COMMANDS ====================

@enhanced_bot.tree.command(name="live-updates", description="Control real-time position updates")
@app_commands.describe(action="on/off/frequency", frequency="Update frequency in seconds (10-300)")
async def live_updates_command(interaction: discord.Interaction, action: str, frequency: int = 30):
    """Control live position updates."""
    await interaction.response.defer()
    
    try:
        if action.lower() == "on":
            enhanced_bot.realtime_service.monitoring_active = True
            await interaction.followup.send("✅ Real-time updates enabled")
        elif action.lower() == "off":
            enhanced_bot.realtime_service.monitoring_active = False
            await interaction.followup.send("⏹️ Real-time updates disabled")
        elif action.lower() == "frequency":
            await enhanced_bot.realtime_service.set_update_frequency(frequency)
            await interaction.followup.send(f"⏱️ Update frequency set to {frequency} seconds")
        else:
            await interaction.followup.send("❌ Invalid action. Use: on, off, or frequency")
            
    except Exception as e:
        await interaction.followup.send(f"❌ Error: {str(e)}")


@enhanced_bot.tree.command(name="position", description="Enhanced position management panel")
@app_commands.describe(symbol="Stock symbol")
async def position_command(interaction: discord.Interaction, symbol: str):
    """Enhanced position management with interactive controls."""
    await interaction.response.defer()
    
    try:
        symbol = symbol.upper()
        alpaca = get_alpaca_service()
        position = await alpaca.get_position(symbol)
        
        if not position:
            await interaction.followup.send(f"❌ No position found for {symbol}")
            return
        
        # Create enhanced position embed
        embed = create_enhanced_position_embed(position)
        
        # Add interactive controls
        view = enhanced_bot.interactive_service.create_position_control_view(symbol)
        
        await interaction.followup.send(embed=embed, view=view)
        
    except Exception as e:
        await interaction.followup.send(f"❌ Error: {str(e)}")


@enhanced_bot.tree.command(name="alerts", description="Configure smart alerts")
@app_commands.describe(action="setup/pause/test", hours="Hours to pause (if pausing)")
async def alerts_command(interaction: discord.Interaction, action: str, hours: int = 1):
    """Configure smart alert system."""
    await interaction.response.defer()
    
    try:
        if action.lower() == "setup":
            embed = discord.Embed(
                title="🚨 Smart Alerts Configuration",
                description="Current alert settings",
                color=discord.Color.blue()
            )
            
            settings = enhanced_bot.alerts_service.alert_settings
            embed.add_field(
                name="Alert Thresholds",
                value=(
                    f"**Volume Spike:** {settings['volume_spike_threshold']}x average\n"
                    f"**Breakout:** {settings['breakout_threshold']*100-100:.0f}% above resistance\n"
                    f"**News Sentiment:** ±{settings['news_sentiment_threshold']}\n"
                    f"**Theta Decay:** {settings['theta_decay_threshold']*100:.0f}% of position value"
                ),
                inline=False
            )
            
            await interaction.followup.send(embed=embed)
            
        elif action.lower() == "pause":
            enhanced_bot.alerts_service.alert_settings["enabled"] = False
            await interaction.followup.send(f"⏸️ Alerts paused for {hours} hours")
            
            # Auto-resume after specified hours
            await asyncio.sleep(hours * 3600)
            enhanced_bot.alerts_service.alert_settings["enabled"] = True
            
        elif action.lower() == "test":
            # Send test alert
            test_embed = discord.Embed(
                title="🧪 Test Alert",
                description="This is a test of the smart alert system",
                color=discord.Color.orange()
            )
            await enhanced_bot.alerts_service.send_smart_alert(test_embed)
            await interaction.followup.send("✅ Test alert sent")
            
    except Exception as e:
        await interaction.followup.send(f"❌ Error: {str(e)}")


@enhanced_bot.tree.command(name="performance", description="Enhanced performance dashboard")
@app_commands.describe(period="Analysis period in days (7, 30, 90)")
async def performance_command(interaction: discord.Interaction, period: int = 30):
    """Enhanced performance analysis with charts."""
    await interaction.response.defer()
    
    try:
        # Generate performance report
        embed = await enhanced_bot.analytics_service.generate_performance_report(period)
        
        # Generate chart if available
        if period <= 30:
            # For shorter periods, generate detailed chart
            chart_file = await enhanced_bot.analytics_service.generate_daily_chart({"total_pl": 0})
            if chart_file:
                await interaction.followup.send(embed=embed, file=chart_file)
            else:
                await interaction.followup.send(embed=embed)
        else:
            await interaction.followup.send(embed=embed)
            
    except Exception as e:
        await interaction.followup.send(f"❌ Error: {str(e)}")


@enhanced_bot.tree.command(name="calc-position", description="Position size calculator")
@app_commands.describe(
    symbol="Stock symbol",
    entry="Entry price",
    stop="Stop loss price", 
    risk="Risk amount in dollars"
)
async def calc_position_command(interaction: discord.Interaction, symbol: str, entry: float, stop: float, risk: float):
    """Calculate optimal position size."""
    await interaction.response.defer()
    
    try:
        # Calculate position size
        risk_per_share = abs(entry - stop)
        shares = int(risk / risk_per_share) if risk_per_share > 0 else 0
        position_value = shares * entry
        
        # Get account info for percentage calculation
        alpaca = get_alpaca_service()
        account = await alpaca.get_account()
        equity = float(account['equity'])
        position_pct = (position_value / equity * 100) if equity > 0 else 0
        risk_pct = (risk / equity * 100) if equity > 0 else 0
        
        embed = discord.Embed(
            title="🧮 Position Size Calculator",
            description=f"Optimal sizing for {symbol.upper()}",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="📊 Input Parameters",
            value=(
                f"**Symbol:** {symbol.upper()}\n"
                f"**Entry Price:** ${entry:.2f}\n"
                f"**Stop Loss:** ${stop:.2f}\n"
                f"**Risk Amount:** ${risk:.2f}"
            ),
            inline=True
        )
        
        embed.add_field(
            name="🎯 Calculated Position",
            value=(
                f"**Shares:** {shares:,}\n"
                f"**Position Value:** ${position_value:,.2f}\n"
                f"**Portfolio %:** {position_pct:.1f}%\n"
                f"**Risk %:** {risk_pct:.2f}%"
            ),
            inline=True
        )
        
        # Risk scenarios
        embed.add_field(
            name="📈 Risk Scenarios",
            value=(
                f"**1% Risk:** {int(equity * 0.01 / risk_per_share):,} shares\n"
                f"**2% Risk:** {int(equity * 0.02 / risk_per_share):,} shares\n"
                f"**3% Risk:** {int(equity * 0.03 / risk_per_share):,} shares"
            ),
            inline=False
        )
        
        await interaction.followup.send(embed=embed)
        
    except Exception as e:
        await interaction.followup.send(f"❌ Error: {str(e)}")


def create_enhanced_position_embed(position: Dict[str, Any]) -> discord.Embed:
    """Create enhanced position embed with all details."""
    symbol = position['symbol']
    current_price = float(position['current_price'])
    entry_price = float(position['avg_entry_price'])
    qty = int(position['qty'])
    pl = float(position['unrealized_pl'])
    pl_pct = float(position['unrealized_plpc']) * 100
    
    # Color based on P/L
    if pl > 0:
        color = discord.Color.green()
        emoji = "📈"
    elif pl < 0:
        color = discord.Color.red()
        emoji = "📉"
    else:
        color = discord.Color.grey()
        emoji = "➖"
    
    embed = discord.Embed(
        title=f"{emoji} {symbol} Position Details",
        description="Complete position analysis with interactive controls",
        color=color,
        timestamp=datetime.now()
    )
    
    # Current status
    embed.add_field(
        name="📊 Current Status",
        value=(
            f"**Current Price:** ${current_price:.2f}\n"
            f"**Entry Price:** ${entry_price:.2f}\n"
            f"**Quantity:** {qty:,} shares\n"
            f"**Market Value:** ${current_price * qty:,.2f}"
        ),
        inline=True
    )
    
    # P&L Analysis
    embed.add_field(
        name="💰 P&L Analysis",
        value=(
            f"**Unrealized P&L:** ${pl:+,.2f}\n"
            f"**P&L Percentage:** {pl_pct:+.2f}%\n"
            f"**Per Share P&L:** ${pl/qty:+.2f}\n"
            f"**Break Even:** ${entry_price:.2f}"
        ),
        inline=True
    )
    
    # Smart targets
    target1 = entry_price * 1.03
    target2 = entry_price * 1.06
    target3 = entry_price * 1.12
    stop_loss = entry_price * 0.98
    
    embed.add_field(
        name="🎯 Smart Targets",
        value=(
            f"**Target 1:** ${target1:.2f} (+3%) {'✅' if current_price >= target1 else ''}\n"
            f"**Target 2:** ${target2:.2f} (+6%) {'✅' if current_price >= target2 else ''}\n"
            f"**Target 3:** ${target3:.2f} (+12%) {'✅' if current_price >= target3 else ''}\n"
            f"**Stop Loss:** ${stop_loss:.2f} (-2%)"
        ),
        inline=False
    )
    
    embed.set_footer(text="Use buttons below for position management • Real-time updates active")
    
    return embed


# Export the enhanced bot
__all__ = ['enhanced_bot']
