"""
Claude API service for sentiment analysis.
Uses Anthropic's Claude for better stock analysis with OpenAI fallback.
"""
import anthropic
from openai import AsyncOpenAI
from typing import List, Dict
from loguru import logger
from config import settings


class ClaudeService:
    """Service for Claude API interactions with OpenAI fallback."""
    
    def __init__(self):
        """Initialize Claude service with OpenAI fallback."""
        # Try to initialize Claude
        if not settings.anthropic_api_key:
            logger.warning("No Anthropic API key provided, Claude service disabled")
            self.client = None
        else:
            self.client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
            logger.info("Claude service initialized")
        
        # Initialize OpenAI as fallback
        self.openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.use_fallback = False
        logger.info("OpenAI fallback initialized")
    
    async def analyze_stock(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 4000,
        temperature: float = 0.3
    ) -> str:
        """
        Analyze stock using Claude Sonnet with OpenAI fallback.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            
        Returns:
            Response content as string
        """
        # Try Claude first if available and not in fallback mode
        if self.client and not self.use_fallback:
            try:
                # Convert messages format (remove system messages, Claude handles them differently)
                claude_messages = []
                system_message = ""
                
                for msg in messages:
                    if msg['role'] == 'system':
                        system_message = msg['content']
                    else:
                        claude_messages.append({
                            "role": msg['role'],
                            "content": msg['content']
                        })
                
                # Call Claude API
                response = self.client.messages.create(
                    model="claude-sonnet-4-20250514",  # Latest Claude Sonnet
                    max_tokens=max_tokens,
                    temperature=temperature,
                    system=system_message if system_message else "You are an expert stock and options trading analyst.",
                    messages=claude_messages
                )
                
                # Extract text from response
                result = response.content[0].text
                logger.info(f"✅ Claude analysis complete: {len(result)} chars")
                return result
                
            except Exception as e:
                error_msg = str(e)
                # Check if it's a credit/billing error
                if "credit balance" in error_msg.lower() or "billing" in error_msg.lower():
                    logger.warning(f"⚠️ Claude API out of credits, switching to OpenAI fallback")
                    self.use_fallback = True
                else:
                    logger.error(f"❌ Error in Claude analysis: {e}")
                    # Try fallback anyway
                    self.use_fallback = True
        
        # Use OpenAI fallback
        try:
            logger.info("🔄 Using OpenAI GPT-4 as fallback...")
            
            response = await self.openai_client.chat.completions.create(
                model="gpt-4o",  # GPT-4 Turbo
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature
            )
            
            result = response.choices[0].message.content
            logger.info(f"✅ OpenAI analysis complete: {len(result)} chars")
            return result
            
        except Exception as e:
            logger.error(f"❌ Error in OpenAI fallback: {e}")
            return ""


# Global instance
_claude_service = None


def get_claude_service() -> ClaudeService:
    """Get the global Claude service instance."""
    global _claude_service
    if _claude_service is None:
        _claude_service = ClaudeService()
    return _claude_service
