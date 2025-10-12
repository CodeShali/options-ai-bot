"""
Sentiment analysis service for market and news sentiment.
"""
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from loguru import logger

from config import settings


class SentimentService:
    """Service for analyzing market and news sentiment."""
    
    def __init__(self):
        """Initialize sentiment service."""
        self.llm = None  # Will be set later to avoid circular import
        self.alpaca = None  # Will be set later for market data
        self.news = None  # Will be set later for news data
        logger.info("Sentiment service initialized")
    
    def set_llm(self, llm_service):
        """Set LLM service for sentiment analysis."""
        self.llm = llm_service
    
    def set_alpaca(self, alpaca_service):
        """Set Alpaca service for market data."""
        self.alpaca = alpaca_service
    
    def set_news(self, news_service):
        """Set News service for news data."""
        self.news = news_service
    
    async def analyze_symbol_sentiment(self, symbol: str) -> Dict[str, Any]:
        """
        Analyze overall sentiment for a symbol.
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Sentiment analysis with score and reasoning
        """
        try:
            logger.info(f"Analyzing sentiment for {symbol}")
            
            # Get news sentiment
            news_sentiment = await self._get_news_sentiment(symbol)
            
            # Get market sentiment
            market_sentiment = await self._get_market_sentiment()
            
            # Get social sentiment (Twitter, Reddit, etc.)
            social_sentiment = await self._get_social_sentiment(symbol)
            
            # Combine sentiments
            combined_score = self._calculate_combined_sentiment(
                news_sentiment,
                market_sentiment,
                social_sentiment
            )
            
            # Get AI interpretation
            interpretation = await self._get_ai_interpretation(
                symbol,
                news_sentiment,
                market_sentiment,
                social_sentiment,
                combined_score
            )
            
            result = {
                "symbol": symbol,
                "overall_score": combined_score,
                "overall_sentiment": self._score_to_label(combined_score),
                "news_sentiment": news_sentiment,
                "market_sentiment": market_sentiment,
                "social_sentiment": social_sentiment,
                "interpretation": interpretation,
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info(
                f"Sentiment for {symbol}: {result['overall_sentiment']} "
                f"(score: {combined_score:.2f})"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error analyzing sentiment for {symbol}: {e}")
            return {
                "symbol": symbol,
                "overall_score": 0.0,
                "overall_sentiment": "NEUTRAL",
                "error": str(e)
            }
    
    async def _get_news_sentiment(self, symbol: str) -> Dict[str, Any]:
        """
        Get news sentiment for a symbol.
        
        Uses news APIs and AI to analyze recent news articles.
        """
        try:
            headlines = []
            data_source = "mock"
            
            # Try to get real news if available
            if self.news:
                try:
                    real_headlines = await self.news.get_headlines(symbol, max_headlines=10)
                    if real_headlines:
                        headlines = real_headlines
                        data_source = "real"
                        logger.info(f"Using {len(headlines)} real news headlines for {symbol}")
                except Exception as e:
                    logger.warning(f"Error fetching real news, using mock: {e}")
            
            # If no real news available, return neutral sentiment
            if not headlines:
                logger.warning(f"No news available for {symbol}, returning neutral sentiment")
                return {
                    "score": 0.0,
                    "sentiment": "NEUTRAL",
                    "themes": [],
                    "impact": "LOW",
                    "reasoning": "No recent news available",
                    "headlines": [],
                    "data_source": "none"
                }
            
            # Use LLM to analyze headlines
            if self.llm:
                prompt = f"""Analyze the sentiment of these recent news headlines for {symbol}:

Headlines:
{chr(10).join(f'- {h}' for h in headlines)}

Provide:
1. Overall sentiment score (-1.0 to 1.0, where -1 is very negative, 0 is neutral, 1 is very positive)
2. Key themes
3. Impact assessment

Format as JSON:
{{
    "score": <float>,
    "sentiment": "<POSITIVE|NEGATIVE|NEUTRAL>",
    "themes": ["theme1", "theme2"],
    "impact": "<HIGH|MEDIUM|LOW>",
    "reasoning": "<brief explanation>"
}}"""
                
                response = await self.llm.chat_completion(
                    [{"role": "user", "content": prompt}],
                    temperature=0.3
                )
                
                # Parse response
                import json
                try:
                    sentiment_data = json.loads(response)
                    return {
                        "score": sentiment_data.get("score", 0.0),
                        "sentiment": sentiment_data.get("sentiment", "NEUTRAL"),
                        "themes": sentiment_data.get("themes", []),
                        "impact": sentiment_data.get("impact", "MEDIUM"),
                        "reasoning": sentiment_data.get("reasoning", ""),
                        "headlines": headlines[:5],  # Show first 5
                        "data_source": data_source
                    }
                except json.JSONDecodeError:
                    # Fallback to neutral if JSON parsing fails
                    logger.warning(f"Failed to parse LLM response for {symbol}, returning neutral")
                    return {
                        "score": 0.0,
                        "sentiment": "NEUTRAL",
                        "themes": [],
                        "impact": "MEDIUM",
                        "reasoning": "Unable to analyze sentiment",
                        "headlines": headlines[:5],
                        "data_source": data_source
                    }
            else:
                # No LLM available
                logger.warning("No LLM service available for sentiment analysis")
                return {
                    "score": 0.0,
                    "sentiment": "NEUTRAL",
                    "themes": [],
                    "impact": "MEDIUM",
                    "reasoning": "LLM service not available",
                    "headlines": headlines[:5],
                    "data_source": data_source
                }
                
        except Exception as e:
            logger.error(f"Error getting news sentiment: {e}")
            return {
                "score": 0.0,
                "sentiment": "NEUTRAL",
                "themes": [],
                "impact": "LOW",
                "reasoning": f"Error: {str(e)}",
                "headlines": [],
                "data_source": "error"
            }
    
    async def _get_market_sentiment(self) -> Dict[str, Any]:
        """
        Get overall market sentiment.
        
        Analyzes major indices, VIX, market breadth, etc.
        """
        try:
            indicators = {}
            
            # Get real market data if Alpaca is available
            if self.alpaca:
                try:
                    # Get SPY (S&P 500) data
                    spy_bars = await self.alpaca.get_bars("SPY", timeframe="1Day", limit=2)
                    if spy_bars and len(spy_bars) >= 2:
                        current_spy = spy_bars[-1]
                        prev_spy = spy_bars[-2]
                        spy_change = ((current_spy['close'] - prev_spy['close']) / prev_spy['close']) * 100
                        indicators["spy_change"] = spy_change
                        indicators["spy_price"] = current_spy['close']
                    else:
                        indicators["spy_change"] = 0.0
                    
                    # Get VIX data
                    try:
                        vix_bars = await self.alpaca.get_bars("VIX", timeframe="1Day", limit=1)
                        if vix_bars:
                            indicators["vix"] = vix_bars[-1]['close']
                        else:
                            indicators["vix"] = 20.0  # Neutral default
                    except:
                        indicators["vix"] = 20.0  # Neutral default if VIX not available
                    
                    # Get QQQ (Nasdaq) for tech sentiment
                    try:
                        qqq_bars = await self.alpaca.get_bars("QQQ", timeframe="1Day", limit=2)
                        if qqq_bars and len(qqq_bars) >= 2:
                            current_qqq = qqq_bars[-1]
                            prev_qqq = qqq_bars[-2]
                            qqq_change = ((current_qqq['close'] - prev_qqq['close']) / prev_qqq['close']) * 100
                            indicators["qqq_change"] = qqq_change
                        else:
                            indicators["qqq_change"] = 0.0
                    except:
                        indicators["qqq_change"] = 0.0
                    
                    # Calculate advance/decline ratio (simplified using SPY vs QQQ)
                    if "spy_change" in indicators and "qqq_change" in indicators:
                        # If both positive, strong breadth
                        if indicators["spy_change"] > 0 and indicators["qqq_change"] > 0:
                            indicators["advance_decline"] = 1.5
                        elif indicators["spy_change"] < 0 and indicators["qqq_change"] < 0:
                            indicators["advance_decline"] = 0.5
                        else:
                            indicators["advance_decline"] = 1.0
                    else:
                        indicators["advance_decline"] = 1.0
                    
                    # Estimate new highs/lows based on momentum
                    avg_change = (indicators.get("spy_change", 0) + indicators.get("qqq_change", 0)) / 2
                    if avg_change > 1.0:
                        indicators["new_highs_lows"] = 2.0
                    elif avg_change < -1.0:
                        indicators["new_highs_lows"] = 0.5
                    else:
                        indicators["new_highs_lows"] = 1.0
                    
                    logger.info(f"Real market data: SPY {indicators.get('spy_change', 0):.2f}%, VIX {indicators.get('vix', 0):.1f}")
                    
                except Exception as e:
                    logger.error(f"Error fetching real market data: {e}")
                    # Return neutral if can't get real data
                    return {
                        "score": 0.0,
                        "sentiment": "NEUTRAL",
                        "indicators": {},
                        "reasoning": "Unable to fetch market data",
                        "data_source": "error"
                    }
            else:
                # No Alpaca service available
                logger.error("Alpaca service not available for market data")
                return {
                    "score": 0.0,
                    "sentiment": "NEUTRAL",
                    "indicators": {},
                    "reasoning": "Alpaca service not configured",
                    "data_source": "none"
                }
            
            # Calculate market sentiment score
            score = 0.0
            
            # SPY positive = bullish
            spy_change = indicators.get("spy_change", 0)
            if spy_change > 0:
                score += 0.3
            elif spy_change < -1:
                score -= 0.3
            
            # Low VIX = bullish
            vix = indicators.get("vix", 20)
            if vix < 20:
                score += 0.2
            elif vix > 30:
                score -= 0.3
            
            # More advances = bullish
            advance_decline = indicators.get("advance_decline", 1.0)
            if advance_decline > 1.5:
                score += 0.3
            elif advance_decline < 0.7:
                score -= 0.3
            
            # More new highs = bullish
            new_highs_lows = indicators.get("new_highs_lows", 1.0)
            if new_highs_lows > 1.5:
                score += 0.2
            elif new_highs_lows < 0.7:
                score -= 0.2
            
            return {
                "score": max(-1.0, min(1.0, score)),
                "sentiment": self._score_to_label(score),
                "indicators": indicators,
                "reasoning": self._get_market_reasoning(score, indicators),
                "data_source": "real" if self.alpaca else "fallback"
            }
            
        except Exception as e:
            logger.error(f"Error getting market sentiment: {e}")
            return {
                "score": 0.0,
                "sentiment": "NEUTRAL",
                "indicators": {},
                "reasoning": "Unable to determine market sentiment",
                "data_source": "error"
            }
    
    def _get_market_reasoning(self, score: float, indicators: Dict) -> str:
        """Generate reasoning for market sentiment."""
        reasons = []
        
        if indicators["spy_change"] > 0:
            reasons.append(f"Market up {indicators['spy_change']:.1f}%")
        elif indicators["spy_change"] < 0:
            reasons.append(f"Market down {abs(indicators['spy_change']):.1f}%")
        
        if indicators["vix"] < 20:
            reasons.append(f"Low volatility (VIX {indicators['vix']:.1f})")
        elif indicators["vix"] > 30:
            reasons.append(f"High volatility (VIX {indicators['vix']:.1f})")
        
        if indicators["advance_decline"] > 1.5:
            reasons.append("Strong market breadth")
        elif indicators["advance_decline"] < 0.7:
            reasons.append("Weak market breadth")
        
        return "; ".join(reasons) if reasons else "Neutral market conditions"
    
    async def _get_social_sentiment(self, symbol: str) -> Dict[str, Any]:
        """
        Get social media sentiment for a symbol.
        
        Note: Social media APIs not yet integrated.
        Returns neutral until Twitter/Reddit APIs are added.
        """
        # Social media integration is Phase 3
        # For now, return neutral to not affect trading decisions
        logger.debug(f"Social sentiment not available for {symbol} (Phase 3 feature)")
        return {
            "score": 0.0,
            "sentiment": "NEUTRAL",
            "mentions": 0,
            "trending": False,
            "reasoning": "Social media analysis not yet implemented",
            "data_source": "none"
        }
    
    def _calculate_combined_sentiment(
        self,
        news: Dict[str, Any],
        market: Dict[str, Any],
        social: Dict[str, Any]
    ) -> float:
        """
        Calculate combined sentiment score.
        
        Weights (social excluded until Phase 3):
        - News: 55% (increased from 40%)
        - Market: 45% (increased from 35%)
        - Social: 0% (not yet implemented)
        """
        news_score = news.get("score", 0.0)
        market_score = market.get("score", 0.0)
        # Social is always 0 until Phase 3
        
        combined = (
            news_score * 0.55 +
            market_score * 0.45
        )
        
        return max(-1.0, min(1.0, combined))
    
    async def _get_ai_interpretation(
        self,
        symbol: str,
        news: Dict,
        market: Dict,
        social: Dict,
        combined_score: float
    ) -> str:
        """Get AI interpretation of sentiment data."""
        try:
            if not self.llm:
                return self._basic_interpretation(combined_score)
            
            prompt = f"""Interpret the following sentiment data for {symbol}:

News Sentiment: {news.get('sentiment')} (score: {news.get('score', 0):.2f})
- {news.get('reasoning', 'N/A')}

Market Sentiment: {market.get('sentiment')} (score: {market.get('score', 0):.2f})
- {market.get('reasoning', 'N/A')}

Social Sentiment: {social.get('sentiment')} (score: {social.get('score', 0):.2f})
- {social.get('reasoning', 'N/A')}

Combined Score: {combined_score:.2f}

Provide a brief (2-3 sentences) interpretation of what this sentiment means for trading {symbol}."""
            
            interpretation = await self.llm.chat_completion(
                [{"role": "user", "content": prompt}],
                temperature=0.5
            )
            
            return interpretation.strip()
            
        except Exception as e:
            logger.error(f"Error getting AI interpretation: {e}")
            return self._basic_interpretation(combined_score)
    
    def _basic_interpretation(self, score: float) -> str:
        """Basic interpretation without AI."""
        if score > 0.5:
            return "Strong positive sentiment suggests favorable conditions for long positions."
        elif score > 0.2:
            return "Moderately positive sentiment indicates cautious optimism."
        elif score > -0.2:
            return "Neutral sentiment suggests waiting for clearer signals."
        elif score > -0.5:
            return "Moderately negative sentiment indicates caution advised."
        else:
            return "Strong negative sentiment suggests avoiding long positions."
    
    def _score_to_label(self, score: float) -> str:
        """Convert sentiment score to label."""
        if score > 0.3:
            return "POSITIVE"
        elif score < -0.3:
            return "NEGATIVE"
        else:
            return "NEUTRAL"
    
    def should_boost_confidence(self, sentiment_score: float, confidence: float) -> tuple[float, str]:
        """
        Determine if sentiment should boost or reduce confidence.
        
        Args:
            sentiment_score: Sentiment score (-1 to 1)
            confidence: Current AI confidence (0-100)
            
        Returns:
            Tuple of (adjusted_confidence, reasoning)
        """
        adjustment = 0.0
        reasoning = ""
        
        if sentiment_score > 0.5:
            adjustment = 5.0
            reasoning = "Strong positive sentiment boosts confidence"
        elif sentiment_score > 0.3:
            adjustment = 3.0
            reasoning = "Positive sentiment slightly boosts confidence"
        elif sentiment_score < -0.5:
            adjustment = -10.0
            reasoning = "Strong negative sentiment reduces confidence"
        elif sentiment_score < -0.3:
            adjustment = -5.0
            reasoning = "Negative sentiment slightly reduces confidence"
        else:
            reasoning = "Neutral sentiment, no adjustment"
        
        adjusted = max(0, min(100, confidence + adjustment))
        
        return adjusted, reasoning


# Global instance
_sentiment_service: Optional[SentimentService] = None


def get_sentiment_service() -> SentimentService:
    """Get the global sentiment service instance."""
    global _sentiment_service
    if _sentiment_service is None:
        _sentiment_service = SentimentService()
    return _sentiment_service
