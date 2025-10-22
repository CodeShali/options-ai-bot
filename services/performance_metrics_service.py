"""
Performance Metrics Service - Calculate trading performance statistics.
"""
from typing import Dict, Any, List
from datetime import datetime, timedelta
from loguru import logger
import math


class PerformanceMetricsService:
    """Service for calculating advanced performance metrics."""
    
    def __init__(self, db_service):
        """Initialize with database service."""
        self.db = db_service
    
    async def calculate_metrics(self, days: int = 30) -> Dict[str, Any]:
        """
        Calculate comprehensive performance metrics.
        
        Args:
            days: Number of days to analyze
            
        Returns:
            Dictionary with all performance metrics
        """
        try:
            # Get trades from database
            trades = await self.db.get_recent_trades(limit=1000)
            
            # Filter by date range
            cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
            recent_trades = [
                t for t in trades 
                if t.get('timestamp', '') >= cutoff_date
            ]
            
            if not recent_trades:
                return self._empty_metrics()
            
            # Calculate all metrics
            win_rate = self._calculate_win_rate(recent_trades)
            sharpe_ratio = await self._calculate_sharpe_ratio(recent_trades)
            max_drawdown = await self._calculate_max_drawdown(days)
            profit_factor = self._calculate_profit_factor(recent_trades)
            avg_win, avg_loss = self._calculate_avg_win_loss(recent_trades)
            total_pnl = self._calculate_total_pnl(recent_trades)
            
            return {
                "period_days": days,
                "total_trades": len(recent_trades),
                "win_rate": win_rate,
                "sharpe_ratio": sharpe_ratio,
                "max_drawdown": max_drawdown,
                "profit_factor": profit_factor,
                "avg_win": avg_win,
                "avg_loss": avg_loss,
                "total_pnl": total_pnl,
                "data_source": "calculated"  # ✅ Clear indicator
            }
            
        except Exception as e:
            logger.error(f"Error calculating performance metrics: {e}")
            return self._empty_metrics()
    
    def _empty_metrics(self) -> Dict[str, Any]:
        """Return empty metrics structure."""
        return {
            "period_days": 0,
            "total_trades": 0,
            "win_rate": 0.0,
            "sharpe_ratio": 0.0,
            "max_drawdown": 0.0,
            "profit_factor": 0.0,
            "avg_win": 0.0,
            "avg_loss": 0.0,
            "total_pnl": 0.0,
            "data_source": "unavailable"
        }
    
    def _calculate_win_rate(self, trades: List[Dict[str, Any]]) -> float:
        """
        Calculate win rate percentage.
        
        Returns:
            Win rate as percentage (0-100)
        """
        if not trades:
            return 0.0
        
        # Group trades by symbol to calculate P&L
        positions = {}
        for trade in trades:
            symbol = trade.get('symbol')
            action = trade.get('action')
            quantity = float(trade.get('quantity', 0))
            price = float(trade.get('price', 0))
            
            if symbol not in positions:
                positions[symbol] = {'buys': [], 'sells': []}
            
            if action == 'buy':
                positions[symbol]['buys'].append({'qty': quantity, 'price': price})
            elif action == 'sell':
                positions[symbol]['sells'].append({'qty': quantity, 'price': price})
        
        # Calculate wins and losses
        wins = 0
        losses = 0
        
        for symbol, pos in positions.items():
            if pos['sells']:
                # Calculate average buy and sell prices
                total_buy_value = sum(b['qty'] * b['price'] for b in pos['buys'])
                total_buy_qty = sum(b['qty'] for b in pos['buys'])
                avg_buy = total_buy_value / total_buy_qty if total_buy_qty > 0 else 0
                
                total_sell_value = sum(s['qty'] * s['price'] for s in pos['sells'])
                total_sell_qty = sum(s['qty'] for s in pos['sells'])
                avg_sell = total_sell_value / total_sell_qty if total_sell_qty > 0 else 0
                
                # Determine win or loss
                if avg_sell > avg_buy:
                    wins += 1
                else:
                    losses += 1
        
        total_closed = wins + losses
        win_rate = (wins / total_closed * 100) if total_closed > 0 else 0.0
        
        return round(win_rate, 2)
    
    async def _calculate_sharpe_ratio(self, trades: List[Dict[str, Any]]) -> float:
        """
        Calculate Sharpe Ratio (risk-adjusted return) using actual P&L.
        
        Sharpe Ratio = (Average Return - Risk-Free Rate) / Standard Deviation of Returns
        
        Returns:
            Sharpe ratio value
        """
        if len(trades) < 2:
            return 0.0
        
        # Group trades by symbol and date to calculate daily P&L
        daily_pnl = {}
        positions_by_date = {}
        
        for trade in trades:
            date = trade.get('timestamp', '')[:10]  # YYYY-MM-DD
            symbol = trade.get('symbol')
            action = trade.get('action')
            quantity = float(trade.get('quantity', 0))
            price = float(trade.get('price', 0))
            
            if date not in positions_by_date:
                positions_by_date[date] = {}
            if symbol not in positions_by_date[date]:
                positions_by_date[date][symbol] = {'buys': [], 'sells': []}
            
            if action == 'buy':
                positions_by_date[date][symbol]['buys'].append({'qty': quantity, 'price': price})
            elif action == 'sell':
                positions_by_date[date][symbol]['sells'].append({'qty': quantity, 'price': price})
        
        # Calculate P&L for each day
        daily_returns = []
        for date, positions in positions_by_date.items():
            day_pnl = 0
            for symbol, pos in positions.items():
                if pos['sells'] and pos['buys']:
                    buy_cost = sum(b['qty'] * b['price'] for b in pos['buys'])
                    sell_proceeds = sum(s['qty'] * s['price'] for s in pos['sells'])
                    day_pnl += (sell_proceeds - buy_cost)
            if day_pnl != 0:  # Only include days with closed positions
                daily_returns.append(day_pnl)
        
        if len(daily_returns) < 2:
            return 0.0
        
        # Calculate average return
        avg_return = sum(daily_returns) / len(daily_returns)
        
        # Calculate standard deviation
        variance = sum((r - avg_return) ** 2 for r in daily_returns) / len(daily_returns)
        std_dev = math.sqrt(variance)
        
        if std_dev == 0:
            return 0.0
        
        # Risk-free rate (assume 0.02% daily = ~5% annual)
        risk_free_rate = 0.0002
        
        # Sharpe ratio
        sharpe = (avg_return - risk_free_rate) / std_dev
        
        # Annualize (multiply by sqrt(252) for trading days)
        sharpe_annualized = sharpe * math.sqrt(252)
        
        return round(sharpe_annualized, 2)
    
    async def _calculate_max_drawdown(self, days: int) -> float:
        """
        Calculate maximum drawdown percentage.
        
        Max Drawdown = (Trough Value - Peak Value) / Peak Value * 100
        
        Returns:
            Max drawdown as percentage (negative value)
        """
        try:
            # Get equity history (would need to track this in DB)
            # For now, calculate from trades
            trades = await self.db.get_recent_trades(limit=1000)
            
            if not trades:
                return 0.0
            
            # Build equity curve
            equity = 100000.0  # Starting equity
            equity_curve = [equity]
            
            for trade in sorted(trades, key=lambda x: x.get('timestamp', '')):
                pnl = self._calculate_trade_pnl(trade)
                equity += pnl
                equity_curve.append(equity)
            
            # Calculate max drawdown
            peak = equity_curve[0]
            max_dd = 0.0
            
            for value in equity_curve:
                if value > peak:
                    peak = value
                
                drawdown = ((value - peak) / peak) * 100
                if drawdown < max_dd:
                    max_dd = drawdown
            
            return round(max_dd, 2)
            
        except Exception as e:
            logger.error(f"Error calculating max drawdown: {e}")
            return 0.0
    
    def _calculate_profit_factor(self, trades: List[Dict[str, Any]]) -> float:
        """
        Calculate profit factor by matching buys with sells.
        
        Profit Factor = Gross Profit / Gross Loss
        
        Returns:
            Profit factor (>1 is profitable)
        """
        # Group trades by symbol to calculate actual P&L
        positions = {}
        for trade in trades:
            symbol = trade.get('symbol')
            action = trade.get('action')
            quantity = float(trade.get('quantity', 0))
            price = float(trade.get('price', 0))
            
            if symbol not in positions:
                positions[symbol] = {'buys': [], 'sells': []}
            
            if action == 'buy':
                positions[symbol]['buys'].append({'qty': quantity, 'price': price})
            elif action == 'sell':
                positions[symbol]['sells'].append({'qty': quantity, 'price': price})
        
        # Calculate gross profit and loss
        gross_profit = 0.0
        gross_loss = 0.0
        
        for symbol, pos in positions.items():
            if pos['sells'] and pos['buys']:
                total_buy_cost = sum(b['qty'] * b['price'] for b in pos['buys'])
                total_sell_proceeds = sum(s['qty'] * s['price'] for s in pos['sells'])
                pnl = total_sell_proceeds - total_buy_cost
                
                if pnl > 0:
                    gross_profit += pnl
                else:
                    gross_loss += abs(pnl)
        
        if gross_loss == 0:
            return 0.0 if gross_profit == 0 else 999.99
        
        profit_factor = gross_profit / gross_loss
        
        return round(profit_factor, 2)
    
    def _calculate_avg_win_loss(self, trades: List[Dict[str, Any]]) -> tuple:
        """
        Calculate average win and average loss by matching buys with sells.
        
        Returns:
            (avg_win, avg_loss) tuple
        """
        # Group trades by symbol to calculate actual P&L
        positions = {}
        for trade in trades:
            symbol = trade.get('symbol')
            action = trade.get('action')
            quantity = float(trade.get('quantity', 0))
            price = float(trade.get('price', 0))
            
            if symbol not in positions:
                positions[symbol] = {'buys': [], 'sells': []}
            
            if action == 'buy':
                positions[symbol]['buys'].append({'qty': quantity, 'price': price})
            elif action == 'sell':
                positions[symbol]['sells'].append({'qty': quantity, 'price': price})
        
        # Calculate P&L for each closed position
        wins = []
        losses = []
        
        for symbol, pos in positions.items():
            if pos['sells'] and pos['buys']:
                # Calculate total buy cost and sell proceeds
                total_buy_cost = sum(b['qty'] * b['price'] for b in pos['buys'])
                total_sell_proceeds = sum(s['qty'] * s['price'] for s in pos['sells'])
                
                # P&L = Sell proceeds - Buy cost
                pnl = total_sell_proceeds - total_buy_cost
                
                if pnl > 0:
                    wins.append(pnl)
                elif pnl < 0:
                    losses.append(abs(pnl))
        
        avg_win = sum(wins) / len(wins) if wins else 0.0
        avg_loss = sum(losses) / len(losses) if losses else 0.0
        
        return (round(avg_win, 2), round(avg_loss, 2))
    
    def _calculate_total_pnl(self, trades: List[Dict[str, Any]]) -> float:
        """Calculate total P&L by matching buys with sells."""
        # Group trades by symbol
        positions = {}
        for trade in trades:
            symbol = trade.get('symbol')
            action = trade.get('action')
            quantity = float(trade.get('quantity', 0))
            price = float(trade.get('price', 0))
            
            if symbol not in positions:
                positions[symbol] = {'buys': [], 'sells': []}
            
            if action == 'buy':
                positions[symbol]['buys'].append({'qty': quantity, 'price': price})
            elif action == 'sell':
                positions[symbol]['sells'].append({'qty': quantity, 'price': price})
        
        # Calculate total P&L
        total_pnl = 0.0
        for symbol, pos in positions.items():
            if pos['sells'] and pos['buys']:
                buy_cost = sum(b['qty'] * b['price'] for b in pos['buys'])
                sell_proceeds = sum(s['qty'] * s['price'] for s in pos['sells'])
                total_pnl += (sell_proceeds - buy_cost)
        
        return round(total_pnl, 2)
    
    def _calculate_trade_pnl(self, trade: Dict[str, Any]) -> float:
        """Calculate P&L for a single trade."""
        action = trade.get('action')
        quantity = float(trade.get('quantity', 0))
        price = float(trade.get('price', 0))
        
        # Simplified: sell = positive, buy = negative
        if action == 'sell':
            return quantity * price
        elif action == 'buy':
            return -(quantity * price)
        
        return 0.0


# Singleton instance
_performance_service = None

def get_performance_metrics_service(db_service):
    """Get or create performance metrics service."""
    global _performance_service
    if _performance_service is None:
        _performance_service = PerformanceMetricsService(db_service)
    return _performance_service
