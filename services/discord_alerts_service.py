"""
Discord Smart Alerts Service
Handles intelligent alerts, notifications, and proactive monitoring.
"""
import asyncio
import discord
from discord import ui
from discord.ext import tasks
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from loguru import logger
import statistics

from services import get_alpaca_service, get_database_service
from services.news_monitor_service import get_news_monitor_service
from services.options_greeks_monitor import get_options_greeks_monitor
from services.volume_momentum_analyzer import get_volume_momentum_analyzer
from config import settings


class DiscordAlertsService:
    """Smart alerts and proactive notifications for Discord."""
    
    def __init__(self, bot):
        """Initialize alerts service."""
        self.bot = bot
        self.alpaca = get_alpaca_service()
        self.db = get_database_service()
        self.news_monitor = get_news_monitor_service()
        self.greeks_monitor = get_options_greeks_monitor()
        self.volume_analyzer = get_volume_momentum_analyzer()
        
        # Alert tracking
        self.alert_history = []
        self.alert_settings = {
            "volume_spike_threshold": 2.5,
            "breakout_threshold": 1.01,
            "news_sentiment_threshold": 0.5,
            "theta_decay_threshold": 0.05,
            "enabled": True
        }
        
        logger.info("🚨 Discord Smart Alerts Service initialized")
    
    def start_monitoring(self):
        """Start smart alert monitoring."""
        self.smart_alert_monitor.start()
        logger.info("✅ Smart alerts monitoring started")
    
    def stop_monitoring(self):
        """Stop smart alert monitoring."""
        self.smart_alert_monitor.cancel()
        logger.info("⏹️ Smart alerts monitoring stopped")
    
    @tasks.loop(seconds=60)
    async def smart_alert_monitor(self):
        """Main smart alert monitoring loop."""
        if not self.alert_settings["enabled"]:
            return
        
        # Check market hours (skip alerts during off-hours unless test mode)
        from config import settings
        if not settings.test_mode:
            from datetime import datetime
            now = datetime.now()
            # Skip on weekends
            if now.weekday() >= 5:
                return
            # Skip outside market hours (9:30 AM - 4:00 PM ET)
            market_hour = now.hour
            if market_hour < 9 or market_hour >= 16:
                return
        
        try:
            # Run all alert checks (news alerts less frequently)
            await asyncio.gather(
                self.check_volume_spikes(),
                self.check_breakouts(),
                self.check_options_greeks_alerts(),
                return_exceptions=True
            )
            
            # Check news alerts only every 5 minutes (not every minute)
            if not hasattr(self, '_news_check_counter'):
                self._news_check_counter = 0
            self._news_check_counter += 1
            
            if self._news_check_counter >= 5:  # Every 5 minutes
                await self.check_news_alerts()
                self._news_check_counter = 0
            
        except Exception as e:
            logger.error(f"Error in smart alert monitor: {e}")
    
    # ==================== VOLUME SPIKE ALERTS ====================
    
    async def check_volume_spikes(self):
        """Check for volume spikes on positions and watchlist."""
        try:
            positions = await self.alpaca.get_positions()
            
            for position in positions:
                symbol = position['symbol']
                
                # Get recent volume data
                bars = await self.alpaca.get_bars(symbol, timeframe='1Min', limit=20)
                if not bars or len(bars) < 20:
                    continue
                
                # Calculate volume metrics
                volumes = [bar['volume'] for bar in bars[:-1]]
                avg_volume = statistics.mean(volumes)
                current_volume = bars[-1]['volume']
                volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1
                
                # Check for significant spike
                if volume_ratio >= self.alert_settings["volume_spike_threshold"]:
                    await self.send_volume_spike_alert(symbol, volume_ratio, bars[-1])
                    
        except Exception as e:
            logger.error(f"Error checking volume spikes: {e}")
    
    async def send_volume_spike_alert(self, symbol: str, volume_ratio: float, bar: Dict[str, Any]):
        """Send volume spike alert with interactive options."""
        try:
            current_price = bar['close']
            volume = bar['volume']
            
            # Determine alert severity
            if volume_ratio >= 5.0:
                severity = "MASSIVE"
                color = discord.Color.gold()
                emoji = "🚀"
            elif volume_ratio >= 3.0:
                severity = "MAJOR"
                color = discord.Color.orange()
                emoji = "📈"
            else:
                severity = "SIGNIFICANT"
                color = discord.Color.blue()
                emoji = "📊"
            
            embed = discord.Embed(
                title=f"{emoji} {severity} VOLUME SPIKE: {symbol}",
                description="Unusual trading activity detected",
                color=color,
                timestamp=datetime.now()
            )
            
            embed.add_field(
                name="📊 Volume Metrics",
                value=(
                    f"**Current Volume:** {volume:,}\n"
                    f"**Volume Ratio:** {volume_ratio:.1f}x average\n"
                    f"**Severity:** {severity}"
                ),
                inline=True
            )
            
            embed.add_field(
                name="💹 Price Action",
                value=(
                    f"**Current Price:** ${current_price:.2f}\n"
                    f"**Time:** {datetime.now().strftime('%H:%M:%S')}\n"
                    f"**Status:** Active monitoring"
                ),
                inline=True
            )
            
            # Add recommendation
            recommendation = self.get_volume_spike_recommendation(volume_ratio)
            embed.add_field(
                name="💡 Recommendation",
                value=recommendation,
                inline=False
            )
            
            # Interactive buttons
            class VolumeAlertView(ui.View):
                def __init__(self, service, symbol):
                    super().__init__(timeout=300)
                    self.service = service
                    self.symbol = symbol
                
                @ui.button(label="📊 Detailed Analysis", style=discord.ButtonStyle.primary)
                async def analyze(self, interaction: discord.Interaction, button: ui.Button):
                    await self.service.send_detailed_volume_analysis(interaction, self.symbol)
                
                @ui.button(label="➕ Add Price Alert", style=discord.ButtonStyle.secondary)
                async def add_alert(self, interaction: discord.Interaction, button: ui.Button):
                    await interaction.response.send_message(f"Price alert added for {self.symbol}", ephemeral=True)
                
                @ui.button(label="📈 View Chart", style=discord.ButtonStyle.secondary)
                async def view_chart(self, interaction: discord.Interaction, button: ui.Button):
                    chart_url = f"https://finviz.com/chart.ashx?t={self.symbol}&ty=c&ta=1&p=d&s=l"
                    chart_embed = discord.Embed(title=f"📊 {self.symbol} Chart", color=discord.Color.blue())
                    chart_embed.set_image(url=chart_url)
                    await interaction.response.send_message(embed=chart_embed, ephemeral=True)
                
                @ui.button(label="🔕 Dismiss", style=discord.ButtonStyle.danger)
                async def dismiss(self, interaction: discord.Interaction, button: ui.Button):
                    await interaction.response.send_message("Alert dismissed", ephemeral=True)
                    self.stop()
            
            view = VolumeAlertView(self, symbol)
            await self.send_smart_alert(embed, view)
            
        except Exception as e:
            logger.error(f"Error sending volume spike alert: {e}")
    
    def get_volume_spike_recommendation(self, volume_ratio: float) -> str:
        """Get recommendation based on volume spike magnitude."""
        if volume_ratio >= 5.0:
            return "🚨 **MASSIVE SPIKE** - Major news or institutional activity likely. Monitor for breakout/breakdown."
        elif volume_ratio >= 3.0:
            return "⚡ **MAJOR SPIKE** - Significant interest. Watch for price movement confirmation."
        else:
            return "📊 **NOTABLE SPIKE** - Increased activity. Monitor for continuation or reversal."
    
    # ==================== BREAKOUT ALERTS ====================
    
    async def check_breakouts(self):
        """Check for breakout patterns."""
        try:
            positions = await self.alpaca.get_positions()
            
            for position in positions:
                symbol = position['symbol']
                
                # Get price data for breakout analysis
                bars = await self.alpaca.get_bars(symbol, timeframe='5Min', limit=50)
                if not bars or len(bars) < 50:
                    continue
                
                # Analyze for breakouts
                breakout_result = self.analyze_breakout_pattern(bars)
                
                if breakout_result['detected']:
                    await self.send_breakout_alert(symbol, breakout_result)
                    
        except Exception as e:
            logger.error(f"Error checking breakouts: {e}")
    
    def analyze_breakout_pattern(self, bars: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze price bars for breakout patterns."""
        try:
            # Calculate resistance/support levels
            highs = [bar['high'] for bar in bars[:-5]]
            lows = [bar['low'] for bar in bars[:-5]]
            volumes = [bar['volume'] for bar in bars[:-5]]
            
            resistance = max(highs)
            support = min(lows)
            avg_volume = statistics.mean(volumes)
            
            current_bar = bars[-1]
            current_price = current_bar['close']
            current_volume = current_bar['volume']
            
            # Check for breakout above resistance
            if current_price > resistance * self.alert_settings["breakout_threshold"]:
                volume_confirmation = current_volume > avg_volume * 1.5
                
                return {
                    "detected": True,
                    "type": "BREAKOUT_ABOVE",
                    "level": resistance,
                    "current_price": current_price,
                    "volume_confirmation": volume_confirmation,
                    "strength": "STRONG" if volume_confirmation else "WEAK"
                }
            
            # Check for breakdown below support
            elif current_price < support * (2 - self.alert_settings["breakout_threshold"]):
                volume_confirmation = current_volume > avg_volume * 1.5
                
                return {
                    "detected": True,
                    "type": "BREAKDOWN_BELOW",
                    "level": support,
                    "current_price": current_price,
                    "volume_confirmation": volume_confirmation,
                    "strength": "STRONG" if volume_confirmation else "WEAK"
                }
            
            return {"detected": False}
            
        except Exception as e:
            logger.error(f"Error analyzing breakout pattern: {e}")
            return {"detected": False}
    
    async def send_breakout_alert(self, symbol: str, breakout: Dict[str, Any]):
        """Send breakout alert with trade suggestions."""
        try:
            breakout_type = breakout['type']
            level = breakout['level']
            current_price = breakout['current_price']
            volume_confirmed = breakout['volume_confirmation']
            strength = breakout['strength']
            
            # Determine colors and emojis
            if breakout_type == "BREAKOUT_ABOVE":
                color = discord.Color.green()
                emoji = "📈"
                direction = "BULLISH"
            else:
                color = discord.Color.red()
                emoji = "📉"
                direction = "BEARISH"
            
            embed = discord.Embed(
                title=f"{emoji} {breakout_type.replace('_', ' ')}: {symbol}",
                description=f"{direction} breakout detected with {strength.lower()} confirmation",
                color=color,
                timestamp=datetime.now()
            )
            
            embed.add_field(
                name="📊 Breakout Details",
                value=(
                    f"**Level Broken:** ${level:.2f}\n"
                    f"**Current Price:** ${current_price:.2f}\n"
                    f"**Volume Confirmed:** {'✅' if volume_confirmed else '❌'}\n"
                    f"**Strength:** {strength}"
                ),
                inline=True
            )
            
            # Calculate targets and stops
            if breakout_type == "BREAKOUT_ABOVE":
                target1 = current_price * 1.02
                target2 = current_price * 1.05
                stop = level * 0.99
            else:
                target1 = current_price * 0.98
                target2 = current_price * 0.95
                stop = level * 1.01
            
            embed.add_field(
                name="🎯 Trade Levels",
                value=(
                    f"**Entry:** ${current_price:.2f}\n"
                    f"**Target 1:** ${target1:.2f}\n"
                    f"**Target 2:** ${target2:.2f}\n"
                    f"**Stop Loss:** ${stop:.2f}"
                ),
                inline=True
            )
            
            # Add recommendation
            recommendation = self.get_breakout_recommendation(breakout)
            embed.add_field(
                name="💡 Trading Recommendation",
                value=recommendation,
                inline=False
            )
            
            # Interactive buttons
            class BreakoutView(ui.View):
                def __init__(self, service, symbol, breakout_data):
                    super().__init__(timeout=300)
                    self.service = service
                    self.symbol = symbol
                    self.breakout_data = breakout_data
                
                @ui.button(label="🎯 View Trade Plan", style=discord.ButtonStyle.primary)
                async def trade_plan(self, interaction: discord.Interaction, button: ui.Button):
                    await self.service.send_breakout_trade_plan(interaction, self.symbol, self.breakout_data)
                
                @ui.button(label="📊 Technical Analysis", style=discord.ButtonStyle.secondary)
                async def technical(self, interaction: discord.Interaction, button: ui.Button):
                    await interaction.response.send_message(f"Running technical analysis for {self.symbol}...", ephemeral=True)
                
                @ui.button(label="⚡ Quick Entry", style=discord.ButtonStyle.success)
                async def quick_entry(self, interaction: discord.Interaction, button: ui.Button):
                    await self.service.handle_quick_entry(interaction, self.symbol, self.breakout_data)
            
            view = BreakoutView(self, symbol, breakout)
            await self.send_smart_alert(embed, view)
            
        except Exception as e:
            logger.error(f"Error sending breakout alert: {e}")
    
    def get_breakout_recommendation(self, breakout: Dict[str, Any]) -> str:
        """Get trading recommendation for breakout."""
        breakout_type = breakout['type']
        volume_confirmed = breakout['volume_confirmation']
        strength = breakout['strength']
        
        if breakout_type == "BREAKOUT_ABOVE":
            if volume_confirmed and strength == "STRONG":
                return "🚀 **STRONG BUY SIGNAL** - Volume-confirmed breakout. Consider aggressive entry."
            elif volume_confirmed:
                return "📈 **BUY SIGNAL** - Breakout with volume. Consider entry with tight stop."
            else:
                return "⚠️ **WEAK SIGNAL** - Breakout without volume confirmation. Wait for confirmation."
        else:
            if volume_confirmed and strength == "STRONG":
                return "🔴 **STRONG SELL SIGNAL** - Volume-confirmed breakdown. Consider exit or short."
            elif volume_confirmed:
                return "📉 **SELL SIGNAL** - Breakdown with volume. Consider reducing exposure."
            else:
                return "⚠️ **WEAK SIGNAL** - Breakdown without volume. Monitor for bounce."
    
    # ==================== OPTIONS GREEKS ALERTS ====================
    
    async def check_options_greeks_alerts(self):
        """Check options Greeks for alert conditions."""
        try:
            greeks_analysis = await self.greeks_monitor.monitor_all_options_greeks()
            
            for alert in greeks_analysis.get('alerts', []):
                if alert['type'] in ['HIGH_THETA_DECAY', 'THETA_ACCELERATION_CRITICAL', 'IV_CRUSH_RISK']:
                    await self.send_greeks_alert(alert)
                    
        except Exception as e:
            logger.error(f"Error checking Greeks alerts: {e}")
    
    async def send_greeks_alert(self, alert: Dict[str, Any]):
        """Send options Greeks alert."""
        try:
            alert_type = alert['type']
            symbol = alert['symbol']
            
            # Determine color and emoji based on alert type
            if 'THETA' in alert_type:
                color = discord.Color.orange()
                emoji = "💸"
            elif 'IV_CRUSH' in alert_type:
                color = discord.Color.purple()
                emoji = "💨"
            else:
                color = discord.Color.yellow()
                emoji = "⚠️"
            
            embed = discord.Embed(
                title=f"{emoji} {alert['message']}",
                description=alert['reasoning'],
                color=color,
                timestamp=datetime.now()
            )
            
            # Add specific Greeks data
            if 'daily_cost' in alert:
                embed.add_field(
                    name="💸 Theta Impact",
                    value=(
                        f"**Daily Decay:** ${alert['daily_cost']:.2f}\n"
                        f"**Percentage:** {alert.get('theta_pct', 0):.1f}% of position\n"
                        f"**DTE:** {alert.get('dte', 'N/A')} days"
                    ),
                    inline=True
                )
            
            # Interactive options
            class GreeksView(ui.View):
                def __init__(self, service, symbol, alert_data):
                    super().__init__(timeout=300)
                    self.service = service
                    self.symbol = symbol
                    self.alert_data = alert_data
                
                @ui.button(label="🔄 Roll Option", style=discord.ButtonStyle.primary)
                async def roll_option(self, interaction: discord.Interaction, button: ui.Button):
                    await interaction.response.send_message(f"Rolling option for {self.symbol}...", ephemeral=True)
                
                @ui.button(label="📉 Close Position", style=discord.ButtonStyle.danger)
                async def close_position(self, interaction: discord.Interaction, button: ui.Button):
                    await interaction.response.send_message(f"Closing option position for {self.symbol}...", ephemeral=True)
                
                @ui.button(label="📊 Greeks Analysis", style=discord.ButtonStyle.secondary)
                async def greeks_analysis(self, interaction: discord.Interaction, button: ui.Button):
                    await self.service.send_detailed_greeks_analysis(interaction, self.symbol)
            
            view = GreeksView(self, symbol, alert)
            await self.send_smart_alert(embed, view)
            
        except Exception as e:
            logger.error(f"Error sending Greeks alert: {e}")
    
    # ==================== NEWS ALERTS ====================
    
    async def check_news_alerts(self):
        """Check for significant news on positions."""
        try:
            news_analysis = await self.news_monitor.monitor_position_news()
            
            for alert in news_analysis.get('news_alerts', []):
                if alert.get('urgency') == 'HIGH':
                    await self.send_news_alert(alert)
                    
        except Exception as e:
            logger.error(f"Error checking news alerts: {e}")
    
    async def send_news_alert(self, alert: Dict[str, Any]):
        """Send news-based alert."""
        try:
            symbol = alert['symbol']
            sentiment = alert['sentiment']
            news_item = alert['news_item']
            
            # Prevent duplicate news alerts (same headline within 2 hours)
            if not hasattr(self, '_sent_news_alerts'):
                self._sent_news_alerts = {}
            
            headline = news_item.get('headline', '')
            alert_key = f"{symbol}_{headline[:50]}"  # Use first 50 chars of headline
            
            from datetime import datetime, timedelta
            now = datetime.now()
            
            # Check if we've sent this alert recently
            if alert_key in self._sent_news_alerts:
                last_sent = self._sent_news_alerts[alert_key]
                if now - last_sent < timedelta(hours=2):
                    logger.debug(f"Skipping duplicate news alert for {symbol}: {headline[:50]}...")
                    return
            
            # Record this alert
            self._sent_news_alerts[alert_key] = now
            
            # Clean up old entries (older than 24 hours)
            cutoff = now - timedelta(hours=24)
            self._sent_news_alerts = {
                k: v for k, v in self._sent_news_alerts.items() 
                if v > cutoff
            }
            
            # Color based on sentiment
            if 'POSITIVE' in sentiment:
                color = discord.Color.green()
                emoji = "📰"
            elif 'NEGATIVE' in sentiment:
                color = discord.Color.red()
                emoji = "⚠️"
            else:
                color = discord.Color.blue()
                emoji = "📰"
            
            embed = discord.Embed(
                title=f"{emoji} BREAKING NEWS: {symbol}",
                description=f"**Sentiment:** {sentiment}",
                color=color,
                timestamp=datetime.now()
            )
            
            embed.add_field(
                name="📰 Headline",
                value=news_item['headline'][:200] + "..." if len(news_item['headline']) > 200 else news_item['headline'],
                inline=False
            )
            
            if news_item.get('summary'):
                embed.add_field(
                    name="📄 Summary",
                    value=news_item['summary'][:300] + "..." if len(news_item['summary']) > 300 else news_item['summary'],
                    inline=False
                )
            
            # Interactive options
            class NewsView(ui.View):
                def __init__(self, service, symbol, news_data):
                    super().__init__(timeout=300)
                    self.service = service
                    self.symbol = symbol
                    self.news_data = news_data
                
                @ui.button(label="📊 Analyze Impact", style=discord.ButtonStyle.primary)
                async def analyze_impact(self, interaction: discord.Interaction, button: ui.Button):
                    await self.service.send_news_impact_analysis(interaction, self.symbol, self.news_data)
                
                @ui.button(label="💰 Position Action", style=discord.ButtonStyle.secondary)
                async def position_action(self, interaction: discord.Interaction, button: ui.Button):
                    await self.service.suggest_position_action(interaction, self.symbol, self.news_data)
                
                @ui.button(label="🔗 Read Full Article", style=discord.ButtonStyle.secondary)
                async def read_article(self, interaction: discord.Interaction, button: ui.Button):
                    url = self.news_data.get('url', '#')
                    await interaction.response.send_message(f"📰 Read full article: {url}", ephemeral=True)
            
            view = NewsView(self, symbol, alert)
            await self.send_smart_alert(embed, view)
            
        except Exception as e:
            logger.error(f"Error sending news alert: {e}")
    
    # ==================== HELPER METHODS ====================
    
    async def send_smart_alert(self, embed: discord.Embed, view: Optional[ui.View] = None):
        """Send smart alert to Discord channel."""
        try:
            channel = self.bot.get_channel(self.bot.notification_channel_id)
            if channel:
                if view:
                    message = await channel.send(embed=embed, view=view)
                else:
                    message = await channel.send(embed=embed)
                
                # Store in alert history
                self.alert_history.append({
                    "timestamp": datetime.now(),
                    "title": embed.title,
                    "description": embed.description,
                    "message_id": message.id
                })
                
                # Keep only last 100 alerts
                if len(self.alert_history) > 100:
                    self.alert_history = self.alert_history[-100:]
                    
        except Exception as e:
            logger.error(f"Error sending smart alert: {e}")
    
    async def send_detailed_volume_analysis(self, interaction: discord.Interaction, symbol: str):
        """Send detailed volume analysis."""
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Get extended volume data
            bars = await self.alpaca.get_bars(symbol, timeframe='1Min', limit=60)
            
            embed = discord.Embed(
                title=f"📊 Detailed Volume Analysis: {symbol}",
                color=discord.Color.blue()
            )
            
            # Calculate volume metrics
            volumes = [bar['volume'] for bar in bars]
            avg_volume = statistics.mean(volumes)
            max_volume = max(volumes)
            current_volume = volumes[-1]
            
            embed.add_field(
                name="Volume Statistics",
                value=(
                    f"**Current:** {current_volume:,}\n"
                    f"**Average:** {avg_volume:,.0f}\n"
                    f"**Maximum:** {max_volume:,}\n"
                    f"**Ratio:** {current_volume/avg_volume:.1f}x"
                ),
                inline=False
            )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            await interaction.followup.send(f"❌ Error: {str(e)}", ephemeral=True)
    
    async def send_news_impact_analysis(self, interaction: discord.Interaction, symbol: str, news_data: Dict[str, Any]):
        """Send detailed news impact analysis."""
        await interaction.response.defer(ephemeral=True)
        
        try:
            embed = discord.Embed(
                title=f"📊 News Impact Analysis: {symbol}",
                description=news_data.get('headline', 'No headline'),
                color=discord.Color.blue()
            )
            
            # Analyze sentiment impact
            sentiment = news_data.get('sentiment', 'neutral')
            impact_score = news_data.get('significance', 50)
            
            embed.add_field(
                name="Impact Assessment",
                value=(
                    f"**Sentiment:** {sentiment.upper()}\n"
                    f"**Significance:** {impact_score}/100\n"
                    f"**Expected Impact:** {'High' if impact_score > 70 else 'Medium' if impact_score > 40 else 'Low'}"
                ),
                inline=False
            )
            
            # Get current position if exists
            try:
                position = await self.alpaca.get_position(symbol)
                if position:
                    unrealized_pl = float(position.get('unrealized_pl', 0))
                    embed.add_field(
                        name="Your Position",
                        value=(
                            f"**Qty:** {position.get('qty')}\n"
                            f"**P/L:** ${unrealized_pl:,.2f}\n"
                            f"**Recommendation:** {'Consider taking profit' if unrealized_pl > 0 and sentiment == 'negative' else 'Hold and monitor'}"
                        ),
                        inline=False
                    )
            except:
                embed.add_field(name="Your Position", value="No position in this symbol", inline=False)
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            await interaction.followup.send(f"❌ Error analyzing news impact: {str(e)}", ephemeral=True)
    
    async def suggest_position_action(self, interaction: discord.Interaction, symbol: str, news_data: Dict[str, Any]):
        """Suggest position action based on news."""
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Get current position
            position = await self.alpaca.get_position(symbol)
            sentiment = news_data.get('sentiment', 'neutral')
            significance = news_data.get('significance', 50)
            
            if not position:
                suggestion = f"💡 **No position in {symbol}**\n\n"
                if sentiment == 'positive' and significance > 60:
                    suggestion += "✅ **Consider opening a position** - Positive news with high significance"
                else:
                    suggestion += "⏸️ **Wait and watch** - Monitor for better entry point"
            else:
                unrealized_pl = float(position.get('unrealized_pl', 0))
                suggestion = f"💡 **Position Action for {symbol}**\n\n"
                
                if sentiment == 'negative' and significance > 60:
                    if unrealized_pl > 0:
                        suggestion += "✅ **Take Profit** - Negative news, lock in gains"
                    else:
                        suggestion += "⚠️ **Set Stop Loss** - Protect against further downside"
                elif sentiment == 'positive' and significance > 60:
                    suggestion += "📈 **Hold or Add** - Positive catalyst, consider adding to position"
                else:
                    suggestion += "⏸️ **Hold** - News impact unclear, maintain current position"
            
            await interaction.followup.send(suggestion, ephemeral=True)
            
        except Exception as e:
            await interaction.followup.send(f"❌ Error: {str(e)}", ephemeral=True)
    
    async def quick_trade_setup(self, interaction: discord.Interaction, symbol: str, alert_data: Dict[str, Any]):
        """Quick trade setup from volume alert."""
        await interaction.response.defer(ephemeral=True)
        
        try:
            current_price = alert_data.get('current_price', 0)
            volume_ratio = alert_data.get('volume_ratio', 0)
            
            embed = discord.Embed(
                title=f"🎯 Quick Trade Setup: {symbol}",
                description=f"Volume spike detected ({volume_ratio:.1f}x normal)",
                color=discord.Color.green()
            )
            
            # Calculate suggested entry/exit
            stop_loss = current_price * 0.98  # 2% stop loss
            take_profit = current_price * 1.04  # 4% take profit
            
            embed.add_field(
                name="Trade Parameters",
                value=(
                    f"**Entry:** ${current_price:.2f}\n"
                    f"**Stop Loss:** ${stop_loss:.2f} (-2%)\n"
                    f"**Take Profit:** ${take_profit:.2f} (+4%)\n"
                    f"**Risk/Reward:** 1:2"
                ),
                inline=False
            )
            
            embed.add_field(
                name="Next Steps",
                value=(
                    "1. Use `/scan {symbol}` for detailed analysis\n"
                    "2. Check `/sentiment {symbol}` for market mood\n"
                    "3. Use NLP: `Set -2% stop loss on {symbol}`"
                ),
                inline=False
            )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            await interaction.followup.send(f"❌ Error: {str(e)}", ephemeral=True)
    
    async def mute_alerts(self, interaction: discord.Interaction, symbol: str, alert_type: str):
        """Mute alerts for a symbol/type."""
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Add to muted list (in-memory for now)
            if not hasattr(self, 'muted_alerts'):
                self.muted_alerts = {}
            
            if symbol not in self.muted_alerts:
                self.muted_alerts[symbol] = []
            
            if alert_type not in self.muted_alerts[symbol]:
                self.muted_alerts[symbol].append(alert_type)
            
            await interaction.followup.send(
                f"🔕 **Alerts muted for {symbol}**\n\n"
                f"Type: {alert_type}\n"
                f"Duration: Until market close\n\n"
                f"Use `/alerts unmute {symbol}` to re-enable",
                ephemeral=True
            )
            logger.info(f"Muted {alert_type} alerts for {symbol}")
            
        except Exception as e:
            await interaction.followup.send(f"❌ Error: {str(e)}", ephemeral=True)
    
    async def send_chart_analysis(self, interaction: discord.Interaction, symbol: str, breakout_data: Dict[str, Any]):
        """Send chart analysis for breakout."""
        await interaction.response.defer(ephemeral=True)
        
        try:
            embed = discord.Embed(
                title=f"📈 Chart Analysis: {symbol}",
                description="Breakout pattern detected",
                color=discord.Color.gold()
            )
            
            breakout_price = breakout_data.get('breakout_price', 0)
            resistance = breakout_data.get('resistance', 0)
            support = breakout_data.get('support', 0)
            
            embed.add_field(
                name="Key Levels",
                value=(
                    f"**Breakout Price:** ${breakout_price:.2f}\n"
                    f"**Resistance:** ${resistance:.2f}\n"
                    f"**Support:** ${support:.2f}\n"
                    f"**Pattern:** {breakout_data.get('pattern', 'Bullish breakout')}"
                ),
                inline=False
            )
            
            embed.add_field(
                name="Technical Indicators",
                value=(
                    f"**Trend:** {breakout_data.get('trend', 'Bullish')}\n"
                    f"**Strength:** {breakout_data.get('strength', 'Strong')}\n"
                    f"**Volume Confirmation:** {'Yes' if breakout_data.get('volume_confirmed') else 'No'}"
                ),
                inline=False
            )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            await interaction.followup.send(f"❌ Error: {str(e)}", ephemeral=True)
    
    async def setup_breakout_trade(self, interaction: discord.Interaction, symbol: str, breakout_data: Dict[str, Any]):
        """Setup trade for breakout."""
        await interaction.response.defer(ephemeral=True)
        
        try:
            breakout_price = breakout_data.get('breakout_price', 0)
            support = breakout_data.get('support', 0)
            
            # Calculate trade parameters
            entry = breakout_price
            stop_loss = support * 0.99  # Just below support
            take_profit = entry + (entry - stop_loss) * 2  # 2:1 R/R
            
            embed = discord.Embed(
                title=f"🎯 Breakout Trade Setup: {symbol}",
                color=discord.Color.green()
            )
            
            embed.add_field(
                name="Trade Plan",
                value=(
                    f"**Entry:** ${entry:.2f}\n"
                    f"**Stop Loss:** ${stop_loss:.2f}\n"
                    f"**Take Profit:** ${take_profit:.2f}\n"
                    f"**Risk/Reward:** 1:2"
                ),
                inline=False
            )
            
            embed.add_field(
                name="Execution",
                value=(
                    "Use NLP to execute:\n"
                    f"• `Buy {symbol} at market`\n"
                    f"• `Set stop loss at ${stop_loss:.2f}`\n"
                    f"• `Set take profit at ${take_profit:.2f}`"
                ),
                inline=False
            )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            await interaction.followup.send(f"❌ Error: {str(e)}", ephemeral=True)
    
    async def send_full_greeks_analysis(self, interaction: discord.Interaction, symbol: str, greeks_data: Dict[str, Any]):
        """Send full Greeks analysis."""
        await interaction.response.defer(ephemeral=True)
        
        try:
            embed = discord.Embed(
                title=f"📊 Full Greeks Analysis: {symbol}",
                color=discord.Color.purple()
            )
            
            embed.add_field(
                name="Greeks Summary",
                value=(
                    f"**Delta:** {greeks_data.get('delta', 0):.3f}\n"
                    f"**Gamma:** {greeks_data.get('gamma', 0):.3f}\n"
                    f"**Theta:** {greeks_data.get('theta', 0):.3f}\n"
                    f"**Vega:** {greeks_data.get('vega', 0):.3f}\n"
                    f"**IV:** {greeks_data.get('iv', 0):.1f}%"
                ),
                inline=False
            )
            
            embed.add_field(
                name="Risk Assessment",
                value=(
                    f"**Directional Risk:** {greeks_data.get('directional_risk', 'Medium')}\n"
                    f"**Time Decay:** {greeks_data.get('time_decay_risk', 'Medium')}\n"
                    f"**Volatility Risk:** {greeks_data.get('vol_risk', 'Medium')}"
                ),
                inline=False
            )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            await interaction.followup.send(f"❌ Error: {str(e)}", ephemeral=True)
    
    async def suggest_hedge_strategy(self, interaction: discord.Interaction, symbol: str, greeks_data: Dict[str, Any]):
        """Suggest hedging strategy based on Greeks."""
        await interaction.response.defer(ephemeral=True)
        
        try:
            delta = greeks_data.get('delta', 0)
            gamma = greeks_data.get('gamma', 0)
            
            suggestion = f"🛡️ **Hedge Strategy for {symbol}**\n\n"
            
            if abs(delta) > 0.7:
                suggestion += "**High Delta Exposure**\n"
                suggestion += f"• Consider delta hedging with {abs(delta)*100:.0f} shares\n"
                suggestion += "• Or use opposite direction options\n\n"
            
            if gamma > 0.05:
                suggestion += "**High Gamma Risk**\n"
                suggestion += "• Position sensitive to price moves\n"
                suggestion += "• Consider reducing position size\n\n"
            
            suggestion += "**Recommended Actions:**\n"
            suggestion += "1. Review position sizing\n"
            suggestion += "2. Set appropriate stop losses\n"
            suggestion += "3. Monitor Greeks daily"
            
            await interaction.followup.send(suggestion, ephemeral=True)
            
        except Exception as e:
            await interaction.followup.send(f"❌ Error: {str(e)}", ephemeral=True)
    
    def configure_alerts(self, settings: Dict[str, Any]):
        """Configure alert settings."""
        self.alert_settings.update(settings)
        logger.info(f"Alert settings updated: {settings}")
    
    def get_alert_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent alert history."""
        return self.alert_history[-limit:]


# Singleton instance
_discord_alerts_service = None

def get_discord_alerts_service(bot=None):
    """Get or create Discord alerts service."""
    global _discord_alerts_service
    if _discord_alerts_service is None and bot:
        _discord_alerts_service = DiscordAlertsService(bot)
    return _discord_alerts_service
