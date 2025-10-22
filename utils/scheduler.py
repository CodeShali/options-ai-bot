"""
Scheduler for periodic tasks.
"""
import asyncio
from typing import Callable, Optional
from datetime import datetime, time
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from loguru import logger

from config import settings


class TradingScheduler:
    """Scheduler for trading system tasks."""
    
    def __init__(self):
        """Initialize the scheduler."""
        self.scheduler = AsyncIOScheduler()
        self.orchestrator = None
        logger.info("Scheduler initialized")
    
    def set_orchestrator(self, orchestrator):
        """Set the orchestrator reference."""
        self.orchestrator = orchestrator
    
    def setup_jobs(self):
        """Setup scheduled jobs."""
        if not self.orchestrator:
            logger.error("Orchestrator not set, cannot setup jobs")
            return
        
        # Scan for opportunities every N minutes during market hours
        self.scheduler.add_job(
            self._scan_and_trade_job,
            trigger=IntervalTrigger(minutes=settings.scan_interval_minutes),
            id="scan_and_trade",
            name="Scan and Trade",
            replace_existing=True
        )
        
        # Monitor positions every 2 minutes
        self.scheduler.add_job(
            self._monitor_positions_job,
            trigger=IntervalTrigger(minutes=2),
            id="monitor_positions",
            name="Monitor Positions",
            replace_existing=True
        )
        
        # Reset circuit breaker daily at market open (9:30 AM ET)
        self.scheduler.add_job(
            self._reset_circuit_breaker_job,
            trigger=CronTrigger(hour=9, minute=30, timezone="America/New_York"),
            id="reset_circuit_breaker",
            name="Reset Circuit Breaker",
            replace_existing=True
        )
        
        # Daily summary at market close (4:00 PM ET)
        self.scheduler.add_job(
            self._daily_summary_job,
            trigger=CronTrigger(hour=16, minute=0, timezone="America/New_York"),
            id="daily_summary",
            name="Daily Summary",
        )
        
        # Hourly summary during market hours (every hour on the hour)
        self.scheduler.add_job(
            self._hourly_summary_job,
            trigger=CronTrigger(minute=0, timezone="America/New_York"),
            id="hourly_summary",
            name="Hourly Summary",
            replace_existing=True
        )
        
        logger.info("Scheduled jobs configured")
    
    async def _scan_and_trade_job(self):
        """Job to scan and execute trades."""
        try:
            logger.info("Running scheduled scan and trade job")
            
            # Check if market is open (respect market hours even in test mode for alerts)
            from config import settings
            now = datetime.now()
            
            # Always check weekends
            if now.weekday() >= 5:  # Weekend
                logger.info("Market closed (weekend), skipping scan")
                return
            
            # Check market hours (9:30 AM - 4:00 PM ET)
            market_hour = now.hour
            if market_hour < 9 or market_hour >= 16:
                logger.info(f"Market closed (hour: {market_hour}), skipping scan")
                return
            
            if settings.test_mode:
                logger.info("🧪 TEST MODE: Market hours respected, proceeding with scan")
            
            result = await self.orchestrator.scan_and_trade()
            logger.info(f"Scan and trade job completed: {result.get('status')}")
            
        except Exception as e:
            logger.error(f"Error in scan and trade job: {e}")
    
    async def _monitor_positions_job(self):
        """Job to monitor positions and execute exits."""
        try:
            logger.debug("Running scheduled monitor positions job")
            
            result = await self.orchestrator.monitor_and_exit()
            logger.debug(f"Monitor positions job completed: {result.get('status')}")
            
        except Exception as e:
            logger.error(f"Error in monitor positions job: {e}")
    
    async def _reset_circuit_breaker_job(self):
        """Job to reset circuit breaker at market open."""
        try:
            logger.info("Resetting circuit breaker for new trading day")
            
            await self.orchestrator.risk_manager.reset_circuit_breaker()
            
            # Send notification
            if self.orchestrator.discord_bot:
                await self.orchestrator.discord_bot.send_notification(
                    "🔄 New trading day - circuit breaker reset"
                )
            
        except Exception as e:
            logger.error(f"Error resetting circuit breaker: {e}")
    
    async def _hourly_summary_job(self):
        """Job to generate hourly summary."""
        try:
            from datetime import datetime
            now = datetime.now()
            
            # Only run during market hours (9 AM - 4 PM ET)
            if now.weekday() >= 5 or now.hour < 9 or now.hour >= 16:
                logger.debug("Skipping hourly summary - market closed")
                return
            
            logger.info("Running hourly summary job")
            
            # Import and use hourly summary service
            from services.hourly_summary_service import get_hourly_summary_service
            
            # Get bot reference from orchestrator
            bot = getattr(self.orchestrator, 'bot', None) if self.orchestrator else None
            
            summary_service = get_hourly_summary_service(bot)
            await summary_service.generate_hourly_summary()
            
            logger.info("Hourly summary job completed")
            
        except Exception as e:
            logger.error(f"Error in hourly summary job: {e}")
    
    async def _daily_summary_job(self):
        """Job to generate daily summary."""
        try:
            logger.info("Running daily summary job")
            # This would generate and send a daily summary
            # Implementation depends on your summary requirements
            
            # Generate AI summary
            summary = await llm.generate_market_summary(
                positions,
                account,
                recent_trades
            )
            
            # Send to Discord
            if self.orchestrator.discord_bot:
                await self.orchestrator.discord_bot.send_notification(
                    f"📊 **Daily Summary**\n\n{summary}"
                )
            
            logger.info("Daily summary generated and sent")
            
        except Exception as e:
            logger.error(f"Error generating daily summary: {e}")
    
    def start(self):
        """Start the scheduler."""
        self.scheduler.start()
        logger.info("Scheduler started")
    
    def shutdown(self):
        """Shutdown the scheduler."""
        self.scheduler.shutdown()
        logger.info("Scheduler shutdown")
    
    def pause_job(self, job_id: str):
        """Pause a specific job."""
        self.scheduler.pause_job(job_id)
        logger.info(f"Job paused: {job_id}")
    
    def resume_job(self, job_id: str):
        """Resume a specific job."""
        self.scheduler.resume_job(job_id)
        logger.info(f"Job resumed: {job_id}")
    
    def get_jobs(self):
        """Get all scheduled jobs."""
        return self.scheduler.get_jobs()
