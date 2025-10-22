"""
Quantitative Trading Strategies.

This package contains all trading strategies:
- Mean Reversion
- Momentum Breakout
- Moving Average Crossover
- Iron Condor (Options)
"""
from .mean_reversion import MeanReversionStrategy
from .momentum_breakout import MomentumBreakoutStrategy
from .ma_crossover import MACrossoverStrategy
from .iron_condor import IronCondorStrategy

__all__ = [
    'MeanReversionStrategy',
    'MomentumBreakoutStrategy',
    'MACrossoverStrategy',
    'IronCondorStrategy',
]
