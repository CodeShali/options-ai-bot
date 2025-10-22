"""
Strategy Agent - Analyzes opportunities and generates trading signals.
"""
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
from loguru import logger

from agents.base_agent import BaseAgent
from services import get_llm_service, get_database_service, get_alpaca_service
from services.sentiment_service import get_sentiment_service
from services.news_service import get_news_service
from config import settings

# Import quantitative strategies
try:
    from strategies.strategy_manager import StrategyManager
    STRATEGIES_AVAILABLE = True
except ImportError:
    STRATEGIES_AVAILABLE = False
    logger.warning("Quantitative strategies not available")


class StrategyAgent(BaseAgent):
    """Agent responsible for strategy analysis and signal generation."""
    
    def __init__(self):
        """Initialize the strategy agent."""
        super().__init__("Strategy")
        self.llm = get_llm_service()
        self.db = get_database_service()
        self.alpaca = get_alpaca_service()
        self.news = get_news_service()
        self.sentiment = get_sentiment_service()
        self.sentiment.set_llm(self.llm)
        self.sentiment.set_alpaca(self.alpaca)
        self.sentiment.set_news(self.news)
        
        # Initialize quantitative strategies
        if STRATEGIES_AVAILABLE:
            self.strategy_manager = StrategyManager()
            logger.info("✅ Quantitative strategies enabled")
        else:
            self.strategy_manager = None
            logger.warning("⚠️ Running without quantitative strategies")
    
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
        Analyze a trading opportunity using quantitative strategies + AI.
        
        Args:
            opportunity: Opportunity data from data pipeline
            
        Returns:
            Analysis result with recommendation
        """
        try:
            symbol = opportunity['symbol']
            logger.info(f"Analyzing opportunity: {symbol}")
            
            # STEP 1: Try quantitative strategies first
            quant_signal = None
            if self.strategy_manager:
                quant_signal = await self._analyze_with_quant_strategies(opportunity)
                
                # If quantitative strategies give strong signal, use it
                if quant_signal and quant_signal.get('action') in ['BUY', 'SELL']:
                    logger.info(f"✅ Quantitative signal for {symbol}: {quant_signal['action']} ({quant_signal.get('strategy')})")
                    return self._format_quant_signal(quant_signal, symbol)
            
            # STEP 2: Fall back to AI analysis if no quant signal
            logger.info(f"Using AI analysis for {symbol} (no strong quant signal)")
            
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
            
            # Determine trade type based on market conditions
            trade_type = self._determine_trade_type(opportunity, technical_indicators, sentiment_data)
            logger.info(f"Trade type for {symbol}: {trade_type}")
            
            # Get AI analysis with trade type specific prompt
            analysis = await self._analyze_with_trade_type(
                symbol,
                market_data,
                technical_indicators,
                sentiment_data,
                trade_type
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
            
            # Add trade type and targets
            analysis['trade_type'] = trade_type
            targets = self._get_targets_for_trade_type(trade_type, market_data['current_price'])
            analysis['profit_target'] = targets['target_price']
            analysis['stop_loss'] = targets['stop_price']
            analysis['max_hold_minutes'] = targets['max_hold_minutes']
            analysis['target_pct'] = targets['target_pct']
            analysis['stop_pct'] = targets['stop_pct']
            
            # Update reasoning with sentiment and trade type
            if sentiment_reasoning:
                analysis['reasoning'] += f" | Sentiment: {sentiment_reasoning}"
            analysis['reasoning'] += f" | Trade Type: {trade_type.upper()} (Target: {targets['target_pct']*100:.1f}%, Stop: {targets['stop_pct']*100:.1f}%)"
            
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
    
    def _determine_trade_type(self, opportunity: Dict[str, Any], 
                             technical_indicators: Dict[str, Any],
                             sentiment_data: Dict[str, Any]) -> str:
        """
        Determine trade type (scalp, day_trade, swing) based on conditions.
        
        Args:
            opportunity: Opportunity data
            technical_indicators: Technical indicators
            sentiment_data: Sentiment analysis
            
        Returns:
            Trade type: 'scalp', 'day_trade', or 'swing'
        """
        score = opportunity.get('score', 0)
        volatility = technical_indicators.get('Volatility', 0)
        volume_ratio = opportunity.get('volume_ratio', 1.0)
        momentum = abs(technical_indicators.get('Momentum_5', 0))
        sentiment_score = abs(sentiment_data.get('overall_score', 0))
        
        # Check if aggressive mode is enabled
        aggressive_mode = getattr(settings, 'scan_interval', 300) <= 60
        
        # Scalping criteria (only in aggressive mode)
        if aggressive_mode and (
            score >= 80 and
            volatility > 2.0 and
            volume_ratio > 2.0 and
            momentum > 2.0 and
            sentiment_score > 0.6
        ):
            return 'scalp'
        
        # Day trading criteria
        elif aggressive_mode and (
            score >= 70 and
            volume_ratio > 1.5 and
            (momentum > 1.0 or sentiment_score > 0.4)
        ):
            return 'day_trade'
        
        # Default to swing trading
        else:
            return 'swing'
    
    def _get_targets_for_trade_type(self, trade_type: str, entry_price: float) -> Dict[str, Any]:
        """
        Get profit target and stop loss based on trade type.
        
        Args:
            trade_type: Trade type (scalp, day_trade, swing)
            entry_price: Entry price
            
        Returns:
            Dictionary with target and stop prices
        """
        if trade_type == 'scalp':
            target_pct = getattr(settings, 'scalp_target_pct', 0.015)  # 1.5%
            stop_pct = getattr(settings, 'tight_stop_pct', 0.01)  # 1%
            max_hold = getattr(settings, 'scalp_hold_time_minutes', 30)
        elif trade_type == 'day_trade':
            target_pct = getattr(settings, 'target_profit_pct', 0.03)  # 3%
            stop_pct = getattr(settings, 'stop_loss_pct_day', 0.015)  # 1.5%
            max_hold = getattr(settings, 'max_hold_time_minutes', 120)
        else:  # swing
            target_pct = 0.50  # 50%
            stop_pct = 0.30  # 30%
            max_hold = None
        
        return {
            'target_price': entry_price * (1 + target_pct),
            'stop_price': entry_price * (1 - stop_pct),
            'target_pct': target_pct,
            'stop_pct': stop_pct,
            'max_hold_minutes': max_hold
        }
    
    async def _analyze_with_trade_type(self,
                                      symbol: str,
                                      market_data: Dict[str, Any],
                                      technical_indicators: Dict[str, Any],
                                      sentiment_data: Dict[str, Any],
                                      trade_type: str) -> Dict[str, Any]:
        """
        Analyze opportunity with trade type specific AI prompt.
        
        Args:
            symbol: Stock symbol
            market_data: Market data
            technical_indicators: Technical indicators
            sentiment_data: Sentiment data
            trade_type: Trade type (scalp, day_trade, swing)
            
        Returns:
            AI analysis result
        """
        current_price = market_data['current_price']
        targets = self._get_targets_for_trade_type(trade_type, current_price)
        
        # Build trade type specific prompt
        if trade_type == 'scalp':
            prompt = self._build_scalp_prompt(symbol, market_data, technical_indicators, 
                                             sentiment_data, targets)
        elif trade_type == 'day_trade':
            prompt = self._build_day_trade_prompt(symbol, market_data, technical_indicators,
                                                  sentiment_data, targets)
        else:
            prompt = self._build_swing_prompt(symbol, market_data, technical_indicators,
                                             sentiment_data, targets)
        
        # Get AI analysis
        response = await self.llm.chat_completion(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=800
        )
        
        # Parse response
        return self._parse_analysis_response(response, trade_type)
    
    def _build_scalp_prompt(self, symbol: str, market_data: Dict[str, Any],
                           technical_indicators: Dict[str, Any],
                           sentiment_data: Dict[str, Any],
                           targets: Dict[str, Any]) -> str:
        """Build AI prompt for scalping analysis."""
        return f"""Analyze this SCALPING opportunity for {symbol}:

