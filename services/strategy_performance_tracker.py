"""
Strategy Performance Tracker.

Tracks performance metrics for each quantitative strategy.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from loguru import logger
from services import get_database_service


class StrategyPerformanceTracker:
    """
    Track and analyze performance of trading strategies.
    
    Metrics tracked:
    - Win rate
    - Average win/loss
    - Profit factor
    - Sharpe ratio
    - Max drawdown
    - Total trades
    """
    
    def __init__(self):
        """Initialize performance tracker."""
        self.db = get_database_service()
        self.strategy_stats = {}
        logger.info("✅ Strategy Performance Tracker initialized")
    
    async def record_trade(self, strategy_name: str, trade_data: Dict[str, Any]):
        """
        Record a trade for performance tracking.
        
        Args:
            strategy_name: Name of strategy
            trade_data: Trade details (entry, exit, pnl, etc.)
        """
        try:
            # Store in database
            await self.db.execute(
                """
                INSERT INTO strategy_trades 
                (strategy_name, symbol, entry_price, exit_price, pnl, pnl_pct, 
                 entry_time, exit_time, win, trade_data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    strategy_name,
                    trade_data.get('symbol'),
                    trade_data.get('entry_price'),
                    trade_data.get('exit_price'),
                    trade_data.get('pnl'),
                    trade_data.get('pnl_pct'),
                    trade_data.get('entry_time'),
                    trade_data.get('exit_time'),
                    1 if trade_data.get('pnl', 0) > 0 else 0,
                    str(trade_data)
                )
            )
            
            logger.info(f"📊 Recorded trade for {strategy_name}: {trade_data.get('symbol')} P&L: ${trade_data.get('pnl', 0):.2f}")
            
        except Exception as e:
            logger.error(f"Error recording trade for {strategy_name}: {e}")
    
    async def get_strategy_performance(self, strategy_name: str, 
                                      days: int = 30) -> Dict[str, Any]:
        """
        Get performance metrics for a strategy.
        
        Args:
            strategy_name: Strategy name
            days: Number of days to analyze
            
        Returns:
            Performance metrics
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            # Get all trades for strategy
            trades = await self.db.fetch_all(
                """
                SELECT * FROM strategy_trades 
                WHERE strategy_name = ? AND exit_time >= ?
                ORDER BY exit_time DESC
                """,
                (strategy_name, cutoff_date.isoformat())
            )
            
            if not trades:
                return {
                    "strategy": strategy_name,
                    "total_trades": 0,
                    "message": "No trades recorded"
                }
            
            # Calculate metrics
            total_trades = len(trades)
            wins = sum(1 for t in trades if t['win'] == 1)
            losses = total_trades - wins
            win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
            
            winning_trades = [t for t in trades if t['win'] == 1]
            losing_trades = [t for t in trades if t['win'] == 0]
            
            avg_win = sum(t['pnl'] for t in winning_trades) / len(winning_trades) if winning_trades else 0
            avg_loss = sum(t['pnl'] for t in losing_trades) / len(losing_trades) if losing_trades else 0
            
            total_pnl = sum(t['pnl'] for t in trades)
            total_win_pnl = sum(t['pnl'] for t in winning_trades)
            total_loss_pnl = abs(sum(t['pnl'] for t in losing_trades))
            
            profit_factor = (total_win_pnl / total_loss_pnl) if total_loss_pnl > 0 else 0
            
            # Calculate Sharpe ratio
            returns = [t['pnl_pct'] for t in trades if t['pnl_pct'] is not None]
            if returns:
                avg_return = sum(returns) / len(returns)
                std_return = (sum((r - avg_return) ** 2 for r in returns) / len(returns)) ** 0.5
                sharpe_ratio = (avg_return / std_return * (252 ** 0.5)) if std_return > 0 else 0
            else:
                sharpe_ratio = 0
            
            # Calculate Sortino ratio (downside deviation only)
            downside_returns = [r for r in returns if r < 0]
            if downside_returns:
                downside_std = (sum(r ** 2 for r in downside_returns) / len(downside_returns)) ** 0.5
                sortino_ratio = (avg_return / downside_std * (252 ** 0.5)) if downside_std > 0 else 0
            else:
                sortino_ratio = sharpe_ratio  # No downside, use Sharpe
            
            # Calculate Calmar ratio (return / max drawdown)
            calmar_ratio = (avg_return * 252 / max_drawdown) if max_drawdown > 0 else 0
            
            # Max drawdown
            cumulative_pnl = 0
            peak = 0
            max_drawdown = 0
            
            for trade in sorted(trades, key=lambda x: x['exit_time']):
                cumulative_pnl += trade['pnl']
                if cumulative_pnl > peak:
                    peak = cumulative_pnl
                drawdown = peak - cumulative_pnl
                if drawdown > max_drawdown:
                    max_drawdown = drawdown
            
            # Calculate additional metrics
            avg_trade_duration = 0
            if trades:
                durations = []
                for t in trades:
                    try:
                        entry = datetime.fromisoformat(t['entry_time'])
                        exit = datetime.fromisoformat(t['exit_time'])
                        duration = (exit - entry).total_seconds() / 3600  # hours
                        durations.append(duration)
                    except:
                        pass
                avg_trade_duration = sum(durations) / len(durations) if durations else 0
            
            # Risk-adjusted return
            risk_adjusted_return = (total_pnl / max_drawdown) if max_drawdown > 0 else 0
            
            return {
                "strategy": strategy_name,
                "period_days": days,
                "total_trades": total_trades,
                "wins": wins,
                "losses": losses,
                "win_rate": win_rate,
                "avg_win": avg_win,
                "avg_loss": avg_loss,
                "profit_factor": profit_factor,
                "total_pnl": total_pnl,
                "sharpe_ratio": sharpe_ratio,
                "sortino_ratio": sortino_ratio,
                "calmar_ratio": calmar_ratio,
                "max_drawdown": max_drawdown,
                "expectancy": (win_rate/100 * avg_win) + ((100-win_rate)/100 * avg_loss),
                "avg_trade_duration_hours": avg_trade_duration,
                "risk_adjusted_return": risk_adjusted_return
            }
            
        except Exception as e:
            logger.error(f"Error getting performance for {strategy_name}: {e}")
            return {"error": str(e)}
    
    async def get_all_strategies_performance(self, days: int = 30) -> List[Dict[str, Any]]:
        """
        Get performance for all strategies.
        
        Args:
            days: Number of days to analyze
            
        Returns:
            List of performance metrics
        """
        try:
            # Get unique strategy names
            strategies = await self.db.fetch_all(
                """
                SELECT DISTINCT strategy_name FROM strategy_trades
                WHERE exit_time >= ?
                """,
                ((datetime.now() - timedelta(days=days)).isoformat(),)
            )
            
            results = []
            for strategy in strategies:
                perf = await self.get_strategy_performance(strategy['strategy_name'], days)
                results.append(perf)
            
            # Sort by total P&L
            results.sort(key=lambda x: x.get('total_pnl', 0), reverse=True)
            
            return results
            
        except Exception as e:
            logger.error(f"Error getting all strategies performance: {e}")
            return []
    
    async def get_best_strategy(self, metric: str = "win_rate", days: int = 30) -> Optional[Dict[str, Any]]:
        """
        Get best performing strategy by metric.
        
        Args:
            metric: Metric to rank by (win_rate, profit_factor, sharpe_ratio, total_pnl)
            days: Number of days to analyze
            
        Returns:
            Best strategy performance
        """
        try:
            all_perf = await self.get_all_strategies_performance(days)
            
            if not all_perf:
                return None
            
            # Sort by metric
            all_perf.sort(key=lambda x: x.get(metric, 0), reverse=True)
            
            return all_perf[0] if all_perf else None
            
        except Exception as e:
            logger.error(f"Error getting best strategy: {e}")
            return None
    
    async def initialize_database(self):
        """Create strategy_trades table if it doesn't exist."""
        try:
            await self.db.execute(
                """
                CREATE TABLE IF NOT EXISTS strategy_trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    strategy_name TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    entry_price REAL,
                    exit_price REAL,
                    pnl REAL,
                    pnl_pct REAL,
                    entry_time TEXT,
                    exit_time TEXT,
                    win INTEGER,
                    trade_data TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            logger.info("✅ Strategy trades table initialized")
        except Exception as e:
            logger.error(f"Error initializing strategy trades table: {e}")


# Singleton instance
_tracker = None


def get_strategy_tracker() -> StrategyPerformanceTracker:
    """Get or create strategy tracker singleton."""
    global _tracker
    if _tracker is None:
        _tracker = StrategyPerformanceTracker()
    return _tracker
