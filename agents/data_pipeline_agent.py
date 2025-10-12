"""
Data Pipeline Agent - Fetches and processes market data.
"""
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from loguru import logger

from agents.base_agent import BaseAgent
from services import get_alpaca_service


class DataPipelineAgent(BaseAgent):
    """Agent responsible for fetching and processing market data."""
    
    def __init__(self):
        """Initialize the data pipeline agent."""
        super().__init__("DataPipeline")
        self.alpaca = get_alpaca_service()
        self.watchlist = [
            "AAPL", "MSFT", "GOOGL", "AMZN", "TSLA",
            "NVDA", "META", "SPY", "QQQ", "IWM"
        ]
    
    async def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process market data request.
        
        Args:
            data: Request data with 'action' and optional 'symbols'
            
        Returns:
            Market data result
        """
        action = data.get("action")
        
        if action == "scan_opportunities":
            return await self.scan_opportunities()
        elif action == "get_market_data":
            symbols = data.get("symbols", [])
            return await self.get_market_data(symbols)
        elif action == "get_quote":
            symbol = data.get("symbol")
            return await self.get_quote(symbol)
        else:
            return {"error": f"Unknown action: {action}"}
    
    async def scan_opportunities(self) -> Dict[str, Any]:
        """
        Scan watchlist for trading opportunities.
        
        Returns:
            Dictionary with opportunities
        """
        logger.info("Scanning for opportunities...")
        
        opportunities = []
        
        for symbol in self.watchlist:
            try:
                # Get latest quote
                quote = await self.alpaca.get_latest_quote(symbol)
                if not quote:
                    continue
                
                # Get historical bars
                bars = await self.alpaca.get_bars(
                    symbol,
                    timeframe="1Day",
                    limit=30
                )
                
                if len(bars) < 20:
                    continue
                
                # Calculate basic indicators
                closes = [bar['close'] for bar in bars]
                volumes = [bar['volume'] for bar in bars]
                
                current_price = quote['ask_price']
                avg_volume = sum(volumes[-20:]) / 20
                sma_20 = sum(closes[-20:]) / 20
                
                # Simple momentum check
                price_change_pct = ((current_price - closes[-2]) / closes[-2]) * 100
                volume_ratio = volumes[-1] / avg_volume if avg_volume > 0 else 0
                
                # Check for opportunity
                if (
                    price_change_pct > 2 and  # Price up > 2%
                    volume_ratio > 1.5 and    # Volume > 1.5x average
                    current_price > sma_20     # Price above SMA
                ):
                    opportunities.append({
                        "symbol": symbol,
                        "current_price": current_price,
                        "price_change_pct": price_change_pct,
                        "volume_ratio": volume_ratio,
                        "sma_20": sma_20,
                        "bars": bars[-5:],  # Last 5 bars
                        "quote": quote,
                        "score": price_change_pct * volume_ratio  # Simple scoring
                    })
                
            except Exception as e:
                logger.error(f"Error scanning {symbol}: {e}")
                continue
        
        # Sort by score
        opportunities.sort(key=lambda x: x['score'], reverse=True)
        
        logger.info(f"Found {len(opportunities)} opportunities")
        
        return {
            "opportunities": opportunities,
            "timestamp": datetime.now().isoformat(),
            "symbols_scanned": len(self.watchlist)
        }
    
    async def get_market_data(self, symbols: List[str]) -> Dict[str, Any]:
        """
        Get market data for specific symbols.
        
        Args:
            symbols: List of symbols
            
        Returns:
            Market data dictionary
        """
        results = {}
        
        for symbol in symbols:
            try:
                quote = await self.alpaca.get_latest_quote(symbol)
                bars = await self.alpaca.get_bars(symbol, timeframe="1Day", limit=30)
                
                if quote and bars:
                    results[symbol] = {
                        "quote": quote,
                        "bars": bars,
                        "timestamp": datetime.now().isoformat()
                    }
            except Exception as e:
                logger.error(f"Error getting market data for {symbol}: {e}")
                results[symbol] = {"error": str(e)}
        
        return results
    
    async def get_quote(self, symbol: str) -> Dict[str, Any]:
        """
        Get current quote for a symbol.
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Quote data
        """
        try:
            quote = await self.alpaca.get_latest_quote(symbol)
            return quote or {"error": "Quote not found"}
        except Exception as e:
            logger.error(f"Error getting quote for {symbol}: {e}")
            return {"error": str(e)}
    
    def add_to_watchlist(self, symbol: str) -> bool:
        """Add symbol to watchlist."""
        if symbol not in self.watchlist:
            self.watchlist.append(symbol)
            logger.info(f"Added {symbol} to watchlist")
            return True
        return False  # Already in watchlist
    
    def is_in_watchlist(self, symbol: str) -> bool:
        """Check if symbol is in watchlist."""
        return symbol in self.watchlist
    
    def get_watchlist(self) -> list:
        """Get current watchlist."""
        return self.watchlist.copy()
    
    def remove_from_watchlist(self, symbol: str):
        """Remove symbol from watchlist."""
        if symbol in self.watchlist:
            self.watchlist.remove(symbol)
            logger.info(f"Removed {symbol} from watchlist")
