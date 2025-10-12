"""
Main entry point for the options trading system.
"""
import asyncio
import signal
from contextlib import asynccontextmanager
from loguru import logger
import uvicorn

from config import settings
from utils import setup_logging, TradingScheduler
from agents import OrchestratorAgent
from bot import get_bot, start_bot
from api import app, set_orchestrator
from services import get_database_service


# Global instances
orchestrator = None
scheduler = None
shutdown_event = asyncio.Event()


@asynccontextmanager
async def lifespan(app):
    """Lifespan context manager for FastAPI."""
    # Startup
    logger.info("Starting trading system...")
    
    global orchestrator, scheduler
    
    try:
        # Initialize database
        db = get_database_service()
        await db.initialize()
        
        # Create orchestrator
        orchestrator = OrchestratorAgent()
        await orchestrator.start()
        
        # Set orchestrator in API
        set_orchestrator(orchestrator)
        
        # Get Discord bot and link with orchestrator
        bot = get_bot()
        bot.set_orchestrator(orchestrator)
        orchestrator.set_discord_bot(bot)
        
        # Create and setup scheduler
        scheduler = TradingScheduler()
        scheduler.set_orchestrator(orchestrator)
        scheduler.setup_jobs()
        scheduler.start()
        
        # Start Discord bot in background
        asyncio.create_task(start_bot())
        
        logger.info("✅ Trading system started successfully")
        logger.info(f"Mode: {settings.trading_mode.upper()}")
        logger.info(f"API: http://{settings.api_host}:{settings.api_port}")
        
        yield
        
    except Exception as e:
        logger.error(f"Error during startup: {e}")
        raise
    
    # Shutdown
    logger.info("Shutting down trading system...")
    
    try:
        if scheduler:
            scheduler.shutdown()
        
        if orchestrator:
            await orchestrator.stop()
        
        logger.info("✅ Trading system shutdown complete")
        
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")


# Attach lifespan to app
app.router.lifespan_context = lifespan


def signal_handler(signum, frame):
    """Handle shutdown signals."""
    logger.info(f"Received signal {signum}, initiating shutdown...")
    shutdown_event.set()


async def run_system():
    """Run the complete trading system."""
    # Setup logging
    setup_logging()
    
    # Get port from environment (for cloud deployment)
    port = int(os.getenv("PORT", settings.api_port))
    
    logger.info("=" * 60)
    logger.info("OPTIONS TRADING SYSTEM")
    logger.info("=" * 60)
    logger.info(f"Trading Mode: {settings.trading_mode.upper()}")
    logger.info(f"Max Position Size: ${settings.max_position_size:,.2f}")
    logger.info(f"Max Daily Loss: ${settings.max_daily_loss:,.2f}")
    logger.info(f"Profit Target: {settings.profit_target_pct * 100:.0f}%")
    logger.info(f"Stop Loss: {settings.stop_loss_pct * 100:.0f}%")
    logger.info(f"Scan Interval: {settings.scan_interval_minutes} minutes")
    logger.info(f"API Port: {port}")
    logger.info("=" * 60)
    
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Run FastAPI server
    config = uvicorn.Config(
        app,
        host="0.0.0.0",  # Bind to all interfaces for cloud deployment
        port=port,
        log_level=settings.log_level.lower()
    )
    server = uvicorn.Server(config)
    
    # Run server
    await server.serve()


def main():
    """Main entry point."""
    try:
        asyncio.run(run_system())
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        raise


if __name__ == "__main__":
    main()
