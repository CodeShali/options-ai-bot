"""
Helper functions for Discord bot formatting and embeds.
"""
import discord
from datetime import datetime
from typing import Dict, Any, List, Optional


def create_status_embed(status_data: Dict[str, Any]) -> discord.Embed:
    """Create a beautiful embed for system status."""
    embed = discord.Embed(
        title="🤖 Trading System Status",
        color=discord.Color.blue(),
        timestamp=datetime.now()
    )
    
    # System Status
    status_emoji = "🟢" if status_data.get('running') else "🔴"
    mode_emoji = "📄" if status_data.get('mode') == 'paper' else "💰"
    
    embed.add_field(
        name="📊 System",
        value=f"{status_emoji} **Status:** {status_data.get('status', 'Unknown')}\n"
              f"{mode_emoji} **Mode:** {status_data.get('mode', 'Unknown').upper()}\n"
              f"⏸️ **Paused:** {'Yes' if status_data.get('paused') else 'No'}",
        inline=True
    )
    
    # Account Info
    account = status_data.get('account', {})
    embed.add_field(
        name="💼 Account",
        value=f"💵 **Equity:** ${float(account.get('equity', 0)):,.2f}\n"
              f"💰 **Cash:** ${float(account.get('cash', 0)):,.2f}\n"
              f"⚡ **Buying Power:** ${float(account.get('buying_power', 0)):,.2f}",
        inline=True
    )
    
    # Positions
    positions = status_data.get('positions', {})
    embed.add_field(
        name="📈 Positions",
        value=f"📊 **Open:** {positions.get('count', 0)}\n"
              f"💹 **Total P/L:** ${positions.get('total_pl', 0):,.2f}\n"
              f"📉 **Today P/L:** ${positions.get('today_pl', 0):,.2f}",
        inline=True
    )
    
    # Performance
    perf = status_data.get('performance', {})
    embed.add_field(
        name="🎯 Performance",
        value=f"✅ **Win Rate:** {perf.get('win_rate', 0):.1f}%\n"
              f"📊 **Total Trades:** {perf.get('total_trades', 0)}\n"
              f"💰 **Total P/L:** ${perf.get('total_pl', 0):,.2f}",
        inline=True
    )
    
    # Circuit Breaker
    cb = status_data.get('circuit_breaker', {})
    cb_emoji = "🔴" if cb.get('active') else "🟢"
    embed.add_field(
        name="🛡️ Circuit Breaker",
        value=f"{cb_emoji} **Status:** {'ACTIVE' if cb.get('active') else 'Normal'}\n"
              f"📉 **Daily Loss:** ${abs(cb.get('daily_loss', 0)):,.2f}\n"
              f"⚠️ **Limit:** ${cb.get('limit', 1000):,.2f}",
        inline=True
    )
    
    # Last Activity
    embed.add_field(
        name="⏰ Activity",
        value=f"🔍 **Last Scan:** {status_data.get('last_scan', 'Never')}\n"
              f"📈 **Last Trade:** {status_data.get('last_trade', 'Never')}\n"
              f"⏱️ **Uptime:** {status_data.get('uptime', 'Unknown')}",
        inline=True
    )
    
    embed.set_footer(text="Trading System v2.0 | Real-time data")
    return embed


