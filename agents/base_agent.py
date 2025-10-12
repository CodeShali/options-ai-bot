"""
Base agent class for all trading agents.
"""
import asyncio
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from loguru import logger


class BaseAgent(ABC):
    """Base class for all agents."""
    
    def __init__(self, name: str):
        """
        Initialize the agent.
        
        Args:
            name: Agent name
        """
        self.name = name
        self.running = False
        self.task: Optional[asyncio.Task] = None
        logger.info(f"Agent initialized: {name}")
    
    @abstractmethod
    async def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process data and return result.
        
        Args:
            data: Input data
            
        Returns:
            Processing result
        """
        pass
    
    async def start(self):
        """Start the agent."""
        if self.running:
            logger.warning(f"Agent {self.name} is already running")
            return
        
        self.running = True
        logger.info(f"Agent started: {self.name}")
    
    async def stop(self):
        """Stop the agent."""
        if not self.running:
            return
        
        self.running = False
        
        if self.task and not self.task.done():
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        
        logger.info(f"Agent stopped: {self.name}")
    
    async def health_check(self) -> bool:
        """
        Check agent health.
        
        Returns:
            True if healthy
        """
        return self.running
