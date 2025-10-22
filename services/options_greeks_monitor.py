"""
Options Greeks Monitor - Track Delta, Theta, Vega, Gamma for options positions.
"""
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from loguru import logger
import math

from services import get_alpaca_service, get_database_service
from config import settings


class OptionsGreeksMonitor:
    """Monitor options Greeks and generate intelligent alerts."""
    
    def __init__(self):
        """Initialize options Greeks monitor."""
        self.alpaca = get_alpaca_service()
        self.db = get_database_service()
        
        # Greeks thresholds
        self.thresholds = {
            "delta": {
                "otm_warning": 0.30,      # Warn when call delta < 0.30
                "deep_otm": 0.15,         # Critical when delta < 0.15
                "deep_itm": 0.85          # Very ITM when delta > 0.85
            },
            "theta": {
                "high_decay_pct": 0.05,   # Alert when theta > 5% of position value per day
                "acceleration_dte": 21,    # Theta accelerates under 21 DTE
                "critical_dte": 7          # Critical theta decay under 7 DTE
            },
            "vega": {
                "high_sensitivity": 0.20,  # High vega exposure
                "iv_crush_risk": 20,       # IV rank below 20th percentile
                "earnings_warning": 3      # Days before earnings
            },
            "gamma": {
                "high_risk": 0.10,        # High gamma (price very sensitive)
                "pin_risk_dte": 3,        # Pin risk under 3 DTE
                "pin_distance_pct": 0.02   # Within 2% of strike
            }
        }
        
        # Track Greeks history for trend analysis
        self.greeks_history = {}  # {symbol: [{"timestamp": ..., "greeks": ...}]}
    
    async def monitor_all_options_greeks(self) -> Dict[str, Any]:
        """Monitor Greeks for all options positions."""
        try:
            logger.info("📊 Monitoring options Greeks...")
            
            # Get options positions
            options_positions = await self.alpaca.get_option_positions()
            
            if not options_positions:
                return {
                    "options_monitored": 0,
                    "alerts": [],
                    "timestamp": datetime.now().isoformat()
                }
            
            alerts = []
            greeks_summary = []
            
            for position in options_positions:
                try:
                    # Get current Greeks
                    greeks = await self._get_option_greeks(position)
                    
                    if not greeks:
                        continue
                    
                    # Store Greeks history
                    self._store_greeks_history(position['symbol'], greeks)
                    
                    # Analyze each Greek
                    delta_alerts = await self._analyze_delta(position, greeks)
                    theta_alerts = await self._analyze_theta(position, greeks)
                    vega_alerts = await self._analyze_vega(position, greeks)
                    gamma_alerts = await self._analyze_gamma(position, greeks)
                    
                    # Combine alerts
                    position_alerts = delta_alerts + theta_alerts + vega_alerts + gamma_alerts
                    alerts.extend(position_alerts)
                    
                    # Summary for dashboard
                    greeks_summary.append({
                        "symbol": position['symbol'],
                        "underlying": position['underlying'],
                        "greeks": greeks,
                        "alerts_count": len(position_alerts),
                        "risk_level": self._calculate_risk_level(position, greeks)
                    })
                    
                except Exception as e:
                    logger.error(f"Error monitoring Greeks for {position.get('symbol', 'unknown')}: {e}")
                    continue
            
            logger.info(f"📊 Greeks monitoring complete: {len(options_positions)} options, {len(alerts)} alerts")
            
            return {
                "options_monitored": len(options_positions),
                "alerts": alerts,
                "greeks_summary": greeks_summary,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error monitoring options Greeks: {e}")
            return {
                "error": str(e),
                "options_monitored": 0,
                "alerts": []
            }
    
    async def _get_option_greeks(self, position: Dict[str, Any]) -> Optional[Dict[str, float]]:
        """Get Greeks for an options position."""
        try:
            # Try to get from Alpaca first
            greeks_data = await self.alpaca.get_option_greeks(position['symbol'])
            
            if greeks_data:
                return greeks_data
            
            # Fallback: Calculate approximate Greeks
            return await self._calculate_approximate_greeks(position)
            
        except Exception as e:
            logger.error(f"Error getting Greeks for {position['symbol']}: {e}")
            return None
    
    async def _calculate_approximate_greeks(self, position: Dict[str, Any]) -> Dict[str, float]:
        """Calculate approximate Greeks using Black-Scholes approximation."""
        try:
            # Get required data
            underlying_price = position.get('underlying_price', 0)
            strike = position.get('strike', 0)
            dte = position.get('dte', 0)
            option_type = position.get('option_type', 'call').lower()
            
            if not all([underlying_price, strike, dte]):
                return {}
            
            # Simple approximations (not exact Black-Scholes)
            moneyness = underlying_price / strike
            time_factor = math.sqrt(dte / 365.0) if dte > 0 else 0.01
            
            # Delta approximation
            if option_type == 'call':
                delta = max(0.01, min(0.99, moneyness - 0.5 + 0.5))
            else:  # put
                delta = max(-0.99, min(-0.01, moneyness - 1.5))
            
            # Theta approximation (higher for shorter DTE)
            theta = -0.05 * (1 / max(time_factor, 0.01)) * (1 / max(dte, 1))
            
            # Vega approximation (higher for ATM)
            vega = 0.3 * time_factor * (1 - abs(moneyness - 1) * 2)
            
            # Gamma approximation (higher for ATM and short DTE)
            gamma = 0.1 * (1 - abs(moneyness - 1) * 3) * (1 / max(time_factor, 0.01))
            
            return {
                "delta": round(delta, 4),
                "theta": round(theta, 4),
                "vega": round(vega, 4),
                "gamma": round(gamma, 4)
            }
            
        except Exception as e:
            logger.error(f"Error calculating approximate Greeks: {e}")
            return {}
    
    async def _analyze_delta(self, position: Dict[str, Any], greeks: Dict[str, float]) -> List[Dict[str, Any]]:
        """Analyze Delta and generate alerts."""
        alerts = []
        
        try:
            delta = greeks.get('delta', 0)
            option_type = position.get('option_type', 'call').lower()
            symbol = position['underlying']
            
            # Call options Delta analysis
            if option_type == 'call':
                if 0 < delta < self.thresholds["delta"]["deep_otm"]:
                    alerts.append({
                        "type": "DELTA_DEEP_OTM",
                        "symbol": symbol,
                        "option_symbol": position['symbol'],
                        "message": f"⚠️ {symbol} call going deep OTM - Delta {delta:.3f}",
                        "reasoning": f"Call option Delta dropped to {delta:.3f} (< {self.thresholds['delta']['deep_otm']}). "
                                   f"Option losing directional sensitivity. Consider closing if no recovery expected.",
                        "severity": "WARNING",
                        "delta": delta,
                        "action_required": "REVIEW_CLOSE"
                    })
                
                elif 0 < delta < self.thresholds["delta"]["otm_warning"]:
                    alerts.append({
                        "type": "DELTA_OTM_WARNING",
                        "symbol": symbol,
                        "option_symbol": position['symbol'],
                        "message": f"📉 {symbol} call Delta declining - {delta:.3f}",
                        "reasoning": f"Call Delta at {delta:.3f} (< {self.thresholds['delta']['otm_warning']}). "
                                   f"Option becoming less sensitive to stock moves. Monitor closely.",
                        "severity": "INFO",
                        "delta": delta,
                        "action_required": "MONITOR"
                    })
                
                elif delta > self.thresholds["delta"]["deep_itm"]:
                    alerts.append({
                        "type": "DELTA_DEEP_ITM",
                        "symbol": symbol,
                        "option_symbol": position['symbol'],
                        "message": f"💎 {symbol} call deep ITM - Delta {delta:.3f}",
                        "reasoning": f"Call Delta at {delta:.3f} (> {self.thresholds['delta']['deep_itm']}). "
                                   f"Option moving almost 1:1 with stock. Consider taking profits or rolling.",
                        "severity": "INFO",
                        "delta": delta,
                        "action_required": "CONSIDER_PROFITS"
                    })
            
            # Put options Delta analysis
            elif option_type == 'put':
                abs_delta = abs(delta)
                
                if 0 < abs_delta < self.thresholds["delta"]["deep_otm"]:
                    alerts.append({
                        "type": "DELTA_DEEP_OTM",
                        "symbol": symbol,
                        "option_symbol": position['symbol'],
                        "message": f"⚠️ {symbol} put going deep OTM - Delta {delta:.3f}",
                        "reasoning": f"Put option Delta at {delta:.3f} (abs < {self.thresholds['delta']['deep_otm']}). "
                                   f"Option losing directional sensitivity. Consider closing.",
                        "severity": "WARNING",
                        "delta": delta,
                        "action_required": "REVIEW_CLOSE"
                    })
                
                elif abs_delta > self.thresholds["delta"]["deep_itm"]:
                    alerts.append({
                        "type": "DELTA_DEEP_ITM",
                        "symbol": symbol,
                        "option_symbol": position['symbol'],
                        "message": f"💎 {symbol} put deep ITM - Delta {delta:.3f}",
                        "reasoning": f"Put Delta at {delta:.3f} (abs > {self.thresholds['delta']['deep_itm']}). "
                                   f"Option moving almost 1:1 with stock. Consider profits.",
                        "severity": "INFO",
                        "delta": delta,
                        "action_required": "CONSIDER_PROFITS"
                    })
            
        except Exception as e:
            logger.error(f"Error analyzing Delta: {e}")
        
        return alerts
    
    async def _analyze_theta(self, position: Dict[str, Any], greeks: Dict[str, float]) -> List[Dict[str, Any]]:
        """Analyze Theta (time decay) and generate alerts."""
        alerts = []
        
        try:
            theta = greeks.get('theta', 0)
            dte = position.get('dte', 0)
            position_value = position.get('market_value', 0)
            contracts = position.get('contracts', 1)
            symbol = position['underlying']
            
            # Calculate daily theta decay in dollars
            daily_theta_cost = abs(theta) * contracts * 100  # Theta is per share, 100 shares per contract
            
            # Theta as percentage of position value
            if position_value > 0:
                theta_pct = daily_theta_cost / position_value
                
                # High theta decay alert
                if theta_pct > self.thresholds["theta"]["high_decay_pct"]:
                    alerts.append({
                        "type": "HIGH_THETA_DECAY",
                        "symbol": symbol,
                        "option_symbol": position['symbol'],
                        "message": f"💸 {symbol} high theta decay - ${daily_theta_cost:.2f}/day",
                        "reasoning": f"Daily theta decay is ${daily_theta_cost:.2f} ({theta_pct*100:.1f}% of position value). "
                                   f"Position losing {theta_pct*100:.1f}% per day to time decay. "
                                   f"Consider closing if no strong directional move expected.",
                        "severity": "WARNING",
                        "theta": theta,
                        "daily_cost": daily_theta_cost,
                        "theta_pct": theta_pct * 100,
                        "action_required": "REVIEW_TIME_DECAY"
                    })
            
            # Theta acceleration alerts based on DTE
            if dte <= self.thresholds["theta"]["critical_dte"]:
                alerts.append({
                    "type": "THETA_ACCELERATION_CRITICAL",
                    "symbol": symbol,
                    "option_symbol": position['symbol'],
                    "message": f"⏰ {symbol} critical theta acceleration - {dte} DTE",
                    "reasoning": f"Only {dte} days to expiration. Theta decay accelerating rapidly. "
                               f"Daily cost: ${daily_theta_cost:.2f}. Close soon to avoid total loss.",
                    "severity": "CRITICAL",
                    "dte": dte,
                    "daily_cost": daily_theta_cost,
                    "action_required": "CLOSE_SOON"
                })
            
            elif dte <= self.thresholds["theta"]["acceleration_dte"]:
                alerts.append({
                    "type": "THETA_ACCELERATION",
                    "symbol": symbol,
                    "option_symbol": position['symbol'],
                    "message": f"⏰ {symbol} theta acceleration - {dte} DTE",
                    "reasoning": f"{dte} days to expiration. Theta decay accelerating. "
                               f"Daily cost: ${daily_theta_cost:.2f}. Monitor closely.",
                    "severity": "WARNING",
                    "dte": dte,
                    "daily_cost": daily_theta_cost,
                    "action_required": "MONITOR_CLOSELY"
                })
            
        except Exception as e:
            logger.error(f"Error analyzing Theta: {e}")
        
        return alerts
    
    async def _analyze_vega(self, position: Dict[str, Any], greeks: Dict[str, float]) -> List[Dict[str, Any]]:
        """Analyze Vega (IV sensitivity) and generate alerts."""
        alerts = []
        
        try:
            vega = greeks.get('vega', 0)
            symbol = position['underlying']
            
            # Get IV rank if available
            iv_rank = position.get('iv_rank', 50)  # Default to 50th percentile
            
            # High Vega exposure
            if abs(vega) > self.thresholds["vega"]["high_sensitivity"]:
                alerts.append({
                    "type": "HIGH_VEGA_EXPOSURE",
                    "symbol": symbol,
                    "option_symbol": position['symbol'],
                    "message": f"📊 {symbol} high IV sensitivity - Vega {vega:.3f}",
                    "reasoning": f"High Vega exposure ({vega:.3f}). Position very sensitive to IV changes. "
                               f"Current IV rank: {iv_rank}th percentile. Monitor for IV crush risk.",
                    "severity": "INFO",
                    "vega": vega,
                    "iv_rank": iv_rank,
                    "action_required": "MONITOR_IV"
                })
            
            # IV crush risk
            if abs(vega) > 0.15 and iv_rank < self.thresholds["vega"]["iv_crush_risk"]:
                alerts.append({
                    "type": "IV_CRUSH_RISK",
                    "symbol": symbol,
                    "option_symbol": position['symbol'],
                    "message": f"💨 {symbol} IV crush risk - Low IV with high Vega",
                    "reasoning": f"IV at {iv_rank}th percentile (low) with high Vega ({vega:.3f}). "
                               f"Risk of further IV compression. Consider closing before events.",
                    "severity": "WARNING",
                    "vega": vega,
                    "iv_rank": iv_rank,
                    "action_required": "CONSIDER_CLOSE"
                })
            
            # Check for upcoming earnings (if available)
            # This would need earnings calendar integration
            # For now, we'll use a placeholder
            
        except Exception as e:
            logger.error(f"Error analyzing Vega: {e}")
        
        return alerts
    
    async def _analyze_gamma(self, position: Dict[str, Any], greeks: Dict[str, float]) -> List[Dict[str, Any]]:
        """Analyze Gamma (Delta sensitivity) and generate alerts."""
        alerts = []
        
        try:
            gamma = greeks.get('gamma', 0)
            dte = position.get('dte', 0)
            underlying_price = position.get('underlying_price', 0)
            strike = position.get('strike', 0)
            symbol = position['underlying']
            
            # High Gamma risk
            if abs(gamma) > self.thresholds["gamma"]["high_risk"]:
                alerts.append({
                    "type": "HIGH_GAMMA_RISK",
                    "symbol": symbol,
                    "option_symbol": position['symbol'],
                    "message": f"🎢 {symbol} high gamma - Very price sensitive",
                    "reasoning": f"High Gamma ({gamma:.3f}) means Delta changes rapidly with price moves. "
                               f"Position can gain/lose value quickly. Monitor closely for volatility.",
                    "severity": "INFO",
                    "gamma": gamma,
                    "action_required": "MONITOR_VOLATILITY"
                })
            
            # Pin risk near expiration
            if dte <= self.thresholds["gamma"]["pin_risk_dte"] and underlying_price > 0 and strike > 0:
                distance_to_strike = abs(underlying_price - strike)
                distance_pct = distance_to_strike / strike
                
                if distance_pct < self.thresholds["gamma"]["pin_distance_pct"]:
                    alerts.append({
                        "type": "PIN_RISK",
                        "symbol": symbol,
                        "option_symbol": position['symbol'],
                        "message": f"📍 {symbol} pin risk - Near strike at expiration",
                        "reasoning": f"Stock at ${underlying_price:.2f}, strike at ${strike:.2f} "
                                   f"({distance_pct*100:.1f}% away) with {dte} DTE. "
                                   f"Pin risk: stock may be held near strike by market makers.",
                        "severity": "WARNING",
                        "underlying_price": underlying_price,
                        "strike": strike,
                        "distance_pct": distance_pct * 100,
                        "dte": dte,
                        "action_required": "CONSIDER_CLOSE"
                    })
            
        except Exception as e:
            logger.error(f"Error analyzing Gamma: {e}")
        
        return alerts
    
    def _store_greeks_history(self, symbol: str, greeks: Dict[str, float]):
        """Store Greeks history for trend analysis."""
        try:
            if symbol not in self.greeks_history:
                self.greeks_history[symbol] = []
            
            # Add current Greeks
            self.greeks_history[symbol].append({
                "timestamp": datetime.now(),
                "greeks": greeks.copy()
            })
            
            # Keep only last 24 hours of data
            cutoff = datetime.now() - timedelta(hours=24)
            self.greeks_history[symbol] = [
                entry for entry in self.greeks_history[symbol]
                if entry["timestamp"] > cutoff
            ]
            
        except Exception as e:
            logger.error(f"Error storing Greeks history: {e}")
    
    def _calculate_risk_level(self, position: Dict[str, Any], greeks: Dict[str, float]) -> str:
        """Calculate overall risk level for the position."""
        try:
            risk_score = 0
            
            # Delta risk
            delta = abs(greeks.get('delta', 0))
            if delta < 0.15:
                risk_score += 3  # High risk - deep OTM
            elif delta > 0.85:
                risk_score += 1  # Low risk - deep ITM
            
            # Theta risk
            dte = position.get('dte', 30)
            if dte <= 7:
                risk_score += 3  # High risk - near expiration
            elif dte <= 21:
                risk_score += 2  # Medium risk
            
            # Vega risk
            vega = abs(greeks.get('vega', 0))
            iv_rank = position.get('iv_rank', 50)
            if vega > 0.20 and iv_rank < 20:
                risk_score += 2  # IV crush risk
            
            # Gamma risk
            gamma = abs(greeks.get('gamma', 0))
            if gamma > 0.10:
                risk_score += 1  # High volatility sensitivity
            
            # Determine risk level
            if risk_score >= 6:
                return "CRITICAL"
            elif risk_score >= 4:
                return "HIGH"
            elif risk_score >= 2:
                return "MEDIUM"
            else:
                return "LOW"
            
        except Exception as e:
            logger.error(f"Error calculating risk level: {e}")
            return "UNKNOWN"
    
    def get_greeks_summary(self, symbol: str) -> Dict[str, Any]:
        """Get Greeks summary for a specific option."""
        try:
            if symbol not in self.greeks_history or not self.greeks_history[symbol]:
                return {"error": "No Greeks history found"}
            
            latest = self.greeks_history[symbol][-1]
            history = self.greeks_history[symbol]
            
            # Calculate trends if we have enough data
            trends = {}
            if len(history) >= 2:
                prev = history[-2]["greeks"]
                current = latest["greeks"]
                
                for greek in ["delta", "theta", "vega", "gamma"]:
                    if greek in prev and greek in current:
                        change = current[greek] - prev[greek]
                        trends[f"{greek}_change"] = change
                        trends[f"{greek}_trend"] = "increasing" if change > 0 else "decreasing" if change < 0 else "stable"
            
            return {
                "symbol": symbol,
                "latest_greeks": latest["greeks"],
                "last_updated": latest["timestamp"].isoformat(),
                "trends": trends,
                "history_points": len(history)
            }
            
        except Exception as e:
            logger.error(f"Error getting Greeks summary: {e}")
            return {"error": str(e)}


# Singleton instance
_options_greeks_monitor = None

def get_options_greeks_monitor():
    """Get or create options Greeks monitor."""
    global _options_greeks_monitor
    if _options_greeks_monitor is None:
        _options_greeks_monitor = OptionsGreeksMonitor()
    return _options_greeks_monitor
