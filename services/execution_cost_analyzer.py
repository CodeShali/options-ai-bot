"""
Execution Cost Analyzer - Track and analyze all trading costs.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from loguru import logger
import statistics

from services import get_database_service


class ExecutionCostAnalyzer:
    """Analyze execution costs and trading efficiency."""
    
    def __init__(self):
        """Initialize the cost analyzer."""
        self.db = get_database_service()
        self.cost_history = []
    
    async def analyze_execution_cost(
        self,
        symbol: str,
        side: str,
        quantity: int,
        expected_price: float,
        actual_price: float,
        order_type: str,
        spread: float,
        volume_traded: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Analyze execution cost for a trade.
        
        Args:
            symbol: Stock symbol
            side: 'buy' or 'sell'
            quantity: Shares/contracts traded
            expected_price: Expected price (mid, VWAP, etc.)
            actual_price: Actual fill price
            order_type: 'market' or 'limit'
            spread: Bid-ask spread at time of trade
            volume_traded: Daily volume for market impact calculation
            
        Returns:
            Cost analysis breakdown
        """
        try:
            # 1. Slippage Cost
            if side.lower() == "buy":
                slippage = actual_price - expected_price
            else:
                slippage = expected_price - actual_price
            
            slippage_cost = slippage * quantity
            slippage_pct = (slippage / expected_price * 100) if expected_price > 0 else 0
            
            # 2. Spread Cost (half-spread cost)
            spread_cost = (spread / 2) * quantity
            spread_cost_pct = (spread / 2 / expected_price * 100) if expected_price > 0 else 0
            
            # 3. Market Impact Cost (for large orders)
            market_impact_cost = 0
            market_impact_pct = 0
            
            if volume_traded and volume_traded > 0:
                participation_rate = quantity / volume_traded
                
                # Estimate market impact using square root law
                # Impact = α * (Q/V)^0.5 * σ * Price
                # Where α ≈ 0.1-0.3 for typical stocks
                if participation_rate > 0.001:  # >0.1% of daily volume
                    alpha = 0.2  # Market impact coefficient
                    volatility_estimate = spread / expected_price  # Rough volatility proxy
                    
                    market_impact_pct = alpha * (participation_rate ** 0.5) * volatility_estimate * 100
                    market_impact_cost = (market_impact_pct / 100) * expected_price * quantity
            
            # 4. Commission Cost (Alpaca is commission-free, but track for completeness)
            commission_cost = 0
            
            # 5. Total Execution Cost
            total_cost = abs(slippage_cost) + spread_cost + market_impact_cost + commission_cost
            trade_value = expected_price * quantity
            total_cost_pct = (total_cost / trade_value * 100) if trade_value > 0 else 0
            
            # 6. Opportunity Cost (if order didn't fill immediately)
            opportunity_cost = 0  # Would need to track time delays
            
            # Cost breakdown
            cost_analysis = {
                "symbol": symbol,
                "side": side,
                "quantity": quantity,
                "trade_value": trade_value,
                "expected_price": expected_price,
                "actual_price": actual_price,
                "order_type": order_type,
                "timestamp": datetime.now().isoformat(),
                
                # Cost components
                "slippage_cost": slippage_cost,
                "slippage_pct": slippage_pct,
                "spread_cost": spread_cost,
                "spread_cost_pct": spread_cost_pct,
                "market_impact_cost": market_impact_cost,
                "market_impact_pct": market_impact_pct,
                "commission_cost": commission_cost,
                "total_cost": total_cost,
                "total_cost_pct": total_cost_pct,
                
                # Efficiency metrics
                "cost_per_share": total_cost / quantity if quantity > 0 else 0,
                "cost_basis_points": total_cost_pct * 100,  # Cost in basis points
                "efficiency_score": max(0, 100 - total_cost_pct * 10),  # 0-100 score
                
                # Market conditions
                "spread": spread,
                "spread_pct": (spread / expected_price * 100) if expected_price > 0 else 0,
                "participation_rate": (quantity / volume_traded) if volume_traded else 0
            }
            
            # Store in history
            self.cost_history.append(cost_analysis)
            
            # Log cost analysis
            logger.info(
                f"💰 Cost Analysis: {symbol} {side} {quantity} shares - "
                f"Total Cost: ${total_cost:.2f} ({total_cost_pct:.3f}%), "
                f"Slippage: ${slippage_cost:.2f} ({slippage_pct:+.3f}%), "
                f"Spread: ${spread_cost:.2f}, Impact: ${market_impact_cost:.2f}"
            )
            
            # Alert on high costs
            if total_cost_pct > 0.5:  # >50 basis points
                logger.warning(f"⚠️ High execution cost: {total_cost_pct:.2f}% on {symbol}")
            
            return cost_analysis
            
        except Exception as e:
            logger.error(f"Error analyzing execution cost: {e}")
            return {}
    
    async def get_cost_summary(self, days: int = 30) -> Dict[str, Any]:
        """
        Get execution cost summary.
        
        Args:
            days: Number of days to analyze
            
        Returns:
            Cost summary statistics
        """
        try:
            # Filter recent trades
            cutoff_date = datetime.now() - timedelta(days=days)
            recent_costs = [
                cost for cost in self.cost_history
                if datetime.fromisoformat(cost['timestamp']) >= cutoff_date
            ]
            
            if not recent_costs:
                return {
                    "period_days": days,
                    "total_trades": 0,
                    "message": "No trades in period"
                }
            
            # Calculate summary statistics
            total_trades = len(recent_costs)
            total_value = sum(cost['trade_value'] for cost in recent_costs)
            total_cost = sum(cost['total_cost'] for cost in recent_costs)
            
            # Cost breakdowns
            total_slippage = sum(abs(cost['slippage_cost']) for cost in recent_costs)
            total_spread_cost = sum(cost['spread_cost'] for cost in recent_costs)
            total_impact_cost = sum(cost['market_impact_cost'] for cost in recent_costs)
            
            # Percentages
            cost_pcts = [cost['total_cost_pct'] for cost in recent_costs if cost['total_cost_pct'] > 0]
            slippage_pcts = [abs(cost['slippage_pct']) for cost in recent_costs]
            
            # Order type breakdown
            limit_orders = sum(1 for cost in recent_costs if cost['order_type'] == 'limit')
            market_orders = sum(1 for cost in recent_costs if cost['order_type'] == 'market')
            
            # Efficiency scores
            efficiency_scores = [cost['efficiency_score'] for cost in recent_costs]
            
            summary = {
                "period_days": days,
                "total_trades": total_trades,
                "total_trade_value": total_value,
                "total_execution_cost": total_cost,
                "avg_cost_per_trade": total_cost / total_trades if total_trades > 0 else 0,
                "total_cost_pct": (total_cost / total_value * 100) if total_value > 0 else 0,
                
                # Cost breakdown
                "slippage_cost": total_slippage,
                "spread_cost": total_spread_cost,
                "market_impact_cost": total_impact_cost,
                "slippage_pct_of_total": (total_slippage / total_cost * 100) if total_cost > 0 else 0,
                "spread_pct_of_total": (total_spread_cost / total_cost * 100) if total_cost > 0 else 0,
                "impact_pct_of_total": (total_impact_cost / total_cost * 100) if total_cost > 0 else 0,
                
                # Statistics
                "avg_cost_pct": statistics.mean(cost_pcts) if cost_pcts else 0,
                "median_cost_pct": statistics.median(cost_pcts) if cost_pcts else 0,
                "max_cost_pct": max(cost_pcts) if cost_pcts else 0,
                "avg_slippage_pct": statistics.mean(slippage_pcts) if slippage_pcts else 0,
                "avg_efficiency_score": statistics.mean(efficiency_scores) if efficiency_scores else 0,
                
                # Order types
                "limit_orders": limit_orders,
                "market_orders": market_orders,
                "limit_order_pct": (limit_orders / total_trades * 100) if total_trades > 0 else 0,
                
                # Cost in basis points (1 bp = 0.01%)
                "avg_cost_bps": statistics.mean(cost_pcts) * 100 if cost_pcts else 0,
                
                # Symbols traded
                "symbols_traded": len(set(cost['symbol'] for cost in recent_costs)),
                
                # Data source
                "data_source": "calculated"
            }
            
            return summary
            
        except Exception as e:
            logger.error(f"Error getting cost summary: {e}")
            return {"error": str(e)}
    
    async def get_symbol_cost_analysis(self, symbol: str, days: int = 30) -> Dict[str, Any]:
        """Get cost analysis for specific symbol."""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            symbol_costs = [
                cost for cost in self.cost_history
                if cost['symbol'] == symbol and 
                datetime.fromisoformat(cost['timestamp']) >= cutoff_date
            ]
            
            if not symbol_costs:
                return {
                    "symbol": symbol,
                    "period_days": days,
                    "trades": 0,
                    "message": "No trades for symbol in period"
                }
            
            # Calculate symbol-specific stats
            trades = len(symbol_costs)
            total_value = sum(cost['trade_value'] for cost in symbol_costs)
            total_cost = sum(cost['total_cost'] for cost in symbol_costs)
            
            cost_pcts = [cost['total_cost_pct'] for cost in symbol_costs]
            slippage_pcts = [cost['slippage_pct'] for cost in symbol_costs]
            
            return {
                "symbol": symbol,
                "period_days": days,
                "trades": trades,
                "total_value": total_value,
                "total_cost": total_cost,
                "avg_cost_pct": statistics.mean(cost_pcts),
                "median_cost_pct": statistics.median(cost_pcts),
                "avg_slippage_pct": statistics.mean([abs(s) for s in slippage_pcts]),
                "best_execution_pct": min(cost_pcts),
                "worst_execution_pct": max(cost_pcts),
                "limit_orders": sum(1 for c in symbol_costs if c['order_type'] == 'limit'),
                "market_orders": sum(1 for c in symbol_costs if c['order_type'] == 'market')
            }
            
        except Exception as e:
            logger.error(f"Error getting symbol cost analysis: {e}")
            return {"error": str(e)}
    
    def get_cost_recommendations(self, summary: Dict[str, Any]) -> List[str]:
        """
        Generate cost reduction recommendations.
        
        Args:
            summary: Cost summary from get_cost_summary()
            
        Returns:
            List of recommendations
        """
        recommendations = []
        
        try:
            avg_cost_pct = summary.get('avg_cost_pct', 0)
            limit_order_pct = summary.get('limit_order_pct', 0)
            avg_slippage_pct = summary.get('avg_slippage_pct', 0)
            
            # High cost recommendations
            if avg_cost_pct > 0.3:  # >30 basis points
                recommendations.append(
                    f"💡 High execution costs ({avg_cost_pct:.2f}%) - Consider using more limit orders"
                )
            
            # Low limit order usage
            if limit_order_pct < 50:
                recommendations.append(
                    f"💡 Only {limit_order_pct:.0f}% limit orders - Increase usage for better fills"
                )
            
            # High slippage
            if avg_slippage_pct > 0.2:
                recommendations.append(
                    f"💡 High slippage ({avg_slippage_pct:.2f}%) - Use limit orders on volatile stocks"
                )
            
            # Good performance
            if avg_cost_pct < 0.1:
                recommendations.append("✅ Excellent execution costs - Keep current strategy")
            
            # Order size recommendations
            if summary.get('market_impact_cost', 0) > summary.get('total_cost', 1) * 0.3:
                recommendations.append("💡 High market impact - Consider breaking large orders into smaller sizes")
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error generating recommendations: {e}")
            return ["Error generating recommendations"]


# Singleton instance
_cost_analyzer = None

def get_execution_cost_analyzer():
    """Get or create execution cost analyzer."""
    global _cost_analyzer
    if _cost_analyzer is None:
        _cost_analyzer = ExecutionCostAnalyzer()
    return _cost_analyzer
