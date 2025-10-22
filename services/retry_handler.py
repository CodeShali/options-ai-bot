"""
Retry Handler - Smart retry logic for failed orders and API calls.
"""
import asyncio
from typing import Dict, Any, Callable, Optional, List
from datetime import datetime, timedelta
from loguru import logger
import random


class RetryHandler:
    """Handle retries with exponential backoff and intelligent error handling."""
    
    def __init__(self):
        """Initialize retry handler."""
        self.retry_history = {}
        
        # Retryable error patterns
        self.retryable_errors = [
            "rate_limit",
            "timeout",
            "connection",
            "server_error",
            "503",
            "502",
            "500",
            "temporary",
            "network",
            "unavailable"
        ]
        
        # Non-retryable error patterns
        self.non_retryable_errors = [
            "insufficient_funds",
            "insufficient_buying_power",
            "invalid_symbol",
            "market_closed",
            "unauthorized",
            "forbidden",
            "invalid_request",
            "account_suspended",
            "position_not_found",
            "order_not_found"
        ]
    
    async def retry_with_backoff(
        self,
        func: Callable,
        *args,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
        retry_key: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Retry function with exponential backoff.
        
        Args:
            func: Function to retry
            max_retries: Maximum number of retry attempts
            base_delay: Base delay in seconds
            max_delay: Maximum delay in seconds
            exponential_base: Base for exponential backoff
            jitter: Add random jitter to delays
            retry_key: Key for tracking retry history
            
        Returns:
            Function result or error info
        """
        last_error = None
        retry_key = retry_key or f"{func.__name__}_{datetime.now().timestamp()}"
        
        for attempt in range(max_retries + 1):  # +1 for initial attempt
            try:
                logger.debug(f"🔄 Attempt {attempt + 1}/{max_retries + 1} for {func.__name__}")
                
                # Call the function
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)
                
                # Success - clear retry history
                if retry_key in self.retry_history:
                    del self.retry_history[retry_key]
                
                logger.debug(f"✅ Success on attempt {attempt + 1} for {func.__name__}")
                return {"success": True, "result": result, "attempts": attempt + 1}
                
            except Exception as e:
                last_error = e
                error_str = str(e).lower()
                
                logger.warning(f"❌ Attempt {attempt + 1} failed for {func.__name__}: {e}")
                
                # Check if error is retryable
                if not self._is_retryable_error(error_str):
                    logger.info(f"🚫 Non-retryable error for {func.__name__}: {e}")
                    return {
                        "success": False,
                        "error": str(e),
                        "error_type": "non_retryable",
                        "attempts": attempt + 1
                    }
                
                # Don't retry on last attempt
                if attempt >= max_retries:
                    break
                
                # Calculate delay with exponential backoff
                delay = min(
                    base_delay * (exponential_base ** attempt),
                    max_delay
                )
                
                # Add jitter to prevent thundering herd
                if jitter:
                    delay *= (0.5 + random.random() * 0.5)  # 50-100% of calculated delay
                
                # Track retry history
                if retry_key not in self.retry_history:
                    self.retry_history[retry_key] = {
                        "function": func.__name__,
                        "start_time": datetime.now(),
                        "attempts": [],
                        "total_attempts": 0
                    }
                
                self.retry_history[retry_key]["attempts"].append({
                    "attempt": attempt + 1,
                    "error": str(e),
                    "timestamp": datetime.now(),
                    "delay": delay
                })
                self.retry_history[retry_key]["total_attempts"] += 1
                
                logger.info(f"⏳ Retrying {func.__name__} in {delay:.1f}s (attempt {attempt + 2}/{max_retries + 1})")
                await asyncio.sleep(delay)
        
        # All retries exhausted
        logger.error(f"💥 All retries exhausted for {func.__name__}: {last_error}")
        return {
            "success": False,
            "error": str(last_error),
            "error_type": "retry_exhausted",
            "attempts": max_retries + 1,
            "retry_history": self.retry_history.get(retry_key, {})
        }
    
    def _is_retryable_error(self, error_str: str) -> bool:
        """Check if error is retryable."""
        # Check non-retryable first (more specific)
        for pattern in self.non_retryable_errors:
            if pattern in error_str:
                return False
        
        # Check retryable patterns
        for pattern in self.retryable_errors:
            if pattern in error_str:
                return True
        
        # Default: retry unknown errors (conservative approach)
        return True
    
    async def retry_order_execution(
        self,
        order_func: Callable,
        symbol: str,
        quantity: int,
        side: str,
        **order_kwargs
    ) -> Dict[str, Any]:
        """
        Retry order execution with order-specific logic.
        
        Args:
            order_func: Order execution function
            symbol: Stock symbol
            quantity: Order quantity
            side: 'buy' or 'sell'
            
        Returns:
            Order execution result
        """
        retry_key = f"order_{symbol}_{side}_{quantity}"
        
        # Custom retry parameters for orders
        max_retries = 3
        base_delay = 2.0  # Longer delay for orders
        
        # Special handling for different order types
        if "limit" in order_func.__name__.lower():
            max_retries = 2  # Fewer retries for limit orders
            base_delay = 5.0  # Longer delay
        elif "market" in order_func.__name__.lower():
            max_retries = 3  # More retries for market orders
            base_delay = 1.0  # Shorter delay
        
        result = await self.retry_with_backoff(
            order_func,
            symbol=symbol,
            quantity=quantity,
            side=side,
            max_retries=max_retries,
            base_delay=base_delay,
            retry_key=retry_key,
            **order_kwargs
        )
        
        # Add order-specific metadata
        if result["success"]:
            result["order_retry_info"] = {
                "symbol": symbol,
                "quantity": quantity,
                "side": side,
                "retry_key": retry_key
            }
        
        return result
    
    async def retry_api_call(
        self,
        api_func: Callable,
        api_name: str,
        *args,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Retry API call with API-specific logic.
        
        Args:
            api_func: API function to call
            api_name: Name of API for logging
            
        Returns:
            API call result
        """
        retry_key = f"api_{api_name}_{datetime.now().timestamp()}"
        
        # API-specific retry parameters
        if "quote" in api_name.lower() or "price" in api_name.lower():
            # Price/quote APIs - retry quickly
            max_retries = 2
            base_delay = 0.5
        elif "order" in api_name.lower():
            # Order APIs - be more patient
            max_retries = 3
            base_delay = 2.0
        elif "position" in api_name.lower():
            # Position APIs - moderate retry
            max_retries = 2
            base_delay = 1.0
        else:
            # Default API retry
            max_retries = 2
            base_delay = 1.0
        
        return await self.retry_with_backoff(
            api_func,
            *args,
            max_retries=max_retries,
            base_delay=base_delay,
            retry_key=retry_key,
            **kwargs
        )
    
    def get_retry_stats(self, hours: int = 24) -> Dict[str, Any]:
        """Get retry statistics for the last N hours."""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        recent_retries = {
            key: history for key, history in self.retry_history.items()
            if history["start_time"] >= cutoff_time
        }
        
        if not recent_retries:
            return {
                "period_hours": hours,
                "total_retry_sessions": 0,
                "message": "No retries in period"
            }
        
        # Calculate statistics
        total_sessions = len(recent_retries)
        total_attempts = sum(h["total_attempts"] for h in recent_retries.values())
        
        # Function breakdown
        function_counts = {}
        for history in recent_retries.values():
            func_name = history["function"]
            function_counts[func_name] = function_counts.get(func_name, 0) + 1
        
        # Error patterns
        error_patterns = {}
        for history in recent_retries.values():
            for attempt in history["attempts"]:
                error = attempt["error"].lower()
                # Find matching pattern
                for pattern in self.retryable_errors + self.non_retryable_errors:
                    if pattern in error:
                        error_patterns[pattern] = error_patterns.get(pattern, 0) + 1
                        break
        
        return {
            "period_hours": hours,
            "total_retry_sessions": total_sessions,
            "total_retry_attempts": total_attempts,
            "avg_attempts_per_session": total_attempts / total_sessions if total_sessions > 0 else 0,
            "function_breakdown": function_counts,
            "error_patterns": error_patterns,
            "most_retried_function": max(function_counts.items(), key=lambda x: x[1])[0] if function_counts else None,
            "most_common_error": max(error_patterns.items(), key=lambda x: x[1])[0] if error_patterns else None
        }
    
    def clear_old_retry_history(self, hours: int = 24):
        """Clear retry history older than N hours."""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        old_keys = [
            key for key, history in self.retry_history.items()
            if history["start_time"] < cutoff_time
        ]
        
        for key in old_keys:
            del self.retry_history[key]
        
        if old_keys:
            logger.info(f"🧹 Cleared {len(old_keys)} old retry history entries")
    
    def get_retry_recommendations(self, stats: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on retry statistics."""
        recommendations = []
        
        try:
            total_sessions = stats.get("total_retry_sessions", 0)
            avg_attempts = stats.get("avg_attempts_per_session", 0)
            most_retried = stats.get("most_retried_function")
            most_common_error = stats.get("most_common_error")
            
            if total_sessions == 0:
                recommendations.append("✅ No retries needed - system running smoothly")
                return recommendations
            
            if avg_attempts > 2.5:
                recommendations.append(f"⚠️ High retry rate ({avg_attempts:.1f} avg) - investigate root causes")
            
            if most_retried:
                recommendations.append(f"🔍 Most retried function: {most_retried} - may need optimization")
            
            if most_common_error:
                if "rate_limit" in most_common_error:
                    recommendations.append("💡 Rate limiting detected - consider longer delays between calls")
                elif "timeout" in most_common_error:
                    recommendations.append("💡 Timeouts detected - consider increasing timeout values")
                elif "connection" in most_common_error:
                    recommendations.append("💡 Connection issues - check network stability")
                elif "server_error" in most_common_error:
                    recommendations.append("💡 Server errors - may be temporary API issues")
            
            if total_sessions > 10:
                recommendations.append("📊 High retry volume - monitor system health")
            elif total_sessions < 3:
                recommendations.append("✅ Low retry volume - system stable")
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error generating retry recommendations: {e}")
            return ["Error generating recommendations"]


# Singleton instance
_retry_handler = None

def get_retry_handler():
    """Get or create retry handler."""
    global _retry_handler
    if _retry_handler is None:
        _retry_handler = RetryHandler()
    return _retry_handler
