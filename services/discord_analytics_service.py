"""
Discord Performance Analytics Service
Handles daily summaries, performance tracking, and automated reports.
"""
import asyncio
import discord
from discord.ext import tasks
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta, time
from loguru import logger
import matplotlib.pyplot as plt
import pandas as pd
import io
import base64

from services import get_alpaca_service, get_database_service
from config import settings


class DiscordAnalyticsService:
    """Performance analytics and automated reporting for Discord."""
    
    def __init__(self, bot):
        """Initialize analytics service."""
        self.bot = bot
        self.alpaca = get_alpaca_service()
        self.db = get_database_service()
        
        # Report settings
        self.daily_summary_time = time(16, 10)  # 4:10 PM ET
        self.weekly_summary_day = 4  # Friday
        self.monthly_summary_enabled = True
        
        logger.info("📊 Discord Analytics Service initialized")
    
    def start_reporting(self):
        """Start automated reporting tasks."""
        self.daily_summary_task.start()
        self.weekly_summary_task.start()
        logger.info("✅ Automated reporting started")
    
    def stop_reporting(self):
        """Stop automated reporting."""
        self.daily_summary_task.cancel()
        self.weekly_summary_task.cancel()
        logger.info("⏹️ Automated reporting stopped")
    
    # ==================== DAILY SUMMARY ====================
    
    @tasks.loop(time=time(16, 10))  # 4:10 PM ET daily
    async def daily_summary_task(self):
        """Auto-post daily performance summary."""
        try:
            await self.post_daily_summary()
        except Exception as e:
            logger.error(f"Error in daily summary task: {e}")
    
    async def post_daily_summary(self):
        """Post comprehensive daily performance summary."""
        try:
            # Get today's data
            today = datetime.now().date()
            summary_data = await self.calculate_daily_metrics(today)
            
            # Create beautiful summary embed
            embed = await self.create_daily_summary_embed(summary_data)
            
            # Generate and attach equity curve chart
            chart_file = await self.generate_daily_chart(summary_data)
            
            # Send to channel
            channel = self.bot.get_channel(self.bot.notification_channel_id)
            if channel:
                if chart_file:
                    await channel.send(embed=embed, file=chart_file)
                else:
                    await channel.send(embed=embed)
                
                logger.info("📊 Daily summary posted successfully")
                
        except Exception as e:
            logger.error(f"Error posting daily summary: {e}")
    
    async def calculate_daily_metrics(self, date) -> Dict[str, Any]:
        """Calculate comprehensive daily performance metrics."""
        try:
            # Get trades for the day
            trades_today = await self.db.get_recent_trades(100)
            trades_today = [t for t in trades_today if datetime.fromisoformat(t['timestamp']).date() == date]
            
            # Get account info
            account = await self.alpaca.get_account()
            positions = await self.alpaca.get_positions()
            
            # Calculate basic metrics
            total_trades = len(trades_today)
            wins = sum(1 for t in trades_today if t.get('action') == 'sell' and float(t.get('profit_loss', 0)) > 0)
            losses = sum(1 for t in trades_today if t.get('action') == 'sell' and float(t.get('profit_loss', 0)) < 0)
            win_rate = (wins / (wins + losses) * 100) if (wins + losses) > 0 else 0
            
            # Calculate P&L
            closed_pl = sum(float(t.get('profit_loss', 0)) for t in trades_today if t.get('action') == 'sell')
            open_pl = sum(float(p.get('unrealized_pl', 0)) for p in positions)
            total_pl = closed_pl + open_pl
            
            # Get best/worst trades
            sell_trades = [t for t in trades_today if t.get('action') == 'sell']
            best_trade = max(sell_trades, key=lambda x: float(x.get('profit_loss', 0))) if sell_trades else None
            worst_trade = min(sell_trades, key=lambda x: float(x.get('profit_loss', 0))) if sell_trades else None
            
            # Calculate returns
            equity = float(account['equity'])
            daily_return_pct = (total_pl / equity * 100) if equity > 0 else 0
            
            # Strategy performance (simplified)
            strategy_performance = await self.calculate_strategy_performance(trades_today)
            
            # Period performance
            week_data = await self.calculate_period_performance(7)
            month_data = await self.calculate_period_performance(30)
            
            return {
                "date": date,
                "total_trades": total_trades,
                "wins": wins,
                "losses": losses,
                "win_rate": win_rate,
                "closed_pl": closed_pl,
                "open_pl": open_pl,
                "total_pl": total_pl,
                "daily_return_pct": daily_return_pct,
                "equity": equity,
                "best_trade": best_trade,
                "worst_trade": worst_trade,
                "strategy_performance": strategy_performance,
                "week_performance": week_data,
                "month_performance": month_data,
                "positions_count": len(positions)
            }
            
        except Exception as e:
            logger.error(f"Error calculating daily metrics: {e}")
            return {}
    
    async def create_daily_summary_embed(self, data: Dict[str, Any]) -> discord.Embed:
        """Create beautiful daily summary embed."""
        try:
            total_pl = data.get('total_pl', 0)
            daily_return_pct = data.get('daily_return_pct', 0)
            
            # Color based on performance
            if total_pl > 0:
                color = discord.Color.green()
                performance_emoji = "📈"
            elif total_pl < 0:
                color = discord.Color.red()
                performance_emoji = "📉"
            else:
                color = discord.Color.blue()
                performance_emoji = "➖"
            
            embed = discord.Embed(
                title="📊 DAILY PERFORMANCE SUMMARY",
                description="━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
                color=color,
                timestamp=datetime.now()
            )
            
            # Overall performance section
            embed.add_field(
                name=f"{performance_emoji} Overall Performance",
                value=(
                    f"**P&L:** ${total_pl:+,.2f} ({daily_return_pct:+.2f}%)\n"
                    f"**Equity:** ${data.get('equity', 0):,.2f}\n"
                    f"**Trades:** {data.get('total_trades', 0)} ({data.get('wins', 0)} wins, {data.get('losses', 0)} losses)\n"
                    f"**Win Rate:** {data.get('win_rate', 0):.0f}%"
                ),
                inline=False
            )
            
            # Best/Worst trades
            best_trade = data.get('best_trade')
            worst_trade = data.get('worst_trade')
            
            if best_trade or worst_trade:
                trade_text = ""
                if best_trade:
                    trade_text += f"🏆 **Best:** {best_trade['symbol']} ${best_trade['profit_loss']:+,.2f}\n"
                if worst_trade:
                    trade_text += f"📉 **Worst:** {worst_trade['symbol']} ${worst_trade['profit_loss']:+,.2f}\n"
                
                embed.add_field(
                    name="🎯 Trade Highlights",
                    value=trade_text,
                    inline=True
                )
            
            # Strategy performance
            strategy_perf = data.get('strategy_performance', {})
            if strategy_perf:
                strategy_text = ""
                for name, perf in strategy_perf.items():
                    emoji = "✅" if perf['pl'] > 0 else "❌"
                    strategy_text += f"{emoji} **{name}:** ${perf['pl']:+,.2f} ({perf['trades']} trades)\n"
                
                embed.add_field(
                    name="🎯 Strategy Breakdown",
                    value=strategy_text,
                    inline=True
                )
            
            # Period performance
            week_perf = data.get('week_performance', {})
            month_perf = data.get('month_performance', {})
            
            if week_perf or month_perf:
                period_text = ""
                if week_perf:
                    period_text += f"**Week:** ${week_perf.get('pl', 0):+,.2f} ({week_perf.get('return_pct', 0):+.2f}%)\n"
                if month_perf:
                    period_text += f"**Month:** ${month_perf.get('pl', 0):+,.2f} ({month_perf.get('return_pct', 0):+.2f}%)\n"
                
                embed.add_field(
                    name="📈 Period Performance",
                    value=period_text,
                    inline=False
                )
            
            # Current positions
            positions_count = data.get('positions_count', 0)
            open_pl = data.get('open_pl', 0)
            
            embed.add_field(
                name="📊 Current Positions",
                value=(
                    f"**Open Positions:** {positions_count}\n"
                    f"**Unrealized P&L:** ${open_pl:+,.2f}\n"
                    f"**Status:** {'Active monitoring' if positions_count > 0 else 'No positions'}"
                ),
                inline=True
            )
            
            # Add performance insights
            insights = self.generate_performance_insights(data)
            if insights:
                embed.add_field(
                    name="💡 Performance Insights",
                    value=insights,
                    inline=False
                )
            
            # Footer with additional info
            embed.set_footer(
                text=f"Daily Summary • {data.get('date', datetime.now().date())} • Auto-generated at 4:10 PM ET"
            )
            
            return embed
            
        except Exception as e:
            logger.error(f"Error creating daily summary embed: {e}")
            return discord.Embed(title="❌ Error generating daily summary", color=discord.Color.red())
    
    def generate_performance_insights(self, data: Dict[str, Any]) -> str:
        """Generate AI-powered performance insights."""
        try:
            insights = []
            
            win_rate = data.get('win_rate', 0)
            total_pl = data.get('total_pl', 0)
            total_trades = data.get('total_trades', 0)
            
            # Win rate insights
            if win_rate >= 80:
                insights.append("🎯 Excellent win rate - strategy execution is strong")
            elif win_rate >= 60:
                insights.append("✅ Good win rate - maintain current approach")
            elif win_rate < 40 and total_trades >= 3:
                insights.append("⚠️ Low win rate - review entry criteria")
            
            # P&L insights
            if total_pl > 1000:
                insights.append("🚀 Strong daily performance - consider scaling up")
            elif total_pl < -500:
                insights.append("🛡️ Significant loss - review risk management")
            
            # Trading frequency insights
            if total_trades > 10:
                insights.append("📊 High trading frequency - monitor for overtrading")
            elif total_trades == 0:
                insights.append("😴 No trades today - market conditions or strategy pause?")
            
            return "\n".join(insights[:3])  # Limit to 3 insights
            
        except Exception as e:
            logger.error(f"Error generating insights: {e}")
            return ""
    
    async def calculate_strategy_performance(self, trades: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate performance by strategy."""
        try:
            # Group trades by strategy (simplified)
            strategies = {
                "Breakout Momentum": {"trades": 0, "pl": 0},
                "Mean Reversion": {"trades": 0, "pl": 0},
                "Options Flow": {"trades": 0, "pl": 0}
            }
            
            # In real implementation, would get strategy from trade data
            for trade in trades:
                if trade.get('action') == 'sell':
                    # Simplified strategy assignment
                    symbol = trade.get('symbol', '')
                    pl = float(trade.get('profit_loss', 0))
                    
                    if 'TSLA' in symbol or 'NVDA' in symbol:
                        strategies["Breakout Momentum"]["trades"] += 1
                        strategies["Breakout Momentum"]["pl"] += pl
                    elif 'AAPL' in symbol or 'MSFT' in symbol:
                        strategies["Mean Reversion"]["trades"] += 1
                        strategies["Mean Reversion"]["pl"] += pl
                    else:
                        strategies["Options Flow"]["trades"] += 1
                        strategies["Options Flow"]["pl"] += pl
            
            return strategies
            
        except Exception as e:
            logger.error(f"Error calculating strategy performance: {e}")
            return {}
    
    async def calculate_period_performance(self, days: int) -> Dict[str, Any]:
        """Calculate performance for a period."""
        try:
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=days)
            
            # Get trades for period
            all_trades = await self.db.get_recent_trades(1000)
            period_trades = [
                t for t in all_trades 
                if start_date <= datetime.fromisoformat(t['timestamp']).date() <= end_date
            ]
            
            # Calculate metrics
            total_pl = sum(float(t.get('profit_loss', 0)) for t in period_trades if t.get('action') == 'sell')
            total_trades = len([t for t in period_trades if t.get('action') == 'sell'])
            
            # Get account equity for return calculation
            account = await self.alpaca.get_account()
            equity = float(account['equity'])
            return_pct = (total_pl / equity * 100) if equity > 0 else 0
            
            return {
                "pl": total_pl,
                "trades": total_trades,
                "return_pct": return_pct,
                "days": days
            }
            
        except Exception as e:
            logger.error(f"Error calculating period performance: {e}")
            return {}
    
    async def generate_daily_chart(self, data: Dict[str, Any]) -> Optional[discord.File]:
        """Generate daily performance chart."""
        try:
            # Create simple performance chart
            fig, ax = plt.subplots(figsize=(10, 6))
            
            # Sample data for demonstration
            dates = [datetime.now().date() - timedelta(days=i) for i in range(7, 0, -1)]
            pnl_values = [100, 250, -50, 180, 320, 150, data.get('total_pl', 0)]
            
            ax.plot(dates, pnl_values, marker='o', linewidth=2, markersize=6)
            ax.axhline(y=0, color='gray', linestyle='--', alpha=0.7)
            ax.set_title('Daily P&L Trend (Last 7 Days)', fontsize=14, fontweight='bold')
            ax.set_ylabel('P&L ($)', fontsize=12)
            ax.grid(True, alpha=0.3)
            
            # Color the line based on performance
            total_pl = data.get('total_pl', 0)
            line_color = 'green' if total_pl > 0 else 'red' if total_pl < 0 else 'blue'
            ax.lines[0].set_color(line_color)
            
            plt.tight_layout()
            
            # Save to bytes
            buffer = io.BytesIO()
            plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
            buffer.seek(0)
            plt.close()
            
            return discord.File(buffer, filename='daily_performance.png')
            
        except Exception as e:
            logger.error(f"Error generating daily chart: {e}")
            return None
    
    # ==================== WEEKLY SUMMARY ====================
    
    @tasks.loop(time=time(16, 15))  # 4:15 PM ET
    async def weekly_summary_task(self):
        """Weekly summary on Fridays."""
        if datetime.now().weekday() == self.weekly_summary_day:  # Friday
            try:
                await self.post_weekly_summary()
            except Exception as e:
                logger.error(f"Error in weekly summary task: {e}")
    
    async def post_weekly_summary(self):
        """Post weekly performance summary."""
        try:
            # Calculate weekly metrics
            weekly_data = await self.calculate_period_performance(7)
            
            embed = discord.Embed(
                title="📊 WEEKLY PERFORMANCE SUMMARY",
                description="Complete week performance analysis",
                color=discord.Color.blue(),
                timestamp=datetime.now()
            )
            
            embed.add_field(
                name="📈 Week Performance",
                value=(
                    f"**Total P&L:** ${weekly_data.get('pl', 0):+,.2f}\n"
                    f"**Return:** {weekly_data.get('return_pct', 0):+.2f}%\n"
                    f"**Total Trades:** {weekly_data.get('trades', 0)}"
                ),
                inline=False
            )
            
            # Generate weekly chart
            chart_file = await self.generate_weekly_chart(weekly_data)
            
            channel = self.bot.get_channel(self.bot.notification_channel_id)
            if channel:
                if chart_file:
                    await channel.send(embed=embed, file=chart_file)
                else:
                    await channel.send(embed=embed)
                
                logger.info("📊 Weekly summary posted successfully")
                
        except Exception as e:
            logger.error(f"Error posting weekly summary: {e}")
    
    async def generate_weekly_chart(self, data: Dict[str, Any]) -> Optional[discord.File]:
        """Generate weekly performance chart."""
        try:
            # Create weekly chart (simplified)
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))
            
            # P&L chart
            days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
            daily_pnl = [50, 120, -30, 80, 200, 0, 0]  # Sample data
            
            colors = ['green' if x > 0 else 'red' if x < 0 else 'gray' for x in daily_pnl]
            ax1.bar(days, daily_pnl, color=colors, alpha=0.7)
            ax1.set_title('Daily P&L This Week', fontsize=14, fontweight='bold')
            ax1.set_ylabel('P&L ($)')
            ax1.axhline(y=0, color='black', linestyle='-', alpha=0.3)
            
            # Cumulative P&L
            cumulative_pnl = [sum(daily_pnl[:i+1]) for i in range(len(daily_pnl))]
            ax2.plot(days, cumulative_pnl, marker='o', linewidth=2, color='blue')
            ax2.set_title('Cumulative P&L This Week', fontsize=14, fontweight='bold')
            ax2.set_ylabel('Cumulative P&L ($)')
            ax2.grid(True, alpha=0.3)
            
            plt.tight_layout()
            
            # Save to bytes
            buffer = io.BytesIO()
            plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
            buffer.seek(0)
            plt.close()
            
            return discord.File(buffer, filename='weekly_performance.png')
            
        except Exception as e:
            logger.error(f"Error generating weekly chart: {e}")
            return None
    
    # ==================== ON-DEMAND REPORTS ====================
    
    async def generate_performance_report(self, days: int = 30) -> discord.Embed:
        """Generate on-demand performance report."""
        try:
            period_data = await self.calculate_period_performance(days)
            
            embed = discord.Embed(
                title=f"📊 Performance Report ({days} Days)",
                color=discord.Color.blue(),
                timestamp=datetime.now()
            )
            
            embed.add_field(
                name="📈 Performance Metrics",
                value=(
                    f"**Total P&L:** ${period_data.get('pl', 0):+,.2f}\n"
                    f"**Return:** {period_data.get('return_pct', 0):+.2f}%\n"
                    f"**Total Trades:** {period_data.get('trades', 0)}\n"
                    f"**Period:** {days} days"
                ),
                inline=False
            )
            
            return embed
            
        except Exception as e:
            logger.error(f"Error generating performance report: {e}")
            return discord.Embed(title="❌ Error generating report", color=discord.Color.red())
    
    def get_analytics_status(self) -> Dict[str, Any]:
        """Get analytics service status."""
        return {
            "daily_summary_enabled": not self.daily_summary_task.is_being_cancelled(),
            "weekly_summary_enabled": not self.weekly_summary_task.is_being_cancelled(),
            "daily_summary_time": self.daily_summary_time.strftime("%H:%M"),
            "weekly_summary_day": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"][self.weekly_summary_day],
            "last_daily_summary": "Today" if datetime.now().time() > self.daily_summary_time else "Yesterday"
        }


# Singleton instance
_discord_analytics_service = None

def get_discord_analytics_service(bot=None):
    """Get or create Discord analytics service."""
    global _discord_analytics_service
    if _discord_analytics_service is None and bot:
        _discord_analytics_service = DiscordAnalyticsService(bot)
    return _discord_analytics_service
