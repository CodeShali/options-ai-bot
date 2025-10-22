"""
News Monitor Service - Track news and events for positions in real-time.
"""
import asyncio
from typing import Dict, Any, List, Optional, Set
from datetime import datetime, timedelta
from loguru import logger
import re

from services import get_alpaca_service, get_database_service
from config import settings


class NewsMonitorService:
    """Monitor news and events for open positions."""
    
    def __init__(self):
        """Initialize news monitor service."""
        self.alpaca = get_alpaca_service()
        self.db = get_database_service()
        
        # News tracking
        self.monitored_symbols: Set[str] = set()
        self.news_history = {}  # {symbol: [news_items]}
        self.alert_callbacks = []
        
        # Sentiment keywords
        self.sentiment_keywords = {
            "very_positive": [
                "beats", "exceeds", "strong", "growth", "bullish", "upgrade", 
                "outperform", "buy", "positive", "surge", "rally", "breakthrough"
            ],
            "positive": [
                "good", "solid", "stable", "improved", "better", "gains", 
                "up", "higher", "increase", "optimistic"
            ],
            "negative": [
                "miss", "disappointing", "weak", "decline", "falls", "drops", 
                "concerns", "issues", "problems", "lower", "down"
            ],
            "very_negative": [
                "plunges", "crashes", "disaster", "terrible", "awful", "downgrade", 
                "sell", "bearish", "bankruptcy", "fraud", "investigation", "lawsuit"
            ]
        }
        
        # Event keywords
        self.event_keywords = {
            "earnings": ["earnings", "eps", "revenue", "quarterly", "q1", "q2", "q3", "q4"],
            "merger": ["merger", "acquisition", "buyout", "takeover", "deal"],
            "fda": ["fda", "approval", "drug", "clinical", "trial", "phase"],
            "guidance": ["guidance", "outlook", "forecast", "expects", "projects"],
            "dividend": ["dividend", "payout", "yield", "distribution"],
            "split": ["split", "stock split", "share split"],
            "insider": ["insider", "ceo", "cfo", "executive", "management"],
            "analyst": ["analyst", "rating", "price target", "recommendation"]
        }
    
    async def start_monitoring(self, symbols: List[str]) -> Dict[str, Any]:
        """Start monitoring news for specified symbols."""
        try:
            self.monitored_symbols.update(symbols)
            
            logger.info(f"📰 Starting news monitoring for {len(self.monitored_symbols)} symbols")
            
            # Start monitoring loop
            asyncio.create_task(self._news_monitoring_loop())
            
            return {
                "success": True,
                "symbols": list(self.monitored_symbols),
                "start_time": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error starting news monitoring: {e}")
            return {"success": False, "error": str(e)}
    
    async def monitor_position_news(self) -> Dict[str, Any]:
        """Monitor news for all current positions."""
        try:
            # Get current positions
            positions = await self.alpaca.get_positions()
            
            if not positions:
                return {
                    "positions_monitored": 0,
                    "news_alerts": [],
                    "timestamp": datetime.now().isoformat()
                }
            
            # Update monitored symbols
            position_symbols = {pos['symbol'] for pos in positions}
            self.monitored_symbols = position_symbols
            
            alerts = []
            
            for symbol in position_symbols:
                try:
                    # Get recent news (last 30 minutes)
                    news_alerts = await self._check_symbol_news(symbol, minutes=30)
                    alerts.extend(news_alerts)
                    
                except Exception as e:
                    logger.error(f"Error checking news for {symbol}: {e}")
                    continue
            
            return {
                "positions_monitored": len(position_symbols),
                "news_alerts": alerts,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error monitoring position news: {e}")
            return {
                "error": str(e),
                "positions_monitored": 0,
                "news_alerts": []
            }
    
    async def _news_monitoring_loop(self):
        """Main news monitoring loop."""
        try:
            while self.monitored_symbols:
                # Check market hours before processing news
                from datetime import datetime
                now = datetime.now()
                
                # Skip on weekends and outside market hours (9:30 AM - 4:00 PM ET)
                if now.weekday() >= 5 or now.hour < 9 or now.hour >= 16:
                    await asyncio.sleep(300)  # Wait 5 minutes during off-hours
                    continue
                
                # Check news for all monitored symbols
                for symbol in list(self.monitored_symbols):
                    try:
                        alerts = await self._check_symbol_news(symbol, minutes=5)
                        
                        # Trigger callbacks for alerts
                        for alert in alerts:
                            await self._trigger_alert_callbacks(alert)
                        
                    except Exception as e:
                        logger.error(f"Error in news loop for {symbol}: {e}")
                
                # Wait 2 minutes before next check
                await asyncio.sleep(120)
                
        except Exception as e:
            logger.error(f"Error in news monitoring loop: {e}")
    
    async def _check_symbol_news(self, symbol: str, minutes: int = 30) -> List[Dict[str, Any]]:
        """Check news for a specific symbol."""
        try:
            # Get recent news from Alpaca
            news_items = await self.alpaca.get_news(
                symbol=symbol,
                limit=20
            )
            
            if not news_items:
                return []
            
            alerts = []
            
            for news_item in news_items:
                # Skip if we've already processed this news
                if self._is_news_processed(symbol, news_item):
                    continue
                
                # Analyze news sentiment and importance
                analysis = self._analyze_news_item(news_item)
                
                # Generate alert if significant
                if analysis["is_significant"]:
                    alert = self._create_news_alert(symbol, news_item, analysis)
                    alerts.append(alert)
                
                # Store in history
                self._store_news_item(symbol, news_item, analysis)
            
            return alerts
            
        except Exception as e:
            logger.error(f"Error checking news for {symbol}: {e}")
            return []
    
    def _analyze_news_item(self, news_item: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze news item for sentiment and significance."""
        try:
            headline = news_item.get('headline', '').lower()
            summary = news_item.get('summary', '').lower()
            content = f"{headline} {summary}"
            
            # Sentiment analysis
            sentiment_score = 0
            sentiment_reasons = []
            
            # Check for sentiment keywords
            for sentiment, keywords in self.sentiment_keywords.items():
                matches = sum(1 for keyword in keywords if keyword in content)
                if matches > 0:
                    if sentiment == "very_positive":
                        sentiment_score += matches * 2
                        sentiment_reasons.append(f"Very positive: {matches} matches")
                    elif sentiment == "positive":
                        sentiment_score += matches * 1
                        sentiment_reasons.append(f"Positive: {matches} matches")
                    elif sentiment == "negative":
                        sentiment_score -= matches * 1
                        sentiment_reasons.append(f"Negative: {matches} matches")
                    elif sentiment == "very_negative":
                        sentiment_score -= matches * 2
                        sentiment_reasons.append(f"Very negative: {matches} matches")
            
            # Event detection
            events_detected = []
            for event_type, keywords in self.event_keywords.items():
                if any(keyword in content for keyword in keywords):
                    events_detected.append(event_type)
            
            # Determine significance
            is_significant = (
                abs(sentiment_score) >= 2 or  # Strong sentiment
                len(events_detected) > 0 or   # Important events
                "breaking" in content or      # Breaking news
                "alert" in content           # News alerts
            )
            
            # Classify sentiment
            if sentiment_score >= 3:
                sentiment_label = "VERY_POSITIVE"
            elif sentiment_score >= 1:
                sentiment_label = "POSITIVE"
            elif sentiment_score <= -3:
                sentiment_label = "VERY_NEGATIVE"
            elif sentiment_score <= -1:
                sentiment_label = "NEGATIVE"
            else:
                sentiment_label = "NEUTRAL"
            
            return {
                "sentiment_score": sentiment_score,
                "sentiment_label": sentiment_label,
                "sentiment_reasons": sentiment_reasons,
                "events_detected": events_detected,
                "is_significant": is_significant,
                "urgency": "HIGH" if abs(sentiment_score) >= 3 else "MEDIUM" if is_significant else "LOW"
            }
            
        except Exception as e:
            logger.error(f"Error analyzing news item: {e}")
            return {
                "sentiment_score": 0,
                "sentiment_label": "NEUTRAL",
                "sentiment_reasons": [],
                "events_detected": [],
                "is_significant": False,
                "urgency": "LOW"
            }
    
    def _create_news_alert(self, symbol: str, news_item: Dict[str, Any], analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Create news alert."""
        try:
            sentiment_label = analysis["sentiment_label"]
            events = analysis["events_detected"]
            urgency = analysis["urgency"]
            
            # Create appropriate emoji and message
            if sentiment_label == "VERY_POSITIVE":
                emoji = "🚀"
                severity = "HIGH"
            elif sentiment_label == "POSITIVE":
                emoji = "📈"
                severity = "MEDIUM"
            elif sentiment_label == "VERY_NEGATIVE":
                emoji = "💥"
                severity = "CRITICAL"
            elif sentiment_label == "NEGATIVE":
                emoji = "📉"
                severity = "HIGH"
            else:
                emoji = "📰"
                severity = "INFO"
            
            # Build message
            message = f"{emoji} {symbol}: {sentiment_label.title()} news"
            
            if events:
                message += f" ({', '.join(events)})"
            
            # Build reasoning
            reasoning = f"**News:** {news_item.get('headline', 'No headline')}\n\n"
            
            if analysis["sentiment_reasons"]:
                reasoning += f"**Sentiment Analysis:**\n"
                for reason in analysis["sentiment_reasons"]:
                    reasoning += f"• {reason}\n"
                reasoning += "\n"
            
            if events:
                reasoning += f"**Events Detected:** {', '.join(events)}\n\n"
            
            reasoning += f"**Summary:** {news_item.get('summary', 'No summary available')[:200]}..."
            
            # Determine action
            if sentiment_label in ["VERY_NEGATIVE", "NEGATIVE"]:
                action_required = "CONSIDER_EXIT"
            elif sentiment_label in ["VERY_POSITIVE", "POSITIVE"]:
                action_required = "MONITOR_FOR_CONTINUATION"
            else:
                action_required = "MONITOR"
            
            return {
                "type": "NEWS_ALERT",
                "symbol": symbol,
                "message": message,
                "reasoning": reasoning,
                "severity": severity,
                "sentiment": sentiment_label,
                "events": events,
                "urgency": urgency,
                "news_item": {
                    "headline": news_item.get('headline'),
                    "summary": news_item.get('summary'),
                    "url": news_item.get('url'),
                    "created_at": news_item.get('created_at')
                },
                "action_required": action_required,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error creating news alert: {e}")
            return {}
    
    def _is_news_processed(self, symbol: str, news_item: Dict[str, Any]) -> bool:
        """Check if news item has already been processed."""
        try:
            if symbol not in self.news_history:
                return False
            
            news_id = news_item.get('id') or news_item.get('headline', '')
            
            for stored_item in self.news_history[symbol]:
                stored_id = stored_item.get('news_item', {}).get('id') or stored_item.get('news_item', {}).get('headline', '')
                if news_id == stored_id:
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking if news processed: {e}")
            return False
    
    def _store_news_item(self, symbol: str, news_item: Dict[str, Any], analysis: Dict[str, Any]):
        """Store news item in history."""
        try:
            if symbol not in self.news_history:
                self.news_history[symbol] = []
            
            # Store news with analysis
            self.news_history[symbol].append({
                "timestamp": datetime.now(),
                "news_item": news_item,
                "analysis": analysis
            })
            
            # Keep only last 24 hours
            cutoff = datetime.now() - timedelta(hours=24)
            self.news_history[symbol] = [
                item for item in self.news_history[symbol]
                if item["timestamp"] > cutoff
            ]
            
        except Exception as e:
            logger.error(f"Error storing news item: {e}")
    
    async def check_earnings_calendar(self, symbol: str, days_ahead: int = 7) -> Dict[str, Any]:
        """Check earnings calendar for upcoming earnings."""
        try:
            # This would integrate with an earnings calendar API
            # For now, we'll return a placeholder
            
            # In a real implementation, you would:
            # 1. Call an earnings calendar API (like Alpha Vantage, FMP, etc.)
            # 2. Parse the response for the symbol
            # 3. Calculate days until earnings
            
            # Placeholder implementation
            return {
                "symbol": symbol,
                "has_earnings": False,
                "days_until": None,
                "date": None,
                "time": None,
                "note": "Earnings calendar integration needed"
            }
            
        except Exception as e:
            logger.error(f"Error checking earnings calendar: {e}")
            return {"error": str(e)}
    
    def register_alert_callback(self, callback):
        """Register callback for news alerts."""
        self.alert_callbacks.append(callback)
        logger.info(f"📰 News alert callback registered: {callback.__name__}")
    
    async def _trigger_alert_callbacks(self, alert: Dict[str, Any]):
        """Trigger all alert callbacks."""
        for callback in self.alert_callbacks:
            try:
                await callback(alert)
            except Exception as e:
                logger.error(f"Error in news alert callback: {e}")
    
    def get_news_summary(self, symbol: str, hours: int = 24) -> Dict[str, Any]:
        """Get news summary for a symbol."""
        try:
            if symbol not in self.news_history:
                return {"symbol": symbol, "news_count": 0, "news_items": []}
            
            # Filter by time
            cutoff = datetime.now() - timedelta(hours=hours)
            recent_news = [
                item for item in self.news_history[symbol]
                if item["timestamp"] > cutoff
            ]
            
            # Aggregate sentiment
            sentiments = [item["analysis"]["sentiment_score"] for item in recent_news]
            avg_sentiment = sum(sentiments) / len(sentiments) if sentiments else 0
            
            # Count events
            all_events = []
            for item in recent_news:
                all_events.extend(item["analysis"]["events_detected"])
            
            event_counts = {}
            for event in all_events:
                event_counts[event] = event_counts.get(event, 0) + 1
            
            return {
                "symbol": symbol,
                "hours": hours,
                "news_count": len(recent_news),
                "avg_sentiment": avg_sentiment,
                "sentiment_label": self._score_to_label(avg_sentiment),
                "event_counts": event_counts,
                "news_items": [
                    {
                        "headline": item["news_item"].get("headline"),
                        "sentiment": item["analysis"]["sentiment_label"],
                        "events": item["analysis"]["events_detected"],
                        "timestamp": item["timestamp"].isoformat()
                    }
                    for item in recent_news[-10:]  # Last 10 items
                ]
            }
            
        except Exception as e:
            logger.error(f"Error getting news summary: {e}")
            return {"error": str(e)}
    
    def _score_to_label(self, score: float) -> str:
        """Convert sentiment score to label."""
        if score >= 3:
            return "VERY_POSITIVE"
        elif score >= 1:
            return "POSITIVE"
        elif score <= -3:
            return "VERY_NEGATIVE"
        elif score <= -1:
            return "NEGATIVE"
        else:
            return "NEUTRAL"
    
    def get_monitoring_status(self) -> Dict[str, Any]:
        """Get current monitoring status."""
        return {
            "monitored_symbols": list(self.monitored_symbols),
            "symbols_count": len(self.monitored_symbols),
            "news_history_symbols": list(self.news_history.keys()),
            "total_news_items": sum(len(items) for items in self.news_history.values()),
            "callbacks_registered": len(self.alert_callbacks)
        }


# Singleton instance
_news_monitor_service = None

def get_news_monitor_service():
    """Get or create news monitor service."""
    global _news_monitor_service
    if _news_monitor_service is None:
        _news_monitor_service = NewsMonitorService()
    return _news_monitor_service
