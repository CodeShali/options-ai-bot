import sqlite3
from pathlib import Path
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict

from loguru import logger

DB_PATH = Path(__file__).parent.parent / "data" / "trading.db"


def _conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c


def init_db():
    with _conn() as c:
        c.executescript("""
            CREATE TABLE IF NOT EXISTS trades (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol      TEXT NOT NULL,
                option_type TEXT NOT NULL,
                strike      REAL NOT NULL,
                expiry      TEXT NOT NULL,
                contracts   INTEGER DEFAULT 1,
                entry_price REAL,
                exit_price  REAL,
                pnl         REAL,
                pnl_pct     REAL,
                status      TEXT DEFAULT 'open',
                entry_time  TEXT,
                exit_time   TEXT,
                reasoning   TEXT,
                confidence  INTEGER,
                order_id    TEXT
            );

            CREATE TABLE IF NOT EXISTS system_state (
                key        TEXT PRIMARY KEY,
                value      TEXT NOT NULL,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_trades_status     ON trades(status);
            CREATE INDEX IF NOT EXISTS idx_trades_entry_time ON trades(entry_time);
        """)
        for key, val in [
            ("auto_trade",      "false"),
            ("trading_mode",    "paper"),
            ("scanning_paused", "false"),
        ]:
            c.execute(
                "INSERT OR IGNORE INTO system_state (key, value) VALUES (?, ?)",
                (key, val),
            )
        c.commit()
    logger.info("Database ready at {}", DB_PATH)


# ── State ─────────────────────────────────────────────────────────────────────

def get_state(key: str) -> Optional[str]:
    with _conn() as c:
        row = c.execute("SELECT value FROM system_state WHERE key=?", (key,)).fetchone()
        return row["value"] if row else None


def set_state(key: str, value: str):
    with _conn() as c:
        c.execute(
            "INSERT OR REPLACE INTO system_state (key, value, updated_at) VALUES (?, ?, ?)",
            (key, value, datetime.now().isoformat()),
        )
        c.commit()


# ── Trades ────────────────────────────────────────────────────────────────────

def record_trade_open(
    symbol: str,
    option_type: str,
    strike: float,
    expiry: str,
    contracts: int,
    entry_price: float,
    reasoning: str,
    confidence: int,
    order_id: Optional[str] = None,
) -> int:
    with _conn() as c:
        cur = c.execute(
            """INSERT INTO trades
               (symbol, option_type, strike, expiry, contracts, entry_price,
                status, entry_time, reasoning, confidence, order_id)
               VALUES (?, ?, ?, ?, ?, ?, 'open', ?, ?, ?, ?)""",
            (symbol, option_type, strike, expiry, contracts, entry_price,
             datetime.now().isoformat(), reasoning, confidence, order_id),
        )
        c.commit()
        return cur.lastrowid


def record_trade_close(trade_id: int, exit_price: float) -> tuple:
    with _conn() as c:
        row = c.execute(
            "SELECT entry_price, contracts FROM trades WHERE id=?", (trade_id,)
        ).fetchone()
        if not row:
            return 0.0, 0.0
        pnl = (exit_price - row["entry_price"]) * row["contracts"] * 100
        pnl_pct = (exit_price - row["entry_price"]) / row["entry_price"] * 100
        c.execute(
            "UPDATE trades SET exit_price=?, pnl=?, pnl_pct=?, status='closed', exit_time=? WHERE id=?",
            (exit_price, pnl, pnl_pct, datetime.now().isoformat(), trade_id),
        )
        c.commit()
        return pnl, pnl_pct


def get_weekly_trade_count() -> int:
    monday = date.today() - timedelta(days=date.today().weekday())
    with _conn() as c:
        row = c.execute(
            "SELECT COUNT(*) AS cnt FROM trades WHERE date(entry_time) >= ? AND status != 'cancelled'",
            (monday.isoformat(),),
        ).fetchone()
        return row["cnt"]


def get_open_trades() -> List[Dict]:
    with _conn() as c:
        rows = c.execute(
            "SELECT * FROM trades WHERE status='open' ORDER BY entry_time DESC"
        ).fetchall()
        return [dict(r) for r in rows]


def get_trade_history(limit: int = 100) -> List[Dict]:
    with _conn() as c:
        rows = c.execute(
            "SELECT * FROM trades ORDER BY entry_time DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]


def get_weekly_pnl() -> float:
    monday = date.today() - timedelta(days=date.today().weekday())
    with _conn() as c:
        row = c.execute(
            "SELECT COALESCE(SUM(pnl), 0) AS total FROM trades "
            "WHERE date(entry_time) >= ? AND status='closed'",
            (monday.isoformat(),),
        ).fetchone()
        return row["total"]


def get_all_time_pnl() -> float:
    with _conn() as c:
        row = c.execute(
            "SELECT COALESCE(SUM(pnl), 0) AS total FROM trades WHERE status='closed'"
        ).fetchone()
        return row["total"]


def get_performance_stats() -> Dict:
    with _conn() as c:
        row = c.execute(
            """SELECT
                COUNT(*)                                               AS total,
                SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END)             AS wins,
                SUM(CASE WHEN pnl <= 0 THEN 1 ELSE 0 END)            AS losses,
                COALESCE(SUM(pnl), 0)                                 AS total_pnl,
                COALESCE(AVG(CASE WHEN pnl > 0 THEN pnl END), 0)     AS avg_win,
                COALESCE(AVG(CASE WHEN pnl <= 0 THEN pnl END), 0)    AS avg_loss
               FROM trades WHERE status='closed'"""
        ).fetchone()
        return dict(row)
