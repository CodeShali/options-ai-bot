"""
Advanced Position Sizing Module.

Implements Kelly Criterion, portfolio heat management, and dynamic sizing.
"""
from typing import Dict, Any, List, Optional
from loguru import logger
import math


class PositionSizer:
    """
    Advanced position sizing with multiple methods.
    
    Methods:
    - Kelly Criterion
    - Fixed Fractional
    - Volatility-based
    - Portfolio Heat
    - Risk Parity
    """
    
    def __init__(self, account_size: float, max_risk_per_trade: float = 0.02):
        """
        Initialize position sizer.
        
        Args:
            account_size: Total account value
            max_risk_per_trade: Maximum risk per trade (default 2%)
        """
        self.account_size = account_size
        self.max_risk_per_trade = max_risk_per_trade
        self.max_portfolio_heat = 0.06  # Max 6% total risk
        logger.info(f"✅ Position Sizer initialized (Account: ${account_size:,.2f}, Max Risk: {max_risk_per_trade*100}%)")
    
    def kelly_criterion(self, win_rate: float, avg_win: float, avg_loss: float,
                       kelly_fraction: float = 0.25) -> float:
        """
        Calculate position size using Kelly Criterion.
        
        Formula: f* = (p*b - q) / b
        where:
        - p = win probability
        - q = loss probability (1-p)
        - b = win/loss ratio
        
        Args:
            win_rate: Historical win rate (0-1)
            avg_win: Average winning trade
            avg_loss: Average losing trade (positive number)
            kelly_fraction: Fraction of Kelly to use (default 0.25 = Quarter Kelly)
            
        Returns:
            Position size as fraction of account (0-1)
        """
        if win_rate <= 0 or win_rate >= 1:
            logger.warning(f"Invalid win rate: {win_rate}, using fixed fractional")
            return self.max_risk_per_trade
        
        if avg_loss <= 0:
            logger.warning("Invalid avg_loss, using fixed fractional")
            return self.max_risk_per_trade
        
        # Calculate win/loss ratio
        win_loss_ratio = avg_win / avg_loss
        
        # Kelly formula
        p = win_rate
        q = 1 - win_rate
        kelly = (p * win_loss_ratio - q) / win_loss_ratio
        
        # Apply Kelly fraction (conservative)
        fractional_kelly = kelly * kelly_fraction
        
        # Cap at max risk
        position_size = min(fractional_kelly, self.max_risk_per_trade)
        position_size = max(position_size, 0)  # No negative positions
        
        logger.info(f"Kelly Criterion: {kelly:.4f} → Fractional: {fractional_kelly:.4f} → Final: {position_size:.4f}")
        
        return position_size
    
    def volatility_adjusted(self, current_volatility: float, 
                           target_volatility: float = 0.15) -> float:
        """
        Adjust position size based on volatility.
        
        Lower volatility → Larger position
        Higher volatility → Smaller position
        
        Args:
            current_volatility: Current asset volatility (annualized)
            target_volatility: Target portfolio volatility (default 15%)
            
        Returns:
            Position size multiplier
        """
        if current_volatility <= 0:
            return 1.0
        
        # Inverse relationship
        multiplier = target_volatility / current_volatility
        
        # Cap between 0.25x and 2x
        multiplier = max(0.25, min(2.0, multiplier))
        
        logger.debug(f"Volatility adjustment: {current_volatility:.2%} → {multiplier:.2f}x")
        
        return multiplier
    
    def calculate_shares(self, entry_price: float, stop_loss: float,
                        risk_amount: float = None) -> int:
        """
        Calculate number of shares based on stop loss.
        
        Args:
            entry_price: Entry price
            stop_loss: Stop loss price
            risk_amount: Amount to risk (default: max_risk_per_trade * account_size)
            
        Returns:
            Number of shares to buy
        """
        if risk_amount is None:
            risk_amount = self.account_size * self.max_risk_per_trade
        
        # Calculate risk per share
        risk_per_share = abs(entry_price - stop_loss)
        
        if risk_per_share <= 0:
            logger.warning("Invalid stop loss, using minimum position")
            return 1
        
        # Calculate shares
        shares = int(risk_amount / risk_per_share)
        
        # Ensure we can afford it
        max_affordable = int(self.account_size / entry_price)
        shares = min(shares, max_affordable)
        shares = max(shares, 1)  # At least 1 share
        
        position_value = shares * entry_price
        actual_risk = shares * risk_per_share
        
        logger.info(f"Position: {shares} shares @ ${entry_price:.2f} = ${position_value:.2f} (Risk: ${actual_risk:.2f})")
        
        return shares
    
    def portfolio_heat_check(self, current_positions: List[Dict[str, Any]],
                            new_position_risk: float) -> tuple[bool, str]:
        """
        Check if adding new position exceeds portfolio heat limit.
        
        Portfolio heat = sum of all position risks
        
        Args:
            current_positions: List of current positions with risk amounts
            new_position_risk: Risk amount for new position
            
        Returns:
            (can_add, reason)
        """
        # Calculate current heat
        current_heat = sum(pos.get('risk_amount', 0) for pos in current_positions)
        current_heat_pct = current_heat / self.account_size
        
        # Calculate new heat
        new_heat = current_heat + new_position_risk
        new_heat_pct = new_heat / self.account_size
        
        # Check limit
        if new_heat_pct > self.max_portfolio_heat:
            return False, f"Portfolio heat would be {new_heat_pct:.2%} (max: {self.max_portfolio_heat:.2%})"
        
        logger.info(f"Portfolio heat: {current_heat_pct:.2%} → {new_heat_pct:.2%} (OK)")
        return True, "Within portfolio heat limits"
    
    def risk_parity(self, positions: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        Calculate risk parity weights for portfolio.
        
        Each position contributes equal risk to portfolio.
        
        Args:
            positions: List of positions with volatility
            
        Returns:
            Dict of symbol -> weight
        """
        if not positions:
            return {}
        
        # Calculate inverse volatility weights
        weights = {}
        total_inv_vol = 0
        
        for pos in positions:
            symbol = pos['symbol']
            volatility = pos.get('volatility', 0.20)  # Default 20%
            
            if volatility > 0:
                inv_vol = 1 / volatility
                weights[symbol] = inv_vol
                total_inv_vol += inv_vol
        
        # Normalize to sum to 1
        if total_inv_vol > 0:
            for symbol in weights:
                weights[symbol] /= total_inv_vol
        
        logger.debug(f"Risk parity weights: {weights}")
        
        return weights
    
    def dynamic_sizing(self, strategy_performance: Dict[str, Any],
                      base_size: float = None) -> float:
        """
        Dynamically adjust position size based on strategy performance.
        
        Good performance → Increase size
        Poor performance → Decrease size
        
        Args:
            strategy_performance: Performance metrics (win_rate, profit_factor, etc)
            base_size: Base position size (default: max_risk_per_trade)
            
        Returns:
            Adjusted position size
        """
        if base_size is None:
            base_size = self.max_risk_per_trade
        
        win_rate = strategy_performance.get('win_rate', 50) / 100
        profit_factor = strategy_performance.get('profit_factor', 1.0)
        sharpe_ratio = strategy_performance.get('sharpe_ratio', 0)
        
        # Calculate performance score
        score = 0
        
        # Win rate component (0-1)
        if win_rate >= 0.6:
            score += 0.4
        elif win_rate >= 0.5:
            score += 0.2
        
        # Profit factor component (0-1)
        if profit_factor >= 2.0:
            score += 0.4
        elif profit_factor >= 1.5:
            score += 0.2
        
        # Sharpe ratio component (0-1)
        if sharpe_ratio >= 2.0:
            score += 0.2
        elif sharpe_ratio >= 1.0:
            score += 0.1
        
        # Adjust size based on score
        # Score 0-0.3: 0.5x (reduce)
        # Score 0.3-0.7: 1.0x (normal)
        # Score 0.7-1.0: 1.5x (increase)
        
        if score < 0.3:
            multiplier = 0.5
        elif score < 0.7:
            multiplier = 1.0
        else:
            multiplier = 1.5
        
        adjusted_size = base_size * multiplier
        
        logger.info(f"Dynamic sizing: Score {score:.2f} → {multiplier}x → {adjusted_size:.4f}")
        
        return adjusted_size
    
    def calculate_optimal_size(self, 
                              entry_price: float,
                              stop_loss: float,
                              strategy_performance: Dict[str, Any],
                              current_positions: List[Dict[str, Any]],
                              volatility: float = None) -> Dict[str, Any]:
        """
        Calculate optimal position size using multiple methods.
        
        Args:
            entry_price: Entry price
            stop_loss: Stop loss price
            strategy_performance: Strategy metrics
            current_positions: Current portfolio positions
            volatility: Asset volatility (optional)
            
        Returns:
            Position sizing recommendation
        """
        # 1. Kelly Criterion
        win_rate = strategy_performance.get('win_rate', 50) / 100
        avg_win = strategy_performance.get('avg_win', 100)
        avg_loss = abs(strategy_performance.get('avg_loss', -50))
        
        kelly_size = self.kelly_criterion(win_rate, avg_win, avg_loss)
        
        # 2. Dynamic sizing based on performance
        dynamic_size = self.dynamic_sizing(strategy_performance)
        
        # 3. Volatility adjustment
        vol_multiplier = 1.0
        if volatility:
            vol_multiplier = self.volatility_adjusted(volatility)
        
        # Combine methods (weighted average)
        combined_size = (kelly_size * 0.5 + dynamic_size * 0.5) * vol_multiplier
        combined_size = min(combined_size, self.max_risk_per_trade)
        
        # 4. Calculate shares
        risk_amount = self.account_size * combined_size
        shares = self.calculate_shares(entry_price, stop_loss, risk_amount)
        
        # 5. Portfolio heat check
        position_risk = shares * abs(entry_price - stop_loss)
        can_add, heat_reason = self.portfolio_heat_check(current_positions, position_risk)
        
        if not can_add:
            # Reduce size to fit within heat limit
            current_heat = sum(pos.get('risk_amount', 0) for pos in current_positions)
            max_new_risk = (self.account_size * self.max_portfolio_heat) - current_heat
            
            if max_new_risk > 0:
                shares = int(max_new_risk / abs(entry_price - stop_loss))
                shares = max(shares, 1)
                logger.warning(f"Reduced position size due to portfolio heat: {shares} shares")
            else:
                shares = 0
                logger.warning("Cannot add position: Portfolio heat limit reached")
        
        position_value = shares * entry_price
        
        return {
            "shares": shares,
            "entry_price": entry_price,
            "stop_loss": stop_loss,
            "position_value": position_value,
            "risk_amount": position_risk,
            "risk_pct": (position_risk / self.account_size * 100) if shares > 0 else 0,
            "kelly_size": kelly_size,
            "dynamic_size": dynamic_size,
            "vol_multiplier": vol_multiplier,
            "combined_size": combined_size,
            "can_add": can_add,
            "heat_reason": heat_reason
        }
