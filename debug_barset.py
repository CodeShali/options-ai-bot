#!/usr/bin/env python3
"""Debug BarSet structure."""
import asyncio
from services.alpaca_service import AlpacaService
from datetime import datetime, timedelta

async def debug_barset():
    alpaca = AlpacaService()
    
    symbol = "SPY"
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)
    
    print(f"Requesting bars for {symbol}...")
    
    # Get the raw bars object
    from alpaca.data.requests import StockBarsRequest
    from alpaca.data.timeframe import TimeFrame
    
    request = StockBarsRequest(
        symbol_or_symbols=symbol,
        timeframe=TimeFrame.Day,
        start=start_date,
        end=end_date,
        limit=5,
        feed="iex"
    )
    
    bars = await asyncio.to_thread(
        alpaca.data_client.get_stock_bars,
        request
    )
    
    print(f"\nBarSet object: {bars}")
    print(f"Type: {type(bars)}")
    print(f"Bool: {bool(bars)}")
    print(f"\nDir: {[x for x in dir(bars) if not x.startswith('_')]}")
    
    # Try different ways to access
    print(f"\n'SPY' in bars: {symbol in bars}")
    print(f"'spy' in bars: {'spy' in bars}")
    
    # Try to iterate
    try:
        print(f"\nTrying to access bars['{symbol}']...")
        data = bars[symbol]
        print(f"Success! Got {len(list(data))} bars")
        for i, bar in enumerate(data):
            if i < 2:
                print(f"  Bar {i}: close={bar.close}, volume={bar.volume}")
    except Exception as e:
        print(f"Error: {e}")
    
    # Try data attribute
    try:
        print(f"\nTrying bars.data...")
        print(f"bars.data: {bars.data}")
    except Exception as e:
        print(f"No .data attribute: {e}")
    
    # Try dict access
    try:
        print(f"\nTrying bars.dict()...")
        print(f"bars.dict(): {bars.dict()}")
    except Exception as e:
        print(f"No .dict() method: {e}")

if __name__ == "__main__":
    asyncio.run(debug_barset())
