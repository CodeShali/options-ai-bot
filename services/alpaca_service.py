"""
Alpaca API service for options trading.
"""
import asyncio
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import (
    GetOrdersRequest,
    MarketOrderRequest,
    LimitOrderRequest,
    StopLossRequest,
    TakeProfitRequest
)
from alpaca.trading.enums import OrderSide, TimeInForce, OrderType, QueryOrderStatus, AssetClass
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest, StockLatestQuoteRequest
from alpaca.data.timeframe import TimeFrame
from loguru import logger

from config import settings


class AlpacaService:
    """Service for interacting with Alpaca API."""
    
    def __init__(self):
        """Initialize Alpaca service."""
        self.trading_client = TradingClient(
            api_key=settings.alpaca_api_key,
            secret_key=settings.alpaca_secret_key,
            paper=settings.is_paper_trading
        )
        self.data_client = StockHistoricalDataClient(
            api_key=settings.alpaca_api_key,
            secret_key=settings.alpaca_secret_key
        )
        logger.info(f"Alpaca service initialized in {settings.trading_mode} mode")
    
    async def get_account(self) -> Dict[str, Any]:
        """
        Get account information.
        
        Returns:
            Account information dictionary
        """
        try:
            account = await asyncio.to_thread(self.trading_client.get_account)
            return {
                "equity": float(account.equity),
                "cash": float(account.cash),
                "buying_power": float(account.buying_power),
                "portfolio_value": float(account.portfolio_value),
                "pattern_day_trader": account.pattern_day_trader,
                "trading_blocked": account.trading_blocked,
                "account_blocked": account.account_blocked,
                "daytrade_count": account.daytrade_count,
            }
        except Exception as e:
            logger.error(f"Error getting account info: {e}")
            raise
    
    async def get_positions(self) -> List[Dict[str, Any]]:
        """
        Get all open positions.
        
        Returns:
            List of position dictionaries
        """
        try:
            positions = await asyncio.to_thread(self.trading_client.get_all_positions)
            return [
                {
                    "symbol": pos.symbol,
                    "qty": float(pos.qty),
                    "avg_entry_price": float(pos.avg_entry_price),
                    "current_price": float(pos.current_price),
                    "market_value": float(pos.market_value),
                    "cost_basis": float(pos.cost_basis),
                    "unrealized_pl": float(pos.unrealized_pl),
                    "unrealized_plpc": float(pos.unrealized_plpc),
                    "side": pos.side,
                }
                for pos in positions
            ]
        except Exception as e:
            logger.error(f"Error getting positions: {e}")
            raise
    
    async def get_position(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific position.
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Position dictionary or None if not found
        """
        try:
            position = await asyncio.to_thread(
                self.trading_client.get_open_position,
                symbol
            )
            return {
                "symbol": position.symbol,
                "qty": float(position.qty),
                "avg_entry_price": float(position.avg_entry_price),
                "current_price": float(position.current_price),
                "market_value": float(position.market_value),
                "cost_basis": float(position.cost_basis),
                "unrealized_pl": float(position.unrealized_pl),
                "unrealized_plpc": float(position.unrealized_plpc),
                "side": position.side,
            }
        except Exception as e:
            logger.debug(f"Position not found for {symbol}: {e}")
            return None
    
    async def place_market_order(
        self,
        symbol: str,
        qty: int,
        side: str,
        time_in_force: str = "day"
    ) -> Dict[str, Any]:
        """
        Place a market order.
        
        Args:
            symbol: Stock symbol
            qty: Quantity
            side: Order side ('buy' or 'sell')
            time_in_force: Time in force ('day', 'gtc', 'ioc', 'fok')
            
        Returns:
            Order information dictionary
        """
        try:
            order_side = OrderSide.BUY if side.lower() == "buy" else OrderSide.SELL
            tif = TimeInForce[time_in_force.upper()]
            
            request = MarketOrderRequest(
                symbol=symbol,
                qty=qty,
                side=order_side,
                time_in_force=tif
            )
            
            order = await asyncio.to_thread(
                self.trading_client.submit_order,
                request
            )
            
            logger.info(f"Market order placed: {side} {qty} {symbol}")
            return self._order_to_dict(order)
        except Exception as e:
            logger.error(f"Error placing market order: {e}")
            raise
    
    async def place_limit_order(
        self,
        symbol: str,
        qty: int,
        side: str,
        limit_price: float,
        time_in_force: str = "day"
    ) -> Dict[str, Any]:
        """
        Place a limit order.
        
        Args:
            symbol: Stock symbol
            qty: Quantity
            side: Order side ('buy' or 'sell')
            limit_price: Limit price
            time_in_force: Time in force ('day', 'gtc', 'ioc', 'fok')
            
        Returns:
            Order information dictionary
        """
        try:
            order_side = OrderSide.BUY if side.lower() == "buy" else OrderSide.SELL
            tif = TimeInForce[time_in_force.upper()]
            
            request = LimitOrderRequest(
                symbol=symbol,
                qty=qty,
                side=order_side,
                time_in_force=tif,
                limit_price=limit_price
            )
            
            order = await asyncio.to_thread(
                self.trading_client.submit_order,
                request
            )
            
            logger.info(f"Limit order placed: {side} {qty} {symbol} @ ${limit_price}")
            return self._order_to_dict(order)
        except Exception as e:
            logger.error(f"Error placing limit order: {e}")
            raise
    
    async def cancel_order(self, order_id: str) -> bool:
        """
        Cancel an order.
        
        Args:
            order_id: Order ID
            
        Returns:
            True if successful
        """
        try:
            await asyncio.to_thread(self.trading_client.cancel_order_by_id, order_id)
            logger.info(f"Order cancelled: {order_id}")
            return True
        except Exception as e:
            logger.error(f"Error cancelling order: {e}")
            return False
    
    async def get_orders(
        self,
        status: str = "open",
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get orders.
        
        Args:
            status: Order status ('open', 'closed', 'all')
            limit: Maximum number of orders to return
            
        Returns:
            List of order dictionaries
        """
        try:
            status_enum = QueryOrderStatus[status.upper()]
            request = GetOrdersRequest(
                status=status_enum,
                limit=limit
            )
            
            orders = await asyncio.to_thread(
                self.trading_client.get_orders,
                request
            )
            
            return [self._order_to_dict(order) for order in orders]
        except Exception as e:
            logger.error(f"Error getting orders: {e}")
            raise
    
    async def get_bars(
        self,
        symbol: str,
        timeframe: str = "1Day",
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get historical bars.
        
        Args:
            symbol: Stock symbol
            timeframe: Timeframe ('1Min', '5Min', '15Min', '1Hour', '1Day')
            start: Start datetime
            end: End datetime
            limit: Maximum number of bars
            
        Returns:
            List of bar dictionaries
        """
        try:
            if start is None:
                start = datetime.now() - timedelta(days=30)
            if end is None:
                end = datetime.now()
            
            timeframe_map = {
                "1Min": TimeFrame.Minute,
                "5Min": TimeFrame(5, "Min"),
                "15Min": TimeFrame(15, "Min"),
                "1Hour": TimeFrame.Hour,
                "1Day": TimeFrame.Day,
            }
            
            tf = timeframe_map.get(timeframe, TimeFrame.Day)
            
            request = StockBarsRequest(
                symbol_or_symbols=symbol,
                timeframe=tf,
                start=start,
                end=end,
                limit=limit
            )
            
            bars = await asyncio.to_thread(
                self.data_client.get_stock_bars,
                request
            )
            
            result = []
            if symbol in bars:
                for bar in bars[symbol]:
                    result.append({
                        "timestamp": bar.timestamp,
                        "open": float(bar.open),
                        "high": float(bar.high),
                        "low": float(bar.low),
                        "close": float(bar.close),
                        "volume": int(bar.volume),
                    })
            
            return result
        except Exception as e:
            logger.error(f"Error getting bars: {e}")
            raise
    
    async def get_latest_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get latest quote for a symbol.
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Quote dictionary or None
        """
        try:
            request = StockLatestQuoteRequest(symbol_or_symbols=symbol)
            quotes = await asyncio.to_thread(
                self.data_client.get_stock_latest_quote,
                request
            )
            
            if symbol in quotes:
                quote = quotes[symbol]
                return {
                    "symbol": symbol,
                    "bid_price": float(quote.bid_price),
                    "ask_price": float(quote.ask_price),
                    "bid_size": int(quote.bid_size),
                    "ask_size": int(quote.ask_size),
                    "timestamp": quote.timestamp,
                }
            return None
        except Exception as e:
            logger.error(f"Error getting quote: {e}")
            return None
    
    async def close_position(self, symbol: str) -> bool:
        """
        Close a position.
        
        Args:
            symbol: Stock symbol
            
        Returns:
            True if successful
        """
        try:
            await asyncio.to_thread(
                self.trading_client.close_position,
                symbol
            )
            logger.info(f"Position closed: {symbol}")
            return True
        except Exception as e:
            logger.error(f"Error closing position: {e}")
            return False
    
    async def close_all_positions(self) -> bool:
        """
        Close all positions.
        
        Returns:
            True if successful
        """
        try:
            await asyncio.to_thread(self.trading_client.close_all_positions)
            logger.info("All positions closed")
            return True
        except Exception as e:
            logger.error(f"Error closing all positions: {e}")
            return False
    
    def _order_to_dict(self, order) -> Dict[str, Any]:
        """Convert order object to dictionary."""
        return {
            "id": order.id,
            "client_order_id": order.client_order_id,
            "symbol": order.symbol,
            "qty": float(order.qty) if order.qty else None,
            "filled_qty": float(order.filled_qty) if order.filled_qty else 0,
            "side": order.side.value if order.side else None,
            "type": order.type.value if order.type else None,
            "status": order.status.value if order.status else None,
            "limit_price": float(order.limit_price) if order.limit_price else None,
            "filled_avg_price": float(order.filled_avg_price) if order.filled_avg_price else None,
            "created_at": order.created_at,
            "updated_at": order.updated_at,
            "submitted_at": order.submitted_at,
            "filled_at": order.filled_at,
        }
    
    # ============= OPTIONS TRADING METHODS =============
    
    async def get_options_chain(self, symbol: str) -> Dict[str, Any]:
        """
        Get options chain for a symbol using Alpaca API.
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Options chain with calls and puts
        """
        try:
            # Calculate expiration date range
            today = datetime.now()
            min_expiration = today + timedelta(days=settings.options_min_dte)
            max_expiration = today + timedelta(days=settings.options_max_dte)
            
            # Use trading client to get options contracts
            # Note: Alpaca's options API may require specific endpoints
            # For now, we'll create a mock structure that can be replaced with actual API calls
            
            import requests
            
            # Alpaca options endpoint (if available in your account)
            url = f"{settings.alpaca_base_url}/v2/options/contracts"
            headers = {
                "APCA-API-KEY-ID": settings.alpaca_api_key,
                "APCA-API-SECRET-KEY": settings.alpaca_secret_key
            }
            params = {
                "underlying_symbol": symbol,
                "expiration_date_gte": min_expiration.strftime("%Y-%m-%d"),
                "expiration_date_lte": max_expiration.strftime("%Y-%m-%d")
            }
            
            response = await asyncio.to_thread(
                requests.get,
                url,
                headers=headers,
                params=params
            )
            
            if response.status_code != 200:
                logger.warning(f"Options chain API returned {response.status_code} for {symbol}")
                return self._create_mock_options_chain(symbol, min_expiration, max_expiration)
            
            data = response.json()
            
            # Organize by expiration and type
            organized_chain = {
                "symbol": symbol,
                "expirations": {},
                "calls": [],
                "puts": []
            }
            
            for contract in data.get("option_contracts", []):
                exp_date = contract.get("expiration_date")
                if exp_date not in organized_chain["expirations"]:
                    organized_chain["expirations"][exp_date] = {"calls": [], "puts": []}
                
                contract_info = {
                    "symbol": contract.get("symbol"),
                    "strike": float(contract.get("strike_price", 0)),
                    "expiration": exp_date,
                    "type": contract.get("type", "call")
                }
                
                if contract.get("type") == "call":
                    organized_chain["calls"].append(contract_info)
                    organized_chain["expirations"][exp_date]["calls"].append(contract_info)
                else:
                    organized_chain["puts"].append(contract_info)
                    organized_chain["expirations"][exp_date]["puts"].append(contract_info)
            
            return organized_chain
            
        except Exception as e:
            logger.error(f"Error getting options chain for {symbol}: {e}")
            # Return mock chain for testing
            return self._create_mock_options_chain(symbol, min_expiration, max_expiration)
    
    def _create_mock_options_chain(self, symbol: str, min_exp: datetime, max_exp: datetime) -> Dict[str, Any]:
        """Create a mock options chain for testing when API is unavailable."""
        # Get current price
        import random
        
        # Create mock expiration dates
        exp_date = (datetime.now() + timedelta(days=35)).strftime("%Y-%m-%d")
        
        # Mock strikes around a base price (you'd get this from current quote)
        base_price = 175.0  # Mock base price
        strikes = [base_price + (i * 5) for i in range(-3, 4)]
        
        organized_chain = {
            "symbol": symbol,
            "expirations": {exp_date: {"calls": [], "puts": []}},
            "calls": [],
            "puts": []
        }
        
        for strike in strikes:
            call_contract = {
                "symbol": self.format_option_symbol(symbol, exp_date, "call", strike),
                "strike": strike,
                "expiration": exp_date,
                "type": "call"
            }
            put_contract = {
                "symbol": self.format_option_symbol(symbol, exp_date, "put", strike),
                "strike": strike,
                "expiration": exp_date,
                "type": "put"
            }
            
            organized_chain["calls"].append(call_contract)
            organized_chain["puts"].append(put_contract)
            organized_chain["expirations"][exp_date]["calls"].append(call_contract)
            organized_chain["expirations"][exp_date]["puts"].append(put_contract)
        
        logger.warning(f"Using mock options chain for {symbol} - API may not be available")
        return organized_chain
    
    async def get_option_quote(self, option_symbol: str, include_greeks: bool = True) -> Optional[Dict[str, Any]]:
        """
        Get quote for a specific option contract with Greeks.
        
        Args:
            option_symbol: Option symbol (e.g., AAPL251220C00180000)
            include_greeks: Whether to include Greeks data
            
        Returns:
            Option quote with bid, ask, price, and Greeks
        """
        try:
            # Try to get real quote from Alpaca
            # Note: This requires options trading approval
            try:
                # Attempt real API call (will work after Alpaca options approval)
                snapshot = self.trading_client.get_option_snapshot(option_symbol)
                
                quote = {
                    "symbol": option_symbol,
                    "bid": snapshot.latest_quote.bid_price,
                    "ask": snapshot.latest_quote.ask_price,
                    "price": (snapshot.latest_quote.bid_price + snapshot.latest_quote.ask_price) / 2,
                    "bid_size": snapshot.latest_quote.bid_size,
                    "ask_size": snapshot.latest_quote.ask_size,
                    "timestamp": datetime.now(),
                    "data_source": "real"
                }
                
                # Add Greeks if available and requested
                if include_greeks and hasattr(snapshot, 'greeks'):
                    quote["greeks"] = {
                        "delta": snapshot.greeks.delta,
                        "gamma": snapshot.greeks.gamma,
                        "theta": snapshot.greeks.theta,
                        "vega": snapshot.greeks.vega,
                        "rho": snapshot.greeks.rho if hasattr(snapshot.greeks, 'rho') else None
                    }
                    logger.info(f"Real Greeks for {option_symbol}: Delta={quote['greeks']['delta']:.3f}")
                elif include_greeks:
                    # Calculate estimated Greeks if not provided
                    quote["greeks"] = self._estimate_greeks(option_symbol)
                
                return quote
                
            except Exception as api_error:
                # Fallback to mock data if API not available
                logger.debug(f"Real options API not available, using mock: {api_error}")
                
                import random
                
                # Mock premium between $2-$8
                mock_price = random.uniform(2.0, 8.0)
                
                quote = {
                    "symbol": option_symbol,
                    "bid": mock_price - 0.05,
                    "ask": mock_price + 0.05,
                    "price": mock_price,
                    "bid_size": 10,
                    "ask_size": 10,
                    "timestamp": datetime.now(),
                    "data_source": "mock"
                }
                
                # Add estimated Greeks
                if include_greeks:
                    quote["greeks"] = self._estimate_greeks(option_symbol)
                
                return quote
            
        except Exception as e:
            logger.error(f"Error getting option quote for {option_symbol}: {e}")
            return None
    
    def _estimate_greeks(self, option_symbol: str) -> Dict[str, float]:
        """
        Estimate Greeks for an option contract.
        
        This is a simplified estimation. Real Greeks should come from Alpaca API.
        
        Args:
            option_symbol: Option symbol
            
        Returns:
            Estimated Greeks
        """
        try:
            # Parse option symbol to get type and strike
            parsed = self.parse_option_symbol(option_symbol)
            if not parsed:
                return self._default_greeks()
            
            option_type = parsed['option_type']
            
            # Simplified Greek estimates based on option type
            # These are rough approximations for testing
            if option_type == 'call':
                return {
                    "delta": 0.65,      # Calls: positive delta (0.5-0.8 for ATM/slightly OTM)
                    "gamma": 0.05,      # Rate of delta change
                    "theta": -0.08,     # Time decay per day (negative)
                    "vega": 0.15,       # Volatility sensitivity
                    "rho": 0.10,        # Interest rate sensitivity
                    "estimated": True
                }
            else:  # put
                return {
                    "delta": -0.35,     # Puts: negative delta (-0.3 to -0.5 for OTM)
                    "gamma": 0.05,      # Rate of delta change
                    "theta": -0.08,     # Time decay per day (negative)
                    "vega": 0.15,       # Volatility sensitivity
                    "rho": -0.10,       # Interest rate sensitivity (negative for puts)
                    "estimated": True
                }
        except Exception as e:
            logger.error(f"Error estimating Greeks: {e}")
            return self._default_greeks()
    
    def _default_greeks(self) -> Dict[str, float]:
        """Return default Greeks when estimation fails."""
        return {
            "delta": 0.50,
            "gamma": 0.05,
            "theta": -0.08,
            "vega": 0.15,
            "rho": 0.05,
            "estimated": True
        }
    
    def format_option_symbol(self, underlying: str, expiration: str, 
                            option_type: str, strike: float) -> str:
        """
        Format option symbol in OCC format.
        
        Args:
            underlying: Stock symbol (e.g., AAPL)
            expiration: Expiration date (YYYY-MM-DD)
            option_type: 'call' or 'put'
            strike: Strike price
            
        Returns:
            Formatted option symbol (e.g., AAPL251220C00180000)
        """
        # Parse expiration date
        exp_date = datetime.strptime(expiration, "%Y-%m-%d")
        
        # Format: SYMBOL + YYMMDD + C/P + Strike (8 digits)
        symbol_part = underlying.ljust(6)[:6]  # Pad to 6 chars
        date_part = exp_date.strftime("%y%m%d")
        type_part = "C" if option_type.lower() == "call" else "P"
        strike_part = f"{int(strike * 1000):08d}"  # Strike in thousands, 8 digits
        
        return f"{symbol_part}{date_part}{type_part}{strike_part}"
    
    async def place_option_order(self, underlying: str, quantity: int,
                                strike: float, expiration: str,
                                option_type: str, side: str = "buy") -> Dict[str, Any]:
        """
        Place an options order.
        
        Args:
            underlying: Stock symbol
            quantity: Number of contracts
            strike: Strike price
            expiration: Expiration date (YYYY-MM-DD)
            option_type: 'call' or 'put'
            side: 'buy' or 'sell'
            
        Returns:
            Order result
        """
        try:
            # Format option symbol
            option_symbol = self.format_option_symbol(
                underlying, expiration, option_type, strike
            )
            
            # Create market order
            order_side = OrderSide.BUY if side.lower() == "buy" else OrderSide.SELL
            
            order_request = MarketOrderRequest(
                symbol=option_symbol,
                qty=quantity,
                side=order_side,
                time_in_force=TimeInForce.DAY
            )
            
            order = await asyncio.to_thread(
                self.trading_client.submit_order,
                order_request
            )
            
            logger.info(
                f"Options order placed: {side.upper()} {quantity} {underlying} "
                f"{option_type} ${strike} exp {expiration}"
            )
            
            return {
                "success": True,
                "order_id": order.id,
                "symbol": option_symbol,
                "underlying": underlying,
                "quantity": quantity,
                "strike": strike,
                "expiration": expiration,
                "option_type": option_type,
                "side": side
            }
            
        except Exception as e:
            logger.error(f"Error placing options order: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_option_positions(self) -> List[Dict[str, Any]]:
        """
        Get all open options positions.
        
        Returns:
            List of options positions
        """
        try:
            positions = await asyncio.to_thread(self.trading_client.get_all_positions)
            
            options_positions = []
            for pos in positions:
                # Check if it's an options position (symbol format check)
                if len(pos.symbol) > 10:  # Options symbols are longer
                    # Parse option symbol
                    parsed = self.parse_option_symbol(pos.symbol)
                    
                    # Calculate days to expiration
                    exp_date = datetime.strptime(parsed['expiration'], "%Y-%m-%d")
                    dte = (exp_date - datetime.now()).days
                    
                    options_positions.append({
                        "symbol": pos.symbol,
                        "underlying": parsed['underlying'],
                        "option_type": parsed['option_type'],
                        "strike": parsed['strike'],
                        "expiration": parsed['expiration'],
                        "dte": dte,
                        "qty": int(pos.qty),
                        "avg_entry_price": float(pos.avg_entry_price),
                        "current_price": float(pos.current_price),
                        "market_value": float(pos.market_value),
                        "cost_basis": float(pos.cost_basis),
                        "unrealized_pl": float(pos.unrealized_pl),
                        "unrealized_plpc": float(pos.unrealized_plpc),
                        "side": pos.side
                    })
            
            return options_positions
            
        except Exception as e:
            logger.error(f"Error getting options positions: {e}")
            return []
    
    def parse_option_symbol(self, option_symbol: str) -> Dict[str, str]:
        """
        Parse OCC option symbol format.
        
        Args:
            option_symbol: Option symbol (e.g., AAPL251220C00180000)
            
        Returns:
            Parsed components
        """
        try:
            # Format: SYMBOL(6) + YYMMDD(6) + C/P(1) + STRIKE(8)
            underlying = option_symbol[:6].strip()
            date_part = option_symbol[6:12]
            option_type = "call" if option_symbol[12] == "C" else "put"
            strike_part = option_symbol[13:21]
            
            # Parse date
            exp_date = datetime.strptime(date_part, "%y%m%d")
            expiration = exp_date.strftime("%Y-%m-%d")
            
            # Parse strike
            strike = int(strike_part) / 1000.0
            
            return {
                "underlying": underlying,
                "expiration": expiration,
                "option_type": option_type,
                "strike": strike
            }
            
        except Exception as e:
            logger.error(f"Error parsing option symbol {option_symbol}: {e}")
            return {
                "underlying": "UNKNOWN",
                "expiration": "2025-01-01",
                "option_type": "call",
                "strike": 0.0
            }
    
    async def close_option_position(self, option_symbol: str) -> bool:
        """
        Close an options position.
        
        Args:
            option_symbol: Option symbol to close
            
        Returns:
            True if successful
        """
        try:
            # Get position to determine quantity
            position = await asyncio.to_thread(
                self.trading_client.get_open_position,
                option_symbol
            )
            
            if not position:
                logger.warning(f"No position found for {option_symbol}")
                return False
            
            # Place closing order
            order_side = OrderSide.SELL if position.side == "long" else OrderSide.BUY
            
            order_request = MarketOrderRequest(
                symbol=option_symbol,
                qty=abs(int(position.qty)),
                side=order_side,
                time_in_force=TimeInForce.DAY
            )
            
            await asyncio.to_thread(
                self.trading_client.submit_order,
                order_request
            )
            
            logger.info(f"Closed options position: {option_symbol}")
            return True
            
        except Exception as e:
            logger.error(f"Error closing options position {option_symbol}: {e}")
            return False


# Global instance
_alpaca_service: Optional[AlpacaService] = None


def get_alpaca_service() -> AlpacaService:
    """Get the global Alpaca service instance."""
    global _alpaca_service
    if _alpaca_service is None:
        _alpaca_service = AlpacaService()
    return _alpaca_service
