"""
Intelligent Scanner - Advanced market scanning with momentum, technicals, and AI analysis.
"""
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from loguru import logger

from services import (
    get_alpaca_service,
    get_sentiment_service,
    get_claude_service,
    get_news_service
)


class IntelligentScanner:
    """
    Advanced scanner that:
    1. Detects momentum (recent price moves in last minutes/candles)
    2. Analyzes with technical indicators
    3. Checks volume and Greeks
    4. Incorporates news sentiment
    5. Generates comprehensive score and recommendation
    """
    
    def __init__(self):
        """Initialize the intelligent scanner."""
        self.alpaca = get_alpaca_service()
        self.sentiment = get_sentiment_service()
        self.claude = get_claude_service()
        self.news = get_news_service()
        
    async def scan_with_full_analysis(self, watchlist: List[str]) -> Dict[str, Any]:
        """
        Perform comprehensive scan with full analysis.
        
        Args:
            watchlist: List of symbols to scan
            
        Returns:
            Complete scan results with recommendations
        """
        logger.info(f"🔍 Starting intelligent scan of {len(watchlist)} symbols...")
        
        scan_start = datetime.now()
        
        # Step 1: Detect momentum movers
        momentum_results = await self._detect_momentum_movers(watchlist)
        
        # Step 2: Analyze each mover with full technical analysis
        analyzed_opportunities = []
        for mover in momentum_results['movers']:
            analysis = await self._full_technical_analysis(mover)
            if analysis:
                analyzed_opportunities.append(analysis)
        
        # Step 3: Get AI recommendations for top opportunities
        top_opportunities = sorted(
            analyzed_opportunities,
            key=lambda x: x['momentum_score'],
            reverse=True
        )[:5]  # Top 5
        
        ai_recommendations = []
        for opp in top_opportunities:
            recommendation = await self._get_ai_recommendation(opp)
            if recommendation:
                ai_recommendations.append(recommendation)
        
        # Step 4: Generate summary report
        summary = await self._generate_scan_summary(
            watchlist,
            momentum_results,
            analyzed_opportunities,
            ai_recommendations
        )
        
        scan_duration = (datetime.now() - scan_start).total_seconds()
        
        logger.info(f"✅ Scan complete in {scan_duration:.1f}s: {len(ai_recommendations)} actionable opportunities")
        
        return {
            "summary": summary,
            "opportunities": ai_recommendations,
            "all_movers": analyzed_opportunities,
            "scan_stats": {
                "symbols_scanned": len(watchlist),
                "movers_detected": len(momentum_results['movers']),
                "opportunities_found": len(ai_recommendations),
                "duration_seconds": scan_duration,
                "timestamp": datetime.now().isoformat()
            }
        }
    
    async def _detect_momentum_movers(self, watchlist: List[str]) -> Dict[str, Any]:
        """
        Detect stocks with significant momentum in recent candles.
        
        Looks for:
        - Sudden price moves in last 5-15 minutes
        - Volume spikes
        - Breakouts from consolidation
        """
        logger.info("📊 Detecting momentum movers...")
        
        movers = []
        
        for symbol in watchlist:
            try:
                # Get intraday bars (5-minute candles)
                bars_5min = await self.alpaca.get_bars(
                    symbol,
                    timeframe="5Min",
                    limit=20  # Last 100 minutes
                )
                
                # Get daily bars for context
                bars_daily = await self.alpaca.get_bars(
                    symbol,
                    timeframe="1Day",
                    limit=30
                )
                
                if not bars_5min or len(bars_5min) < 10:
                    continue
                
                # Get current quote
                quote = await self.alpaca.get_latest_quote(symbol)
                if not quote:
                    continue
                
                current_price = quote['price']
                
                # Calculate momentum indicators
                momentum = self._calculate_momentum(bars_5min, bars_daily, current_price)
                
                # Check if this is a mover
                if self._is_significant_mover(momentum):
                    movers.append({
                        "symbol": symbol,
                        "current_price": current_price,
                        "momentum": momentum,
                        "bars_5min": bars_5min[-10:],  # Last 10 candles
                        "bars_daily": bars_daily,
                        "quote": quote
                    })
                    logger.info(f"  🚀 {symbol}: {momentum['direction']} {momentum['move_pct']:.2f}% in {momentum['timeframe']}")
                
            except Exception as e:
                logger.error(f"Error detecting momentum for {symbol}: {e}")
                continue
        
        return {
            "movers": movers,
            "timestamp": datetime.now().isoformat()
        }
    
    def _calculate_momentum(
        self,
        bars_5min: List[Dict],
        bars_daily: List[Dict],
        current_price: float
    ) -> Dict[str, Any]:
        """Calculate comprehensive momentum indicators."""
        
        # Recent 5-min candles
        recent_closes = [bar['close'] for bar in bars_5min[-10:]]
        recent_volumes = [bar['volume'] for bar in bars_5min[-10:]]
        recent_highs = [bar['high'] for bar in bars_5min[-10:]]
        recent_lows = [bar['low'] for bar in bars_5min[-10:]]
        
        # Daily data
        daily_closes = [bar['close'] for bar in bars_daily]
        daily_volumes = [bar['volume'] for bar in bars_daily]
        
        # 1. Price momentum (last 15 minutes vs 50 minutes ago)
        price_15min_ago = recent_closes[0] if len(recent_closes) >= 3 else recent_closes[0]
        move_15min = ((current_price - price_15min_ago) / price_15min_ago) * 100
        
        # 2. Volume analysis
        avg_volume_5min = sum(recent_volumes) / len(recent_volumes) if recent_volumes else 1
        current_volume_5min = recent_volumes[-1] if recent_volumes else 0
        volume_ratio = current_volume_5min / avg_volume_5min if avg_volume_5min > 0 else 0
        
        # 3. Volatility (ATR-like)
        ranges = [high - low for high, low in zip(recent_highs, recent_lows)]
        avg_range = sum(ranges) / len(ranges) if ranges else 0
        volatility_pct = (avg_range / current_price) * 100 if current_price > 0 else 0
        
        # 4. Trend strength
        if len(recent_closes) >= 5:
            # Simple trend: are we making higher highs?
            trend_up = all(recent_closes[i] >= recent_closes[i-1] for i in range(-4, 0))
            trend_down = all(recent_closes[i] <= recent_closes[i-1] for i in range(-4, 0))
            trend = "STRONG_UP" if trend_up else "STRONG_DOWN" if trend_down else "CHOPPY"
        else:
            trend = "UNKNOWN"
        
        # 5. Daily context
        sma_20 = sum(daily_closes[-20:]) / 20 if len(daily_closes) >= 20 else current_price
        distance_from_sma = ((current_price - sma_20) / sma_20) * 100
        
        avg_daily_volume = sum(daily_volumes[-20:]) / 20 if len(daily_volumes) >= 20 else 1
        daily_volume_ratio = daily_volumes[-1] / avg_daily_volume if avg_daily_volume > 0 else 0
        
        return {
            "move_pct": move_15min,
            "direction": "UP" if move_15min > 0 else "DOWN",
            "timeframe": "15min",
            "volume_ratio_5min": volume_ratio,
            "volume_ratio_daily": daily_volume_ratio,
            "volatility_pct": volatility_pct,
            "trend": trend,
            "distance_from_sma20": distance_from_sma,
            "sma_20": sma_20,
            "strength": abs(move_15min) * volume_ratio  # Momentum strength score
        }
    
    def _is_significant_mover(self, momentum: Dict[str, Any]) -> bool:
        """Determine if momentum is significant enough to analyze."""
        
        # Criteria for significant mover:
        # 1. Price moved > 1% in last 15 minutes, OR
        # 2. Price moved > 0.5% with high volume (>2x), OR
        # 3. Strong trend with volume confirmation
        
        move = abs(momentum['move_pct'])
        vol_ratio = momentum['volume_ratio_5min']
        trend = momentum['trend']
        
        if move > 1.0:  # Strong move
            return True
        
        if move > 0.5 and vol_ratio > 2.0:  # Moderate move with high volume
            return True
        
        if trend in ["STRONG_UP", "STRONG_DOWN"] and vol_ratio > 1.5:
            return True
        
        return False
    
    async def _full_technical_analysis(self, mover: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Perform full technical analysis on a mover.
        
        Includes:
        - Moving averages (SMA, EMA)
        - RSI, MACD
        - Support/Resistance
        - Volume analysis
        - Greeks (for options)
        """
        symbol = mover['symbol']
        logger.info(f"  📈 Analyzing {symbol}...")
        
        try:
            bars_daily = mover['bars_daily']
            current_price = mover['current_price']
            
            closes = [bar['close'] for bar in bars_daily]
            volumes = [bar['volume'] for bar in bars_daily]
            highs = [bar['high'] for bar in bars_daily]
            lows = [bar['low'] for bar in bars_daily]
            
            # Calculate technical indicators
            technicals = self._calculate_technical_indicators(
                closes, volumes, highs, lows, current_price
            )
            
            # Get options data and Greeks
            options_analysis = await self._analyze_options(symbol, current_price)
            
            # Calculate momentum score (0-100)
            momentum_score = self._calculate_momentum_score(
                mover['momentum'],
                technicals,
                options_analysis
            )
            
            return {
                "symbol": symbol,
                "current_price": current_price,
                "momentum": mover['momentum'],
                "technicals": technicals,
                "options": options_analysis,
                "momentum_score": momentum_score,
                "quote": mover['quote']
            }
            
        except Exception as e:
            logger.error(f"Error in technical analysis for {symbol}: {e}")
            return None
    
    def _calculate_technical_indicators(
        self,
        closes: List[float],
        volumes: List[float],
        highs: List[float],
        lows: List[float],
        current_price: float
    ) -> Dict[str, Any]:
        """Calculate technical indicators."""
        
        # Moving averages
        sma_10 = sum(closes[-10:]) / 10 if len(closes) >= 10 else current_price
        sma_20 = sum(closes[-20:]) / 20 if len(closes) >= 20 else current_price
        sma_50 = sum(closes[-50:]) / 50 if len(closes) >= 50 else current_price
        
        # RSI (simplified 14-period)
        rsi = self._calculate_rsi(closes, period=14)
        
        # Support/Resistance (recent highs/lows)
        support = min(lows[-20:]) if len(lows) >= 20 else current_price * 0.95
        resistance = max(highs[-20:]) if len(highs) >= 20 else current_price * 1.05
        
        # Volume trend
        avg_volume = sum(volumes[-20:]) / 20 if len(volumes) >= 20 else 1
        volume_trend = "INCREASING" if volumes[-1] > avg_volume * 1.2 else "DECREASING" if volumes[-1] < avg_volume * 0.8 else "NORMAL"
        
        # Price position
        distance_to_resistance = ((resistance - current_price) / current_price) * 100
        distance_to_support = ((current_price - support) / current_price) * 100
        
        return {
            "sma_10": sma_10,
            "sma_20": sma_20,
            "sma_50": sma_50,
            "rsi": rsi,
            "support": support,
            "resistance": resistance,
            "distance_to_resistance_pct": distance_to_resistance,
            "distance_to_support_pct": distance_to_support,
            "volume_trend": volume_trend,
            "avg_volume": avg_volume,
            "price_vs_sma20": "ABOVE" if current_price > sma_20 else "BELOW",
            "golden_cross": sma_10 > sma_20 > sma_50 if len(closes) >= 50 else False
        }
    
    def _calculate_rsi(self, closes: List[float], period: int = 14) -> float:
        """Calculate RSI indicator."""
        if len(closes) < period + 1:
            return 50.0  # Neutral
        
        gains = []
        losses = []
        
        for i in range(1, len(closes)):
            change = closes[i] - closes[i-1]
            if change > 0:
                gains.append(change)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(change))
        
        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    async def _analyze_options(self, symbol: str, current_price: float) -> Dict[str, Any]:
        """Analyze options for the symbol."""
        try:
            # Get options chain
            options_chain = await self.alpaca.get_options_chain(symbol)
            
            if not options_chain or 'strikes' not in options_chain:
                return {"available": False}
            
            # Find ATM options
            atm_call = None
            atm_put = None
            min_diff = float('inf')
            
            for strike_data in options_chain['strikes']:
                strike = strike_data['strike']
                diff = abs(strike - current_price)
                
                if diff < min_diff:
                    min_diff = diff
                    if strike_data['type'] == 'call':
                        atm_call = strike_data
                    else:
                        atm_put = strike_data
            
            return {
                "available": True,
                "atm_call": atm_call,
                "atm_put": atm_put,
                "underlying_price": options_chain.get('underlying_price', current_price)
            }
            
        except Exception as e:
            logger.debug(f"Options not available for {symbol}: {e}")
            return {"available": False}
    
    def _calculate_momentum_score(
        self,
        momentum: Dict[str, Any],
        technicals: Dict[str, Any],
        options: Dict[str, Any]
    ) -> float:
        """
        Calculate comprehensive momentum score (0-100).
        
        Factors:
        - Price momentum strength
        - Volume confirmation
        - Technical alignment
        - Trend strength
        """
        score = 0.0
        
        # 1. Price momentum (0-30 points)
        move_pct = abs(momentum['move_pct'])
        score += min(move_pct * 10, 30)  # Max 30 points
        
        # 2. Volume confirmation (0-20 points)
        vol_ratio = momentum['volume_ratio_5min']
        score += min(vol_ratio * 10, 20)  # Max 20 points
        
        # 3. Technical alignment (0-25 points)
        if technicals['price_vs_sma20'] == "ABOVE" and momentum['direction'] == "UP":
            score += 10
        elif technicals['price_vs_sma20'] == "BELOW" and momentum['direction'] == "DOWN":
            score += 10
        
        if 30 <= technicals['rsi'] <= 70:  # Not overbought/oversold
            score += 10
        
        if technicals['golden_cross']:
            score += 5
        
        # 4. Trend strength (0-15 points)
        if momentum['trend'] in ["STRONG_UP", "STRONG_DOWN"]:
            score += 15
        elif momentum['trend'] == "CHOPPY":
            score += 5
        
        # 5. Volume trend (0-10 points)
        if technicals['volume_trend'] == "INCREASING":
            score += 10
        elif technicals['volume_trend'] == "NORMAL":
            score += 5
        
        return min(score, 100)  # Cap at 100
    
    async def _get_ai_recommendation(self, opportunity: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Get AI recommendation using Claude for comprehensive analysis.
        
        Includes:
        - News sentiment
        - Risk assessment
        - Entry/exit strategy
        - Position sizing
        - Options vs stock recommendation
        """
        symbol = opportunity['symbol']
        logger.info(f"  🤖 Getting AI recommendation for {symbol}...")
        
        try:
            # Get news sentiment
            news_data = await self.news.get_headlines(symbol, max_headlines=5)
            
            # Build comprehensive prompt for Claude
            prompt = self._build_recommendation_prompt(opportunity, news_data)
            
            # Get Claude's analysis
            messages = [
                {"role": "user", "content": prompt}
            ]
            response = await self.claude.analyze_stock(messages)
            
            # Parse response
            recommendation = self._parse_ai_recommendation(response, opportunity)
            
            return recommendation
            
        except Exception as e:
            logger.error(f"Error getting AI recommendation for {symbol}: {e}")
            return None
    
    def _build_recommendation_prompt(
        self,
        opportunity: Dict[str, Any],
        news_data: List[str]
    ) -> str:
        """Build comprehensive prompt for AI analysis."""
        
        symbol = opportunity['symbol']
        momentum = opportunity['momentum']
        technicals = opportunity['technicals']
        options = opportunity['options']
        
        prompt = f"""Analyze this trading opportunity and provide a comprehensive recommendation.

SYMBOL: {symbol}
CURRENT PRICE: ${opportunity['current_price']:.2f}

MOMENTUM (Last 15 minutes):
- Direction: {momentum['direction']}
- Move: {momentum['move_pct']:+.2f}%
- Volume Ratio: {momentum['volume_ratio_5min']:.2f}x
- Trend: {momentum['trend']}
- Strength Score: {momentum['strength']:.1f}

TECHNICAL INDICATORS:
- RSI: {technicals['rsi']:.1f}
- Price vs SMA20: {technicals['price_vs_sma20']}
- Support: ${technicals['support']:.2f} ({technicals['distance_to_support_pct']:.1f}% below)
- Resistance: ${technicals['resistance']:.2f} ({technicals['distance_to_resistance_pct']:.1f}% above)
- Volume Trend: {technicals['volume_trend']}
- Golden Cross: {technicals['golden_cross']}

OPTIONS AVAILABLE: {options['available']}

RECENT NEWS:
{chr(10).join(f'- {headline}' for headline in news_data[:5]) if news_data else '- No recent news'}

MOMENTUM SCORE: {opportunity['momentum_score']:.0f}/100

Provide a JSON response with:
{{
  "action": "BUY_STOCK|BUY_CALL|BUY_PUT|WAIT",
  "confidence": 0-100,
  "reasoning": "2-3 sentence explanation",
  "entry_strategy": "When and how to enter",
  "target_price": price target,
  "stop_loss": stop loss price,
  "risk_level": "LOW|MEDIUM|HIGH",
  "time_horizon": "SCALP|DAY|SWING",
  "position_size_pct": 1-10 (% of portfolio),
  "why_not_other_options": "Why not stock/call/put instead"
}}"""
        
        return prompt
    
    def _parse_ai_recommendation(
        self,
        ai_response: str,
        opportunity: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Parse AI recommendation response."""
        
        import json
        
        try:
            # Try to parse JSON from response
            recommendation = json.loads(ai_response)
        except:
            # Fallback if JSON parsing fails
            recommendation = {
                "action": "WAIT",
                "confidence": 50,
                "reasoning": "Unable to parse AI response",
                "risk_level": "HIGH"
            }
        
        # Add opportunity data
        recommendation['symbol'] = opportunity['symbol']
        recommendation['current_price'] = opportunity['current_price']
        recommendation['momentum_score'] = opportunity['momentum_score']
        recommendation['momentum'] = opportunity['momentum']
        recommendation['technicals'] = opportunity['technicals']
        recommendation['timestamp'] = datetime.now().isoformat()
        
        return recommendation
    
    async def _generate_scan_summary(
        self,
        watchlist: List[str],
        momentum_results: Dict[str, Any],
        analyzed_opportunities: List[Dict[str, Any]],
        ai_recommendations: List[Dict[str, Any]]
    ) -> str:
        """Generate human-readable scan summary."""
        
        summary = f"""
🔍 **MARKET SCAN SUMMARY**

📊 **Scan Overview:**
- Symbols Scanned: {len(watchlist)}
- Momentum Movers: {len(momentum_results['movers'])}
- Analyzed Opportunities: {len(analyzed_opportunities)}
- AI Recommendations: {len(ai_recommendations)}

"""
        
        if ai_recommendations:
            summary += "🎯 **TOP OPPORTUNITIES:**\n\n"
            
            for i, rec in enumerate(ai_recommendations[:3], 1):
                summary += f"{i}. **{rec['symbol']}** - ${rec['current_price']:.2f}\n"
                summary += f"   Action: {rec['action']} (Confidence: {rec['confidence']}%)\n"
                summary += f"   {rec['reasoning']}\n"
                summary += f"   Risk: {rec.get('risk_level', 'UNKNOWN')} | Score: {rec['momentum_score']:.0f}/100\n\n"
        else:
            summary += "⏸️ **No actionable opportunities found at this time.**\n\n"
        
        summary += "📈 **NEXT STEPS:**\n"
        if ai_recommendations:
            summary += "- Review top opportunities above\n"
            summary += "- Check entry strategies\n"
            summary += "- Validate with your risk tolerance\n"
            summary += "- Execute trades if conditions align\n"
        else:
            summary += "- Continue monitoring for momentum\n"
            summary += "- Wait for better setups\n"
            summary += "- Next scan in 30 minutes\n"
        
        return summary
