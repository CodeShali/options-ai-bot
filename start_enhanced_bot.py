#!/usr/bin/env python3
"""
Start the Enhanced Discord Bot with all features.
"""
import sys
from loguru import logger
from bot.discord_bot import bot
from config import settings

# Configure logger
logger.remove()
logger.add(sys.stdout, level="INFO")

if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("🚀 TARA Enhanced Edition - Starting...")
    logger.info("=" * 60)
    logger.info("✅ Real-time monitoring: ENABLED")
    logger.info("✅ Interactive controls: ENABLED")
    logger.info("✅ Smart alerts: ENABLED")
    logger.info("✅ Analytics & reporting: ENABLED")
    logger.info("✅ Market intelligence: ENABLED")
    logger.info("✅ Risk calculator: ENABLED")
    logger.info("✅ Conversational AI: ENABLED")
    logger.info("=" * 60)
    
    try:
        # Start the bot
        bot.run(settings.discord_bot_token)
    except Exception as e:
        logger.error(f"❌ Error starting bot: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
