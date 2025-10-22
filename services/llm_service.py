"""
LLM service for market analysis using OpenAI.
"""
import asyncio
from typing import Dict, List, Optional, Any
from openai import AsyncOpenAI
from loguru import logger

from config import settings


class LLMService:
    """Service for interacting with OpenAI."""
    
    def __init__(self):
        """Initialize LLM service."""
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.model = "gpt-4o"  # or "gpt-4-turbo" or "gpt-3.5-turbo"
        logger.info("LLM service initialized with OpenAI")
    
    async def analyze_market_opportunity(
        self,
        symbol: str,
        market_data: Dict[str, Any],
        technical_indicators: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Analyze a market opportunity using OpenAI.
        
        Args:
            symbol: Stock symbol
            market_data: Market data including price, volume, etc.
            technical_indicators: Optional technical indicators
            
        Returns:
            Analysis result with recommendation
        """
        try:
            prompt = self._build_analysis_prompt(
                symbol,
                market_data,
                technical_indicators
            )
            
            response = await self.client.chat.completions.create(
                model=self.model,
                max_tokens=2000,
                temperature=0.7,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert options trading analyst."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )
            
            analysis_text = response.choices[0].message.content
            
            # Parse the response
            result = self._parse_analysis_response(analysis_text)
            result["raw_analysis"] = analysis_text
            
            logger.info(f"Market analysis completed for {symbol}: {result.get('recommendation', 'N/A')}")
            return result
            
        except Exception as e:
            logger.error(f"Error analyzing market opportunity: {e}")
            return {
                "recommendation": "HOLD",
                "confidence": 0.0,
                "reasoning": f"Error during analysis: {str(e)}",
                "risk_level": "HIGH"
            }
    
    async def analyze_exit_signal(
        self,
        symbol: str,
        position_data: Dict[str, Any],
        market_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Analyze whether to exit a position.
        
        Args:
            symbol: Stock symbol
            position_data: Current position data
            market_data: Current market data
            
        Returns:
            Exit analysis with recommendation
        """
        try:
            prompt = self._build_exit_prompt(symbol, position_data, market_data)
            
            response = await self.client.chat.completions.create(
                model=self.model,
                max_tokens=1500,
                temperature=0.7,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert options trading analyst."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )
            
            analysis_text = response.choices[0].message.content
            
            # Parse the response
            result = self._parse_exit_response(analysis_text)
            result["raw_analysis"] = analysis_text
            
            logger.info(f"Exit analysis completed for {symbol}: {result.get('action', 'N/A')}")
            return result
            
        except Exception as e:
            logger.error(f"Error analyzing exit signal: {e}")
            return {
                "action": "HOLD",
                "confidence": 0.0,
                "reasoning": f"Error during analysis: {str(e)}"
            }
    
    async def generate_market_summary(
        self,
        positions: List[Dict[str, Any]],
        account_info: Dict[str, Any],
        recent_trades: List[Dict[str, Any]]
    ) -> str:
        """
        Generate a market summary report.
        
        Args:
            positions: Current positions
            account_info: Account information
            recent_trades: Recent trade history
            
        Returns:
            Summary text
        """
        try:
            prompt = self._build_summary_prompt(positions, account_info, recent_trades)
            
            response = await self.client.chat.completions.create(
                model=self.model,
                max_tokens=1500,
                temperature=0.7,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert options trading analyst."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )
            
            summary = response.choices[0].message.content
            logger.info("Market summary generated")
            return summary
            
        except Exception as e:
            logger.error(f"Error generating market summary: {e}")
            return f"Error generating summary: {str(e)}"
    
    def _build_analysis_prompt(
        self,
        symbol: str,
        market_data: Dict[str, Any],
        technical_indicators: Optional[Dict[str, Any]]
    ) -> str:
        """Build prompt for market analysis."""
        prompt = f"""You are an expert options trading analyst. Analyze the following market opportunity and provide a recommendation.

Symbol: {symbol}

Market Data:
- Current Price: ${market_data.get('current_price', 'N/A')}
- Volume: {market_data.get('volume', 'N/A')}
- Day High: ${market_data.get('high', 'N/A')}
- Day Low: ${market_data.get('low', 'N/A')}
- Previous Close: ${market_data.get('prev_close', 'N/A')}
"""
        
        if technical_indicators:
            prompt += f"\nTechnical Indicators:\n"
            for key, value in technical_indicators.items():
                prompt += f"- {key}: {value}\n"
        
        prompt += """
Please provide your analysis in the following format:

RECOMMENDATION: [BUY/SELL/HOLD]
CONFIDENCE: [0-100]
RISK_LEVEL: [LOW/MEDIUM/HIGH]
REASONING: [Your detailed reasoning here]
TARGET_PRICE: [Optional target price]
STOP_LOSS: [Optional stop loss price]

Consider:
1. Price momentum and trends
2. Volume patterns
3. Technical indicators
4. Risk/reward ratio
5. Market conditions
"""
        
        return prompt
    
    def _build_exit_prompt(
        self,
        symbol: str,
        position_data: Dict[str, Any],
        market_data: Dict[str, Any]
    ) -> str:
        """Build prompt for exit analysis."""
        unrealized_pl = position_data.get('unrealized_pl', 0)
        unrealized_plpc = position_data.get('unrealized_plpc', 0) * 100
        
        prompt = f"""You are an expert options trading analyst. Analyze whether to exit this position.

Symbol: {symbol}

Position Data:
- Entry Price: ${position_data.get('avg_entry_price', 'N/A')}
- Current Price: ${position_data.get('current_price', 'N/A')}
- Quantity: {position_data.get('qty', 'N/A')}
- Unrealized P/L: ${unrealized_pl:.2f} ({unrealized_plpc:.2f}%)
- Cost Basis: ${position_data.get('cost_basis', 'N/A')}
- Market Value: ${position_data.get('market_value', 'N/A')}

Current Market Data:
- Current Price: ${market_data.get('current_price', 'N/A')}
- Volume: {market_data.get('volume', 'N/A')}
- Day High: ${market_data.get('high', 'N/A')}
- Day Low: ${market_data.get('low', 'N/A')}

Please provide your analysis in the following format:

ACTION: [EXIT/HOLD/PARTIAL_EXIT]
CONFIDENCE: [0-100]
REASONING: [Your detailed reasoning here]

Consider:
1. Current profit/loss percentage
2. Price momentum
3. Whether profit target or stop loss should be triggered
4. Market conditions
5. Risk of reversal
"""
        
        return prompt
    
    def _build_summary_prompt(
        self,
        positions: List[Dict[str, Any]],
        account_info: Dict[str, Any],
        recent_trades: List[Dict[str, Any]]
    ) -> str:
        """Build prompt for market summary."""
        prompt = f"""You are an expert options trading analyst. Generate a concise market summary report.

Account Information:
- Portfolio Value: ${account_info.get('portfolio_value', 'N/A')}
- Cash: ${account_info.get('cash', 'N/A')}
- Buying Power: ${account_info.get('buying_power', 'N/A')}

Current Positions ({len(positions)}):
"""
        
        for pos in positions[:10]:  # Limit to 10 positions
            prompt += f"- {pos['symbol']}: {pos['qty']} shares @ ${pos['avg_entry_price']:.2f}, "
            prompt += f"P/L: ${pos['unrealized_pl']:.2f} ({pos['unrealized_plpc']*100:.2f}%)\n"
        
        prompt += f"\nRecent Trades ({len(recent_trades)}):\n"
        for trade in recent_trades[:5]:  # Limit to 5 trades
            prompt += f"- {trade.get('symbol', 'N/A')}: {trade.get('action', 'N/A')} "
            prompt += f"{trade.get('quantity', 'N/A')} @ ${trade.get('price', 'N/A'):.2f}\n"
        
        prompt += """
Please provide a concise summary (3-5 sentences) covering:
1. Overall portfolio performance
2. Key positions and their status
3. Recent trading activity
4. Any notable risks or opportunities
"""
        
        return prompt
    
    def _parse_analysis_response(self, text: str) -> Dict[str, Any]:
        """Parse analysis response from OpenAI."""
        result = {
            "recommendation": "HOLD",
            "confidence": 50.0,
            "risk_level": "MEDIUM",
            "reasoning": text,
            "target_price": None,
            "stop_loss": None
        }
        
        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith("RECOMMENDATION:"):
                rec = line.split(":", 1)[1].strip().upper()
                if rec in ["BUY", "SELL", "HOLD"]:
                    result["recommendation"] = rec
            elif line.startswith("CONFIDENCE:"):
                try:
                    conf = line.split(":", 1)[1].strip()
                    result["confidence"] = float(conf.replace("%", ""))
                except:
                    pass
            elif line.startswith("RISK_LEVEL:"):
                risk = line.split(":", 1)[1].strip().upper()
                if risk in ["LOW", "MEDIUM", "HIGH"]:
                    result["risk_level"] = risk
            elif line.startswith("REASONING:"):
                result["reasoning"] = line.split(":", 1)[1].strip()
            elif line.startswith("TARGET_PRICE:"):
                try:
                    price = line.split(":", 1)[1].strip().replace("$", "")
                    result["target_price"] = float(price)
                except:
                    pass
            elif line.startswith("STOP_LOSS:"):
                try:
                    price = line.split(":", 1)[1].strip().replace("$", "")
                    result["stop_loss"] = float(price)
                except:
                    pass
        
        return result
    
    def _parse_exit_response(self, text: str) -> Dict[str, Any]:
        """Parse exit analysis response from OpenAI."""
        result = {
            "action": "HOLD",
            "confidence": 50.0,
            "reasoning": text
        }
        
        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith("ACTION:"):
                action = line.split(":", 1)[1].strip().upper()
                if action in ["EXIT", "HOLD", "PARTIAL_EXIT"]:
                    result["action"] = action
            elif line.startswith("CONFIDENCE:"):
                try:
                    conf = line.split(":", 1)[1].strip()
                    result["confidence"] = float(conf.rstrip('%'))
                except:
                    pass
        
        return result
    
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000,
        model: Optional[str] = None,
        functions: Optional[List[Dict[str, Any]]] = None,
        function_call: Optional[str] = None
    ):
        """
        Chat completion wrapper with optional function calling support.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            model: Optional model override (e.g., 'gpt-4o-mini' for cheaper calls)
            functions: Optional list of function definitions for function calling
            function_call: Optional function call mode ('auto', 'none', or specific function)
            
        Returns:
            Response content as string, or dict with function_call if AI wants to call a function
        """
        try:
            use_model = model or self.model
            
            # Build request parameters
            params = {
                "model": use_model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens
            }
            
            # Add function calling if provided
            if functions:
                params["tools"] = [{"type": "function", "function": f} for f in functions]
                if function_call:
                    params["tool_choice"] = function_call if function_call == "auto" else {"type": "function", "function": {"name": function_call}}
            
            response = await self.client.chat.completions.create(**params)
            
            message = response.choices[0].message
            
            # Check if AI wants to call a function
            if message.tool_calls:
                tool_call = message.tool_calls[0]
                logger.debug(f"LLM wants to call function: {tool_call.function.name}")
                return {
                    "function_call": {
                        "name": tool_call.function.name,
                        "arguments": tool_call.function.arguments
                    }
                }
            
            logger.debug(f"LLM call completed using {use_model}")
            return message.content or ""
            
        except Exception as e:
            logger.error(f"Error in chat completion: {e}")
            return ""


# Global instance
_llm_service: Optional[LLMService] = None


def get_llm_service() -> LLMService:
    """Get the global LLM service instance."""
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service
