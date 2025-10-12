"""
Logging configuration for the trading system.
"""
import sys
from pathlib import Path
from loguru import logger

from config import settings


def setup_logging():
    """Setup logging configuration."""
    # Remove default handler
    logger.remove()
    
    # Ensure log directory exists
    log_file = Path(settings.log_file)
    log_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Console handler with colors
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
        level=settings.log_level,
        colorize=True
    )
    
    # File handler
    logger.add(
        settings.log_file,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level=settings.log_level,
        rotation="10 MB",
        retention="30 days",
        compression="zip"
    )
    
    logger.info("Logging configured")