TRADE TYPE: SCALP (hold 5-30 minutes)
Target: {targets['target_pct']*100:.1f}% profit
Stop: {targets['stop_pct']*100:.1f}% loss

MARKET DATA:
- Current Price: ${market_data['current_price']:.2f}
- Change: {market_data['price_change_pct']:.2f}%
- Volume Ratio: {market_data['volume_ratio']:.2f}x
- High/Low: ${market_data['high']:.2f} / ${market_data['low']:.2f}

TECHNICAL INDICATORS:
- RSI: {technical_indicators.get('RSI', 'N/A')}
- Momentum (5-bar): {technical_indicators.get('Momentum_5', 'N/A'):.2f}%
- Volatility: {technical_indicators.get('Volatility', 'N/A')}
- Volume Ratio: {technical_indicators.get('Volume_Ratio', 'N/A')}

SENTIMENT:
- Overall: {sentiment_data['overall_sentiment']} ({sentiment_data['overall_score']:.2f})
- News: {sentiment_data['news_sentiment']['sentiment']}
- Market: {sentiment_data['market_sentiment']['sentiment']}

FOCUS ON:
1. Immediate momentum (next 5-30 minutes)
2. Quick entry/exit points
3. Tight risk management
4. High probability setups only
5. Volume confirmation

