"""
Strategy Manager.

Manages all trading strategies and provides unified interface.
"""
from typing import Dict, Any, List, Optional
from loguru import logger

from .mean_reversion import MeanReversionStrategy
from .momentum_breakout import MomentumBreakoutStrategy
from .ma_crossover import MACrossoverStrategy
from .iron_condor import IronCondorStrategy


class StrategyManager:
    """
    Manages all trading strategies.
    
    Provides unified interface for strategy analysis and execution.
    """
    
    def __init__(self):
        """Initialize all strategies."""
        self.strategies = {
            "mean_reversion": MeanReversionStrategy(),
            "momentum_breakout": MomentumBreakoutStrategy(),
            "ma_crossover": MACrossoverStrategy(),
            "iron_condor": IronCondorStrategy()
        }
        
        self.active_strategies = ["mean_reversion", "momentum_breakout", "ma_crossover"]
        
        logger.info(f"✅ Strategy Manager initialized with {len(self.strategies)} strategies")
    
    def analyze_all(self, symbol: str, bars: List[Dict[str, Any]], 
                   current_price: float, **kwargs) -> Dict[str, Any]:
        """
        Run all active strategies and return best signal.
        
        Args:
            symbol: Stock symbol
            bars: Historical bars
            current_price: Current price
            **kwargs: Additional data (iv_rank, options_chain, etc.)
            
        Returns:
            Best signal from all strategies
        """
        signals = {}
        
        for strategy_name in self.active_strategies:
            strategy = self.strategies.get(strategy_name)
            
            if not strategy:
                continue
            
            try:
                # Run strategy analysis
                if strategy_name == "iron_condor":
                    signal = strategy.analyze(
                        symbol, 
                        current_price, 
                        iv_rank=kwargs.get('iv_rank'),
                        options_chain=kwargs.get('options_chain')
                    )
                else:
                    signal = strategy.analyze(symbol, bars, current_price)
                
                signals[strategy_name] = signal
                
                logger.debug(f"{strategy_name}: {signal.get('action')} - {signal.get('reason')}")
                
            except Exception as e:
                logger.error(f"Error running {strategy_name} for {symbol}: {e}")
                continue
        
        # Find best signal (prioritize BUY signals)
        buy_signals = [s for s in signals.values() if s.get('action') == 'BUY']
        sell_signals = [s for s in signals.values() if s.get('action') == 'SELL']
        
        if buy_signals:
            # Return first buy signal (or implement scoring logic)
            return buy_signals[0]
        
        if sell_signals:
            return sell_signals[0]
        
        # No actionable signals
        return {
            "action": "HOLD",
            "reason": "No strategy generated actionable signal",
            "all_signals": signals
        }
    
    def get_strategy(self, name: str):
        """Get specific strategy by name."""
        return self.strategies.get(name)
    
    def enable_strategy(self, name: str):
        """Enable a strategy."""
        if name in self.strategies and name not in self.active_strategies:
            self.active_strategies.append(name)
            logger.info(f"✅ Enabled strategy: {name}")
            return True
        return False
    
    def disable_strategy(self, name: str):
        """Disable a strategy."""
        if name in self.active_strategies:
            self.active_strategies.remove(name)
            logger.info(f"⚠️ Disabled strategy: {name}")
            return True
        return False
    
    def list_strategies(self) -> Dict[str, bool]:
        """List all strategies and their status."""
        return {
            name: name in self.active_strategies 
            for name in self.strategies.keys()
        }
    
    def get_strategy_info(self, name: str) -> Dict[str, Any]:
        """Get information about a strategy."""
        strategy = self.strategies.get(name)
        
        if not strategy:
            return {}
        
        return {
            "name": strategy.name,
            "active": name in self.active_strategies,
            "type": "options" if name == "iron_condor" else "equity",
            "description": strategy.__doc__.strip() if strategy.__doc__ else ""
        }
