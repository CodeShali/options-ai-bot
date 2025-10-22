"""
Enhanced Sentiment Service - Real data, not AI fluff.

Provides:
- News sentiment analysis
- Options flow data
- Technical sentiment indicators
- Clear trading implications
"""
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from loguru import logger
from collections import Counter


class EnhancedSentimentService:
    """Enhanced sentiment analysis with real market data."""
    
    def __init__(self, alpaca_service, news_service):
        """Initialize with required services."""
        self.alpaca = alpaca_service
        self.news = news_service
        logger.info("✅ Enhanced Sentiment Service initialized")
    
    async def analyze_sentiment(self, symbol: str) -> Dict[str, Any]:
        """
        Comprehensive sentiment analysis with real data.
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Sentiment analysis with news, options, and technical data
        """
        try:
            logger.info(f"📊 Analyzing sentiment for {symbol}")
            
            # Gather all data in parallel
            news_data, options_data, technical_data, price_data = await asyncio.gather(
                self._analyze_news_sentiment(symbol),
                self._analyze_options_flow(symbol),
                self._analyze_technical_sentiment(symbol),
                self._get_price_data(symbol),
                return_exceptions=True
            )
            
            # Handle exceptions
            if isinstance(news_data, Exception):
                logger.error(f"News analysis error: {news_data}")
                news_data = {"error": str(news_data)}
            
            if isinstance(options_data, Exception):
                logger.error(f"Options analysis error: {options_data}")
                options_data = {"error": str(options_data)}
            
            if isinstance(technical_data, Exception):
                logger.error(f"Technical analysis error: {technical_data}")
                technical_data = {"error": str(technical_data)}
            
            if isinstance(price_data, Exception):
                logger.error(f"Price data error: {price_data}")
                price_data = {"error": str(price_data)}
            
            # Calculate overall sentiment
            overall_sentiment = self._calculate_overall_sentiment(
                news_data, options_data, technical_data
            )
            
            return {
                "symbol": symbol,
                "timestamp": datetime.now().isoformat(),
                "overall_sentiment": overall_sentiment,
                "news_sentiment": news_data,
                "options_flow": options_data,
                "technical_sentiment": technical_data,
                "price_data": price_data
            }
            
        except Exception as e:
            logger.error(f"Error analyzing sentiment for {symbol}: {e}")
            return {
                "symbol": symbol,
                "error": str(e),
                "overall_sentiment": {"score": 5.0, "label": "NEUTRAL", "emoji": "⚪"}
            }
    
    async def _analyze_news_sentiment(self, symbol: str) -> Dict[str, Any]:
        """Analyze news sentiment from real articles."""
        try:
            # Get news articles from last 24 hours
            articles = await self.news.get_news(symbol, days=1, max_articles=20)
            
            if not articles:
                return {
                    "available": False,
                    "reason": "No news articles found"
                }
            
            # Analyze sentiment of each article
            sentiments = []
            headlines = []
            
            for article in articles[:10]:  # Top 10
                title = article.get("title", "")
                published = article.get("publishedAt", "")
                
                # Simple sentiment analysis based on keywords
                sentiment = self._classify_headline_sentiment(title)
                sentiments.append(sentiment)
                
                # Format time
                try:
                    pub_time = datetime.fromisoformat(published.replace('Z', '+00:00'))
                    time_ago = self._format_time_ago(pub_time)
                except:
                    time_ago = "Unknown"
                
                headlines.append({
                    "title": title[:100],  # Truncate long titles
                    "sentiment": sentiment,
                    "time_ago": time_ago,
                    "url": article.get("url", "")
                })
            
            # Count sentiments
            sentiment_counts = Counter(sentiments)
            total = len(sentiments)
            
            positive_pct = (sentiment_counts.get("Bullish", 0) / total * 100) if total > 0 else 0
            neutral_pct = (sentiment_counts.get("Neutral", 0) / total * 100) if total > 0 else 0
            negative_pct = (sentiment_counts.get("Bearish", 0) / total * 100) if total > 0 else 0
            
            # Determine overall news sentiment
            if positive_pct > 50:
                overall = "Bullish"
                emoji = "🟢"
            elif negative_pct > 50:
                overall = "Bearish"
                emoji = "🔴"
            else:
                overall = "Neutral"
                emoji = "⚪"
            
            return {
                "available": True,
                "total_articles": len(articles),
                "analyzed_articles": len(sentiments),
                "positive_count": sentiment_counts.get("Bullish", 0),
                "neutral_count": sentiment_counts.get("Neutral", 0),
                "negative_count": sentiment_counts.get("Bearish", 0),
                "positive_pct": positive_pct,
                "neutral_pct": neutral_pct,
                "negative_pct": negative_pct,
                "overall": overall,
                "emoji": emoji,
                "top_headlines": headlines[:5]  # Top 5
            }
            
        except Exception as e:
            logger.error(f"Error analyzing news sentiment: {e}")
            return {
                "available": False,
                "error": str(e)
            }
    
    async def _analyze_options_flow(self, symbol: str) -> Dict[str, Any]:
        """Analyze options flow and unusual activity using REAL Alpaca data."""
        try:
            from datetime import datetime, timedelta
            
            # Get option contracts for next 30 days
            today = datetime.now()
            min_exp = (today + timedelta(days=7)).strftime("%Y-%m-%d")
            max_exp = (today + timedelta(days=30)).strftime("%Y-%m-%d")
            
            # Get REAL option contracts from Alpaca
            contracts = await self.alpaca.get_option_contracts_real(
                symbol,
                expiration_date_gte=min_exp,
                expiration_date_lte=max_exp
            )
            
            fallback_used = False
            
            if not contracts:
                logger.warning(f"No REAL options contracts found for {symbol}, attempting fallback")
                try:
                    fallback_chain = await self.alpaca.get_options_chain(symbol)
                except Exception as fallback_error:
                    fallback_chain = None
                    logger.error(f"Fallback options chain failed for {symbol}: {fallback_error}")
                
                if fallback_chain:
                    logger.info(f"Using fallback options chain for {symbol}")
                    contracts = []
                    for opt in fallback_chain.get("calls", []):
                        opt_data = {
                            "symbol": opt.get("symbol"),
                            "type": "call",
                            "strike_price": opt.get("strike"),
                            "expiration_date": opt.get("expiration")
                        }
                        contracts.append(opt_data)
                    for opt in fallback_chain.get("puts", []):
                        opt_data = {
                            "symbol": opt.get("symbol"),
                            "type": "put",
                            "strike_price": opt.get("strike"),
                            "expiration_date": opt.get("expiration")
                        }
                        contracts.append(opt_data)
                    fallback_used = True
                else:
                    return {
                        "available": False,
                        "reason": "Unable to reach Alpaca options API"
                    }
            
            logger.info(f"📊 Analyzing {len(contracts)} option contracts for {symbol}")
            
            # Get quotes with volume for each contract
            calls_with_volume = []
            puts_with_volume = []
            
            # Sample up to 50 contracts to avoid rate limits
            sample_size = min(len(contracts), 50)
            sampled_contracts = contracts[:sample_size]
            
            for contract in sampled_contracts:
                contract_symbol = contract.get("symbol")
                contract_type = contract.get("type", "call")
                strike = float(contract.get("strike_price", 0))
                
                # Try to get quote with volume
                if not fallback_used:
                    try:
                        quote = await self.alpaca.get_option_quote_with_greeks(contract_symbol)
                        if quote:
                            volume = quote.get("volume", 0)
                            iv = quote.get("implied_volatility", 0)
                            
                            contract_data = {
                                "symbol": contract_symbol,
                                "type": contract_type,
                                "strike": strike,
                                "volume": volume,
                                "implied_volatility": iv,
                                "expiration_date": contract.get("expiration_date")
                            }
                            
                            if contract_type == "call":
                                calls_with_volume.append(contract_data)
                            else:
                                puts_with_volume.append(contract_data)
                    except Exception as e:
                        logger.debug(f"Could not get quote for {contract_symbol}: {e}")
                        continue
                else:
                    # Fallback chain has no volume/IV data, use counts only
                    contract_data = {
                        "symbol": contract_symbol,
                        "type": contract_type,
                        "strike": strike,
                        "volume": 0,
                        "implied_volatility": 0,
                        "expiration_date": contract.get("expiration_date")
                    }
                    if contract_type == "call":
                        calls_with_volume.append(contract_data)
                    else:
                        puts_with_volume.append(contract_data)
            
            # Calculate call/put ratio by volume
            call_volume = sum(opt.get("volume", 0) for opt in calls_with_volume)
            put_volume = sum(opt.get("volume", 0) for opt in puts_with_volume)
            
            if call_volume == 0 and put_volume == 0:
                # No volume data, use contract count as proxy
                call_volume = len([c for c in contracts if c.get("type") == "call"])
                put_volume = len([c for c in contracts if c.get("type") == "put"])
                logger.info(f"Using contract count as proxy: {call_volume} calls, {put_volume} puts")
            
            call_put_ratio = call_volume / put_volume if put_volume > 0 else 0
            
            # Determine sentiment from ratio
            if call_put_ratio > 1.5:
                flow_sentiment = "Bullish"
                flow_emoji = "🟢"
            elif call_put_ratio < 0.7:
                flow_sentiment = "Bearish"
                flow_emoji = "🔴"
            else:
                flow_sentiment = "Neutral"
                flow_emoji = "⚪"
            
            # Find unusual activity (high volume options)
            all_options = calls_with_volume + puts_with_volume
            all_options.sort(key=lambda x: x.get("volume", 0), reverse=True)
            unusual_activity = []
            
            for opt in all_options[:3]:  # Top 3 by volume
                volume = opt.get("volume", 0)
                if volume > 100:  # Threshold for "unusual"
                    unusual_activity.append({
                        "type": opt.get("type", "unknown").upper(),
                        "strike": opt.get("strike", 0),
                        "volume": volume,
                        "expiry": opt.get("expiration_date", "Unknown")
                    })
            
            # Calculate IV Rank (simplified)
            if not fallback_used and all_options:
                avg_iv = sum(opt.get("implied_volatility", 0) for opt in all_options) / len(all_options)
                iv_rank = min(avg_iv * 100, 100)
            else:
                iv_rank = 0
            
            logger.info(f"✅ Options flow for {symbol}: C/P ratio {call_put_ratio:.2f}, {len(unusual_activity)} unusual")
            
            return {
                "available": True,
                "call_volume": call_volume,
                "put_volume": put_volume,
                "call_put_ratio": call_put_ratio,
                "sentiment": flow_sentiment,
                "emoji": flow_emoji,
                "unusual_activity": unusual_activity,
                "iv_rank": iv_rank,
                "total_options": len(contracts),
                "analyzed_options": len(all_options),
                "fallback_used": fallback_used,
                "reason": "Fallback options chain used" if fallback_used else None
            }
            
        except Exception as e:
            logger.error(f"Error analyzing options flow: {e}")
            return {
                "available": False,
                "error": str(e)
            }
    
    async def _analyze_technical_sentiment(self, symbol: str) -> Dict[str, Any]:
        """Analyze technical indicators for sentiment."""
        try:
            # Get historical bars
            bars = await self.alpaca.get_bars(symbol, timeframe="1Day", limit=200)
            
            if not bars or len(bars) < 50:
                return {
                    "available": False,
                    "reason": "Insufficient historical data"
                }
            
            # Extract closes and volumes
            closes = [bar["close"] for bar in bars]
            volumes = [bar["volume"] for bar in bars]
            current_price = closes[-1]
            
            # Calculate RSI
            rsi = self._calculate_rsi(closes, period=14)
            
            # Calculate MACD
            macd_line, signal_line = self._calculate_macd(closes)
            macd_histogram = macd_line - signal_line
            macd_bullish = macd_histogram > 0
            
            # Calculate volume trend
            recent_volume = sum(volumes[-5:]) / 5
            avg_volume = sum(volumes[-20:]) / 20
            volume_ratio = recent_volume / avg_volume if avg_volume > 0 else 1
            
            # Calculate SMAs for trend
            sma_20 = sum(closes[-20:]) / 20
            sma_50 = sum(closes[-50:]) / 50 if len(closes) >= 50 else sma_20
            sma_200 = sum(closes[-200:]) / 200 if len(closes) >= 200 else sma_50
            
            # Determine trend
            if sma_20 > sma_50 > sma_200:
                trend = "Strong Uptrend"
                trend_emoji = "🟢"
            elif sma_20 > sma_50:
                trend = "Uptrend"
                trend_emoji = "🟢"
            elif sma_20 < sma_50 < sma_200:
                trend = "Strong Downtrend"
                trend_emoji = "🔴"
            elif sma_20 < sma_50:
                trend = "Downtrend"
                trend_emoji = "🔴"
            else:
                trend = "Sideways"
                trend_emoji = "⚪"
            
            # RSI sentiment
            if rsi < 30:
                rsi_label = "Oversold"
                rsi_emoji = "🟢"
            elif rsi > 70:
                rsi_label = "Overbought"
                rsi_emoji = "🔴"
            else:
                rsi_label = "Neutral"
                rsi_emoji = "⚪"
            
            # Volume sentiment
            if volume_ratio > 1.5:
                volume_label = "Strong"
                volume_emoji = "🟢"
            elif volume_ratio > 1.0:
                volume_label = "Above Average"
                volume_emoji = "🟢"
            else:
                volume_label = "Weak"
                volume_emoji = "🔴"
            
            return {
                "available": True,
                "rsi": rsi,
                "rsi_label": rsi_label,
                "rsi_emoji": rsi_emoji,
                "macd_bullish": macd_bullish,
                "macd_histogram": macd_histogram,
                "volume_ratio": volume_ratio,
                "volume_label": volume_label,
                "volume_emoji": volume_emoji,
                "trend": trend,
                "trend_emoji": trend_emoji,
                "sma_20": sma_20,
                "sma_50": sma_50,
                "sma_200": sma_200
            }
            
        except Exception as e:
            logger.error(f"Error analyzing technical sentiment: {e}")
            return {
                "available": False,
                "error": str(e)
            }
    
    async def _get_price_data(self, symbol: str) -> Dict[str, Any]:
        """Get current price and basic stats."""
        try:
            # Get latest quote
            quote = await self.alpaca.get_latest_quote(symbol)
            
            if not quote:
                return {"available": False}
            
            current_price = quote.get("ap", 0)  # Ask price
            
            # Get bars for 52-week high/low
            bars = await self.alpaca.get_bars(symbol, timeframe="1Day", limit=252)
            
            if bars:
                highs = [bar["high"] for bar in bars]
                lows = [bar["low"] for bar in bars]
                week_52_high = max(highs)
                week_52_low = min(lows)
                
                distance_from_high = ((week_52_high - current_price) / week_52_high * 100)
                distance_from_low = ((current_price - week_52_low) / week_52_low * 100)
            else:
                week_52_high = current_price
                week_52_low = current_price
                distance_from_high = 0
                distance_from_low = 0
            
            return {
                "available": True,
                "current_price": current_price,
                "week_52_high": week_52_high,
                "week_52_low": week_52_low,
                "distance_from_high_pct": distance_from_high,
                "distance_from_low_pct": distance_from_low
            }
            
        except Exception as e:
            logger.error(f"Error getting price data: {e}")
            return {"available": False, "error": str(e)}
    
    def _calculate_overall_sentiment(
        self, 
        news_data: Dict, 
        options_data: Dict, 
        technical_data: Dict
    ) -> Dict[str, Any]:
        """Calculate overall sentiment score from all sources."""
        
        scores = []
        
        # News sentiment score (0-10)
        if news_data.get("available"):
            positive_pct = news_data.get("positive_pct", 0)
            negative_pct = news_data.get("negative_pct", 0)
            news_score = (positive_pct - negative_pct) / 10 + 5  # Scale to 0-10
            scores.append(news_score)
        
        # Options flow score (0-10)
        if options_data.get("available"):
            ratio = options_data.get("call_put_ratio", 1.0)
            # Ratio of 2.0 = score 7.5, ratio of 0.5 = score 2.5
            options_score = min(max(ratio * 2.5 + 2.5, 0), 10)
            scores.append(options_score)
        
        # Technical score (0-10)
        if technical_data.get("available"):
            rsi = technical_data.get("rsi", 50)
            macd_bullish = technical_data.get("macd_bullish", False)
            volume_ratio = technical_data.get("volume_ratio", 1.0)
            
            # RSI contribution (0-10)
            rsi_score = 10 - abs(rsi - 50) / 5  # RSI 50 = score 10, RSI 0/100 = score 0
            
            # MACD contribution
            macd_score = 7 if macd_bullish else 3
            
            # Volume contribution
            volume_score = min(volume_ratio * 5, 10)
            
            technical_score = (rsi_score + macd_score + volume_score) / 3
            scores.append(technical_score)
        
        # Calculate average score
        if scores:
            avg_score = sum(scores) / len(scores)
        else:
            avg_score = 5.0  # Neutral
        
        # Determine label and emoji
        if avg_score >= 7:
            label = "BULLISH"
            emoji = "🟢"
        elif avg_score >= 6:
            label = "SLIGHTLY BULLISH"
            emoji = "🟢"
        elif avg_score >= 4.5:
            label = "NEUTRAL"
            emoji = "⚪"
        elif avg_score >= 3:
            label = "SLIGHTLY BEARISH"
            emoji = "🔴"
        else:
            label = "BEARISH"
            emoji = "🔴"
        
        return {
            "score": round(avg_score, 1),
            "label": label,
            "emoji": emoji,
            "sources_used": len(scores)
        }
    
    def _classify_headline_sentiment(self, headline: str) -> str:
        """Simple keyword-based sentiment classification."""
        headline_lower = headline.lower()
        
        # Bullish keywords
        bullish_keywords = [
            "beat", "surge", "rally", "gain", "rise", "jump", "soar", "upgrade",
            "bullish", "positive", "growth", "profit", "record", "high", "strong",
            "outperform", "buy", "optimistic", "success", "win", "breakthrough"
        ]
        
        # Bearish keywords
        bearish_keywords = [
            "miss", "fall", "drop", "decline", "plunge", "downgrade", "bearish",
            "negative", "loss", "weak", "concern", "risk", "warning", "cut",
            "underperform", "sell", "pessimistic", "fail", "struggle", "crisis"
        ]
        
        bullish_count = sum(1 for word in bullish_keywords if word in headline_lower)
        bearish_count = sum(1 for word in bearish_keywords if word in headline_lower)
        
        if bullish_count > bearish_count:
            return "Bullish"
        elif bearish_count > bullish_count:
            return "Bearish"
        else:
            return "Neutral"
    
    def _format_time_ago(self, dt: datetime) -> str:
        """Format datetime as 'X hours ago' or 'X days ago'."""
        now = datetime.now(dt.tzinfo)
        delta = now - dt
        
        if delta.days > 0:
            return f"{delta.days}d ago"
        elif delta.seconds >= 3600:
            hours = delta.seconds // 3600
            return f"{hours}h ago"
        elif delta.seconds >= 60:
            minutes = delta.seconds // 60
            return f"{minutes}m ago"
        else:
            return "Just now"
    
    def _calculate_rsi(self, closes: List[float], period: int = 14) -> float:
        """Calculate RSI indicator."""
        if len(closes) < period + 1:
            return 50.0
        
        deltas = [closes[i] - closes[i-1] for i in range(1, len(closes))]
        gains = [d if d > 0 else 0 for d in deltas]
        losses = [-d if d < 0 else 0 for d in deltas]
        
        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return round(rsi, 1)
    
    def _calculate_macd(self, closes: List[float]) -> tuple:
        """Calculate MACD indicator."""
        if len(closes) < 26:
            return (0.0, 0.0)
        
        # Calculate EMAs
        ema_12 = self._calculate_ema(closes, 12)
        ema_26 = self._calculate_ema(closes, 26)
        
        macd_line = ema_12 - ema_26
        
        # Signal line (9-day EMA of MACD)
        # Simplified: just use average for now
        signal_line = macd_line * 0.9  # Approximation
        
        return (macd_line, signal_line)
    
    def _calculate_ema(self, closes: List[float], period: int) -> float:
        """Calculate Exponential Moving Average."""
        if len(closes) < period:
            return closes[-1]
        
        multiplier = 2 / (period + 1)
        ema = sum(closes[-period:]) / period  # Start with SMA
        
        # Apply EMA formula for recent prices
        for price in closes[-period:]:
            ema = (price * multiplier) + (ema * (1 - multiplier))
        
        return ema


# Singleton instance
_enhanced_sentiment_service = None


def get_enhanced_sentiment_service(alpaca_service=None, news_service=None):
    """Get or create enhanced sentiment service instance."""
    global _enhanced_sentiment_service
    
    if _enhanced_sentiment_service is None and alpaca_service and news_service:
        _enhanced_sentiment_service = EnhancedSentimentService(alpaca_service, news_service)
    
    return _enhanced_sentiment_service
