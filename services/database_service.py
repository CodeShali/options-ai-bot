"""
Database service for storing trade history and system state.
"""
import asyncio
import aiosqlite
from typing import List, Dict, Optional, Any
from datetime import datetime
from pathlib import Path
from loguru import logger

from config import settings


class DatabaseService:
    """Service for database operations."""
    
    def __init__(self):
        """Initialize database service."""
        self.db_path = settings.database_path
        self._ensure_db_directory()
        self._initialized = False
        logger.info(f"Database service initialized: {self.db_path}")
    
    def _ensure_db_directory(self):
        """Ensure database directory exists."""
        db_dir = Path(self.db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)
    
    async def initialize(self):
        """Initialize database schema."""
        if self._initialized:
            return
        
        async with aiosqlite.connect(self.db_path) as db:
            # Trades table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trade_id TEXT UNIQUE,
                    symbol TEXT NOT NULL,
                    action TEXT NOT NULL,
                    quantity REAL NOT NULL,
                    price REAL NOT NULL,
                    total_value REAL NOT NULL,
                    timestamp DATETIME NOT NULL,
                    order_id TEXT,
                    status TEXT,
                    notes TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Positions table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS positions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT UNIQUE NOT NULL,
                    quantity REAL NOT NULL,
                    avg_entry_price REAL NOT NULL,
                    current_price REAL,
                    cost_basis REAL NOT NULL,
                    market_value REAL,
                    unrealized_pl REAL,
                    unrealized_plpc REAL,
                    opened_at DATETIME NOT NULL,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    closed_at DATETIME,
                    status TEXT DEFAULT 'open'
                )
            """)
            
            # Analysis history table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS analysis_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    analysis_type TEXT NOT NULL,
                    recommendation TEXT,
                    confidence REAL,
                    risk_level TEXT,
                    reasoning TEXT,
                    market_data TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # System state table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS system_state (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    key TEXT UNIQUE NOT NULL,
                    value TEXT,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Daily stats table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS daily_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date DATE UNIQUE NOT NULL,
                    total_trades INTEGER DEFAULT 0,
                    winning_trades INTEGER DEFAULT 0,
                    losing_trades INTEGER DEFAULT 0,
                    total_profit_loss REAL DEFAULT 0,
                    portfolio_value REAL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create indexes
            await db.execute("CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trades(symbol)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_trades_timestamp ON trades(timestamp)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_positions_symbol ON positions(symbol)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_analysis_symbol ON analysis_history(symbol)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_analysis_timestamp ON analysis_history(timestamp)")
            
            await db.commit()
        
        self._initialized = True
        logger.info("Database schema initialized")
    
    async def record_trade(
        self,
        trade_id: str,
        symbol: str,
        action: str,
        quantity: float,
        price: float,
        order_id: Optional[str] = None,
        status: str = "completed",
        notes: Optional[str] = None
    ) -> int:
        """
        Record a trade in the database.
        
        Args:
            trade_id: Unique trade identifier
            symbol: Stock symbol
            action: Trade action (buy/sell)
            quantity: Quantity traded
            price: Price per share
            order_id: Alpaca order ID
            status: Trade status
            notes: Additional notes
            
        Returns:
            Trade record ID
        """
        await self.initialize()
        
        total_value = quantity * price
        timestamp = datetime.now().isoformat()  # Convert to string for SQLite
        
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                INSERT INTO trades (trade_id, symbol, action, quantity, price, total_value, 
                                   timestamp, order_id, status, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (trade_id, symbol, action, quantity, price, total_value, 
                  timestamp, order_id, status, notes))
            
            await db.commit()
            trade_record_id = cursor.lastrowid
        
        logger.info(f"Trade recorded: {action} {quantity} {symbol} @ ${price}")
        return trade_record_id
    
    async def update_position(
        self,
        symbol: str,
        quantity: float,
        avg_entry_price: float,
        current_price: float,
        cost_basis: float,
        market_value: float,
        unrealized_pl: float,
        unrealized_plpc: float
    ) -> None:
        """Update or insert a position."""
        await self.initialize()
        
        async with aiosqlite.connect(self.db_path) as db:
            # Check if position exists
            cursor = await db.execute(
                "SELECT id FROM positions WHERE symbol = ? AND status = 'open'",
                (symbol,)
            )
            existing = await cursor.fetchone()
            
            if existing:
                await db.execute("""
                    UPDATE positions 
                    SET quantity = ?, avg_entry_price = ?, current_price = ?,
                        cost_basis = ?, market_value = ?, unrealized_pl = ?,
                        unrealized_plpc = ?, updated_at = ?
                    WHERE symbol = ? AND status = 'open'
                """, (quantity, avg_entry_price, current_price, cost_basis,
                      market_value, unrealized_pl, unrealized_plpc,
                      datetime.now(), symbol))
            else:
                await db.execute("""
                    INSERT INTO positions (symbol, quantity, avg_entry_price, current_price,
                                         cost_basis, market_value, unrealized_pl, unrealized_plpc,
                                         opened_at, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'open')
                """, (symbol, quantity, avg_entry_price, current_price, cost_basis,
                      market_value, unrealized_pl, unrealized_plpc, datetime.now()))
            
            await db.commit()
    
    async def close_position(self, symbol: str) -> None:
        """Mark a position as closed."""
        await self.initialize()
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE positions 
                SET status = 'closed', closed_at = ?, updated_at = ?
                WHERE symbol = ? AND status = 'open'
            """, (datetime.now(), datetime.now(), symbol))
            
            await db.commit()
        
        logger.info(f"Position closed in database: {symbol}")
    
    async def get_open_positions(self) -> List[Dict[str, Any]]:
        """Get all open positions from database."""
        await self.initialize()
        
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT * FROM positions WHERE status = 'open' ORDER BY opened_at DESC
            """)
            rows = await cursor.fetchall()
            
            return [dict(row) for row in rows]
    
    async def record_analysis(
        self,
        symbol: str,
        analysis_type: str,
        recommendation: str,
        confidence: float,
        risk_level: str,
        reasoning: str,
        market_data: Optional[str] = None
    ) -> int:
        """Record an analysis in the database."""
        await self.initialize()
        
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                INSERT INTO analysis_history (symbol, analysis_type, recommendation, 
                                             confidence, risk_level, reasoning, market_data)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (symbol, analysis_type, recommendation, confidence, risk_level, 
                  reasoning, market_data))
            
            await db.commit()
            return cursor.lastrowid
    
    async def get_recent_trades(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent trades."""
        await self.initialize()
        
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT * FROM trades ORDER BY timestamp DESC LIMIT ?
            """, (limit,))
            rows = await cursor.fetchall()
            
            return [dict(row) for row in rows]
    
    async def get_trades_by_symbol(self, symbol: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get trades for a specific symbol."""
        await self.initialize()
        
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT * FROM trades WHERE symbol = ? ORDER BY timestamp DESC LIMIT ?
            """, (symbol, limit))
            rows = await cursor.fetchall()
            
            return [dict(row) for row in rows]
    
    async def get_daily_stats(self, date: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get daily statistics."""
        await self.initialize()
        
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT * FROM daily_stats WHERE date = ?
            """, (date,))
            row = await cursor.fetchone()
            
            return dict(row) if row else None
    
    async def update_daily_stats(
        self,
        date: str,
        total_trades: int,
        winning_trades: int,
        losing_trades: int,
        total_profit_loss: float,
        portfolio_value: float
    ) -> None:
        """Update daily statistics."""
        await self.initialize()
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT OR REPLACE INTO daily_stats 
                (date, total_trades, winning_trades, losing_trades, total_profit_loss, portfolio_value)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (date, total_trades, winning_trades, losing_trades, total_profit_loss, portfolio_value))
            
            await db.commit()
    
    async def set_system_state(self, key: str, value: str) -> None:
        """Set a system state value."""
        await self.initialize()
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT OR REPLACE INTO system_state (key, value, updated_at)
                VALUES (?, ?, ?)
            """, (key, value, datetime.now()))
            
            await db.commit()
    
    async def get_system_state(self, key: str) -> Optional[str]:
        """Get a system state value."""
        await self.initialize()
        
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                SELECT value FROM system_state WHERE key = ?
            """, (key,))
            row = await cursor.fetchone()
            
            return row[0] if row else None
    
    async def get_performance_metrics(self, days: int = 30) -> Dict[str, Any]:
        """Get performance metrics for the last N days."""
        await self.initialize()
        
        async with aiosqlite.connect(self.db_path) as db:
            # Total trades
            cursor = await db.execute("""
                SELECT COUNT(*) FROM trades 
                WHERE timestamp >= datetime('now', '-' || ? || ' days')
            """, (days,))
            total_trades = (await cursor.fetchone())[0]
            
            # Win rate
            cursor = await db.execute("""
                SELECT 
                    COUNT(CASE WHEN total_value > 0 THEN 1 END) as wins,
                    COUNT(CASE WHEN total_value < 0 THEN 1 END) as losses
                FROM trades 
                WHERE action = 'sell' AND timestamp >= datetime('now', '-' || ? || ' days')
            """, (days,))
            row = await cursor.fetchone()
            wins, losses = row[0], row[1]
            win_rate = (wins / (wins + losses) * 100) if (wins + losses) > 0 else 0
            
            # Total P/L
            cursor = await db.execute("""
                SELECT SUM(total_value) FROM trades 
                WHERE timestamp >= datetime('now', '-' || ? || ' days')
            """, (days,))
            total_pl = (await cursor.fetchone())[0] or 0
            
            return {
                "total_trades": total_trades,
                "winning_trades": wins,
                "losing_trades": losses,
                "win_rate": win_rate,
                "total_profit_loss": total_pl,
                "days": days
            }


# Global instance
_database_service: Optional[DatabaseService] = None


def get_database_service() -> DatabaseService:
    """Get the global database service instance."""
    global _database_service
    if _database_service is None:
        _database_service = DatabaseService()
    return _database_service


# ==================== CACHE SERVICE ====================

import time
from collections import defaultdict, deque


class CacheService:
    """In-memory cache with TTL support for Tara."""
    
    def __init__(self, default_ttl: int = 900):  # 15 minutes default
        """Initialize cache service.
        
        Args:
            default_ttl: Default time-to-live in seconds (900 = 15 minutes)
        """
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._default_ttl = default_ttl
        logger.info(f"Cache service initialized with {default_ttl}s TTL")
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache.
        
        Args:
            key: Cache key (symbol, contract_id, order_id, thread_id)
            
        Returns:
            Cached value or None if expired/not found
        """
        if key not in self._cache:
            return None
        
        entry = self._cache[key]
        
        # Check if expired
        if time.time() > entry['expires_at']:
            del self._cache[key]
            logger.debug(f"Cache expired: {key}")
            return None
        
        logger.debug(f"Cache hit: {key}")
        return entry['value']
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """Set value in cache with TTL.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (uses default if None)
        """
        ttl = ttl or self._default_ttl
        expires_at = time.time() + ttl
        
        self._cache[key] = {
            'value': value,
            'expires_at': expires_at,
            'created_at': time.time()
        }
        
        logger.debug(f"Cache set: {key} (TTL: {ttl}s)")
    
    async def delete(self, key: str):
        """Delete value from cache.
        
        Args:
            key: Cache key to delete
        """
        if key in self._cache:
            del self._cache[key]
            logger.debug(f"Cache deleted: {key}")
    
    async def exists(self, key: str) -> bool:
        """Check if key exists and is not expired.
        
        Args:
            key: Cache key
            
        Returns:
            True if key exists and valid, False otherwise
        """
        value = await self.get(key)
        return value is not None
    
    async def clear(self):
        """Clear all cache entries."""
        self._cache.clear()
        logger.info("Cache cleared")
    
    async def cleanup_expired(self):
        """Remove all expired entries."""
        now = time.time()
        expired_keys = [
            key for key, entry in self._cache.items()
            if now > entry['expires_at']
        ]
        
        for key in expired_keys:
            del self._cache[key]
        
        if expired_keys:
            logger.info(f"Cleaned up {len(expired_keys)} expired cache entries")
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics.
        
        Returns:
            Dictionary with cache stats
        """
        await self.cleanup_expired()
        
        return {
            'total_entries': len(self._cache),
            'default_ttl': self._default_ttl,
            'memory_size_estimate': len(str(self._cache))
        }
    
    # Convenience methods for specific cache keys
    async def get_position(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get cached position for symbol."""
        return await self.get(f"position:{symbol}")
    
    async def set_position(self, symbol: str, position: Dict[str, Any], ttl: Optional[int] = None):
        """Cache position for symbol."""
        await self.set(f"position:{symbol}", position, ttl)
    
    async def get_order(self, order_id: str) -> Optional[Dict[str, Any]]:
        """Get cached order."""
        return await self.get(f"order:{order_id}")
    
    async def set_order(self, order_id: str, order: Dict[str, Any], ttl: Optional[int] = None):
        """Cache order."""
        await self.set(f"order:{order_id}", order, ttl)
    
    async def get_thread_id(self, symbol: str) -> Optional[str]:
        """Get cached Discord thread ID for symbol."""
        return await self.get(f"thread:{symbol}")
    
    async def set_thread_id(self, symbol: str, thread_id: str, ttl: Optional[int] = None):
        """Cache Discord thread ID for symbol."""
        await self.set(f"thread:{symbol}", thread_id, ttl)
    
    async def get_contract(self, contract_id: str) -> Optional[Dict[str, Any]]:
        """Get cached options contract."""
        return await self.get(f"contract:{contract_id}")
    
    async def set_contract(self, contract_id: str, contract: Dict[str, Any], ttl: Optional[int] = None):
        """Cache options contract."""
        await self.set(f"contract:{contract_id}", contract, ttl)


