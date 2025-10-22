"""
Discord Real-Time Updates Service
Handles live position updates, price streaming, and real-time monitoring.
"""
import asyncio
import discord
from discord.ext import tasks
from typing import Dict, Any, Optional
from datetime import datetime
from loguru import logger

from services import get_alpaca_service, get_database_service
from config import settings


class DiscordRealTimeService:
    """Real-time position updates and monitoring for Discord."""
    
    def __init__(self, bot):
        """Initialize real-time service."""
        self.bot = bot
        self.alpaca = get_alpaca_service()
        self.db = get_database_service()
        
        # Tracking
        self.position_threads = {}  # {symbol: thread_id}
        self.position_messages = {}  # {symbol: message_id} for live updates
        self.monitoring_active = True
        self.update_frequency = 30  # seconds
        
        logger.info("📡 Discord Real-Time Service initialized")
    
    def start_monitoring(self):
        """Start real-time monitoring tasks."""
        self.real_time_position_updates.start()
        logger.info("✅ Real-time position monitoring started")
    
    def stop_monitoring(self):
        """Stop real-time monitoring."""
        self.real_time_position_updates.cancel()
        self.monitoring_active = False
        logger.info("⏹️ Real-time monitoring stopped")
    
    @tasks.loop(seconds=30)
    async def real_time_position_updates(self):
        """Update all position threads every 30 seconds."""
        if not self.monitoring_active or not self.position_threads:
            return
        
        try:
            positions = await self.alpaca.get_positions()
            
            for position in positions:
                symbol = position['symbol']
                
                if symbol not in self.position_threads:
                    continue
                
                await self._update_position_thread(symbol, position)
                
        except Exception as e:
            logger.error(f"Error in real-time position updates: {e}")
    
    async def _update_position_thread(self, symbol: str, position: Dict[str, Any]):
        """Update specific position thread with live data."""
        try:
            # Get thread
            channel = self.bot.get_channel(self.bot.notification_channel_id)
            if not channel:
                return
            
            thread = channel.get_thread(self.position_threads[symbol])
            if not thread:
                return
            
            # Create live update embed
            embed = self._create_live_position_embed(position)
            
            # Update existing message or create new one
            if symbol in self.position_messages:
                try:
                    msg = await thread.fetch_message(self.position_messages[symbol])
                    await msg.edit(embed=embed)
                except:
                    # Message not found, create new one
                    msg = await thread.send(embed=embed)
                    self.position_messages[symbol] = msg.id
            else:
                msg = await thread.send(embed=embed)
                self.position_messages[symbol] = msg.id
                
        except Exception as e:
            logger.error(f"Error updating position thread for {symbol}: {e}")
    
    def _create_live_position_embed(self, position: Dict[str, Any]) -> discord.Embed:
        """Create beautiful live position update embed."""
        symbol = position['symbol']
        current_price = float(position['current_price'])
        entry_price = float(position['avg_entry_price'])
        qty = int(position['qty'])
        pl = float(position['unrealized_pl'])
        pl_pct = float(position['unrealized_plpc']) * 100
        
        # Calculate smart targets
        target1 = entry_price * 1.03  # 3% target
        target2 = entry_price * 1.06  # 6% target
        target3 = entry_price * 1.12  # 12% target
        stop_loss = entry_price * 0.98  # 2% stop
        
        # Progress calculations
        if current_price >= entry_price:
            # Progress to first target
            progress_to_target = min(100, ((current_price - entry_price) / (target1 - entry_price)) * 100)
            progress_bar = self._create_progress_bar(progress_to_target)
            target_distance = ((target1 - current_price) / current_price) * 100
            
            if current_price >= target1:
                target_text = f"🎯 Target 1 HIT! Progress to T2: {self._create_progress_bar(min(100, ((current_price - target1) / (target2 - target1)) * 100))}"
            else:
                target_text = f"Target 1: {progress_bar} {progress_to_target:.0f}% ({target_distance:.1f}% to go)"
        else:
            # Below entry - show distance to stop
            distance_to_stop = ((current_price - stop_loss) / current_price) * 100
            danger_level = "🔴 DANGER" if distance_to_stop < 1 else "⚠️ CAUTION" if distance_to_stop < 2 else "🟡 WATCH"
            target_text = f"{danger_level} Below entry | Stop distance: {distance_to_stop:.1f}%"
        
        # Time held calculation (simplified)
        time_held = self._calculate_time_held(symbol)
        
        # Color and emoji based on P/L
        if pl > 0:
            color = discord.Color.green()
            emoji = "📈"
            status = "IN PROFIT"
        elif pl < 0:
            color = discord.Color.red()
            emoji = "📉"
            status = "AT LOSS"
        else:
            color = discord.Color.grey()
            emoji = "➖"
            status = "BREAKEVEN"
        
        # Create embed
        embed = discord.Embed(
            title=f"{emoji} {symbol} Live Update",
            description=f"**Status:** {status} | **Last Update:** {datetime.now().strftime('%H:%M:%S')}",
            color=color,
            timestamp=datetime.now()
        )
        
        # Price movement section
        price_change = current_price - entry_price
        price_change_emoji = "🟢" if price_change > 0 else "🔴" if price_change < 0 else "⚪"
        
        embed.add_field(
            name="💹 Price Movement",
            value=(
                f"**Current:** ${current_price:.2f}\n"
                f"**Entry:** ${entry_price:.2f}\n"
                f"**Change:** {price_change_emoji} ${price_change:+.2f} ({pl_pct:+.2f}%)"
            ),
            inline=True
        )
        
        # P&L section
        embed.add_field(
            name="💰 Profit/Loss",
            value=(
                f"**Total P/L:** ${pl:+,.2f}\n"
                f"**Per Share:** ${pl/qty:+.2f}\n"
                f"**Percentage:** {pl_pct:+.2f}%"
            ),
            inline=True
        )
        
        # Position details
        position_value = qty * current_price
        embed.add_field(
            name="📊 Position Info",
            value=(
                f"**Quantity:** {qty:,} shares\n"
                f"**Value:** ${position_value:,.2f}\n"
                f"**Time Held:** {time_held}"
            ),
            inline=True
        )
        
        # Progress to targets
        embed.add_field(
            name="🎯 Target Progress",
            value=target_text,
            inline=False
        )
        
        # Smart targets display
        embed.add_field(
            name="🎯 Smart Targets",
            value=(
                f"**T1:** ${target1:.2f} (+3%) {'✅' if current_price >= target1 else ''}\n"
                f"**T2:** ${target2:.2f} (+6%) {'✅' if current_price >= target2 else ''}\n"
                f"**T3:** ${target3:.2f} (+12%) {'✅' if current_price >= target3 else ''}"
            ),
            inline=True
        )
        
        # Risk management
        embed.add_field(
            name="🛡️ Risk Management",
            value=(
                f"**Stop Loss:** ${stop_loss:.2f} (-2%)\n"
                f"**Risk:** ${abs(entry_price - stop_loss) * qty:.2f}\n"
                f"**R:R Ratio:** 1:1.5"
            ),
            inline=True
        )
        
        # Add momentum indicator
        momentum = self._calculate_momentum(symbol, current_price, entry_price)
        embed.add_field(
            name="📈 Momentum",
            value=momentum,
            inline=False
        )
        
        embed.set_footer(text=f"Updates every {self.update_frequency}s | Real-time monitoring • Use buttons below for actions")
        
        return embed
    
    def _create_progress_bar(self, percentage: float) -> str:
        """Create visual progress bar."""
        percentage = max(0, min(100, percentage))
        filled = int(percentage / 10)
        empty = 10 - filled
        return "▓" * filled + "░" * empty
    
    def _calculate_time_held(self, symbol: str) -> str:
        """Calculate time held for position (simplified)."""
        # In real implementation, would track entry time in database
        # For now, return placeholder
        return "2h 15m"
    
    def _calculate_momentum(self, symbol: str, current_price: float, entry_price: float) -> str:
        """Calculate momentum indicator."""
        change_pct = ((current_price - entry_price) / entry_price) * 100
        
        if change_pct > 2:
            return "🚀 Strong Bullish Momentum"
        elif change_pct > 0.5:
            return "📈 Positive Momentum"
        elif change_pct > -0.5:
            return "➖ Neutral/Sideways"
        elif change_pct > -2:
            return "📉 Negative Momentum"
        else:
            return "🔴 Strong Bearish Momentum"
    
    async def create_position_thread(self, symbol: str, entry_price: float, quantity: int) -> Optional[int]:
        """Create enhanced position thread with real-time updates."""
        try:
            channel = self.bot.get_channel(self.bot.notification_channel_id)
            if not channel:
                return None
            
            # Create thread with enhanced name
            thread_name = f"📈 {symbol} • ${entry_price:.2f} × {quantity:,} • Live Updates"
            message = await channel.send(f"🆕 **New Position Opened:** {symbol}")
            thread = await message.create_thread(name=thread_name, auto_archive_duration=1440)
            
            # Store thread ID
            self.position_threads[symbol] = thread.id
            
            # Send enhanced initial message
            embed = discord.Embed(
                title=f"📈 Position Opened: {symbol}",
                description="Real-time monitoring activated • Updates every 30 seconds",
                color=discord.Color.blue(),
                timestamp=datetime.now()
            )
            
            embed.add_field(
                name="📊 Entry Details",
                value=(
                    f"**Symbol:** {symbol}\n"
                    f"**Entry Price:** ${entry_price:.2f}\n"
                    f"**Quantity:** {quantity:,} shares\n"
                    f"**Total Cost:** ${entry_price * quantity:,.2f}"
                ),
                inline=True
            )
            
            # Calculate targets
            target1 = entry_price * 1.03
            target2 = entry_price * 1.06
            target3 = entry_price * 1.12
            stop_loss = entry_price * 0.98
            
            embed.add_field(
                name="🎯 Smart Targets",
                value=(
                    f"**Target 1:** ${target1:.2f} (+3%)\n"
                    f"**Target 2:** ${target2:.2f} (+6%)\n"
                    f"**Target 3:** ${target3:.2f} (+12%)\n"
                    f"**Stop Loss:** ${stop_loss:.2f} (-2%)"
                ),
                inline=True
            )
            
            embed.add_field(
                name="⚡ Live Features",
                value=(
                    "• Real-time price updates\n"
                    "• Progress tracking\n"
                    "• Smart alerts\n"
                    "• Interactive controls\n"
                    "• Risk monitoring"
                ),
                inline=False
            )
            
            await thread.send(embed=embed)
            
            logger.info(f"📈 Created enhanced position thread for {symbol}: {thread.id}")
            return thread.id
            
        except Exception as e:
            logger.error(f"Error creating position thread: {e}")
            return None
    
    async def close_position_thread(self, symbol: str, final_pl: float):
        """Close position thread with enhanced summary."""
        try:
            if symbol not in self.position_threads:
                return
            
            channel = self.bot.get_channel(self.bot.notification_channel_id)
            if not channel:
                return
            
            thread = channel.get_thread(self.position_threads[symbol])
            if thread:
                # Create final summary embed
                emoji = "🟢" if final_pl > 0 else "🔴"
                status = "PROFIT" if final_pl > 0 else "LOSS"
                
                embed = discord.Embed(
                    title=f"{emoji} Position Closed: {symbol}",
                    description=f"**Final Result:** {status}",
                    color=discord.Color.green() if final_pl > 0 else discord.Color.red(),
                    timestamp=datetime.now()
                )
                
                embed.add_field(
                    name="💰 Final P&L",
                    value=(
                        f"**Total P&L:** ${final_pl:+,.2f}\n"
                        f"**Status:** {status}\n"
                        f"**Closed:** {datetime.now().strftime('%H:%M:%S')}"
                    ),
                    inline=True
                )
                
                # Add performance metrics
                time_held = self._calculate_time_held(symbol)
                embed.add_field(
                    name="📊 Performance",
                    value=(
                        f"**Time Held:** {time_held}\n"
                        f"**Strategy:** Smart Exit\n"
                        f"**Execution:** Automated"
                    ),
                    inline=True
                )
                
                embed.set_footer(text="Position monitoring ended • Thread will be archived")
                
                await thread.send(embed=embed)
                
                # Archive thread after delay
                await asyncio.sleep(5)
                await thread.edit(archived=True)
            
            # Clean up tracking
            del self.position_threads[symbol]
            if symbol in self.position_messages:
                del self.position_messages[symbol]
            
            logger.info(f"📉 Closed position thread for {symbol}")
            
        except Exception as e:
            logger.error(f"Error closing position thread: {e}")
    
    async def set_update_frequency(self, seconds: int):
        """Change update frequency."""
        if seconds < 10:
            seconds = 10  # Minimum 10 seconds
        elif seconds > 300:
            seconds = 300  # Maximum 5 minutes
        
        self.update_frequency = seconds
        
        # Restart task with new frequency
        self.real_time_position_updates.cancel()
        self.real_time_position_updates.change_interval(seconds=seconds)
        self.real_time_position_updates.start()
        
        logger.info(f"📡 Update frequency changed to {seconds} seconds")
    
    def get_monitoring_status(self) -> Dict[str, Any]:
        """Get current monitoring status."""
        return {
            "active": self.monitoring_active,
            "update_frequency": self.update_frequency,
            "monitored_positions": len(self.position_threads),
            "position_symbols": list(self.position_threads.keys()),
            "last_update": datetime.now().isoformat()
        }


# Singleton instance
_discord_realtime_service = None

def get_discord_realtime_service(bot=None):
    """Get or create Discord real-time service."""
    global _discord_realtime_service
    if _discord_realtime_service is None and bot:
        _discord_realtime_service = DiscordRealTimeService(bot)
    return _discord_realtime_service