def create_position_embed(position: Dict[str, Any]) -> discord.Embed:
    """Create a beautiful embed for a position."""
    symbol = position.get('symbol', 'Unknown')
    pl = position.get('unrealized_pl', 0)
    pl_pct = position.get('unrealized_plpc', 0) * 100
    
    # Color based on P/L
    if pl > 0:
        color = discord.Color.green()
        emoji = "📈"
    elif pl < 0:
        color = discord.Color.red()
        emoji = "📉"
    else:
        color = discord.Color.light_grey()
        emoji = "➖"
    
    embed = discord.Embed(
        title=f"{emoji} {symbol}",
        color=color,
        timestamp=datetime.now()
    )
    
    # Position Details
    embed.add_field(
        name="📊 Position",
        value=f"🔢 **Quantity:** {position.get('qty', 0)}\n"
              f"💵 **Entry:** ${position.get('avg_entry_price', 0):.2f}\n"
              f"💰 **Current:** ${position.get('current_price', 0):.2f}",
        inline=True
    )
    
    # P/L
    pl_emoji = "🟢" if pl > 0 else "🔴" if pl < 0 else "⚪"
    embed.add_field(
        name="💹 Profit/Loss",
        value=f"{pl_emoji} **P/L:** ${pl:,.2f}\n"
              f"📊 **P/L %:** {pl_pct:+.2f}%\n"
              f"💎 **Value:** ${position.get('market_value', 0):,.2f}",
        inline=True
    )
    
    # Targets
    embed.add_field(
        name="🎯 Targets",
        value=f"🎯 **Profit:** ${position.get('profit_target', 0):.2f}\n"
              f"🛑 **Stop:** ${position.get('stop_loss', 0):.2f}\n"
              f"📏 **Distance:** {position.get('distance_to_target', 0):.1f}%",
        inline=True
    )
    
    # Options specific
    if position.get('asset_class') == 'option':
        embed.add_field(
            name="📋 Option Details",
            value=f"🎲 **Type:** {position.get('option_type', 'N/A').upper()}\n"
                  f"💵 **Strike:** ${position.get('strike', 0):.2f}\n"
                  f"📅 **DTE:** {position.get('dte', 0)} days",
            inline=True
        )
        
        # Greeks
        greeks = position.get('greeks', {})
        if greeks:
            embed.add_field(
                name="🎯 Greeks",
                value=f"Δ **Delta:** {greeks.get('delta', 0):.3f}\n"
                      f"Θ **Theta:** {greeks.get('theta', 0):.3f}\n"
                      f"V **Vega:** {greeks.get('vega', 0):.3f}",
                inline=True
            )
    
    embed.set_footer(text=f"Position ID: {position.get('id', 'N/A')}")
    return embed


def create_trade_embed(trade: Dict[str, Any]) -> discord.Embed:
    """Create a beautiful embed for a trade."""
    side = trade.get('side', 'buy')
    symbol = trade.get('symbol', 'Unknown')
    
    # Color and emoji based on side
    if side == 'buy':
        color = discord.Color.green()
        emoji = "🟢"
        title = f"{emoji} BUY {symbol}"
    else:
        color = discord.Color.red()
        emoji = "🔴"
        title = f"{emoji} SELL {symbol}"
    
    embed = discord.Embed(
        title=title,
        color=color,
        timestamp=datetime.fromisoformat(trade.get('timestamp', datetime.now().isoformat()))
    )
    
    # Trade Details
    embed.add_field(
        name="📊 Trade",
        value=f"🔢 **Quantity:** {trade.get('qty', 0)}\n"
              f"💵 **Price:** ${trade.get('price', 0):.2f}\n"
              f"💰 **Value:** ${trade.get('value', 0):,.2f}",
        inline=True
    )
    
    # Analysis
    embed.add_field(
        name="🤖 AI Analysis",
        value=f"📊 **Confidence:** {trade.get('confidence', 0):.0f}%\n"
              f"⚠️ **Risk:** {trade.get('risk_level', 'N/A')}\n"
              f"💭 **Sentiment:** {trade.get('sentiment', 'N/A')}",
        inline=True
    )
    
    # P/L (for exits)
    if side == 'sell' and trade.get('pl') is not None:
        pl = trade.get('pl', 0)
        pl_emoji = "🟢" if pl > 0 else "🔴" if pl < 0 else "⚪"
        embed.add_field(
            name="💹 Result",
            value=f"{pl_emoji} **P/L:** ${pl:,.2f}\n"
                  f"📊 **P/L %:** {trade.get('pl_pct', 0):+.2f}%\n"
                  f"⏱️ **Hold Time:** {trade.get('hold_time', 'N/A')}",
            inline=True
        )
    
    # Reasoning
    if trade.get('reasoning'):
        embed.add_field(
            name="💭 Reasoning",
            value=trade.get('reasoning', 'N/A')[:1024],
            inline=False
        )
    
    embed.set_footer(text=f"Trade ID: {trade.get('id', 'N/A')}")
    return embed


