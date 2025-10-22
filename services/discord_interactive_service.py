"""
Discord Interactive Controls Service
Handles buttons, modals, position management, and interactive UI elements.
"""
import asyncio
import discord
from discord import ui
from typing import Dict, Any, Optional
from datetime import datetime
from loguru import logger

from services import get_alpaca_service, get_database_service
from config import settings


class DiscordInteractiveService:
    """Interactive controls and UI elements for Discord."""
    
    def __init__(self, bot):
        """Initialize interactive service."""
        self.bot = bot
        self.alpaca = get_alpaca_service()
        self.db = get_database_service()
        
        logger.info("🎮 Discord Interactive Service initialized")
    
    # ==================== POSITION CONTROL VIEWS ====================
    
    class PositionControlView(ui.View):
        """Interactive buttons for position management."""
        
        def __init__(self, symbol: str, service):
            super().__init__(timeout=None)
            self.symbol = symbol
            self.service = service
        
        @ui.button(label="Sell 25%", style=discord.ButtonStyle.primary, emoji="💹")
        async def sell_25(self, interaction: discord.Interaction, button: ui.Button):
            await self.service.handle_partial_sell(interaction, self.symbol, 0.25)
        
        @ui.button(label="Sell 50%", style=discord.ButtonStyle.primary, emoji="💹")
        async def sell_50(self, interaction: discord.Interaction, button: ui.Button):
            await self.service.handle_partial_sell(interaction, self.symbol, 0.50)
        
        @ui.button(label="Sell 75%", style=discord.ButtonStyle.secondary, emoji="💹")
        async def sell_75(self, interaction: discord.Interaction, button: ui.Button):
            await self.service.handle_partial_sell(interaction, self.symbol, 0.75)
        
        @ui.button(label="Close All", style=discord.ButtonStyle.danger, emoji="🚪")
        async def sell_all(self, interaction: discord.Interaction, button: ui.Button):
            await self.service.handle_partial_sell(interaction, self.symbol, 1.0)
        
        @ui.button(label="Set Target", style=discord.ButtonStyle.secondary, emoji="🎯", row=1)
        async def set_target(self, interaction: discord.Interaction, button: ui.Button):
            await interaction.response.send_modal(self.service.SetTargetModal(self.symbol, self.service))
        
        @ui.button(label="Set Stop", style=discord.ButtonStyle.secondary, emoji="🛑", row=1)
        async def set_stop(self, interaction: discord.Interaction, button: ui.Button):
            await interaction.response.send_modal(self.service.SetStopModal(self.symbol, self.service))
        
        @ui.button(label="Trailing Stop", style=discord.ButtonStyle.secondary, emoji="📈", row=1)
        async def trailing_stop(self, interaction: discord.Interaction, button: ui.Button):
            await interaction.response.send_modal(self.service.TrailingStopModal(self.symbol, self.service))
        
        @ui.button(label="View Chart", style=discord.ButtonStyle.secondary, emoji="📊", row=1)
        async def view_chart(self, interaction: discord.Interaction, button: ui.Button):
            await self.service.send_position_chart(interaction, self.symbol)
        
        @ui.button(label="Latest News", style=discord.ButtonStyle.secondary, emoji="📰", row=1)
        async def latest_news(self, interaction: discord.Interaction, button: ui.Button):
            await self.service.send_position_news(interaction, self.symbol)
    
    # ==================== MODALS FOR INPUT ====================
    
    class SetTargetModal(ui.Modal):
        """Modal for setting custom target price."""
        
        def __init__(self, symbol: str, service):
            super().__init__(title=f"Set Target Price for {symbol}")
            self.symbol = symbol
            self.service = service
            
            self.target_price = ui.TextInput(
                label="Target Price ($)",
                placeholder="Enter target price (e.g., 185.50)",
                required=True,
                max_length=10
            )
            self.add_item(self.target_price)
            
            self.quantity = ui.TextInput(
                label="Quantity (% or shares)",
                placeholder="50% or 100 (shares)",
                required=False,
                max_length=10
            )
            self.add_item(self.quantity)
        
        async def on_submit(self, interaction: discord.Interaction):
            try:
                target = float(self.target_price.value)
                qty_input = self.quantity.value.strip()
                
                # Parse quantity
                if qty_input.endswith('%'):
                    qty_pct = float(qty_input[:-1]) / 100
                    qty_text = f"{qty_pct*100:.0f}% of position"
                elif qty_input:
                    qty_shares = int(qty_input)
                    qty_text = f"{qty_shares} shares"
                else:
                    qty_text = "entire position"
                
                # Store target in database
                await self.service.db.store_custom_target(self.symbol, target, qty_input)
                
                embed = discord.Embed(
                    title="✅ Target Price Set",
                    description=f"Target set for **{self.symbol}**",
                    color=discord.Color.green()
                )
                
                embed.add_field(
                    name="Target Details",
                    value=(
                        f"**Price:** ${target:.2f}\n"
                        f"**Quantity:** {qty_text}\n"
                        f"**Set At:** {datetime.now().strftime('%H:%M:%S')}"
                    ),
                    inline=False
                )
                
                await interaction.response.send_message(embed=embed, ephemeral=True)
                
            except ValueError:
                await interaction.response.send_message(
                    "❌ Invalid input format. Use numbers only (e.g., 185.50 for price, 50% or 100 for quantity)",
                    ephemeral=True
                )
    
    class SetStopModal(ui.Modal):
        """Modal for setting custom stop loss."""
        
        def __init__(self, symbol: str, service):
            super().__init__(title=f"Set Stop Loss for {symbol}")
            self.symbol = symbol
            self.service = service
            
            self.stop_price = ui.TextInput(
                label="Stop Loss Price ($)",
                placeholder="Enter stop price (e.g., 170.50)",
                required=True,
                max_length=10
            )
            self.add_item(self.stop_price)
            
            self.stop_type = ui.TextInput(
                label="Stop Type",
                placeholder="market, limit, or trailing",
                required=False,
                max_length=10,
                default="market"
            )
            self.add_item(self.stop_type)
        
        async def on_submit(self, interaction: discord.Interaction):
            try:
                stop = float(self.stop_price.value)
                stop_type = self.stop_type.value.lower() or "market"
                
                # Store stop in database
                await self.service.db.store_custom_stop(self.symbol, stop, stop_type)
                
                embed = discord.Embed(
                    title="✅ Stop Loss Set",
                    description=f"Stop loss configured for **{self.symbol}**",
                    color=discord.Color.orange()
                )
                
                embed.add_field(
                    name="Stop Details",
                    value=(
                        f"**Price:** ${stop:.2f}\n"
                        f"**Type:** {stop_type.title()}\n"
                        f"**Set At:** {datetime.now().strftime('%H:%M:%S')}"
                    ),
                    inline=False
                )
                
                await interaction.response.send_message(embed=embed, ephemeral=True)
                
            except ValueError:
                await interaction.response.send_message(
                    "❌ Invalid price format. Use numbers only (e.g., 170.50)",
                    ephemeral=True
                )
    
    class TrailingStopModal(ui.Modal):
        """Modal for setting trailing stop."""
        
        def __init__(self, symbol: str, service):
            super().__init__(title=f"Set Trailing Stop for {symbol}")
            self.symbol = symbol
            self.service = service
            
            self.trail_percent = ui.TextInput(
                label="Trail Percentage (%)",
                placeholder="Enter trail % (e.g., 2.5 for 2.5%)",
                required=True,
                max_length=5
            )
            self.add_item(self.trail_percent)
            
            self.activation_price = ui.TextInput(
                label="Activation Price (Optional)",
                placeholder="Price to activate trailing (optional)",
                required=False,
                max_length=10
            )
            self.add_item(self.activation_price)
        
        async def on_submit(self, interaction: discord.Interaction):
            try:
                trail_pct = float(self.trail_percent.value)
                activation = float(self.activation_price.value) if self.activation_price.value else None
                
                # Store trailing stop configuration
                await self.service.db.store_trailing_stop(self.symbol, trail_pct, activation)
                
                embed = discord.Embed(
                    title="✅ Trailing Stop Set",
                    description=f"Trailing stop configured for **{self.symbol}**",
                    color=discord.Color.blue()
                )
                
                embed.add_field(
                    name="Trailing Stop Details",
                    value=(
                        f"**Trail Percentage:** {trail_pct}%\n"
                        f"**Activation Price:** ${activation:.2f}" if activation else "**Activation:** Immediate\n"
                        f"**Set At:** {datetime.now().strftime('%H:%M:%S')}"
                    ),
                    inline=False
                )
                
                await interaction.response.send_message(embed=embed, ephemeral=True)
                
            except ValueError:
                await interaction.response.send_message(
                    "❌ Invalid input format. Use numbers only (e.g., 2.5 for percentage)",
                    ephemeral=True
                )
    
    # ==================== CONFIRMATION VIEWS ====================
    
    class TradeConfirmationView(ui.View):
        """Confirmation dialog for trades."""
        
        def __init__(self, service, symbol: str, action: str, quantity: int, price: float):
            super().__init__(timeout=30)
            self.service = service
            self.symbol = symbol
            self.action = action
            self.quantity = quantity
            self.price = price
        
        @ui.button(label="✅ Confirm Trade", style=discord.ButtonStyle.success)
        async def confirm(self, interaction: discord.Interaction, button: ui.Button):
            await interaction.response.defer()
            
            # Execute trade
            result = await self.service.execute_trade(self.symbol, self.action, self.quantity, self.price)
            
            if result['success']:
                embed = discord.Embed(
                    title="✅ Trade Executed",
                    description=f"Successfully {self.action} {self.quantity} shares of {self.symbol}",
                    color=discord.Color.green()
                )
                
                embed.add_field(
                    name="Execution Details",
                    value=(
                        f"**Order ID:** {result.get('order_id', 'N/A')}\n"
                        f"**Status:** {result.get('status', 'Submitted')}\n"
                        f"**Time:** {datetime.now().strftime('%H:%M:%S')}"
                    ),
                    inline=False
                )
                
                await interaction.followup.send(embed=embed)
            else:
                await interaction.followup.send(f"❌ Trade failed: {result.get('error')}")
            
            self.stop()
        
        @ui.button(label="❌ Cancel", style=discord.ButtonStyle.danger)
        async def cancel(self, interaction: discord.Interaction, button: ui.Button):
            await interaction.response.send_message("❌ Trade cancelled", ephemeral=True)
            self.stop()
        
        @ui.button(label="📊 Preview", style=discord.ButtonStyle.secondary)
        async def preview(self, interaction: discord.Interaction, button: ui.Button):
            # Show detailed preview
            embed = discord.Embed(
                title="📊 Trade Preview",
                description=f"Detailed preview for {self.symbol} trade",
                color=discord.Color.blue()
            )
            
            # Calculate impact
            total_value = self.quantity * self.price
            
            embed.add_field(
                name="Trade Impact",
                value=(
                    f"**Total Value:** ${total_value:,.2f}\n"
                    f"**Commission:** ~$1.00\n"
                    f"**Net Proceeds:** ${total_value - 1:,.2f}"
                ),
                inline=False
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
    
    # ==================== MAIN METHODS ====================
    
    async def handle_partial_sell(self, interaction: discord.Interaction, symbol: str, percentage: float):
        """Handle partial position sell with confirmation."""
        try:
            # Get position details
            position = await self.alpaca.get_position(symbol)
            
            if not position:
                await interaction.response.send_message(f"❌ No position found for {symbol}", ephemeral=True)
                return
            
            qty_to_sell = int(float(position['qty']) * percentage)
            current_price = float(position['current_price'])
            value = qty_to_sell * current_price
            
            # Create confirmation embed
            embed = discord.Embed(
                title="⚠️ Confirm Trade",
                description=f"Confirm {percentage*100:.0f}% position sale",
                color=discord.Color.orange(),
                timestamp=datetime.now()
            )
            
            embed.add_field(
                name="Trade Details",
                value=(
                    f"**Symbol:** {symbol}\n"
                    f"**Action:** SELL\n"
                    f"**Quantity:** {qty_to_sell:,} shares ({percentage*100:.0f}%)\n"
                    f"**Est. Price:** ${current_price:.2f}\n"
                    f"**Est. Value:** ${value:,.2f}"
                ),
                inline=True
            )
            
            # Calculate remaining position
            remaining_qty = int(float(position['qty'])) - qty_to_sell
            remaining_value = remaining_qty * current_price
            
            embed.add_field(
                name="Remaining Position",
                value=(
                    f"**Remaining:** {remaining_qty:,} shares\n"
                    f"**Value:** ${remaining_value:,.2f}\n"
                    f"**Percentage:** {(1-percentage)*100:.0f}%"
                ),
                inline=True
            )
            
            # P&L impact
            entry_price = float(position['avg_entry_price'])
            pl_per_share = current_price - entry_price
            total_pl = pl_per_share * qty_to_sell
            
            embed.add_field(
                name="P&L Impact",
                value=(
                    f"**P&L per Share:** ${pl_per_share:+.2f}\n"
                    f"**Total P&L:** ${total_pl:+,.2f}\n"
                    f"**P&L %:** {(pl_per_share/entry_price)*100:+.2f}%"
                ),
                inline=False
            )
            
            # Confirmation view
            view = self.TradeConfirmationView(self, symbol, "sell", qty_to_sell, current_price)
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error handling partial sell: {e}")
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)
    
    async def execute_trade(self, symbol: str, action: str, quantity: int, price: float) -> Dict[str, Any]:
        """Execute trade order."""
        try:
            order = await self.alpaca.place_order(
                symbol=symbol,
                qty=quantity,
                side=action,
                order_type='market',
                time_in_force='day'
            )
            
            return {
                "success": True,
                "order_id": order.get('id'),
                "status": order.get('status'),
                "order": order
            }
            
        except Exception as e:
            logger.error(f"Error executing trade: {e}")
            return {"success": False, "error": str(e)}
    
    async def send_position_chart(self, interaction: discord.Interaction, symbol: str):
        """Send position chart image."""
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Generate chart (placeholder - would use real charting)
            chart_url = f"https://finviz.com/chart.ashx?t={symbol}&ty=c&ta=1&p=d&s=l"
            
            embed = discord.Embed(
                title=f"📊 {symbol} Chart",
                description="Real-time price chart",
                color=discord.Color.blue()
            )
            
            embed.set_image(url=chart_url)
            embed.set_footer(text="Chart provided by FinViz")
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            await interaction.followup.send(f"❌ Error loading chart: {str(e)}", ephemeral=True)
    
    async def send_position_news(self, interaction: discord.Interaction, symbol: str):
        """Send latest news for position."""
        await interaction.response.defer(ephemeral=True)
        
        try:
            from services.news_monitor_service import get_news_monitor_service
            
            news_service = get_news_monitor_service()
            news_alerts = await news_service._check_symbol_news(symbol, minutes=60)
            
            embed = discord.Embed(
                title=f"📰 Latest News: {symbol}",
                description="Recent news and sentiment",
                color=discord.Color.blue(),
                timestamp=datetime.now()
            )
            
            if news_alerts:
                for i, alert in enumerate(news_alerts[:3], 1):
                    embed.add_field(
                        name=f"News #{i}",
                        value=(
                            f"**Headline:** {alert['news_item']['headline'][:100]}...\n"
                            f"**Sentiment:** {alert['sentiment']}\n"
                            f"**Time:** {alert['timestamp'][:19]}"
                        ),
                        inline=False
                    )
            else:
                embed.add_field(
                    name="No Recent News",
                    value="No significant news found in the last hour",
                    inline=False
                )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            await interaction.followup.send(f"❌ Error loading news: {str(e)}", ephemeral=True)
    
    def create_position_control_view(self, symbol: str) -> ui.View:
        """Create position control view for a symbol."""
        return self.PositionControlView(symbol, self)


# Singleton instance
_discord_interactive_service = None

def get_discord_interactive_service(bot=None):
    """Get or create Discord interactive service."""
    global _discord_interactive_service
    if _discord_interactive_service is None and bot:
        _discord_interactive_service = DiscordInteractiveService(bot)
    return _discord_interactive_service
