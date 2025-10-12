"""
Quick test to check PLTR data fetching
"""
import asyncio
from services.alpaca_service import get_alpaca_service

async def test_pltr():
    alpaca = get_alpaca_service()
    
    print("=" * 60)
    print("Testing PLTR Data Fetch")
    print("=" * 60)
    
    # Test 1: Get quote
    print("\n1. Testing get_latest_quote(PLTR)...")
    quote = await alpaca.get_latest_quote("PLTR")
    print(f"Quote: {quote}")
    
    # Test 2: Get bars
    print("\n2. Testing get_bars(PLTR, 1Day, 5)...")
    bars = await alpaca.get_bars("PLTR", timeframe="1Day", limit=5)
    print(f"Bars count: {len(bars) if bars else 0}")
    if bars:
        print(f"Latest bar: {bars[-1]}")
    
    # Test 3: Get options chain
    print("\n3. Testing get_options_chain(PLTR)...")
    chain = await alpaca.get_options_chain("PLTR")
    print(f"Options available: {chain.get('calls', []) != []}")
    if chain.get('underlying_price'):
        print(f"Underlying price from chain: ${chain['underlying_price']}")
    
    print("\n" + "=" * 60)
    print("Test Complete")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_pltr())
