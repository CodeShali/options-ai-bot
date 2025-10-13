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
    
    async def scan_opportunities(self, custom_symbols: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Scan watchlist for trading opportunities using intelligent scanner.
        
        Args:
            custom_symbols: Optional list of symbols to scan instead of watchlist
        
        Returns:
            Dictionary with opportunities
        """
        # Use intelligent scanner
        from agents.intelligent_scanner import IntelligentScanner
        
        scanner = IntelligentScanner()
        
        # Use custom symbols if provided, otherwise use watchlist
        symbols_to_scan = custom_symbols if custom_symbols else self.watchlist
        
        logger.info(f"🔍 Scanning {len(symbols_to_scan)} symbols with intelligent scanner...")
        
        # Run full intelligent scan
        result = await scanner.scan_with_full_analysis(symbols_to_scan)
        
        # Extract opportunities for backward compatibility
        opportunities = []
        for rec in result.get('opportunities', []):
            opportunities.append({
                "symbol": rec['symbol'],
                "current_price": rec['current_price'],
                "action": rec['action'],
                "confidence": rec['confidence'],
                "score": rec['momentum_score'],
                "reasoning": rec['reasoning'],
                "recommendation": rec  # Full recommendation
            })
        
        logger.info(f"✅ Found {len(opportunities)} opportunities")
        
        return {
            "opportunities": opportunities,
            "full_scan_result": result,
            "timestamp": datetime.now().isoformat(),
            "symbols_scanned": len(symbols_to_scan)
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
