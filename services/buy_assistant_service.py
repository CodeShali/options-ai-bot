"""
Buy Assistant Service - Helps users find and execute optimal buy orders.
Includes stock and options buying with Greeks analysis.
"""
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from loguru import logger

from services import get_alpaca_service, get_llm_service


class BuyAssistantService:
    """Service to assist with buying stocks and options."""
    
    def __init__(self):
        """Initialize buy assistant service."""
        self.alpaca = get_alpaca_service()
        self.llm = get_llm_service()
        logger.info("💰 Buy Assistant Service initialized")
    
    async def analyze_buy_opportunity(self, symbol: str) -> Dict[str, Any]:
        """
        Analyze if a symbol is a good buy opportunity.
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Analysis with recommendation
        """
        try:
            # Get current quote
            quote = await self.alpaca.get_latest_quote(symbol)
            if not quote:
                return {"error": "Could not fetch quote"}
            
            # Get snapshot for more data
            snapshot = await self.alpaca.get_snapshot(symbol)
            
            # Get account info
            account = await self.alpaca.get_account()
            buying_power = float(account.get("buying_power", 0))
            
            current_price = float(quote.get("price", 0))
            
            return {
                "symbol": symbol,
                "current_price": current_price,
                "buying_power": buying_power,
                "max_shares": int(buying_power / current_price) if current_price > 0 else 0,
                "snapshot": snapshot,
                "recommendation": "ANALYZE"  # Will be filled by AI
            }
            
        except Exception as e:
            logger.error(f"Error analyzing buy opportunity for {symbol}: {e}")
            return {"error": str(e)}
    
    async def find_best_options(
        self,
        symbol: str,
        strategy: str = "call",
        max_risk: float = 1000.0,
        target_delta: float = 0.5
    ) -> List[Dict[str, Any]]:
        """
        Find best options contracts based on Greeks and risk parameters.
        
        Args:
            symbol: Stock symbol
            strategy: 'call' or 'put'
            max_risk: Maximum risk per contract
            target_delta: Target delta (0.3-0.7 for moderate risk)
            
        Returns:
            List of recommended options contracts
        """
        try:
            logger.info(f"🔍 Finding best {strategy} options for {symbol}...")
            
            # Get options chain
            options_chain = await self.alpaca.get_options_chain(symbol)
            if not options_chain:
                return []
            
            # Filter by strategy
            filtered_options = [
                opt for opt in options_chain
                if opt.get("type", "").lower() == strategy.lower()
            ]
            
            # Get current stock price
            quote = await self.alpaca.get_latest_quote(symbol)
            current_price = float(quote.get("price", 0))
            
            # Score and rank options
            scored_options = []
            for option in filtered_options:
                try:
                    # Get Greeks
                    greeks = option.get("greeks", {})
                    delta = abs(float(greeks.get("delta", 0)))
                    theta = float(greeks.get("theta", 0))
                    vega = float(greeks.get("vega", 0))
                    gamma = float(greeks.get("gamma", 0))
                    
                    # Get pricing
                    ask_price = float(option.get("ask", 0))
                    bid_price = float(option.get("bid", 0))
                    mid_price = (ask_price + bid_price) / 2
                    
                    # Get strike and expiration
                    strike = float(option.get("strike", 0))
                    expiration = option.get("expiration_date", "")
                    
                    # Calculate days to expiration
                    try:
                        exp_date = datetime.fromisoformat(expiration.replace("Z", "+00:00"))
                        days_to_exp = (exp_date - datetime.now()).days
                    except:
                        days_to_exp = 0
                    
                    # Skip if too expensive
                    contract_cost = mid_price * 100  # Options are per 100 shares
                    if contract_cost > max_risk:
                        continue
                    
                    # Skip if expiring too soon (less than 7 days) or too far (more than 90 days)
                    if days_to_exp < 7 or days_to_exp > 90:
                        continue
                    
                    # Calculate moneyness
                    if strategy.lower() == "call":
                        moneyness = (strike - current_price) / current_price
                    else:
                        moneyness = (current_price - strike) / current_price
                    
                    # Score the option (higher is better)
                    score = 0
                    
                    # Delta score (prefer target delta)
                    delta_diff = abs(delta - target_delta)
                    score += (1 - delta_diff) * 30  # 30 points max
                    
                    # Theta score (prefer lower theta decay for safer trades)
                    theta_score = max(0, 1 - abs(theta) / 0.1) * 20  # 20 points max
                    score += theta_score
                    
                    # Moneyness score (prefer slightly OTM for better risk/reward)
                    if -0.05 <= moneyness <= 0.05:  # Near ATM
                        score += 25
                    elif 0.05 < moneyness <= 0.10:  # Slightly OTM
                        score += 30
                    elif -0.10 <= moneyness < -0.05:  # Slightly ITM
                        score += 20
                    
                    # Days to expiration score (prefer 30-45 days)
                    if 30 <= days_to_exp <= 45:
                        score += 20
                    elif 20 <= days_to_exp < 30 or 45 < days_to_exp <= 60:
                        score += 15
                    
                    # Liquidity score (prefer tighter bid-ask spread)
                    if mid_price > 0:
                        spread_pct = (ask_price - bid_price) / mid_price
                        liquidity_score = max(0, 1 - spread_pct) * 5  # 5 points max
                        score += liquidity_score
                    
                    scored_options.append({
                        "symbol": option.get("symbol"),
                        "strike": strike,
                        "expiration": expiration,
                        "days_to_exp": days_to_exp,
                        "type": strategy,
                        "bid": bid_price,
                        "ask": ask_price,
                        "mid_price": mid_price,
                        "contract_cost": contract_cost,
                        "delta": delta,
                        "theta": theta,
                        "gamma": gamma,
                        "vega": vega,
                        "moneyness": moneyness,
                        "score": score,
                        "risk_level": self._assess_risk_level(delta, days_to_exp, moneyness),
                        "recommendation": self._generate_recommendation(delta, theta, moneyness, days_to_exp)
                    })
                    
                except Exception as e:
                    logger.debug(f"Error scoring option: {e}")
                    continue
            
            # Sort by score (highest first)
            scored_options.sort(key=lambda x: x["score"], reverse=True)
            
            # Return top 5
            top_options = scored_options[:5]
            
            logger.info(f"✅ Found {len(top_options)} recommended options for {symbol}")
            return top_options
            
        except Exception as e:
            logger.error(f"Error finding best options for {symbol}: {e}")
            return []
    
    def _assess_risk_level(self, delta: float, days_to_exp: int, moneyness: float) -> str:
        """Assess risk level of an option."""
        risk_score = 0
        
        # Delta risk
        if delta < 0.3:
            risk_score += 2  # High risk (far OTM)
        elif delta < 0.5:
            risk_score += 1  # Medium risk
        else:
            risk_score += 0  # Lower risk (closer to ITM)
        
        # Time risk
        if days_to_exp < 14:
            risk_score += 2  # High risk (expiring soon)
        elif days_to_exp < 30:
            risk_score += 1  # Medium risk
        
        # Moneyness risk
        if abs(moneyness) > 0.10:
            risk_score += 1  # Higher risk (far from ATM)
        
        if risk_score >= 4:
            return "HIGH"
        elif risk_score >= 2:
            return "MODERATE"
        else:
            return "LOW"
    
    def _generate_recommendation(self, delta: float, theta: float, moneyness: float, days_to_exp: int) -> str:
        """Generate recommendation text for an option."""
        recommendations = []
        
        if 0.4 <= delta <= 0.6:
            recommendations.append("Good delta for balanced risk/reward")
        elif delta > 0.7:
            recommendations.append("High delta - moves with stock closely")
        elif delta < 0.3:
            recommendations.append("Low delta - higher risk, higher reward potential")
        
        if days_to_exp >= 30:
            recommendations.append("Good time value")
        else:
            recommendations.append("Watch time decay")
        
        if -0.05 <= moneyness <= 0.05:
            recommendations.append("Near the money - balanced position")
        elif moneyness > 0.05:
            recommendations.append("Out of the money - speculative")
        else:
            recommendations.append("In the money - more conservative")
        
        return " | ".join(recommendations)
    
    async def execute_stock_buy(
        self,
        symbol: str,
        quantity: int,
        order_type: str = "market",
        limit_price: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Execute a stock buy order.
        
        Args:
            symbol: Stock symbol
            quantity: Number of shares
            order_type: 'market' or 'limit'
            limit_price: Limit price (required for limit orders)
            
        Returns:
            Order result
        """
        try:
            logger.info(f"💰 Executing BUY order: {quantity} shares of {symbol}")
            
            # Validate buying power
            account = await self.alpaca.get_account()
            buying_power = float(account.get("buying_power", 0))
            
            quote = await self.alpaca.get_latest_quote(symbol)
            estimated_cost = float(quote.get("price", 0)) * quantity
            
            if estimated_cost > buying_power:
                return {
                    "success": False,
                    "error": f"Insufficient buying power. Need ${estimated_cost:,.2f}, have ${buying_power:,.2f}"
                }
            
            # Place order
            order = await self.alpaca.place_order(
                symbol=symbol,
                qty=quantity,
                side="buy",
                type=order_type,
                limit_price=limit_price
            )
            
            if order:
                logger.info(f"✅ Buy order placed: {order.get('id')}")
                return {
                    "success": True,
                    "order": order,
                    "estimated_cost": estimated_cost
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to place order"
                }
            
        except Exception as e:
            logger.error(f"Error executing stock buy: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def execute_option_buy(
        self,
        option_symbol: str,
        quantity: int = 1,
        order_type: str = "market",
        limit_price: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Execute an option buy order.
        
        Args:
            option_symbol: Option contract symbol
            quantity: Number of contracts
            order_type: 'market' or 'limit'
            limit_price: Limit price per contract
            
        Returns:
            Order result
        """
        try:
            logger.info(f"💰 Executing OPTION BUY: {quantity} contracts of {option_symbol}")
            
            # Place order
            order = await self.alpaca.place_order(
                symbol=option_symbol,
                qty=quantity,
                side="buy",
                type=order_type,
                limit_price=limit_price
            )
            
            if order:
                logger.info(f"✅ Option buy order placed: {order.get('id')}")
                return {
                    "success": True,
                    "order": order
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to place option order"
                }
            
        except Exception as e:
            logger.error(f"Error executing option buy: {e}")
            return {
                "success": False,
                "error": str(e)
            }


# Global instance
_buy_assistant_service: Optional[BuyAssistantService] = None


def get_buy_assistant_service() -> BuyAssistantService:
    """Get the global buy assistant service instance."""
    global _buy_assistant_service
    if _buy_assistant_service is None:
        _buy_assistant_service = BuyAssistantService()
    return _buy_assistant_service
