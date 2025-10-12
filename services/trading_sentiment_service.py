"""
Comprehensive trading sentiment analysis with detailed opportunities.
Uses Claude Sonnet for superior stock analysis.
"""
import json
from typing import Dict, Any, Optional
from datetime import datetime
from loguru import logger


class TradingSentimentAnalyzer:
    """Analyzes stocks and provides detailed trading opportunities."""
    
    def __init__(self, llm_service, alpaca_service, news_service, claude_service=None):
        """Initialize with required services."""
        self.llm = llm_service
        self.alpaca = alpaca_service
        self.news = news_service
        self.claude = claude_service  # Claude for sentiment analysis
    
    async def analyze_for_trading(self, symbol: str) -> Dict[str, Any]:
        """
        Comprehensive trading analysis with detailed opportunities.
        
        Uses GPT-4o-mini for cost-effective sentiment analysis.
        Returns actionable trade recommendations across all strategies.
        """
        try:
            logger.info(f"Starting comprehensive trading analysis for {symbol}")
            
            # 1. Gather all data
            stock_data = await self._get_stock_data(symbol)
            news_data = await self._get_news_data(symbol)
            market_data = await self._get_market_context()
            options_data = await self._get_options_context(symbol)
            
            # 2. Build comprehensive prompt
            prompt = self._build_comprehensive_prompt(
                symbol, stock_data, news_data, market_data, options_data
            )
            
            # 3. Get AI analysis using Claude Sonnet (best for stock analysis!)
            response = ""
            model_used = "gpt-4o-mini"
            cost_estimate = 0.0001
            
            # Try Claude first
            if self.claude and self.claude.client:
                try:
                    logger.info(f"Using Claude Sonnet for {symbol} analysis")
                    response = await self.claude.analyze_stock(
                        messages=[
                            {
                                "role": "system",
                                "content": "You are an expert options and stock trader providing detailed, actionable trade recommendations."
                            },
                            {
                                "role": "user",
                                "content": prompt
                            }
                        ],
                        max_tokens=4000,
                        temperature=0.3
                    )
                    if response:
                        model_used = "claude-sonnet-4"
                        cost_estimate = 0.0003
                except Exception as e:
                    logger.warning(f"Claude failed, falling back to GPT-4o-mini: {e}")
                    response = ""
            
            # Fallback to GPT-4o-mini if Claude failed or not available
            if not response:
                logger.info(f"Using GPT-4o-mini for {symbol} analysis")
                response = await self.llm.chat_completion(
                    messages=[
                        {
                            "role": "system",
                            "content": "You are an expert options and stock trader providing detailed, actionable trade recommendations."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    model="gpt-4o-mini",
                    temperature=0.3,
                    max_tokens=3000
                )
                model_used = "gpt-4o-mini"
                cost_estimate = 0.0001
            
            # 4. Parse response (clean markdown code blocks if present)
            try:
                # Clean response - remove markdown code blocks
                cleaned_response = response.strip()
                if cleaned_response.startswith("```json"):
                    cleaned_response = cleaned_response.split("```json", 1)[1]
                elif cleaned_response.startswith("```"):
                    cleaned_response = cleaned_response.split("```", 1)[1]
                
                if cleaned_response.endswith("```"):
                    cleaned_response = cleaned_response.rsplit("```", 1)[0]
                
                cleaned_response = cleaned_response.strip()
                
                # Parse JSON
                analysis = json.loads(cleaned_response)
                logger.info(f"Successfully parsed AI response for {symbol}")
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse AI response as JSON: {e}")
                logger.debug(f"Raw response: {response[:500]}")
                analysis = self._create_fallback_analysis(symbol, stock_data)
            
            # 5. Enrich with metadata
            analysis["symbol"] = symbol
            analysis["timestamp"] = datetime.now().isoformat()
            analysis["model_used"] = model_used
            analysis["cost_estimate"] = cost_estimate
            
            logger.info(f"Analysis complete for {symbol}: {analysis.get('recommendation', 'N/A')}")
            return analysis
            
        except Exception as e:
            logger.error(f"Error in trading analysis for {symbol}: {e}")
            return self._create_error_analysis(symbol, str(e))
    
    async def _get_stock_data(self, symbol: str) -> Dict[str, Any]:
        """Get comprehensive stock data."""
        try:
            # Get current quote
            quote = await self.alpaca.get_latest_quote(symbol)
            
            if not quote:
                logger.error(f"No quote data available for {symbol}")
                return {"error": "No quote data"}
            
            # Get recent bars for trend analysis (use longer timeframe to ensure data)
            from datetime import datetime, timedelta
            end_date = datetime.now()
            start_date = end_date - timedelta(days=30)  # Get 30 days to ensure we have data
            bars = await self.alpaca.get_bars(symbol, timeframe="1Day", limit=20, start=start_date, end=end_date)
            
            # Use quote price as current price
            current_price = quote.get('price', 0)
            
            logger.info(f"Stock data for {symbol}: Price=${current_price:.2f}, Bars={len(bars) if bars else 0}")
            
            # Calculate metrics (handle empty bars)
            if bars and len(bars) > 0:
                prices = [bar['close'] for bar in bars]
                volumes = [bar['volume'] for bar in bars]
            else:
                # Fallback to current price if no bars
                logger.warning(f"No historical bars for {symbol}, using current price only")
                prices = [current_price]
                volumes = [0]
            
            avg_volume = sum(volumes) / len(volumes) if volumes else 0
            current_volume = volumes[-1] if volumes else 0
            volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1.0
            
            # Price changes
            if len(prices) >= 2:
                change_1d = ((prices[-1] - prices[-2]) / prices[-2]) * 100
            else:
                change_1d = 0
            
            if len(prices) >= 5:
                change_5d = ((prices[-1] - prices[-5]) / prices[-5]) * 100
            else:
                change_5d = 0
            
            # 52-week high/low (approximate from 20 days)
            high_52w = max(prices)
            low_52w = min(prices)
            
            return {
                "price": current_price,
                "bid": quote.get('bid', current_price),
                "ask": quote.get('ask', current_price),
                "spread": quote.get('spread', 0),
                "volume": current_volume,
                "avg_volume": avg_volume,
                "volume_ratio": volume_ratio,
                "change_1d_pct": change_1d,
                "change_5d_pct": change_5d,
                "high_52w": high_52w,
                "low_52w": low_52w,
                "distance_from_high": ((current_price - high_52w) / high_52w) * 100,
                "distance_from_low": ((current_price - low_52w) / low_52w) * 100,
            }
        except Exception as e:
            logger.error(f"Error getting stock data: {e}")
            return {"error": str(e)}
    
    async def _get_news_data(self, symbol: str) -> Dict[str, Any]:
        """Get recent news headlines."""
        try:
            if not self.news:
                return {"headlines": [], "count": 0}
            
            headlines = await self.news.get_headlines(symbol, max_headlines=10)
            return {
                "headlines": headlines[:10],
                "count": len(headlines)
            }
        except Exception as e:
            logger.error(f"Error getting news: {e}")
            return {"headlines": [], "count": 0, "error": str(e)}
    
    async def _get_market_context(self) -> Dict[str, Any]:
        """Get overall market context."""
        try:
            # Get SPY, QQQ, VIX
            spy_bars = await self.alpaca.get_bars("SPY", timeframe="1Day", limit=2)
            qqq_bars = await self.alpaca.get_bars("QQQ", timeframe="1Day", limit=2)
            
            market_data = {}
            
            if spy_bars and len(spy_bars) >= 2:
                spy_change = ((spy_bars[-1]['close'] - spy_bars[-2]['close']) / spy_bars[-2]['close']) * 100
                market_data["spy_change"] = spy_change
                market_data["spy_price"] = spy_bars[-1]['close']
            
            if qqq_bars and len(qqq_bars) >= 2:
                qqq_change = ((qqq_bars[-1]['close'] - qqq_bars[-2]['close']) / qqq_bars[-2]['close']) * 100
                market_data["qqq_change"] = qqq_change
                market_data["qqq_price"] = qqq_bars[-1]['close']
            
            # Try to get VIX
            try:
                vix_bars = await self.alpaca.get_bars("VIX", timeframe="1Day", limit=1)
                if vix_bars:
                    market_data["vix"] = vix_bars[-1]['close']
            except:
                market_data["vix"] = 20.0  # Default neutral
            
            return market_data
        except Exception as e:
            logger.error(f"Error getting market context: {e}")
            return {"spy_change": 0, "qqq_change": 0, "vix": 20}
    
    async def _get_options_context(self, symbol: str) -> Dict[str, Any]:
        """Get options context with REAL premiums and Greeks."""
        try:
            # Get options chain
            chain = await self.alpaca.get_options_chain(symbol)
            
            if not chain or not chain.get('calls'):
                logger.warning(f"No options available for {symbol}")
                return {"available": False}
            
            # Find ATM options
            stock_price = chain.get('underlying_price', 0)
            if stock_price == 0:
                logger.warning(f"No underlying price in options chain for {symbol}")
                return {"available": False}
            
            logger.info(f"Options chain for {symbol}: Underlying=${stock_price:.2f}")
            
            # Get calls
            calls = chain.get('calls', [])
            if not calls:
                return {"available": False}
            
            # Find ATM strike
            atm_call = min(calls, key=lambda x: abs(x.get('strike', 0) - stock_price))
            
            # Get REAL option data with Greeks for ATM
            options_data = {
                "available": True,
                "underlying_price": stock_price,
                "expirations_available": len(chain.get('expirations', {})),
                "strikes": []
            }
            
            # Fetch real data for ATM strike
            try:
                atm_symbol = atm_call.get('symbol')
                logger.info(f"Fetching real option data for {atm_symbol}")
                
                # Get real quote with Greeks
                option_quote = await self.alpaca.get_option_quote_with_greeks(atm_symbol)
                
                if option_quote:
                    options_data["strikes"].append({
                        "type": "atm",
                        "strike": atm_call.get('strike'),
                        "symbol": atm_symbol,
                        "premium_bid": option_quote.get('bid_price', 0),
                        "premium_ask": option_quote.get('ask_price', 0),
                        "premium_mid": (option_quote.get('bid_price', 0) + option_quote.get('ask_price', 0)) / 2,
                        "greeks": {
                            "delta": option_quote.get('delta', 0),
                            "gamma": option_quote.get('gamma', 0),
                            "theta": option_quote.get('theta', 0),
                            "vega": option_quote.get('vega', 0),
                            "rho": option_quote.get('rho', 0)
                        },
                        "iv": option_quote.get('implied_volatility', 0)
                    })
                    logger.info(f"✅ Real option data: Strike=${atm_call.get('strike')}, Premium=${option_quote.get('ask_price', 0):.2f}, Delta={option_quote.get('delta', 0):.3f}")
                else:
                    logger.warning(f"No option quote available for {atm_symbol}")
            except Exception as e:
                logger.error(f"Error fetching option data for {atm_symbol}: {e}")
            
            return options_data
            
        except Exception as e:
            logger.error(f"Error getting options context: {e}")
            return {"available": False}
    
    def _build_comprehensive_prompt(
        self,
        symbol: str,
        stock_data: Dict,
        news_data: Dict,
        market_data: Dict,
        options_data: Dict
    ) -> str:
        """Build comprehensive analysis prompt."""
        
        prompt = f"""Analyze {symbol} for trading and provide detailed, actionable recommendations.

STOCK DATA:
- Current Price: ${stock_data.get('price', 0):.2f}
- Bid/Ask: ${stock_data.get('bid', 0):.2f} / ${stock_data.get('ask', 0):.2f}
- Spread: ${stock_data.get('spread', 0):.3f}
- 1-Day Change: {stock_data.get('change_1d_pct', 0):+.2f}%
- 5-Day Change: {stock_data.get('change_5d_pct', 0):+.2f}%
- Volume: {stock_data.get('volume', 0):,.0f} ({stock_data.get('volume_ratio', 1):.1f}x average)
- 52w High/Low: ${stock_data.get('high_52w', 0):.2f} / ${stock_data.get('low_52w', 0):.2f}
- Distance from High: {stock_data.get('distance_from_high', 0):.1f}%

MARKET CONTEXT:
- SPY: {market_data.get('spy_change', 0):+.2f}% (${market_data.get('spy_price', 0):.2f})
- QQQ: {market_data.get('qqq_change', 0):+.2f}% (${market_data.get('qqq_price', 0):.2f})
- VIX: {market_data.get('vix', 20):.1f}

NEWS HEADLINES ({news_data.get('count', 0)} recent):
{chr(10).join(f'- {h}' for h in news_data.get('headlines', [])[:5]) or '- No recent news'}

OPTIONS DATA:"""
        
        # Add real options data if available
        if options_data.get('available') and options_data.get('strikes'):
            prompt += f"\n- Underlying Price: ${options_data.get('underlying_price', 0):.2f}"
            for strike_data in options_data.get('strikes', []):
                prompt += f"""
- {strike_data['type'].upper()} Strike: ${strike_data['strike']:.2f}
  - Premium (Bid/Ask): ${strike_data['premium_bid']:.2f} / ${strike_data['premium_ask']:.2f}
  - Greeks: Delta={strike_data['greeks']['delta']:.3f}, Gamma={strike_data['greeks']['gamma']:.4f}, Theta={strike_data['greeks']['theta']:.4f}, Vega={strike_data['greeks']['vega']:.4f}
  - IV: {strike_data['iv']*100:.1f}%"""
        else:
            prompt += "\n- No options data available"
        
        prompt += """

Provide a comprehensive trading analysis in JSON format with the following structure:

{{
  "overview": "2-3 sentence market overview explaining the current setup, key drivers, and overall opportunity. Be specific and actionable.",
  
  "recommendation": "BUY_STOCK|BUY_CALLS|BUY_PUTS|BULL_SPREAD|BEAR_SPREAD|HOLD|AVOID",
  "confidence": 0-100,
  "time_horizon": "scalp|day|swing|position",
  
  "opportunities": {{
    "stock": {{
      "recommended": true/false,
      "action": "buy|sell|hold",
      "entry_price": price,
      "target_price": price,
      "stop_loss": price,
      "position_size_shares": number,
      "expected_gain_pct": percentage,
      "hold_time": "description",
      "best_for": "trader type",
      "reasoning": "why this specific trade"
    }},
    
    "call_options": [
      {{
        "recommended": true/false,
        "type": "atm|otm_aggressive|itm_conservative|0dte_scalp",
        "strike": price,
        "expiry_days": days,
        "entry_premium_estimate": price,
        "target_premium_estimate": price,
        "max_gain_pct": percentage,
        "hold_time": "description",
        "best_for": "trader type",
        "reasoning": "why this specific strike/expiry"
      }}
    ],
    
    "put_options": [
      {{
        "recommended": true/false,
        "type": "atm|otm|itm",
        "strike": price,
        "expiry_days": days,
        "reasoning": "why or why not"
      }}
    ],
    
    "spreads": [
      {{
        "recommended": true/false,
        "type": "bull_call|bear_put|iron_condor|etc",
        "description": "specific strikes and expiries",
        "max_gain": amount,
        "max_loss": amount,
        "best_for": "trader type",
        "reasoning": "why this spread"
      }}
    ]
  }},
  
  "catalysts": ["specific bullish factors"],
  "risks": ["specific risk factors"],
  
  "timing": {{
    "best_entry_time": "specific time range or condition",
    "best_exit_time": "specific time range or condition",
    "avoid_times": "times to avoid"
  }},
  
  "key_levels": {{
    "support": [prices],
    "resistance": [prices]
  }}
}}

Be specific with prices, percentages, and timeframes. Focus on actionable insights.

IMPORTANT: Return ONLY the JSON object, no markdown formatting, no code blocks, no extra text. Just pure JSON."""

        return prompt
    
    def _create_fallback_analysis(self, symbol: str, stock_data: Dict) -> Dict[str, Any]:
        """Create fallback analysis if AI fails."""
        return {
            "overview": f"{symbol} analysis unavailable due to parsing error. Manual review recommended.",
            "recommendation": "HOLD",
            "confidence": 0,
            "time_horizon": "unknown",
            "opportunities": {
                "stock": {"recommended": False, "reasoning": "Analysis unavailable"},
                "call_options": [],
                "put_options": [],
                "spreads": []
            },
            "catalysts": [],
            "risks": ["Analysis system error"],
            "timing": {},
            "key_levels": {}
        }
    
    def _create_error_analysis(self, symbol: str, error: str) -> Dict[str, Any]:
        """Create error analysis."""
        return {
            "overview": f"Error analyzing {symbol}: {error}",
            "recommendation": "HOLD",
            "confidence": 0,
            "time_horizon": "unknown",
            "opportunities": {
                "stock": {"recommended": False, "reasoning": f"Error: {error}"},
                "call_options": [],
                "put_options": [],
                "spreads": []
            },
            "catalysts": [],
            "risks": [f"System error: {error}"],
            "timing": {},
            "key_levels": {},
            "error": error
        }