# Global cache instance
_cache_service: Optional[CacheService] = None


def get_cache_service() -> CacheService:
    """Get global cache service instance."""
    global _cache_service
    if _cache_service is None:
        _cache_service = CacheService()
    return _cache_service


# ==================== API TRACKER ====================


class APITracker:
    """Track API calls and rate limits for Tara."""
    
    def __init__(self, rate_limit_per_minute: int = 200):
        """Initialize API tracker.
        
        Args:
            rate_limit_per_minute: Maximum API calls per minute
        """
        self.rate_limit = rate_limit_per_minute
        self.calls_today: Dict[str, int] = defaultdict(int)
        self.errors_today: Dict[str, int] = defaultdict(int)
        self.call_history: deque = deque(maxlen=100)  # Last 100 calls
        self.last_reset = datetime.now().replace(hour=0, minute=0, second=0)
        
        # Rate limiting
        self.call_times: deque = deque(maxlen=rate_limit_per_minute)
        
        logger.info(f"API Tracker initialized (limit: {rate_limit_per_minute}/min)")
    
    async def record_call(self, endpoint: str, status_code: int, latency_ms: float, 
                         provider: str = "Alpaca") -> bool:
        """Record an API call.
        
        Args:
            endpoint: API endpoint called
            status_code: HTTP status code
            latency_ms: Response time in milliseconds
            provider: API provider name
            
        Returns:
            True if call was successful, False if error
        """
        # Check if we need to reset daily counters
        await self._check_daily_reset()
        
        # Record call
        now = time.time()
        call_data = {
            'endpoint': endpoint,
            'status': status_code,
            'latency_ms': latency_ms,
            'provider': provider,
            'timestamp': now
        }
        
        self.call_history.append(call_data)
        self.call_times.append(now)
        self.calls_today[provider] += 1
        
        # Track errors
        is_error = status_code >= 400
        if is_error:
            self.errors_today[provider] += 1
            logger.warning(f"API error: {endpoint} returned {status_code}")
        
        return not is_error
    
    async def can_make_call(self) -> bool:
        """Check if we can make an API call without exceeding rate limit.
        
        Returns:
            True if call is allowed, False if rate limited
        """
        now = time.time()
        minute_ago = now - 60
        
        # Remove calls older than 1 minute
        while self.call_times and self.call_times[0] < minute_ago:
            self.call_times.popleft()
        
        # Check if we're at limit
        if len(self.call_times) >= self.rate_limit:
            logger.warning(f"Rate limit reached: {len(self.call_times)}/{self.rate_limit} calls/min")
            return False
        
        return True
    
    async def wait_if_needed(self):
        """Wait if rate limit is reached."""
        if not await self.can_make_call():
            # Wait until oldest call is more than 1 minute old
            if self.call_times:
                oldest_call = self.call_times[0]
                wait_time = 60 - (time.time() - oldest_call)
                if wait_time > 0:
                    logger.info(f"Rate limit: waiting {wait_time:.1f}s")
                    await asyncio.sleep(wait_time)
    
    async def get_status(self, provider: str = "Alpaca") -> Dict[str, Any]:
        """Get API status and metrics.
        
        Args:
            provider: API provider name
            
        Returns:
            Status dictionary with metrics
        """
        await self._check_daily_reset()
        
        # Calculate current rate
        now = time.time()
        minute_ago = now - 60
        calls_last_minute = sum(1 for t in self.call_times if t >= minute_ago)
        
        # Get recent calls
        recent_calls = list(self.call_history)[-10:]
        last_calls_formatted = [
            {
                'endpoint': call['endpoint'],
                'status': call['status'],
                'latency_ms': round(call['latency_ms'], 2)
            }
            for call in recent_calls
        ]
        
        # Calculate next reset time
        from datetime import timedelta
        tomorrow = datetime.now().replace(hour=0, minute=0, second=0) + timedelta(days=1)
        
        return {
            'provider': provider,
            'calls_today': self.calls_today[provider],
            'errors': self.errors_today[provider],
            'rate_limit_used': calls_last_minute,
            'rate_limit_total': self.rate_limit,
            'last_calls': last_calls_formatted,
            'next_reset': tomorrow.isoformat(),
            'status': 'healthy' if self.errors_today[provider] < 10 else 'degraded'
        }
    
    async def _check_daily_reset(self):
        """Reset daily counters if it's a new day."""
        now = datetime.now()
        if now.date() > self.last_reset.date():
            logger.info("Resetting daily API counters")
            self.calls_today.clear()
            self.errors_today.clear()
            self.last_reset = now.replace(hour=0, minute=0, second=0)
    
    async def get_metrics(self) -> Dict[str, Any]:
        """Get detailed metrics for all providers."""
        metrics = {}
        for provider in set(list(self.calls_today.keys()) + list(self.errors_today.keys())):
            metrics[provider] = await self.get_status(provider)
        return metrics


# Global tracker instance
_api_tracker: Optional[APITracker] = None


def get_api_tracker() -> APITracker:
    """Get global API tracker instance."""
    global _api_tracker
    if _api_tracker is None:
        _api_tracker = APITracker()
    return _api_tracker
