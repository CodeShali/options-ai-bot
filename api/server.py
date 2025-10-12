"""
FastAPI server for internal agent communication and monitoring.
"""
from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from loguru import logger

from config import settings


# Request/Response models
class TradeRequest(BaseModel):
    symbol: str
    action: str
    quantity: int
    price: float
    notes: Optional[str] = None


class AgentRequest(BaseModel):
    agent: str
    action: str
    data: Optional[Dict[str, Any]] = None


class StatusResponse(BaseModel):
    status: str
    message: str
    data: Optional[Dict[str, Any]] = None


# Create FastAPI app
app = FastAPI(
    title="Options Trading System API",
    description="Internal API for agent communication and monitoring",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global orchestrator reference
orchestrator = None


def set_orchestrator(orch):
    """Set the orchestrator reference."""
    global orchestrator
    orchestrator = orch


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "Options Trading System API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")
    
    health = {
        "orchestrator": await orchestrator.health_check(),
        "data_pipeline": await orchestrator.data_pipeline.health_check(),
        "strategy": await orchestrator.strategy.health_check(),
        "risk_manager": await orchestrator.risk_manager.health_check(),
        "execution": await orchestrator.execution.health_check(),
        "monitor": await orchestrator.monitor.health_check(),
    }
    
    all_healthy = all(health.values())
    
    return {
        "status": "healthy" if all_healthy else "degraded",
        "agents": health
    }


@app.get("/status")
async def get_status():
    """Get system status."""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")
    
    try:
        from services import get_alpaca_service, get_database_service
        
        alpaca = get_alpaca_service()
        db = get_database_service()
        
        account = await alpaca.get_account()
        positions = await alpaca.get_positions()
        metrics = await db.get_performance_metrics(30)
        
        return {
            "status": "active" if not orchestrator.paused else "paused",
            "trading_mode": settings.trading_mode,
            "account": account,
            "positions": {
                "count": len(positions),
                "total_value": sum(p['market_value'] for p in positions),
                "total_pl": sum(p['unrealized_pl'] for p in positions)
            },
            "performance": metrics
        }
        
    except Exception as e:
        logger.error(f"Error getting status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/positions")
async def get_positions():
    """Get all open positions."""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")
    
    try:
        from services import get_alpaca_service
        
        alpaca = get_alpaca_service()
        positions = await alpaca.get_positions()
        
        return {
            "positions": positions,
            "count": len(positions)
        }
        
    except Exception as e:
        logger.error(f"Error getting positions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/agent/execute")
async def execute_agent_action(request: AgentRequest):
    """Execute an agent action."""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")
    
    try:
        agent_map = {
            "orchestrator": orchestrator,
            "data_pipeline": orchestrator.data_pipeline,
            "strategy": orchestrator.strategy,
            "risk_manager": orchestrator.risk_manager,
            "execution": orchestrator.execution,
            "monitor": orchestrator.monitor,
        }
        
        agent = agent_map.get(request.agent)
        if not agent:
            raise HTTPException(status_code=404, detail=f"Agent not found: {request.agent}")
        
        data = request.data or {}
        data["action"] = request.action
        
        result = await agent.process(data)
        
        return {
            "status": "success",
            "agent": request.agent,
            "action": request.action,
            "result": result
        }
        
    except Exception as e:
        logger.error(f"Error executing agent action: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/trade/manual")
async def manual_trade(symbol: str):
    """Execute a manual trade."""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")
    
    try:
        result = await orchestrator.manual_trade(symbol)
        
        return {
            "status": result.get("status"),
            "result": result
        }
        
    except Exception as e:
        logger.error(f"Error executing manual trade: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/system/pause")
async def pause_system():
    """Pause the trading system."""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")
    
    try:
        orchestrator.paused = True
        await orchestrator.db.set_system_state("paused", "true")
        
        return {
            "status": "success",
            "message": "System paused"
        }
        
    except Exception as e:
        logger.error(f"Error pausing system: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/system/resume")
async def resume_system():
    """Resume the trading system."""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")
    
    try:
        orchestrator.paused = False
        await orchestrator.db.set_system_state("paused", "false")
        
        return {
            "status": "success",
            "message": "System resumed"
        }
        
    except Exception as e:
        logger.error(f"Error resuming system: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/system/emergency-stop")
async def emergency_stop():
    """Emergency stop - close all positions and pause."""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")
    
    try:
        result = await orchestrator.emergency_stop()
        
        return {
            "status": "success",
            "message": "Emergency stop executed",
            "result": result
        }
        
    except Exception as e:
        logger.error(f"Error in emergency stop: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/dashboard")
async def get_dashboard_data():
    """Get dashboard data."""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")
    
    try:
        data = await orchestrator.monitor.generate_dashboard_data()
        
        return data
        
    except Exception as e:
        logger.error(f"Error getting dashboard data: {e}")
        raise HTTPException(status_code=500, detail=str(e))
