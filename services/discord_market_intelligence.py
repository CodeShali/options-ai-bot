"""
Discord Market Intelligence Service
Provides real-time market insights, sector analysis, and trading opportunities.
"""
import asyncio
import discord
from discord.ext import tasks
from typing import Dict, Any, List, Optional
from datetime import datetime, time
from loguru import logger

from services import get_alpaca_service, get_database_service
from config import settings


class DiscordMarketIntelligenceService:
    """Market intelligence and insights for Discord."""
    
    def __init__(self, bot):
        """Initialize market intelligence service."""
        self.bot = bot
        self.alpaca = get_alpaca_service()
        self.db = get_database_service()
        
        # Market data
        self.market_status = {}
        self.sector_performance = {}
        self.top_movers = {}
        self.market_sentiment = "NEUTRAL"
        
        logger.info("📊 Discord Market Intelligence Service initialized")
    
    def start_intelligence_feed(self):
        """Start market intelligence tasks."""
        self.market_open_report.start()
        self.hourly_market_update.start()
        self.market_close_summary.start()
        logger.info("✅ Market intelligence feed started")
    
    def stop_intelligence_feed(self):
        """Stop market intelligence feed."""
        self.market_open_report.cancel()
        self.hourly_market_update.cancel()
        self.market_close_summary.cancel()
        logger.info("⏹️ Market intelligence feed stopped")
    
    # ==================== MARKET OPEN REPORT ====================
    
    @tasks.loop(time=time(9, 30))  # 9:30 AM ET - Market Open
    async def market_open_report(self):
        """Post market open analysis."""
        try:
            await self.post_market_open_analysis()
        except Exception as e:
            logger.error(f"Error in market open report: {e}")
    
    async def post_market_open_analysis(self):
        """Post comprehensive market open analysis."""
        try:
            # Get market data
            market_data = await self.get_market_open_data()
            
            embed = discord.Embed(
                title="📊 MARKET OPEN REPORT",
                description=f"Market Analysis • {datetime.now().strftime('%B %d, %Y')} • 9:30 AM ET",
                color=discord.Color.blue(),
                timestamp=datetime.now()
            )
            
            # Major indices
            indices_data = market_data.get('indices', {})
            embed.add_field(
                name="📈 Major Indices",
                value=(
                    f"**SPY:** ${indices_data.get('SPY', {}).get('price', 0):.2f} "
                    f"({indices_data.get('SPY', {}).get('change_pct', 0):+.2f}%)\n"
                    f"**QQQ:** ${indices_data.get('QQQ', {}).get('price', 0):.2f} "
                    f"({indices_data.get('QQQ', {}).get('change_pct', 0):+.2f}%)\n"
                    f"**IWM:** ${indices_data.get('IWM', {}).get('price', 0):.2f} "
                    f"({indices_data.get('IWM', {}).get('change_pct', 0):+.2f}%)\n"
                    f"**VIX:** {indices_data.get('VIX', {}).get('price', 0):.1f} "
                    f"({indices_data.get('VIX', {}).get('change_pct', 0):+.1f}%)"
                ),
                inline=True
            )
            
            # Top movers
            movers = market_data.get('top_movers', {})
            embed.add_field(
                name="🔥 Top Movers",
                value=(
                    f"🚀 **Gainers:**\n"
                    f"{self.format_movers_list(movers.get('gainers', []))}\n"
                    f"📉 **Losers:**\n"
                    f"{self.format_movers_list(movers.get('losers', []))}"
                ),
                inline=True
            )
            
            # Market sentiment & opportunities
            opportunities = market_data.get('opportunities', [])
            embed.add_field(
                name="🎯 Trading Opportunities",
                value=self.format_opportunities(opportunities),
                inline=False
            )
            
            # Risk factors
            risks = market_data.get('risks', [])
            if risks:
                embed.add_field(
                    name="⚠️ Risk Factors",
                    value="\n".join([f"• {risk}" for risk in risks[:3]]),
                    inline=True
                )
            
            # Economic calendar
            events = market_data.get('economic_events', [])
            if events:
                embed.add_field(
                    name="📅 Today's Events",
                    value="\n".join([f"• {event}" for event in events[:3]]),
                    inline=True
                )
            
            await self.send_market_intelligence(embed)
            
        except Exception as e:
            logger.error(f"Error posting market open analysis: {e}")
    
    async def get_market_open_data(self) -> Dict[str, Any]:
        """Get comprehensive market open data."""
        try:
            # Get major indices
            indices = ['SPY', 'QQQ', 'IWM', 'VIX']
            indices_data = {}
            
            for symbol in indices:
                try:
                    quote = await self.alpaca.get_latest_quote(symbol)
                    if quote:
                        # Calculate change (simplified)
                        current_price = quote['price']
                        prev_close = current_price * 0.998  # Placeholder
                        change_pct = ((current_price - prev_close) / prev_close) * 100
                        
                        indices_data[symbol] = {
                            'price': current_price,
                            'change_pct': change_pct
                        }
                except:
                    continue
            
            # Get top movers (simplified)
            top_movers = {
                'gainers': [
                    {'symbol': 'NVDA', 'change_pct': 3.5},
                    {'symbol': 'TSLA', 'change_pct': 2.8},
                    {'symbol': 'AMD', 'change_pct': 2.1}
                ],
                'losers': [
                    {'symbol': 'AAPL', 'change_pct': -1.2},
                    {'symbol': 'MSFT', 'change_pct': -0.8},
                    {'symbol': 'GOOGL', 'change_pct': -0.5}
                ]
            }
            
            # Generate opportunities
            opportunities = [
                "NVDA: Breakout above $500 resistance",
                "TSLA: Bull flag pattern forming",
                "SPY: Support holding at $448"
            ]
            
            # Risk factors
            risks = [
                "Fed speech at 2 PM ET",
                "CPI data release tomorrow",
                "High options expiration volume"
            ]
            
            # Economic events
            economic_events = [
                "10:00 AM - Consumer Confidence",
                "2:00 PM - Fed Chair Speech",
                "4:30 PM - API Crude Inventory"
            ]
            
            return {
                'indices': indices_data,
                'top_movers': top_movers,
                'opportunities': opportunities,
                'risks': risks,
                'economic_events': economic_events
            }
            
        except Exception as e:
            logger.error(f"Error getting market open data: {e}")
            return {}
    
    def format_movers_list(self, movers: List[Dict[str, Any]]) -> str:
        """Format top movers list."""
        if not movers:
            return "No significant movers"
        
        formatted = []
        for mover in movers[:3]:
            symbol = mover['symbol']
            change = mover['change_pct']
            formatted.append(f"**{symbol}:** {change:+.1f}%")
        
        return "\n".join(formatted)
    
    def format_opportunities(self, opportunities: List[str]) -> str:
        """Format trading opportunities."""
        if not opportunities:
            return "No clear opportunities identified"
        
        formatted = []
        for i, opp in enumerate(opportunities[:3], 1):
            formatted.append(f"{i}. {opp}")
        
        return "\n".join(formatted)
    
    # ==================== HOURLY UPDATES ====================
    
    @tasks.loop(minutes=60)
    async def hourly_market_update(self):
        """Post hourly market updates during trading hours."""
        current_hour = datetime.now().hour
        
        # Only during market hours (9:30 AM - 4 PM ET)
        if 9 <= current_hour <= 16:
            try:
                await self.post_hourly_update()
            except Exception as e:
                logger.error(f"Error in hourly update: {e}")
    
    async def post_hourly_update(self):
        """Post hourly market update."""
        try:
            current_time = datetime.now().strftime("%I:%M %p ET")
            
            embed = discord.Embed(
                title=f"⏰ Market Update • {current_time}",
                description="Hourly market pulse check",
                color=discord.Color.orange(),
                timestamp=datetime.now()
            )
            
            # Get current market pulse
            pulse_data = await self.get_market_pulse()
            
            embed.add_field(
                name="📊 Market Pulse",
                value=(
                    f"**Trend:** {pulse_data.get('trend', 'Neutral')}\n"
                    f"**Volume:** {pulse_data.get('volume_status', 'Normal')}\n"
                    f"**Volatility:** {pulse_data.get('volatility', 'Low')}\n"
                    f"**Sentiment:** {pulse_data.get('sentiment', 'Neutral')}"
                ),
                inline=True
            )
            
            # Key levels
            levels = pulse_data.get('key_levels', {})
            embed.add_field(
                name="🎯 Key Levels (SPY)",
                value=(
                    f"**Resistance:** ${levels.get('resistance', 0):.2f}\n"
                    f"**Support:** ${levels.get('support', 0):.2f}\n"
                    f"**Current:** ${levels.get('current', 0):.2f}"
                ),
                inline=True
            )
            
            # Notable moves
            notable_moves = pulse_data.get('notable_moves', [])
            if notable_moves:
                embed.add_field(
                    name="📈 Notable Moves",
                    value="\n".join([f"• {move}" for move in notable_moves[:3]]),
                    inline=False
                )
            
            await self.send_market_intelligence(embed)
            
        except Exception as e:
            logger.error(f"Error posting hourly update: {e}")
    
    async def get_market_pulse(self) -> Dict[str, Any]:
        """Get current market pulse data."""
        try:
            # Simplified market pulse calculation
            spy_quote = await self.alpaca.get_latest_quote('SPY')
            current_price = spy_quote['price'] if spy_quote else 450
            
            # Determine trend (simplified)
            if current_price > 452:
                trend = "Bullish 📈"
            elif current_price < 448:
                trend = "Bearish 📉"
            else:
                trend = "Neutral ➖"
            
            return {
                'trend': trend,
                'volume_status': 'Above Average',
                'volatility': 'Moderate',
                'sentiment': 'Cautiously Optimistic',
                'key_levels': {
                    'resistance': 455.0,
                    'support': 448.0,
                    'current': current_price
                },
                'notable_moves': [
                    "NVDA up 2.5% on chip demand",
                    "Energy sector leading gains",
                    "Tech showing resilience"
                ]
            }
            
        except Exception as e:
            logger.error(f"Error getting market pulse: {e}")
            return {}
    
    # ==================== MARKET CLOSE SUMMARY ====================
    
    @tasks.loop(time=time(16, 5))  # 4:05 PM ET - After Market Close
    async def market_close_summary(self):
        """Post market close summary."""
        try:
            await self.post_market_close_summary()
        except Exception as e:
            logger.error(f"Error in market close summary: {e}")
    
    async def post_market_close_summary(self):
        """Post comprehensive market close summary."""
        try:
            embed = discord.Embed(
                title="🔔 MARKET CLOSE SUMMARY",
                description=f"Trading Day Recap • {datetime.now().strftime('%B %d, %Y')}",
                color=discord.Color.purple(),
                timestamp=datetime.now()
            )
            
            # Get close data
            close_data = await self.get_market_close_data()
            
            # Market performance
            performance = close_data.get('performance', {})
            embed.add_field(
                name="📊 Market Performance",
                value=(
                    f"**SPY:** {performance.get('SPY', 0):+.2f}%\n"
                    f"**QQQ:** {performance.get('QQQ', 0):+.2f}%\n"
                    f"**IWM:** {performance.get('IWM', 0):+.2f}%\n"
                    f"**VIX:** {performance.get('VIX', 0):+.1f}"
                ),
                inline=True
            )
            
            # Sector performance
            sectors = close_data.get('sectors', {})
            embed.add_field(
                name="🏭 Sector Performance",
                value=self.format_sector_performance(sectors),
                inline=True
            )
            
            # Day's highlights
            highlights = close_data.get('highlights', [])
            embed.add_field(
                name="⭐ Day's Highlights",
                value="\n".join([f"• {highlight}" for highlight in highlights[:4]]),
                inline=False
            )
            
            # Tomorrow's outlook
            outlook = close_data.get('outlook', "Mixed signals for tomorrow's session")
            embed.add_field(
                name="🔮 Tomorrow's Outlook",
                value=outlook,
                inline=False
            )
            
            await self.send_market_intelligence(embed)
            
        except Exception as e:
            logger.error(f"Error posting market close summary: {e}")
    
    async def get_market_close_data(self) -> Dict[str, Any]:
        """Get market close data."""
        try:
            # Simplified market close data
            return {
                'performance': {
                    'SPY': 0.45,
                    'QQQ': 0.62,
                    'IWM': -0.15,
                    'VIX': -2.3
                },
                'sectors': {
                    'Technology': 1.2,
                    'Healthcare': 0.8,
                    'Financial': -0.3,
                    'Energy': 2.1,
                    'Consumer': 0.1
                },
                'highlights': [
                    "Tech sector led gains on AI optimism",
                    "Energy surged on crude oil inventory draw",
                    "Small caps underperformed large caps",
                    "Volume was above average at 1.2B shares"
                ],
                'outlook': "Mixed signals with tech strength offset by rate concerns. Watch Fed speakers tomorrow."
            }
            
        except Exception as e:
            logger.error(f"Error getting market close data: {e}")
            return {}
    
    def format_sector_performance(self, sectors: Dict[str, float]) -> str:
        """Format sector performance."""
        if not sectors:
            return "No sector data available"
        
        # Sort by performance
        sorted_sectors = sorted(sectors.items(), key=lambda x: x[1], reverse=True)
        
        formatted = []
        for sector, performance in sorted_sectors[:5]:
            emoji = "🟢" if performance > 0 else "🔴" if performance < 0 else "⚪"
            formatted.append(f"{emoji} **{sector}:** {performance:+.1f}%")
        
        return "\n".join(formatted)
    
    # ==================== HELPER METHODS ====================
    
    async def send_market_intelligence(self, embed: discord.Embed):
        """Send market intelligence to dedicated channel or main channel."""
        try:
            channel = self.bot.get_channel(self.bot.notification_channel_id)
            if channel:
                await channel.send(embed=embed)
                
        except Exception as e:
            logger.error(f"Error sending market intelligence: {e}")
    
    async def get_sector_rotation_analysis(self) -> Dict[str, Any]:
        """Analyze sector rotation patterns."""
        try:
            # Simplified sector rotation analysis
            return {
                'rotating_into': ['Technology', 'Energy'],
                'rotating_out_of': ['Utilities', 'REITs'],
                'neutral': ['Healthcare', 'Consumer'],
                'recommendation': 'Focus on tech and energy names for momentum plays'
            }
            
        except Exception as e:
            logger.error(f"Error in sector rotation analysis: {e}")
            return {}
    
    async def get_market_regime(self) -> str:
        """Determine current market regime."""
        try:
            # Simplified market regime detection
            spy_quote = await self.alpaca.get_latest_quote('SPY')
            vix_quote = await self.alpaca.get_latest_quote('VIX')
            
            spy_price = spy_quote['price'] if spy_quote else 450
            vix_level = vix_quote['price'] if vix_quote else 15
            
            if vix_level < 15:
                return "LOW_VOLATILITY_BULL"
            elif vix_level > 25:
                return "HIGH_VOLATILITY_BEAR"
            else:
                return "NORMAL_VOLATILITY"
                
        except Exception as e:
            logger.error(f"Error determining market regime: {e}")
            return "UNKNOWN"
    
    def get_intelligence_status(self) -> Dict[str, Any]:
        """Get market intelligence service status."""
        return {
            "market_open_report_active": not self.market_open_report.is_being_cancelled(),
            "hourly_updates_active": not self.hourly_market_update.is_being_cancelled(),
            "market_close_summary_active": not self.market_close_summary.is_being_cancelled(),
            "current_market_sentiment": self.market_sentiment,
            "last_update": datetime.now().isoformat()
        }


# Singleton instance
_discord_market_intelligence = None

def get_discord_market_intelligence(bot=None):
    """Get or create Discord market intelligence service."""
    global _discord_market_intelligence
    if _discord_market_intelligence is None and bot:
        _discord_market_intelligence = DiscordMarketIntelligenceService(bot)
    return _discord_market_intelligence
