"""
Intelligent Scanner - Advanced market scanning with momentum, technicals, and AI analysis.
"""
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from loguru import logger

from agents.base_agent import BaseAgent
from services import (
    get_alpaca_service,
    get_sentiment_service,
    get_claude_service,
    get_news_service
)

# Import quantitative strategies
try:
    from strategies.strategy_manager import StrategyManager
    from utils.multi_timeframe import MultiTimeframeAnalyzer
    STRATEGIES_AVAILABLE = True
except ImportError:
    STRATEGIES_AVAILABLE = False
    logger.warning("Quantitative strategies not available for scanner")


class IntelligentScanner:
    """
    Advanced scanner that:
    1. Detects momentum (recent price moves in last minutes/candles)
    2. Analyzes with technical indicators
    3. Checks volume and Greeks
    4. Incorporates news sentiment
    5. Generates comprehensive score and analysis
    6. Uses quantitative strategies for signal generation
    """
    
    def __init__(self):
        """Initialize the intelligent scanner."""
        self.alpaca = get_alpaca_service()
        self.sentiment = get_sentiment_service()
        self.claude = get_claude_service()
        self.news = get_news_service()
        
        # Initialize quantitative strategies
        if STRATEGIES_AVAILABLE:
            self.strategy_manager = StrategyManager()
            self.mtf_analyzer = MultiTimeframeAnalyzer()
            logger.info("✅ Scanner: Quantitative strategies enabled")
        else:
            self.strategy_manager = None
            self.mtf_analyzer = None
        
    async def scan_with_full_analysis(self, watchlist: List[str]) -> Dict[str, Any]:
        """
        Perform comprehensive scan with full analysis.
        
        Args:
            watchlist: List of symbols to scan
            
        Returns:
            Complete scan results with analysis
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
        
        # Step 3: Get AI analysis for top opportunities
        top_opportunities = sorted(
            analyzed_opportunities,
            key=lambda x: x['momentum_score'],
            reverse=True
        )[:5]  # Top 5
        
        ai_analysis = []
        for opp in top_opportunities:
            analysis = await self._get_ai_analysis(opp)
            if analysis:
                ai_analysis.append(analysis)
        
        # Step 4: Generate summary report
        summary = await self._generate_scan_summary(
            watchlist,
            momentum_results,
            analyzed_opportunities,
            ai_analysis
        )
        
        scan_duration = (datetime.now() - scan_start).total_seconds()
        
        logger.info(f"✅ Scan complete in {scan_duration:.1f}s: {len(ai_analysis)} actionable opportunities")
        
        return {
            "summary": summary,
            "opportunities": ai_analysis,
            "all_movers": analyzed_opportunities,
            "scan_stats": {
                "symbols_scanned": len(watchlist),
                "movers_detected": len(momentum_results['movers']),
                "opportunities_found": len(ai_analysis),
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
        
        # Use Alpaca's bulk snapshot API - 10x faster!
        logger.info(f"📸 Getting snapshots for {len(watchlist)} symbols in ONE API call...")
        snapshots = await self.alpaca.get_snapshots_bulk(watchlist)
        
        if not snapshots:
            logger.warning("No snapshots received from Alpaca")
            return {"movers": [], "timestamp": datetime.now().isoformat()}
        
        logger.info(f"✅ Got {len(snapshots)} snapshots from Alpaca")
        
        for symbol, snapshot in snapshots.items():
            try:
                current_price = snapshot['price']
                prev_close = snapshot['prev_close']
                change_1d = snapshot['change_1d_pct']
                
                # Get 5-min bars only if needed for detailed momentum
                bars_5min = await self.alpaca.get_bars(
                    symbol,
                    timeframe="5Min",
                    limit=20
                )
                
                if not bars_5min or len(bars_5min) < 10:
                    continue
                
                # Calculate momentum using Alpaca's data
                momentum = self._calculate_momentum_from_snapshot(
                    snapshot, 
                    bars_5min
                )
                
                # Check if this is a mover
                if self._is_significant_mover(momentum):
                    movers.append({
                        "symbol": symbol,
                        "current_price": current_price,
                        "momentum": momentum,
                        "bars_5min": bars_5min[-10:],
                        "snapshot": snapshot  # Include full snapshot data
                    })
                    logger.info(f"  🚀 {symbol}: {momentum['direction']} {momentum['move_pct']:.2f}% in {momentum['timeframe']}")
                
            except Exception as e:
                logger.error(f"Error detecting momentum for {symbol}: {e}")
                continue
        
        return {
            "movers": movers,
            "timestamp": datetime.now().isoformat()
        }
    
    def _calculate_momentum_from_snapshot(
        self,
        snapshot: Dict[str, Any],
        bars_5min: List[Dict]
    ) -> Dict[str, Any]:
        """Calculate momentum using Alpaca's snapshot data (no manual calculations!)."""
        
        current_price = snapshot['price']
        prev_close = snapshot['prev_close']
        daily_volume = snapshot['daily_volume']
        
        # Use Alpaca's pre-calculated 1-day change
        change_1d = snapshot['change_1d_pct']
        
        # Recent 5-min candles for intraday momentum
        recent_closes = [bar['close'] for bar in bars_5min[-10:]]
        recent_volumes = [bar['volume'] for bar in bars_5min[-10:]]
        recent_highs = [bar['high'] for bar in bars_5min[-10:]]
        recent_lows = [bar['low'] for bar in bars_5min[-10:]]
        
        # 1. Intraday momentum (last 15 minutes)
        price_15min_ago = recent_closes[0] if len(recent_closes) >= 3 else recent_closes[0]
        move_15min = ((current_price - price_15min_ago) / price_15min_ago) * 100
        
        # 2. Volume analysis (5-min)
        avg_volume_5min = sum(recent_volumes) / len(recent_volumes) if recent_volumes else 1
        current_volume_5min = recent_volumes[-1] if recent_volumes else 0
        volume_ratio_5min = current_volume_5min / avg_volume_5min if avg_volume_5min > 0 else 0
        
        # 3. Volatility (ATR-like)
        ranges = [high - low for high, low in zip(recent_highs, recent_lows)]
        avg_range = sum(ranges) / len(ranges) if ranges else 0
        volatility_pct = (avg_range / current_price) * 100 if current_price > 0 else 0
        
        # 4. Trend strength
        if len(recent_closes) >= 5:
            trend_up = all(recent_closes[i] >= recent_closes[i-1] for i in range(-4, 0))
            trend_down = all(recent_closes[i] <= recent_closes[i-1] for i in range(-4, 0))
            trend = "STRONG_UP" if trend_up else "STRONG_DOWN" if trend_down else "CHOPPY"
        else:
            trend = "UNKNOWN"
        
        # 5. Daily context from snapshot
        daily_high = snapshot['daily_high']
        daily_low = snapshot['daily_low']
        daily_open = snapshot['daily_open']
        
        # Distance from daily high/low
        distance_from_high = ((current_price - daily_high) / daily_high) * 100 if daily_high > 0 else 0
        distance_from_low = ((current_price - daily_low) / daily_low) * 100 if daily_low > 0 else 0
        
        return {
            "move_pct": move_15min,
            "change_1d_pct": change_1d,  # From Alpaca!
            "direction": "UP" if move_15min > 0 else "DOWN",
            "timeframe": "15min",
            "volume_ratio_5min": volume_ratio_5min,
            "volatility_pct": volatility_pct,
            "trend": trend,
            "distance_from_high": distance_from_high,
            "distance_from_low": distance_from_low,
            "daily_high": daily_high,
            "daily_low": daily_low,
            "daily_open": daily_open,
            "prev_close": prev_close,
            "strength": abs(move_15min) * volume_ratio_5min  # Momentum strength score
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
            # Get daily bars for technical analysis (need 200 for MTF)
            from datetime import datetime, timedelta
            end_date = datetime.now()
            start_date = end_date - timedelta(days=250)  # Get more for MTF
            bars_daily = await self.alpaca.get_bars(
                symbol,
                timeframe="1Day",
                limit=250,  # Increased for multi-timeframe analysis
                start=start_date,
                end=end_date
            )
            
            if not bars_daily or len(bars_daily) < 20:
                logger.warning(f"Insufficient daily bars for {symbol}")
                return None
            
            current_price = mover['current_price']
            
            closes = [bar['close'] for bar in bars_daily]
            volumes = [bar['volume'] for bar in bars_daily]
            highs = [bar['high'] for bar in bars_daily]
            lows = [bar['low'] for bar in bars_daily]
            
            # Calculate technical indicators
            technicals = self._calculate_technical_indicators(
                closes, volumes, highs, lows, current_price
            )
            
            # NEW: Run quantitative strategies
            strategy_signal = None
            if self.strategy_manager and len(bars_daily) >= 30:
                try:
                    strategy_signal = self.strategy_manager.analyze_all(
                        symbol=symbol,
                        bars=bars_daily,
                        current_price=current_price
                    )
                    if strategy_signal:
                        action = strategy_signal.get('action', 'HOLD')
                        strategy_name = strategy_signal.get('strategy', 'Unknown')
                        logger.info(f"  🎯 Strategy signal for {symbol}: {action} ({strategy_name})")
                except Exception as e:
                    logger.error(f"Error running strategies for {symbol}: {e}")
            
            # NEW: Multi-timeframe analysis (need 200 bars)
            mtf_analysis = None
            if self.mtf_analyzer and len(bars_daily) >= 200:
                try:
                    mtf_analysis = self.mtf_analyzer.analyze(bars_daily, current_price)
                    if mtf_analysis and mtf_analysis.get('available'):
                        alignment = mtf_analysis.get('alignment', {}).get('alignment', 'UNKNOWN')
                        logger.info(f"  📈 MTF for {symbol}: {alignment}")
                except Exception as e:
                    logger.error(f"Error in MTF analysis for {symbol}: {e}")
            elif len(bars_daily) < 200:
                logger.debug(f"  ⚠️ Insufficient bars for MTF ({len(bars_daily)}/200)")
            
            # Get options data and Greeks
            options_analysis = await self._analyze_options(symbol, current_price)
            
            # Calculate momentum score (0-100) - NOW includes strategy and MTF
            momentum_score = self._calculate_momentum_score(
                mover['momentum'],
                technicals,
                strategy_signal,
                mtf_analysis,
                options_analysis
            )
            
            return {
                "symbol": symbol,
                "current_price": current_price,
                "momentum": mover['momentum'],
                "technicals": technicals,
                "strategy_signal": strategy_signal,  # NEW
                "mtf_analysis": mtf_analysis,        # NEW
                "options": options_analysis,
                "momentum_score": momentum_score,
                "snapshot": mover.get('snapshot', {})
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
        """Calculate technical indicators including Bollinger Bands, ATR, and VWAP."""
        
        # Moving averages
        sma_10 = sum(closes[-10:]) / 10 if len(closes) >= 10 else current_price
        sma_20 = sum(closes[-20:]) / 20 if len(closes) >= 20 else current_price
        sma_50 = sum(closes[-50:]) / 50 if len(closes) >= 50 else current_price
        
        # RSI (simplified 14-period)
        rsi = self._calculate_rsi(closes, period=14)
        
        # Bollinger Bands (20-period, 2 std dev) - NEW
        bb_upper, bb_middle, bb_lower, bb_width = self._calculate_bollinger_bands(closes, period=20)
        
        # ATR (Average True Range) - NEW
        atr = self._calculate_atr(highs, lows, closes, period=14)
        
        # VWAP (Volume Weighted Average Price) - NEW
        vwap = self._calculate_vwap(closes, highs, lows, volumes)
        
        # Support/Resistance (recent highs/lows)
        support = min(lows[-20:]) if len(lows) >= 20 else current_price * 0.95
        resistance = max(highs[-20:]) if len(highs) >= 20 else current_price * 1.05
        
        # Volume trend
        avg_volume = sum(volumes[-20:]) / 20 if len(volumes) >= 20 else 1
        volume_trend = "INCREASING" if volumes[-1] > avg_volume * 1.2 else "DECREASING" if volumes[-1] < avg_volume * 0.8 else "NORMAL"
        
        # Price position
        distance_to_resistance = ((resistance - current_price) / current_price) * 100
        distance_to_support = ((current_price - support) / current_price) * 100
        
        # Bollinger Band position
        bb_position = "OVERBOUGHT" if current_price > bb_upper else "OVERSOLD" if current_price < bb_lower else "NEUTRAL"
        
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
            "golden_cross": sma_10 > sma_20 > sma_50 if len(closes) >= 50 else False,
            # NEW INDICATORS
            "bollinger_upper": bb_upper,
            "bollinger_middle": bb_middle,
            "bollinger_lower": bb_lower,
            "bollinger_width": bb_width,
            "bollinger_position": bb_position,
            "atr": atr,
            "atr_pct": (atr / current_price * 100) if current_price > 0 else 0,
            "vwap": vwap,
            "price_vs_vwap": "ABOVE" if current_price > vwap else "BELOW",
            "data_source": "calculated"  # ✅ Clear indicator
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
    
    def _calculate_bollinger_bands(self, closes: List[float], period: int = 20, std_dev: float = 2.0) -> tuple:
        """
        Calculate Bollinger Bands.
        
        Returns:
            (upper_band, middle_band, lower_band, bandwidth)
        """
        if len(closes) < period:
            current = closes[-1] if closes else 0
            return (current * 1.02, current, current * 0.98, 0.04)
        
        # Middle band (SMA)
        middle = sum(closes[-period:]) / period
        
        # Standard deviation
        variance = sum((x - middle) ** 2 for x in closes[-period:]) / period
        std = variance ** 0.5
        
        # Upper and lower bands
        upper = middle + (std_dev * std)
        lower = middle - (std_dev * std)
        
        # Bandwidth (normalized)
        bandwidth = ((upper - lower) / middle) * 100 if middle > 0 else 0
        
        return (upper, middle, lower, bandwidth)
    
    def _calculate_atr(self, highs: List[float], lows: List[float], closes: List[float], period: int = 14) -> float:
        """
        Calculate Average True Range (ATR) for volatility measurement.
        
        Returns:
            ATR value
        """
        if len(closes) < period + 1:
            return 0.0
        
        true_ranges = []
        for i in range(1, len(closes)):
            high_low = highs[i] - lows[i]
            high_close = abs(highs[i] - closes[i-1])
            low_close = abs(lows[i] - closes[i-1])
            true_range = max(high_low, high_close, low_close)
            true_ranges.append(true_range)
        
        # Average of last 'period' true ranges
        atr = sum(true_ranges[-period:]) / period if len(true_ranges) >= period else 0
        
        return atr
    
    def _calculate_vwap(self, closes: List[float], highs: List[float], lows: List[float], volumes: List[float]) -> float:
        """
        Calculate Volume Weighted Average Price (VWAP).
        
        Returns:
            VWAP value
        """
        if not closes or not volumes or len(closes) != len(volumes):
            return closes[-1] if closes else 0
        
        # Typical price = (high + low + close) / 3
        typical_prices = []
        for i in range(len(closes)):
            if i < len(highs) and i < len(lows):
                typical = (highs[i] + lows[i] + closes[i]) / 3
            else:
                typical = closes[i]
            typical_prices.append(typical)
        
        # VWAP = sum(typical_price * volume) / sum(volume)
        cumulative_tp_volume = sum(tp * vol for tp, vol in zip(typical_prices, volumes))
        cumulative_volume = sum(volumes)
        
        vwap = cumulative_tp_volume / cumulative_volume if cumulative_volume > 0 else closes[-1]
        
        return vwap
    
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
        strategy_signal: Optional[Dict[str, Any]],
        mtf_analysis: Optional[Dict[str, Any]],
        options: Dict[str, Any]
    ) -> float:
        """
        Calculate comprehensive momentum score (0-100) with quantitative strategies.
        
        Weighting:
        - Technical indicators: 30%
        - Quantitative strategies: 40%
        - Multi-timeframe: 20%
        - Momentum/Volume: 10%
        """
        score = 0.0
        
        # 1. Technical Score (30 points max)
        technical_score = 0
        
        # RSI
        rsi = technicals.get('rsi', 50)
        if rsi < 30:
            technical_score += 10  # Oversold
        elif rsi > 70:
            technical_score -= 10  # Overbought
        elif 40 <= rsi <= 60:
            technical_score += 5  # Neutral zone
        
        # Price vs SMA
        if technicals['price_vs_sma20'] == "ABOVE" and momentum['direction'] == "UP":
            technical_score += 10
        elif technicals['price_vs_sma20'] == "BELOW" and momentum['direction'] == "DOWN":
            technical_score += 10
        
        # Golden/Death Cross
        if technicals.get('golden_cross'):
            technical_score += 10
        
        score += max(0, technical_score) * 0.3
        
        # 2. Quantitative Strategy Score (40 points max) - NEW
        strategy_score = 50  # Neutral default
        if strategy_signal:
            action = strategy_signal.get('action', 'HOLD')
            if action == 'BUY':
                strategy_score = 100
            elif action == 'SELL':
                strategy_score = 0
            # Boost based on confidence if available
            confidence = strategy_signal.get('confidence', 0.75)
            strategy_score *= confidence
        
        score += strategy_score * 0.4
        
        # 3. Multi-Timeframe Score (20 points max) - NEW
        mtf_score = 50  # Neutral default
        if mtf_analysis and mtf_analysis.get('available'):
            alignment = mtf_analysis.get('alignment', {}).get('alignment', 'MIXED')
            if alignment == 'FULLY_ALIGNED_BULLISH':
                mtf_score = 100
            elif alignment == 'MOSTLY_BULLISH':
                mtf_score = 75
            elif alignment == 'FULLY_ALIGNED_BEARISH':
                mtf_score = 0
            elif alignment == 'MOSTLY_BEARISH':
                mtf_score = 25
        
        score += mtf_score * 0.2
        
        # 4. Momentum/Volume Score (10 points max)
        momentum_score = 0
        
        # Volume confirmation
        vol_ratio = momentum.get('volume_ratio_5min', 1.0)
        if vol_ratio > 2.0:
            momentum_score += 5
        elif vol_ratio > 1.5:
            momentum_score += 3
        
        # Trend strength
        if momentum.get('trend') in ["STRONG_UP", "STRONG_DOWN"]:
            momentum_score += 5
        
        score += min(momentum_score, 10) * 0.1
        
        return min(max(score, 0), 100)  # Cap between 0-100
    
    async def _get_ai_analysis(self, opportunity: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Get AI analysis using Claude for comprehensive insights.
        
        Includes:
        - News sentiment
        - Risk assessment
        - Entry/exit strategy
        - Position sizing
        - Options vs stock analysis
        """
        symbol = opportunity['symbol']
        logger.info(f"  🤖 Getting AI analysis for {symbol}...")
        
        try:
            # Get news sentiment
            news_data = await self.news.get_headlines(symbol, max_headlines=5)
            
            # Build comprehensive prompt for Claude
            prompt = self._build_analysis_prompt(opportunity, news_data)
            
            # Get Claude's analysis
            messages = [
                {"role": "user", "content": prompt}
            ]
            response = await self.claude.analyze_stock(messages)
            
            # Parse response
            analysis = self._parse_ai_analysis(response, opportunity)
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error getting AI analysis for {symbol}: {e}")
            return None
    
    def _build_analysis_prompt(
        self,
        opportunity: Dict[str, Any],
        news_data: List[str]
    ) -> str:
        """Build comprehensive prompt for AI analysis."""
        
        symbol = opportunity['symbol']
        momentum = opportunity['momentum']
        technicals = opportunity['technicals']
        options = opportunity['options']
        
        prompt = f"""Analyze this trading opportunity and provide comprehensive insights.

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

IMPORTANT: Respond with ONLY valid JSON, no other text. Format:

{{
  "action": "BUY_STOCK|BUY_CALL|BUY_PUT|WAIT",
  "confidence": 85,
  "reasoning": "2-3 sentence explanation of why this action",
  "entry_strategy": "When and how to enter the position",
  "target_price": 495.00,
  "stop_loss": 478.00,
  "risk_level": "LOW|MEDIUM|HIGH",
  "time_horizon": "SCALP|DAY|SWING",
  "position_size_pct": 5,
  "why_not_other_options": "Why this action vs alternatives"
}}

Respond with ONLY the JSON object, no markdown, no explanation."""
        
        return prompt
    
    def _parse_ai_analysis(
        self,
        ai_response: str,
        opportunity: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Parse AI analysis response."""
        
        import json
        import re
        
        try:
            # Try to parse JSON from response
            analysis = json.loads(ai_response)
        except:
            # Try to extract JSON from markdown code blocks
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', ai_response, re.DOTALL)
            if json_match:
                try:
                    analysis = json.loads(json_match.group(1))
                except:
                    analysis = None
            else:
                # Try to find JSON object in the response
                json_match = re.search(r'\{[^{}]*"action"[^{}]*\}', ai_response, re.DOTALL)
                if json_match:
                    try:
                        analysis = json.loads(json_match.group(0))
                    except:
                        analysis = None
                else:
                    analysis = None
            
            # If still no valid JSON, use the full response as reasoning
            if not analysis:
                analysis = {
                    "action": "WAIT",
                    "confidence": 50,
                    "reasoning": ai_response[:500] if len(ai_response) > 500 else ai_response,
                    "risk_level": "HIGH"
                }
        
        # Add opportunity data
        analysis['symbol'] = opportunity['symbol']
        analysis['current_price'] = opportunity['current_price']
        analysis['momentum_score'] = opportunity['momentum_score']
        analysis['momentum'] = opportunity['momentum']
        analysis['technicals'] = opportunity['technicals']
        analysis['timestamp'] = datetime.now().isoformat()
        
        return analysis
    
    async def _generate_scan_summary(
        self,
        watchlist: List[str],
        momentum_results: Dict[str, Any],
        analyzed_opportunities: List[Dict[str, Any]],
        ai_analysis: List[Dict[str, Any]]
    ) -> str:
        """Generate human-readable scan summary."""
        
        summary = f"""
🔍 **MARKET SCAN SUMMARY**

📊 **Scan Overview:**
- Symbols Scanned: {len(watchlist)}
- Momentum Movers: {len(momentum_results['movers'])}
- Analyzed Opportunities: {len(analyzed_opportunities)}
- AI Analysis: {len(ai_analysis)}

"""
        
        if ai_analysis:
            summary += "🎯 **TOP OPPORTUNITIES:**\n\n"
            
            for i, rec in enumerate(ai_analysis[:3], 1):
                summary += f"{i}. **{rec['symbol']}** - ${rec['current_price']:.2f}\n"
                summary += f"   Action: {rec['action']} (Confidence: {rec['confidence']}%)\n"
                summary += f"   {rec['reasoning']}\n"
                summary += f"   Risk: {rec.get('risk_level', 'UNKNOWN')} | Score: {rec['momentum_score']:.0f}/100\n\n"
        else:
            summary += "⏸️ **No actionable opportunities found at this time.**\n\n"
        
        summary += "📈 **NEXT STEPS:**\n"
        if ai_analysis:
            summary += "- Review opportunities above\n"
            summary += "- Check entry strategies\n"
            summary += "- This is analysis, not financial advice\n"
            summary += "- Execute trades if conditions align\n"
        else:
            summary += "- Continue monitoring for momentum\n"
            summary += "- Wait for better setups\n"
            summary += "- Next scan in 30 minutes\n"
        
        return summary
