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
            replace_existing=True
        )
        
        logger.info("Scheduled jobs configured")
    
    async def _scan_and_trade_job(self):
        """Job to scan for opportunities and execute trades."""
        try:
            logger.info("Running scheduled scan and trade job")
            
            # Check if market is open (simplified check)
            now = datetime.now()
            if now.weekday() >= 5:  # Weekend
                logger.info("Market closed (weekend), skipping scan")
                return
            
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
    
    async def _daily_summary_job(self):
        """Job to generate daily summary."""
        try:
            logger.info("Generating daily summary")
            
            from services import get_alpaca_service, get_llm_service
            
            alpaca = get_alpaca_service()
            llm = get_llm_service()
            
            # Get data
            account = await alpaca.get_account()
            positions = await alpaca.get_positions()
            recent_trades = await self.orchestrator.db.get_recent_trades(10)
            
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