def create_sentiment_embed(sentiment: Dict[str, Any]) -> discord.Embed:
    """Create a beautiful embed for sentiment analysis."""
    symbol = sentiment.get('symbol', 'Unknown')
    overall = sentiment.get('overall_sentiment', 'NEUTRAL')
    score = sentiment.get('overall_score', 0)
    
    # Color based on sentiment
    if overall == 'POSITIVE':
        color = discord.Color.green()
        emoji = "🟢"
    elif overall == 'NEGATIVE':
        color = discord.Color.red()
        emoji = "🔴"
    else:
        color = discord.Color.light_grey()
        emoji = "⚪"
    
    embed = discord.Embed(
        title=f"{emoji} Sentiment Analysis: {symbol}",
        description=f"**Overall: {overall}** (Score: {score:.2f})",
        color=color,
        timestamp=datetime.now()
    )
    
    # News Sentiment
    news = sentiment.get('news_sentiment', {})
    news_emoji = "🟢" if news.get('sentiment') == 'POSITIVE' else "🔴" if news.get('sentiment') == 'NEGATIVE' else "⚪"
    embed.add_field(
        name="📰 News Sentiment",
        value=f"{news_emoji} **Sentiment:** {news.get('sentiment', 'N/A')}\n"
              f"📊 **Score:** {news.get('score', 0):.2f}\n"
              f"💥 **Impact:** {news.get('impact', 'N/A')}\n"
              f"📡 **Source:** {news.get('data_source', 'N/A')}",
        inline=True
    )
    
    # Market Sentiment
    market = sentiment.get('market_sentiment', {})
    market_emoji = "🟢" if market.get('sentiment') == 'POSITIVE' else "🔴" if market.get('sentiment') == 'NEGATIVE' else "⚪"
    embed.add_field(
        name="📈 Market Sentiment",
        value=f"{market_emoji} **Sentiment:** {market.get('sentiment', 'N/A')}\n"
              f"📊 **Score:** {market.get('score', 0):.2f}\n"
              f"📡 **Source:** {market.get('data_source', 'N/A')}",
        inline=True
    )
    
    # Social Sentiment
    social = sentiment.get('social_sentiment', {})
    social_emoji = "🟢" if social.get('sentiment') == 'POSITIVE' else "🔴" if social.get('sentiment') == 'NEGATIVE' else "⚪"
    embed.add_field(
        name="💬 Social Sentiment",
        value=f"{social_emoji} **Sentiment:** {social.get('sentiment', 'N/A')}\n"
              f"📊 **Score:** {social.get('score', 0):.2f}\n"
              f"👥 **Mentions:** {social.get('mentions', 0)}\n"
              f"📡 **Source:** {social.get('data_source', 'N/A')}",
        inline=True
    )
    
    # Headlines
    headlines = news.get('headlines', [])
    if headlines:
        headlines_text = "\n".join([f"• {h[:80]}..." for h in headlines[:3]])
        embed.add_field(
            name="📰 Recent Headlines",
            value=headlines_text,
            inline=False
        )
    
    # AI Interpretation
    if sentiment.get('interpretation'):
        embed.add_field(
            name="🤖 AI Interpretation",
            value=sentiment.get('interpretation')[:1024],
            inline=False
        )
    
    embed.set_footer(text="Sentiment Analysis | Real-time data")
    return embed