Provide your analysis in this EXACT format:
RECOMMENDATION: [BUY/SELL/HOLD]
CONFIDENCE: [0-100]
RISK_LEVEL: [LOW/MEDIUM/HIGH]
ENTRY_PRICE: [price]
REASONING: [2-3 sentences focusing on immediate momentum and scalp setup]"""
    
    def _build_day_trade_prompt(self, symbol: str, market_data: Dict[str, Any],
                                technical_indicators: Dict[str, Any],
                                sentiment_data: Dict[str, Any],
                                targets: Dict[str, Any]) -> str:
        """Build AI prompt for day trading analysis."""
        return f"""Analyze this DAY TRADING opportunity for {symbol}:

TRADE TYPE: DAY TRADE (hold 30-120 minutes)
Target: {targets['target_pct']*100:.1f}% profit
Stop: {targets['stop_pct']*100:.1f}% loss

MARKET DATA:
- Current Price: ${market_data['current_price']:.2f}
- Change: {market_data['price_change_pct']:.2f}%
- Volume Ratio: {market_data['volume_ratio']:.2f}x
- SMA 20: ${market_data['sma_20']:.2f}
- High/Low: ${market_data['high']:.2f} / ${market_data['low']:.2f}

TECHNICAL INDICATORS:
- RSI: {technical_indicators.get('RSI', 'N/A')}
- SMA 20: {technical_indicators.get('SMA_20', 'N/A')}
- SMA 50: {technical_indicators.get('SMA_50', 'N/A')}
- Momentum: {technical_indicators.get('Momentum_5', 'N/A'):.2f}%
- Volatility: {technical_indicators.get('Volatility', 'N/A')}

SENTIMENT:
- Overall: {sentiment_data['overall_sentiment']} ({sentiment_data['overall_score']:.2f})
- News: {sentiment_data['news_sentiment']['sentiment']} (Impact: {sentiment_data['news_sentiment']['impact']})
- Market: {sentiment_data['market_sentiment']['sentiment']}

FOCUS ON:
1. Intraday trend strength and direction
2. Support/resistance levels
3. Volume confirmation
4. Risk/reward ratio (targeting {targets['target_pct']*100:.1f}%)
5. News catalyst impact

