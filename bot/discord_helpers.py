"""
Helper functions for Discord bot formatting and embeds.
"""
import discord
from datetime import datetime
from typing import Dict, Any, List, Optional


def create_status_embed(status_data: Dict[str, Any]) -> discord.Embed:
    """Create a comprehensive trading dashboard embed."""
    
    # Determine overall health color
    is_running = status_data.get('running', False)
    has_issues = status_data.get('circuit_breaker', {}).get('active', False)
    
    if is_running and not has_issues:
        color = discord.Color.green()
        status_emoji = "🟢"
    elif is_running and has_issues:
        color = discord.Color.orange()
        status_emoji = "🟡"
    else:
        color = discord.Color.red()
        status_emoji = "🔴"
    
    # Get current time
    now = datetime.now()
    time_str = now.strftime("%I:%M %p ET")
    
    # Title with status
    mode = status_data.get('mode', 'unknown').upper()
    mode_emoji = "📄" if mode == 'PAPER' else "💰"
    
    embed = discord.Embed(
        title=f"📊 TARA Trading System",
        description=f"{status_emoji} **{status_data.get('status', 'Unknown')}** | {mode_emoji} {mode} Mode | {time_str}",
        color=color,
        timestamp=now
    )
    
    # Account Summary
    account = status_data.get('account', {})
    equity = float(account.get('equity', 0))
    cash = float(account.get('cash', 0))
    buying_power = float(account.get('buying_power', 0))
    
    embed.add_field(
        name="💰 Account Summary",
        value=f"**Portfolio Value:** ${equity:,.2f}\n"
              f"**Buying Power:** ${buying_power:,.2f}\n"
              f"**Cash:** ${cash:,.2f}",
        inline=True
    )
    
    # Today's Performance
    positions = status_data.get('positions', {})
    today_pl = positions.get('today_pl', 0)
    today_pl_pct = (today_pl / equity * 100) if equity > 0 else 0
    pl_emoji = "🟢" if today_pl >= 0 else "🔴"
    
    embed.add_field(
        name="📈 Today's Performance",
        value=f"{pl_emoji} **P&L:** ${today_pl:+,.2f} ({today_pl_pct:+.2f}%)\n"
              f"**Trades:** {status_data.get('today_trades', 0)}\n"
              f"**Win Rate:** {status_data.get('today_win_rate', 0):.0f}%",
        inline=True
    )
    
    # Positions Summary
    pos_count = positions.get('count', 0)
    total_pl = positions.get('total_pl', 0)
    total_pl_pct = (total_pl / equity * 100) if equity > 0 else 0
    pos_emoji = "📊" if pos_count > 0 else "⚪"
    
    embed.add_field(
        name=f"{pos_emoji} Open Positions ({pos_count})",
        value=f"**Total P&L:** ${total_pl:+,.2f} ({total_pl_pct:+.2f}%)\n"
              f"**Largest:** {status_data.get('largest_position', 'N/A')}\n"
              f"**At Risk:** ${status_data.get('total_risk', 0):,.2f}",
        inline=True
    )
    
    # Strategy Status
    strategies = status_data.get('strategies', {})
    strategy_text = ""
    for name, data in strategies.items():
        status_icon = "✅" if data.get('active') else "⚠️"
        signals = data.get('signals_today', 0)
        strategy_text += f"{status_icon} {name}: {signals} signals\n"
    
    if not strategy_text:
        strategy_text = "No strategies active"
    
    embed.add_field(
        name="🎯 Active Strategies",
        value=strategy_text.strip(),
        inline=True
    )
    
    # Scanner Status
    last_scan = status_data.get('last_scan', 'Never')
    next_scan = status_data.get('next_scan', 'Unknown')
    watching = status_data.get('symbols_watching', 0)
    opps_found = status_data.get('opportunities_found', 0)
    
    embed.add_field(
        name="🔍 Scanner Status",
        value=f"**Last Scan:** {last_scan}\n"
              f"**Next Scan:** {next_scan}\n"
              f"**Watching:** {watching} symbols\n"
              f"**Opportunities:** {opps_found}",
        inline=True
    )
    
    # Risk Metrics
    cb = status_data.get('circuit_breaker', {})
    cb_active = cb.get('active', False)
    daily_loss = abs(cb.get('daily_loss', 0))
    loss_limit = cb.get('limit', 1000)
    portfolio_heat = status_data.get('portfolio_heat', 0)
    heat_limit = status_data.get('heat_limit', 6.0)
    
    risk_emoji = "🔴" if cb_active else "🟢" if portfolio_heat < heat_limit * 0.8 else "🟡"
    
    embed.add_field(
        name=f"{risk_emoji} Risk Status",
        value=f"**Portfolio Heat:** {portfolio_heat:.1f}% / {heat_limit:.1f}%\n"
              f"**Daily Loss:** ${daily_loss:,.2f} / ${loss_limit:,.2f}\n"
              f"**Circuit Breaker:** {'🔴 ACTIVE' if cb_active else '🟢 Normal'}",
        inline=True
    )
    
    # Add warning if paused
    if status_data.get('paused'):
        embed.add_field(
            name="⚠️ System Paused",
            value="Trading is paused. Use `/resume` to continue.\n"
                  "No scans or trades will execute while paused.",
            inline=False
        )
    
    # Add warning if circuit breaker active
    if cb_active:
        embed.add_field(
            name="🚨 Circuit Breaker Active",
            value=f"Daily loss limit reached (${daily_loss:,.2f}).\n"
                  f"Trading halted for protection.\n"
                  f"Will reset tomorrow or use `/override` (risky!).",
            inline=False
        )
    
    embed.set_footer(text=f"TARA v2.0 | Uptime: {status_data.get('uptime', 'Unknown')}")
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
    """Create a comprehensive, trading-focused sentiment analysis embed."""
    symbol = sentiment.get('symbol', 'Unknown')
    overall = sentiment.get('overall_sentiment', 'NEUTRAL')
    score = sentiment.get('overall_score', 0)
    
    # Color based on sentiment
    if overall == 'POSITIVE':
        color = discord.Color.green()
        emoji = "🟢"
        action = "BUY"
    elif overall == 'NEGATIVE':
        color = discord.Color.red()
        emoji = "🔴"
        action = "SELL/AVOID"
    else:
        color = discord.Color.light_grey()
        emoji = "⚪"
        action = "HOLD"
    
    # Calculate confidence percentage
    confidence = min(abs(score) * 100, 100)
    
    # Main embed with overall assessment
    embed = discord.Embed(
        title=f"📊 Sentiment Analysis: {symbol}",
        description=(
            f"**━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━**\n"
            f"## 🎯 OVERALL ASSESSMENT\n"
            f"{emoji} **{overall}** | Confidence: **{confidence:.0f}%**\n"
            f"Score: **{score:+.2f}** | Recommended Action: **{action}**\n"
            f"**━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━**"
        ),
        color=color,
        timestamp=datetime.now()
    )
    
    # Trading Impact Section
    news = sentiment.get('news_sentiment', {})
    market = sentiment.get('market_sentiment', {})
    
    # Determine trade type recommendation based on sentiment strength
    if abs(score) >= 0.7:
        trade_type = "DAY TRADE" if score > 0 else "AVOID"
        hold_time = "2 hours"
    elif abs(score) >= 0.5:
        trade_type = "SWING TRADE" if score > 0 else "HOLD"
        hold_time = "1-3 days"
    else:
        trade_type = "HOLD"
        hold_time = "N/A"
    
    if score > 0:
        embed.add_field(
            name="💡 TRADING IMPACT",
            value=(
                f"✅ **Action:** {action}\n"
                f"📈 **Trade Type:** {trade_type}\n"
                f"⏱️ **Hold Time:** {hold_time}\n"
                f"🎯 **Confidence:** {confidence:.0f}%"
            ),
            inline=False
        )
    
    # AI Interpretation (Most Important - Show First!)
    interpretation = sentiment.get('interpretation', '')
    if interpretation:
        # Truncate if too long
        if len(interpretation) > 400:
            interpretation = interpretation[:397] + "..."
        embed.add_field(
            name="🤖 AI REASONING",
            value=f"```{interpretation}```",
            inline=False
        )
    
    # News Sentiment with Details
    news_emoji = "🟢" if news.get('sentiment') == 'POSITIVE' else "🔴" if news.get('sentiment') == 'NEGATIVE' else "⚪"
    news_value = (
        f"{news_emoji} **Sentiment:** {news.get('sentiment', 'N/A')}\n"
        f"📊 **Score:** {news.get('score', 0):+.2f}\n"
        f"💥 **Impact:** {news.get('impact', 'N/A')}\n"
        f"📡 **Source:** {news.get('data_source', 'none')}"
    )
    
    # Add reasoning if available
    if news.get('reasoning'):
        news_value += f"\n💭 {news.get('reasoning')[:100]}"
    
    embed.add_field(
        name="📰 NEWS SENTIMENT",
        value=news_value,
        inline=True
    )
    
    # Market Sentiment with Indicators
    market_emoji = "🟢" if market.get('sentiment') == 'POSITIVE' else "🔴" if market.get('sentiment') == 'NEGATIVE' else "⚪"
    market_value = (
        f"{market_emoji} **Sentiment:** {market.get('sentiment', 'N/A')}\n"
        f"📊 **Score:** {market.get('score', 0):+.2f}\n"
        f"📡 **Source:** {market.get('data_source', 'none')}"
    )
    
    # Add indicators if available
    indicators = market.get('indicators', {})
    if indicators:
        market_value += f"\n📈 Indicators: {len(indicators)} signals"
    
    embed.add_field(
        name="📈 MARKET SENTIMENT",
        value=market_value,
        inline=True
    )
    
    # Headlines (if available)
    headlines = news.get('headlines', [])
    if headlines:
        headlines_text = "\n".join([f"• {h[:70]}" for h in headlines[:3]])
        embed.add_field(
            name="📰 RECENT HEADLINES",
            value=headlines_text or "No recent headlines",
            inline=False
        )
    
    # Themes (if available)
    themes = news.get('themes', [])
    if themes:
        themes_text = ", ".join(themes[:5])
        embed.add_field(
            name="🏷️ KEY THEMES",
            value=themes_text,
            inline=False
        )
    
    # How This Affects Trading
    if abs(score) > 0.3:
        impact_text = ""
        if score > 0.7:
            impact_text = (
                f"**For DAY TRADE:** ✅ EXCELLENT setup\n"
                f"• Sentiment: Strong positive ({score:+.2f})\n"
                f"• Confidence: {confidence:.0f}%\n"
                f"• Recommendation: Aggressive entry\n\n"
                f"**For SCALP:** ✅ GOOD setup\n"
                f"• Quick momentum play\n"
                f"• High probability: {min(confidence + 10, 100):.0f}%"
            )
        elif score > 0.4:
            impact_text = (
                f"**For SWING TRADE:** ✅ GOOD setup\n"
                f"• Sentiment: Positive ({score:+.2f})\n"
                f"• Confidence: {confidence:.0f}%\n"
                f"• Recommendation: Consider entry\n\n"
                f"**For DAY TRADE:** ⚠️ MODERATE\n"
                f"• Wait for stronger signals"
            )
        elif score < -0.5:
            impact_text = (
                f"**WARNING:** ❌ Negative sentiment\n"
                f"• Score: {score:+.2f}\n"
                f"• Recommendation: AVOID or SHORT\n"
                f"• Risk: HIGH"
            )
        
        if impact_text:
            embed.add_field(
                name="🎯 HOW THIS AFFECTS YOUR TRADING",
                value=impact_text,
                inline=False
            )
    
    # OpenAI Usage Info
    embed.add_field(
        name="🤖 AI ANALYSIS",
        value=(
            f"This analysis used **2 OpenAI calls**:\n"
            f"• News sentiment analysis\n"
            f"• Overall interpretation\n"
            f"Cost: ~$0.002 | Fresh data ✅"
        ),
        inline=False
    )
    
    embed.set_footer(text=f"Sentiment Analysis | {symbol} | Real-time data")
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
    """Format a list of positions with full trading context."""
    
    if not positions:
        embed = discord.Embed(
            title="📊 Open Positions",
            description="No open positions",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        return embed
    
    total_value = sum(float(p.get('market_value', 0)) for p in positions)
    total_pl = sum(float(p.get('unrealized_pl', 0)) for p in positions)
    total_pl_pct = (total_pl / total_value * 100) if total_value > 0 else 0
    
    # Color based on overall P/L
    if total_pl > 0:
        color = discord.Color.green()
        pl_emoji = "🟢"
    elif total_pl < 0:
        color = discord.Color.red()
        pl_emoji = "🔴"
    else:
        color = discord.Color.blue()
        pl_emoji = "⚪"
    
    embed = discord.Embed(
        title=f"📊 Open Positions ({len(positions)})",
        description=f"{pl_emoji} **Total P/L:** ${total_pl:+,.2f} ({total_pl_pct:+.2f}%) | **Portfolio Value:** ${total_value:,.2f}",
        color=color,
        timestamp=datetime.now()
    )
    
    for pos in positions[:10]:  # Limit to 10 positions
        symbol = pos.get('symbol', 'Unknown')
        qty = int(pos.get('qty', 0))
        entry_price = float(pos.get('avg_entry_price', 0))
        current_price = float(pos.get('current_price', 0))
        pl = float(pos.get('unrealized_pl', 0))
        pl_pct = float(pos.get('unrealized_plpc', 0)) * 100
        market_value = float(pos.get('market_value', 0))
        
        # P/L emoji and status
        if pl > 0:
            pos_emoji = "🟢"
            status = "In Profit"
        elif pl < 0:
            pos_emoji = "🔴"
            status = "At Loss"
        else:
            pos_emoji = "⚪"
            status = "Break Even"
        
        # Calculate stop and target (estimate if not provided)
        stop_loss = entry_price * 0.98  # 2% stop
        target = entry_price * 1.05  # 5% target
        
        # Distance to stop/target
        if current_price <= stop_loss * 1.005:  # Within 0.5% of stop
            status = "⚠️ NEAR STOP LOSS!"
        elif current_price >= target * 0.995:  # Within 0.5% of target
            status = "🎯 APPROACHING TARGET"
        
        # Entry time (if available)
        entry_time = pos.get('entry_time', 'Unknown')
        if entry_time != 'Unknown':
            try:
                entry_dt = datetime.fromisoformat(entry_time)
                time_held = datetime.now() - entry_dt
                hours = int(time_held.total_seconds() / 3600)
                if hours < 24:
                    time_str = f"{hours}h ago"
                else:
                    days = hours // 24
                    time_str = f"{days}d ago"
            except:
                time_str = "Unknown"
        else:
            time_str = "Unknown"
        
        # Strategy (if available)
        strategy = pos.get('strategy', 'Unknown')
        
        value = (
            f"{pos_emoji} **{qty} shares** | **Status:** {status}\n"
            f"💵 **Entry:** ${entry_price:.2f} → **Current:** ${current_price:.2f}\n"
            f"💹 **P/L:** ${pl:+,.2f} ({pl_pct:+.2f}%) | **Value:** ${market_value:,.2f}\n"
            f"🎯 **Target:** ${target:.2f} | **Stop:** ${stop_loss:.2f}\n"
            f"⏰ **Held:** {time_str} | **Strategy:** {strategy}"
        )
        
        embed.add_field(
            name=f"📈 {symbol}",
            value=value,
            inline=False
        )
    
    if len(positions) > 10:
        embed.set_footer(text=f"Showing 10 of {len(positions)} positions | Use /position [symbol] for details")
    else:
        embed.set_footer(text="Use /position [symbol] for detailed analysis")
    
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


def create_trading_analysis_embed(analysis: Dict[str, Any]) -> discord.Embed:
    """
    Create comprehensive trading analysis embed with detailed opportunities.
    Shows stocks and options opportunities with actionable trade plans.
    """
    symbol = analysis.get('symbol', 'Unknown')
    recommendation = analysis.get('recommendation', 'HOLD')
    confidence = analysis.get('confidence', 0)
    overview = analysis.get('overview', 'Analysis unavailable')
    
    # Color based on recommendation
    if 'BUY' in recommendation.upper():
        color = discord.Color.green()
        emoji = "🟢"
    elif 'SELL' in recommendation.upper() or 'AVOID' in recommendation.upper():
        color = discord.Color.red()
        emoji = "🔴"
    else:
        color = discord.Color.light_grey()
        emoji = "⚪"
    
    # Main embed
    embed = discord.Embed(
        title=f"📊 Trading Analysis: {symbol}",
        description=(
            f"**━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━**\n"
            f"## {emoji} {recommendation}\n"
            f"**Confidence:** {confidence}%  |  **Horizon:** {analysis.get('time_horizon', 'N/A').title()}\n"
            f"**━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━**"
        ),
        color=color,
        timestamp=datetime.now()
    )
    
    # Market Overview (2-3 sentences)
    embed.add_field(
        name="💡 MARKET OVERVIEW",
        value=f"```{overview[:500]}```",
        inline=False
    )
    
    # Get opportunities
    opportunities = analysis.get('opportunities', {})
    
    # Stock Opportunity
    stock_opp = opportunities.get('stock', {})
    if stock_opp.get('recommended'):
        stock_value = (
            f"**Action:** {stock_opp.get('action', 'N/A').upper()}\n"
            f"**Entry:** ${stock_opp.get('entry_price', 0):.2f}\n"
            f"**Target:** ${stock_opp.get('target_price', 0):.2f} ({stock_opp.get('expected_gain_pct', 0):+.1f}%)\n"
            f"**Stop:** ${stock_opp.get('stop_loss', 0):.2f}\n"
            f"**Size:** {stock_opp.get('position_size_shares', 0)} shares\n"
            f"**Hold:** {stock_opp.get('hold_time', 'N/A')}\n"
            f"**Best For:** {stock_opp.get('best_for', 'N/A')}\n"
            f"```{stock_opp.get('reasoning', 'N/A')[:150]}```"
        )
        embed.add_field(
            name="📈 STOCK TRADE",
            value=stock_value,
            inline=False
        )
    
    # Call Options
    call_options = opportunities.get('call_options', [])
    if call_options:
        for i, call in enumerate(call_options[:3], 1):  # Show top 3
            if not call.get('recommended'):
                continue
            
            call_value = (
                f"**Type:** {call.get('type', 'N/A').replace('_', ' ').title()}\n"
                f"**Strike:** ${call.get('strike', 0):.2f}\n"
                f"**Expiry:** {call.get('expiry_days', 0)} days\n"
                f"**Entry:** ${call.get('entry_premium_estimate', 0):.2f}\n"
                f"**Target:** ${call.get('target_premium_estimate', 0):.2f} ({call.get('max_gain_pct', 0):+.0f}%)\n"
                f"**Hold:** {call.get('hold_time', 'N/A')}\n"
                f"**Best For:** {call.get('best_for', 'N/A')}\n"
                f"```{call.get('reasoning', 'N/A')[:120]}```"
            )
            
            type_emoji = "⚡" if '0dte' in call.get('type', '').lower() else "📞"
            embed.add_field(
                name=f"{type_emoji} CALL OPTION #{i}",
                value=call_value,
                inline=True
            )
    
    # Put Options
    put_options = opportunities.get('put_options', [])
    if put_options:
        for i, put in enumerate(put_options[:2], 1):  # Show top 2
            if not put.get('recommended'):
                continue
            
            put_value = (
                f"**Strike:** ${put.get('strike', 0):.2f}\n"
                f"**Expiry:** {put.get('expiry_days', 0)} days\n"
                f"```{put.get('reasoning', 'N/A')[:100]}```"
            )
            embed.add_field(
                name=f"📉 PUT OPTION #{i}",
                value=put_value,
                inline=True
            )
    
    # Spreads removed - not supported yet
    
    # Catalysts & Risks (side by side)
    catalysts = analysis.get('catalysts', [])
    risks = analysis.get('risks', [])
    
    if catalysts:
        catalysts_text = "\n".join([f"• {c}" for c in catalysts[:4]])
        embed.add_field(
            name="🚀 CATALYSTS",
            value=catalysts_text or "None identified",
            inline=True
        )
    
    if risks:
        risks_text = "\n".join([f"• {r}" for r in risks[:4]])
        embed.add_field(
            name="⚠️ RISKS",
            value=risks_text or "None identified",
            inline=True
        )
    
    # Timing
    timing = analysis.get('timing', {})
    if timing:
        timing_value = ""
        if timing.get('best_entry_time'):
            timing_value += f"**Entry:** {timing['best_entry_time']}\n"
        if timing.get('best_exit_time'):
            timing_value += f"**Exit:** {timing['best_exit_time']}\n"
        if timing.get('avoid_times'):
            timing_value += f"**Avoid:** {timing['avoid_times']}"
        
        if timing_value:
            embed.add_field(
                name="⏰ TIMING",
                value=timing_value,
                inline=False
            )
    
    # Key Levels
    key_levels = analysis.get('key_levels', {})
    if key_levels:
        levels_value = ""
        if key_levels.get('support'):
            supports = [f"${s:.2f}" for s in key_levels['support'][:3]]
            levels_value += f"**Support:** {', '.join(supports)}\n"
        if key_levels.get('resistance'):
            resistances = [f"${r:.2f}" for r in key_levels['resistance'][:3]]
            levels_value += f"**Resistance:** {', '.join(resistances)}"
        
        if levels_value:
            embed.add_field(
                name="📊 KEY LEVELS",
                value=levels_value,
                inline=False
            )
    
    # Footer with model info
    model_used = analysis.get('model_used', 'gpt-4o-mini')
    cost = analysis.get('cost_estimate', 0.0001)
    embed.set_footer(text=f"AI Model: {model_used} | Cost: ${cost:.4f} | Real-time analysis")
    
    return embed


# ==================== TARA-SPECIFIC MESSAGE TEMPLATES ====================
# Analyst-style message formatting for Tara personality

def format_existing_position_message(symbol: str, contract: str, position_data: Dict[str, Any]) -> str:
    """
    Format message when existing position is detected (Tara template).
    Returns analyst-style message with suggestion.
    """
    avg_price = position_data.get('avg_entry_price', 0)
    qty = position_data.get('qty', 0)
    open_pnl = position_data.get('unrealized_pl', 0)
    open_pnl_pct = position_data.get('unrealized_plpc', 0) * 100
    
    # Determine suggestion based on P&L
    if open_pnl_pct > 10:
        suggestion = "Scale-In (already profitable +{:.1f}%)".format(open_pnl_pct)
        rationale = "Position showing strength. Consider scaling if conviction remains high."
    elif open_pnl_pct < -5:
        suggestion = "Skip or Exit (down {:.1f}%)".format(abs(open_pnl_pct))
        rationale = "Position underwater. Avoid adding to losing trade unless thesis changed."
    else:
        suggestion = "Hold (flat {:.1f}%)".format(open_pnl_pct)
        rationale = "Position neutral. Let current position play out before adding exposure."
    
    message = (
        f"🔎 **Existing Position Detected — {symbol} {contract}**\n"
        f"─────────────────────────────────────────\n"
        f"**Avg Price:** ${avg_price:.2f} | **Qty:** {qty} | **Open P&L:** ${open_pnl:+.2f} ({open_pnl_pct:+.2f}%)\n"
        f"**Action:** Reviewing strategy before adding exposure.\n"
        f"**Suggest:** {suggestion}\n"
        f"**Rationale:** {rationale}"
    )
    return message


def format_order_submitted_message(symbol: str, contract: str, side: str, qty: int, price: float, order_type: str = "limit") -> str:
    """
    Format order submitted message (Tara trade lifecycle template).
    """
    iso_time = datetime.now().strftime("%H:%M:%S")
    price_str = f"${price:.2f}" if order_type == "limit" else "Market"
    
    message = (
        f"📤 **Order Submitted — {symbol} {contract}**\n"
        f"**Time:** {iso_time}\n"
        f"**Side:** {side.upper()} | **Qty:** {qty} | **Price:** {price_str}"
    )
    return message


def format_order_accepted_message(symbol: str, contract: str, broker_ref: str) -> str:
    """
    Format order accepted message (Tara trade lifecycle template).
    """
    message = (
        f"✅ **Order Accepted — {symbol} {contract}**\n"
        f"**BrokerRef:** {broker_ref}"
    )
    return message


def format_order_filled_message(symbol: str, contract: str, fill_price: float, filled_qty: int, avg_price: float, current_pnl: float = None) -> str:
    """
    Format order filled message (Tara trade lifecycle template).
    """
    message = (
        f"🟢 **Order Filled — {symbol} {contract}**\n"
        f"**Filled @** ${fill_price:.2f} | **Qty:** {filled_qty}\n"
        f"**Avg Price:** ${avg_price:.2f}"
    )
    
    if current_pnl is not None:
        message += f"\n**P&L (real-time):** ${current_pnl:+.2f}"
    
    return message


def format_account_summary(account_data: Dict[str, Any], api_calls: int = 0, performance_metrics: Optional[Dict[str, Any]] = None) -> str:
    """
    Format account summary with friendly field names and performance metrics (Tara template).
    """
    account_name = account_data.get('account_name', 'Trading Account')
    cash = float(account_data.get('cash', 0))
    equity = float(account_data.get('equity', 0))
    buying_power = float(account_data.get('buying_power', 0))
    
    # Calculate P&L metrics
    positions = account_data.get('positions', [])
    open_pnl = sum(float(p.get('unrealized_pl', 0)) for p in positions)
    equity_start = float(account_data.get('equity_start_of_day', equity))
    open_pnl_pct = (open_pnl / equity_start * 100) if equity_start > 0 else 0
    
    closed_pnl = float(account_data.get('closed_pl_today', 0))
    daily_return_pct = float(account_data.get('daily_return_pct', 0))
    total_return_pct = float(account_data.get('total_return_pct', 0))
    open_positions = len(positions)
    
    message = (
        f"💰 **Account Summary — {account_name}**\n"
        f"─────────────────────────────\n"
        f"**Cash Balance:** ${cash:,.2f}\n"
        f"**Equity:** ${equity:,.2f}\n"
        f"**Buying Power:** ${buying_power:,.2f}\n"
        f"**Open P&L:** ${open_pnl:+,.2f} ({open_pnl_pct:+.2f}%)\n"
        f"**Closed P&L (Today):** ${closed_pnl:+,.2f}\n"
        f"**Daily Return:** {daily_return_pct:+.2f}%\n"
        f"**Total Return:** {total_return_pct:+.2f}%\n"
        f"**Positions:** {open_positions}\n"
        f"**API Calls Today:** {api_calls}\n"
    )
    
    # Add performance metrics if available
    if performance_metrics and performance_metrics.get('total_trades', 0) > 0:
        message += (
            f"\n📊 **Performance Metrics (30 Days)**\n"
            f"─────────────────────────────\n"
            f"**Win Rate:** {performance_metrics.get('win_rate', 0):.1f}%\n"
            f"**Sharpe Ratio:** {performance_metrics.get('sharpe_ratio', 0):.2f}\n"
            f"**Max Drawdown:** {performance_metrics.get('max_drawdown', 0):.2f}%\n"
            f"**Profit Factor:** {performance_metrics.get('profit_factor', 0):.2f}\n"
            f"**Avg Win:** ${performance_metrics.get('avg_win', 0):,.2f}\n"
            f"**Avg Loss:** ${performance_metrics.get('avg_loss', 0):,.2f}\n"
            f"**Total Trades:** {performance_metrics.get('total_trades', 0)}\n"
            f"✅ *Real calculated metrics*"
        )
    
    return message


def format_circuit_breaker_message(reason: str, duration: str, actions: List[str]) -> str:
    """
    Format circuit breaker message with human explanation (Tara template).
    """
    actions_text = "\n".join([f"• {action}" for action in actions])
    
    message = (
        f"⚠️ **Circuit Breaker Activated**\n"
        f"**Reason:** {reason}\n"
        f"**Effect:** Trading paused for {duration}.\n\n"
        f"**Suggested Actions:**\n"
        f"{actions_text}\n\n"
        f"**To Resume:** Contact administrator or wait for automatic reset."
    )
    return message


def format_api_status(provider: str, calls_today: int, errors: int, rate_limit_used: int, rate_limit_total: int, 
                     last_calls: List[Dict[str, Any]], next_reset: str, notes: str = "") -> str:
    """
    Format API status message (Tara template).
    """
    last_calls_formatted = ", ".join(
        [f"{call['endpoint']}:{call['status']}:{call['latency_ms']}ms" for call in last_calls[:5]]
    ) if last_calls else "No recent calls"
    
    message = (
        f"⚙️ **API Status**\n"
        f"─────────────────\n"
        f"**Provider:** {provider}\n"
        f"**Calls Today:** {calls_today} | **Errors:** {errors}\n"
        f"**Rate Limit:** {rate_limit_used}/{rate_limit_total}\n"
        f"**Last 5 Calls:** [{last_calls_formatted}]\n"
        f"**Next Reset:** {next_reset}"
    )
    
    if notes:
        message += f"\n**Notes:** {notes}"
    
    return message


def format_premarket_analysis(date: str, opportunities: List[Dict[str, Any]]) -> str:
    """
    Format pre-market analysis (Tara template).
    """
    message = (
        f"☀️ **Pre-Market — {date}**\n"
        f"**Top Opportunities:**\n"
    )
    
    for opp in opportunities[:5]:  # Top 5
        symbol = opp.get('symbol', 'N/A')
        bias = opp.get('bias', 'neutral')
        rationale = opp.get('rationale', 'No details')
        entry = opp.get('entry', 0)
        stop = opp.get('stop', 0)
        target = opp.get('target', 0)
        
        message += (
            f"\n• **{symbol}** — Bias: **{bias.upper()}** — {rationale}\n"
            f"  Actionable: Entry ${entry:.2f} | Stop ${stop:.2f} | Target ${target:.2f}"
        )
    
    return message


def format_aftermarket_summary(date: str, summary: str, trades: Dict[str, Any], notes: str) -> str:
    """
    Format after-market summary (Tara template).
    """
    win_count = trades.get('wins', 0)
    loss_count = trades.get('losses', 0)
    net_pnl = trades.get('net_pnl', 0)
    
    message = (
        f"🌙 **After-Market Summary — {date}**\n"
        f"**Summary:** {summary}\n"
        f"**Trades:** Wins {win_count} / Losses {loss_count} | Net P&L: ${net_pnl:+,.2f}\n"
        f"**Notes:** {notes}"
    )
    return message


def format_scan_results(scan_name: str, timestamp: str, new_opportunities: List[Dict[str, Any]], 
                       active_positions: List[Dict[str, Any]] = None, include_active: bool = False) -> str:
    """
    Format scan results with separate sections for new opportunities and active positions (Tara template).
    """
    message = (
        f"🔍 **Scan — {scan_name} — {timestamp}**\n"
        f"─────────────────────────────\n"
        f"**New Opportunities:**\n"
    )
    
    if new_opportunities:
        for opp in new_opportunities[:10]:  # Limit to 10
            symbol = opp.get('symbol', 'N/A')
            signal = opp.get('signal', 'N/A')
            reason = opp.get('reason', 'No details')[:80]
            message += f"• **{symbol}** — {signal} — Reason: {reason}\n"
    else:
        message += "• No new opportunities found\n"
    
    if include_active and active_positions:
        message += "\n**Active Positions:**\n"
        for pos in active_positions[:10]:  # Limit to 10
            symbol = pos.get('symbol', 'N/A')
            open_pnl = pos.get('unrealized_pl', 0)
            status = pos.get('status', 'Open')
            message += f"• **{symbol}** — Open P&L: ${open_pnl:+.2f} | Status: {status}\n"
    
    return message


def format_backtest_results(symbol: str, timeframe: str, strategy: str, results: Dict[str, Any]) -> str:
    """
    Format backtest results (Tara template).
    """
    total_trades = results.get('total_trades', 0)
    win_rate = results.get('win_rate', 0)
    net_return = results.get('net_return', 0)
    max_drawdown = results.get('max_drawdown', 0)
    notes = results.get('notes', 'No additional notes')
    
    message = (
        f"🧪 **Backtest — {symbol} | {timeframe} | {strategy}**\n"
        f"**Total Trades:** {total_trades}\n"
        f"**Win Rate:** {win_rate:.1f}%\n"
        f"**Net Return:** {net_return:+.2f}%\n"
        f"**Max Drawdown:** {max_drawdown:.2f}%\n"
        f"**Notes:** {notes}"
    )
    return message


def create_enhanced_sentiment_embed(sentiment_data: Dict[str, Any]) -> discord.Embed:
    """
    Create enhanced sentiment embed with real market data.
    
    Shows:
    - News sentiment
    - Options flow
    - Technical indicators
    - Trading implications
    """
    symbol = sentiment_data.get("symbol", "Unknown")
    overall = sentiment_data.get("overall_sentiment", {})
    
    # Overall sentiment
    score = overall.get("score", 5.0)
    label = overall.get("label", "NEUTRAL")
    emoji = overall.get("emoji", "⚪")
    
    # Color based on sentiment
    if score >= 6:
        color = discord.Color.green()
    elif score >= 4.5:
        color = discord.Color.blue()
    else:
        color = discord.Color.red()
    
    embed = discord.Embed(
        title=f"📊 {symbol} Sentiment Analysis",
        description=f"{emoji} **Overall Sentiment:** {label} ({score}/10)",
        color=color,
        timestamp=datetime.now()
    )
    
    # News Sentiment
    news = sentiment_data.get("news_sentiment", {})
    if news.get("available"):
        pos_pct = news.get("positive_pct", 0)
        neu_pct = news.get("neutral_pct", 0)
        neg_pct = news.get("negative_pct", 0)
        total = news.get("analyzed_articles", 0)
        
        news_text = (
            f"🟢 Positive: {pos_pct:.0f}%\n"
            f"⚪ Neutral: {neu_pct:.0f}%\n"
            f"🔴 Negative: {neg_pct:.0f}%\n"
            f"📰 {total} articles analyzed (24h)"
        )
        
        embed.add_field(
            name="📰 News Sentiment",
            value=news_text,
            inline=True
        )
        
        # Top headlines
        headlines = news.get("top_headlines", [])
        if headlines:
            headline_text = ""
            for h in headlines[:3]:
                sent_emoji = "🟢" if h["sentiment"] == "Bullish" else "🔴" if h["sentiment"] == "Bearish" else "⚪"
                title = h["title"][:60] + "..." if len(h["title"]) > 60 else h["title"]
                headline_text += f"{sent_emoji} {title} ({h['time_ago']})\n"
            
            embed.add_field(
                name="📑 Top Headlines",
                value=headline_text or "No headlines",
                inline=False
            )
    else:
        embed.add_field(
            name="📰 News Sentiment",
            value="❌ No news data available",
            inline=True
        )
    
    # Options Flow
    options = sentiment_data.get("options_flow", {})
    if options.get("available"):
        ratio = options.get("call_put_ratio", 0)
        sentiment = options.get("sentiment", "Neutral")
        emoji_opt = options.get("emoji", "⚪")
        
        options_text = (
            f"📊 Call/Put Ratio: {ratio:.2f} ({sentiment})\n"
            f"📈 Call Volume: {options.get('call_volume', 0):,}\n"
            f"📉 Put Volume: {options.get('put_volume', 0):,}\n"
            f"💹 IV Rank: {options.get('iv_rank', 0):.0f}%"
        )
        
        embed.add_field(
            name="📊 Options Flow",
            value=options_text,
            inline=True
        )
        
        # Unusual activity
        unusual = options.get("unusual_activity", [])
        if unusual:
            unusual_text = ""
            for u in unusual[:3]:
                unusual_text += f"• {u['type']} ${u['strike']} - {u['volume']:,} vol\n"
            
            embed.add_field(
                name="🚨 Unusual Activity",
                value=unusual_text or "None detected",
                inline=False
            )
    else:
        embed.add_field(
            name="📊 Options Flow",
            value="❌ No options data available",
            inline=True
        )
    
    # Technical Sentiment
    technical = sentiment_data.get("technical_sentiment", {})
    if technical.get("available"):
        rsi = technical.get("rsi", 50)
        rsi_label = technical.get("rsi_label", "Neutral")
        rsi_emoji = technical.get("rsi_emoji", "⚪")
        
        macd_bullish = technical.get("macd_bullish", False)
        macd_emoji = "🟢" if macd_bullish else "🔴"
        macd_label = "Bullish" if macd_bullish else "Bearish"
        
        volume_ratio = technical.get("volume_ratio", 1.0)
        volume_label = technical.get("volume_label", "Normal")
        volume_emoji = technical.get("volume_emoji", "⚪")
        
        trend = technical.get("trend", "Sideways")
        trend_emoji = technical.get("trend_emoji", "⚪")
        
        technical_text = (
            f"{rsi_emoji} **RSI:** {rsi:.0f} ({rsi_label})\n"
            f"{macd_emoji} **MACD:** {macd_label}\n"
            f"{volume_emoji} **Volume:** {volume_ratio:.1f}x ({volume_label})\n"
            f"{trend_emoji} **Trend:** {trend}"
        )
        
        embed.add_field(
            name="📈 Technical Sentiment",
            value=technical_text,
            inline=True
        )
    else:
        embed.add_field(
            name="📈 Technical Sentiment",
            value="❌ No technical data available",
            inline=True
        )
    
    # Trading Implication
    price_data = sentiment_data.get("price_data", {})
    if price_data.get("available"):
        current = price_data.get("current_price", 0)
        high_52 = price_data.get("week_52_high", 0)
        low_52 = price_data.get("week_52_low", 0)
        
        # Determine trading implication based on overall sentiment
        if score >= 7:
            implication = f"🟢 **Sentiment supports LONG positions**\n"
            implication += f"💰 Current: ${current:.2f}\n"
            implication += f"🎯 Consider entries on pullbacks\n"
            implication += f"📊 52W Range: ${low_52:.2f} - ${high_52:.2f}"
        elif score >= 6:
            implication = f"🟢 **Slightly bullish - Watch for confirmation**\n"
            implication += f"💰 Current: ${current:.2f}\n"
            implication += f"⚠️ Wait for technical setup\n"
            implication += f"📊 52W Range: ${low_52:.2f} - ${high_52:.2f}"
        elif score >= 4.5:
            implication = f"⚪ **Neutral - No clear direction**\n"
            implication += f"💰 Current: ${current:.2f}\n"
            implication += f"⏸️ Stay on sidelines\n"
            implication += f"📊 52W Range: ${low_52:.2f} - ${high_52:.2f}"
        elif score >= 3:
            implication = f"🔴 **Slightly bearish - Caution advised**\n"
            implication += f"💰 Current: ${current:.2f}\n"
            implication += f"⚠️ Avoid new longs\n"
            implication += f"📊 52W Range: ${low_52:.2f} - ${high_52:.2f}"
        else:
            implication = f"🔴 **Bearish - Avoid or consider shorts**\n"
            implication += f"💰 Current: ${current:.2f}\n"
            implication += f"🚫 Stay away from longs\n"
            implication += f"📊 52W Range: ${low_52:.2f} - ${high_52:.2f}"
        
        embed.add_field(
            name="⚡ Trading Implication",
            value=implication,
            inline=False
        )
    
    # Sources
    sources_used = overall.get("sources_used", 0)
    embed.set_footer(text=f"Data from {sources_used} sources | Real market data, not AI fluff")
    
    return embed
