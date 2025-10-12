"""
News service for fetching real-time news articles.
"""
import aiohttp
from typing import Dict, Any, List
from datetime import datetime, timedelta
from loguru import logger

from config import settings


class NewsService:
    """Service for fetching news from NewsAPI."""
    
    def __init__(self):
        """Initialize news service."""
        self.api_key = settings.news_api_key
        self.enabled = settings.news_api_enabled and bool(self.api_key)
        self.base_url = "https://newsapi.org/v2"
        
        if self.enabled:
            logger.info("News service initialized with real NewsAPI")
        else:
            logger.info("News service initialized in mock mode (no API key)")
    
    async def get_news(self, symbol: str, days: int = 7, max_articles: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent news articles for a symbol.
        
        Args:
            symbol: Stock symbol
            days: Number of days to look back
            max_articles: Maximum number of articles to return
            
        Returns:
            List of news articles with title, description, url, publishedAt
        """
        if not self.enabled:
            logger.debug(f"News API disabled, returning empty list for {symbol}")
            return []
        
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            # Search for company name and ticker
            query = f"{symbol} OR ${symbol}"
            
            params = {
                "q": query,
                "from": start_date.strftime("%Y-%m-%d"),
                "to": end_date.strftime("%Y-%m-%d"),
                "apiKey": self.api_key,
                "language": "en",
                "sortBy": "relevancy",
                "pageSize": max_articles
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/everything", params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        articles = data.get("articles", [])
                        
                        logger.info(f"Fetched {len(articles)} news articles for {symbol}")
                        
                        # Format articles
                        formatted_articles = []
                        for article in articles:
                            formatted_articles.append({
                                "title": article.get("title", ""),
                                "description": article.get("description", ""),
                                "url": article.get("url", ""),
                                "publishedAt": article.get("publishedAt", ""),
                                "source": article.get("source", {}).get("name", "Unknown")
                            })
                        
                        return formatted_articles
                    
                    elif response.status == 426:
                        logger.warning("NewsAPI requires upgrade - free tier limit reached")
                        return []
                    
                    elif response.status == 401:
                        logger.error("NewsAPI authentication failed - check API key")
                        return []
                    
                    else:
                        logger.error(f"NewsAPI error: {response.status}")
                        return []
        
        except Exception as e:
            logger.error(f"Error fetching news for {symbol}: {e}")
            return []
    
    async def get_headlines(self, symbol: str, max_headlines: int = 10) -> List[str]:
        """
        Get just the headlines for a symbol.
        
        Args:
            symbol: Stock symbol
            max_headlines: Maximum number of headlines
            
        Returns:
            List of headline strings
        """
        articles = await self.get_news(symbol, days=7, max_articles=max_headlines)
        return [article["title"] for article in articles if article["title"]]


# Singleton instance
_news_service = None


def get_news_service() -> NewsService:
    """Get or create news service singleton."""
    global _news_service
    if _news_service is None:
        _news_service = NewsService()
    return _news_service
