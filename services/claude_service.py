"""
Claude API service for sentiment analysis.
Uses Anthropic's Claude for better stock analysis.
"""
import anthropic
from typing import List, Dict
from loguru import logger
from config import settings


class ClaudeService:
    """Service for Claude API interactions."""
    
    def __init__(self):
        """Initialize Claude service."""
        if not settings.anthropic_api_key:
            logger.warning("No Anthropic API key provided, Claude service disabled")
            self.client = None
        else:
            self.client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
            logger.info("Claude service initialized")
    
    async def analyze_stock(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 4000,
        temperature: float = 0.3
    ) -> str:
        """
        Analyze stock using Claude Sonnet.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            
        Returns:
            Response content as string
        """
        if not self.client:
            logger.error("Claude client not initialized")
            return ""
        
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
            logger.info(f"Claude analysis complete: {len(result)} chars")
            return result
            
        except Exception as e:
            logger.error(f"Error in Claude analysis: {e}")
            return ""


# Global instance
_claude_service = None


def get_claude_service() -> ClaudeService:
    """Get the global Claude service instance."""
    global _claude_service
    if _claude_service is None:
        _claude_service = ClaudeService()
    return _claude_service