def create_error_embed(error_message: str) -> discord.Embed:
    """Create an error embed."""
    embed = discord.Embed(
        title="❌ Error",
        description=error_message,
        color=discord.Color.red(),
        timestamp=datetime.now()
    )
    return embed


def create_success_embed(message: str) -> discord.Embed:
    """Create a success embed."""
    embed = discord.Embed(
        title="✅ Success",
        description=message,
        color=discord.Color.green(),
        timestamp=datetime.now()
    )
    return embed


def create_warning_embed(message: str) -> discord.Embed:
    """Create a warning embed."""
    embed = discord.Embed(
        title="⚠️ Warning",
        description=message,
        color=discord.Color.orange(),
        timestamp=datetime.now()
    )
    return embed


def create_info_embed(title: str, description: str) -> discord.Embed:
    """Create an info embed."""
    embed = discord.Embed(
        title=f"ℹ️ {title}",
        description=description,
        color=discord.Color.blue(),
        timestamp=datetime.now()
    )
    return embed


def format_positions_list(positions: List[Dict[str, Any]]) -> discord.Embed:
    """Format a list of positions into an embed."""
    embed = discord.Embed(
        title="📊 Open Positions",
        color=discord.Color.blue(),
        timestamp=datetime.now()
    )
    
    if not positions:
        embed.description = "No open positions"
        return embed
    
    total_value = sum(float(p.get('market_value', 0)) for p in positions)
    total_pl = sum(float(p.get('unrealized_pl', 0)) for p in positions)
    
    embed.description = f"**Total Value:** ${total_value:,.2f} | **Total P/L:** ${total_pl:+,.2f}"
    
    for pos in positions[:10]:  # Limit to 10 positions
        symbol = pos.get('symbol', 'Unknown')
        pl = float(pos.get('unrealized_pl', 0))
        pl_pct = float(pos.get('unrealized_plpc', 0)) * 100
        pl_emoji = "🟢" if pl > 0 else "🔴" if pl < 0 else "⚪"
        
        value = (
            f"{pl_emoji} **P/L:** ${pl:+,.2f} ({pl_pct:+.2f}%)\n"
            f"💵 **Entry:** ${pos.get('avg_entry_price', 0):.2f} | "
            f"**Current:** ${pos.get('current_price', 0):.2f}\n"
            f"🔢 **Qty:** {pos.get('qty', 0)} | "
            f"💎 **Value:** ${pos.get('market_value', 0):,.2f}"
        )
        
        embed.add_field(
            name=f"📈 {symbol}",
            value=value,
            inline=False
        )
    
    if len(positions) > 10:
        embed.set_footer(text=f"Showing 10 of {len(positions)} positions")
    
    return embed


def format_trades_list(trades: List[Dict[str, Any]]) -> discord.Embed:
    """Format a list of trades into an embed."""
    embed = discord.Embed(
        title="📜 Recent Trades",
        color=discord.Color.blue(),
        timestamp=datetime.now()
    )
    
    if not trades:
        embed.description = "No recent trades"
        return embed
    
    for trade in trades[:10]:  # Limit to 10 trades
        symbol = trade.get('symbol', 'Unknown')
        side = trade.get('side', 'buy')
        side_emoji = "🟢" if side == 'buy' else "🔴"
        
        value = (
            f"{side_emoji} **{side.upper()}** | "
            f"💵 ${trade.get('price', 0):.2f} × {trade.get('qty', 0)}\n"
            f"⏰ {trade.get('timestamp', 'Unknown')}"
        )
        
        if trade.get('pl') is not None:
            pl = float(trade.get('pl', 0))
            pl_emoji = "🟢" if pl > 0 else "🔴" if pl < 0 else "⚪"
            value += f"\n{pl_emoji} **P/L:** ${pl:+,.2f}"
        
        embed.add_field(
            name=f"{symbol}",
            value=value,
            inline=False
        )
    
    if len(trades) > 10:
        embed.set_footer(text=f"Showing 10 of {len(trades)} trades")
    
    return embed
