"""
Market Hours Service - Handle regular and extended trading hours.
"""
from typing import Dict, Any, Optional
from datetime import datetime, time, timedelta
import pytz
from loguru import logger

from config import settings


class MarketHoursService:
    """Service to handle market hours and extended trading sessions."""
    
    def __init__(self):
        """Initialize market hours service."""
        self.eastern = pytz.timezone('America/New_York')
        
        # Regular market hours (ET)
        self.regular_open = time(9, 30)   # 9:30 AM
        self.regular_close = time(16, 0)  # 4:00 PM
        
        # Extended hours (ET)
        self.premarket_open = time(4, 0)   # 4:00 AM
        self.premarket_close = time(9, 30) # 9:30 AM
        self.afterhours_open = time(16, 0) # 4:00 PM
        self.afterhours_close = time(20, 0) # 8:00 PM
        
        # Market holidays (simplified - would use real holiday calendar)
        self.holidays_2025 = [
            "2025-01-01",  # New Year's Day
            "2025-01-20",  # MLK Day
            "2025-02-17",  # Presidents Day
            "2025-04-18",  # Good Friday
            "2025-05-26",  # Memorial Day
            "2025-06-19",  # Juneteenth
            "2025-07-04",  # Independence Day
            "2025-09-01",  # Labor Day
            "2025-11-27",  # Thanksgiving
            "2025-12-25",  # Christmas
        ]
    
    def get_current_market_status(self) -> Dict[str, Any]:
        """
        Get current market status.
        
        Returns:
            Market status information
        """
        try:
            now_et = datetime.now(self.eastern)
            current_time = now_et.time()
            current_date = now_et.date()
            weekday = now_et.weekday()  # 0=Monday, 6=Sunday
            
            # Check if it's a weekend
            is_weekend = weekday >= 5  # Saturday=5, Sunday=6
            
            # Check if it's a holiday
            is_holiday = current_date.isoformat() in self.holidays_2025
            
            # Determine market session
            session = "closed"
            session_description = "Market Closed"
            next_session = None
            next_session_time = None
            
            if is_weekend or is_holiday:
                session = "closed"
                session_description = "Weekend" if is_weekend else "Holiday"
                # Calculate next trading day
                next_session, next_session_time = self._get_next_trading_session(now_et)
                
            elif self.regular_open <= current_time < self.regular_close:
                session = "regular"
                session_description = "Regular Trading Hours"
                next_session = "after_hours"
                next_session_time = self._combine_date_time(current_date, self.afterhours_open)
                
            elif settings.extended_hours_trading:
                if self.premarket_open <= current_time < self.premarket_close:
                    session = "pre_market"
                    session_description = "Pre-Market Trading"
                    next_session = "regular"
                    next_session_time = self._combine_date_time(current_date, self.regular_open)
                    
                elif self.afterhours_open <= current_time < self.afterhours_close:
                    session = "after_hours"
                    session_description = "After-Hours Trading"
                    next_session = "pre_market"
                    # Next pre-market is tomorrow
                    tomorrow = current_date + timedelta(days=1)
                    next_session_time = self._combine_date_time(tomorrow, self.premarket_open)
                    
                else:
                    session = "closed"
                    session_description = "Extended Hours Closed"
                    next_session, next_session_time = self._get_next_trading_session(now_et)
            else:
                session = "closed"
                session_description = "Market Closed (Extended Hours Disabled)"
                next_session, next_session_time = self._get_next_trading_session(now_et)
            
            # Calculate time until next session
            time_until_next = None
            if next_session_time:
                time_until_next = next_session_time - now_et
                if time_until_next.total_seconds() < 0:
                    # Next session is tomorrow or later
                    time_until_next = None
            
            return {
                "current_time_et": now_et.strftime("%Y-%m-%d %H:%M:%S %Z"),
                "session": session,
                "session_description": session_description,
                "is_trading_hours": session in ["regular", "pre_market", "after_hours"],
                "is_regular_hours": session == "regular",
                "is_extended_hours": session in ["pre_market", "after_hours"],
                "extended_hours_enabled": settings.extended_hours_trading,
                "is_weekend": is_weekend,
                "is_holiday": is_holiday,
                "next_session": next_session,
                "next_session_time": next_session_time.strftime("%Y-%m-%d %H:%M:%S %Z") if next_session_time else None,
                "time_until_next": str(time_until_next).split(".")[0] if time_until_next else None,
                "can_trade": self._can_trade_now(session)
            }
            
        except Exception as e:
            logger.error(f"Error getting market status: {e}")
            return {
                "session": "unknown",
                "session_description": "Error determining market status",
                "is_trading_hours": False,
                "can_trade": False,
                "error": str(e)
            }
    
    def _can_trade_now(self, session: str) -> bool:
        """Determine if trading is allowed in current session."""
        if settings.test_mode:
            return True  # Always allow trading in test mode
        
        if session == "regular":
            return True  # Always allow regular hours trading
        
        if session in ["pre_market", "after_hours"]:
            return settings.extended_hours_trading
        
        return False  # Closed sessions
    
    def _get_next_trading_session(self, current_time: datetime) -> tuple:
        """Get the next trading session and time."""
        current_date = current_time.date()
        current_weekday = current_time.weekday()
        
        # If it's Friday after hours or weekend, next session is Monday pre-market
        if current_weekday == 4 and current_time.time() >= self.afterhours_close:  # Friday after 8 PM
            next_monday = current_date + timedelta(days=3)  # Friday + 3 = Monday
            if settings.extended_hours_trading:
                return "pre_market", self._combine_date_time(next_monday, self.premarket_open)
            else:
                return "regular", self._combine_date_time(next_monday, self.regular_open)
                
        elif current_weekday >= 5:  # Weekend
            days_until_monday = 7 - current_weekday  # Saturday=1 day, Sunday=0 days
            next_monday = current_date + timedelta(days=days_until_monday)
            if settings.extended_hours_trading:
                return "pre_market", self._combine_date_time(next_monday, self.premarket_open)
            else:
                return "regular", self._combine_date_time(next_monday, self.regular_open)
        
        # Weekday - determine next session
        current_time_only = current_time.time()
        
        if settings.extended_hours_trading:
            if current_time_only < self.premarket_open:
                return "pre_market", self._combine_date_time(current_date, self.premarket_open)
            elif current_time_only < self.regular_open:
                return "regular", self._combine_date_time(current_date, self.regular_open)
            elif current_time_only < self.afterhours_open:
                return "after_hours", self._combine_date_time(current_date, self.afterhours_open)
            elif current_time_only < self.afterhours_close:
                # Next day pre-market
                tomorrow = current_date + timedelta(days=1)
                return "pre_market", self._combine_date_time(tomorrow, self.premarket_open)
        else:
            if current_time_only < self.regular_open:
                return "regular", self._combine_date_time(current_date, self.regular_open)
            else:
                # Next day regular hours
                tomorrow = current_date + timedelta(days=1)
                return "regular", self._combine_date_time(tomorrow, self.regular_open)
        
        return None, None
    
    def _combine_date_time(self, date, time_obj) -> datetime:
        """Combine date and time into timezone-aware datetime."""
        dt = datetime.combine(date, time_obj)
        return self.eastern.localize(dt)
    
    def should_scan_now(self) -> Dict[str, Any]:
        """
        Determine if scanning should occur now.
        
        Returns:
            Scan decision with reasoning
        """
        status = self.get_current_market_status()
        
        if settings.test_mode:
            return {
                "should_scan": True,
                "reason": "Test mode - scanning enabled",
                "session": status["session"]
            }
        
        if status["session"] == "regular":
            return {
                "should_scan": True,
                "reason": "Regular trading hours",
                "session": "regular"
            }
        
        if status["session"] in ["pre_market", "after_hours"] and settings.extended_hours_trading:
            return {
                "should_scan": True,
                "reason": f"Extended hours trading enabled ({status['session_description']})",
                "session": status["session"]
            }
        
        return {
            "should_scan": False,
            "reason": status["session_description"],
            "session": status["session"],
            "next_scan_time": status.get("next_session_time")
        }
    
    def get_trading_session_info(self) -> Dict[str, Any]:
        """Get detailed trading session information."""
        status = self.get_current_market_status()
        
        return {
            "current_session": status["session"],
            "session_description": status["session_description"],
            "trading_allowed": status["can_trade"],
            "regular_hours": {
                "open": self.regular_open.strftime("%H:%M"),
                "close": self.regular_close.strftime("%H:%M"),
                "active": status["is_regular_hours"]
            },
            "extended_hours": {
                "enabled": settings.extended_hours_trading,
                "pre_market": {
                    "open": self.premarket_open.strftime("%H:%M"),
                    "close": self.premarket_close.strftime("%H:%M"),
                    "active": status["session"] == "pre_market"
                },
                "after_hours": {
                    "open": self.afterhours_open.strftime("%H:%M"),
                    "close": self.afterhours_close.strftime("%H:%M"),
                    "active": status["session"] == "after_hours"
                }
            },
            "next_session": {
                "type": status.get("next_session"),
                "time": status.get("next_session_time"),
                "countdown": status.get("time_until_next")
            }
        }
    
    def format_market_status_message(self) -> str:
        """Format market status for Discord/logging."""
        status = self.get_current_market_status()
        
        emoji_map = {
            "regular": "🟢",
            "pre_market": "🟡",
            "after_hours": "🟠",
            "closed": "🔴"
        }
        
        emoji = emoji_map.get(status["session"], "⚪")
        
        message = f"{emoji} **{status['session_description']}**"
        
        if status["can_trade"]:
            message += " - Trading Active"
        else:
            message += " - Trading Suspended"
        
        if status.get("next_session_time"):
            message += f"\n📅 Next: {status['next_session']} at {status['next_session_time']}"
            if status.get("time_until_next"):
                message += f" (in {status['time_until_next']})"
        
        if settings.extended_hours_trading:
            message += "\n✅ Extended hours enabled"
        else:
            message += "\n⏸️ Extended hours disabled"
        
        return message


# Singleton instance
_market_hours_service = None

def get_market_hours_service():
    """Get or create market hours service."""
    global _market_hours_service
    if _market_hours_service is None:
        _market_hours_service = MarketHoursService()
    return _market_hours_service
