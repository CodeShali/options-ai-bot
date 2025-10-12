"""
Strategy Agent - Analyzes opportunities and generates trading signals.
"""
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
from loguru import logger

from agents.base_agent import BaseAgent
from services import get_llm_service, get_database_service
from services.sentiment_service import get_sentiment_service


class StrategyAgent(BaseAgent):
    """Agent responsible for strategy analysis and signal generation."""
    
    def __init__(self):
        """Initialize the strategy agent."""
        super().__init__("Strategy")
        self.llm = get_llm_service()
        self.db = get_database_service()
        self.sentiment = get_sentiment_service()
        self.sentiment.set_llm(self.llm)
    
    async def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process strategy analysis request.
        
        Args:
            data: Request data with 'action' and opportunity data
            
        Returns:
            Analysis result
        """
        action = data.get("action")
        
        if action == "analyze_opportunity":
            opportunity = data.get("opportunity")
            return await self.analyze_opportunity(opportunity)
        elif action == "analyze_exit":
            position = data.get("position")
            market_data = data.get("market_data")
            return await self.analyze_exit(position, market_data)
        elif action == "batch_analyze":
            opportunities = data.get("opportunities", [])
            return await self.batch_analyze(opportunities)
        else:
            return {"error": f"Unknown action: {action}"}
    
    async def analyze_opportunity(self, opportunity: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze a trading opportunity using AI.
        
        Args:
            opportunity: Opportunity data from data pipeline
            
        Returns:
            Analysis result with recommendation
        """
        try:
            symbol = opportunity['symbol']
            logger.info(f"Analyzing opportunity: {symbol}")
            
            # Prepare market data for LLM
            market_data = {
                "current_price": opportunity['current_price'],
                "price_change_pct": opportunity['price_change_pct'],
                "volume_ratio": opportunity['volume_ratio'],
                "sma_20": opportunity['sma_20'],
                "volume": opportunity['quote']['bid_size'] + opportunity['quote']['ask_size'],
                "high": max(bar['high'] for bar in opportunity['bars']),
                "low": min(bar['low'] for bar in opportunity['bars']),
                "prev_close": opportunity['bars'][-2]['close'] if len(opportunity['bars']) > 1 else None
            }
            
            # Calculate technical indicators
            technical_indicators = self._calculate_indicators(opportunity['bars'])
            
            # Get sentiment analysis
            sentiment_data = await self.sentiment.analyze_symbol_sentiment(symbol)
            
            # Get AI analysis
            analysis = await self.llm.analyze_market_opportunity(
                symbol,
                market_data,
                technical_indicators
            )
            
            # Adjust confidence based on sentiment
            original_confidence = analysis['confidence']
            adjusted_confidence, sentiment_reasoning = self.sentiment.should_boost_confidence(
                sentiment_data['overall_score'],
                original_confidence
            )
            
            # Update analysis with sentiment
            analysis['confidence'] = adjusted_confidence
            analysis['sentiment'] = sentiment_data
            analysis['sentiment_adjustment'] = {
                "original_confidence": original_confidence,
                "adjusted_confidence": adjusted_confidence,
                "reasoning": sentiment_reasoning
            }
            
            # Update reasoning with sentiment
            if sentiment_reasoning:
                analysis['reasoning'] += f" | Sentiment: {sentiment_reasoning}"
            
            # Record analysis in database
            await self.db.record_analysis(
                symbol=symbol,
                analysis_type="opportunity",
                recommendation=analysis['recommendation'],
                confidence=analysis['confidence'],
                risk_level=analysis['risk_level'],
                reasoning=analysis['reasoning'],
                market_data=str(market_data)
            )
            
            # Add opportunity data to result
            analysis['symbol'] = symbol
            analysis['opportunity'] = opportunity
            
            logger.info(
                f"Analysis complete for {symbol}: "
                f"{analysis['recommendation']} (confidence: {analysis['confidence']}%, "
                f"sentiment: {sentiment_data['overall_sentiment']})"
            )
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing opportunity: {e}")
            return {
                "symbol": opportunity.get('symbol', 'UNKNOWN'),
                "recommendation": "HOLD",
                "confidence": 0.0,
                "risk_level": "HIGH",
                "reasoning": f"Error during analysis: {str(e)}",
                "error": str(e)
            }
    
    async def analyze_exit(
        self,
        position: Dict[str, Any],
        market_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Analyze whether to exit a position.
        
        Args:
            position: Current position data
            market_data: Current market data
            
        Returns:
            Exit analysis result
        """
        try:
            symbol = position['symbol']
            logger.info(f"Analyzing exit for: {symbol}")
            
            # Get AI analysis
            analysis = await self.llm.analyze_exit_signal(
                symbol,
                position,
                market_data
            )
            
            # Record analysis
            await self.db.record_analysis(
                symbol=symbol,
                analysis_type="exit",
                recommendation=analysis['action'],
                confidence=analysis['confidence'],
                risk_level="N/A",
                reasoning=analysis['reasoning'],
                market_data=str(market_data)
            )
            
            analysis['symbol'] = symbol
            analysis['position'] = position
            
            logger.info(
                f"Exit analysis complete for {symbol}: "
                f"{analysis['action']} (confidence: {analysis['confidence']}%)"
            )
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing exit: {e}")
            return {
                "symbol": position.get('symbol', 'UNKNOWN'),
                "action": "HOLD",
                "confidence": 0.0,
                "reasoning": f"Error during analysis: {str(e)}",
                "error": str(e)
            }
    
    async def batch_analyze(self, opportunities: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze multiple opportunities in parallel.
        
        Args:
            opportunities: List of opportunities
            
        Returns:
            Batch analysis results
        """
        logger.info(f"Batch analyzing {len(opportunities)} opportunities")
        
        # Analyze in parallel with concurrency limit
        semaphore = asyncio.Semaphore(3)  # Max 3 concurrent analyses
        
        async def analyze_with_limit(opp):
            async with semaphore:
                return await self.analyze_opportunity(opp)
        
        tasks = [analyze_with_limit(opp) for opp in opportunities]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter successful analyses
        successful = []
        failed = []
        
        for result in results:
            if isinstance(result, Exception):
                failed.append(str(result))
            elif result.get('error'):
                failed.append(result['error'])
            else:
                successful.append(result)
        
        # Sort by confidence
        successful.sort(key=lambda x: x['confidence'], reverse=True)
        
        logger.info(
            f"Batch analysis complete: {len(successful)} successful, {len(failed)} failed"
        )
        
        return {
            "analyses": successful,
            "failed_count": len(failed),
            "total_count": len(opportunities),
            "timestamp": datetime.now().isoformat()
        }
    
    def _calculate_indicators(self, bars: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculate technical indicators from bars.
        
        Args:
            bars: Historical bar data
            
        Returns:
            Dictionary of indicators
        """
        if not bars:
            return {}
        
        closes = [bar['close'] for bar in bars]
        highs = [bar['high'] for bar in bars]
        lows = [bar['low'] for bar in bars]
        volumes = [bar['volume'] for bar in bars]
        
        indicators = {}
        
        # Moving averages
        if len(closes) >= 20:
            indicators['SMA_20'] = sum(closes[-20:]) / 20
        if len(closes) >= 50:
            indicators['SMA_50'] = sum(closes[-50:]) / 50
        
        # RSI (simplified)
        if len(closes) >= 14:
            gains = []
            losses = []
            for i in range(1, min(15, len(closes))):
                change = closes[-i] - closes[-i-1]
                if change > 0:
                    gains.append(change)
                else:
                    losses.append(abs(change))
            
            avg_gain = sum(gains) / 14 if gains else 0
            avg_loss = sum(losses) / 14 if losses else 0
            
            if avg_loss != 0:
                rs = avg_gain / avg_loss
                indicators['RSI'] = 100 - (100 / (1 + rs))
            else:
                indicators['RSI'] = 100
        
        # Volatility
        if len(closes) >= 20:
            mean = sum(closes[-20:]) / 20
            variance = sum((x - mean) ** 2 for x in closes[-20:]) / 20
            indicators['Volatility'] = variance ** 0.5
        
        # Volume trend
        if len(volumes) >= 20:
            indicators['Avg_Volume_20'] = sum(volumes[-20:]) / 20
            indicators['Volume_Ratio'] = volumes[-1] / indicators['Avg_Volume_20']
        
        # Price momentum
        if len(closes) >= 5:
            indicators['Momentum_5'] = ((closes[-1] - closes[-5]) / closes[-5]) * 100
        
        return indicators
    
    async def decide_instrument_type(self, analysis: Dict[str, Any], opportunity: Dict[str, Any]) -> Dict[str, Any]:
        """
        Decide whether to use stock or options based on signal strength.
        
        Args:
            analysis: AI analysis result
            opportunity: Opportunity data
            
        Returns:
            Instrument decision with details
        """
        from config import settings
        
        # Check if options trading is enabled
        if not settings.enable_options_trading:
            return {
                "instrument": "stock",
                "reasoning": "Options trading disabled"
            }
        
        confidence = analysis['confidence']
        recommendation = analysis['recommendation']
        score = opportunity.get('score', 0)
        
        # Strong bullish signal -> Call option
        if recommendation == "BUY" and confidence >= 75 and score >= 75:
            return {
                "instrument": "option",
                "option_type": "call",
                "reasoning": f"Strong bullish signal (confidence {confidence}%, score {score}) - use call option for leverage",
                "confidence": confidence
            }
        
        # Strong bearish signal -> Put option
        if recommendation == "SELL" and confidence >= 75 and score >= 75:
            return {
                "instrument": "option",
                "option_type": "put",
                "reasoning": f"Strong bearish signal (confidence {confidence}%, score {score}) - use put option for leverage",
                "confidence": confidence
            }
        
        # Moderate bullish signal -> Stock (safer)
        elif recommendation == "BUY" and confidence >= 60:
            if settings.enable_stock_trading:
                return {
                    "instrument": "stock",
                    "reasoning": f"Moderate bullish signal (confidence {confidence}%) - use stock for lower risk",
                    "confidence": confidence
                }
            else:
                return {
                    "instrument": "none",
                    "reasoning": "Stock trading disabled and signal not strong enough for options"
                }
        
        # Weak or unclear signal -> Skip
        else:
            return {
                "instrument": "none",
                "reasoning": f"Signal not strong enough ({recommendation}, {confidence}%)",
                "confidence": confidence
            }
    
    async def select_options_contract(self, symbol: str, option_type: str, 
                                     current_price: float) -> Dict[str, Any]:
        """
        Select optimal options contract (strike and expiration).
        
        Args:
            symbol: Stock symbol
            option_type: 'call' or 'put'
            current_price: Current stock price
            
        Returns:
            Selected contract details
        """
        from config import settings
        from services import get_alpaca_service
        from datetime import datetime, timedelta
        
        try:
            alpaca = get_alpaca_service()
            
            # Get options chain
            chain = await alpaca.get_options_chain(symbol)
            
            if 'error' in chain or not chain['expirations']:
                return {"error": "No options chain available"}
            
            # Select expiration (closest to middle of DTE range)
            target_dte = (settings.options_min_dte + settings.options_max_dte) / 2
            today = datetime.now()
            
            best_expiration = None
            best_dte_diff = float('inf')
            
            for exp_date_str in chain['expirations'].keys():
                exp_date = datetime.strptime(exp_date_str, "%Y-%m-%d")
                dte = (exp_date - today).days
                dte_diff = abs(dte - target_dte)
                
                if dte_diff < best_dte_diff:
                    best_dte_diff = dte_diff
                    best_expiration = exp_date_str
            
            if not best_expiration:
                return {"error": "No suitable expiration found"}
            
            # Select strike based on preference
            contracts = chain['expirations'][best_expiration]['calls' if option_type == 'call' else 'puts']
            
            if not contracts:
                return {"error": f"No {option_type} contracts available"}
            
            # Sort by strike
            contracts.sort(key=lambda x: x['strike'])
            
            # Select strike based on preference
            if settings.options_strike_preference == "ATM":
                # Find closest to current price
                selected = min(contracts, key=lambda x: abs(x['strike'] - current_price))
            
            elif settings.options_strike_preference == "OTM":
                # Find N strikes away
                if option_type == "call":
                    # For calls, OTM is above current price
                    otm_contracts = [c for c in contracts if c['strike'] > current_price]
                    if len(otm_contracts) >= settings.options_otm_strikes:
                        selected = otm_contracts[settings.options_otm_strikes - 1]
                    else:
                        selected = otm_contracts[-1] if otm_contracts else contracts[-1]
                else:
                    # For puts, OTM is below current price
                    otm_contracts = [c for c in contracts if c['strike'] < current_price]
                    if len(otm_contracts) >= settings.options_otm_strikes:
                        selected = otm_contracts[-(settings.options_otm_strikes)]
                    else:
                        selected = otm_contracts[0] if otm_contracts else contracts[0]
            
            else:  # ITM
                if option_type == "call":
                    itm_contracts = [c for c in contracts if c['strike'] < current_price]
                    selected = itm_contracts[-1] if itm_contracts else contracts[0]
                else:
                    itm_contracts = [c for c in contracts if c['strike'] > current_price]
                    selected = itm_contracts[0] if itm_contracts else contracts[-1]
            
            # Get quote for selected contract
            quote = await alpaca.get_option_quote(selected['symbol'])
            
            if not quote:
                return {"error": "Could not get option quote"}
            
            return {
                "symbol": selected['symbol'],
                "underlying": symbol,
                "strike": selected['strike'],
                "expiration": best_expiration,
                "option_type": option_type,
                "premium": quote['price'],
                "bid": quote['bid'],
                "ask": quote['ask'],
                "dte": (datetime.strptime(best_expiration, "%Y-%m-%d") - today).days
            }
            
        except Exception as e:
            logger.error(f"Error selecting options contract: {e}")
            return {"error": str(e)}
