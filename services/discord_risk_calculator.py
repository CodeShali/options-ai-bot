"""
Discord Risk Calculator Service
Advanced risk calculations, position sizing, and portfolio analysis.
"""
import asyncio
import discord
from discord import ui
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from loguru import logger
import math

from services import get_alpaca_service, get_database_service
from config import settings


class DiscordRiskCalculatorService:
    """Advanced risk calculations and position sizing for Discord."""
    
    def __init__(self, bot):
        """Initialize risk calculator service."""
        self.bot = bot
        self.alpaca = get_alpaca_service()
        self.db = get_database_service()
        
        # Risk parameters
        self.default_risk_pct = 1.0  # 1% default risk per trade
        self.max_position_pct = 25.0  # 25% max position size
        self.max_portfolio_risk = 6.0  # 6% max total portfolio risk
        
        logger.info("🧮 Discord Risk Calculator Service initialized")
    
    # ==================== POSITION SIZE CALCULATOR ====================
    
    async def calculate_position_size(
        self, 
        symbol: str, 
        entry_price: float, 
        stop_price: float, 
        risk_amount: Optional[float] = None,
        risk_percentage: Optional[float] = None
    ) -> Dict[str, Any]:
        """Calculate optimal position size based on risk parameters."""
        try:
            # Get account info
            account = await self.alpaca.get_account()
            equity = float(account['equity'])
            
            # Determine risk amount
            if risk_amount:
                risk_dollars = risk_amount
                risk_pct = (risk_amount / equity) * 100
            elif risk_percentage:
                risk_pct = risk_percentage
                risk_dollars = equity * (risk_percentage / 100)
            else:
                risk_pct = self.default_risk_pct
                risk_dollars = equity * (self.default_risk_pct / 100)
            
            # Calculate risk per share
            risk_per_share = abs(entry_price - stop_price)
            
            if risk_per_share <= 0:
                return {"error": "Invalid entry/stop prices"}
            
            # Calculate position size
            shares = int(risk_dollars / risk_per_share)
            position_value = shares * entry_price
            position_pct = (position_value / equity) * 100
            
            # Check position size limits
            max_shares_by_position = int((equity * (self.max_position_pct / 100)) / entry_price)
            
            if shares > max_shares_by_position:
                shares = max_shares_by_position
                position_value = shares * entry_price
                position_pct = (position_value / equity) * 100
                actual_risk = shares * risk_per_share
                actual_risk_pct = (actual_risk / equity) * 100
                warning = f"Position size limited by {self.max_position_pct}% portfolio limit"
            else:
                actual_risk = risk_dollars
                actual_risk_pct = risk_pct
                warning = None
            
            # Calculate R:R ratio
            target_price = self.calculate_target_price(entry_price, stop_price)
            reward_per_share = abs(target_price - entry_price)
            rr_ratio = reward_per_share / risk_per_share if risk_per_share > 0 else 0
            
            return {
                "symbol": symbol,
                "entry_price": entry_price,
                "stop_price": stop_price,
                "target_price": target_price,
                "shares": shares,
                "position_value": position_value,
                "position_percentage": position_pct,
                "risk_dollars": actual_risk,
                "risk_percentage": actual_risk_pct,
                "risk_per_share": risk_per_share,
                "reward_per_share": reward_per_share,
                "rr_ratio": rr_ratio,
                "equity": equity,
                "warning": warning
            }
            
        except Exception as e:
            logger.error(f"Error calculating position size: {e}")
            return {"error": str(e)}
    
    def calculate_target_price(self, entry_price: float, stop_price: float) -> float:
        """Calculate target price based on 2:1 R:R ratio."""
        risk_per_share = abs(entry_price - stop_price)
        
        if entry_price > stop_price:  # Long position
            return entry_price + (risk_per_share * 2)
        else:  # Short position
            return entry_price - (risk_per_share * 2)
    
    # ==================== OPTIONS CALCULATOR ====================
    
    async def calculate_options_position(
        self,
        symbol: str,
        strike: float,
        expiry_days: int,
        option_type: str,
        premium: float,
        risk_amount: float
    ) -> Dict[str, Any]:
        """Calculate options position sizing and risk metrics."""
        try:
            # Get account info
            account = await self.alpaca.get_account()
            equity = float(account['equity'])
            
            # Calculate contracts
            cost_per_contract = premium * 100  # Options are per 100 shares
            max_contracts = int(risk_amount / cost_per_contract)
            
            if max_contracts <= 0:
                return {"error": "Risk amount too small for options position"}
            
            # Calculate position metrics
            total_cost = max_contracts * cost_per_contract
            total_risk = total_cost  # Max loss is premium paid
            risk_pct = (total_risk / equity) * 100
            
            # Get underlying price for analysis
            underlying_quote = await self.alpaca.get_latest_quote(symbol)
            underlying_price = underlying_quote['price'] if underlying_quote else strike
            
            # Calculate breakeven and profit scenarios
            if option_type.lower() == 'call':
                breakeven = strike + premium
                itm_probability = self.estimate_itm_probability(underlying_price, strike, expiry_days, 'call')
            else:
                breakeven = strike - premium
                itm_probability = self.estimate_itm_probability(underlying_price, strike, expiry_days, 'put')
            
            # Calculate potential profits at different price levels
            profit_scenarios = self.calculate_option_scenarios(
                underlying_price, strike, premium, option_type, max_contracts
            )
            
            return {
                "symbol": symbol,
                "option_type": option_type,
                "strike": strike,
                "premium": premium,
                "expiry_days": expiry_days,
                "contracts": max_contracts,
                "total_cost": total_cost,
                "total_risk": total_risk,
                "risk_percentage": risk_pct,
                "underlying_price": underlying_price,
                "breakeven": breakeven,
                "itm_probability": itm_probability,
                "profit_scenarios": profit_scenarios,
                "max_profit": "Unlimited" if option_type.lower() == 'call' else f"${(strike - premium) * max_contracts * 100:,.0f}",
                "max_loss": f"${total_cost:,.0f}"
            }
            
        except Exception as e:
            logger.error(f"Error calculating options position: {e}")
            return {"error": str(e)}
    
    def estimate_itm_probability(self, underlying: float, strike: float, days: int, option_type: str) -> float:
        """Estimate probability of finishing in-the-money (simplified)."""
        try:
            # Simplified probability calculation
            moneyness = underlying / strike
            time_factor = math.sqrt(days / 365)
            
            if option_type.lower() == 'call':
                if moneyness > 1.05:  # 5% ITM
                    return min(85, 60 + (moneyness - 1) * 100)
                elif moneyness > 0.95:  # Near ATM
                    return 50 + (moneyness - 1) * 500
                else:  # OTM
                    return max(15, 50 - (1 - moneyness) * 200)
            else:  # Put
                if moneyness < 0.95:  # 5% ITM
                    return min(85, 60 + (1 - moneyness) * 100)
                elif moneyness < 1.05:  # Near ATM
                    return 50 + (1 - moneyness) * 500
                else:  # OTM
                    return max(15, 50 - (moneyness - 1) * 200)
                    
        except Exception as e:
            logger.error(f"Error estimating ITM probability: {e}")
            return 50.0
    
    def calculate_option_scenarios(
        self, 
        underlying: float, 
        strike: float, 
        premium: float, 
        option_type: str, 
        contracts: int
    ) -> List[Dict[str, Any]]:
        """Calculate profit/loss scenarios at different price levels."""
        try:
            scenarios = []
            
            # Price levels to analyze
            price_levels = [
                underlying * 0.90,  # -10%
                underlying * 0.95,  # -5%
                underlying,         # Current
                underlying * 1.05,  # +5%
                underlying * 1.10   # +10%
            ]
            
            for price in price_levels:
                if option_type.lower() == 'call':
                    intrinsic_value = max(0, price - strike)
                else:
                    intrinsic_value = max(0, strike - price)
                
                # Simplified: assume intrinsic value at expiration
                option_value = intrinsic_value
                profit_per_contract = (option_value - premium) * 100
                total_profit = profit_per_contract * contracts
                
                scenarios.append({
                    "underlying_price": price,
                    "price_change_pct": ((price - underlying) / underlying) * 100,
                    "option_value": option_value,
                    "profit_per_contract": profit_per_contract,
                    "total_profit": total_profit,
                    "total_return_pct": (total_profit / (premium * contracts * 100)) * 100
                })
            
            return scenarios
            
        except Exception as e:
            logger.error(f"Error calculating option scenarios: {e}")
            return []
    
    # ==================== PORTFOLIO RISK ANALYSIS ====================
    
    async def analyze_portfolio_risk(self) -> Dict[str, Any]:
        """Comprehensive portfolio risk analysis."""
        try:
            # Get current positions and account
            positions = await self.alpaca.get_positions()
            account = await self.alpaca.get_account()
            equity = float(account['equity'])
            
            if not positions:
                return {"error": "No positions to analyze"}
            
            # Calculate position-level risks
            position_risks = []
            total_risk = 0
            
            for position in positions:
                symbol = position['symbol']
                qty = int(position['qty'])
                entry_price = float(position['avg_entry_price'])
                current_price = float(position['current_price'])
                market_value = float(position['market_value'])
                
                # Estimate stop loss (2% below entry for longs)
                estimated_stop = entry_price * 0.98
                risk_per_share = abs(entry_price - estimated_stop)
                position_risk = abs(qty) * risk_per_share
                
                position_risks.append({
                    "symbol": symbol,
                    "market_value": market_value,
                    "position_pct": (market_value / equity) * 100,
                    "estimated_risk": position_risk,
                    "risk_pct": (position_risk / equity) * 100,
                    "current_pl": float(position['unrealized_pl'])
                })
                
                total_risk += position_risk
            
            # Portfolio-level metrics
            total_risk_pct = (total_risk / equity) * 100
            largest_position = max(position_risks, key=lambda x: x['market_value'])
            
            # Concentration analysis
            concentration_risk = self.analyze_concentration_risk(position_risks, equity)
            
            # Correlation risk (simplified)
            correlation_risk = self.analyze_correlation_risk(positions)
            
            return {
                "equity": equity,
                "total_positions": len(positions),
                "total_market_value": sum(p['market_value'] for p in position_risks),
                "total_risk": total_risk,
                "total_risk_percentage": total_risk_pct,
                "largest_position": largest_position,
                "position_risks": position_risks,
                "concentration_risk": concentration_risk,
                "correlation_risk": correlation_risk,
                "risk_level": self.determine_risk_level(total_risk_pct),
                "recommendations": self.generate_risk_recommendations(total_risk_pct, concentration_risk)
            }
            
        except Exception as e:
            logger.error(f"Error analyzing portfolio risk: {e}")
            return {"error": str(e)}
    
    def analyze_concentration_risk(self, position_risks: List[Dict], equity: float) -> Dict[str, Any]:
        """Analyze position concentration risk."""
        try:
            # Sort by position size
            sorted_positions = sorted(position_risks, key=lambda x: x['market_value'], reverse=True)
            
            # Calculate concentration metrics
            top_1_pct = sorted_positions[0]['position_pct'] if sorted_positions else 0
            top_3_pct = sum(p['position_pct'] for p in sorted_positions[:3])
            top_5_pct = sum(p['position_pct'] for p in sorted_positions[:5])
            
            # Herfindahl-Hirschman Index
            hhi = sum((p['position_pct'] / 100) ** 2 for p in position_risks)
            
            return {
                "top_1_concentration": top_1_pct,
                "top_3_concentration": top_3_pct,
                "top_5_concentration": top_5_pct,
                "herfindahl_index": hhi,
                "concentration_level": self.get_concentration_level(top_1_pct, hhi)
            }
            
        except Exception as e:
            logger.error(f"Error analyzing concentration risk: {e}")
            return {}
    
    def analyze_correlation_risk(self, positions: List[Dict]) -> Dict[str, Any]:
        """Analyze correlation risk (simplified)."""
        try:
            # Simplified sector-based correlation
            sectors = {}
            for position in positions:
                symbol = position['symbol']
                # Simplified sector mapping
                if symbol in ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'TSLA', 'NVDA']:
                    sector = 'Technology'
                elif symbol in ['JPM', 'BAC', 'WFC', 'GS']:
                    sector = 'Financial'
                else:
                    sector = 'Other'
                
                sectors[sector] = sectors.get(sector, 0) + 1
            
            # Calculate correlation risk
            total_positions = len(positions)
            max_sector_positions = max(sectors.values()) if sectors else 0
            sector_concentration = (max_sector_positions / total_positions) * 100 if total_positions > 0 else 0
            
            return {
                "sector_breakdown": sectors,
                "sector_concentration": sector_concentration,
                "correlation_level": "HIGH" if sector_concentration > 60 else "MEDIUM" if sector_concentration > 40 else "LOW"
            }
            
        except Exception as e:
            logger.error(f"Error analyzing correlation risk: {e}")
            return {}
    
    def get_concentration_level(self, top_1_pct: float, hhi: float) -> str:
        """Determine concentration risk level."""
        if top_1_pct > 30 or hhi > 0.20:
            return "HIGH"
        elif top_1_pct > 20 or hhi > 0.15:
            return "MEDIUM"
        else:
            return "LOW"
    
    def determine_risk_level(self, total_risk_pct: float) -> str:
        """Determine overall portfolio risk level."""
        if total_risk_pct > self.max_portfolio_risk:
            return "HIGH"
        elif total_risk_pct > self.max_portfolio_risk * 0.75:
            return "MEDIUM"
        else:
            return "LOW"
    
    def generate_risk_recommendations(self, total_risk_pct: float, concentration_risk: Dict) -> List[str]:
        """Generate risk management recommendations."""
        recommendations = []
        
        if total_risk_pct > self.max_portfolio_risk:
            recommendations.append(f"Reduce total portfolio risk from {total_risk_pct:.1f}% to below {self.max_portfolio_risk}%")
        
        concentration_level = concentration_risk.get('concentration_level', 'LOW')
        if concentration_level == 'HIGH':
            recommendations.append("Reduce position concentration - consider trimming largest positions")
        
        top_1_pct = concentration_risk.get('top_1_concentration', 0)
        if top_1_pct > self.max_position_pct:
            recommendations.append(f"Largest position is {top_1_pct:.1f}% - consider reducing to below {self.max_position_pct}%")
        
        if not recommendations:
            recommendations.append("Portfolio risk levels are within acceptable ranges")
        
        return recommendations
    
    # ==================== RISK SCENARIO ANALYSIS ====================
    
    async def calculate_risk_scenarios(self, market_drop_pct: float = 10.0) -> Dict[str, Any]:
        """Calculate portfolio impact under stress scenarios."""
        try:
            positions = await self.alpaca.get_positions()
            account = await self.alpaca.get_account()
            equity = float(account['equity'])
            
            scenarios = {}
            
            # Market drop scenarios
            for drop_pct in [5, 10, 15, 20]:
                scenario_loss = 0
                
                for position in positions:
                    market_value = float(position['market_value'])
                    # Assume position moves with market (simplified)
                    position_loss = market_value * (drop_pct / 100)
                    scenario_loss += position_loss
                
                scenarios[f"market_drop_{drop_pct}pct"] = {
                    "scenario": f"Market drops {drop_pct}%",
                    "estimated_loss": scenario_loss,
                    "loss_percentage": (scenario_loss / equity) * 100,
                    "remaining_equity": equity - scenario_loss
                }
            
            return {
                "current_equity": equity,
                "scenarios": scenarios,
                "worst_case": max(scenarios.values(), key=lambda x: x['estimated_loss'])
            }
            
        except Exception as e:
            logger.error(f"Error calculating risk scenarios: {e}")
            return {"error": str(e)}


# Singleton instance
_discord_risk_calculator = None

def get_discord_risk_calculator(bot=None):
    """Get or create Discord risk calculator service."""
    global _discord_risk_calculator
    if _discord_risk_calculator is None and bot:
        _discord_risk_calculator = DiscordRiskCalculatorService(bot)
    return _discord_risk_calculator
