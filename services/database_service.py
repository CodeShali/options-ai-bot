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
        timestamp = datetime.now()
        
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
