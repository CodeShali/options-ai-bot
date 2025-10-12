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
        logger.info("Sentiment service initialized")
    
    def set_llm(self, llm_service):
        """Set LLM service for sentiment analysis."""
        self.llm = llm_service
    
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
            # Mock news headlines (replace with actual news API)
            mock_headlines = [
                f"{symbol} reports strong quarterly earnings",
                f"Analysts upgrade {symbol} to buy rating",
                f"{symbol} announces new product launch",
                f"Market volatility affects {symbol} stock",
                f"{symbol} CEO discusses growth strategy"
            ]
            
            # Use LLM to analyze headlines
            if self.llm:
                prompt = f"""Analyze the sentiment of these recent news headlines for {symbol}:

Headlines:
{chr(10).join(f'- {h}' for h in mock_headlines)}

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
                        "headlines": mock_headlines
                    }
                except json.JSONDecodeError:
                    # Fallback if JSON parsing fails
                    return self._mock_news_sentiment(symbol)
            else:
                return self._mock_news_sentiment(symbol)
                
        except Exception as e:
            logger.error(f"Error getting news sentiment: {e}")
            return self._mock_news_sentiment(symbol)
    
    def _mock_news_sentiment(self, symbol: str) -> Dict[str, Any]:
        """Mock news sentiment for testing."""
        import random
        score = random.uniform(-0.3, 0.7)  # Slightly positive bias
        return {
            "score": score,
            "sentiment": self._score_to_label(score),
            "themes": ["earnings", "growth", "market"],
            "impact": "MEDIUM",
            "reasoning": "Mixed news with slightly positive outlook",
            "headlines": [f"Recent news about {symbol}"]
        }
    
    async def _get_market_sentiment(self) -> Dict[str, Any]:
        """
        Get overall market sentiment.
        
        Analyzes major indices, VIX, market breadth, etc.
        """
        try:
            # Mock market indicators (replace with actual market data)
            mock_indicators = {
                "spy_change": 0.5,  # S&P 500 change %
                "vix": 15.2,  # Volatility index
                "advance_decline": 1.3,  # Advancing vs declining stocks
                "new_highs_lows": 2.1  # New highs vs new lows
            }
            
            # Calculate market sentiment score
            score = 0.0
            
            # SPY positive = bullish
            if mock_indicators["spy_change"] > 0:
                score += 0.3
            elif mock_indicators["spy_change"] < -1:
                score -= 0.3
            
            # Low VIX = bullish
            if mock_indicators["vix"] < 20:
                score += 0.2
            elif mock_indicators["vix"] > 30:
                score -= 0.3
            
            # More advances = bullish
            if mock_indicators["advance_decline"] > 1.5:
                score += 0.3
            elif mock_indicators["advance_decline"] < 0.7:
                score -= 0.3
            
            # More new highs = bullish
            if mock_indicators["new_highs_lows"] > 1.5:
                score += 0.2
            elif mock_indicators["new_highs_lows"] < 0.7:
                score -= 0.2
            
            return {
                "score": max(-1.0, min(1.0, score)),
                "sentiment": self._score_to_label(score),
                "indicators": mock_indicators,
                "reasoning": self._get_market_reasoning(score, mock_indicators)
            }
            
        except Exception as e:
            logger.error(f"Error getting market sentiment: {e}")
            return {
                "score": 0.0,
                "sentiment": "NEUTRAL",
                "indicators": {},
                "reasoning": "Unable to determine market sentiment"
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
        
        Analyzes Twitter, Reddit, StockTwits, etc.
        """
        try:
            # Mock social sentiment (replace with actual social media APIs)
            import random
            
            mentions = random.randint(100, 5000)
            score = random.uniform(-0.4, 0.6)
            
            return {
                "score": score,
                "sentiment": self._score_to_label(score),
                "mentions": mentions,
                "trending": mentions > 1000,
                "reasoning": f"{mentions} mentions with {self._score_to_label(score).lower()} sentiment"
            }
            
        except Exception as e:
            logger.error(f"Error getting social sentiment: {e}")
            return {
                "score": 0.0,
                "sentiment": "NEUTRAL",
                "mentions": 0,
                "trending": False,
                "reasoning": "Unable to determine social sentiment"
            }
    
    def _calculate_combined_sentiment(
        self,
        news: Dict[str, Any],
        market: Dict[str, Any],
        social: Dict[str, Any]
    ) -> float:
        """
        Calculate combined sentiment score.
        
        Weights:
        - News: 40%
        - Market: 35%
        - Social: 25%
        """
        news_score = news.get("score", 0.0)
        market_score = market.get("score", 0.0)
        social_score = social.get("score", 0.0)
        
        combined = (
            news_score * 0.40 +
            market_score * 0.35 +
            social_score * 0.25
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