Provide your analysis in this EXACT format:
RECOMMENDATION: [BUY/SELL/HOLD]
CONFIDENCE: [0-100]
RISK_LEVEL: [LOW/MEDIUM/HIGH]
ENTRY_PRICE: [price]
REASONING: [3-4 sentences on intraday setup, trend, and catalysts]"""
    
    def _build_swing_prompt(self, symbol: str, market_data: Dict[str, Any],
                           technical_indicators: Dict[str, Any],
                           sentiment_data: Dict[str, Any],
                           targets: Dict[str, Any]) -> str:
        """Build AI prompt for swing trading analysis."""
        return f"""Analyze this SWING TRADING opportunity for {symbol}:

TRADE TYPE: SWING (hold hours to days)
Target: {targets['target_pct']*100:.0f}% profit
Stop: {targets['stop_pct']*100:.0f}% loss

MARKET DATA:
- Current Price: ${market_data['current_price']:.2f}
- Change: {market_data['price_change_pct']:.2f}%
- Volume Ratio: {market_data['volume_ratio']:.2f}x
- SMA 20: ${market_data['sma_20']:.2f}
- High/Low: ${market_data['high']:.2f} / ${market_data['low']:.2f}

TECHNICAL INDICATORS:
- RSI: {technical_indicators.get('RSI', 'N/A')}
- SMA 20/50: {technical_indicators.get('SMA_20', 'N/A')} / {technical_indicators.get('SMA_50', 'N/A')}
- Momentum: {technical_indicators.get('Momentum_5', 'N/A'):.2f}%
- Volatility: {technical_indicators.get('Volatility', 'N/A')}

SENTIMENT:
- Overall: {sentiment_data['overall_sentiment']} ({sentiment_data['overall_score']:.2f})
- News: {sentiment_data['news_sentiment']['sentiment']} (Impact: {sentiment_data['news_sentiment']['impact']})
- Market: {sentiment_data['market_sentiment']['sentiment']}
- Headlines: {len(sentiment_data['news_sentiment'].get('headlines', []))} recent articles

FOCUS ON:
1. Multi-day trend potential
2. News catalysts and fundamental drivers
3. Broader market conditions
4. Longer-term risk/reward (targeting {targets['target_pct']*100:.0f}%)
5. Technical support/resistance

