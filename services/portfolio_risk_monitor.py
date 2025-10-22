"""
Portfolio Risk Monitor - Track concentration, correlation, and overall portfolio risk.
"""
import asyncio
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from loguru import logger
import statistics
import math

from services import get_alpaca_service, get_database_service
from config import settings


class PortfolioRiskMonitor:
    """Monitor portfolio-level risks and generate alerts."""
    
    def __init__(self):
        """Initialize portfolio risk monitor."""
        self.alpaca = get_alpaca_service()
        self.db = get_database_service()
        
        # Risk thresholds
        self.risk_thresholds = {
            "concentration": {
                "single_position": 0.25,      # 25% max in one position
                "warning_level": 0.20,        # Warn at 20%
                "critical_level": 0.35        # Critical at 35%
            },
            "sector": {
                "max_exposure": 0.40,         # 40% max in one sector
                "warning_level": 0.30,        # Warn at 30%
                "diversification_min": 3      # Min 3 sectors
            },
            "correlation": {
                "high_correlation": 0.80,     # 80%+ correlation is high
                "max_correlated_pairs": 3,    # Max 3 highly correlated pairs
                "portfolio_correlation": 0.85  # Portfolio vs market correlation
            },
            "volatility": {
                "max_portfolio_vol": 0.25,    # 25% max portfolio volatility
                "position_vol_limit": 0.40,   # 40% max single position volatility
                "vol_spike_threshold": 2.0    # 2x normal volatility = spike
            },
            "beta": {
                "max_beta_weighted": 0.75,    # Max 75% beta-weighted exposure
                "min_beta_weighted": -0.25,   # Min -25% (short exposure)
                "neutral_range": 0.15         # ±15% is considered neutral
            }
        }
        
        # Sector mappings (simplified)
        self.sector_mappings = {
            # Technology
            "AAPL": "Technology", "MSFT": "Technology", "GOOGL": "Technology", 
            "AMZN": "Technology", "META": "Technology", "TSLA": "Technology",
            "NVDA": "Technology", "AMD": "Technology", "INTC": "Technology",
            
            # Financial
            "JPM": "Financial", "BAC": "Financial", "WFC": "Financial",
            "GS": "Financial", "MS": "Financial", "C": "Financial",
            
            # Healthcare
            "JNJ": "Healthcare", "PFE": "Healthcare", "UNH": "Healthcare",
            "ABBV": "Healthcare", "MRK": "Healthcare", "LLY": "Healthcare",
            
            # Energy
            "XOM": "Energy", "CVX": "Energy", "COP": "Energy",
            
            # Consumer
            "WMT": "Consumer", "PG": "Consumer", "KO": "Consumer",
            "PEP": "Consumer", "MCD": "Consumer", "NKE": "Consumer",
            
            # Industrial
            "BA": "Industrial", "CAT": "Industrial", "GE": "Industrial",
            
            # Default
            "DEFAULT": "Other"
        }
        
        # Risk history for trending
        self.risk_history = []
    
    async def analyze_portfolio_risk(self) -> Dict[str, Any]:
        """Comprehensive portfolio risk analysis."""
        try:
            logger.info("⚖️ Analyzing portfolio risk...")
            
            # Get current positions and account
            positions = await self.alpaca.get_positions()
            account = await self.alpaca.get_account()
            
            if not positions:
                return {
                    "total_positions": 0,
                    "risk_alerts": [],
                    "risk_score": 0,
                    "timestamp": datetime.now().isoformat()
                }
            
            # Calculate portfolio metrics
            portfolio_value = float(account.get('portfolio_value', 0))
            
            # Analyze different risk dimensions
            concentration_analysis = await self._analyze_concentration_risk(positions, portfolio_value)
            sector_analysis = await self._analyze_sector_risk(positions, portfolio_value)
            correlation_analysis = await self._analyze_correlation_risk(positions)
            volatility_analysis = await self._analyze_volatility_risk(positions)
            beta_analysis = await self._analyze_beta_risk(positions, portfolio_value)
            
            # Combine all analyses
            all_alerts = []
            all_alerts.extend(concentration_analysis.get("alerts", []))
            all_alerts.extend(sector_analysis.get("alerts", []))
            all_alerts.extend(correlation_analysis.get("alerts", []))
            all_alerts.extend(volatility_analysis.get("alerts", []))
            all_alerts.extend(beta_analysis.get("alerts", []))
            
            # Calculate overall risk score
            risk_score = self._calculate_overall_risk_score(
                concentration_analysis, sector_analysis, correlation_analysis,
                volatility_analysis, beta_analysis
            )
            
            # Store risk history
            self._store_risk_history({
                "timestamp": datetime.now(),
                "risk_score": risk_score,
                "concentration": concentration_analysis,
                "sector": sector_analysis,
                "correlation": correlation_analysis,
                "volatility": volatility_analysis,
                "beta": beta_analysis
            })
            
            logger.info(f"⚖️ Portfolio risk analysis complete: {len(all_alerts)} alerts, risk score: {risk_score}")
            
            return {
                "total_positions": len(positions),
                "portfolio_value": portfolio_value,
                "risk_score": risk_score,
                "risk_level": self._get_risk_level(risk_score),
                "risk_alerts": all_alerts,
                "detailed_analysis": {
                    "concentration": concentration_analysis,
                    "sector": sector_analysis,
                    "correlation": correlation_analysis,
                    "volatility": volatility_analysis,
                    "beta": beta_analysis
                },
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error analyzing portfolio risk: {e}")
            return {
                "error": str(e),
                "total_positions": 0,
                "risk_alerts": []
            }
    
    async def _analyze_concentration_risk(self, positions: List[Dict], portfolio_value: float) -> Dict[str, Any]:
        """Analyze position concentration risk."""
        try:
            alerts = []
            position_weights = []
            
            for position in positions:
                market_value = abs(float(position.get('market_value', 0)))
                weight = market_value / portfolio_value if portfolio_value > 0 else 0
                position_weights.append({
                    "symbol": position['symbol'],
                    "weight": weight,
                    "market_value": market_value
                })
                
                # Check concentration thresholds
                if weight >= self.risk_thresholds["concentration"]["critical_level"]:
                    alerts.append({
                        "type": "CRITICAL_CONCENTRATION",
                        "symbol": position['symbol'],
                        "message": f"🚨 Critical concentration: {position['symbol']} is {weight*100:.1f}% of portfolio",
                        "reasoning": f"Position represents {weight*100:.1f}% of total portfolio value "
                                   f"(${market_value:,.0f} of ${portfolio_value:,.0f}). "
                                   f"Exceeds critical threshold of {self.risk_thresholds['concentration']['critical_level']*100:.0f}%. "
                                   f"Consider reducing position size to limit single-name risk.",
                        "severity": "CRITICAL",
                        "weight_pct": weight * 100,
                        "threshold_pct": self.risk_thresholds["concentration"]["critical_level"] * 100,
                        "action_required": "REDUCE_POSITION"
                    })
                
                elif weight >= self.risk_thresholds["concentration"]["single_position"]:
                    alerts.append({
                        "type": "HIGH_CONCENTRATION",
                        "symbol": position['symbol'],
                        "message": f"⚠️ High concentration: {position['symbol']} is {weight*100:.1f}% of portfolio",
                        "reasoning": f"Position represents {weight*100:.1f}% of portfolio. "
                                   f"Exceeds recommended maximum of {self.risk_thresholds['concentration']['single_position']*100:.0f}%. "
                                   f"Consider taking partial profits or rebalancing.",
                        "severity": "HIGH",
                        "weight_pct": weight * 100,
                        "threshold_pct": self.risk_thresholds["concentration"]["single_position"] * 100,
                        "action_required": "CONSIDER_REBALANCE"
                    })
                
                elif weight >= self.risk_thresholds["concentration"]["warning_level"]:
                    alerts.append({
                        "type": "CONCENTRATION_WARNING",
                        "symbol": position['symbol'],
                        "message": f"📊 {position['symbol']} approaching concentration limit at {weight*100:.1f}%",
                        "reasoning": f"Position is {weight*100:.1f}% of portfolio, approaching "
                                   f"{self.risk_thresholds['concentration']['single_position']*100:.0f}% limit. Monitor closely.",
                        "severity": "MEDIUM",
                        "weight_pct": weight * 100,
                        "action_required": "MONITOR"
                    })
            
            # Sort by weight
            position_weights.sort(key=lambda x: x["weight"], reverse=True)
            
            # Calculate concentration metrics
            top_3_weight = sum(pos["weight"] for pos in position_weights[:3])
            top_5_weight = sum(pos["weight"] for pos in position_weights[:5])
            
            # Herfindahl-Hirschman Index (concentration measure)
            hhi = sum(pos["weight"] ** 2 for pos in position_weights)
            
            return {
                "alerts": alerts,
                "position_weights": position_weights,
                "top_3_concentration": top_3_weight,
                "top_5_concentration": top_5_weight,
                "herfindahl_index": hhi,
                "concentration_level": "HIGH" if hhi > 0.15 else "MEDIUM" if hhi > 0.08 else "LOW"
            }
            
        except Exception as e:
            logger.error(f"Error analyzing concentration risk: {e}")
            return {"alerts": [], "error": str(e)}
    
    async def _analyze_sector_risk(self, positions: List[Dict], portfolio_value: float) -> Dict[str, Any]:
        """Analyze sector concentration risk."""
        try:
            alerts = []
            sector_exposure = {}
            
            # Calculate sector exposures
            for position in positions:
                symbol = position['symbol']
                market_value = abs(float(position.get('market_value', 0)))
                weight = market_value / portfolio_value if portfolio_value > 0 else 0
                
                # Get sector (simplified mapping)
                sector = self.sector_mappings.get(symbol, "Other")
                
                if sector not in sector_exposure:
                    sector_exposure[sector] = {
                        "weight": 0,
                        "positions": [],
                        "market_value": 0
                    }
                
                sector_exposure[sector]["weight"] += weight
                sector_exposure[sector]["market_value"] += market_value
                sector_exposure[sector]["positions"].append({
                    "symbol": symbol,
                    "weight": weight,
                    "market_value": market_value
                })
            
            # Check sector concentration
            for sector, data in sector_exposure.items():
                weight = data["weight"]
                
                if weight >= self.risk_thresholds["sector"]["max_exposure"]:
                    alerts.append({
                        "type": "HIGH_SECTOR_CONCENTRATION",
                        "sector": sector,
                        "message": f"⚠️ High {sector} sector exposure: {weight*100:.1f}%",
                        "reasoning": f"{sector} sector represents {weight*100:.1f}% of portfolio "
                                   f"across {len(data['positions'])} positions. "
                                   f"Exceeds recommended maximum of {self.risk_thresholds['sector']['max_exposure']*100:.0f}%. "
                                   f"Consider diversifying into other sectors.",
                        "severity": "HIGH",
                        "weight_pct": weight * 100,
                        "positions": data["positions"],
                        "action_required": "DIVERSIFY"
                    })
                
                elif weight >= self.risk_thresholds["sector"]["warning_level"]:
                    alerts.append({
                        "type": "SECTOR_CONCENTRATION_WARNING",
                        "sector": sector,
                        "message": f"📊 {sector} sector exposure at {weight*100:.1f}%",
                        "reasoning": f"{sector} sector approaching concentration limit. Monitor closely.",
                        "severity": "MEDIUM",
                        "weight_pct": weight * 100,
                        "action_required": "MONITOR"
                    })
            
            # Check diversification
            num_sectors = len(sector_exposure)
            if num_sectors < self.risk_thresholds["sector"]["diversification_min"]:
                alerts.append({
                    "type": "INSUFFICIENT_DIVERSIFICATION",
                    "message": f"📉 Portfolio only spans {num_sectors} sectors",
                    "reasoning": f"Portfolio concentrated in only {num_sectors} sectors. "
                               f"Recommend diversifying across at least {self.risk_thresholds['sector']['diversification_min']} sectors "
                               f"to reduce sector-specific risk.",
                    "severity": "MEDIUM",
                    "sectors_count": num_sectors,
                    "action_required": "DIVERSIFY"
                })
            
            # Sort sectors by exposure
            sorted_sectors = sorted(
                sector_exposure.items(),
                key=lambda x: x[1]["weight"],
                reverse=True
            )
            
            return {
                "alerts": alerts,
                "sector_exposure": dict(sorted_sectors),
                "num_sectors": num_sectors,
                "top_sector_weight": sorted_sectors[0][1]["weight"] if sorted_sectors else 0,
                "diversification_score": min(1.0, num_sectors / 8)  # Score out of 8 sectors
            }
            
        except Exception as e:
            logger.error(f"Error analyzing sector risk: {e}")
            return {"alerts": [], "error": str(e)}
    
    async def _analyze_correlation_risk(self, positions: List[Dict]) -> Dict[str, Any]:
        """Analyze correlation risk between positions."""
        try:
            alerts = []
            
            if len(positions) < 2:
                return {"alerts": [], "correlation_pairs": []}
            
            # Get correlation data (simplified - would use real correlation calculation)
            correlation_pairs = []
            high_correlation_count = 0
            
            # Simplified correlation analysis
            # In a real implementation, you would:
            # 1. Get historical price data for all positions
            # 2. Calculate correlation matrix
            # 3. Identify highly correlated pairs
            
            # For now, we'll use sector-based correlation assumptions
            sector_positions = {}
            for position in positions:
                symbol = position['symbol']
                sector = self.sector_mappings.get(symbol, "Other")
                
                if sector not in sector_positions:
                    sector_positions[sector] = []
                sector_positions[sector].append(symbol)
            
            # Assume positions in same sector have high correlation
            for sector, symbols in sector_positions.items():
                if len(symbols) > 1:
                    # All pairs in same sector are highly correlated
                    for i in range(len(symbols)):
                        for j in range(i + 1, len(symbols)):
                            correlation_pairs.append({
                                "symbol1": symbols[i],
                                "symbol2": symbols[j],
                                "correlation": 0.85,  # Assumed high correlation
                                "sector": sector
                            })
                            high_correlation_count += 1
            
            # Alert on high correlation
            if high_correlation_count > self.risk_thresholds["correlation"]["max_correlated_pairs"]:
                alerts.append({
                    "type": "HIGH_CORRELATION_RISK",
                    "message": f"⚠️ {high_correlation_count} highly correlated position pairs",
                    "reasoning": f"Portfolio has {high_correlation_count} pairs of highly correlated positions. "
                               f"This reduces diversification benefits and increases concentration risk. "
                               f"Consider reducing positions in similar sectors or assets.",
                    "severity": "HIGH",
                    "correlated_pairs": high_correlation_count,
                    "correlation_pairs": correlation_pairs[:5],  # Show top 5
                    "action_required": "REDUCE_CORRELATION"
                })
            
            # Portfolio correlation to market (simplified)
            # Would calculate actual correlation to SPY/QQQ
            tech_weight = sum(
                abs(float(pos.get('market_value', 0)))
                for pos in positions
                if self.sector_mappings.get(pos['symbol'], "Other") == "Technology"
            )
            total_value = sum(abs(float(pos.get('market_value', 0))) for pos in positions)
            tech_pct = tech_weight / total_value if total_value > 0 else 0
            
            # High tech exposure = high market correlation
            market_correlation = min(0.95, 0.6 + tech_pct * 0.4)
            
            if market_correlation > self.risk_thresholds["correlation"]["portfolio_correlation"]:
                alerts.append({
                    "type": "HIGH_MARKET_CORRELATION",
                    "message": f"📊 Portfolio highly correlated to market ({market_correlation:.0%})",
                    "reasoning": f"Portfolio correlation to market is {market_correlation:.0%}. "
                               f"High correlation reduces diversification benefits during market downturns. "
                               f"Consider adding uncorrelated assets or hedges.",
                    "severity": "MEDIUM",
                    "market_correlation": market_correlation,
                    "action_required": "ADD_HEDGES"
                })
            
            return {
                "alerts": alerts,
                "correlation_pairs": correlation_pairs,
                "high_correlation_count": high_correlation_count,
                "market_correlation": market_correlation
            }
            
        except Exception as e:
            logger.error(f"Error analyzing correlation risk: {e}")
            return {"alerts": [], "error": str(e)}
    
    async def _analyze_volatility_risk(self, positions: List[Dict]) -> Dict[str, Any]:
        """Analyze volatility risk."""
        try:
            alerts = []
            
            # Simplified volatility analysis
            # In real implementation, would calculate actual historical volatility
            
            high_vol_positions = []
            total_vol_weighted = 0
            total_weight = 0
            
            for position in positions:
                symbol = position['symbol']
                market_value = abs(float(position.get('market_value', 0)))
                
                # Simplified volatility assignment based on symbol
                if symbol in ["TSLA", "NVDA", "AMD", "MEME_STOCKS"]:
                    volatility = 0.45  # 45% volatility
                elif self.sector_mappings.get(symbol, "Other") == "Technology":
                    volatility = 0.30  # 30% volatility
                elif symbol in ["SPY", "QQQ", "IWM"]:
                    volatility = 0.20  # 20% volatility
                else:
                    volatility = 0.25  # 25% default
                
                weight = market_value / sum(abs(float(p.get('market_value', 0))) for p in positions)
                total_vol_weighted += volatility * weight
                total_weight += weight
                
                # Check individual position volatility
                if volatility > self.risk_thresholds["volatility"]["position_vol_limit"]:
                    high_vol_positions.append({
                        "symbol": symbol,
                        "volatility": volatility,
                        "weight": weight
                    })
                    
                    alerts.append({
                        "type": "HIGH_VOLATILITY_POSITION",
                        "symbol": symbol,
                        "message": f"🎢 {symbol}: High volatility position ({volatility:.0%})",
                        "reasoning": f"{symbol} has estimated volatility of {volatility:.0%}, "
                                   f"above the {self.risk_thresholds['volatility']['position_vol_limit']:.0%} threshold. "
                                   f"Position represents {weight:.1%} of portfolio. Monitor closely for large moves.",
                        "severity": "MEDIUM",
                        "volatility_pct": volatility * 100,
                        "weight_pct": weight * 100,
                        "action_required": "MONITOR_CLOSELY"
                    })
            
            # Portfolio volatility
            portfolio_volatility = total_vol_weighted / total_weight if total_weight > 0 else 0
            
            if portfolio_volatility > self.risk_thresholds["volatility"]["max_portfolio_vol"]:
                alerts.append({
                    "type": "HIGH_PORTFOLIO_VOLATILITY",
                    "message": f"⚠️ High portfolio volatility: {portfolio_volatility:.0%}",
                    "reasoning": f"Estimated portfolio volatility is {portfolio_volatility:.0%}, "
                               f"above the {self.risk_thresholds['volatility']['max_portfolio_vol']:.0%} threshold. "
                               f"Consider reducing position sizes or adding lower-volatility assets.",
                    "severity": "HIGH",
                    "portfolio_volatility": portfolio_volatility * 100,
                    "high_vol_positions": len(high_vol_positions),
                    "action_required": "REDUCE_VOLATILITY"
                })
            
            return {
                "alerts": alerts,
                "portfolio_volatility": portfolio_volatility,
                "high_vol_positions": high_vol_positions,
                "volatility_level": "HIGH" if portfolio_volatility > 0.25 else "MEDIUM" if portfolio_volatility > 0.15 else "LOW"
            }
            
        except Exception as e:
            logger.error(f"Error analyzing volatility risk: {e}")
            return {"alerts": [], "error": str(e)}
    
    async def _analyze_beta_risk(self, positions: List[Dict], portfolio_value: float) -> Dict[str, Any]:
        """Analyze beta-weighted market exposure."""
        try:
            alerts = []
            
            # Simplified beta analysis
            total_beta_weighted = 0
            
            for position in positions:
                symbol = position['symbol']
                market_value = abs(float(position.get('market_value', 0)))
                weight = market_value / portfolio_value if portfolio_value > 0 else 0
                
                # Simplified beta assignment
                if symbol in ["TSLA", "NVDA"]:
                    beta = 1.8
                elif self.sector_mappings.get(symbol, "Other") == "Technology":
                    beta = 1.3
                elif symbol in ["SPY"]:
                    beta = 1.0
                elif symbol in ["VIX", "UVXY"]:
                    beta = -0.5  # Inverse correlation
                else:
                    beta = 1.1  # Slightly above market
                
                total_beta_weighted += beta * weight
            
            # Check beta-weighted exposure
            if total_beta_weighted > self.risk_thresholds["beta"]["max_beta_weighted"]:
                alerts.append({
                    "type": "HIGH_BETA_EXPOSURE",
                    "message": f"📈 High market exposure: {total_beta_weighted:.2f} beta-weighted",
                    "reasoning": f"Portfolio beta-weighted exposure is {total_beta_weighted:.2f}, "
                               f"above the {self.risk_thresholds['beta']['max_beta_weighted']:.2f} threshold. "
                               f"Portfolio will amplify market moves. Consider adding hedges or reducing high-beta positions.",
                    "severity": "HIGH",
                    "beta_weighted": total_beta_weighted,
                    "action_required": "ADD_HEDGES"
                })
            
            elif total_beta_weighted < self.risk_thresholds["beta"]["min_beta_weighted"]:
                alerts.append({
                    "type": "NEGATIVE_BETA_EXPOSURE",
                    "message": f"📉 Negative market exposure: {total_beta_weighted:.2f} beta-weighted",
                    "reasoning": f"Portfolio has negative beta exposure ({total_beta_weighted:.2f}). "
                               f"Will benefit from market declines but miss market rallies.",
                    "severity": "MEDIUM",
                    "beta_weighted": total_beta_weighted,
                    "action_required": "REVIEW_STRATEGY"
                })
            
            # Determine market exposure level
            if abs(total_beta_weighted) <= self.risk_thresholds["beta"]["neutral_range"]:
                exposure_level = "MARKET_NEUTRAL"
            elif total_beta_weighted > 0.5:
                exposure_level = "BULLISH"
            elif total_beta_weighted < -0.2:
                exposure_level = "BEARISH"
            else:
                exposure_level = "MODERATE"
            
            return {
                "alerts": alerts,
                "beta_weighted_exposure": total_beta_weighted,
                "exposure_level": exposure_level,
                "is_market_neutral": abs(total_beta_weighted) <= self.risk_thresholds["beta"]["neutral_range"]
            }
            
        except Exception as e:
            logger.error(f"Error analyzing beta risk: {e}")
            return {"alerts": [], "error": str(e)}
    
    def _calculate_overall_risk_score(self, concentration: Dict, sector: Dict, 
                                    correlation: Dict, volatility: Dict, beta: Dict) -> int:
        """Calculate overall portfolio risk score (0-100)."""
        try:
            score = 0
            
            # Concentration risk (0-25 points)
            hhi = concentration.get("herfindahl_index", 0)
            if hhi > 0.20:
                score += 25
            elif hhi > 0.15:
                score += 20
            elif hhi > 0.10:
                score += 15
            elif hhi > 0.08:
                score += 10
            else:
                score += 5
            
            # Sector risk (0-20 points)
            num_sectors = sector.get("num_sectors", 8)
            top_sector_weight = sector.get("top_sector_weight", 0)
            
            if num_sectors < 3:
                score += 15
            elif num_sectors < 5:
                score += 10
            else:
                score += 5
            
            if top_sector_weight > 0.5:
                score += 5
            
            # Correlation risk (0-20 points)
            high_corr_count = correlation.get("high_correlation_count", 0)
            market_corr = correlation.get("market_correlation", 0.7)
            
            if high_corr_count > 5:
                score += 15
            elif high_corr_count > 3:
                score += 10
            else:
                score += 5
            
            if market_corr > 0.9:
                score += 5
            
            # Volatility risk (0-20 points)
            portfolio_vol = volatility.get("portfolio_volatility", 0.2)
            high_vol_positions = len(volatility.get("high_vol_positions", []))
            
            if portfolio_vol > 0.35:
                score += 20
            elif portfolio_vol > 0.25:
                score += 15
            elif portfolio_vol > 0.20:
                score += 10
            else:
                score += 5
            
            # Beta risk (0-15 points)
            beta_exposure = abs(beta.get("beta_weighted_exposure", 0.5))
            
            if beta_exposure > 1.0:
                score += 15
            elif beta_exposure > 0.75:
                score += 10
            else:
                score += 5
            
            return min(100, score)
            
        except Exception as e:
            logger.error(f"Error calculating risk score: {e}")
            return 50  # Default medium risk
    
    def _get_risk_level(self, risk_score: int) -> str:
        """Convert risk score to risk level."""
        if risk_score >= 80:
            return "CRITICAL"
        elif risk_score >= 60:
            return "HIGH"
        elif risk_score >= 40:
            return "MEDIUM"
        elif risk_score >= 20:
            return "LOW"
        else:
            return "VERY_LOW"
    
    def _store_risk_history(self, risk_data: Dict[str, Any]):
        """Store risk analysis history."""
        try:
            self.risk_history.append(risk_data)
            
            # Keep only last 24 hours
            cutoff = datetime.now() - timedelta(hours=24)
            self.risk_history = [
                entry for entry in self.risk_history
                if entry["timestamp"] > cutoff
            ]
            
        except Exception as e:
            logger.error(f"Error storing risk history: {e}")
    
    def get_risk_trends(self, hours: int = 24) -> Dict[str, Any]:
        """Get risk trends over time."""
        try:
            if not self.risk_history:
                return {"error": "No risk history available"}
            
            cutoff = datetime.now() - timedelta(hours=hours)
            recent_history = [
                entry for entry in self.risk_history
                if entry["timestamp"] > cutoff
            ]
            
            if len(recent_history) < 2:
                return {"error": "Insufficient history for trends"}
            
            # Calculate trends
            risk_scores = [entry["risk_score"] for entry in recent_history]
            
            return {
                "period_hours": hours,
                "data_points": len(recent_history),
                "current_risk_score": risk_scores[-1],
                "avg_risk_score": statistics.mean(risk_scores),
                "min_risk_score": min(risk_scores),
                "max_risk_score": max(risk_scores),
                "risk_trend": "increasing" if risk_scores[-1] > risk_scores[0] else "decreasing",
                "volatility": statistics.stdev(risk_scores) if len(risk_scores) > 1 else 0
            }
            
        except Exception as e:
            logger.error(f"Error getting risk trends: {e}")
            return {"error": str(e)}


# Singleton instance
_portfolio_risk_monitor = None

def get_portfolio_risk_monitor():
    """Get or create portfolio risk monitor."""
    global _portfolio_risk_monitor
    if _portfolio_risk_monitor is None:
        _portfolio_risk_monitor = PortfolioRiskMonitor()
    return _portfolio_risk_monitor