Provide your analysis in this EXACT format:
RECOMMENDATION: [BUY/SELL/HOLD]
CONFIDENCE: [0-100]
RISK_LEVEL: [LOW/MEDIUM/HIGH]
ENTRY_PRICE: [price]
REASONING: [5+ sentences covering trend, catalysts, and longer-term outlook]"""
    
    def _parse_analysis_response(self, response: str, trade_type: str) -> Dict[str, Any]:
        """Parse AI analysis response."""
        lines = response.strip().split('\n')
        result = {
            'recommendation': 'HOLD',
            'confidence': 0.0,
            'risk_level': 'MEDIUM',
            'entry_price': 0.0,
            'reasoning': '',
            'trade_type': trade_type
        }
        
        for line in lines:
            line = line.strip()
            if line.startswith('RECOMMENDATION:'):
                result['recommendation'] = line.split(':', 1)[1].strip()
            elif line.startswith('CONFIDENCE:'):
                try:
                    result['confidence'] = float(line.split(':', 1)[1].strip())
                except:
                    result['confidence'] = 50.0
            elif line.startswith('RISK_LEVEL:'):
                result['risk_level'] = line.split(':', 1)[1].strip()
            elif line.startswith('ENTRY_PRICE:'):
                try:
                    result['entry_price'] = float(line.split(':', 1)[1].strip().replace('$', ''))
                except:
                    result['entry_price'] = 0.0
            elif line.startswith('REASONING:'):
                result['reasoning'] = line.split(':', 1)[1].strip()
        
        return result
    
    async def decide_instrument_type(self, analysis: Dict[str, Any], opportunity: Dict[str, Any]) -> Dict[str, Any]:
        """
        Decide whether to use stock or options based on signal strength.
        
        Args:
            analysis: AI analysis result from intelligent scanner
            opportunity: Opportunity data (same as analysis from intelligent scanner)
            
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
        
        # Get values from intelligent scanner format
        confidence = analysis.get('confidence', 0)
        action = analysis.get('action', '')  # BUY_STOCK, BUY_CALL, BUY_PUT
        momentum_score = analysis.get('momentum_score', 0)  # Use momentum_score instead of score
        
        # Map intelligent scanner actions
        # BUY_CALL -> Already wants call option
        if action == "BUY_CALL" and confidence >= 70:
            return {
                "instrument": "option",
                "option_type": "call",
                "reasoning": f"AI recommends CALL option (confidence {confidence}%, momentum {momentum_score:.0f})",
                "confidence": confidence
            }
        
        # BUY_PUT -> Already wants put option
        if action == "BUY_PUT" and confidence >= 70:
            return {
                "instrument": "option",
                "option_type": "put",
                "reasoning": f"AI recommends PUT option (confidence {confidence}%, momentum {momentum_score:.0f})",
                "confidence": confidence
            }
        
        # BUY_STOCK -> Use stock
        if action == "BUY_STOCK" and confidence >= 70:
            if settings.enable_stock_trading:
                return {
                    "instrument": "stock",
                    "reasoning": f"AI recommends STOCK (confidence {confidence}%, momentum {momentum_score:.0f})",
                    "confidence": confidence
                }
            else:
                return {
                    "instrument": "none",
                    "reasoning": "Stock trading disabled"
                }
        
        # Weak or unclear signal -> Skip
        else:
            return {
                "instrument": "none",
                "reasoning": f"Signal not strong enough (action: {action}, confidence: {confidence}%)",
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
                "expiration": selected['expiration'],
                "option_type": option_type,
                "bid": quote['bid'],
                "ask": quote['ask'],
                "mid": (quote['bid'] + quote['ask']) / 2,
                "volume": quote.get('volume', 0),
                "open_interest": quote.get('open_interest', 0)
            }
            
        except Exception as e:
            logger.error(f"Error selecting option contract: {e}")
            return {"error": str(e)}

    async def _analyze_with_quant_strategies(self, opportunity: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Analyze opportunity using quantitative strategies.
        
        Args:
            opportunity: Opportunity data
            
        Returns:
            Signal from quantitative strategies
        """
        try:
            symbol = opportunity['symbol']
            bars = opportunity.get('bars', [])
            current_price = opportunity['current_price']
            
            if not bars or len(bars) < 30:
                return None
            
            # Run all quantitative strategies
            signal = self.strategy_manager.analyze_all(
                symbol=symbol,
                bars=bars,
                current_price=current_price
            )
            
            return signal
            
        except Exception as e:
            logger.error(f"Error in quantitative analysis: {e}")
            return None
    
    def _format_quant_signal(self, signal: Dict[str, Any], symbol: str) -> Dict[str, Any]:
        """
        Format quantitative signal into standard analysis format.
        
        Args:
            signal: Signal from quantitative strategy
            symbol: Stock symbol
            
        Returns:
            Formatted analysis result
        """
        action = signal.get('action')
        strategy_name = signal.get('strategy', 'Quantitative')
        
        # Map action to recommendation
        if action == 'BUY':
            recommendation = 'BUY'
            confidence = 0.75  # High confidence for quant signals
        elif action == 'SELL':
            recommendation = 'SELL'
            confidence = 0.70
        else:
            recommendation = 'HOLD'
            confidence = 0.50
        
        return {
            "symbol": symbol,
            "recommendation": recommendation,
            "confidence": confidence,
            "risk_level": "MEDIUM",
            "reasoning": f"{strategy_name}: {signal.get('reason', 'Quantitative signal')}",
            "entry_price": signal.get('entry_price', 0),
            "stop_loss": signal.get('stop_loss', 0),
            "profit_target": signal.get('take_profit', signal.get('profit_target', 0)),
            "strategy_type": "QUANTITATIVE",
            "strategy_name": strategy_name,
            "indicators": signal.get('indicators', {}),
            "trade_type": "swing",  # Default
            "max_hold_minutes": 14400,  # 10 days
            "target_pct": 0.05,  # 5%
            "stop_pct": 0.02  # 2%
        }
